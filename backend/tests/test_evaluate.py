from __future__ import annotations

from core.schemas import AgentResponse, AgentStatus
from pipeline.evaluate import compute_confidence, heuristic_score, rank, score_all_heuristic
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
