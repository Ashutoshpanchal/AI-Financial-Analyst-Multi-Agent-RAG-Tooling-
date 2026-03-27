"""
Reranker — improves RAG quality by re-scoring retrieved chunks.

Why reranking?
    Cosine similarity (step 1) compares vectors independently.
    It finds chunks that are semantically close but doesn't understand
    how well the chunk actually answers the specific question.

    A cross-encoder reranker reads the query AND chunk together,
    like a human would, and scores them as a pair — much more accurate.

Two-stage pipeline:
    Stage 1 — cosine similarity (fast, vector math)
        query → embed → pgvector → top 20 candidates

    Stage 2 — cross-encoder rerank (slower, but precise)
        (query, chunk_1) → score: 0.91  ← best match
        (query, chunk_2) → score: 0.43
        (query, chunk_3) → score: 0.87  ← second best
        ...top 5 returned to LLM

Model: ms-marco-MiniLM-L-12-v2 (via flashrank)
    - Runs on CPU, no GPU needed
    - ~33MB, auto-downloaded on first use
    - Specifically trained on passage re-ranking tasks
"""

from functools import lru_cache
from flashrank import Ranker, RerankRequest


@lru_cache
def get_ranker() -> Ranker:
    """
    Cached ranker instance — loaded once, reused across requests.
    Model is downloaded automatically on first call (~33MB).
    """
    return Ranker(model_name="ms-marco-MiniLM-L-12-v2")


def rerank(query: str, chunks: list[dict], top_k: int = 5) -> list[dict]:
    """
    Rerank a list of retrieved chunks using a cross-encoder.

    Args:
        query:   the original user question
        chunks:  list of chunk dicts from similarity_search()
        top_k:   how many top results to return after reranking

    Returns the top_k chunks sorted by rerank score (highest first),
    with a 'rerank_score' field added to each chunk dict.
    """
    if not chunks:
        return chunks

    ranker = get_ranker()

    # flashrank expects a list of {"id": ..., "text": ...}
    passages = [
        {"id": i, "text": chunk["text"]}
        for i, chunk in enumerate(chunks)
    ]

    request = RerankRequest(query=query, passages=passages)
    results = ranker.rerank(request)

    # Map rerank scores back to original chunk dicts
    reranked = []
    for result in results[:top_k]:
        original_chunk = chunks[result["id"]]
        reranked.append({
            **original_chunk,
            "rerank_score": round(float(result["score"]), 4),
        })

    return reranked
