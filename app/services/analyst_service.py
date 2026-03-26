"""
Analyst Service — orchestrates the full LangGraph workflow per request.
"""

from app.workflows.graph import workflow
from app.workflows.state import GraphState
from app.observability.tracer import TraceContext


async def run_analysis(query: str, user_id: str | None = None) -> dict:
    ctx = TraceContext(name="run_analysis", user_id=user_id)
    ctx.start(input={"query": query})

    initial_state: GraphState = {
        "query": query,
        "user_id": user_id,
        "query_type": None,
        "next_agent": None,
        "plan": None,
        "steps": [],
        "retrieved_context": None,
        "tool_results": {},
        "final_answer": None,
        "is_valid": None,
        "critique": None,
        "errors": [],
        "trace_id": ctx.trace.id if ctx.trace else None,
    }

    try:
        final_state: GraphState = await workflow.ainvoke(initial_state)

        result = {
            "query":         query,
            "query_type":    final_state.get("query_type"),
            "plan":          final_state.get("plan"),
            "steps":         final_state.get("steps", []),
            "answer":        final_state.get("final_answer") or "No answer generated.",
            "is_valid":      final_state.get("is_valid"),
            "critique":      final_state.get("critique"),
            "tool_results":  final_state.get("tool_results", {}),
            "errors":        final_state.get("errors", []),
            "trace_id":      ctx.trace.id if ctx.trace else None,
        }

        ctx.end(output=result)
        return result

    except Exception as e:
        ctx.end(output={"error": str(e)}, status="error")
        raise
