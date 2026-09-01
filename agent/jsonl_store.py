"""Shared JSONL write/rotation primitives for public, admin and community APIs."""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

JSONL_MAX_LINES = 5000
jsonl_lock = threading.Lock()


def maybe_rotate_jsonl(filepath: Path) -> None:
    try:
        if not filepath.exists():
            return
        lines = filepath.read_text(encoding="utf-8").splitlines()
        if len(lines) <= JSONL_MAX_LINES:
            return
        archive = filepath.with_suffix(f".{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.jsonl")
        archive.write_text("\n".join(lines[:-JSONL_MAX_LINES]) + "\n", encoding="utf-8")
        tmp = filepath.with_suffix(".tmp")
        tmp.write_text("\n".join(lines[-JSONL_MAX_LINES:]) + "\n", encoding="utf-8")
        tmp.replace(filepath)
    except Exception:
        logger.exception("JSONL rotation failed for %s", filepath)
