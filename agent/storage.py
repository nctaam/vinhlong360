"""
vinhlong360 — S3-compatible Object Storage for user-uploaded media.

Uses Bizfly Object Storage (S3-compatible) in production.
Falls back to local filesystem in dev (no S3 credentials).

Usage:
  from storage import storage
  url = await storage.upload_image(file_bytes, "posts/abc123.webp")
  await storage.delete(key)
"""

import hashlib
import io
import os
import uuid
from pathlib import Path

LOCAL_MEDIA_DIR = Path(__file__).resolve().parent.parent / "web" / "media"

S3_ENDPOINT = os.getenv("S3_ENDPOINT", "")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "")
S3_BUCKET = os.getenv("S3_BUCKET", "vinhlong360-media")
S3_REGION = os.getenv("S3_REGION", "hn")

USE_S3 = bool(S3_ENDPOINT and S3_ACCESS_KEY and S3_SECRET_KEY)

if USE_S3:
    import boto3
    from botocore.config import Config

    _s3 = boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
        region_name=S3_REGION,
        config=Config(signature_version="s3v4"),
    )

MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/avif"}


class Storage:

    def __init__(self):
        self.use_s3 = USE_S3
        if not self.use_s3:
            LOCAL_MEDIA_DIR.mkdir(parents=True, exist_ok=True)

    async def upload_image(self, data: bytes, folder: str = "uploads",
                           content_type: str = "image/webp") -> str:
        if len(data) > MAX_IMAGE_SIZE:
            raise ValueError(f"File quá lớn (tối đa {MAX_IMAGE_SIZE // 1024 // 1024}MB)")
        if content_type not in ALLOWED_TYPES:
            raise ValueError(f"Định dạng không hỗ trợ: {content_type}")

        ext = content_type.split("/")[-1]
        if ext == "jpeg":
            ext = "jpg"
        name = f"{uuid.uuid4().hex[:12]}.{ext}"
        key = f"{folder}/{name}"

        if self.use_s3:
            _s3.upload_fileobj(
                io.BytesIO(data), S3_BUCKET, key,
                ExtraArgs={"ContentType": content_type, "ACL": "public-read"},
            )
            return f"{S3_ENDPOINT}/{S3_BUCKET}/{key}"
        else:
            path = LOCAL_MEDIA_DIR / folder
            path.mkdir(parents=True, exist_ok=True)
            (path / name).write_bytes(data)
            return f"/media/{key}"

    async def delete(self, key_or_url: str):
        if self.use_s3:
            key = key_or_url
            if key.startswith("http"):
                key = key.split(f"{S3_BUCKET}/")[-1]
            _s3.delete_object(Bucket=S3_BUCKET, Key=key)
        else:
            path = LOCAL_MEDIA_DIR / key_or_url.replace("/media/", "")
            if path.exists():
                path.unlink()


storage = Storage()
