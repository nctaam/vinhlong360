#!/usr/bin/env python3
"""pre_merge_check.py — Chạy TRƯỚC khi merge session branches vào main.

Kiểm tra 5 vấn đề phổ biến từ parallel sessions:
1. CLAUDE.md bị session ghi đè (không còn là file gốc)
2. File overlap giữa các branches (dự đoán conflict)
3. Config mới yêu cầu env vars mà prod chưa có
4. Scope creep — session sửa file ngoài phạm vi
5. Import/dependency mới chưa khai báo

Usage:
    python scripts/pre_merge_check.py session-fe session-be session-content
    python scripts/pre_merge_check.py session-fe  # check 1 branch
"""

import subprocess
import sys
import os
import json
import re
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_BRANCH = "main"
VPS_HOST = "root@66.42.57.202"
VPS_KEY = str(Path.home() / ".ssh" / "vinhlong_vps")
REMOTE_DIR = "/opt/vinhlong360"

SCOPE_RULES = {
    "fe": {
        "allowed_dirs": ["web-nuxt/"],
        "forbidden_dirs": ["agent/", "scripts/", "web/data.json"],
        "label": "Frontend",
    },
    "be": {
        "allowed_dirs": ["agent/", "requirements.txt"],
        "forbidden_dirs": ["web-nuxt/", "scripts/", "web/data.json"],
        "label": "Backend",
    },
    "content": {
        "allowed_dirs": ["scripts/", "web/", "docs/", "tests/", "web-nuxt/public/data/"],
        "forbidden_dirs": ["agent/", "web-nuxt/components/", "web-nuxt/pages/", "web-nuxt/composables/"],
        "label": "Content",
    },
}

SHARED_FILES = {"CLAUDE.md", ".env.example", "docker-compose.yml", ".gitignore"}


def run(cmd, check=True):
    r = subprocess.run(cmd, capture_output=True, text=True, shell=True, encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        return ""
    return (r.stdout or "").strip()


def detect_session_type(branch_name):
    lower = branch_name.lower()
    for key in SCOPE_RULES:
        if key in lower:
            return key
    return None


def get_changed_files(branch):
    base = run(f"git merge-base {BASE_BRANCH} {branch}")
    if not base:
        base = BASE_BRANCH
    out = run(f"git diff --name-only {base}..{branch}")
    return set(out.splitlines()) if out.strip() else set()


def check_claude_md(branches):
    """1. Kiểm tra CLAUDE.md có bị ghi đè thành scoped version."""
    issues = []
    for branch in branches:
        diff = run(f'git diff {BASE_BRANCH}..{branch} -- CLAUDE.md')
        if diff and "SESSION SCOPE" in diff:
            issues.append(f"  [{branch}] CLAUDE.md bị thay bằng scoped version — cần restore sau merge")
    return issues


def check_file_overlap(branches):
    """2. Kiểm tra file overlap giữa các branches."""
    issues = []
    files_by_branch = {}
    for branch in branches:
        files_by_branch[branch] = get_changed_files(branch) - SHARED_FILES

    for i, b1 in enumerate(branches):
        for b2 in branches[i+1:]:
            overlap = files_by_branch[b1] & files_by_branch[b2]
            overlap = {f for f in overlap if not f.startswith("docs/")}
            if overlap:
                issues.append(f"  [{b1}] vs [{b2}] — {len(overlap)} files overlap:")
                for f in sorted(overlap)[:10]:
                    issues.append(f"    - {f}")
                if len(overlap) > 10:
                    issues.append(f"    ... và {len(overlap)-10} files nữa")
    return issues


def check_config_env(branches):
    """3. Kiểm tra config mới yêu cầu env vars mà prod có thể chưa có."""
    issues = []

    prod_vars = set()
    out = run(
        f'ssh -i {VPS_KEY} -o ConnectTimeout=10 {VPS_HOST} '
        f'"grep -E \'^[A-Z]\' {REMOTE_DIR}/.env | cut -d= -f1"'
    )
    if out:
        prod_vars = set(out.splitlines())
    else:
        issues.append("  [WARN] Không kết nối được VPS — bỏ qua check env vars prod")
        return issues

    for branch in branches:
        diff = run(f'git diff {BASE_BRANCH}..{branch} -- agent/config.py')
        if not diff:
            continue

        new_fields = re.findall(r'^\+\s+(\w+):\s+(?:str|int|float|bool)', diff, re.MULTILINE)
        for field in new_fields:
            if field not in prod_vars and field.isupper():
                issues.append(f"  [{branch}] config.py thêm '{field}' — KHÔNG có trên VPS .env")

        if "missing.append" in diff:
            required = re.findall(r'^\+.*missing\.append\("(\w+)"\)', diff, re.MULTILINE)
            for var in required:
                if var not in prod_vars:
                    issues.append(f"  [{branch}] config.py REQUIRED '{var}' trên prod — VPS CHƯA CÓ → sẽ crash!")

    return issues


def check_scope(branches):
    """4. Kiểm tra session có sửa file ngoài phạm vi."""
    issues = []
    for branch in branches:
        stype = detect_session_type(branch)
        if not stype:
            issues.append(f"  [{branch}] Không nhận diện được session type (fe/be/content)")
            continue

        rules = SCOPE_RULES[stype]
        files = get_changed_files(branch) - SHARED_FILES

        violations = []
        for f in files:
            in_allowed = any(f.startswith(d) or f == d for d in rules["allowed_dirs"])
            in_forbidden = any(f.startswith(d) for d in rules["forbidden_dirs"])

            if in_forbidden:
                violations.append(f)

        if violations:
            issues.append(f"  [{branch}] {rules['label']} session sửa {len(violations)} file NGOÀI phạm vi:")
            for v in sorted(violations)[:10]:
                issues.append(f"    - {v}")
    return issues


def check_new_deps(branches):
    """5. Kiểm tra dependency mới."""
    issues = []
    for branch in branches:
        pkg_diff = run(f'git diff {BASE_BRANCH}..{branch} -- web-nuxt/package.json')
        if pkg_diff:
            added = re.findall(r'^\+\s+"([\w@/-]+)":\s+"', pkg_diff, re.MULTILINE)
            added = [a for a in added if a not in ("name", "version", "private")]
            if added:
                issues.append(f"  [{branch}] Thêm npm packages: {', '.join(added)}")

        req_diff = run(f'git diff {BASE_BRANCH}..{branch} -- requirements.txt')
        if req_diff:
            added_pip = re.findall(r'^\+([\w-]+)', req_diff, re.MULTILINE)
            added_pip = [a for a in added_pip if not a.startswith(('#', '+'))]
            if added_pip:
                issues.append(f"  [{branch}] Thêm pip packages: {', '.join(added_pip)}")
    return issues


# ---------- SP1 (2026-07-07): 3 bước tiêu-chuẩn — run_hard, scorecard, plan-result ----------

def _run_code(cmd: list, runner=None) -> tuple[int, str]:
    """subprocess có returncode (helper run() cũ nuốt mất code)."""
    fn = runner or (lambda c: subprocess.run(c, capture_output=True, text=True, encoding="utf-8", errors="replace"))
    r = fn(cmd)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def check_standards_hard(branches, runner=None):
    """6. run_hard --all: hard = 0 và ratchet không tăng (docs/standards/)."""
    code, out = _run_code([sys.executable, "scripts/checks/run_hard.py", "--all"], runner)
    if code != 0:
        tail = "\n".join(f"    {ln}" for ln in out.strip().splitlines()[-12:])
        return [f"  [standards] run_hard --all FAIL — vi phạm tiêu chuẩn sẽ crash chất lượng, REQUIRED sửa trước merge:\n{tail}"]
    return []


def check_scorecard(branches, runner=None):
    """7. scorecard --no-append: không hard-violation, không chiều nào TỤT điểm."""
    code, out = _run_code([sys.executable, "scripts/scorecard.py", "--no-append"], runner)
    if code != 0:
        tail = "\n".join(f"    {ln}" for ln in out.strip().splitlines()[-10:])
        return [f"  [standards] scorecard FAIL (tụt điểm hoặc hard) — REQUIRED:\n{tail}"]
    return []


def check_plan_result(branches):
    """8. Nhánh có plan trong docs/superpowers/plans/ → plan phải có mục KẾT QUẢ trước merge (R60.5)."""
    issues = []
    for branch in branches:
        files = get_changed_files(branch)
        plans = [f for f in files if f.startswith("docs/superpowers/plans/") and f.endswith(".md")]
        for rel in plans:
            content = run(f"git show {branch}:{rel}", check=False)
            if content and "KẾT QUẢ" not in content:
                issues.append(f"  [{branch}] {rel} chưa có mục 'KẾT QUẢ' (plan-result bắt buộc khi kết đợt — R60.5)")
    return issues


def main():
    branches = sys.argv[1:] or []
    if not branches:
        out = run("git branch --list 'session-*'")
        if out:
            branches = [b.strip().lstrip("* ") for b in out.splitlines()]

    if not branches:
        print("Usage: python scripts/pre_merge_check.py <branch1> [branch2] ...")
        sys.exit(1)

    print(f"Pre-merge check: {', '.join(branches)} -> {BASE_BRANCH}")
    print(f"{'='*60}")

    checks = [
        ("1. CLAUDE.md bị ghi đè?", check_claude_md),
        ("2. File overlap giữa branches?", check_file_overlap),
        ("3. Config env vars mới vs prod?", check_config_env),
        ("4. Scope violations?", check_scope),
        ("5. Dependency mới?", check_new_deps),
        ("6. Tiêu chuẩn run_hard --all?", check_standards_hard),
        ("7. Scorecard không tụt điểm?", check_scorecard),
        ("8. Plan-result đã ghi?", check_plan_result),
    ]

    total_issues = 0
    critical = 0

    for title, check_fn in checks:
        print(f"\n{title}")
        issues = check_fn(branches)
        if issues:
            for line in issues:
                marker = "CRITICAL" if "crash" in line.lower() or "REQUIRED" in line else ""
                if marker:
                    critical += 1
                print(f"  {'!!!' if marker else '   '} {line.strip()}")
            total_issues += len([i for i in issues if i.strip().startswith("[")])
        else:
            print("  OK")

    print(f"\n{'='*60}")
    if critical:
        print(f"CRITICAL: {critical} vấn đề sẽ gây crash prod — PHẢI sửa trước merge!")
        sys.exit(1)
    elif total_issues:
        print(f"WARNING: {total_issues} vấn đề — review trước merge")
        sys.exit(0)
    else:
        print("ALL CLEAR — sẵn sàng merge")
        sys.exit(0)


if __name__ == "__main__":
    main()
