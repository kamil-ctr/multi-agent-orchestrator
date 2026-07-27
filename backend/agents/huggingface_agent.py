"""HuggingFace Inference adapter, via the OpenAI-compatible router endpoint."""
from __future__ import annotations

import httpx

from agents._openai_compat import openai_chat_completion
from agents.base import BaseAgent


class HuggingFaceAgent(BaseAgent):
    name = "huggingface"

    async def _call_api(self, client: httpx.AsyncClient, prompt: str, image=None) -> str:
        return await openai_chat_completion(
            client,
            "https://router.huggingface.co/v1/chat/completions",
            self.config.api_key or "",
            self.config.model,
            prompt,
        )
