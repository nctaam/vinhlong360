"""Committed province-configuration authority shared across backend, checks, and Nuxt."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROVINCE_CONFIG_ENV = "PROVINCE_CONFIG_PATH"
_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "province.config.json"


class ProvinceConfigError(RuntimeError):
    """Raised when province configuration is missing or fails validation."""


@dataclass(frozen=True)
class ProvinceArea:
    slug: str
    name: str
    emoji: str
    icon: str
    blurb: str
    distance: str
    hub: str
    lat: float
    lon: float
    is_primary: bool


@dataclass(frozen=True)
class ProvinceConfig:
    schema_version: int
    slug: str
    province_slug: str
    province_id: str
    province_name: str
    province_full_name: str
    brand_name: str
    brand_display_name: str
    logo_suffix: str
    domain: str
    site_url: str
    contact_email: str
    zalo_handle: str
    twitter_handle: str
    esms_brandname: str
    storage_prefix: str
    weather_user_agent: str
    og_image_url: str
    tagline: str
    footer_tagline: str
    copyright: str
    alternate_name: str
    seo_title: str
    seo_description: str
    og_description: str
    json_ld_description: str
    seed_seo_description: str
    hero_subtitle: str
    chat_title: str
    chat_placeholder: str
    ward_count: int
    merged_from: tuple[str, ...]
    legacy_province_names: tuple[str, ...]
    schema_bbox: dict[str, tuple[float, float]]
    ingest_bbox_tuple: tuple[float, float, float, float]
    canonical_area_slug: str
    canonical_region_id: str
    multi_region_slug: str
    multi_region_label: str
    areas: tuple[ProvinceArea, ...]
    out_of_province_patterns: tuple[str, ...]
    out_of_province_message: str
    raw: dict[str, Any]

    @property
    def primary_area_slug(self) -> str:
        for area in self.areas:
            if area.is_primary:
                return area.slug
        return self.areas[0].slug

    @property
    def area_names(self) -> dict[str, str]:
        return {area.slug: area.name for area in self.areas}

    @property
    def itinerary_area_names(self) -> dict[str, str]:
        return {**self.area_names, self.multi_region_slug: self.multi_region_label}

    @property
    def area_coords(self) -> dict[str, dict[str, Any]]:
        return {
            area.slug: {"lat": area.lat, "lon": area.lon, "name": area.name}
            for area in self.areas
        }


_CACHE: dict[Path, tuple[int, ProvinceConfig]] = {}


def _require_str(mapping: dict[str, Any], key: str, *, context: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ProvinceConfigError(f"{context}.{key} must be a non-empty string")
    return value


def _require_int(mapping: dict[str, Any], key: str, *, minimum: int, context: str) -> int:
    value = mapping.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ProvinceConfigError(f"{context}.{key} must be an integer >= {minimum}")
    return value


def _require_str_list(mapping: dict[str, Any], key: str, *, context: str) -> tuple[str, ...]:
    value = mapping.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ProvinceConfigError(f"{context}.{key} must be a list of non-empty strings")
    return tuple(value)


def _require_mapping(mapping: dict[str, Any], key: str, *, context: str) -> dict[str, Any]:
    value = mapping.get(key)
    if not isinstance(value, dict):
        raise ProvinceConfigError(f"{context}.{key} must be an object")
    return value


def _parse_bbox_pair(pair: Any, *, name: str, low: float, high: float) -> tuple[float, float]:
    if not isinstance(pair, list) or len(pair) != 2:
        raise ProvinceConfigError(f"{name} must be [min, max]")
    a, b = pair
    if isinstance(a, bool) or isinstance(b, bool) or not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        raise ProvinceConfigError(f"{name} coordinates must be numeric")
    fa, fb = float(a), float(b)
    if fa >= fb or fa < low or fb > high:
        raise ProvinceConfigError(f"{name} out of range [{low}, {high}] or inverted")
    return (fa, fb)


def _parse_schema_bbox(raw_bbox: dict[str, Any], *, name: str) -> dict[str, tuple[float, float]]:
    return {
        "lat": _parse_bbox_pair(raw_bbox.get("lat"), name=f"{name}.lat", low=-90.0, high=90.0),
        "lng": _parse_bbox_pair(raw_bbox.get("lng"), name=f"{name}.lng", low=-180.0, high=180.0),
    }


def _parse_area(item: Any, index: int) -> ProvinceArea:
    if not isinstance(item, dict):
        raise ProvinceConfigError(f"areas.items[{index}] must be an object")
    ctx = f"areas.items[{index}]"
    lat = item.get("lat")
    lon = item.get("lon")
    if isinstance(lat, bool) or isinstance(lon, bool) or not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
        raise ProvinceConfigError(f"{ctx} lat/lon must be numeric")
    return ProvinceArea(
        slug=_require_str(item, "slug", context=ctx),
        name=_require_str(item, "name", context=ctx),
        emoji=_require_str(item, "emoji", context=ctx),
        icon=_require_str(item, "icon", context=ctx),
        blurb=_require_str(item, "blurb", context=ctx),
        distance=_require_str(item, "distance", context=ctx),
        hub=_require_str(item, "hub", context=ctx),
        lat=float(lat),
        lon=float(lon),
        is_primary=bool(item.get("isPrimary", False)),
    )


def resolve_province_config_path(path: Path | None = None) -> Path:
    if path is not None:
        return Path(path)
    env_path = os.environ.get(PROVINCE_CONFIG_ENV, "").strip()
    if env_path:
        return Path(env_path)
    return _DEFAULT_CONFIG_PATH


def _build_province_config(payload: dict[str, Any]) -> ProvinceConfig:
    if payload.get("schemaVersion") != 1:
        raise ProvinceConfigError("schemaVersion must be 1")

    identity = _require_mapping(payload, "identity", context="root")
    bounds = _require_mapping(payload, "bounds", context="root")
    areas_cfg = _require_mapping(payload, "areas", context="root")
    guards = _require_mapping(payload, "contentGuards", context="root")
    for section in ("weather", "tide", "home", "deploy"):
        _require_mapping(payload, section, context="root")
    if not isinstance(payload.get("emergencyHotlines"), list):
        raise ProvinceConfigError("root.emergencyHotlines must be a list")

    site_url = _require_str(identity, "siteUrl", context="identity")
    if not site_url.startswith("https://"):
        raise ProvinceConfigError("identity.siteUrl must start with https://")

    schema_bbox = _parse_schema_bbox(
        _require_mapping(bounds, "schemaBbox", context="bounds"),
        name="bounds.schemaBbox",
    )
    ingest_bbox = _parse_schema_bbox(
        _require_mapping(bounds, "ingestBbox", context="bounds"),
        name="bounds.ingestBbox",
    )

    raw_items = areas_cfg.get("items")
    if not isinstance(raw_items, list) or not raw_items:
        raise ProvinceConfigError("areas.items must be a non-empty list")
    areas = tuple(_parse_area(item, idx) for idx, item in enumerate(raw_items))

    og_path = _require_str(identity, "ogImagePath", context="identity")
    og_image_url = og_path if og_path.startswith("http") else f"{site_url.rstrip('/')}{og_path}"

    return ProvinceConfig(
        schema_version=1,
        slug=_require_str(identity, "slug", context="identity"),
        province_slug=_require_str(identity, "provinceSlug", context="identity"),
        province_id=_require_str(identity, "provinceId", context="identity"),
        province_name=_require_str(identity, "provinceName", context="identity"),
        province_full_name=_require_str(identity, "provinceFullName", context="identity"),
        brand_name=_require_str(identity, "brandName", context="identity"),
        brand_display_name=_require_str(identity, "brandDisplayName", context="identity"),
        logo_suffix=_require_str(identity, "logoSuffix", context="identity"),
        domain=_require_str(identity, "domain", context="identity"),
        site_url=site_url,
        contact_email=_require_str(identity, "contactEmail", context="identity"),
        zalo_handle=_require_str(identity, "zaloHandle", context="identity"),
        twitter_handle=_require_str(identity, "twitterHandle", context="identity"),
        esms_brandname=_require_str(identity, "esmsBrandname", context="identity"),
        storage_prefix=_require_str(identity, "storagePrefix", context="identity"),
        weather_user_agent=_require_str(identity, "weatherUserAgent", context="identity"),
        og_image_url=og_image_url,
        tagline=_require_str(identity, "tagline", context="identity"),
        footer_tagline=_require_str(identity, "footerTagline", context="identity"),
        copyright=_require_str(identity, "copyright", context="identity"),
        alternate_name=_require_str(identity, "alternateName", context="identity"),
        seo_title=_require_str(identity, "seoTitle", context="identity"),
        seo_description=_require_str(identity, "seoDescription", context="identity"),
        og_description=_require_str(identity, "ogDescription", context="identity"),
        json_ld_description=_require_str(identity, "jsonLdDescription", context="identity"),
        seed_seo_description=_require_str(identity, "seedSeoDescription", context="identity"),
        hero_subtitle=_require_str(identity, "heroSubtitle", context="identity"),
        chat_title=_require_str(identity, "chatTitle", context="identity"),
        chat_placeholder=_require_str(identity, "chatPlaceholder", context="identity"),
        ward_count=_require_int(identity, "wardCount", minimum=1, context="identity"),
        merged_from=_require_str_list(identity, "mergedFrom", context="identity"),
        legacy_province_names=_require_str_list(identity, "legacyProvinceNames", context="identity"),
        schema_bbox=schema_bbox,
        ingest_bbox_tuple=(*ingest_bbox["lat"], *ingest_bbox["lng"]),
        canonical_area_slug=_require_str(areas_cfg, "canonicalAreaSlug", context="areas"),
        canonical_region_id=_require_str(areas_cfg, "canonicalRegionId", context="areas"),
        multi_region_slug=_require_str(areas_cfg, "multiRegionSlug", context="areas"),
        multi_region_label=_require_str(areas_cfg, "multiRegionLabel", context="areas"),
        areas=areas,
        out_of_province_patterns=_require_str_list(guards, "outOfProvincePatterns", context="contentGuards"),
        out_of_province_message=_require_str(guards, "outOfProvinceMessage", context="contentGuards"),
        raw=payload,
    )


def load_province_config(path: Path | None = None) -> ProvinceConfig:
    """Load and validate the canonical province configuration."""
    config_path = resolve_province_config_path(path).resolve()
    try:
        stat_result = config_path.stat()
        payload = json.loads(config_path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProvinceConfigError(f"province config is unavailable or invalid: {config_path}") from exc

    cached = _CACHE.get(config_path)
    if cached is not None and cached[0] == stat_result.st_mtime_ns:
        return cached[1]

    if not isinstance(payload, dict):
        raise ProvinceConfigError("province config root must be a JSON object")

    parsed = _build_province_config(payload)
    _CACHE[config_path] = (stat_result.st_mtime_ns, parsed)
    return parsed
