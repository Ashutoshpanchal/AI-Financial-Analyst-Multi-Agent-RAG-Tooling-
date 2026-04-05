"""
MCP stdio entry point — for Claude Desktop and Claude Code CLI.

Claude Desktop spawns this as a subprocess and communicates
over stdin/stdout using the MCP protocol.

Usage (you don't run this manually — Claude Desktop runs it):
    python mcp_stdio.py

Claude Desktop config (~/.claude/claude_desktop_config.json):
{
  "mcpServers": {
    "financial-analyst": {
      "command": "python",
      "args": ["/absolute/path/to/mcp_stdio.py"],
      "env": {
        "OPENAI_API_KEY": "sk-...",
        "DATABASE_URL": "postgresql+asyncpg://postgres:postgres@localhost:5432/financial_analyst"
      }
    }
  }
}

After adding this config, restart Claude Desktop.
You will see "financial-analyst" in the MCP tools panel.
"""

from app.mcp.server import mcp

if __name__ == "__main__":
    mcp.run(transport="stdio")

