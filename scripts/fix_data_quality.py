"""
Automated data-quality fixes for web/data.json.

Detects and optionally fixes:
  1. Asymmetric "near" relationships (A->B exists but B->A missing)
  2. Entities with coords_approximate flag
  3. Entities whose summary mentions wrong province
  4. Phone numbers needing normalization (spaces, dashes, +84 prefix)
  5. Duplicate entities (same name + type + area)

IMPORTANT: When --fix is used, this script calls scripts/backup_data.py first
(Invariant B1 from CLAUDE.md).

Usage:
    python scripts/fix_data_quality.py                      # dry-run report (default)
    python scripts/fix_data_quality.py --fix                # apply fixes (backs up first)
    python scripts/fix_data_quality.py --json               # JSON report output
    python scripts/fix_data_quality.py --data path/to.json  # custom data file
"""

from __future__ import annotations

import argparse
import io
import json
import re
import subprocess
import sys
from pathlib import Path

# Ensure stdout can handle Vietnamese characters on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() not in ("utf-8", "utf8"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
DATA_JSON = ROOT / "web" / "data.json"

# Province keywords for wrong-province detection
PROVINCE_KEYWORDS: dict[str, list[str]] = {
    "vinh-long": ["Vĩnh Long", "tỉnh Vĩnh Long"],
    "ben-tre": ["Bến Tre", "tỉnh Bến Tre"],
    "tra-vinh": ["Trà Vinh", "tỉnh Trà Vinh"],
}

# VN phone regex: valid formats
VN_PHONE_RE = re.compile(r"^(\+84|0)\d{9,10}$")


def _load_data(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _save_data(path: Path, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[fix] saved {path}")


def _run_backup() -> bool:
    """Run backup_data.py (B1 invariant). Returns True on success."""
    backup_script = ROOT / "scripts" / "backup_data.py"
    if not backup_script.exists():
        print("[fix] WARNING: scripts/backup_data.py not found, skipping backup", file=sys.stderr)
        return True
    print("[fix] running backup_data.py (B1 invariant)...")
    result = subprocess.run(
        [sys.executable, str(backup_script), "--label", "pre-fix-data-quality"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"[fix] backup FAILED:\n{result.stderr}", file=sys.stderr)
        return False
    for line in result.stdout.strip().splitlines():
        print(f"  {line}")
    return True


def _rel_source(rel: dict) -> str:
    """Get relationship source (handles both 'from' and 'source' field names)."""
    return str(rel.get("from") or rel.get("from_id") or rel.get("source_id") or "")


def _rel_target(rel: dict) -> str:
    """Get relationship target (handles both 'to' and 'target' field names)."""
    return str(rel.get("to") or rel.get("to_id") or rel.get("target_id") or "")


def _rel_type(rel: dict) -> str:
    """Get relationship type."""
    return str(rel.get("type") or rel.get("rel_type") or "")


def check_asymmetric_near(
    entities: list[dict],
    relationships: list[dict],
) -> tuple[list[dict], list[dict]]:
    """Find asymmetric 'near' relationships and return (issues, fixes).

    A 'near' relationship from A->B should have a matching B->A.
    """
    entity_ids = {e["id"] for e in entities}

    # Build set of existing (source, target) pairs for 'near'
    near_pairs: set[tuple[str, str]] = set()
    for rel in relationships:
        if _rel_type(rel) == "near":
            src = _rel_source(rel)
            tgt = _rel_target(rel)
            if src and tgt:
                near_pairs.add((src, tgt))

    issues: list[dict] = []
    fixes: list[dict] = []
    for src, tgt in sorted(near_pairs):
        if (tgt, src) not in near_pairs:
            if tgt in entity_ids and src in entity_ids:
                issues.append({
                    "code": "ASYMMETRIC_NEAR",
                    "message": f"near {src} -> {tgt} exists but reverse is missing",
                    "source": src,
                    "target": tgt,
                })
                # Build the reverse relationship using the same field names as
                # the original (data.json uses "from"/"to", not "source"/"target")
                original = next(
                    (r for r in relationships
                     if _rel_type(r) == "near" and _rel_source(r) == src and _rel_target(r) == tgt),
                    None,
                )
                # Detect which field names the data uses
                if original and "from" in original:
                    reverse: dict = {"from": tgt, "to": src, "type": "near"}
                else:
                    reverse = {"source_id": tgt, "target_id": src, "type": "near"}
                if original and "attributes" in original:
                    reverse["attributes"] = dict(original["attributes"])
                fixes.append(reverse)
    return issues, fixes


def check_coords_approximate(entities: list[dict]) -> list[dict]:
    """Report entities with coords_approximate=true."""
    issues: list[dict] = []
    for e in entities:
        attrs = e.get("attributes", {})
        if isinstance(attrs, dict) and attrs.get("coords_approximate"):
            issues.append({
                "code": "COORDS_APPROXIMATE",
                "message": f"entity '{e.get('name', e['id'])}' has approximate coordinates",
                "entity_id": e["id"],
                "type": e.get("type", "unknown"),
                "area": e.get("area", "unknown"),
            })
    return issues


def check_wrong_province_summary(entities: list[dict]) -> list[dict]:
    """Report entities whose summary mentions a different province than their area."""
    issues: list[dict] = []
    for e in entities:
        area = e.get("area", "")
        summary = e.get("summary", "")
        if not area or not summary:
            continue
        for province_area, keywords in PROVINCE_KEYWORDS.items():
            if province_area == area:
                continue  # correct province
            for kw in keywords:
                if kw in summary and area in PROVINCE_KEYWORDS:
                    issues.append({
                        "code": "WRONG_PROVINCE_SUMMARY",
                        "message": (
                            f"entity '{e.get('name', e['id'])}' (area={area}) "
                            f"summary mentions '{kw}'"
                        ),
                        "entity_id": e["id"],
                        "area": area,
                        "mentioned_province": province_area,
                    })
                    break  # one report per entity per wrong province
    return issues


def fix_phone_numbers(entities: list[dict]) -> tuple[list[dict], int]:
    """Normalize phone numbers in entity attributes. Returns (issues, fix_count)."""
    issues: list[dict] = []
    fix_count = 0

    for e in entities:
        attrs = e.get("attributes", {})
        if not isinstance(attrs, dict):
            continue
        phone = attrs.get("phone", "")
        if not phone or not isinstance(phone, str):
            continue

        # Strip spaces, dashes, dots
        cleaned = re.sub(r"[\s\-.]", "", phone)
        # Convert +84 prefix to 0
        if cleaned.startswith("+84"):
            cleaned = "0" + cleaned[3:]

        if cleaned != phone:
            issues.append({
                "code": "PHONE_NORMALIZED",
                "message": f"'{phone}' -> '{cleaned}' for entity '{e.get('name', e['id'])}'",
                "entity_id": e["id"],
                "old": phone,
                "new": cleaned,
            })
            attrs["phone"] = cleaned
            fix_count += 1

        # Validate final format
        if not VN_PHONE_RE.match(cleaned):
            issues.append({
                "code": "PHONE_INVALID",
                "message": f"phone '{cleaned}' for entity '{e.get('name', e['id'])}' does not match VN format",
                "entity_id": e["id"],
                "phone": cleaned,
            })

    return issues, fix_count


def check_duplicates(entities: list[dict]) -> list[dict]:
    """Report duplicate entities (same name + type + area)."""
    seen: dict[tuple[str, str, str], list[str]] = {}
    for e in entities:
        key = (
            e.get("name", "").strip().lower(),
            e.get("type", ""),
            e.get("area", ""),
        )
        if key[0]:  # skip entities without name
            seen.setdefault(key, []).append(e["id"])

    issues: list[dict] = []
    for (name, etype, area), ids in sorted(seen.items()):
        if len(ids) > 1:
            issues.append({
                "code": "DUPLICATE_ENTITY",
                "message": f"duplicate: name='{name}', type={etype}, area={area}, ids={ids}",
                "ids": ids,
                "name": name,
                "type": etype,
                "area": area,
            })
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Automated data-quality fixes for web/data.json."
    )
    parser.add_argument(
        "--data",
        default=str(DATA_JSON),
        help="path to data.json (default: web/data.json)",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="apply fixes (calls backup_data.py first). Default is dry-run.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="output report as JSON",
    )
    args = parser.parse_args()

    data_path = Path(args.data)
    if not data_path.exists():
        print(f"[fix] ERROR: {data_path} not found", file=sys.stderr)
        return 1

    data = _load_data(data_path)
    entities = data.get("entities", [])
    relationships = data.get("relationships", [])

    all_issues: list[dict] = []
    summary: dict = {}
    applied_fixes: list[str] = []

    # 1. Asymmetric near relationships
    near_issues, near_fixes = check_asymmetric_near(entities, relationships)
    all_issues.extend(near_issues)
    summary["asymmetric_near"] = len(near_issues)

    # 2. Coords approximate
    coords_issues = check_coords_approximate(entities)
    all_issues.extend(coords_issues)
    summary["coords_approximate"] = len(coords_issues)

    # 3. Wrong province summary
    province_issues = check_wrong_province_summary(entities)
    all_issues.extend(province_issues)
    summary["wrong_province_summary"] = len(province_issues)

    # 4. Phone normalization
    phone_issues, phone_fix_count = fix_phone_numbers(entities)
    all_issues.extend(phone_issues)
    summary["phone_issues"] = len(phone_issues)
    summary["phone_normalized"] = phone_fix_count

    # 5. Duplicates
    dup_issues = check_duplicates(entities)
    all_issues.extend(dup_issues)
    summary["duplicates"] = len(dup_issues)

    summary["total_issues"] = len(all_issues)
    summary["entities_scanned"] = len(entities)
    summary["relationships_scanned"] = len(relationships)

    # --- Apply fixes if requested ---
    if args.fix and (near_fixes or phone_fix_count > 0):
        if not _run_backup():
            print("[fix] ERROR: backup failed, aborting fix", file=sys.stderr)
            return 1

        if near_fixes:
            relationships.extend(near_fixes)
            data["relationships"] = relationships
            applied_fixes.append(f"added {len(near_fixes)} reverse 'near' relationships")

        if phone_fix_count > 0:
            applied_fixes.append(f"normalized {phone_fix_count} phone numbers")

        _save_data(data_path, data)
        summary["fixes_applied"] = applied_fixes
    elif args.fix:
        summary["fixes_applied"] = ["(no fixable issues found)"]

    # --- Output ---
    report = {"summary": summary, "issues": all_issues}

    if args.json_output:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        mode = "FIX" if args.fix else "DRY-RUN"
        print(f"[fix] data quality report ({mode})")
        print(f"  entities scanned: {summary['entities_scanned']}")
        print(f"  relationships scanned: {summary['relationships_scanned']}")
        print(f"  total issues: {summary['total_issues']}")
        print()

        for key in ("asymmetric_near", "coords_approximate", "wrong_province_summary", "phone_issues", "duplicates"):
            count = summary.get(key, 0)
            label = key.replace("_", " ").title()
            marker = "!!" if count > 0 else "ok"
            print(f"  [{marker}] {label}: {count}")

        if applied_fixes:
            print()
            print("  Fixes applied:")
            for fix_desc in applied_fixes:
                print(f"    - {fix_desc}")

        if all_issues:
            print()
            # Group by code
            by_code: dict[str, list[dict]] = {}
            for issue in all_issues:
                by_code.setdefault(issue["code"], []).append(issue)

            for code, items in by_code.items():
                print(f"  --- {code} ({len(items)}) ---")
                for item in items[:10]:  # show up to 10 per category
                    print(f"    {item['message']}")
                if len(items) > 10:
                    print(f"    ... and {len(items) - 10} more")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
