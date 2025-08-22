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
import json
import random
import math

FRAME_WIDTH = 6
FONT_CHARACTER_WEIGHT = 1
FRAME_TEXT_PADDING_BOTTOM = 3
FRAME_TEXT_FONT_SIZE = 16
BOTTOM_TEXT_FONT_FACTOR = 128 / 573
BOTTOM_TEXT_PADDING_TOP = 4
WORDS_PER_LINE = 5


def prepare_sentence(s: str) -> str:
    toks = s.split()
    res = []

    for i in range(math.ceil(len(toks) / WORDS_PER_LINE)):
        start = i * WORDS_PER_LINE
        end = (i + 1) * WORDS_PER_LINE

        if len(toks) >= end:
            res.append(" ".join(toks[start:end]))
        else:
            res.append(" ".join(toks[start:]))

    return "\n".join(res)


class OmonHandler:
    aliases = ["омон"]
    bot: Bot

    face_cascade: cv2.CascadeClassifier
    sentences: list[tuple[str, str]]

    font_path: str

    def __init__(self, dp: Dispatcher, bot: Bot, static_path: str) -> None:
        self.bot = bot

        self.font_path = os.path.join(
            static_path, "LiberationSans-Regular.ttf")
        self.face_cascade = cv2.CascadeClassifier(
            os.path.join(static_path, "facerecognition.xml"))

        with open(os.path.join(static_path, "sentences.txt"), "r") as f:
            self.sentences = [(k, prepare_sentence(v))
                              for k, v in json.loads(f.read()).items()]

        dp.message(CommandFilter(self.aliases))(self.handle)

    async def handle(self, message: Message, args: list[str]) -> any:
        photo = fetch_image_from_message(message)
        if not photo:
            await message.answer("нужно прикрепить пикчу")
            return

        print(photo.width, photo.height)

        pic = (await self.bot.download(photo)).read()

        nparr = np.frombuffer(pic, np.uint8)
        cv2img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        gray = cv2.cvtColor(cv2img, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 5)

        if len(faces) == 0:
            await message.answer("лица не обнаружены")
            return

        chosen_sentences = random.sample(self.sentences, len(faces))

        with Image(blob=pic) as source:
            with Drawing() as draw:
                for i, (x, y, w, h) in enumerate(faces):
                    txt = "Статья " + chosen_sentences[i][0]

                    draw.stroke_width = FRAME_WIDTH
                    draw.stroke_color = Color("green")
                    draw.fill_color = Color("black")
                    draw.font = self.font_path
                    draw.fill_opacity = 0x00
                    draw.font_size = FRAME_TEXT_FONT_SIZE

                    points = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
                    draw.polygon(points)

                    metrics = draw.get_font_metrics(source, txt)

                    draw.stroke_color = Color("black")
                    draw.fill_opacity = 0xFF

                    points = [(x, y - FRAME_WIDTH),
                              (x + metrics.text_width, y - FRAME_WIDTH),
                              (x + metrics.text_width, y -
                               metrics.text_height - FRAME_WIDTH),
                              (x, y - metrics.text_height - FRAME_WIDTH)]
                    draw.polygon(points)

                    draw.stroke_color = Color("green")
                    draw.fill_color = Color("green")
                    draw.stroke_width = FONT_CHARACTER_WEIGHT
                    draw.text(int(x), int(
                        y - FRAME_WIDTH - FRAME_TEXT_PADDING_BOTTOM), txt)

                draw(source)

            with Drawing() as draw:
                draw.font = self.font_path
                draw.font_size = int(BOTTOM_TEXT_FONT_FACTOR * source.width)
                draw.stroke_color = Color("green")
                draw.fill_color = Color("green")

                txt = "\n".join("Статья {}. {}".format(x, y)
                                for (x, y) in chosen_sentences)
                metrics = draw.get_font_metrics(source, txt, multiline=True)
                with Image(width=int(metrics.text_width + BOTTOM_TEXT_PADDING_TOP),
                           height=int(metrics.text_height),
                           background=Color("black")) as appendix:
                    draw.text(0, int(metrics.y2 + BOTTOM_TEXT_PADDING_TOP), txt)
                    draw(appendix)

                    appendix.resize(source.width,
                                    int(metrics.text_height *
                                        (source.width / metrics.text_width)))
                    source.extent(source.width,
                                  source.height + appendix.height)
                    source.composite(
                        appendix, 0, source.height - appendix.height)

            blob = source.make_blob("jpeg")
            await message.answer_photo(BufferedInputFile(blob, "default"),
                                       caption="ваша пикча")
