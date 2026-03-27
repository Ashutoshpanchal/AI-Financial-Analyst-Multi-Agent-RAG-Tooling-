"""
MCP Transport — mounts the MCP server into FastAPI via SSE.

Routes:
  GET  /mcp/sse        ← client opens SSE stream here
  POST /mcp/messages/  ← client sends tool calls here

Path resolution (mcp 1.x):
  SseServerTransport(endpoint) uses scope['root_path'] + endpoint to build
  the full URL it advertises to clients.
  When mounted at /mcp, Starlette sets root_path='/mcp', so:
    endpoint="/messages/"  →  client receives "/mcp/messages/"  ✓
    endpoint="/mcp/messages/"  →  client receives "/mcp/mcp/messages/"  ✗ (double prefix)

  Therefore: pass "/messages/" (relative to mount), not "/mcp/messages/".

handle_sse must return Response() to avoid NoneType error on client disconnect
(documented in mcp 1.26.0 source).
"""

from fastapi import FastAPI
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Mount, Route
from app.mcp.server import mcp


def mount_mcp(app: FastAPI) -> None:
    """
    Mounts MCP SSE endpoints into FastAPI at /mcp via a Starlette sub-app.
    """
    # "/messages/" is relative to the /mcp mount point
    # mcp will advertise root_path + "/messages/" = "/mcp/messages/" to clients
    sse = SseServerTransport("/messages/")

    server = mcp._mcp_server

    async def handle_sse(request: Request):
        async with sse.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            await server.run(
                streams[0],
                streams[1],
                server.create_initialization_options(),
            )
        # Return Response() to prevent NoneType error on client disconnect
        return Response()

    mcp_app = Starlette(routes=[
        Route("/sse", endpoint=handle_sse),
        Mount("/messages/", app=sse.handle_post_message),
    ])

    app.mount("/mcp", mcp_app)
