"""Fail when the checked-in OpenAPI contract differs from live FastAPI routes."""

from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPORTER = ROOT / "scripts" / "export_openapi.py"
DEFAULT_SNAPSHOT = ROOT / "contracts" / "openapi" / "backend-openapi.json"

# Keep contract generation local and deterministic even when invoked from a
# developer shell that has production credentials in its environment.
SENSITIVE_ENVIRONMENT_KEYS = (
    "DATABASE_URL",
    "LLM_API_KEY",
    "LLM_BASE_URL",
    "ADMIN_API_KEY",
    "JWT_SECRET",
    "CSRF_SECRET",
    "CHAT_OWNER_SECRET",
    "CASE_KERNEL_ENCRYPTION_KEY",
    "ESMS_API_KEY",
    "ESMS_SECRET",
    "TELEGRAM_BOT_TOKEN",
    "ZALO_OA_ACCESS_TOKEN",
    "ZALO_OA_SECRET",
    "S3_ACCESS_KEY",
    "S3_SECRET_KEY",
    "R2_ACCESS_KEY_ID",
    "R2_SECRET_ACCESS_KEY",
    "VISION_API_KEY",
    "WEATHER_API_KEY",
    "IMAGE_API_KEY",
    "MEMORY_ENCRYPTION_KEY",
    "TOTP_ENC_KEY",
    "EXPORT_CURSOR_SECRET",
    "PILOT_ATTEST_RUNNER_KEY",
)


def _safe_export_environment() -> dict[str, str]:
    """Return an environment that cannot select production services."""

    inherited = os.environ
    # Preserve interpreter/runtime variables (including Python's user-site
    # location on Windows), then blank anything that looks credential-like.
    environment = dict(inherited)
    for key in tuple(environment):
        upper = key.upper()
        if any(marker in upper for marker in ("KEY", "SECRET", "TOKEN", "PASSWORD")):
            environment[key] = ""
    environment.update(
        {
            "PYTHONIOENCODING": "utf-8",
            "PYTHONUTF8": "1",
            "PYTHONHASHSEED": "0",
            "ENVIRONMENT": "development",
            "CORS_ORIGINS": "http://localhost:8360",
            "REDIS_URL": "",
            "R2_ENDPOINT": "",
            "S3_ENDPOINT": "",
            "LOCATION_REVERSE_GEOCODER_URL": "",
            "LOCATION_IP_GEOCODER_URL": "",
            "LOG_LEVEL": "WARNING",
            "OTEL_ENABLED": "false",
            "SCHEDULER_ENABLED": "false",
            "BACKGROUND_INDEX_BUILD": "false",
            "BUILD_SEARCH_INDEXES": "false",
            "DESTRUCTIVE_OPS_LOCKED": "1",
            "VL360_DISABLE_DOTENV": "1",
        }
    )
    for key in SENSITIVE_ENVIRONMENT_KEYS:
        # Blank values stop load_dotenv's non-overriding load from importing a
        # local production .env file for any known credential.
        environment[key] = ""
    if os.name == "nt":
        for key in ("SystemRoot", "SYSTEMROOT", "TEMP", "TMP"):
            value = inherited.get(key)
            if value:
                environment[key] = value
    return environment


def _export_to(path: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(EXPORTER), "--output", str(path)],
        cwd=ROOT,
        env=_safe_export_environment(),
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"OpenAPI exporter failed with exit code {result.returncode}")


def check_drift(snapshot: Path) -> int:
    if not snapshot.is_file():
        print(f"Contract snapshot is missing: {snapshot}", file=sys.stderr)
        print(
            "Regenerate it with: python scripts/export_openapi.py "
            "--output contracts/openapi/backend-openapi.json",
            file=sys.stderr,
        )
        return 2

    try:
        with tempfile.TemporaryDirectory(prefix="vl360-openapi-") as directory:
            generated = Path(directory) / "backend-openapi.json"
            _export_to(generated)
            expected = snapshot.read_bytes()
            actual = generated.read_bytes()
    except (OSError, RuntimeError) as exc:
        print(f"Contract drift check could not export OpenAPI: {exc}", file=sys.stderr)
        print(
            "Regenerate it with: python scripts/export_openapi.py "
            "--output contracts/openapi/backend-openapi.json",
            file=sys.stderr,
        )
        return 2

    if actual != expected:
        print(f"Contract drift detected in {snapshot}", file=sys.stderr)
        print(
            f"  checked-in sha256: {hashlib.sha256(expected).hexdigest()}",
            file=sys.stderr,
        )
        print(f"  live export sha256: {hashlib.sha256(actual).hexdigest()}", file=sys.stderr)
        print(
            "Regenerate it with: python scripts/export_openapi.py "
            "--output contracts/openapi/backend-openapi.json",
            file=sys.stderr,
        )
        return 1

    print(f"OpenAPI contract is up to date: {snapshot}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--snapshot",
        type=Path,
        default=DEFAULT_SNAPSHOT,
        help="checked-in OpenAPI snapshot to compare (defaults to the canonical contract)",
    )
    args = parser.parse_args(argv)
    snapshot = args.snapshot if args.snapshot.is_absolute() else ROOT / args.snapshot
    return check_drift(snapshot.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
