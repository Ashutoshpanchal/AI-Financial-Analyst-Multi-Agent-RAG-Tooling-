"""
Router Agent — classifies query type using a cheap model (gpt-4o-mini via ModelRouter).
"""

from pydantic import BaseModel
from app.workflows.state import GraphState, QueryType
from app.models.router import get_model_router


class RouterDecision(BaseModel):
    query_type: QueryType
    reasoning: str
    next_agent: str


async def router_agent(state: GraphState) -> GraphState:
    client = get_model_router().get("routing")

    prompt = f"""You are a financial query classifier.

Classify the following query into exactly one type:
- rag:         requires searching financial documents (reports, filings, news)
- computation: requires financial calculations (ratios, returns, metrics)
- hybrid:      requires both document search AND calculations
- general:     general finance knowledge, no tools needed

Query: {state["query"]}

Return your classification and a brief reasoning."""

    try:
        decision: RouterDecision = await client.complete_structured(
            messages=[{"role": "user", "content": prompt}],
            schema=RouterDecision,
        )
        return {
            **state,
            "query_type": decision.query_type,
            "next_agent": decision.next_agent,
        }
    except Exception as e:
        return {
            **state,
            "query_type": "general",
            "next_agent": "planner_agent",
            "errors": state.get("errors", []) + [f"RouterAgent error: {str(e)}"],
        }
