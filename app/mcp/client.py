"""
MCP Client — lets your agents consume external MCP servers.

Use this when you want to pull data from external MCP servers
(market data, SEC filings, news APIs) into your RAG or computation agents.

Example external MCP servers you could connect to:
  - filesystem MCP server  → read local financial data files
  - fetch MCP server       → fetch live financial data from URLs
  - your own MCP servers   → chain multiple financial analyst instances

Usage inside an agent:
    async with MCPClient("http://external-mcp-server/sse") as client:
        tools = await client.list_tools()
        result = await client.call_tool("get_stock_price", {"ticker": "AAPL"})
"""

from contextlib import asynccontextmanager
from mcp import ClientSession
from mcp.client.sse import sse_client


class MCPClient:
    """
    Async context manager for connecting to an external MCP server via SSE.

    Example:
        async with MCPClient("http://market-data-server/mcp/sse") as client:
            result = await client.call_tool("get_price", {"ticker": "AAPL"})
            print(result)
    """

    def __init__(self, server_url: str):
        self.server_url = server_url
        self._session: ClientSession | None = None
        self._context = None

    async def __aenter__(self) -> "MCPClient":
        self._context = sse_client(self.server_url)
        read, write = await self._context.__aenter__()
        self._session = ClientSession(read, write)
        await self._session.__aenter__()
        await self._session.initialize()
        return self

    async def __aexit__(self, *args) -> None:
        if self._session:
            await self._session.__aexit__(*args)
        if self._context:
            await self._context.__aexit__(*args)

    async def list_tools(self) -> list[dict]:
        """List all tools available on the remote MCP server."""
        result = await self._session.list_tools()
        return [
            {"name": t.name, "description": t.description}
            for t in result.tools
        ]

    async def list_resources(self) -> list[dict]:
        """List all resources available on the remote MCP server."""
        result = await self._session.list_resources()
        return [
            {"uri": str(r.uri), "name": r.name}
            for r in result.resources
        ]

    async def call_tool(self, tool_name: str, arguments: dict) -> str:
        """Call a tool on the remote MCP server and return the text result."""
        result = await self._session.call_tool(tool_name, arguments)
        # Extract text content from the result
        for content in result.content:
            if hasattr(content, "text"):
                return content.text
        return str(result.content)

    async def read_resource(self, uri: str) -> str:
        """Read a resource from the remote MCP server."""
        result = await self._session.read_resource(uri)
        for content in result.contents:
            if hasattr(content, "text"):
                return content.text
        return str(result.contents)


async def call_self(tool_name: str, arguments: dict, base_url: str = "http://localhost:8000") -> str:
    """
    Convenience function to call a tool on THIS server's MCP endpoint.
    Useful for testing and agent-to-agent calls within the same deployment.
    """
    async with MCPClient(f"{base_url}/mcp/sse") as client:
        return await client.call_tool(tool_name, arguments)
