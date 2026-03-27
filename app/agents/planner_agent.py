"""
Planner Agent — produces a step-by-step execution plan using gpt-4o via ModelRouter.
"""

from pydantic import BaseModel
from langfuse.decorators import observe, langfuse_context
from app.workflows.state import GraphState
from app.models.router import get_model_router, TASK_MODEL_MAP


class PlannerDecision(BaseModel):
    plan: str
    steps: list[str]


@observe(name="planner_agent", as_type="generation")
async def planner_agent(state: GraphState) -> GraphState:
    client = get_model_router().get("planning")
    langfuse_context.update_current_observation(
        model=TASK_MODEL_MAP["planning"],
        input={"query": state["query"], "query_type": state.get("query_type")},
    )

    context_parts = []
    if state.get("retrieved_context"):
        context_parts.append(f"Retrieved Context:\n{state['retrieved_context']}")
    if state.get("tool_results"):
        context_parts.append(f"Tool Results:\n{state['tool_results']}")

    context_block = "\n\n".join(context_parts) if context_parts else "No additional context yet."

    prompt = f"""You are a financial analysis planner.

Query:      {state["query"]}
Query Type: {state["query_type"]}
Context:    {context_block}

Produce a clear execution plan.
- plan:  1-2 sentence summary of the approach
- steps: ordered list of 2-5 concrete steps"""

    try:
        decision: PlannerDecision = await client.complete_structured(
            messages=[{"role": "user", "content": prompt}],
            schema=PlannerDecision,
        )
        return {**state, "plan": decision.plan, "steps": decision.steps}
    except Exception as e:
        return {
            **state,
            "plan": "Direct answer",
            "steps": ["Answer the query directly"],
            "errors": state.get("errors", []) + [f"PlannerAgent error: {str(e)}"],
        }
