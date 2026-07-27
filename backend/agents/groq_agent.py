"""Groq adapter — OpenAI-compatible chat completions, very low latency."""
from __future__ import annotations

import httpx

from agents._openai_compat import openai_chat_completion
from agents.base import BaseAgent


class GroqAgent(BaseAgent):
    name = "groq"

    async def _call_api(self, client: httpx.AsyncClient, prompt: str, image=None) -> str:
        return await openai_chat_completion(
            client,
            "https://api.groq.com/openai/v1/chat/completions",
            self.config.api_key or "",
            self.config.model,
            prompt,
        )
