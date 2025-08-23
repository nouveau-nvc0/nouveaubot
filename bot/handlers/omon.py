from aiogram import Dispatcher, Bot
from aiogram.types import Message, BufferedInputFile
from wand.image import Image
from wand.drawing import Drawing
from wand.color import Color

from bot.command_filter import CommandFilter
from bot.utils.message_data_fetchers import fetch_image_from_message
from bot.utils.detect_faces import detect_faces

import os
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

    sentences: list[tuple[str, str]]
    font_path: str

    def __init__(self, dp: Dispatcher, bot: Bot, static_path: str) -> None:
        self.bot = bot

        self.font_path = os.path.join(static_path, "LiberationSans-Regular.ttf")

        with open(os.path.join(static_path, "sentences.txt"), "r") as f:
            self.sentences = [(k, prepare_sentence(v))
                              for k, v in json.loads(f.read()).items()]

        dp.message(CommandFilter(self.aliases))(self.handle)

    async def handle(self, message: Message, args: list[str]) -> any:
        photo = fetch_image_from_message(message)
        if not photo:
            await message.answer("нужно прикрепить пикчу")
            return

        pic = (await self.bot.download(photo)).read()
        faces = detect_faces(pic)

        if len(faces) == 0:
            await message.answer("лица не обнаружены")
            return

        chosen_sentences = random.sample(self.sentences, len(faces))

        with Image(blob=pic) as source:
            source.transform(resize="3072x3072>")
            source.transform(resize="512x512<")

            with Drawing() as draw:
                for i, f in enumerate(faces):
                    w, h = f.x2 - f.x1, f.y2 - f.y1
                    txt = "Статья " + chosen_sentences[i][0]

                    draw.stroke_width = FRAME_WIDTH
                    draw.stroke_color = Color("green")
                    draw.fill_color = Color("black")
                    draw.font = self.font_path
                    draw.fill_opacity = 0x00
                    draw.font_size = FRAME_TEXT_FONT_SIZE

                    # рамка вокруг лица
                    points = [(f.x1, f.y1), (f.x2, f.y1), (f.x2, f.y2), (f.x1, f.y2)]
                    draw.polygon(points)

                    metrics = draw.get_font_metrics(source, txt)

                    draw.stroke_color = Color("black")
                    draw.fill_opacity = 0xFF

                    # фон под текстом сверху
                    top_y = max(f.y1 - metrics.text_height - FRAME_WIDTH, 0)
                    base_y = max(f.y1 - FRAME_WIDTH, 0)
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
                    draw.stroke_width = FONT_CHARACTER_WEIGHT
                    text_y = max(f.y1 - FRAME_WIDTH - FRAME_TEXT_PADDING_BOTTOM, 0)
                    draw.text(int(f.x1), text_y, txt)

                draw(source)

            # нижняя подпись с перечислением статей
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
            await message.answer_photo(
                BufferedInputFile(blob, "default"),
                caption="ваша пикча"
            )
