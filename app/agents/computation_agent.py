"""
Computation Agent — uses ModelRouter to get the right LLM, then calls financial tools.
"""

from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage, ToolMessage
from app.workflows.state import GraphState
from app.tools.registry import FINANCIAL_TOOLS
from app.models.router import get_model_router

tool_node = ToolNode(FINANCIAL_TOOLS)


async def computation_agent(state: GraphState) -> GraphState:
    router = get_model_router()
    llm = router.get("computation")._llm.bind_tools(FINANCIAL_TOOLS)

    system_prompt = """You are a financial calculation assistant.
Extract the required numbers from the query and call the appropriate tools.
Call ALL tools that are relevant. Do not guess or compute yourself — always use tools."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": state["query"]},
    ]

    if state.get("retrieved_context"):
        messages.append({
            "role": "user",
            "content": f"Use this context if it contains financial figures:\n{state['retrieved_context']}"
        })

    try:
        tool_results = {}
        response = await llm.ainvoke(messages)

        if response.tool_calls:
            result_state = await tool_node.ainvoke({"messages": [response]})
            for msg in result_state.get("messages", []):
                if isinstance(msg, ToolMessage):
                    tool_results[msg.name] = msg.content

        return {**state, "tool_results": tool_results}

    except Exception as e:
        return {
            **state,
            "tool_results": {},
            "errors": state.get("errors", []) + [f"ComputationAgent error: {str(e)}"],
        }
