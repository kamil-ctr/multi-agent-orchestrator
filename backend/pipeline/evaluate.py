"""Stage 4 — Multi-Dimensional Evaluation Engine.

Every response is first scored by a deterministic, dependency-free heuristic
(`heuristic_score`) so the pipeline can rank responses even with zero
network access. If a judge agent is available, `llm_judge_refine` asks it to
review the responses and override the heuristic numbers with its own
judgement — the heuristic result is always the safety net, never a
placeholder that silently disappears.
"""
from __future__ import annotations

import json
import re
import statistics

from agents.base import BaseAgent
from core.logger import get_logger
from core.schemas import AgentResponse, AgentStatus, EvaluationScore
from pipeline.normalize import CollectionSummary

logger = get_logger(__name__)

_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "to", "of",
    "and", "in", "on", "for", "with", "that", "this", "it", "as", "at", "by",
    "or", "but", "if", "so", "do", "does", "did", "can", "could", "should",
    "would", "will", "shall", "i", "you", "he", "she", "we", "they", "them",
    "what", "which", "who", "how", "why", "when", "where",
}

_WEIGHTS = {"accuracy": 0.30, "relevance": 0.25, "depth": 0.20, "clarity": 0.15, "conciseness": 0.10}


def _words(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9']+", text.lower())


def _significant_words(text: str) -> set[str]:
    return {w for w in _words(text) if w not in _STOPWORDS and len(w) > 2}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def _clip(value: float, lo: float = 0.0, hi: float = 10.0) -> float:
    return max(lo, min(hi, value))


def _score_accuracy(text: str, others: list[str]) -> float:
    """Proxy for factual consistency: agreement with the majority of peer responses."""
    if not others:
        return 6.5  # neutral when there is nothing to cross-check against
    mine = _significant_words(text)
    sims = [_jaccard(mine, _significant_words(o)) for o in others]
    avg_sim = sum(sims) / len(sims)
    return _clip(avg_sim * 10 * 1.6)  # scale up since Jaccard on prose is naturally low


def _score_depth(text: str, others: list[str]) -> float:
    word_count = len(_words(text))
    if not others:
        return _clip(word_count / 25)
    peer_avg = sum(len(_words(o)) for o in others) / len(others) or 1
    relative = word_count / peer_avg
    return _clip(5 + (relative - 1) * 4)


def _score_clarity(text: str) -> float:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    sentences = [s for s in sentences if s]
    if not sentences:
        return 0.0
    words = _words(text)
    avg_sentence_len = len(words) / len(sentences)
    # Sweet spot ~12-22 words/sentence; penalize run-ons and telegraphic fragments.
    if 8 <= avg_sentence_len <= 25:
        length_score = 10.0
    else:
        overshoot = min(avg_sentence_len, 60) - 25 if avg_sentence_len > 25 else 8 - avg_sentence_len
        length_score = _clip(10 - abs(overshoot) * 0.4)
    structure_bonus = 1.5 if re.search(r"(\n\s*[-*\d]|\n#+ )", text) else 0.0
    return _clip(length_score * 0.85 + structure_bonus)


def _score_relevance(query: str, text: str) -> float:
    q_words = _significant_words(query)
    r_words = _significant_words(text)
    overlap = _jaccard(q_words, r_words)
    coverage = len(q_words & r_words) / len(q_words) if q_words else 0.5
    return _clip(overlap * 4 + coverage * 6)


def _score_conciseness(text: str) -> float:
    words = _words(text)
    if not words:
        return 0.0
    unique_ratio = len(set(words)) / len(words)
    length_penalty = 0.0
    if len(words) > 400:
        length_penalty = min(4.0, (len(words) - 400) / 200)
    return _clip(unique_ratio * 10 - length_penalty + 1.5)


def _strengths_weaknesses(scores: dict[str, float]) -> tuple[str, str]:
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    top = [k for k, v in ranked[:2] if v >= 6.5]
    bottom = [k for k, v in ranked[-2:] if v < 6.0]
    strengths = f"Strong {', '.join(top)}" if top else "No standout dimension"
    weaknesses = f"Weak {', '.join(bottom)}" if bottom else "No notable weaknesses"
    return strengths, weaknesses


def heuristic_score(query: str, response: AgentResponse, all_responses: list[AgentResponse]) -> EvaluationScore:
    """Score one response on 5 dimensions using deterministic, offline heuristics.

    No network call, no LLM — pure text analysis (word overlap, sentence
    length distribution, lexical diversity). This is the always-available
    baseline every response gets; llm_judge_refine may override these
    numbers afterward if a judge agent is configured and available.

    Args:
        query: The (possibly expanded) prompt the response is answering.
        response: The response to score. Must have status SUCCESS with
            non-empty response_text for a meaningful score.
        all_responses: Every response collected for this query (including
            `response` itself) — used to compute peer-consensus signals
            like accuracy and relative depth. `response.agent` is excluded
            from its own peer set automatically.

    Returns:
        An EvaluationScore with all 5 dimensions plus a weighted `overall`
        and one-line strengths/weaknesses summaries.
    """
    text = response.response_text or ""
    peer_texts = [
        r.response_text
        for r in all_responses
        if r.agent != response.agent and r.status == AgentStatus.SUCCESS and r.response_text
    ]

    dims = {
        "accuracy": _score_accuracy(text, peer_texts),
        "depth": _score_depth(text, peer_texts),
        "clarity": _score_clarity(text),
        "relevance": _score_relevance(query, text),
        "conciseness": _score_conciseness(text),
    }
    overall = sum(dims[k] * w for k, w in _WEIGHTS.items())
    strengths, weaknesses = _strengths_weaknesses(dims)

    return EvaluationScore(
        agent=response.agent,
        accuracy=round(dims["accuracy"], 2),
        depth=round(dims["depth"], 2),
        clarity=round(dims["clarity"], 2),
        relevance=round(dims["relevance"], 2),
        conciseness=round(dims["conciseness"], 2),
        overall=round(overall, 2),
        strengths=strengths,
        weaknesses=weaknesses,
    )


def score_all_heuristic(query: str, responses: list[AgentResponse]) -> list[EvaluationScore]:
    """Run heuristic_score over every successful response in a batch.

    Failed/timed-out/disabled responses are silently excluded — there's
    nothing to score without response text.

    Args:
        query: The (possibly expanded) prompt every response is answering.
        responses: All AgentResponse objects collected for this query.

    Returns:
        One EvaluationScore per successful response, unranked (see `rank`).
    """
    successful = [r for r in responses if r.status == AgentStatus.SUCCESS and r.response_text]
    return [heuristic_score(query, r, successful) for r in successful]


_JUDGE_PROMPT_TEMPLATE = """You are an impartial evaluator comparing answers from several AI models to the same query.

Query: {query}

Responses:
{responses_block}

Score EACH response on a 0-10 scale for these dimensions:
- accuracy: factual correctness / consistency with the other responses
- depth: information density and completeness
- clarity: readability and structure
- relevance: how directly it addresses the query
- conciseness: signal-to-noise ratio (not just short — no padding)

Also give a one-line "strengths" and one-line "weaknesses" per response.

Respond with ONLY a JSON object, no prose, no markdown fences, in this exact shape:
{{"agent_name": {{"accuracy": 0, "depth": 0, "clarity": 0, "relevance": 0, "conciseness": 0, "strengths": "...", "weaknesses": "..."}}, ...}}
"""


def _build_judge_prompt(query: str, responses: list[AgentResponse]) -> str:
    blocks = []
    for r in responses:
        text = (r.response_text or "")[:2000]
        blocks.append(f"### {r.agent}\n{text}")
    return _JUDGE_PROMPT_TEMPLATE.format(query=query, responses_block="\n\n".join(blocks))


def _extract_json(text: str) -> dict | None:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


async def llm_judge_refine(
    query: str,
    responses: list[AgentResponse],
    heuristic_scores: list[EvaluationScore],
    judge: BaseAgent | None,
) -> tuple[list[EvaluationScore], str]:
    """Ask a judge LLM to review and override the heuristic scores, if possible.

    Requires a configured, available judge agent AND at least 2 successful
    responses to cross-compare — with only one response there's nothing for
    a judge to differentiate. Falls back to the heuristic scores unchanged
    on any failure mode: no judge, judge call fails, or judge output isn't
    parseable JSON. Per-agent, if the judge's output is malformed for that
    specific agent, that agent's heuristic score is kept while others are
    still refined — one bad entry doesn't discard the whole batch.

    Args:
        query: The (possibly expanded) prompt every response is answering.
        responses: All AgentResponse objects collected for this query.
        heuristic_scores: The pre-computed heuristic scores to refine (or
            fall back to).
        judge: The agent to use as judge, or None to skip straight to the
            heuristic fallback.

    Returns:
        A (scores, evaluator_used) tuple. evaluator_used is the literal
        string "heuristic" on any fallback path, or f"llm:{judge.name}"
        when the judge's refinement was actually used.
    """
    successful = [r for r in responses if r.status == AgentStatus.SUCCESS and r.response_text]
    if judge is None or not judge.is_available or len(successful) < 2:
        return heuristic_scores, "heuristic"

    prompt = _build_judge_prompt(query, successful)
    judge_response = await judge.generate(prompt)
    if judge_response.status != AgentStatus.SUCCESS or not judge_response.response_text:
        logger.info("Judge agent unavailable/failed, keeping heuristic scores")
        return heuristic_scores, "heuristic"

    parsed = _extract_json(judge_response.response_text)
    if not parsed:
        logger.info("Judge response was not valid JSON, keeping heuristic scores")
        return heuristic_scores, "heuristic"

    refined: list[EvaluationScore] = []
    heuristic_by_agent = {s.agent: s for s in heuristic_scores}
    for r in successful:
        judged = parsed.get(r.agent)
        fallback = heuristic_by_agent.get(r.agent)
        if not isinstance(judged, dict) or fallback is None:
            if fallback:
                refined.append(fallback)
            continue
        try:
            dims = {
                k: _clip(float(judged.get(k, getattr(fallback, k))))
                for k in ("accuracy", "depth", "clarity", "relevance", "conciseness")
            }
        except (TypeError, ValueError):
            refined.append(fallback)
            continue
        overall = sum(dims[k] * w for k, w in _WEIGHTS.items())
        refined.append(
            EvaluationScore(
                agent=r.agent,
                accuracy=round(dims["accuracy"], 2),
                depth=round(dims["depth"], 2),
                clarity=round(dims["clarity"], 2),
                relevance=round(dims["relevance"], 2),
                conciseness=round(dims["conciseness"], 2),
                overall=round(overall, 2),
                strengths=str(judged.get("strengths", fallback.strengths))[:200],
                weaknesses=str(judged.get("weaknesses", fallback.weaknesses))[:200],
            )
        )

    if not refined:
        return heuristic_scores, "heuristic"
    return refined, f"llm:{judge.name}"


def compute_confidence(evaluations: list[EvaluationScore], summary: CollectionSummary) -> float:
    """Compute an overall confidence percentage for the synthesized answer.

    Combines three signals: the top individual score (50% weight), how much
    agents agreed with each other via inverse score variance (30% weight),
    and the fraction of dispatched agents that succeeded at all (20%
    weight) — a single great response from an agent that mostly failed to
    dispatch should score lower confidence than the same response backed by
    a full, converging field.

    Args:
        evaluations: Scores for the responses that were actually evaluated
            (see score_all_heuristic / llm_judge_refine).
        summary: The CollectionSummary for the same query, used for the
            success-rate term.

    Returns:
        A confidence percentage in [0, 100], rounded to 1 decimal place.
        0.0 when there are no evaluations at all.
    """
    if not evaluations:
        return 0.0
    scores = [e.overall for e in evaluations]
    top = max(scores)
    variance = statistics.pvariance(scores) if len(scores) > 1 else 0.0
    agreement = max(0.0, 1 - variance / 10)
    success_rate = (summary.succeeded / summary.total) if summary.total else 0.0

    confidence = (top / 10) * 50 + agreement * 30 + success_rate * 20
    return round(_clip(confidence, 0.0, 100.0), 1)


def rank(evaluations: list[EvaluationScore]) -> list[EvaluationScore]:
    """Sort evaluations by overall score, best first.

    Args:
        evaluations: Unranked EvaluationScore objects.

    Returns:
        A new list sorted by `overall` descending (does not mutate the input).
    """
    return sorted(evaluations, key=lambda e: e.overall, reverse=True)
