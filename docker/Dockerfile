FROM python:3.11-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

RUN pip install uv

COPY pyproject.toml .

RUN uv venv .venv
RUN uv pip install --python .venv/bin/python \
    fastapi uvicorn[standard] pydantic pydantic-settings \
    python-dotenv httpx sqlalchemy[asyncio] asyncpg \
    alembic python-multipart "langfuse>=2.0.0,<3.0.0" openai \
    langgraph langchain langchain-openai langchain-community \
    langchain-text-splitters langchain-core \
    pgvector pypdf pandas \
    mcp flashrank yfinance

COPY app/ ./app/
COPY run.py .
COPY mcp_stdio.py .

EXPOSE 8000

ENV PATH="/app/.venv/bin:$PATH"
CMD ["python", "run.py"]
