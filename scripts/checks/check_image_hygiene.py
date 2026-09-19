# -*- coding: utf-8 -*-
"""R45.1 — Cổng kiểm định vệ sinh hình ảnh & chú thích ảnh (HARD).

Quy chuẩn kiểm tra toàn bộ 1.772 thực thể trong web/data.json:
1. Tệp hình ảnh WebP tương ứng phải tồn tại trên ổ đĩa tại
   web-nuxt/public/img/entities/{id}.webp và có dung lượng > 0 bytes.
2. Chú thích hình ảnh (attributes.image_caption) nếu có phải đảm bảo:
   - 0 tàn dư cấp huyện/thị xã/thị trấn cũ.
   - 0 từ ngữ sáo rỗng/filler (miền Tây, thiên đường, điểm đến lý tưởng...).
   - 0 gán nhầm đơn vị hành chính cũ (tỉnh Bến Tre, tỉnh Trà Vinh).
   - 0 câu mở đầu công thức sáo mòn (Tọa lạc tại, Nằm tại, Là một trong những).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from .common import repo_root

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RE_OLD_ADMIN = re.compile(r"\b(huyện|thị xã|thị trấn)\s+[A-ZĐÀ-Ỹ]")
RE_FILLERS = re.compile(
    r"miền Tây|sông nước hữu tình|thiên đường|hidden gem|must[- ]see|"
    r"không thể bỏ lỡ|đắm chìm|hòa mình vào|điểm đến lý tưởng"
)
RE_OLD_PROVINCES = re.compile(r"tỉnh (Bến Tre|Trà Vinh)")
RE_FORMULA_STARTS = re.compile(
    r"^(Tọa lạc tại|Nằm tại|Nằm ở|Nằm bên|Nằm trong|Là một trong những)\b"
)
DATA_REL = "web/data.json"
IMG_BASE = Path("web-nuxt/public/img/entities")


def _get_image_file_map(img_dir: Path) -> dict[str, int]:
    """Pre-scan image directory into a filename -> byte_size map."""
    if not img_dir.exists():
        return {}
    return {p.name: p.stat().st_size for p in img_dir.iterdir() if p.is_file()}


def _check_caption_editorial(caption: str) -> list[str]:
    """Check caption text against editorial rules."""
    errors = []
    if RE_OLD_ADMIN.search(caption):
        errors.append("chú thích chứa tên cấp huyện/thị cũ (R45.1)")
    if RE_FILLERS.search(caption):
        errors.append("chú thích chứa từ ngữ filler sáo rỗng (R45.1)")
    if RE_OLD_PROVINCES.search(caption):
        errors.append("chú thích dùng tỉnh cũ ngoài quy chuẩn (R45.1)")
    if RE_FORMULA_STARTS.search(caption):
        errors.append("chú thích mở đầu bằng mẫu câu sáo mòn (R45.1)")
    return errors


class ImageHygieneCheck:
    name, level, rule = "image_hygiene", "hard", "R45.1"

    def __init__(self, root: Path | None = None):
        self._root = root

    @property
    def root(self) -> Path:
        return self._root or repo_root()

    def run(self, files: list[str] | None = None) -> dict:
        data_path = self.root / DATA_REL
        if not data_path.exists():
            return {"check": self.name, "level": self.level, "rule": self.rule,
                    "count": 0, "violations": []}

        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        img_map = _get_image_file_map(self.root / IMG_BASE)
        violations = []
        for entity in data.get("entities", []):
            eid = entity.get("id", "")
            if not eid:
                continue

            fname = f"{eid}.webp"
            if fname not in img_map:
                violations.append({"file": DATA_REL, "line": 0, "rule": self.rule,
                                   "msg": f"{eid}: thiếu tệp ảnh WebP ({fname})"})
            elif img_map[fname] == 0:
                violations.append({"file": DATA_REL, "line": 0, "rule": self.rule,
                                   "msg": f"{eid}: tệp ảnh rỗng 0-byte ({fname})"})

            attrs = entity.get("attributes") or {}
            caption = attrs.get("image_caption", "")
            if caption:
                for err in _check_caption_editorial(caption):
                    violations.append({"file": DATA_REL, "line": 0, "rule": self.rule,
                                       "msg": f"{eid}: {err}"})

        return {"check": self.name, "level": self.level, "rule": self.rule,
                "count": len(violations), "violations": violations}


CHECKS = [ImageHygieneCheck()]

if __name__ == "__main__":
    check = ImageHygieneCheck()
    result = check.run()
    print(f"[{result['rule']}] {result['check']} ({result['level']}): {result['count']} violations")
    for v in result["violations"][:10]:
        print(f"  - {v['msg']}")
