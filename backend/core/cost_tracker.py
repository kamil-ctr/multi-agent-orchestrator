"""Token/cost estimation. Most integrated APIs are free-tier (cost 0), but the
estimator still reports token usage and would-be cost so the same code path
works if paid models are swapped in later."""
from __future__ import annotations

from core.config import AgentConfig
from core.schemas import AgentResponse


def estimate_tokens(text: str | None) -> int:
    """Rough token estimate: ~4 characters per token (OpenAI-style heuristic)."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def estimate_cost_usd(
    agent_cfg: AgentConfig | None,
    input_tokens: int,
    output_tokens: int,
) -> float:
    if agent_cfg is None:
        return 0.0
    cost = (input_tokens / 1000) * agent_cfg.price_per_1k_input
    cost += (output_tokens / 1000) * agent_cfg.price_per_1k_output
    return round(cost, 6)


def total_tokens(responses: list[AgentResponse]) -> int:
    return sum(r.token_count_estimate or 0 for r in responses)
