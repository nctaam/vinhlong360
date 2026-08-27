# -*- coding: utf-8 -*-
"""run_hard — cổng chặn commit/merge (SP1).

- Chạy: hard (count>0 = chặn) + RATCHET cho mọi *-ratchet (tăng so baseline = chặn).
- `--staged` (hook, <5s) | `--all` (pre_merge).
- SKIP_CHECKS: CHỈ rule soft-ratchet, bắt buộc SKIP_REASON, tự append
  docs/standards/90-exceptions-log.md (COMMITTED). hard/hard-ratchet KHÔNG skip được.
"""
from __future__ import annotations

import argparse
from copy import copy
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
from checks.check_axe import CHECKS as axe  # noqa: E402
from checks.check_banned_claims import CHECKS as banned  # noqa: E402
from checks.check_bundle import CHECKS as bundle  # noqa: E402
from checks.check_complexity import CHECKS as complexity  # noqa: E402
from checks.check_content_gates import CHECKS as content_gates  # noqa: E402
from checks.check_content_voice import CHECKS as voice  # noqa: E402
from checks.check_coverage import CHECKS as coverage  # noqa: E402
from checks.check_data_schema import CHECKS as schema  # noqa: E402
from checks.check_doc_status import CHECKS as doc_status  # noqa: E402
from checks.check_entity_image_renderers import CHECKS as entity_image_renderers  # noqa: E402
from checks.check_fe_tokens import CHECKS as fe_tokens  # noqa: E402
from checks.check_links import CHECKS as links  # noqa: E402
from checks.check_policy_http_registry import CHECKS as policy_http_registry  # noqa: E402
from checks.check_ruff import CHECKS as ruff_lint  # noqa: E402
from checks.check_secrets import CHECKS as secrets  # noqa: E402
from checks.check_test_pairing import CHECKS as pairing  # noqa: E402
from checks.check_thin_content import CHECKS as thin  # noqa: E402
from checks.check_tinh_cu import CHECKS as tinh_cu  # noqa: E402

ALL_CHECKS = (secrets + banned + schema + api_checks
              + tinh_cu + fe_tokens + doc_status + links
              + voice + content_gates + thin + pairing + complexity + ruff_lint + coverage
              + bundle + axe + policy_http_registry + entity_image_renderers)
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


def _hard_messages(results: list) -> tuple[bool, list[str]]:
    """Khối phát hiện hard-block (count>0). Trả (blocked, messages) — logic verbatim."""
    blocked = False
    messages: list[str] = []
    for r in results:
        if r["level"] == "hard" and r["count"] > 0:
            blocked = True
            messages.append(f'✖ HARD {r["rule"]} ({r["check"]}): {r["count"]} vi phạm')
            for v in r["violations"][:5]:
                messages.append(f'    {v["file"]}:{v["line"]} — {v["msg"]}')
    return blocked, messages


def _ratchet_messages(blockers: list, skips: set[str], lvl: dict) -> tuple[bool, list[str]]:
    """Khối xử lý ratchet-blockers + skip-soft. Trả (blocked, messages) — logic verbatim."""
    blocked = False
    messages: list[str] = []
    for b in blockers:
        rule = b.split(" ")[0]
        if rule in skips and lvl.get(rule, "").startswith("soft"):
            messages.append(f"⚠ SKIPPED (soft) {b}")
            continue
        blocked = True
        messages.append(f"✖ RATCHET {b}")
    return blocked, messages


def _bind_checks_to_root(checks: list, root: Path) -> list:
    bound = [copy(check) if hasattr(check, "_root") else check for check in checks]
    for check in bound:
        if hasattr(check, "_root"):
            check._root = root
    return bound


def _head_counts(files: list[str], checks: list, root: Path) -> dict:
    """Đếm vi phạm của CHÍNH những file đang staged, nhưng ở bản HEAD.

    Dựng lại nội dung HEAD vào một thư mục tạm rồi chạy đúng bộ check trên đó.
    File MỚI (chưa có ở HEAD) → `git show` lỗi → bỏ qua, tức HEAD coi như 0 vi
    phạm cho file ấy; thêm file mới mang theo nợ VẪN bị tính là tăng.
    """
    import shutil
    import subprocess
    import tempfile

    out: dict = {}
    td = tempfile.mkdtemp(prefix="vl360-gate-")
    try:
        tmp = Path(td)
        kept = []
        for rel in files:
            r = subprocess.run(["git", "show", f"HEAD:{rel}"], cwd=str(root),
                               capture_output=True)
            if r.returncode != 0:
                continue
            dst = tmp / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(r.stdout)
            kept.append(rel)
        if not kept:
            # KHÔNG thoát sớm. Không file nào tồn tại ở HEAD nghĩa là TẤT CẢ đều
            # mới, tức HEAD có 0 vi phạm — và commit toàn-file-mới mang nợ vẫn
            # phải bị chặn. Trả về rỗng ở đây là mở đúng cái lỗ vừa bịt: sáng
            # 2026-08-27 `agent/ocop.py` (file MỚI, complexity 21) lọt qua hook
            # chính vì con đường này.
            return {c.rule: 0 for c in checks}
        for c in _bind_checks_to_root(checks, tmp):
            out[c.rule] = out.get(c.rule, 0) + c.run(kept)["count"]
    finally:
        shutil.rmtree(td, ignore_errors=True)
    return out


def _per_file_ratchet(files: list[str], checks: list, root: Path, baseline: dict,
                      results: list[dict], skips: set, lvl: dict) -> tuple[bool, list[str]]:
    """RATCHET THEO-FILE — bịt lỗ §44.

    Ở chế độ `--staged`, `count` của mỗi check chỉ đếm trong FILE ĐANG STAGED,
    nhưng `ratchet_violations` lại so nó với baseline TOÀN KHO. Với rule có
    baseline > 0 (R20.8=47, R30.2=330, R30.3=147, R30.8=369) tập con gần như
    luôn nhỏ hơn tổng, nên phép so ấy KHÔNG BAO GIỜ đỏ được — hook chỉ thực sự
    canh được những rule có baseline = 0.

    Đo được hậu quả: 2026-08-27 tôi thêm một hàm complexity 21 và commit qua hook
    trót lọt; chỉ `--all` mới bắt (R20.8 48 > 47).

    Cách bịt: so CÙNG NHỮNG FILE ẤY với chính chúng ở bản HEAD. Phép so này đúng
    bất kể baseline bao nhiêu, và vẫn nhanh vì chỉ đụng vài file.

    KHÔNG áp cho rule baseline = 0 (phép so cũ đã đủ và chính xác) lẫn cho các
    rule quét-toàn-bộ như R50.* — chúng khoá theo `web/data.json` nên khi file đó
    được staged thì `count` đã là số toàn kho, so với baseline toàn kho là đúng.
    """
    now = {r["rule"]: r["count"] for r in results}
    watched = [c for c in checks
               if getattr(c, "level", "").endswith("-ratchet")
               and baseline.get(getattr(c, "rule", ""), 0) > 0]
    if not watched:
        return False, []
    head = _head_counts(files, watched, root)
    blocked, msgs = False, []
    for c in watched:
        n_now, n_head = now.get(c.rule, 0), head.get(c.rule, 0)
        if n_now <= n_head:
            continue
        msg = (f'{c.rule} ({c.name}): {n_now} vi phạm trong file đang sửa, '
               f'bản HEAD của chính những file đó có {n_head} '
               f'— RATCHET theo-file: đừng thêm nợ vào file mình đang sửa.')
        if c.rule in skips and lvl.get(c.rule, "").startswith("soft"):
            msgs.append(f"⚠ SKIPPED (soft) {msg}")
            continue
        blocked = True
        msgs.append(f"✖ RATCHET {msg}")
    return blocked, msgs


def _ratchet_phase(files, checks: list, root: Path, baseline: dict,
                   results: list[dict], skips: set) -> tuple[bool, list[str], list[str]]:
    """Gộp HAI phép so ratchet: theo TOÀN KHO và theo TỪNG FILE.

    Tách khỏi `run()` vì gộp thẳng vào đó đẩy nó lên complexity 14 — và chính
    cổng vừa vá đã chặn commit này. Bắt đúng thứ nó sinh ra để bắt.
    """
    lvl = {c.rule: c.level for c in checks}
    blockers, suggestions = common.ratchet_violations(results, baseline)
    blocked, msgs = _ratchet_messages(blockers, skips, lvl)
    if files:   # §44 — xem _per_file_ratchet
        d_blocked, d_msgs = _per_file_ratchet(files, checks, root, baseline,
                                              results, skips, lvl)
        msgs.extend(d_msgs)
        blocked = blocked or d_blocked
    return blocked, msgs, suggestions


def run(files: list[str] | None, checks: list | None = None, root: Path | None = None,
        baseline: dict | None = None, skips: set[str] | None = None) -> tuple[int, list[str]]:
    """Trả (exit_code, messages). Tách tham số để test được."""
    checks = checks if checks is not None else ALL_CHECKS
    root = root or common.repo_root()
    baseline = baseline if baseline is not None else common.load_baseline(root=root)
    skips = skips if skips is not None else set()
    checks = _bind_checks_to_root(checks, root)
    results = [c.run(files) for c in checks]
    messages: list[str] = []
    hard_blocked, hard_msgs = _hard_messages(results)
    messages.extend(hard_msgs)
    blocked = hard_blocked
    r_blocked, r_msgs, suggestions = _ratchet_phase(files, checks, root, baseline,
                                                    results, skips)
    messages.extend(r_msgs)
    blocked = blocked or r_blocked
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
