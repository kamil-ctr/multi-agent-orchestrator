"""Abstract base class every agent adapter implements.

To add a new agent: subclass BaseAgent, implement `_call_api`, add a config
block for it in config.yaml, and drop the file in agents/. The registry
auto-discovers it — no other wiring required.
"""
from __future__ import annotations

import asyncio
import random
import time
from abc import ABC, abstractmethod

import httpx

from core.config import AgentConfig
from core.cost_tracker import estimate_tokens
from core.logger import get_logger
from core.schemas import AgentResponse, AgentStatus, ImageInput

logger = get_logger(__name__)

_BACKOFF_BASE_S = 0.6


class BaseAgent(ABC):
    """Common contract every provider adapter implements.

    Subclasses only implement `_call_api` (the actual HTTP request for that
    provider's schema); timeout enforcement, retry with exponential backoff,
    latency tracking, and disabled/missing-key handling all live here in
    `generate()` and are shared by every adapter for free. See
    `agents/registry.py` for how subclasses get discovered and wired up
    automatically from `config.yaml`.
    """

    name: str = "base"
    supports_vision: bool = False

    def __init__(self, config: AgentConfig) -> None:
        """Store this agent's configuration (model, timeout, retries, API key env var, ...)."""
        self.config = config

    @property
    def is_available(self) -> bool:
        """Whether this agent is enabled in config AND has an API key configured.

        Does not verify the key is actually valid — only that dispatch
        should be attempted. An invalid key still surfaces as an ERROR
        AgentResponse from generate(), not a False here.
        """
        return self.config.is_available

    @abstractmethod
    async def _call_api(
        self, client: httpx.AsyncClient, prompt: str, image: ImageInput | None = None
    ) -> str:
        """Perform the actual HTTP call and return the raw response text.

        `image` is only ever non-None for adapters with supports_vision=True —
        the orchestrator never sends an image to an agent that can't use it.
        Must raise on failure (httpx.HTTPStatusError, httpx.RequestError, etc.)
        rather than swallowing errors — retry/backoff is handled by generate().
        """
        raise NotImplementedError

    async def generate(self, prompt: str, image: ImageInput | None = None) -> AgentResponse:
        """Call this agent with retry/backoff/timeout, never raising on failure.

        This is the one method every other part of the codebase calls —
        dispatch, the judge, image description all go through here. Every
        failure mode (disabled, missing key, timeout, rate limit, HTTP
        error, network error, or any unexpected exception from `_call_api`)
        is caught and converted into an AgentResponse with an appropriate
        AgentStatus, so a single bad agent can never raise an exception that
        takes down a concurrent dispatch of several agents.

        Retries use exponential backoff with jitter
        (`_BACKOFF_BASE_S * 2^attempt + random jitter`) up to
        `config.max_retries` times, on every failure type including rate
        limits — there's no separate "don't retry on 429" path, since a
        short backoff is often enough for a rate limit to clear.

        Args:
            prompt: The text prompt to send.
            image: An optional image to attach. Only meaningful for adapters
                with `supports_vision = True`; passed straight through to
                `_call_api` for adapters that don't use it.

        Returns:
            An AgentResponse. On success: status SUCCESS with response_text,
            latency_ms, and a token estimate. On any failure: the
            appropriate status (DISABLED/TIMEOUT/RATE_LIMITED/ERROR) with a
            human-readable `error` message and the latency spent before
            giving up.
        """
        if not self.config.enabled:
            return AgentResponse(agent=self.name, status=AgentStatus.DISABLED, error="disabled in config")
        if not self.config.api_key:
            return AgentResponse(
                agent=self.name, status=AgentStatus.DISABLED, error=f"missing {self.config.api_key_env}"
            )

        start = time.perf_counter()
        status = AgentStatus.ERROR
        last_error: str | None = None
        attempt = 0

        async with httpx.AsyncClient(timeout=self.config.timeout_s) as client:
            while attempt <= self.config.max_retries:
                try:
                    text = await asyncio.wait_for(
                        self._call_api(client, prompt, image), timeout=self.config.timeout_s
                    )
                    latency_ms = (time.perf_counter() - start) * 1000
                    tokens = estimate_tokens(prompt) + estimate_tokens(text)
                    return AgentResponse(
                        agent=self.name,
                        status=AgentStatus.SUCCESS,
                        response_text=text,
                        latency_ms=latency_ms,
                        token_count_estimate=tokens,
                        retries=attempt,
                        model=self.config.model,
                    )
                except asyncio.TimeoutError:
                    status, last_error = AgentStatus.TIMEOUT, f"timed out after {self.config.timeout_s}s"
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429:
                        status, last_error = AgentStatus.RATE_LIMITED, "rate limited (429)"
                    else:
                        status = AgentStatus.ERROR
                        last_error = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
                except httpx.RequestError as e:
                    status, last_error = AgentStatus.ERROR, f"network error: {e}"
                except Exception as e:  # noqa: BLE001 - any adapter/parsing failure must not crash the pipeline
                    status, last_error = AgentStatus.ERROR, f"{type(e).__name__}: {e}"

                logger.debug("%s attempt %d failed: %s", self.name, attempt, last_error)
                attempt += 1
                if attempt <= self.config.max_retries:
                    backoff = _BACKOFF_BASE_S * (2 ** (attempt - 1)) + random.uniform(0, 0.25)
                    await asyncio.sleep(backoff)

        latency_ms = (time.perf_counter() - start) * 1000
        return AgentResponse(
            agent=self.name,
            status=status,
            error=last_error,
            latency_ms=latency_ms,
            retries=attempt - 1,
            model=self.config.model,
        )
