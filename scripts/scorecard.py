#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scorecard — đồng hồ world-class (SP1).

Điểm/chiều = 100 × (1 − nợ_hiện / nợ_gốc), floor 0; chiều không nợ gốc và nợ hiện = 0 → 100.
nợ_gốc đóng băng PER-RULE: nợ tại entry ĐẦU TIÊN rule đó xuất hiện trong
docs/standards/scorecard-history.jsonl (mốc ban hành của từng rule — SP2: gate
mới bật với nợ tồn đọng thì MỞ RỘNG mẫu số thay vì đánh sập điểm về 0, để tiến
bộ đã trả không bị che). Điểm là TIẾN ĐỘ TRẢ NỢ, không phải lời tự khen.
Đích chương trình ≥95/chiều (spec §0.5); sàn world-class = 90.

Exit ≠ 0 khi: (a) có hard-violation, hoặc (b) bất kỳ chiều nào TỤT so entry trước.
Mỗi lần chạy (không --no-append) tự ghi history — kết đợt dán bảng vào plan-result.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from checks import common  # noqa: E402

DIMENSIONS = {"10": "data", "20": "backend", "30": "frontend", "40": "ui-design",
              "50": "content", "60": "docs", "70": "ops"}
HISTORY_REL = "docs/standards/scorecard-history.jsonl"


def collect_debts(checks: list, files=None) -> tuple[dict, int]:
    debts: dict[str, int] = {}
    hard = 0
    for c in checks:
        r = c.run(files)
        debts[r["rule"]] = debts.get(r["rule"], 0) + r["count"]
        if r["level"] == "hard":
            hard += r["count"]
    return debts, hard


def _dim_of(rule: str) -> str | None:
    for prefix, name in DIMENSIONS.items():
        if rule.startswith(f"R{prefix}."):
            return name
    return None


def dim_debts(debts: dict) -> dict:
    out = {name: 0 for name in DIMENSIONS.values()}
    seen = {name: False for name in DIMENSIONS.values()}
    for rule, n in debts.items():
        d = _dim_of(rule)
        if d:
            out[d] += n
            seen[d] = True
    return {d: (out[d] if seen[d] else None) for d in out}  # None = chưa đo


def scores(current: dict, origin: dict) -> dict:
    result = {}
    for d, debt in current.items():
        if debt is None:
            result[d] = None  # chưa đo
            continue
        base = origin.get(d) or 0
        if base <= 0:
            result[d] = 100 if debt == 0 else 0
        else:
            result[d] = max(0, round(100 * (1 - debt / base)))
    return result


def load_history(root: Path) -> list[dict]:
    p = root / HISTORY_REL
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]


def origin_rule_debts(history: list[dict], current: dict) -> dict:
    """Nợ gốc per-rule = entry đầu tiên rule xuất hiện; rule mới toanh = nợ hiện tại."""
    seen: dict[str, int] = {}
    for h in history:
        for rule, n in (h.get("debts") or {}).items():
            seen.setdefault(rule, n)
    for rule, n in current.items():
        seen.setdefault(rule, n)
    return seen


def run(checks: list, root: Path, append: bool = True) -> tuple[int, dict]:
    debts, hard = collect_debts(checks)
    cur = dim_debts(debts)
    history = load_history(root)
    origin = dim_debts(origin_rule_debts(history, debts))
    sc = scores(cur, {d: (v or 0) for d, v in origin.items()})
    prev = history[-1]["scores"] if history else None
    regressions = []
    if prev:
        for d, s in sc.items():
            ps = prev.get(d)
            if s is not None and ps is not None and s < ps:
                regressions.append(f"{d}: {ps} → {s}")
    entry = {"ts": datetime.now().isoformat(timespec="seconds"), "scores": sc,
             "dim_debts": cur, "debts": debts, "hard_violations": hard}
    if append:
        p = root / HISTORY_REL
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    code = 1 if (hard > 0 or regressions) else 0
    return code, {"entry": entry, "regressions": regressions}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-append", action="store_true")
    a = ap.parse_args()
    from checks.run_hard import ALL_CHECKS

    root = common.repo_root()
    code, out = run(ALL_CHECKS, root, append=not a.no_append)
    e = out["entry"]
    if a.json:
        print(json.dumps(out, ensure_ascii=False, indent=1))
    else:
        print(f'SCORECARD {e["ts"]}  (đích ≥95, sàn world-class 90)')
        for d, s in e["scores"].items():
            debt = e["dim_debts"][d]
            label = "chưa đo" if s is None else f'{s:>3}/100 (nợ {debt})'
            print(f'  {d:<10} {label}')
        print(f'  hard-violations: {e["hard_violations"]}')
        for r in out["regressions"]:
            print(f"  ✖ TỤT ĐIỂM: {r}")
    return code


if __name__ == "__main__":
    sys.exit(main())
