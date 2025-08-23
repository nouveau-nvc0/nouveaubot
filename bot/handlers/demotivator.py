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

import logging
import re
from math import floor, ceil
import asyncio

from wand.color import Color
from wand.drawing import Drawing
from wand.font import Font
from wand.image import Image

from aiogram import Dispatcher, Bot
from aiogram.types import Message, BufferedInputFile

from bot.command_filter import CommandFilter
from bot.utils.message_data_fetchers import fetch_image_from_message
from bot.utils.pool_executor import executor
from bot.handler import Handler

class _Demotivator:
    _BIG_FONT_SIZE = 0.052
    _SM_FONT_SIZE = 0.036

    @staticmethod
    def _dem_text(img: Image, txt: str, font_k: float, font: str) -> Image:
        dem = Image(width=floor(img.width * 1.1), height=1000)
        dem.options['gravity'] = 'center'
        dem.options['pango:wrap'] = 'word-char'
        dem.options['trim:edges'] = 'south'
        dem.font = Font(font)
        dem.font_size = floor(font_k * dem.width)
        dem.font_color = '#ffffff'
        dem.background_color = Color('black')
        dem.pseudo(dem.width, dem.height, pseudo=f'pango:{txt}')
        dem.trim(color=Color('black'))
        return dem

    @staticmethod
    def create(img_data: bytes, _text1: str, _text2: list[str]) -> bytes | str:
        text1 = re.sub(r'[<>]', '', _text1)
        text2 = re.sub(r'[<>]', '', r'\n'.join(_text2))
        draw = Drawing()
        draw.stroke_color = Color('white')
        img = Image(blob=img_data)
        img.transform(resize='1500x1500>')
        img.transform(resize='300x300<')

        dem1 = _Demotivator._dem_text(img, text1, _Demotivator._BIG_FONT_SIZE, 'serif')
        dem2 = _Demotivator._dem_text(img, text2, _Demotivator._SM_FONT_SIZE, 'sans')

        output = Image(width=dem1.width,
                       height=dem1.height + dem2.height + img.height + floor(0.12 * img.width),
                       background=Color('black'))
        img_left = floor(0.05 * img.width)
        img_top = floor(0.05 * img.width)
        draw.stroke_width = ceil(img.width / 500)
        k = draw.stroke_width * 4
        draw.polygon([(img_left - k, img_top - k),
                      (img_left + img.width + k, img_top - k),
                      (img_left + img.width + k, img_top + img.height + k),
                      (img_left - k, img_top + img.height + k)])  # Square polygon around image
        draw(output)
        output.composite(image=img, left=img_left, top=img_top)
        img_height = floor(0.07 * img.width + img.height)
        output.composite(image=dem1, left=0, top=img_height)
        output.composite(image=dem2, left=0, top=img_height + dem1.height)
        
        result = output.make_blob("jpeg")
        if not isinstance(result, bytes):
            logging.error(f'Unexcepted make_blob() result: {result}')
            return 'не удалось обработать пикчу'
        return result


class DemotivatorHandler(Handler):
    _bot: Bot

    @property
    def aliases(self) -> list[str]:
        return ["dem", "дем"]
    
    @property
    def description(self) -> str:
        return 'сгенерировать демотиватор. разделитель - перенос строки'
    
    def __init__(self, dp: Dispatcher, bot: Bot) -> None:
        self._bot = bot
        dp.message(CommandFilter(self.aliases))(self.handle)

    async def handle(self, message: Message) -> None:
        if not message.text:
            return
        command_regex = re.compile(r'^/([\w\u0400-\u04FF]+)(?:\s+([\s\S]+))?')
        matched = command_regex.match(message.text)
        if matched is None:
            return
        args = (matched.group(2) or "").splitlines()

        photo = fetch_image_from_message(message)
        if not photo:
            await message.answer("нужно прикрепить пикчу")
            return

        stream = await self._bot.download(photo)
        if not stream:
            await message.answer('не удалось скачать пикчу')
            return
        pic = await asyncio.get_running_loop().run_in_executor(None, stream.read)
        result = await asyncio.get_running_loop().run_in_executor(executor, _Demotivator.create, pic, args[0], args[1:])
        
        if isinstance(result, bytes):
            await message.answer_photo(
                    BufferedInputFile(result, "default"),
                    caption="ваша пикча"
                )
        elif isinstance(result, str):
            await message.answer(result)
        else:
            logging.error(f'Unexcepted _Demotivator.create() result: {result}')
            await message.answer('не удалось обработать пикчу')