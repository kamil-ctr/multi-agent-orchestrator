"""Stage 3 — Response Collection & Normalization.

Agent adapters already emit the common AgentResponse schema; this stage
finalizes it (zeroing missing fields, computing aggregate stats) so later
stages can treat every response uniformly regardless of success/failure.
"""
from __future__ import annotations

from dataclasses import dataclass

from core.schemas import AgentResponse, AgentStatus


@dataclass
class CollectionSummary:
    total: int
    succeeded: int
    failed_agents: list[str]
    disabled_agents: list[str]
    total_latency_ms: float
    total_tokens: int


def normalize_responses(responses: list[AgentResponse]) -> list[AgentResponse]:
    """Fill in safe defaults on non-successful responses for uniform downstream handling.

    Agent adapters already return the common AgentResponse shape, so this is
    mostly a defensive pass: any non-SUCCESS response gets response_text
    coerced to None and token_count_estimate coerced to 0, so later stages
    never have to special-case missing fields.

    Args:
        responses: Raw AgentResponse objects from the dispatch stage.

    Returns:
        The same list, mutated in place and returned for chaining.
    """
    normalized = []
    for r in responses:
        if r.status != AgentStatus.SUCCESS:
            r.response_text = r.response_text or None
            r.token_count_estimate = r.token_count_estimate or 0
        normalized.append(r)
    return normalized


def summarize(responses: list[AgentResponse]) -> CollectionSummary:
    """Compute aggregate stats across a batch of agent responses.

    Args:
        responses: Normalized AgentResponse objects for one query.

    Returns:
        A CollectionSummary with success/failure/disabled counts, wall-clock
        latency (the max across agents, since dispatch runs concurrently —
        not the sum), and total estimated token usage.
    """
    succeeded = [r for r in responses if r.status == AgentStatus.SUCCESS]
    failed = [r.agent for r in responses if r.status in (AgentStatus.ERROR, AgentStatus.TIMEOUT, AgentStatus.RATE_LIMITED)]
    disabled = [r.agent for r in responses if r.status == AgentStatus.DISABLED]
    return CollectionSummary(
        total=len(responses),
        succeeded=len(succeeded),
        failed_agents=failed,
        disabled_agents=disabled,
        total_latency_ms=max((r.latency_ms or 0.0) for r in responses) if responses else 0.0,
        total_tokens=sum(r.token_count_estimate or 0 for r in responses),
    )
