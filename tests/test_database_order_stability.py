"""`list_entities` phải có THỨ TỰ TOÀN PHẦN — nếu không, phân trang nói dối.

Truy vấn dựng `ORDER BY {order} LIMIT ? OFFSET ?` mà không nhánh `order` nào có
khoá phá hoà: `name ASC` (dữ liệu CÓ tên trùng — Vicosap ×2, dừa sáp ×2),
`rating DESC` (điểm thô, trùng hàng loạt), `updatedAt DESC` (4 entity đồng
điểm). Khi khoá sắp xếp đồng điểm, SQL KHÔNG hứa thứ tự nào cả — nó được phép
trả khác nhau giữa hai lần chạy, và giữa hai OFFSET khác nhau của cùng một truy
vấn. Hậu quả: một entity hiện ở cả trang 1 lẫn trang 2, một entity khác không
hiện ở trang nào.

SQLite thường trả theo rowid nên hay TÌNH CỜ ổn định; Postgres thì không, vì
planner được phép chọn kế hoạch khác cho mỗi OFFSET. Nên hai bài phân trang dưới
đây có thể xanh cả TRƯỚC lẫn SAU bản vá trên SQLite — chúng là hợp đồng, không
phải bằng chứng. Bằng chứng nằm ở `test_moi_nhanh_sap_xep_deu_ket_bang_khoa_duy_nhat`:
bài đó đọc thẳng mệnh đề ORDER BY mà mã sản phẩm dựng ra, nên nó đỏ ngay khi một
nhánh mới quên khoá phá hoà — kể cả nhánh chưa ai chạy tới.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "agent"))

import database  # noqa: E402


def _make_db(tmp_path, monkeypatch, n=12):
    """N entity CỐ Ý đồng điểm ở cả ba khoá sắp xếp."""
    monkeypatch.setattr(database, "USE_PG", False)
    monkeypatch.setattr(database, "DATABASE_URL", "")
    db = database.Database(str(tmp_path / "order.db"))
    assert db._use_pg is False
    for i in range(n):
        db.upsert_entity({
            "id": f"e{i:02d}",
            "type": "product",
            "name": "Trùng tên hoàn toàn",         # name ASC đồng điểm
            "area": "vinh-long",
            "attributes": {"rating": 4.5},          # rating DESC đồng điểm
            "updatedAt": "2026-01-01T00:00:00Z",    # updatedAt DESC đồng điểm
        })
    return db, n


def _phan_trang(db, sort, tong, buoc=5):
    ra = []
    for off in range(0, tong, buoc):
        ra.extend(e["id"] for e in db.list_entities(limit=buoc, offset=off, sort=sort))
    return ra


def test_phan_trang_khong_lap_khong_sot_khi_dong_diem(tmp_path, monkeypatch):
    db, n = _make_db(tmp_path, monkeypatch)
    for sort in (None, "newest", "name", "rating"):
        ids = _phan_trang(db, sort, n)
        assert len(ids) == n, f"sort={sort}: phân trang trả {len(ids)} thay vì {n}"
        assert len(set(ids)) == n, f"sort={sort}: có id LẶP giữa các trang — {ids}"


def test_cung_truy_van_hai_lan_cho_cung_thu_tu(tmp_path, monkeypatch):
    db, n = _make_db(tmp_path, monkeypatch)
    for sort in (None, "newest", "name", "rating"):
        a = [e["id"] for e in db.list_entities(limit=n, offset=0, sort=sort)]
        b = [e["id"] for e in db.list_entities(limit=n, offset=0, sort=sort)]
        assert a == b, f"sort={sort}: hai lần gọi ra hai thứ tự khác nhau"


def test_moi_nhanh_sap_xep_deu_ket_bang_khoa_duy_nhat():
    """BẰNG CHỨNG thật, khác hai bài trên.

    Hai bài phân trang chỉ chạy được nhánh nào SQLite thực sự đi qua, và SQLite
    tình cờ ổn định nên chúng xanh cả trước lẫn sau bản vá. Bài này đọc thẳng
    mệnh đề mà mã dựng ra, cho CẢ hai backend, nên nó đỏ ngay khi một nhánh
    quên khoá phá hoà — kể cả nhánh chỉ chạy trên Postgres.
    """
    for use_pg in (False, True):
        for sort in (None, "newest", "name", "rating", "khong-biet"):
            join, order = database._entity_order_clause(sort, use_pg)
            assert order.endswith(database._ENTITY_TIEBREAK), (
                f"use_pg={use_pg} sort={sort}: ORDER BY không kết bằng khoá "
                f"duy nhất — {order!r}"
            )
            # Khoá phá hoà phải là khoá CHÍNH, không phải một cột có thể trùng.
            assert "e.id" in database._ENTITY_TIEBREAK
            if sort == "rating":
                assert "entity_food_details" in join
            else:
                assert join == ""


def test_nhat_ky_kiem_toan_cung_tat_dinh():
    """`entity_changes` sắp theo created_at DESC; hai thay đổi trong cùng một
    giây thì thứ tự tuỳ hứng. Nhật ký kiểm toán không được phép như vậy."""
    src = Path(database.__file__).read_text(encoding="utf-8")
    assert "ORDER BY created_at DESC, id DESC" in src
