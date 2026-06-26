"""
DEPRECATED: This module is dead code (not imported anywhere).
Use eval_framework.py directly instead. See docs/DEAD-CODE-AUDIT.md.

vinhlong360 — Run Evaluation Benchmark against Live Server.

Goi /chat endpoint voi 54 test cases tu eval_framework,
do luong chat luong tra loi thuc te.

Usage:
  python agent/run_eval.py                    # Full 54 test cases
  python agent/run_eval.py --quick            # 10 test cases nhanh
  python agent/run_eval.py --category factual # Chi chay 1 category
"""

import json
import os
import re
import sys
import time
import argparse
import unicodedata
from pathlib import Path

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

AGENT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(AGENT_DIR))

import requests
from eval_framework import BENCHMARK_SUITE, run_benchmark, EvalRunner, eval_runner

SERVER_URL = os.environ.get("EVAL_SERVER", "http://localhost:8360")


def _normalize_vn(text: str) -> str:
    """Strip Vietnamese diacritics for fuzzy matching."""
    s = unicodedata.normalize("NFD", text.lower())
    s = re.sub(r"[̀-ͯ]", "", s)
    return s.replace("đ", "d").replace("Đ", "D")


def call_server(query: str):
    """Call /chat endpoint and return (reply, tools_used)."""
    try:
        resp = requests.post(
            f"{SERVER_URL}/chat",
            json={"message": query, "session_id": f"eval-{int(time.time())}"},
            timeout=180,
        )
        if resp.status_code == 200:
            data = resp.json()
            reply = data.get("reply", "")
            raw_tools = data.get("tool_calls", [])
            tools = []
            for t in raw_tools:
                if isinstance(t, dict):
                    tools.append(t.get("name", ""))
                elif isinstance(t, str):
                    tools.append(t)
            return reply, tools
        else:
            return f"[ERROR {resp.status_code}] {resp.text[:200]}", []
    except Exception as e:
        return f"[ERROR] {e}", []


def run_quick_eval():
    """Run 10 representative test cases for quick check."""
    # Pick 10 diverse cases
    categories = {}
    for tc in BENCHMARK_SUITE:
        if tc.category not in categories:
            categories[tc.category] = tc
        if len(categories) >= 6:
            break

    quick_cases = list(categories.values())
    # Add a few more to reach 10
    remaining = [tc for tc in BENCHMARK_SUITE if tc not in quick_cases]
    quick_cases.extend(remaining[:max(0, 10 - len(quick_cases))])

    print(f"\n{'='*60}")
    print(f"  QUICK EVAL — {len(quick_cases)} test cases")
    print(f"  Server: {SERVER_URL}")
    print(f"{'='*60}\n")

    scores = []
    for i, tc in enumerate(quick_cases, 1):
        print(f"  [{i}/{len(quick_cases)}] {tc.category}: {tc.query[:50]}...", end=" ", flush=True)
        t0 = time.time()
        reply, tools = call_server(tc.query)
        dur = time.time() - t0

        # Simple scoring with diacritics-insensitive matching
        score = 0.0
        reply_norm = _normalize_vn(reply)
        if reply and not reply.startswith("[ERROR"):
            score += 2.0  # Got a response
            if len(reply) > 50:
                score += 0.5  # Meaningful length
            # Check expected keywords (diacritics-insensitive)
            for kw in tc.expected_keywords:
                if _normalize_vn(kw) in reply_norm:
                    score += 1.0
            score = min(score, 5.0)

        scores.append(score)
        status = "PASS" if score >= 3 else "WARN" if score >= 2 else "FAIL"
        print(f"{status} (score={score:.1f}, {dur:.1f}s)")

    avg = sum(scores) / len(scores) if scores else 0
    passed = sum(1 for s in scores if s >= 3)
    print(f"\n{'='*60}")
    print(f"  RESULT: {passed}/{len(scores)} passed, avg score={avg:.2f}/5.0")
    print(f"{'='*60}\n")
    return avg


def run_full_eval(category_filter=None):
    """Run full eval_framework benchmark."""
    cases = BENCHMARK_SUITE
    if category_filter:
        cases = [tc for tc in cases if tc.category == category_filter]

    print(f"\n{'='*60}")
    print(f"  FULL EVAL — {len(cases)} test cases")
    if category_filter:
        print(f"  Category: {category_filter}")
    print(f"  Server: {SERVER_URL}")
    print(f"{'='*60}\n")

    t0 = time.time()
    result = run_benchmark(call_server)
    dur = time.time() - t0

    print(f"\n{'='*60}")
    print(f"  BENCHMARK RESULTS")
    print(f"{'='*60}")
    print(f"  Total cases:  {result['total']}")
    print(f"  Passed:       {result['passed']}")
    print(f"  Failed:       {result['failed']}")
    print(f"  Avg score:    {result['avg_score']:.2f}/5.0")
    print(f"  Duration:     {dur:.1f}s")
    print(f"\n  Scores by category:")
    for cat, cat_score in sorted(result.get("scores_by_category", {}).items()):
        print(f"    {cat}: {cat_score:.2f}")
    if result.get("regressions"):
        print(f"\n  REGRESSIONS: {len(result['regressions'])}")
        for reg in result["regressions"][:5]:
            print(f"    - {reg}")
    print(f"{'='*60}\n")

    # Save result
    report_path = AGENT_DIR / "data" / "eval" / f"eval-{int(time.time())}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Report saved: {report_path}")

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="vinhlong360 Evaluation Runner")
    parser.add_argument("--quick", action="store_true", help="Quick 10-case eval")
    parser.add_argument("--category", type=str, help="Run only this category")
    args = parser.parse_args()

    if args.quick:
        run_quick_eval()
    else:
        run_full_eval(category_filter=args.category)
