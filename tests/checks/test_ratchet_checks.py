# -*- coding: utf-8 -*-
"""Test 4 module HARD-RATCHET (SP01 T4)."""
import json
import sys
from pathlib import Path

import pytest

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
    # Từ 2026-08-05 đếm theo TỪNG MATCH: dòng style có #ff0000 VÀ rgb(1,2,3) → 2.
    # Đếm theo dòng biến ratchet thành lỗ: gộp màu cũ vào một dòng là mua suất
    # cho màu cứng mới ở chỗ khác.
    assert results["R30.3"]["count"] == 2
    assert results["R30.3"]["level"] == "hard-ratchet"
    assert results["R30.2"]["count"] == 1 and results["R30.2"]["level"] == "soft-ratchet"


def test_fe_colors_dem_tung_match_khong_phai_tung_dong(tmp_path):
    """Chốt chặn cho chính lỗ ratchet: 3 màu / 3 dòng và 3 màu / 1 dòng phải bằng nhau."""
    _mk(tmp_path, "web-nuxt/pages/nhieu-dong.vue",
        "<style>\n.a{color:#111111}\n.b{color:#222222}\n.c{color:#333333}\n</style>\n")
    spread = {r["rule"]: r["count"] for r in (c.run() for c in fe_checks(root=tmp_path))}

    (tmp_path / "web-nuxt/pages/nhieu-dong.vue").unlink()
    _mk(tmp_path, "web-nuxt/pages/mot-dong.vue",
        "<style>.a{color:#111111}.b{color:#222222}.c{color:#333333}</style>\n")
    packed = {r["rule"]: r["count"] for r in (c.run() for c in fe_checks(root=tmp_path))}

    assert spread["R30.3"] == 3
    assert packed["R30.3"] == 3, "gộp dòng vẫn giấu được màu cứng"


def test_fe_colors_rgb_co_khoang_trang_truoc_var_khong_bi_bat(tmp_path):
    """`rgb( var(--x) )` là dùng token; lookahead phải bao cả khoảng trắng."""
    _mk(tmp_path, "web-nuxt/pages/a.vue",
        "<style>.ok{color:rgb( var(--x) )}</style>\n")
    results = {r["rule"]: r["count"] for r in (c.run() for c in fe_checks(root=tmp_path))}
    assert results["R30.3"] == 0


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


# --- R60.1: STATUS phải có nội dung (hồi quy 2026-08-05) -------------------

def _doc(tmp_path, body: str):
    p = tmp_path / "docs" / "x.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")
    return DocStatusCheck(root=tmp_path)


@pytest.mark.parametrize("header", [
    "> STATUS: active", "> **STATUS**: done", "> STATUS (2026-08-04): complete",
    "> STATUS: implementation complete - đã kiểm chứng", ">STATUS: obsolete",
])
def test_doc_status_chap_nhan_header_co_noi_dung(tmp_path, header):
    assert _doc(tmp_path, f"{header}\n\n# Tài liệu\n").run()["count"] == 0


@pytest.mark.parametrize("header", [
    "> STATUS", "> STATUS:", "> STATUS: ", "> STATUSAAAA vớ vẩn", "> STATUS  ",
])
def test_doc_status_bat_header_rong_hoac_gia(tmp_path, header):
    """Gõ đúng chữ STATUS rồi bỏ trống từng qua cổng hard-ratchet."""
    assert _doc(tmp_path, f"{header}\n\n# Tài liệu\n").run()["count"] == 1


# --- R10.7: whitelist phải ĐẾM, và quét cả vùng lồng (hồi quy 2026-08-05) ---

def _mk_nested_data(tmp_path, wl_lines=""):
    _mk(tmp_path, "web/data.json", json.dumps({
        "entities": [{
            "id": "e1", "type": "dish", "name": "A", "summary": "s", "description": "d",
            # attributes LỒNG — bản cũ chỉ nhìn attributes kiểu chuỗi nên bỏ sót hết
            "attributes": {"key_facts": ["Sản lượng lớn nhất tỉnh Bến Tre", "không liên quan"]},
        }],
        "relationships": [],
        "itineraries": [{"id": "t1", "stops": [{"name": "Bảo tàng tỉnh Bến Tre"}]}],
    }, ensure_ascii=False))
    _mk(tmp_path, "docs/standards/whitelist-tinh-cu.txt", wl_lines)


def test_tinh_cu_quet_attributes_long_va_itineraries(tmp_path):
    """8 occurrence trong key_facts[] và 1 trong itineraries từng vô hình hoàn toàn."""
    _mk_nested_data(tmp_path)
    result = TinhCuCheck(root=tmp_path).run()

    fields = {v["msg"].split(" — ")[0] for v in result["violations"]}
    assert "e1:attr:key_facts[0]" in fields, fields
    assert "t1:itinerary:stops[0].name" in fields, fields


def test_tinh_cu_whitelist_dem_so_lan(tmp_path):
    """Một dòng whitelist chỉ miễn ĐÚNG số lần khai, không phải vô hạn."""
    _mk(tmp_path, "web/data.json", json.dumps({
        "entities": [{"id": "e1", "type": "dish", "name": "A", "description": "d",
                      "summary": "tỉnh Bến Tre và tỉnh Trà Vinh và tỉnh Bến Tre",
                      "attributes": {}}],
        "relationships": [], "itineraries": [],
    }, ensure_ascii=False))
    wl = tmp_path / "docs/standards/whitelist-tinh-cu.txt"
    wl.parent.mkdir(parents=True, exist_ok=True)

    wl.write_text("e1\tsummary\n", encoding="utf-8")          # 1 suất
    assert TinhCuCheck(root=tmp_path).run()["count"] == 2

    wl.write_text("e1\tsummary\t3\n", encoding="utf-8")       # đủ 3 suất
    assert TinhCuCheck(root=tmp_path).run()["count"] == 0

    wl.write_text("e1\tsummary\t2\n", encoding="utf-8")       # thiếu 1
    result = TinhCuCheck(root=tmp_path).run()
    assert result["count"] == 1
    assert "vượt số lần đã duyệt" in result["violations"][0]["msg"]


def test_tinh_cu_whitelist_2_cot_van_doc_duoc(tmp_path):
    """88 dòng cũ (2 cột) không được vỡ khi thêm cột thứ ba."""
    _mk_nested_data(tmp_path, "e1\tattr:key_facts[0]\nt1\titinerary:stops[0].name\n")
    assert TinhCuCheck(root=tmp_path).run()["count"] == 0
