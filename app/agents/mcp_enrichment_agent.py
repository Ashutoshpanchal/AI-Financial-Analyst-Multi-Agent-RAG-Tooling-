"""
MCP Enrichment Agent — sits between RAG/Computation and Planner.

Responsibility:
    After RAG retrieves document context, this agent:
    1. Uses LLM to scan the context and identify which financial metrics can be calculated
    2. Calls MCP tools (pe_ratio, cagr, ebitda, etc.) with extracted numbers
    3. Merges results into tool_results before Planner sees them

Why this is useful:
    RAG gives raw document text.
    MCP Enrichment turns that text into calculated financial metrics automatically.
    Planner then has BOTH text context + computed numbers — richer plan.

Flow:
    rag_agent
        └── [mcp_enrichment_agent]  ← YOU ARE HERE
                └── planner_agent

Why MCP (not just calling functions directly)?
    MCP tools are the single source of truth for financial calculations.
    External clients (Claude Desktop, Cursor) use the same tools via MCP protocol.
    The enrichment agent uses the same registered tools — no duplication.

Skips gracefully when:
    - No retrieved_context in state (no document was retrieved)
    - LLM finds no extractable numbers in the context
    - query_type is "general" (no financial data involved)
"""

from pydantic import BaseModel
from langfuse.decorators import observe, langfuse_context
from app.workflows.state import GraphState
from app.models.router import get_model_router, TASK_MODEL_MAP
from app.mcp.server import (
    pe_ratio,
    cagr,
    ebitda,
    debt_to_equity,
    profit_margin,
)


# ── Schema for LLM structured output ──────────────────────────────────────────

class MCPToolCall(BaseModel):
    """Represents a single MCP tool call the LLM decided to make."""
    tool_name: str   # one of the 5 registered MCP tools
    inputs: dict     # exact kwargs to pass to the tool function
    reason: str      # why this calculation is relevant to the query


class MCPEnrichmentDecision(BaseModel):
    """LLM decision: which MCP tools to call given the context."""
    tool_calls: list[MCPToolCall]
    skip_reason: str | None = None  # set when no tools applicable


# ── Tool registry — maps name → callable MCP tool function ────────────────────

_MCP_TOOLS = {
    "pe_ratio":         pe_ratio,
    "cagr":             cagr,
    "ebitda":           ebitda,
    "debt_to_equity":   debt_to_equity,
    "profit_margin":    profit_margin,
}

_TOOL_SIGNATURES = """
Available MCP Financial Tools:
  pe_ratio(stock_price: float, earnings_per_share: float)
      → P/E ratio: how much investors pay per $1 of earnings

  cagr(start_value: float, end_value: float, years: float)
      → Compound Annual Growth Rate: smoothed annual growth

  ebitda(net_income: float, interest: float, taxes: float, depreciation: float, amortization: float)
      → EBITDA: core operating profitability

  debt_to_equity(total_debt: float, shareholders_equity: float)
      → D/E ratio: financial leverage / risk

  profit_margin(net_income: float, revenue: float)
      → Net profit margin: % of revenue that becomes profit
"""


# ── Agent ─────────────────────────────────────────────────────────────────────

@observe(name="mcp_enrichment_agent", as_type="generation")
async def mcp_enrichment_agent(state: GraphState) -> GraphState:
    langfuse_context.update_current_observation(model=TASK_MODEL_MAP["routing"])
    """
    LangGraph node — enriches state with MCP tool results extracted from document context.
    Runs between rag_agent (or parallel_agent) and planner_agent.
    """

    # Skip if no document context was retrieved — nothing to enrich from
    if not state.get("retrieved_context"):
        return {**state, "mcp_enrichment": {"skipped": "no retrieved context"}}

    # Skip for general queries — no financial data involved
    if state.get("query_type") == "general":
        return {**state, "mcp_enrichment": {"skipped": "general query, no enrichment needed"}}

    client = get_model_router().get("routing")   # lightweight model — just extraction

    prompt = f"""You are a financial data extractor. Look at the document context below and
identify any numbers that can be used to calculate financial metrics.

Query: {state["query"]}

Retrieved Document Context (first 2000 chars):
{str(state["retrieved_context"])[:2000]}

{_TOOL_SIGNATURES}

Instructions:
- Scan the context for numerical financial data (prices, revenues, earnings, debt, etc.)
- If you find inputs for any tool, include a tool_call with exact numeric values
- Only include tool_calls where ALL required inputs are clearly present in the context
- If no numbers are extractable, set tool_calls to [] and explain in skip_reason
- Do NOT guess or hallucinate numbers — only use values explicitly in the context

Return structured JSON only."""

    try:
        decision: MCPEnrichmentDecision = await client.complete_structured(
            messages=[{"role": "user", "content": prompt}],
            schema=MCPEnrichmentDecision,
        )

        # No tools to call
        if not decision.tool_calls:
            return {
                **state,
                "mcp_enrichment": {"skipped": decision.skip_reason or "no extractable numbers found"},
            }

        # ── Call each MCP tool ─────────────────────────────────────────────────
        enrichment_results = {}

        for tc in decision.tool_calls:
            tool_fn = _MCP_TOOLS.get(tc.tool_name)
            if tool_fn is None:
                enrichment_results[tc.tool_name] = f"Unknown tool: {tc.tool_name}"
                continue

            try:
                result = tool_fn(**tc.inputs)
                enrichment_results[tc.tool_name] = {
                    "result": result,
                    "reason": tc.reason,
                    "inputs": tc.inputs,
                }
            except Exception as tool_err:
                enrichment_results[tc.tool_name] = {
                    "error": str(tool_err),
                    "inputs": tc.inputs,
                }

        # Merge with any existing tool_results (computation_agent may have already written some)
        merged_tool_results = {**state.get("tool_results", {}), **enrichment_results}

        return {
            **state,
            "tool_results":   merged_tool_results,
            "mcp_enrichment": enrichment_results,   # separate field for tracing / debugging
        }

    except Exception as e:
        # Non-fatal — enrichment failed but pipeline continues
        return {
            **state,
            "mcp_enrichment": {"error": str(e)},
            "errors": state.get("errors", []) + [f"MCPEnrichmentAgent error: {str(e)}"],
        }
