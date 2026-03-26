"""
Vector Store — interface for storing and searching document chunks in pgvector.

Key concept (cosine similarity search):
    When a user asks a question, we embed the question into a vector,
    then find the chunks whose vectors are closest to it.

    pgvector operator <=> means "cosine distance" (lower = more similar).
    We ORDER BY distance ASC and take the top-k results.

    SQL it generates:
        SELECT * FROM document_chunks
        ORDER BY embedding <=> '[0.021, -0.14, ...]'
        LIMIT 5;
"""

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import DocumentChunk


async def save_chunks(chunks: list[dict], db: AsyncSession) -> int:
    """
    Persist embedded chunks to the database.
    Returns number of chunks saved.
    """
    records = []
    for chunk in chunks:
        metadata = chunk.get("metadata", {})
        record = DocumentChunk(
            source=metadata.get("source", "unknown"),
            chunk_index=metadata.get("chunk_index", 0),
            page=metadata.get("page"),
            doc_type=metadata.get("type", "unknown"),
            text=chunk["text"],
            embedding=chunk["embedding"],
        )
        record.set_metadata(metadata)
        records.append(record)

    db.add_all(records)
    await db.commit()
    return len(records)


async def similarity_search(
    query_embedding: list[float],
    db: AsyncSession,
    top_k: int = 5,
    source_filter: str | None = None,
) -> list[dict]:
    """
    Find the top-k most relevant chunks for a query embedding.

    Args:
        query_embedding:  the embedded user query vector
        top_k:            number of results to return
        source_filter:    optionally restrict to a specific document

    Returns list of dicts with text + metadata + similarity score.
    """
    stmt = (
        select(
            DocumentChunk,
            # cosine distance — cast embedding to vector for the operator
            (1 - DocumentChunk.embedding.cosine_distance(query_embedding)).label("similarity"),
        )
        .order_by(DocumentChunk.embedding.cosine_distance(query_embedding))
        .limit(top_k)
    )

    if source_filter:
        stmt = stmt.where(DocumentChunk.source == source_filter)

    result = await db.execute(stmt)
    rows = result.all()

    return [
        {
            "text": row.DocumentChunk.text,
            "source": row.DocumentChunk.source,
            "page": row.DocumentChunk.page,
            "similarity": round(float(row.similarity), 4),
            "metadata": row.DocumentChunk.get_metadata(),
        }
        for row in rows
    ]


async def create_vector_index(db: AsyncSession) -> None:
    """
    Create an IVFFlat index on the embedding column for fast similarity search.
    Call this once after bulk-inserting documents.

    IVFFlat splits vectors into clusters — much faster than brute-force
    at the cost of a small accuracy tradeoff (acceptable for RAG).
    """
    await db.execute(text("""
        CREATE INDEX IF NOT EXISTS document_chunks_embedding_idx
        ON document_chunks
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100);
    """))
    await db.commit()
