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
from aiogram.types import BotCommand

from bot.handlers.ping import PingHandler
from bot.handlers.tactical import TacticalHandler
from bot.handlers.omon import OmonHandler
from bot.handlers.cp import CPHandler
from bot.handlers.demotivator import DemotivatorHandler
from bot.handlers.start import StartHandler
from bot.handler import Handler

import re


def _find_latin(aliases: list[str]) -> str | None:
    for a in aliases:
        if a and bool(re.fullmatch(r"[A-Za-z]+", a)):
            return a

async def route(dp: Dispatcher,
                bot: Bot,
                static_path: str) -> None:
    handlers: list[Handler] = [
      OmonHandler(dp, bot, static_path),
      DemotivatorHandler(dp, bot),
      TacticalHandler(dp, bot),
      CPHandler(dp, bot),
      PingHandler(dp, bot),
    ]

    handlers.append(StartHandler(dp, bot, handlers))

    commands: list[BotCommand] = []
    
    for handler in handlers:
        name = _find_latin(handler.aliases)
        if not name:
            continue
        commands.append(BotCommand(command=name, description=handler.description))
    
    await bot.set_my_commands(commands)
