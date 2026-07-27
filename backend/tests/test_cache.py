from __future__ import annotations

import time

from core.cache import ResponseCache
from core.schemas import AgentResponse, AgentStatus, PipelineResult


def _make_result(query: str) -> PipelineResult:
    return PipelineResult(
        query=query,
        query_type="factual",
        expanded_query=query,
        agent_responses=[AgentResponse(agent="a", status=AgentStatus.SUCCESS, response_text="x")],
        evaluations=[],
        synthesized_answer="answer",
        attribution={},
        confidence_score=50.0,
        total_latency_ms=100.0,
        total_tokens_estimate=10,
        estimated_cost_usd=0.0,
    )


def test_cache_miss_returns_none(tmp_path):
    cache = ResponseCache(tmp_path / "cache.sqlite", ttl_seconds=3600)
    assert cache.get("never asked this") is None


def test_cache_set_then_get_roundtrips(tmp_path):
    cache = ResponseCache(tmp_path / "cache.sqlite", ttl_seconds=3600)
    result = _make_result("what is 2+2")

    cache.set("what is 2+2", result)
    hit = cache.get("what is 2+2")

    assert hit is not None
    assert hit.synthesized_answer == "answer"
    assert hit.cached is True


def test_cache_is_case_and_whitespace_insensitive(tmp_path):
    cache = ResponseCache(tmp_path / "cache.sqlite", ttl_seconds=3600)
    cache.set("  What Is 2+2  ", _make_result("What Is 2+2"))

    assert cache.get("what is 2+2") is not None


def test_cache_expires_after_ttl(tmp_path):
    cache = ResponseCache(tmp_path / "cache.sqlite", ttl_seconds=0)
    cache.set("expires fast", _make_result("expires fast"))
    time.sleep(0.05)

    assert cache.get("expires fast") is None


def test_cache_invalidate_removes_entry(tmp_path):
    cache = ResponseCache(tmp_path / "cache.sqlite", ttl_seconds=3600)
    cache.set("to be removed", _make_result("to be removed"))
    cache.invalidate("to be removed")

    assert cache.get("to be removed") is None
