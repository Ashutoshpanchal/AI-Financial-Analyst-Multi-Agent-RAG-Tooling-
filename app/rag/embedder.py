"""
Embedder — converts text into dense vectors using OpenAI embeddings.

Key concept (what is an embedding?):
    An embedding is a list of ~1536 floats that represents the
    *meaning* of a piece of text in high-dimensional space.
    Similar meanings → similar vectors → close together in vector space.

    "Apple revenue 2023"  →  [0.021, -0.14, 0.88, ...]
    "Apple income 2023"   →  [0.019, -0.13, 0.87, ...]  ← very close
    "dog food recipe"     →  [-0.72, 0.44, -0.31, ...]  ← far away

Model: text-embedding-3-small
    - 1536 dimensions
    - Cheap ($0.02 per 1M tokens)
    - Good enough for financial document retrieval
"""

from openai import AsyncOpenAI
from app.config.settings import get_settings

settings = get_settings()
_client = AsyncOpenAI(api_key=settings.openai_api_key)

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536


async def embed_text(text: str) -> list[float]:
    """Embed a single string. Used at query time."""
    response = await _client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
    )
    return response.data[0].embedding


async def embed_chunks(chunks: list[dict]) -> list[dict]:
    """
    Embed a batch of chunk dicts.
    Adds an 'embedding' key to each chunk dict and returns them.

    Batches all texts in one API call — much cheaper than one call per chunk.
    """
    texts = [chunk["text"] for chunk in chunks]

    response = await _client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=texts,
    )

    for chunk, embedding_obj in zip(chunks, response.data):
        chunk["embedding"] = embedding_obj.embedding

    return chunks
