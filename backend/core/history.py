"""Query history & agent-performance analytics, backed by SQLite."""
from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

from core.schemas import PipelineResult


@dataclass
class HistoryEntry:
    id: int
    query: str
    query_type: str
    confidence_score: float
    total_latency_ms: float
    estimated_cost_usd: float
    timestamp: float
    result_json: str

    def result(self) -> PipelineResult:
        return PipelineResult.from_dict(json.loads(self.result_json))


class HistoryStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS queries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query TEXT NOT NULL,
                    query_type TEXT NOT NULL,
                    confidence_score REAL NOT NULL,
                    total_latency_ms REAL NOT NULL,
                    estimated_cost_usd REAL NOT NULL,
                    timestamp REAL NOT NULL,
                    result_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query_id INTEGER NOT NULL,
                    agent TEXT NOT NULL,
                    query_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    overall_score REAL,
                    latency_ms REAL,
                    timestamp REAL NOT NULL,
                    FOREIGN KEY(query_id) REFERENCES queries(id)
                )
                """
            )
            conn.commit()

    def record(self, result: PipelineResult) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                """
                INSERT INTO queries
                    (query, query_type, confidence_score, total_latency_ms,
                     estimated_cost_usd, timestamp, result_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.query,
                    result.query_type,
                    result.confidence_score,
                    result.total_latency_ms,
                    result.estimated_cost_usd,
                    result.timestamp,
                    json.dumps(result.to_dict()),
                ),
            )
            query_id = cur.lastrowid

            score_by_agent = {e.agent: e.overall for e in result.evaluations}
            for resp in result.agent_responses:
                conn.execute(
                    """
                    INSERT INTO agent_scores
                        (query_id, agent, query_type, status, overall_score, latency_ms, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        query_id,
                        resp.agent,
                        result.query_type,
                        resp.status.value,
                        score_by_agent.get(resp.agent),
                        resp.latency_ms,
                        result.timestamp,
                    ),
                )
            conn.commit()
            return query_id

    def recent(self, limit: int = 20, offset: int = 0, search: str | None = None) -> list[HistoryEntry]:
        query = """
            SELECT id, query, query_type, confidence_score, total_latency_ms,
                   estimated_cost_usd, timestamp, result_json
            FROM queries
        """
        params: list = []
        if search:
            query += " WHERE query LIKE ?"
            params.append(f"%{search}%")
        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(query, params).fetchall()
        return [HistoryEntry(*row) for row in rows]

    def count(self, search: str | None = None) -> int:
        query = "SELECT COUNT(*) FROM queries"
        params: list = []
        if search:
            query += " WHERE query LIKE ?"
            params.append(f"%{search}%")
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute(query, params).fetchone()[0]

    def get(self, query_id: int) -> HistoryEntry | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT id, query, query_type, confidence_score, total_latency_ms,
                       estimated_cost_usd, timestamp, result_json
                FROM queries WHERE id = ?
                """,
                (query_id,),
            ).fetchone()
        return HistoryEntry(*row) if row else None

    def leaderboard(self, query_type: str | None = None) -> list[dict]:
        """Aggregate agent performance: win rate, avg score, avg latency, success rate."""
        query = """
            SELECT agent,
                   COUNT(*) as total_runs,
                   SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successes,
                   AVG(CASE WHEN status = 'success' THEN overall_score END) as avg_score,
                   AVG(CASE WHEN status = 'success' THEN latency_ms END) as avg_latency_ms
            FROM agent_scores
        """
        params: tuple = ()
        if query_type:
            query += " WHERE query_type = ?"
            params = (query_type,)
        query += " GROUP BY agent"

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            cols = [d[0] for d in cursor.description]

        results = []
        for row in rows:
            d = dict(zip(cols, row))
            d["success_rate"] = (d["successes"] / d["total_runs"]) if d["total_runs"] else 0.0
            results.append(d)
        results.sort(key=lambda d: (d["avg_score"] is None, -(d["avg_score"] or 0)))
        return results

    def stats_by_query_type(self) -> dict[str, int]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT query_type, COUNT(*) FROM queries GROUP BY query_type"
            ).fetchall()
        return dict(rows)
