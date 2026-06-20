#!/usr/bin/env python3
"""MEGA ENTITY DEEP — Phân tích CỰC SÂU cho từng entity trong database.

Mỗi entity nhận 1 bài phân tích dài, chi tiết, đa chiều — siêu hơn
enrichment cơ bản. Đây là content premium cho trang chi tiết.

Modes:
  --mode attractions  : Điểm tham quan (attraction, temple, museum, market, park)
  --mode food         : Ẩm thực (food, restaurant, dish)
  --mode lodging      : Chỗ ở (hotel, homestay, resort)
  --mode craft        : Làng nghề (craft_village, workshop)
  --mode nature       : Thiên nhiên (nature, island, beach, river)
  --mode cultural     : Văn hóa (festival, heritage, pagoda)
  --mode all          : TẤT CẢ

Usage:
  python -u agent/scripts/mega_entity_deep.py --mode all
"""
from __future__ import annotations
import argparse, json, os, sys, time, warnings
warnings.filterwarnings("ignore", message=".*renamed.*ddgs.*")
from pathlib import Path

AGENT_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = AGENT_DIR.parent
OUTPUT_DIR = AGENT_DIR / "data" / "mega_research" / "entity_deep"

sys.path.insert(0, str(AGENT_DIR))
sys.path.insert(0, str(AGENT_DIR / "scripts"))
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_DIR / ".env")
except Exception:
    pass

from mega_research import (LLM, read_jsonl, append_jsonl, load_entities,
                           log, utc, PROVINCE, _cfg_io)


SYS_ENTITY = """Bạn là CHUYÊN GIA ĐỊA PHƯƠNG ĐẦU NGÀNH về vùng ĐBSCL (Vĩnh Long, Bến Tre, Trà Vinh).
Viết bài phân tích SIÊU CHI TIẾT cho điểm đến/entity được hỏi.
Trình độ: kết hợp Lonely Planet chuyên sâu + National Geographic + học thuật địa phương.
KHÔNG bịa dữ liệu. Nếu không chắc → nói "cần kiểm chứng".
Viết tiếng Việt, xen thuật ngữ tiếng Anh khi cần thiết."""


def _analyze_entity(llm, f, entity):
    eid = entity.get("id", "")
    name = entity.get("name", "")
    etype = entity.get("type", "")
    area = entity.get("area", "")
    desc = entity.get("description", "")[:500]
    addr = entity.get("address", "")

    prompt = f"""Phân tích SIÊU CHI TIẾT cho: **{name}**
Loại: {etype} | Vùng: {area} | Địa chỉ: {addr}
Mô tả hiện tại: {desc}

Viết bài phân tích ĐA CHIỀU bao gồm:
1. **Tổng quan nâng cao**: lịch sử hình thành, ý nghĩa văn hóa/xã hội
2. **Trải nghiệm chi tiết**: du khách sẽ thấy gì, nghe gì, ngửi gì, cảm gì?
3. **Thời điểm vàng**: tháng, ngày, giờ tốt nhất để đến
4. **Bí quyết insider**: điều 99% du khách không biết
5. **Kết nối**: liên hệ với địa điểm gần, route gợi ý
6. **Nhiếp ảnh**: góc chụp đẹp nhất, ánh sáng lý tưởng
7. **Câu chuyện**: anecdote, truyền thuyết, nhân vật gắn liền
8. **Đánh giá chuyên gia**: điểm mạnh/yếu, so sánh với tương tự
9. **Khuyến nghị**: ai nên đến, ai không nên, mang gì, mặc gì
10. **Bảo tồn**: thách thức bảo tồn, cách du khách có thể giúp

Trả về JSON với các key: entity_id, name, type, area,
overview, experience, best_time, insider_tips, connections,
photography, stories, expert_rating, recommendations, conservation"""

    r = llm.ask_json(sys=SYS_ENTITY, user=prompt, temp=0.25, max_tok=6000)
    if r:
        r["entity_id"] = eid; r["ts"] = utc()
        append_jsonl(f, r)
        log(f"  ✓ {eid}: {name}")
    return r


TYPE_GROUPS = {
    "attractions": ["attraction", "temple", "museum", "market", "park", "monument", "bridge"],
    "food": ["food", "restaurant", "dish", "cafe", "street_food"],
    "lodging": ["hotel", "homestay", "resort", "guesthouse"],
    "craft": ["craft_village", "workshop", "factory"],
    "nature": ["nature", "island", "beach", "river", "lake", "forest", "garden", "eco_tourism"],
    "cultural": ["festival", "heritage", "pagoda", "church", "mosque", "shrine"],
}


def run_mode(llm, mode):
    types = TYPE_GROUPS.get(mode, [])
    if not types:
        log(f"Unknown mode: {mode}"); return

    log(f"═══ ENTITY DEEP: {mode.upper()} ═══")
    f = OUTPUT_DIR / f"{mode}.jsonl"
    done = {r.get("entity_id") for r in read_jsonl(f)}

    entities = load_entities()
    targets = [e for e in entities
               if e.get("type", "").lower() in types and e.get("id") not in done]

    log(f"  {len(targets)} entities to analyze (done: {len(done)})")

    for i, e in enumerate(targets):
        t1 = time.time()
        try:
            _analyze_entity(llm, f, e)
            elapsed = time.time() - t1
            if (i + 1) % 5 == 0:
                log(f"  Progress: {i+1}/{len(targets)} ({elapsed:.0f}s) — {llm.info()}")
        except Exception as ex:
            log(f"  ERR: {ex}")


def main():
    _cfg_io()
    ap = argparse.ArgumentParser(description="Mega Entity Deep — per-entity deep analysis")
    ap.add_argument("--mode", required=True,
                    choices=list(TYPE_GROUPS.keys()) + ["all"])
    a = ap.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    llm = LLM()
    if not llm.ok:
        log("ERROR: LLM not configured"); return

    t0 = time.time()
    log(f"Model: {llm.model}  (SEQUENTIAL — 1 call at a time)")
    log(f"Entities loaded: {len(load_entities())}")

    modes = list(TYPE_GROUPS.keys()) if a.mode == "all" else [a.mode]
    for m in modes:
        run_mode(llm, m)
        log(f"  LLM after {m}: {llm.info()}")

    elapsed = (time.time() - t0) / 60
    log(f"\n═══ DONE ({elapsed:.1f}m) ═══")
    log(f"  FINAL LLM: {llm.info()}")


if __name__ == "__main__":
    main()
