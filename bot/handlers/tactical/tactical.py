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

import os
import cv2
import numpy as np


class TacticalHandler:
    aliases = ["боевая", "бой"]
    bot: Bot

    face_cascade: cv2.CascadeClassifier

    bubble_height = 260
    bubble_width = 2048
    bubble_dot1 = 12 / 17
    bubble_dot2 = 16 / 17

    def __init__(self, dp: Dispatcher, bot: Bot, static_path: str) -> None:
        self.bot = bot

        self.face_cascade = cv2.CascadeClassifier(
            os.path.join(static_path, "facerecognition.xml"))

        dp.message(CommandFilter(self.aliases))(self.handle)

    async def handle(self, message: Message, args: list[str]) -> any:
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

        pic = (await self.bot.download(photo)).read()

        nparr = np.frombuffer(pic, np.uint8)
        cv2img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        gray = cv2.cvtColor(cv2img, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 5)

        if len(faces) == 0:
            await message.answer("лица не обнаружены")
            return
        if len(faces) < face_num + 1:
            await message.answer("такого лица нет")
            return

        with Image(blob=pic) as source:
            source_width, source_height = source.size
            ratio = source_width / self.bubble_width
            bubble_height = self.bubble_height * ratio

            source.extent(source_width, int(
                source_height+bubble_height),
                0, int(self.bubble_height * ratio) * -1)

            with Drawing() as draw:
                draw.fill_color = Color("white")

                points = [
                    (source_width * self.bubble_dot1, bubble_height - 1),
                    (source_width * self.bubble_dot2, bubble_height - 1),
                    (faces[face_num][0] + (faces[face_num][2] * 3 / 4),
                     faces[face_num][1] + bubble_height)
                ]

                draw.polygon(points)
                draw(source)

            blob = source.make_blob("jpeg")
            await message.answer_photo(BufferedInputFile(blob, "default"),
                                       caption="ваша пикча")
