"""
Evaluation API endpoint — trigger and view evaluation runs via HTTP.
"""

from fastapi import APIRouter, Query
from app.services.eval_service import run_evaluation

router = APIRouter()


@router.post("/eval/run")
async def run_eval(
    query_ids: list[str] | None = Query(default=None),
) -> dict:
    """
    Run the evaluation pipeline.
    Pass query_ids to run only specific tests, or omit to run all.

    Results are logged to Langfuse automatically.
    """
    return await run_evaluation(query_ids=query_ids)
