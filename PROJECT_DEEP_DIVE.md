# AI Financial Analyst — Deep Dive

> Complete explanation of flow, models, and LangGraph internals.

---

## TABLE OF CONTENTS

1. [Models Used](#1-models-used)
2. [Document Ingestion Flow](#2-document-ingestion-flow)
3. [Query Retrieval Flow](#3-query-retrieval-flow)
4. [All Agents — What Each Does](#4-all-agents--what-each-does)
5. [All Tools — What Each Does](#5-all-tools--what-each-does)
6. [LangGraph — Complete Guide](#6-langgraph--complete-guide)

---

## 1. MODELS USED

| Purpose | Model | Where |
|---------|-------|--------|
| LLM (all agents) | `meta/llama-4-maverick-17b-128e-instruct` | NVIDIA NIM API |
| Embedding | `nvidia/nv-embedqa-e5-v5` | NVIDIA NIM API |
| Reranker | `ms-marco-MiniLM-L-12-v2` | Local CPU (flashrank, ~33MB) |

### How LangChain calls NVIDIA NIM

NVIDIA NIM exposes an OpenAI-compatible API. `ChatOpenAI` works by just pointing `base_url` at NVIDIA:

```python
ChatOpenAI(
    model="meta/llama-4-maverick-17b-128e-instruct",
    api_key="nvapi-...",                                  # NVIDIA key
    base_url="https://integrate.api.nvidia.com/v1",      # NVIDIA endpoint
)
```

Actual HTTP request sent:
```
POST https://integrate.api.nvidia.com/v1/chat/completions
{ "model": "meta/llama-4-maverick...", "messages": [...] }
```

Same OpenAI format — NVIDIA just runs Llama on their servers.

### Why nvidia/nv-embedqa-e5-v5 is asymmetric

The model has two modes — trained separately for questions vs documents:

```
input_type="passage"  →  "I am a document waiting to be found"
input_type="query"    →  "I am a question looking for an answer"
```

Even when query and answer use completely different words, vectors still point toward each other because the model was trained on millions of (question, answer) pairs.

### Why 1024 dimensions

More dimensions = more nuance captured about meaning.
`500 chars ≈ 100-150 tokens` — well under the 512-token limit of nv-embedqa, so character-based chunking is safe without a separate tokenizer.

---

## 2. DOCUMENT INGESTION FLOW

```
PDF / CSV uploaded via POST /api/v1/documents
         │
         ▼ Step 1 — LOAD (loader.py)
         │
         │  PDF → pypdf extracts text per page
         │        output: [{text: "page text...", metadata: {source, page, type}}]
         │
         │  CSV → pandas converts each row to readable sentence
         │        "Revenue: 394B, Net Income: 99B..."
         │
         ▼ Step 2 — CHUNK (chunker.py)
         │
         │  RecursiveCharacterTextSplitter
         │  chunk_size=500 chars, overlap=100 chars
         │  splits on: paragraphs → sentences → words
         │
         │  [----chunk 1 (500)----]
         │              [--overlap--][----chunk 2 (500)----]
         │
         ▼ Step 3 — EMBED (embedder.py)
         │
         │  Model: nvidia/nv-embedqa-e5-v5
         │  input_type="passage"
         │  Sends all chunks in one batch API call
         │  Each chunk → 1024-dimensional float vector
         │
         ▼ Step 4 — STORE (vector_store.py)
         │
         │  Saves to PostgreSQL with pgvector extension
         │  Table: document_chunks
         │  Columns: text, embedding (vector 1024), source, page, chunk_index
         │
         ▼ Done — chunks searchable via cosine similarity
```

---

## 3. QUERY RETRIEVAL FLOW

```
User query: "What was Apple's profit margin?"
         │
         ▼ Step 1 — EMBED QUERY (embedder.py)
         │
         │  Same model: nvidia/nv-embedqa-e5-v5
         │  input_type="query"  ← different mode than ingestion
         │  Query → 1024-dim vector
         │
         ▼ Step 2 — COSINE SIMILARITY (vector_store.py)
         │
         │  pgvector operator <=>  (cosine distance)
         │  SELECT * FROM document_chunks
         │  ORDER BY embedding <=> '[query vector]'
         │  LIMIT 20
         │
         │  Returns top 20 candidates with similarity scores
         │
         ▼ Step 3 — RERANK (reranker.py)
         │
         │  Model: ms-marco-MiniLM-L-12-v2 (local CPU)
         │  Cross-encoder reads query + chunk TOGETHER:
         │
         │  [CLS] What was profit margin? [SEP] Apple net income $99.8B [SEP]
         │                    ↓ neural network
         │               score: 0.91
         │
         │  Runs 20 times (once per candidate)
         │  Returns top 5 by rerank score
         │
         ▼ Step 4 — FORMAT (retriever.py)
         │
         │  Formats top 5 into context string:
         │  [Source 1: apple_report.pdf, page 4 | rerank: 0.91 | cosine: 0.89]
         │  Total net revenue was $394.3 billion...
         │
         ▼ Injected into LLM prompt as retrieved_context
```

### Why two-stage (embed + rerank)?

| Stage | Speed | Method | Weakness |
|-------|-------|--------|----------|
| Cosine similarity | Fast | vector distance | doesn't read query+chunk together |
| Cross-encoder rerank | Slower | reads both as pair | can't scale to full DB |

Together: cosine narrows to 20 candidates fast → reranker deeply scores those 20.

### [CLS] and [SEP] tokens

These are BERT special tokens — handled automatically by flashrank:
- `[CLS]` — sits at start, collects meaning of entire input into one vector → produces the score
- `[SEP]` — wall between query and chunk, tells model "two different texts"

---

## 4. ALL AGENTS — WHAT EACH DOES

### Shared State

Every agent reads from and writes to `GraphState` — a single TypedDict passed through every node:

```python
class GraphState(TypedDict):
    query: str                   # never changes
    query_type: str | None       # router writes
    retrieved_context: str | None # rag_agent writes
    tool_results: dict           # computation + mcp_enrichment write
    live_stock_data: dict | None # yfinance_agent writes
    data_comparison: dict | None # yfinance_agent writes
    plan: str | None             # planner writes
    steps: list[str]             # planner writes
    final_answer: str | None     # aggregator writes
    is_valid: bool | None        # critic writes
    critique: str | None         # critic writes
    errors: list[str]            # any agent appends errors
```

Rule: every agent does `return {**state, "my_field": value}` — never overwrites other agents' work.

---

### Agent 1 — router_agent
**Model:** llama-4-maverick
**Reads:** `query`
**Writes:** `query_type`, `next_agent`

Classifies query into one of 4 types:
```
rag         → needs document search
computation → needs financial calculations
hybrid      → needs both
general     → general knowledge, no tools
```

Uses `complete_structured()` with `RouterDecision` Pydantic model — LLM forced to return typed JSON.

---

### Agent 2 — rag_agent
**Model:** NO LLM — pure retrieval
**Reads:** `query`
**Writes:** `retrieved_context`

Calls `retrieve(query, db, top_k=5)` which runs the full 2-stage pipeline (embed → cosine → rerank). Returns formatted context string with source citations.

---

### Agent 3 — computation_agent
**Model:** llama-4-maverick + 5 financial tools bound
**Reads:** `query`, `retrieved_context`
**Writes:** `tool_results`

LLM decides which tools to call and with what numbers. `ToolNode` executes the actual Python math. LLM never calculates itself.

```
LLM sees tool signatures → decides "call pe_ratio_tool(150, 6.05)"
ToolNode executes pe_ratio_tool → returns "P/E Ratio: 24.79x"
```

---

### Agent 4 — yfinance_agent
**Model:** NO LLM — pure data fetch
**Reads:** `query`, `retrieved_context`
**Writes:** `ticker`, `live_stock_data`, `data_comparison`

1. Detects ticker from query (explicit: `AAPL`, or name: `"Apple"` → `AAPL`)
2. Fetches live data from Yahoo Finance (price, P/E, revenue, margins, debt...)
3. Compares live numbers vs document numbers — flags differences (docs may be historical)

Skips gracefully if no ticker detected.

---

### Agent 5 — mcp_enrichment_agent
**Model:** llama-4-maverick
**Reads:** `retrieved_context`, `query_type`
**Writes:** `tool_results` (merges with existing)

Scans retrieved document text → extracts financial numbers → auto-calls MCP tools.

```
Doc says: "net income $99.8B, revenue $394.3B"
LLM extracts → calls profit_margin(99.8, 394.3)
Result merged into tool_results before planner sees it
```

Skips if no retrieved_context or query_type = "general".

---

### Agent 6 — planner_agent
**Model:** llama-4-maverick
**Reads:** `query`, `query_type`, `retrieved_context`, `tool_results`
**Writes:** `plan`, `steps`

Creates a step-by-step execution plan from all gathered context.

```python
PlannerDecision(
    plan="Analyze Apple profitability using retrieved financials and live data",
    steps=["Review revenue figures", "Apply profit margin calculation", "Compare sources"]
)
```

---

### Agent 7 — aggregator_agent
**Model:** llama-4-maverick
**Reads:** everything in state
**Writes:** `final_answer`

Combines plan + document context + tool results + live stock data → writes complete answer.
Told explicitly: cite source for each number `(live)` or `(document, page X)`, do NOT hallucinate.

---

### Agent 8 — critic_agent
**Model:** llama-4-maverick
**Reads:** `final_answer`, `tool_results`, `live_stock_data`, `retrieved_context`
**Writes:** `is_valid`, `critique`

Validates final answer against 3 sources of ground truth:
1. Tool calculation results
2. Live yfinance data
3. Retrieved document context

Catches: number mismatches, unsupported claims, hallucinated figures.
If issues found → appends `⚠️ Note: ...` to final_answer.

---

## 5. ALL TOOLS — WHAT EACH DOES

Tools are pure Python math — **no LLM, no API call, always deterministic**.

### Tool 1 — pe_ratio_tool
```
Formula:  P/E = Stock Price / EPS
Input:    stock_price=150, earnings_per_share=6.05
Output:   "P/E Ratio: 24.79x"
Use when: user asks about stock valuation
```

### Tool 2 — cagr_tool
```
Formula:  CAGR = (end/start)^(1/years) - 1
Input:    start_value=100, end_value=150, years=3
Output:   "CAGR: 14.47%"
Use when: user asks about growth rate over multiple years
```

### Tool 3 — ebitda_tool
```
Formula:  EBITDA = Net Income + Interest + Taxes + Depreciation + Amortization
Input:    net_income=99.8, interest=2.9, taxes=29.9, depreciation=11.1, amortization=0
Output:   "EBITDA: $143.70B"
Use when: user asks about operating profitability
```

### Tool 4 — debt_to_equity_tool
```
Formula:  D/E = Total Debt / Shareholders Equity
Input:    total_debt=120, shareholders_equity=60
Output:   "Debt-to-Equity: 2.0x"
Use when: user asks about financial leverage or debt levels
```

### Tool 5 — profit_margin_tool
```
Formula:  Margin = (Net Income / Revenue) × 100
Input:    net_income=99.8, revenue=394.3
Output:   "Profit Margin: 25.31%"
Use when: user asks about profitability
```

Every tool returns a `ToolResult` dataclass with `value`, `formatted`, `formula`, `inputs` — so the LLM can cite the formula, not hallucinate it.

---

## 6. LANGGRAPH — COMPLETE GUIDE

---

### What is LangGraph

A framework to build **stateful multi-agent pipelines** as directed graphs.

```
Nodes  =  agents (Python functions)
Edges  =  paths between agents
State  =  shared data flowing through all nodes
```

---

### State

Shared TypedDict passed from node to node. Each agent reads what it needs, writes only its own fields.

```python
# Every agent pattern:
async def my_agent(state: GraphState) -> GraphState:
    data = state["query"]           # READ
    result = do_something(data)
    return {**state, "my_field": result}  # WRITE only my field
```

Without `**state` → you lose all previous agents' work.

---

### Nodes

A node is any Python function (sync or async) registered with the graph:

```python
builder.add_node("planner_agent", planner_agent)
#                 ↑ name           ↑ function
```

LangGraph calls `planner_agent(state)` when it's this node's turn.

---

### Edges

**Fixed edge** — always goes to same node:
```python
builder.add_edge("planner_agent", "aggregator_agent")
```

**Conditional edge** — decides at runtime based on state:
```python
def route_after_router(state):
    return {
        "rag": "rag_agent",
        "computation": "computation_agent",
        "hybrid": "parallel_agent",
        "general": "planner_agent",
    }[state["query_type"]]

builder.add_conditional_edges("router_agent", route_after_router, {...})
```

Key insight: `add_edge` only **registers** the connection. A node only runs if something has an edge pointing TO it.

---

### RetryPolicy

Automatically retries a node on failure — without touching agent code:

```python
from langgraph.pregel import RetryPolicy

_llm_retry   = RetryPolicy(max_attempts=3, wait_seconds=1.0, backoff=2.0)
_quick_retry = RetryPolicy(max_attempts=2, wait_seconds=0.5, backoff=1.5)

builder.add_node("aggregator_agent", aggregator_agent, retry=_llm_retry)
```

Retry flow:
```
attempt 1 → fails → wait 1s
attempt 2 → fails → wait 2s  (1.0 × backoff 2.0)
attempt 3 → success ✅
```

**Important:** Only triggers if agent raises an exception. If agent catches exception internally and returns fallback → LangGraph sees success → NO retry.

```
Agent raises Exception  →  LangGraph retries
Agent catches Exception →  LangGraph sees normal return → no retry
```

---

### Tool Calling — how LLM uses tools

Tools are Python functions decorated with `@tool` and bound to the LLM:

```python
llm = router.get("computation")._llm.bind_tools(FINANCIAL_TOOLS)
response = await llm.ainvoke(messages)

# LLM responds with tool call decision:
# response.tool_calls = [{"name": "pe_ratio_tool", "args": {"stock_price": 150, ...}}]

if response.tool_calls:
    result_state = await tool_node.ainvoke({"messages": [response]})
    # ToolNode executes actual Python function
```

```
LLM decides WHAT to call + WHAT args
ToolNode executes actual Python code
LLM never calculates — always uses tools
```

---

### Parallel Execution

Your project uses `asyncio.gather` for hybrid queries (rag + computation simultaneously):

```python
rag_result, comp_result = await asyncio.gather(
    rag_agent(state),
    computation_agent(state),
)
```

Works because:
- Both read the same input (query)
- Both write to **different keys** (retrieved_context vs tool_results)
- No dependency between them

```
WITHOUT parallel:  rag (2s) + computation (2s) = 4s
WITH parallel:     rag (2s) || computation (2s) = 2s
```

**Why not ProcessPoolExecutor for true parallelism?**
All agents depend on previous agents' state. ProcessPoolExecutor gives each process separate memory — state changes in one process are invisible to others. Sequential dependency breaks.

Only safe parallelism = agents that read same input AND write different keys.

---

### Full Graph Flow

```
User query
     │
     ▼
router_agent  ──── classifies query type
     │
     ├── "rag"         → rag_agent
     │                       │
     ├── "computation" → computation_agent
     │                       │
     ├── "hybrid"      → parallel_agent (rag + computation simultaneously)
     │                       │
     └── "general" ─────────►│◄─── all paths converge here
                              ▼
                        yfinance_agent    → fetches live stock data
                              │
                        mcp_enrichment    → auto-calculates from doc numbers
                              │
                        planner_agent     → creates execution plan
                              │
                        aggregator_agent  → writes final answer
                              │
                        critic_agent      → validates, flags issues
                              │
                             END
```

---

### Structured Output — how LLM returns typed data

```python
class RouterDecision(BaseModel):
    query_type: str
    reasoning: str
    next_agent: str

llm = self._llm.with_structured_output(RouterDecision, include_raw=True)
result = await llm.ainvoke(messages)

result["parsed"]  # → RouterDecision object, typed fields
result["raw"]     # → AIMessage with token usage metadata
```

`with_structured_output` does two things:
1. **Outgoing** → tells LLM "respond in this JSON shape" (generates JSON schema from Pydantic class)
2. **Incoming** → parses LLM JSON response into typed Pydantic object

`include_raw=True` — needed to extract token counts for Langfuse observability. Without it you'd only get the parsed object, no metadata.

---

### Model Layer Architecture

```
Agent
  │
  └── get_model_router().get("planning")
              │
              ▼
         ModelRouter         → decides which model based on task
              │
       ┌──────┴──────┐
       ▼             ▼
  OpenAIClient   LocalLLMClient
  (NVIDIA NIM)   (Ollama local)
       │
  ChatOpenAI → HTTP → NVIDIA NIM API
```

All tasks currently use `llama-4-maverick`. Original design used `gpt-4o` / `gpt-4o-mini` — switched to NVIDIA NIM by changing `TASK_MODEL_MAP` and `base_url` only. Agent code untouched.

`@lru_cache` on `get_model_router()` — one instance for entire app lifetime.

---

### MCP (Model Context Protocol)

Two transport modes:

| Transport | How | Used by |
|-----------|-----|---------|
| SSE | HTTP at `/mcp/sse` | Frontend, web clients |
| stdio | stdin/stdout subprocess | Claude Desktop (optional) |

MCP runs **inside FastAPI on port 8000** — not a separate port. Mounted at `/mcp` via Starlette sub-app.

The MCP server exposes the same 5 financial tools + `analyze_query` + `get_stock_data` as callable tools for any MCP client.
