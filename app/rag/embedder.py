"""
Embedder — converts text into dense vectors.

Supports both OpenAI and NVIDIA embedding models via settings:
  OpenAI:  EMBEDDING_MODEL=text-embedding-3-small  EMBEDDING_DIMENSIONS=1536
  NVIDIA:  EMBEDDING_MODEL=nvidia/nv-embedqa-e5-v5  EMBEDDING_DIMENSIONS=1024
"""

from openai import AsyncOpenAI
from app.config.settings import get_settings

settings = get_settings()

_client = AsyncOpenAI(
    api_key=settings.embedding_api_key or settings.openai_api_key,
    base_url=settings.openai_base_url,
)

EMBEDDING_MODEL = settings.embedding_model
EMBEDDING_DIMENSIONS = settings.embedding_dimensions


async def embed_text(text: str) -> list[float]:
    """Embed a single query string. Used at retrieval time."""
    response = await _client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
        extra_body={"input_type": "query", "truncate": "END"},
    )
    return response.data[0].embedding


async def embed_chunks(chunks: list[dict]) -> list[dict]:
    """
    Embed a batch of document chunks for storage.
    Uses input_type='passage' — optimised for document content.
    """
    texts = [chunk["text"] for chunk in chunks]

    response = await _client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=texts,
        extra_body={"input_type": "passage", "truncate": "END"},
    )

    for chunk, embedding_obj in zip(chunks, response.data):
        chunk["embedding"] = embedding_obj.embedding

    return chunks
