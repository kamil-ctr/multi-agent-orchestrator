"""Lightweight semantic-similarity embeddings via Cohere's embed API.

Deliberately not sentence-transformers/PyTorch: a local embedding model
adds ~500MB+ of runtime (torch + the model), which risks OOM-killing the
free-tier backend deployment (512MB RAM total, shared with the whole
FastAPI app and concurrent agent dispatches). A hosted embed call keeps
the memory footprint unchanged from before this feature existed, at the
cost of one extra small HTTP round-trip per cache write/lookup.

Cohere's embed-english-v3.0 was chosen after comparing real similarity
scores against Mistral's embeddings API: Cohere cleanly separates true
paraphrases (~0.94-0.96) from related-but-different questions (~0.7) and
unrelated ones (~0.1), matching the threshold this feature is tuned
around; Mistral's embeddings compressed everything into a narrow band
where an unrelated question could score higher than a true paraphrase.
"""
from __future__ import annotations

import httpx

_URL = "https://api.cohere.com/v2/embed"
_MODEL = "embed-english-v3.0"


async def embed_text(client: httpx.AsyncClient, text: str, api_key: str | None) -> list[float] | None:
    """Embed a single text for semantic cache comparison.

    Returns None (never raises) if no API key is configured or the call
    fails for any reason — semantic caching is a best-effort enhancement,
    never a hard dependency of the query path.
    """
    if not api_key:
        return None
    try:
        resp = await client.post(
            _URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": _MODEL,
                "texts": [text],
                "input_type": "search_query",
                "embedding_types": ["float"],
            },
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["embeddings"]["float"][0]
    except Exception:  # noqa: BLE001 - best-effort, never break the query path
        return None


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)
