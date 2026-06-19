#!/usr/bin/env python3
"""
Standardize vinhlong360 data — normalize formats directly in the SQLite DB.

Phase 2: Format standardization (source, attributes, season)
Phase 3: Inference & enrichment (area, placeId, geocode, LLM)
Phase 4: Cleanup (low confidence, empty attrs, duplicates)

Usage:
  python scripts/standardize_data.py --phase 2      # format normalize only
  python scripts/standardize_data.py --phase 3      # inference + enrichment
  python scripts/standardize_data.py --phase all     # run everything
  python scripts/standardize_data.py --check         # dry-run, report only
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import unicodedata
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "agent" / "data" / "vinhlong360.db"

MEKONG_BBOX = {"lat_min": 9.2, "lat_max": 10.65, "lng_min": 105.6, "lng_max": 106.95}

ATTRIBUTE_KEY_MAP = {
    "open_hours": "hours",
    "opening_hours": "hours",
    "foodyRating": "rating",
    "foodyComments": "review_count",
    "bestTime": "best_time",
    "gia": "price",
    "thoiluong": "duration",
    "entrance_fee": "admission_fee",
}


def _configure_output():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")


def _parse_json(val: str | None) -> Any:
    if val is None or val == "":
        return None
    try:
        return json.loads(val)
    except (json.JSONDecodeError, TypeError):
        return val


def normalize_source(raw: Any) -> list[dict]:
    """Normalize source field → always list[dict]."""
    if raw is None or raw == "" or raw == "{}":
        return []

    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            pass

    if isinstance(raw, str):
        raw = raw.strip()
        if not raw:
            return []
        if raw.startswith("http"):
            return [{"url": raw}]
        return [{"name": raw}]

    if isinstance(raw, dict):
        if not raw:
            return []
        return [raw]

    if isinstance(raw, list):
        result = []
        for item in raw:
            if isinstance(item, dict):
                result.append(item)
            elif isinstance(item, str):
                item = item.strip()
                if item.startswith("http"):
                    result.append({"url": item})
                elif item:
                    result.append({"name": item})
        return result

    return []


def normalize_attributes(raw: Any) -> tuple[dict, list[str]]:
    """Normalize attribute keys. Returns (normalized_dict, list_of_renamed_keys)."""
    if raw is None or raw == "" or raw == "{}":
        return {}, []

    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return {}, []

    if not isinstance(raw, dict):
        return {}, []

    result = {}
    renamed = []
    for key, value in raw.items():
        new_key = ATTRIBUTE_KEY_MAP.get(key, key)
        if new_key != key:
            renamed.append(f"{key}→{new_key}")
        if new_key in result:
            if not result[new_key] and value:
                result[new_key] = value
        else:
            result[new_key] = value

    return result, renamed


def normalize_season(raw: Any) -> dict | None:
    """Normalize season field → always dict with months/peak/text or None."""
    if raw is None or raw == "" or raw == "null":
        return None

    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            pass

    if isinstance(raw, str):
        raw = raw.strip()
        if not raw:
            return None
        return {"months": [], "peak": [], "text": raw}

    if isinstance(raw, dict):
        months = raw.get("months", [])
        peak = raw.get("peak", [])
        text = raw.get("text", "")

        if not isinstance(months, list):
            months = []
        if not isinstance(peak, list):
            peak = []

        months = [m for m in months if isinstance(m, int) and 1 <= m <= 12]
        peak = [m for m in peak if isinstance(m, int) and 1 <= m <= 12]

        if peak and months:
            peak = [m for m in peak if m in months]

        if not months and not peak and not text:
            return None

        return {"months": months, "peak": peak, "text": text}

    return None


def phase2_normalize_formats(db: sqlite3.Connection, *, dry_run: bool = False) -> dict:
    """Phase 2: Normalize source, attributes, season formats in-place."""
    stats = {
        "source_normalized": 0,
        "source_by_type": Counter(),
        "attributes_renamed": 0,
        "attribute_keys_renamed": Counter(),
        "season_string_to_dict": 0,
        "season_cleaned": 0,
    }

    rows = db.execute(
        "SELECT id, source, attributes, season FROM entities"
    ).fetchall()

    updates = []

    for entity_id, source_raw, attrs_raw, season_raw in rows:
        source_changed = False
        attrs_changed = False
        season_changed = False

        # --- Source ---
        old_source = _parse_json(source_raw)
        new_source = normalize_source(source_raw)

        if isinstance(old_source, str):
            source_changed = True
            stats["source_by_type"]["string→list"] += 1
        elif isinstance(old_source, dict):
            source_changed = True
            stats["source_by_type"]["dict→list"] += 1
        elif isinstance(old_source, list):
            new_json = json.dumps(new_source, ensure_ascii=False)
            old_json = json.dumps(old_source, ensure_ascii=False)
            if new_json != old_json:
                source_changed = True
                stats["source_by_type"]["list_cleaned"] += 1
        elif old_source is None:
            if new_source:
                source_changed = True
            else:
                new_source_json = json.dumps(new_source, ensure_ascii=False)
                if source_raw != new_source_json:
                    source_changed = True

        if source_changed:
            stats["source_normalized"] += 1

        # --- Attributes ---
        new_attrs, renamed = normalize_attributes(attrs_raw)
        if renamed:
            attrs_changed = True
            stats["attributes_renamed"] += 1
            for r in renamed:
                stats["attribute_keys_renamed"][r] += 1
        else:
            old_attrs = _parse_json(attrs_raw)
            if isinstance(old_attrs, dict) and old_attrs == new_attrs:
                attrs_changed = False
            elif not isinstance(old_attrs, dict) and not new_attrs:
                attrs_changed = False
            else:
                attrs_changed = True

        # --- Season ---
        old_season = _parse_json(season_raw)
        new_season = normalize_season(season_raw)

        if isinstance(old_season, str) and new_season:
            season_changed = True
            stats["season_string_to_dict"] += 1
        elif isinstance(old_season, dict) and new_season:
            if json.dumps(old_season, ensure_ascii=False, sort_keys=True) != json.dumps(new_season, ensure_ascii=False, sort_keys=True):
                season_changed = True
                stats["season_cleaned"] += 1
        elif old_season is None and new_season is None:
            season_changed = False

        if source_changed or attrs_changed or season_changed:
            updates.append((
                json.dumps(new_source, ensure_ascii=False),
                json.dumps(new_attrs, ensure_ascii=False) if new_attrs else "{}",
                json.dumps(new_season, ensure_ascii=False) if new_season else None,
                entity_id,
            ))

    if not dry_run and updates:
        db.executemany(
            "UPDATE entities SET source=?, attributes=?, season=? WHERE id=?",
            updates,
        )
        db.commit()

    stats["total_updated"] = len(updates)
    return stats


def phase3_infer_area(db: sqlite3.Connection, *, dry_run: bool = False) -> dict:
    """Phase 3.1: Infer missing area from placeId or address keywords."""
    stats = {"from_place": 0, "from_keywords": 0}

    place_areas = dict(db.execute(
        "SELECT id, area FROM entities WHERE type='place' AND area IS NOT NULL"
    ).fetchall())

    AREA_KEYWORDS = {
        "vinh-long": ("vinh long", "vĩnh long"),
        "ben-tre": ("ben tre", "bến tre"),
        "tra-vinh": ("tra vinh", "trà vinh"),
    }

    rows = db.execute(
        "SELECT id, placeId, name, attributes FROM entities WHERE type != 'place' AND (area IS NULL OR area = '')"
    ).fetchall()

    updates = []
    for entity_id, place_id, name, attrs_raw in rows:
        area = None

        if place_id and place_id in place_areas:
            area = place_areas[place_id]
            stats["from_place"] += 1
        else:
            attrs = _parse_json(attrs_raw) or {}
            search_text = " ".join(filter(None, [
                entity_id, name,
                attrs.get("address", ""),
                attrs.get("province", ""),
                attrs.get("area", ""),
            ])).lower()
            search_text = unicodedata.normalize("NFD", search_text)
            search_text = "".join(ch for ch in search_text if unicodedata.category(ch) != "Mn")
            search_text = search_text.replace("đ", "d")

            hits = [
                a for a, kws in AREA_KEYWORDS.items()
                if any(k.replace("đ", "d") in search_text for k in [
                    unicodedata.normalize("NFD", kw).replace("đ", "d")
                    for kw in kws
                ])
            ]
            if len(hits) == 1:
                area = hits[0]
                stats["from_keywords"] += 1

        if area:
            updates.append((area, entity_id))

    if not dry_run and updates:
        db.executemany("UPDATE entities SET area=? WHERE id=?", updates)
        db.commit()

    stats["total"] = len(updates)
    return stats


def phase3_infer_placeid(db: sqlite3.Connection, *, dry_run: bool = False) -> dict:
    """Phase 3.2: Infer placeId from address text fuzzy-matching place names."""
    stats = {"matched": 0, "ambiguous": 0}

    places = db.execute(
        "SELECT id, name, area FROM entities WHERE type='place'"
    ).fetchall()

    def _normalize(text: str) -> str:
        text = text.lower().strip()
        text = unicodedata.normalize("NFD", text)
        text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
        return text.replace("đ", "d").replace("-", " ")

    place_lookup: dict[str, list[tuple[str, str]]] = {}
    for pid, pname, parea in places:
        norm_name = _normalize(pname)
        for prefix in ("phuong ", "xa ", "thi tran "):
            if norm_name.startswith(prefix):
                short_name = norm_name[len(prefix):]
                break
        else:
            short_name = norm_name

        place_lookup.setdefault(short_name, []).append((pid, parea or ""))

    rows = db.execute("""
        SELECT id, name, attributes, area
        FROM entities
        WHERE type != 'place' AND (placeId IS NULL OR placeId = '')
    """).fetchall()

    updates = []
    for entity_id, name, attrs_raw, entity_area in rows:
        attrs = _parse_json(attrs_raw) or {}
        address = attrs.get("address", "") or ""
        ward = attrs.get("ward", "") or ""
        district = attrs.get("district", "") or ""

        search_parts = [address, ward, district]
        search_text = _normalize(" ".join(filter(None, search_parts)))
        if not search_text.strip():
            continue

        candidates = []
        for place_name, place_entries in place_lookup.items():
            if place_name in search_text:
                for pid, parea in place_entries:
                    if entity_area and parea and entity_area != parea:
                        continue
                    candidates.append((pid, len(place_name)))

        if not candidates:
            continue

        candidates.sort(key=lambda x: -x[1])
        best_len = candidates[0][1]
        top = [c for c in candidates if c[1] == best_len]

        if len(top) == 1:
            updates.append((top[0][0], entity_id))
            stats["matched"] += 1
        else:
            stats["ambiguous"] += 1

    if not dry_run and updates:
        db.executemany("UPDATE entities SET placeId=? WHERE id=?", updates)
        db.commit()

    stats["total"] = len(updates)
    return stats


def phase3_geocode_from_place(db: sqlite3.Connection, *, dry_run: bool = False) -> dict:
    """Phase 3.3a: Copy coordinates from place centroid for entities with placeId but no coords."""
    stats = {"assigned": 0}

    place_coords = {}
    for pid, coords_raw in db.execute(
        "SELECT id, coordinates FROM entities WHERE type='place' AND coordinates IS NOT NULL"
    ).fetchall():
        coords = _parse_json(coords_raw)
        if isinstance(coords, list) and len(coords) == 2:
            place_coords[pid] = coords

    rows = db.execute("""
        SELECT id, placeId FROM entities
        WHERE (coordinates IS NULL OR coordinates = '')
          AND placeId IS NOT NULL AND placeId != ''
    """).fetchall()

    updates = []
    for entity_id, place_id in rows:
        if place_id in place_coords:
            coords = place_coords[place_id]
            updates.append((json.dumps(coords), entity_id))
            stats["assigned"] += 1

    if not dry_run and updates:
        db.executemany("UPDATE entities SET coordinates=? WHERE id=?", updates)
        db.commit()

    stats["total"] = len(updates)
    return stats


def phase3_fix_near_relationships(db: sqlite3.Connection, *, dry_run: bool = False) -> dict:
    """Phase 3.6: Remove near-relationships where endpoint has no coordinates or distance > 50km."""
    stats = {"removed_no_coords": 0, "removed_far": 0}

    broken = db.execute("""
        SELECT r.rowid
        FROM relationships r
        JOIN entities e1 ON r.from_id = e1.id
        JOIN entities e2 ON r.to_id = e2.id
        WHERE r.type = 'near'
          AND (e1.coordinates IS NULL OR e1.coordinates = ''
               OR e2.coordinates IS NULL OR e2.coordinates = '')
    """).fetchall()

    stats["removed_no_coords"] = len(broken)
    remove_rowids = [r[0] for r in broken]

    far = db.execute("""
        SELECT r.rowid, e1.coordinates, e2.coordinates
        FROM relationships r
        JOIN entities e1 ON r.from_id = e1.id
        JOIN entities e2 ON r.to_id = e2.id
        WHERE r.type = 'near'
          AND e1.coordinates IS NOT NULL AND e1.coordinates != ''
          AND e2.coordinates IS NOT NULL AND e2.coordinates != ''
    """).fetchall()

    import math
    for rowid, c1_raw, c2_raw in far:
        try:
            c1 = json.loads(c1_raw) if isinstance(c1_raw, str) else c1_raw
            c2 = json.loads(c2_raw) if isinstance(c2_raw, str) else c2_raw
            lat1, lng1 = math.radians(c1[0]), math.radians(c1[1])
            lat2, lng2 = math.radians(c2[0]), math.radians(c2[1])
            dlat, dlng = lat2 - lat1, lng2 - lng1
            a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlng/2)**2
            dist = 6371.0 * 2 * math.asin(math.sqrt(a))
            if dist > 50.0:
                remove_rowids.append(rowid)
                stats["removed_far"] += 1
        except (TypeError, IndexError, ValueError, json.JSONDecodeError):
            pass

    if not dry_run and remove_rowids:
        placeholders = ",".join("?" * len(remove_rowids))
        db.execute(f"DELETE FROM relationships WHERE rowid IN ({placeholders})", remove_rowids)
        db.commit()

    stats["total_removed"] = len(remove_rowids)
    return stats


def phase3_fix_produced_in_conflicts(db: sqlite3.Connection, *, dry_run: bool = False) -> dict:
    """Remove produced_in relationships where endpoints have conflicting areas."""
    stats = {"removed": 0}

    conflicts = db.execute("""
        SELECT r.rowid
        FROM relationships r
        JOIN entities e1 ON r.from_id = e1.id
        JOIN entities e2 ON r.to_id = e2.id
        WHERE r.type = 'produced_in'
          AND e1.area IS NOT NULL AND e1.area != ''
          AND e2.area IS NOT NULL AND e2.area != ''
          AND e1.area != e2.area
    """).fetchall()

    stats["removed"] = len(conflicts)

    if not dry_run and conflicts:
        rowids = [r[0] for r in conflicts]
        placeholders = ",".join("?" * len(rowids))
        db.execute(f"DELETE FROM relationships WHERE rowid IN ({placeholders})", rowids)
        db.commit()

    return stats


SEASON_TYPES = {"product", "experience", "dish", "attraction", "nature", "craft_village", "event", "accommodation"}
SKIP_SEASON_TYPES = {"person", "history", "place", "itinerary", "organization", "drink", "economy"}

def _llm_call(prompt: str, system: str = "", *, model: str = "", retries: int = 2) -> str:
    """Call LLM API (OpenAI-compatible)."""
    import os
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
    except Exception:
        pass
    from openai import OpenAI

    client = OpenAI(
        base_url=os.environ.get("LLM_BASE_URL", ""),
        api_key=os.environ.get("LLM_API_KEY", ""),
        timeout=90,
    )
    llm_model = model or os.environ.get("LLM_MODEL", "cx/gpt-5.5")

    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})

    for attempt in range(retries + 1):
        try:
            import time
            r = client.chat.completions.create(
                model=llm_model, messages=msgs,
                temperature=0.3, max_tokens=4000,
            )
            return r.choices[0].message.content.strip()
        except Exception as e:
            if attempt < retries:
                import time
                time.sleep(3 * (attempt + 1))
            else:
                raise


def _parse_llm_json(text: str) -> Any:
    """Extract JSON from LLM response (handles markdown fences)."""
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"(\[.*\])", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass
        m = re.search(r"(\{.*\})", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass
    return None


def phase3_llm_season(db: sqlite3.Connection, *, dry_run: bool = False, batch_size: int = 25) -> dict:
    """Phase 3.4: LLM enrichment for season data."""
    stats = {"enriched": 0, "skipped_type": 0, "llm_calls": 0, "failed": 0}

    rows = db.execute("""
        SELECT id, name, type, summary, area
        FROM entities
        WHERE (season IS NULL OR season = '' OR season = 'null')
          AND type NOT IN ('person', 'history', 'place', 'itinerary', 'organization', 'drink', 'economy')
    """).fetchall()

    if dry_run:
        stats["candidates"] = len(rows)
        stats["batches_needed"] = (len(rows) + batch_size - 1) // batch_size
        return stats

    SYSTEM = """Bạn là chuyên gia du lịch Đồng bằng sông Cửu Long (Vĩnh Long, Bến Tre, Trà Vinh).
Cho danh sách entity, xác định mùa vụ/thời gian tốt nhất để trải nghiệm.

Trả về JSON array, mỗi phần tử:
{"id": "entity-id", "months": [1,2,...], "peak": [1,2,...], "text": "mô tả ngắn mùa vụ"}

Quy tắc:
- months: danh sách tháng hoạt động/có sẵn (1-12). Nếu quanh năm → [1..12]
- peak: tháng cao điểm/tốt nhất (subset of months). Nếu không rõ → []
- text: 1-2 câu tiếng Việt mô tả mùa vụ
- Sản phẩm OCOP/nông sản: theo mùa thu hoạch vùng ĐBSCL
- Món ăn: theo mùa nguyên liệu
- Trải nghiệm/điểm đến: mùa du lịch (tháng 10-4 mùa khô = cao điểm)
- Lễ hội: theo lịch tổ chức
- Nếu không đủ thông tin → months=[], peak=[], text="Chưa xác định mùa vụ"
CHỈ trả về JSON array, không giải thích."""

    total = len(rows)

    for batch_start in range(0, total, batch_size):
        batch = rows[batch_start:batch_start + batch_size]
        entities_text = "\n".join(
            f"- id: {eid}, name: {name}, type: {etype}, area: {area or '?'}, summary: {(summary or '')[:100]}"
            for eid, name, etype, summary, area in batch
        )

        try:
            response = _llm_call(
                f"Xác định mùa vụ cho {len(batch)} entity sau:\n{entities_text}",
                system=SYSTEM,
                retries=3,
            )
            stats["llm_calls"] += 1

            result = _parse_llm_json(response)
            if not isinstance(result, list):
                stats["failed"] += 1
                print(f"  [season] batch {batch_start//batch_size + 1}: invalid response")
                continue

            id_to_season = {item["id"]: item for item in result if isinstance(item, dict) and "id" in item}
            batch_updates = []

            for eid, name, etype, summary, area in batch:
                season_data = id_to_season.get(eid)
                if not season_data:
                    continue

                months = season_data.get("months", [])
                peak = season_data.get("peak", [])
                text = season_data.get("text", "")

                if not isinstance(months, list):
                    months = []
                if not isinstance(peak, list):
                    peak = []
                months = [m for m in months if isinstance(m, int) and 1 <= m <= 12]
                peak = [m for m in peak if isinstance(m, int) and 1 <= m <= 12 and m in months]

                if months or text:
                    season = {"months": months, "peak": peak, "text": text}
                    batch_updates.append((json.dumps(season, ensure_ascii=False), eid))
                    stats["enriched"] += 1

            if batch_updates:
                db.executemany("UPDATE entities SET season=? WHERE id=?", batch_updates)
                db.commit()

            done = min(batch_start + batch_size, total)
            print(f"  [season] {done}/{total} processed, {stats['enriched']} enriched", flush=True)

        except Exception as e:
            stats["failed"] += 1
            print(f"  [season] batch error: {e}", flush=True)

    return stats


def phase4_enrich_attributes(db: sqlite3.Connection, *, dry_run: bool = False, batch_size: int = 20) -> dict:
    """Phase 4.1: LLM enrichment for entities with empty attributes."""
    stats = {"enriched": 0, "llm_calls": 0, "failed": 0}

    rows = db.execute("""
        SELECT id, name, type, summary, area
        FROM entities
        WHERE type != 'place'
          AND (attributes IS NULL OR attributes = '{}' OR attributes = '' OR attributes = 'null')
    """).fetchall()

    if dry_run:
        stats["candidates"] = len(rows)
        return stats

    SYSTEM = """Bạn là chuyên gia du lịch Đồng bằng sông Cửu Long (Vĩnh Long, Bến Tre, Trà Vinh).
Cho danh sách entity, sinh thông tin attributes cơ bản phù hợp với loại entity.

Trả về JSON array, mỗi phần tử:
{"id": "entity-id", "attrs": {"key": "value", ...}}

Quy tắc theo type:
- dish: price (giá ước lượng VND), address (nếu biết)
- product: price, weight/unit nếu biết
- accommodation: price (giá phòng/đêm), address, phone nếu biết
- attraction: hours (giờ mở cửa), admission_fee nếu có, address
- craft_village: address, products (sản phẩm chính)
- nature: hours nếu có, admission_fee nếu có
- experience: duration (thời lượng), price nếu có
- history: era (thời kỳ) nếu biết
- event: schedule (lịch tổ chức) nếu biết

Chỉ sinh thông tin bạn TỰ TIN biết. Không bịa địa chỉ cụ thể nếu không chắc.
CHỈ trả về JSON array, không giải thích."""

    total = len(rows)
    for batch_start in range(0, total, batch_size):
        batch = rows[batch_start:batch_start + batch_size]
        entities_text = "\n".join(
            f"- id: {eid}, name: {name}, type: {etype}, area: {area or '?'}, summary: {(summary or '')[:120]}"
            for eid, name, etype, summary, area in batch
        )

        try:
            response = _llm_call(
                f"Sinh attributes cho {len(batch)} entity:\n{entities_text}",
                system=SYSTEM, retries=3,
            )
            stats["llm_calls"] += 1
            result = _parse_llm_json(response)
            if not isinstance(result, list):
                stats["failed"] += 1
                continue

            id_to_attrs = {item["id"]: item.get("attrs", {}) for item in result
                           if isinstance(item, dict) and "id" in item}
            batch_updates = []
            for eid, name, etype, summary, area in batch:
                attrs = id_to_attrs.get(eid)
                if attrs and isinstance(attrs, dict) and len(attrs) > 0:
                    batch_updates.append((json.dumps(attrs, ensure_ascii=False), eid))
                    stats["enriched"] += 1

            if batch_updates:
                db.executemany("UPDATE entities SET attributes=? WHERE id=?", batch_updates)
                db.commit()

            done = min(batch_start + batch_size, total)
            print(f"  [attrs] {done}/{total} processed, {stats['enriched']} enriched", flush=True)

        except Exception as e:
            stats["failed"] += 1
            print(f"  [attrs] batch error: {e}", flush=True)

    return stats


def phase4_enrich_summary(db: sqlite3.Connection, *, dry_run: bool = False) -> dict:
    """Phase 4.2: LLM enrichment for entities missing summary."""
    stats = {"enriched": 0}

    rows = db.execute("""
        SELECT id, name, type, area FROM entities
        WHERE summary IS NULL OR summary = ''
    """).fetchall()

    if dry_run:
        stats["candidates"] = len(rows)
        return stats

    for eid, name, etype, area in rows:
        try:
            response = _llm_call(
                f"Viết mô tả ngắn 1-2 câu tiếng Việt cho: {name} (loại: {etype}, vùng: {area or '?'}). "
                "Chỉ trả về văn bản mô tả, không giải thích thêm.",
                retries=2,
            )
            summary = response.strip().strip('"').strip("'")
            if summary and len(summary) > 10:
                db.execute("UPDATE entities SET summary=? WHERE id=?", (summary, eid))
                db.commit()
                stats["enriched"] += 1
                print(f"  [summary] {eid}: {summary[:60]}...", flush=True)
        except Exception as e:
            print(f"  [summary] {eid} error: {e}", flush=True)

    return stats


def phase4_infer_placeid_llm(db: sqlite3.Connection, *, dry_run: bool = False, batch_size: int = 20) -> dict:
    """Phase 4.3: LLM inference for missing placeId — match entity to xã/phường."""
    stats = {"inferred": 0, "llm_calls": 0, "failed": 0, "no_match": 0}

    # Get all place names for matching
    places = db.execute("SELECT id, name FROM entities WHERE type='place'").fetchall()
    place_list = "\n".join(f"- {pid}: {pname}" for pid, pname in places)

    rows = db.execute("""
        SELECT id, name, type, summary, area, attributes
        FROM entities
        WHERE type NOT IN ('place', 'itinerary')
          AND (placeId IS NULL OR placeId = '')
    """).fetchall()

    if dry_run:
        stats["candidates"] = len(rows)
        return stats

    SYSTEM = f"""Bạn là chuyên gia địa lý Đồng bằng sông Cửu Long.
Cho danh sách entity và danh sách xã/phường, hãy xác định entity thuộc xã/phường nào.

Danh sách xã/phường (id: tên):
{place_list}

Trả về JSON array:
[{{"id": "entity-id", "placeId": "place-id"}}]

Quy tắc:
- Chỉ gán placeId khi BẠN CHẮC CHẮN entity thuộc xã/phường đó
- Dựa vào tên, area, address, summary để suy luận
- Nếu không chắc → placeId: null
CHỈ trả về JSON array."""

    total = len(rows)
    for batch_start in range(0, total, batch_size):
        batch = rows[batch_start:batch_start + batch_size]
        entities_text = "\n".join(
            f"- id: {eid}, name: {name}, type: {etype}, area: {area or '?'}, summary: {(summary or '')[:80]}"
            for eid, name, etype, summary, area, _ in batch
        )

        try:
            response = _llm_call(
                f"Xác định placeId cho {len(batch)} entity:\n{entities_text}",
                system=SYSTEM, retries=3,
            )
            stats["llm_calls"] += 1
            result = _parse_llm_json(response)
            if not isinstance(result, list):
                stats["failed"] += 1
                continue

            place_ids = {p[0] for p in places}
            batch_updates = []
            for item in result:
                if not isinstance(item, dict):
                    continue
                eid = item.get("id")
                pid = item.get("placeId")
                if eid and pid and pid in place_ids:
                    batch_updates.append((pid, eid))
                    stats["inferred"] += 1
                elif eid and not pid:
                    stats["no_match"] += 1

            if batch_updates:
                db.executemany("UPDATE entities SET placeId=? WHERE id=?", batch_updates)
                db.commit()

            done = min(batch_start + batch_size, total)
            print(f"  [placeId] {done}/{total} processed, {stats['inferred']} inferred", flush=True)

        except Exception as e:
            stats["failed"] += 1
            print(f"  [placeId] batch error: {e}", flush=True)

    return stats


def phase4_geocode_from_place_retry(db: sqlite3.Connection, *, dry_run: bool = False) -> dict:
    """Phase 4.4: Retry geocoding from place for entities that now have placeId."""
    stats = {"geocoded": 0}

    rows = db.execute("""
        SELECT e.id, e.placeId, p.coordinates
        FROM entities e
        JOIN entities p ON e.placeId = p.id
        WHERE (e.coordinates IS NULL OR e.coordinates = '' OR e.coordinates = 'null')
          AND p.coordinates IS NOT NULL AND p.coordinates != '' AND p.coordinates != 'null'
          AND e.type != 'place'
    """).fetchall()

    if dry_run:
        stats["candidates"] = len(rows)
        return stats

    updates = []
    for eid, pid, pcoords_raw in rows:
        try:
            pcoords = json.loads(pcoords_raw) if isinstance(pcoords_raw, str) else pcoords_raw
            if isinstance(pcoords, list) and len(pcoords) == 2:
                updates.append((json.dumps(pcoords), eid))
                stats["geocoded"] += 1
        except (json.JSONDecodeError, TypeError):
            pass

    if updates:
        db.executemany("UPDATE entities SET coordinates=? WHERE id=?", updates)
        db.commit()

    return stats


def phase5_fix_area_from_place(db: sqlite3.Connection, *, dry_run: bool = False) -> dict:
    """Phase 5.1: Set area from placeId's place entity area."""
    stats = {"fixed": 0}
    rows = db.execute("""
        SELECT e.id, p.area
        FROM entities e
        JOIN entities p ON e.placeId = p.id
        WHERE e.type != 'place'
          AND (e.area IS NULL OR e.area = '')
          AND p.area IS NOT NULL AND p.area != ''
    """).fetchall()

    if dry_run:
        stats["candidates"] = len(rows)
        return stats

    if rows:
        db.executemany("UPDATE entities SET area=? WHERE id=?",
                       [(area, eid) for eid, area in rows])
        db.commit()
        stats["fixed"] = len(rows)
    return stats


def phase5_infer_area_llm(db: sqlite3.Connection, *, dry_run: bool = False, batch_size: int = 25) -> dict:
    """Phase 5.2: LLM inference for missing area."""
    stats = {"inferred": 0, "llm_calls": 0, "failed": 0}

    rows = db.execute("""
        SELECT id, name, type, summary FROM entities
        WHERE type != 'place'
          AND (area IS NULL OR area = '')
    """).fetchall()

    if dry_run:
        stats["candidates"] = len(rows)
        return stats

    SYSTEM = """Xác định vùng cho các entity du lịch/OCOP ở Đồng bằng sông Cửu Long.
Mỗi entity thuộc 1 trong 3 vùng: vinh-long, ben-tre, tra-vinh.

Trả về JSON array: [{"id": "...", "area": "vinh-long|ben-tre|tra-vinh"}]

Quy tắc:
- Dựa vào tên, summary, đặc sản vùng miền để suy luận
- Nếu không đủ thông tin → area: null
CHỈ trả về JSON array."""

    total = len(rows)
    for batch_start in range(0, total, batch_size):
        batch = rows[batch_start:batch_start + batch_size]
        text = "\n".join(
            f"- id: {eid}, name: {name}, type: {t}, summary: {(s or '')[:100]}"
            for eid, name, t, s in batch
        )
        try:
            response = _llm_call(f"Xác định vùng cho {len(batch)} entity:\n{text}",
                                 system=SYSTEM, retries=3)
            stats["llm_calls"] += 1
            result = _parse_llm_json(response)
            if not isinstance(result, list):
                stats["failed"] += 1
                continue

            VALID = {"vinh-long", "ben-tre", "tra-vinh"}
            batch_updates = []
            for item in result:
                if not isinstance(item, dict):
                    continue
                eid, area = item.get("id"), item.get("area")
                if eid and area and area in VALID:
                    batch_updates.append((area, eid))
                    stats["inferred"] += 1

            if batch_updates:
                db.executemany("UPDATE entities SET area=? WHERE id=?", batch_updates)
                db.commit()

            done = min(batch_start + batch_size, total)
            print(f"  [area] {done}/{total} processed, {stats['inferred']} inferred", flush=True)
        except Exception as e:
            stats["failed"] += 1
            print(f"  [area] batch error: {e}", flush=True)

    return stats


def phase5_geocode_places(db: sqlite3.Connection, *, dry_run: bool = False) -> dict:
    """Phase 5.3: Geocode place entities (xã/phường) via OSM Nominatim."""
    stats = {"geocoded": 0, "miss": 0}

    sys.path.insert(0, str(ROOT / "agent"))
    from geocode import geocode

    rows = db.execute("""
        SELECT id, name, area FROM entities
        WHERE type = 'place'
          AND (coordinates IS NULL OR coordinates = '' OR coordinates = 'null')
    """).fetchall()

    if dry_run:
        stats["candidates"] = len(rows)
        return stats

    AREA_TO_PROVINCE = {
        "vinh-long": "Vĩnh Long",
        "ben-tre": "Bến Tre",
        "tra-vinh": "Trà Vinh",
    }
    import time
    updates = []
    total = len(rows)
    for i, (eid, name, area) in enumerate(rows):
        province = AREA_TO_PROVINCE.get(area, "")
        query = f"{name}, {province}" if province else name
        try:
            coords = geocode(query)
            if coords:
                lat, lng = coords
                if 9.0 <= lat <= 11.0 and 105.0 <= lng <= 107.0:
                    updates.append((json.dumps([lat, lng]), eid))
                    stats["geocoded"] += 1
                else:
                    stats["miss"] += 1
            else:
                stats["miss"] += 1
        except Exception:
            stats["miss"] += 1

        if (i + 1) % 25 == 0 or i == total - 1:
            print(f"  [geo-place] {i+1}/{total}, {stats['geocoded']} geocoded", flush=True)
        time.sleep(1.1)

    if updates:
        db.executemany("UPDATE entities SET coordinates=? WHERE id=?", updates)
        db.commit()

    return stats


def phase5_geocode_address(db: sqlite3.Connection, *, dry_run: bool = False) -> dict:
    """Phase 5.4: Geocode non-place entities that have address attribute."""
    stats = {"geocoded": 0, "miss": 0}

    sys.path.insert(0, str(ROOT / "agent"))
    from geocode import geocode

    AREA_TO_PROVINCE = {
        "vinh-long": "Vĩnh Long",
        "ben-tre": "Bến Tre",
        "tra-vinh": "Trà Vinh",
    }

    rows = db.execute("""
        SELECT id, name, attributes, area FROM entities
        WHERE type != 'place'
          AND (coordinates IS NULL OR coordinates = '' OR coordinates = 'null' OR coordinates = '[]')
    """).fetchall()

    candidates = []
    for eid, name, attrs_raw, area in rows:
        try:
            attrs = json.loads(attrs_raw) if isinstance(attrs_raw, str) else (attrs_raw or {})
        except (json.JSONDecodeError, TypeError):
            attrs = {}
        addr = attrs.get("address", "")
        if addr and len(addr) > 5:
            candidates.append((eid, name, addr, area))

    if dry_run:
        stats["candidates"] = len(candidates)
        return stats

    import time
    total = len(candidates)
    updates = []
    for i, (eid, name, addr, area) in enumerate(candidates):
        province = AREA_TO_PROVINCE.get(area, "")
        query = f"{addr}, {province}" if province else addr
        try:
            coords = geocode(query)
            if coords:
                lat, lng = coords
                if 9.0 <= lat <= 11.0 and 105.0 <= lng <= 107.0:
                    updates.append((json.dumps([lat, lng]), eid))
                    stats["geocoded"] += 1
                else:
                    stats["miss"] += 1
            else:
                stats["miss"] += 1
        except Exception:
            stats["miss"] += 1

        if (i + 1) % 25 == 0 or i == total - 1:
            print(f"  [geo-addr] {i+1}/{total}, {stats['geocoded']} geocoded", flush=True)
        time.sleep(1.1)

    if updates:
        db.executemany("UPDATE entities SET coordinates=? WHERE id=?", updates)
        db.commit()

    return stats


def phase5_review_confidence(db: sqlite3.Connection, *, dry_run: bool = False, batch_size: int = 20) -> dict:
    """Phase 5.5: LLM review low-confidence entities — validate or flag."""
    stats = {"reviewed": 0, "upgraded": 0, "llm_calls": 0, "failed": 0}

    rows = db.execute("""
        SELECT id, name, type, summary, area, confidence FROM entities
        WHERE confidence < 0.5
    """).fetchall()

    if dry_run:
        stats["candidates"] = len(rows)
        return stats

    SYSTEM = """Đánh giá chất lượng các entity du lịch/OCOP Đồng bằng sông Cửu Long.
Mỗi entity có confidence thấp (<0.5). Hãy đánh giá:
- Entity có thật (tên hợp lệ, không phải rác/trùng lặp)?
- Summary có ý nghĩa?
- Nên giữ hay loại?

Trả về JSON array: [{"id": "...", "valid": true/false, "confidence": 0.0-1.0, "reason": "..."}]
- valid=true + confidence>=0.6: entity hợp lệ, nâng confidence
- valid=true + confidence<0.6: giữ nguyên
- valid=false: entity rác/trùng/vô nghĩa
CHỈ trả về JSON array."""

    total = len(rows)
    for batch_start in range(0, total, batch_size):
        batch = rows[batch_start:batch_start + batch_size]
        text = "\n".join(
            f"- id: {eid}, name: {name}, type: {t}, area: {a or '?'}, confidence: {c}, summary: {(s or '')[:100]}"
            for eid, name, t, s, a, c in batch
        )
        try:
            response = _llm_call(f"Đánh giá {len(batch)} entity:\n{text}",
                                 system=SYSTEM, retries=3)
            stats["llm_calls"] += 1
            result = _parse_llm_json(response)
            if not isinstance(result, list):
                stats["failed"] += 1
                continue

            batch_updates = []
            for item in result:
                if not isinstance(item, dict):
                    continue
                eid = item.get("id")
                valid = item.get("valid")
                new_conf = item.get("confidence")
                if eid and valid and isinstance(new_conf, (int, float)) and new_conf >= 0.6:
                    batch_updates.append((min(new_conf, 1.0), eid))
                    stats["upgraded"] += 1
                stats["reviewed"] += 1

            if batch_updates:
                db.executemany("UPDATE entities SET confidence=? WHERE id=?", batch_updates)
                db.commit()

            done = min(batch_start + batch_size, total)
            print(f"  [conf] {done}/{total} reviewed, {stats['upgraded']} upgraded", flush=True)
        except Exception as e:
            stats["failed"] += 1
            print(f"  [conf] batch error: {e}", flush=True)

    return stats


def phase5_tag_source(db: sqlite3.Connection, *, dry_run: bool = False) -> dict:
    """Phase 5.6: Tag entities with missing source as auto-generated."""
    stats = {"tagged": 0}

    rows = db.execute("""
        SELECT id, type FROM entities
        WHERE source IS NULL OR source = '' OR source = 'null' OR source = '[]' OR source = '{}'
    """).fetchall()

    if dry_run:
        stats["candidates"] = len(rows)
        return stats

    updates = []
    for eid, etype in rows:
        src = [{"name": "vinhlong360 auto-learn", "type": "internal"}]
        updates.append((json.dumps(src, ensure_ascii=False), eid))
        stats["tagged"] += 1

    if updates:
        db.executemany("UPDATE entities SET source=? WHERE id=?", updates)
        db.commit()

    return stats


def phase3_geocode_osm(db: sqlite3.Connection, *, dry_run: bool = False) -> dict:
    """Phase 3.3b: Geocode entities with address text via OSM Nominatim."""
    stats = {"geocoded": 0, "cache_hit": 0, "miss": 0, "skipped": 0}

    sys.path.insert(0, str(ROOT / "agent"))
    from geocode import geocode, _load_cache, _norm

    AREA_TO_REGION = {
        "vinh-long": "Vĩnh Long",
        "ben-tre": "Bến Tre",
        "tra-vinh": "Trà Vinh",
    }

    rows = db.execute("""
        SELECT id, name, attributes, area, type
        FROM entities
        WHERE (coordinates IS NULL OR coordinates = '')
          AND type != 'place'
    """).fetchall()

    updates = []
    total = len(rows)
    for i, (entity_id, name, attrs_raw, area, etype) in enumerate(rows):
        attrs = _parse_json(attrs_raw) or {}
        address = attrs.get("address", "") or ""

        if not address or len(address.strip()) < 5:
            query_name = name
        else:
            query_name = f"{name}, {address}"

        region = AREA_TO_REGION.get(area, "Vĩnh Long")

        cache = _load_cache()
        cache_key = _norm(f"{query_name}|{region}")
        was_cached = cache_key in cache

        if dry_run:
            if was_cached:
                coords = cache.get(cache_key)
                if coords:
                    stats["cache_hit"] += 1
                    updates.append((json.dumps(coords), entity_id))
                else:
                    stats["miss"] += 1
            else:
                stats["skipped"] += 1
            continue

        coords = geocode(query_name, region=region)

        if coords:
            updates.append((json.dumps(coords), entity_id))
            stats["geocoded"] += 1
            if (stats["geocoded"] % 20) == 0:
                print(f"  [geocode] {stats['geocoded']} found, {i+1}/{total} processed")
        else:
            stats["miss"] += 1

    if not dry_run and updates:
        db.executemany("UPDATE entities SET coordinates=? WHERE id=?", updates)
        db.commit()

    stats["total_updates"] = len(updates)
    return stats


def print_stats(phase: str, stats: dict):
    print(f"\n{'='*50}")
    print(f"  {phase}")
    print(f"{'='*50}")
    for key, value in stats.items():
        if isinstance(value, Counter):
            print(f"  {key}:")
            for k, v in value.most_common():
                print(f"    {k}: {v}")
        else:
            print(f"  {key}: {value}")


def main():
    _configure_output()
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--phase", default="2", help="Phase to run: 2, 3, 3a, 3b, 3c, 4, 5, all")
    parser.add_argument("--check", action="store_true", help="Dry-run, report only")
    parser.add_argument("--db", type=Path, default=DB_PATH, help="Path to SQLite DB")
    args = parser.parse_args()

    db = sqlite3.connect(str(args.db))
    db.execute("PRAGMA journal_mode=WAL")

    phases = args.phase.lower()
    dry = args.check
    mode = "DRY RUN" if dry else "APPLY"
    print(f"[standardize] mode={mode}, phase={phases}, db={args.db}")

    total_count = db.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
    print(f"[standardize] {total_count} entities in DB")

    if phases in ("2", "all"):
        stats = phase2_normalize_formats(db, dry_run=dry)
        print_stats("Phase 2: Format Standardization", stats)

    if phases in ("3", "3a", "all"):
        stats = phase3_infer_area(db, dry_run=dry)
        print_stats("Phase 3.1: Infer Area", stats)

        stats = phase3_infer_placeid(db, dry_run=dry)
        print_stats("Phase 3.2: Infer PlaceId", stats)

        stats = phase3_geocode_from_place(db, dry_run=dry)
        print_stats("Phase 3.3a: Geocode from Place", stats)

    if phases in ("3", "3b", "all"):
        stats = phase3_geocode_osm(db, dry_run=dry)
        print_stats("Phase 3.3b: Geocode via OSM Nominatim", stats)

    if phases in ("3", "3c", "all"):
        stats = phase3_llm_season(db, dry_run=dry)
        print_stats("Phase 3.4: LLM Season Enrichment", stats)

    if phases in ("3", "3a", "3b", "3c", "all"):
        stats = phase3_fix_near_relationships(db, dry_run=dry)
        print_stats("Phase 3.6: Fix Near Relationships", stats)

        stats = phase3_fix_produced_in_conflicts(db, dry_run=dry)
        print_stats("Phase 3.7: Fix Produced_in Conflicts", stats)

    if phases in ("4", "all"):
        stats = phase4_enrich_attributes(db, dry_run=dry)
        print_stats("Phase 4.1: LLM Attribute Enrichment", stats)

        stats = phase4_enrich_summary(db, dry_run=dry)
        print_stats("Phase 4.2: LLM Summary Enrichment", stats)

        stats = phase4_infer_placeid_llm(db, dry_run=dry)
        print_stats("Phase 4.3: LLM PlaceId Inference", stats)

        stats = phase4_geocode_from_place_retry(db, dry_run=dry)
        print_stats("Phase 4.4: Geocode from Place (retry)", stats)

        stats = phase3_fix_near_relationships(db, dry_run=dry)
        print_stats("Phase 4.5: Fix Near Relationships (cleanup)", stats)

        stats = phase3_fix_produced_in_conflicts(db, dry_run=dry)
        print_stats("Phase 4.6: Fix Produced_in Conflicts (cleanup)", stats)

    if phases in ("5", "all"):
        stats = phase5_fix_area_from_place(db, dry_run=dry)
        print_stats("Phase 5.1: Fix Area from PlaceId", stats)

        stats = phase5_infer_area_llm(db, dry_run=dry)
        print_stats("Phase 5.2: LLM Area Inference", stats)

        stats = phase5_geocode_places(db, dry_run=dry)
        print_stats("Phase 5.3: Geocode Places (OSM)", stats)

        stats = phase5_geocode_address(db, dry_run=dry)
        print_stats("Phase 5.4: Geocode by Address (OSM)", stats)

        stats = phase4_geocode_from_place_retry(db, dry_run=dry)
        print_stats("Phase 5.5: Geocode from Place (retry)", stats)

        stats = phase5_review_confidence(db, dry_run=dry)
        print_stats("Phase 5.6: LLM Confidence Review", stats)

        stats = phase5_tag_source(db, dry_run=dry)
        print_stats("Phase 5.7: Tag Missing Source", stats)

        stats = phase3_fix_near_relationships(db, dry_run=dry)
        print_stats("Phase 5.8: Fix Near Relationships (final)", stats)

        stats = phase3_fix_produced_in_conflicts(db, dry_run=dry)
        print_stats("Phase 5.9: Fix Produced_in Conflicts (final)", stats)

    db.close()
    print(f"\n[standardize] Done ({mode})")


if __name__ == "__main__":
    main()
