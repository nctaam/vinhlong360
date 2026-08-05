# -*- coding: utf-8 -*-
"""R10.7 — chống tái nhiễm "tỉnh Bến Tre/Trà Vinh" như đơn vị hiện hành (HARD-RATCHET).

Whitelist per-occurrence: docs/standards/whitelist-tinh-cu.txt — mỗi dòng `entity_id<TAB>field`
(87 occurrence lịch-sử/tên-riêng đã duyệt trong campaign 2026-07-07). Occurrence NGOÀI whitelist
= vi phạm → baseline kỳ vọng 0 (swap-lận: thay 1 dòng cũ bằng 1 dòng mới vẫn bị bắt).
FE code (.vue/.ts): mọi match đều là vi phạm (không có whitelist).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .common import iter_text_files, repo_root

PAT = re.compile(r"tỉnh (Bến Tre|Trà Vinh)")
WHITELIST_REL = "docs/standards/whitelist-tinh-cu.txt"
DATA_REL = "web/data.json"


def _load_whitelist(root: Path) -> dict[tuple[str, str], int]:
    """{(id, field): số occurrence được duyệt}.

    Format `id<TAB>field<TAB>số_lần`; thiếu cột thứ ba = 1 lần. Bản cũ chỉ là
    tập cặp nên một dòng miễn KHÔNG GIỚI HẠN số lần xuất hiện trong field đó —
    trái hẳn chữ "per-occurrence" ở docstring, và đủ để nhét thêm bao nhiêu
    "tỉnh Bến Tre" cũng được vào một field đã duyệt.
    """
    p = root / WHITELIST_REL
    if not p.exists():
        return {}
    allowed: dict[tuple[str, str], int] = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        try:
            times = int(parts[2]) if len(parts) > 2 and parts[2].strip() else 1
        except ValueError:
            times = 1
        key = (parts[0], parts[1])
        allowed[key] = allowed.get(key, 0) + times
    return allowed


def _walk_strings(node, path: str):
    """(đường_dẫn, chuỗi) cho mọi chuỗi trong cây — kể cả trong dict/list lồng."""
    if isinstance(node, str):
        yield path, node
    elif isinstance(node, dict):
        for k, v in node.items():
            yield from _walk_strings(v, f"{path}.{k}" if path else str(k))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _walk_strings(v, f"{path}[{i}]")


def _entity_occurrences(entity: dict):
    for f in ("name", "description", "summary"):
        v = entity.get(f)
        if isinstance(v, str):
            for _ in PAT.finditer(v):
                yield entity["id"], f
    for sub, text in _walk_strings(entity.get("attributes") or {}, ""):
        for _ in PAT.finditer(text):
            yield entity["id"], f"attr:{sub}"


def _itinerary_occurrences(itinerary: dict):
    owner = itinerary.get("id") or "?"
    for sub, text in _walk_strings(itinerary, ""):
        if sub == "id":
            continue
        for _ in PAT.finditer(text):
            yield owner, f"itinerary:{sub}"


def _data_occurrences(root: Path):
    """(owner_id, field) cho mọi occurrence trong data.json.

    Quét ĐỆ QUY: bản cũ chỉ nhìn `name`/`description`/`summary` và attributes
    kiểu chuỗi, nên bỏ sót attributes lồng và toàn bộ `itineraries`. Đo
    2026-08-05 trên data.json thật: 8 occurrence trong `attributes.key_facts[]`
    và 1 trong `itineraries` chưa từng được cổng nào nhìn thấy.
    """
    path = root / DATA_REL
    if not path.exists():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    for entity in data.get("entities", []):
        yield from _entity_occurrences(entity)
    for itinerary in data.get("itineraries", []):
        yield from _itinerary_occurrences(itinerary)


class TinhCuCheck:
    name, level, rule = "tinh_cu", "hard-ratchet", "R10.7"

    def __init__(self, root: Path | None = None):
        self._root = root

    @property
    def root(self) -> Path:
        return self._root or repo_root()

    def _data_violations(self, norm: list[str] | None) -> list[dict]:
        """1) data.json — theo whitelist per-occurrence, có ĐẾM số lần."""
        violations: list[dict] = []
        if norm is None or DATA_REL in norm:
            budget = dict(_load_whitelist(self.root))
            for eid, field in _data_occurrences(self.root):
                key = (eid, field)
                if budget.get(key, 0) > 0:
                    budget[key] -= 1  # tiêu một suất đã duyệt
                    continue
                extra = " (vượt số lần đã duyệt)" if key in budget else ""
                violations.append({"file": DATA_REL, "line": 0, "rule": self.rule,
                                   "msg": f"{eid}:{field} — tỉnh cũ ngoài whitelist{extra} (§1.6)"})
        return violations

    def _fe_files(self, norm: list[str] | None) -> list[str]:
        return (
            iter_text_files(self.root, ["*.vue", "*.ts"], ["web-nuxt"], ["web-nuxt/node_modules"])
            if norm is None
            else [f for f in norm if f.startswith("web-nuxt/") and (f.endswith(".vue") or f.endswith(".ts"))]
        )

    def _fe_violations(self, norm: list[str] | None) -> list[dict]:
        """2) FE code — mọi match là vi phạm."""
        violations = []
        for rel in self._fe_files(norm):
            p = self.root / rel
            if not p.exists():
                continue
            for i, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if PAT.search(line):
                    violations.append({"file": rel, "line": i, "rule": self.rule,
                                       "msg": "tỉnh cũ trong FE code — dùng khung tỉnh-mới (§1.6)"})
        return violations

    def run(self, files: list[str] | None = None) -> dict:
        norm = [f.replace("\\", "/") for f in files] if files is not None else None
        violations = self._data_violations(norm) + self._fe_violations(norm)
        return {"check": self.name, "level": self.level, "rule": self.rule,
                "count": len(violations), "violations": violations}


CHECKS = [TinhCuCheck()]
