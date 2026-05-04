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

BLOCKED_PATTERNS=(".env" ".env.local" "__pycache__" ".DS_Store" "node_modules" ".next" "graphify-out")
FOUND_ISSUES=""

# Check 1: inspect the command string itself for sensitive file patterns
# Catches: git add .env, git add -f .env, etc.
if echo "$COMMAND" | grep -qE "^git add"; then
  # Extract everything after "git add" and split on spaces
  ARGS=$(echo "$COMMAND" | sed 's/^git add[[:space:]]*//' | tr ' ' '\n')
  while IFS= read -r ARG; do
    # Skip flags like -f, -A, --all
    [[ "$ARG" == -* ]] && continue
    for PATTERN in "${BLOCKED_PATTERNS[@]}"; do
      if echo "$ARG" | grep -q "$PATTERN"; then
        FOUND_ISSUES="$FOUND_ISSUES\n  BLOCKED (command): $ARG (matches '$PATTERN')"
      fi
    done
  done <<< "$ARGS"
fi

# Check 2: inspect already-staged files (catches multi-step staging)
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
STAGED=$(git -C "$PROJECT_ROOT" diff --cached --name-only 2>/dev/null)

if [ -n "$STAGED" ]; then
  while IFS= read -r FILE; do
    for PATTERN in "${BLOCKED_PATTERNS[@]}"; do
      if echo "$FILE" | grep -q "$PATTERN"; then
        FOUND_ISSUES="$FOUND_ISSUES\n  BLOCKED (staged): $FILE (matches '$PATTERN')"
      fi
    done
  done <<< "$STAGED"
fi

if [ -n "$FOUND_ISSUES" ]; then
  echo "Git safety guard: sensitive or cache files detected."
  printf "%b\n" "$FOUND_ISSUES"
  echo ""
  echo "Remove staged files with: git restore --staged <file>"
  echo "Add to .gitignore if this keeps happening."
  exit 1
fi

exit 0
