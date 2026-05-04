#!/bin/bash
# Triggered by PreToolUse on Bash. Receives tool JSON on stdin.
INPUT=$(cat)
COMMAND=$(echo "$INPUT" | python3 -c "
import sys, json
d = json.loads(sys.stdin.read())
print(d.get('tool_input', {}).get('command', ''))
" 2>/dev/null)

# Only intercept git add, commit, push
if ! echo "$COMMAND" | grep -qE "^git (add|commit|push)"; then
  exit 0
fi

# Get staged files
STAGED=$(git -C "$(cd "$(dirname "$0")/../.." && pwd)" diff --cached --name-only 2>/dev/null)

if [ -z "$STAGED" ]; then
  exit 0
fi

BLOCKED_PATTERNS=(".env" ".env.local" "__pycache__" ".DS_Store" "node_modules" ".next" "graphify-out")
FOUND_ISSUES=""

while IFS= read -r FILE; do
  for PATTERN in "${BLOCKED_PATTERNS[@]}"; do
    if echo "$FILE" | grep -q "$PATTERN"; then
      FOUND_ISSUES="$FOUND_ISSUES\n  BLOCKED: $FILE (matches '$PATTERN')"
    fi
  done
done <<< "$STAGED"

if [ -n "$FOUND_ISSUES" ]; then
  echo "Git safety guard: sensitive or cache files are staged."
  printf "%b\n" "$FOUND_ISSUES"
  echo ""
  echo "Remove them with: git restore --staged <file>"
  echo "Add to .gitignore if this keeps happening."
  exit 1
fi

exit 0
