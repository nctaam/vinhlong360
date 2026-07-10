# -*- coding: utf-8 -*-
"""Test 4 module HARD-RATCHET (SP01 T4)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from checks.check_doc_status import DocStatusCheck  # noqa: E402
from checks.check_fe_tokens import build_checks as fe_checks  # noqa: E402
from checks.check_links import LinksCheck  # noqa: E402
from checks.check_tinh_cu import TinhCuCheck  # noqa: E402


def _mk(tmp_path: Path, rel: str, text: str) -> Path:
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


# ---------- tinh_cu ----------

def _mk_data(tmp_path, wl_lines=""):
    _mk(tmp_path, "web/data.json", json.dumps({"entities": [
        {"id": "e1", "type": "dish", "name": "A", "summary": "đặc sản tỉnh Bến Tre ngon",
         "description": "x", "attributes": {}},
        {"id": "e2", "type": "dish", "name": "B", "summary": "s", "description": "x",
         "attributes": {"note": "UBND tỉnh Trà Vinh công nhận 2016"}},
    ], "relationships": [], "itineraries": []}, ensure_ascii=False))
    _mk(tmp_path, "docs/standards/whitelist-tinh-cu.txt", wl_lines)


def test_tinh_cu_counts_non_whitelisted(tmp_path):
    _mk_data(tmp_path, "e2\tattr:note\n")
    r = TinhCuCheck(root=tmp_path).run()
    assert r["count"] == 1 and "e1:summary" in r["violations"][0]["msg"]


def test_tinh_cu_all_whitelisted_zero(tmp_path):
    _mk_data(tmp_path, "e1\tsummary\ne2\tattr:note\n")
    assert TinhCuCheck(root=tmp_path).run()["count"] == 0


def test_tinh_cu_fe_code_always_violation(tmp_path):
    _mk_data(tmp_path, "e1\tsummary\ne2\tattr:note\n")
    _mk(tmp_path, "web-nuxt/pages/x.vue", "<p>thuộc tỉnh Bến Tre</p>\n")
    r = TinhCuCheck(root=tmp_path).run()
    assert r["count"] == 1 and r["violations"][0]["file"].endswith("x.vue")


# ---------- fe_tokens ----------

def test_fe_colors_and_emoji_counters(tmp_path):
    _mk(tmp_path, "web-nuxt/pages/a.vue", "<style>.x{color:#ff0000;background:rgb(1,2,3)}</style>\n<template><span>🌿</span></template>\n")
    results = {r["rule"]: r for r in (c.run() for c in fe_checks(root=tmp_path))}
    assert results["R30.3"]["count"] == 1  # dòng style có hex + rgb → 1 dòng vi phạm... mỗi dòng 1 violation
    assert results["R30.3"]["level"] == "hard-ratchet"
    assert results["R30.2"]["count"] == 1 and results["R30.2"]["level"] == "soft-ratchet"


def test_fe_tokens_var_usage_clean(tmp_path):
    _mk(tmp_path, "web-nuxt/pages/a.vue", "<style>.x{color:var(--primary)}</style>\n")
    results = {r["rule"]: r["count"] for r in (c.run() for c in fe_checks(root=tmp_path))}
    assert results["R30.3"] == 0


def test_fe_colors_token_based_rgba_not_flagged(tmp_path):
    # rgba(var(--x-rgb), a) = DÙNG token (idiomatic áp alpha lên token màu) →
    # KHÔNG phải nợ (trước đây check flag nhầm ~620). rgb/rgba LITERAL vẫn bị bắt.
    _mk(tmp_path, "web-nuxt/pages/a.vue",
        "<style>.ok{background:rgba(var(--primary-rgb), .5); color:rgb( var(--x) )}"
        ".bad{border-color:rgba(1,2,3,.4)}</style>\n")
    results = {r["rule"]: r["count"] for r in (c.run() for c in fe_checks(root=tmp_path))}
    assert results["R30.3"] == 1  # chỉ .bad (rgba literal); 2 token-based bỏ qua


# ---------- doc_status ----------

def test_doc_status_missing_and_present(tmp_path):
    _mk(tmp_path, "docs/co.md", "# X\n\n> **STATUS (2026-07-07): active.**\n")
    _mk(tmp_path, "docs/thieu.md", "# Y\nnội dung\n")
    _mk(tmp_path, "docs/archive/old.md", "# Z\n")
    r = DocStatusCheck(root=tmp_path).run()
    assert r["count"] == 1 and r["violations"][0]["file"].endswith("thieu.md")


# ---------- links ----------

def test_links_broken_vs_alive(tmp_path):
    _mk(tmp_path, "docs/target.md", "# ok\n")
    _mk(tmp_path, "docs/a.md", "> STATUS x\n[ok](target.md) [chет](khong-ton-tai.md) [web](https://x.vn) [neo](#phan-1)\n")
    r = LinksCheck(root=tmp_path).run()
    assert r["count"] == 1 and "khong-ton-tai" in r["violations"][0]["msg"]


def test_links_repo_root_relative(tmp_path):
    _mk(tmp_path, "scripts/tool.py", "x\n")
    _mk(tmp_path, "docs/a.md", "[tool](scripts/tool.py)\n")
    assert LinksCheck(root=tmp_path).run()["count"] == 0


def test_links_ignores_inline_and_fenced_code(tmp_path):
    # Link-syntax trong inline-code / fenced-code là VÍ DỤ mô tả rule, KHÔNG phải
    # link thật → không được flag (false-positive R60.4 khi doc mô tả chính rule).
    _mk(tmp_path, "docs/a.md",
        "> STATUS x\n"
        "Rule: link markdown `[..](path)` nội bộ trỏ file không tồn tại.\n"
        "```\n[cũng-vậy](khong-ton-tai.md)\n```\n")
    assert LinksCheck(root=tmp_path).run()["count"] == 0

    # Nhưng link THẬT (ngoài code) vẫn bị bắt.
    _mk(tmp_path, "docs/b.md", "> STATUS x\n[thật](khong-ton-tai.md)\n")
    assert LinksCheck(root=tmp_path).run()["count"] == 1
