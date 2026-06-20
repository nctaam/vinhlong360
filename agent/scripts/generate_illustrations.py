#!/usr/bin/env python3
"""Illustration Generator — GPT-5.5 Image for vinhlong360 UI assets.

Generates copyright-free illustrations for:
  Batch 1: 3 region hero images (Vĩnh Long, Bến Tre, Trà Vinh)
  Batch 2: Homepage hero / OG default image
  Batch 3: Category icons/illustrations (8 categories)
  Batch 4: Seasonal illustrations (4 seasons)
  Batch 5: Empty state / placeholder illustrations

Uses cx/gpt-5.5-image via scripts/gen_image.py helper.
Output: web-nuxt/public/img/gen/ — ready to use.

SECRET: Reads IMAGE_API_KEY from env — KHÔNG hardcode.
"""
from __future__ import annotations
import json, os, sys, time, subprocess
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent.parent
GEN_SCRIPT = PROJECT_DIR / "scripts" / "gen_image.py"
OUTPUT_DIR = PROJECT_DIR / "web-nuxt" / "public" / "img" / "gen"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR = Path(__file__).resolve().parent.parent / "data" / "illustrations"
LOG_DIR.mkdir(parents=True, exist_ok=True)

os.environ["PYTHONUNBUFFERED"] = "1"
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_DIR / ".env")
except Exception:
    pass

API_KEY = os.environ.get("IMAGE_API_KEY", "")
RUN_TS = datetime.now().strftime("%Y%m%d_%H%M%S")


def tprint(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


STYLE_BASE = (
    "Watercolor illustration style, soft warm palette, Vietnamese Mekong Delta scenery, "
    "gentle brush strokes, dreamy atmospheric perspective, golden hour lighting, "
    "clean composition suitable for web hero image, no text, no watermark, "
    "16:9 aspect ratio composition, high detail, professional quality"
)

ILLUSTRATIONS = [
    # Batch 1: Region heroes
    {
        "id": "hero-vinh-long",
        "file": "hero-vinh-long.jpg",
        "size": "1536x1024",
        "prompt": f"{STYLE_BASE}. Vĩnh Long province Vietnam: lush green fruit orchards (cam sành oranges, bưởi Năm Roi pomelo), traditional pottery village (Mang Thít), peaceful river with small wooden boats, coconut palms, a rustic fruit garden entrance with hanging fruits, warm sunrise colors reflecting on calm river water",
    },
    {
        "id": "hero-ben-tre",
        "file": "hero-ben-tre.jpg",
        "size": "1536x1024",
        "prompt": f"{STYLE_BASE}. Bến Tre province Vietnam - the Coconut Land: endless rows of tall coconut palms, small canal with traditional sampan boat, coconut candy workshop scene in background, green bưởi da xanh pomelos hanging from trees, Cồn Phụng island atmosphere, tropical lush greenery, soft morning mist",
    },
    {
        "id": "hero-tra-vinh",
        "file": "hero-tra-vinh.jpg",
        "size": "1536x1024",
        "prompt": f"{STYLE_BASE}. Trà Vinh province Vietnam - Khmer culture: ancient Khmer pagoda with ornate golden roof and naga serpent decorations, serene Ao Bà Om (Bà Om Pond) surrounded by ancient trees, traditional Khmer motifs, monks in saffron robes in background, unique dừa sáp (special waxy coconut), peaceful countryside atmosphere",
    },

    # Batch 2: Homepage / OG
    {
        "id": "hero-homepage",
        "file": "hero-homepage.jpg",
        "size": "1536x1024",
        "prompt": f"{STYLE_BASE}. Panoramic view of Vietnamese Mekong Delta combining three provinces: fruit orchards, coconut palms, Khmer pagoda in distance, floating market scene, river with boats, tropical birds, vibrant but harmonious warm colors, inviting and magical atmosphere, wide cinematic composition",
    },
    {
        "id": "og-default",
        "file": "og-default.jpg",
        "size": "1200x630",
        "prompt": "Clean modern illustration for social media card, Vietnamese Mekong Delta travel theme, watercolor style, warm golden colors, iconic elements: river, coconut palm, pagoda, tropical fruits, boat. Balanced composition with space for text overlay on left side. Professional, inviting, memorable. No text.",
    },

    # Batch 3: Category illustrations
    {
        "id": "cat-dish",
        "file": "cat-dish.jpg",
        "size": "1024x1024",
        "prompt": f"{STYLE_BASE}, square format. Vietnamese Mekong Delta cuisine: steaming bowl of bún nước lèo (Khmer noodle soup), bánh xèo (crispy pancake), fresh tropical fruits on banana leaf, coconut candy, local herbs and vegetables, warm kitchen atmosphere, appetizing food photography style but watercolor",
    },
    {
        "id": "cat-attraction",
        "file": "cat-attraction.jpg",
        "size": "1024x1024",
        "prompt": f"{STYLE_BASE}, square format. Tourist attractions in Mekong Delta: iconic river scene with traditional wooden bridge, floating market, garden gate entrance, temple in distance, butterflies and tropical flowers, magical discovery feeling",
    },
    {
        "id": "cat-nature",
        "file": "cat-nature.jpg",
        "size": "1024x1024",
        "prompt": f"{STYLE_BASE}, square format. Mekong Delta nature: bird sanctuary with egrets and herons, mangrove forest, water hyacinth flowers on calm canal, fireflies at dusk, lotus pond, serene untouched nature atmosphere",
    },
    {
        "id": "cat-craft",
        "file": "cat-craft.jpg",
        "size": "1024x1024",
        "prompt": f"{STYLE_BASE}, square format. Vietnamese craft village: artisan hands weaving coconut leaf, pottery wheel with clay vessel, traditional loom, coconut shell crafts, warm workshop interior with natural light, cultural heritage atmosphere",
    },
    {
        "id": "cat-history",
        "file": "cat-history.jpg",
        "size": "1024x1024",
        "prompt": f"{STYLE_BASE}, square format. Historical sites in Mekong Delta: ancient Vietnamese đình (communal house) with ornate roof, century-old banyan tree, stone stele, traditional courtyard, weathered but dignified architecture, sense of history and cultural depth",
    },
    {
        "id": "cat-product",
        "file": "cat-product.jpg",
        "size": "1024x1024",
        "prompt": f"{STYLE_BASE}, square format. OCOP local products display: beautifully arranged coconut candy, mật hoa dừa (coconut blossom nectar), khoai lang (sweet potato), rice paper rolls, local honey, woven baskets, artisanal packaging, market stall aesthetic",
    },
    {
        "id": "cat-experience",
        "file": "cat-experience.jpg",
        "size": "1024x1024",
        "prompt": f"{STYLE_BASE}, square format. Mekong Delta travel experience: tourist on traditional sampan boat going through narrow canal, fruit picking in garden, cooking class scene, cycling on rural road, joyful discovery moments, authentic local life",
    },
    {
        "id": "cat-event",
        "file": "cat-event.jpg",
        "size": "1024x1024",
        "prompt": f"{STYLE_BASE}, square format. Vietnamese Mekong Delta festival: traditional boat race (đua ghe ngo), colorful Ok Om Bok Khmer festival lanterns, flower market during Tết, crowd celebration, vibrant energy, cultural joy",
    },

    # Batch 4: Seasonal
    {
        "id": "season-spring",
        "file": "season-spring.jpg",
        "size": "1024x576",
        "prompt": f"{STYLE_BASE}. Spring in Mekong Delta (Tết season): mai vàng (yellow apricot blossoms), hoa đào, traditional Tết decorations, blooming orchards, fresh green rice paddies, festive warm atmosphere, new beginning energy",
    },
    {
        "id": "season-summer",
        "file": "season-summer.jpg",
        "size": "1024x576",
        "prompt": f"{STYLE_BASE}. Summer in Mekong Delta: abundant tropical fruits (mangosteen, rambutan, durian, longan), lush green canopy, children swimming in river, vibrant market scene, intense tropical colors, peak harvest energy",
    },
    {
        "id": "season-autumn",
        "file": "season-autumn.jpg",
        "size": "1024x576",
        "prompt": f"{STYLE_BASE}. Autumn in Mekong Delta: Ok Om Bok festival moonlight, floating lanterns on water, harvest rice paddies golden, gentle rain mist, coconut groves in soft light, contemplative peaceful atmosphere",
    },
    {
        "id": "season-winter",
        "file": "season-winter.jpg",
        "size": "1024x576",
        "prompt": f"{STYLE_BASE}. Dry season in Mekong Delta (Nov-Feb): crisp clear skies, perfect travel weather, outdoor dining scene, cycling tourists, flower gardens in full bloom for Tết preparation, warm golden sunsets, ideal travel atmosphere",
    },

    # Batch 5: Empty states / placeholders
    {
        "id": "empty-search",
        "file": "empty-search.jpg",
        "size": "512x512",
        "prompt": "Cute minimal watercolor illustration: a small Vietnamese sampan boat on calm water with a magnifying glass reflecting the landscape, soft pastel colors, peaceful, whimsical, suitable for empty search results page, no text",
    },
    {
        "id": "empty-community",
        "file": "empty-community.jpg",
        "size": "512x512",
        "prompt": "Cute minimal watercolor illustration: friendly Vietnamese people gathering under a banyan tree sharing stories and food, warm community feeling, soft pastel colors, inviting atmosphere, suitable for empty community feed, no text",
    },
]


def generate_one(item):
    out_path = OUTPUT_DIR / item["file"]
    if out_path.exists():
        tprint(f"  ⏭ {item['id']} — already exists, skip")
        return {"id": item["id"], "status": "skipped"}

    tprint(f"  🎨 {item['id']} — generating ({item['size']})...")
    try:
        result = subprocess.run(
            [
                sys.executable, str(GEN_SCRIPT),
                "--prompt", item["prompt"],
                "--out", str(out_path),
                "--size", item["size"],
            ],
            capture_output=True, text=True, timeout=300,
            env={**os.environ, "IMAGE_API_KEY": API_KEY},
        )
        if result.returncode == 0:
            tprint(f"  ✓ {item['id']} — {out_path.name}")
            return {"id": item["id"], "status": "ok", "file": str(out_path), "stdout": result.stdout.strip()}
        else:
            tprint(f"  ✗ {item['id']} — {result.stderr.strip()[:200]}")
            return {"id": item["id"], "status": "error", "error": result.stderr.strip()[:300]}
    except subprocess.TimeoutExpired:
        tprint(f"  ✗ {item['id']} — timeout (300s)")
        return {"id": item["id"], "status": "timeout"}
    except Exception as e:
        tprint(f"  ✗ {item['id']} — {e}")
        return {"id": item["id"], "status": "error", "error": str(e)}


def main():
    if not API_KEY:
        sys.exit("ERROR: Set env IMAGE_API_KEY first (see scripts/gen_image.py)")

    tprint("=== Illustration Generator ===")
    tprint(f"Total images: {len(ILLUSTRATIONS)}")
    tprint(f"Output: {OUTPUT_DIR}")
    tprint("")

    results = []
    for item in ILLUSTRATIONS:
        r = generate_one(item)
        results.append(r)
        time.sleep(2)

    log_file = LOG_DIR / f"gen_log_{RUN_TS}.json"
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    ok = sum(1 for r in results if r["status"] == "ok")
    skip = sum(1 for r in results if r["status"] == "skipped")
    fail = sum(1 for r in results if r["status"] in ("error", "timeout"))
    tprint(f"\n=== DONE: {ok} generated, {skip} skipped, {fail} failed ===")
    tprint(f"Log: {log_file}")


if __name__ == "__main__":
    main()
