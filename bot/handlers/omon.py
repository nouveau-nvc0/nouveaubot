# Copyright (C) 2025 nouveaubot contributors

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import io
import os
import random
import asyncio
import logging
import re
from typing import Callable

import cv2
from natsort import natsorted
import numpy as np
import cairo
import gi
gi.require_version("PangoCairo", "1.0")
from gi.repository import PangoCairo

from aiogram import Dispatcher, Bot
from aiogram.types import Message, BufferedInputFile
from aiogram.enums.parse_mode import ParseMode

from bot.command_filter import CommandFilter
from bot.utils.message_data_fetchers import fetch_image_from_message
from bot.utils.detect_faces import detect_faces
from bot.utils.pool_executor import executor
from bot.utils.cairo_helpers import scale_dims, scale_for_tg, layout_text, image_surface_from_cv2_img
from bot.handler import Handler
from bot.utils.omon_db import (
    CodeRecord, OmonDB
)


class OmonHandler(Handler):
    _FRAME_WIDTH = 6
    _FRAME_TEXT_FONT_SIZE = 16
    _BOTTOM_TEXT_FONT_FACTOR = 0.02
    _FONT_FAMILY = 'DejaVu Sans Mono'

    _bot: Bot
    _db: OmonDB

    @property
    def aliases(self) -> list[str]:
        return ["omon", "омон"]

    @property
    def description(self) -> str:
        return 'статьи УК РФ для каждого на картинке'

    def __init__(self, dp: Dispatcher, bot: Bot, static_path: str, db_file: str) -> None:
        self._bot = bot
        self._db = OmonDB.instance(db_file, os.path.join(static_path, 'omon.sql'))
        CommandFilter.setup(self.aliases, dp, bot, self._handle, allow_suffix_for=self.aliases)

    @staticmethod
    def _list_codes_text(codes: list[CodeRecord]) -> str:
        return f"""прикрепи картинку.
доступные команды для этого чата:
• /omon
{"\n".join(f'• /omon_{x.name}' for x in codes)}
"""

    @staticmethod
    def process_image(img_data: bytes, sentences: dict[str, str], manual_sentences: list[str]) -> str | bytes:
        nparr = np.frombuffer(img_data, np.uint8)
        cv2img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if cv2img is None:
            return 'не удалось обработать изображение'
        faces = detect_faces(cv2img)
        if len(faces) == 0:
            return "лица не обнаружены"
        
        chosen_sentences: list[tuple[str, str]] = []

        # ручные статьи
        for i, sentence in enumerate(manual_sentences):
            if i >= len(faces):
                break
            if sentence not in sentences:
                return f'статья {sentence} не найдена'
            chosen_sentences.append((sentence, sentences[sentence]))

        # добор до количества лиц
        remaining = len(faces) - len(chosen_sentences)
        if remaining > 0:
            exclude = {name for name, _ in chosen_sentences}
            pool = [(k, v) for k, v in sentences.items() if k not in exclude]
            if not pool:
                return 'нет статей для выбора'
            if len(pool) >= remaining:
                chosen_sentences += random.sample(pool, remaining)
            else:
                chosen_sentences += pool
                extra = remaining - len(pool)
                chosen_sentences += random.choices(pool, k=extra)

        src_surf = image_surface_from_cv2_img(cv2img)
        work_surf, scale = scale_dims(src_surf)
        scaled_w, scaled_h = work_surf.get_width(), work_surf.get_height()
        work_cr = cairo.Context(work_surf)

        label_draws: list[Callable[[], None]] = []

        # Рисуем рамки и верхний текст для каждого лица
        for i, f in enumerate(faces):
            x1 = int(f.x1 * scale); y1 = int(f.y1 * scale)
            x2 = int(f.x2 * scale); y2 = int(f.y2 * scale)
            base_y = max(y1 - OmonHandler._FRAME_WIDTH, 0) + OmonHandler._FRAME_WIDTH // 2
            base_x = x2 + OmonHandler._FRAME_WIDTH // 2

            # рамка
            work_cr.set_line_width(OmonHandler._FRAME_WIDTH)
            work_cr.set_source_rgb(0, 1.0, 0)
            work_cr.rectangle(x1, y1, x2 - x1, y2 - y1)
            work_cr.stroke()

            txt = "Статья " + chosen_sentences[i][0]
            layout_real, metrics_w, metrics_h = \
                layout_text(work_cr, txt, OmonHandler._FONT_FAMILY, OmonHandler._FRAME_TEXT_FONT_SIZE)

            def draw_label(base_x=base_x, base_y=base_y, layout=layout_real, w=metrics_w, h=metrics_h):
                work_cr.save()
                work_cr.rectangle(base_x, base_y, w, h)
                work_cr.set_source_rgb(0, 0, 0)
                work_cr.fill()
                work_cr.restore()

                work_cr.save()
                work_cr.translate(base_x, base_y)
                PangoCairo.update_layout(work_cr, layout)
                work_cr.set_source_rgb(0, 1, 0)
                PangoCairo.show_layout(work_cr, layout)
                work_cr.restore()

            label_draws.append(draw_label)

        for f in label_draws:
            f()

        # Нижний блок с перечислением статей, сразу нужной ширины
        bottom_txt = "\n".join("Статья {}. {}".format(x, y) for (x, y) in natsorted(chosen_sentences, lambda s: s[0]))
        bottom_font_size = OmonHandler._BOTTOM_TEXT_FONT_FACTOR * scaled_w

        appendix_w = scaled_w
        tmp_surf2 = cairo.ImageSurface(cairo.FORMAT_ARGB32, appendix_w, 1)
        tmp_cr2 = cairo.Context(tmp_surf2)
        layout_bottom, _, bottom_h = layout_text(tmp_cr2, bottom_txt, OmonHandler._FONT_FAMILY, bottom_font_size, width=appendix_w)

        appendix_h = max(1, bottom_h)
        appendix = cairo.ImageSurface(cairo.FORMAT_ARGB32, appendix_w, appendix_h)
        ac = cairo.Context(appendix)
        ac.set_source_rgb(0, 0, 0)
        ac.rectangle(0, 0, appendix_w, appendix_h)
        ac.fill()

        ac.save()
        ac.translate(0, 0)
        PangoCairo.update_layout(ac, layout_bottom)
        ac.set_source_rgb(0, 1, 0)
        PangoCairo.show_layout(ac, layout_bottom)
        ac.restore()

        final_w = scaled_w
        final_h = scaled_h + appendix_h
        final_surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, final_w, final_h)
        fcr = cairo.Context(final_surf)
        fcr.set_source_surface(work_surf, 0, 0)
        fcr.paint()
        fcr.set_source_surface(appendix, 0, scaled_h)
        fcr.paint()

        result = scale_for_tg(final_surf)

        out = io.BytesIO()
        result.write_to_png(out)
        return out.getvalue()

    async def _handle(self, message: Message, args: list[list[str]]) -> None:
        text = (message.text or message.caption or "").strip()
        m = re.match(r'^/(?:omon|омон)(?:_([a-z]+))?(?:\s+(.*))?$', text)
        code_name = (m.group(1).lower() if m and m.group(1) else None)
        manual_sentences = (m.group(2).split() if m and m.group(2) else [])

        photo = fetch_image_from_message(message)
        if not photo:
            codes = await self._db.get_codes(message.chat.id)
            await message.answer(self._list_codes_text(codes), parse_mode=ParseMode.HTML)
            return

        stream = await self._bot.download(photo)
        if stream is None:
            await message.answer('не удалось скачать пикчу')
            return
        pic = await asyncio.get_running_loop().run_in_executor(None, stream.read)

        code_id = await self._db.get_or_default_code_id(message.chat.id, code_name)
        sentences = await self._db.load_sentences(code_id)

        result = await asyncio.get_running_loop().run_in_executor(
            executor, self.process_image, pic, sentences, manual_sentences
        )

        if isinstance(result, bytes):
            buffered = BufferedInputFile(result, "image.png")
            await message.answer_photo(buffered, caption="ваша пикча")
        elif isinstance(result, str):
            await message.answer(result)
        else:
            logging.error(f'Unexpected process_image() result: {result}')
            await message.answer('не удалось обработать пикчу')

