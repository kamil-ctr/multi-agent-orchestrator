"""Shared in-memory job store for SSE-streamed pipeline runs.

Used by both /api/query (legacy single-shot) and
/api/conversations/{id}/messages — a query_id from either endpoint is
consumed the same way via GET /api/query/{query_id}/stream, since the SSE
event shape doesn't depend on which endpoint started the run.
"""
from __future__ import annotations

import time
from collections import OrderedDict

_MAX_JOBS = 200


class QueryJob:
    def __init__(self, query_id: str) -> None:
        self.query_id = query_id
        self.events: list[dict] = []
        self.done = False
        self.created_at = time.time()


JOBS: "OrderedDict[str, QueryJob]" = OrderedDict()


def register_job(job: QueryJob) -> None:
    JOBS[job.query_id] = job
    while len(JOBS) > _MAX_JOBS:
        JOBS.popitem(last=False)
