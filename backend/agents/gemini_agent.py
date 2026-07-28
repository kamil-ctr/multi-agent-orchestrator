"""Google Gemini adapter (generativelanguage.googleapis.com REST API)."""
from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx

from agents.base import BaseAgent
from core.schemas import ImageInput


def _build_parts(prompt: str, image: ImageInput | None) -> list[dict]:
    parts: list[dict] = [{"text": prompt}]
    if image:
        parts.append({"inline_data": {"mime_type": image.mime_type, "data": image.data_base64}})
    return parts


class GeminiAgent(BaseAgent):
    name = "gemini"
    supports_vision = True

    async def _call_api(self, client: httpx.AsyncClient, prompt: str, image: ImageInput | None = None) -> str:
        model = self.config.effective_vision_model if image else self.config.model
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

        resp = await client.post(
            url,
            params={"key": self.config.api_key},
            headers={"Content-Type": "application/json"},
            json={"contents": [{"parts": _build_parts(prompt, image)}]},
        )
        resp.raise_for_status()
        data = resp.json()
        candidates = data.get("candidates") or []
        if not candidates:
            reason = data.get("promptFeedback", {}).get("blockReason", "no candidates returned")
            raise ValueError(f"Gemini returned no content: {reason}")
        response_parts = candidates[0].get("content", {}).get("parts", [])
        return "".join(p.get("text", "") for p in response_parts)

    async def _call_api_stream(
        self, client: httpx.AsyncClient, prompt: str, image: ImageInput | None = None
    ) -> AsyncIterator[str]:
        model = self.config.effective_vision_model if image else self.config.model
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent"

        async with client.stream(
            "POST",
            url,
            params={"key": self.config.api_key, "alt": "sse"},
            headers={"Content-Type": "application/json"},
            json={"contents": [{"parts": _build_parts(prompt, image)}]},
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = line[len("data: ") :].strip()
                if not data:
                    continue
                try:
                    chunk = json.loads(data)
                except json.JSONDecodeError:
                    continue
                candidates = chunk.get("candidates") or []
                if not candidates:
                    continue
                for part in candidates[0].get("content", {}).get("parts", []):
                    text = part.get("text")
                    if text:
                        yield text
