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

import sqlite3
import aiosqlite
from typing import Optional, List, Dict

MAX_CODES_PER_CHAT = 10
MAX_SENTENCES_PER_CODE = 500
RESERVED_DEFAULT_CODE = 'ukrf'

def _conn(db_file: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_file)
    conn.execute('PRAGMA foreign_keys = ON')
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_file: str, sql_path: str) -> None:
    """Выполняется один раз при старте: можно вызывать из __init__ хендлера."""
    with open(sql_path, 'r', encoding='utf-8') as f:
        script = f.read()
    with _conn(db_file) as c:
        c.executescript(script)


async def get_codes(db_file: str, chat_id: int) -> List[str]:
    async with aiosqlite.connect(db_file) as c:
        await c.execute('PRAGMA foreign_keys = ON')
        c.row_factory = sqlite3.Row
        cur = await c.execute(
            'SELECT code_name FROM codes WHERE chat_id = ? ORDER BY code_name',
            (chat_id,)
        )
        rows = await cur.fetchall()
        return [r['code_name'] for r in rows]

async def get_or_default_code_id(db_file: str, chat_id: Optional[int], code_name: Optional[str]) -> int:
    """Если code_name не задан — вернуть id глобального ukrf (chat_id IS NULL)."""
    if not code_name:
        chat_id = None
        code_name = RESERVED_DEFAULT_CODE
    async with aiosqlite.connect(db_file) as c:
        await c.execute('PRAGMA foreign_keys = ON')
        c.row_factory = sqlite3.Row

        cur = await c.execute(
            'SELECT id FROM codes WHERE chat_id IS ? AND code_name = ?',
            (chat_id, code_name)
        )
        row = await cur.fetchone()
        if row:
            return int(row['id'])

        cur = await c.execute(
            'SELECT id FROM codes WHERE chat_id IS NULL AND code_name = ?',
            (RESERVED_DEFAULT_CODE,)
        )
        row = await cur.fetchone()
        if not row:
            raise RuntimeError('default code ukrf missing')
        return int(row['id'])

async def load_sentences(db_file: str, code_id: int) -> Dict[str, str]:
    async with aiosqlite.connect(db_file) as c:
        await c.execute('PRAGMA foreign_keys = ON')
        c.row_factory = sqlite3.Row
        cur = await c.execute(
            'SELECT sentence_name, sentence_description FROM codes_sentences WHERE code_id = ?',
            (code_id,)
        )
        rows = await cur.fetchall()
        return {r['sentence_name']: r['sentence_description'] for r in rows}

async def create_code(db_file: str, chat_id: int, code_name: str) -> None:
    if code_name == RESERVED_DEFAULT_CODE:
        raise ValueError('code_name ukrf is reserved')
    async with aiosqlite.connect(db_file) as c:
        await c.execute('PRAGMA foreign_keys = ON')
        await c.execute(
            'INSERT INTO codes(chat_id, code_name) VALUES (?, ?)',
            (chat_id, code_name)
        )
        await c.commit()

async def delete_code(db_file: str, chat_id: int, code_name: str) -> int:
    async with aiosqlite.connect(db_file) as c:
        await c.execute('PRAGMA foreign_keys = ON')
        cur = await c.execute(
            'DELETE FROM codes WHERE chat_id = ? AND code_name = ?',
            (chat_id, code_name)
        )
        await c.commit()
        return cur.rowcount

async def get_code_id(db_file: str, chat_id: int, code_name: str) -> Optional[int]:
    async with aiosqlite.connect(db_file) as c:
        await c.execute('PRAGMA foreign_keys = ON')
        c.row_factory = sqlite3.Row
        cur = await c.execute(
            'SELECT id FROM codes WHERE chat_id = ? AND code_name = ?',
            (chat_id, code_name)
        )
        row = await cur.fetchone()
        return int(row['id']) if row else None

async def upsert_sentence(db_file: str, code_id: int, sentence_name: str, sentence_description: str) -> None:
    async with aiosqlite.connect(db_file) as c:
        await c.execute('PRAGMA foreign_keys = ON')
        await c.execute(
            'INSERT INTO codes_sentences(code_id, sentence_name, sentence_description) VALUES (?, ?, ?) '
            'ON CONFLICT(code_id, sentence_name) DO UPDATE SET sentence_description=excluded.sentence_description',
            (code_id, sentence_name, sentence_description)
        )
        await c.commit()

async def delete_sentence(db_file: str, code_id: int, sentence_name: str) -> int:
    async with aiosqlite.connect(db_file) as c:
        await c.execute('PRAGMA foreign_keys = ON')
        cur = await c.execute(
            'DELETE FROM codes_sentences WHERE code_id = ? AND sentence_name = ?',
            (code_id, sentence_name)
        )
        await c.commit()
        return cur.rowcount
