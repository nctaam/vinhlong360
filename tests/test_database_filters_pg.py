"""Nhánh SQL CHỈ-CÓ-TRÊN-POSTGRES của bộ lọc entity công khai.

`tests/test_database_filters.py` (sau 0f7269ea) ghim `USE_PG=False` để 4 bài chạy
được ở CẢ hai job CI thay vì `skipif` im lặng. Đổi lại: dưới job `test-pg` chúng
vẫn đi đường SQLite, nên 4 nhánh SQL riêng của Postgres KHÔNG hề được chạy —
chính docstring của file đó ghi nợ này lại ("… vẫn CHƯA có test — đó là việc khác").

File này trả nợ đó. Mỗi bài khoá đúng một nhánh `if self._use_pg:`:

  1. `_append_area_filter` (agent/database.py:390) — `e."placeId"` PHẢI có nháy kép.
     Bỏ nháy → PG hạ chữ thành `placeid` → `UndefinedColumn`. SQLite không bao giờ
     lộ lỗi này vì tên cột ở đó là `placeId` không nháy.
  2. `_append_q_filter` (agent/database.py:401) — `f_unaccent(lower(...))` (migration
     015) khiến tìm kiếm KHÔNG phân biệt dấu VÀ không phân biệt hoa/thường. Nhánh
     SQLite là `LIKE` trần, không có tính chất này.
  3. `_month_condition` (agent/database.py:1182) — `e.season::jsonb->'months' @> %s::jsonb`
     với tham số `json.dumps([month])`. Nhánh SQLite dùng `json_each` + số nguyên trần.
  4. `list_entities` sort mặc định (agent/database.py:1215) — `e."updatedAt"` cũng
     phải có nháy kép, cùng lớp lỗi với (1).

DB Postgres của CI DÙNG CHUNG cho cả suite và đã seed dữ liệu thật, nên mọi bài ở
đây tự cô lập bằng một `area`/tên chứa tag ngẫu nhiên rồi tự dọn — không bài nào
khẳng định trên tổng số hàng.
"""

import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "agent"))

import database  # noqa: E402  (R20.7: ghép file test ↔ agent/database.py)
from database import db  # noqa: E402

pg_only = pytest.mark.skipif(
    not db._use_pg,
    reason="Nhánh SQL Postgres-only. Đặt DATABASE_URL=postgresql://… để chạy.",
)


@pytest.fixture
def pg_fixture():
    """Tạo 1 place + 3 entity mang tag duy nhất, dọn sạch sau bài test."""
    tag = uuid.uuid4().hex[:12]
    area = f"zz-test-area-{tag}"
    ids = [f"zz-place-{tag}", f"zz-dish-{tag}", f"zz-old-{tag}", f"zz-new-{tag}"]

    db.upsert_entity({
        "id": ids[0],
        "type": "place",
        "name": f"Place {tag}",
        "area": area,
    })
    # KHÔNG đặt `area` — buộc bộ lọc phải đi qua nhánh con `placeId IN (SELECT …)`,
    # tức đúng chỗ cần nháy kép trên Postgres.
    db.upsert_entity({
        "id": ids[1],
        "type": "dish",
        "name": f"Bánh Xèo {tag}",
        "summary": "bánh dân dã",
        "placeId": ids[0],
        "season": {"months": [7, 8]},
        "updatedAt": "2026-03-01T00:00:00Z",
    })
    db.upsert_entity({
        "id": ids[2],
        "type": "attraction",
        "name": f"Cũ {tag}",
        "area": area,
        "updatedAt": "2026-01-01T00:00:00Z",
    })
    db.upsert_entity({
        "id": ids[3],
        "type": "attraction",
        "name": f"Mới {tag}",
        "area": area,
        "updatedAt": "2026-06-01T00:00:00Z",
    })
    try:
        yield {"tag": tag, "area": area, "ids": ids}
    finally:
        for entity_id in ids:
            db.delete_entity(entity_id)


@pg_only
def test_area_filter_resolves_place_via_quoted_placeid_column(pg_fixture):
    """`e."placeId"` — bỏ nháy kép thì PG ném UndefinedColumn, SQLite thì không."""
    rows = db.list_entities(area=pg_fixture["area"], limit=50)

    ids = {r["id"] for r in rows}
    # dish KHÔNG có cột area — chỉ lọt qua được bằng nhánh placeId
    assert pg_fixture["ids"][1] in ids
    assert pg_fixture["ids"][2] in ids and pg_fixture["ids"][3] in ids
    assert pg_fixture["ids"][0] not in ids  # place bị loại bởi `type != 'place'`


@pg_only
def test_count_filtered_matches_list_through_placeid_branch(pg_fixture):
    """Cùng nhánh area nhưng ở câu COUNT (đường code riêng, dễ lệch khi sửa)."""
    assert db.count_entities_filtered(area=pg_fixture["area"]) == 3


@pg_only
def test_q_filter_ignores_diacritics(pg_fixture):
    """f_unaccent: gõ không dấu vẫn ra tên có dấu. Nhánh SQLite KHÔNG làm được."""
    rows = db.search_entities(q=f"banh xeo {pg_fixture['tag']}", limit=20)

    assert [r["id"] for r in rows] == [pg_fixture["ids"][1]]


@pg_only
def test_q_filter_ignores_case_of_query(pg_fixture):
    """`escape_like(q.lower())` + `lower(e.name)` — truy vấn HOA vẫn khớp."""
    rows = db.search_entities(q=f"BÁNH XÈO {pg_fixture['tag']}".upper(), limit=20)

    assert [r["id"] for r in rows] == [pg_fixture["ids"][1]]


@pg_only
def test_month_condition_uses_jsonb_containment(pg_fixture):
    """`season::jsonb->'months' @> '[7]'::jsonb` — tháng có/không đều phải đúng."""
    hit = db.list_entities(area=pg_fixture["area"], month=7, limit=50)
    miss = db.list_entities(area=pg_fixture["area"], month=9, limit=50)

    assert [r["id"] for r in hit] == [pg_fixture["ids"][1]]
    assert miss == []


@pg_only
def test_month_condition_survives_search_path(pg_fixture):
    """`_month_param` phải trả `json.dumps([month])` — số trần sẽ nổ ở cast jsonb."""
    rows = db.search_entities(q=pg_fixture["tag"], area=pg_fixture["area"],
                              month=8, limit=20)

    assert [r["id"] for r in rows] == [pg_fixture["ids"][1]]


@pg_only
def test_default_sort_orders_by_quoted_updated_at(pg_fixture):
    """`e."updatedAt"` — cùng lớp lỗi nháy kép với placeId, và thứ tự phải giảm dần."""
    rows = db.list_entities(area=pg_fixture["area"], entity_type="attraction", limit=50)

    assert [r["id"] for r in rows] == [pg_fixture["ids"][3], pg_fixture["ids"][2]]


@pg_only
def test_pg_branch_flags_are_actually_engaged():
    """Chốt tiền đề: nếu `_use_pg` False thì mọi bài trên đo nhầm engine."""
    assert db._use_pg is True
    assert db._ph == "%s"
    assert database.USE_PG is True
