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

from os import environ
from aiogram import Bot, Dispatcher

from bot.route import route

import asyncio


async def main(token: str, static_path: str) -> None:
    bot = Bot(token)

    dp = Dispatcher()
    await route(dp=dp, bot=bot, static_path=static_path)

    await dp.start_polling(bot)

if __name__ == "__main__":
    token = environ["BOT_TOKEN"]
    static_path = environ["BOT_STATIC_PATH"]

    asyncio.run(main(token, static_path))
