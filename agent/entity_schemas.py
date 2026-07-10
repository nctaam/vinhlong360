"""agent/entity_schemas.py — Content-model registry (entity architecture Phase 1).

Single source of truth for the *typed structure* of each entity type. Drives:
  - AdminCP typed create/edit forms  (GET /admin/entity-schema)
  - server-side attribute validation on save  (admin.py)
  - the canonical VALID_TYPES set + the type->kind (owner category) mapping

Design decision (deep research 2026-07, docs/architecture-decisions + kien-truc):
STI-with-registry. The physical `entities` table STAYS a single polymorphic
table (id/type/name/summary/…/attributes JSONB). This module adds the per-type
field structure at the *application layer* — additive, reversible, NO DDL. It is
the app-layer equivalent of a headless-CMS content model (Strapi/Directus): one
field schema per type → auto-generated admin form + validation + display.

Physically splitting into per-type tables was evaluated and rejected for this
scale (1730 rows / 17 types held in RAM): it fractures the unified id space the
relationship graph + RAM loader depend on, turns every cross-type query into a
UNION fan-out, and forces a big-bang migration against the additive-first
invariants. Per-type extension tables (CTI) are reserved for a future trigger —
a single type growing a heavy, independently-queried, FK-constrained attribute
set — and tracked in ROADMAP "Backlog phát sinh", not built now.

Widgets understood by the frontend <SchemaField> dispatcher:
  text | textarea | number | select | multiselect | tags | bool | tel | url | date
"""
from __future__ import annotations

# ── Owner-facing categories (kinds) grouping the 17 raw types ──────────────
# The owner asked to think in 7 categories; the data has 17 types. This maps
# each raw `type` to a coarse "kind" for grouping/reporting. `type` stays the
# storage discriminator; `kind` is a derived label (Phase 2 exposes it on the API).
KIND_META: dict[str, dict] = {
    "place":       {"label": "Địa điểm", "emoji": "🛕"},   # tourism destinations
    "experience":  {"label": "Trải nghiệm", "emoji": "🌾"},
    "product":     {"label": "Sản phẩm & OCOP", "emoji": "🍊"},
    "food":        {"label": "Ẩm thực & Ăn uống", "emoji": "🍲"},
    "lodging":     {"label": "Lưu trú", "emoji": "🏡"},
    "event":       {"label": "Sự kiện & Lễ hội", "emoji": "🎉"},
    "itinerary":   {"label": "Lịch trình", "emoji": "🗺️"},
    "facility":    {"label": "Cơ quan & Tiện ích", "emoji": "🏛️"},
    "person":      {"label": "Nhân vật", "emoji": "👤"},
    "admin_place": {"label": "Xã/Phường (hành chính)", "emoji": "📍"},
    "other":       {"label": "Khác", "emoji": "📦"},
}

KIND_OF_TYPE: dict[str, str] = {
    "attraction": "place", "nature": "place", "history": "place",
    "experience": "experience",
    "product": "product", "craft_village": "product",
    "dish": "food", "drink": "food", "restaurant": "food", "cafe": "food",
    "accommodation": "lodging",
    "event": "event",
    "itinerary": "itinerary",
    "facility": "facility",
    "person": "person",
    "place": "admin_place",
    "organization": "other", "economy": "other",
}


def _f(key, label, widget="text", **extra):
    """Build one field definition. extra: required, options, group, help, unit,
    placeholder, max, min, step."""
    d = {"key": key, "label": label, "widget": widget}
    d.update(extra)
    return d


# ── Reusable field bundles (grounded in the empirical attribute taxonomy) ──
# "Practical info" — the address/phone/hours cluster shared by most card types.
CONTACT = [
    _f("address", "Địa chỉ", "text", group="Liên hệ & thực dụng",
       placeholder="Số nhà, ấp/khóm, xã/phường"),
    _f("phone", "Điện thoại", "tel", group="Liên hệ & thực dụng"),
    _f("website", "Website / Fanpage", "url", group="Liên hệ & thực dụng"),
    _f("hours", "Giờ mở cửa", "text", group="Liên hệ & thực dụng",
       placeholder="VD: 7:00–17:00 hằng ngày"),
]
SUBCAT = _f("sub_category", "Phân loại chi tiết", "text", group="Cơ bản",
            help="Nhãn phụ mô tả loại con (VD: chùa Khmer, vườn trái cây…)")
PRICE = _f("price_range", "Khoảng giá", "text", group="Liên hệ & thực dụng",
           placeholder="VD: 20.000–50.000đ")
BESTTIME = _f("best_time", "Thời điểm đẹp nhất", "text", group="Trải nghiệm",
              placeholder="VD: sáng sớm, mùa nước nổi tháng 9–11")
ADMISSION = _f("admission", "Vé / phí vào cửa", "text", group="Liên hệ & thực dụng",
               placeholder="VD: Miễn phí / 20.000đ")
HIGHLIGHT = _f("highlight", "Điểm nhấn", "textarea", group="Trải nghiệm",
               help="Một câu mô tả điều đặc biệt nhất")

HERITAGE_LEVELS = ["Di tích quốc gia đặc biệt", "Di tích quốc gia",
                   "Di tích cấp tỉnh", "Chưa xếp hạng"]
ACCOM_TYPES = ["Khách sạn", "Homestay", "Nhà nghỉ", "Resort", "Nhà vườn", "Khác"]
# SP6 2026-07-07: +4 mục cho facility ngoài-cơ-quan (bến xe/phà, ngân hàng/ATM,
# viễn thông, cửa hàng) — trước đây 28/58 facility không có lựa chọn khớp.
OFFICE_KINDS = ["ubnd", "cong_an", "y_te", "truong_hoc", "buu_dien", "tu_phap",
                "giao_thong", "ngan_hang", "vien_thong", "cua_hang", "khac"]
DIFFICULTY = ["Dễ", "Trung bình", "Khó"]


# ── Per-type schemas: type -> ordered list of ATTRIBUTE field defs ─────────
# Only the type-specific *attributes* tail is defined here. The top-level entity
# columns (name/type/placeId/summary/description/coordinates/season/images) are
# rendered by the core form section and are common to all types.
ENTITY_SCHEMAS: dict[str, dict] = {
    "attraction": {"fields": [
        SUBCAT, *CONTACT, ADMISSION, BESTTIME,
        _f("architecture_style", "Phong cách kiến trúc", "text", group="Chi tiết"),
        _f("founding_year", "Năm hình thành", "number", group="Chi tiết"),
        _f("religion", "Tôn giáo / tín ngưỡng", "text", group="Chi tiết"),
        _f("dress_code", "Quy định trang phục", "text", group="Chi tiết"),
        HIGHLIGHT,
    ]},
    "history": {"fields": [
        SUBCAT, *CONTACT, ADMISSION,
        _f("architectural_style", "Phong cách kiến trúc", "text", group="Chi tiết"),
        _f("heritage_type", "Loại di tích", "text", group="Chi tiết"),
        _f("heritage_level", "Cấp xếp hạng", "select", options=HERITAGE_LEVELS, group="Chi tiết"),
        _f("historical_period", "Thời kỳ lịch sử", "text", group="Chi tiết"),
        HIGHLIGHT,
    ]},
    "nature": {"fields": [
        SUBCAT, *CONTACT, ADMISSION, BESTTIME,
        _f("waterway_type", "Loại thủy vực", "text", group="Chi tiết",
           placeholder="VD: sông, kênh, cù lao"),
        _f("scenic_rating", "Điểm cảnh quan (1–5)", "number", group="Chi tiết", min=1, max=5),
        _f("best_view_point", "Điểm ngắm cảnh đẹp", "text", group="Chi tiết"),
        HIGHLIGHT,
    ]},
    "experience": {"fields": [
        SUBCAT, *CONTACT, ADMISSION, PRICE, BESTTIME,
        _f("duration", "Thời lượng", "text", group="Trải nghiệm",
           placeholder="VD: 2–3 giờ, nửa ngày"),
        _f("operator", "Đơn vị tổ chức", "text", group="Chi tiết"),
        HIGHLIGHT,
    ]},
    "product": {"fields": [
        SUBCAT, *CONTACT, PRICE,
        _f("ocop_star", "Sao OCOP", "select", options=["1", "2", "3", "4", "5"], group="OCOP"),
        _f("ocop_certified", "Đã chứng nhận OCOP", "bool", group="OCOP"),
        _f("gi_certification", "Chỉ dẫn địa lý (GI)", "text", group="OCOP"),
        _f("producer", "Nhà sản xuất / cơ sở", "text", group="Chi tiết"),
        _f("variety", "Giống / loại", "text", group="Chi tiết"),
        _f("shelf_life", "Hạn sử dụng", "text", group="Chi tiết"),
        _f("specialty", "Đặc điểm nổi bật", "text", group="Chi tiết"),
    ]},
    "dish": {"fields": [
        SUBCAT, *CONTACT, PRICE, BESTTIME,
        _f("origin", "Nguồn gốc", "text", group="Ẩm thực"),
        _f("ingredients", "Nguyên liệu chính", "tags", group="Ẩm thực"),
        _f("specialty", "Đặc trưng", "text", group="Ẩm thực"),
        _f("where_to_eat", "Ăn ở đâu", "text", group="Ẩm thực"),
        _f("cooking_method", "Cách chế biến", "text", group="Ẩm thực"),
        _f("main_ingredient", "Nguyên liệu chủ đạo", "text", group="Ẩm thực"),
    ]},
    "drink": {"fields": [
        SUBCAT, *CONTACT, PRICE,
        _f("origin", "Nguồn gốc", "text", group="Ẩm thực"),
        _f("ingredients", "Nguyên liệu", "tags", group="Ẩm thực"),
        _f("where_to_eat", "Uống ở đâu", "text", group="Ẩm thực"),
    ]},
    "craft_village": {"fields": [
        SUBCAT, *CONTACT,
        _f("specialty", "Sản phẩm đặc trưng", "text", group="Làng nghề", required=True),
        _f("households", "Số hộ làm nghề", "number", group="Làng nghề"),
        _f("raw_material", "Nguyên liệu", "text", group="Làng nghề"),
        _f("recognition_date", "Ngày công nhận", "text", group="Làng nghề"),
        _f("cooperative", "Hợp tác xã", "text", group="Làng nghề"),
    ]},
    "accommodation": {"fields": [
        _f("accommodation_type", "Loại hình lưu trú", "select", options=ACCOM_TYPES,
           group="Lưu trú", required=True),
        SUBCAT, *CONTACT, PRICE,
        _f("star_rating", "Hạng sao", "number", group="Lưu trú", min=1, max=5),
        _f("rooms", "Số phòng", "number", group="Lưu trú"),
        _f("check_in", "Giờ nhận phòng", "text", group="Lưu trú"),
        _f("check_out", "Giờ trả phòng", "text", group="Lưu trú"),
        _f("amenities", "Tiện nghi", "tags", group="Lưu trú"),
        _f("booking_note", "Ghi chú đặt phòng", "textarea", group="Lưu trú",
           help="Chỉ giới thiệu — KHÔNG chốt đơn/giá/số lượng on-site"),
    ]},
    "restaurant": {"fields": [
        SUBCAT, *CONTACT, PRICE,
        _f("specialty", "Món đặc trưng", "text", group="Quán ăn"),
        _f("signature_dish", "Món signature", "text", group="Quán ăn"),
        _f("rating", "Điểm đánh giá", "number", group="Quán ăn", min=0, max=5, step=0.1),
        _f("review_count", "Số lượt đánh giá", "number", group="Quán ăn"),
        _f("parking", "Có chỗ đậu xe", "bool", group="Quán ăn"),
        _f("view", "Không gian / view", "text", group="Quán ăn"),
    ]},
    "cafe": {"fields": [
        SUBCAT, *CONTACT, PRICE, BESTTIME,
        _f("specialty", "Đồ uống đặc trưng", "text", group="Cà phê"),
        _f("wifi", "Có wifi", "bool", group="Cà phê"),
        _f("rating", "Điểm đánh giá", "number", group="Cà phê", min=0, max=5, step=0.1),
        _f("review_count", "Số lượt đánh giá", "number", group="Cà phê"),
    ]},
    "event": {"fields": [
        SUBCAT, *CONTACT,
        _f("date_start", "Ngày bắt đầu", "text", group="Thời gian",
           placeholder="VD: 2026-01-15 hoặc rằm tháng Giêng"),
        _f("date_end", "Ngày kết thúc", "text", group="Thời gian"),
        _f("lunar_date", "Ngày âm lịch", "text", group="Thời gian",
           help="Điền nếu là lễ hội theo lịch âm → hệ thống xem là lễ hội"),
        _f("month", "Tháng diễn ra", "number", group="Thời gian", min=1, max=12),
        _f("duration_days", "Số ngày diễn ra", "number", group="Thời gian"),
        _f("organizer", "Đơn vị tổ chức", "text", group="Chi tiết"),
        _f("venue", "Địa điểm tổ chức", "text", group="Chi tiết"),
        _f("target_audience", "Đối tượng", "text", group="Chi tiết"),
        HIGHLIGHT,
    ]},
    "itinerary": {"fields": [
        _f("duration", "Thời lượng", "text", group="Lịch trình",
           placeholder="VD: 2 ngày 1 đêm"),
        _f("provinces", "Tỉnh/vùng đi qua", "tags", group="Lịch trình"),
        _f("traveler_type", "Phù hợp cho", "text", group="Lịch trình",
           placeholder="VD: gia đình, cặp đôi, phượt"),
        _f("budget_range", "Ngân sách dự kiến", "text", group="Lịch trình"),
        _f("difficulty", "Độ khó", "select", options=DIFFICULTY, group="Lịch trình"),
        _f("start_point", "Điểm xuất phát", "text", group="Lịch trình"),
        BESTTIME,
    ]},
    "facility": {"fields": [
        _f("office_kind", "Loại cơ quan / tiện ích", "select", options=OFFICE_KINDS,
           group="Cơ quan", required=True,
           help="ubnd, cong_an, y_te, truong_hoc, buu_dien, tu_phap, giao_thong, ngan_hang, vien_thong, cua_hang, khac"),
        _f("address", "Địa chỉ", "text", group="Liên hệ & thực dụng"),
        _f("phone", "Điện thoại", "tel", group="Liên hệ & thực dụng"),
        _f("emergency_phone", "SĐT khẩn cấp", "tel", group="Liên hệ & thực dụng"),
        _f("hours", "Giờ làm việc", "text", group="Liên hệ & thực dụng"),
        _f("note_for_tourists", "Ghi chú cho du khách", "textarea", group="Chi tiết"),
        _f("category_tag", "Nhãn danh mục", "text", group="Chi tiết"),
        _f("transport_type", "Loại giao thông", "text", group="Chi tiết"),
    ]},
    "person": {"fields": [
        _f("role", "Vai trò / chức danh", "text", group="Nhân vật", required=True),
        _f("birth_year", "Năm sinh", "number", group="Nhân vật"),
        _f("death_year", "Năm mất", "number", group="Nhân vật"),
        _f("hometown", "Quê quán", "text", group="Nhân vật"),
        _f("address", "Nơi tưởng niệm / gắn với", "text", group="Nhân vật"),
    ]},
    "organization": {"fields": [
        SUBCAT, *CONTACT, PRICE,
    ]},
    "economy": {"fields": [
        SUBCAT, *CONTACT,
    ]},
    "place": {"fields": [
        _f("former_district", "Huyện cũ", "text", group="Hành chính"),
        _f("merged_from", "Sáp nhập từ", "tags", group="Hành chính"),
        _f("population", "Dân số", "number", group="Hành chính"),
        _f("effective_date", "Ngày hiệu lực", "text", group="Hành chính"),
        _f("governance_model", "Mô hình chính quyền", "text", group="Hành chính"),
    ]},
}

# Attach kind + emoji/label metadata to each schema entry (from useConstants parity).
_TYPE_LABEL = {
    "attraction": ("Tham quan", "🛕"), "history": ("Lịch sử / Di tích", "🏛️"),
    "nature": ("Thiên nhiên", "🌿"), "experience": ("Trải nghiệm", "🌾"),
    "product": ("Đặc sản & OCOP", "🍊"), "dish": ("Ẩm thực", "🍲"),
    "drink": ("Đồ uống", "🥤"), "craft_village": ("Làng nghề", "🏺"),
    "accommodation": ("Lưu trú", "🏡"), "restaurant": ("Quán ăn", "🍽️"),
    "cafe": ("Quán cà phê", "☕"), "event": ("Sự kiện & Lễ hội", "🎉"),
    "itinerary": ("Lịch trình", "🗺️"), "facility": ("Cơ quan hành chính", "🏛️"),
    "person": ("Nhân vật", "👤"), "organization": ("Cơ sở / HTX", "🏢"),
    "economy": ("Kinh tế", "📊"), "place": ("Xã/Phường", "📍"),
}
for _t, _s in ENTITY_SCHEMAS.items():
    _lbl, _emo = _TYPE_LABEL.get(_t, (_t, "📍"))
    _s["type"] = _t
    _s["label"] = _lbl
    _s["emoji"] = _emo
    _s["kind"] = KIND_OF_TYPE.get(_t, "other")


# ── Public helpers ─────────────────────────────────────────────────────────
def valid_types() -> set[str]:
    """Canonical set of entity types — single source of truth for admin.py."""
    return set(ENTITY_SCHEMAS.keys())


def kind_of(entity_type: str) -> str:
    return KIND_OF_TYPE.get(entity_type, "other")


def schema_for(entity_type: str) -> dict | None:
    return ENTITY_SCHEMAS.get(entity_type)


def field_map(entity_type: str) -> dict[str, dict]:
    s = ENTITY_SCHEMAS.get(entity_type)
    return {f["key"]: f for f in s["fields"]} if s else {}


def all_schemas() -> dict:
    """Full registry payload for the AdminCP (GET /admin/entity-schema)."""
    return {
        "types": ENTITY_SCHEMAS,
        "kinds": KIND_META,
        "kind_of_type": KIND_OF_TYPE,
    }


def _coerce_number(value):
    """Coerce a raw value to int/float for the 'number' widget. May raise
    ValueError/TypeError (caught by the caller)."""
    if isinstance(value, bool):
        return value, False
    if isinstance(value, (int, float)):
        return value, True
    s = str(value).strip().replace(",", ".")
    f = float(s)
    return (int(f) if f.is_integer() else f), True


def _coerce_bool(value):
    """Coerce a raw value to bool for the 'bool' widget."""
    if isinstance(value, bool):
        return value, True
    return str(value).strip().lower() in ("1", "true", "yes", "có", "co", "on"), True


def _coerce_tags(value):
    """Coerce a raw value to a list for the 'tags'/'multiselect' widgets."""
    if isinstance(value, list):
        return value, True
    return [p.strip() for p in str(value).split(",") if p.strip()], True


def _coerce(value, widget):
    """Best-effort coerce a raw value to the widget's expected python type.
    Returns (coerced_value, ok). Never raises."""
    if value is None or value == "":
        return value, True
    try:
        if widget == "number":
            return _coerce_number(value)
        if widget == "bool":
            return _coerce_bool(value)
        if widget in ("tags", "multiselect"):
            return _coerce_tags(value)
        return value, True
    except (ValueError, TypeError):
        return value, False


def validate_attributes(entity_type: str, attrs: dict | None) -> tuple[dict, list[str]]:
    """Non-destructive typed validation of an entity's attributes against its
    schema. Coerces KNOWN typed fields (number/bool/tags) and checks
    required/select-membership. Unknown keys are PRESERVED verbatim (the long
    bespoke tail — deity_worshipped, sac_phong, …). Returns (normalized_attrs,
    warnings); never raises, so it can't break an existing save.
    """
    attrs = dict(attrs or {})
    warnings: list[str] = []
    fmap = field_map(entity_type)
    if not fmap:
        return attrs, warnings
    for key, fdef in fmap.items():
        _validate_field(key, fdef, attrs, warnings)
    return attrs, warnings


def _validate_field(key, fdef, attrs, warnings):
    """Validate/coerce a single field IN PLACE: mutates attrs[key] to its coerced
    value and appends any warnings. Extracted verbatim from validate_attributes'
    loop body — same checks, same side-effect order."""
    if key not in attrs:
        if fdef.get("required"):
            warnings.append(f"Thiếu trường bắt buộc: {fdef['label']} ({key})")
        return
    val = attrs[key]
    coerced, ok = _coerce(val, fdef["widget"])
    if not ok:
        warnings.append(f"Giá trị không hợp lệ cho {fdef['label']} ({key}): {val!r}")
        return
    attrs[key] = coerced
    if fdef.get("required") and (coerced is None or coerced == ""):
        warnings.append(f"Trường bắt buộc để trống: {fdef['label']} ({key})")
    _check_select_membership(key, fdef, coerced, warnings)


def _check_select_membership(key, fdef, coerced, warnings):
    """Warn if a 'select' field's coerced value is outside its allowed options."""
    opts = fdef.get("options")
    if opts and fdef["widget"] == "select" and coerced not in ("", None):
        if str(coerced) not in [str(o) for o in opts]:
            warnings.append(f"{fdef['label']} ({key}) = {coerced!r} không thuộc danh sách cho phép")
