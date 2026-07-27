"""Shared helper for the many providers that expose an OpenAI-compatible
`/chat/completions` endpoint (Groq, Mistral, Perplexity, HF router,
OpenAI itself, xAI Grok, DeepSeek, Together AI, ...).
"""
from __future__ import annotations

from typing import Any

import httpx

from core.schemas import ImageInput


async def openai_chat_completion(
    client: httpx.AsyncClient,
    url: str,
    api_key: str,
    model: str,
    prompt: str,
    image: ImageInput | None = None,
    extra_body: dict[str, Any] | None = None,
) -> str:
    if image:
        content: Any = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:{image.mime_type};base64,{image.data_base64}"}},
        ]
    else:
        content = prompt

    payload: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": content}],
    }
    if extra_body:
        payload.update(extra_body)

    resp = await client.post(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]
