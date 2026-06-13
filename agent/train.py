"""
vinhlong360 — Agent Training Harness.

IMPORTANT: This does NOT fine-tune the LLM's weights (the model is an external
OpenAI-compatible API). It "trains" the agent's NON-PARAMETRIC learning loops by
feeding it interactions + feedback, then triggering the (eval-gated) learning
machinery and measuring whether quality improved.

A training session:

  1. BASELINE   — measure offline fitness (retrieval recall + KB health).
  2. INTERACT   — for each training example: ask /chat, score the answer by how
                  well it covers the expected facts, then send /feedback (👍/👎).
                  The server auto-records into: experience memory, few-shot demo
                  pool, self-optimizer performance, analytics.
  3. CONSOLIDATE— trigger server-side learning: compile few-shot demos, run the
                  eval-gated learn cycle (gaps→web→KB, with auto-rollback).
  4. MEASURE    — re-measure fitness + report the delta and what was learned.

Usage:
  python agent/train.py                              # default trainset, 1 epoch
  python agent/train.py --data path/to/set.json --epochs 3
  python agent/train.py --threshold 6                # 👍 if score >= 6/10
  python agent/train.py --eval-only                  # just measure, no training
  python agent/train.py --no-learn                   # interact+feedback, skip consolidate

Requires the server running (default http://localhost:8360) and ADMIN_API_KEY in
.env for the learn trigger.
"""

import argparse
import json
import os
import re
import sys
import time
import unicodedata
from pathlib import Path

AGENT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(AGENT_DIR))

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import requests
from dotenv import load_dotenv

load_dotenv(AGENT_DIR.parent / ".env")

SERVER = os.environ.get("EVAL_SERVER", "http://localhost:8360")
ADMIN_KEY = os.environ.get("ADMIN_API_KEY", "")
DEFAULT_DATA = AGENT_DIR / "data" / "train" / "trainset.json"


def _norm(text: str) -> str:
    s = unicodedata.normalize("NFD", (text or "").lower())
    s = re.sub(r"[̀-ͯ]", "", s)
    return s.replace("đ", "d")


def score_answer(reply: str, expect: list, tools: list) -> float:
    """Score 0-10: expected-fact coverage (0-7) + answered/used-tools (0-3)."""
    if not reply or len(reply) < 40:
        return 0.0
    rn = _norm(reply)
    hits = sum(1 for e in expect if _norm(e) in rn)
    coverage = (hits / len(expect)) if expect else 1.0
    score = 7.0 * coverage
    # Quality signal: substantive answer + grounded by tools
    if len(reply) > 200:
        score += 1.5
    if tools:
        score += 1.5
    # Penalize "không có thông tin / chưa kiểm chứng" when facts were expected
    if expect and ("khong co thong tin" in rn or "chua tim thay" in rn):
        score *= 0.4
    return round(min(score, 10.0), 1)


def call_chat(query: str, session_id: str) -> tuple[str, list]:
    try:
        r = requests.post(f"{SERVER}/chat",
                          json={"message": query, "session_id": session_id}, timeout=180)
        if r.status_code == 200:
            d = r.json()
            tools = []
            for t in d.get("tool_calls", []):
                tools.append(t.get("name", "") if isinstance(t, dict) else str(t))
            return d.get("reply", ""), tools
    except Exception as e:
        print(f"  [chat error] {e}")
    return "", []


def send_feedback(query: str, rating: int, session_id: str):
    try:
        requests.post(f"{SERVER}/feedback",
                     json={"query": query, "rating": rating, "session_id": session_id},
                     timeout=15)
    except Exception:
        pass


def measure_fitness() -> dict:
    """Offline fitness (no LLM) — recall + KB health."""
    try:
        import self_eval
        return self_eval.compute_fitness()
    except Exception as e:
        return {"error": str(e)}


def consolidate():
    """Trigger server-side learning: compile few-shot + eval-gated learn cycle."""
    results = {}
    # Few-shot compile (in-process, no server needed)
    try:
        import prompt_compiler
        results["fewshot"] = prompt_compiler.compile()
    except Exception as e:
        results["fewshot"] = {"error": str(e)}
    # Eval-gated learn cycle (admin endpoint)
    if ADMIN_KEY:
        try:
            r = requests.post(f"{SERVER}/system/learning/run",
                             headers={"X-Admin-Key": ADMIN_KEY}, timeout=300)
            results["learn_cycle"] = r.json() if r.status_code == 200 else {"status": r.status_code}
        except Exception as e:
            results["learn_cycle"] = {"error": str(e)}
    else:
        results["learn_cycle"] = {"skipped": "no ADMIN_API_KEY"}
    return results


def run_training(data_path: Path, epochs: int, threshold: float,
                 do_learn: bool, eval_only: bool):
    payload = json.loads(data_path.read_text(encoding="utf-8"))
    examples = payload.get("examples", payload) if isinstance(payload, dict) else payload

    print("=" * 64)
    print(f"  vinhlong360 — Training session")
    print(f"  Examples: {len(examples)} | Epochs: {epochs} | 👍 threshold: {threshold}/10")
    print("=" * 64)

    print("\n[1/4] Baseline fitness…")
    before = measure_fitness()
    print(f"      composite={before.get('composite')} recall@5={before.get('recall_at_5')} "
          f"summary_cov={before.get('summary_coverage')}")

    if eval_only:
        print("\n(eval-only) done.")
        return

    print("\n[2/4] Interaction + feedback…")
    all_scores = []
    pos = neg = 0
    for epoch in range(epochs):
        for i, ex in enumerate(examples):
            q = ex["query"]
            sid = f"train-e{epoch}-{i}-{int(time.time())}"
            reply, tools = call_chat(q, sid)
            s = score_answer(reply, ex.get("expect", []), tools)
            all_scores.append(s)
            rating = 1 if s >= threshold else 0
            pos += rating
            neg += (1 - rating)
            send_feedback(q, rating, sid)
            mark = "👍" if rating else "👎"
            print(f"   e{epoch} #{i:02d} [{s:>4}/10] {mark} {q[:50]}")

    avg = round(sum(all_scores) / len(all_scores), 2) if all_scores else 0
    print(f"\n      avg score: {avg}/10 | 👍 {pos} | 👎 {neg}")

    if do_learn:
        print("\n[3/4] Consolidate (compile few-shot + eval-gated learn cycle)…")
        res = consolidate()
        print(f"      few-shot: {res.get('fewshot')}")
        lc = res.get("learn_cycle", {})
        print(f"      learn cycle: decision={lc.get('decision', lc)}")
    else:
        print("\n[3/4] (--no-learn) skipped consolidation")

    print("\n[4/4] Post-training fitness…")
    after = measure_fitness()
    print(f"      composite={after.get('composite')} recall@5={after.get('recall_at_5')} "
          f"summary_cov={after.get('summary_coverage')}")

    dc = (after.get("composite", 0) or 0) - (before.get("composite", 0) or 0)
    print("\n" + "=" * 64)
    print(f"  RESULT: avg_answer_score={avg}/10 | fitness Δ composite={dc:+.4f}")
    print(f"  Learned signal saved to: experience_memory, demo pool, optimizer, analytics")
    print(f"  Next: run more epochs, expand trainset, or check /system/self-evolution")
    print("=" * 64)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="vinhlong360 agent training harness")
    ap.add_argument("--data", type=str, default=str(DEFAULT_DATA))
    ap.add_argument("--epochs", type=int, default=1)
    ap.add_argument("--threshold", type=float, default=6.0)
    ap.add_argument("--no-learn", action="store_true", help="skip consolidation step")
    ap.add_argument("--eval-only", action="store_true", help="only measure fitness")
    args = ap.parse_args()

    run_training(Path(args.data), args.epochs, args.threshold,
                 do_learn=not args.no_learn, eval_only=args.eval_only)
