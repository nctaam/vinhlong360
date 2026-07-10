# -*- coding: utf-8 -*-
"""R10.schema (R10.1-R10.4) — schema gate cho web/data.json (tầng HARD)
+ R10.3b per-type required + R10.8 RICH-source (tầng HARD-RATCHET, SP2 T3).

Chỉ chạy khi data.json nằm trong tập file (staged) hoặc chạy --all.
Enum type đọc THẬT từ TYPE_META (web-nuxt/composables/useConstants.ts);
per-type schema tái dùng agent/entity_schemas.py; RICH tái dùng agent/seo.py
— 1 nguồn sự thật, không chế chuẩn thứ hai.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from .common import repo_root

DATA_REL = "web/data.json"
BBOX = {"lat": (9.0, 10.6), "lng": (105.6, 107.1)}  # tỉnh Vĩnh Long mới (siết từ validator cũ)
REQUIRED = ["id", "type", "name", "summary"]

# agent/ của repo THẬT (không phụ thuộc root fixture — validate/is_index_worthy là logic thuần)
_AGENT_DIR = str(Path(__file__).resolve().parents[2] / "agent")


def load_type_enum(root: Path) -> set[str]:
    src = (root / "web-nuxt" / "composables" / "useConstants.ts").read_text(encoding="utf-8")
    m = re.search(r"TYPE_META[^=]*=\s*\{(.*?)\n\}", src, re.S)
    if not m:
        raise RuntimeError("Không parse được TYPE_META từ useConstants.ts")
    return set(re.findall(r"^\s*'?\"?([a-z_]+)'?\"?:\s*\{", m.group(1), re.M))


class DataSchemaCheck:
    name, level, rule = "data_schema", "hard", "R10.schema"

    def __init__(self, root: Path | None = None):
        self._root = root

    @property
    def root(self) -> Path:
        return self._root or repo_root()

    def run(self, files: list[str] | None = None) -> dict:
        if files is not None and DATA_REL not in [f.replace("\\", "/") for f in files]:
            return {"check": self.name, "level": self.level, "rule": self.rule, "count": 0, "violations": []}
        violations = []
        path = self.root / DATA_REL
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            return self._result([{"file": DATA_REL, "line": 0, "rule": self.rule, "msg": f"parse fail: {e}"}])
        enum = load_type_enum(self.root)
        seen: set[str] = set()
        for e in data.get("entities", []):
            self._check_entity(e, enum, seen, violations)
        return self._result(violations)

    def _check_entity(self, e: dict, enum: set, seen: set, violations: list) -> None:
        eid = e.get("id") or "<no-id>"
        if eid in seen:
            violations.append({"file": DATA_REL, "line": 0, "rule": self.rule, "msg": f"id trùng: {eid}"})
        seen.add(eid)
        if e.get("type") not in enum:
            violations.append({"file": DATA_REL, "line": 0, "rule": self.rule,
                               "msg": f"{eid}: type '{e.get('type')}' ngoài enum {len(enum)} loại"})
        for f in REQUIRED:
            if not e.get(f):
                violations.append({"file": DATA_REL, "line": 0, "rule": self.rule,
                                   "msg": f"{eid}: thiếu trường bắt buộc '{f}'"})
        self._check_coords(e, eid, violations)

    def _check_coords(self, e: dict, eid: str, violations: list) -> None:
        c = e.get("coordinates")
        if isinstance(c, dict) and c.get("lat") is not None:
            lat, lng = c.get("lat"), c.get("lng")
            if not (BBOX["lat"][0] <= lat <= BBOX["lat"][1] and BBOX["lng"][0] <= lng <= BBOX["lng"][1]):
                violations.append({"file": DATA_REL, "line": 0, "rule": self.rule,
                                   "msg": f"{eid}: coords ({lat},{lng}) ngoài bbox tỉnh"})

    def _result(self, violations: list) -> dict:
        return {"check": self.name, "level": self.level, "rule": self.rule,
                "count": len(violations), "violations": violations}


class _DataJsonCheck:
    """Nền chung cho các gate trên web/data.json: skip khi không staged, parse 1 lần."""

    name = level = rule = ""  # lớp con định nghĩa

    def __init__(self, root: Path | None = None):
        self._root = root

    @property
    def root(self) -> Path:
        return self._root or repo_root()

    def run(self, files: list[str] | None = None) -> dict:
        if files is not None and DATA_REL not in [f.replace("\\", "/") for f in files]:
            return self._result([])
        try:
            data = json.loads((self.root / DATA_REL).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            return self._result([{"file": DATA_REL, "line": 0, "rule": self.rule, "msg": f"parse fail: {e}"}])
        return self._result(self.check_entities(data.get("entities", [])))

    def check_entities(self, entities: list) -> list:  # pragma: no cover — lớp con
        raise NotImplementedError

    def _result(self, violations: list) -> dict:
        return {"check": self.name, "level": self.level, "rule": self.rule,
                "count": len(violations), "violations": violations}


class DataTypedRequiredCheck(_DataJsonCheck):
    """R10.3b — trường bắt buộc PER-TYPE (registry agent/entity_schemas.py).

    Hard-ratchet: baseline = nợ đo lúc bật; entity mới/sửa không được thêm nợ.
    """

    name, level, rule = "data_typed_required", "hard-ratchet", "R10.3b"

    def check_entities(self, entities: list) -> list:
        if _AGENT_DIR not in sys.path:
            sys.path.insert(0, _AGENT_DIR)
        from entity_schemas import validate_attributes  # lazy — chỉ khi data.json trong tập file

        violations = []
        for e in entities:
            _, warns = validate_attributes(e.get("type") or "", e.get("attributes") or {})
            for w in warns:
                if "bắt buộc" in w:
                    violations.append({"file": DATA_REL, "line": 0, "rule": self.rule,
                                       "msg": f"{e.get('id') or '<no-id>'}: {w}"})
        return violations


class DataRichSourceCheck(_DataJsonCheck):
    """R10.8 — entity RICH (index-worthy theo agent/seo.py) phải có nguồn.

    Hard-ratchet baseline 0: thành quả 0/405 RICH thiếu nguồn không được thụt lùi.
    """

    name, level, rule = "data_rich_source", "hard-ratchet", "R10.8"

    def check_entities(self, entities: list) -> list:
        if _AGENT_DIR not in sys.path:
            sys.path.insert(0, _AGENT_DIR)
        from seo import is_index_worthy  # lazy — import seo ~1s, chỉ khi data.json trong tập file

        violations = []
        for e in entities:
            if not is_index_worthy(e):
                continue
            s = e.get("source")
            has = bool(s) if isinstance(s, list) else bool(str(s or "").strip())
            if not has:
                violations.append({"file": DATA_REL, "line": 0, "rule": self.rule,
                                   "msg": f"{e.get('id') or '<no-id>'}: RICH nhưng thiếu source"})
        return violations


CHECKS = [DataSchemaCheck(), DataTypedRequiredCheck(), DataRichSourceCheck()]
