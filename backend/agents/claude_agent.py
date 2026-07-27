"""Anthropic Claude adapter (Messages API)."""
from __future__ import annotations

import httpx

from agents.base import BaseAgent
from core.schemas import ImageInput

ANTHROPIC_VERSION = "2023-06-01"


class ClaudeAgent(BaseAgent):
    name = "claude"
    supports_vision = True

    async def _call_api(self, client: httpx.AsyncClient, prompt: str, image: ImageInput | None = None) -> str:
        model = self.config.effective_vision_model if image else self.config.model

        content: list[dict] = []
        if image:
            content.append(
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": image.mime_type, "data": image.data_base64},
                }
            )
        content.append({"type": "text", "text": prompt})

        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": self.config.api_key or "",
                "anthropic-version": ANTHROPIC_VERSION,
                "content-type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": content}],
            },
        )
        resp.raise_for_status()
        data = resp.json()
        blocks = data.get("content", [])
        return "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
