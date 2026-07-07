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


def _load_whitelist(root: Path) -> set[tuple[str, str]]:
    p = root / WHITELIST_REL
    if not p.exists():
        return set()
    pairs = set()
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) == 2:
            pairs.add((parts[0], parts[1]))
    return pairs


def _data_occurrences(root: Path):
    """(entity_id, field) cho mọi occurrence trong data.json."""
    path = root / DATA_REL
    if not path.exists():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    for e in data.get("entities", []):
        for f in ("name", "description", "summary"):
            v = e.get(f)
            if isinstance(v, str):
                for _ in PAT.finditer(v):
                    yield e["id"], f
        for k, v in (e.get("attributes") or {}).items():
            if isinstance(v, str):
                for _ in PAT.finditer(v):
                    yield e["id"], f"attr:{k}"


class TinhCuCheck:
    name, level, rule = "tinh_cu", "hard-ratchet", "R10.7"

    def __init__(self, root: Path | None = None):
        self._root = root

    @property
    def root(self) -> Path:
        return self._root or repo_root()

    def run(self, files: list[str] | None = None) -> dict:
        violations = []
        norm = [f.replace("\\", "/") for f in files] if files is not None else None
        # 1) data.json — theo whitelist per-occurrence
        if norm is None or DATA_REL in norm:
            wl = _load_whitelist(self.root)
            for eid, field in _data_occurrences(self.root):
                if (eid, field) not in wl:
                    violations.append({"file": DATA_REL, "line": 0, "rule": self.rule,
                                       "msg": f"{eid}:{field} — tỉnh cũ ngoài whitelist (§1.6)"})
        # 2) FE code — mọi match là vi phạm
        fe_files = (
            iter_text_files(self.root, ["*.vue", "*.ts"], ["web-nuxt"], ["web-nuxt/node_modules"])
            if norm is None
            else [f for f in norm if f.startswith("web-nuxt/") and (f.endswith(".vue") or f.endswith(".ts"))]
        )
        for rel in fe_files:
            p = self.root / rel
            if not p.exists():
                continue
            for i, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if PAT.search(line):
                    violations.append({"file": rel, "line": i, "rule": self.rule,
                                       "msg": "tỉnh cũ trong FE code — dùng khung tỉnh-mới (§1.6)"})
        return {"check": self.name, "level": self.level, "rule": self.rule,
                "count": len(violations), "violations": violations}


CHECKS = [TinhCuCheck()]
