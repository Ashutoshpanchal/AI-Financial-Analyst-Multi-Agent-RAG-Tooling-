"""
RAG Agent — retrieves relevant document context for the query.

Responsibility:
    1. Use the retriever to find relevant chunks from pgvector
    2. Write retrieved_context into state
    3. Downstream agents (aggregator) will use this context to answer

Key concept (why separate retrieval from answering?):
    The RAG agent only RETRIEVES — it does not answer.
    The aggregator agent (Step 8) combines retrieved context
    with tool results to produce the final answer.
    This separation makes each agent testable in isolation.
"""

from langchain_openai import ChatOpenAI
from app.workflows.state import GraphState
from app.rag.retriever import retrieve
from app.db.session import AsyncSessionLocal
from app.config.settings import get_settings

settings = get_settings()


async def rag_agent(state: GraphState) -> GraphState:
    """
    LangGraph node — retrieves document context for the query.
    Only runs for query_type in ["rag", "hybrid"].
    """
    query = state["query"]

    try:
        # Open a DB session for this retrieval
        async with AsyncSessionLocal() as db:
            context = await retrieve(query=query, db=db, top_k=5)

        return {
            **state,
            "retrieved_context": context,
        }

    except Exception as e:
        return {
            **state,
            "retrieved_context": None,
            "errors": state.get("errors", []) + [f"RAGAgent error: {str(e)}"],
        }
