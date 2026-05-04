#!/bin/bash
# Triggered by PostToolUse on Write/Edit. Receives tool JSON on stdin.
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | python3 -c "
import sys, json
d = json.loads(sys.stdin.read())
print(d.get('tool_input', {}).get('file_path', ''))
" 2>/dev/null)

# Only process .py files
if [[ "$FILE_PATH" != *.py ]]; then
  exit 0
fi

# Skip if file doesn't exist
if [ ! -f "$FILE_PATH" ]; then
  exit 0
fi

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

echo "--- Python lint: $FILE_PATH ---"

cd "$PROJECT_ROOT" && \
  uv run isort "$FILE_PATH" && \
  uv run ruff format "$FILE_PATH" && \
  uv run ruff check "$FILE_PATH" || exit 2 && \
  uv run pyright "$FILE_PATH" || exit 2

echo "Lint passed."
exit 0
