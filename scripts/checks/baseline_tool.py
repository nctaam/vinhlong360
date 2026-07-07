# -*- coding: utf-8 -*-
"""baseline_tool — chụp/ghi nhận nợ chuẩn hiện tồn (RATCHET gốc).

Dùng:
  python scripts/checks/baseline_tool.py            # xem bảng count/rule
  python scripts/checks/baseline_tool.py --write    # ghi docs/standards/baseline.json

QUY TẮC (spec §0): baseline chỉ được cập nhật trong cùng commit với thay đổi
diện-rộng có giải trình, hoặc khi ghi nhận TIẾN BỘ (count giảm). KHÔNG baseline-hoá
vi phạm tầng hard — hard phải = 0 trước khi ban hành.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from checks import common  # noqa: E402


def collect(checks: list) -> dict:
    """Chạy mọi check --all → {rule: count} (đủ mọi rule, kể cả 0)."""
    counts: dict[str, int] = {}
    for chk in checks:
        r = chk.run(None) if not callable(chk) else chk(None)
        counts[r["rule"]] = counts.get(r["rule"], 0) + r["count"]
    return counts


def run(checks: list, root: Path | None = None, write: bool = False) -> dict:
    counts = collect(checks)
    hard_rules = {getattr(c, "rule", None): getattr(c, "level", "") for c in checks if not callable(c)}
    width = max((len(r) for r in counts), default=6)
    print(f'{"RULE".ljust(width)}  COUNT')
    for rule in sorted(counts):
        flag = "  <-- HARD phải = 0" if hard_rules.get(rule) == "hard" and counts[rule] > 0 else ""
        print(f"{rule.ljust(width)}  {counts[rule]}{flag}")
    if write:
        common.save_baseline(counts, root=root)
        print("WROTE docs/standards/baseline.json")
    return counts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    from checks.run_hard import REGISTRY  # registry đầy đủ (T6)

    run(list(REGISTRY.values()), write=a.write)
    return 0


if __name__ == "__main__":
    sys.exit(main())
