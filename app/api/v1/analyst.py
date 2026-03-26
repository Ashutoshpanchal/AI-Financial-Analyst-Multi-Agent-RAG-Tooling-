from fastapi import APIRouter
from pydantic import BaseModel
from app.services.analyst_service import run_analysis

router = APIRouter()


class AnalystRequest(BaseModel):
    query: str
    user_id: str | None = None


class AnalystResponse(BaseModel):
    query: str
    query_type: str | None
    plan: str | None
    steps: list[str]
    answer: str
    errors: list[str]
    trace_id: str | None


@router.post("/analyze", response_model=AnalystResponse)
async def analyze(body: AnalystRequest) -> AnalystResponse:
    result = await run_analysis(query=body.query, user_id=body.user_id)
    return AnalystResponse(**result)
