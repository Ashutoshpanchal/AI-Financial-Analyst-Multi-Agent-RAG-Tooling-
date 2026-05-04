Run the full test suite for the AI Financial Analyst project and report results clearly.

## Steps

1. Run this exact command:
   ```
   cd /Users/ashutoshpanchal/Desktop/Project/AI-Financial-Analyst-Multi-Agent-RAG-Tooling- && uv run pytest tests/ --cov=app --cov-report=term-missing -q 2>&1
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
4. If pytest is not installed, say: "Run: uv add --dev pytest pytest-cov"
5. If the tests/ directory has no test files yet, say: "No tests found yet."
