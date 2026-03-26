"""
Chunker — splits documents into smaller overlapping pieces.

Key concept (why chunk?):
    LLMs have limited context windows.
    Embedding models work best on short, focused text (~200-500 tokens).
    Overlap ensures that context at chunk boundaries is not lost.

    Example with chunk_size=500, overlap=100:
    [----chunk 1 (500)----]
                [---overlap---][----chunk 2 (500)----]

Why RecursiveCharacterTextSplitter?
    It tries to split on paragraph breaks first, then sentences,
    then words — preserving semantic units where possible.
"""

from langchain_text_splitters import RecursiveCharacterTextSplitter


def chunk_documents(
    documents: list[dict],
    chunk_size: int = 500,
    chunk_overlap: int = 100,
) -> list[dict]:
    """
    Split a list of document dicts into smaller chunks.
    Preserves and passes through all original metadata.

    Returns a flat list of chunk dicts ready for embedding.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks = []
    for doc in documents:
        splits = splitter.split_text(doc["text"])

        for chunk_idx, split_text in enumerate(splits):
            chunks.append({
                "text": split_text,
                "metadata": {
                    **doc["metadata"],
                    "chunk_index": chunk_idx,
                }
            })

    return chunks
