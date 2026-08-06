# -*- coding: utf-8 -*-
"""Bug lộ ra khi đọc code để viết docstring cho route công khai (2026-08-06).

Ba cái đầu là bug HÀNH VI, không phải nợ chuẩn — và không cái nào bị test hiện
có bắt, vì các test đó chỉ assert cấu trúc response (status 200 + có khoá) chứ
không assert nội dung.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys

import pytest

AGENT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AGENT_DIR))

import public_api  # noqa: E402
import seo  # noqa: E402


# ── 1. /api/areas trả rỗng vì hai điều kiện loại trừ nhau ───────────────────

def test_list_entities_khong_bao_gio_tra_ve_type_place():
    """`db.list_entities` loại cứng `e.type != 'place'` (database.py).

    Đây là hành vi CỐ Ý cho danh sách entity thường, nhưng nó biến mọi lời gọi
    kèm `entity_type="place"` thành truy vấn luôn rỗng — chính là cách
    `/api/areas` đang dùng.
    """
    from database import db

    tat_ca = db.all_entities()
    so_place_that = sum(1 for e in tat_ca if e.get("type") == "place")
    assert so_place_that > 0, "DB test phải có ít nhất một entity type=place"

    qua_list_entities = db.list_entities(entity_type="place", limit=1000)
    assert qua_list_entities == [], (
        "list_entities đã đổi hành vi — nếu nay nó TRẢ được place thì "
        "hàm _query() trong list_areas không còn cần đường vòng nữa"
    )


def test_api_areas_tra_ve_du_lieu_that():
    """Hợp đồng: /api/areas phải gom được place theo area, không trả rỗng.

    Test cũ (`test_integration_api.py`) chỉ assert có khoá `areas`/`total_places`
    nên endpoint chết vẫn qua.
    """
    from database import db

    class _Resp:
        def __init__(self):
            self.headers = {}

    so_place = sum(1 for e in db.all_entities() if e.get("type") == "place")
    # Gọi thẳng coroutine bằng asyncio.run: repo không cài pytest-asyncio, và
    # anyio plugin đòi fixture riêng — ở đây chỉ cần chạy đúng một coroutine.
    ket_qua = asyncio.run(public_api.list_areas(_Resp()))

    assert ket_qua["total_places"] > 0, "/api/areas vẫn trả rỗng"
    assert ket_qua["total_places"] <= so_place
    assert ket_qua["areas"], "không nhóm được khu vực nào"
    for nhom in ket_qua["areas"]:
        assert nhom["count"] == len(nhom["places"])


# ── 2. entity_og_meta lộ meta của entity chưa được duyệt ────────────────────

def _dat_data_json(tmp_path, monkeypatch, entity: dict) -> None:
    path = tmp_path / "data.json"
    path.write_text(
        json.dumps({"entities": [entity], "relationships": [], "itineraries": []},
                   ensure_ascii=False),
        encoding="utf-8",
    )
    monkeypatch.setattr(seo, "DATA_PATH", path)
    monkeypatch.setattr(seo, "_data", None)
    monkeypatch.setattr(seo, "_data_mtime_ns", None)
    monkeypatch.setattr(seo, "_by_id_cache", None)
    # _load_seo_data() = _load_db_data() or _load(); ép nhánh DB trả None để
    # endpoint đọc đúng file fixture thay vì DB thật của máy.
    monkeypatch.setattr(seo, "_load_db_data", lambda: None)


@pytest.mark.parametrize(
    "entity_extra",
    [{"status": "provisional"}, {"verified": False}],
    ids=["provisional", "verified-false"],
)
def test_entity_og_meta_khong_lo_entity_chua_duyet(tmp_path, monkeypatch, entity_extra):
    """`/seo/og/{id}` phải theo cùng luật hiển thị với `/seo/jsonld/{id}`.

    entity_jsonld lọc `_is_listing_visible`, entity_og_meta thì không — nên một
    entity chưa duyệt vẫn trả về tiêu đề, mô tả, ảnh qua đường OG. Đây là rò rỉ
    nội dung chưa kiểm duyệt ra ngoài (Track-H).
    """
    _dat_data_json(tmp_path, monkeypatch, {
        "id": "chua-duyet", "name": "Chưa duyệt", "type": "attraction",
        "summary": "Nội dung chưa qua kiểm duyệt", **entity_extra,
    })

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        seo.entity_og_meta("chua-duyet")
    assert exc.value.status_code == 404


def test_entity_og_meta_van_tra_entity_da_duyet(tmp_path, monkeypatch):
    _dat_data_json(tmp_path, monkeypatch, {
        "id": "da-duyet", "name": "Đã duyệt", "type": "attraction",
        "summary": "Nội dung công khai",
    })

    meta = seo.entity_og_meta("da-duyet")

    assert meta["og:title"]


# ── 3. toggle_rsvp suy `going` từ rowcount thay vì trạng thái thật ──────────

def test_toggle_rsvp_lay_going_tu_trang_thai_that_khong_phai_rowcount():
    """Đọc source: sau nhánh INSERT, `going` phải phản ánh dòng CÓ tồn tại hay không.

    Bản cũ dùng `bool(cur.rowcount > 0)` sau `INSERT ... ON CONFLICT DO NOTHING`.
    Khi dòng đã tồn tại (hai request đồng thời, DELETE không khớp), rowcount = 0
    nên API trả going=False trong khi `count` ở cùng response VẪN đếm dòng đó —
    hai trường mâu thuẫn nhau và nút trên giao diện nhảy sai trạng thái.

    Kiểm bằng source vì nhánh này chỉ chạy trên PostgreSQL.
    """
    import notifications

    src = Path(notifications.__file__).read_text(encoding="utf-8")
    than = src[src.index("async def toggle_rsvp"):]
    than = than[:than.index("@router.get")]

    assert "cur.rowcount > 0" not in than, (
        "going vẫn suy từ rowcount của INSERT ON CONFLICT DO NOTHING"
    )
    assert "SELECT 1 FROM event_rsvp" in than, (
        "cần đọc lại trạng thái thật sau thao tác để tính going"
    )
