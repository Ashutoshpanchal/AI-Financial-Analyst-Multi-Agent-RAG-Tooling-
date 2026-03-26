"use client";

import { useState } from "react";
import { Play, CheckCircle, XCircle, Clock, Loader2, ChevronDown, ChevronRight } from "lucide-react";
import { runEval, type EvalResult, type EvalRecord } from "@/lib/api";
import { cn } from "@/lib/utils";

function ScoreBadge({ pass }: { pass: boolean }) {
  return (
    <span className={cn(
      "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium",
      pass ? "bg-green-500/20 text-green-400" : "bg-red-500/20 text-red-400"
    )}>
      {pass ? <CheckCircle className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
      {pass ? "PASS" : "FAIL"}
    </span>
  );
}

function RecordRow({ r }: { r: EvalRecord }) {
  const [open, setOpen] = useState(false);
  const pass = r.scores.passed;

  return (
    <div className={cn("border rounded-xl overflow-hidden transition-colors", pass ? "border-gray-700/50" : "border-red-800/40")}>
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-gray-800/30 transition-colors"
      >
        {open ? <ChevronDown className="w-3.5 h-3.5 text-gray-500 shrink-0" /> : <ChevronRight className="w-3.5 h-3.5 text-gray-500 shrink-0" />}
        <ScoreBadge pass={pass} />
        <span className="text-xs font-mono text-gray-500 shrink-0">{r.id}</span>
        <span className="text-sm text-gray-300 flex-1 truncate">{r.query}</span>
        <div className="flex items-center gap-1 shrink-0 text-xs text-gray-600">
          <Clock className="w-3 h-3" />
          {r.latency_ms}ms
        </div>
      </button>

      {open && (
        <div className="px-4 pb-4 pt-1 border-t border-gray-800 space-y-3">
          {r.error ? (
            <p className="text-xs text-red-400">{r.error}</p>
          ) : (
            <>
              {/* Score breakdown */}
              <div className="flex flex-wrap gap-2">
                {[
                  ["Query Type", r.scores.query_type_match],
                  ["Tool Used",  r.scores.tool_used],
                  ["Answer Contains", r.scores.answer_contains],
                  ["Critic Valid", r.scores.is_valid],
                ].map(([label, value]) => value !== undefined && (
                  <div key={label as string} className={cn(
                    "flex items-center gap-1 px-2 py-0.5 rounded text-xs",
                    value ? "bg-green-900/30 text-green-400" : "bg-red-900/30 text-red-400"
                  )}>
                    {value ? <CheckCircle className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
                    {label as string}
                  </div>
                ))}
              </div>

              {/* Answer */}
              {r.answer && (
                <div>
                  <p className="text-xs text-gray-600 mb-1">Answer</p>
                  <p className="text-xs text-gray-300 bg-gray-800/50 rounded-lg px-3 py-2 leading-relaxed">{r.answer}</p>
                </div>
              )}

              {/* Tools used */}
              {r.tool_results && r.tool_results.length > 0 && (
                <div className="flex gap-2 flex-wrap">
                  {r.tool_results.map((t) => (
                    <span key={t} className="text-xs font-mono bg-purple-900/30 text-purple-400 px-2 py-0.5 rounded">{t}</span>
                  ))}
                </div>
              )}

              {/* Tags */}
              {r.tags?.length > 0 && (
                <div className="flex gap-1">
                  {r.tags.map((t) => (
                    <span key={t} className="text-xs text-gray-600 bg-gray-800 px-1.5 py-0.5 rounded">{t}</span>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}

export default function EvalPage() {
  const [result, setResult] = useState<EvalResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleRun() {
    setLoading(true);
    setError(null);
    try {
      const data = await runEval();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Eval failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="p-6 max-w-3xl">
      <div className="mb-6">
        <h1 className="text-lg font-semibold">Evaluation</h1>
        <p className="text-xs text-gray-500 mt-1">Run the test suite against the full multi-agent pipeline. Results are logged to Langfuse.</p>
      </div>

      {/* Run button */}
      <button
        onClick={handleRun}
        disabled={loading}
        className="flex items-center gap-2 bg-brand-600 hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-xl px-5 py-2.5 text-sm font-medium transition-colors"
      >
        {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
        {loading ? "Running..." : "Run Evaluation"}
      </button>

      {error && (
        <div className="mt-4 bg-red-900/20 border border-red-800/50 rounded-xl px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {/* Summary stats */}
      {result && (
        <>
          <div className="mt-6 grid grid-cols-4 gap-3">
            {[
              { label: "Total",      value: result.total,                   color: "text-gray-200" },
              { label: "Passed",     value: result.passed,                  color: "text-green-400" },
              { label: "Failed",     value: result.failed,                  color: "text-red-400" },
              { label: "Pass Rate",  value: `${result.pass_rate}%`,         color: "text-brand-400" },
            ].map(({ label, value, color }) => (
              <div key={label} className="bg-gray-800/50 border border-gray-700/50 rounded-xl px-4 py-3">
                <p className="text-xs text-gray-500">{label}</p>
                <p className={cn("text-2xl font-semibold mt-1", color)}>{value}</p>
              </div>
            ))}
          </div>

          <div className="mt-2 text-xs text-gray-600 flex items-center gap-1">
            <Clock className="w-3 h-3" />
            Avg latency: {result.avg_latency_ms}ms
          </div>

          {/* Results */}
          <div className="mt-5 space-y-2">
            <h2 className="text-sm font-medium text-gray-400">Results</h2>
            {result.results.map((r) => <RecordRow key={r.id} r={r} />)}
          </div>
        </>
      )}
    </div>
  );
}
