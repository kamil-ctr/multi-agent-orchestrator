"""Stage 2 — Parallel Dispatch.

Fires every enabled agent concurrently. Per-agent timeout, retry with
exponential backoff, and latency tracking all live inside BaseAgent.generate()
so this stage only needs to fan out and collect — a single agent hanging or
erroring never blocks the others.
"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable

from agents.base import BaseAgent
from core.logger import get_logger
from core.schemas import AgentResponse, ImageInput

logger = get_logger(__name__)


async def dispatch_all(agents: list[BaseAgent], prompt: str) -> list[AgentResponse]:
    """Dispatch prompt to every agent concurrently and wait for all to finish.

    Simple, non-streaming variant used by the CLI's batch path. Every agent's
    own timeout/retry lives inside BaseAgent.generate(), so a hung or failing
    agent surfaces as a TIMEOUT/ERROR AgentResponse rather than raising here
    or blocking the others.

    Args:
        agents: The agents to dispatch to (already filtered to whichever
            subset should run for this query).
        prompt: The text prompt sent to every agent.

    Returns:
        One AgentResponse per agent, in the order asyncio.gather resolves
        them (not necessarily agents' input order).
    """
    if not agents:
        return []
    results = await asyncio.gather(*(agent.generate(prompt) for agent in agents))
    return list(results)


async def dispatch_streaming(
    agents: list[BaseAgent],
    prompt: str,
    on_result: Callable[[AgentResponse], None] | None = None,
) -> AsyncIterator[AgentResponse]:
    """Dispatch prompt to every agent concurrently, yielding each result as it lands.

    Used where the caller wants to react to each agent finishing individually
    (e.g. push a live UI update) rather than waiting for the full batch.

    Args:
        agents: The agents to dispatch to.
        prompt: The text prompt sent to every agent.
        on_result: Optional callback invoked synchronously with each
            AgentResponse the moment it's available, before it's yielded.

    Yields:
        AgentResponse objects in completion order (fastest agent first).
    """
    if not agents:
        return

    tasks = {asyncio.create_task(agent.generate(prompt)): agent.name for agent in agents}
    for coro in asyncio.as_completed(tasks):
        result = await coro
        logger.info("%s finished: %s (%.0fms)", result.agent, result.status.value, result.latency_ms or 0)
        if on_result:
            on_result(result)
        yield result


async def dispatch_streaming_tokens(
    agents: list[BaseAgent],
    prompt_selector: Callable[[BaseAgent], tuple[str, ImageInput | None]],
    on_token: Callable[[str, str], None] | None = None,
    on_result: Callable[[AgentResponse], None] | None = None,
) -> AsyncIterator[AgentResponse]:
    """Dispatch prompt to every agent concurrently via token-by-token streaming.

    Each agent's tokens are relayed live via `on_token` the instant they
    arrive from `BaseAgent.generate_stream()`; every agent's finalized
    AgentResponse is relayed via `on_result`/yielded once its stream ends
    (success or failure), same contract as dispatch_streaming_mm. Multiple
    agents' concurrent token streams are fanned into a single ordered-by-
    arrival queue so one agent's tokens are never blocked waiting on another.

    Args:
        agents: The agents to dispatch to.
        prompt_selector: Called once per agent to produce that agent's
            (prompt_text, image_or_none) pair (see dispatch_streaming_mm).
        on_token: Optional callback invoked with (agent_name, token_text)
            for every text delta as it arrives.
        on_result: Optional callback invoked synchronously with each
            AgentResponse the moment its stream finishes.

    Yields:
        AgentResponse objects in completion order (fastest agent first).
    """
    if not agents:
        return

    queue: asyncio.Queue = asyncio.Queue()
    _DONE = object()

    async def run_agent(agent: BaseAgent) -> None:
        text, image = prompt_selector(agent)
        async for kind, payload in agent.generate_stream(text, image):
            await queue.put((kind, agent.name, payload))

    async def run_all() -> None:
        await asyncio.gather(*(run_agent(a) for a in agents))
        await queue.put(_DONE)

    runner = asyncio.create_task(run_all())

    while True:
        item = await queue.get()
        if item is _DONE:
            break
        kind, agent_name, payload = item
        if kind == "token":
            if on_token:
                on_token(agent_name, payload)
            continue
        result: AgentResponse = payload
        logger.info("%s finished: %s (%.0fms)", result.agent, result.status.value, result.latency_ms or 0)
        if on_result:
            on_result(result)
        yield result

    await runner


async def dispatch_streaming_mm(
    agents: list[BaseAgent],
    prompt_selector: Callable[[BaseAgent], tuple[str, ImageInput | None]],
    on_result: Callable[[AgentResponse], None] | None = None,
) -> AsyncIterator[AgentResponse]:
    """Multimodal variant of dispatch_streaming: each agent gets its own (text, image) pair.

    Vision-capable agents receive the image directly; everyone else gets a
    text-only variant (typically with an image description substituted in
    by the orchestrator) via the same prompt_selector callback.

    Args:
        agents: The agents to dispatch to.
        prompt_selector: Called once per agent to produce that agent's
            (prompt_text, image_or_none) pair — lets vision- and non-vision
            agents receive different inputs for the same logical query.
        on_result: Optional callback invoked synchronously with each
            AgentResponse the moment it's available, before it's yielded.

    Yields:
        AgentResponse objects in completion order (fastest agent first).
    """
    if not agents:
        return

    tasks = {}
    for agent in agents:
        text, image = prompt_selector(agent)
        tasks[asyncio.create_task(agent.generate(text, image))] = agent.name

    for coro in asyncio.as_completed(tasks):
        result = await coro
        logger.info("%s finished: %s (%.0fms)", result.agent, result.status.value, result.latency_ms or 0)
        if on_result:
            on_result(result)
        yield result
