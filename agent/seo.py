"""
vinhlong360 SEO endpoints: JSON-LD, sitemap.xml, robots.txt.

The SEO layer reads from web/data.json because that file remains the
moderated public source of truth. Helpers are intentionally defensive so
older coordinate/source shapes do not break structured data endpoints.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse
from xml.sax.saxutils import escape as xml_escape

logger = logging.getLogger(__name__)

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse, Response

router = APIRouter()

DATA_PATH = Path(__file__).parent.parent / "web" / "data.json"
SITE = "https://vinhlong360.vn"

AREA_NAMES = {
    "vinh-long": "Vĩnh Long",
    "ben-tre": "Bến Tre",
    "tra-vinh": "Trà Vinh",
}

TYPE_SCHEMA = {
    "accommodation": "LodgingBusiness",
    "attraction": "TouristAttraction",
    "cafe": "CafeOrCoffeeShop",
    "craft_village": "LocalBusiness",
    "dish": "FoodEstablishment",
    "drink": "Product",
    "economy": "LocalBusiness",
    "event": "Event",
    "experience": "TouristAttraction",
    "facility": "CivicStructure",
    "history": "LandmarksOrHistoricalBuildings",
    "itinerary": "TouristTrip",
    "nature": "TouristAttraction",
    "organization": "Organization",
    "person": "Person",
    "place": "Place",
    "product": "Product",
    "restaurant": "Restaurant",
}

# Maps entity type -> existing catalog/list route used as the breadcrumb's
# "type" tier. Kept in sync with web-nuxt/pages/dia-diem/[id].vue TYPE_BREADCRUMB
# so on-page and JSON-LD breadcrumbs point to the same real routes.
TYPE_BREADCRUMB_PATH = {
    "product": "/san-pham",
    "experience": "/du-lich",
    "attraction": "/du-lich",
    "nature": "/du-lich",
    "history": "/du-lich",
    "dish": "/du-lich",
    "drink": "/san-pham",
    "craft_village": "/du-lich",
    "accommodation": "/luu-tru",
    "event": "/le-hoi",
    "organization": "/danh-ba",
    "place": "/xa-phuong",
}

TYPE_BREADCRUMB_LABEL = {
    "product": "Sản phẩm",
    "experience": "Du lịch",
    "attraction": "Du lịch",
    "nature": "Du lịch",
    "history": "Du lịch",
    "dish": "Du lịch",
    "drink": "Sản phẩm",
    "craft_village": "Du lịch",
    "accommodation": "Lưu trú",
    "event": "Lễ hội",
    "organization": "Danh bạ",
    "place": "Xã phường",
}

# Catalog collections served as ItemList JSON-LD. Each maps a public route to
# the set of entity types it lists, plus SEO/GEO name + description. Pages exist
# at web-nuxt/pages/{du-lich,ocop,san-pham,luu-tru,le-hoi}.vue.
COLLECTIONS: dict[str, dict[str, Any]] = {
    "du-lich": {
        "types": {"experience", "attraction", "nature", "craft_village", "history", "dish"},
        "name": "Du lịch — Trải nghiệm miền Tây",
        "description": (
            "Khám phá điểm tham quan, trải nghiệm, vườn cây trái, làng nghề và "
            "di tích ở Vĩnh Long, Bến Tre, Trà Vinh."
        ),
    },
    "ocop": {
        "types": {"product", "dish"},
        "name": "Sản phẩm OCOP — Mỗi xã một sản phẩm",
        "description": (
            "Sản phẩm OCOP chất lượng cao từ 3 vùng: đặc sản, thủ công mỹ nghệ, "
            "ẩm thực địa phương."
        ),
        # OCOP only lists products/dishes carrying an OCOP rating.
        "require_attr": "ocop",
    },
    "san-pham": {
        "types": {"product", "dish", "drink"},
        "name": "Đặc sản & Sản phẩm địa phương",
        "description": (
            "Các sản phẩm đặc trưng của vùng đất miền Tây: đặc sản, thủ công mỹ "
            "nghệ, ẩm thực và đồ uống địa phương."
        ),
    },
    "luu-tru": {
        "types": {"accommodation"},
        "name": "Lưu trú & Nơi ở",
        "description": "Khách sạn, homestay, resort, nhà vườn lưu trú ở Vĩnh Long, Bến Tre, Trà Vinh.",
    },
    "le-hoi": {
        "types": {"event"},
        "name": "Lễ hội & Sự kiện",
        "description": "Lễ hội truyền thống, sự kiện cộng đồng, ngày hội đặc sắc quanh năm.",
    },
}

DETAIL_PRIORITY = {
    "attraction": "0.9",
    "experience": "0.8",
    "product": "0.8",
    "history": "0.8",
    "nature": "0.8",
    "event": "0.7",
    "dish": "0.7",
    "craft_village": "0.7",
    "accommodation": "0.7",
    "person": "0.6",
    "organization": "0.6",
    "itinerary": "0.6",
}

CORE_PAGES = [
    ("/", "daily", "1.0"),
    ("/du-lich", "weekly", "0.9"),
    ("/san-pham", "weekly", "0.9"),
    ("/ocop", "weekly", "0.8"),
    ("/luu-tru", "weekly", "0.8"),
    ("/le-hoi", "weekly", "0.8"),
    ("/su-kien", "weekly", "0.7"),
    ("/theo-mua", "weekly", "0.8"),
    ("/ban-do", "weekly", "0.7"),
    ("/lich-trinh", "weekly", "0.8"),
    ("/tuyen-duong", "weekly", "0.7"),
    ("/tao-lich-trinh", "monthly", "0.6"),
    ("/danh-ba", "monthly", "0.7"),
    ("/tim-kiem", "monthly", "0.5"),
    ("/cong-dong", "daily", "0.6"),
]

GUIDE_PAGES = [
    ("/kham-pha/am-thuc", "weekly", "0.8"),
    ("/kham-pha/thien-nhien", "weekly", "0.8"),
    ("/kham-pha/van-hoa", "weekly", "0.8"),
    ("/kham-pha/lang-nghe", "weekly", "0.8"),
    ("/kham-pha/mua-sam", "weekly", "0.8"),
]

SITEMAP_DOCS = [
    "/sitemap-pages.xml",
    "/sitemap-entities.xml",
    "/sitemap-itineraries.xml",
    "/sitemap-guides.xml",
    "/sitemap-media.xml",
]

_data: dict[str, Any] | None = None
_data_mtime_ns: int | None = None
_by_id_cache: dict[str, dict[str, Any]] | None = None
_by_id_cache_key: int | None = None
_sitemap_cache: dict[tuple[str, int, int, str], str] | None = None


def _load() -> dict[str, Any]:
    global _data, _data_mtime_ns, _by_id_cache, _by_id_cache_key, _sitemap_cache
    if _data is not None and _data_mtime_ns is None:
        _data.setdefault("entities", [])
        _data.setdefault("relationships", [])
        _data.setdefault("itineraries", [])
        return _data
    mtime_ns = DATA_PATH.stat().st_mtime_ns
    if _data is None or _data_mtime_ns != mtime_ns:
        _data = json.loads(DATA_PATH.read_text(encoding="utf-8-sig"))
        _data.setdefault("entities", [])
        _data.setdefault("relationships", [])
        _data.setdefault("itineraries", [])
        _data_mtime_ns = mtime_ns
        _by_id_cache = None
        _by_id_cache_key = None
        _sitemap_cache = None
    return _data


def _by_id(data: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    global _by_id_cache, _by_id_cache_key
    data = data or _load()
    data_key = id(data)
    if _by_id_cache is None or _by_id_cache_key != data_key:
        _by_id_cache = {str(e.get("id")): e for e in data["entities"] if isinstance(e, dict) and e.get("id")}
        _by_id_cache_key = data_key
    return _by_id_cache


def _is_valid_url(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    parsed = urlparse(value.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _is_external_url(url: Any) -> bool:
    """Valid http(s) URL that is NOT our own site (self-citation is not a source)."""
    if not _is_valid_url(url):
        return False
    u = str(url).lower()
    return ("//vinhlong360.vn" not in u) and ("//www.vinhlong360.vn" not in u)


def _source_info(entity: dict[str, Any]) -> tuple[str | None, str | None]:
    source = entity.get("source")
    if isinstance(source, list):  # source stored as a list of {title,url,maps}; use the first
        source = source[0] if source else None
    if isinstance(source, str):
        return (source, source if _is_external_url(source) else None)
    if isinstance(source, dict):
        url = source.get("url")
        return (source.get("title") or source.get("name") or None, url if _is_external_url(url) else None)
    return (None, None)


def parse_coordinates(value: Any) -> tuple[float, float] | None:
    for _ in range(3):
        if not isinstance(value, str):
            break
        try:
            value = json.loads(value)
        except Exception:
            return None
    if isinstance(value, dict):
        value = [value.get("lat", value.get("latitude")), value.get("lng", value.get("lon", value.get("longitude")))]
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        return None
    try:
        lat = float(value[0])
        lng = float(value[1])
    except (TypeError, ValueError):
        return None
    if abs(lat) <= 90 and abs(lng) <= 180:
        return (lat, lng)
    if abs(lng) <= 90 and abs(lat) <= 180:
        return (lng, lat)
    return None


def _entity_area(entity: dict[str, Any], by_id: dict[str, dict[str, Any]]) -> str | None:
    area = entity.get("area")
    if area:
        return str(area)
    place_id = entity.get("placeId")
    place = by_id.get(str(place_id)) if place_id else None
    if place and place.get("area"):
        return str(place["area"])
    return None


def _entity_url(entity_id: str) -> str:
    return f"{SITE}/dia-diem/{quote(entity_id, safe='-_~')}"


def _itinerary_url(itinerary_id: str) -> str:
    return f"{SITE}/lich-trinh/{quote(itinerary_id, safe='-_~')}"


def _safe_date(value: Any, fallback: str) -> str:
    if isinstance(value, str) and re.match(r"^\d{4}-\d{2}-\d{2}$", value.strip()):
        return value.strip()
    return fallback


def _same_as_values(entity: dict[str, Any]) -> list[str]:
    values: list[str] = []
    attrs = entity.get("attributes") if isinstance(entity.get("attributes"), dict) else {}
    website = attrs.get("website") if attrs else None
    if _is_valid_url(website):
        values.append(str(website))
    _title, source_url = _source_info(entity)
    if source_url and source_url not in values:
        values.append(source_url)
    return values


def _build_image_objects(
    images: Any, entity_name: str, attrs: dict[str, Any]
) -> list[dict[str, Any]]:
    """Build a schema.org ImageObject[] from real image URLs only.

    B6: never fabricate attribution. We only attach ``author``/``license``/
    ``copyrightHolder`` when those values are actually present on the entity's
    attributes (image_author / image_license / image_credit). Entities with no
    real ``images`` (the common case today) produce an empty list and the
    caller falls back to leaving image off entirely.
    """
    if not isinstance(images, list):
        images = [images] if images else []
    author = attrs.get("image_author") or attrs.get("image_credit")
    license_url = attrs.get("image_license")
    out: list[dict[str, Any]] = []
    for idx, img_url in enumerate(images):
        if not isinstance(img_url, str) or not img_url.startswith("http"):
            continue
        obj: dict[str, Any] = {
            "@type": "ImageObject",
            "url": img_url,
            "contentUrl": img_url,
            "name": f"{entity_name} — {idx + 1}" if entity_name else None,
        }
        if isinstance(author, str) and author.strip():
            obj["author"] = author.strip()
            obj["copyrightHolder"] = author.strip()
        if isinstance(license_url, str) and license_url.strip():
            obj["license"] = license_url.strip()
        out.append({k: v for k, v in obj.items() if v not in (None, "", [], {})})
    return out


def _build_breadcrumb(entity: dict[str, Any], by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """BreadcrumbList for an entity detail page.

    Tiers: Trang chủ > Type (catalog route) > Khu vực (if known) > Entity.
    The type tier reuses real catalog routes (TYPE_BREADCRUMB_PATH) so the
    JSON-LD breadcrumb matches the on-page breadcrumb in dia-diem/[id].vue and
    never links to a non-existent route.
    """
    entity_id = str(entity.get("id"))
    items: list[dict[str, Any]] = [
        {"@type": "ListItem", "position": 1, "name": "Trang chủ", "item": f"{SITE}/"},
    ]
    etype = str(entity.get("type")) if entity.get("type") else None
    type_path = TYPE_BREADCRUMB_PATH.get(etype) if etype else None
    type_label = TYPE_BREADCRUMB_LABEL.get(etype) if etype else None
    if type_path and type_label:
        items.append({
            "@type": "ListItem",
            "position": len(items) + 1,
            "name": type_label,
            "item": f"{SITE}{type_path}",
        })
    area = _entity_area(entity, by_id)
    if area:
        items.append({
            "@type": "ListItem",
            "position": len(items) + 1,
            "name": AREA_NAMES.get(area, area),
            "item": f"{SITE}/khu-vuc/{quote(area, safe='-_~')}",
        })
    items.append({
        "@type": "ListItem",
        "position": len(items) + 1,
        "name": entity.get("name") or entity_id,
        "item": _entity_url(entity_id),
    })
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": items,
    }


def build_entity_jsonld(entity: dict[str, Any], by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    schema_type = TYPE_SCHEMA.get(str(entity.get("type")), "Thing")
    entity_id = str(entity.get("id"))
    area = _entity_area(entity, by_id)
    place = by_id.get(str(entity.get("placeId"))) if entity.get("placeId") else None
    attrs = entity.get("attributes") if isinstance(entity.get("attributes"), dict) else {}
    source_title, source_url = _source_info(entity)

    ld: dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": schema_type,
        "name": entity.get("name") or entity_id,
        "url": _entity_url(entity_id),
    }

    if entity.get("summary"):
        ld["description"] = entity["summary"]
    if entity.get("images"):
        # B6: emit ImageObject[] (with attribution when available) only when
        # real image URLs exist; otherwise leave image off entirely.
        image_objects = _build_image_objects(entity["images"], ld["name"], attrs)
        if image_objects:
            ld["image"] = image_objects

    coordinates = parse_coordinates(entity.get("coordinates") or entity.get("coords"))
    if coordinates:
        lat, lng = coordinates
        ld["geo"] = {"@type": "GeoCoordinates", "latitude": lat, "longitude": lng}

    if area or place or attrs.get("address"):
        address: dict[str, Any] = {"@type": "PostalAddress", "addressCountry": "VN"}
        if attrs.get("address"):
            address["streetAddress"] = attrs["address"]
        if place:
            address["addressLocality"] = place.get("name")
        if area:
            address["addressRegion"] = AREA_NAMES.get(area, area)
        ld["address"] = address

    same_as = _same_as_values(entity)
    if same_as:
        ld["sameAs"] = same_as if len(same_as) > 1 else same_as[0]
    if source_url:
        ld["citation"] = {"@type": "CreativeWork", "name": source_title or source_url, "url": source_url}

    if attrs.get("phone"):
        ld["telephone"] = attrs["phone"]
    if attrs.get("hours"):
        ld["openingHours"] = attrs["hours"]

    if schema_type == "Product":
        if attrs.get("price"):
            price_digits = re.sub(r"[^0-9]", "", str(attrs["price"]))
            price_value = price_digits if price_digits else str(attrs["price"])
            if price_value.strip():
                ld["offers"] = {
                    "@type": "Offer",
                    "price": price_value,
                    "priceCurrency": "VND",
                    "availability": "https://schema.org/InStock",
                }
        if attrs.get("ocop"):
            ld["brand"] = {"@type": "Brand", "name": f"OCOP {attrs['ocop']}"}

    if schema_type == "Event":
        # P1-6: data thực dùng date_start/date_end (public_api) — trước chỉ đọc startDate camelCase
        date_value = (attrs.get("startDate") or attrs.get("date_start")
                      or attrs.get("date") or entity.get("startDate"))
        if date_value:
            ld["startDate"] = date_value
        end_value = attrs.get("endDate") or attrs.get("date_end") or entity.get("endDate")
        if end_value:
            ld["endDate"] = end_value
        if place:
            ld["location"] = {"@type": "Place", "name": place.get("name"), "address": ld.get("address")}

    if schema_type == "Person" and attrs.get("role"):
        ld["jobTitle"] = attrs["role"]

    ld["breadcrumb"] = _build_breadcrumb(entity, by_id)

    return {key: value for key, value in ld.items() if value not in (None, "", [], {})}


@router.get("/seo/jsonld/{entity_id}")
def entity_jsonld(entity_id: str):
    data = _load()
    by_id = _by_id(data)
    entity = by_id.get(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="not found")
    return build_entity_jsonld(entity, by_id)


def _is_public(entity: dict[str, Any]) -> bool:
    """An entity is listable in public collection schema unless it is explicitly
    provisional or explicitly marked verified=False (Track-H: only surface
    moderated public entities)."""
    if entity.get("status") == "provisional":
        return False
    if entity.get("verified") is False:
        return False
    return True


def build_collection_jsonld(collection_type: str, data: dict[str, Any]) -> dict[str, Any] | None:
    """ItemList JSON-LD for a catalog collection route, or None if unknown."""
    collection = COLLECTIONS.get(collection_type)
    if not collection:
        return None
    types = collection["types"]
    require_attr = collection.get("require_attr")
    items: list[dict[str, Any]] = []
    for e in data.get("entities", []):
        if not isinstance(e, dict) or e.get("type") not in types or not e.get("id"):
            continue
        if not _is_public(e):
            continue
        if require_attr:
            attrs = e.get("attributes") if isinstance(e.get("attributes"), dict) else {}
            if not attrs.get(require_attr):
                continue
        items.append(e)

    items.sort(key=lambda e: (-float(e.get("confidence") or 0.5), str(e.get("name") or "")))
    items = items[:100]

    elements: list[dict[str, Any]] = []
    for idx, e in enumerate(items):
        element: dict[str, Any] = {
            "@type": "ListItem",
            "position": idx + 1,
            "name": e.get("name") or str(e.get("id")),
            "url": _entity_url(str(e.get("id"))),
        }
        summary = e.get("summary")
        if isinstance(summary, str) and summary.strip():
            element["description"] = summary.strip()[:200]
        elements.append(element)

    return {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": collection["name"],
        "description": collection["description"],
        "url": f"{SITE}/{collection_type}",
        "numberOfItems": len(elements),
        "itemListElement": elements,
    }


@router.get("/seo/jsonld/collection/{collection_type}")
def collection_jsonld(collection_type: str):
    data = _load()
    result = build_collection_jsonld(collection_type, data)
    if result is None:
        raise HTTPException(status_code=404, detail="not found")
    return result


def _url_xml(loc: str, *, changefreq: str, priority: str, lastmod: str | None = None) -> str:
    parts = ["  <url>", f"    <loc>{xml_escape(loc)}</loc>"]
    if lastmod:
        parts.append(f"    <lastmod>{xml_escape(lastmod)}</lastmod>")
    parts.append(f"    <changefreq>{xml_escape(changefreq)}</changefreq>")
    parts.append(f"    <priority>{xml_escape(priority)}</priority>")
    parts.append("  </url>")
    return "\n".join(parts)


@router.get("/sitemap.xml", response_class=Response)
def sitemap():
    global _sitemap_cache
    data = _load()
    now = datetime.now(UTC).strftime("%Y-%m-%d")
    mtime_ns = _data_mtime_ns or 0
    data_key = id(data)
    if _sitemap_cache and _sitemap_cache[0] == mtime_ns and _sitemap_cache[1] == data_key and _sitemap_cache[2] == now:
        return Response(
            content=_sitemap_cache[3],
            media_type="application/xml",
            headers={"Cache-Control": "public, max-age=300, stale-while-revalidate=600"},
        )
    urls: list[str] = []

    for path, changefreq, priority in CORE_PAGES:
        urls.append(_url_xml(f"{SITE}{path}", changefreq=changefreq, priority=priority, lastmod=now))
    for area in AREA_NAMES:
        urls.append(_url_xml(f"{SITE}/khu-vuc/{area}", changefreq="weekly", priority="0.8", lastmod=now))

    for entity in data.get("entities", []):
        if not isinstance(entity, dict) or entity.get("type") != "place" or not entity.get("id"):
            continue
        urls.append(_url_xml(
            f"{SITE}/xa-phuong/{quote(str(entity['id']))}",
            changefreq="monthly",
            priority="0.6",
            lastmod=now,
        ))

    seen: set[str] = set()
    for entity in data.get("entities", []):
        if not isinstance(entity, dict) or not entity.get("id") or entity.get("type") == "place":
            continue
        if not _is_public(entity):  # P1-7: KHÔNG đưa entity provisional/chưa-verify vào sitemap
            continue
        loc = _entity_url(str(entity["id"]))
        if loc in seen:
            continue
        seen.add(loc)
        urls.append(_url_xml(
            loc,
            changefreq="weekly",
            priority=DETAIL_PRIORITY.get(str(entity.get("type")), "0.5"),
            lastmod=_safe_date(entity.get("updatedAt"), now),
        ))

    for itinerary in data.get("itineraries", []):
        if not isinstance(itinerary, dict) or not itinerary.get("id"):
            continue
        urls.append(_url_xml(
            _itinerary_url(str(itinerary["id"])),
            changefreq="monthly",
            priority="0.7",
            lastmod=_safe_date(itinerary.get("updatedAt"), now),
        ))

    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    xml += "\n".join(urls)
    xml += "\n</urlset>"
    _sitemap_cache = (mtime_ns, data_key, now, xml)
    return Response(
        content=xml,
        media_type="application/xml",
        headers={"Cache-Control": "public, max-age=300, stale-while-revalidate=600"},
    )


@router.get("/sitemap-media.xml", response_class=Response)
def sitemap_media():
    """GĐ8.5: image sitemap — entity detail URLs with their image(s) so Google
    Images can index them. Auto-populates as entities gain images (GĐ8.2/8.4)."""
    data = _load()
    urls: list[str] = []
    for entity in data.get("entities", []):
        if not isinstance(entity, dict) or not entity.get("id") or entity.get("type") == "place":
            continue
        if not _is_public(entity):
            continue
        imgs = entity.get("images")
        if not isinstance(imgs, list) or not imgs:
            continue
        loc = _entity_url(str(entity["id"]))
        tags = ""
        for img in imgs[:20]:
            if isinstance(img, str) and img.startswith("http"):
                tags += f"\n    <image:image><image:loc>{xml_escape(img)}</image:loc></image:image>"
        if tags:
            urls.append(f"  <url>\n    <loc>{xml_escape(loc)}</loc>{tags}\n  </url>")

    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += ('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
            'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n')
    xml += "\n".join(urls)
    xml += "\n</urlset>"
    return Response(
        content=xml,
        media_type="application/xml",
        headers={"Cache-Control": "public, max-age=600, stale-while-revalidate=1200"},
    )


@router.get("/robots.txt", response_class=PlainTextResponse)
def robots():
    return f"""User-agent: *
Allow: /
Disallow: /admin
Disallow: /admin-api
Disallow: /tim-kiem

User-agent: GPTBot
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Google-Extended
Allow: /

Sitemap: {SITE}/sitemap.xml
Sitemap: {SITE}/sitemap-media.xml
"""
