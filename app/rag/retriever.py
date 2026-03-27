"""
Retriever — the single entry point for RAG queries.

Two-stage pipeline:
    1. Cosine similarity search  → fetch top 20 candidates (fast)
    2. Cross-encoder rerank      → re-score, return top 5 (accurate)

Agents call retrieve() and get back a formatted context string.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from app.rag.embedder import embed_text
from app.rag.vector_store import similarity_search
from app.rag.reranker import rerank


async def retrieve(
    query: str,
    db: AsyncSession,
    top_k: int = 5,
    fetch_k: int = 20,
    source_filter: str | None = None,
) -> str:
    """
    Retrieve and rerank the most relevant document chunks for a query.

    Args:
        query:         the user's natural language question
        top_k:         final number of chunks to return to the LLM (after rerank)
        fetch_k:       how many candidates to fetch from pgvector before reranking
        source_filter: optionally restrict to a specific document filename

    Returns a formatted string injected directly into the LLM prompt.
    """
    # Stage 1 — embed query and fetch candidates via cosine similarity
    query_embedding = await embed_text(query)

    candidates = await similarity_search(
        query_embedding=query_embedding,
        db=db,
        top_k=fetch_k,         # fetch more than needed for reranking
        source_filter=source_filter,
    )

    if not candidates:
        return "No relevant documents found."

    # Stage 2 — rerank candidates with cross-encoder, keep top_k
    chunks = rerank(query=query, chunks=candidates, top_k=top_k)

    # Format into a context block for the LLM
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        source_info = chunk["source"]
        if chunk.get("page"):
            source_info += f", page {chunk['page']}"

        score_info = f"rerank: {chunk.get('rerank_score', 'n/a')} | cosine: {chunk.get('similarity', 'n/a')}"

        context_parts.append(
            f"[Source {i}: {source_info} | {score_info}]\n"
            f"{chunk['text']}"
        )

    return "\n\n---\n\n".join(context_parts)
