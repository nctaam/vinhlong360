# -*- coding: utf-8 -*-
"""R50.2 filler-giọng (SOFT-RATCHET) + R10.9 địa danh ngoài tỉnh (SOFT-RATCHET).

Filler = tell "đọc-như-AI/miền-Tây-generic" theo playbook chống-AI-spam.
Quét template FE (raw) + web/data.json THEO TRƯỜNG BIÊN-TẬP (name/summary/
description/attributes/itinerary), BỎ field `source` (SP6: tên bài báo được
trích dẫn là giọng của NGUỒN, không phải giọng biên tập của site) + metadata
(coords/province/url/images). SP6 kéo nợ xuống; ratchet chặn phát sinh.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .common import RegexCheck, _norm, load_json_cached, repo_root

FILLERS = [
    r"(?<!Xây dựng )(?<!đờn ca tài tử )(?<!ĐCTT )(?<!3 tỉnh )miền Tây",
    r"sông nước hữu tình",
    r"thiên đường",
    r"hidden gem",
    r"must[- ]see",
    r"không thể bỏ lỡ",
    r"đắm chìm",
    r"hòa mình vào",
    r"điểm đến lý tưởng",
]
_DEFAULT_OUT_OF_PROVINCE = [r"Cái Bè", r"Lai Vung", r"Định Yên"]
_DEFAULT_OUT_OF_PROVINCE_MSG = "địa danh NGOÀI tỉnh (Đồng Tháp/Tiền Giang cũ) — kiểm xuất xứ (R10.9)"


def _load_out_of_province(root: Path | None) -> tuple[list[str], str]:
    if root is None:
        return _DEFAULT_OUT_OF_PROVINCE, _DEFAULT_OUT_OF_PROVINCE_MSG
    cfg_path = root / "config" / "province.config.json"
    if not cfg_path.exists():
        return _DEFAULT_OUT_OF_PROVINCE, _DEFAULT_OUT_OF_PROVINCE_MSG
    try:
        guards = json.loads(cfg_path.read_text(encoding="utf-8-sig")).get("contentGuards", {})
        patterns = guards.get("outOfProvincePatterns")
        message = guards.get("outOfProvinceMessage") or _DEFAULT_OUT_OF_PROVINCE_MSG
        if isinstance(patterns, list) and all(isinstance(p, str) and p for p in patterns):
            return [re.escape(p) for p in patterns], str(message)
    except (OSError, ValueError, TypeError):
        pass
    return _DEFAULT_OUT_OF_PROVINCE, _DEFAULT_OUT_OF_PROVINCE_MSG


OUT_OF_PROVINCE, _ = _load_out_of_province(Path(__file__).resolve().parents[2])

DATA_REL = "web/data.json"

# Key KHÔNG phải giọng biên tập: id/metadata/nguồn/toạ độ/ảnh. Khớp là bỏ nhánh.
# (anchor cho các cột id-like; substring cho nhóm nguồn/địa-lý-kỹ-thuật)
SKIP_KEY = re.compile(
    r"^(id|type|placeid|area|slug|legacyarea|status|verified|parentid|confidence|"
    r"level|createdat|updatedat|verifiedat|created_at)$"
    r"|source|url|coord|province|image|link|website",
    re.I,
)


def _walk_authored(obj):
    """Sinh mọi chuỗi biên-tập trong obj, bỏ nhánh có key metadata/nguồn."""
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if SKIP_KEY.search(k):
                continue
            yield from _walk_authored(v)
    elif isinstance(obj, list):
        for x in obj:
            yield from _walk_authored(x)


def _authored_texts(data: dict):
    for e in data.get("entities", []):
        yield from _walk_authored(e)
    for it in data.get("itineraries", []):
        yield from _walk_authored(it)


class VoiceCheck:
    """R50.2/R10.9 — FE raw per-match + data.json theo trường biên-tập (bỏ source)."""

    def __init__(self, name: str, level: str, rule: str, patterns: list[str],
                 fe_roots: list[str], msg: str, root: Path | None = None):
        self.name, self.level, self.rule = name, level, rule
        self._patterns = [re.compile(p) for p in patterns]
        self._raw_patterns = patterns
        self.fe_roots = fe_roots
        self.msg = msg
        self._root = root

    @property
    def root(self) -> Path:
        return self._root or repo_root()

    def run(self, files: list[str] | None = None) -> dict:
        violations: list[dict] = []
        # 1) FE template — raw per-match (không đổi so với bản cũ)
        fe = RegexCheck(
            name=self.name, level=self.level, rule=self.rule, patterns=self._raw_patterns,
            globs=["*.vue", "*.ts", "*.py"], roots=self.fe_roots,
            exclude_paths=["web-nuxt/node_modules"], msg=self.msg,
            root=self._root, count_matches=True,
        )
        violations.extend(fe.run(files)["violations"])
        # 2) data.json — chỉ trường biên-tập (bỏ source/metadata)
        want_data = files is None or DATA_REL in [_norm(f) for f in files]
        if want_data:
            path = self.root / DATA_REL
            if path.exists():
                try:
                    data = load_json_cached(path)
                except (OSError, ValueError):
                    data = None
                if data:
                    for txt in _authored_texts(data):
                        for p in self._patterns:
                            for _ in p.finditer(txt):
                                violations.append({"file": DATA_REL, "line": 0,
                                                   "rule": self.rule, "msg": self.msg})
        return {"check": self.name, "level": self.level, "rule": self.rule,
                "count": len(violations), "violations": violations}


def build_checks(root: Path | None = None) -> list:
    out_patterns, out_msg = _load_out_of_province(root)
    return [
        VoiceCheck(
            name="content_fillers", level="soft-ratchet", rule="R50.2", patterns=FILLERS,
            fe_roots=["web-nuxt/pages", "web-nuxt/components", "web-nuxt/utils", "web-nuxt/composables", "agent/seo.py"],
            msg="filler giọng generic — thay bằng đặc-thù bản địa (R50.2, playbook)", root=root,
        ),
        VoiceCheck(
            name="out_of_province", level="soft-ratchet", rule="R10.9", patterns=out_patterns,
            fe_roots=["web-nuxt/pages", "web-nuxt/components", "web-nuxt/utils"],
            msg=out_msg, root=root,
        ),
    ]


CHECKS = build_checks()
