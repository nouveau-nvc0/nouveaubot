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

from typing import Dict, Tuple, Optional
from aiogram import Dispatcher, Bot, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ForceReply

from bot.command_filter import CommandFilter
from bot.handler import Handler

from bot.utils.omon_db import (
    create_code, delete_code, get_codes,
    get_code_id, upsert_sentence, delete_sentence
)

_PENDING: Dict[int, Tuple[str, int]] = {}

class ConfigOmonHandler(Handler):
    @property
    def aliases(self) -> list[str]:
        return ["config_omon", "конфиг_омон"]

    @property
    def description(self) -> str:
        return "настройка кодексов для чата"

    def __init__(self, dp: Dispatcher, bot: Bot, db_file: str) -> None:
        self._db_file = db_file
        self._bot = bot
        CommandFilter.setup(self.aliases, dp, bot, self._handle)

        # callbacks
        dp.callback_query.register(self._cb_add,  F.data == "cfg:add")
        dp.callback_query.register(self._cb_del,  F.data == "cfg:del")
        dp.callback_query.register(self._cb_adds, F.data == "cfg:adds")
        dp.callback_query.register(self._cb_dels, F.data == "cfg:dels")

        # ForceReply answers
        dp.message.register(self._on_reply_add,  F.reply_to_message.as_('rtm'),
                            F.reply_to_message.func(lambda m: m and m.text and m.text.startswith("Введите имя кодекса")))
        dp.message.register(self._on_reply_del,  F.reply_to_message.as_('rtm'),
                            F.reply_to_message.func(lambda m: m and m.text and m.text.startswith("Удалить кодекс")))
        dp.message.register(self._on_reply_adds, F.reply_to_message.as_('rtm'),
                            F.reply_to_message.func(lambda m: m and m.text and m.text.startswith("Добавить статью")))
        dp.message.register(self._on_reply_dels, F.reply_to_message.as_('rtm'),
                            F.reply_to_message.func(lambda m: m and m.text and m.text.startswith("Удалить статью")))

    # ---------- helpers ----------

    def _chat_id_from_message(self, m: Message) -> Optional[int]:
        return m.chat.id if getattr(m, "chat", None) else None

    def _chat_id_from_cq(self, cq: CallbackQuery) -> Optional[int]:
        return cq.message.chat.id if cq.message and getattr(cq.message, "chat", None) else None

    def _user_id_from_message(self, m: Message) -> Optional[int]:
        return m.from_user.id if m.from_user else None

    def _user_id_from_cq(self, cq: CallbackQuery) -> Optional[int]:
        return cq.from_user.id if getattr(cq, "from_user", None) else None

    async def _safe_answer_msg(self, m: Message, text: str, reply_markup=None) -> None:
        try:
            await m.answer(text, reply_markup=reply_markup)
        except Exception:
            uid = self._user_id_from_message(m)
            if uid is not None:
                await self._bot.send_message(uid, text, reply_markup=reply_markup)

    async def _safe_answer_cq(self, cq: CallbackQuery, text: str, reply_markup=None) -> None:
        if cq.message:
            try:
                await cq.message.answer(text, reply_markup=reply_markup)
            except Exception:
                uid = self._user_id_from_cq(cq)
                if uid is not None:
                    await self._bot.send_message(uid, text, reply_markup=reply_markup)
        else:
            uid = self._user_id_from_cq(cq)
            if uid is not None:
                await self._bot.send_message(uid, text, reply_markup=reply_markup)
        try:
            await cq.answer()
        except Exception:
            pass

    # ---------- handlers ----------

    async def _handle(self, message: Message, args: list[list[str]]) -> None:
        chat_id = self._chat_id_from_message(message)
        if chat_id is None:
            await self._safe_answer_msg(message, "Команда недоступна в этом контексте.")
            return

        names = await get_codes(self._db_file, chat_id)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Добавить кодекс",    callback_data="cfg:add")],
            [InlineKeyboardButton(text="Удалить кодекс",     callback_data="cfg:del")],
            [InlineKeyboardButton(text="Добавить статью",    callback_data="cfg:adds")],
            [InlineKeyboardButton(text="Удалить статью",     callback_data="cfg:dels")],
        ])
        txt = "Кодексы чата:\n" + ("\n".join(f"- {n}" for n in names) if names else "— нет —")
        await self._safe_answer_msg(message, txt, reply_markup=kb)

    # --- callbacks -> ForceReply prompts ---

    async def _cb_add(self, cq: CallbackQuery):
        chat_id = self._chat_id_from_cq(cq)
        uid = self._user_id_from_cq(cq)
        if chat_id is None or uid is None:
            await self._safe_answer_cq(cq, "Недоступно здесь.")
            return
        _PENDING[uid] = ("add", chat_id)
        await self._safe_answer_cq(cq, "Введите имя кодекса (только [a-z], не 'ukrf'):", reply_markup=ForceReply())

    async def _cb_del(self, cq: CallbackQuery):
        chat_id = self._chat_id_from_cq(cq)
        uid = self._user_id_from_cq(cq)
        if chat_id is None or uid is None:
            await self._safe_answer_cq(cq, "Недоступно здесь.")
            return
        _PENDING[uid] = ("del", chat_id)
        await self._safe_answer_cq(cq, "Удалить кодекс: введите имя:", reply_markup=ForceReply())

    async def _cb_adds(self, cq: CallbackQuery):
        chat_id = self._chat_id_from_cq(cq)
        uid = self._user_id_from_cq(cq)
        if chat_id is None or uid is None:
            await self._safe_answer_cq(cq, "Недоступно здесь.")
            return
        _PENDING[uid] = ("adds", chat_id)
        await self._safe_answer_cq(cq, "Добавить статью: введите строку вида\n[code] [sentence] [description...]", reply_markup=ForceReply())

    async def _cb_dels(self, cq: CallbackQuery):
        chat_id = self._chat_id_from_cq(cq)
        uid = self._user_id_from_cq(cq)
        if chat_id is None or uid is None:
            await self._safe_answer_cq(cq, "Недоступно здесь.")
            return
        _PENDING[uid] = ("dels", chat_id)
        await self._safe_answer_cq(cq, "Удалить статью: введите строку вида\n[code] [sentence]", reply_markup=ForceReply())

    # --- ForceReply answers ---

    async def _on_reply_add(self, message: Message, rtm: Message):
        uid = self._user_id_from_message(message)
        if uid is None:
            return
        act, chat_id = _PENDING.pop(uid, (None, None))
        if act != "add" or chat_id is None:
            return

        name = (message.text or "").strip()
        if not name.isalpha() or not name.islower():
            await self._safe_answer_msg(message, "имя должно быть [a-z]+")
            return
        try:
            await create_code(self._db_file, chat_id, name)  # chat_id: int
            await self._safe_answer_msg(message, f"добавлено: {name}")
        except Exception as e:
            await self._safe_answer_msg(message, f"ошибка: {e}")

    async def _on_reply_del(self, message: Message, rtm: Message):
        uid = self._user_id_from_message(message)
        if uid is None:
            return
        act, chat_id = _PENDING.pop(uid, (None, None))
        if act != "del" or chat_id is None:
            return

        name = (message.text or "").strip()
        try:
            n = delete_code(self._db_file, chat_id, name)  # chat_id: int
            await self._safe_answer_msg(message, "удалено" if n else "не найдено")
        except Exception as e:
            await self._safe_answer_msg(message, f"ошибка: {e}")

    async def _on_reply_adds(self, message: Message, rtm: Message):
        uid = self._user_id_from_message(message)
        if uid is None:
            return
        act, chat_id = _PENDING.pop(uid, (None, None))
        if act != "adds" or chat_id is None:
            return

        parts = (message.text or "").split(maxsplit=2)
        if len(parts) < 3:
            await self._safe_answer_msg(message, "нужно: [code] [sentence] [description...]")
            return
        code, sentence, desc = parts[0].strip(), parts[1].strip(), parts[2].strip()
        cid = await get_code_id(self._db_file, chat_id, code)  # chat_id: int
        if cid is None:
            await self._safe_answer_msg(message, "кодекс не найден")
            return
        try:
            await upsert_sentence(self._db_file, cid, sentence, desc)
            await self._safe_answer_msg(message, "ок")
        except Exception as e:
            await self._safe_answer_msg(message, f"ошибка: {e}")

    async def _on_reply_dels(self, message: Message, rtm: Message):
        uid = self._user_id_from_message(message)
        if uid is None:
            return
        act, chat_id = _PENDING.pop(uid, (None, None))
        if act != "dels" or chat_id is None:
            return

        parts = (message.text or "").split(maxsplit=1)
        if len(parts) < 2:
            await self._safe_answer_msg(message, "нужно: [code] [sentence]")
            return
        code, sentence = parts[0].strip(), parts[1].strip()
        cid = await get_code_id(self._db_file, chat_id, code)  # chat_id: int
        if cid is None:
            await self._safe_answer_msg(message, "кодекс не найден")
            return
        try:
            n = await delete_sentence(self._db_file, cid, sentence)
            await self._safe_answer_msg(message, "удалено" if n else "не найдено")
        except Exception as e:
            await self._safe_answer_msg(message, f"ошибка: {e}")
