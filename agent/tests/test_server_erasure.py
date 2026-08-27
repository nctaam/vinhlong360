"""Readiness contract for the erasure scheduler capability."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import server  # noqa: E402


def test_readiness_reports_erasure_scheduler_state():
    source = (Path(__file__).resolve().parents[1] / "server.py").read_text(
        encoding="utf-8"
    )

    assert 'checks["erasure_scheduler"]' in source
    assert '"required_schema_version"' in source


# ─────────────────────────────────────────────────────────────────────────
# `overdue_count` phải LỘ RA — nó là bằng chứng lời hứa bị bỏ lỡ
# ─────────────────────────────────────────────────────────────────────────
# Người dùng bấm "Lên lịch xoá" và được trả lời «Tài khoản sẽ bị xoá vĩnh viễn
# sau N ngày» (agent/auth.py). Nhưng `_effective_erasure_audit_only()` trả True
# nếu THIẾU một trong hai cờ, và ở chế độ đó `erase_due_accounts` đếm số hồ sơ
# quá hạn rồi thoát TRƯỚC vòng xoá — 288 lần/ngày, lần nào cũng vậy.
#
# `overdue_count` vốn đã có trong `_ERASURE_STATUS` nhưng KHÔNG được chiếu ra
# /ready, nên tình trạng "hứa xoá mà không xoá" hoàn toàn vô hình với vận hành.
# Bài dưới đây khoá việc nó phải lộ ra, và khoá luôn TÊN trạng thái đáng lo.
#
# `ok` cố ý KHÔNG lật đỏ: chế độ chỉ-đếm là mặc định AN TOÀN cho giai đoạn chưa
# có người dùng thật, và lật /ready đỏ là chặn deploy của một cấu hình cố ý —
# quyết định đó thuộc chủ dự án, không thuộc cổng.

_SCHEMA_OK = {"ok": True, "schema_version": 81, "required_schema_version": 81}


def test_ready_lo_so_ho_so_qua_han_chua_xoa():
    out = server._erasure_readiness(
        {"audit_only": True, "overdue_count": 7}, _SCHEMA_OK
    )
    assert out["overdue_count"] == 7, "số hồ sơ quá hạn phải lộ ra /ready"
    assert out["state"] == "audit_only_with_overdue"
    # KHÔNG lật đỏ — xem giải thích ở đầu khối.
    assert out["ok"] is True


def test_ready_phan_biet_chi_dem_co_va_khong_co_ho_so_qua_han():
    khong = server._erasure_readiness({"audit_only": True, "overdue_count": 0}, _SCHEMA_OK)
    assert khong["state"] == "audit_only"
    co = server._erasure_readiness({"audit_only": True, "overdue_count": 1}, _SCHEMA_OK)
    assert co["state"] == "audit_only_with_overdue"
    assert khong["ok"] is co["ok"] is True


def test_ready_bao_dang_xoa_that_khi_tat_che_do_chi_dem():
    out = server._erasure_readiness(
        {"audit_only": False, "overdue_count": 0}, _SCHEMA_OK
    )
    assert out["state"] == "ready"
    assert out["audit_only"] is False


def test_ready_khong_vo_khi_status_thieu_hoac_hong():
    # Thiếu hẳn khoá → coi như chỉ-đếm (mặc định an toàn) và `ok` False vì hợp
    # đồng cũ đòi khoá `audit_only` phải có mặt.
    trong = server._erasure_readiness({}, _SCHEMA_OK)
    assert trong["audit_only"] is True
    assert trong["overdue_count"] == 0
    assert trong["ok"] is False
    # Giá trị rác không được làm sập probe.
    for rac in (None, "", "nhiều", [], {}):
        out = server._erasure_readiness(
            {"audit_only": True, "overdue_count": rac}, _SCHEMA_OK
        )
        assert out["overdue_count"] == 0, rac


def test_ready_do_khi_schema_chua_san_sang():
    out = server._erasure_readiness(
        {"audit_only": True, "overdue_count": 0},
        {"ok": False, "schema_version": 80, "required_schema_version": 81},
    )
    assert out["ok"] is False
