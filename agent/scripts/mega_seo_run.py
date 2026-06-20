#!/usr/bin/env python3
"""MEGA SEO RUNNER — SEO-optimized content for ALL 1816 entities.

Generates rich, search-optimized Vietnamese content: meta title, meta description,
long-form description, FAQ schema, related keywords, internal linking suggestions.

SEQUENTIAL — one API call at a time (proxy constraint).
Resume-safe via JSONL done set.

Usage:
  python -u agent/scripts/mega_seo_run.py 2>&1
"""
from __future__ import annotations
import json, os, sys, time, warnings
warnings.filterwarnings("ignore", message=".*renamed.*ddgs.*")
from pathlib import Path

AGENT_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = AGENT_DIR.parent
OUTPUT_DIR = AGENT_DIR / "data" / "mega_research" / "seo"

sys.path.insert(0, str(AGENT_DIR))
sys.path.insert(0, str(AGENT_DIR / "scripts"))
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_DIR / ".env")
except Exception:
    pass

from mega_research import (LLM, read_jsonl, append_jsonl, load_entities,
                           log, utc, _cfg_io)

SYS = "Bạn là SEO EXPERT + CONTENT STRATEGIST cho du lịch Việt Nam. Trả về JSON thuần túy. Viết tiếng Việt tự nhiên."

BATCH_SIZE = 5


def build_batch_prompt(entities):
    items = []
    for e in entities:
        items.append(f'- id:"{e["id"]}", name:"{e.get("name","")}", type:"{e.get("type","")}", area:"{e.get("area","")}", desc:"{(e.get("description","") or "")[:200]}"')
    entity_list = "\n".join(items)

    return f"""Viết SEO content cho {len(entities)} địa điểm/entity sau. Mỗi entity cần:
1. meta_title (55-60 ký tự, có keyword chính)
2. meta_description (150-160 ký tự, có CTA)
3. h1 (tiêu đề trang, khác meta_title)
4. long_description (300-500 từ, tự nhiên, informative, có keyword)
5. faq (3 câu hỏi FAQ schema, Q&A format)
6. keywords (10 từ khóa liên quan, Vietnamese)
7. related_searches (5 gợi ý tìm kiếm liên quan)
8. slug_suggestion (URL-friendly Vietnamese slug)

Entities:
{entity_list}

JSON: {{"entities":[{{"id":"...","meta_title":"...","meta_description":"...","h1":"...","long_description":"...","faq":[{{"q":"...","a":"..."}}...],"keywords":[...],"related_searches":[...],"slug":"..."}}...]}}"""


def main():
    _cfg_io()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    llm = LLM()
    if not llm.ok:
        log("ERROR: LLM not configured"); return

    t0 = time.time()
    log(f"Model: {llm.model}")

    f = OUTPUT_DIR / "seo_content.jsonl"
    done = set()
    for r in read_jsonl(f):
        if "entities" in r:
            for ent in r["entities"]:
                done.add(ent.get("id", ""))
        elif "id" in r:
            done.add(r["id"])

    all_entities = load_entities()
    remaining = [e for e in all_entities if e.get("id") not in done]
    log(f"Total entities: {len(all_entities)}, remaining: {len(remaining)}, done: {len(done)}")

    batches = [remaining[i:i+BATCH_SIZE] for i in range(0, len(remaining), BATCH_SIZE)]
    log(f"Batches of {BATCH_SIZE}: {len(batches)}")

    for bi, batch in enumerate(batches):
        t1 = time.time()
        names = ", ".join(e.get("name", "?")[:20] for e in batch)
        log(f"[{bi+1}/{len(batches)}] {names}...")
        prompt = build_batch_prompt(batch)
        r = llm.ask_json(sys=SYS, user=prompt, temp=0.2, max_tok=6000)
        elapsed = time.time() - t1
        if r:
            r["batch_index"] = bi; r["ts"] = utc()
            append_jsonl(f, r)
            size = len(json.dumps(r, ensure_ascii=False))
            log(f"  ✓ batch {bi+1} ({elapsed:.0f}s, {size} chars)")
        else:
            log(f"  ✗ batch {bi+1} ({elapsed:.0f}s) — no valid JSON")
        log(f"  LLM: {llm.info()}")

    total_min = (time.time() - t0) / 60
    log(f"\n═══ DONE ({total_min:.1f}m) ═══")
    log(f"  FINAL: {llm.info()}")


if __name__ == "__main__":
    main()
