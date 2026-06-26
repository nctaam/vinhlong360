"""Tests cho storage.py — sniff_image_type, _slugify, _to_webp, path validation."""

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from storage import (  # noqa: E402
    ALLOWED_TYPES,
    MAX_IMAGE_SIZE,
    WEBP_SIZES,
    Storage,
    _slugify,
    sniff_image_type,
)


# ── sniff_image_type ──


class TestSniffImageType:
    def test_jpeg(self):
        data = b"\xff\xd8\xff\xe0" + b"\x00" * 20
        assert sniff_image_type(data) == "image/jpeg"

    def test_png(self):
        data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
        assert sniff_image_type(data) == "image/png"

    def test_gif87a(self):
        data = b"GIF87a" + b"\x00" * 20
        assert sniff_image_type(data) == "image/gif"

    def test_gif89a(self):
        data = b"GIF89a" + b"\x00" * 20
        assert sniff_image_type(data) == "image/gif"

    def test_webp(self):
        data = b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"\x00" * 20
        assert sniff_image_type(data) == "image/webp"

    def test_avif(self):
        data = b"\x00\x00\x00\x1c" + b"ftyp" + b"avif" + b"\x00" * 20
        assert sniff_image_type(data) == "image/avif"

    def test_unknown_bytes(self):
        assert sniff_image_type(b"\x00\x01\x02\x03" * 5) is None

    def test_empty_bytes(self):
        assert sniff_image_type(b"") is None

    def test_too_short(self):
        assert sniff_image_type(b"\xff\xd8") is None

    def test_none_input(self):
        assert sniff_image_type(None) is None


# ── _slugify ──


class TestSlugify:
    def test_basic(self):
        assert _slugify("Kẹo Dừa") == "k-o-d-a"

    def test_empty(self):
        assert _slugify("") == "img"

    def test_none(self):
        assert _slugify(None) == "img"

    def test_special_chars(self):
        result = _slugify("hello world! @#$")
        assert ".." not in result
        assert "/" not in result

    def test_max_length(self):
        result = _slugify("a" * 100)
        assert len(result) <= 48


# ── Storage local backend ──


class TestStorageLocal:
    @pytest.fixture
    def local_storage(self, tmp_path, monkeypatch):
        monkeypatch.setattr("storage.LOCAL_MEDIA_DIR", tmp_path / "media")
        monkeypatch.setattr("storage._BACKEND", "local")
        monkeypatch.setattr("storage._PUBLIC_BASE", "/media")
        s = Storage()
        s.backend = "local"
        s.use_s3 = False
        return s

    def test_put_local(self, local_storage, tmp_path):
        url = local_storage._put(b"test data", "test/file.txt", "text/plain")
        assert url == "/media/test/file.txt"
        written = (tmp_path / "media" / "test" / "file.txt").read_bytes()
        assert written == b"test data"

    def test_delete_local(self, local_storage, tmp_path):
        media = tmp_path / "media"
        media.mkdir(parents=True, exist_ok=True)
        f = media / "test.txt"
        f.write_bytes(b"data")
        local_storage.delete("/media/test.txt")
        assert not f.exists()

    def test_delete_nonexistent_noop(self, local_storage):
        local_storage.delete("/media/nonexistent.txt")


# ── Validation ──


class TestStorageValidation:
    @pytest.fixture
    def local_storage(self, tmp_path, monkeypatch):
        monkeypatch.setattr("storage.LOCAL_MEDIA_DIR", tmp_path / "media")
        monkeypatch.setattr("storage._BACKEND", "local")
        monkeypatch.setattr("storage._PUBLIC_BASE", "/media")
        s = Storage()
        s.backend = "local"
        s.use_s3 = False
        return s

    def test_upload_image_set_too_large(self, local_storage):
        data = b"\xff" * (MAX_IMAGE_SIZE + 1)
        with pytest.raises(ValueError, match="quá lớn"):
            local_storage.upload_image_set(data, folder="test")

    def test_upload_image_set_path_traversal(self, local_storage):
        with pytest.raises(ValueError, match="Invalid folder"):
            local_storage.upload_image_set(b"\xff\xd8\xff" * 10, folder="../etc")

    def test_upload_image_set_absolute_path(self, local_storage):
        with pytest.raises(ValueError, match="Invalid folder"):
            local_storage.upload_image_set(b"\xff\xd8\xff" * 10, folder="/tmp/hack")

    def test_upload_image_path_traversal(self, local_storage):
        with pytest.raises(ValueError, match="Invalid folder"):
            asyncio.run(local_storage.upload_image(b"\xff\xd8\xff" * 10, folder="../etc"))

    def test_upload_image_bad_content_type(self, local_storage):
        with pytest.raises(ValueError, match="không hỗ trợ"):
            asyncio.run(local_storage.upload_image(b"data", folder="test", content_type="text/html"))


# ── Constants ──


def test_allowed_types():
    assert "image/jpeg" in ALLOWED_TYPES
    assert "image/webp" in ALLOWED_TYPES
    assert "text/html" not in ALLOWED_TYPES


def test_webp_sizes():
    assert "sm" in WEBP_SIZES
    assert "md" in WEBP_SIZES
    assert "lg" in WEBP_SIZES
    assert WEBP_SIZES["sm"] < WEBP_SIZES["md"] < WEBP_SIZES["lg"]
