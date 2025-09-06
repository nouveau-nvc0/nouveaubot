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

from aiogram import Dispatcher, Bot
from aiogram.types import Message

from bot.command_filter import CommandFilter
from bot.utils.message_data_fetchers import fetch_text_from_message
from bot.handler import Handler

import random
import re

PROBABILITY_PERCENT = 5


class CPHandler(Handler):
    @property
    def aliases(self) -> list[str]:
        return ["cp", "childporn"]

    @property
    def description(self) -> str:
        return "тупой юмор"

    def __init__(self, dp: Dispatcher, bot: Bot) -> None:
        CommandFilter.setup(self.aliases, dp, bot, self._handle)

    async def _handle(self, message: Message) -> None:
        txt = fetch_text_from_message(message)
        if txt is None:
            await message.answer("дополнительно напишите или перешлите текст")
            return

        matches = list(re.finditer(r"[^\s]+", txt))
        if not matches:
            await message.answer(txt)
            return

        selected = [random.randrange(100) < PROBABILITY_PERCENT for _ in range(len(matches))]
        if not any(selected):
            selected[random.randint(0, len(matches) - 1)] = True

        result = []
        last = 0
        for i, m in enumerate(matches):
            start, end = m.span()
            result.append(txt[last:start])
            if selected[i]:
                result.append("CHILD PORN")
            else:
                result.append(m.group())
            last = end
        result.append(txt[last:])

        await message.answer("".join(result))

