"""Cohere adapter (Chat v2 API)."""
from __future__ import annotations

import httpx

from agents.base import BaseAgent


class CohereAgent(BaseAgent):
    name = "cohere"

    async def _call_api(self, client: httpx.AsyncClient, prompt: str, image=None) -> str:
        resp = await client.post(
            "https://api.cohere.com/v2/chat",
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.config.model,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        resp.raise_for_status()
        data = resp.json()
        content_blocks = data.get("message", {}).get("content", [])
        return "".join(b.get("text", "") for b in content_blocks if b.get("type") == "text")
