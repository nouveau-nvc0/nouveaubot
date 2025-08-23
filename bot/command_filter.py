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

from aiogram.types import Message
from aiogram.filters import Filter
import re

PATTERN = re.compile(
    r"^/([^\s@]+)(?:@ed25519bot)?(?=\s|$)(?:\s+([\s\S]*))?$"
)

def parse_command(text: str) -> tuple[None, None] | tuple[str, str]:
    mt = PATTERN.match(text)
    if mt:
        cmd = mt.group(1)
        args = mt.group(2)
        if not args:
            args = ""
        return cmd, args
    return None, None

class CommandFilter(Filter):
    aliases: list[str]

    def __init__(self, aliases: list[str]) -> None:
        self.aliases = aliases

    async def __call__(self, message: Message) -> bool | dict[str, any]:
        msg = message.text if message.text else message.caption
        if not msg or msg == "":
            return False
        cmd, args = parse_command(msg)
        if cmd is None or cmd not in self.aliases:
            return False

        # Разделяем аргументы на строки и слова
        args_list = [line.split() for line in args.splitlines() if line.strip()]
        return {"args": args_list}
