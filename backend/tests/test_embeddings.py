from __future__ import annotations

import pytest

from core.embeddings import cosine_similarity, embed_text


def test_cosine_similarity_identical_vectors():
    assert cosine_similarity([1.0, 0.0, 0.0], [1.0, 0.0, 0.0]) == pytest.approx(1.0)


def test_cosine_similarity_orthogonal_vectors():
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)


def test_cosine_similarity_opposite_vectors():
    assert cosine_similarity([1.0, 0.0], [-1.0, 0.0]) == pytest.approx(-1.0)


def test_cosine_similarity_zero_vector_is_zero_not_a_crash():
    assert cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0


@pytest.mark.asyncio
async def test_embed_text_returns_none_without_api_key():
    result = await embed_text(client=None, text="hello", api_key=None)
    assert result is None


@pytest.mark.asyncio
async def test_embed_text_returns_none_without_api_key_empty_string():
    result = await embed_text(client=None, text="hello", api_key="")
    assert result is None
