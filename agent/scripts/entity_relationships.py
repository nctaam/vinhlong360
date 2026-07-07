#!/usr/bin/env python3
"""Entity Relationship Graph Builder — GPT-5.5 multi-layer relationship mapping.

Builds a knowledge graph of relationships between entities:
  Layer 1: Spatial proximity (entities near each other)
  Layer 2: Thematic connections (dish ↔ ingredient ↔ craft village)
  Layer 3: Temporal connections (seasonal co-occurrence)
  Layer 4: Experience chains (visit A → eat at B → buy at C)
  Layer 5: Cultural connections (history ↔ festival ↔ craft)

Output: agent/data/relationships/ — JSONL edges for knowledge graph.
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
OUTPUT_DIR = AGENT_DIR / "data" / "relationships"
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
_stats = {"done": 0, "fail": 0, "edges": 0}
RUN_TS = datetime.now().strftime("%Y%m%d_%H%M%S")
RESULT_FILE = OUTPUT_DIR / f"relationships_{RUN_TS}.jsonl"


def tprint(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def llm_call(prompt, system="", retries=2, max_tokens=3000):
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    for attempt in range(retries + 1):
        try:
            r = client.chat.completions.create(
                model=LLM_MODEL, messages=msgs,
                temperature=0.5, max_tokens=max_tokens
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
        m = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
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


SYSTEM = """Bạn là chuyên gia du lịch miền Tây, am hiểu sâu mối liên hệ giữa các địa điểm,
món ăn, sản phẩm, lễ hội, làng nghề ở Vĩnh Long, Bến Tre, Trà Vinh. Nhiệm vụ: xác định
MỐI LIÊN HỆ THỰC TẾ giữa các entity du lịch — chỉ những mối liên hệ có ý nghĩa cho du khách."""


def build_cluster_relationships(cluster_name, entities_in_cluster):
    names = [f"{e['name']} ({e['type']}, {e.get('area','')})" for e in entities_in_cluster]
    names_str = "\n".join(f"  - {n}" for n in names[:30])

    prompt = f"""Phân tích MỐI LIÊN HỆ giữa các entity du lịch trong cluster "{cluster_name}":

{names_str}

Xác định các mối liên hệ theo 5 tầng:
1. SPATIAL: gần nhau về địa lý (cùng khu vực/đường)
2. THEMATIC: liên quan chủ đề (món ăn dùng nguyên liệu từ làng nghề, v.v.)
3. TEMPORAL: cùng mùa/thời điểm (lễ hội + sản phẩm mùa vụ)
4. EXPERIENCE: chuỗi trải nghiệm (tham quan A → ăn B → mua C)
5. CULTURAL: kết nối văn hóa (di tích ↔ lễ hội ↔ nghề truyền thống)

Trả về JSON:
{{
  "relationships": [
    {{
      "from": "tên entity nguồn",
      "to": "tên entity đích",
      "type": "spatial|thematic|temporal|experience|cultural",
      "strength": 0.1-1.0,
      "description": "mô tả ngắn mối liên hệ",
      "tourist_value": "giá trị cho du khách (1 câu)"
    }}
  ],
  "experience_chains": [
    {{
      "name": "tên chuỗi trải nghiệm",
      "sequence": ["entity1", "entity2", "entity3"],
      "duration": "thời gian ước tính",
      "description": "mô tả trải nghiệm"
    }}
  ]
}}

CHỈ trả JSON. Chỉ liệt kê MỐI LIÊN HỆ THỰC SỰ CÓ Ý NGHĨA (không bịa)."""

    try:
        raw = llm_call(prompt, SYSTEM)
        data = parse_json(raw)
        if not data:
            tprint(f"  ✗ {cluster_name}: parse fail")
            _stats["fail"] += 1
            return

        rels = data.get("relationships", [])
        chains = data.get("experience_chains", [])

        record = {
            "cluster": cluster_name,
            "relationships": rels,
            "experience_chains": chains,
            "entity_count": len(entities_in_cluster),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        append_result(record)
        _stats["done"] += 1
        _stats["edges"] += len(rels)
        tprint(f"  ✓ {cluster_name}: {len(rels)} edges, {len(chains)} chains")
    except Exception as e:
        tprint(f"  ✗ {cluster_name}: {e}")
        _stats["fail"] += 1


def main():
    with open(PROJECT_DIR / "web" / "data.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    entities = data.get("entities", [])
    hi = [e for e in entities if e.get("confidence", 0) >= 0.7]

    # Build clusters: by area × type
    clusters = {}
    for e in hi:
        area = e.get("area", "unknown")
        etype = e.get("type", "unknown")
        key = f"{area}/{etype}"
        clusters.setdefault(key, []).append(e)

    # Also cross-type clusters per area (for cross-type relationships)
    for area in ["vinh-long", "ben-tre", "tra-vinh"]:
        area_ents = [e for e in hi if e.get("area") == area]
        if area_ents:
            clusters[f"{area}/cross-type"] = area_ents[:40]

    # Inter-area thematic clusters
    for etype in ["dish", "product", "craft_village", "event", "experience"]:
        type_ents = [e for e in hi if e.get("type") == etype]
        if len(type_ents) >= 3:
            clusters[f"cross-area/{etype}"] = type_ents[:30]

    tprint("=== Entity Relationship Graph Builder ===")
    tprint(f"High-confidence entities: {len(hi)}")
    tprint(f"Clusters to process: {len(clusters)}")
    tprint(f"Model: {LLM_MODEL}")
    tprint(f"Output: {RESULT_FILE}")
    tprint("")

    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(build_cluster_relationships, name, ents): name
                   for name, ents in clusters.items()}
        for fut in as_completed(futures):
            try:
                fut.result()
            except Exception:
                _stats["fail"] += 1

    tprint(f"\n=== DONE: {_stats['done']} clusters, {_stats['edges']} edges, {_stats['fail']} failed ===")
    tprint(f"Output: {RESULT_FILE}")


if __name__ == "__main__":
    main()
