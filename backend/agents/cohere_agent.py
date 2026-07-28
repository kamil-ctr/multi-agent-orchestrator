"""Cohere adapter (Chat v2 API)."""
from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx

from agents.base import BaseAgent

_URL = "https://api.cohere.com/v2/chat"


class CohereAgent(BaseAgent):
    name = "cohere"

    async def _call_api(self, client: httpx.AsyncClient, prompt: str, image=None) -> str:
        resp = await client.post(
            _URL,
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

    async def _call_api_stream(self, client: httpx.AsyncClient, prompt: str, image=None) -> AsyncIterator[str]:
        async with client.stream(
            "POST",
            _URL,
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.config.model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": True,
            },
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = line[len("data: ") :].strip()
                if not data:
                    continue
                try:
                    event = json.loads(data)
                except json.JSONDecodeError:
                    continue
                if event.get("type") != "content-delta":
                    continue
                text = event.get("delta", {}).get("message", {}).get("content", {}).get("text")
                if text:
                    yield text
