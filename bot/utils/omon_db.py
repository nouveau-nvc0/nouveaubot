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
from aiosqlitepool import SQLiteConnectionPool
from dataclasses import dataclass
from typing import Optional
import threading


@dataclass
class CodeRecord:
    id: int
    name: str
    n_sentences: int


class OmonDB:
    _instance: Optional["OmonDB"] = None
    _lock = threading.Lock()

    _pool: SQLiteConnectionPool
    _initialized: bool = False
    _pragmas: list[str] = [
        "PRAGMA foreign_keys = ON",
        "PRAGMA journal_mode = WAL",
        "PRAGMA synchronous = FULL",
        "PRAGMA cache_size = 10000",
        "PRAGMA temp_store = MEMORY",
        "PRAGMA mmap_size = 268435456"
    ]

    # ---------- singleton factory ----------
    @classmethod
    def instance(cls, db_file: str, sql_path: str) -> "OmonDB":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(db_file, sql_path)
        return cls._instance

    # ---------- ctor (sync init + pool) ----------
    def __init__(self, db_file: str, sql_path: str) -> None:
        if self._initialized:
            return  # guard against double __init__
        self._init_db_sync(db_file, sql_path)
        self._pool = self._make_pool(db_file)
        self._initialized = True

    def _init_db_sync(self, db_file: str, sql_path: str) -> None:
        with open(sql_path, "r", encoding="utf-8") as f:
            script = f.read()
        conn = sqlite3.connect(db_file)
        try:
            for pragma in self._pragmas:
                conn.execute(pragma)
            conn.executescript(script)
            conn.commit()
        finally:
            conn.close()

    def _make_pool(self, db_file: str) -> SQLiteConnectionPool:
        async def connection_factory() -> aiosqlite.Connection:
            conn = await aiosqlite.connect(db_file)
            for pragma in self._pragmas:
                await conn.execute(pragma)
            conn.row_factory = sqlite3.Row
            return conn

        return SQLiteConnectionPool(connection_factory=connection_factory)  # pyright: ignore[reportArgumentType]

    async def get_codes(self, chat_id: int) -> list[CodeRecord]:
        async with self._pool.connection() as c:
            cur = await c.execute(
                """
                SELECT codes.id, codes.code_name, COUNT(codes_sentences.id) AS sentences_count
                FROM codes
                LEFT JOIN codes_sentences ON codes.id = codes_sentences.code_id
                WHERE codes.chat_id = ?
                GROUP BY codes.id, codes.code_name
                ORDER BY codes.code_name
                """,
                (chat_id,),
            )
            rows = await cur.fetchall()
            return [CodeRecord(r["id"], r["code_name"], r["sentences_count"]) for r in rows]

    async def get_or_default_code_id(
        self, chat_id: int | None, code_name: str | None
    ) -> int:
        async with self._pool.connection() as c:
            if chat_id is not None and code_name is not None:
                cur = await c.execute(
                    "SELECT id FROM codes WHERE chat_id = ? AND code_name = ?",
                    (chat_id, code_name),
                )
                row = await cur.fetchone()
                if row:
                    return int(row["id"])

            cur = await c.execute("SELECT id FROM codes WHERE chat_id IS NULL")
            row = await cur.fetchone()
            if not row:
                raise RuntimeError("default code missing")
            return int(row["id"])

    async def load_sentences(self, code_id: int) -> dict[str, str]:
        async with self._pool.connection() as c:
            cur = await c.execute(
                "SELECT sentence_name, sentence_description FROM codes_sentences WHERE code_id = ?",
                (code_id,),
            )
            rows = await cur.fetchall()
            return {r["sentence_name"]: r["sentence_description"] for r in rows}

    async def create_code(self, chat_id: int, code_name: str) -> None:
        async with self._pool.connection() as c:
            await c.execute(
                "INSERT INTO codes(chat_id, code_name) VALUES (?, ?)",
                (chat_id, code_name),
            )
            await c.commit() # pyright: ignore[reportAttributeAccessIssue]

    async def delete_code(self, chat_id: int, code_name: str) -> int:
        async with self._pool.connection() as c:
            cur = await c.execute(
                "DELETE FROM codes WHERE chat_id = ? AND code_name = ?",
                (chat_id, code_name),
            )
            await c.commit() # pyright: ignore[reportAttributeAccessIssue]
            return cur.rowcount

    async def upsert_sentence(
        self, code_id: int, sentence_name: str, sentence_description: str
    ) -> None:
        async with self._pool.connection() as c:
            await c.execute(
                "INSERT INTO codes_sentences(code_id, sentence_name, sentence_description) "
                "VALUES (?, ?, ?) "
                "ON CONFLICT(code_id, sentence_name) DO UPDATE SET sentence_description=excluded.sentence_description",
                (code_id, sentence_name, sentence_description),
            )
            await c.commit() # pyright: ignore[reportAttributeAccessIssue]

    async def delete_sentence(self, code_id: int, sentence_name: str) -> int:
        async with self._pool.connection() as c:
            cur = await c.execute(
                "DELETE FROM codes_sentences WHERE code_id = ? AND sentence_name = ?",
                (code_id, sentence_name),
            )
            await c.commit() # pyright: ignore[reportAttributeAccessIssue]
            return cur.rowcount