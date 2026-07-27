"""POST /api/query kicks off a pipeline run as a background task and returns
immediately with a query_id; GET /api/query/{id}/stream replays its lifecycle
events (agent_start/agent_done/agent_error/synthesis_done) as SSE.

Events are stored in an in-memory, append-only list per job rather than
handed out through a single-consumer queue, so a client that connects late
(or reconnects) always gets the full event history replayed from the start —
important since EventSource auto-reconnects on any hiccup.
"""
from __future__ import annotations

import asyncio
import json
import time
import uuid
from collections import OrderedDict

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from core.logger import get_logger
from core.schemas import ImageInput

logger = get_logger(__name__)
router = APIRouter()

_MAX_JOBS = 200
_POLL_INTERVAL_S = 0.05


class QueryJob:
    def __init__(self, query_id: str) -> None:
        self.query_id = query_id
        self.events: list[dict] = []
        self.done = False
        self.created_at = time.time()


JOBS: "OrderedDict[str, QueryJob]" = OrderedDict()


def _register_job(job: QueryJob) -> None:
    JOBS[job.query_id] = job
    while len(JOBS) > _MAX_JOBS:
        JOBS.popitem(last=False)


class QueryRequest(BaseModel):
    prompt: str
    image_base64: str | None = None
    image_mime: str | None = None
    file_context: str | None = None
    file_name: str | None = None
    use_cache: bool = True
    enabled_agents: list[str] | None = None


class QueryAck(BaseModel):
    query_id: str


@router.post("/query", response_model=QueryAck)
async def create_query(req: QueryRequest, request: Request) -> QueryAck:
    if not req.prompt or not req.prompt.strip():
        raise HTTPException(400, "prompt must not be empty")

    orch = request.app.state.orchestrator
    if not any(orch.availability().values()):
        raise HTTPException(503, "No agents are available — add at least one API key to .env")

    query_id = uuid.uuid4().hex
    job = QueryJob(query_id)
    _register_job(job)

    image = None
    if req.image_base64 and req.image_mime:
        image = ImageInput(mime_type=req.image_mime, data_base64=req.image_base64)

    async def run_job() -> None:
        def on_event(evt: dict) -> None:
            job.events.append(evt)

        try:
            await orch.run_streaming(
                req.prompt,
                image=image,
                file_context=req.file_context,
                use_cache=req.use_cache,
                enabled_agents=req.enabled_agents,
                on_event=on_event,
            )
        except Exception as e:  # noqa: BLE001 — must reach the client as an event, never crash the server
            logger.exception("query %s failed", query_id)
            job.events.append({"type": "fatal_error", "error": str(e)})
        finally:
            job.done = True

    asyncio.create_task(run_job())
    return QueryAck(query_id=query_id)


def _sse_format(event: dict) -> str:
    event_type = event.get("type", "message")
    return f"event: {event_type}\ndata: {json.dumps(event)}\n\n"


@router.get("/query/{query_id}/stream")
async def stream_query(query_id: str) -> StreamingResponse:
    job = JOBS.get(query_id)
    if job is None:
        raise HTTPException(404, "unknown query_id (it may have expired)")

    _TERMINAL_TYPES = {"synthesis_done", "fatal_error"}

    async def event_gen():
        idx = 0
        while True:
            if idx < len(job.events):
                item = job.events[idx]
                idx += 1
                yield _sse_format(item)
                if item.get("type") in _TERMINAL_TYPES:
                    return
            elif job.done:
                return
            else:
                await asyncio.sleep(_POLL_INTERVAL_S)

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )
