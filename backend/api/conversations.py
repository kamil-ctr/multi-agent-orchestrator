"""Multi-turn conversation endpoints.

POST /conversations/{id}/messages is the primary way to run the pipeline
going forward — it persists both sides of the turn (core.conversations),
passes recent conversation history as context to the agents, and (on the
first turn) kicks off async title generation. It reuses the same
query_id/SSE-stream mechanism as the legacy /api/query endpoint
(core.jobs) — GET /api/query/{query_id}/stream works identically either way.
"""
from __future__ import annotations

import asyncio
import json
import uuid

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from core.jobs import QueryJob, register_job
from core.logger import get_logger
from core.schemas import AgentStatus, ImageInput

logger = get_logger(__name__)
router = APIRouter()


class ConversationCreate(BaseModel):
    title: str | None = None


class RenameRequest(BaseModel):
    title: str


class MessageRequest(BaseModel):
    prompt: str
    image_base64: str | None = None
    image_mime: str | None = None
    file_context: str | None = None
    file_name: str | None = None
    use_cache: bool = True
    enabled_agents: list[str] | None = None


async def generate_title(orch, conv_store, conversation_id: int, first_message: str) -> None:
    """Best-effort async title generation — never raises, falls back to a
    truncated version of the first message if no judge agent is available
    or the call fails."""
    fallback = first_message.strip().replace("\n", " ")[:60]
    title = fallback
    try:
        judge = orch.agents_by_name.get("gemini") or next((a for a in orch.agents if a.is_available), None)
        if judge and judge.is_available:
            prompt = (
                "Summarize the following user message as a short, single-line "
                "conversation title, under 8 words, with no quotes and no "
                f"trailing punctuation:\n\n{first_message}"
            )
            resp = await judge.generate(prompt)
            if resp.status == AgentStatus.SUCCESS and resp.response_text:
                candidate = resp.response_text.strip().strip('"').strip("'").strip()
                if candidate:
                    title = candidate[:80]
    except Exception:  # noqa: BLE001 - titling is cosmetic, never break the conversation
        logger.exception("title generation failed for conversation %s", conversation_id)
    conv_store.rename(conversation_id, title)


@router.post("/conversations")
async def create_conversation(body: ConversationCreate, request: Request) -> dict:
    store = request.app.state.orchestrator.conversations
    conversation_id = store.create(title=body.title)
    return store.get_meta(conversation_id)


@router.get("/conversations")
async def list_conversations(
    request: Request, page: int = 1, page_size: int = 20, search: str | None = None
) -> dict:
    page = max(1, page)
    page_size = max(1, min(100, page_size))
    store = request.app.state.orchestrator.conversations
    total = store.count(search=search)
    items = store.list(page=page, page_size=page_size, search=search)
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": max(1, (total + page_size - 1) // page_size),
        "items": items,
    }


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: int, request: Request) -> dict:
    store = request.app.state.orchestrator.conversations
    conv = store.get(conversation_id)
    if conv is None:
        raise HTTPException(404, f"No conversation with id {conversation_id}")
    return conv


@router.patch("/conversations/{conversation_id}")
async def rename_conversation(conversation_id: int, body: RenameRequest, request: Request) -> dict:
    store = request.app.state.orchestrator.conversations
    if not store.exists(conversation_id):
        raise HTTPException(404, f"No conversation with id {conversation_id}")
    title = body.title.strip()
    if not title:
        raise HTTPException(400, "title must not be empty")
    store.rename(conversation_id, title[:200])
    return store.get_meta(conversation_id)


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: int, request: Request) -> dict:
    store = request.app.state.orchestrator.conversations
    if not store.exists(conversation_id):
        raise HTTPException(404, f"No conversation with id {conversation_id}")
    store.delete(conversation_id)
    return {"status": "deleted"}


@router.post("/conversations/{conversation_id}/messages")
async def send_message(conversation_id: int, req: MessageRequest, request: Request) -> dict:
    orch = request.app.state.orchestrator
    store = orch.conversations
    if not store.exists(conversation_id):
        raise HTTPException(404, f"No conversation with id {conversation_id}")
    if not req.prompt or not req.prompt.strip():
        raise HTTPException(400, "prompt must not be empty")
    if not any(orch.availability().values()):
        raise HTTPException(503, "No agents are available — add at least one API key to .env")

    query_id = uuid.uuid4().hex
    job = QueryJob(query_id)
    register_job(job)

    store.add_message(conversation_id, role="user", content=req.prompt)
    is_first_turn = store.message_count(conversation_id) == 1
    context = store.build_context(
        conversation_id,
        max_messages=orch.config.conversation_context_messages,
        max_tokens=orch.config.conversation_context_max_tokens,
    )

    image = None
    if req.image_base64 and req.image_mime:
        image = ImageInput(mime_type=req.image_mime, data_base64=req.image_base64)

    async def run_job() -> None:
        def on_event(evt: dict) -> None:
            job.events.append(evt)

        try:
            result = await orch.run_streaming(
                req.prompt,
                image=image,
                file_context=req.file_context,
                conversation_context=context,
                use_cache=req.use_cache,
                enabled_agents=req.enabled_agents,
                on_event=on_event,
            )
            store.add_message(
                conversation_id,
                role="assistant",
                content=result.synthesized_answer,
                agent_responses_json=json.dumps(result.to_dict()),
            )
            if is_first_turn:
                asyncio.create_task(generate_title(orch, store, conversation_id, req.prompt))
        except Exception as e:  # noqa: BLE001 — must reach the client as an event, never crash the server
            logger.exception("conversation %s message %s failed", conversation_id, query_id)
            job.events.append({"type": "fatal_error", "error": str(e)})
        finally:
            job.done = True

    asyncio.create_task(run_job())
    return {"query_id": query_id, "conversation_id": conversation_id}
