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

from aiogram import Dispatcher
from aiogram.types import Message
from aiogram import Bot

from bot.command_filter import CommandFilter
from bot.handler import Handler

class PingHandler(Handler):
    @property
    def aliases(self) -> list[str]:
        return ["ping", "пинг"]
    
    @property
    def description(self) -> str:
        return 'проверить работоспособность бота'

    def __init__(self, dp: Dispatcher, bot: Bot) -> None:
        CommandFilter.setup(self.aliases, dp, bot, self.handle)

    async def handle(self, message: Message) -> None:
        await message.answer("понг")
