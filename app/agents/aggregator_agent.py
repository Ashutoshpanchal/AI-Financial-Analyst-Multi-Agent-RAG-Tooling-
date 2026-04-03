"""
Aggregator Agent — combines all upstream results into a final answer.

Reads from state:
  - query
  - plan + steps         (from planner)
  - retrieved_context    (from rag_agent)
  - tool_results         (from computation_agent)

Writes to state:
  - final_answer
"""

from langfuse.decorators import observe, langfuse_context
from app.workflows.state import GraphState
from app.models.router import get_model_router, TASK_MODEL_MAP


@observe(name="aggregator_agent", as_type="generation")
async def aggregator_agent(state: GraphState) -> GraphState:
    client = get_model_router().get("aggregation")
    langfuse_context.update_current_observation(
        model=TASK_MODEL_MAP["aggregation"],
        input={"query": state["query"]},
    )

    # Build a rich context block from all available results
    sections = []

    if state.get("plan"):
        sections.append(f"## Analysis Plan\n{state['plan']}")

    if state.get("retrieved_context"):
        sections.append(f"## Retrieved Document Context\n{state['retrieved_context']}")

    if state.get("tool_results"):
        tool_block = "\n".join(
            f"- **{tool}**: {result}"
            for tool, result in state["tool_results"].items()
        )
        sections.append(f"## Calculation Results\n{tool_block}")

    if state.get("live_stock_data"):
        live = state["live_stock_data"]
        def fmt(v):
            if v is None: return "N/A"
            if isinstance(v, float) and abs(v) >= 1e9: return f"${v/1e9:.2f}B"
            if isinstance(v, float) and abs(v) >= 1e6: return f"${v/1e6:.2f}M"
            return str(round(v, 4)) if isinstance(v, float) else str(v)

        live_lines = [
            f"- Price:          {fmt(live.get('price'))}",
            f"- P/E Ratio:      {fmt(live.get('pe_ratio'))}",
            f"- EPS:            {fmt(live.get('eps'))}",
            f"- Revenue:        {fmt(live.get('revenue'))}",
            f"- Net Income:     {fmt(live.get('net_income'))}",
            f"- Profit Margin:  {fmt(live.get('profit_margins'))}",
            f"- EBITDA:         {fmt(live.get('ebitda'))}",
            f"- Total Debt:     {fmt(live.get('total_debt'))}",
            f"- Market Cap:     {fmt(live.get('market_cap'))}",
            f"- Beta:           {fmt(live.get('beta'))}",
        ]
        sections.append(f"## Live Market Data ({live.get('ticker')} via Yahoo Finance)\n" + "\n".join(live_lines))

    if state.get("data_comparison"):
        comp = state["data_comparison"]
        sections.append(f"## Document vs Live Data Comparison\n{comp.get('summary', '')}")

    context_block = "\n\n".join(sections) if sections else "No additional context available."

    system_prompt = """You are a senior financial analyst. Your job is to synthesize information \
from multiple sources into a clear, accurate answer.

Rules you must always follow:
- Use live market data for current figures, document context for historical figures
- If both sources have the same metric, note differences (documents may be from a prior period)
- Cite source for every number: (live) or (document, page X)
- If tool results exist, include the formula used
- Never hallucinate numbers not present in the provided context, live data, or tool results
- Be concise but complete"""

    user_prompt = f"""**User Query:** {state["query"]}

**Available Information:**
{context_block}

Synthesize a comprehensive answer using the information above."""

    try:
        answer = await client.complete(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
        )
        return {**state, "final_answer": answer}
    except Exception as e:
        fallback = (
            f"Analysis complete. "
            f"Query type: {state.get('query_type')}. "
            f"Tools used: {list(state.get('tool_results', {}).keys())}."
        )
        return {
            **state,
            "final_answer": fallback,
            "errors": state.get("errors", []) + [f"AggregatorAgent error: {str(e)}"],
        }
