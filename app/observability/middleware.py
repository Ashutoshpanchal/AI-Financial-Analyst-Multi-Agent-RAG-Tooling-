"""
FastAPI middleware that auto-creates a Langfuse trace for every request.

What it tracks per request:
- method + path
- status code
- latency (ms)
- errors

This runs automatically — no need to manually add tracing in every route.
"""

import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from app.observability.tracer import get_langfuse_client


class LangfuseMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip health checks — no need to trace them
        if request.url.path == "/api/v1/health":
            return await call_next(request)

        client = get_langfuse_client()
        start_time = time.time()

        # Create a trace at the start of the request
        trace = client.trace(
            name=f"{request.method} {request.url.path}",
            input={
                "method": request.method,
                "path": str(request.url.path),
                "query_params": dict(request.query_params),
            },
        )

        # Attach trace_id to request state so route handlers can access it
        request.state.trace_id = trace.id
        request.state.trace = trace

        try:
            response = await call_next(request)
            latency_ms = round((time.time() - start_time) * 1000, 2)

            trace.update(
                output={"status_code": response.status_code},
                metadata={"latency_ms": latency_ms},
            )
            return response

        except Exception as exc:
            latency_ms = round((time.time() - start_time) * 1000, 2)
            trace.update(
                output={"error": str(exc)},
                metadata={"latency_ms": latency_ms},
                status_message="error",
            )
            raise exc

        finally:
            client.flush()
