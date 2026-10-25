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
import re
import shutil
import threading
from pathlib import Path

from versioned_json_store import load_json, replace_json

logger = logging.getLogger(__name__)

AGENT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = AGENT_DIR.parent
DATA_JSON = PROJECT_DIR / "web" / "data.json"
SNAP_DIR = AGENT_DIR / "data" / "kb_snapshots"
SNAP_DIR.mkdir(parents=True, exist_ok=True)
MANIFEST = SNAP_DIR / "manifest.json"

KEEP_SNAPSHOTS = 20
_SNAP_ID_RE = re.compile(r"^[A-Za-z0-9_.-]{1,120}$")
_snap_lock = threading.RLock()


def _safe_snap_path(filename: str) -> Path | None:
    if not filename or "/" in filename or "\\" in filename or ".." in filename:
        return None
    base = SNAP_DIR.resolve()
    candidate = (SNAP_DIR / filename).resolve()
    if candidate.parent != base:
        return None
    return SNAP_DIR / filename


def _load_manifest() -> list:
    if MANIFEST.exists():
        try:
            return json.loads(MANIFEST.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("Failed to load snapshot manifest: %s", exc)
            return []
    return []


def _save_manifest(entries: list):
    from versioned_json_store import atomic_write_json

    atomic_write_json(MANIFEST, entries, indent=2)


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
    with _snap_lock:
        if not DATA_JSON.exists():
            return None
        entries = _load_manifest()
        if snapshot_id is None:
            snapshot_id = f"snap_{len(entries) + 1:05d}"
        elif not _SNAP_ID_RE.match(snapshot_id) or ".." in snapshot_id:
            return None

        dest = _safe_snap_path(f"{snapshot_id}.json")
        if dest is None:
            return None
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
                old_path = _safe_snap_path(str(old.get("file", "")))
                try:
                    if old_path is not None and old_path.exists():
                        old_path.unlink()
                except Exception as exc:
                    logger.warning("Failed to prune snapshot %s: %s", old_path, exc)
            entries = entries[-KEEP_SNAPSHOTS:]

        _save_manifest(entries)
        return entry


def list_snapshots() -> list:
    with _snap_lock:
        return _load_manifest()


def rollback(snapshot_id: str | None = None, expected_version: str | None = None) -> dict:
    """Restore data.json from a snapshot (latest if id is None).

    Guarded callers pass ``expected_version`` so rollback refuses to erase data
    changed after the guarded apply. Omitting it keeps force-rollback behavior
    for explicit manual recovery, while still using the shared write lock.

    Returns {restored: bool, id, entity_count}. Caller is responsible for
    calling knowledge.reload() only when ``restored`` is true.
    """
    with _snap_lock:
        entries = _load_manifest()
        if not entries:
            return {"restored": False, "error": "no snapshots"}

        if snapshot_id is None:
            target = entries[-1]
        else:
            target = next((e for e in entries if e["id"] == snapshot_id), None)
            if target is None:
                return {"restored": False, "error": f"snapshot {snapshot_id} not found"}

        src = _safe_snap_path(str(target.get("file", "")))
        if src is None or not src.exists():
            return {"restored": False, "error": f"snapshot file missing: {target.get('file')}"}

        snapshot_data = load_json(src)
        if not replace_json(DATA_JSON, snapshot_data, expected_version=expected_version):
            return {"restored": False, "error": "rollback_conflict"}
        return {"restored": True, "id": target["id"], "entity_count": target["entity_count"]}


def stats() -> dict:
    with _snap_lock:
        entries = _load_manifest()
        return {
            "count": len(entries),
            "latest": entries[-1] if entries else None,
            "keep": KEEP_SNAPSHOTS,
        }
