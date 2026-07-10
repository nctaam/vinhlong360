#!/usr/bin/env python3
"""Entity Data Enrichment Engine — GPT-5.5 multi-layer enrichment.

For each high-value entity (confidence >= 0.7), generates:
  Layer 1: Rich description (150-300 words, evocative, Vietnamese)
  Layer 2: Travel tips (best time, what to bring, local customs)
  Layer 3: Season/timing data (peak season, events, harvest)
  Layer 4: Tags & keywords (SEO + discovery)
  Layer 5: Related entities suggestion

Output: agent/data/enrichment/ — JSONL per batch, review queue (NOT direct DB write).
"""
from __future__ import annotations
import json
import os
import sys
import time
import threading
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

AGENT_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = AGENT_DIR.parent
OUTPUT_DIR = AGENT_DIR / "data" / "enrichment"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(AGENT_DIR))
os.environ["PYTHONUNBUFFERED"] = "1"
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_DIR / ".env")
except Exception:
    pass

from openai import OpenAI

LLM_BASE = os.environ.get("LLM_BASE_URL", "")
LLM_KEY = os.environ.get("LLM_API_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "cx/gpt-5.5")

client = OpenAI(base_url=LLM_BASE, api_key=LLM_KEY)
_lock = threading.Lock()
_stats = {"done": 0, "fail": 0, "skip": 0}
RUN_TS = datetime.now().strftime("%Y%m%d_%H%M%S")
RESULT_FILE = OUTPUT_DIR / f"enrich_{RUN_TS}.jsonl"


def tprint(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def llm_call(prompt, system="", retries=2):
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    for attempt in range(retries + 1):
        try:
            r = client.chat.completions.create(
                model=LLM_MODEL, messages=msgs,
                temperature=0.7, max_tokens=2000
            )
            return r.choices[0].message.content.strip()
        except Exception:
            if attempt < retries:
                time.sleep(5 * (attempt + 1))
            else:
                raise


def parse_json(text):
    text = re.sub(r"^```(?:json)?|```$", "", (text or "").strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"(\{.*\})", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except Exception:
                pass
    return None


def append_result(record):
    with _lock:
        with open(RESULT_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


SYSTEM_PROMPT = """Bạn là chuyên gia du lịch miền Tây Nam Bộ, am hiểu sâu văn hóa, ẩm thực, lịch sử
Vĩnh Long, Bến Tre, Trà Vinh. Viết nội dung TIẾNG VIỆT, giọng ấm áp, sinh động, giàu cảm xúc nhưng
chính xác. Dùng hình ảnh cụ thể, chi tiết ngũ quan (mùi, vị, âm thanh, xúc giác) để người đọc
cảm nhận như đang ở đó. Tránh sáo rỗng, tránh quảng cáo quá mức."""

TYPE_CONTEXT = {
    "dish": "món ăn/quán ăn địa phương",
    "craft_village": "làng nghề truyền thống",
    "history": "di tích lịch sử/văn hóa",
    "accommodation": "nơi lưu trú",
    "experience": "trải nghiệm du lịch",
    "attraction": "điểm tham quan",
    "product": "sản phẩm đặc sản/OCOP",
    "nature": "cảnh quan thiên nhiên",
    "event": "sự kiện/lễ hội",
    "place": "địa điểm",
    "itinerary": "lịch trình gợi ý",
    "person": "nhân vật/nghệ nhân",
}

AREA_NAMES = {
    "vinh-long": "Vĩnh Long",
    "ben-tre": "Bến Tre",
    "tra-vinh": "Trà Vinh",
}


def enrich_entity(entity):
    eid = entity["id"]
    name = entity["name"]
    etype = entity.get("type", "place")
    area = AREA_NAMES.get(entity.get("area", ""), entity.get("area", ""))
    summary = entity.get("summary", "")
    attrs = entity.get("attributes", {})
    addr = attrs.get("address", "")
    type_label = TYPE_CONTEXT.get(etype, etype)

    context = f"Tên: {name}\nLoại: {type_label}\nVùng: {area}"
    if addr:
        context += f"\nĐịa chỉ: {addr}"
    if summary:
        context += f"\nTóm tắt hiện có: {summary}"

    prompt = f"""Hãy làm giàu dữ liệu cho {type_label} sau đây. Trả về JSON:

{context}

{{
  "description": "Mô tả chi tiết 150-300 từ, giàu cảm xúc, hình ảnh cụ thể, giọng kể chuyện. Đề cập đặc trưng riêng, lịch sử nếu có, trải nghiệm thực tế du khách sẽ có.",
  "travel_tips": ["Mẹo 1 về thời gian/cách đi/điều cần biết", "Mẹo 2", "Mẹo 3"],
  "best_time": "Thời điểm lý tưởng nhất để ghé thăm (tháng/mùa cụ thể + lý do)",
  "season": "peak|shoulder|year-round — kèm giải thích ngắn",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
  "seo_keywords": ["từ khóa tìm kiếm 1", "từ khóa 2", "từ khóa 3"],
  "emotional_hook": "Một câu ngắn gợi cảm xúc mạnh, dùng cho card/preview (< 30 từ)",
  "related_types": ["loại entity liên quan 1", "loại 2"]
}}

QUAN TRỌNG: Chỉ trả về JSON hợp lệ, không giải thích thêm."""

    try:
        raw = llm_call(prompt, SYSTEM_PROMPT)
        data = parse_json(raw)
        if not data:
            tprint(f"  ✗ {name}: parse fail")
            _stats["fail"] += 1
            return None

        result = {
            "entity_id": eid,
            "entity_name": name,
            "entity_type": etype,
            "area": entity.get("area", ""),
            "enrichment": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model": LLM_MODEL,
        }
        append_result(result)
        _stats["done"] += 1
        tprint(f"  ✓ {name} ({etype}, {area})")
        return result
    except Exception as e:
        tprint(f"  ✗ {name}: {e}")
        _stats["fail"] += 1
        return None


def main():
    with open(PROJECT_DIR / "web" / "data.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    entities = data.get("entities", [])

    candidates = [e for e in entities if e.get("confidence", 0) >= 0.7]
    candidates.sort(key=lambda e: (-e.get("confidence", 0), e["name"]))

    tprint("=== Entity Enrichment Engine ===")
    tprint(f"Total entities: {len(entities)}, candidates (conf>=0.7): {len(candidates)}")
    tprint(f"Output: {RESULT_FILE}")
    tprint(f"Model: {LLM_MODEL}")
    tprint("")

    workers = 4
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(enrich_entity, e): e for e in candidates}
        for fut in as_completed(futures):
            try:
                fut.result()
            except Exception:
                _stats["fail"] += 1
            if (_stats["done"] + _stats["fail"]) % 20 == 0:
                tprint(f"  --- Progress: {_stats['done']} done, {_stats['fail']} fail / {len(candidates)} ---")

    tprint(f"\n=== DONE: {_stats['done']} enriched, {_stats['fail']} failed ===")
    tprint(f"Results: {RESULT_FILE}")


if __name__ == "__main__":
    main()
