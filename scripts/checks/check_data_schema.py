# -*- coding: utf-8 -*-
"""R10.schema (R10.1-R10.4) — schema gate cho web/data.json (tầng HARD).

Chỉ chạy khi data.json nằm trong tập file (staged) hoặc chạy --all.
Enum type đọc THẬT từ TYPE_META (web-nuxt/composables/useConstants.ts) — 1 nguồn sự thật.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .common import repo_root

DATA_REL = "web/data.json"
BBOX = {"lat": (9.0, 10.6), "lng": (105.6, 107.1)}  # tỉnh Vĩnh Long mới (siết từ validator cũ)
REQUIRED = ["id", "type", "name", "summary"]


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
            c = e.get("coordinates")
            if isinstance(c, dict) and c.get("lat") is not None:
                lat, lng = c.get("lat"), c.get("lng")
                if not (BBOX["lat"][0] <= lat <= BBOX["lat"][1] and BBOX["lng"][0] <= lng <= BBOX["lng"][1]):
                    violations.append({"file": DATA_REL, "line": 0, "rule": self.rule,
                                       "msg": f"{eid}: coords ({lat},{lng}) ngoài bbox tỉnh"})
        return self._result(violations)

    def _result(self, violations: list) -> dict:
        return {"check": self.name, "level": self.level, "rule": self.rule,
                "count": len(violations), "violations": violations}


CHECKS = [DataSchemaCheck()]
