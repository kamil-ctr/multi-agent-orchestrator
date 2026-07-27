"""xAI Grok adapter — OpenAI-compatible chat completions, vision-capable."""
from __future__ import annotations

import httpx

from agents._openai_compat import openai_chat_completion
from agents.base import BaseAgent
from core.schemas import ImageInput


class GrokAgent(BaseAgent):
    name = "grok"
    supports_vision = True

    async def _call_api(self, client: httpx.AsyncClient, prompt: str, image: ImageInput | None = None) -> str:
        model = self.config.effective_vision_model if image else self.config.model
        return await openai_chat_completion(
            client,
            "https://api.x.ai/v1/chat/completions",
            self.config.api_key or "",
            model,
            prompt,
            image=image,
        )
