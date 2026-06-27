"""
Enrich entities with detailed descriptions (multi-paragraph).

Reads entities from SQLite DB that have empty `description` field,
generates rich Vietnamese content via LLM, saves back to DB.

Usage:
  python scripts/enrich_descriptions.py                    # all non-place entities
  python scripts/enrich_descriptions.py --type attraction  # only attractions
  python scripts/enrich_descriptions.py --limit 20         # first 20
  python scripts/enrich_descriptions.py --id hai-chom-chom-an-binh  # single entity
  python scripts/enrich_descriptions.py --dry-run          # preview without saving
  python scripts/enrich_descriptions.py --workers 6        # parallel workers
"""

import argparse
import json
import os
import sys
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
AGENT_DIR = PROJECT_DIR / "agent"
sys.path.insert(0, str(AGENT_DIR))
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
for _envp in [PROJECT_DIR / ".env", PROJECT_DIR.parent / ".env"]:
    if _envp.exists():
        load_dotenv(_envp)
        break

from openai import OpenAI
from database import Database

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("enrich")

API_KEY = os.environ.get("LLM_API_KEY", "")
BASE_URL = os.environ.get("LLM_BASE_URL", "")
MODEL = os.environ.get("LLM_MODEL", "cx/gpt-5.5")

AREA_NAMES = {"vinh-long": "Vĩnh Long", "ben-tre": "Bến Tre", "tra-vinh": "Trà Vinh"}
TYPE_LABELS = {
    "attraction": "điểm tham quan",
    "experience": "trải nghiệm du lịch",
    "nature": "thiên nhiên/sinh thái",
    "history": "di tích lịch sử",
    "craft_village": "làng nghề truyền thống",
    "dish": "món ăn đặc sản",
    "product": "sản phẩm/nông sản địa phương",
    "accommodation": "cơ sở lưu trú",
    "event": "sự kiện/lễ hội",
    "person": "nhân vật lịch sử",
    "organization": "tổ chức",
    "cafe": "quán cà phê",
    "restaurant": "nhà hàng",
    "drink": "thức uống",
    "facility": "tiện ích công cộng",
    "economy": "kinh tế địa phương",
}

PRIORITY_TYPES = ["attraction", "experience", "nature", "history", "craft_village",
                  "dish", "product", "event", "accommodation",
                  "cafe", "restaurant", "drink", "facility", "organization",
                  "person", "economy", "itinerary"]

db = Database()
stats = {"success": 0, "skip": 0, "fail": 0, "tokens": 0}


def _client():
    return OpenAI(api_key=API_KEY, base_url=BASE_URL)


def _build_prompt(entity):
    etype = TYPE_LABELS.get(entity["type"], entity["type"])
    area = AREA_NAMES.get(entity.get("area", ""), "miền Tây")
    summary = entity.get("summary", "") or ""
    attrs = entity.get("attributes") or {}
    season = entity.get("season") or {}

    context_parts = [f"Tên: {entity['name']}", f"Loại: {etype}", f"Vùng: {area}"]
    if summary:
        context_parts.append(f"Tóm tắt: {summary}")
    if attrs.get("address"):
        context_parts.append(f"Địa chỉ: {attrs['address']}")
    if attrs.get("hours"):
        context_parts.append(f"Giờ mở cửa: {attrs['hours']}")
    if attrs.get("price") or attrs.get("fee"):
        context_parts.append(f"Giá/phí: {attrs.get('price') or attrs.get('fee')}")
    if attrs.get("best_time"):
        context_parts.append(f"Thời điểm tốt nhất: {attrs['best_time']}")
    if attrs.get("ocop"):
        context_parts.append(f"Chứng nhận OCOP: {attrs['ocop']}")
    if attrs.get("key_facts"):
        context_parts.append(f"Thông tin nổi bật: {attrs['key_facts']}")
    if attrs.get("transport"):
        context_parts.append(f"Di chuyển: {attrs['transport']}")
    if attrs.get("amenities"):
        am = attrs["amenities"]
        if isinstance(am, list):
            am = ", ".join(am)
        context_parts.append(f"Tiện ích: {am}")
    if season.get("months"):
        months = ", ".join([f"T{m}" for m in season["months"]])
        context_parts.append(f"Mùa vụ: {months}")
        if season.get("peak"):
            peak = ", ".join([f"T{m}" for m in season["peak"]])
            context_parts.append(f"Rộ nhất: {peak}")

    context = "\n".join(context_parts)

    type_guide = ""
    if entity["type"] in ("dish", "drink"):
        type_guide = """- Mô tả hương vị, nguyên liệu chính, cách chế biến đặc trưng
- Nêu cách thưởng thức đúng điệu (ăn kèm gì, uống gì)
- Lịch sử hoặc giai thoại gắn với món ăn (nếu có)
- Nơi nào bán ngon nhất, giá cả tham khảo"""
    elif entity["type"] in ("attraction", "experience", "nature"):
        type_guide = """- Cảnh quan, không khí, những gì du khách sẽ thấy khi đến
- Hoạt động có thể tham gia (chèo thuyền, hái trái cây, chụp ảnh...)
- Thời điểm đẹp nhất trong ngày/năm để ghé thăm
- Mẹo hữu ích cho lần đầu đến"""
    elif entity["type"] == "history":
        type_guide = """- Niên đại, bối cảnh lịch sử ra đời
- Ý nghĩa văn hóa, tâm linh hoặc lịch sử
- Kiến trúc, hiện vật đáng chú ý
- Lễ hội hoặc sự kiện liên quan"""
    elif entity["type"] == "craft_village":
        type_guide = """- Lịch sử hình thành làng nghề, bao nhiêu đời truyền thừa
- Quy trình sản xuất thủ công đặc trưng
- Sản phẩm nổi bật, có thể mua làm quà
- Trải nghiệm du khách: xem nghệ nhân làm việc, tự tay thử"""
    elif entity["type"] == "product":
        type_guide = """- Đặc điểm sản phẩm, chất lượng, hương vị (nếu thực phẩm)
- Quy trình sản xuất, nguồn nguyên liệu
- Chứng nhận chất lượng (OCOP, VietGAP...)
- Cách chọn mua, bảo quản, sử dụng"""
    elif entity["type"] == "accommodation":
        type_guide = """- Phong cách kiến trúc, không gian nghỉ dưỡng
- Tiện nghi nổi bật, loại phòng
- Trải nghiệm đặc biệt (view sông, vườn cây, ẩm thực tại chỗ)
- Phù hợp với đối tượng nào (gia đình, couple, nhóm bạn)"""
    elif entity["type"] == "event":
        type_guide = """- Thời gian, địa điểm tổ chức
- Hoạt động chính, chương trình nổi bật
- Ý nghĩa văn hóa, truyền thống
- Lưu ý khi tham dự"""

    return f"""Viết bài giới thiệu chi tiết bằng tiếng Việt cho nội dung sau. Bài viết dành cho website du lịch cộng đồng vùng {area}.

{context}

Yêu cầu:
- Viết 3-5 đoạn văn (mỗi đoạn 2-4 câu), cách nhau bằng dòng trống
- Đoạn 1: Giới thiệu tổng quan, nêu điểm đặc biệt nhất
- Đoạn 2-3: Chi tiết chuyên sâu theo loại nội dung
- Đoạn cuối: Gợi ý cho du khách (khi nào đến, lưu ý gì)
{type_guide}

Quy tắc:
- Viết tự nhiên, chân thực, KHÔNG quảng cáo phóng đại
- CHỈ viết những gì có cơ sở từ thông tin được cung cấp, KHÔNG bịa thêm chi tiết cụ thể (số liệu, năm tháng, tên người) mà không có nguồn
- Nếu thiếu thông tin, viết ở mức tổng quát hơn thay vì bịa
- KHÔNG bắt đầu bằng tên entity
- KHÔNG dùng markdown (**, ##, -, *). Chỉ trả văn bản thuần với dòng trống ngăn đoạn
- KHÔNG viết "Kết luận", "Tóm lại" ở đoạn cuối"""


def generate_description(entity):
    prompt = _build_prompt(entity)
    try:
        client = _client()
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.65,
            max_tokens=800,
        )
        text = resp.choices[0].message.content.strip()
        usage = resp.usage
        if usage:
            stats["tokens"] += (usage.prompt_tokens or 0) + (usage.completion_tokens or 0)
        if text and len(text) > 80:
            text = text.replace("**", "").replace("##", "").replace("# ", "")
            return text
    except Exception as e:
        log.error(f"  LLM error for {entity['id']}: {e}")
    return None


def get_entities_to_enrich(entity_type=None, limit=None, entity_id=None):
    db.initialize()
    ph = db._ph
    with db._conn() as conn:
        if entity_id:
            rows = db._fetchall(conn,
                f"SELECT * FROM entities WHERE id = {ph}", (entity_id,))
        elif entity_type:
            rows = db._fetchall(conn,
                f"SELECT * FROM entities WHERE type = {ph} AND (description IS NULL OR description = '') ORDER BY confidence DESC",
                (entity_type,))
        else:
            types_ph = ", ".join([ph] * len(PRIORITY_TYPES))
            rows = db._fetchall(conn,
                f"SELECT * FROM entities WHERE type IN ({types_ph}) AND (description IS NULL OR description = '') ORDER BY confidence DESC",
                tuple(PRIORITY_TYPES))
        entities = [db._parse_entity(r) for r in rows]
        if limit:
            entities = entities[:limit]
        return entities


def main():
    parser = argparse.ArgumentParser(description="Enrich entity descriptions via LLM")
    parser.add_argument("--type", help="Entity type filter")
    parser.add_argument("--limit", type=int, help="Max entities to process")
    parser.add_argument("--id", help="Single entity ID")
    parser.add_argument("--workers", type=int, default=4, help="Parallel workers")
    parser.add_argument("--dry-run", action="store_true", help="Preview without saving")
    args = parser.parse_args()

    if not API_KEY or not BASE_URL:
        log.error("LLM_API_KEY and LLM_BASE_URL must be set in .env")
        sys.exit(1)

    entities = get_entities_to_enrich(args.type, args.limit, args.id)
    log.info(f"Found {len(entities)} entities to enrich")

    if not entities:
        log.info("Nothing to do")
        return

    def process_one(entity):
        desc = generate_description(entity)
        if not desc:
            stats["fail"] += 1
            return
        if args.dry_run:
            log.info(f"\n{'='*60}\n{entity['name']} ({entity['type']})\n{'='*60}\n{desc}\n")
            stats["success"] += 1
            return
        db.update_description(entity["id"], desc)
        stats["success"] += 1
        log.info(f"  ✓ {entity['name']} ({len(desc)} chars)")

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(process_one, e): e for e in entities}
        for i, f in enumerate(as_completed(futures), 1):
            try:
                f.result()
            except Exception as e:
                log.error(f"  Error: {e}")
                stats["fail"] += 1
            if i % 10 == 0:
                log.info(f"  Progress: {i}/{len(entities)} | OK={stats['success']} Fail={stats['fail']} Tokens≈{stats['tokens']:,}")

    log.info(f"\nDone: {stats['success']} enriched, {stats['fail']} failed, ~{stats['tokens']:,} tokens used")


if __name__ == "__main__":
    main()
