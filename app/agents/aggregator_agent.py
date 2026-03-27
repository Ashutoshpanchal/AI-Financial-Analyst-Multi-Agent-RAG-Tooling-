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

    context_block = "\n\n".join(sections) if sections else "No additional context available."

    prompt = f"""You are a financial analyst synthesizing a comprehensive answer.

**User Query:** {state["query"]}

**Available Information:**
{context_block}

Instructions:
- Directly answer the user's question
- Reference specific numbers and calculations where available
- If tool results exist, include them with their formulas
- If document context exists, cite the source
- Be concise but complete
- Do NOT hallucinate numbers not present in the context or tool results"""

    try:
        answer = await client.complete(
            messages=[{"role": "user", "content": prompt}],
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
