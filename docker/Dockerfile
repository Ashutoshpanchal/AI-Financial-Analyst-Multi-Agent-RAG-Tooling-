FROM python:3.11-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

RUN pip install uv

COPY pyproject.toml .

RUN uv venv .venv
RUN uv pip install --python .venv/bin/python -e .

COPY app/ ./app/
COPY run.py .
COPY mcp_stdio.py .

EXPOSE 8000

ENV PATH="/app/.venv/bin:$PATH"
CMD ["python", "run.py"]
