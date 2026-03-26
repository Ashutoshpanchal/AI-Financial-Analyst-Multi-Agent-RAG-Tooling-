"use client";

import { useEffect, useState } from "react";
import { Wrench, Database, RefreshCw, Loader2, CheckCircle, XCircle } from "lucide-react";
import { getMCPStatus, type MCPStatus } from "@/lib/api";
import { cn } from "@/lib/utils";

export default function MCPPage() {
  const [status, setStatus] = useState<MCPStatus | null>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    try {
      const data = await getMCPStatus();
      setStatus(data);
    } catch {
      setStatus({ status: "error", mcp_endpoint: "", tools: [], resources: [], error: "Could not reach MCP server" });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  const isOk = status?.status === "ok";

  return (
    <div className="p-6 max-w-3xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-lg font-semibold">MCP Tools</h1>
          <p className="text-xs text-gray-500 mt-1">Model Context Protocol — tools exposed to Claude Desktop and other MCP clients</p>
        </div>
        <button
          onClick={load}
          disabled={loading}
          className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-gray-200 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-lg px-3 py-1.5 transition-colors disabled:opacity-50"
        >
          <RefreshCw className={cn("w-3 h-3", loading && "animate-spin")} />
          Refresh
        </button>
      </div>

      {loading && (
        <div className="flex items-center gap-2 text-gray-500 text-sm">
          <Loader2 className="w-4 h-4 animate-spin" />
          Connecting to MCP server...
        </div>
      )}

      {status && !loading && (
        <>
          {/* Status badge */}
          <div className={cn(
            "flex items-center gap-2 px-4 py-3 rounded-xl border text-sm mb-6",
            isOk ? "bg-green-900/20 border-green-800/50 text-green-400" : "bg-red-900/20 border-red-800/50 text-red-400"
          )}>
            {isOk ? <CheckCircle className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
            <span className="font-medium">{isOk ? "MCP Server Online" : "MCP Server Offline"}</span>
            {status.mcp_endpoint && (
              <span className="ml-auto text-xs font-mono text-gray-500">{status.mcp_endpoint}</span>
            )}
          </div>

          {status.error && (
            <p className="text-xs text-red-400 mb-4">{status.error}</p>
          )}

          {/* Tools */}
          {status.tools.length > 0 && (
            <section className="mb-6">
              <h2 className="flex items-center gap-2 text-sm font-medium text-gray-300 mb-3">
                <Wrench className="w-4 h-4 text-purple-400" />
                Tools ({status.tools.length})
              </h2>
              <div className="space-y-2">
                {status.tools.map((tool) => (
                  <div key={tool.name} className="bg-gray-800/50 border border-gray-700/50 rounded-xl px-4 py-3">
                    <p className="text-sm font-mono text-purple-400">{tool.name}</p>
                    <p className="text-xs text-gray-500 mt-1 leading-relaxed">{tool.description}</p>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Resources */}
          {status.resources.length > 0 && (
            <section className="mb-6">
              <h2 className="flex items-center gap-2 text-sm font-medium text-gray-300 mb-3">
                <Database className="w-4 h-4 text-blue-400" />
                Resources ({status.resources.length})
              </h2>
              <div className="space-y-2">
                {status.resources.map((r) => (
                  <div key={r.uri} className="bg-gray-800/50 border border-gray-700/50 rounded-xl px-4 py-3">
                    <p className="text-sm font-mono text-blue-400">{r.uri}</p>
                    <p className="text-xs text-gray-500 mt-1">{r.name}</p>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Claude Desktop config */}
          <section>
            <h2 className="text-sm font-medium text-gray-300 mb-3">Connect Claude Desktop</h2>
            <div className="bg-gray-900 border border-gray-700 rounded-xl p-4">
              <p className="text-xs text-gray-500 mb-2">Add to ~/.claude/claude_desktop_config.json</p>
              <pre className="text-xs text-gray-300 overflow-x-auto leading-relaxed">{`{
  "mcpServers": {
    "financial-analyst": {
      "command": "python",
      "args": ["/path/to/project/mcp_stdio.py"],
      "env": {
        "OPENAI_API_KEY": "sk-...",
        "DATABASE_URL": "postgresql+asyncpg://..."
      }
    }
  }
}`}</pre>
            </div>
          </section>
        </>
      )}
    </div>
  );
}
