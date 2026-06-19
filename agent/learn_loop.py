"""
vinhlong360 — Feedback-Driven Learning Loop.

Kết nối các module tự học thành vòng lặp khép kín:

  User hỏi → Analytics ghi nhận → Phát hiện gap
       ↓
  Feedback (👍/👎) → Cập nhật confidence
       ↓
  Knowledge Gap → Auto-Learn trigger (không cần LLM)
       ↓
  Entity mới → KB mở rộng → Trả lời tốt hơn

Vòng lặp tự học có 3 cơ chế:
  1. GAP-BASED: Câu hỏi không trả lời được → tự tìm kiếm web → trích xuất
  2. FEEDBACK-BASED: User vote 👎 → đánh giá lại entity confidence
  3. ENRICHMENT: Entity thiếu summary/coordinates → auto-fill từ web

Chạy tự động qua scheduler (mỗi 3h) hoặc CLI:
  python agent/learn_loop.py --gaps      # Học từ knowledge gaps
  python agent/learn_loop.py --enrich    # Bổ sung entities thiếu
  python agent/learn_loop.py --feedback  # Xử lý user feedback
  python agent/learn_loop.py --all       # Chạy tất cả
"""

import json
import logging
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from threading import Lock

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

AGENT_DIR = Path(__file__).resolve().parent
DATA_DIR = AGENT_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

LEARN_LOG = DATA_DIR / "learn_loop_log.jsonl"
FEEDBACK_FILE = DATA_DIR / "feedback_history.json"
ROOT = AGENT_DIR.parent
DATA_JSON = ROOT / "web" / "data.json"

_logger = logging.getLogger("learn_loop")
if not _logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    _logger.addHandler(_h)
    _logger.setLevel(getattr(logging, os.environ.get("LOG_LEVEL", "INFO")))


# ══════════════════════════════════════════════════
#  1. GAP-BASED LEARNING (không cần LLM)
# ══════════════════════════════════════════════════

def _load_kb() -> dict:
    """Load knowledge base."""
    with open(DATA_JSON, encoding="utf-8") as f:
        return json.load(f)


def _save_kb(data: dict):
    """Save knowledge base."""
    with open(DATA_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _get_knowledge_gaps() -> list[dict]:
    """Lấy top knowledge gaps từ analytics."""
    try:
        import analytics
        gaps = analytics.get_knowledge_gaps(limit=10)
        return gaps if gaps else []
    except Exception as e:
        _logger.debug(f"No knowledge gaps available: {e}")
        return []


def _web_search_light(query: str, max_results: int = 3) -> list[dict]:
    """Tìm kiếm DuckDuckGo (lightweight, không cần LLM)."""
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query + " Vĩnh Long Bến Tre Trà Vinh",
                                     region="vn-vi", max_results=max_results))
        return results
    except Exception as e:
        _logger.warning(f"Web search failed: {e}")
        return []


def _extract_entity_from_snippet(snippet: str, title: str, url: str, query: str) -> dict | None:
    """Trích xuất entity từ search snippet KHÔNG cần LLM.

    Dùng heuristics + regex thay vì LLM call.
    Phù hợp khi LLM API down.
    """
    text = f"{title} {snippet}".strip()
    if len(text) < 30:
        return None

    # Detect location keywords
    location_patterns = {
        "vinh-long": r"[Vv]ĩnh\s*[Ll]ong",
        "ben-tre": r"[Bb]ến\s*[Tt]re",
        "tra-vinh": r"[Tt]rà\s*[Vv]inh",
    }
    area = None
    for area_id, pattern in location_patterns.items():
        if re.search(pattern, text):
            area = area_id
            break

    if not area:
        return None  # Không liên quan đến VL/BT/TV

    # Detect entity type from keywords
    type_keywords = {
        "dish": ["món", "ẩm thực", "bún", "phở", "bánh", "cơm", "lẩu", "nướng", "chè", "gỏi"],
        "product": ["đặc sản", "OCOP", "nông sản", "trái cây", "dừa", "cam", "bưởi", "xoài", "sầu riêng"],
        "attraction": ["chùa", "đền", "miếu", "nhà thờ", "bảo tàng", "khu du lịch", "di tích", "cầu"],
        "experience": ["du lịch", "trải nghiệm", "tham quan", "chèo xuồng", "đạp xe", "homestay"],
        "event": ["lễ hội", "festival", "sự kiện", "mùa"],
        "nature": ["sông", "cù lao", "rừng", "vườn", "hồ", "biển", "cồn"],
        "craft_village": ["làng nghề", "thủ công", "gốm", "dệt", "đan"],
        "person": ["nhà thơ", "danh nhân", "anh hùng", "nghệ nhân", "giáo sư"],
        "history": ["lịch sử", "kháng chiến", "cách mạng", "thời kỳ"],
    }

    entity_type = "attraction"  # default
    for etype, keywords in type_keywords.items():
        if any(kw in text.lower() for kw in keywords):
            entity_type = etype
            break

    # Use title as entity name (cleaned)
    name = re.sub(r"\s*[-|–—]\s*.{0,30}$", "", title)  # Remove " - SiteName" suffix
    name = re.sub(r"\s*\(.*?\)\s*$", "", name)  # Remove trailing (...)
    name = name.strip()

    if len(name) < 4 or len(name) > 100:
        return None

    # Generate ID
    import unicodedata
    slug = unicodedata.normalize("NFD", name.lower())
    slug = re.sub(r"[̀-ͯ]", "", slug)
    slug = slug.replace("đ", "d").replace("Đ", "d")
    slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")[:60]

    if not slug or len(slug) < 3:
        return None

    return {
        "id": slug,
        "type": entity_type,
        "name": name,
        "summary": snippet[:300] if snippet else "",
        "placeId": None,
        "confidence": 0.4,  # Low — needs review
        "status": "provisional",   # quarantine: not yet trusted
        "verified": False,         # auto-learned, awaiting promotion/review
        "learned_at": datetime.now().strftime("%Y-%m-%d"),
        "source": {"title": url.split("/")[2] if "/" in url else "web", "url": url},
        "updatedAt": datetime.now().strftime("%Y-%m-%d"),
        "attributes": {},
        "season": None,
        "images": [],
    }


def learn_from_gaps(max_gaps: int = 5, dry_run: bool = False) -> dict:
    """Học từ knowledge gaps — KHÔNG cần LLM.

    1. Lấy top knowledge gaps từ analytics
    2. Search web cho mỗi gap
    3. Trích xuất entities từ snippets (heuristics)
    4. Thêm vào KB (confidence thấp, cần admin review)

    Returns: {gaps_processed, entities_found, entities_added}
    """
    gaps = _get_knowledge_gaps()
    if not gaps:
        _logger.info("No knowledge gaps to learn from")
        return {"gaps_processed": 0, "entities_found": 0, "entities_added": 0}

    kb = _load_kb()

    def _norm_name(s: str) -> str:
        import unicodedata
        x = unicodedata.normalize("NFD", (s or "").lower())
        x = re.sub(r"[̀-ͯ]", "", x).replace("đ", "d")
        return re.sub(r"\s+", " ", x).strip()

    existing_ids = {e["id"] for e in kb["entities"]}
    existing_names = {_norm_name(e["name"]) for e in kb["entities"]}

    # Also check DB names to prevent duplicates missed by data.json-only dedup
    try:
        from database import db as _db
        for row in _db.search_entities("", limit=5000):
            eid = row.get("id", "")
            ename = row.get("name", "")
            if eid:
                existing_ids.add(eid)
            if ename:
                existing_names.add(_norm_name(ename))
    except Exception as exc:
        _logger.debug(f"DB dedup check unavailable: {exc}")

    new_entities = []
    processed = 0

    for gap in gaps[:max_gaps]:
        query = gap["query"]
        count = gap["count"]
        _logger.info(f"Learning from gap: '{query}' (asked {count}x)")
        processed += 1

        results = _web_search_light(query)
        for r in results:
            title = r.get("title", "")
            snippet = r.get("body", "")
            url = r.get("href", r.get("url", ""))

            entity = _extract_entity_from_snippet(snippet, title, url, query)
            if not entity:
                continue

            # Dedup check (diacritic-insensitive name + id)
            if entity["id"] in existing_ids:
                continue
            if _norm_name(entity["name"]) in existing_names:
                continue

            # Near-duplicate / contradiction gate: skip candidates that restate
            # an existing same-type entity under a slightly different name.
            try:
                import kb_curation
                dup = kb_curation.find_near_duplicate(entity["name"], entity["type"], kb["entities"])
                if dup:
                    _logger.info(f"  Skipped near-duplicate of '{dup}': {entity['name']}")
                    continue
            except Exception:
                pass

            # Geocode for the map (precise coords from OSM, not the LLM)
            try:
                import geocode as _geo
                c = _geo.geocode(entity["name"])
                if c:
                    entity["coords"] = c
            except Exception:
                pass

            new_entities.append(entity)
            existing_ids.add(entity["id"])
            existing_names.add(_norm_name(entity["name"]))
            _logger.info(f"  Found: [{entity['type']}] {entity['name']} (conf={entity['confidence']})")

        time.sleep(1)  # Rate limit

    added = 0
    if new_entities and not dry_run:
        for e in new_entities:
            kb["entities"].append(e)
        _save_kb(kb)
        # GĐ-audit (B1): ghi entity mới vào DB (chat đọc DB) — không chỉ data.json.
        try:
            from database import db
            for e in new_entities:
                db.upsert_entity(e)
        except Exception as exc:  # noqa: BLE001
            _logger.error(f"learn_loop: ghi DB that bai: {exc}")
        added = len(new_entities)
        _logger.info(f"Added {added} entities to KB (low confidence, needs review)")

        # Reload knowledge module
        try:
            import knowledge
            knowledge.reload()
        except Exception:
            pass

    # Log
    _log_event("gap_learning", {
        "gaps_processed": processed,
        "entities_found": len(new_entities),
        "entities_added": added,
        "entities": [{"id": e["id"], "name": e["name"], "type": e["type"]} for e in new_entities],
    })

    return {
        "gaps_processed": processed,
        "entities_found": len(new_entities),
        "entities_added": added,
    }


# ══════════════════════════════════════════════════
#  2. FEEDBACK-BASED LEARNING
# ══════════════════════════════════════════════════

def _load_feedback() -> list[dict]:
    """Load user feedback history."""
    if FEEDBACK_FILE.exists():
        try:
            return json.loads(FEEDBACK_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return []


def _save_feedback(data: list[dict]):
    """Save feedback history."""
    FEEDBACK_FILE.write_text(
        json.dumps(data[-1000:], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def record_feedback(query: str, rating: int, entity_id: str = None, session_id: str = None):
    """Ghi nhận feedback từ user.

    Args:
        query: Câu hỏi gốc
        rating: 0 (bad) hoặc 1 (good)
        entity_id: Entity liên quan (nếu có)
        session_id: Session ID
    """
    feedback = _load_feedback()
    feedback.append({
        "query": query[:200],
        "rating": rating,
        "entity_id": entity_id,
        "session_id": session_id,
        "timestamp": datetime.now().isoformat(),
    })
    _save_feedback(feedback)

    # Nếu feedback negative + có entity → giảm confidence
    if rating == 0 and entity_id:
        _adjust_entity_confidence(entity_id, delta=-0.05)
        _logger.info(f"Negative feedback → reduced confidence for {entity_id}")

    # Nếu feedback positive + có entity → tăng confidence
    if rating == 1 and entity_id:
        _adjust_entity_confidence(entity_id, delta=+0.02)


def _adjust_entity_confidence(entity_id: str, delta: float):
    """Điều chỉnh confidence dựa trên feedback."""
    try:
        kb = _load_kb()
        for e in kb["entities"]:
            if e["id"] == entity_id:
                old_conf = e.get("confidence", 0.7)
                new_conf = max(0.1, min(1.0, old_conf + delta))
                e["confidence"] = round(new_conf, 3)
                e["updatedAt"] = datetime.now().strftime("%Y-%m-%d")
                _save_kb(kb)
                # GĐ-audit (B1): cập nhật confidence vào DB (chat đọc DB).
                try:
                    from database import db
                    if db.get_entity(entity_id):
                        db.upsert_entity(e)
                except Exception as exc:  # noqa: BLE001
                    _logger.error(f"learn_loop: cap nhat confidence DB that bai: {exc}")
                _logger.debug(f"Confidence {entity_id}: {old_conf} → {new_conf}")
                return
    except Exception as e:
        _logger.error(f"Failed to adjust confidence: {e}")


def process_feedback_batch() -> dict:
    """Xử lý batch feedback — tìm pattern xấu và điều chỉnh.

    Returns: {total_feedback, negative_count, entities_adjusted}
    """
    feedback = _load_feedback()
    if not feedback:
        return {"total_feedback": 0, "negative_count": 0, "entities_adjusted": 0}

    # Nhóm negative feedback theo entity
    from collections import Counter
    neg_entities = Counter()
    neg_queries = Counter()

    for fb in feedback:
        if fb["rating"] == 0:
            if fb.get("entity_id"):
                neg_entities[fb["entity_id"]] += 1
            q = fb["query"].lower().strip().rstrip("?").strip()
            if len(q) > 5:
                neg_queries[q] += 1

    # Entity bị vote negative >= 3 lần → giảm confidence mạnh
    entities_adjusted = 0
    for entity_id, count in neg_entities.items():
        if count >= 3:
            _adjust_entity_confidence(entity_id, delta=-0.1)
            entities_adjusted += 1
            _logger.warning(f"Entity {entity_id} got {count} negative votes → reduced confidence")

    # Query bị negative >= 3 lần → đánh dấu là knowledge gap
    for query, count in neg_queries.most_common(10):
        if count >= 3:
            _logger.info(f"Frequent negative query: '{query}' ({count}x) → priority gap")

    total = len(feedback)
    negative = sum(1 for fb in feedback if fb["rating"] == 0)

    _log_event("feedback_processing", {
        "total_feedback": total,
        "negative_count": negative,
        "positive_count": total - negative,
        "entities_adjusted": entities_adjusted,
        "top_negative_queries": [{"query": q, "count": c} for q, c in neg_queries.most_common(5)],
    })

    return {
        "total_feedback": total,
        "negative_count": negative,
        "entities_adjusted": entities_adjusted,
    }


# ══════════════════════════════════════════════════
#  3. AUTO-ENRICHMENT (fill missing data)
# ══════════════════════════════════════════════════

def enrich_entities(max_entities: int = 10, dry_run: bool = False) -> dict:
    """Bổ sung summary cho entities thiếu.

    Tìm entities không có summary, search web để tạo summary.
    KHÔNG cần LLM — dùng search snippet làm summary.

    Returns: {scanned, enriched, skipped}
    """
    kb = _load_kb()
    enriched = 0
    skipped = 0

    # Tìm entities thiếu summary
    missing = [
        e for e in kb["entities"]
        if e.get("type") != "place"
        and (not e.get("summary") or len(e.get("summary", "")) < 10)
    ]

    if not missing:
        _logger.info("All entities have summaries — nothing to enrich")
        return {"scanned": 0, "enriched": 0, "skipped": 0}

    _logger.info(f"Found {len(missing)} entities without summary")

    for entity in missing[:max_entities]:
        name = entity.get("name", "")
        etype = entity.get("type", "")

        # Search web for this entity
        query = f"{name} {etype} Vĩnh Long"
        results = _web_search_light(query, max_results=2)

        best_snippet = ""
        for r in results:
            snippet = r.get("body", "")
            title = r.get("title", "")
            # Check if the snippet is actually about this entity
            if name.lower()[:5] in (snippet + title).lower():
                best_snippet = snippet
                break

        if best_snippet and len(best_snippet) > 20:
            # Clean and truncate
            summary = best_snippet.strip()
            if len(summary) > 300:
                # Cut at sentence boundary
                cut = summary[:300].rfind(".")
                if cut > 100:
                    summary = summary[:cut + 1]
                else:
                    summary = summary[:300] + "..."

            if not dry_run:
                entity["summary"] = summary
                entity["updatedAt"] = datetime.now().strftime("%Y-%m-%d")
                enriched += 1
                _logger.info(f"  Enriched: {name} ← {summary[:60]}...")
            else:
                enriched += 1
                _logger.info(f"  [DRY RUN] Would enrich: {name}")
        else:
            skipped += 1
            _logger.debug(f"  No good snippet for: {name}")

        time.sleep(1)  # Rate limit

    if enriched > 0 and not dry_run:
        _save_kb(kb)
        _logger.info(f"Enriched {enriched} entities with summaries")

        try:
            import knowledge
            knowledge.reload()
        except Exception:
            pass

    _log_event("enrichment", {
        "total_missing": len(missing),
        "scanned": min(max_entities, len(missing)),
        "enriched": enriched,
        "skipped": skipped,
    })

    return {
        "scanned": min(max_entities, len(missing)),
        "enriched": enriched,
        "skipped": skipped,
    }


# ══════════════════════════════════════════════════
#  4. LEARNING STATUS & LOGGING
# ══════════════════════════════════════════════════

def _log_event(event_type: str, data: dict):
    """Ghi log event vào file."""
    try:
        entry = {
            "type": event_type,
            "timestamp": datetime.now().isoformat(),
            **data,
        }
        with open(LEARN_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def learning_status() -> dict:
    """Trạng thái tổng quan của vòng lặp tự học."""
    # Knowledge gaps
    gaps = _get_knowledge_gaps()

    # Feedback
    feedback = _load_feedback()
    recent_fb = [fb for fb in feedback if fb.get("timestamp", "") > datetime.now().strftime("%Y-%m-%d")]

    # Missing summaries
    try:
        kb = _load_kb()
        missing = len([
            e for e in kb["entities"]
            if e.get("type") != "place" and (not e.get("summary") or len(e.get("summary", "")) < 10)
        ])
        low_conf = len([
            e for e in kb["entities"]
            if e.get("type") != "place" and e.get("confidence", 1) < 0.5
        ])
        total = len([e for e in kb["entities"] if e.get("type") != "place"])
    except Exception:
        missing = 0
        low_conf = 0
        total = 0

    # Recent learning activity
    recent_events = []
    try:
        if LEARN_LOG.exists():
            lines = LEARN_LOG.read_text(encoding="utf-8").strip().split("\n")
            for line in lines[-10:]:
                try:
                    recent_events.append(json.loads(line))
                except Exception:
                    pass
    except Exception:
        pass

    return {
        "knowledge_gaps": len(gaps),
        "top_gaps": gaps[:5],
        "total_entities": total,
        "missing_summaries": missing,
        "low_confidence_entities": low_conf,
        "feedback_today": len(recent_fb),
        "feedback_total": len(feedback),
        "recent_learning": recent_events[-5:],
    }


def backfill_coords(max_entities: int = 15, dry_run: bool = False) -> dict:
    """Geocode entities missing map coordinates (prioritize provisional ones).

    Coordinates come from OSM/Nominatim — never from the LLM. Offline-safe:
    if geocoding is unavailable, this is a no-op.
    """
    try:
        import geocode as _geo
    except Exception:
        return {"checked": 0, "geocoded": 0, "reason": "geocode unavailable"}

    kb = _load_kb()
    places_by_id = {e["id"]: e for e in kb["entities"] if e.get("type") == "place"}
    candidates = [e for e in kb["entities"]
                  if e.get("type") != "place" and not e.get("coords") and e.get("name")]
    # Provisional/unverified first — they're the freshly auto-learned ones.
    candidates.sort(key=lambda e: 0 if (e.get("status") == "provisional" or e.get("verified") is False) else 1)

    geocoded = []
    for e in candidates[:max_entities]:
        # Variant 1: plain name
        c = _geo.geocode(e["name"])
        # Variant 2: name scoped by its commune/ward (helps OSM disambiguate)
        if not c and e.get("placeId") in places_by_id:
            pname = places_by_id[e["placeId"]].get("name", "")
            if pname:
                c = _geo.geocode(e["name"], region=pname)
        # Variant 3: name without category prefix (e.g. "Khu di tích X" → "X")
        if not c:
            import re as _re
            stripped = _re.sub(
                r"^(khu di tích|khu lưu niệm|khu du lịch|di tích|làng nghề|cơ sở|vườn quốc gia)\s+",
                "", e["name"], flags=_re.IGNORECASE).strip()
            if stripped and stripped != e["name"] and len(stripped) >= 4:
                c = _geo.geocode(stripped)
        if c:
            e["coords"] = c
            geocoded.append(e["id"])

    if geocoded and not dry_run:
        _save_kb(kb)
        try:
            import knowledge
            knowledge.reload()
        except Exception:
            pass
        _logger.info(f"Backfilled coords for {len(geocoded)} entities")

    return {"checked": min(len(candidates), max_entities), "geocoded": len(geocoded), "ids": geocoded}


def run_full_cycle(dry_run: bool = False) -> dict:
    """Chạy 1 vòng lặp tự học đầy đủ.

    1. Xử lý feedback
    2. Học từ knowledge gaps (kèm geocode toạ độ cho bản đồ)
    3. Bổ sung entities thiếu summary
    4. Geocode bổ sung toạ độ cho entity còn thiếu

    Returns: Combined results
    """
    _logger.info("═══ Learning Loop — Full Cycle ═══")
    results = {}

    # Step 1: Process feedback
    _logger.info("Step 1: Processing user feedback...")
    results["feedback"] = process_feedback_batch()

    # Step 2: Learn from gaps (new entities get geocoded inline)
    _logger.info("Step 2: Learning from knowledge gaps...")
    results["gap_learning"] = learn_from_gaps(max_gaps=5, dry_run=dry_run)

    # Step 3: Enrich entities
    _logger.info("Step 3: Enriching entities...")
    results["enrichment"] = enrich_entities(max_entities=10, dry_run=dry_run)

    # Step 4: Backfill map coordinates for entities still missing them
    _logger.info("Step 4: Backfilling map coordinates...")
    results["geocoding"] = backfill_coords(max_entities=15, dry_run=dry_run)

    _logger.info(f"═══ Learning Loop Complete ═══")
    _logger.info(f"  Feedback processed: {results['feedback']['total_feedback']}")
    _logger.info(f"  Gaps learned: {results['gap_learning']['entities_added']}")
    _logger.info(f"  Entities enriched: {results['enrichment']['enriched']}")
    _logger.info(f"  Coords geocoded: {results['geocoding']['geocoded']}")

    return results


# ══════════════════════════════════════════════════
#  CLI
# ══════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="vinhlong360 Learning Loop")
    parser.add_argument("--gaps", action="store_true", help="Learn from knowledge gaps")
    parser.add_argument("--enrich", action="store_true", help="Enrich entities missing summary")
    parser.add_argument("--feedback", action="store_true", help="Process user feedback")
    parser.add_argument("--all", action="store_true", help="Run full learning cycle")
    parser.add_argument("--status", action="store_true", help="Show learning status")
    parser.add_argument("--dry-run", action="store_true", help="Don't modify data")
    args = parser.parse_args()

    if args.status:
        status = learning_status()
        print(json.dumps(status, ensure_ascii=False, indent=2))
    elif args.all:
        results = run_full_cycle(dry_run=args.dry_run)
        print(json.dumps(results, ensure_ascii=False, indent=2))
    elif args.gaps:
        results = learn_from_gaps(dry_run=args.dry_run)
        print(json.dumps(results, ensure_ascii=False, indent=2))
    elif args.enrich:
        results = enrich_entities(dry_run=args.dry_run)
        print(json.dumps(results, ensure_ascii=False, indent=2))
    elif args.feedback:
        results = process_feedback_batch()
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        parser.print_help()
