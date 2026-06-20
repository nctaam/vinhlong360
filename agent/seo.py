"""
vinhlong360 SEO endpoints: JSON-LD, sitemap.xml, robots.txt.

The SEO layer reads from web/data.json because that file remains the
moderated public source of truth. Helpers are intentionally defensive so
older coordinate/source shapes do not break structured data endpoints.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse
from xml.sax.saxutils import escape as xml_escape

from fastapi import APIRouter
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
    "craft_village": "LocalBusiness",
    "dish": "FoodEstablishment",
    "drink": "Product",
    "economy": "LocalBusiness",
    "event": "Event",
    "experience": "TouristAttraction",
    "history": "LandmarksOrHistoricalBuildings",
    "itinerary": "TouristTrip",
    "nature": "TouristAttraction",
    "organization": "Organization",
    "person": "Person",
    "place": "Place",
    "product": "Product",
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
        ld["image"] = entity["images"] if isinstance(entity["images"], list) else [entity["images"]]

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
            ld["offers"] = {
                "@type": "Offer",
                "price": re.sub(r"[^0-9]", "", str(attrs["price"])) or str(attrs["price"]),
                "priceCurrency": "VND",
                "availability": "https://schema.org/InStock",
            }
        if attrs.get("ocop"):
            ld["brand"] = {"@type": "Brand", "name": f"OCOP {attrs['ocop']}"}

    if schema_type == "Event":
        date_value = attrs.get("startDate") or attrs.get("date") or entity.get("startDate")
        if date_value:
            ld["startDate"] = date_value
        if attrs.get("endDate") or entity.get("endDate"):
            ld["endDate"] = attrs.get("endDate") or entity.get("endDate")
        if place:
            ld["location"] = {"@type": "Place", "name": place.get("name"), "address": ld.get("address")}

    if schema_type == "Person" and attrs.get("role"):
        ld["jobTitle"] = attrs["role"]

    return {key: value for key, value in ld.items() if value not in (None, "", [], {})}


@router.get("/seo/jsonld/{entity_id}")
def entity_jsonld(entity_id: str):
    data = _load()
    by_id = _by_id(data)
    entity = by_id.get(entity_id)
    if not entity:
        return {"error": "not found"}
    return build_entity_jsonld(entity, by_id)


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
