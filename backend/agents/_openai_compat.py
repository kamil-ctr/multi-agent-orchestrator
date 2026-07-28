"""Shared helper for providers that expose an OpenAI-compatible
`/chat/completions` endpoint (currently Groq and Mistral) — reusable
for any future provider with the same request/response shape.
"""
from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from core.schemas import ImageInput


def _build_payload(
    model: str, prompt: str, image: ImageInput | None, extra_body: dict[str, Any] | None
) -> dict[str, Any]:
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
    return payload


async def openai_chat_completion(
    client: httpx.AsyncClient,
    url: str,
    api_key: str,
    model: str,
    prompt: str,
    image: ImageInput | None = None,
    extra_body: dict[str, Any] | None = None,
) -> str:
    payload = _build_payload(model, prompt, image, extra_body)

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


async def openai_chat_completion_stream(
    client: httpx.AsyncClient,
    url: str,
    api_key: str,
    model: str,
    prompt: str,
    image: ImageInput | None = None,
    extra_body: dict[str, Any] | None = None,
) -> AsyncIterator[str]:
    """Streaming variant of openai_chat_completion — yields text deltas as they arrive.

    Parses the standard OpenAI-style `data: {...}` SSE lines, terminated by
    a `data: [DONE]` sentinel line.
    """
    payload = _build_payload(model, prompt, image, extra_body)
    payload["stream"] = True

    async with client.stream(
        "POST",
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
    ) as resp:
        resp.raise_for_status()
        async for line in resp.aiter_lines():
            if not line.startswith("data: "):
                continue
            data = line[len("data: ") :].strip()
            if data == "[DONE]":
                break
            try:
                chunk = json.loads(data)
            except json.JSONDecodeError:
                continue
            choices = chunk.get("choices") or []
            if not choices:
                continue
            text = choices[0].get("delta", {}).get("content")
            if text:
                yield text
