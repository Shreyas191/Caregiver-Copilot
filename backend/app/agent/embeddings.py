"""BGE-M3 embedding pipeline.

Wraps the OllamaProvider to produce dense vectors from BGE-M3.
Sparse vectors are approximated via BM25-style term weighting since
Ollama does not expose BGE-M3's native sparse output.
"""

import math
import re
from collections import Counter
from functools import lru_cache

from pydantic import BaseModel

from app.core.config import get_settings
from app.providers.factory import get_embedding_provider


class DenseSparseVector(BaseModel):
    dense: list[float]
    sparse: dict[int, float]


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\b[a-z0-9]+\b", text.lower())


def _bm25_sparse(text: str, k1: float = 1.2, b: float = 0.75) -> dict[int, float]:
    """Approximate BM25 sparse representation.

    Returns token hash -> weight mapping. Uses term frequency only
    (no IDF since we have no corpus statistics at query time). Adequate
    for boosting exact term matches in hybrid retrieval.
    """
    tokens = _tokenize(text)
    if not tokens:
        return {}

    tf = Counter(tokens)
    doc_len = len(tokens)
    avg_len = doc_len  # single-document approximation

    sparse: dict[int, float] = {}
    for token, count in tf.items():
        token_id = abs(hash(token)) % (2**31)
        tf_score = (count * (k1 + 1)) / (count + k1 * (1 - b + b * doc_len / avg_len))
        sparse[token_id] = round(tf_score, 4)

    return sparse


class Embedder:
    """Wrapper around the Ollama BGE-M3 model for dense + sparse embeddings."""

    def __init__(self) -> None:
        settings = get_settings()
        self._model = settings.embedding_model_name
        self._provider = get_embedding_provider()

    async def embed_texts(self, texts: list[str]) -> list[DenseSparseVector]:
        """Embed a batch of texts, returning dense (1024-dim) + sparse vectors."""
        dense_list = await self._provider.embed(texts=texts, model=self._model)
        return [
            DenseSparseVector(dense=dense, sparse=_bm25_sparse(text))
            for dense, text in zip(dense_list, texts)
        ]

    async def embed_query(self, text: str) -> DenseSparseVector:
        """Embed a single query string."""
        results = await self.embed_texts([text])
        return results[0]

    async def aclose(self) -> None:
        await self._provider.aclose()
