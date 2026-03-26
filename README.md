# AI Financial Analyst — Multi-Agent RAG System

A production-grade financial analysis system built with **LangGraph multi-agent orchestration**, **RAG over financial documents**, **deterministic financial tools**, **Langfuse observability**, and **MCP (Model Context Protocol)** support.

---

## Architecture

```
User Query
    │
    ▼
┌─────────────────────────────────────────────────────┐
│                  LangGraph Workflow                 │
│                                                     │
│  router_agent      classify query type              │
│       │                                             │
│       ├── rag ──────► rag_agent                     │
│       ├── computation ► computation_agent           │
│       ├── hybrid ───► parallel(rag + computation)   │
│       └── general ──► planner_agent                 │
│                           │                         │
│                      planner_agent  plan + steps    │
│                           │                         │
│                      aggregator_agent  final answer │
│                           │                         │
│                      critic_agent  validate         │
└─────────────────────────────────────────────────────┘
    │
    ▼
Response: answer + is_valid + critique + trace_id
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (async) |
| Agent Orchestration | LangGraph |
| LLM | OpenAI GPT-4o / GPT-4o-mini |
| Local LLM | Ollama (LLaMA 3.2) |
| RAG Vector Store | pgvector (Postgres) |
| Embeddings | OpenAI text-embedding-3-small |
| Observability | Langfuse |
| MCP | FastMCP (SSE + stdio) |
| Frontend | Next.js 14 + Tailwind CSS |
| Database | PostgreSQL 16 |
| Analytics DB | ClickHouse |
| Containerization | Docker + docker-compose |

---

## Project Structure

```
├── app/
│   ├── agents/               # LangGraph agent nodes
│   │   ├── router_agent.py   # Classifies query type
│   │   ├── planner_agent.py  # Produces execution plan
│   │   ├── rag_agent.py      # Retrieves document context
│   │   ├── computation_agent.py  # Calls financial tools
│   │   ├── aggregator_agent.py   # Synthesizes final answer
│   │   └── critic_agent.py   # Validates for hallucinations
│   ├── workflows/
│   │   ├── state.py          # Shared GraphState TypedDict
│   │   ├── graph.py          # LangGraph graph definition
│   │   └── parallel.py       # Parallel RAG + computation
│   ├── tools/
│   │   ├── financial_metrics.py  # Pure Python: PE, CAGR, EBITDA, etc.
│   │   └── registry.py           # LangChain @tool wrappers
│   ├── rag/
│   │   ├── loader.py         # PDF + CSV loaders
│   │   ├── chunker.py        # Recursive text splitter
│   │   ├── embedder.py       # OpenAI embeddings
│   │   ├── vector_store.py   # pgvector save + similarity search
│   │   └── retriever.py      # Clean retrieval interface
│   ├── models/
│   │   ├── router.py         # ModelRouter — routes tasks to right LLM
│   │   ├── openai_client.py  # OpenAI wrapper
│   │   └── local_client.py   # Ollama wrapper
│   ├── mcp/
│   │   ├── server.py         # FastMCP server (tools + resources + prompts)
│   │   ├── transport.py      # Mounts MCP into FastAPI at /mcp
│   │   └── client.py         # MCP client for consuming external servers
│   ├── observability/
│   │   ├── tracer.py         # Langfuse Trace / Span / Generation
│   │   ├── middleware.py     # Auto-traces every HTTP request
│   │   └── llm_tracker.py    # Tracks tokens + cost per LLM call
│   ├── api/v1/
│   │   ├── analyst.py        # POST /api/v1/analyze
│   │   ├── documents.py      # POST /api/v1/documents/ingest
│   │   ├── eval.py           # POST /api/v1/eval/run
│   │   ├── mcp_status.py     # GET  /api/v1/mcp/status
│   │   └── health.py         # GET  /api/v1/health
│   ├── services/
│   │   ├── analyst_service.py    # Orchestrates workflow per request
│   │   ├── document_service.py   # Ingest pipeline
│   │   └── eval_service.py       # Evaluation pipeline
│   ├── config/settings.py    # Pydantic settings from .env
│   ├── db/
│   │   ├── session.py        # Async SQLAlchemy + pgvector
│   │   └── models.py         # DocumentChunk ORM model
│   └── main.py               # FastAPI app factory
├── ui/                       # Next.js frontend
│   └── src/app/
│       ├── chat/             # Query interface
│       ├── documents/        # Document upload
│       ├── eval/             # Evaluation dashboard
│       └── mcp/              # MCP tools inspector
├── tests/eval/
│   ├── queries.json          # Test queries + expected outputs
│   └── run_eval.py           # Standalone eval runner
├── docker/
│   ├── Dockerfile            # FastAPI image
│   └── init.sql              # Postgres init (pgvector extension)
├── docker-compose.yml        # All services
├── mcp_stdio.py              # MCP stdio entry point (Claude Desktop)
└── pyproject.toml            # Python dependencies
```

---

## Quickstart

### 1. Clone and configure

```bash
git clone <repo-url>
cd AI-Financial-Analyst-Multi-Agent-RAG-Tooling-

cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### 2. Start all services

```bash
docker-compose up --build
```

### 3. Set up Langfuse

1. Open `http://localhost:3000`
2. Create an account
3. Go to **Settings → API Keys** → copy Secret Key + Public Key
4. Add to `.env`:
   ```env
   LANGFUSE_SECRET_KEY=sk-lf-...
   LANGFUSE_PUBLIC_KEY=pk-lf-...
   ```
5. Restart: `docker-compose restart app`

### 4. Open the UI

```
http://localhost:3001
```

---

## Services

| Service | URL | Description |
|---|---|---|
| Next.js UI | http://localhost:3001 | Main application |
| FastAPI | http://localhost:8000/docs | Swagger UI |
| Langfuse | http://localhost:3000 | Observability dashboard |
| Postgres | localhost:5432 | Main DB + pgvector |
| ClickHouse | localhost:8123 | Langfuse analytics |
| MCP (SSE) | http://localhost:8000/mcp/sse | MCP endpoint |

---

## API Endpoints

```bash
# Run a financial analysis
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"query": "Calculate CAGR from 100B to 185B over 4 years", "user_id": "u1"}'

# Upload a financial document (PDF or CSV)
curl -X POST http://localhost:8000/api/v1/documents/ingest \
  -F "file=@apple_10k.pdf"

# Run evaluation suite
curl -X POST http://localhost:8000/api/v1/eval/run

# Check MCP tools
curl http://localhost:8000/api/v1/mcp/status

# Health check
curl http://localhost:8000/api/v1/health
```

---

## Financial Tools

Pure Python — no LLM, always deterministic:

| Tool | Formula | Input |
|---|---|---|
| `calculate_pe_ratio` | Stock Price / EPS | stock_price, earnings_per_share |
| `calculate_cagr` | (end/start)^(1/years) - 1 | start_value, end_value, years |
| `calculate_ebitda` | NI + Interest + Taxes + D&A | net_income, interest, taxes, depreciation, amortization |
| `calculate_debt_to_equity` | Total Debt / Equity | total_debt, shareholders_equity |
| `calculate_profit_margin` | Net Income / Revenue × 100 | net_income, revenue |

---

## Multi-Model Routing

Tasks are routed to the right model automatically:

| Task | Model | Reason |
|---|---|---|
| Query routing | gpt-4o-mini | Simple classification |
| Planning | gpt-4o | Needs reasoning |
| RAG synthesis | gpt-4o | Reads documents |
| Tool calling | gpt-4o | Reliable function calls |
| Aggregation | gpt-4o | Answer quality |
| Critique | gpt-4o | Validation accuracy |

To use a local LLM (Ollama), set in `.env`:
```env
LOCAL_LLM_ENABLED=true
LOCAL_LLM_MODEL=llama3.2
LOCAL_LLM_BASE_URL=http://localhost:11434/v1
```

---

## MCP (Model Context Protocol)

### Connect Claude Desktop

Add to `~/.claude/claude_desktop_config.json`:

```json
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
```

Restart Claude Desktop. All 6 tools + 2 resources will appear in the toolbar.

### Exposed via MCP

| Type | Name |
|---|---|
| Tool | `pe_ratio`, `cagr`, `ebitda`, `debt_to_equity`, `profit_margin` |
| Tool | `analyze_query` — runs full LangGraph workflow |
| Resource | `financial://formulas` — formula reference |
| Resource | `financial://metrics` — interpretation guide |
| Prompt | `financial_analysis_prompt` — reusable analysis template |

---

## Evaluation

```bash
# Via API
curl -X POST http://localhost:8000/api/v1/eval/run

# Standalone (no server needed)
python tests/eval/run_eval.py

# Run specific tests
python tests/eval/run_eval.py --ids eval_001 eval_002
```

Results are scored on:
- **Query type match** — did the router classify correctly?
- **Tool used** — was the right tool called?
- **Answer contains** — are expected values in the response?
- **Critic valid** — did the critic approve the answer?

All scores are logged to Langfuse per trace.

---

## Local Development (without Docker)

```bash
# Install deps
pip install uv
uv pip install -r pyproject.toml

# Run backend
cp .env.example .env  # fill in keys
python run.py

# Run UI
cd ui
npm install
npm run dev
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | Yes | OpenAI API key |
| `DATABASE_URL` | Yes | Postgres connection string |
| `LANGFUSE_SECRET_KEY` | Yes | Langfuse secret key |
| `LANGFUSE_PUBLIC_KEY` | Yes | Langfuse public key |
| `LANGFUSE_HOST` | Yes | Langfuse URL (default: http://localhost:3000) |
| `LOCAL_LLM_ENABLED` | No | Enable Ollama (default: false) |
| `LOCAL_LLM_MODEL` | No | Ollama model name (default: llama3.2) |
| `LOCAL_LLM_BASE_URL` | No | Ollama base URL |
| `APP_ENV` | No | development / production |
