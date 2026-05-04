# AI Financial Analyst — Project Rules

## Stack
- Backend: Python 3.11, FastAPI, LangGraph, MCP
- Frontend: Next.js (ui/), TypeScript, Tailwind
- Cache: Redis (app/cache/redis_cache.py)
- DB: PostgreSQL + pgvector (app/db/)
- Agents: app/agents/ — planner, router, rag, yfinance, computation, aggregator, critic, mcp_enrichment
- Workflows: app/workflows/ — LangGraph graph, parallel execution, state
- Tests: tests/ — run with: uv run pytest tests/ --cov=app

## Code Rules
- New agents go in app/agents/, follow the pattern in existing agents
- New tools go in app/tools/
- New API endpoints go in app/api/v1/
- Import sorting: uv run isort <file>
- Formatting: uv run ruff format <file>
- Linter: uv run ruff check <file>
- Type checker: uv run pyright <file>
- Security scanner: uv run bandit -r app/
- Complexity tool: uv run radon cc app/

## Git Rules — CRITICAL
- NEVER commit: .env, .env.local, __pycache__, .DS_Store, graphify-out/, node_modules/, .next/
- Always check staged files before committing
- Use descriptive commit messages: feat:, fix:, chore:, refactor:

## Slash Commands Available
- /test     → run test suite with coverage
- /lint     → code quality check with score (isort + ruff format + ruff check + pyright)
- /optimize → complexity + security analysis with score
- /all      → runs all three with combined score
