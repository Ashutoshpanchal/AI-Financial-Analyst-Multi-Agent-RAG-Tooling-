"""
Standalone eval runner — run this directly without the server.

Usage:
    python tests/eval/run_eval.py
    python tests/eval/run_eval.py --ids eval_001 eval_002
"""

import asyncio
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.eval_service import run_evaluation


async def main(query_ids: list[str] | None = None):
    print("Running evaluation...\n")
    summary = await run_evaluation(query_ids=query_ids)

    print(f"{'='*50}")
    print(f"Results: {summary['passed']}/{summary['total']} passed ({summary['pass_rate']}%)")
    print(f"Avg latency: {summary['avg_latency_ms']}ms")
    print(f"{'='*50}\n")

    for r in summary["results"]:
        status = "PASS" if r["scores"].get("passed") else "FAIL"
        print(f"[{status}] {r['id']} — {r['query'][:60]}...")
        if not r["scores"].get("passed"):
            scores = r["scores"]
            if not scores.get("query_type_match"):
                print(f"       Query type mismatch")
            if not scores.get("tool_used"):
                print(f"       Expected tool not called")
            if not scores.get("answer_contains"):
                detail = scores.get("contains_detail", {})
                missing = [k for k, v in detail.items() if not v]
                print(f"       Missing in answer: {missing}")
        if r.get("error"):
            print(f"       Error: {r['error']}")
        print()

    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ids", nargs="*", help="Specific query IDs to run")
    args = parser.parse_args()
    asyncio.run(main(query_ids=args.ids))
