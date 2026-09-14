#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ingest authentic documentary/journalistic photos for entities.

- Downloads or reads real photos from news/official portals.
- Converts and optimizes locally as WebP (max-width 1200px, quality 82).
- Saves to web-nuxt/public/img/entities/{entity_id}.webp.
- Updates SQLite entities.attributes with image_author, image_source, image_type, is_verified_photo.
- Synchronizes SQLite -> web/data.json.
"""

from __future__ import annotations

import argparse
import io
import json
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any

from PIL import Image

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "agent" / "data" / "vinhlong360.db"
DATA_JSON_PATH = ROOT / "web" / "data.json"
IMG_DIR = ROOT / "web-nuxt" / "public" / "img" / "entities"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def optimize_and_save_webp(img_bytes: bytes, target_path: Path) -> int:
    """Optimize image to WebP with max dimension 1200px and quality 82."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(io.BytesIO(img_bytes)) as img:
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")

        max_w = 1200
        if img.width > max_w:
            new_h = int(img.height * (max_w / img.width))
            img = img.resize((max_w, new_h), Image.Resampling.LANCZOS)

        img.save(target_path, format="WEBP", quality=82, method=6)
    return target_path.stat().st_size


def fetch_image_bytes(source: str) -> bytes:
    """Fetch image bytes from URL or local file path."""
    source_str = source.strip()
    if source_str.startswith("http://") or source_str.startswith("https://"):
        import requests

        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            "Referer": "https://www.google.com/",
        }
        resp = requests.get(source_str, headers=headers, timeout=20)
        resp.raise_for_status()
        return resp.content

    file_path = Path(source_str)
    if not file_path.is_absolute():
        file_path = ROOT / file_path
    if not file_path.exists():
        raise FileNotFoundError(f"Local image file not found: {file_path}")
    return file_path.read_bytes()


def ingest_entity_image(
    conn: sqlite3.Connection,
    entity_id: str,
    source: str,
    author: str,
    source_name: str,
    caption: str = "",
    license_str: str = "",
) -> dict[str, Any]:
    """Ingest a single entity image into WebP and update SQLite."""
    cur = conn.cursor()
    cur.execute("SELECT id, name, attributes FROM entities WHERE id = ?", (entity_id,))
    row = cur.fetchone()
    if not row:
        raise ValueError(f"Entity '{entity_id}' not found in database.")

    _eid, name, attrs_raw = row
    attrs = json.loads(attrs_raw or "{}")

    target_webp = IMG_DIR / f"{entity_id}.webp"
    if source and source.strip():
        img_bytes = fetch_image_bytes(source)
        file_size = optimize_and_save_webp(img_bytes, target_webp)
    else:
        if not target_webp.exists() or target_webp.stat().st_size < 100:
            raise FileNotFoundError(f"Local target WebP not found or empty: {target_webp}")
        file_size = target_webp.stat().st_size

    attrs["image_author"] = author.strip()
    attrs["image_source"] = source_name.strip()
    attrs["image_type"] = "documentary"
    attrs["is_verified_photo"] = True
    if caption:
        attrs["image_caption"] = caption.strip()
    attrs["image_license"] = license_str.strip() or f"Tư liệu báo chí / {source_name.strip()}"

    local_rel_url = f"/img/entities/{entity_id}.webp"
    cur.execute(
        "UPDATE entities SET images = ?, attributes = ?, updatedAt = datetime('now') WHERE id = ?",
        (json.dumps([local_rel_url], ensure_ascii=False), json.dumps(attrs, ensure_ascii=False), entity_id),
    )
    conn.commit()

    return {
        "id": entity_id,
        "name": name,
        "author": attrs["image_author"],
        "source": attrs["image_source"],
        "size_bytes": file_size,
        "path": str(target_webp.relative_to(ROOT)),
    }


def _process_batch(conn: sqlite3.Connection, batch_file: Path) -> list[dict[str, Any]]:
    """Process a batch JSON file of photo descriptors."""
    if not batch_file.is_absolute():
        batch_file = ROOT / batch_file
    with open(batch_file, "r", encoding="utf-8") as f:
        items = json.load(f)

    results: list[dict[str, Any]] = []
    print(f"[*] Ingesting batch of {len(items)} documentary photos...")
    for item in items:
        try:
            res = ingest_entity_image(
                conn,
                entity_id=item["entity_id"],
                source=item.get("image", ""),
                author=item["author"],
                source_name=item["source"],
                caption=item.get("caption", ""),
                license_str=item.get("license", ""),
            )
            kb = res["size_bytes"] / 1024
            print(f"  ✓ {res['id']}: {res['name']} | Ảnh: {res['author']} · {res['source']} ({kb:.1f} KB)")
            results.append(res)
        except Exception as err:
            print(f"  ✖ {item.get('entity_id')}: Error: {err}", file=sys.stderr)
    return results


def _sync_export() -> bool:
    """Synchronize SQLite data to web/data.json."""
    print("[*] Synchronizing to web/data.json...")
    cmd = [sys.executable, str(ROOT / "scripts" / "export_data.py"), "--out", str(DATA_JSON_PATH)]
    ret = subprocess.run(cmd, capture_output=True, text=True)
    if ret.returncode == 0:
        print("  ✓ Synchronized web/data.json successfully.")
        return True
    print(f"  ✖ Export failed:\n{ret.stderr}", file=sys.stderr)
    return False


def _build_parser() -> argparse.ArgumentParser:
    """Build argument parser for CLI."""
    parser = argparse.ArgumentParser(description="Ingest authentic documentary entity photos into WebP")
    parser.add_argument("--entity-id", help="Entity ID in SQLite")
    parser.add_argument("--image", default="", help="URL or local file path to source image")
    parser.add_argument("--author", help="Photographer or author name")
    parser.add_argument("--source", help="Publication / source portal name (e.g. Báo Vĩnh Long)")
    parser.add_argument("--caption", default="", help="Optional image caption")
    parser.add_argument("--license", default="", help="Optional license string")
    parser.add_argument("--batch", help="Path to JSON file containing array of photo descriptors")
    parser.add_argument("--skip-export", action="store_true", help="Skip syncing to web/data.json")
    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)
    results = []

    if args.batch:
        results = _process_batch(conn, Path(args.batch))
    elif args.entity_id and args.author and args.source:
        res = ingest_entity_image(
            conn,
            entity_id=args.entity_id,
            source=args.image,
            author=args.author,
            source_name=args.source,
            caption=args.caption,
            license_str=args.license,
        )
        kb = res["size_bytes"] / 1024
        print(f"✓ Ingested {res['id']} ({res['name']}): Ảnh: {res['author']} · {res['source']} ({kb:.1f} KB)")
        results.append(res)
    else:
        parser.print_help()
        sys.exit(1)

    conn.close()

    if not args.skip_export and results:
        _sync_export()


if __name__ == "__main__":
    main()
