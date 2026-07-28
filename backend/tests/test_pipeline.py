from __future__ import annotations

import pytest

from core.config import AppConfig
from core.schemas import AgentStatus, QueryType
from pipeline.dispatch import dispatch_all
from pipeline.orchestrator import Orchestrator
from pipeline.preprocess import classify_query_type
from pipeline.synthesize import synthesize
from pipeline.evaluate import score_all_heuristic


@pytest.mark.asyncio
async def test_dispatch_all_collects_results_from_multiple_agents(fake_agent_factory):
    a = fake_agent_factory("agent-a", text="response A")
    b = fake_agent_factory("agent-b", text="response B")

    results = await dispatch_all([a, b], "hello")

    assert {r.agent for r in results} == {"agent-a", "agent-b"}
    assert all(r.status == AgentStatus.SUCCESS for r in results)


@pytest.mark.asyncio
async def test_dispatch_handles_timeout_without_crashing(fake_agent_factory):
    slow = fake_agent_factory("slow", hang=True)
    fast = fake_agent_factory("fast", text="quick answer")

    results = await dispatch_all([slow, fast], "hello")
    by_agent = {r.agent: r for r in results}

    assert by_agent["slow"].status == AgentStatus.TIMEOUT
    assert by_agent["fast"].status == AgentStatus.SUCCESS


@pytest.mark.asyncio
async def test_dispatch_handles_error_without_crashing_other_agents(fake_agent_factory):
    broken = fake_agent_factory("broken", should_fail=True)
    healthy = fake_agent_factory("healthy", text="all good")

    results = await dispatch_all([broken, healthy], "hello")
    by_agent = {r.agent: r for r in results}

    assert by_agent["broken"].status == AgentStatus.ERROR
    assert by_agent["healthy"].status == AgentStatus.SUCCESS


@pytest.mark.parametrize(
    "prompt,expected",
    [
        ("What is the capital of Japan?", QueryType.FACTUAL),
        ("Write a poem about the ocean", QueryType.CREATIVE),
        ("Compare the pros and cons of solar vs wind energy", QueryType.ANALYTICAL),
        ("Write a Python function to reverse a linked list", QueryType.CODING),
        ("Hey, how's it going?", QueryType.CONVERSATIONAL),
    ],
)
def test_classify_query_type(prompt, expected):
    assert classify_query_type(prompt) == expected


@pytest.mark.asyncio
async def test_synthesize_falls_back_to_top_response_without_synthesizer(fake_agent_factory):
    a = fake_agent_factory("a", text="a solid, on-topic and reasonably detailed answer")
    resp = await a.generate("query")
    scores = score_all_heuristic("query", [resp])

    answer, attribution = await synthesize("query", [resp], scores, synthesizer=None)

    assert "solid, on-topic" in answer
    assert attribution


@pytest.mark.asyncio
async def test_orchestrator_end_to_end_with_fake_agents(tmp_path, fake_agent_factory):
    config = AppConfig(
        agents={},
        cache_ttl_seconds=3600,
        judge_agent="a",
        data_dir=tmp_path,
        top_n_for_synthesis=2,
    )
    orch = Orchestrator(config)
    a = fake_agent_factory("a", text="Paris is the capital of France, a country in Europe.")
    b = fake_agent_factory("b", text="France's capital city is Paris.")
    orch.agents = [a, b]
    orch.agents_by_name = {"a": a, "b": b}

    result = await orch.run("What is the capital of France?", use_cache=True)

    assert result.confidence_score > 0
    assert len(result.agent_responses) == 2
    assert result.synthesized_answer
    assert result.cached is False

    cached_result = await orch.run("What is the capital of France?", use_cache=True)
    assert cached_result.cached is True


@pytest.mark.asyncio
async def test_orchestrator_run_streaming_emits_lifecycle_events(tmp_path, fake_agent_factory):
    config = AppConfig(agents={}, judge_agent="a", data_dir=tmp_path, top_n_for_synthesis=2)
    orch = Orchestrator(config)
    a = fake_agent_factory("a", text="Paris is the capital of France, a country in Europe.")
    b = fake_agent_factory("b", text="France's capital city is Paris.")
    orch.agents = [a, b]
    orch.agents_by_name = {"a": a, "b": b}

    events = []
    result = await orch.run_streaming(
        "What is the capital of France?", use_cache=False, on_event=events.append
    )

    types = [e["type"] for e in events]
    assert types.count("agent_start") == 2
    assert types.count("agent_done") == 2
    assert types[-1] == "synthesis_done"
    assert events[-1]["result"]["synthesized_answer"]
    assert result.synthesized_answer


@pytest.mark.asyncio
async def test_orchestrator_run_streaming_with_file_context(tmp_path, fake_agent_factory):
    config = AppConfig(agents={}, judge_agent="a", data_dir=tmp_path, top_n_for_synthesis=1)
    orch = Orchestrator(config)
    a = fake_agent_factory("a", text="The report says revenue grew 10%.")
    orch.agents = [a]
    orch.agents_by_name = {"a": a}

    result = await orch.run_streaming(
        "Summarize this",
        file_context="Q3 revenue grew 10% year over year.",
        use_cache=False,
    )

    assert result.query == "Summarize this"
    assert result.synthesized_answer


@pytest.mark.asyncio
async def test_run_streaming_prepends_conversation_context_to_agent_prompt(tmp_path, fake_agent_factory):
    config = AppConfig(
        agents={}, judge_agent="a", data_dir=tmp_path, top_n_for_synthesis=1, streaming_enabled=False
    )
    orch = Orchestrator(config)
    a = fake_agent_factory("a", echo=True)
    orch.agents = [a]
    orch.agents_by_name = {"a": a}

    result = await orch.run_streaming(
        "What about tomorrow?",
        conversation_context="User: What's the weather today?\nAssistant: It's sunny.",
        use_cache=False,
    )

    agent_prompt = result.agent_responses[0].response_text
    assert "What's the weather today?" in agent_prompt
    assert "It's sunny." in agent_prompt
    assert "What about tomorrow?" in agent_prompt
