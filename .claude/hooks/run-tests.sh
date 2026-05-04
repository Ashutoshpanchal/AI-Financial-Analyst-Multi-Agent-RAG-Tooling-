#!/bin/bash
# Triggered by Stop. Runs pytest after every Claude response.
PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$PROJECT_DIR"

# Skip if no test files exist yet
if [ ! -d "tests" ] || [ -z "$(find tests -name '*.py' -not -name '__init__.py' 2>/dev/null)" ]; then
  exit 0
fi

echo ""
echo "--- Auto test run ---"
uv run pytest tests/ -q --tb=line 2>&1 | tail -8
