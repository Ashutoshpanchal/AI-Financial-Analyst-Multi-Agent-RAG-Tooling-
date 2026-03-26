"""
MCP Transport — mounts the MCP server into FastAPI via SSE.

SSE (Server-Sent Events) transport:
  - MCP client connects to GET /mcp/sse  → opens a persistent event stream
  - MCP client sends messages to POST /mcp/messages
  - Server pushes tool results back through the SSE stream

This means your MCP server runs on the same port as FastAPI (8000).
No separate process needed for web clients.
"""

from fastapi import FastAPI
from app.mcp.server import mcp


def mount_mcp(app: FastAPI) -> None:
    """
    Attaches the MCP SSE router to the FastAPI app.
    After this, MCP is available at:
      - GET  /mcp/sse       ← client connects here first
      - POST /mcp/messages  ← client sends tool calls here
    """
    # Get the FastAPI router from fastmcp's SSE app
    mcp_app = mcp.get_asgi_app()
    app.mount("/mcp", mcp_app)
