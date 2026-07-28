"""Multi-turn conversation storage, backed by SQLite.

Separate from HistoryStore (core/history.py), which records every pipeline
run for leaderboard analytics regardless of whether it happened inside a
conversation. A conversation is a sequence of user/assistant messages; each
assistant message optionally carries the full PipelineResult (as JSON) that
produced it, so a reloaded conversation can render the same synthesized
answer, comparison table, and per-agent breakdown as a fresh query.
"""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

from core.cost_tracker import estimate_tokens

_DEFAULT_TITLE = "New conversation"


class ConversationStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    agent_responses_json TEXT,
                    created_at REAL NOT NULL,
                    FOREIGN KEY(conversation_id) REFERENCES conversations(id)
                )
                """
            )
            conn.commit()

    def create(self, title: str | None = None) -> int:
        now = time.time()
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "INSERT INTO conversations (title, created_at, updated_at) VALUES (?, ?, ?)",
                (title or _DEFAULT_TITLE, now, now),
            )
            conn.commit()
            return cur.lastrowid

    def exists(self, conversation_id: int) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT 1 FROM conversations WHERE id = ?", (conversation_id,)).fetchone()
        return row is not None

    def get_meta(self, conversation_id: int) -> dict | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT id, title, created_at, updated_at FROM conversations WHERE id = ?", (conversation_id,)
            ).fetchone()
            if row is None:
                return None
            count = conn.execute(
                "SELECT COUNT(*) FROM messages WHERE conversation_id = ?", (conversation_id,)
            ).fetchone()[0]
        return {"id": row[0], "title": row[1], "created_at": row[2], "updated_at": row[3], "message_count": count}

    def list(self, page: int = 1, page_size: int = 20, search: str | None = None) -> list[dict]:
        query = "SELECT id, title, created_at, updated_at FROM conversations"
        params: list = []
        if search:
            query += " WHERE title LIKE ?"
            params.append(f"%{search}%")
        query += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
        params.extend([page_size, (page - 1) * page_size])

        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(query, params).fetchall()
            items = []
            for row in rows:
                count = conn.execute(
                    "SELECT COUNT(*) FROM messages WHERE conversation_id = ?", (row[0],)
                ).fetchone()[0]
                items.append({"id": row[0], "title": row[1], "created_at": row[2], "updated_at": row[3], "message_count": count})
        return items

    def count(self, search: str | None = None) -> int:
        query = "SELECT COUNT(*) FROM conversations"
        params: list = []
        if search:
            query += " WHERE title LIKE ?"
            params.append(f"%{search}%")
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute(query, params).fetchone()[0]

    def get(self, conversation_id: int) -> dict | None:
        meta = self.get_meta(conversation_id)
        if meta is None:
            return None
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT id, role, content, agent_responses_json, created_at
                FROM messages WHERE conversation_id = ? ORDER BY id ASC
                """,
                (conversation_id,),
            ).fetchall()
        messages = [
            {
                "id": r[0],
                "role": r[1],
                "content": r[2],
                "agent_responses": None if r[3] is None else json.loads(r[3]),
                "created_at": r[4],
            }
            for r in rows
        ]
        return {**meta, "messages": messages}

    def add_message(
        self, conversation_id: int, role: str, content: str, agent_responses_json: str | None = None
    ) -> int:
        now = time.time()
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                """
                INSERT INTO messages (conversation_id, role, content, agent_responses_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (conversation_id, role, content, agent_responses_json, now),
            )
            conn.execute("UPDATE conversations SET updated_at = ? WHERE id = ?", (now, conversation_id))
            conn.commit()
            return cur.lastrowid

    def message_count(self, conversation_id: int) -> int:
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM messages WHERE conversation_id = ?", (conversation_id,)
            ).fetchone()[0]

    def rename(self, conversation_id: int, title: str) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",
                (title, time.time(), conversation_id),
            )
            conn.commit()

    def delete(self, conversation_id: int) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
            conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
            conn.commit()

    def build_context(self, conversation_id: int, max_messages: int = 10, max_tokens: int = 3000) -> str:
        """Format the last `max_messages` messages as context, trimming the
        oldest first if the estimated token count exceeds `max_tokens`.

        Returns an empty string if there's no prior history (e.g. the first
        message in a new conversation) — callers should treat that as "no
        context to prepend."
        """
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT role, content FROM messages WHERE conversation_id = ?
                ORDER BY id DESC LIMIT ?
                """,
                (conversation_id, max_messages),
            ).fetchall()
        messages = list(reversed(rows))  # oldest first

        while messages:
            text = _format_messages(messages)
            if estimate_tokens(text) <= max_tokens:
                return text
            messages = messages[1:]  # drop the oldest and re-check
        return ""


def _format_messages(messages: list[tuple[str, str]]) -> str:
    lines = []
    for role, content in messages:
        label = "User" if role == "user" else "Assistant"
        lines.append(f"{label}: {content}")
    return "\n".join(lines)
