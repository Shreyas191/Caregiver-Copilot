"""Tests for CC-023: BGE-M3 embedding pipeline."""

import pytest
from unittest.mock import AsyncMock, patch

from app.agent.embeddings import Embedder, DenseSparseVector, _bm25_sparse, _tokenize


def test_tokenize_basic():
    tokens = _tokenize("Blood pressure reading 145/88")
    assert "blood" in tokens
    assert "pressure" in tokens
    assert "reading" in tokens


def test_tokenize_empty():
    assert _tokenize("") == []


def test_bm25_sparse_basic():
    sparse = _bm25_sparse("lisinopril causes cough lisinopril")
    assert len(sparse) > 0
    # All values should be positive floats
    for v in sparse.values():
        assert v > 0


def test_bm25_sparse_empty():
    assert _bm25_sparse("") == {}


def test_bm25_sparse_repeated_term_has_higher_score():
    sparse_one = _bm25_sparse("headache")
    sparse_two = _bm25_sparse("headache headache headache")
    # Token for "headache" should have higher score when repeated
    key = list(sparse_one.keys())[0]
    assert sparse_two.get(key, 0) > sparse_one.get(key, 0)


@pytest.mark.asyncio
async def test_embedder_returns_correct_dimensions():
    """Embedder wraps provider.embed() and returns DenseSparseVector."""
    fake_dense = [0.1] * 1024

    with patch("app.agent.embeddings.get_embedding_provider") as mock_factory:
        mock_provider = AsyncMock()
        mock_provider.embed = AsyncMock(return_value=[fake_dense])
        mock_provider.aclose = AsyncMock()
        mock_factory.return_value = mock_provider

        embedder = Embedder()
        results = await embedder.embed_texts(["test sentence"])
        await embedder.aclose()

    assert len(results) == 1
    vec = results[0]
    assert isinstance(vec, DenseSparseVector)
    assert len(vec.dense) == 1024
    assert isinstance(vec.sparse, dict)


@pytest.mark.asyncio
async def test_embedder_batch():
    """Embed a batch of texts returns one vector per text."""
    texts = ["sentence one", "sentence two", "sentence three"]
    fake_dense = [[0.1] * 1024 for _ in texts]

    with patch("app.agent.embeddings.get_embedding_provider") as mock_factory:
        mock_provider = AsyncMock()
        mock_provider.embed = AsyncMock(return_value=fake_dense)
        mock_provider.aclose = AsyncMock()
        mock_factory.return_value = mock_provider

        embedder = Embedder()
        results = await embedder.embed_texts(texts)
        await embedder.aclose()

    assert len(results) == 3
    for r in results:
        assert len(r.dense) == 1024


@pytest.mark.asyncio
async def test_embedder_deterministic():
    """Same input produces same sparse vector (BM25 is deterministic)."""
    with patch("app.agent.embeddings.get_embedding_provider") as mock_factory:
        mock_provider = AsyncMock()
        mock_provider.embed = AsyncMock(return_value=[[0.5] * 1024])
        mock_provider.aclose = AsyncMock()
        mock_factory.return_value = mock_provider

        embedder = Embedder()
        r1 = await embedder.embed_texts(["lisinopril blood pressure"])
        r2 = await embedder.embed_texts(["lisinopril blood pressure"])
        await embedder.aclose()

    assert r1[0].sparse == r2[0].sparse
