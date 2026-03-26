from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from app.api.deps import DBSession
from app.services.document_service import ingest_document

router = APIRouter()


class IngestResponse(BaseModel):
    filename: str
    pages: int
    chunks: int
    status: str


@router.post("/documents/ingest", response_model=IngestResponse)
async def ingest(
    db: DBSession,
    file: UploadFile = File(...),
) -> IngestResponse:
    """
    Upload a PDF or CSV financial document.
    It will be chunked, embedded, and stored in pgvector for RAG queries.
    """
    if not file.filename.endswith((".pdf", ".csv")):
        raise HTTPException(status_code=400, detail="Only PDF and CSV files are supported")

    file_bytes = await file.read()
    result = await ingest_document(
        file_bytes=file_bytes,
        filename=file.filename,
        db=db,
    )
    return IngestResponse(**result)
