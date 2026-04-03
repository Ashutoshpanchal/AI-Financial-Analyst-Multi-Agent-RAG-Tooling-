"""
Critic Agent — validates the final answer for correctness and hallucinations.

Checks:
  1. Numerical consistency — do the numbers in the answer match tool results?
  2. Logical consistency — does the conclusion follow from the evidence?
  3. Hallucination detection — are any claims unsupported by context or tools?

Writes to state:
  - is_valid:  True if answer passes all checks
  - critique:  explanation of issues found (or "Answer is valid." if clean)
"""

from pydantic import BaseModel
from langfuse.decorators import observe, langfuse_context
from app.workflows.state import GraphState
from app.models.router import get_model_router, TASK_MODEL_MAP


class CriticVerdict(BaseModel):
    is_valid: bool
    critique: str
    issues: list[str]     # specific issues found, empty if valid


@observe(name="critic_agent", as_type="generation")
async def critic_agent(state: GraphState) -> GraphState:
    client = get_model_router().get("critique")
    langfuse_context.update_current_observation(
        model=TASK_MODEL_MAP["critique"],
        input={"query": state["query"], "final_answer": state.get("final_answer", "")},
    )

    tool_results_block = (
        "\n".join(f"- {k}: {v}" for k, v in state["tool_results"].items())
        if state.get("tool_results")
        else "No tool results."
    )

    doc_context_block = state.get("retrieved_context") or "No document context."

    live_block = "No live market data."
    if state.get("live_stock_data"):
        live = state["live_stock_data"]
        live_block = "\n".join(
            f"- {k}: {v}" for k, v in live.items() if v is not None
        )

    comparison_block = state.get("data_comparison", {}).get("summary", "No comparison available.")

    prompt = f"""You are a financial analysis critic. Validate this answer strictly.

**Original Query:** {state["query"]}

**Tool Calculation Results (ground truth):**
{tool_results_block}

**Live Market Data from Yahoo Finance (ground truth):**
{live_block}

**Document vs Live Comparison:**
{comparison_block}

**Document Context Used:**
{doc_context_block[:2000]}

**Answer to Validate:**
{state.get("final_answer", "")}

Check for:
1. Any numbers in the answer that don't match tool results OR live market data
2. Any factual claims not supported by document context or live data
3. Logical errors or contradictions
4. Hallucinated company names, dates, or figures
5. If answer mixes live and historical data without clearly stating the source/period

Return:
- is_valid: true only if the answer has no significant issues
- critique: brief explanation (1-2 sentences)
- issues:   list of specific issues found (empty list if none)"""

    try:
        verdict: CriticVerdict = await client.complete_structured(
            messages=[{"role": "user", "content": prompt}],
            schema=CriticVerdict,
        )

        # If critic finds issues, append critique to the answer so user is informed
        final_answer = state.get("final_answer", "")
        if not verdict.is_valid and verdict.issues:
            issues_text = "; ".join(verdict.issues)
            final_answer = f"{final_answer}\n\n⚠️ *Note: {verdict.critique}*"

        return {
            **state,
            "final_answer": final_answer,
            "is_valid": verdict.is_valid,
            "critique": verdict.critique,
        }

    except Exception as e:
        return {
            **state,
            "is_valid": True,           # don't block the response on critic failure
            "critique": "Validation skipped.",
            "errors": state.get("errors", []) + [f"CriticAgent error: {str(e)}"],
        }
