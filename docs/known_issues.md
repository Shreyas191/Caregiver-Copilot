# Known Issues

## RxNav Drug Interaction API

As of May 2025, the RxNav `/REST/interaction/list.json` endpoint is available but returns
results only for drugs with known interaction data in the NLM database. Some newer medications
or combinations may return empty results even when clinical interactions are known.

**Workaround**: For medications not returning results from the list endpoint, consider falling
back to individual pairwise lookups via `/REST/interaction/interaction.json?rxcui=<rxcui>`.
This has been documented but not yet implemented; tracking in backlog.

## BGE-M3 Sparse Vectors via Ollama

Ollama's BGE-M3 endpoint (`/api/embeddings`) only returns dense vectors (1024-dim). The native
sparse output (SPLADE-style) is not exposed through Ollama's API. As a result, the `Embedder`
class in `app/agent/embeddings.py` approximates sparse representations using BM25-style term
weighting. This is adequate for keyword boosting but does not match the quality of true SPLADE
sparse vectors.

**Impact**: Hybrid retrieval provides reasonable results but may not fully leverage BGE-M3's
cross-lingual sparse retrieval capabilities. For production deployment with higher retrieval
quality requirements, consider using the `FlagEmbedding` Python library directly or a vector
server that exposes sparse outputs.

## LangGraph MemorySaver

The current graph uses `MemorySaver` for checkpointing (in-memory, not persistent). This means:
- Conversation state is lost on server restart.
- Thread continuity across sessions requires the client to pass `thread_id` explicitly.

For production: migrate to `PostgresSaver` (LangGraph) or a Redis-backed checkpoint store.
