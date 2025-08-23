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

from bot.handlers.ping import PingHandler
from bot.handlers.tactical.tactical import TacticalHandler
from bot.handlers.omon import OmonHandler
from bot.handlers.cp import CPHandler
from bot.handlers.demotivator import DemotivatorHandler


def route(dp: Dispatcher = None,
          bot: Bot = None,
          static_path: str = "") -> None:
    PingHandler(dp)
    CPHandler(dp)
    TacticalHandler(dp, bot, static_path)
    OmonHandler(dp, bot, static_path)
    DemotivatorHandler(dp, bot)
