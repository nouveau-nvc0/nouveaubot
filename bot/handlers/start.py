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

from aiogram import Dispatcher, Bot
from aiogram.types import Message
from aiogram.enums.parse_mode import ParseMode
from aiogram.enums import ChatType

from bot.command_filter import CommandFilter
from bot.handler import Handler

from typing import Iterable

class StartHandler(Handler):
    _start_html: str
    _bot: Bot

    @property
    def aliases(self) -> list[str]:
        return ["start", "help"]
    
    @property
    def description(self) -> str:
        return 'список команд'

    def __init__(self, dp: Dispatcher, bot: Bot, handlers: Iterable[Handler]) -> None:
        self._bot = bot
        CommandFilter.setup(self.aliases, dp, bot, self._handle)
        self._start_html = '\n\n'.join(f'<b>/{x.aliases[0]}{{bot_tag}}</b>: {x.description}' for x in handlers) + \
          ('\n\n<a href="https://github.com/nouveau-nvc0/nouveaubot/blob/main/LICENSE">AGPLv3</a>. '
          'All (far-)rights reserved. <a href="https://github.com/nouveau-nvc0/nouveaubot">Source code</a>')

    async def _handle(self, message: Message) -> None:
        me = await self._bot.me()
        await message.answer(self._start_html.format(bot_tag=f'@{me.username}' if message.chat.type != ChatType.PRIVATE else ''),
                             parse_mode=ParseMode.HTML, disable_web_page_preview=True)
