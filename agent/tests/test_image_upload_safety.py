"""
Image upload safety — magic-byte sniff (không tin Content-Type) + chống
decompression-bomb + lỗi decode → 400. Offline (PIL có sẵn, không cần PG/mạng).
"""
import io
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from storage import sniff_image_type, _to_webp  # noqa: E402
from database import db  # noqa: E402

pg_only = pytest.mark.skipif(
    not db._use_pg,
    reason="UGC upload là Postgres-only (SQLite dev trả 503). Set DATABASE_URL để chạy.",
)


def _png(size=(8, 8), color=(0, 128, 0)) -> bytes:
    from PIL import Image
    b = io.BytesIO()
    Image.new("RGB", size, color).save(b, "PNG")
    return b.getvalue()


def _jpeg() -> bytes:
    from PIL import Image
    b = io.BytesIO()
    Image.new("RGB", (8, 8)).save(b, "JPEG")
    return b.getvalue()


# ── sniff: nhận đúng ảnh thật ──────────────────────────────────────────────
def test_sniff_accepts_png():
    assert sniff_image_type(_png()) == "image/png"


def test_sniff_accepts_jpeg():
    assert sniff_image_type(_jpeg()) == "image/jpeg"


def test_sniff_accepts_gif():
    assert sniff_image_type(b"GIF89a" + b"\x00" * 16) == "image/gif"


def test_sniff_accepts_webp():
    assert sniff_image_type(b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 8) == "image/webp"


# ── sniff: từ chối nội dung nguy hiểm / không phải ảnh ──────────────────────
def test_sniff_rejects_svg_script():
    svg = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
    assert sniff_image_type(svg) is None


def test_sniff_rejects_html():
    assert sniff_image_type(b"<!DOCTYPE html><html><body>x</body></html>") is None


def test_sniff_rejects_too_short():
    assert sniff_image_type(b"abc") is None
    assert sniff_image_type(b"") is None


# ── _to_webp: lỗi decode → ValueError (endpoint dịch sang 400) ──────────────
def test_to_webp_raises_on_junk():
    with pytest.raises(ValueError):
        _to_webp(b"this is not an image, definitely not a valid one at all", 400)


def test_to_webp_processes_real_png_to_webp():
    out = _to_webp(_png(), 400)
    assert sniff_image_type(out) == "image/webp"


# ── endpoint: /api/upload/image từ chối non-image dù gắn nhãn image/png ──────
@pg_only
def test_upload_endpoint_rejects_fake_image():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    import social
    from auth_middleware import require_user

    app = FastAPI()
    app.include_router(social.router)
    app.dependency_overrides[require_user] = lambda: {
        "id": "00000000-0000-0000-0000-000000000000", "display_name": "tester",
    }
    client = TestClient(app)
    # SVG-script gắn nhãn image/png → magic-byte chặn → 400 (không 500)
    r = client.post("/api/upload/image",
                    files={"file": ("x.png", b'<svg><script>alert(1)</script></svg>', "image/png")})
    assert r.status_code == 400
