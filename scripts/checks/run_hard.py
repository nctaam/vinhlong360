# -*- coding: utf-8 -*-
"""run_hard — cổng chặn commit/merge (SP1).

- Chạy: hard (count>0 = chặn) + RATCHET cho mọi *-ratchet (tăng so baseline = chặn).
- `--staged` (hook, <5s) | `--all` (pre_merge).
- SKIP_CHECKS: CHỈ rule soft-ratchet, bắt buộc SKIP_REASON, tự append
  docs/standards/90-exceptions-log.md (COMMITTED). hard/hard-ratchet KHÔNG skip được.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):  # hook console Windows = cp1252
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from checks import common  # noqa: E402
from checks.check_api_contract import CHECKS as api_checks  # noqa: E402
from checks.check_banned_claims import CHECKS as banned  # noqa: E402
from checks.check_complexity import CHECKS as complexity  # noqa: E402
from checks.check_content_gates import CHECKS as content_gates  # noqa: E402
from checks.check_content_voice import CHECKS as voice  # noqa: E402
from checks.check_data_schema import CHECKS as schema  # noqa: E402
from checks.check_doc_status import CHECKS as doc_status  # noqa: E402
from checks.check_fe_tokens import CHECKS as fe_tokens  # noqa: E402
from checks.check_links import CHECKS as links  # noqa: E402
from checks.check_ruff import CHECKS as ruff_lint  # noqa: E402
from checks.check_secrets import CHECKS as secrets  # noqa: E402
from checks.check_test_pairing import CHECKS as pairing  # noqa: E402
from checks.check_thin_content import CHECKS as thin  # noqa: E402
from checks.check_tinh_cu import CHECKS as tinh_cu  # noqa: E402

ALL_CHECKS = (secrets + banned + schema + api_checks
              + tinh_cu + fe_tokens + doc_status + links
              + voice + content_gates + thin + pairing + complexity + ruff_lint)
REGISTRY = {c.name: c for c in ALL_CHECKS}


def _parse_skips(root: Path) -> set[str]:
    raw = os.environ.get("SKIP_CHECKS", "").strip()
    if not raw:
        return set()
    reason = os.environ.get("SKIP_REASON", "").strip()
    if not reason:
        print("SKIP_CHECKS cần SKIP_REASON — từ chối skip.", file=sys.stderr)
        return set()
    rules = {r.strip() for r in raw.split(",") if r.strip()}
    levels = {c.rule: c.level for c in ALL_CHECKS}
    ok = set()
    for r in rules:
        if levels.get(r) == "soft-ratchet" or levels.get(r) == "soft":
            ok.add(r)
        else:
            print(f"TỪ CHỐI skip {r}: tầng {levels.get(r, '?')} — chỉ soft được skip.", file=sys.stderr)
    if ok:
        log = root / "docs" / "standards" / "90-exceptions-log.md"
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("a", encoding="utf-8") as f:
            f.write(f"\n- {datetime.now().isoformat(timespec='seconds')} SKIP {','.join(sorted(ok))} — {reason}\n")
        print(f"SKIP (soft) {sorted(ok)} — đã ghi 90-exceptions-log.md (nhớ commit).")
    return ok


def run(files: list[str] | None, checks: list | None = None, root: Path | None = None,
        baseline: dict | None = None, skips: set[str] | None = None) -> tuple[int, list[str]]:
    """Trả (exit_code, messages). Tách tham số để test được."""
    checks = checks if checks is not None else ALL_CHECKS
    root = root or common.repo_root()
    baseline = baseline if baseline is not None else common.load_baseline(root=root)
    skips = skips if skips is not None else set()
    results = [c.run(files) for c in checks]
    messages: list[str] = []
    blocked = False
    for r in results:
        if r["level"] == "hard" and r["count"] > 0:
            blocked = True
            messages.append(f'✖ HARD {r["rule"]} ({r["check"]}): {r["count"]} vi phạm')
            for v in r["violations"][:5]:
                messages.append(f'    {v["file"]}:{v["line"]} — {v["msg"]}')
    blockers, suggestions = common.ratchet_violations(results, baseline)
    lvl = {c.rule: c.level for c in checks}
    for b in blockers:
        rule = b.split(" ")[0]
        if rule in skips and lvl.get(rule, "").startswith("soft"):
            messages.append(f"⚠ SKIPPED (soft) {b}")
            continue
        blocked = True
        messages.append(f"✖ RATCHET {b}")
    if files is None:  # suggestions chỉ có nghĩa khi đếm TOÀN repo (--all)
        for s in suggestions:
            messages.append(f"↓ {s}")
    if not blocked:
        messages.append("✓ run_hard: sạch (hard=0, ratchet không tăng)")
    return (1 if blocked else 0), messages


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--staged", action="store_true")
    g.add_argument("--all", action="store_true")
    a = ap.parse_args()
    root = common.repo_root()
    files = common.staged_files() if a.staged else None
    if a.staged and not files:
        print("✓ run_hard: không có file staged.")
        return 0
    skips = _parse_skips(root)
    code, messages = run(files, root=root, skips=skips)
    print("\n".join(messages))
    if code:
        print("\nCommit bị CHẶN theo tiêu chuẩn (docs/standards/). Sửa vi phạm — đừng tăng nợ.", file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
