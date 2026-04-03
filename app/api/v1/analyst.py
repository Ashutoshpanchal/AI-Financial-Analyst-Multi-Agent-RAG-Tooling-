from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.services.analyst_service import run_analysis, stream_analysis

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
    cache_hit: bool = False


@router.post("/analyze", response_model=AnalystResponse)
async def analyze(body: AnalystRequest) -> AnalystResponse:
    result = await run_analysis(query=body.query, user_id=body.user_id)
    return AnalystResponse(**result)


@router.get("/analyze/stream")
async def analyze_stream(query: str, user_id: str | None = None) -> StreamingResponse:
    """
    SSE endpoint — streams one event per agent as it completes.
    Final event is sent after critic_agent finishes.

    Usage:
        GET /api/v1/analyze/stream?query=What+is+Apple+PE&user_id=user_123

    Events emitted (in order):
        router_agent        → { event, status, label, query_type }
        rag/computation/... → { event, status, label }
        yfinance_agent      → { event, status, label, ticker }
        aggregator_agent    → { event, status, label, answer }
        critic_agent        → { event, status, label, answer, is_valid, critique, errors, trace_id }
        stream_end          → { event: "stream_end" }
    """
    return StreamingResponse(
        stream_analysis(query=query, user_id=user_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control":               "no-cache",
            "X-Accel-Buffering":           "no",    # disable nginx buffering
            "Access-Control-Allow-Origin": "*",
        },
    )
