"""
Generate SEO metadata (slug + meta_description) for entities in web/data.json.

Produces a JSON patch file mapping entity ID -> {slug, meta_description}.

Slug generation: Vietnamese diacritics stripped via unicodedata.normalize (NFD),
lowercased, spaces -> hyphens, special chars removed.

Usage:
    python scripts/generate_seo_meta.py                                 # default output
    python scripts/generate_seo_meta.py --output seo.json               # custom output
    python scripts/generate_seo_meta.py --max-desc-length 120           # shorter descriptions
    python scripts/generate_seo_meta.py --data path/to.json --json      # JSON stats
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_JSON = ROOT / "web" / "data.json"
DEFAULT_OUTPUT = ROOT / "scripts" / "_seo_patch.json"


def _vietnamese_to_slug(text: str) -> str:
    """Convert Vietnamese text to a URL-safe slug.

    Steps:
      1. NFD normalize to decompose accented characters
      2. Strip combining characters (diacritics)
      3. Handle special Vietnamese characters (d-bar)
      4. Lowercase
      5. Replace spaces/underscores with hyphens
      6. Strip non-alphanumeric (except hyphens)
      7. Collapse multiple hyphens
      8. Strip leading/trailing hyphens
    """
    # NFD decomposition splits base characters from combining marks
    normalized = unicodedata.normalize("NFD", text)

    # Remove combining characters (diacritics: accents, hooks, tildes, dots below)
    stripped = "".join(
        ch for ch in normalized
        if unicodedata.category(ch) != "Mn"
    )

    # Handle special Vietnamese: d-bar (d) -> d, D-bar (D) -> D
    stripped = stripped.replace("đ", "d").replace("Đ", "D")

    # Lowercase
    slug = stripped.lower()

    # Replace whitespace and underscores with hyphens
    slug = re.sub(r"[\s_]+", "-", slug)

    # Remove everything except alphanumeric and hyphens
    slug = re.sub(r"[^a-z0-9-]", "", slug)

    # Collapse multiple hyphens
    slug = re.sub(r"-{2,}", "-", slug)

    # Strip leading/trailing hyphens
    slug = slug.strip("-")

    return slug


def _make_meta_description(summary: str, max_length: int) -> str:
    """Create a meta description from the entity summary.

    Truncates at *max_length* characters, breaking at the last word boundary,
    and appends "..." if truncated.
    """
    if not summary:
        return ""

    # Clean up whitespace
    clean = re.sub(r"\s+", " ", summary).strip()

    if len(clean) <= max_length:
        return clean

    # Truncate at word boundary
    truncated = clean[:max_length]
    last_space = truncated.rfind(" ")
    if last_space > max_length * 0.6:  # only break at word if not too far back
        truncated = truncated[:last_space]

    return truncated.rstrip(",.;:!? ") + "..."


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate SEO metadata (slug + meta_description) for entities."
    )
    parser.add_argument(
        "--data",
        default=str(DATA_JSON),
        help="path to data.json (default: web/data.json)",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="output JSON file (default: scripts/_seo_patch.json)",
    )
    parser.add_argument(
        "--max-desc-length",
        type=int,
        default=155,
        help="maximum meta_description length (default: 155)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_stats",
        help="output stats as JSON to stdout",
    )
    args = parser.parse_args()

    data_path = Path(args.data)
    if not data_path.exists():
        print(f"[seo] ERROR: {data_path} not found", file=sys.stderr)
        return 1

    with open(data_path, encoding="utf-8") as f:
        data = json.load(f)

    entities = data.get("entities", [])
    if not entities:
        print("[seo] WARNING: no entities found in data", file=sys.stderr)
        return 1

    patch: dict[str, dict[str, str]] = {}
    stats = {
        "total_entities": len(entities),
        "processed": 0,
        "slugs_generated": 0,
        "descriptions_generated": 0,
        "descriptions_truncated": 0,
        "empty_summary": 0,
        "empty_name": 0,
        "slug_collisions": 0,
        "by_type": {},
    }

    seen_slugs: dict[str, list[str]] = {}

    for entity in entities:
        eid = entity.get("id", "")
        name = entity.get("name", "")
        summary = entity.get("summary", "")
        etype = entity.get("type", "unknown")

        if not eid:
            continue

        stats["processed"] += 1
        stats["by_type"][etype] = stats["by_type"].get(etype, 0) + 1

        entry: dict[str, str] = {}

        # Generate slug
        if name:
            slug = _vietnamese_to_slug(name)
            if slug:
                entry["slug"] = slug
                stats["slugs_generated"] += 1

                # Track collisions
                seen_slugs.setdefault(slug, []).append(eid)
        else:
            stats["empty_name"] += 1

        # Generate meta description
        if summary:
            desc = _make_meta_description(summary, args.max_desc_length)
            if desc:
                entry["meta_description"] = desc
                stats["descriptions_generated"] += 1
                if desc.endswith("..."):
                    stats["descriptions_truncated"] += 1
        else:
            stats["empty_summary"] += 1

        if entry:
            patch[eid] = entry

    # Count slug collisions
    collisions = {slug: ids for slug, ids in seen_slugs.items() if len(ids) > 1}
    stats["slug_collisions"] = len(collisions)

    # Write patch file
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(patch, f, ensure_ascii=False, indent=2)

    # Report
    if args.json_stats:
        report = {"stats": stats}
        if collisions:
            report["slug_collisions"] = {
                slug: ids for slug, ids in sorted(collisions.items())[:20]
            }
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        pct_desc = (
            (stats["descriptions_generated"] / stats["total_entities"] * 100)
            if stats["total_entities"] > 0
            else 0
        )
        pct_slug = (
            (stats["slugs_generated"] / stats["total_entities"] * 100)
            if stats["total_entities"] > 0
            else 0
        )

        print(f"[seo] SEO metadata generated")
        print(f"  entities: {stats['total_entities']}")
        print(f"  processed: {stats['processed']}")
        print(f"  slugs generated: {stats['slugs_generated']} ({pct_slug:.1f}%)")
        print(f"  descriptions generated: {stats['descriptions_generated']} ({pct_desc:.1f}%)")
        print(f"  descriptions truncated: {stats['descriptions_truncated']}")
        print(f"  empty names: {stats['empty_name']}")
        print(f"  empty summaries: {stats['empty_summary']}")
        print(f"  slug collisions: {stats['slug_collisions']}")
        print(f"  output: {output_path}")

        if collisions:
            print()
            print("  Slug collisions (top 10):")
            for slug, ids in sorted(collisions.items())[:10]:
                print(f"    '{slug}': {ids}")

        print()
        print("  By type:")
        for etype, count in sorted(stats["by_type"].items(), key=lambda x: -x[1]):
            print(f"    {etype}: {count}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
