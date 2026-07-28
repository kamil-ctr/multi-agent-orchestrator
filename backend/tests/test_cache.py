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


def test_get_semantic_returns_none_without_any_embeddings_stored(tmp_path):
    cache = ResponseCache(tmp_path / "cache.sqlite", ttl_seconds=3600)
    cache.set("what is 2+2", _make_result("what is 2+2"))  # no embedding

    result, sim = cache.get_semantic([1.0, 0.0, 0.0], threshold=0.9)

    assert result is None
    assert sim is None


def test_get_semantic_hits_above_threshold(tmp_path):
    cache = ResponseCache(tmp_path / "cache.sqlite", ttl_seconds=3600)
    cache.set("what is 2+2", _make_result("what is 2+2"), embedding=[1.0, 0.0, 0.0])

    result, sim = cache.get_semantic([0.99, 0.01, 0.0], threshold=0.9)

    assert result is not None
    assert result.cached is True
    assert sim > 0.9


def test_get_semantic_misses_below_threshold(tmp_path):
    cache = ResponseCache(tmp_path / "cache.sqlite", ttl_seconds=3600)
    cache.set("what is 2+2", _make_result("what is 2+2"), embedding=[1.0, 0.0, 0.0])

    result, sim = cache.get_semantic([0.0, 1.0, 0.0], threshold=0.9)

    assert result is None
    assert sim is None


def test_get_semantic_scoped_to_conversation_id(tmp_path):
    cache = ResponseCache(tmp_path / "cache.sqlite", ttl_seconds=3600)
    cache.set("what is 2+2", _make_result("conv A answer"), embedding=[1.0, 0.0, 0.0], conversation_id=1)
    cache.set("what is 2+2", _make_result("conv B answer"), embedding=[1.0, 0.0, 0.0], conversation_id=2)

    result_a, _ = cache.get_semantic([1.0, 0.0, 0.0], threshold=0.9, conversation_id=1)
    result_b, _ = cache.get_semantic([1.0, 0.0, 0.0], threshold=0.9, conversation_id=2)
    result_standalone, _ = cache.get_semantic([1.0, 0.0, 0.0], threshold=0.9, conversation_id=None)

    assert result_a.query == "conv A answer"
    assert result_b.query == "conv B answer"
    assert result_standalone is None  # neither entry is a standalone (conversation_id IS NULL) entry


def test_identical_prompt_in_different_conversations_does_not_collide(tmp_path):
    """Regression test: entries must be keyed by more than prompt_hash alone,
    since two different conversations can ask the identical literal question
    and legitimately get different correct answers."""
    cache = ResponseCache(tmp_path / "cache.sqlite", ttl_seconds=3600)
    cache.set("what is my favorite color", _make_result("blue"), embedding=[1.0, 0.0], conversation_id=1)
    cache.set("what is my favorite color", _make_result("green"), embedding=[1.0, 0.0], conversation_id=2)

    result_a, _ = cache.get_semantic([1.0, 0.0], threshold=0.9, conversation_id=1)
    result_b, _ = cache.get_semantic([1.0, 0.0], threshold=0.9, conversation_id=2)

    assert result_a.query == "blue"
    assert result_b.query == "green"


def test_exact_get_ignores_conversation_scoped_entries(tmp_path):
    """A conversation-scoped entry must never satisfy a standalone exact lookup."""
    cache = ResponseCache(tmp_path / "cache.sqlite", ttl_seconds=3600)
    cache.set("what is 2+2", _make_result("conv-scoped answer"), conversation_id=5)

    assert cache.get("what is 2+2") is None


def test_standalone_set_dedupes_in_place(tmp_path):
    cache = ResponseCache(tmp_path / "cache.sqlite", ttl_seconds=3600)
    cache.set("what is 2+2", _make_result("first answer"))
    cache.set("what is 2+2", _make_result("second answer"))

    hit = cache.get("what is 2+2")
    assert hit.query == "second answer"
