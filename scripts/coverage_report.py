#!/usr/bin/env python3
"""Data coverage metrics for the VinhLong360 knowledge dataset.

Computes the percentage of entities (overall + per type) that carry each of a
set of "richness" fields:

  * images        — at least one real photo URL in ``images[]``
  * summary       — a non-empty summary string
  * external_source — at least one external (non vinhlong360.vn) source URL
  * coordinates   — valid lat/lng coordinates
  * placeId       — a non-empty placeId
  * area          — a non-empty area

This is an **informational** report. It never mutates data and always exits 0,
so it can run as a non-blocking CI step. Use ``--json`` for machine output.

The coordinate/source-detection helpers intentionally mirror the logic in
``scripts/validate_data.py`` so the two reports agree; this script is fully
standalone (no import of validate_data) to keep it side-effect free in CI.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = ROOT / "web" / "data.json"

# Fields tracked, in display order. (key suffix -> human label)
FIELDS = ("images", "summary", "external_source", "coordinates", "placeId", "area")


def _configure_output() -> None:
    # Vietnamese entity names may appear in error paths; force UTF-8 on Windows.
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass


def _parse_json_string(value: Any) -> Any:
    """Decode up to 4 layers of accidental JSON-string wrapping (matches validate_data)."""
    current = value
    for _ in range(4):
        if not isinstance(current, str):
            return current
        text = current.strip()
        if not text:
            return None
        try:
            current = json.loads(text)
        except json.JSONDecodeError:
            return current
    return current


def normalized_coordinates(value: Any) -> list[float] | None:
    """Return [lat, lng] if value is valid coordinates, else None.

    Mirrors scripts/validate_data.py::normalized_coordinates so coverage and
    validation agree on what counts as "has coordinates".
    """
    value = _parse_json_string(value)
    if isinstance(value, dict):
        lat = value.get("lat", value.get("latitude"))
        lng = value.get("lng", value.get("lon", value.get("longitude")))
        value = [lat, lng]
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        return None
    try:
        lat = float(value[0])
        lng = float(value[1])
    except (TypeError, ValueError):
        return None
    if -90 <= lat <= 90 and -180 <= lng <= 180:
        return [lat, lng]
    if -180 <= lat <= 180 and -90 <= lng <= 90:
        # Common imported shape is [lng, lat]; contract requires [lat, lng].
        return [lng, lat]
    return None


def has_real_photo(images: Any) -> bool:
    """True if images[] holds at least one usable photo URL.

    Accepts the current shape (list of strings) and a forward-compatible shape
    (list of dicts with a ``url`` key, e.g. once attribution metadata ships per
    B6). Empty list / None / non-list -> False.
    """
    if not isinstance(images, list):
        return False
    for img in images:
        url = None
        if isinstance(img, str):
            url = img
        elif isinstance(img, dict):
            url = img.get("url") or img.get("src")
        if isinstance(url, str) and url.strip().lower().startswith("http"):
            return True
    return False


def is_external_source(source: Any) -> bool:
    """True if source carries at least one external (non vinhlong360.vn) URL.

    Handles the data shapes seen in data.json: a list of dicts ({url|maps|...}),
    a list of strings, a bare dict, or a bare string.
    """
    if not source:
        return False
    sources = source if isinstance(source, list) else [source]
    for s in sources:
        urls: list[Any] = []
        if isinstance(s, dict):
            urls = [s.get("url"), s.get("maps")]
        elif isinstance(s, str):
            urls = [s]
        for url in urls:
            if not isinstance(url, str):
                continue
            lower = url.strip().lower()
            if lower.startswith("http") and "vinhlong360" not in lower:
                return True
    return False


def load_data(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def _empty_counts() -> dict[str, int]:
    counts = {"total": 0}
    for field in FIELDS:
        counts[f"has_{field}"] = 0
    return counts


def compute_coverage(data: dict[str, Any]) -> dict[str, Any]:
    """Return coverage percentages overall and per entity type.

    Pure function (no I/O, no mutation) so callers can reuse it.
    """
    entities = [e for e in data.get("entities", []) if isinstance(e, dict)]

    by_type: dict[str, dict[str, int]] = defaultdict(_empty_counts)
    overall = _empty_counts()
    overall["total"] = len(entities)

    for entity in entities:
        etype = entity.get("type") or "unknown"
        bucket = by_type[etype]
        bucket["total"] += 1

        checks = {
            "images": has_real_photo(entity.get("images")),
            "summary": bool(
                isinstance(entity.get("summary"), str) and entity.get("summary", "").strip()
            ),
            "external_source": is_external_source(entity.get("source")),
            "coordinates": normalized_coordinates(entity.get("coordinates")) is not None,
            "placeId": bool(entity.get("placeId")),
            "area": bool(entity.get("area")),
        }
        for field, ok in checks.items():
            if ok:
                bucket[f"has_{field}"] += 1
                overall[f"has_{field}"] += 1

    def to_pct(counts: dict[str, int]) -> dict[str, Any]:
        total = counts["total"] or 1
        out: dict[str, Any] = {"total": counts["total"]}
        for field in FIELDS:
            out[f"{field}_pct"] = round(100 * counts[f"has_{field}"] / total, 1)
            out[f"{field}_count"] = counts[f"has_{field}"]
        return out

    return {
        "overall": to_pct(overall),
        "by_type": {etype: to_pct(c) for etype, c in sorted(by_type.items())},
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def _print_field_lines(stats: dict[str, Any], indent: str) -> None:
    for field in FIELDS:
        pct = stats.get(f"{field}_pct")
        count = stats.get(f"{field}_count")
        total = stats.get("total")
        print(f"{indent}{field:<16} {pct:>5}%  ({count}/{total})")


def print_report(coverage: dict[str, Any]) -> None:
    print("VinhLong360 data coverage")
    print("=========================")
    overall = coverage.get("overall", {})
    print(f"\nOverall ({overall.get('total', 0)} entities):")
    _print_field_lines(overall, "  ")

    print("\nBy entity type:")
    for etype, stats in coverage.get("by_type", {}).items():
        print(f"  {etype} ({stats.get('total', 0)} entities):")
        _print_field_lines(stats, "    ")

    print(f"\ngenerated_at: {coverage.get('generated_at')}")


def main(argv: list[str] | None = None) -> int:
    _configure_output()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA, help="Path to data.json")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON report")
    args = parser.parse_args(argv)

    try:
        data = load_data(args.data)
    except FileNotFoundError:
        # Informational tool: never break the build just because data is absent.
        print(f"coverage_report: data file not found: {args.data}", file=sys.stderr)
        return 0
    except Exception as exc:  # noqa: BLE001 — stay non-blocking in CI
        print(f"coverage_report: could not load {args.data}: {exc}", file=sys.stderr)
        return 0

    coverage = compute_coverage(data)

    if args.json:
        print(json.dumps(coverage, ensure_ascii=False, indent=2))
    else:
        print_report(coverage)

    return 0  # always 0 — informational, non-blocking


if __name__ == "__main__":
    raise SystemExit(main())
