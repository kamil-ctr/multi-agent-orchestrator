from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx
import pytest

from agents.base import BaseAgent
from core.config import AgentConfig

os.environ.setdefault("FAKE_KEY", "test-key")


class FakeAgent(BaseAgent):
    """A test double that skips the network entirely and returns a fixed
    response, error, or hangs (to exercise timeout handling)."""

    def __init__(self, name: str, text: str = "", should_fail: bool = False, hang: bool = False):
        cfg = AgentConfig(
            name=name,
            enabled=True,
            model="fake-model",
            api_key_env="FAKE_KEY",
            timeout_s=0.2,
            max_retries=0,
        )
        super().__init__(cfg)
        self.name = name
        self._text = text
        self._should_fail = should_fail
        self._hang = hang

    async def _call_api(self, client: httpx.AsyncClient, prompt: str, image=None) -> str:
        import asyncio

        if self._hang:
            await asyncio.sleep(10)
        if self._should_fail:
            raise RuntimeError("simulated failure")
        return self._text


@pytest.fixture
def fake_agent_factory():
    def _make(name: str, text: str = "sample response text", should_fail: bool = False, hang: bool = False):
        agent = FakeAgent(name, text=text, should_fail=should_fail, hang=hang)
        return agent

    return _make
