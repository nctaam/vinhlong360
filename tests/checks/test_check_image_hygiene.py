# -*- coding: utf-8 -*-
"""Unit tests for ImageHygieneCheck (R45.1)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from checks.check_image_hygiene import ImageHygieneCheck  # noqa: E402


def _setup_mock_repo(tmp_path: Path, entities: list[dict], create_images: bool = True) -> Path:
    """Helper to create dummy data.json and web-nuxt images."""
    data_file = tmp_path / "web" / "data.json"
    data_file.parent.mkdir(parents=True, exist_ok=True)
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump({"entities": entities}, f)

    img_dir = tmp_path / "web-nuxt" / "public" / "img" / "entities"
    img_dir.mkdir(parents=True, exist_ok=True)

    if create_images:
        for e in entities:
            eid = e["id"]
            img_file = img_dir / f"{eid}.webp"
            img_file.write_bytes(b"RIFF....WEBPVP8 ...")

    return tmp_path


def test_image_hygiene_clean_dataset(tmp_path: Path) -> None:
    entities = [
        {
            "id": "chua-ong",
            "name": "Chùa Ông",
            "attributes": {
                "image_caption": "Ngôi chùa cổ kính xây dựng năm 1892 tại phường Long Châu."
            },
        }
    ]
    _setup_mock_repo(tmp_path, entities)
    check = ImageHygieneCheck(root=tmp_path)
    res = check.run()
    assert res["count"] == 0
    assert len(res["violations"]) == 0


def test_image_hygiene_missing_file(tmp_path: Path) -> None:
    entities = [
        {
            "id": "missing-entity",
            "name": "Missing",
            "attributes": {"image_caption": "Ảnh miêu tả."},
        }
    ]
    _setup_mock_repo(tmp_path, entities, create_images=False)
    check = ImageHygieneCheck(root=tmp_path)
    res = check.run()
    assert res["count"] == 1
    assert "thiếu tệp ảnh WebP" in res["violations"][0]["msg"]


def test_image_hygiene_empty_file(tmp_path: Path) -> None:
    entities = [
        {
            "id": "empty-file-entity",
            "name": "Empty",
            "attributes": {"image_caption": "Ảnh miêu tả."},
        }
    ]
    _setup_mock_repo(tmp_path, entities, create_images=False)
    empty_img = tmp_path / "web-nuxt" / "public" / "img" / "entities" / "empty-file-entity.webp"
    empty_img.write_bytes(b"")

    check = ImageHygieneCheck(root=tmp_path)
    res = check.run()
    assert res["count"] == 1
    assert "tệp ảnh rỗng 0-byte" in res["violations"][0]["msg"]


def test_image_hygiene_caption_violations(tmp_path: Path) -> None:
    entities = [
        {
            "id": "flawed-caption-1",
            "name": "Flawed 1",
            "attributes": {
                "image_caption": "Khung cảnh tại thị trấn Long Hồ."
            },
        },
        {
            "id": "flawed-caption-2",
            "name": "Flawed 2",
            "attributes": {
                "image_caption": "Đây là thiên đường du lịch miệt vườn."
            },
        },
        {
            "id": "flawed-caption-3",
            "name": "Flawed 3",
            "attributes": {
                "image_caption": "Nằm tại trung tâm thành phố."
            },
        },
        {
            "id": "flawed-caption-4",
            "name": "Flawed 4",
            "attributes": {
                "image_caption": "Địa điểm trực thuộc tỉnh Bến Tre hiện nay."
            },
        },
    ]
    _setup_mock_repo(tmp_path, entities)
    check = ImageHygieneCheck(root=tmp_path)
    res = check.run()
    assert res["count"] == 4
    msgs = [v["msg"] for v in res["violations"]]
    assert any("cấp huyện/thị cũ" in m for m in msgs)
    assert any("từ ngữ filler" in m for m in msgs)
    assert any("mẫu câu sáo mòn" in m for m in msgs)
    assert any("tỉnh cũ" in m for m in msgs)
