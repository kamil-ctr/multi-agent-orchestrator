from __future__ import annotations

import pytest

from core.config import AppConfig
from core.schemas import AgentStatus
from pipeline.dispatch import dispatch_streaming_tokens
from pipeline.orchestrator import Orchestrator


@pytest.mark.asyncio
async def test_generate_stream_yields_tokens_then_done(fake_agent_factory):
    agent = fake_agent_factory("a", text="hello there world")

    tokens = []
    final = None
    async for kind, payload in agent.generate_stream("prompt"):
        if kind == "token":
            tokens.append(payload)
        else:
            final = (kind, payload)

    assert len(tokens) > 1
    assert "".join(tokens) == "hello there world"
    assert final[0] == "done"
    assert final[1].status == AgentStatus.SUCCESS
    assert final[1].response_text == "hello there world"


@pytest.mark.asyncio
async def test_generate_stream_failure_before_any_token(fake_agent_factory):
    agent = fake_agent_factory("broken", should_fail=True)

    events = [item async for item in agent.generate_stream("prompt")]

    assert len(events) == 1
    kind, payload = events[0]
    assert kind == "error"
    assert payload.status == AgentStatus.ERROR
    assert payload.response_text is None


@pytest.mark.asyncio
async def test_generate_stream_mid_stream_failure_finalizes_with_partial_text(fake_agent_factory):
    agent = fake_agent_factory("flaky", text="one two three four", fail_after_tokens=2)

    tokens = []
    final = None
    async for kind, payload in agent.generate_stream("prompt"):
        if kind == "token":
            tokens.append(payload)
        else:
            final = (kind, payload)

    assert "".join(tokens) == "one two"
    assert final[0] == "error"
    assert final[1].status == AgentStatus.ERROR
    assert final[1].response_text == "one two"


@pytest.mark.asyncio
async def test_dispatch_streaming_tokens_relays_tokens_and_results(fake_agent_factory):
    a = fake_agent_factory("a", text="fast reply")
    b = fake_agent_factory("b", text="slower reply here")

    received_tokens: list[tuple[str, str]] = []

    def on_token(agent_name: str, token: str) -> None:
        received_tokens.append((agent_name, token))

    results = []
    async for result in dispatch_streaming_tokens([a, b], lambda agent: ("prompt", None), on_token=on_token):
        results.append(result)

    assert {r.agent for r in results} == {"a", "b"}
    assert all(r.status == AgentStatus.SUCCESS for r in results)
    assert {name for name, _ in received_tokens} == {"a", "b"}
    by_agent_text = {}
    for name, tok in received_tokens:
        by_agent_text[name] = by_agent_text.get(name, "") + tok
    assert by_agent_text["a"] == "fast reply"
    assert by_agent_text["b"] == "slower reply here"


@pytest.mark.asyncio
async def test_run_streaming_emits_agent_token_events_by_default(tmp_path, fake_agent_factory):
    config = AppConfig(agents={}, judge_agent="a", data_dir=tmp_path, top_n_for_synthesis=1)
    orch = Orchestrator(config)
    a = fake_agent_factory("a", text="hi there")
    orch.agents = [a]
    orch.agents_by_name = {"a": a}

    events = []
    await orch.run_streaming("hello", use_cache=False, on_event=events.append)

    token_events = [e for e in events if e["type"] == "agent_token"]
    assert token_events
    assert "".join(e["token"] for e in token_events) == "hi there"


@pytest.mark.asyncio
async def test_run_streaming_respects_streaming_disabled_flag(tmp_path, fake_agent_factory):
    config = AppConfig(
        agents={}, judge_agent="a", data_dir=tmp_path, top_n_for_synthesis=1, streaming_enabled=False
    )
    orch = Orchestrator(config)
    a = fake_agent_factory("a", text="hi there")
    orch.agents = [a]
    orch.agents_by_name = {"a": a}

    events = []
    result = await orch.run_streaming("hello", use_cache=False, on_event=events.append)

    assert not any(e["type"] == "agent_token" for e in events)
    assert any(e["type"] == "agent_done" for e in events)
    assert result.synthesized_answer
