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

import json
from typing import AsyncGenerator
from langfuse.decorators import observe, langfuse_context
from app.workflows.graph import workflow
from app.workflows.state import GraphState
from app.models.router import TASK_MODEL_MAP
from app.cache.redis_cache import get_cache


@observe(name="run_analysis")
async def run_analysis(query: str, user_id: str | None = None) -> dict:
    # ── Redis FAQ cache check ─────────────────────────────────────────────────
    cache = await get_cache()
    cached = await cache.get(query)
    if cached is not None:
        cached["cache_hit"] = True
        return cached

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

        # ── Store in Redis for future identical queries ────────────────────────
        result["cache_hit"] = False
        await cache.set(query, result)

        return result

    except Exception as e:
        langfuse_context.update_current_observation(
            level="ERROR",
            status_message=str(e),
        )
        raise


# ── Agent display labels shown in SSE events ──────────────────────────────────
_AGENT_LABELS = {
    "router_agent":          "Classifying query",
    "rag_agent":             "Retrieving documents",
    "computation_agent":     "Running calculations",
    "parallel_agent":        "Retrieving documents & calculating",
    "yfinance_agent":        "Fetching live market data",
    "mcp_enrichment_agent":  "Enriching with MCP tools",
    "planner_agent":         "Planning analysis",
    "aggregator_agent":      "Synthesizing answer",
    "critic_agent":          "Validating answer",
}


async def stream_analysis(
    query: str,
    user_id: str | None = None,
) -> AsyncGenerator[str, None]:
    """
    Streams SSE events as each LangGraph agent completes.
    Final event is emitted after critic_agent finishes.

    Event format (each line):
        data: {"event": "<agent_name>", "status": "done", "label": "...", "data": {...}}

    Final event:
        data: {"event": "done", "answer": "...", "is_valid": true, ...}
    """
    trace_id = None

    initial_state: GraphState = {
        "query":             query,
        "user_id":           user_id,
        "query_type":        None,
        "next_agent":        None,
        "plan":              None,
        "steps":             [],
        "retrieved_context": None,
        "tool_results":      {},
        "mcp_enrichment":    {},
        "live_stock_data":   None,
        "data_comparison":   None,
        "ticker":            None,
        "final_answer":      None,
        "is_valid":          None,
        "critique":          None,
        "errors":            [],
        "trace_id":          None,
    }

    try:
        # astream_events emits an event every time a node starts or finishes
        async for event in workflow.astream_events(initial_state, version="v2"):
            kind  = event.get("event", "")
            name  = event.get("name", "")

            # Fire when a node (agent) finishes
            if kind == "on_chain_end" and name in _AGENT_LABELS:
                output = event.get("data", {}).get("output", {})

                # Capture trace_id once router sets it
                if name == "router_agent":
                    trace_id = output.get("trace_id")

                payload: dict = {
                    "event":  name,
                    "status": "done",
                    "label":  _AGENT_LABELS[name],
                }

                # Attach useful data per agent
                if name == "router_agent":
                    payload["query_type"] = output.get("query_type")

                elif name == "yfinance_agent":
                    payload["ticker"] = output.get("ticker")

                elif name == "aggregator_agent":
                    payload["answer"] = output.get("final_answer")

                elif name == "critic_agent":
                    # Final agent — send the complete result
                    payload["answer"]    = output.get("final_answer")
                    payload["is_valid"]  = output.get("is_valid")
                    payload["critique"]  = output.get("critique")
                    payload["errors"]    = output.get("errors", [])
                    payload["trace_id"]  = trace_id or output.get("trace_id")

                yield f"data: {json.dumps(payload)}\n\n"

        # Sentinel event — tells the client the stream is fully complete
        yield f"data: {json.dumps({'event': 'stream_end'})}\n\n"

    except Exception as e:
        error_payload = {"event": "error", "message": str(e)}
        yield f"data: {json.dumps(error_payload)}\n\n"
