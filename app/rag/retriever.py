"""
Retriever — the single entry point for RAG queries.

Agents never touch vector_store.py directly.
They call retrieve() and get back a formatted context string.

This separation means we can swap the vector store (pgvector → LanceDB)
without touching any agent code.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from app.rag.embedder import embed_text
from app.rag.vector_store import similarity_search


async def retrieve(
    query: str,
    db: AsyncSession,
    top_k: int = 5,
    source_filter: str | None = None,
) -> str:
    """
    Given a natural language query, returns the most relevant
    document context as a single formatted string.

    The returned string is injected directly into the LLM prompt.
    """
    # 1. Embed the query using the same model used for documents
    query_embedding = await embed_text(query)

    # 2. Find nearest chunks in pgvector
    chunks = await similarity_search(
        query_embedding=query_embedding,
        db=db,
        top_k=top_k,
        source_filter=source_filter,
    )

    if not chunks:
        return "No relevant documents found."

    # 3. Format chunks into a readable context block for the LLM
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        source_info = f"{chunk['source']}"
        if chunk.get("page"):
            source_info += f", page {chunk['page']}"

        context_parts.append(
            f"[Source {i}: {source_info} | similarity: {chunk['similarity']}]\n"
            f"{chunk['text']}"
        )

    return "\n\n---\n\n".join(context_parts)
