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

import asyncio
from aiogram.types import Message
from aiogram.filters import Filter
from aiogram import Dispatcher, Bot

from typing import Any, Awaitable, Callable, Iterable
import re


class CommandFilter(Filter):
    _aliases: list[str]
    _regex_pattern: re.Pattern

    def __init__(self, bot_username: str, aliases: Iterable[str]) -> None:
        self._aliases = list(aliases)
        self._regex_pattern = re.compile(r"^/([^\s@]+)(?:@" + bot_username + r")?(?=\s|$)(?:\s+([\s\S]*))?$")

    def parse_command(self, text: str) -> tuple[None, None] | tuple[str, str]:
        mt = self._regex_pattern.match(text)
        if mt:
            cmd = mt.group(1)
            args = mt.group(2) or ""
            return cmd, args
        return None, None

    async def __call__(self, message: Message) -> bool | dict[str, list[list[str]]]:
        msg = message.text if message.text else message.caption
        if not msg:
            return False

        cmd, args = self.parse_command(msg)
        if cmd is None or cmd not in self._aliases:
            return False

        # многострочные аргументы → список строк → список слов
        args_list = [line.split() for line in args.splitlines() if line.strip()] if args is not None else []
        return {"args": args_list}

    @staticmethod
    def setup(aliases: list[str], dp: Dispatcher, bot: Bot, handler: Callable[..., Awaitable[Any]]) -> None:
        loop = asyncio.get_running_loop()
        task = loop.create_task(bot.me())

        def on_me_ready(t: asyncio.Task) -> None:
            me = t.result().username
            if me is None:
                raise RuntimeError("Cannnot fetch bot's username")
            dp.message(CommandFilter(me, aliases))(handler)

        task.add_done_callback(on_me_ready)