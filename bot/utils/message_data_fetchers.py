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

from aiogram.types import Message, PhotoSize


def fetch_image_from_message(msg: Message) -> None | PhotoSize:
    if not msg.photo:
        if not msg.reply_to_message:
            return None
        if not msg.reply_to_message.photo:
            return None
        return msg.reply_to_message.photo[-1]
    return msg.photo[-1]


def fetch_text_from_message(msg: Message) -> None | str:
    without_cmd = " ".join(msg.text.split()[1:])
    if not without_cmd:
        if not msg.caption:
            if not msg.reply_to_message:
                return None
            if not msg.reply_to_message.text:
                if not msg.reply_to_message.caption:
                    return None
                return msg.reply_to_message.caption
            return msg.reply_to_message.text
        return msg.caption
    return without_cmd
