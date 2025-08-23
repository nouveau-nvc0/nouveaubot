# Copyright (C) 2025 basilbot contributors

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

import os
import json
import random
import math
from typing import Any
import asyncio

_FRAME_WIDTH = 6
_FONT_CHARACTER_WEIGHT = 1
_FRAME_TEXT_PADDING_BOTTOM = 3
_FRAME_TEXT_FONT_SIZE = 16
_BOTTOM_TEXT_FONT_FACTOR = 128 / 573
_BOTTOM_TEXT_PADDING_TOP = 4
_WORDS_PER_LINE = 5

class OmonHandler:
    aliases = ["омон", "omon"]
    _bot: Bot

    _sentences: list[tuple[str, str]]
    _font_path: str

    def __init__(self, dp: Dispatcher, bot: Bot, static_path: str) -> None:
        self._bot = bot

        self._font_path = os.path.join(static_path, "LiberationSans-Regular.ttf")

        with open(os.path.join(static_path, "sentences.txt"), "r") as f:
            self._sentences = [(k, self._prepare_sentence(v))
                              for k, v in json.loads(f.read()).items()]

        dp.message(CommandFilter(self.aliases))(self.handle)

    @staticmethod
    def _prepare_sentence(s: str) -> str:
        toks = s.split()
        res = []

        for i in range(math.ceil(len(toks) / _WORDS_PER_LINE)):
            start = i * _WORDS_PER_LINE
            end = (i + 1) * _WORDS_PER_LINE

            if len(toks) >= end:
                res.append(" ".join(toks[start:end]))
            else:
                res.append(" ".join(toks[start:]))

        return "\n".join(res)

    @staticmethod
    def process_image(img_data: bytes, font_path: str, sentences: list[tuple[str, str]]) -> str | bytes:
        faces = detect_faces(img_data)

        if len(faces) == 0:
            return "лица не обнаружены"
        chosen_sentences = random.sample(sentences, len(faces))

        with Image(blob=img_data) as source:
            source.transform(resize="3072x3072>")
            source.transform(resize="512x512<")

            with Drawing() as draw:
                for i, f in enumerate(faces):
                    txt = "Статья " + chosen_sentences[i][0]

                    draw.stroke_width = _FRAME_WIDTH
                    draw.stroke_color = Color("green")
                    draw.fill_color = Color("black")
                    draw.font = font_path
                    draw.fill_opacity = 0x00
                    draw.font_size = _FRAME_TEXT_FONT_SIZE

                    # рамка вокруг лица
                    points = [(f.x1, f.y1), (f.x2, f.y1), (f.x2, f.y2), (f.x1, f.y2)]
                    draw.polygon(points)

                    metrics = draw.get_font_metrics(source, txt)

                    draw.stroke_color = Color("black")
                    draw.fill_opacity = 0xFF

                    # фон под текстом сверху
                    top_y = max(f.y1 - metrics.text_height - _FRAME_WIDTH, 0)
                    base_y = max(f.y1 - _FRAME_WIDTH, 0)
                    points = [
                        (f.x1, base_y),
                        (f.x1 + metrics.text_width, base_y),
                        (f.x1 + metrics.text_width, top_y),
                        (f.x1, top_y)
                    ]
                    draw.polygon(points)

                    # сам текст
                    draw.stroke_color = Color("green")
                    draw.fill_color = Color("green")
                    draw.stroke_width = _FONT_CHARACTER_WEIGHT
                    text_y = max(f.y1 - _FRAME_WIDTH - _FRAME_TEXT_PADDING_BOTTOM, 0)
                    text_x = max(int(f.x1), 0)
                    draw.text(text_x, text_y, txt)

                draw(source)

            # нижняя подпись с перечислением статей
            with Drawing() as draw:
                draw.font = font_path
                draw.font_size = int(_BOTTOM_TEXT_FONT_FACTOR * source.width)
                draw.stroke_color = Color("green")
                draw.fill_color = Color("green")

                txt = "\n".join("Статья {}. {}".format(x, y)
                                for (x, y) in chosen_sentences)
                metrics = draw.get_font_metrics(source, txt, multiline=True)

                with Image(width=int(metrics.text_width + _BOTTOM_TEXT_PADDING_TOP),
                           height=int(metrics.text_height),
                           background=Color("black")) as appendix:
                    draw.text(0, int(metrics.y2 + _BOTTOM_TEXT_PADDING_TOP), txt)
                    draw(appendix)

                    appendix.resize(source.width,
                                    int(metrics.text_height *
                                        (source.width / metrics.text_width)))
                    source.extent(source.width,
                                  source.height + appendix.height)
                    source.composite(
                        appendix, 0, source.height - appendix.height)

            return source.make_blob("jpeg")

    async def handle(self, message: Message) -> Any:
        photo = fetch_image_from_message(message)
        if not photo:
            await message.answer("нужно прикрепить пикчу")
            return

        pic = await asyncio.get_running_loop().run_in_executor(None, (await self._bot.download(photo)).read)
        result = await asyncio.get_running_loop().run_in_executor(executor, self.process_image, pic, self._font_path, self._sentences)

        if isinstance(result, bytes):
            await message.answer_photo(
                    BufferedInputFile(result, "default"),
                    caption="ваша пикча"
                )
        else:
            await message.answer(result)
