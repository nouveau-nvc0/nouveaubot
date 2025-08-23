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

from aiogram import Dispatcher
from aiogram.types import Message

from bot.command_filter import CommandFilter
from bot.utils.message_data_fetchers import fetch_text_from_message
from bot.handler import Handler

import random


class CPHandler(Handler):
    @property
    def aliases(self) -> list[str]:
        return ["cp", "childporn"]
    
    @property
    def description(self) -> str:
        return 'тупой юмор'

    def __init__(self, dp: Dispatcher) -> None:
        Handler.__init__(self)
        dp.message(CommandFilter(self.aliases))(self.ping)

    async def ping(self, message: Message) -> None:
        txt = fetch_text_from_message(message)
        if txt is None:
            await message.answer("дополнительно напишите или перешлите текст")
            return

        res = " ".join("CHILD PORN" if random.randrange(100)
                       < 5 else x for x in txt.split(" "))

        await message.answer(res)
