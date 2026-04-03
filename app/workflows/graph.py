"""
LangGraph workflow — final complete graph.

Full flow:
    START
      └── router_agent  (classify query)
            ├── general     → planner → aggregator → critic → END
            ├── rag         → rag_agent → yfinance_agent → mcp_enrichment → planner → aggregator → critic → END
            ├── computation → computation_agent → yfinance_agent → mcp_enrichment → planner → aggregator → critic → END
            └── hybrid      → parallel(rag + computation) → yfinance_agent → mcp_enrichment → planner → aggregator → critic → END

yFinance node:
    Sits between data-gathering agents and mcp_enrichment.
    Detects ticker from query, fetches live Yahoo Finance data,
    compares live numbers vs uploaded document numbers.

MCP Enrichment node:
    Sits between yfinance_agent and planner.
    Scans retrieved context for financial numbers, auto-calls MCP tools (pe_ratio, cagr, etc.)
    Planner receives raw context + live data + pre-computed metrics.
"""

from langgraph.graph import StateGraph, START, END
try:
    from langgraph.types import RetryPolicy
except ImportError:
    from langgraph.pregel import RetryPolicy
from app.workflows.state import GraphState
from app.agents.router_agent import router_agent
from app.agents.planner_agent import planner_agent
from app.agents.rag_agent import rag_agent
from app.agents.computation_agent import computation_agent
from app.agents.aggregator_agent import aggregator_agent
from app.agents.critic_agent import critic_agent
from app.agents.mcp_enrichment_agent import mcp_enrichment_agent
from app.agents.yfinance_agent import yfinance_agent
from app.workflows.parallel import parallel_rag_and_computation


def route_after_router(state: GraphState) -> str:
    query_type = state.get("query_type", "general")
    routes = {
        "rag":         "rag_agent",
        "computation": "computation_agent",
        "hybrid":      "parallel_agent",
        "general":     "planner_agent",
    }
    return routes.get(query_type, "planner_agent")


def build_graph() -> StateGraph:
    builder = StateGraph(GraphState)

    # Retry for transient API failures (rate limits, timeouts)
    # max_attempts=3 → tries 3 times total
    # initial_interval=1.0, backoff_factor=2.0 → waits 1s, 2s between retries
    _llm_retry    = RetryPolicy(max_attempts=3, initial_interval=1.0, backoff_factor=2.0)
    _quick_retry  = RetryPolicy(max_attempts=2, initial_interval=0.5, backoff_factor=1.5)

    # ── Nodes ─────────────────────────────────────────────────────────────────
    builder.add_node("router_agent",         router_agent,                retry=_quick_retry)
    builder.add_node("rag_agent",            rag_agent,                   retry=_quick_retry)
    builder.add_node("computation_agent",    computation_agent,           retry=_llm_retry)
    builder.add_node("parallel_agent",       parallel_rag_and_computation,retry=_quick_retry)
    builder.add_node("yfinance_agent",       yfinance_agent,              retry=_quick_retry)
    builder.add_node("mcp_enrichment_agent", mcp_enrichment_agent,        retry=_llm_retry)
    builder.add_node("planner_agent",        planner_agent,               retry=_llm_retry)
    builder.add_node("aggregator_agent",     aggregator_agent,            retry=_llm_retry)
    builder.add_node("critic_agent",         critic_agent,                retry=_llm_retry)

    # ── Edges ─────────────────────────────────────────────────────────────────
    builder.add_edge(START, "router_agent")

    builder.add_conditional_edges(
        "router_agent",
        route_after_router,
        {
            "rag_agent":          "rag_agent",
            "computation_agent":  "computation_agent",
            "parallel_agent":     "parallel_agent",
            "planner_agent":      "planner_agent",
        }
    )

    # All data-gathering paths → yFinance → MCP Enrichment → Planner
    builder.add_edge("rag_agent",            "yfinance_agent")
    builder.add_edge("computation_agent",    "yfinance_agent")
    builder.add_edge("parallel_agent",       "yfinance_agent")
    builder.add_edge("yfinance_agent",       "mcp_enrichment_agent")
    builder.add_edge("mcp_enrichment_agent", "planner_agent")

    # Planner → Aggregator → Critic → END
    builder.add_edge("planner_agent",        "aggregator_agent")
    builder.add_edge("aggregator_agent",     "critic_agent")
    builder.add_edge("critic_agent",         END)

    return builder.compile()


workflow = build_graph()
