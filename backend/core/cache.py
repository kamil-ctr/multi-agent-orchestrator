"""Prompt-hash response cache backed by SQLite, with TTL expiry."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from pathlib import Path

from core.schemas import PipelineResult


class ResponseCache:
    def __init__(self, db_path: Path, ttl_seconds: int = 3600) -> None:
        self.db_path = db_path
        self.ttl_seconds = ttl_seconds
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cache (
                    prompt_hash TEXT PRIMARY KEY,
                    result_json TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
                """
            )
            conn.commit()

    @staticmethod
    def hash_prompt(prompt: str) -> str:
        return hashlib.sha256(prompt.strip().lower().encode("utf-8")).hexdigest()

    def get(self, prompt: str) -> PipelineResult | None:
        key = self.hash_prompt(prompt)
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT result_json, created_at FROM cache WHERE prompt_hash = ?",
                (key,),
            ).fetchone()

        if row is None:
            return None

        result_json, created_at = row
        if time.time() - created_at > self.ttl_seconds:
            self.invalidate(prompt)
            return None

        result = PipelineResult.from_dict(json.loads(result_json))
        result.cached = True
        return result

    def set(self, prompt: str, result: PipelineResult) -> None:
        key = self.hash_prompt(prompt)
        payload = json.dumps(result.to_dict())
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO cache (prompt_hash, result_json, created_at)
                VALUES (?, ?, ?)
                ON CONFLICT(prompt_hash) DO UPDATE SET
                    result_json = excluded.result_json,
                    created_at = excluded.created_at
                """,
                (key, payload, time.time()),
            )
            conn.commit()

    def invalidate(self, prompt: str) -> None:
        key = self.hash_prompt(prompt)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM cache WHERE prompt_hash = ?", (key,))
            conn.commit()

    def clear(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM cache")
            conn.commit()
