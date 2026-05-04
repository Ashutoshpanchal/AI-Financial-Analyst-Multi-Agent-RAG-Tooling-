Run /test, /lint, and /optimize together and produce a combined health score with top-5 priority fixes.

## Steps

Run all three analyses in sequence:

### 1. Tests
```
cd /Users/ashutoshpanchal/Desktop/Project/AI-Financial-Analyst-Multi-Agent-RAG-Tooling- && uv run pytest tests/ --cov=app --cov-report=term-missing -q 2>&1
```
Calculate test_score:
- passing_rate = passed / total (0 if no tests)
- coverage_pct = overall coverage % / 100
- test_score = round((passing_rate * 0.6 + coverage_pct * 0.4) * 100)

### 2. Lint
```
cd /Users/ashutoshpanchal/Desktop/Project/AI-Financial-Analyst-Multi-Agent-RAG-Tooling- && uv run isort app/ --check --diff 2>&1
cd /Users/ashutoshpanchal/Desktop/Project/AI-Financial-Analyst-Multi-Agent-RAG-Tooling- && uv run ruff format app/ --check 2>&1
cd /Users/ashutoshpanchal/Desktop/Project/AI-Financial-Analyst-Multi-Agent-RAG-Tooling- && uv run ruff check app/ --output-format=text 2>&1
cd /Users/ashutoshpanchal/Desktop/Project/AI-Financial-Analyst-Multi-Agent-RAG-Tooling- && uv run pyright app/ 2>&1
```
Calculate lint_score:
- lint_score = max(0, 100 - isort_issues * 3 - ruff_errors * 5 - pyright_errors * 5)

### 3. Optimize
```
cd /Users/ashutoshpanchal/Desktop/Project/AI-Financial-Analyst-Multi-Agent-RAG-Tooling- && uv run radon cc app/ -a -s --min=B 2>&1
cd /Users/ashutoshpanchal/Desktop/Project/AI-Financial-Analyst-Multi-Agent-RAG-Tooling- && uv run bandit -r app/ -ll -f text 2>&1
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
  5. [LINT ERROR]     app/workflows/graph.py:78 — pyright type mismatch

Run /test, /lint, or /optimize individually for full details on each area.
```
