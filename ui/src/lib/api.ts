const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface AnalysisResult {
  query: string;
  query_type: string | null;
  plan: string | null;
  steps: string[];
  answer: string;
  is_valid: boolean | null;
  critique: string | null;
  tool_results: Record<string, string>;
  errors: string[];
  trace_id: string | null;
}

export interface IngestResult {
  filename: string;
  pages: number;
  chunks: number;
  status: string;
}

export interface EvalResult {
  total: number;
  passed: number;
  failed: number;
  pass_rate: number;
  avg_latency_ms: number;
  results: EvalRecord[];
}

export interface EvalRecord {
  id: string;
  query: string;
  latency_ms: number;
  answer?: string;
  query_type?: string;
  tool_results?: string[];
  scores: {
    passed: boolean;
    query_type_match?: boolean;
    tool_used?: boolean;
    answer_contains?: boolean;
    is_valid?: boolean;
  };
  tags: string[];
  trace_id?: string;
  error?: string;
}

export interface MCPStatus {
  status: string;
  mcp_endpoint: string;
  tools: { name: string; description: string }[];
  resources: { uri: string; name: string }[];
  error?: string;
}

export async function analyze(query: string, userId?: string): Promise<AnalysisResult> {
  const res = await fetch(`${BASE}/api/v1/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, user_id: userId || "ui_user" }),
  });
  if (!res.ok) throw new Error(`Analysis failed: ${res.statusText}`);
  return res.json();
}

export async function ingestDocument(file: File): Promise<IngestResult> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/api/v1/documents/ingest`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) throw new Error(`Ingest failed: ${res.statusText}`);
  return res.json();
}

export async function runEval(queryIds?: string[]): Promise<EvalResult> {
  const params = queryIds?.length
    ? "?" + queryIds.map((id) => `query_ids=${id}`).join("&")
    : "";
  const res = await fetch(`${BASE}/api/v1/eval/run${params}`, { method: "POST" });
  if (!res.ok) throw new Error(`Eval failed: ${res.statusText}`);
  return res.json();
}

export async function getMCPStatus(): Promise<MCPStatus> {
  const res = await fetch(`${BASE}/api/v1/mcp/status`);
  if (!res.ok) throw new Error(`MCP status failed: ${res.statusText}`);
  return res.json();
}

export async function getHealth(): Promise<{ status: string; environment: string; database: string }> {
  const res = await fetch(`${BASE}/api/v1/health`);
  if (!res.ok) throw new Error("Health check failed");
  return res.json();
}

export interface StockSearchResult {
  symbol: string;
  name: string;
  exchange: string;
  type: string;
}

export interface StockData {
  symbol: string;
  name: string | null;
  sector: string | null;
  industry: string | null;
  country: string | null;
  website: string | null;
  description: string | null;
  price: number | null;
  prev_close: number | null;
  open: number | null;
  day_low: number | null;
  day_high: number | null;
  week_52_low: number | null;
  week_52_high: number | null;
  market_cap: number | null;
  pe_ratio: number | null;
  forward_pe: number | null;
  eps: number | null;
  price_to_book: number | null;
  revenue: number | null;
  net_income: number | null;
  total_debt: number | null;
  total_cash: number | null;
  ebitda: number | null;
  gross_margins: number | null;
  profit_margins: number | null;
  dividend_yield: number | null;
  dividend_rate: number | null;
  beta: number | null;
  shares_outstanding: number | null;
  avg_volume: number | null;
  volume: number | null;
}

export async function searchStocks(q: string): Promise<StockSearchResult[]> {
  const res = await fetch(`${BASE}/api/v1/stock/search?q=${encodeURIComponent(q)}`);
  if (!res.ok) throw new Error("Search failed");
  return res.json();
}

export async function getStockData(ticker: string): Promise<StockData> {
  const res = await fetch(`${BASE}/api/v1/stock/${encodeURIComponent(ticker)}`);
  if (!res.ok) throw new Error(`Failed to fetch data for ${ticker}`);
  return res.json();
}
