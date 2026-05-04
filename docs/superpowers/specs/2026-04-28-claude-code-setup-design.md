# Claude Code Setup Design
**Date:** 2026-04-28
**Project:** AI Financial Analyst — Multi-Agent RAG Tooling

---

## Overview

Set up Claude Code infrastructure for this project: project rules (CLAUDE.md), automated hooks, and 4 custom slash commands that give scored feedback on code health.

---

## 1. CLAUDE.md

A project-level instruction file Claude reads at the start of every session.

**Contents:**
- Stack: Python 3.11, FastAPI, LangGraph, Next.js, Docker, Redis, PostgreSQL
- Agent pattern: new agents go in `app/agents/`, follow existing structure
- New tools go in `app/tools/`, API endpoints in `app/api/v1/`
- Linter: `ruff` + `mypy` (Python), `eslint` + `tsc` (Next.js)
- Tests: `pytest` in `tests/`, run with `pytest --cov=app`
- Security scanner: `bandit`
- Never commit: `.env`, `.env.local`, `__pycache__`, `.DS_Store`, `graphify-out/`

**Location:** `CLAUDE.md` (project root)

---

## 2. Hooks (settings.local.json)

Four hooks added to `.claude/settings.local.json`. All are shell commands that run automatically.

| Hook | Type | Trigger | Command |
|------|------|---------|---------|
| Python lint | PostToolUse | Claude writes any `.py` file | Shell script reads file path from stdin JSON (`$.file_path`), runs `ruff check` + `mypy` on it |
| UI lint | PostToolUse | Claude writes any `.ts` or `.tsx` file | Shell script reads file path from stdin JSON, runs `eslint` + `tsc --noEmit` |
| Git safety | PreToolUse | Claude runs any `git` command | Shell script reads command from stdin JSON, checks `git diff --cached --name-only` for `.env`, `__pycache__`, `.DS_Store` — exits 1 if found |
| Test runner | Stop | Claude finishes any response | `cd <project> && pytest tests/ -q --tb=short 2>&1 | tail -5` |

**Error behavior:**
- Hooks that exit non-zero block the action and surface the error to Claude
- Claude must resolve the error before proceeding

---

## 3. Custom Slash Commands

Four markdown files in `.claude/commands/`. Each defines what Claude does when the command is invoked.

### `/test`
**Purpose:** Run the test suite and report results.

**Steps:**
1. Run `pytest tests/ --cov=app --cov-report=term-missing -q`
2. Parse: total tests, passed, failed, coverage %
3. Output structured report with failed test names and coverage per module

**Output format:**
```
Tests: 12/15 passing
Coverage: 74%
Failed:
  - tests/eval/test_rag.py::test_retrieval (assertion error)
```

---

### `/lint`
**Purpose:** Check code quality across Python and Next.js, give a score.

**Steps:**
1. Run `ruff check app/ --output-format=json`
2. Run `mypy app/ --ignore-missing-imports`
3. Run `cd ui && npx eslint src/ --format=json`
4. Run `cd ui && npx tsc --noEmit`
5. Calculate score: 100 − (errors × 5) − (warnings × 2), floor 0
6. Output issues grouped by file with fix suggestions

**Output format:**
```
Lint Score: 82/100
Python (ruff): 3 warnings in app/agents/rag_agent.py
Python (mypy): 1 error in app/services/analyst_service.py
UI (eslint): 2 warnings in ui/src/components/Chat.tsx
→ Fix suggestions for each issue
```

---

### `/optimize`
**Purpose:** Analyze code complexity and security, give a score, suggest improvements.

**Steps:**
1. Run `radon cc app/ -a -s` (cyclomatic complexity per function)
2. Run `radon mi app/ -s` (maintainability index)
3. Run `bandit -r app/ -f json -ll` (security scan, medium+ severity)
4. Score:
   - Complexity: 100 − (count of functions with complexity > 10) × 10
   - Security: 100 − (high issues × 20) − (medium issues × 10)
   - Combined optimize score = (complexity 50% + security 50%)
5. Output ranked list of improvements by impact

**Output format:**
```
Optimize Score: 71/100

Complexity (60/100):
  - aggregator_agent.py::merge_results  complexity=14 → suggest breaking into 2 functions
  - rag_agent.py::retrieve              complexity=12 → suggest extracting filter logic

Security (82/100):
  - HIGH: app/config/settings.py:12 — hardcoded API key pattern detected
  - MEDIUM: app/mcp/client.py:45 — subprocess call with shell=True

→ Ranked fix list (by impact)
```

---

### `/all`
**Purpose:** Run `/test` + `/lint` + `/optimize` together, produce a combined score and top-5 fix list.

**Steps:**
1. Run all three commands sequentially
2. Combined score = Tests 30% + Lint 40% + Optimize 30%
3. Merge all issues, rank by: severity × impact
4. Output top 5 fixes across all dimensions

**Output format:**
```
Overall Score: 76/100
  Tests    ████████░░  74%  (12/15 passing)
  Lint     ████████░░  82%  (5 issues)
  Optimize ███████░░░  71%  (5 issues)

Top 5 fixes (by impact):
  1. [SECURITY HIGH] Hardcoded key in settings.py:12
  2. [COMPLEXITY]    aggregator_agent.py::merge_results — refactor
  3. [TEST]          test_rag.py::test_retrieval — failing
  4. [LINT]          analyst_service.py:34 — mypy type error
  5. [SECURITY MED]  mcp/client.py:45 — shell=True in subprocess
```

---

## 4. File Structure

```
AI-Financial-Analyst-Multi-Agent-RAG-Tooling-/
├── CLAUDE.md                          ← project rules
├── .claude/
│   ├── settings.local.json            ← hooks + permissions (update existing)
│   └── commands/
│       ├── test.md                    ← /test command
│       ├── lint.md                    ← /lint command
│       ├── optimize.md                ← /optimize command
│       └── all.md                     ← /all command
└── docs/
    └── superpowers/
        └── specs/
            └── 2026-04-28-claude-code-setup-design.md  ← this file
```

---

## 5. Dependencies Required

| Tool | Purpose | Install |
|------|---------|---------|
| `ruff` | Python linter | `pip install ruff` |
| `mypy` | Python type checker | `pip install mypy` |
| `bandit` | Python security scanner | `pip install bandit` |
| `radon` | Code complexity metrics | `pip install radon` |
| `pytest-cov` | Test coverage | `pip install pytest-cov` |
| `eslint` | JS/TS linter | already in `ui/package.json` |
| `typescript` | TS type checker | already in `ui/package.json` |

---

## 6. Error Handling

- If a tool is not installed, the command prints a clear install instruction and exits gracefully — does not crash the entire command
- If tests directory is empty, `/test` skips and notes it
- If `ui/` has no node_modules, UI lint steps are skipped with a warning
- Hook failures surface the raw error message to Claude so it can fix the issue before retrying

---

## 7. Success Criteria

- All 4 hooks fire correctly at the right moment
- All 4 slash commands produce structured, readable output
- `/all` score is a true weighted combination of the 3 sub-scores
- No `.env` or cache files can be committed even if Claude tries
- Claude reads CLAUDE.md conventions and follows them in new code
