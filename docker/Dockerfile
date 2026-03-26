FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

RUN pip install uv

COPY pyproject.toml .

RUN uv venv .venv
RUN uv pip install --python .venv/bin/python \
    fastapi uvicorn[standard] pydantic pydantic-settings \
    python-dotenv httpx sqlalchemy[asyncio] asyncpg \
    alembic python-multipart langfuse openai \
    langgraph langchain-openai langchain-community \
    langchain-text-splitters langchain-core \
    pgvector pypdf pandas \
    mcp fastmcp

COPY app/ ./app/
COPY run.py .
COPY mcp_stdio.py .

EXPOSE 8000

ENV PATH="/app/.venv/bin:$PATH"
CMD ["python", "run.py"]
