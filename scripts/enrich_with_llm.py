#!/usr/bin/env python3
"""Làm giàu dữ liệu entity bằng LLM (cx/gpt-5.5).

Hai chế độ:
  1. description  — sinh description từ summary có sẵn (không bịa thêm fact)
  2. summary      — cải thiện summary: thêm location keyword tự nhiên

BẮT BUỘC: backup trước khi chạy --apply (§B1)
KHÔNG bịa thông tin (§B6): LLM chỉ diễn giải/mở rộng data đã có.

Usage:
  python scripts/enrich_with_llm.py description                    # dry-run
  python scripts/enrich_with_llm.py description --apply --limit 20
  python scripts/enrich_with_llm.py summary --apply --type dish --limit 50
  python scripts/enrich_with_llm.py description --apply --type dish

Env vars:
  LLM_API_KEY     — API key (bắt buộc)
  LLM_BASE_URL    — endpoint base (default: .env hoặc http://localhost:20128)
  LLM_MODEL       — model name (default: cx/gpt-5.5)
"""

import argparse
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENT_DIR = ROOT / "agent"
sys.path.insert(0, str(AGENT_DIR))

# Load .env if available (check project root, then parent)
for env_candidate in [ROOT / ".env", ROOT.parent / ".env"]:
    if env_candidate.exists():
        with open(env_candidate, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k, v = k.strip(), v.strip().strip('"').strip("'")
                    if k and v and k not in os.environ:
                        os.environ[k] = v
        break

API_KEY = os.environ.get("LLM_API_KEY", "")
API_BASE = os.environ.get("LLM_BASE_URL", "http://localhost:20128")
MODEL = os.environ.get("LLM_MODEL_ENRICH", os.environ.get("LLM_MODEL", "cx/gpt-5.5"))

AREA_LABELS = {
    "vinh-long": "Vĩnh Long",
    "ben-tre": "Bến Tre",
    "tra-vinh": "Trà Vinh",
}

TYPE_LABELS = {
    "dish": "món ăn/ẩm thực", "drink": "thức uống", "experience": "trải nghiệm du lịch",
    "product": "đặc sản/sản phẩm OCOP", "accommodation": "lưu trú",
    "nature": "địa điểm thiên nhiên", "history": "di tích lịch sử",
    "attraction": "điểm tham quan", "craft_village": "làng nghề truyền thống",
    "event": "lễ hội/sự kiện", "facility": "tiện ích công cộng",
    "organization": "tổ chức", "person": "nhân vật lịch sử",
    "cafe": "quán cà phê", "restaurant": "nhà hàng", "economy": "kinh tế",
}


def call_llm(prompt: str, system: str = "", max_tokens: int = 500) -> str:
    if not API_KEY:
        sys.exit("ERROR: đặt env LLM_API_KEY trước khi chạy.")

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    body = json.dumps({
        "model": MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.3,
    }).encode()

    req = urllib.request.Request(
        f"{API_BASE}/v1/chat/completions",
        data=body, method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
        })

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"[ERROR] {e}"


# ──────────────────────────────────────────────
# Mode 1: Generate description from summary
# ──────────────────────────────────────────────

SYSTEM_DESC = """Bạn là copywriter du lịch cho vinhlong360.vn — cổng thông tin du lịch vùng Vĩnh Long, Bến Tre, Trà Vinh (miền Tây Nam Bộ).

Nhiệm vụ: Viết MÔ TẢ CHI TIẾT (200-400 từ) từ tóm tắt có sẵn.

Quy tắc TUYỆT ĐỐI:
- KHÔNG bịa thêm thông tin mới (địa chỉ, giá, SĐT, giờ mở cửa) nếu không có trong tóm tắt
- CHỈ diễn giải, mở rộng, làm phong phú ngôn ngữ từ nội dung tóm tắt
- Nếu tóm tắt thiếu thông tin → viết chung chung, KHÔNG đoán
- Viết tiếng Việt tự nhiên, giọng thân thiện, hướng du lịch
- Nhắc tên tỉnh/vùng tự nhiên trong bài (SEO)
- KHÔNG dùng bullet points hay heading — viết văn xuôi liền mạch
- KHÔNG mở đầu bằng "Mô tả:" hay tiêu đề"""


def build_desc_prompt(entity: dict) -> str:
    name = entity.get("name", "")
    etype = entity.get("type", "")
    area = entity.get("area", "")
    summary = (entity.get("summary") or "").strip()
    attrs = entity.get("attributes") or {}

    type_label = TYPE_LABELS.get(etype, etype)
    area_label = AREA_LABELS.get(area, area)

    parts = [f"Tên: {name}"]
    parts.append(f"Loại: {type_label}")
    if area_label:
        parts.append(f"Khu vực: {area_label}")
    parts.append(f"Tóm tắt: {summary}")

    addr = attrs.get("address", "")
    if addr:
        parts.append(f"Địa chỉ: {addr}")
    price = attrs.get("price_range", "") or attrs.get("price", "")
    if price:
        parts.append(f"Giá: {price}")
    hours = attrs.get("hours", "")
    if hours:
        parts.append(f"Giờ mở cửa: {hours}")

    return "\n".join(parts)


def enrich_descriptions(db, apply=False, limit=0, entity_type=None):
    entities = [e for e in db.all_entities() if e.get("type") != "place"]
    if entity_type:
        entities = [e for e in entities if e.get("type") == entity_type]

    targets = [e for e in entities
               if not (e.get("description") or "").strip()
               and len((e.get("summary") or "").strip()) >= 80]

    if limit:
        targets = targets[:limit]

    print(f"[description] Targets: {len(targets)}")

    if not targets:
        print("  Nothing to do.")
        return 0

    if not apply:
        print(f"  DRY-RUN — would generate {len(targets)} descriptions")
        print(f"  Model: {MODEL}")
        print(f"  API: {API_BASE}")
        for e in targets[:5]:
            print(f"    {e['id']:45s} summary={len(e.get('summary',''))} chars")
        return len(targets)

    success = 0
    fail = 0
    for i, e in enumerate(targets):
        prompt = build_desc_prompt(e)
        result = call_llm(prompt, system=SYSTEM_DESC, max_tokens=800)

        if result.startswith("[ERROR]"):
            fail += 1
            print(f"  [{i+1}/{len(targets)}] FAIL {e['id'][:40]} {result}")
            if "rate" in result.lower() or "429" in result:
                time.sleep(5)
            continue

        if len(result) < 50:
            fail += 1
            print(f"  [{i+1}/{len(targets)}] SKIP {e['id'][:40]} (too short: {len(result)})")
            continue

        e["description"] = result
        db.upsert_entity(e)
        success += 1
        print(f"  [{i+1}/{len(targets)}] OK   {e['id'][:40]} ({len(result)} chars)")

        time.sleep(0.5)

    print(f"\nDone: {success} generated, {fail} failed")
    return success


# ──────────────────────────────────────────────
# Mode 2: Improve summary with location keywords
# ──────────────────────────────────────────────

SYSTEM_SUMMARY = """Bạn là SEO editor cho vinhlong360.vn.

Nhiệm vụ: Cải thiện tóm tắt entity để tự nhiên chứa tên tỉnh/vùng (SEO).

Quy tắc:
- Giữ NGUYÊN mọi thông tin gốc — KHÔNG thêm, KHÔNG bớt fact
- CHỈ thêm/sửa cách diễn đạt để nhắc tên tỉnh hoặc "miền Tây" tự nhiên
- Giữ độ dài tương đương (±20 ký tự)
- Trả về CHỈ tóm tắt mới, không giải thích
- Nếu tóm tắt đã có tên tỉnh → trả về nguyên bản"""

LOCATION_KEYWORDS = [
    "vĩnh long", "bến tre", "trà vinh", "vinh long", "ben tre", "tra vinh",
    "mekong", "miền tây", "đồng bằng", "sông nước",
]

EXEMPT_TYPES = {"person", "event", "itinerary"}


def enrich_summaries(db, apply=False, limit=0, entity_type=None):
    entities = [e for e in db.all_entities() if e.get("type") != "place"]
    if entity_type:
        entities = [e for e in entities if e.get("type") == entity_type]

    targets = []
    for e in entities:
        if e.get("type") in EXEMPT_TYPES:
            continue
        summary = (e.get("summary") or "").strip()
        if len(summary) < 50:
            continue
        if any(kw in summary.lower() for kw in LOCATION_KEYWORDS):
            continue
        targets.append(e)

    if limit:
        targets = targets[:limit]

    print(f"[summary] Targets missing location keyword: {len(targets)}")

    if not targets:
        print("  Nothing to do.")
        return 0

    if not apply:
        print(f"  DRY-RUN — would improve {len(targets)} summaries")
        print(f"  Model: {MODEL}")
        for e in targets[:5]:
            s = (e.get("summary") or "")[:60]
            area = AREA_LABELS.get(e.get("area", ""), "?")
            print(f"    {e['id'][:40]:40s} [{area}] {s}...")
        return len(targets)

    success = 0
    fail = 0
    for i, e in enumerate(targets):
        area_label = AREA_LABELS.get(e.get("area", ""), "miền Tây")
        summary = (e.get("summary") or "").strip()
        type_label = TYPE_LABELS.get(e.get("type", ""), "")

        prompt = (f"Tóm tắt gốc: {summary}\n"
                  f"Tên: {e.get('name','')}\n"
                  f"Loại: {type_label}\n"
                  f"Khu vực: {area_label}\n\n"
                  f"Cải thiện tóm tắt để tự nhiên nhắc đến \"{area_label}\" hoặc \"miền Tây\".")

        result = call_llm(prompt, system=SYSTEM_SUMMARY, max_tokens=400)

        if result.startswith("[ERROR]"):
            fail += 1
            print(f"  [{i+1}/{len(targets)}] FAIL {e['id'][:40]} {result}")
            if "rate" in result.lower() or "429" in result:
                time.sleep(5)
            continue

        result = result.strip().strip('"')
        if len(result) < 30 or len(result) > len(summary) * 2:
            fail += 1
            print(f"  [{i+1}/{len(targets)}] SKIP {e['id'][:40]} (bad length: {len(result)})")
            continue

        if not any(kw in result.lower() for kw in LOCATION_KEYWORDS):
            fail += 1
            print(f"  [{i+1}/{len(targets)}] SKIP {e['id'][:40]} (no keyword added)")
            continue

        e["summary"] = result
        db.upsert_entity(e)
        success += 1
        print(f"  [{i+1}/{len(targets)}] OK   {e['id'][:40]} ({len(result)} chars)")

        time.sleep(0.5)

    print(f"\nDone: {success} improved, {fail} failed/skipped")
    return success


# ──────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Làm giàu dữ liệu entity bằng LLM")
    ap.add_argument("mode", choices=["description", "summary"],
                    help="description = sinh mô tả, summary = cải thiện tóm tắt")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--type", dest="entity_type")
    args = ap.parse_args()

    if args.apply:
        print(f"[WARNING] APPLY mode — sẽ gọi LLM ({MODEL}) và sửa DB!")
        print(f"[WARNING] Đảm bảo đã chạy: python scripts/backup_data.py")
        print()

    from database import db

    if args.mode == "description":
        enrich_descriptions(db, args.apply, args.limit, args.entity_type)
    else:
        enrich_summaries(db, args.apply, args.limit, args.entity_type)


if __name__ == "__main__":
    main()
