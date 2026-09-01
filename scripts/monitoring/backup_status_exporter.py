"""Minimal unauthenticated backup-status exporter for Prometheus.

Only aggregate operational state is exposed; artifact contents and admin data
never leave the exporter. Configure BACKUP_DIR to the read-only backup mount.
"""

from __future__ import annotations

import os
import sys
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backup_manifest import find_latest_manifest
from backup_manifest import load_manifest, validate_manifest_artifact

BACKUP_DIR = Path(os.environ.get("BACKUP_DIR", "/backups"))


def _manifest_artifact(manifest_path: Path):
    """Return a verified manifest/artifact pair, or ``None`` when invalid."""
    try:
        raw = manifest_path.read_text(encoding="utf-8")
        import json

        payload = json.loads(raw)
        declared = (payload.get("artifact") or {}).get("path") or payload.get("artifact_path")
        if not isinstance(declared, str) or not declared.strip():
            return None
        artifact = (manifest_path.parent / declared).resolve()
        if artifact.parent != manifest_path.parent.resolve() or not artifact.is_file():
            return None
        manifest = load_manifest(manifest_path)
        validate_manifest_artifact(manifest, artifact)
        return manifest, artifact
    except (OSError, ValueError, TypeError, UnicodeError):
        return None


def render_metrics() -> str:
    now = time.time()
    success = 0.0
    failure = 0.0
    stale = 1.0
    try:
        result = find_latest_manifest(BACKUP_DIR)
    except Exception:
        result = None
    if result is not None:
        _, manifest = result
        try:
            created = datetime.fromisoformat(manifest.created_at.replace("Z", "+00:00")).timestamp()
            success = created
            stale = 1.0 if now - created > 86400 else 0.0
        except (TypeError, ValueError, OverflowError):
            failure = now
    else:
        failure = now

    # Keep the previous verified success visible when a newer manifest is
    # malformed/tampered, while exposing the failure timestamp separately.
    try:
        manifest_paths = list(BACKUP_DIR.rglob("manifest.json")) + list(BACKUP_DIR.rglob("*.manifest.json"))
        newest = max(manifest_paths, key=lambda path: path.stat().st_mtime) if manifest_paths else None
        if newest is not None and _manifest_artifact(newest) is None:
            failure = max(failure, newest.stat().st_mtime)
    except (OSError, ValueError):
        failure = max(failure, now)
    lines = [
        "# HELP vl360_backup_last_success_timestamp_seconds Unix timestamp of the last checksum-verified backup.",
        "# TYPE vl360_backup_last_success_timestamp_seconds gauge",
        f"vl360_backup_last_success_timestamp_seconds {success:g}",
        "# HELP vl360_backup_last_failure_timestamp_seconds Unix timestamp of the latest invalid/missing backup state.",
        "# TYPE vl360_backup_last_failure_timestamp_seconds gauge",
        f"vl360_backup_last_failure_timestamp_seconds {failure:g}",
        "# HELP vl360_backup_stale Whether the latest verified backup is stale (1/0).",
        "# TYPE vl360_backup_stale gauge",
        f"vl360_backup_stale {stale:g}",
        "# HELP vl360_backup_exporter_up Exporter health.",
        "# TYPE vl360_backup_exporter_up gauge",
        "vl360_backup_exporter_up 1",
    ]
    return "\n".join(lines) + "\n"


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        if self.path != "/metrics":
            self.send_response(404)
            self.end_headers()
            return
        body = render_metrics().encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        return


def main() -> int:
    server = HTTPServer((os.environ.get("LISTEN_HOST", "0.0.0.0"), int(os.environ.get("PORT", "9105"))), _Handler)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
