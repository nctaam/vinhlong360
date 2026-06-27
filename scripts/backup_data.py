"""
Snapshot dữ liệu trước MỌI thao tác ETL/migrate/normalize (Bất biến B1 — xem CLAUDE.md).

Sao lưu (không phá gì):
  - web/data.json  (nguồn de-facto hiện tại, KHÔNG tái tạo được)
  - agent/data/vinhlong360.db  (SQLite KB, nếu có)
  - manifest.json  (timestamp + đếm entity/relationship/itinerary)

Đích: scratch/backups/<YYYYmmdd-HHMMSS>/

Dùng:
    python scripts/backup_data.py            # snapshot mặc định
    python scripts/backup_data.py --label x  # gắn nhãn vào tên thư mục

Chỉ dùng thư viện chuẩn — KHÔNG import module agent (tránh side-effect lúc import).
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_JSON = ROOT / "web" / "data.json"
DB_FILE = ROOT / "agent" / "data" / "vinhlong360.db"
BACKUP_ROOT = ROOT / "scratch" / "backups"


def _count_data_json(path: Path) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:  # noqa: BLE001 - manifest chỉ để tham khảo
        return {"error": f"{type(exc).__name__}: {exc}"}

    def _len(key: str) -> int:
        val = data.get(key) if isinstance(data, dict) else None
        return len(val) if isinstance(val, list) else 0

    return {
        "entities": _len("entities"),
        "relationships": _len("relationships"),
        "itineraries": _len("itineraries"),
    }


def _file_size_human(path: Path) -> str:
    size = path.stat().st_size
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def _cleanup_old_backups(keep: int = 5, max_age_days: int = 30) -> None:
    """Remove backups older than *max_age_days*, always keeping the *keep* newest."""
    if not BACKUP_ROOT.is_dir():
        return
    dirs = sorted(
        [d for d in BACKUP_ROOT.iterdir() if d.is_dir()],
        key=lambda d: d.stat().st_mtime,
        reverse=True,
    )
    if len(dirs) <= keep:
        return
    cutoff = datetime.now().timestamp() - max_age_days * 86400
    for d in dirs[keep:]:
        if d.stat().st_mtime < cutoff:
            shutil.rmtree(d, ignore_errors=True)
            print(f"[backup] cleanup: removed old backup {d.name}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Snapshot data.json + SQLite KB trước thao tác dữ liệu.")
    parser.add_argument("--label", default="", help="nhãn thêm vào tên thư mục backup")
    parser.add_argument("--keep", type=int, default=5, help="số bản backup giữ lại tối thiểu (mặc định: 5)")
    parser.add_argument("--max-age-days", type=int, default=30, help="xóa backup cũ hơn N ngày (mặc định: 30)")
    args = parser.parse_args()

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    name = f"{ts}-{args.label}" if args.label else ts
    dest = BACKUP_ROOT / name
    dest.mkdir(parents=True, exist_ok=True)

    manifest: dict = {"timestamp": ts, "copied": [], "counts": {}, "sizes": {}}

    if DATA_JSON.exists():
        shutil.copy2(DATA_JSON, dest / "data.json")
        manifest["copied"].append("web/data.json")
        manifest["counts"] = _count_data_json(DATA_JSON)
        manifest["sizes"]["data.json"] = _file_size_human(DATA_JSON)
    else:
        manifest["counts"] = {"warning": "web/data.json không tồn tại"}

    if DB_FILE.exists():
        shutil.copy2(DB_FILE, dest / "vinhlong360.db")
        manifest["copied"].append("agent/data/vinhlong360.db")
        manifest["sizes"]["vinhlong360.db"] = _file_size_human(DB_FILE)

    with open(dest / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"[backup] -> {dest}")
    print(f"[backup] copied: {', '.join(manifest['copied']) or '(none)'}")
    for fname, size in manifest["sizes"].items():
        print(f"[backup] size: {fname} = {size}")
    print(f"[backup] counts: {manifest['counts']}")

    if not manifest["copied"]:
        print("[backup] CẢNH BÁO: không có gì để sao lưu.", file=sys.stderr)
        return 1

    _cleanup_old_backups(keep=args.keep, max_age_days=args.max_age_days)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
