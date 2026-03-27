"""
Shared Graph State — the single object that flows through every agent node.

Key concept:
    LangGraph passes this state from node to node.
    Each agent READS what it needs and WRITES only its own fields.
    No agent directly calls another agent — they only modify state.

Flow:
    user query
        → RouterAgent  sets: query_type, next_agent
        → PlannerAgent sets: plan, steps
        → (Step 5) RAGAgent       sets: retrieved_context
        → (Step 6) ComputationAgent sets: tool_results
        → (Step 8) AggregatorAgent  sets: final_answer
        → (Step 8) CriticAgent      sets: is_valid, critique
"""

from typing import Literal
from typing_extensions import TypedDict


# Possible query types the Router can classify
QueryType = Literal["rag", "computation", "hybrid", "general"]


class GraphState(TypedDict):
    # ── Input ──────────────────────────────────────────
    query: str                          # original user question
    user_id: str | None                 # for tracing + memory

    # ── Router output ───────────────────────────────────
    query_type: QueryType | None        # what kind of question is this?
    next_agent: str | None              # which agent handles it next

    # ── Planner output ──────────────────────────────────
    plan: str | None                    # reasoning plan as text
    steps: list[str]                    # ordered list of steps to execute

    # ── RAG output (Step 5) ─────────────────────────────
    retrieved_context: str | None       # relevant text from documents

    # ── Computation output (Step 6) ─────────────────────
    tool_results: dict                  # results from financial tools

    # ── MCP Enrichment output ───────────────────────────
    mcp_enrichment: dict                # MCP tool calls made + results (for tracing)

    # ── Final output (Step 8) ───────────────────────────
    final_answer: str | None            # assembled answer
    is_valid: bool | None               # critic verdict
    critique: str | None                # critic explanation

    # ── Metadata ────────────────────────────────────────
    errors: list[str]                   # any errors collected along the way
    trace_id: str | None                # Langfuse trace id for observability
