"""
Langfuse tracer — central observability utility.

Concepts:
- Trace:    one complete request (e.g. user asks a question)
- Span:     one step inside a trace (e.g. RAG retrieval, LLM call)
- Generation: a specific LLM call — tracks model, tokens, cost

Hierarchy:
  Trace
  └── Span (rag_retrieval)
  └── Generation (openai_call)  ← tracks tokens + cost automatically
"""

from functools import lru_cache
from langfuse import Langfuse
from app.config.settings import get_settings

settings = get_settings()


@lru_cache
def get_langfuse_client() -> Langfuse:
    """
    Returns a cached Langfuse client.
    Called once — reused across all requests.
    """
    return Langfuse(
        secret_key=settings.langfuse_secret_key,
        public_key=settings.langfuse_public_key,
        host=settings.langfuse_host,
    )


class TraceContext:
    """
    Wraps a single Langfuse trace for one request lifecycle.

    Usage:
        ctx = TraceContext(name="analyze_query", user_id="user_123")
        ctx.start(input={"query": "What is Apple's PE ratio?"})

        span = ctx.span("rag_retrieval")
        span.end(output={"chunks": [...]})

        ctx.end(output={"answer": "..."})
    """

    def __init__(self, name: str, user_id: str | None = None):
        self.client = get_langfuse_client()
        self.name = name
        self.user_id = user_id
        self.trace = None

    def start(self, input: dict) -> "TraceContext":
        """Create the root trace for this request."""
        self.trace = self.client.trace(
            name=self.name,
            input=input,
            user_id=self.user_id,
        )
        return self

    def span(self, name: str, input: dict | None = None):
        """
        Create a child span inside this trace.
        Use for non-LLM steps: retrieval, tool calls, parsing.
        """
        if not self.trace:
            raise RuntimeError("Call .start() before creating spans")
        return self.trace.span(name=name, input=input or {})

    def generation(
        self,
        name: str,
        model: str,
        prompt: str,
        input: dict | None = None,
    ):
        """
        Create a Generation — a tracked LLM call.
        Langfuse uses model name to automatically estimate token cost.
        """
        if not self.trace:
            raise RuntimeError("Call .start() before creating generations")
        return self.trace.generation(
            name=name,
            model=model,
            input=input or {"prompt": prompt},
        )

    def end(self, output: dict, status: str = "success") -> None:
        """Finalize the trace with the final output."""
        if self.trace:
            self.trace.update(output=output, status_message=status)
            # Flush ensures data is sent even in async contexts
            self.client.flush()


