"""Stage 5 — Response Synthesis.

Combines the best elements of the top-N scoring responses into one answer,
via a synthesizer agent call. Falls back to returning the single best
response verbatim (clearly labeled) when no agent is available — the
pipeline must still produce something useful offline.
"""
from __future__ import annotations

from agents.base import BaseAgent
from core.logger import get_logger
from core.schemas import AgentResponse, AgentStatus, EvaluationScore
from pipeline.evaluate import rank

logger = get_logger(__name__)

_SYNTHESIS_PROMPT_TEMPLATE = """You are synthesizing a single best answer to a user's query from multiple AI-generated candidate answers, ranked best-first.

Query: {query}

Candidate answers:
{candidates_block}

Write ONE final answer that combines the strongest, most accurate, most complete elements of these candidates. Resolve any contradictions in favor of the majority / most-detailed candidate. Do not mention that you are synthesizing or reference "candidate 1/2/3" in the final answer text itself — just answer the query directly and well.

After the answer, on a new line, add:
ATTRIBUTION: a short JSON object mapping each contributing agent name to a brief note on what it contributed, e.g. {{"gemini": "core explanation", "groq": "code example"}}
"""


def _build_synthesis_prompt(query: str, top: list[tuple[AgentResponse, EvaluationScore]]) -> str:
    blocks = []
    for i, (resp, score) in enumerate(top, start=1):
        blocks.append(f"### Candidate {i} (agent: {resp.agent}, score: {score.overall}/10)\n{resp.response_text}")
    return _SYNTHESIS_PROMPT_TEMPLATE.format(query=query, candidates_block="\n\n".join(blocks))


def _split_answer_and_attribution(raw: str) -> tuple[str, dict[str, str]]:
    import json
    import re

    marker = re.search(r"ATTRIBUTION:\s*(\{.*\})", raw, re.DOTALL)
    if not marker:
        return raw.strip(), {}

    answer = raw[: marker.start()].strip()
    try:
        attribution = json.loads(marker.group(1))
        if not isinstance(attribution, dict):
            attribution = {}
    except json.JSONDecodeError:
        attribution = {}
    return answer, attribution


async def synthesize(
    query: str,
    responses: list[AgentResponse],
    evaluations: list[EvaluationScore],
    synthesizer: BaseAgent | None,
    top_n: int = 3,
) -> tuple[str, dict[str, str]]:
    """Combine the top-N scoring responses into one synthesized answer.

    Degrades gracefully through three tiers: if a synthesizer agent is
    available, it's asked to merge the top_n responses and attribute which
    agent contributed what. If no synthesizer is configured/available, or
    the synthesis call itself fails, the single best-ranked response is
    returned verbatim with a note explaining why. If no agent produced a
    usable response at all, a clear "no usable response" message is
    returned instead of an empty string or an exception.

    Args:
        query: The (possibly expanded) prompt being answered.
        responses: All AgentResponse objects collected for this query.
        evaluations: Scores for those responses (see pipeline.evaluate) —
            used to pick which top_n responses feed the synthesis prompt.
        synthesizer: The agent to use for synthesis (typically the
            configured judge agent), or None to go straight to the
            verbatim-fallback tier.
        top_n: How many top-scoring responses to include as synthesis
            candidates.

    Returns:
        A (synthesized_answer, attribution) tuple. attribution maps agent
        name to a short note on its contribution; it's empty only in the
        all-agents-failed case.
    """
    successful_by_agent = {
        r.agent: r for r in responses if r.status == AgentStatus.SUCCESS and r.response_text
    }
    ranked_evals = rank(evaluations)
    top = [
        (successful_by_agent[e.agent], e)
        for e in ranked_evals[:top_n]
        if e.agent in successful_by_agent
    ]

    if not top:
        return "No agent produced a usable response — all agents were unavailable, timed out, or errored.", {}

    if synthesizer is None or not synthesizer.is_available:
        best_resp, best_score = top[0]
        note = f"\n\n_(Synthesizer agent unavailable — showing top-ranked response from {best_resp.agent} as-is.)_"
        return (best_resp.response_text or "") + note, {best_resp.agent: "full response (no synthesis available)"}

    prompt = _build_synthesis_prompt(query, top)
    synth_response = await synthesizer.generate(prompt)

    if synth_response.status != AgentStatus.SUCCESS or not synth_response.response_text:
        logger.info("Synthesis call failed, falling back to top-ranked response verbatim")
        best_resp, best_score = top[0]
        note = f"\n\n_(Synthesis call failed — showing top-ranked response from {best_resp.agent} as-is.)_"
        return (best_resp.response_text or "") + note, {best_resp.agent: "full response (synthesis failed)"}

    answer, attribution = _split_answer_and_attribution(synth_response.response_text)
    if not attribution:
        attribution = {resp.agent: "contributed to synthesis" for resp, _ in top}
    return answer, attribution
