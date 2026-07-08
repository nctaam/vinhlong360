"""
vinhlong360 -- Content Freshness Checker.

Phân tích và đánh giá độ "tươi" (freshness) của knowledge base:
  - Phát hiện entity cũ (stale) cần cập nhật
  - Phát hiện entity thiếu thông tin (incomplete)
  - Phát hiện entity confidence thấp
  - Đề xuất danh sách ưu tiên cập nhật
  - Tạo báo cáo tổng quan

Chạy:
  python agent/freshness.py                     # Kiểm tra & in báo cáo
  python agent/freshness.py --schedule 20       # Lên lịch refresh top 20
  python agent/freshness.py --json              # Xuất kết quả JSON
"""

import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if hasattr(sys.stdout, "reconfigure") and sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
DATA_JSON = ROOT / "web" / "data.json"
ANALYTICS_FILE = Path(__file__).resolve().parent / "data" / "analytics.json"
DATA_DIR = Path(__file__).resolve().parent / "data"
REFRESH_QUEUE_FILE = DATA_DIR / "refresh_queue.json"

# ── Defaults ──

DEFAULT_MAX_AGE_DAYS = 180
DEFAULT_MIN_CONFIDENCE = 0.6
DEFAULT_MIN_SUMMARY_LEN = 30


# ══════════════════════════════════════════════════
#  Helpers
# ══════════════════════════════════════════════════

def _load_data() -> dict:
    """Load entities from web/data.json."""
    if not DATA_JSON.exists():
        return {"entities": []}
    with open(DATA_JSON, encoding="utf-8") as f:
        return json.load(f)


def _load_analytics() -> dict:
    """Load analytics data (entity_hits etc.) if available."""
    if not ANALYTICS_FILE.exists():
        return {}
    with open(ANALYTICS_FILE, encoding="utf-8") as f:
        return json.load(f)


def _get_date_field(entity: dict) -> str | None:
    """Extract date string from entity, supporting both field names."""
    return entity.get("learned_at") or entity.get("updatedAt")


def _get_location_field(entity: dict) -> str | None:
    """Extract location reference, supporting both field names."""
    return entity.get("ward_id") or entity.get("placeId") or entity.get("area")


def _get_source_value(entity: dict) -> str | None:
    """Extract source info. Source can be a string or an object."""
    src = entity.get("source")
    if src is None:
        return None
    if isinstance(src, str):
        return src if src.strip() else None
    if isinstance(src, dict):
        title = src.get("title", "")
        url = src.get("url", "")
        return title or url or None
    return None


def _parse_date(date_str: str) -> datetime | None:
    """Parse date → tz-aware (UTC). Xử lý ISO-8601 có offset ('...Z', '+07:00' —
    format CHÍNH trong data.json: 1694/1749 date) lẫn 3 format naive cũ.

    Trước đây trả naive: date-only parseable → so với `cutoff` aware gây
    `TypeError` → /freshness/check & /freshness/report CRASH 500 (55 entity
    date-only); còn '...Z' thì strptime không nuốt → None → staleness câm lặng
    cho 1694 entity. Nay chuẩn-hoá aware, staleness đúng toàn dataset (bug SP3-W5)."""
    if not date_str:
        return None
    try:  # fromisoformat nuốt cả 3 format naive cũ lẫn ISO-offset ('...Z')
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def _is_knowledge_entity(entity: dict) -> bool:
    """Check if entity is a knowledge entity (not a bare place/ward)."""
    etype = entity.get("type", "")
    # Place entities without summaries are structural, not knowledge
    if etype == "place" and not entity.get("summary"):
        return False
    return True


# ══════════════════════════════════════════════════
#  1. check_freshness
# ══════════════════════════════════════════════════

def _staleness_reason(entity: dict, cutoff: datetime, now: datetime) -> str | None:
    """Compute the staleness reason for one entity (None if fresh)."""
    date_str = _get_date_field(entity)
    if date_str:
        dt = _parse_date(date_str)
        if dt and dt < cutoff:
            age_days = (now - dt).days
            return f"Stale: last updated {age_days} days ago ({date_str})"
        return None
    return "Stale: no update date recorded"


def _missing_fields_reason(entity: dict) -> str | None:
    """Compute the missing-critical-fields reason for one entity (None if complete)."""
    missing = []
    if not entity.get("summary"):
        missing.append("summary")
    if not _get_location_field(entity):
        missing.append("location (ward_id/placeId)")
    if not _get_source_value(entity):
        missing.append("source")
    if missing:
        return f"Missing fields: {', '.join(missing)}"
    return None


def _entity_reasons(entity: dict, cutoff: datetime, now: datetime) -> list[str]:
    """Gather all freshness issue reasons for a single entity, in order."""
    reasons: list[str] = []

    # --- Staleness check ---
    stale_reason = _staleness_reason(entity, cutoff, now)
    if stale_reason:
        reasons.append(stale_reason)

    # --- Low confidence ---
    confidence = entity.get("confidence")
    if confidence is not None and confidence < DEFAULT_MIN_CONFIDENCE:
        reasons.append(f"Low confidence: {confidence}")

    # --- Missing critical fields ---
    missing_reason = _missing_fields_reason(entity)
    if missing_reason:
        reasons.append(missing_reason)

    # --- Short summary ---
    summary = entity.get("summary", "")
    if summary and len(summary) < DEFAULT_MIN_SUMMARY_LEN:
        reasons.append(f"Short summary: only {len(summary)} chars")

    return reasons


def check_freshness(entities: dict, max_age_days: int = DEFAULT_MAX_AGE_DAYS) -> dict:
    """
    Analyze all entities for staleness, low confidence, and missing data.

    Returns:
        {
            "total": int,
            "fresh": int,
            "stale": int,
            "low_confidence": int,
            "incomplete": int,
            "issues": [{"id": str, "name": str, "reasons": [str]}]
        }
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=max_age_days)

    all_entities = entities.get("entities", [])
    # Filter to knowledge entities only
    knowledge = [e for e in all_entities if _is_knowledge_entity(e)]

    total = len(knowledge)
    stale_count = 0
    low_conf_count = 0
    incomplete_count = 0
    issues: list[dict] = []

    for entity in knowledge:
        eid = entity.get("id", "unknown")
        name = entity.get("name", eid)
        reasons = _entity_reasons(entity, cutoff, now)

        # --- Tally ---
        if reasons:
            has_stale = any(r.startswith("Stale") for r in reasons)
            has_low_conf = any(r.startswith("Low confidence") for r in reasons)
            has_incomplete = any(
                r.startswith("Missing") or r.startswith("Short summary")
                for r in reasons
            )

            if has_stale:
                stale_count += 1
            if has_low_conf:
                low_conf_count += 1
            if has_incomplete:
                incomplete_count += 1

            issues.append({"id": eid, "name": name, "reasons": reasons})

    fresh_count = total - len(issues)

    return {
        "total": total,
        "fresh": fresh_count,
        "stale": stale_count,
        "low_confidence": low_conf_count,
        "incomplete": incomplete_count,
        "issues": issues,
    }


# ══════════════════════════════════════════════════
#  2. auto_refresh_candidates
# ══════════════════════════════════════════════════

def auto_refresh_candidates(entities: dict, limit: int = 20) -> list[dict]:
    """
    Select top entities that most need updating, prioritized by:
      1. Stale + popular (high entity_hits)  -- highest priority
      2. Stale + unpopular                   -- medium priority
      3. Incomplete (missing fields/short)   -- lower priority

    Returns:
        [{"id": str, "name": str, "reasons": [str], "priority": int, "hits": int}]
    """
    result = check_freshness(entities)
    analytics = _load_analytics()
    entity_hits = analytics.get("entity_hits", {})

    candidates = []
    for issue in result["issues"]:
        eid = issue["id"]
        hits = entity_hits.get(eid, 0)
        reasons = issue["reasons"]

        is_stale = any(r.startswith("Stale") for r in reasons)
        is_incomplete = any(
            r.startswith("Missing") or r.startswith("Short summary")
            for r in reasons
        )

        # Priority: lower number = higher priority
        if is_stale and hits > 0:
            priority = 1  # stale + popular
        elif is_stale:
            priority = 2  # stale + unpopular
        elif is_incomplete:
            priority = 3  # incomplete
        else:
            priority = 4  # low confidence only

        candidates.append({
            "id": eid,
            "name": issue["name"],
            "reasons": reasons,
            "priority": priority,
            "hits": hits,
        })

    # Sort: priority ascending, then hits descending (popular first within tier)
    candidates.sort(key=lambda c: (c["priority"], -c["hits"]))

    return candidates[:limit]


# ══════════════════════════════════════════════════
#  3. freshness_report
# ══════════════════════════════════════════════════

def _report_overview_lines(result: dict, total: int) -> list[str]:
    """Build the header + overview stats block for the report."""
    lines = []
    lines.append("=" * 60)
    lines.append("  CONTENT FRESHNESS REPORT")
    lines.append("  " + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"))
    lines.append("=" * 60)
    lines.append("")

    # --- Overview ---
    pct_fresh = result["fresh"] / total * 100
    pct_stale = result["stale"] / total * 100
    pct_low = result["low_confidence"] / total * 100
    pct_inc = result["incomplete"] / total * 100

    lines.append(f"  Total entities:    {total}")
    lines.append(f"  Fresh:             {result['fresh']:>4}  ({pct_fresh:.1f}%)")
    lines.append(f"  Stale:             {result['stale']:>4}  ({pct_stale:.1f}%)")
    lines.append(f"  Low confidence:    {result['low_confidence']:>4}  ({pct_low:.1f}%)")
    lines.append(f"  Incomplete:        {result['incomplete']:>4}  ({pct_inc:.1f}%)")
    lines.append(f"  Issues found:      {len(result['issues']):>4}")
    lines.append("")
    return lines


def _group_report_items(issues: list[dict]) -> tuple[list, list, list]:
    """Split issue reasons into (stale, low_confidence, incomplete) item tuples."""
    stale_items = []
    low_conf_items = []
    incomplete_items = []

    for issue in issues:
        for reason in issue["reasons"]:
            if reason.startswith("Stale"):
                stale_items.append((issue["id"], issue["name"], reason))
            elif reason.startswith("Low confidence"):
                low_conf_items.append((issue["id"], issue["name"], reason))
            elif reason.startswith("Missing") or reason.startswith("Short summary"):
                incomplete_items.append((issue["id"], issue["name"], reason))

    return stale_items, low_conf_items, incomplete_items


def _report_section_lines(title: str, items: list, cap: int) -> list[str]:
    """Render one issue section (header + up to `cap` items + overflow note)."""
    if not items:
        return []
    lines = []
    lines.append("-" * 60)
    lines.append(f"  {title} ({len(items)})")
    lines.append("-" * 60)
    for eid, name, reason in items[:cap]:
        lines.append(f"    [{eid}] {name}")
        lines.append(f"      -> {reason}")
    if len(items) > cap:
        lines.append(f"    ... and {len(items) - cap} more")
    lines.append("")
    return lines


def _report_candidate_lines(entities: dict) -> list[str]:
    """Render the top refresh candidates block."""
    candidates = auto_refresh_candidates(entities, limit=10)
    if not candidates:
        return []
    lines = []
    lines.append("-" * 60)
    lines.append("  TOP REFRESH CANDIDATES")
    lines.append("-" * 60)
    for i, c in enumerate(candidates, 1):
        hits_label = f" ({c['hits']} queries)" if c["hits"] else ""
        lines.append(f"    {i:>2}. [{c['id']}] {c['name']}{hits_label}")
    lines.append("")
    return lines


def freshness_report(entities: dict) -> str:
    """Generate a human-readable freshness report."""
    result = check_freshness(entities)
    total = result["total"]
    if total == 0:
        return "No knowledge entities found."

    lines = _report_overview_lines(result, total)

    if not result["issues"]:
        lines.append("  All entities are fresh and complete!")
        lines.append("")
        return "\n".join(lines)

    # --- Group by issue type ---
    stale_items, low_conf_items, incomplete_items = _group_report_items(result["issues"])

    lines.extend(_report_section_lines("STALE ENTITIES", stale_items, 30))
    lines.extend(_report_section_lines("LOW CONFIDENCE", low_conf_items, 20))
    lines.extend(_report_section_lines("INCOMPLETE ENTITIES", incomplete_items, 20))

    # --- Refresh recommendations ---
    lines.extend(_report_candidate_lines(entities))

    lines.append("=" * 60)
    return "\n".join(lines)


# ══════════════════════════════════════════════════
#  4. schedule_refresh
# ══════════════════════════════════════════════════

def schedule_refresh(entity_ids: list[str]) -> dict:
    """
    Mark entities for auto-learn refresh by saving to refresh_queue.json.

    Returns:
        {"scheduled": int, "queue_file": str, "timestamp": str}
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Load existing queue
    queue: dict = {}
    if REFRESH_QUEUE_FILE.exists():
        with open(REFRESH_QUEUE_FILE, encoding="utf-8") as f:
            queue = json.load(f)

    pending = queue.get("pending", [])
    existing_ids = {item["id"] for item in pending}
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    added = 0
    for eid in entity_ids:
        if eid not in existing_ids:
            pending.append({
                "id": eid,
                "queued_at": now_str,
                "status": "pending",
            })
            existing_ids.add(eid)
            added += 1

    queue["pending"] = pending
    queue["last_updated"] = now_str

    tmp = REFRESH_QUEUE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(REFRESH_QUEUE_FILE)

    return {
        "scheduled": added,
        "queue_file": str(REFRESH_QUEUE_FILE),
        "timestamp": now_str,
    }


# ══════════════════════════════════════════════════
#  CLI
# ══════════════════════════════════════════════════

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Content Freshness Checker")
    parser.add_argument(
        "--json", action="store_true",
        help="Output raw JSON instead of report",
    )
    parser.add_argument(
        "--schedule", type=int, metavar="N",
        help="Schedule top N candidates for refresh",
    )
    parser.add_argument(
        "--max-age", type=int, default=DEFAULT_MAX_AGE_DAYS,
        help=f"Max age in days before flagging as stale (default: {DEFAULT_MAX_AGE_DAYS})",
    )
    args = parser.parse_args()

    data = _load_data()

    if args.json:
        result = check_freshness(data, max_age_days=args.max_age)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # Print report
    report = freshness_report(data)
    print(report)

    # Schedule if requested
    if args.schedule:
        candidates = auto_refresh_candidates(data, limit=args.schedule)
        if candidates:
            ids = [c["id"] for c in candidates]
            result = schedule_refresh(ids)
            print(f"\nScheduled {result['scheduled']} entities for refresh.")
            print(f"Queue file: {result['queue_file']}")
        else:
            print("\nNo candidates to schedule.")


if __name__ == "__main__":
    main()
