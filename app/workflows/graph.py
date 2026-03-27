"""
LangGraph workflow — final complete graph.

Full flow:
    START
      └── router_agent  (classify query)
            ├── general     → planner → aggregator → critic → END
            ├── rag         → rag_agent → mcp_enrichment → planner → aggregator → critic → END
            ├── computation → computation_agent → mcp_enrichment → planner → aggregator → critic → END
            └── hybrid      → parallel(rag + computation) → mcp_enrichment → planner → aggregator → critic → END

MCP Enrichment node:
    Sits between data-gathering agents and planner.
    Scans retrieved context for financial numbers, auto-calls MCP tools (pe_ratio, cagr, etc.)
    Planner receives both raw context + pre-computed metrics.
"""

from langgraph.graph import StateGraph, START, END
from app.workflows.state import GraphState
from app.agents.router_agent import router_agent
from app.agents.planner_agent import planner_agent
from app.agents.rag_agent import rag_agent
from app.agents.computation_agent import computation_agent
from app.agents.aggregator_agent import aggregator_agent
from app.agents.critic_agent import critic_agent
from app.agents.mcp_enrichment_agent import mcp_enrichment_agent
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

    # ── Nodes ─────────────────────────────────────────────────────────────────
    builder.add_node("router_agent",         router_agent)
    builder.add_node("rag_agent",            rag_agent)
    builder.add_node("computation_agent",    computation_agent)
    builder.add_node("parallel_agent",       parallel_rag_and_computation)
    builder.add_node("mcp_enrichment_agent", mcp_enrichment_agent)   # ← NEW
    builder.add_node("planner_agent",        planner_agent)
    builder.add_node("aggregator_agent",     aggregator_agent)
    builder.add_node("critic_agent",         critic_agent)

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

    # All data-gathering paths → MCP Enrichment → Planner
    builder.add_edge("rag_agent",            "mcp_enrichment_agent")
    builder.add_edge("computation_agent",    "mcp_enrichment_agent")
    builder.add_edge("parallel_agent",       "mcp_enrichment_agent")
    builder.add_edge("mcp_enrichment_agent", "planner_agent")

    # Planner → Aggregator → Critic → END
    builder.add_edge("planner_agent",        "aggregator_agent")
    builder.add_edge("aggregator_agent",     "critic_agent")
    builder.add_edge("critic_agent",         END)

    return builder.compile()


workflow = build_graph()
