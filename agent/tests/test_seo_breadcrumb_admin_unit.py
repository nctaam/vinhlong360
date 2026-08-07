"""Khoá hình dạng mắt xích hành chính trong BreadcrumbList backend phát ra.

§1.6 CLAUDE.md: từ 1/7/2025 tỉnh Vĩnh Long mới chạy hành chính 2 CẤP
(tỉnh → 124 xã/phường). "Bến Tre"/"Trà Vinh" KHÔNG còn là đơn vị hành chính;
trường `area` chỉ là vùng CŨ dùng tra cứu/lọc, không được đứng trong breadcrumb.

`/seo/jsonld/{id}` trước đây phát mắt xích `area` (`/khu-vuc/...`) nên
structured data nói "Bến Tre" trong khi HTML nói "P. An Hội" — lệch.
Backend giờ phải phát THẲNG mắt xích xã/phường, đúng quy ước của
web-nuxt/utils/adminUnit.ts (`adminUnitLabel` + `adminUnitCrumb`):

- 'Phường An Hội' → 'P. An Hội'; 'Xã Long Hòa' → giữ nguyên; 'Tỉnh X' → 'X'
- `level` của entity place thắng tiền tố suy từ tên
- không xác định được xã/phường → BỎ HẲN mắt xích (không bịa địa bàn)
- entity `type=place` → KHÔNG đội mắt xích hành chính lên chính nó

Test đối chiếu 1-1 với web-nuxt/tests/detail-admin-unit-breadcrumb.test.ts.
"""

import seo

SITE = seo.SITE

PLACES = [
    {"id": "p-an-hoi", "name": "Phường An Hội", "type": "place", "level": "phuong", "area": "ben-tre"},
    {"id": "x-long-hoa", "name": "Xã Long Hòa", "type": "place", "level": "xa", "area": "ben-tre"},
    {"id": "t-vinh-long", "name": "Tỉnh Vĩnh Long", "type": "place", "level": "tinh"},
    # Place chỉ có tên mang tiền tố, không có `level` — phải suy được từ tên.
    {"id": "p-ben-tre", "name": "Phường Bến Tre", "type": "place", "area": "ben-tre"},
]


def _by_id(extra=()):
    return {e["id"]: e for e in [*PLACES, *extra]}


def _crumbs(entity, by_id=None):
    return seo._build_breadcrumb(entity, by_id if by_id is not None else _by_id())["itemListElement"]


def _names(entity, by_id=None):
    return [item["name"] for item in _crumbs(entity, by_id)]


def _assert_wellformed(items):
    """Bất biến chung: đánh số liên tục từ 1, không mắt xích vùng cũ, không rỗng."""
    assert [item["position"] for item in items] == list(range(1, len(items) + 1))
    assert all(item["@type"] == "ListItem" for item in items)
    assert all(str(item["name"]).strip() for item in items)
    assert "/khu-vuc/" not in str(items)


# ── entity CÓ placeId ────────────────────────────────────────────────────────


def test_breadcrumb_emits_ward_tier_instead_of_defunct_area():
    entity = {
        "id": "cho-ben-tre",
        "name": "Chợ Bến Tre",
        "type": "attraction",
        "placeId": "p-an-hoi",
        "area": "ben-tre",  # vùng cũ vẫn còn trên entity — không được lọt ra breadcrumb
    }
    items = _crumbs(entity)

    assert [i["name"] for i in items] == ["Trang chủ", "Du lịch", "P. An Hội", "Chợ Bến Tre"]
    # Khớp từng field với mắt xích mà frontend dựng (detail-admin-unit-breadcrumb.test.ts)
    assert items[2] == {
        "@type": "ListItem",
        "position": 3,
        "name": "P. An Hội",
        "item": f"{SITE}/xa-phuong/p-an-hoi",
    }
    _assert_wellformed(items)


def test_breadcrumb_spells_out_xa_without_p_prefix():
    entity = {
        "id": "vuon-dua-long-hoa",
        "name": "Vườn dừa Long Hòa",
        "type": "experience",
        "placeId": "x-long-hoa",
        "area": "ben-tre",
    }
    items = _crumbs(entity)

    assert [i["name"] for i in items] == ["Trang chủ", "Du lịch", "Xã Long Hòa", "Vườn dừa Long Hòa"]
    assert items[2]["item"] == f"{SITE}/xa-phuong/x-long-hoa"
    _assert_wellformed(items)


def test_breadcrumb_infers_level_from_name_prefix_when_place_has_no_level():
    entity = {"id": "quan-oc", "name": "Quán ốc", "type": "restaurant", "placeId": "p-ben-tre"}
    # 'Phường Bến Tre' là PHƯỜNG của tỉnh Vĩnh Long mới, không phải tỉnh Bến Tre cũ.
    assert _names(entity)[-2] == "P. Bến Tre"


def test_breadcrumb_drops_province_prefix_so_no_defunct_tier_survives():
    entity = {"id": "su-kien-tinh", "name": "Sự kiện cấp tỉnh", "type": "event", "placeId": "t-vinh-long"}
    assert _names(entity) == ["Trang chủ", "Lễ hội", "Vĩnh Long", "Sự kiện cấp tỉnh"]


def test_breadcrumb_encodes_place_id_unsafe_in_a_path():
    by_id = _by_id([{"id": "p a/b", "name": "Phường A", "type": "place", "level": "phuong"}])
    entity = {"id": "x", "name": "X", "type": "attraction", "placeId": "p a/b"}
    assert _crumbs(entity, by_id)[2]["item"] == f"{SITE}/xa-phuong/p%20a%2Fb"


# ── entity KHÔNG có placeId ──────────────────────────────────────────────────


def test_breadcrumb_drops_the_tier_when_place_id_is_missing():
    entity = {"id": "khong-co-place", "name": "Điểm chưa gán xã", "type": "experience", "area": "ben-tre"}
    items = _crumbs(entity)

    # Trước khi vá: mắt xích "Bến Tre" → /khu-vuc/ben-tre. Không bịa địa bàn nữa.
    assert [i["name"] for i in items] == ["Trang chủ", "Du lịch", "Điểm chưa gán xã"]
    _assert_wellformed(items)


def test_breadcrumb_drops_the_tier_when_place_id_points_at_a_missing_id():
    entity = {
        "id": "place-id-chet",
        "name": "Điểm có placeId chết",
        "type": "experience",
        "placeId": "p-khong-ton-tai",
        "area": "ben-tre",
    }
    items = _crumbs(entity)

    assert [i["name"] for i in items] == ["Trang chủ", "Du lịch", "Điểm có placeId chết"]
    _assert_wellformed(items)


def test_breadcrumb_keeps_an_unlinked_label_when_only_place_name_is_known():
    """Payload đã enrich (`place_name`) nhưng không có placeId → giữ nhãn, bỏ liên kết."""
    entity = {"id": "x", "name": "X", "type": "attraction", "place_name": "Xã Long Hòa"}
    items = _crumbs(entity)

    assert [i["name"] for i in items] == ["Trang chủ", "Du lịch", "Xã Long Hòa", "X"]
    assert "item" not in items[2]
    _assert_wellformed(items)


# ── entity type=place ────────────────────────────────────────────────────────


def test_breadcrumb_never_puts_a_ward_above_a_place_entity():
    """39/125 place trong web/data.json có placeId ≠ id (32 trỏ nhầm p-long-chau).

    Trang "Xã An Bình" không được đội mắt xích "P. Long Châu" — nó ĐÃ LÀ đơn vị
    hành chính, phía trên chỉ còn chuyên mục Xã phường.
    """
    entity = {
        "id": "xa-an-binh",
        "name": "Xã An Bình",
        "type": "place",
        "level": "xa",
        "area": "vinh-long",
        "placeId": "p-an-hoi",  # dữ liệu trỏ nhầm sang phường khác
    }
    items = _crumbs(entity)

    assert [i["name"] for i in items] == ["Trang chủ", "Xã phường", "Xã An Bình"]
    assert "An Hội" not in str(items)
    # Mắt xích chuyên mục /xa-phuong (không có id) phải còn — nó không phải mắt xích địa bàn.
    assert items[1]["item"] == f"{SITE}/xa-phuong"
    _assert_wellformed(items)


def test_breadcrumb_drops_a_self_referential_place_id():
    entity = {"id": "p-an-hoi", "name": "Phường An Hội", "type": "organization", "placeId": "p-an-hoi"}
    assert _names(entity) == ["Trang chủ", "Danh bạ", "Phường An Hội"]


# ── xuyên suốt JSON-LD entity ────────────────────────────────────────────────


def test_entity_jsonld_breadcrumb_carries_no_defunct_area_tier(sample_entities):
    by_id = {str(e["id"]): e for e in sample_entities if e.get("id")}
    ld = seo.build_entity_jsonld(by_id["cam-sanh-vinh-long"], by_id)
    items = ld["breadcrumb"]["itemListElement"]

    assert [i["name"] for i in items] == [
        "Trang chủ",
        "Sản phẩm",
        "Xã Bình Hòa Phước",
        "Cam sành Vĩnh Long",
    ]
    assert "/khu-vuc/" not in str(ld["breadcrumb"])
    _assert_wellformed(items)


# _admin_unit_source — tách khỏi _admin_unit_crumb cho cổng R20.8. Hai nguồn
# (entity place tra được vs payload đã enrich) là lý do hàm tồn tại, nên khoá cả hai.


def test_admin_unit_source_uu_tien_entity_place_tra_duoc():
    by_id = {"p-an-hoi": {"name": "Phường An Hội", "level": "phuong"}}
    entity = {"placeId": "p-an-hoi", "place_name": "SAI — không được dùng"}
    assert seo._admin_unit_source(entity, by_id, "p-an-hoi") == ("Phường An Hội", "phuong")


def test_admin_unit_source_roi_ve_payload_da_enrich():
    """API công khai chỉ gắn place_name/place_level, không gắn cả entity place."""
    entity = {"placeId": "p-khong-co", "place_name": "Xã Long Hòa", "place_level": "xa"}
    assert seo._admin_unit_source(entity, {}, "p-khong-co") == ("Xã Long Hòa", "xa")


def test_admin_unit_source_khong_co_place_id():
    entity = {"place_name": "Phường An Hội"}
    assert seo._admin_unit_source(entity, {"x": {"name": "SAI"}}, "") == ("Phường An Hội", None)
