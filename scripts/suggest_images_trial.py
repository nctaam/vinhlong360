"""
GĐ8.2 TRIAL (option C) — read-only image SUGGESTIONS for a sample of famous
entities, so a human can judge real match accuracy before any apply.

Reuses ingest_wikimedia_images.search_wikipedia_image (proven relevance filter:
skips logos/flags/maps, name/type/area keyword matching), adds:
  - sample limit + type filter, prefer entities without images
  - real Commons license + author lookup (B6)
  - reviewable JSON (full clickable image URLs) + summary

Writes NOTHING to data.json/DB. Usage:
  python scripts/suggest_images_trial.py --types attraction,craft_village --limit 40
"""

import argparse
import importlib
import json
import re
import sys
import time
import urllib.parse
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
ing = importlib.import_module("ingest_wikimedia_images")  # reuse search + filters

COMMONS = "https://commons.wikimedia.org/w/api.php"
LICENSE_OK = ("cc0", "public domain", "cc by", "cc-by", "creative commons", "pdm", "cc-by-sa")
_client = httpx.Client(headers=ing.HEADERS, timeout=25, follow_redirects=True)


def commons_license(image_url: str) -> dict:
    m = re.search(r"/commons/(?:thumb/)?[0-9a-f]/[0-9a-f]{2}/([^/]+)", image_url)
    if not m:
        return {"license": "(non-Commons)", "artist": "", "ok": False}
    fname = urllib.parse.unquote(m.group(1))
    try:
        r = _client.get(COMMONS, params={
            "action": "query", "titles": f"File:{fname}", "prop": "imageinfo",
            "iiprop": "extmetadata", "format": "json"})
        page = next(iter(r.json().get("query", {}).get("pages", {}).values()), {})
        info = page.get("imageinfo", [{}])
        ext = info[0].get("extmetadata", {}) if info else {}
        lic = (ext.get("LicenseShortName", {}) or {}).get("value", "") or (ext.get("License", {}) or {}).get("value", "")
        artist = re.sub(r"<[^>]+>", "", (ext.get("Artist", {}) or {}).get("value", "")).strip()
        return {"license": lic or "(unknown)", "artist": artist[:70],
                "ok": any(k in (lic or "").lower() for k in LICENSE_OK)}
    except Exception:
        return {"license": "(lookup error)", "artist": "", "ok": False}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--types", default="attraction,craft_village")
    ap.add_argument("--limit", type=int, default=40)
    ap.add_argument("--out", default="scratch/img_trial.json")
    args = ap.parse_args()

    data = json.loads((ROOT / "web" / "data.json").read_text(encoding="utf-8"))
    types = {t.strip() for t in args.types.split(",") if t.strip()}
    ents = [e for e in data.get("entities", [])
            if e.get("type") in types and e.get("name") and not e.get("images")]
    ents.sort(key=lambda e: e.get("confidence", 0), reverse=True)
    ents = ents[:args.limit]

    print(f"Tra {len(ents)} entity nổi bật (types={','.join(sorted(types))}), chưa có ảnh...\n")
    rows, hit, lic_ok = [], 0, 0
    for i, e in enumerate(ents, 1):
        res = ing.search_wikipedia_image(e["name"], e)
        if res:
            lic = commons_license(res["url"])
            hit += 1
            lic_ok += 1 if lic["ok"] else 0
            rows.append({"id": e["id"], "name": e["name"], "type": e["type"], "area": e.get("area"),
                         "wp_title": res["title"], "image": res["url"],
                         "license": lic["license"], "license_ok": lic["ok"], "artist": lic["artist"]})
            flag = "✓" if lic["ok"] else "⚠"
            print(f"[{i:>2}] {flag}lic {e['name'][:32]:<32} → {res['title'][:28]:<28} [{lic['license'][:16]}]")
        else:
            rows.append({"id": e["id"], "name": e["name"], "type": e["type"], "match": "NONE"})
            print(f"[{i:>2}] —    {e['name'][:32]} (không tìm thấy ảnh phù hợp)")
        time.sleep(0.3)

    pct = 100 * hit // max(len(ents), 1)
    print(f"\n=== {hit}/{len(ents)} có ảnh ứng viên ({pct}%) | {lic_ok} license rõ-ràng-OK ===")
    op = ROOT / args.out
    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Chi tiết + URL ảnh (bấm xem để chấm đúng/sai): {args.out}")


if __name__ == "__main__":
    main()
