"""GET /api/agents — configured agents with live availability status.

Never exposes the key value itself — only whether one is configured.
"""
from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/agents")
async def list_agents(request: Request) -> list[dict]:
    orch = request.app.state.orchestrator
    return [
        {
            "name": a.name,
            "model": a.config.model,
            "vision_model": a.config.vision_model,
            "supports_vision": a.supports_vision,
            "enabled": a.config.enabled,
            "available": a.is_available,
            "key_configured": bool(a.config.api_key),
            "timeout_s": a.config.timeout_s,
            "max_retries": a.config.max_retries,
        }
        for a in orch.agents
    ]
