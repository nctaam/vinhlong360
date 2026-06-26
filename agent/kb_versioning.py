"""
vinhlong360 — KB Versioning & Rollback.

Immutable snapshots of the knowledge base (web/data.json) taken before every
autonomous self-modification, so any regression or KB pollution is "one revert
away" (the rollback discipline from the self-evolving-agents safety literature).

Snapshots live in agent/data/kb_snapshots/ as timestamped copies + a manifest.
Old snapshots are pruned (keep last N). All writes are atomic.
"""

import json
import logging
import shutil
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

AGENT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = AGENT_DIR.parent
DATA_JSON = PROJECT_DIR / "web" / "data.json"
SNAP_DIR = AGENT_DIR / "data" / "kb_snapshots"
SNAP_DIR.mkdir(parents=True, exist_ok=True)
MANIFEST = SNAP_DIR / "manifest.json"

KEEP_SNAPSHOTS = 20


def _load_manifest() -> list:
    if MANIFEST.exists():
        try:
            return json.loads(MANIFEST.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("Failed to load snapshot manifest: %s", exc)
            return []
    return []


def _save_manifest(entries: list):
    tmp = MANIFEST.with_suffix(".tmp")
    tmp.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(MANIFEST)


def _entity_count(path: Path) -> int:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return len(data.get("entities", []))
    except Exception as exc:
        logger.debug("Failed to count entities in %s: %s", path, exc)
        return -1


def snapshot(reason: str, snapshot_id: str | None = None) -> dict | None:
    """Create an immutable snapshot of data.json.

    `snapshot_id` should be a caller-supplied stable id (e.g. a timestamp passed
    in via args); if None, a counter-based id is used (no wall-clock here so the
    module stays import-safe in restricted runtimes).
    """
    if not DATA_JSON.exists():
        return None
    entries = _load_manifest()
    if snapshot_id is None:
        snapshot_id = f"snap_{len(entries) + 1:05d}"

    dest = SNAP_DIR / f"{snapshot_id}.json"
    shutil.copy2(DATA_JSON, dest)

    entry = {
        "id": snapshot_id,
        "reason": reason,
        "file": dest.name,
        "entity_count": _entity_count(dest),
    }
    entries.append(entry)

    # Prune old snapshots (keep last N)
    if len(entries) > KEEP_SNAPSHOTS:
        for old in entries[:-KEEP_SNAPSHOTS]:
            old_path = SNAP_DIR / old["file"]
            try:
                if old_path.exists():
                    old_path.unlink()
            except Exception as exc:
                logger.warning("Failed to prune snapshot %s: %s", old_path, exc)
        entries = entries[-KEEP_SNAPSHOTS:]

    _save_manifest(entries)
    return entry


def list_snapshots() -> list:
    return _load_manifest()


def rollback(snapshot_id: str | None = None) -> dict:
    """Restore data.json from a snapshot (latest if id is None).

    Returns {restored: bool, id, entity_count} . Caller is responsible for
    calling knowledge.reload() afterwards.
    """
    entries = _load_manifest()
    if not entries:
        return {"restored": False, "error": "no snapshots"}

    if snapshot_id is None:
        target = entries[-1]
    else:
        target = next((e for e in entries if e["id"] == snapshot_id), None)
        if target is None:
            return {"restored": False, "error": f"snapshot {snapshot_id} not found"}

    src = SNAP_DIR / target["file"]
    if not src.exists():
        return {"restored": False, "error": f"snapshot file missing: {target['file']}"}

    # Atomic restore
    tmp = DATA_JSON.with_suffix(".rollback.tmp")
    shutil.copy2(src, tmp)
    tmp.replace(DATA_JSON)
    return {"restored": True, "id": target["id"], "entity_count": target["entity_count"]}


def stats() -> dict:
    entries = _load_manifest()
    return {
        "count": len(entries),
        "latest": entries[-1] if entries else None,
        "keep": KEEP_SNAPSHOTS,
    }
