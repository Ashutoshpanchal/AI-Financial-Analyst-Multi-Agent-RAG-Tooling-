Analyze code complexity and security for the AI Financial Analyst project. Give a score and ranked improvement suggestions.

## Steps

### Complexity analysis

1. Run radon cyclomatic complexity:
   ```
   cd /Users/ashutoshpanchal/Desktop/Project/AI-Financial-Analyst-Multi-Agent-RAG-Tooling- && uv run radon cc app/ -a -s --min=B 2>&1
   ```
   This shows functions with complexity grade B or worse (complexity >= 6).

2. Run radon maintainability index:
   ```
   cd /Users/ashutoshpanchal/Desktop/Project/AI-Financial-Analyst-Multi-Agent-RAG-Tooling- && uv run radon mi app/ -s 2>&1
   ```

### Security analysis

3. Run bandit:
   ```
   cd /Users/ashutoshpanchal/Desktop/Project/AI-Financial-Analyst-Multi-Agent-RAG-Tooling- && uv run bandit -r app/ -ll -f text 2>&1
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

5. If bandit or radon is not installed, say: "Run: uv add --dev bandit radon"
