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

from aiogram import Dispatcher, Bot
from aiogram.types import Message, BufferedInputFile
import cv2
import numpy as np
import cairo
import gi
gi.require_version("PangoCairo", "1.0")
from gi.repository import PangoCairo

from bot.command_filter import CommandFilter
from bot.utils.message_data_fetchers import fetch_image_from_message
from bot.utils.detect_faces import detect_faces
from bot.utils.pool_executor import executor
from bot.utils.cairo_helpers import scale_dims, scale_for_tg, layout_text, image_surface_from_cv2_img
from bot.handler import Handler

import os
import json
import random
import asyncio
import logging
import io
from typing import Callable

_FRAME_WIDTH = 6
_FRAME_TEXT_FONT_SIZE = 16
_BOTTOM_TEXT_FONT_FACTOR = 0.02
_FONT_FAMILY = 'Mono'

class OmonHandler(Handler):
    _bot: Bot

    _sentences: dict[str, str]

    @property
    def aliases(self) -> list[str]:
        return ["омон", "omon"]
    
    @property
    def description(self) -> str:
        return 'статьи УК РФ для каждого на картинке'

    def __init__(self, dp: Dispatcher, bot: Bot, static_path: str) -> None:
        self._bot = bot

        with open(os.path.join(static_path, "sentences.json"), "r") as f:
            self._sentences = json.load(f)

        dp.message(CommandFilter(self.aliases))(self.handle)

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
        for i, sentence in enumerate(manual_sentences):
            if i == len(faces):
                break
            try:
                chosen_sentences.append((sentence, sentences[sentence]))
            except KeyError:
                return f'статья {sentence} не найдена'

        if len(chosen_sentences) < len(faces):
            chosen_sentences += random.sample(list(sentences.items()), len(faces) - len(chosen_sentences))

        src_surf = image_surface_from_cv2_img(cv2img)
        work_surf, scale = scale_dims(src_surf)
        scaled_w, scaled_h = work_surf.get_width(), work_surf.get_height()
        work_cr = cairo.Context(work_surf)

        label_draws: list[Callable[[], None]] = []

        # Рисуем рамки и верхний текст для каждого лица
        for i, f in enumerate(faces):
            x1 = int(f.x1 * scale); y1 = int(f.y1 * scale)
            x2 = int(f.x2 * scale); y2 = int(f.y2 * scale)
            base_y = max(y1 - _FRAME_WIDTH, 0) + _FRAME_WIDTH // 2
            base_x = x2 + _FRAME_WIDTH // 2

            # рамка
            work_cr.set_line_width(_FRAME_WIDTH)
            work_cr.set_source_rgb(0, 1.0, 0)
            work_cr.rectangle(x1, y1, x2 - x1, y2 - y1)
            work_cr.stroke()

            txt = "Статья " + chosen_sentences[i][0]
            layout_real, metrics_w, metrics_h = layout_text(work_cr, txt, _FONT_FAMILY, _FRAME_TEXT_FONT_SIZE)

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
        bottom_txt = "\n".join("Статья {}. {}".format(x, y) for (x, y) in chosen_sentences)
        bottom_font_size = _BOTTOM_TEXT_FONT_FACTOR * scaled_w

        appendix_w = scaled_w
        tmp_surf2 = cairo.ImageSurface(cairo.FORMAT_ARGB32, appendix_w, 1)
        tmp_cr2 = cairo.Context(tmp_surf2)
        layout_bottom, _, bottom_h = layout_text(tmp_cr2, bottom_txt, _FONT_FAMILY, bottom_font_size, width=appendix_w)

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

    async def handle(self, message: Message, args: list[list[str]]) -> None:
        photo = fetch_image_from_message(message)
        if not photo:
            await message.answer("нужно прикрепить пикчу")
            return

        stream = await self._bot.download(photo)
        if stream is None:
            await message.answer('не удалось скачать пикчу')
            return
        
        pic = await asyncio.get_running_loop().run_in_executor(None, stream.read)
        result = await asyncio.get_running_loop()\
            .run_in_executor(executor, self.process_image, pic, self._sentences, args[0] if args else [])

        if isinstance(result, bytes):
            buffered = BufferedInputFile(result, "image.png")
            await message.answer_photo(
                buffered,
                caption="ваша пикча"
            )
        elif isinstance(result, str):
            await message.answer(result)
        else:
            logging.error(f'Unexcepted process_image() result: {result}')
            await message.answer('не удалось обработать пикчу')

