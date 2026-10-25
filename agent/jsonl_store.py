"""Shared JSONL write/rotation primitives for public, admin and community APIs."""

from __future__ import annotations

import json
import logging
import threading
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

JSONL_MAX_LINES = 5000
jsonl_lock = threading.Lock()
_jsonl_line_state: dict[Path, tuple[int, int]] = {}


def append_jsonl(filepath: Path, record: Mapping[str, object]) -> None:
    """Append one JSON record under the shared lock, then apply rotation."""
    payload = json.dumps(record, ensure_ascii=False) + "\n"
    with jsonl_lock:
        filepath.parent.mkdir(exist_ok=True)
        cached = _jsonl_line_state.get(filepath)
        pre_size = filepath.stat().st_size if cached and filepath.exists() else -1
        with open(filepath, "a", encoding="utf-8") as file:
            file.write(payload)
        if cached and cached[0] == pre_size:
            next_lines = cached[1] + 1
            _jsonl_line_state[filepath] = (filepath.stat().st_size, next_lines)
            if next_lines <= JSONL_MAX_LINES:
                return
        maybe_rotate_jsonl(filepath)


def maybe_rotate_jsonl(filepath: Path) -> None:
    try:
        if not filepath.exists():
            _jsonl_line_state.pop(filepath, None)
            return
        lines = filepath.read_text(encoding="utf-8").splitlines()
        if len(lines) <= JSONL_MAX_LINES:
            _jsonl_line_state[filepath] = (filepath.stat().st_size, len(lines))
            return
        archive = filepath.with_suffix(f".{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.jsonl")
        archive.write_text("\n".join(lines[:-JSONL_MAX_LINES]) + "\n", encoding="utf-8")
        import os
        import tempfile

        fd, tmp_name = tempfile.mkstemp(
            dir=str(filepath.parent),
            prefix=f".{filepath.name}.",
            suffix=".tmp",
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write("\n".join(lines[-JSONL_MAX_LINES:]) + "\n")
                f.flush()
                os.fsync(f.fileno())
            Path(tmp_name).replace(filepath)
            _jsonl_line_state[filepath] = (filepath.stat().st_size, JSONL_MAX_LINES)
        finally:
            Path(tmp_name).unlink(missing_ok=True)
    except Exception:
        logger.exception("JSONL rotation failed for %s", filepath)
