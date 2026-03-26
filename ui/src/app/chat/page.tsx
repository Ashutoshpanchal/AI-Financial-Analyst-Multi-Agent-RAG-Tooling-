"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Loader2, CheckCircle, XCircle, ChevronDown, ChevronRight, ExternalLink } from "lucide-react";
import { analyze, type AnalysisResult } from "@/lib/api";
import { cn } from "@/lib/utils";

const QUERY_TYPE_COLORS: Record<string, string> = {
  rag:         "bg-blue-500/20 text-blue-400 border-blue-500/30",
  computation: "bg-purple-500/20 text-purple-400 border-purple-500/30",
  hybrid:      "bg-orange-500/20 text-orange-400 border-orange-500/30",
  general:     "bg-gray-500/20 text-gray-400 border-gray-500/30",
};

const EXAMPLE_QUERIES = [
  "Calculate CAGR for revenue that grew from $50B to $95B over 5 years",
  "What is the P/E ratio if stock price is $150 and EPS is $6?",
  "Calculate EBITDA: net income $10M, interest $2M, taxes $3M, depreciation $1.5M, amortization $0.5M",
  "What is debt-to-equity if total debt is $80B and equity is $40B?",
  "Explain what EBITDA measures and why investors use it",
];

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  result?: AnalysisResult;
  loading?: boolean;
  error?: string;
}

function ResultCard({ result }: { result: AnalysisResult }) {
  const [showSteps, setShowSteps] = useState(false);
  const [showTools, setShowTools] = useState(false);
  const hasTools = Object.keys(result.tool_results || {}).length > 0;
  const hasSteps = result.steps?.length > 0;

  return (
    <div className="mt-3 space-y-3">
      {/* Query type badge */}
      {result.query_type && (
        <span className={cn("inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border", QUERY_TYPE_COLORS[result.query_type] || QUERY_TYPE_COLORS.general)}>
          {result.query_type}
        </span>
      )}

      {/* Plan */}
      {result.plan && (
        <p className="text-sm text-gray-400 italic border-l-2 border-gray-700 pl-3">{result.plan}</p>
      )}

      {/* Steps collapsible */}
      {hasSteps && (
        <div>
          <button
            onClick={() => setShowSteps(!showSteps)}
            className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-300 transition-colors"
          >
            {showSteps ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
            {result.steps.length} steps
          </button>
          {showSteps && (
            <ol className="mt-2 space-y-1 ml-3">
              {result.steps.map((step, i) => (
                <li key={i} className="flex gap-2 text-xs text-gray-400">
                  <span className="text-brand-500 font-mono shrink-0">{i + 1}.</span>
                  {step}
                </li>
              ))}
            </ol>
          )}
        </div>
      )}

      {/* Tool results collapsible */}
      {hasTools && (
        <div>
          <button
            onClick={() => setShowTools(!showTools)}
            className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-300 transition-colors"
          >
            {showTools ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
            {Object.keys(result.tool_results).length} tool{Object.keys(result.tool_results).length > 1 ? "s" : ""} used
          </button>
          {showTools && (
            <div className="mt-2 space-y-1 ml-3">
              {Object.entries(result.tool_results).map(([tool, output]) => (
                <div key={tool} className="bg-gray-800/60 rounded px-3 py-2">
                  <p className="text-xs font-mono text-purple-400 mb-1">{tool}</p>
                  <p className="text-xs text-gray-300">{output}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Critic verdict */}
      <div className="flex items-start gap-2">
        {result.is_valid === true && (
          <div className="flex items-center gap-1 text-xs text-green-400">
            <CheckCircle className="w-3 h-3" />
            <span>Validated</span>
          </div>
        )}
        {result.is_valid === false && (
          <div className="flex items-center gap-1 text-xs text-yellow-400">
            <XCircle className="w-3 h-3" />
            <span>{result.critique}</span>
          </div>
        )}
        {result.trace_id && (
          <a
            href={`${process.env.NEXT_PUBLIC_LANGFUSE_URL || "http://localhost:3000"}`}
            target="_blank"
            rel="noreferrer"
            className="ml-auto flex items-center gap-1 text-xs text-gray-600 hover:text-gray-400 transition-colors"
          >
            <ExternalLink className="w-3 h-3" />
            trace
          </a>
        )}
      </div>

      {/* Errors */}
      {result.errors?.length > 0 && (
        <div className="bg-red-900/20 border border-red-800/50 rounded px-3 py-2">
          {result.errors.map((e, i) => (
            <p key={i} className="text-xs text-red-400">{e}</p>
          ))}
        </div>
      )}
    </div>
  );
}

function MessageBubble({ msg }: { msg: Message }) {
  if (msg.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-xl bg-brand-600 text-white rounded-2xl rounded-tr-sm px-4 py-2.5 text-sm">
          {msg.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-3">
      <div className="w-7 h-7 rounded-full bg-gray-800 border border-gray-700 flex items-center justify-center shrink-0 mt-0.5">
        <span className="text-xs">AI</span>
      </div>
      <div className="flex-1 max-w-2xl">
        {msg.loading ? (
          <div className="flex items-center gap-2 text-gray-500 text-sm py-1">
            <Loader2 className="w-4 h-4 animate-spin" />
            Analyzing...
          </div>
        ) : msg.error ? (
          <div className="bg-red-900/20 border border-red-800/50 rounded-xl px-4 py-3 text-sm text-red-400">
            {msg.error}
          </div>
        ) : (
          <div className="bg-gray-800/50 rounded-2xl rounded-tl-sm px-4 py-3">
            <p className="text-sm text-gray-100 whitespace-pre-wrap leading-relaxed">{msg.content}</p>
            {msg.result && <ResultCard result={msg.result} />}
          </div>
        )}
      </div>
    </div>
  );
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function sendMessage(query: string) {
    if (!query.trim() || loading) return;
    setInput("");
    setLoading(true);

    const userMsg: Message = { id: Date.now().toString(), role: "user", content: query };
    const loadingMsg: Message = { id: Date.now().toString() + "_ai", role: "assistant", content: "", loading: true };
    setMessages((prev) => [...prev, userMsg, loadingMsg]);

    try {
      const result = await analyze(query);
      setMessages((prev) =>
        prev.map((m) =>
          m.id === loadingMsg.id
            ? { ...m, loading: false, content: result.answer, result }
            : m
        )
      );
    } catch (err) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === loadingMsg.id
            ? { ...m, loading: false, error: err instanceof Error ? err.message : "Request failed" }
            : m
        )
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col h-screen">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-800">
        <h1 className="text-lg font-semibold">Financial Analyst</h1>
        <p className="text-xs text-gray-500">Multi-agent RAG · powered by LangGraph</p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-5">
        {messages.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center gap-6 text-center">
            <div>
              <p className="text-gray-400 text-sm mb-1">Ask a financial question or try an example</p>
              <p className="text-gray-600 text-xs">Upload documents in the Documents tab to enable RAG queries</p>
            </div>
            <div className="grid gap-2 w-full max-w-lg">
              {EXAMPLE_QUERIES.map((q) => (
                <button
                  key={q}
                  onClick={() => sendMessage(q)}
                  className="text-left text-xs text-gray-400 bg-gray-800/50 hover:bg-gray-800 border border-gray-700/50 rounded-lg px-4 py-2.5 transition-colors"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((msg) => (
          <MessageBubble key={msg.id} msg={msg} />
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="px-6 py-4 border-t border-gray-800">
        <form
          onSubmit={(e) => { e.preventDefault(); sendMessage(input); }}
          className="flex gap-2"
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a financial question..."
            disabled={loading}
            className="flex-1 bg-gray-800 border border-gray-700 rounded-xl px-4 py-3 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-brand-600 disabled:opacity-50 transition-colors"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="bg-brand-600 hover:bg-brand-700 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-xl px-4 py-3 transition-colors"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          </button>
        </form>
      </div>
    </div>
  );
}
