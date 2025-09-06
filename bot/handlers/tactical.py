# Copyright (C) 2024 nouveaubot contributors

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
from aiogram import Dispatcher, Bot
from aiogram.types import Message, BufferedInputFile
import cairo
import cv2
import numpy as np

from bot.command_filter import CommandFilter
from bot.utils.cairo_helpers import image_surface_from_cv2_img, scale_dims, scale_for_tg
from bot.utils.message_data_fetchers import fetch_image_from_message
from bot.utils.detect_faces import detect_faces
from bot.utils.pool_executor import executor
from bot.handler import Handler

import asyncio
import logging

_BUBBLE_DOT1 = 12 / 17
_BUBBLE_DOT2 = 16 / 17
_LINE_WIDTH_K = 6 / 512
_BUBBLE_HEIGHT_K = 0.1


class TacticalHandler(Handler):
    _bot: Bot

    @property
    def aliases(self) -> list[str]:
        return ["tactical", "tact", "боевая", "бой"]
    
    @property
    def description(self) -> str:
        return 'наложить на картинку облачко говорящего'

    def __init__(self, dp: Dispatcher, bot: Bot) -> None:
        self._bot = bot

        dp.message(CommandFilter(self.aliases))(self.handle)

    @staticmethod
    def process_image(img_data: bytes, face_num: int) -> bytes | str:
        nparr = np.frombuffer(img_data, np.uint8)
        cv2img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if cv2img is None:
            return "не удалось обработать изображение"
        
        faces = detect_faces(cv2img)

        if len(faces) == 0:
            return "лица не обнаружены"
        if len(faces) < face_num + 1:
            return "такого лица нет"
        
        src_surf = image_surface_from_cv2_img(cv2img)
        img_surf, scale = scale_dims(src_surf)
        img_w, img_h = img_surf.get_width(), img_surf.get_height()
        
        line_width = _LINE_WIDTH_K * ((img_w * img_h) ** 0.5)
        face_width = faces[face_num].x2 - faces[face_num].x1

        def draw_triangle(cr: cairo.Context, x1=img_w * _BUBBLE_DOT1, y1=line_width * 0.5,
                          x2=(faces[face_num].x1 + face_width * 0.5) * scale, y2=faces[face_num].y1 * scale,
                          x3=img_w * _BUBBLE_DOT2, y3=line_width * 0.5) -> None:
            cr.line_to(x1, y1)
            cr.line_to(x2, y2)
            cr.line_to(x3, y3)

        fill_cr = cairo.Context(img_surf)
        fill_cr.set_source_rgb(1, 1, 1) # white
        draw_triangle(fill_cr, y1=0.0, y3=0.0)
        fill_cr.close_path()
        fill_cr.fill()

        stroke_cr = cairo.Context(img_surf)
        stroke_cr.set_line_width(line_width)
        stroke_cr.set_source_rgb(0, 0, 0) # black
        stroke_cr.line_to(0.0, line_width * 0.5)
        draw_triangle(stroke_cr)
        stroke_cr.line_to(img_w, line_width * 0.5)
        stroke_cr.stroke()

        bubble_h = int(_BUBBLE_HEIGHT_K * img_h)
        out_surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, img_w, img_h + bubble_h)
        cr = cairo.Context(out_surf)

        # полоса
        cr.set_source_rgb(1, 1, 1)
        cr.rectangle(0, 0, img_w, bubble_h)
        cr.fill()

        # исходное изображение ниже полосы
        cr.set_source_surface(img_surf, 0, bubble_h)
        cr.paint()

        final_surf = scale_for_tg(out_surf)
        buf = io.BytesIO()
        final_surf.write_to_png(buf)
        return buf.getvalue()

    async def handle(self, message: Message, args: list[list[str]]) -> None:
        photo = fetch_image_from_message(message)
        if not photo:
            await message.answer("нужно прикрепить пикчу")
            return

        face_num = 0
        if len(args) > 0:
            if args[0][0].isnumeric():
                face_num = int(args[0][0]) - 1
            else:
                await message.answer("напишите номер лица")
                return

        stream = await self._bot.download(photo)
        if not stream:
            await message.answer('не удалось скачать пикчу')
            return
        pic = await asyncio.get_running_loop().run_in_executor(None, stream.read)
        result = await asyncio.get_running_loop().run_in_executor(executor, self.process_image, pic, face_num)

        if isinstance(result, bytes):
            await message.answer_photo(BufferedInputFile(result, "default"),
                                        caption="ваша пикча")
        elif isinstance(result, str):
            await message.answer(result)
        else:
            logging.error(f'Unexcepted process_image() result: {result}')
            await message.answer('не удалось обработать пикчу')
