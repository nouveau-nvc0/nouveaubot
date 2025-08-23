# Copyright (C) 2024 basilbot contributors

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
from wand.image import Image
from wand.drawing import Drawing
from wand.color import Color

from bot.command_filter import CommandFilter
from bot.utils.message_data_fetchers import fetch_image_from_message
from bot.utils.detect_faces import detect_faces
from bot.utils.pool_executor import executor

import asyncio
from typing import Any

_BUBBLE_HEIGHT = 260
_BUBBLE_WIDTH = 2048
_BUBBLE_DOT1 = 12 / 17
_BUBBLE_DOT2 = 16 / 17


class TacticalHandler:
    aliases = ["боевая", "бой", "tactical", "tact"]
    _bot: Bot

    def __init__(self, dp: Dispatcher, bot: Bot, static_path: str) -> None:
        self._bot = bot

        dp.message(CommandFilter(self.aliases))(self.handle)

    @staticmethod
    def process_image(img_data: bytes, face_num: int) -> bytes | str:
        faces = detect_faces(img_data)

        if len(faces) == 0:
            return "лица не обнаружены"
        if len(faces) < face_num + 1:
            return "такого лица нет"

        with Image(blob=img_data) as source:
            source_width, source_height = source.size
            ratio = source_width / _BUBBLE_WIDTH
            bubble_height = _BUBBLE_HEIGHT * ratio

            source.extent(source_width, int(
                source_height+bubble_height),
                0, int(_BUBBLE_HEIGHT * ratio) * -1)

            with Drawing() as draw:
                draw.fill_color = Color("white")
                face_width = faces[face_num].x2 - faces[face_num].x1
                points = [
                    (source_width * _BUBBLE_DOT1, bubble_height - 1),
                    (source_width * _BUBBLE_DOT2, bubble_height - 1),
                    (faces[face_num].x1 + face_width * 0.5,
                     faces[face_num].y1 + bubble_height)
                ]

                draw.polygon(points)
                draw(source)

            return source.make_blob("jpeg")

    async def handle(self, message: Message, args: list[str]) -> Any:
        photo = fetch_image_from_message(message)
        if not photo:
            await message.answer("нужно прикрепить пикчу")
            return

        face_num = 0
        if len(args) > 0:
            if args[0].isnumeric():
                face_num = int(args[0]) - 1
            else:
                await message.answer("напишите номер лица")
                return

        pic = await asyncio.get_running_loop().run_in_executor(None, (await self._bot.download(photo)).read)
        result = await asyncio.get_running_loop().run_in_executor(executor, self.process_image, pic, face_num)

        if isinstance(result, bytes):
            await message.answer_photo(BufferedInputFile(result, "default"),
                                        caption="ваша пикча")
        else:
            await message.answer(result)
