"""GET /api/history — paginated query history."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

router = APIRouter()


@router.get("/history")
async def get_history(request: Request, page: int = 1, page_size: int = 20, search: str | None = None) -> dict:
    page = max(1, page)
    page_size = max(1, min(100, page_size))
    orch = request.app.state.orchestrator

    total = orch.history.count(search=search)
    offset = (page - 1) * page_size
    entries = orch.history.recent(limit=page_size, offset=offset, search=search)

    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": max(1, (total + page_size - 1) // page_size),
        "items": [
            {
                "id": e.id,
                "query": e.query,
                "query_type": e.query_type,
                "confidence_score": e.confidence_score,
                "total_latency_ms": e.total_latency_ms,
                "estimated_cost_usd": e.estimated_cost_usd,
                "timestamp": e.timestamp,
            }
            for e in entries
        ],
    }


@router.get("/history/{query_id}")
async def get_history_item(query_id: int, request: Request) -> dict:
    orch = request.app.state.orchestrator
    entry = orch.history.get(query_id)
    if entry is None:
        raise HTTPException(404, f"No history entry with id {query_id}")
    return entry.result().to_dict()
