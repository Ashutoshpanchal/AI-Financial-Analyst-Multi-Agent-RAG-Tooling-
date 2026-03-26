"""
ORM models.

DocumentChunk stores:
- the raw text of each chunk
- its vector embedding (pgvector column)
- metadata (source file, page, etc.)

The pgvector extension (enabled in init.sql) adds a Vector column type
to Postgres, so we can do similarity search using SQL operators.
"""

import json
from datetime import datetime
from sqlalchemy import String, Text, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector
from app.db.session import Base
from app.rag.embedder import EMBEDDING_DIMENSIONS


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Source info
    source: Mapped[str] = mapped_column(String(255))         # filename
    chunk_index: Mapped[int] = mapped_column(Integer)
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    doc_type: Mapped[str] = mapped_column(String(50))        # "pdf" or "csv"

    # Content
    text: Mapped[str] = mapped_column(Text)

    # Vector embedding — this is what pgvector stores and searches
    embedding: Mapped[list[float]] = mapped_column(
        Vector(EMBEDDING_DIMENSIONS)
    )

    # Extra metadata as JSON string
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    def set_metadata(self, metadata: dict) -> None:
        self.metadata_json = json.dumps(metadata)

    def get_metadata(self) -> dict:
        return json.loads(self.metadata_json) if self.metadata_json else {}
