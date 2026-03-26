"""
Document Service — orchestrates the full ingestion pipeline.

Pipeline:
    uploaded file
        → loader    (extract raw text)
        → chunker   (split into pieces)
        → embedder  (convert to vectors)
        → vector_store (save to pgvector)
"""

from sqlalchemy.ext.asyncio import AsyncSession
from app.rag.loader import load_file
from app.rag.chunker import chunk_documents
from app.rag.embedder import embed_chunks
from app.rag.vector_store import save_chunks


async def ingest_document(
    file_bytes: bytes,
    filename: str,
    db: AsyncSession,
) -> dict:
    """
    Full ingestion pipeline for a single uploaded file.
    Returns a summary of what was ingested.
    """
    # Step 1: Load raw text from file
    documents = load_file(file_bytes, filename)

    if not documents:
        return {"filename": filename, "pages": 0, "chunks": 0, "status": "empty"}

    # Step 2: Chunk into smaller pieces
    chunks = chunk_documents(documents)

    # Step 3: Embed all chunks in one batch API call
    embedded_chunks = await embed_chunks(chunks)

    # Step 4: Save to pgvector
    saved_count = await save_chunks(embedded_chunks, db)

    return {
        "filename": filename,
        "pages": len(documents),
        "chunks": saved_count,
        "status": "success",
    }
