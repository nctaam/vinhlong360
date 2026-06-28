"""
vinhlong360 — object storage (Cloudflare R2 in prod) + WebP pipeline.

Backend selection (first that is fully configured wins):
  1. Cloudflare R2  — R2_ACCESS_KEY_ID + R2_SECRET_ACCESS_KEY (endpoint/bucket/
     public-base default to the project's values, override via env).
  2. Generic S3     — S3_ENDPOINT + S3_ACCESS_KEY + S3_SECRET_KEY (legacy/Bizfly).
  3. Local FS       — web/media/ (dev fallback, served by Nuxt/nginx at /media/).

Public URLs are built from the PUBLIC base (e.g. https://cdn.vinhlong360.vn) so
the private S3 API endpoint is never exposed. Only the two R2_*_KEY values are
secret and must be set in .env; everything else has a safe default.

Usage:
  from storage import storage
  urls = storage.upload_image_set(jpeg_bytes, folder="entities", slug="keo-dua")
  # -> {"sm": ".../entities/keo-dua-<hash>-400.webp", "md": ..., "lg": ...}
  url = await storage.upload_image(webp_bytes, folder="posts")  # single, legacy
  storage.delete(url)
"""

import io
import logging
import os
import re
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)

LOCAL_MEDIA_DIR = Path(__file__).resolve().parent.parent / "web" / "media"

# ── Cloudflare R2 (preferred) ──────────────────────────────────────────────
# Non-secret defaults baked in so prod only needs the two *_KEY values in .env.
R2_ENDPOINT = os.getenv("R2_ENDPOINT", "https://b0dacfc035669a6b0b4fe331c760a6d7.r2.cloudflarestorage.com")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY", "")
R2_BUCKET = os.getenv("R2_BUCKET", "vinhlong360")
R2_PUBLIC_BASE = os.getenv("R2_PUBLIC_BASE", "https://cdn.vinhlong360.vn").rstrip("/")

# ── Generic S3 (legacy / Bizfly) ───────────────────────────────────────────
S3_ENDPOINT = os.getenv("S3_ENDPOINT", "")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "")
S3_BUCKET = os.getenv("S3_BUCKET", "vinhlong360-media")
S3_REGION = os.getenv("S3_REGION", "hn")
S3_PUBLIC_BASE = os.getenv("S3_PUBLIC_BASE", "").rstrip("/")

if R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY:
    _BACKEND = "r2"
    _ENDPOINT, _AK, _SK = R2_ENDPOINT, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY
    _BUCKET, _REGION = R2_BUCKET, "auto"
    _PUBLIC_BASE = R2_PUBLIC_BASE
elif S3_ENDPOINT and S3_ACCESS_KEY and S3_SECRET_KEY:
    _BACKEND = "s3"
    _ENDPOINT, _AK, _SK = S3_ENDPOINT, S3_ACCESS_KEY, S3_SECRET_KEY
    _BUCKET, _REGION = S3_BUCKET, S3_REGION
    _PUBLIC_BASE = S3_PUBLIC_BASE or f"{S3_ENDPOINT}/{S3_BUCKET}"
else:
    _BACKEND = "local"
    _ENDPOINT = _AK = _SK = _BUCKET = ""
    _REGION = ""
    _PUBLIC_BASE = "/media"

_s3 = None
if _BACKEND in ("r2", "s3"):
    import boto3
    from botocore.config import Config

    _s3 = boto3.client(
        "s3",
        endpoint_url=_ENDPOINT,
        aws_access_key_id=_AK,
        aws_secret_access_key=_SK,
        region_name=_REGION,
        config=Config(signature_version="s3v4"),
    )

MAX_IMAGE_SIZE = 12 * 1024 * 1024  # 12MB raw upload before processing
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/avif", "image/gif"}
# Responsive WebP widths (px). Cover/detail images get all three.
WEBP_SIZES = {"sm": 400, "md": 800, "lg": 1600}
WEBP_QUALITY = 82


def _slugify(s: str) -> str:
    s = (s or "img").lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:48] or "img"


def sniff_image_type(data: bytes) -> str | None:
    """Nhận dạng ảnh raster qua magic-byte (KHÔNG tin Content-Type client gửi).
    Trả MIME nếu là JPEG/PNG/GIF/WebP/AVIF; None nếu không phải (vd SVG, HTML, polyglot)."""
    if not data or len(data) < 12:
        return None
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    # AVIF/HEIF: hộp 'ftyp' với brand avif/avis/mif1
    if data[4:8] == b"ftyp" and data[8:12] in (b"avif", b"avis", b"mif1"):
        return "image/avif"
    return None


# Trần điểm-ảnh chống decompression-bomb (ảnh nhỏ-byte nhưng giải nén khổng lồ → DoS).
MAX_IMAGE_PIXELS = 40_000_000  # ~40MP, đủ cho ảnh máy ảnh thật


def _to_webp(data: bytes, max_w: int) -> bytes:
    """Re-encode to WebP at <= max_w (strips EXIF, honours orientation).
    Raise ValueError nếu dữ liệu không phải ảnh hợp lệ / là bom giải-nén."""
    from PIL import Image, ImageOps

    Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS  # PIL raise DecompressionBombError khi vượt
    try:
        img = Image.open(io.BytesIO(data))
        img.load()  # buộc giải mã ngay để bắt lỗi/bom sớm (Image.open vốn lazy)
    except Exception as e:  # UnidentifiedImageError, DecompressionBombError, truncated...
        raise ValueError("File ảnh không hợp lệ hoặc đã hỏng") from e
    img = ImageOps.exif_transpose(img)  # apply rotation, then EXIF is dropped on save
    has_alpha = "A" in img.getbands()
    img = img.convert("RGBA" if has_alpha else "RGB")
    if img.width > max_w:
        h = round(img.height * max_w / img.width)
        img = img.resize((max_w, h), Image.LANCZOS)
    out = io.BytesIO()
    img.save(out, format="WEBP", quality=WEBP_QUALITY, method=6)
    return out.getvalue()


class Storage:
    def __init__(self):
        self.backend = _BACKEND
        self.use_s3 = _BACKEND in ("r2", "s3")
        if self.backend == "local":
            LOCAL_MEDIA_DIR.mkdir(parents=True, exist_ok=True)

    # Magic-byte sniff (truy cập qua instance: storage.sniff_image_type(data))
    sniff_image_type = staticmethod(sniff_image_type)

    # ── low-level put ──────────────────────────────────────────────────────
    def _put(self, data: bytes, key: str, content_type: str) -> str:
        if self.use_s3:
            extra = {"ContentType": content_type, "CacheControl": "public, max-age=31536000, immutable"}
            if self.backend == "s3":
                extra["ACL"] = "public-read"
            _s3.upload_fileobj(io.BytesIO(data), _BUCKET, key, ExtraArgs=extra)
            logger.debug("Uploaded %s to %s/%s (%d bytes)", content_type, self.backend, key, len(data))
            return f"{_PUBLIC_BASE}/{key}"
        path = (LOCAL_MEDIA_DIR / key).resolve()
        if not path.is_relative_to(LOCAL_MEDIA_DIR.resolve()):
            raise ValueError("Invalid storage key")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        logger.debug("Saved local file %s (%d bytes)", path, len(data))
        return f"/media/{key}"

    # ── responsive set (cover/detail images) ───────────────────────────────
    def upload_image_set(self, data: bytes, folder: str = "entities",
                         slug: str = "img") -> dict:
        """Process to WebP at sm/md/lg widths, upload all, return {size: url}."""
        if len(data) > MAX_IMAGE_SIZE:
            raise ValueError(f"Ảnh quá lớn (tối đa {MAX_IMAGE_SIZE // 1024 // 1024}MB)")
        if ".." in folder or folder.startswith("/"):
            raise ValueError(f"Invalid folder path: {folder}")
        base = f"{_slugify(slug)}-{uuid.uuid4().hex[:8]}"
        urls = {}
        for size, width in WEBP_SIZES.items():
            webp = _to_webp(data, width)
            key = f"{folder}/{base}-{width}.webp"
            urls[size] = self._put(webp, key, "image/webp")
        return urls

    # ── single image (legacy: posts/reviews already WebP-encoded client side) ─
    async def upload_image(self, data: bytes, folder: str = "uploads",
                           content_type: str = "image/webp") -> str:
        if len(data) > MAX_IMAGE_SIZE:
            raise ValueError(f"File quá lớn (tối đa {MAX_IMAGE_SIZE // 1024 // 1024}MB)")
        if ".." in folder or folder.startswith("/"):
            raise ValueError(f"Invalid folder path: {folder}")
        if content_type not in ALLOWED_TYPES:
            raise ValueError(f"Định dạng không hỗ trợ: {content_type}")
        import asyncio
        def _sync_upload():
            webp = _to_webp(data, WEBP_SIZES["lg"])
            key = f"{folder}/{uuid.uuid4().hex[:12]}.webp"
            return self._put(webp, key, "image/webp")
        return await asyncio.to_thread(_sync_upload)

    def delete(self, key_or_url: str):
        if self.use_s3:
            key = key_or_url
            if key.startswith("http"):
                key = key.split(f"{_PUBLIC_BASE}/")[-1] if _PUBLIC_BASE in key else key.rsplit("/", 1)[-1]
            _s3.delete_object(Bucket=_BUCKET, Key=key)
            logger.debug("Deleted %s/%s", self.backend, key)
        else:
            path = (LOCAL_MEDIA_DIR / key_or_url.replace("/media/", "")).resolve()
            if not path.is_relative_to(LOCAL_MEDIA_DIR.resolve()):
                logger.warning("Path traversal attempt in storage.delete: %s", key_or_url[:100])
                return
            try:
                path.unlink()
                logger.debug("Deleted local file %s", path)
            except FileNotFoundError:
                pass


storage = Storage()
