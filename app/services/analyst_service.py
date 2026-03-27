"""
Analyst Service — orchestrates the full LangGraph workflow per request.

Langfuse tracing via @observe decorator:
  @observe on run_analysis creates the root trace.
  Every @observe-decorated agent called from within is automatically
  nested as a child span under this trace — no manual context passing needed.

Trace hierarchy in Langfuse:
  run_analysis  (root trace)
    ├── router_agent
    ├── rag_agent / computation_agent / parallel
    ├── mcp_enrichment_agent
    ├── planner_agent
    ├── aggregator_agent
    └── critic_agent
"""

from langfuse.decorators import observe, langfuse_context
from app.workflows.graph import workflow
from app.workflows.state import GraphState
from app.models.router import TASK_MODEL_MAP


@observe(name="run_analysis")
async def run_analysis(query: str, user_id: str | None = None) -> dict:
    # Tag the trace with user and input query
    langfuse_context.update_current_trace(
        name="run_analysis",
        user_id=user_id,
        input={"query": query},
        tags=["financial-analyst"],
        metadata={
            "model": TASK_MODEL_MAP["aggregation"],   # primary model used
            "all_models": TASK_MODEL_MAP,
        },
    )

    # Get the trace_id created by @observe so agents can reference it
    trace_id = langfuse_context.get_current_trace_id()

    initial_state: GraphState = {
        "query":              query,
        "user_id":            user_id,
        "query_type":         None,
        "next_agent":         None,
        "plan":               None,
        "steps":              [],
        "retrieved_context":  None,
        "tool_results":       {},
        "mcp_enrichment":     {},
        "final_answer":       None,
        "is_valid":           None,
        "critique":           None,
        "errors":             [],
        "trace_id":           trace_id,
    }

    try:
        final_state: GraphState = await workflow.ainvoke(initial_state)

        result = {
            "query":        query,
            "query_type":   final_state.get("query_type"),
            "plan":         final_state.get("plan"),
            "steps":        final_state.get("steps", []),
            "answer":       final_state.get("final_answer") or "No answer generated.",
            "is_valid":     final_state.get("is_valid"),
            "critique":     final_state.get("critique"),
            "tool_results": final_state.get("tool_results", {}),
            "errors":       final_state.get("errors", []),
            "trace_id":     trace_id,
        }

        # Update root trace with final output
        langfuse_context.update_current_trace(output={"answer": result["answer"]})
        return result

    except Exception as e:
        langfuse_context.update_current_observation(
            level="ERROR",
            status_message=str(e),
        )
        raise
