"""
vinhlong360 — Auto-Relationship Discovery.

Dùng LLM phát hiện mối liên hệ giữa các entities:
  - Cùng khu vực → "near"
  - Cùng chủ đề → "related_to"
  - Sản phẩm ↔ Làng nghề → "produced_in"
  - Nhân vật ↔ Nơi liên quan → "associated_with"

Chạy: python agent/relationship_discovery.py [--apply]
"""

import json
import os
import re
import sys
from pathlib import Path

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

DATA_PATH = Path(__file__).resolve().parent.parent / "web" / "data.json"

# ── Rule-based discovery (no LLM needed) ──

def discover_by_place(entities: list[dict]) -> list[dict]:
    """Phát hiện quan hệ 'near' giữa entities cùng placeId."""
    by_place = {}
    for e in entities:
        pid = e.get("placeId")
        if pid:
            by_place.setdefault(pid, []).append(e)

    new_rels = []
    for pid, group in by_place.items():
        if len(group) < 2:
            continue
        # Chỉ tạo near cho entity khác loại
        for i, a in enumerate(group):
            for b in group[i+1:]:
                if a["type"] != b["type"]:
                    new_rels.append({
                        "from": a["id"],
                        "to": b["id"],
                        "type": "near",
                        "auto": True,
                    })
    return new_rels


def discover_product_craft(entities: list[dict]) -> list[dict]:
    """Phát hiện quan hệ 'produced_in' giữa product/dish và craft_village cùng placeId."""
    craft_by_place = {}
    for e in entities:
        if e["type"] == "craft_village" and e.get("placeId"):
            craft_by_place.setdefault(e["placeId"], []).append(e)

    new_rels = []
    for e in entities:
        if e["type"] not in ("product", "dish"):
            continue
        pid = e.get("placeId")
        if pid and pid in craft_by_place:
            for craft in craft_by_place[pid]:
                new_rels.append({
                    "from": e["id"],
                    "to": craft["id"],
                    "type": "produced_in",
                    "auto": True,
                })
    return new_rels


def discover_person_history(entities: list[dict]) -> list[dict]:
    """Liên kết person với history entities cùng khu vực dựa trên tên xuất hiện trong summary."""
    persons = [e for e in entities if e["type"] == "person"]
    histories = [e for e in entities if e["type"] == "history"]

    new_rels = []
    for person in persons:
        name = person["name"].lower()
        for hist in histories:
            summary = (hist.get("summary", "") + " " + hist.get("name", "")).lower()
            if name in summary or any(w in summary for w in name.split() if len(w) > 3):
                new_rels.append({
                    "from": person["id"],
                    "to": hist["id"],
                    "type": "associated_with",
                    "auto": True,
                })
    return new_rels


def discover_by_keyword(entities: list[dict]) -> list[dict]:
    """Phát hiện quan hệ 'related_to' dựa trên từ khóa chung trong summary."""
    TOPIC_KEYWORDS = {
        "dừa": "dừa", "coconut": "dừa",
        "khmer": "khmer", "chùa": "chùa",
        "lúa": "nông nghiệp", "gạo": "nông nghiệp",
        "cá": "thủy sản", "tôm": "thủy sản",
        "trái cây": "trái cây", "vườn": "trái cây",
        "gốm": "thủ công", "đan": "thủ công",
    }

    by_topic: dict[str, list[dict]] = {}
    for e in entities:
        text = (e.get("name", "") + " " + e.get("summary", "")).lower()
        for kw, topic in TOPIC_KEYWORDS.items():
            if kw in text:
                by_topic.setdefault(topic, []).append(e)
                break

    new_rels = []
    for topic, group in by_topic.items():
        if len(group) < 2:
            continue
        for i, a in enumerate(group):
            for b in group[i + 1:min(i + 4, len(group))]:  # Max 3 rels per entity
                if a["id"] != b["id"] and a["type"] != b["type"]:
                    new_rels.append({
                        "from": a["id"],
                        "to": b["id"],
                        "type": "related_to",
                        "auto": True,
                    })
    return new_rels


def discover_all(data: dict) -> list[dict]:
    """Chạy tất cả rule-based discovery."""
    entities = [e for e in data["entities"] if e["type"] != "place"]
    existing = {(r["from"], r["to"]) for r in data["relationships"]}
    existing |= {(r["to"], r["from"]) for r in data["relationships"]}

    all_new = []
    all_new.extend(discover_by_place(entities))
    all_new.extend(discover_product_craft(entities))
    all_new.extend(discover_person_history(entities))
    all_new.extend(discover_by_keyword(entities))

    # Deduplicate
    seen = set()
    unique = []
    for r in all_new:
        key = (r["from"], r["to"], r["type"])
        rev_key = (r["to"], r["from"], r["type"])
        if key not in seen and rev_key not in seen:
            if (r["from"], r["to"]) not in existing:
                seen.add(key)
                unique.append(r)

    return unique


# ── LLM-based discovery (optional, more expensive) ──

def discover_with_llm(entities: list[dict], batch_size: int = 20) -> list[dict]:
    """Dùng LLM phát hiện mối liên hệ phức tạp."""
    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=os.environ["LLM_API_KEY"],
            base_url=os.environ["LLM_BASE_URL"],
        )
    except Exception as e:
        print(f"  LLM unavailable: {e}")
        return []

    MODEL = os.environ.get("LLM_MODEL_MINI", "cx/gpt-5.4-mini")
    new_rels = []

    # Process in batches
    for i in range(0, len(entities), batch_size):
        batch = entities[i:i + batch_size]
        entity_list = "\n".join(f"- {e['id']}: {e['name']} ({e['type']})" for e in batch)

        prompt = f"""Dưới đây là danh sách các thực thể du lịch ở Vĩnh Long/Bến Tre/Trà Vinh:

{entity_list}

Hãy phát hiện các mối liên hệ giữa chúng. Các loại quan hệ:
- "near": gần nhau về địa lý
- "related_to": cùng chủ đề/ngành
- "produced_in": sản phẩm được sản xuất tại làng nghề
- "associated_with": nhân vật liên quan đến sự kiện/nơi

Trả về JSON array, mỗi phần tử: {{"from": "id1", "to": "id2", "type": "loại"}}
Chỉ trả JSON array, không text khác. Nếu không tìm thấy mối liên hệ nào, trả []."""

        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            content = response.choices[0].message.content.strip()
            content = re.sub(r"^```json\s*", "", content)
            content = re.sub(r"\s*```$", "", content)
            rels = json.loads(content)
            if isinstance(rels, list):
                for r in rels:
                    if all(k in r for k in ("from", "to", "type")):
                        r["auto"] = True
                        new_rels.append(r)
        except Exception as e:
            print(f"  LLM batch error: {e}")

    return new_rels


# ── Main CLI ──

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Auto-discover relationships between entities")
    parser.add_argument("--apply", action="store_true", help="Actually add new relationships to data.json")
    parser.add_argument("--llm", action="store_true", help="Also use LLM for complex relationship discovery")
    args = parser.parse_args()

    print("=" * 50)
    print("vinhlong360 — Relationship Discovery")
    print("=" * 50)

    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    print(f"  Loaded: {len(data['entities'])} entities, {len(data['relationships'])} existing relationships")

    # Rule-based
    new_rels = discover_all(data)
    print(f"\n  Rule-based discovery: {len(new_rels)} new relationships")

    for r in new_rels:
        print(f"    {r['from']} --[{r['type']}]--> {r['to']}")

    # LLM-based (optional)
    if args.llm:
        content_entities = [e for e in data["entities"] if e["type"] != "place"]
        llm_rels = discover_with_llm(content_entities)
        # Deduplicate with rule-based
        existing_pairs = {(r["from"], r["to"]) for r in new_rels}
        llm_unique = [r for r in llm_rels if (r["from"], r["to"]) not in existing_pairs]
        print(f"\n  LLM discovery: {len(llm_unique)} additional relationships")
        new_rels.extend(llm_unique)

    # Apply
    if args.apply and new_rels:
        data["relationships"].extend(new_rels)
        DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n  ✅ Saved {len(new_rels)} new relationships → data.json")
        print(f"  Total relationships: {len(data['relationships'])}")
    elif new_rels:
        print(f"\n  ⚠ Dry run — add --apply to save changes")
    else:
        print(f"\n  ✓ No new relationships found")

    print()


if __name__ == "__main__":
    main()
