"""Google Gemini adapter (generativelanguage.googleapis.com REST API)."""
from __future__ import annotations

import httpx

from agents.base import BaseAgent
from core.schemas import ImageInput


class GeminiAgent(BaseAgent):
    name = "gemini"
    supports_vision = True

    async def _call_api(self, client: httpx.AsyncClient, prompt: str, image: ImageInput | None = None) -> str:
        model = self.config.effective_vision_model if image else self.config.model
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

        parts: list[dict] = [{"text": prompt}]
        if image:
            parts.append({"inline_data": {"mime_type": image.mime_type, "data": image.data_base64}})

        resp = await client.post(
            url,
            params={"key": self.config.api_key},
            headers={"Content-Type": "application/json"},
            json={"contents": [{"parts": parts}]},
        )
        resp.raise_for_status()
        data = resp.json()
        candidates = data.get("candidates") or []
        if not candidates:
            reason = data.get("promptFeedback", {}).get("blockReason", "no candidates returned")
            raise ValueError(f"Gemini returned no content: {reason}")
        response_parts = candidates[0].get("content", {}).get("parts", [])
        return "".join(p.get("text", "") for p in response_parts)
