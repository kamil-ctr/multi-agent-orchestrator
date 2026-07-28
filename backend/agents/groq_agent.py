"""Groq adapter — OpenAI-compatible chat completions, very low latency."""
from __future__ import annotations

from collections.abc import AsyncIterator

import httpx

from agents._openai_compat import openai_chat_completion, openai_chat_completion_stream
from agents.base import BaseAgent

_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqAgent(BaseAgent):
    name = "groq"

    async def _call_api(self, client: httpx.AsyncClient, prompt: str, image=None) -> str:
        return await openai_chat_completion(
            client,
            _URL,
            self.config.api_key or "",
            self.config.model,
            prompt,
        )

    async def _call_api_stream(self, client: httpx.AsyncClient, prompt: str, image=None) -> AsyncIterator[str]:
        async for chunk in openai_chat_completion_stream(
            client,
            _URL,
            self.config.api_key or "",
            self.config.model,
            prompt,
        ):
            yield chunk
