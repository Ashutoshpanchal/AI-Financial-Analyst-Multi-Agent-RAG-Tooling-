"""
MCP status endpoint — introspect what the MCP server exposes.
Useful for debugging and for clients discovering available tools.
"""

from fastapi import APIRouter
from app.mcp.client import call_self, MCPClient

router = APIRouter()


@router.get("/mcp/status")
async def mcp_status() -> dict:
    """
    Lists all tools, resources, and prompts exposed by the MCP server.
    Hit this endpoint to verify MCP is working correctly.
    """
    try:
        async with MCPClient("http://localhost:8000/mcp/sse") as client:
            tools = await client.list_tools()
            resources = await client.list_resources()

        return {
            "status": "ok",
            "mcp_endpoint": "http://localhost:8000/mcp/sse",
            "tools": tools,
            "resources": resources,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "mcp_endpoint": "http://localhost:8000/mcp/sse",
        }
