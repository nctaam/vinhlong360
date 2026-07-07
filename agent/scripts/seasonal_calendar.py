#!/usr/bin/env python3
"""Seasonal Calendar Generator — GPT-5.5 deep month-by-month guide.

For each of the 12 months, generates:
  Layer 1: Weather & conditions
  Layer 2: Fruits in season (with specific varieties)
  Layer 3: Festivals & events (lunar + solar calendar)
  Layer 4: Best activities & experiences
  Layer 5: Products to buy (OCOP, seasonal specialties)
  Layer 6: Photography opportunities
  Layer 7: Practical tips (what to pack, what to avoid)

Cross-referenced across 3 regions (Vĩnh Long, Bến Tre, Trà Vinh).
Output: agent/data/calendar/ — structured JSON for frontend integration.
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
OUTPUT_DIR = AGENT_DIR / "data" / "calendar"
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
RUN_TS = datetime.now().strftime("%Y%m%d_%H%M%S")

MONTHS_VI = ["Tháng 1","Tháng 2","Tháng 3","Tháng 4","Tháng 5","Tháng 6",
             "Tháng 7","Tháng 8","Tháng 9","Tháng 10","Tháng 11","Tháng 12"]


def tprint(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def llm_call(prompt, system="", retries=2, max_tokens=4000):
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    for attempt in range(retries + 1):
        try:
            r = client.chat.completions.create(
                model=LLM_MODEL, messages=msgs,
                temperature=0.6, max_tokens=max_tokens
            )
            return r.choices[0].message.content.strip()
        except Exception as e:
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


SYSTEM = """Bạn là chuyên gia du lịch miền Tây Nam Bộ, am hiểu sâu mùa vụ, thời tiết, lễ hội
âm lịch, trái cây theo mùa, sản phẩm OCOP. Cung cấp thông tin CHÍNH XÁC, CỤ THỂ cho vùng
Vĩnh Long, Bến Tre, Trà Vinh. Phân biệt rõ 3 vùng khi thông tin khác nhau."""


def generate_month(month_num):
    month_name = MONTHS_VI[month_num - 1]
    tprint(f"  📅 {month_name}...")

    prompt = f"""Tạo hướng dẫn du lịch chi tiết cho {month_name} (tháng {month_num} dương lịch)
tại Vĩnh Long, Bến Tre, Trà Vinh.

Trả về JSON:
{{
  "month": {month_num},
  "month_name": "{month_name}",
  "weather": {{
    "temperature": "khoảng nhiệt độ (°C)",
    "rainfall": "lượng mưa ước tính",
    "humidity": "độ ẩm",
    "conditions": "mô tả thời tiết chung",
    "travel_rating": 1-10,
    "notes": "lưu ý đặc biệt (mùa mưa/khô/lũ)"
  }},
  "fruits_in_season": [
    {{
      "name": "tên trái cây",
      "peak": true,
      "varieties": "giống cụ thể (vd: bưởi Năm Roi, cam sành Tam Bình)",
      "where": "nơi tốt nhất để mua/hái",
      "price_range": "giá tham khảo (VND/kg)"
    }}
  ],
  "festivals_events": [
    {{
      "name": "tên lễ hội/sự kiện",
      "lunar_date": "ngày âm lịch (nếu có)",
      "solar_date_approx": "khoảng ngày dương lịch",
      "location": "nơi tổ chức",
      "region": "vinh-long|ben-tre|tra-vinh",
      "description": "mô tả ngắn",
      "must_see": true
    }}
  ],
  "best_activities": [
    {{
      "activity": "hoạt động",
      "why_this_month": "tại sao tháng này đặc biệt",
      "region": "vùng tốt nhất",
      "duration": "thời gian",
      "cost_range": "chi phí ước tính"
    }}
  ],
  "products_to_buy": [
    {{
      "product": "sản phẩm",
      "type": "OCOP|đặc sản|thủ công",
      "why_now": "tại sao mua lúc này",
      "where": "nơi mua",
      "price_range": "giá"
    }}
  ],
  "photography_spots": [
    {{
      "location": "địa điểm",
      "best_time": "giờ chụp tốt nhất",
      "what_to_capture": "chụp gì",
      "tip": "mẹo chụp ảnh"
    }}
  ],
  "practical_tips": {{
    "what_to_pack": ["đồ cần mang 1", "2", "3"],
    "what_to_avoid": ["tránh 1", "2"],
    "budget_per_day": "chi phí trung bình/ngày (VND)",
    "crowds": "đông/vừa/vắng",
    "booking_advance": "nên đặt trước bao lâu"
  }},
  "highlight_quote": "1 câu gợi cảm xúc về tháng này ở miền Tây (< 25 từ)"
}}

CHỈ trả về JSON hợp lệ. Thông tin phải CHÍNH XÁC theo thực tế miền Tây."""

    try:
        raw = llm_call(prompt, SYSTEM)
        data = parse_json(raw)
        if data:
            tprint(f"  ✓ {month_name}")
            return data
        tprint(f"  ✗ {month_name} — parse fail")
    except Exception as e:
        tprint(f"  ✗ {month_name} — {e}")
    return None


def generate_annual_overview():
    tprint("  📅 Annual overview...")
    prompt = """Tạo tổng quan du lịch cả năm cho Vĩnh Long, Bến Tre, Trà Vinh:

Trả về JSON:
{
  "best_months_overall": [{"month": 1, "reason": "lý do"}],
  "peak_season": {"months": [12,1,2,3], "description": "mô tả mùa cao điểm"},
  "shoulder_season": {"months": [4,5,10,11], "description": "mô tả"},
  "rainy_season": {"months": [6,7,8,9], "description": "mô tả + lợi thế riêng"},
  "fruit_calendar_summary": {"best_month_per_fruit": [{"fruit": "tên", "peak_months": [5,6]}]},
  "festival_highlights": [{"name": "lễ hội", "month_approx": 10, "importance": "1-10"}],
  "budget_variation": {"cheapest_months": [6,7], "most_expensive": [1,2], "notes": "ghi chú"},
  "unique_selling_points_by_season": {
    "dry_season": ["USP 1", "2"],
    "rainy_season": ["USP 1", "2"],
    "tet": ["USP 1", "2"]
  }
}

CHỈ trả về JSON."""

    try:
        raw = llm_call(prompt, SYSTEM)
        data = parse_json(raw)
        if data:
            tprint("  ✓ Annual overview")
            return data
        tprint("  ✗ Annual overview — parse fail")
    except Exception as e:
        tprint(f"  ✗ Annual overview — {e}")
    return None


def main():
    tprint("=== Seasonal Calendar Generator ===")
    tprint(f"Model: {LLM_MODEL}")
    tprint(f"Output: {OUTPUT_DIR}")
    tprint("")

    calendar = {"months": {}, "annual_overview": None, "generated_at": RUN_TS}

    # Generate months in parallel (4 at a time)
    with ThreadPoolExecutor(max_workers=4) as pool:
        futs = {pool.submit(generate_month, m): m for m in range(1, 13)}
        for f in as_completed(futs):
            month_num = futs[f]
            data = f.result()
            if data:
                calendar["months"][str(month_num)] = data

    # Annual overview
    calendar["annual_overview"] = generate_annual_overview()

    out = OUTPUT_DIR / f"seasonal_calendar_{RUN_TS}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(calendar, f, ensure_ascii=False, indent=2)

    tprint(f"\n=== DONE: {len(calendar['months'])}/12 months ===")
    tprint(f"Output: {out}")


if __name__ == "__main__":
    main()
