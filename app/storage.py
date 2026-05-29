import asyncio
import sqlite3
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class StoredMessage:
    id: int
    user_id: int
    chat_id: int
    message_thread_id: Optional[int]
    telegram_message_id: Optional[int]
    role: str
    text: str
    reply_to_telegram_message_id: Optional[int]
    parent_id: Optional[int]
    duration_ms: Optional[int]
    created_at: int


class Storage:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chats (
                    chat_id INTEGER PRIMARY KEY,
                    created_at INTEGER NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    language TEXT,
                    verified INTEGER NOT NULL DEFAULT 0,
                    show_duration INTEGER NOT NULL DEFAULT 1,
                    response_mode TEXT NOT NULL DEFAULT 'normal',
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                )
                """
            )
            user_cols = {str(r["name"]) for r in conn.execute("PRAGMA table_info(users)").fetchall()}
            if "show_duration" not in user_cols:
                conn.execute("ALTER TABLE users ADD COLUMN show_duration INTEGER NOT NULL DEFAULT 1")
            if "response_mode" not in user_cols:
                conn.execute("ALTER TABLE users ADD COLUMN response_mode TEXT NOT NULL DEFAULT 'normal'")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL,
                    message_thread_id INTEGER,
                    telegram_message_id INTEGER,
                    role TEXT NOT NULL,
                    text TEXT NOT NULL,
                    reply_to_telegram_message_id INTEGER,
                    parent_id INTEGER,
                    duration_ms INTEGER,
                    created_at INTEGER NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(user_id)
                )
                """
            )
            cols = {str(r["name"]) for r in conn.execute("PRAGMA table_info(messages)").fetchall()}
            if "message_thread_id" not in cols:
                conn.execute("ALTER TABLE messages ADD COLUMN message_thread_id INTEGER")
            if "telegram_message_id" not in cols:
                conn.execute("ALTER TABLE messages ADD COLUMN telegram_message_id INTEGER")
            if "reply_to_telegram_message_id" not in cols:
                conn.execute("ALTER TABLE messages ADD COLUMN reply_to_telegram_message_id INTEGER")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_chat_telegram_id ON messages(chat_id, telegram_message_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_user_chat_thread ON messages(user_id, chat_id, message_thread_id, id)")

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS thread_settings (
                    user_id INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL,
                    thread_id INTEGER NOT NULL,
                    show_duration INTEGER NOT NULL DEFAULT 1,
                    response_mode TEXT NOT NULL DEFAULT 'normal',
                    private_mode INTEGER NOT NULL DEFAULT 0,
                    asked_private_mode INTEGER NOT NULL DEFAULT 0,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL,
                    PRIMARY KEY (user_id, chat_id, thread_id)
                )
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS pending_topic_messages (
                    user_id INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL,
                    thread_id INTEGER NOT NULL,
                    telegram_message_id INTEGER,
                    text TEXT NOT NULL,
                    reply_to_telegram_message_id INTEGER,
                    reply_fallback_text TEXT,
                    created_at INTEGER NOT NULL,
                    PRIMARY KEY (user_id, chat_id, thread_id)
                )
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS profile_facts (
                    user_id INTEGER NOT NULL,
                    fact TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    PRIMARY KEY (user_id, fact)
                )
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS topic_summaries (
                    user_id INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL,
                    thread_id INTEGER NOT NULL,
                    summary TEXT NOT NULL,
                    updated_at INTEGER NOT NULL,
                    PRIMARY KEY (user_id, chat_id, thread_id)
                )
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS topic_message_ids (
                    user_id INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL,
                    thread_id INTEGER NOT NULL,
                    telegram_message_id INTEGER NOT NULL,
                    owner TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    PRIMARY KEY (user_id, chat_id, thread_id, telegram_message_id)
                )
                """
            )

    @staticmethod
    def _thread_key(message_thread_id: Optional[int]) -> int:
        try:
            return int(message_thread_id or 0)
        except Exception:
            return 0

    async def upsert_user(self, user_id: int, username: str, full_name: str, language: Optional[str], verified: Optional[bool]) -> None:
        now = int(time.time())

        def _op() -> None:
            with self._connect() as conn:
                row = conn.execute("SELECT user_id, created_at FROM users WHERE user_id = ?", (user_id,)).fetchone()
                created_at = int(row["created_at"]) if row else now
                current = conn.execute(
                    "SELECT username, full_name, language, verified, show_duration, response_mode FROM users WHERE user_id = ?",
                    (user_id,),
                ).fetchone()
                lang = language if language is not None else (current["language"] if current else None)
                ver = int(verified) if verified is not None else (int(current["verified"]) if current else 0)
                uname = username if username is not None else (current["username"] if current else None)
                fname = full_name if full_name is not None else (current["full_name"] if current else None)
                show_dur = int(current["show_duration"]) if current and current["show_duration"] is not None else 1
                resp_mode = str(current["response_mode"]) if current and current["response_mode"] is not None else "normal"

                conn.execute(
                    """
                    INSERT INTO users (user_id, username, full_name, language, verified, show_duration, response_mode, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET
                        username=excluded.username,
                        full_name=excluded.full_name,
                        language=excluded.language,
                        verified=excluded.verified,
                        show_duration=excluded.show_duration,
                        response_mode=excluded.response_mode,
                        updated_at=excluded.updated_at
                    """,
                    (user_id, uname, fname, lang, ver, show_dur, resp_mode, created_at, now),
                )

        await asyncio.to_thread(_op)

    async def user_exists(self, user_id: int) -> bool:
        def _op() -> bool:
            with self._connect() as conn:
                row = conn.execute("SELECT 1 FROM users WHERE user_id = ? LIMIT 1", (user_id,)).fetchone()
                return bool(row)

        return await asyncio.to_thread(_op)

    async def track_chat(self, chat_id: int) -> None:
        now = int(time.time())

        def _op() -> None:
            with self._connect() as conn:
                conn.execute(
                    "INSERT INTO chats (chat_id, created_at) VALUES (?, ?) ON CONFLICT(chat_id) DO NOTHING",
                    (int(chat_id), now),
                )

        await asyncio.to_thread(_op)

    async def count_users(self) -> int:
        def _op() -> int:
            with self._connect() as conn:
                row = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()
                return int(row["c"] if row and row["c"] is not None else 0)

        return await asyncio.to_thread(_op)

    async def count_chats(self) -> int:
        def _op() -> int:
            with self._connect() as conn:
                row = conn.execute("SELECT COUNT(*) AS c FROM chats").fetchone()
                return int(row["c"] if row and row["c"] is not None else 0)

        return await asyncio.to_thread(_op)

    async def ensure_thread_settings(
        self,
        *,
        user_id: int,
        chat_id: int,
        message_thread_id: Optional[int],
        default_show_duration: bool,
        default_response_mode: str,
    ) -> None:
        now = int(time.time())
        thread_id = self._thread_key(message_thread_id)

        def _op() -> None:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO thread_settings (user_id, chat_id, thread_id, show_duration, response_mode, private_mode, asked_private_mode, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, 0, 0, ?, ?)
                    ON CONFLICT(user_id, chat_id, thread_id) DO NOTHING
                    """,
                    (int(user_id), int(chat_id), int(thread_id), 1 if default_show_duration else 0, str(default_response_mode), now, now),
                )

        await asyncio.to_thread(_op)

    async def get_thread_settings(self, *, user_id: int, chat_id: int, message_thread_id: Optional[int]) -> Dict[str, object]:
        thread_id = self._thread_key(message_thread_id)

        def _op() -> Dict[str, object]:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT show_duration, response_mode, private_mode, asked_private_mode FROM thread_settings WHERE user_id = ? AND chat_id = ? AND thread_id = ?",
                    (int(user_id), int(chat_id), int(thread_id)),
                ).fetchone()
                if not row:
                    return {"show_duration": True, "response_mode": "normal", "private_mode": False, "asked_private_mode": False}
                return {
                    "show_duration": bool(int(row["show_duration"])) if row["show_duration"] is not None else True,
                    "response_mode": str(row["response_mode"] or "normal"),
                    "private_mode": bool(int(row["private_mode"])) if row["private_mode"] is not None else False,
                    "asked_private_mode": bool(int(row["asked_private_mode"])) if row["asked_private_mode"] is not None else False,
                }

        return await asyncio.to_thread(_op)

    async def update_thread_settings(
        self,
        *,
        user_id: int,
        chat_id: int,
        message_thread_id: Optional[int],
        show_duration: Optional[bool] = None,
        response_mode: Optional[str] = None,
        private_mode: Optional[bool] = None,
        asked_private_mode: Optional[bool] = None,
    ) -> None:
        now = int(time.time())
        thread_id = self._thread_key(message_thread_id)

        def _op() -> None:
            with self._connect() as conn:
                parts: List[str] = []
                args: List[object] = []
                if show_duration is not None:
                    parts.append("show_duration = ?")
                    args.append(1 if show_duration else 0)
                if response_mode is not None:
                    parts.append("response_mode = ?")
                    args.append(str(response_mode))
                if private_mode is not None:
                    parts.append("private_mode = ?")
                    args.append(1 if private_mode else 0)
                if asked_private_mode is not None:
                    parts.append("asked_private_mode = ?")
                    args.append(1 if asked_private_mode else 0)
                if not parts:
                    return
                parts.append("updated_at = ?")
                args.append(now)
                args.extend([int(user_id), int(chat_id), int(thread_id)])
                conn.execute(
                    f"UPDATE thread_settings SET {', '.join(parts)} WHERE user_id = ? AND chat_id = ? AND thread_id = ?",
                    tuple(args),
                )

        await asyncio.to_thread(_op)

    async def set_pending_topic_message(
        self,
        *,
        user_id: int,
        chat_id: int,
        message_thread_id: Optional[int],
        telegram_message_id: Optional[int],
        text: str,
        reply_to_telegram_message_id: Optional[int],
        reply_fallback_text: str,
    ) -> None:
        now = int(time.time())
        thread_id = self._thread_key(message_thread_id)

        def _op() -> None:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO pending_topic_messages (user_id, chat_id, thread_id, telegram_message_id, text, reply_to_telegram_message_id, reply_fallback_text, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(user_id, chat_id, thread_id) DO UPDATE SET
                        telegram_message_id=excluded.telegram_message_id,
                        text=excluded.text,
                        reply_to_telegram_message_id=excluded.reply_to_telegram_message_id,
                        reply_fallback_text=excluded.reply_fallback_text,
                        created_at=excluded.created_at
                    """,
                    (
                        int(user_id),
                        int(chat_id),
                        int(thread_id),
                        int(telegram_message_id) if telegram_message_id is not None else None,
                        str(text),
                        int(reply_to_telegram_message_id) if reply_to_telegram_message_id is not None else None,
                        str(reply_fallback_text or ""),
                        now,
                    ),
                )

        await asyncio.to_thread(_op)

    async def get_pending_topic_message(self, *, user_id: int, chat_id: int, message_thread_id: Optional[int]) -> Optional[Dict[str, object]]:
        thread_id = self._thread_key(message_thread_id)

        def _op() -> Optional[Dict[str, object]]:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT telegram_message_id, text, reply_to_telegram_message_id, reply_fallback_text FROM pending_topic_messages WHERE user_id = ? AND chat_id = ? AND thread_id = ?",
                    (int(user_id), int(chat_id), int(thread_id)),
                ).fetchone()
                if not row:
                    return None
                return {
                    "telegram_message_id": int(row["telegram_message_id"]) if row["telegram_message_id"] is not None else None,
                    "text": str(row["text"] or ""),
                    "reply_to_telegram_message_id": int(row["reply_to_telegram_message_id"]) if row["reply_to_telegram_message_id"] is not None else None,
                    "reply_fallback_text": str(row["reply_fallback_text"] or ""),
                }

        return await asyncio.to_thread(_op)

    async def clear_pending_topic_message(self, *, user_id: int, chat_id: int, message_thread_id: Optional[int]) -> None:
        thread_id = self._thread_key(message_thread_id)

        def _op() -> None:
            with self._connect() as conn:
                conn.execute(
                    "DELETE FROM pending_topic_messages WHERE user_id = ? AND chat_id = ? AND thread_id = ?",
                    (int(user_id), int(chat_id), int(thread_id)),
                )

        await asyncio.to_thread(_op)

    async def add_profile_fact(self, *, user_id: int, fact: str) -> None:
        now = int(time.time())
        fact = (fact or "").strip()
        if not fact:
            return

        def _op() -> None:
            with self._connect() as conn:
                conn.execute(
                    "INSERT INTO profile_facts (user_id, fact, created_at) VALUES (?, ?, ?) ON CONFLICT(user_id, fact) DO NOTHING",
                    (int(user_id), fact, now),
                )

        await asyncio.to_thread(_op)

    async def list_profile_facts(self, *, user_id: int, limit: int = 24) -> List[str]:
        def _op() -> List[str]:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT fact FROM profile_facts WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
                    (int(user_id), int(limit)),
                ).fetchall()
                return [str(r["fact"]) for r in rows or []]

        return await asyncio.to_thread(_op)

    async def clear_profile_facts(self, *, user_id: int) -> None:
        def _op() -> None:
            with self._connect() as conn:
                conn.execute("DELETE FROM profile_facts WHERE user_id = ?", (int(user_id),))

        await asyncio.to_thread(_op)

    async def get_user_settings(self, user_id: int) -> Dict[str, object]:
        def _op() -> Dict[str, object]:
            with self._connect() as conn:
                row = conn.execute("SELECT show_duration, response_mode FROM users WHERE user_id = ?", (user_id,)).fetchone()
                if not row:
                    return {"show_duration": True, "response_mode": "normal"}
                show_duration = bool(int(row["show_duration"])) if row["show_duration"] is not None else True
                response_mode = str(row["response_mode"] or "normal")
                return {"show_duration": show_duration, "response_mode": response_mode}

        return await asyncio.to_thread(_op)

    async def update_user_settings(self, user_id: int, *, show_duration: Optional[bool] = None, response_mode: Optional[str] = None) -> None:
        now = int(time.time())

        def _op() -> None:
            with self._connect() as conn:
                parts: List[str] = []
                args: List[object] = []
                if show_duration is not None:
                    parts.append("show_duration = ?")
                    args.append(1 if show_duration else 0)
                if response_mode is not None:
                    parts.append("response_mode = ?")
                    args.append(str(response_mode))
                if not parts:
                    return
                parts.append("updated_at = ?")
                args.append(now)
                args.append(user_id)
                conn.execute(f"UPDATE users SET {', '.join(parts)} WHERE user_id = ?", tuple(args))

        await asyncio.to_thread(_op)

    async def create_message(
        self,
        *,
        user_id: int,
        chat_id: int,
        message_thread_id: Optional[int] = None,
        telegram_message_id: Optional[int] = None,
        role: str,
        text: str,
        reply_to_telegram_message_id: Optional[int] = None,
        parent_id: Optional[int] = None,
        duration_ms: Optional[int] = None,
    ) -> int:
        created_at = int(time.time())

        def _op() -> int:
            with self._connect() as conn:
                cur = conn.execute(
                    "INSERT INTO messages (user_id, chat_id, message_thread_id, telegram_message_id, role, text, reply_to_telegram_message_id, parent_id, duration_ms, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (user_id, chat_id, message_thread_id, telegram_message_id, role, text, reply_to_telegram_message_id, parent_id, duration_ms, created_at),
                )
                return int(cur.lastrowid)

        return await asyncio.to_thread(_op)

    async def update_message(
        self,
        message_id: int,
        *,
        text: Optional[str] = None,
        duration_ms: Optional[int] = None,
        telegram_message_id: Optional[int] = None,
    ) -> None:
        def _op() -> None:
            with self._connect() as conn:
                if text is None and duration_ms is None and telegram_message_id is None:
                    return
                parts = []
                args = []
                if text is not None:
                    parts.append("text = ?")
                    args.append(text)
                if duration_ms is not None:
                    parts.append("duration_ms = ?")
                    args.append(duration_ms)
                if telegram_message_id is not None:
                    parts.append("telegram_message_id = ?")
                    args.append(telegram_message_id)
                args.append(message_id)
                conn.execute(f"UPDATE messages SET {', '.join(parts)} WHERE id = ?", tuple(args))

        await asyncio.to_thread(_op)

    async def get_message(self, message_id: int) -> Optional[StoredMessage]:
        def _op() -> Optional[StoredMessage]:
            with self._connect() as conn:
                row = conn.execute("SELECT * FROM messages WHERE id = ?", (message_id,)).fetchone()
                if not row:
                    return None
                return StoredMessage(
                    id=int(row["id"]),
                    user_id=int(row["user_id"]),
                    chat_id=int(row["chat_id"]),
                    message_thread_id=int(row["message_thread_id"]) if row["message_thread_id"] is not None else None,
                    telegram_message_id=int(row["telegram_message_id"]) if row["telegram_message_id"] is not None else None,
                    role=str(row["role"]),
                    text=str(row["text"]),
                    reply_to_telegram_message_id=int(row["reply_to_telegram_message_id"]) if row["reply_to_telegram_message_id"] is not None else None,
                    parent_id=int(row["parent_id"]) if row["parent_id"] is not None else None,
                    duration_ms=int(row["duration_ms"]) if row["duration_ms"] is not None else None,
                    created_at=int(row["created_at"]),
                )

        return await asyncio.to_thread(_op)

    async def get_message_by_telegram_id(self, chat_id: int, telegram_message_id: int) -> Optional[StoredMessage]:
        def _op() -> Optional[StoredMessage]:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT * FROM messages WHERE chat_id = ? AND telegram_message_id = ? ORDER BY id DESC LIMIT 1",
                    (chat_id, telegram_message_id),
                ).fetchone()
                if not row:
                    return None
                return StoredMessage(
                    id=int(row["id"]),
                    user_id=int(row["user_id"]),
                    chat_id=int(row["chat_id"]),
                    message_thread_id=int(row["message_thread_id"]) if row["message_thread_id"] is not None else None,
                    telegram_message_id=int(row["telegram_message_id"]) if row["telegram_message_id"] is not None else None,
                    role=str(row["role"]),
                    text=str(row["text"]),
                    reply_to_telegram_message_id=int(row["reply_to_telegram_message_id"]) if row["reply_to_telegram_message_id"] is not None else None,
                    parent_id=int(row["parent_id"]) if row["parent_id"] is not None else None,
                    duration_ms=int(row["duration_ms"]) if row["duration_ms"] is not None else None,
                    created_at=int(row["created_at"]),
                )

        return await asyncio.to_thread(_op)

    async def get_recent_messages(
        self,
        *,
        user_id: int,
        chat_id: int,
        limit: int,
        message_thread_id: Optional[int] = None,
    ) -> List[StoredMessage]:
        def _op() -> List[StoredMessage]:
            where = "WHERE user_id = ? AND chat_id = ?"
            args: List[object] = [user_id, chat_id]
            if message_thread_id is not None:
                where += " AND message_thread_id = ?"
                args.append(message_thread_id)
            sql = f"SELECT * FROM messages {where} ORDER BY id DESC LIMIT ?"
            args.append(limit)
            with self._connect() as conn:
                rows = conn.execute(sql, tuple(args)).fetchall()
            out: List[StoredMessage] = []
            for row in reversed(rows):
                out.append(
                    StoredMessage(
                        id=int(row["id"]),
                        user_id=int(row["user_id"]),
                        chat_id=int(row["chat_id"]),
                        message_thread_id=int(row["message_thread_id"]) if row["message_thread_id"] is not None else None,
                        telegram_message_id=int(row["telegram_message_id"]) if row["telegram_message_id"] is not None else None,
                        role=str(row["role"]),
                        text=str(row["text"]),
                        reply_to_telegram_message_id=int(row["reply_to_telegram_message_id"]) if row["reply_to_telegram_message_id"] is not None else None,
                        parent_id=int(row["parent_id"]) if row["parent_id"] is not None else None,
                        duration_ms=int(row["duration_ms"]) if row["duration_ms"] is not None else None,
                        created_at=int(row["created_at"]),
                    )
                )
            return out

        return await asyncio.to_thread(_op)

    async def get_parent(self, message_id: int) -> Optional[StoredMessage]:
        msg = await self.get_message(message_id)
        if not msg or msg.parent_id is None:
            return None
        return await self.get_message(msg.parent_id)

    async def delete_messages(
        self,
        *,
        user_id: int,
        chat_id: int,
        message_thread_id: Optional[int] = None,
    ) -> int:
        def _op() -> int:
            where = "WHERE user_id = ? AND chat_id = ?"
            args: List[object] = [user_id, chat_id]
            if message_thread_id is None:
                sql = f"DELETE FROM messages {where}"
            else:
                where += " AND message_thread_id = ?"
                args.append(message_thread_id)
                sql = f"DELETE FROM messages {where}"
            with self._connect() as conn:
                cur = conn.execute(sql, tuple(args))
                return int(cur.rowcount or 0)

        return await asyncio.to_thread(_op)

    async def count_messages(
        self,
        *,
        user_id: int,
        chat_id: int,
        message_thread_id: Optional[int] = None,
    ) -> int:
        def _op() -> int:
            where = "WHERE user_id = ? AND chat_id = ?"
            args: List[object] = [user_id, chat_id]
            if message_thread_id is not None:
                where += " AND message_thread_id = ?"
                args.append(message_thread_id)
            sql = f"SELECT COUNT(*) AS c FROM messages {where}"
            with self._connect() as conn:
                row = conn.execute(sql, tuple(args)).fetchone()
            return int(row["c"]) if row else 0

        return await asyncio.to_thread(_op)

    async def count_messages_by_role(
        self,
        *,
        user_id: int,
        chat_id: int,
        role: str,
        message_thread_id: Optional[int] = None,
        any_thread: bool = True,
    ) -> int:
        def _op() -> int:
            where = "WHERE user_id = ? AND chat_id = ? AND role = ?"
            args: List[object] = [int(user_id), int(chat_id), str(role)]
            if not bool(any_thread):
                if message_thread_id is None:
                    where += " AND message_thread_id IS NULL"
                else:
                    where += " AND message_thread_id = ?"
                    args.append(int(message_thread_id))
            sql = f"SELECT COUNT(*) AS c FROM messages {where}"
            with self._connect() as conn:
                row = conn.execute(sql, tuple(args)).fetchone()
            return int(row["c"]) if row else 0

        return await asyncio.to_thread(_op)

    async def get_recent_texts_by_role(
        self,
        *,
        user_id: int,
        chat_id: int,
        role: str,
        limit: int,
        message_thread_id: Optional[int] = None,
        any_thread: bool = True,
    ) -> List[str]:
        def _op() -> List[str]:
            where = "WHERE user_id = ? AND chat_id = ? AND role = ?"
            args: List[object] = [int(user_id), int(chat_id), str(role)]
            if not bool(any_thread):
                if message_thread_id is None:
                    where += " AND message_thread_id IS NULL"
                else:
                    where += " AND message_thread_id = ?"
                    args.append(int(message_thread_id))
            sql = f"SELECT text FROM messages {where} ORDER BY id DESC LIMIT ?"
            args.append(int(limit))
            with self._connect() as conn:
                rows = conn.execute(sql, tuple(args)).fetchall()
            out: List[str] = []
            for row in reversed(rows or []):
                out.append(str(row["text"] or ""))
            return out

        return await asyncio.to_thread(_op)

    async def upsert_topic_summary(
        self,
        *,
        user_id: int,
        chat_id: int,
        message_thread_id: Optional[int],
        summary: str,
    ) -> None:
        now = int(time.time())
        thread_id = self._thread_key(message_thread_id)
        summary = (summary or "").strip() or " "

        def _op() -> None:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO topic_summaries (user_id, chat_id, thread_id, summary, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(user_id, chat_id, thread_id) DO UPDATE SET
                        summary=excluded.summary,
                        updated_at=excluded.updated_at
                    """,
                    (int(user_id), int(chat_id), int(thread_id), summary, now),
                )

        await asyncio.to_thread(_op)

    async def get_topic_summary(self, *, user_id: int, chat_id: int, message_thread_id: Optional[int]) -> Optional[str]:
        thread_id = self._thread_key(message_thread_id)

        def _op() -> Optional[str]:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT summary FROM topic_summaries WHERE user_id = ? AND chat_id = ? AND thread_id = ?",
                    (int(user_id), int(chat_id), int(thread_id)),
                ).fetchone()
            if not row:
                return None
            val = str(row["summary"] or "").strip()
            return val or None

        return await asyncio.to_thread(_op)

    async def clear_topic_summary(self, *, user_id: int, chat_id: int, message_thread_id: Optional[int]) -> None:
        thread_id = self._thread_key(message_thread_id)

        def _op() -> None:
            with self._connect() as conn:
                conn.execute(
                    "DELETE FROM topic_summaries WHERE user_id = ? AND chat_id = ? AND thread_id = ?",
                    (int(user_id), int(chat_id), int(thread_id)),
                )

        await asyncio.to_thread(_op)

    async def count_messages_in_thread(self, *, user_id: int, chat_id: int, message_thread_id: Optional[int]) -> int:
        def _op() -> int:
            where = "WHERE user_id = ? AND chat_id = ?"
            args: List[object] = [int(user_id), int(chat_id)]
            if message_thread_id is None:
                where += " AND message_thread_id IS NULL"
            else:
                where += " AND message_thread_id = ?"
                args.append(int(message_thread_id))
            sql = f"SELECT COUNT(*) AS c FROM messages {where}"
            with self._connect() as conn:
                row = conn.execute(sql, tuple(args)).fetchone()
            return int(row["c"]) if row else 0

        return await asyncio.to_thread(_op)

    async def count_visible_messages_in_thread(self, *, user_id: int, chat_id: int, message_thread_id: Optional[int]) -> int:
        def _op() -> int:
            where = "WHERE user_id = ? AND chat_id = ? AND telegram_message_id IS NOT NULL"
            args: List[object] = [int(user_id), int(chat_id)]
            if message_thread_id is None:
                where += " AND message_thread_id IS NULL"
            else:
                where += " AND message_thread_id = ?"
                args.append(int(message_thread_id))
            sql = f"SELECT COUNT(*) AS c FROM messages {where}"
            with self._connect() as conn:
                row = conn.execute(sql, tuple(args)).fetchone()
            return int(row["c"]) if row else 0

        return await asyncio.to_thread(_op)

    async def get_messages_page_in_thread(
        self,
        *,
        user_id: int,
        chat_id: int,
        message_thread_id: Optional[int],
        limit: int,
        offset: int,
    ) -> List[StoredMessage]:
        def _op() -> List[StoredMessage]:
            where = "WHERE user_id = ? AND chat_id = ?"
            args: List[object] = [int(user_id), int(chat_id)]
            if message_thread_id is None:
                where += " AND message_thread_id IS NULL"
            else:
                where += " AND message_thread_id = ?"
                args.append(int(message_thread_id))
            sql = f"SELECT * FROM messages {where} ORDER BY id DESC LIMIT ? OFFSET ?"
            args.extend([int(limit), int(max(0, offset))])
            with self._connect() as conn:
                rows = conn.execute(sql, tuple(args)).fetchall()
            out: List[StoredMessage] = []
            for row in reversed(rows or []):
                out.append(
                    StoredMessage(
                        id=int(row["id"]),
                        user_id=int(row["user_id"]),
                        chat_id=int(row["chat_id"]),
                        message_thread_id=int(row["message_thread_id"]) if row["message_thread_id"] is not None else None,
                        telegram_message_id=int(row["telegram_message_id"]) if row["telegram_message_id"] is not None else None,
                        role=str(row["role"]),
                        text=str(row["text"]),
                        reply_to_telegram_message_id=int(row["reply_to_telegram_message_id"]) if row["reply_to_telegram_message_id"] is not None else None,
                        parent_id=int(row["parent_id"]) if row["parent_id"] is not None else None,
                        duration_ms=int(row["duration_ms"]) if row["duration_ms"] is not None else None,
                        created_at=int(row["created_at"]),
                    )
                )
            return out

        return await asyncio.to_thread(_op)

    async def get_visible_messages_page_in_thread(
        self,
        *,
        user_id: int,
        chat_id: int,
        message_thread_id: Optional[int],
        limit: int,
        offset: int,
    ) -> List[StoredMessage]:
        def _op() -> List[StoredMessage]:
            where = "WHERE user_id = ? AND chat_id = ? AND telegram_message_id IS NOT NULL"
            args: List[object] = [int(user_id), int(chat_id)]
            if message_thread_id is None:
                where += " AND message_thread_id IS NULL"
            else:
                where += " AND message_thread_id = ?"
                args.append(int(message_thread_id))
            sql = f"SELECT * FROM messages {where} ORDER BY id DESC LIMIT ? OFFSET ?"
            args.extend([int(limit), int(max(0, offset))])
            with self._connect() as conn:
                rows = conn.execute(sql, tuple(args)).fetchall()
            out: List[StoredMessage] = []
            for row in reversed(rows or []):
                out.append(
                    StoredMessage(
                        id=int(row["id"]),
                        user_id=int(row["user_id"]),
                        chat_id=int(row["chat_id"]),
                        message_thread_id=int(row["message_thread_id"]) if row["message_thread_id"] is not None else None,
                        telegram_message_id=int(row["telegram_message_id"]) if row["telegram_message_id"] is not None else None,
                        role=str(row["role"]),
                        text=str(row["text"]),
                        reply_to_telegram_message_id=int(row["reply_to_telegram_message_id"]) if row["reply_to_telegram_message_id"] is not None else None,
                        parent_id=int(row["parent_id"]) if row["parent_id"] is not None else None,
                        duration_ms=int(row["duration_ms"]) if row["duration_ms"] is not None else None,
                        created_at=int(row["created_at"]),
                    )
                )
            return out

        return await asyncio.to_thread(_op)

    async def list_telegram_message_ids_in_thread(self, *, user_id: int, chat_id: int, message_thread_id: Optional[int]) -> List[int]:
        def _op() -> List[int]:
            where = "WHERE user_id = ? AND chat_id = ? AND telegram_message_id IS NOT NULL"
            args: List[object] = [int(user_id), int(chat_id)]
            if message_thread_id is None:
                where += " AND message_thread_id IS NULL"
            else:
                where += " AND message_thread_id = ?"
                args.append(int(message_thread_id))
            sql = f"SELECT DISTINCT telegram_message_id FROM messages {where}"
            with self._connect() as conn:
                rows = conn.execute(sql, tuple(args)).fetchall()
            out: List[int] = []
            for r in rows or []:
                try:
                    out.append(int(r["telegram_message_id"]))
                except Exception:
                    continue
            return out

        return await asyncio.to_thread(_op)

    async def list_telegram_message_ids_in_chat(self, *, user_id: int, chat_id: int) -> List[int]:
        def _op() -> List[int]:
            sql = "SELECT DISTINCT telegram_message_id FROM messages WHERE user_id = ? AND chat_id = ? AND telegram_message_id IS NOT NULL"
            with self._connect() as conn:
                rows = conn.execute(sql, (int(user_id), int(chat_id))).fetchall()
            out: List[int] = []
            for r in rows or []:
                try:
                    out.append(int(r["telegram_message_id"]))
                except Exception:
                    continue
            return out

        return await asyncio.to_thread(_op)

    async def add_topic_message_id(
        self,
        *,
        user_id: int,
        chat_id: int,
        message_thread_id: Optional[int],
        telegram_message_id: int,
        owner: str,
    ) -> None:
        now = int(time.time())
        thread_id = self._thread_key(message_thread_id)

        def _op() -> None:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO topic_message_ids (user_id, chat_id, thread_id, telegram_message_id, owner, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(user_id, chat_id, thread_id, telegram_message_id) DO NOTHING
                    """,
                    (int(user_id), int(chat_id), int(thread_id), int(telegram_message_id), str(owner), now),
                )

        await asyncio.to_thread(_op)

    async def list_topic_message_ids(self, *, user_id: int, chat_id: int, message_thread_id: Optional[int]) -> List[int]:
        thread_id = self._thread_key(message_thread_id)

        def _op() -> List[int]:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT telegram_message_id FROM topic_message_ids WHERE user_id = ? AND chat_id = ? AND thread_id = ?",
                    (int(user_id), int(chat_id), int(thread_id)),
                ).fetchall()
            out: List[int] = []
            for r in rows or []:
                try:
                    out.append(int(r["telegram_message_id"]))
                except Exception:
                    continue
            return out

        return await asyncio.to_thread(_op)

    async def list_topic_message_ids_in_chat(self, *, user_id: int, chat_id: int) -> List[int]:
        def _op() -> List[int]:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT telegram_message_id FROM topic_message_ids WHERE user_id = ? AND chat_id = ?",
                    (int(user_id), int(chat_id)),
                ).fetchall()
            out: List[int] = []
            for r in rows or []:
                try:
                    out.append(int(r["telegram_message_id"]))
                except Exception:
                    continue
            return out

        return await asyncio.to_thread(_op)

    async def clear_topic_message_ids(self, *, user_id: int, chat_id: int, message_thread_id: Optional[int]) -> None:
        thread_id = self._thread_key(message_thread_id)

        def _op() -> None:
            with self._connect() as conn:
                conn.execute(
                    "DELETE FROM topic_message_ids WHERE user_id = ? AND chat_id = ? AND thread_id = ?",
                    (int(user_id), int(chat_id), int(thread_id)),
                )

        await asyncio.to_thread(_op)

    async def clear_topic_message_ids_in_chat(self, *, user_id: int, chat_id: int) -> None:
        def _op() -> None:
            with self._connect() as conn:
                conn.execute("DELETE FROM topic_message_ids WHERE user_id = ? AND chat_id = ?", (int(user_id), int(chat_id)))

        await asyncio.to_thread(_op)

    async def delete_topic_data(self, *, user_id: int, chat_id: int, message_thread_id: Optional[int]) -> int:
        thread_id = self._thread_key(message_thread_id)

        def _op() -> int:
            with self._connect() as conn:
                if message_thread_id is None:
                    cur = conn.execute(
                        "DELETE FROM messages WHERE user_id = ? AND chat_id = ? AND message_thread_id IS NULL",
                        (int(user_id), int(chat_id)),
                    )
                else:
                    cur = conn.execute(
                        "DELETE FROM messages WHERE user_id = ? AND chat_id = ? AND message_thread_id = ?",
                        (int(user_id), int(chat_id), int(message_thread_id)),
                    )
                conn.execute(
                    "DELETE FROM pending_topic_messages WHERE user_id = ? AND chat_id = ? AND thread_id = ?",
                    (int(user_id), int(chat_id), int(thread_id)),
                )
                conn.execute(
                    "DELETE FROM topic_summaries WHERE user_id = ? AND chat_id = ? AND thread_id = ?",
                    (int(user_id), int(chat_id), int(thread_id)),
                )
                conn.execute(
                    "DELETE FROM topic_message_ids WHERE user_id = ? AND chat_id = ? AND thread_id = ?",
                    (int(user_id), int(chat_id), int(thread_id)),
                )
                return int(cur.rowcount or 0)

        return await asyncio.to_thread(_op)

    async def delete_all_data_for_chat(self, *, user_id: int, chat_id: int) -> int:
        def _op() -> int:
            with self._connect() as conn:
                cur = conn.execute("DELETE FROM messages WHERE user_id = ? AND chat_id = ?", (int(user_id), int(chat_id)))
                conn.execute("DELETE FROM pending_topic_messages WHERE user_id = ? AND chat_id = ?", (int(user_id), int(chat_id)))
                conn.execute("DELETE FROM topic_summaries WHERE user_id = ? AND chat_id = ?", (int(user_id), int(chat_id)))
                conn.execute("DELETE FROM topic_message_ids WHERE user_id = ? AND chat_id = ?", (int(user_id), int(chat_id)))
                return int(cur.rowcount or 0)

        return await asyncio.to_thread(_op)

    async def get_user_message_stats(self, *, user_id: int, chat_id: int) -> Tuple[int, int]:
        def _op() -> Tuple[int, int]:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT COUNT(*) AS c, MIN(created_at) AS first_ts FROM messages WHERE user_id = ? AND chat_id = ?",
                    (user_id, chat_id),
                ).fetchone()
            if not row:
                return 0, 0
            return int(row["c"] or 0), int(row["first_ts"] or 0)

        return await asyncio.to_thread(_op)
