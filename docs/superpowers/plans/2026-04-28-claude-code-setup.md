# Claude Code Setup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Set up Claude Code infrastructure — CLAUDE.md, 4 automated hooks, and 4 slash commands (/test, /lint, /optimize, /all) that give scored feedback on code health.

**Architecture:** Hook scripts live in `.claude/hooks/`, are triggered automatically by Claude Code events, and parse tool input from stdin JSON. Slash commands are markdown files in `.claude/commands/` that Claude reads and follows when invoked.

**Tech Stack:** Python 3.11, uv, isort, ruff (format+check), pyright, bandit, radon, pytest-cov, eslint, tsc, bash

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `CLAUDE.md` | Create | Project rules Claude reads every session |
| `.claude/hooks/py-lint.sh` | Create | Runs isort + ruff format + ruff check + pyright via uv after any .py file is written |
| `.claude/hooks/ui-lint.sh` | Create | Runs eslint after any .ts/.tsx file is written |
| `.claude/hooks/git-safety.sh` | Create | Blocks git add/commit/push if .env or cache files staged |
| `.claude/hooks/run-tests.sh` | Create | Runs pytest after every Claude response |
| `.claude/settings.local.json` | Modify | Add hooks config (preserve existing permissions) |
| `.claude/commands/test.md` | Create | /test slash command |
| `.claude/commands/lint.md` | Create | /lint slash command |
| `.claude/commands/optimize.md` | Create | /optimize slash command |
| `.claude/commands/all.md` | Create | /all slash command |

---

## Task 1: Install Missing Dev Dependencies

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add missing tools to pyproject.toml dev dependencies**

Open `pyproject.toml` and update the `[project.optional-dependencies]` dev section to:

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-httpx>=0.30.0",
    "pytest-cov>=5.0.0",
    "ruff>=0.4.0",
    "isort>=5.13.0",
    "pyright>=1.1.0",
    "bandit>=1.7.0",
    "radon>=6.0.0",
]
```

- [ ] **Step 2: Install the new tools via uv**

```bash
uv add --dev isort pyright bandit radon pytest-cov
```

Expected output: Resolved and installed all packages successfully.

- [ ] **Step 3: Verify all tools are available via uv run**

```bash
uv run isort --version && uv run ruff --version && uv run pyright --version && uv run bandit --version && uv run radon --version && uv run pytest --version
```

Expected: version strings for all 6 tools, no errors.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "chore: add mypy, bandit, radon, pytest-cov to dev dependencies"
```

---

## Task 2: Create CLAUDE.md

**Files:**
- Create: `CLAUDE.md`

- [ ] **Step 1: Create CLAUDE.md at project root**

```markdown
# AI Financial Analyst — Project Rules

## Stack
- Backend: Python 3.11, FastAPI, LangGraph, MCP
- Frontend: Next.js (ui/), TypeScript, Tailwind
- Cache: Redis (app/cache/redis_cache.py)
- DB: PostgreSQL + pgvector (app/db/)
- Agents: app/agents/ — planner, router, rag, yfinance, computation, aggregator, critic, mcp_enrichment
- Workflows: app/workflows/ — LangGraph graph, parallel execution, state
- Tests: tests/ — run with: pytest tests/ --cov=app

## Code Rules
- New agents go in app/agents/, follow the pattern in existing agents
- New tools go in app/tools/
- New API endpoints go in app/api/v1/
- Linter: ruff (Python), eslint (Next.js)
- Type checker: mypy (Python), tsc (Next.js)
- Security scanner: bandit (Python)
- Complexity tool: radon (Python)

## Git Rules — CRITICAL
- NEVER commit: .env, .env.local, __pycache__, .DS_Store, graphify-out/, node_modules/, .next/
- Always check staged files before committing
- Use descriptive commit messages: feat:, fix:, chore:, refactor:

## Slash Commands Available
- /test     → run test suite with coverage
- /lint     → code quality check with score
- /optimize → complexity + security analysis with score
- /all      → runs all three with combined score
```

- [ ] **Step 2: Verify the file exists**

```bash
cat CLAUDE.md
```

Expected: full file contents printed.

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "chore: add CLAUDE.md with project rules and slash command docs"
```

---

## Task 3: Create Hook Scripts

**Files:**
- Create: `.claude/hooks/py-lint.sh`
- Create: `.claude/hooks/ui-lint.sh`
- Create: `.claude/hooks/git-safety.sh`
- Create: `.claude/hooks/run-tests.sh`

- [ ] **Step 1: Create hooks directory**

```bash
mkdir -p .claude/hooks
```

- [ ] **Step 2: Create Python lint hook**

Create `.claude/hooks/py-lint.sh`:

```bash
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
```

- [ ] **Step 3: Create UI lint hook**

Create `.claude/hooks/ui-lint.sh`:

```bash
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
```

- [ ] **Step 4: Create git safety hook**

Create `.claude/hooks/git-safety.sh`:

```bash
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
STAGED=$(git diff --cached --name-only 2>/dev/null)

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
  echo -e "$FOUND_ISSUES"
  echo ""
  echo "Remove them with: git restore --staged <file>"
  echo "Add to .gitignore if this keeps happening."
  exit 1
fi

exit 0
```

- [ ] **Step 5: Create stop/test runner hook**

Create `.claude/hooks/run-tests.sh`:

```bash
#!/bin/bash
# Triggered by Stop. Runs pytest after every Claude response.
PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$PROJECT_DIR"

# Skip if no tests exist yet
if [ ! -d "tests" ] || [ -z "$(find tests -name '*.py' -not -name '__init__.py' 2>/dev/null)" ]; then
  exit 0
fi

echo ""
echo "--- Auto test run ---"
python3 -m pytest tests/ -q --tb=line 2>&1 | tail -8
```

- [ ] **Step 6: Make all scripts executable**

```bash
chmod +x .claude/hooks/py-lint.sh .claude/hooks/ui-lint.sh .claude/hooks/git-safety.sh .claude/hooks/run-tests.sh
```

- [ ] **Step 7: Smoke test git-safety hook manually**

```bash
echo '{"tool_input": {"command": "git add ."}}' | bash .claude/hooks/git-safety.sh
```

Expected: exits 0 (nothing staged currently, or clean pass)

- [ ] **Step 8: Smoke test py-lint hook manually**

```bash
echo '{"tool_input": {"file_path": "app/main.py"}}' | bash .claude/hooks/py-lint.sh
```

Expected: runs ruff + mypy on app/main.py, prints results.

- [ ] **Step 9: Commit**

```bash
git add .claude/hooks/
git commit -m "chore: add Claude Code hook scripts for lint, UI lint, git safety, and test runner"
```

---

## Task 4: Update settings.local.json With Hooks

**Files:**
- Modify: `.claude/settings.local.json`

- [ ] **Step 1: Replace settings.local.json with hooks + existing permissions**

Write the following to `.claude/settings.local.json` (preserves all existing `allow` entries):

```json
{
  "permissions": {
    "allow": [
      "Bash(docker exec:*)",
      "Bash(docker compose:*)",
      "Bash(curl -s http://localhost:8000/api/v1/mcp/status)",
      "Bash(python3 -m json.tool)",
      "Bash(python3 -c \"import sys,json; d=json.load\\(sys.stdin\\); print\\(''''Status:'''', d[''''status'''']\\); print\\(''''Tools:'''', [t[''''name''''] for t in d.get\\(''''tools'''',[]\\)]\\)\")",
      "Bash(python3 -c \"import sys,json; c=json.load\\(sys.stdin\\); svc=c[''''services''''][''''app'''']; print\\(svc.get\\(''''environment'''', {}\\)\\)\")",
      "Bash(curl -s http://localhost:8000/api/v1/health)",
      "Bash(python3 -c \"import sys,json; d=json.load\\(sys.stdin\\); print\\(''''trace_id:'''', d.get\\(''''trace_id''''\\)\\); print\\(''''type:'''', d.get\\(''''query_type''''\\)\\)\")",
      "Bash(grep -r RetryPolicy .venv/lib/python3.11/site-packages/langgraph/ --include=*.py -l)",
      "Bash(python -c \"import langgraph; print\\(langgraph.__version__\\)\")",
      "Bash(find /Users/ashutoshpanchal/Desktop/Project/AI-Financial-Analyst-Multi-Agent-RAG-Tooling- -name requirements*.txt -o -name pyproject.toml)",
      "Bash(/opt/homebrew/bin/python3.13 -m pip install graphifyy)",
      "Bash(/opt/homebrew/bin/python3.13 -m pip install graphifyy --break-system-packages)"
    ]
  },
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "bash .claude/hooks/py-lint.sh"
          },
          {
            "type": "command",
            "command": "bash .claude/hooks/ui-lint.sh"
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "bash .claude/hooks/git-safety.sh"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash .claude/hooks/run-tests.sh"
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 2: Validate JSON is valid**

```bash
python3 -m json.tool .claude/settings.local.json > /dev/null && echo "JSON valid"
```

Expected: `JSON valid`

- [ ] **Step 3: Commit**

```bash
git add .claude/settings.local.json
git commit -m "chore: add PostToolUse, PreToolUse, and Stop hooks to Claude Code settings"
```

---

## Task 5: Create /test Command

**Files:**
- Create: `.claude/commands/test.md`

- [ ] **Step 1: Create commands directory**

```bash
mkdir -p .claude/commands
```

- [ ] **Step 2: Create test.md**

Create `.claude/commands/test.md`:

```markdown
Run the full test suite for the AI Financial Analyst project and report results clearly.

## Steps

1. Run this exact command:
   ```
   cd /Users/ashutoshpanchal/Desktop/Project/AI-Financial-Analyst-Multi-Agent-RAG-Tooling- && python3 -m pytest tests/ --cov=app --cov-report=term-missing -q 2>&1
   ```

2. Parse the output and report in this format:

```
Tests: X/Y passing
Coverage: Z%

Failed tests:
  - tests/path/test_file.py::test_name
    Error: <one-line summary of the failure>

Coverage by module:
  app/agents/rag_agent.py         85%
  app/agents/planner_agent.py     72%
  app/services/analyst_service.py 68%
  (show all modules below 80%)
```

3. If all tests pass, say so clearly.
4. If pytest is not installed, say: "Run: pip install pytest pytest-cov"
5. If the tests/ directory has no test files yet, say: "No tests found yet."
```

- [ ] **Step 3: Verify file created**

```bash
cat .claude/commands/test.md
```

Expected: full file contents.

- [ ] **Step 4: Commit**

```bash
git add .claude/commands/test.md
git commit -m "chore: add /test slash command"
```

---

## Task 6: Create /lint Command

**Files:**
- Create: `.claude/commands/lint.md`

- [ ] **Step 1: Create lint.md**

Create `.claude/commands/lint.md`:

```markdown
Run code quality checks across Python and Next.js, calculate a lint score, and suggest fixes.

## Steps

### Python lint

1. Run isort check (dry-run, shows what would change):
   ```
   cd /Users/ashutoshpanchal/Desktop/Project/AI-Financial-Analyst-Multi-Agent-RAG-Tooling- && uv run isort app/ --check --diff 2>&1
   ```

2. Run ruff format check:
   ```
   cd /Users/ashutoshpanchal/Desktop/Project/AI-Financial-Analyst-Multi-Agent-RAG-Tooling- && uv run ruff format app/ --check 2>&1
   ```

3. Run ruff lint:
   ```
   cd /Users/ashutoshpanchal/Desktop/Project/AI-Financial-Analyst-Multi-Agent-RAG-Tooling- && uv run ruff check app/ --output-format=text 2>&1
   ```

4. Run pyright type checker:
   ```
   cd /Users/ashutoshpanchal/Desktop/Project/AI-Financial-Analyst-Multi-Agent-RAG-Tooling- && uv run pyright app/ 2>&1
   ```

### UI lint (only if ui/node_modules exists)

3. Run eslint:
   ```
   cd /Users/ashutoshpanchal/Desktop/Project/AI-Financial-Analyst-Multi-Agent-RAG-Tooling-/ui && npx eslint src/ 2>&1
   ```

### Calculate score

5. Count:
   - `isort_issues` = number of files isort would reorder
   - `ruff_errors` = number of ruff check error/warning lines
   - `pyright_errors` = number of pyright error lines
   - `eslint_warnings` = number of eslint warning/error lines
   - `lint_score` = max(0, 100 - (isort_issues * 3) - (ruff_errors * 5) - (pyright_errors * 5) - (eslint_warnings * 2))

### Report in this format

```
Lint Score: XX/100

Python (isort): N files with wrong import order — run: uv run isort app/
Python (ruff format): N files need formatting — run: uv run ruff format app/
Python (ruff check): N issues
  - app/agents/rag_agent.py:45 — F401 unused import 'os'
  - app/services/analyst_service.py:12 — E711 comparison to None
Python (pyright): N issues
  - app/workflows/graph.py:78 — error: Argument of type "str" cannot be assigned to "int"
UI (eslint): N issues
  - ui/src/components/Chat.tsx:23 — no-unused-vars

Suggested fixes:
  1. [auto-fix] Run: uv run isort app/ && uv run ruff format app/
  2. [manual]   app/agents/rag_agent.py:45 — remove unused import 'os'
  3. [manual]   app/workflows/graph.py:78 — fix type mismatch on line 78
```

5. If lint score is 100, say: "Perfect lint score."
```

- [ ] **Step 2: Commit**

```bash
git add .claude/commands/lint.md
git commit -m "chore: add /lint slash command"
```

---

## Task 7: Create /optimize Command

**Files:**
- Create: `.claude/commands/optimize.md`

- [ ] **Step 1: Create optimize.md**

Create `.claude/commands/optimize.md`:

```markdown
Analyze code complexity and security for the AI Financial Analyst project. Give a score and ranked improvement suggestions.

## Steps

### Complexity analysis

1. Run radon cyclomatic complexity:
   ```
   cd /Users/ashutoshpanchal/Desktop/Project/AI-Financial-Analyst-Multi-Agent-RAG-Tooling- && python3 -m radon cc app/ -a -s --min=B 2>&1
   ```
   This shows functions with complexity grade B or worse (complexity >= 6).

2. Run radon maintainability index:
   ```
   cd /Users/ashutoshpanchal/Desktop/Project/AI-Financial-Analyst-Multi-Agent-RAG-Tooling- && python3 -m radon mi app/ -s 2>&1
   ```

### Security analysis

3. Run bandit:
   ```
   cd /Users/ashutoshpanchal/Desktop/Project/AI-Financial-Analyst-Multi-Agent-RAG-Tooling- && python3 -m bandit -r app/ -ll -f text 2>&1
   ```
   (`-ll` = medium severity and above only)

### Calculate scores

4. Count:
   - `complex_functions` = number of functions with complexity > 10
   - `complexity_score` = max(0, 100 - complex_functions * 10)
   - `high_issues` = number of HIGH severity bandit findings
   - `medium_issues` = number of MEDIUM severity bandit findings
   - `security_score` = max(0, 100 - high_issues * 20 - medium_issues * 10)
   - `optimize_score` = round(complexity_score * 0.5 + security_score * 0.5)

### Report in this format

```
Optimize Score: XX/100
  Complexity: YY/100
  Security:   ZZ/100

Complexity issues:
  - app/agents/aggregator_agent.py::merge_results  complexity=14 (grade D)
    → Suggestion: split into merge_financial_data() and merge_agent_outputs()
  - app/workflows/graph.py::build_graph            complexity=11 (grade C)
    → Suggestion: extract node registration into separate helper

Security issues:
  - HIGH   app/config/settings.py:12 — hardcoded secret string detected
    → Fix: move to environment variable, load with os.getenv()
  - MEDIUM app/mcp/client.py:45 — subprocess call with shell=True
    → Fix: use shell=False and pass args as list

Ranked fix list (by impact):
  1. [SECURITY HIGH]  settings.py:12 — hardcoded secret
  2. [COMPLEXITY D]   aggregator_agent.py::merge_results — refactor
  3. [SECURITY MED]   mcp/client.py:45 — shell=True
```

5. If bandit is not installed, say: "Run: pip install bandit"
6. If radon is not installed, say: "Run: pip install radon"
```

- [ ] **Step 2: Commit**

```bash
git add .claude/commands/optimize.md
git commit -m "chore: add /optimize slash command"
```

---

## Task 8: Create /all Command

**Files:**
- Create: `.claude/commands/all.md`

- [ ] **Step 1: Create all.md**

Create `.claude/commands/all.md`:

```markdown
Run /test, /lint, and /optimize together and produce a combined health score with top-5 priority fixes.

## Steps

Run all three analyses in sequence:

### 1. Tests
```
cd /Users/ashutoshpanchal/Desktop/Project/AI-Financial-Analyst-Multi-Agent-RAG-Tooling- && python3 -m pytest tests/ --cov=app --cov-report=term-missing -q 2>&1
```
Calculate test_score:
- passing_rate = passed / total (0 if no tests)
- coverage_pct = overall coverage % / 100
- test_score = round((passing_rate * 0.6 + coverage_pct * 0.4) * 100)

### 2. Lint
```
python3 -m ruff check app/ --output-format=text 2>&1
python3 -m mypy app/ --ignore-missing-imports --no-error-summary 2>&1
```
Calculate lint_score:
- lint_score = max(0, 100 - ruff_errors * 5 - mypy_errors * 5)

### 3. Optimize
```
python3 -m radon cc app/ -a -s --min=B 2>&1
python3 -m bandit -r app/ -ll -f text 2>&1
```
Calculate optimize_score:
- complexity_score = max(0, 100 - complex_functions * 10)
- security_score = max(0, 100 - high_issues * 20 - medium_issues * 10)
- optimize_score = round(complexity_score * 0.5 + security_score * 0.5)

### 4. Combined score
combined_score = round(test_score * 0.30 + lint_score * 0.40 + optimize_score * 0.30)

### 5. Collect ALL issues from all three analyses into one list.
Rank by impact:
  - SECURITY HIGH = priority 1
  - Test FAIL = priority 2
  - SECURITY MEDIUM = priority 3
  - COMPLEXITY grade D (>12) = priority 4
  - Lint ERROR = priority 5
  - COMPLEXITY grade C (>10) = priority 6
  - Lint WARNING = priority 7

### Report in this exact format

```
Overall Score: XX/100
  Tests    [████████░░]  YY%   (A/B passing, Z% coverage)
  Lint     [████████░░]  YY%   (N issues)
  Optimize [███████░░░]  YY%   (N issues)

Top 5 fixes (by impact):
  1. [SECURITY HIGH]  app/config/settings.py:12 — hardcoded secret
  2. [TEST FAIL]      tests/eval/test_rag.py::test_retrieval — assertion error
  3. [SECURITY MED]   app/mcp/client.py:45 — shell=True in subprocess
  4. [COMPLEXITY D]   app/agents/aggregator_agent.py::merge_results
  5. [LINT ERROR]     app/workflows/graph.py:78 — mypy type mismatch

Run /test, /lint, or /optimize individually for full details on each area.
```
```

- [ ] **Step 2: Commit**

```bash
git add .claude/commands/all.md
git commit -m "chore: add /all slash command combining test, lint, and optimize"
```

---

## Task 9: End-to-End Verification

- [ ] **Step 1: Verify all files exist**

```bash
ls -la CLAUDE.md .claude/hooks/ .claude/commands/ .claude/settings.local.json
```

Expected: all 10 files present.

- [ ] **Step 2: Verify hooks JSON is valid**

```bash
python3 -m json.tool .claude/settings.local.json > /dev/null && echo "JSON valid"
```

Expected: `JSON valid`

- [ ] **Step 3: Test git safety hook blocks .env**

```bash
# Temporarily stage .env to test the block
git add .env 2>/dev/null || true
echo '{"tool_input": {"command": "git add .env"}}' | bash .claude/hooks/git-safety.sh
echo "Exit code: $?"
git restore --staged .env 2>/dev/null || true
```

Expected: prints blocked message, exit code 1.

- [ ] **Step 4: Test git safety hook passes clean files**

```bash
echo '{"tool_input": {"command": "git add CLAUDE.md"}}' | bash .claude/hooks/git-safety.sh
echo "Exit code: $?"
```

Expected: exits 0 (no blocked files).

- [ ] **Step 5: Test py-lint hook on a real file**

```bash
echo "{\"tool_input\": {\"file_path\": \"$(pwd)/app/main.py\"}}" | bash .claude/hooks/py-lint.sh
```

Expected: runs ruff + mypy on app/main.py, prints results.

- [ ] **Step 6: Final commit of verification**

```bash
git status
```

Expected: working tree clean (all committed in prior tasks).

---

## Dependencies Summary

| Tool | Source | Already installed |
|------|--------|------------------|
| uv | system | Must be installed: `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| ruff | pyproject.toml dev | Yes (via uv run) |
| isort | pyproject.toml dev | Added in Task 1 (via uv run) |
| pyright | pyproject.toml dev | Added in Task 1 (via uv run) |
| pytest | pyproject.toml dev | Yes (via uv run) |
| bandit | pyproject.toml dev | Added in Task 1 (via uv run) |
| radon | pyproject.toml dev | Added in Task 1 (via uv run) |
| pytest-cov | pyproject.toml dev | Added in Task 1 (via uv run) |
| eslint | ui/package.json | Yes (if ui/npm install done) |
| tsc | ui/package.json | Yes (if ui/npm install done) |
