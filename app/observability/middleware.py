"""
Pure ASGI middleware that auto-creates a Langfuse trace for every request.

Why pure ASGI instead of BaseHTTPMiddleware:
    BaseHTTPMiddleware buffers responses and uses body streaming assertions
    that break SSE (Server-Sent Events) connections like /mcp/sse.
    A pure ASGI middleware wraps only the `send` callable — it never
    buffers the body, so SSE streams pass through untouched.

What it tracks per request:
- method + path
- status code
- latency (ms)
- errors
"""

import time
from app.observability.tracer import get_langfuse_client

_SKIP_PREFIXES = ("/mcp",)
_SKIP_EXACT = {"/api/v1/health"}


class LangfuseMiddleware:
    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        # Only instrument HTTP requests
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path: str = scope.get("path", "")

        # Skip health checks and MCP SSE endpoints
        if path in _SKIP_EXACT or any(path.startswith(p) for p in _SKIP_PREFIXES):
            await self.app(scope, receive, send)
            return

        client = get_langfuse_client()
        start_time = time.time()
        method: str = scope.get("method", "")
        query_string: str = scope.get("query_string", b"").decode()

        trace = client.trace(
            name=f"{method} {path}",
            input={
                "method": method,
                "path": path,
                "query_params": query_string,
            },
        )

        status_code: int | None = None

        async def send_wrapper(message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 0)
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
            latency_ms = round((time.time() - start_time) * 1000, 2)
            trace.update(
                output={"status_code": status_code},
                metadata={"latency_ms": latency_ms},
            )
        except Exception as exc:
            latency_ms = round((time.time() - start_time) * 1000, 2)
            trace.update(
                output={"error": str(exc)},
                metadata={"latency_ms": latency_ms},
                status_message="error",
            )
            raise
        finally:
            client.flush()
