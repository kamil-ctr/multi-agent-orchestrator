from __future__ import annotations

import pytest

from core.schemas import AgentResponse, AgentStatus
from pipeline.evaluate import (
    _extract_explanation,
    compute_confidence,
    heuristic_score,
    llm_judge_refine,
    rank,
    score_all_heuristic,
)
from pipeline.normalize import summarize


def _resp(agent: str, text: str, status=AgentStatus.SUCCESS) -> AgentResponse:
    return AgentResponse(agent=agent, status=status, response_text=text, latency_ms=100.0, token_count_estimate=len(text.split()))


def test_heuristic_score_relevance_rewards_query_overlap():
    query = "What is the capital of France?"
    on_topic = _resp("a", "The capital of France is Paris, a major European city.")
    off_topic = _resp("b", "Bananas are a good source of potassium and fiber.")

    score_on = heuristic_score(query, on_topic, [on_topic, off_topic])
    score_off = heuristic_score(query, off_topic, [on_topic, off_topic])

    assert score_on.relevance > score_off.relevance


def test_heuristic_score_accuracy_rewards_consensus():
    query = "Who wrote Hamlet?"
    r1 = _resp("a", "William Shakespeare wrote Hamlet in the early 1600s.")
    r2 = _resp("b", "Hamlet was written by William Shakespeare.")
    r3 = _resp("c", "The moon is made of cheese and rocks.")

    responses = [r1, r2, r3]
    s1 = heuristic_score(query, r1, responses)
    s3 = heuristic_score(query, r3, responses)

    assert s1.accuracy > s3.accuracy


def test_heuristic_score_conciseness_penalizes_bloat():
    query = "Explain gravity"
    concise = _resp("a", "Gravity is the force that attracts two bodies with mass toward each other.")
    bloated = _resp("b", " ".join(["the the the the the the the the the the"] * 60))

    s_concise = heuristic_score(query, concise, [concise, bloated])
    s_bloated = heuristic_score(query, bloated, [concise, bloated])

    assert s_concise.conciseness > s_bloated.conciseness


def test_score_all_heuristic_skips_failed_responses():
    ok = _resp("a", "a working response with enough words to score")
    failed = AgentResponse(agent="b", status=AgentStatus.ERROR, error="boom")

    scores = score_all_heuristic("test query", [ok, failed])

    assert len(scores) == 1
    assert scores[0].agent == "a"


def test_rank_orders_by_overall_descending():
    query = "test"
    r1 = _resp("low", "short")
    r2 = _resp("high", "a much more detailed and directly relevant answer about the test query at hand")
    scores = score_all_heuristic(query, [r1, r2])

    ranked = rank(scores)

    assert ranked[0].overall >= ranked[-1].overall


def test_compute_confidence_zero_when_no_evaluations():
    summary = summarize([])
    assert compute_confidence([], summary) == 0.0


def test_compute_confidence_higher_with_more_successes_and_agreement():
    responses_ok = [_resp("a", "text one"), _resp("b", "text two")]
    responses_partial = [_resp("a", "text one"), AgentResponse(agent="b", status=AgentStatus.TIMEOUT)]

    scores_ok = score_all_heuristic("q", responses_ok)
    scores_partial = score_all_heuristic("q", [responses_partial[0]])

    conf_ok = compute_confidence(scores_ok, summarize(responses_ok))
    conf_partial = compute_confidence(scores_partial, summarize(responses_partial))

    assert conf_ok >= conf_partial


def test_extract_explanation_valid():
    parsed = {"_explanation": {"summary": "Groq was more concise.", "key_differentiators": ["shorter", "on-topic"]}}
    explanation = _extract_explanation(parsed)

    assert explanation is not None
    assert explanation.summary == "Groq was more concise."
    assert explanation.key_differentiators == ["shorter", "on-topic"]


def test_extract_explanation_missing_field_returns_none():
    assert _extract_explanation({}) is None


def test_extract_explanation_malformed_returns_none():
    assert _extract_explanation({"_explanation": "not a dict"}) is None
    assert _extract_explanation({"_explanation": {"summary": ""}}) is None
    assert _extract_explanation({"_explanation": {"summary": "   "}}) is None


def test_extract_explanation_filters_non_string_differentiators_and_caps_length():
    parsed = {
        "_explanation": {
            "summary": "ok",
            "key_differentiators": ["a", 123, None, "b", "c", "d", "e", "f", "g"],
        }
    }
    explanation = _extract_explanation(parsed)

    assert explanation.key_differentiators == ["a", "123", "b", "c", "d", "e"]  # None dropped, capped at 6


@pytest.mark.asyncio
async def test_llm_judge_refine_returns_none_explanation_without_judge():
    scores = score_all_heuristic("q", [_resp("a", "answer one"), _resp("b", "answer two")])
    responses = [_resp("a", "answer one"), _resp("b", "answer two")]

    refined, evaluator_used, explanation = await llm_judge_refine("q", responses, scores, None)

    assert evaluator_used == "heuristic"
    assert explanation is None
    assert refined == scores


@pytest.mark.asyncio
async def test_llm_judge_refine_extracts_explanation_from_judge_output(fake_agent_factory):
    import json

    judge_output = json.dumps(
        {
            "a": {"accuracy": 8, "depth": 7, "clarity": 8, "relevance": 8, "conciseness": 8, "strengths": "clear", "weaknesses": "none"},
            "b": {"accuracy": 5, "depth": 5, "clarity": 5, "relevance": 5, "conciseness": 5, "strengths": "ok", "weaknesses": "vague"},
            "_explanation": {
                "summary": "Agent a was prioritized for its precise, verifiable claim.",
                "key_differentiators": ["a cited a specific fact", "b was vague"],
            },
        }
    )
    judge = fake_agent_factory("judge", text=judge_output)
    responses = [_resp("a", "answer one"), _resp("b", "answer two")]
    heuristic_scores = score_all_heuristic("q", responses)

    refined, evaluator_used, explanation = await llm_judge_refine("q", responses, heuristic_scores, judge)

    assert evaluator_used == "llm:judge"
    assert explanation is not None
    assert "prioritized" in explanation.summary
    assert len(explanation.key_differentiators) == 2
