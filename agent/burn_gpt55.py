"""
vinhlong360 — GPT 5.5 Token Burner: Enrichment Mega-Batch

Chạy SONG SONG tối đa để đốt token GPT 5.5 nhanh nhất:
  1. Enrich ALL entity descriptions (561 entities → rich Vietnamese descriptions)
  2. Generate SEO meta for ALL entities (title, description, keywords)
  3. Generate travel tips per entity
  4. Fill missing attributes (giờ mở cửa, giá, địa chỉ, tips)
  5. Generate 30+ NEW itineraries (all combos of area × interest × duration)
  6. Generate entity relationships / "nên đi cùng" suggestions
  7. Quality score + auto-tag all entities

Usage:
  python agent/burn_gpt55.py                    # run all tasks
  python agent/burn_gpt55.py --task enrich      # only enrich descriptions
  python agent/burn_gpt55.py --task seo         # only SEO meta
  python agent/burn_gpt55.py --task itineraries # only generate itineraries
  python agent/burn_gpt55.py --task tips        # only travel tips
  python agent/burn_gpt55.py --task attrs       # only fill attributes
  python agent/burn_gpt55.py --task relations   # only relationships
  python agent/burn_gpt55.py --task tags        # only auto-tagging
  python agent/burn_gpt55.py --workers 20       # more parallel workers (default 12)
  python agent/burn_gpt55.py --dry-run          # preview without saving
"""

import argparse
import json
import os
import re
import sys
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

AGENT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = AGENT_DIR.parent
sys.path.insert(0, str(AGENT_DIR))
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
load_dotenv(PROJECT_DIR / ".env")

from openai import OpenAI
from database import Database

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(AGENT_DIR / "data" / "burn_log.txt", encoding="utf-8"),
    ]
)
log = logging.getLogger("burn")

# ── Config ──
API_KEY = os.environ.get("LLM_API_KEY", "")
BASE_URL = os.environ.get("LLM_BASE_URL", "")
MODEL = os.environ.get("LLM_MODEL", "cx/gpt-5.5")
# Only use full model — mini not supported on this account

AREAS = ["vinh-long", "ben-tre", "tra-vinh"]
AREA_NAMES = {"vinh-long": "Vĩnh Long", "ben-tre": "Bến Tre", "tra-vinh": "Trà Vinh"}
TYPE_LABELS = {
    "attraction": "điểm tham quan",
    "experience": "trải nghiệm du lịch",
    "nature": "thiên nhiên/sinh thái",
    "history": "di tích lịch sử",
    "craft_village": "làng nghề",
    "dish": "món ăn đặc sản",
    "product": "sản phẩm/nông sản",
    "accommodation": "lưu trú",
    "event": "sự kiện/lễ hội",
    "person": "nhân vật",
    "organization": "tổ chức",
    "economy": "kinh tế",
}

INTERESTS = ["am_thuc", "lich_su", "thien_nhien", "van_hoa", "mua_sam", "tham_quan"]
INTEREST_LABELS = {
    "am_thuc": "ẩm thực", "lich_su": "lịch sử văn hóa",
    "thien_nhien": "thiên nhiên sinh thái", "van_hoa": "văn hóa dân gian",
    "mua_sam": "mua sắm đặc sản", "tham_quan": "tham quan tổng hợp",
}

db = Database()
tokens_used = {"input": 0, "output": 0, "calls": 0}


def _client():
    return OpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=60)


def _llm(prompt, model=None, temperature=0.7, max_tokens=1500):
    """Single LLM call with token tracking."""
    model = model or MODEL
    try:
        resp = _client().chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=60,
        )
        usage = resp.usage
        if usage:
            tokens_used["input"] += usage.prompt_tokens
            tokens_used["output"] += usage.completion_tokens
        tokens_used["calls"] += 1
        return resp.choices[0].message.content or ""
    except Exception as e:
        log.warning(f"LLM error: {e}")
        return ""


def _parse_json(text):
    """Extract JSON from LLM response."""
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    m = re.search(r"[\[{].*[\]}]", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    return None


# ═══════════════════════════════════════════════════════
# TASK 1: Enrich Entity Descriptions
# ═══════════════════════════════════════════════════════

def enrich_one(entity):
    """Generate rich Vietnamese description for one entity."""
    etype = TYPE_LABELS.get(entity["type"], entity["type"])
    area = AREA_NAMES.get(entity.get("area", ""), "Vĩnh Long")
    old_summary = entity.get("summary", "")
    attrs = entity.get("attributes") or {}
    addr = attrs.get("address", "")

    prompt = f"""Viết mô tả chi tiết 3-5 câu bằng tiếng Việt cho {etype} sau ở {area}:

Tên: {entity['name']}
Mô tả hiện tại: {old_summary}
Địa chỉ: {addr}
Loại: {etype}

Yêu cầu:
- Mô tả phải HẤP DẪN, giàu thông tin thực tế cho du khách
- Nêu điểm nổi bật, lý do nên đến, đặc trưng riêng
- Nếu là món ăn/đặc sản: nêu hương vị, nguyên liệu, cách thưởng thức
- Nếu là di tích: nêu niên đại, ý nghĩa lịch sử
- Nếu là thiên nhiên: nêu cảnh quan, hoạt động có thể làm
- Viết tự nhiên, không quảng cáo, CHỈ nêu sự thật
- KHÔNG bắt đầu bằng tên entity
- Chỉ trả văn bản thuần, không markdown"""

    result = _llm(prompt, model=MODEL, temperature=0.6, max_tokens=400)
    if result and len(result) > 30:
        return {"id": entity["id"], "summary": result.strip()}
    return None


def task_enrich(entities, dry_run=False, workers=12):
    """Enrich ALL entity descriptions."""
    log.info(f"=== TASK: Enrich descriptions ({len(entities)} entities) ===")
    updated = 0

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(enrich_one, e): e for e in entities}
        for f in as_completed(futures):
            result = f.result()
            if result:
                if not dry_run:
                    entity = futures[f]
                    entity["summary"] = result["summary"]
                    entity["updatedAt"] = datetime.now().strftime("%Y-%m-%d")
                    db.upsert_entity(entity)
                updated += 1
                if updated % 20 == 0:
                    log.info(f"  Enriched {updated}/{len(entities)} ... tokens: {tokens_used['output']:,}")

    log.info(f"  ✓ Enriched {updated} entities")
    return updated


# ═══════════════════════════════════════════════════════
# TASK 2: Generate SEO Meta
# ═══════════════════════════════════════════════════════

def seo_one(entity):
    """Generate SEO title, description, keywords for one entity."""
    etype = TYPE_LABELS.get(entity["type"], entity["type"])
    area = AREA_NAMES.get(entity.get("area", ""), "Vĩnh Long")

    prompt = f"""Tạo thẻ SEO cho trang web giới thiệu {etype} "{entity['name']}" ở {area}.

Mô tả: {(entity.get('summary', '') or '')[:200]}

Trả về JSON duy nhất:
{{"seo_title": "tiêu đề < 60 ký tự, có tên + khu vực + từ khóa du lịch", "seo_description": "mô tả < 155 ký tự, hấp dẫn, có call-to-action", "keywords": ["5-8 từ khóa SEO tiếng Việt"]}}

Chỉ trả JSON, không thêm gì."""

    result = _llm(prompt, model=MODEL, temperature=0.3, max_tokens=300)
    data = _parse_json(result)
    if data and "seo_title" in data:
        return {"id": entity["id"], "seo": data}
    return None


def task_seo(entities, dry_run=False, workers=12):
    """Generate SEO meta for ALL entities."""
    log.info(f"=== TASK: SEO meta ({len(entities)} entities) ===")
    updated = 0

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(seo_one, e): e for e in entities}
        for f in as_completed(futures):
            result = f.result()
            if result:
                if not dry_run:
                    entity = futures[f]
                    attrs = entity.get("attributes") or {}
                    if isinstance(attrs, str):
                        try:
                            attrs = json.loads(attrs)
                        except Exception:
                            attrs = {}
                    attrs["seo_title"] = result["seo"]["seo_title"]
                    attrs["seo_description"] = result["seo"]["seo_description"]
                    attrs["seo_keywords"] = result["seo"].get("keywords", [])
                    entity["attributes"] = attrs
                    entity["updatedAt"] = datetime.now().strftime("%Y-%m-%d")
                    db.upsert_entity(entity)
                updated += 1
                if updated % 20 == 0:
                    log.info(f"  SEO {updated}/{len(entities)} ... tokens: {tokens_used['output']:,}")

    log.info(f"  ✓ SEO generated for {updated} entities")
    return updated


# ═══════════════════════════════════════════════════════
# TASK 3: Generate Travel Tips
# ═══════════════════════════════════════════════════════

def tips_one(entity):
    """Generate practical travel tips for one entity."""
    etype = TYPE_LABELS.get(entity["type"], entity["type"])
    area = AREA_NAMES.get(entity.get("area", ""), "Vĩnh Long")

    prompt = f"""Viết 3-5 mẹo du lịch thực tế cho du khách khi đến {etype} "{entity['name']}" ở {area}.

Mô tả: {(entity.get('summary', '') or '')[:200]}

Trả về JSON:
{{"tips": ["mẹo 1 (1-2 câu)", "mẹo 2", "mẹo 3"], "best_time": "thời điểm tốt nhất để đến", "duration_suggest": "thời gian tham quan gợi ý", "nearby_food": "gợi ý ăn uống gần đó (nếu biết)"}}

Chỉ trả JSON, dựa trên kiến thức thực tế về {area}."""

    result = _llm(prompt, model=MODEL, temperature=0.5, max_tokens=500)
    data = _parse_json(result)
    if data and "tips" in data:
        return {"id": entity["id"], "tips_data": data}
    return None


def task_tips(entities, dry_run=False, workers=12):
    """Generate travel tips for ALL entities."""
    log.info(f"=== TASK: Travel tips ({len(entities)} entities) ===")
    updated = 0

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(tips_one, e): e for e in entities}
        for f in as_completed(futures):
            result = f.result()
            if result:
                if not dry_run:
                    entity = futures[f]
                    attrs = entity.get("attributes") or {}
                    if isinstance(attrs, str):
                        try:
                            attrs = json.loads(attrs)
                        except Exception:
                            attrs = {}
                    attrs["travel_tips"] = result["tips_data"].get("tips", [])
                    attrs["best_time"] = result["tips_data"].get("best_time", "")
                    attrs["duration_suggest"] = result["tips_data"].get("duration_suggest", "")
                    attrs["nearby_food"] = result["tips_data"].get("nearby_food", "")
                    entity["attributes"] = attrs
                    entity["updatedAt"] = datetime.now().strftime("%Y-%m-%d")
                    db.upsert_entity(entity)
                updated += 1
                if updated % 20 == 0:
                    log.info(f"  Tips {updated}/{len(entities)} ... tokens: {tokens_used['output']:,}")

    log.info(f"  ✓ Tips generated for {updated} entities")
    return updated


# ═══════════════════════════════════════════════════════
# TASK 4: Fill Missing Attributes
# ═══════════════════════════════════════════════════════

def attrs_one(entity):
    """Fill missing attributes using GPT knowledge."""
    etype = TYPE_LABELS.get(entity["type"], entity["type"])
    area = AREA_NAMES.get(entity.get("area", ""), "Vĩnh Long")
    existing_attrs = entity.get("attributes") or {}
    if isinstance(existing_attrs, str):
        try:
            existing_attrs = json.loads(existing_attrs)
        except Exception:
            existing_attrs = {}

    prompt = f"""Bổ sung thông tin thực tế cho {etype} "{entity['name']}" ở {area}.

Thông tin hiện có: {json.dumps(existing_attrs, ensure_ascii=False)[:300]}
Mô tả: {(entity.get('summary', '') or '')[:200]}

Trả về JSON với CÁC TRƯỜNG SAU (bỏ trống nếu không biết chắc):
{{
  "address": "địa chỉ chi tiết (xã, huyện, tỉnh)",
  "open_hours": "giờ mở cửa (vd: 7:00-17:00)",
  "admission_fee": "phí vào cửa (vd: Miễn phí / 20.000đ)",
  "phone": "số điện thoại (nếu biết)",
  "website": "website (nếu có)",
  "parking": "có/không, miễn phí/trả phí",
  "accessibility": "mô tả tiếp cận (xe máy, ô tô, thuyền...)",
  "highlights": ["3 điểm nổi bật nhất"],
  "tags": ["5-8 tag phân loại, vd: gia-dinh, cap-doi, chup-hinh, mien-phi"]
}}

CHỈ điền thông tin CÓ THẬT. Bỏ trống ("" hoặc []) nếu không chắc. Chỉ trả JSON."""

    result = _llm(prompt, model=MODEL, temperature=0.3, max_tokens=600)
    data = _parse_json(result)
    if data and isinstance(data, dict):
        # Only keep non-empty values
        cleaned = {k: v for k, v in data.items() if v and v != "" and v != []}
        if cleaned:
            return {"id": entity["id"], "new_attrs": cleaned}
    return None


def task_attrs(entities, dry_run=False, workers=12):
    """Fill missing attributes for entities."""
    # Focus on entities with few attributes
    targets = [e for e in entities if not _has_rich_attrs(e)]
    log.info(f"=== TASK: Fill attributes ({len(targets)}/{len(entities)} need enrichment) ===")
    updated = 0

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(attrs_one, e): e for e in targets}
        for f in as_completed(futures):
            result = f.result()
            if result:
                if not dry_run:
                    entity = futures[f]
                    attrs = entity.get("attributes") or {}
                    if isinstance(attrs, str):
                        try:
                            attrs = json.loads(attrs)
                        except Exception:
                            attrs = {}
                    # Merge — don't overwrite existing values
                    for k, v in result["new_attrs"].items():
                        if k not in attrs or not attrs[k]:
                            attrs[k] = v
                    entity["attributes"] = attrs
                    entity["updatedAt"] = datetime.now().strftime("%Y-%m-%d")
                    db.upsert_entity(entity)
                updated += 1
                if updated % 20 == 0:
                    log.info(f"  Attrs {updated}/{len(targets)} ... tokens: {tokens_used['output']:,}")

    log.info(f"  ✓ Attributes filled for {updated} entities")
    return updated


def _has_rich_attrs(entity):
    attrs = entity.get("attributes") or {}
    if isinstance(attrs, str):
        try:
            attrs = json.loads(attrs)
        except Exception:
            return False
    return len(attrs) >= 5


# ═══════════════════════════════════════════════════════
# TASK 5: Generate Itineraries (MASSIVE)
# ═══════════════════════════════════════════════════════

def gen_itinerary(area, interest, days, entities_in_area):
    """Generate one complete itinerary using GPT 5.5."""
    area_name = AREA_NAMES.get(area, area)
    interest_label = INTEREST_LABELS.get(interest, interest)

    # Pick relevant entities for context
    relevant = [e for e in entities_in_area if e.get("area") == area][:30]
    entity_list = "\n".join(
        f"- {e['name']} ({TYPE_LABELS.get(e['type'], e['type'])}): {(e.get('summary','') or '')[:80]}"
        for e in relevant
    )

    prompt = f"""Tạo lịch trình du lịch {days} ngày tại {area_name} (tỉnh Vĩnh Long mới) với chủ đề {interest_label}.

Các địa điểm/đặc sản có trong hệ thống:
{entity_list}

Trả về JSON:
{{
  "title": "Tiêu đề hấp dẫn (tiếng Việt)",
  "summary": "Tóm tắt 2-3 câu về lịch trình",
  "stops": [
    {{
      "name": "tên điểm (phải khớp với danh sách trên nếu có)",
      "time": "08:00",
      "type": "attraction/dish/nature/history/...",
      "summary": "mô tả ngắn hoạt động tại đây",
      "note": "ghi chú thực tế (giá, mẹo...)"
    }}
  ],
  "tips": ["3 mẹo du lịch cho lịch trình này"]
}}

Yêu cầu:
- {5 * days} đến {7 * days} điểm dừng, xen kẽ ăn uống
- ƯU TIÊN dùng tên từ danh sách trên, nhưng có thể thêm nếu cần
- Sắp xếp hợp lý theo địa lý (gần nhau đi cùng buổi)
- Thời gian thực tế, có bữa sáng/trưa/tối
- Chỉ trả JSON"""

    result = _llm(prompt, model=MODEL, temperature=0.7, max_tokens=2000)
    data = _parse_json(result)
    if data and "stops" in data:
        # Try to link stops to actual entity IDs
        entity_map = {e["name"].lower(): e for e in relevant}
        for stop in data["stops"]:
            name_lower = stop.get("name", "").lower()
            matched = entity_map.get(name_lower)
            if matched:
                stop["id"] = matched["id"]
                if not stop.get("type"):
                    stop["type"] = matched["type"]
                coords = matched.get("coordinates")
                if coords:
                    stop["coordinates"] = coords

        slug = f"{area}-{interest}-{days}d"
        return {
            "id": slug,
            "title": data.get("title", f"Lịch trình {days} ngày {interest_label} {area_name}"),
            "area": area,
            "duration": f"{days} ngày",
            "summary": data.get("summary", ""),
            "stops": data["stops"],
        }
    return None


def task_itineraries(entities, dry_run=False, workers=12):
    """Generate itineraries for ALL area × interest × duration combos."""
    combos = []
    for area in AREAS:
        for interest in INTERESTS:
            for days in [1, 2, 3]:
                combos.append((area, interest, days))

    # Also special combos
    for area in AREAS:
        combos.append((area, "tong_hop", 1))
        combos.append((area, "tong_hop", 2))
    # Cross-area itineraries
    combos.append(("vinh-long", "tong_hop", 4))
    combos.append(("ben-tre", "tong_hop", 5))

    log.info(f"=== TASK: Generate itineraries ({len(combos)} combinations) ===")
    generated = 0

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {}
        for area, interest, days in combos:
            f = pool.submit(gen_itinerary, area, interest, days, entities)
            futures[f] = (area, interest, days)

        for f in as_completed(futures):
            result = f.result()
            if result:
                if not dry_run:
                    db.upsert_itinerary(result)
                generated += 1
                combo = futures[f]
                log.info(f"  ✓ Itinerary: {result['title'][:60]}... ({combo[0]}/{combo[1]}/{combo[2]}d)")

    log.info(f"  ✓ Generated {generated} itineraries")
    return generated


# ═══════════════════════════════════════════════════════
# TASK 6: Entity Relationships
# ═══════════════════════════════════════════════════════

def relations_batch(batch_entities, all_entities):
    """Find relationships for a batch of entities."""
    names_ctx = "\n".join(f"- {e['id']}: {e['name']} ({e['type']})" for e in all_entities[:100])

    results = []
    for entity in batch_entities:
        prompt = f"""Cho entity "{entity['name']}" (loại: {entity['type']}, khu vực: {entity.get('area','')}),
tìm các mối quan hệ với entities khác trong danh sách dưới.

Danh sách entities:
{names_ctx}

Trả về JSON:
{{"relations": [
  {{"target_id": "id-cua-entity-lien-quan", "type": "near|part_of|pairs_with|similar|famous_for", "reason": "lý do 1 câu"}}
]}}

Các loại quan hệ:
- near: gần nhau, nên đi cùng buổi
- part_of: thuộc về / nằm trong
- pairs_with: nên kết hợp (vd: món ăn + nơi bán)
- similar: tương tự, thay thế được
- famous_for: nổi tiếng vì

Tối đa 5 mối quan hệ. Chỉ trả JSON."""

        result = _llm(prompt, model=MODEL, temperature=0.3, max_tokens=400)
        data = _parse_json(result)
        if data and "relations" in data:
            for rel in data["relations"]:
                if rel.get("target_id") and rel.get("type"):
                    results.append({
                        "from_id": entity["id"],
                        "to_id": rel["target_id"],
                        "type": rel["type"],
                    })
    return results


def task_relations(entities, dry_run=False, workers=12):
    """Generate entity relationships."""
    log.info(f"=== TASK: Entity relationships ({len(entities)} entities) ===")

    # Batch entities into groups of 5 for efficiency
    batches = [entities[i:i+5] for i in range(0, len(entities), 5)]
    total_rels = 0

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(relations_batch, batch, entities): batch for batch in batches}
        for f in as_completed(futures):
            rels = f.result()
            for rel in rels:
                if not dry_run:
                    try:
                        db.add_relationship(rel["from_id"], rel["to_id"], rel["type"])
                    except Exception:
                        pass
                total_rels += 1
            if total_rels % 50 == 0 and total_rels > 0:
                log.info(f"  Relations: {total_rels} found ... tokens: {tokens_used['output']:,}")

    log.info(f"  ✓ Generated {total_rels} relationships")
    return total_rels


# ═══════════════════════════════════════════════════════
# TASK 7: Auto-Tagging & Quality Scoring
# ═══════════════════════════════════════════════════════

def tag_one(entity):
    """Auto-tag and quality-score an entity."""
    prompt = f"""Đánh giá và gắn tag cho entity du lịch sau:

Tên: {entity['name']}
Loại: {entity['type']}
Mô tả: {(entity.get('summary', '') or '')[:200]}
Khu vực: {entity.get('area', '')}

Trả về JSON:
{{
  "quality_score": 0.0-1.0 (chất lượng thông tin: 0.3=thiếu nhiều, 0.7=đầy đủ, 1.0=xuất sắc),
  "tourist_rating": 1-5 (độ hấp dẫn du lịch: 1=bình thường, 5=must-visit),
  "audience": ["gia-dinh", "cap-doi", "nhom-ban", "mot-minh", "nguoi-gia"],
  "season_tags": ["mua-kho", "mua-mua", "quanh-nam"],
  "activity_tags": ["tham-quan", "chup-hinh", "an-uong", "mua-sam", "nghi-duong", "kham-pha", "hoc-hoi"],
  "budget_level": "thap/trung_binh/cao",
  "visit_duration_minutes": 30-240,
  "one_liner": "1 câu marketing hấp dẫn < 80 ký tự cho entity này"
}}

Dựa trên kiến thức thực tế. Chỉ trả JSON."""

    result = _llm(prompt, model=MODEL, temperature=0.4, max_tokens=400)
    data = _parse_json(result)
    if data and "quality_score" in data:
        return {"id": entity["id"], "tags": data}
    return None


def task_tags(entities, dry_run=False, workers=12):
    """Auto-tag and score ALL entities."""
    log.info(f"=== TASK: Auto-tagging ({len(entities)} entities) ===")
    updated = 0

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(tag_one, e): e for e in entities}
        for f in as_completed(futures):
            result = f.result()
            if result:
                if not dry_run:
                    entity = futures[f]
                    attrs = entity.get("attributes") or {}
                    if isinstance(attrs, str):
                        try:
                            attrs = json.loads(attrs)
                        except Exception:
                            attrs = {}
                    tags_data = result["tags"]
                    attrs["tourist_rating"] = tags_data.get("tourist_rating")
                    attrs["audience"] = tags_data.get("audience", [])
                    attrs["season_tags"] = tags_data.get("season_tags", [])
                    attrs["activity_tags"] = tags_data.get("activity_tags", [])
                    attrs["budget_level"] = tags_data.get("budget_level", "")
                    attrs["visit_duration_minutes"] = tags_data.get("visit_duration_minutes")
                    attrs["one_liner"] = tags_data.get("one_liner", "")
                    entity["attributes"] = attrs
                    # Also update confidence based on quality score
                    qs = tags_data.get("quality_score", 0.5)
                    entity["confidence"] = round(min(1.0, max(0.1, qs)), 2)
                    entity["updatedAt"] = datetime.now().strftime("%Y-%m-%d")
                    db.upsert_entity(entity)
                updated += 1
                if updated % 20 == 0:
                    log.info(f"  Tags {updated}/{len(entities)} ... tokens: {tokens_used['output']:,}")

    log.info(f"  ✓ Tagged {updated} entities")
    return updated


# ═══════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════

ALL_TASKS = ["enrich", "seo", "tips", "attrs", "itineraries", "relations", "tags"]

def main():
    parser = argparse.ArgumentParser(description="GPT 5.5 Token Burner")
    parser.add_argument("--task", choices=ALL_TASKS + ["all"], default="all")
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    tasks = ALL_TASKS if args.task == "all" else [args.task]
    workers = args.workers
    dry_run = args.dry_run

    log.info("=" * 60)
    log.info(f"GPT 5.5 TOKEN BURNER — {datetime.now()}")
    log.info(f"Tasks: {tasks}, Workers: {workers}, Dry run: {dry_run}")
    log.info(f"Model: {MODEL} / Mini: {MODEL}")
    log.info("=" * 60)

    # Load all entities
    entities = db.list_entities(limit=9999)
    log.info(f"Loaded {len(entities)} entities from database")

    start = time.time()
    results = {}

    for task in tasks:
        task_start = time.time()
        if task == "enrich":
            results[task] = task_enrich(entities, dry_run, workers)
        elif task == "seo":
            results[task] = task_seo(entities, dry_run, workers)
        elif task == "tips":
            results[task] = task_tips(entities, dry_run, workers)
        elif task == "attrs":
            results[task] = task_attrs(entities, dry_run, workers)
        elif task == "itineraries":
            results[task] = task_itineraries(entities, dry_run, workers)
        elif task == "relations":
            results[task] = task_relations(entities, dry_run, workers)
        elif task == "tags":
            results[task] = task_tags(entities, dry_run, workers)

        elapsed = time.time() - task_start
        log.info(f"  Task '{task}' done in {elapsed:.0f}s")

        # Reload entities after modifications
        if task in ["enrich", "seo", "tips", "attrs", "tags"] and not dry_run:
            entities = db.list_entities(limit=9999)

    total_time = time.time() - start

    log.info("=" * 60)
    log.info("SUMMARY")
    log.info("=" * 60)
    for task, count in results.items():
        log.info(f"  {task}: {count}")
    log.info(f"  Total LLM calls: {tokens_used['calls']:,}")
    log.info(f"  Input tokens: {tokens_used['input']:,}")
    log.info(f"  Output tokens: {tokens_used['output']:,}")
    log.info(f"  Total tokens: {tokens_used['input'] + tokens_used['output']:,}")
    log.info(f"  Time: {total_time:.0f}s ({total_time/60:.1f} min)")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
