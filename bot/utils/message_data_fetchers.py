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

from aiogram.types import Message, PhotoSize


def _photo_from_msg(m: Message) -> PhotoSize | None:
    IMAGE_MIME_PREFIXES = ("image/",)
    IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".gif")

    # 1) Native photos
    if m.photo:
        return m.photo[-1]

    # 2) Animations/GIFs (as animation or as document)
    if m.animation and m.animation.thumbnail:
        return m.animation.thumbnail

    if m.document:
        mt = (m.document.mime_type or "").lower()
        fn = (m.document.file_name or "").lower()
        if (
            m.document.thumbnail
            and (mt.startswith(IMAGE_MIME_PREFIXES) or fn.endswith(IMAGE_EXTS))
        ):
            return m.document.thumbnail

    # 3) Stickers (static/animated/video) — use thumbnail if present
    if m.sticker and m.sticker.thumbnail:
        return m.sticker.thumbnail

    # 4) Videos with a poster (sometimes people send short GIF-like videos)
    if m.video and m.video.thumbnail:
        return m.video.thumbnail

    # 5) Video notes / voice notes with preview (rarely useful, but harmless)
    if m.video_note and m.video_note.thumbnail:
        return m.video_note.thumbnail

    return None


def fetch_image_from_message(msg: Message) -> PhotoSize | None:
    r = _photo_from_msg(msg)
    if r:
        return r
    if msg.reply_to_message:
        return _photo_from_msg(msg.reply_to_message)
    return None


def fetch_text_from_message(msg: Message) -> None | str:
    if msg.text is None:
        return None
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
