#!/usr/bin/env python3
"""Generate descriptions for entities that don't have one yet.

Reads entities with empty description from the DB, calls LLM to generate
a rich description, and writes it back to the DB. Processes in batches
with rate limiting. Safe to re-run (skips entities that already have descriptions).
"""
import json, os, sys, time, sqlite3, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT / "agent" / "data" / "vinhlong360.db"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT / ".env")
except Exception:
    pass

from openai import OpenAI

LLM_BASE = os.environ.get("LLM_BASE_URL", "")
LLM_KEY = os.environ.get("LLM_API_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "cx/gpt-5.5")

if not LLM_BASE or not LLM_KEY:
    print("ERROR: LLM_BASE_URL and LLM_API_KEY must be set in .env")
    sys.exit(1)

client = OpenAI(base_url=LLM_BASE, api_key=LLM_KEY)
_lock = threading.Lock()
_stats = {"done": 0, "fail": 0}

TYPE_CONTEXT = {
    "dish": "món ăn/quán ăn địa phương",
    "craft_village": "làng nghề truyền thống",
    "history": "di tích lịch sử/văn hóa",
    "accommodation": "nơi lưu trú (homestay/khách sạn/nhà nghỉ)",
    "experience": "trải nghiệm du lịch",
    "attraction": "điểm tham quan",
    "product": "sản phẩm đặc sản/OCOP",
    "nature": "cảnh quan thiên nhiên",
    "event": "sự kiện/lễ hội",
    "place": "địa điểm",
    "organization": "tổ chức/cơ quan",
    "person": "nhân vật/nghệ nhân",
}

AREA_NAMES = {
    "vinh-long": "Vĩnh Long",
    "ben-tre": "Bến Tre",
    "tra-vinh": "Trà Vinh",
}

SYSTEM = """Bạn là chuyên gia du lịch miền Tây Nam Bộ. Viết mô tả TIẾNG VIỆT cho một địa điểm/sản phẩm/trải nghiệm.
Yêu cầu:
- 150-250 từ, chia thành 2-3 đoạn văn (ngăn cách bằng dòng trống)
- Giọng ấm áp, cụ thể, giàu hình ảnh (mùi, vị, âm thanh, khung cảnh)
- Dựa trên thông tin được cung cấp, KHÔNG bịa thêm chi tiết không có cơ sở
- Nếu thiếu thông tin, viết về đặc trưng chung của loại hình đó ở vùng miền Tây
- KHÔNG dùng tiêu đề, KHÔNG dùng markdown, chỉ văn xuôi thuần
- Tránh sáo rỗng ("không thể bỏ qua", "nhất định phải thử")"""


def generate_description(entity):
    eid = entity["id"]
    name = entity["name"]
    etype = entity.get("type", "place")
    area = AREA_NAMES.get(entity.get("area", ""), entity.get("area", ""))
    summary = entity.get("summary", "")
    attrs = entity.get("attributes", {})
    type_label = TYPE_CONTEXT.get(etype, etype)

    parts = [f"Tên: {name}", f"Loại: {type_label}", f"Vùng: {area}"]
    if attrs.get("address"):
        parts.append(f"Địa chỉ: {attrs['address']}")
    if attrs.get("hours"):
        parts.append(f"Giờ mở cửa: {attrs['hours']}")
    if attrs.get("price"):
        parts.append(f"Giá: {attrs['price']}")
    if summary:
        parts.append(f"Tóm tắt hiện có: {summary}")

    prompt = f"Viết mô tả chi tiết cho {type_label} sau:\n\n" + "\n".join(parts)

    for attempt in range(3):
        try:
            r = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=800,
            )
            desc = r.choices[0].message.content.strip()
            if len(desc) < 50:
                raise ValueError(f"Too short: {len(desc)} chars")
            return eid, desc
        except Exception as e:
            if attempt < 2:
                time.sleep(3 * (attempt + 1))
            else:
                print(f"  FAIL {name}: {e}")
                return eid, None


def main():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT id, name, type, summary, area, attributes
        FROM entities
        WHERE description IS NULL OR description = ''
        ORDER BY type, name
    """)
    rows = cur.fetchall()
    conn.close()

    entities = []
    for row in rows:
        attrs = {}
        try:
            attrs = json.loads(row["attributes"]) if row["attributes"] else {}
        except Exception:
            pass
        entities.append({
            "id": row["id"],
            "name": row["name"],
            "type": row["type"],
            "summary": row["summary"] or "",
            "area": row["area"] or "",
            "attributes": attrs,
        })

    print(f"Generating descriptions for {len(entities)} entities...")
    print(f"Model: {LLM_MODEL}")

    results = []
    workers = 4
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(generate_description, e): e for e in entities}
        for fut in as_completed(futures):
            eid, desc = fut.result()
            if desc:
                results.append((eid, desc))
                _stats["done"] += 1
            else:
                _stats["fail"] += 1
            total = _stats["done"] + _stats["fail"]
            if total % 25 == 0:
                print(f"  Progress: {total}/{len(entities)} ({_stats['done']} ok, {_stats['fail']} fail)")

    # Write to DB
    print(f"\nWriting {len(results)} descriptions to DB...")
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    for eid, desc in results:
        cur.execute("UPDATE entities SET description = ? WHERE id = ?", (desc, eid))
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM entities WHERE description IS NOT NULL AND description != ''")
    total_with = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM entities")
    total = cur.fetchone()[0]
    conn.close()

    print(f"\nDone: {_stats['done']} generated, {_stats['fail']} failed")
    print(f"DB state: {total_with}/{total} entities now have descriptions")


if __name__ == "__main__":
    main()
