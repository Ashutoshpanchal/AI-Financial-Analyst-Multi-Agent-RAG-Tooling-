"""
Evaluation Service — runs test queries and scores results.

Metrics tracked per query:
  - query_type_match:   did the router classify it correctly?
  - tool_used:          did the right tool get called?
  - answer_contains:    does the answer include expected substrings?
  - is_valid:           did the critic approve the answer?
  - latency_ms:         how long did it take?

All results are logged to Langfuse as evaluation traces so you can
track accuracy over time in the Langfuse dashboard.
"""

import time
import json
from pathlib import Path
from app.services.analyst_service import run_analysis
from app.observability.tracer import get_langfuse_client


QUERIES_PATH = Path(__file__).parent.parent.parent / "tests" / "eval" / "queries.json"


def load_eval_queries() -> list[dict]:
    with open(QUERIES_PATH) as f:
        return json.load(f)


def score_result(result: dict, expected: dict) -> dict:
    """Score a single result against its expected values."""
    answer = (result.get("answer") or "").lower()

    # 1. Did router classify correctly?
    query_type_match = result.get("query_type") == expected.get("query_type")

    # 2. Was the right tool called?
    tool_used = True
    expected_tool = expected.get("expected_tool")
    if expected_tool:
        tool_used = expected_tool in result.get("tool_results", {})

    # 3. Does the answer contain expected substrings?
    expected_contains = expected.get("expected_contains", [])
    contains_checks = {
        phrase: phrase.lower() in answer
        for phrase in expected_contains
    }
    answer_contains = all(contains_checks.values())

    # 4. Did the critic approve?
    is_valid = result.get("is_valid", True)

    # Overall pass: all checks must pass
    passed = query_type_match and tool_used and answer_contains and is_valid

    return {
        "passed": passed,
        "query_type_match": query_type_match,
        "tool_used": tool_used,
        "answer_contains": answer_contains,
        "contains_detail": contains_checks,
        "is_valid": is_valid,
    }


async def run_evaluation(query_ids: list[str] | None = None) -> dict:
    """
    Run evaluation on all queries (or a subset by ID).
    Logs each result to Langfuse and returns a summary.
    """
    queries = load_eval_queries()
    if query_ids:
        queries = [q for q in queries if q["id"] in query_ids]

    langfuse = get_langfuse_client()
    results = []

    for query in queries:
        start = time.time()

        try:
            result = await run_analysis(
                query=query["query"],
                user_id="eval_pipeline",
            )
            latency_ms = round((time.time() - start) * 1000, 2)
            scores = score_result(result, query)

            eval_record = {
                "id":          query["id"],
                "query":       query["query"],
                "latency_ms":  latency_ms,
                "answer":      result.get("answer", ""),
                "query_type":  result.get("query_type"),
                "tool_results": list(result.get("tool_results", {}).keys()),
                "scores":      scores,
                "tags":        query.get("tags", []),
                "trace_id":    result.get("trace_id"),
            }

            # Log to Langfuse as a score on the trace
            if result.get("trace_id"):
                langfuse.score(
                    trace_id=result["trace_id"],
                    name="eval_passed",
                    value=1.0 if scores["passed"] else 0.0,
                    comment=json.dumps(scores),
                )
                langfuse.score(
                    trace_id=result["trace_id"],
                    name="latency_ms",
                    value=latency_ms,
                )

        except Exception as e:
            latency_ms = round((time.time() - start) * 1000, 2)
            eval_record = {
                "id":         query["id"],
                "query":      query["query"],
                "latency_ms": latency_ms,
                "error":      str(e),
                "scores":     {"passed": False},
                "tags":       query.get("tags", []),
            }

        results.append(eval_record)

    langfuse.flush()

    # Summary stats
    total = len(results)
    passed = sum(1 for r in results if r["scores"].get("passed", False))
    avg_latency = round(
        sum(r["latency_ms"] for r in results) / total if total else 0, 2
    )

    return {
        "total":       total,
        "passed":      passed,
        "failed":      total - passed,
        "pass_rate":   round(passed / total * 100, 1) if total else 0,
        "avg_latency_ms": avg_latency,
        "results":     results,
    }
