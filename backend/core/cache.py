"""Prompt-hash response cache backed by SQLite, with TTL expiry.

Also supports semantic caching: on write, a query's embedding (see
core/embeddings.py) is stored alongside the response; on a cache miss by
exact hash, the incoming query's embedding is compared against stored
ones (scoped to the same conversation, or globally across standalone
queries) via cosine similarity, and a hit above the configured threshold
returns that cached result instead of re-dispatching to every agent.
Embeddings are stored as raw float32 bytes via the stdlib `array` module
(no numpy dependency) — see core/embeddings.py's docstring for why this
avoids pulling in a local ML runtime.

`conversation_id` is NULL for standalone (non-conversation) queries and
set for turns within a conversation. Rows are keyed by an autoincrement
id rather than prompt_hash alone: identical prompt text asked in two
different conversations must NOT collide (their surrounding context, and
therefore the correct answer, can differ), so each conversation-scoped
turn gets its own row. Exact-hash lookups/writes stay restricted to
conversation_id IS NULL — the original global "same question, same
answer" fast path — and dedupe in place same as before this feature.
"""
from __future__ import annotations

import array
import hashlib
import json
import sqlite3
import time
from pathlib import Path

from core.embeddings import cosine_similarity
from core.schemas import PipelineResult


class ResponseCache:
    def __init__(self, db_path: Path, ttl_seconds: int = 3600) -> None:
        self.db_path = db_path
        self.ttl_seconds = ttl_seconds
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            cols = {row[1] for row in conn.execute("PRAGMA table_info(cache)")}
            if cols and "id" not in cols:
                # Pre-semantic-caching schema (prompt_hash as PRIMARY KEY) —
                # this is a TTL-based cache, not durable user data, so the
                # simplest safe migration is to drop and recreate it.
                conn.execute("DROP TABLE cache")
                cols = set()

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prompt_hash TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    embedding BLOB,
                    conversation_id INTEGER
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_prompt_hash ON cache(prompt_hash)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_conversation_id ON cache(conversation_id)")
            conn.commit()

    @staticmethod
    def hash_prompt(prompt: str) -> str:
        return hashlib.sha256(prompt.strip().lower().encode("utf-8")).hexdigest()

    @staticmethod
    def _encode_embedding(embedding: list[float]) -> bytes:
        return array.array("f", embedding).tobytes()

    @staticmethod
    def _decode_embedding(blob: bytes) -> list[float]:
        arr = array.array("f")
        arr.frombytes(blob)
        return list(arr)

    def get(self, prompt: str) -> PipelineResult | None:
        """Exact prompt-hash lookup, scoped to standalone (non-conversation)
        entries — unchanged behavior from before semantic caching."""
        key = self.hash_prompt(prompt)
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT result_json, created_at FROM cache WHERE prompt_hash = ? AND conversation_id IS NULL",
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

    def get_semantic(
        self, embedding: list[float], threshold: float, conversation_id: int | None = None
    ) -> tuple[PipelineResult | None, float | None]:
        """Find the best semantically-similar cached entry above `threshold`.

        Scoped to `conversation_id` when given (only that conversation's
        prior turns are considered), or to other standalone entries
        (conversation_id IS NULL) otherwise — a standalone query never
        matches a response given in the context of an unrelated
        conversation, and vice versa.

        Returns (None, None) if nothing stored has an embedding, nothing
        is above threshold, or every candidate has expired.
        """
        if conversation_id is not None:
            query = "SELECT result_json, embedding, created_at FROM cache WHERE conversation_id = ? AND embedding IS NOT NULL"
            params: tuple = (conversation_id,)
        else:
            query = "SELECT result_json, embedding, created_at FROM cache WHERE conversation_id IS NULL AND embedding IS NOT NULL"
            params = ()

        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(query, params).fetchall()

        now = time.time()
        best_sim = 0.0
        best_result_json: str | None = None
        for result_json, emb_blob, created_at in rows:
            if now - created_at > self.ttl_seconds:
                continue
            sim = cosine_similarity(embedding, self._decode_embedding(emb_blob))
            if sim > best_sim:
                best_sim = sim
                best_result_json = result_json

        if best_result_json is not None and best_sim >= threshold:
            result = PipelineResult.from_dict(json.loads(best_result_json))
            result.cached = True
            return result, best_sim
        return None, None

    def set(
        self,
        prompt: str,
        result: PipelineResult,
        embedding: list[float] | None = None,
        conversation_id: int | None = None,
    ) -> None:
        key = self.hash_prompt(prompt)
        payload = json.dumps(result.to_dict())
        emb_bytes = self._encode_embedding(embedding) if embedding else None
        with sqlite3.connect(self.db_path) as conn:
            if conversation_id is None:
                # Standalone entries dedupe in place, same as the old
                # prompt_hash-primary-key behavior.
                conn.execute("DELETE FROM cache WHERE prompt_hash = ? AND conversation_id IS NULL", (key,))
            conn.execute(
                """
                INSERT INTO cache (prompt_hash, result_json, created_at, embedding, conversation_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                (key, payload, time.time(), emb_bytes, conversation_id),
            )
            conn.commit()

    def invalidate(self, prompt: str) -> None:
        key = self.hash_prompt(prompt)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM cache WHERE prompt_hash = ? AND conversation_id IS NULL", (key,))
            conn.commit()

    def clear(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM cache")
            conn.commit()
