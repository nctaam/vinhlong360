# -*- coding: utf-8 -*-
"""R50.4 — entity mỏng (summary+description < 200 ký tự) — SOFT report xu hướng (SP6 kéo)."""
from __future__ import annotations

import json
from pathlib import Path

from .common import repo_root

THRESHOLD = 200  # khớp sàn tối thiểu content-creation-guide (ngưỡng index-worthy cao hơn — SP6)
DATA_REL = "web/data.json"


class ThinContentCheck:
    name, level, rule = "thin_content", "soft", "R50.4"

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
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            for e in data.get("entities", []):
                text = (e.get("summary") or "") + (e.get("description") or "")
                if len(text) < THRESHOLD:
                    violations.append({"file": DATA_REL, "line": 0, "rule": self.rule,
                                       "msg": f"{e.get('id')}: {len(text)} ký tự < {THRESHOLD}"})
        return {"check": self.name, "level": self.level, "rule": self.rule,
                "count": len(violations), "violations": violations}


CHECKS = [ThinContentCheck()]
