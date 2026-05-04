#!/bin/bash
# Triggered by PostToolUse on Write/Edit. Receives tool JSON on stdin.
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | python3 -c "
import sys, json
d = json.loads(sys.stdin.read())
print(d.get('tool_input', {}).get('file_path', ''))
" 2>/dev/null)

# Only process .ts and .tsx files
if [[ "$FILE_PATH" != *.ts ]] && [[ "$FILE_PATH" != *.tsx ]]; then
  exit 0
fi

PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
UI_DIR="$PROJECT_DIR/ui"

if [ ! -d "$UI_DIR/node_modules" ]; then
  echo "UI node_modules not found — skipping UI lint. Run: cd ui && npm install"
  exit 0
fi

echo "--- UI lint: $FILE_PATH ---"
cd "$UI_DIR" && npx eslint "$FILE_PATH" --max-warnings=0 2>&1
ESLINT_EXIT=$?

if [ $ESLINT_EXIT -ne 0 ]; then
  echo ""
  echo "Fix the above ESLint issues before proceeding."
  exit 1
fi

echo "UI lint passed."
exit 0
