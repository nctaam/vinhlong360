"""Hợp đồng cấu hình cho vòng xoá tài khoản — VÀ cho lời hứa đi kèm nó.

ĐẢO MẶC ĐỊNH 2026-08-30, theo chỉ đạo chủ dự án ("thực hiện theo Luật 91/2025").
File này TRƯỚC ĐÓ ghim đúng chiều ngược lại:

    assert fields["ERASURE_AUDIT_ONLY"].default is True
    assert fields["ERASURE_ACTIVATION_ENABLED"].default is False

Ghi rõ để không ai tưởng đây là nới một rào an toàn: mặc định cũ ĐANG NÓI DỐI.
`identity/api.py` trả lời người dùng «Tài khoản sẽ bị xoá vĩnh viễn sau N ngày»
VÔ ĐIỀU KIỆN, còn tác vụ nền ở chế độ chỉ-đếm thì đếm hồ sơ quá hạn rồi thoát
trước vòng xoá, 288 lần/ngày. Luật 91/2025 cho người dùng QUYỀN được xoá; một
mặc định "an toàn" bằng cách không xoá là an toàn cho hệ thống, không phải cho họ.

Foot-gun được chặn ở tầng dưới chứ không phải bằng mặc định: `erase_due_accounts`
đòi PostgreSQL (`db._use_pg`) và trả DB_ERROR nếu không có — mọi máy dev chạy
SQLite KHÔNG thể xoá gì. Và `ERASURE_ACTIVATION_ENABLED` vẫn là CẦU DAO: đặt
False là dừng xoá ngay, không cần deploy lại.
"""

from __future__ import annotations

import inspect

from config import Settings, erasure_is_audit_only, settings


def test_mac_dinh_la_XOA_THAT_chu_khong_phai_chi_dem():
    fields = Settings.model_fields

    assert fields["ERASURE_AUDIT_ONLY"].default is False
    assert fields["ERASURE_ACTIVATION_ENABLED"].default is True
    assert erasure_is_audit_only() is False, (
        "với mặc định, hệ thống phải THẬT SỰ xoá — nếu không thì lời hứa ở "
        "identity/api.py lại thành nói dối"
    )


def test_cau_dao_van_tat_duoc_bang_MOT_co(monkeypatch):
    """Cả hai cờ đều phải tự mình dừng được vòng xoá — đây là đường lùi khẩn."""
    monkeypatch.setattr(settings, "ERASURE_ACTIVATION_ENABLED", False)
    assert erasure_is_audit_only() is True
    monkeypatch.undo()

    monkeypatch.setattr(settings, "ERASURE_AUDIT_ONLY", True)
    assert erasure_is_audit_only() is True


def test_scheduler_va_api_hoi_CUNG_MOT_cau():
    """Hai nơi phải dùng chung một nguồn sự thật, không tự dựng luật riêng.

    Đây là rào cho chính lỗ hổng P0: chỗ trả lời người dùng không hỏi được cấu
    hình nên cứ hứa "xoá vĩnh viễn" bất kể vòng xoá đang bật hay tắt.
    """
    import scheduler
    from identity import api as identity_api

    assert "erasure_is_audit_only" in inspect.getsource(
        scheduler._effective_erasure_audit_only
    ), "scheduler phải uỷ quyền cho config, đừng chép lại luật"
    assert "erasure_is_audit_only" in inspect.getsource(
        identity_api.delete_account
    ), "chỗ trả lời người dùng phải hỏi cấu hình trước khi hứa"


def test_loi_hua_doi_theo_cau_hinh_chu_khong_ghim_cung():
    """Câu «xoá vĩnh viễn» chỉ được xuất hiện ở NHÁNH có xoá thật.

    Ghim theo cấu trúc chứ không theo chữ: trong mã dựng câu trả lời phải có một
    nhánh điều kiện dựa trên `erasure_is_audit_only`, và chuỗi hứa-xoá-vĩnh-viễn
    phải nằm SAU `else` của nhánh đó. Nếu ai gỡ điều kiện đi, rào này đỏ.
    """
    from pathlib import Path

    src = (Path(__file__).resolve().parents[1] / "identity" / "api.py").read_text(
        encoding="utf-8"
    )
    assert "erasure_is_audit_only" in src
    i_dieu_kien = src.find("chi_dem = erasure_is_audit_only()")
    i_hua = src.find("sẽ bị xoá vĩnh viễn")
    assert i_dieu_kien != -1, "mất nhánh điều kiện — lời hứa lại thành vô điều kiện"
    assert i_hua > i_dieu_kien, (
        "chuỗi hứa xoá-vĩnh-viễn phải nằm SAU khi đã hỏi cấu hình"
    )
