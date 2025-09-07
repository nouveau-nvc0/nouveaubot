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

import os
from aiogram import Dispatcher, Bot
from aiogram.types import Message
from aiogram.enums.parse_mode import ParseMode

from bot.command_filter import CommandFilter
from bot.handler import Handler

from bot.utils.omon_db import (
    CodeRecord, OmonDB
)

class ConfigOmonHandler(Handler):
    _ADD_USAGE = 'добавить кодекс: <b>/config_omon add <i>[имя кодекса]</i></b>'
    _DEL_USAGE = 'удалить кодекс: <b>/config_omon del <i>[имя кодекса]</i></b>'
    _ADDS_USAGE = 'добавить статью: <b>/config_omon adds <i>[имя кодекса] [название статьи] [описание статьи...]</i></b>'
    _DELS_USAGE = 'удалить статью: <b>/config_omon dels <i>[имя кодекса] [название статьи]</i></b>'

    _db: OmonDB
    _bot: Bot

    @property
    def aliases(self) -> list[str]:
        return ["config_omon", "конфиг_омон"]

    @property
    def description(self) -> str:
        return "настройка кодексов для чата"

    def __init__(self, dp: Dispatcher, bot: Bot, static_path: str, db_file: str) -> None:
        self._bot = bot
        self._db = OmonDB.instance(db_file, os.path.join(static_path, 'omon.sql'))
        CommandFilter.setup(self.aliases, dp, bot, self._handle)

    @staticmethod
    def _chat_id_from_message(m: Message) -> int | None:
        return m.chat.id if getattr(m, "chat", None) else None

    async def _handle(self, message: Message, args: list[list[str]]) -> None:
        chat_id = self._chat_id_from_message(message)
        if chat_id is None:
            await message.answer("команда недоступна здесь")
            return
        
        codes = await self._db.get_codes(chat_id)

        usage = f"""кодексы в чате:
{("\n".join(f"• {code.name} ({code.n_sentences})" for code in codes) if codes else "— нет —")}

{self._ADD_USAGE}

{self._ADDS_USAGE}

{self._DEL_USAGE}

{self._DELS_USAGE}"""

        if not args or not args[0]:
            await message.answer(usage, parse_mode=ParseMode.HTML)
            return
        
        match args[0][0]:
            case 'add':
                await self._on_add(chat_id, message, args[0])
            case 'del':
                await self._on_del(chat_id, message, args[0])
            case 'adds':
                await self._on_adds(message, args[0], codes)
            case 'dels':
                await self._on_dels(message, args[0], codes)
            case _:
                await message.answer(usage, parse_mode=ParseMode.HTML)
            

    async def _on_add(self, chat_id: int, message: Message, args: list[str]) -> None:
        if len(args) != 2:
            await message.answer(self._ADD_USAGE, parse_mode=ParseMode.HTML)
            return
        
        try:
            await self._db.create_code(chat_id, args[1])
            await message.answer(f"добавлено: {args[1]}")
        except Exception as e:
            await message.answer(f"ошибка: {e}")

    async def _on_del(self, chat_id: int, message: Message, args: list[str]):
        if len(args) != 2:
            await message.answer(self._DEL_USAGE, parse_mode=ParseMode.HTML)
            return

        try:
            n = await self._db.delete_code(chat_id, args[1])
            await message.answer("удалено" if n else "не найдено")
        except Exception as e:
            await message.answer(f"ошибка: {e}")

    async def _on_adds(self, message: Message, args: list[str], codes: list[CodeRecord]):
        if len(args) < 4:
            await message.answer(self._ADDS_USAGE, parse_mode=ParseMode.HTML)
            return

        code, sentence, desc = args[1].strip(), args[2].strip(), ' '.join(args[3:])
        cid = next((x.id for x in codes if x.name == code), None)
        if cid is None:
            await message.answer("кодекс не найден")
            return
        try:
            await self._db.upsert_sentence(cid, sentence, desc)
            await message.answer("ок")
        except Exception as e:
            await message.answer(f"ошибка: {e}")

    async def _on_dels(self, message: Message, args: list[str], codes: list[CodeRecord]):
        if len(args) != 3:
            await message.answer(self._DELS_USAGE, parse_mode=ParseMode.HTML)
            return

        code, sentence = args[1].strip(), args[2].strip()
        cid = next((x.id for x in codes if x.name == code), None)
        if cid is None:
            await message.answer("кодекс не найден")
            return
        try:
            n = await self._db.delete_sentence(cid, sentence)
            await message.answer("удалено" if n else "не найдено")
        except Exception as e:
            await message.answer(f"ошибка: {e}")
