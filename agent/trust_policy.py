"""Trust tiers, freshness, and privacy-safe recommendation explanations."""

from __future__ import annotations

import unicodedata
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Literal, NotRequired, TypedDict


SourceTier = Literal["official", "verified", "community", "unknown"]
FreshnessStatus = Literal["fresh", "aging", "stale", "unknown"]

FRESH_MAX_DAYS = 90
AGING_MAX_DAYS = 180

_AGE_BANDS = frozenset(
    {"under_18", "18_24", "25_34", "35_49", "50_plus", "unknown"}
)
_COMMUNITY_SOURCE_KINDS = frozenset({"review-ugc", "community-ugc"})
_DEFAULT_REASON = "Được cộng đồng quan tâm"
_EXPLICIT_REASON = "Phù hợp với sở thích bạn đã chọn"


class RecommendationExplanation(TypedDict):
    primary_reason: str
    reasons: list[str]
    region_label: NotRequired[str]
    explicit_interests: NotRequired[list[str]]
    derived_age_band: NotRequired[str]


def _parse_timestamp(value: object) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _verified_at(entity: Mapping[str, object]) -> datetime | None:
    source_freshness = _mapping(entity.get("source_freshness"))
    attributes = _mapping(entity.get("attributes"))
    for value in (
        entity.get("verified_at"),
        source_freshness.get("verified_at"),
        attributes.get("verifiedAt"),
    ):
        if parsed := _parse_timestamp(value):
            return parsed
    return None


def _updated_at(entity: Mapping[str, object]) -> datetime | None:
    source_freshness = _mapping(entity.get("source_freshness"))
    for value in (
        entity.get("updated_at"),
        source_freshness.get("updated_at"),
        entity.get("updatedAt"),
    ):
        if parsed := _parse_timestamp(value):
            return parsed
    return None


def derive_source_tier(entity: object) -> SourceTier:
    if not isinstance(entity, Mapping):
        return "unknown"
    if entity.get("official") is True:
        return "official"
    if (
        entity.get("source_class") == "user-uploaded"
        or entity.get("source_kind") in _COMMUNITY_SOURCE_KINDS
    ):
        return "community"
    if entity.get("partner_verified") is True and _verified_at(entity) is not None:
        return "verified"
    return "unknown"


def derive_freshness(
    entity: object, now: datetime | str | None = None
) -> FreshnessStatus:
    if not isinstance(entity, Mapping):
        return "unknown"
    reference = _parse_timestamp(now) if now is not None else datetime.now(timezone.utc)
    if reference is None:
        return "unknown"
    timestamp = _verified_at(entity) or _updated_at(entity)
    if timestamp is None:
        return "unknown"
    days = (reference - timestamp).days
    if days <= FRESH_MAX_DAYS:
        return "fresh"
    if days <= AGING_MAX_DAYS:
        return "aging"
    return "stale"


def _fold_text(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value.strip().lower())
    return " ".join(
        "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn").split()
    )


_SAFE_REASON_MAP = {
    "hop voi nhom noi dung ban quan tam": "Hợp với nhóm nội dung bạn quan tâm",
    "hop voi noi dung ban quan tam": "Hợp với nội dung bạn quan tâm",
    "cung khu vuc ban hay xem": "Cùng khu vực bạn quan tâm",
    "cung chu de voi noi dang xem": "Cùng chủ đề với nơi đang xem",
    "gan mach kham pha hien tai": "Gần mạch khám phá hiện tại",
    "lien quan truc tiep toi tim kiem": "Liên quan tới tìm kiếm hiện tại",
    "duoc cong dong quan tam": _DEFAULT_REASON,
    "lien quan trong ban do tri thuc": "Liên quan trong bản đồ tri thức",
    "gan nhau trong cung xa phuong": "Gần nhau trong cùng xã phường",
    "cung khu vuc kham pha": "Cùng khu vực khám phá",
    "co chu de trai nghiem gan nhau": "Có chủ đề trải nghiệm gần nhau",
    "cung nhom noi dung": "Cùng nhóm nội dung",
    "phu hop de kham pha tiep": "Phù hợp để khám phá tiếp",
}


def _safe_reasons(
    reasons: object, *, has_explicit_interests: bool
) -> list[tuple[int, str]]:
    if not isinstance(reasons, Sequence) or isinstance(reasons, (str, bytes, bytearray)):
        return []
    safe: list[tuple[int, str]] = []
    for reason in reasons:
        if not isinstance(reason, str):
            continue
        folded = _fold_text(reason)
        if folded.startswith("khop so thich "):
            text = _EXPLICIT_REASON if has_explicit_interests else "Hợp với nội dung bạn quan tâm"
            safe.append((0 if has_explicit_interests else 1, text))
            continue
        if text := _SAFE_REASON_MAP.get(folded):
            safe.append((1, text))
    return safe


def _bounded_strings(value: object, *, limit: int, max_length: int) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    result: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        normalized = item.strip()
        if not normalized or len(normalized) > max_length or normalized in result:
            continue
        result.append(normalized)
        if len(result) == limit:
            break
    return result


def build_explanation(
    entity: object,
    reasons: object,
    preference_snapshot: object,
) -> RecommendationExplanation:
    del entity  # Entity metadata is intentionally excluded from explanation output.
    preferences = _mapping(preference_snapshot)
    personalized = preferences.get("personalization_enabled") is True
    explicit_interests = (
        _bounded_strings(
            preferences.get("explicit_interests"), limit=3, max_length=64
        )
        if personalized
        else []
    )
    safe = _safe_reasons(
        reasons, has_explicit_interests=bool(explicit_interests)
    )
    safe.sort(key=lambda item: item[0])
    ordered_reasons = list(dict.fromkeys(text for _, text in safe))[:3]
    if not ordered_reasons:
        ordered_reasons = [_DEFAULT_REASON]

    explanation: RecommendationExplanation = {
        "primary_reason": ordered_reasons[0],
        "reasons": ordered_reasons,
    }
    source = preferences.get("location_source")
    location_allowed = source == "manual" or (
        source in {"gps", "ip"} and preferences.get("location_enabled") is True
    )
    region_label = preferences.get("region_label")
    if location_allowed and isinstance(region_label, str):
        normalized_region = region_label.strip()
        if normalized_region and len(normalized_region) <= 160:
            explanation["region_label"] = normalized_region
    if explicit_interests:
        explanation["explicit_interests"] = explicit_interests
    age_band = preferences.get("derived_age_band")
    if personalized and isinstance(age_band, str) and age_band in _AGE_BANDS:
        explanation["derived_age_band"] = age_band
    return explanation
