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

5. Run eslint:
   ```
   cd /Users/ashutoshpanchal/Desktop/Project/AI-Financial-Analyst-Multi-Agent-RAG-Tooling-/ui && npx eslint src/ 2>&1
   ```

### Calculate score

6. Count:
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
Python (pyright): N issues
  - app/workflows/graph.py:78 — error: Argument of type "str" cannot be assigned to "int"
UI (eslint): N issues
  - ui/src/components/Chat.tsx:23 — no-unused-vars

Suggested fixes:
  1. [auto-fix] Run: uv run isort app/ && uv run ruff format app/
  2. [manual]   app/agents/rag_agent.py:45 — remove unused import 'os'
  3. [manual]   app/workflows/graph.py:78 — fix type mismatch on line 78
```

7. If lint score is 100, say: "Perfect lint score."
