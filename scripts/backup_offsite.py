"""
Upload the latest local backup to S3-compatible storage (Cloudflare R2 / Backblaze B2).

Uses the AWS CLI (`aws s3 cp`) for actual upload.  If the CLI is not installed
the script prints installation instructions and exits 1.

Environment variables (or CLI flags):
    S3_ENDPOINT   — e.g. https://<account>.r2.cloudflarestorage.com
    S3_ACCESS_KEY  — access key ID
    S3_SECRET_KEY  — secret access key
    S3_BUCKET      — bucket name
    S3_REGION      — region (default: auto)

Usage:
    python scripts/backup_offsite.py                          # upload latest backup
    python scripts/backup_offsite.py --backup-dir backups/    # custom backup dir
    python scripts/backup_offsite.py --dry-run                # show what would be done
    python scripts/backup_offsite.py --bucket my-bucket --prefix prod/
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _file_size_human(path: Path) -> str:
    size = path.stat().st_size
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def _find_latest_backup(backup_dir: Path) -> Path | None:
    """Return the most-recently-modified file or directory inside *backup_dir*."""
    if not backup_dir.is_dir():
        return None

    candidates: list[Path] = []
    # Look for tarball files first (deploy.sh creates .tar.gz backups)
    for ext in ("*.tar.gz", "*.zip", "*.sql"):
        candidates.extend(backup_dir.glob(ext))
    # Also consider timestamped subdirectories (backup_data.py style)
    candidates.extend(d for d in backup_dir.iterdir() if d.is_dir())

    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _check_aws_cli() -> str | None:
    """Return path to aws CLI, or None if not found."""
    return shutil.which("aws")


def _build_env(
    endpoint: str | None,
    access_key: str | None,
    secret_key: str | None,
    region: str,
) -> dict[str, str]:
    """Build an environment dict for the aws subprocess."""
    env = dict(os.environ)
    if access_key:
        env["AWS_ACCESS_KEY_ID"] = access_key
    if secret_key:
        env["AWS_SECRET_ACCESS_KEY"] = secret_key
    if region:
        env["AWS_DEFAULT_REGION"] = region
    return env


def _upload(
    aws_cli: str,
    local_path: Path,
    bucket: str,
    prefix: str,
    endpoint: str | None,
    env: dict[str, str],
    dry_run: bool,
) -> bool:
    """Upload *local_path* (file or directory) to s3://*bucket*/*prefix*."""
    s3_dest = f"s3://{bucket}/{prefix.strip('/')}/{local_path.name}"

    cmd: list[str] = [aws_cli, "s3", "cp"]
    if local_path.is_dir():
        cmd.append("--recursive")
    cmd.append(str(local_path))
    cmd.append(s3_dest)
    if endpoint:
        cmd.extend(["--endpoint-url", endpoint])

    if dry_run:
        print("[offsite] DRY-RUN would execute:")
        print(f"  {' '.join(cmd)}")
        return True

    print(f"[offsite] uploading {local_path.name} -> {s3_dest}")
    try:
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=600,
        )
        if result.returncode != 0:
            print(f"[offsite] FAILED (exit {result.returncode})", file=sys.stderr)
            if result.stderr:
                print(f"  stderr: {result.stderr.strip()}", file=sys.stderr)
            return False
        if result.stdout:
            print(f"  {result.stdout.strip()}")
        print("[offsite] upload OK")
        return True
    except subprocess.TimeoutExpired:
        print("[offsite] FAILED: upload timed out after 600s", file=sys.stderr)
        return False
    except FileNotFoundError:
        print("[offsite] FAILED: aws CLI not found during execution", file=sys.stderr)
        return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Upload latest local backup to S3-compatible storage."
    )
    parser.add_argument(
        "--backup-dir",
        default=str(ROOT / "backups"),
        help="directory containing backups (default: backups/)",
    )
    parser.add_argument(
        "--bucket",
        default=os.environ.get("S3_BUCKET", ""),
        help="S3 bucket name (default: $S3_BUCKET)",
    )
    parser.add_argument(
        "--prefix",
        default="vl360-backups/",
        help="S3 key prefix (default: vl360-backups/)",
    )
    parser.add_argument(
        "--endpoint",
        default=os.environ.get("S3_ENDPOINT", ""),
        help="S3-compatible endpoint URL (default: $S3_ENDPOINT)",
    )
    parser.add_argument(
        "--region",
        default=os.environ.get("S3_REGION", "auto"),
        help="AWS region (default: $S3_REGION or 'auto')",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="show what would be uploaded without actually uploading",
    )
    args = parser.parse_args()

    # --- check aws CLI ---
    aws_cli = _check_aws_cli()
    if aws_cli is None:
        print(
            "[offsite] ERROR: 'aws' CLI not found.\n"
            "\n"
            "Install the AWS CLI:\n"
            "  pip install awscli            # via pip\n"
            "  brew install awscli           # macOS\n"
            "  choco install awscli          # Windows (Chocolatey)\n"
            "  # or download from https://aws.amazon.com/cli/\n"
            "\n"
            "For Cloudflare R2, set:\n"
            "  S3_ENDPOINT=https://<account-id>.r2.cloudflarestorage.com\n"
            "  S3_ACCESS_KEY=<your-key>\n"
            "  S3_SECRET_KEY=<your-secret>\n"
            "  S3_BUCKET=<your-bucket>\n",
            file=sys.stderr,
        )
        return 1

    # --- resolve config ---
    access_key = os.environ.get("S3_ACCESS_KEY", "")
    secret_key = os.environ.get("S3_SECRET_KEY", "")
    endpoint = args.endpoint or None
    bucket = args.bucket

    if not bucket:
        print(
            "[offsite] ERROR: no bucket specified. Use --bucket or set S3_BUCKET.",
            file=sys.stderr,
        )
        return 1

    if not access_key or not secret_key:
        print(
            "[offsite] WARNING: S3_ACCESS_KEY / S3_SECRET_KEY not set. "
            "aws CLI will use its default credentials chain.",
        )

    # --- find latest backup ---
    backup_dir = Path(args.backup_dir)
    # Also check scratch/backups (backup_data.py destination)
    if not backup_dir.is_dir():
        alt = ROOT / "scratch" / "backups"
        if alt.is_dir():
            backup_dir = alt
            print(f"[offsite] backups/ not found, using {alt}")

    latest = _find_latest_backup(backup_dir)
    if latest is None:
        print(
            f"[offsite] ERROR: no backups found in {backup_dir}",
            file=sys.stderr,
        )
        return 1

    print(f"[offsite] latest backup: {latest.name}")
    if latest.is_file():
        print(f"[offsite] size: {_file_size_human(latest)}")

    # --- upload ---
    env = _build_env(endpoint, access_key, secret_key, args.region)
    ok = _upload(aws_cli, latest, bucket, args.prefix, endpoint, env, args.dry_run)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
