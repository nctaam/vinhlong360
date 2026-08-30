# -*- coding: utf-8 -*-
"""R20.4 — coverage gate (SP3 Backend). Đọc coverage.json (sinh bởi
`pytest --cov=agent --cov-report=json`), so ngưỡng agent-total + core-4 module.

Gate KHÔNG chạy pytest (chậm/nặng) — chỉ đọc coverage.json có sẵn. Hook staged
được graceful-skip khi thiếu artifact; full/pre-merge gate fail-closed vì CI và
pre-merge phải sinh coverage.json trước khi gọi check.

Ngưỡng ratchet đọc từ docs/standards/coverage-thresholds.json (nâng dần, không tụt):
  {"agent": 60, "core": {"database.py": 80, "auth.py": 80, "social.py": 80, "server.py": 80}}
count = số ngưỡng CHƯA đạt (0 = pass). level soft-ratchet để nợ giảm dần theo đợt.
"""
from __future__ import annotations

import json
from pathlib import Path

from .common import repo_root

COV_JSON = "coverage.json"
THRESHOLDS = "docs/standards/coverage-thresholds.json"
CORE = ("database.py", "auth.py", "social.py", "server.py")


def _pct(files: dict, suffix: str) -> float | None:
    """% covered cho core-module theo basename CHÍNH XÁC (agent/server.py).
    Phải khớp đúng tên file, KHÔNG endswith lỏng — nếu không `mcp_server.py`
    (basename khác) sẽ che `server.py` và trả nhầm 0%.

    Key chứa '/' → khớp SUFFIX đường dẫn (2026-08-29, gỡ shim): repo nay có
    4 file cùng basename `api.py` (chat/community/identity/entities) — floor
    của community/identity phải ghi 'community/api.py' để không khớp mù."""
    for name, data in files.items():
        n = name.replace("\\", "/")
        if "/" in suffix:
            if n == suffix or n.endswith("/" + suffix):
                return (data.get("summary") or {}).get("percent_covered", 0.0)
        elif n.rsplit("/", 1)[-1] == suffix:
            return (data.get("summary") or {}).get("percent_covered", 0.0)
    return None


class CoverageCheck:
    name, level, rule = "coverage", "soft-ratchet", "R20.4"

    def __init__(self, root: Path | None = None):
        self._root = root

    @property
    def root(self) -> Path:
        return self._root or repo_root()

    def _load(self, rel: str) -> dict | None:
        p = self.root / rel
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def run(self, files: list[str] | None = None) -> dict:
        cov = self._load(COV_JSON)
        if cov is None:
            # GRACEFUL-SKIP, cùng khuôn với R30.7 (`check_bundle`): rule này chỉ
            # đo được ở nơi vừa chạy pytest có --cov. Ở `run_hard --all` nói
            # chung — hook pre-commit, job CI không sinh coverage — nó im lặng,
            # và bản NGHIÊM sống ở `main()` bên dưới, nơi CI gọi trực tiếp sau
            # khi đã chạy suite với PostgreSQL.
            #
            # Vì sao phải tách: ngưỡng identity 85 / community 90 CHỈ đạt được
            # khi có PG (đo 2026-08-30: không PG 46,2/29,2 · có PG 88,3/95,8).
            # Để cổng ở job SQLite là thực thi một phép đo không đầy đủ.
            return self._result([])
        thr = self._load(THRESHOLDS) or {"agent": 60, "core": {c: 80 for c in CORE}}
        cfiles = cov.get("files", {})
        violations = []
        agent_total = (cov.get("totals") or {}).get("percent_covered")
        if agent_total is not None and agent_total < thr.get("agent", 60):
            violations.append({"file": "agent/", "line": 0, "rule": self.rule,
                               "msg": f"agent coverage {agent_total:.1f}% < {thr.get('agent', 60)}%"})
        for mod, floor in (thr.get("core") or {}).items():
            pct = _pct(cfiles, mod)
            if pct is None:
                # FAIL-CLOSED. Bản cũ chỉ ghi vi phạm khi `pct is not None`, nên
                # một khoá sàn không khớp file nào sẽ BIẾN MẤT không một tiếng
                # động: count vẫn 0, cổng vẫn xanh, và module đó tụt về 0% cũng
                # không ai hay. Đổi tên file / dời module là làm được điều đó —
                # đúng chuyện suýt xảy ra với `itinerary_gen.py`, nay đã dời sang
                # `agent/itineraries/` và còn khớp CHỈ nhờ nhánh so basename.
                # Sàn không đo được là một sàn hỏng, không phải một sàn đã đạt.
                violations.append({"file": f"agent/{mod}", "line": 0, "rule": self.rule,
                                   "msg": (f"{mod}: sàn {floor}% khai trong "
                                           f"{THRESHOLDS} nhưng KHÔNG khớp file nào "
                                           "trong coverage.json — module đã đổi tên/dời "
                                           "chỗ, hoặc suite không còn chạm tới nó. Sửa "
                                           "khoá cho khớp, đừng để sàn tự mất.")})
            elif pct < floor:
                violations.append({"file": f"agent/{mod}", "line": 0, "rule": self.rule,
                                   "msg": f"{mod} coverage {pct:.1f}% < {floor}%"})
        return self._result(violations)

    def _result(self, violations: list) -> dict:
        return {"check": self.name, "level": self.level, "rule": self.rule,
                "count": len(violations), "violations": violations}


def main() -> int:
    """Chạy riêng R20.4 ở nơi phép đo HỢP LỆ — job CI có PostgreSQL.

    `run_hard.py --all` chạy ở job `test`, nơi suite chạy trên SQLite. Hai module
    lớn nhất chỉ đo được 46,2% và 29,2% ở đó, so với 88,3% và 95,8% khi có PG —
    tức ngưỡng 85/90 KHÔNG THỂ đạt, và cổng sẽ chặn mọi lượt push vì một phép đo
    thiếu, không phải vì độ phủ tụt.

    Chủ dự án chốt 2026-08-30: chuyển cổng sang job `test-pg`. Entry này để job đó
    gọi trực tiếp, đúng cách `check_bundle` đã làm cho R30.7:
        PYTHONPATH=scripts python3 -m checks.check_coverage

    Khác `run()`: ở đây THIẾU coverage.json là LỖI, không phải bỏ qua. Gọi entry
    này nghĩa là bạn vừa chạy pytest có --cov; không có file tức là bước đó hỏng.
    """
    check = CHECKS[0]
    if not (check.root / COV_JSON).exists():
        print(f"✖ R20.4: không thấy {COV_JSON} — phải chạy SAU pytest với --cov-report=json")
        return 2
    result = check.run(None)
    for violation in result["violations"]:
        print(f"✖ R20.4 {violation['file']}: {violation['msg']}")
    if result["count"]:
        print(f"Độ phủ dưới sàn: {result['count']} vi phạm")
        return 1
    print("✓ R20.4 coverage: đạt")
    return 0


CHECKS = [CoverageCheck()]


if __name__ == "__main__":
    raise SystemExit(main())
