# -*- coding: utf-8 -*-
"""SP6 gates mới trên giọng biên tập (đọc trường biên-tập của data.json, bỏ source):
- R50.3 formula: mở bài công thức (Tọa lạc/Nằm ở/…/"là một") + kết sáo (Hãy đến/Đừng bỏ lỡ).
- R50.7 superlative-trơ: "nổi tiếng/nhất vùng/đậm đà bản sắc" trong câu KHÔNG có số/năm/nguồn.
- R10.10 đơn-vị-HC-cũ: "huyện/thị xã/thị trấn X" (cấp huyện đã bỏ 07/2025) trong giọng biên tập.

Tái dùng _authored_texts từ check_content_voice (1 nguồn trích trường). FE quét raw.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .check_content_voice import _authored_texts
from .common import RegexCheck, _norm, repo_root

DATA_REL = "web/data.json"

FORMULA_START = re.compile(r"^\s*(Tọa lạc|Nằm (ở|tại|trong|bên)\b|Là một trong những\b)", re.I)
LA_MOT = re.compile(r"^[^.!?\n]{0,80}?\blà một\b", re.I)
CLICHE_END = re.compile(r"(Hãy đến|Đừng bỏ lỡ|hãy một lần|Hãy ghé)", re.I)
SUPERLATIVE = re.compile(r"nổi tiếng|nhất vùng|đậm đà bản sắc", re.I)
HAS_EVIDENCE = re.compile(r"\d")  # số/năm cùng câu = có dẫn chứng tối thiểu
# "huyện/thị xã/thị trấn" + tên riêng viết hoa ngay sau (tránh 'huyện lỵ' generic)
OLD_ADMIN = re.compile(r"\b(huyện|thị xã|thị trấn)\s+[A-ZĐÀ-Ỹ]")


def _first_sentence(txt: str) -> str:
    return re.split(r"[.!?\n]", txt.strip(), maxsplit=1)[0] if txt.strip() else ""


def _last_sentence(txt: str) -> str:
    parts = [s for s in re.split(r"[.!?\n]", txt.strip()) if s.strip()]
    return parts[-1] if parts else ""


class _DataGate:
    """Nền: quét _authored_texts của data.json + (tuỳ chọn) FE raw."""

    name = level = rule = ""

    def __init__(self, root: Path | None = None):
        self._root = root

    @property
    def root(self) -> Path:
        return self._root or repo_root()

    def _data_hits(self, texts) -> int:  # pragma: no cover — lớp con
        raise NotImplementedError

    def run(self, files: list[str] | None = None) -> dict:
        want = files is None or DATA_REL in [_norm(f) for f in files]
        n = 0
        if want:
            path = self.root / DATA_REL
            if path.exists():
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    data = None
                if data:
                    n = self._data_hits(_authored_texts(data))
        return {"check": self.name, "level": self.level, "rule": self.rule, "count": n,
                "violations": [{"file": DATA_REL, "line": 0, "rule": self.rule,
                                "msg": f"{n} {self.name}"}] if n else []}


class FormulaCheck(_DataGate):
    name, level, rule = "content_formula", "soft-ratchet", "R50.3"

    def _data_hits(self, texts) -> int:
        n = 0
        for t in texts:
            if not t.strip():
                continue
            fs = _first_sentence(t)
            if FORMULA_START.search(fs) or LA_MOT.search(fs):
                n += 1
            if CLICHE_END.search(_last_sentence(t)):
                n += 1
        return n


class SuperlativeCheck(_DataGate):
    name, level, rule = "content_superlative", "soft-ratchet", "R50.7"

    def _data_hits(self, texts) -> int:
        n = 0
        for t in texts:
            for sent in re.split(r"[.!?\n]", t):
                if SUPERLATIVE.search(sent) and not HAS_EVIDENCE.search(sent):
                    n += 1
        return n


class OldAdminCheck(_DataGate):
    name, level, rule = "old_admin_unit", "soft-ratchet", "R10.10"

    def _data_hits(self, texts) -> int:
        return sum(len(OLD_ADMIN.findall(t)) for t in texts)


CHECKS = [FormulaCheck(), SuperlativeCheck(), OldAdminCheck()]
