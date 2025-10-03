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
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from bot.command_filter import CommandFilter
from bot.handler import Handler


class PinHandler(Handler):
    @property
    def aliases(self) -> list[str]:
        return ["pin", "пин", "закреп"]

    @property
    def description(self) -> str:
        return "закрепить сообщение"

    def __init__(self, dp: Dispatcher, bot: Bot) -> None:
        self.bot = bot
        CommandFilter.setup(self.aliases, dp, bot, self._handle)

    async def _handle(self, message: Message) -> None:
        if not message.reply_to_message or message.reply_to_message.chat.id != message.chat.id:
            await message.reply("ответь этой командой на сообщение, которое нужно закрепить")
            return

        try:
            await self.bot.pin_chat_message(
                chat_id=message.chat.id,
                message_id=message.reply_to_message.message_id,
                disable_notification=True,
            )
        except TelegramForbiddenError:
            await message.reply("нет прав закрепить в этом чате")
        except TelegramBadRequest as e:
            s = str(e).lower()
            if "message is not modified" in s or "chat not modified" in s:
                await message.reply("уже закреплено")
            elif "message to pin not found" in s or "message_id_invalid" in s:
                await message.reply("не нашёл сообщение для закрепления")
            elif "not enough rights" in s or "chat admin required" in s:
                await message.reply("нет прав закрепить в этом чате")
            elif "message can't be pinned" in s:
                await message.reply("это сообщение нельзя закрепить")
            else:
                await message.reply(f"ошибка: {e}")
        except Exception as e:
            await message.reply(f"ошибка: {e}")
