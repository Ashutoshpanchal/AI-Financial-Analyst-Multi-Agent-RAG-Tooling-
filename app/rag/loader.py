"""
Document Loader — reads raw files into plain text.

Supports:
- PDF  (financial reports, 10-K filings)
- CSV  (financial data tables)

Key concept:
    Loaders are kept completely separate from chunking and embedding.
    Each function returns a list of {text, metadata} dicts — a universal
    format that the chunker accepts regardless of file type.
"""

import io
import pandas as pd
from pypdf import PdfReader


def load_pdf(file_bytes: bytes, filename: str) -> list[dict]:
    """
    Extract text from each page of a PDF.
    Returns one document dict per page.
    """
    reader = PdfReader(io.BytesIO(file_bytes))
    documents = []

    for page_num, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        text = text.strip()

        if not text:
            continue  # skip blank pages

        documents.append({
            "text": text,
            "metadata": {
                "source": filename,
                "page": page_num + 1,
                "type": "pdf",
            }
        })

    return documents


def load_csv(file_bytes: bytes, filename: str) -> list[dict]:
    """
    Convert CSV rows into readable text chunks.
    Each row becomes a sentence: "Column: value, Column: value, ..."

    This format works better for embedding than raw CSV strings.
    """
    df = pd.read_csv(io.BytesIO(file_bytes))
    documents = []

    # Convert each row into a readable sentence
    for idx, row in df.iterrows():
        row_text = ", ".join(
            f"{col}: {val}"
            for col, val in row.items()
            if pd.notna(val)
        )
        documents.append({
            "text": row_text,
            "metadata": {
                "source": filename,
                "row": int(idx),
                "type": "csv",
            }
        })

    return documents


def load_file(file_bytes: bytes, filename: str) -> list[dict]:
    """
    Auto-detect file type and load accordingly.
    """
    if filename.lower().endswith(".pdf"):
        return load_pdf(file_bytes, filename)
    elif filename.lower().endswith(".csv"):
        return load_csv(file_bytes, filename)
    else:
        raise ValueError(f"Unsupported file type: {filename}")
