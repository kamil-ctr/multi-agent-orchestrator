"""GET /api/leaderboard — agent performance rankings, aggregated from history."""
from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/leaderboard")
async def get_leaderboard(request: Request, query_type: str | None = None) -> dict:
    orch = request.app.state.orchestrator
    rows = orch.history.leaderboard(query_type)
    return {"query_type": query_type, "rows": rows}
