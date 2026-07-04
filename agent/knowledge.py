"""
vinhlong360 — Knowledge layer.

Đọc dữ liệu từ web/data.js, cung cấp các hàm truy vấn
cho Knowledge Agent (tương đương store.js phía Python).
"""

import json
import logging
import os
import re
import threading
import unicodedata
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "web"

# ── Parse data.js ──

def _parse_data_js():
    """Trích xuất entities, relationships, itineraries từ data.js bằng regex."""
    src = (DATA_DIR / "data.js").read_text(encoding="utf-8")

    # Bóc tách mảng places và items bằng cách eval qua JSON không được
    # (JS syntax ≠ JSON). Ta chuyển sang approach: export JSON riêng.
    # Nhưng hiện tại data.js là nguồn duy nhất → ta parse thủ công.

    # Approach: dùng data.js như source of truth, sinh ra data.json 1 lần.
    json_path = DATA_DIR / "data.json"
    if json_path.exists():
        with open(json_path, encoding="utf-8") as f:
            return json.load(f)
    raise FileNotFoundError(
        "data.json chưa được sinh. Chạy: python agent/export_data.py"
    )


def _load_from_json():
    """Seed/fallback: đọc trực tiếp từ web/data.json."""
    data = _parse_data_js()
    entities = {e["id"]: e for e in data["entities"]}
    relationships = data["relationships"]
    itineraries = {it["id"]: it for it in data["itineraries"]}
    return entities, relationships, itineraries


def _load_from_db():
    """GĐ3.5: DB là nguồn sự thật. Nạp toàn bộ vào in-memory (giữ tốc độ).

    Nếu DB rỗng (fresh deploy/CI), tự seed từ web/data.json một lần.
    """
    from database import db  # lazy import: tránh vòng import lúc khởi tạo

    Path(db.db_path).parent.mkdir(parents=True, exist_ok=True)
    db.initialize()
    stats = db.stats()
    if (stats.get("entities", 0) + stats.get("places", 0)) == 0:
        json_path = DATA_DIR / "data.json"
        if json_path.exists():
            db.migrate_from_json(str(json_path))
    entities = {e["id"]: e for e in db.all_entities()}
    relationships = db.all_relationships()
    itineraries = {it["id"]: it for it in db.all_itineraries()}
    return entities, relationships, itineraries


# Nguồn dữ liệu thực tế đã dùng ở lần load gần nhất ("db" | "json") — để introspect.
_data_source = None


def _load():
    """DB-primary; production PostgreSQL must fail hard instead of masking drift."""
    global _data_source
    try:
        entities, relationships, itineraries = _load_from_db()
        if entities:
            _data_source = "db"
            return entities, relationships, itineraries
    except Exception as exc:  # noqa: BLE001 - degrade gracefully
        env = os.environ.get("ENVIRONMENT", "development").strip().lower()
        database_url = os.environ.get("DATABASE_URL", "")
        allow_json_fallback = os.environ.get("VL360_ALLOW_JSON_FALLBACK", "").strip().lower() in {"1", "true", "yes", "on"}
        if database_url.startswith("postgresql") and env == "production" and not allow_json_fallback:
            _data_source = "db_error"
            logger.error("Production DB load failed; refusing data.json fallback (%s: %s)",
                         type(exc).__name__, exc)
            raise
        logger.warning("DB load failed (%s: %s); falling back to data.json",
                       type(exc).__name__, exc)
    _data_source = "json"
    return _load_from_json()


_entities, _relationships, _itineraries = None, None, None
# GĐ11.2: index kề {entity_id: [rel,...]} -> related() O(degree). Tự dựng lại (self-healing)
# khi _relationships đổi identity (qua reload HOẶC test patch trực tiếp).
_adjacency = None
_adj_src = None
_adj_lock = threading.Lock()


def _get_adjacency() -> dict:
    """Trả index kề, dựng lại nếu chưa có hoặc _relationships đã đổi (đối tượng khác)."""
    global _adjacency, _adj_src
    if _adjacency is not None and _adj_src is _relationships:
        return _adjacency
    with _adj_lock:
        if _adjacency is not None and _adj_src is _relationships:
            return _adjacency
        adj: dict[str, list] = {}
        for r in (_relationships or []):
            f, t = r.get("from"), r.get("to")
            if f:
                adj.setdefault(f, []).append(r)
            if t and t != f:
                adj.setdefault(t, []).append(r)
        _adjacency = adj
        _adj_src = _relationships
    return _adjacency


def _ensure():
    global _entities, _relationships, _itineraries
    if _entities is None:
        _entities, _relationships, _itineraries = _load()


# GĐ11.4: khoá tuần-tự-hoá reload (chống 2 reload đua nhau dựng + swap lẫn lộn).
# Reader (/chat, search, related) KHÔNG lấy khoá này → reload không đóng băng đọc;
# phần build nặng (_load đọc DB) nằm trong khoá nên chỉ chặn reload khác, không chặn reader.
_reload_lock = threading.Lock()


def reload():
    """Hot-reload data từ DB (sau admin CRUD / auto-learn / migrate).

    GĐ11.4: build nặng + swap dưới `_reload_lock` (tuần tự hoá reload). Endpoint /reload
    gọi qua asyncio.to_thread nên event loop KHÔNG bị đóng băng trong lúc đọc DB.
    Sau swap, vô hiệu adjacency để dựng lại theo _relationships mới (atomic-ish swap).
    """
    global _entities, _relationships, _itineraries, _adjacency, _adj_src
    with _reload_lock:
        new_e, new_r, new_i = _load()         # nặng (đọc DB) — chỉ chặn reload khác, không chặn reader
        _entities, _relationships, _itineraries = new_e, new_r, new_i
        _adjacency = None                     # vô hiệu index kề -> dựng lại lazy theo rel mới
        _adj_src = None
        src = _data_source
    return {"status": "ok", "entities": len(new_e),
            "itineraries": len(new_i), "source": src}


def _normalize_vn(text: str) -> str:
    """Bỏ dấu tiếng Việt để fuzzy match."""
    s = unicodedata.normalize("NFD", text.lower())
    s = re.sub(r"[̀-ͯ]", "", s)
    s = s.replace("đ", "d")
    return s


# Common Vietnamese words that don't signal topical relevance
_RELEVANCE_STOPWORDS = frozenset({
    "gi", "la", "co", "cua", "va", "o", "dau", "the", "nao", "khong", "duoc",
    "cho", "den", "tu", "ve", "mot", "cac", "nay", "do", "gia", "re", "cao",
    "dep", "ngon", "hay", "nhat", "tot", "moi", "nhieu", "it", "lon", "nho",
    "di", "an", "mua", "xem", "tim", "bao", "may", "sao", "khi", "tai", "voi",
    # GĐ-audit: từ phân loại/thương mại quá chung (gây khớp giả: "nhà hàng"→Lệ "Hằng",
    # "Nhà hàng X") — KHÔNG phải dấu hiệu phân biệt. Không đụng từ nội dung đặc trưng.
    "nha", "hang", "buffet", "cap", "ve", "phong", "dat",
})


def query_relevance(query: str, entity: dict) -> bool:
    """Heuristic: does this entity plausibly match the query topic?

    Used as an abstention gate for the degraded (LLM-down) path so we don't list
    out-of-domain entities surfaced by weak BM25 token matches. An entity is
    relevant if EITHER:
      - the cleaned query (or a ≥4-char fragment) is a substring of the entity's
        name/summary, OR
      - a meaningful content token (len ≥ 3, not a stopword) from the query
        appears in the entity NAME (high-precision signal).
    """
    qn = _normalize_vn(query)
    name_n = _normalize_vn(entity.get("name", ""))
    summary_n = _normalize_vn(entity.get("summary", ""))
    hay = name_n + " " + summary_n

    if qn and len(qn) >= 4 and qn in hay:
        return True

    q_tokens = [t for t in re.split(r"\s+", qn) if len(t) >= 3 and t not in _RELEVANCE_STOPWORDS]
    name_tokens = set(re.split(r"\s+", name_n))
    for t in q_tokens:
        if t in name_tokens:
            return True
    return False


# ── Query functions (tools cho agent) ──

ALL_MONTHS = list(range(1, 13))

MONTH_NAMES = {
    1: "tháng 1", 2: "tháng 2", 3: "tháng 3", 4: "tháng 4",
    5: "tháng 5", 6: "tháng 6", 7: "tháng 7", 8: "tháng 8",
    9: "tháng 9", 10: "tháng 10", 11: "tháng 11", 12: "tháng 12",
}


def season_text(e: dict) -> str:
    """Mô tả mùa vụ dạng text."""
    s = e.get("season")
    if not s:
        return "quanh năm"
    months = s.get("months", [])
    peak = s.get("peak", [])
    if not months:
        return "quanh năm"
    parts = []
    if peak:
        parts.append("mùa cao điểm " + ", ".join(MONTH_NAMES.get(m, str(m)) for m in peak))
    parts.append("mùa: " + ", ".join(MONTH_NAMES.get(m, str(m)) for m in months))
    return "; ".join(parts)

CARD_TYPES = ["experience", "product", "dish", "craft_village", "attraction", "accommodation",
              "person", "event", "history", "nature", "economy"]

# GĐ4.5: cấp hành chính của type=place. 'place' phi-hành-chính (level ngoài tập này) thực chất
# là quán/nhà hàng/doanh nghiệp/địa danh bị gán nhầm type=place -> nên cho vào tìm kiếm.
ADMIN_LEVELS = {"phuong", "xa", "tinh", "huyen", "quan", "thi-tran", "thanh-pho"}


def _is_searchable(e: dict) -> bool:
    """Entity hiển thị trong tìm kiếm: card-type, place phi-hành-chính (quán/DN), HOẶC facility (cơ quan)."""
    t = e.get("type")
    if t in CARD_TYPES or t == "facility":  # GĐ13: cho cơ quan nhà nước vào tìm kiếm
        return True
    return t == "place" and e.get("level") not in ADMIN_LEVELS

AREA_META = {
    "vinh-long": {"name": "Vĩnh Long", "emoji": "🍊"},
    "ben-tre": {"name": "Bến Tre", "emoji": "🥥"},
    "tra-vinh": {"name": "Trà Vinh", "emoji": "🛕"},
    "lien-vung": {"name": "Liên vùng", "emoji": "🧭"},
}


def get_entity(entity_id: str) -> dict | None:
    _ensure()
    return _entities.get(entity_id)


def get_place(entity_id: str) -> dict | None:
    """Trả về xã/phường mà entity thuộc về."""
    _ensure()
    e = _entities.get(entity_id)
    if not e:
        return None
    pid = e.get("placeId")
    return _entities.get(pid) if pid else None


def area_of(entity_id: str) -> str | None:
    p = get_place(entity_id)
    return p["area"] if p else None


def places(area: str = None) -> list[dict]:
    _ensure()
    out = [e for e in _entities.values()
           if e["type"] == "place" and e.get("parentId")]
    if area:
        out = [p for p in out if p.get("area") == area]
    return sorted(out, key=lambda p: p["name"])


def search_entities(
    q: str = None,
    entity_type: str = None,
    area: str = None,
    place_id: str = None,
    month: int = None,
    ocop_only: bool = False,
    limit: int = 20,
) -> list[dict]:
    """Tìm kiếm entities theo nhiều tiêu chí."""
    _ensure()
    results = []
    for e in _entities.values():
        if not _is_searchable(e):  # GĐ4.5: gồm cả place phi-hành-chính (quán/nhà hàng)
            continue
        if entity_type and e["type"] != entity_type:
            continue
        if place_id and e.get("placeId") != place_id:
            continue
        if area:
            p = get_place(e["id"])
            # Primary: check via places data
            area_match = p and p.get("area") == area
            # Fallback: check province_old attribute (for new ward-crawl entities)
            if not area_match:
                prov = (e.get("attributes") or {}).get("province_old", "")
                _AREA_PROV = {
                    "ben-tre": "Bến Tre",
                    "tra-vinh": "Trà Vinh",
                    "vinh-long": "Vĩnh Long",
                }
                area_match = prov == _AREA_PROV.get(area, "")
            if not area_match:
                continue
        if month:
            season = e.get("season")
            if season and month not in season.get("months", ALL_MONTHS):
                continue
        if ocop_only:
            attrs = e.get("attributes", {})
            if not attrs.get("ocop"):
                continue
        if q:
            ql = q.lower()
            ql_norm = _normalize_vn(q)
            place_info = get_place(e["id"]) or {}
            attrs = e.get("attributes") or {}
            searchable = " ".join(filter(None, [
                e.get("name"), e.get("summary"),
                place_info.get("alias"), place_info.get("legacyArea"), place_info.get("name"),
                attrs.get("ward"), attrs.get("district"),
                attrs.get("province_old"), attrs.get("address"),
            ])).lower()
            searchable_norm = _normalize_vn(searchable)
            if ql not in searchable and ql_norm not in searchable_norm:
                continue
        results.append(e)

    # Smart ranking: popularity + season + content richness
    try:
        from smart_rank import smart_score
        results.sort(key=lambda e: smart_score(e, month=month), reverse=True)
    except ImportError:
        def score(e):
            s = e.get("season")
            if not month or not s:
                return 1
            if month in (s.get("peak") or []):
                return 4
            if month in s.get("months", []):
                return 3
            return 1
        results.sort(key=score, reverse=True)

    return results[:limit]


def seasonal_now(month: int) -> list[dict]:
    """Sản phẩm/trải nghiệm đang vào mùa."""
    _ensure()
    results = []
    for e in _entities.values():
        if e["type"] not in ("product", "experience"):
            continue
        s = e.get("season")
        if not s:
            continue
        if month in (s.get("peak") or []):
            results.append(e)
    return results[:10]


def related(entity_id: str) -> list[dict]:
    """Các thực thể liên quan qua relationships."""
    _ensure()
    REL_FWD = {"hosts": "Tổ chức", "offered_by": "Đặt qua", "made_by": "Sản xuất bởi",
               "produced_in": "Sản xuất tại", "supplies_to": "Cung ứng cho", "near": "Gần"}
    REL_BWD = {"hosts": "Diễn ra tại", "offered_by": "Cung cấp", "made_by": "Sản phẩm",
               "produced_in": "Đặc sản", "supplies_to": "Nguồn cung", "near": "Gần"}
    out = []
    for r in (_get_adjacency().get(entity_id) or []):  # GĐ11.2: chỉ duyệt cạnh kề entity này
        if r["from"] == entity_id and r["to"] in _entities:
            other = _entities[r["to"]]
            out.append({"label": REL_FWD.get(r["type"], r["type"]),
                        "entity": other["name"], "id": other["id"]})
        elif r["to"] == entity_id and r["from"] in _entities:
            other = _entities[r["from"]]
            out.append({"label": REL_BWD.get(r["type"], r["type"]),
                        "entity": other["name"], "id": other["id"]})
    return out


def directory_search(query: str, limit: int = 12) -> list[dict]:
    """GĐ13: tra danh bạ cơ quan (facility) theo tên cơ quan HOẶC tên xã/phường.

    Trả [{name, office_kind, address, phone, hours, ward, source, updated_at}].
    Trống nếu chưa nạp dữ liệu danh bạ thật (13.6).
    """
    _ensure()
    qn = _normalize_vn(query or "")
    out = []
    for e in _entities.values():
        if e.get("type") != "facility":
            continue
        ward = _entities.get(e.get("placeId")) or {}
        hay = _normalize_vn(f"{e.get('name', '')} {ward.get('name', '')}")
        if not qn or qn in hay:
            attrs = e.get("attributes") or {}
            src = e.get("source") or {}
            out.append({
                "name": e.get("name"),
                "office_kind": attrs.get("office_kind"),
                "address": attrs.get("address"),
                "phone": attrs.get("phone"),
                "hours": attrs.get("hours"),
                "ward": ward.get("name"),
                "source": src.get("url") or src.get("title"),
                "updated_at": e.get("updatedAt"),
            })
        if len(out) >= limit:
            break
    return out


def get_itinerary(itinerary_id: str) -> dict | None:
    _ensure()
    return _itineraries.get(itinerary_id)


def list_itineraries(area: str = None) -> list[dict]:
    _ensure()
    out = list(_itineraries.values())
    if area:
        out = [it for it in out if it.get("area") == area or area in (it.get("areas") or [])]
    return out


def stats() -> dict:
    _ensure()
    by_type = {}
    for e in _entities.values():
        if e["type"] in CARD_TYPES:
            by_type[e["type"]] = by_type.get(e["type"], 0) + 1
    all_places = places()
    return {
        "total_content": sum(by_type.values()),
        "by_type": by_type,
        "places": len(all_places),
        "phuong": sum(1 for p in all_places if p.get("level") == "phuong"),
        "xa": sum(1 for p in all_places if p.get("level") == "xa"),
        "itineraries": len(_itineraries),
    }


def health_check() -> dict:
    """Quick readiness probe for the knowledge layer."""
    _ensure()
    entity_count = len(_entities) if _entities else 0
    return {
        "status": "ok" if entity_count > 0 else "degraded",
        "data_source": _data_source or "unknown",
        "entity_count": entity_count,
        "relationship_count": len(_relationships) if _relationships else 0,
        "itinerary_count": len(_itineraries) if _itineraries else 0,
    }


def compare_areas(area_1: str, area_2: str) -> dict:
    """So sánh 2 khu vực theo nhiều tiêu chí."""
    _ensure()

    def area_stats(area: str) -> dict:
        by_type = {}
        total = 0
        for e in _entities.values():
            if e["type"] not in CARD_TYPES:
                continue
            p = get_place(e["id"])
            if not p or p.get("area") != area:
                continue
            by_type[e["type"]] = by_type.get(e["type"], 0) + 1
            total += 1

        ps = places(area)
        return {
            "area": area,
            "area_name": AREA_META.get(area, {}).get("name", area),
            "total_content": total,
            "by_type": by_type,
            "places_count": len(ps),
            "highlights": _top_entities(area, 5),
        }

    return {
        "area_1": area_stats(area_1),
        "area_2": area_stats(area_2),
    }


def _top_entities(area: str, limit: int = 5) -> list[dict]:
    """Top entities của 1 area."""
    _ensure()
    entries = []
    for e in _entities.values():
        if e["type"] not in CARD_TYPES:
            continue
        p = get_place(e["id"])
        if not p or p.get("area") != area:
            continue
        entries.append(e)
    entries.sort(key=lambda e: e.get("name", ""))
    return [{"id": e["id"], "name": e["name"], "type": e["type"], "summary": e.get("summary", "")[:100]} for e in entries[:limit]]


def nearby_entities(entity_id: str, limit: int = 8) -> list[dict]:
    """Tìm entities gần 1 entity (cùng placeId hoặc cùng area)."""
    _ensure()
    e = _entities.get(entity_id)
    if not e:
        return []

    pid = e.get("placeId")
    place = _entities.get(pid) if pid else None
    area = place.get("area") if place else None

    nearby = []

    # 1. Cùng placeId
    if pid:
        for other in _entities.values():
            if len(nearby) >= limit:
                break
            if other["id"] == entity_id:
                continue
            if other["type"] not in CARD_TYPES:
                continue
            if other.get("placeId") == pid:
                nearby.append({"id": other["id"], "name": other["name"], "type": other["type"],
                               "summary": other.get("summary", "")[:80], "proximity": "cùng xã/phường"})

    # 2. Cùng area (nếu chưa đủ)
    if len(nearby) < limit and area:
        for other in _entities.values():
            if other["id"] == entity_id:
                continue
            if other["type"] not in CARD_TYPES:
                continue
            if other.get("placeId") == pid:
                continue  # Đã có
            op = get_place(other["id"])
            if op and op.get("area") == area:
                nearby.append({"id": other["id"], "name": other["name"], "type": other["type"],
                               "summary": other.get("summary", "")[:80], "proximity": "cùng khu vực"})
            if len(nearby) >= limit:
                break

    # 3. Qua relationships
    rels = related(entity_id)
    for r in rels:
        if len(nearby) >= limit:
            break
        if r["id"] not in {n["id"] for n in nearby}:
            re_entity = _entities.get(r["id"])
            if re_entity:
                nearby.append({"id": r["id"], "name": r["entity"], "type": re_entity.get("type", ""),
                               "summary": re_entity.get("summary", "")[:80], "proximity": r["label"]})

    return nearby[:limit]


def entity_detail(entity_id: str) -> dict | None:
    """Thông tin đầy đủ về 1 entity, bao gồm place + related."""
    _ensure()
    e = _entities.get(entity_id)
    if not e:
        return None
    place = get_place(entity_id)
    rels = related(entity_id)
    area = place["area"] if place else None
    return {
        **e,
        "place_name": place["name"] if place else None,
        "place_alias": place.get("alias") if place else None,
        "legacy_area": place.get("legacyArea") if place else None,
        "area": area,
        "area_name": AREA_META.get(area, {}).get("name") if area else None,
        "related": rels,
    }
