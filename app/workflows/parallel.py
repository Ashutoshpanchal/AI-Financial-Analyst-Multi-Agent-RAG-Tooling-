"""
Parallel execution node — runs RAG and Computation agents concurrently.

Used only for hybrid queries.

Key concept:
    asyncio.gather runs both agents at the same time.
    Each returns an updated state dict.
    We merge them — RAG writes retrieved_context, Computation writes tool_results.
    No race condition because they write to different state keys.

Without parallel:  RAG (2s) + Computation (2s) = 4s total
With parallel:     RAG (2s) || Computation (2s) = 2s total
"""

import asyncio
from app.workflows.state import GraphState
from app.agents.rag_agent import rag_agent
from app.agents.computation_agent import computation_agent


async def parallel_rag_and_computation(state: GraphState) -> GraphState:
    """
    Runs rag_agent and computation_agent concurrently.
    Merges their outputs into a single state update.
    """
    # Both agents receive the same input state and run simultaneously
    rag_result, comp_result = await asyncio.gather(
        rag_agent(state),
        computation_agent(state),
    )

    # Merge: each agent only wrote to its own keys so no conflicts
    merged_errors = (
        state.get("errors", []) +
        rag_result.get("errors", []) +
        comp_result.get("errors", [])
    )

    return {
        **state,
        "retrieved_context": rag_result.get("retrieved_context"),
        "tool_results": comp_result.get("tool_results", {}),
        "errors": merged_errors,
    }
