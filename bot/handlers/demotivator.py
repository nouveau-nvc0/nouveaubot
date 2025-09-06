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

import logging
from math import floor, ceil
import asyncio
import io

import cv2
import numpy as np
import cairo
import gi

gi.require_version("Pango", "1.0")
gi.require_version("PangoCairo", "1.0")
from gi.repository import Pango, PangoCairo

from aiogram import Dispatcher, Bot
from aiogram.types import Message, BufferedInputFile

from bot.command_filter import CommandFilter
from bot.utils.message_data_fetchers import fetch_image_from_message
from bot.utils.pool_executor import executor
from bot.handler import Handler
from bot.utils.cairo_helpers import scale_dims, scale_for_tg, image_surface_from_cv2_img, layout_text


class DemotivatorHandler(Handler):
    _BIG_FONT_SIZE = 0.052
    _SM_FONT_SIZE = 0.036
    _MIN_IMG_W = 512

    _bot: Bot

    @property
    def aliases(self) -> list[str]:
        return ["dem", "дем"]

    @property
    def description(self) -> str:
        return "сгенерировать демотиватор. разделитель - перенос строки"

    def __init__(self, dp: Dispatcher, bot: Bot) -> None:
        self._bot = bot
        CommandFilter.setup(self.aliases, dp, bot, self.handle)

    @staticmethod
    def create(img_data: bytes, text1: str, _text2: list[str]) -> bytes | str:
        text2 = '\n'.join(_text2)

        # decode via OpenCV
        nparr = np.frombuffer(img_data, np.uint8)
        cv2img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if cv2img is None:
            return "не удалось обработать изображение"

        # convert to cairo surface
        src_surf = image_surface_from_cv2_img(cv2img)
        img_surf, _ = scale_dims(src_surf)
        img_w, img_h = img_surf.get_width(), img_surf.get_height()

        # output width = floor(img.width * 1.1)
        out_w = floor(img_w * 1.1)
        # paddings and frame params per original
        img_left = floor(0.05 * img_w)
        img_top = floor(0.05 * img_w)
        stroke_width = max(1, ceil(img_w / 500))
        k = stroke_width * 4  # expansion around image for frame polygon

        # prepare text layouts to get heights
        # big line
        tmp1 = cairo.ImageSurface(cairo.FORMAT_ARGB32, out_w, 1)
        cr1 = cairo.Context(tmp1)
        big_font_px = DemotivatorHandler._BIG_FONT_SIZE * out_w
        layout1, big_w, big_h = layout_text(cr1, text1, "serif, Apple Color Emoji", big_font_px, width=out_w, alignment=Pango.Alignment.CENTER)
        
        # small block
        sm_h = 0
        layout2: Pango.Layout | None = None
        if text2:
            tmp2 = cairo.ImageSurface(cairo.FORMAT_ARGB32, out_w, 1)
            cr2 = cairo.Context(tmp2)
            sm_font_px = DemotivatorHandler._SM_FONT_SIZE * out_w
            layout2, sm_w, sm_h = layout_text(cr2, text2, "sans, Apple Color Emoji", sm_font_px, width=out_w, alignment=Pango.Alignment.CENTER)

        # compute total height:
        # dem1.height + dem2.height + img.height + floor(0.12 * img.width)
        spacer = floor(0.12 * img_w)
        out_h = (big_h + sm_h + img_h + spacer)
        out = cairo.ImageSurface(cairo.FORMAT_ARGB32, out_w, out_h)
        cr = cairo.Context(out)

        # black background
        cr.set_source_rgb(0, 0, 0)
        cr.paint()

        # white frame polygon (around image with expansion k)
        cr.save()
        cr.set_source_rgb(1, 1, 1)
        cr.set_line_width(stroke_width)
        cr.rectangle(img_left - k, img_top - k, img_w + 2 * k, img_h + 2 * k)
        cr.stroke()
        cr.restore()

        # draw image
        cr.save()
        cr.set_source_surface(img_surf, img_left, img_top)
        cr.paint()
        cr.restore()

        # y start for dem1 (original: floor(0.07 * img.width + img.height))
        img_height_top = floor(0.07 * img_w + img_h)

        # render big line (white, centered)
        cr.save()
        cr.set_source_rgb(1, 1, 1)
        cr.translate(0, img_height_top)
        PangoCairo.update_layout(cr, layout1)
        PangoCairo.show_layout(cr, layout1)
        cr.restore()

        # render small block
        cr.save()
        cr.set_source_rgb(1, 1, 1)
        cr.translate(0, img_height_top + big_h)
        if layout2 is not None:
            PangoCairo.update_layout(cr, layout2)
            PangoCairo.show_layout(cr, layout2)
        cr.restore()

        # final scale/letterbox for Telegram by helper
        final_surf = scale_for_tg(out)

        buf = io.BytesIO()
        final_surf.write_to_png(buf)
        return buf.getvalue()

    async def handle(self, message: Message, args: list[list[str]]) -> None:
        if not args:
            return
        lines = [' '.join(x) for x in args]

        photo = fetch_image_from_message(message)
        if not photo:
            await message.answer("нужно прикрепить пикчу")
            return

        stream = await self._bot.download(photo)
        if not stream:
            await message.answer("не удалось скачать пикчу")
            return

        pic = await asyncio.get_running_loop().run_in_executor(None, stream.read)
        result = await asyncio.get_running_loop().run_in_executor(executor, DemotivatorHandler.create, pic, lines[0], lines[1:])

        if isinstance(result, bytes):
            await message.answer_photo(
                BufferedInputFile(result, "image.png"),
                caption="ваша пикча",
            )
        elif isinstance(result, str):
            await message.answer(result)
        else:
            logging.error(f"Unexcepted _Demotivator.create() result: {result}")
            await message.answer("не удалось обработать пикчу")
