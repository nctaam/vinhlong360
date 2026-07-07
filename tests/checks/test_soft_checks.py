# -*- coding: utf-8 -*-
"""Test 4 module SOFT (SP01 T5)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from checks.check_complexity import BareExceptCheck, ComplexityCheck  # noqa: E402
from checks.check_content_voice import build_checks as voice_checks  # noqa: E402
from checks.check_test_pairing import TestPairingCheck  # noqa: E402
from checks.check_thin_content import ThinContentCheck  # noqa: E402


def _mk(tmp_path: Path, rel: str, text: str) -> Path:
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def test_content_voice_fillers_and_out_of_province(tmp_path):
    _mk(tmp_path, "web-nuxt/pages/x.vue", "<p>thiên đường miền Tây, chợ nổi Cái Bè</p>\n")
    results = {r["rule"]: r["count"] for r in (c.run() for c in voice_checks(root=tmp_path))}
    assert results["R50.2"] == 2  # per-match: thiên đường + miền Tây
    assert results["R10.9"] == 1  # Cái Bè


def test_content_voice_scans_data_json_per_match(tmp_path):
    # data.json 1-dòng: đếm TỪNG match (2 filler = 2), không bị neg-context nuốt cả dòng
    _mk(tmp_path, "web/data.json", json.dumps({"entities": [{"summary": "must-see điểm đến lý tưởng, KHÔNG liên quan"}]}, ensure_ascii=False))
    results = {r["rule"]: r["count"] for r in (c.run() for c in voice_checks(root=tmp_path))}
    assert results["R50.2"] == 2


def test_content_voice_skips_source_titles(tmp_path):
    # SP6: filler trong tên bài NGUỒN (field source) là giọng của báo, KHÔNG tính;
    # nhưng filler trong summary/attributes (giọng biên tập) VẪN tính.
    _mk(tmp_path, "web/data.json", json.dumps({"entities": [{
        "id": "x", "summary": "Chợ nổi họp lúc tinh mơ",
        "attributes": {"best_time": "mùa nước nổi miền Tây", "coords_source": "OSM miền Tây"},
        "source": [{"title": "Về miền Tây thăm chợ nổi Cái Bè", "url": "https://x.vn/mien-tay"}],
    }]}, ensure_ascii=False))
    results = {r["rule"]: r["count"] for r in (c.run() for c in voice_checks(root=tmp_path))}
    assert results["R50.2"] == 1   # best_time đếm; source.title + coords_source KHÔNG
    assert results["R10.9"] == 0   # "Cái Bè" chỉ trong source.title → bỏ


def test_thin_content_counts_under_threshold(tmp_path):
    _mk(tmp_path, "web/data.json", json.dumps({"entities": [
        {"id": "a", "summary": "ngắn", "description": ""},
        {"id": "b", "summary": "x" * 250, "description": ""},
    ]}, ensure_ascii=False))
    r = ThinContentCheck(root=tmp_path).run()
    assert r["count"] == 1 and r["level"] == "soft"


def test_test_pairing_blocks_agent_without_tests():
    r = TestPairingCheck().run(files=["agent/server.py"])
    assert r["count"] == 1
    assert TestPairingCheck().run(files=["agent/server.py", "tests/test_x.py"])["count"] == 0
    assert TestPairingCheck().run(files=["docs/a.md"])["count"] == 0
    assert TestPairingCheck().run(files=None)["count"] == 0  # --all: không áp


def test_complexity_flags_deep_function(tmp_path):
    body = "\n".join(f"    if x > {i}: x += {i}" for i in range(15))
    _mk(tmp_path, "agent/deep.py", f"def f(x):\n{body}\n    return x\n")
    r = ComplexityCheck(root=tmp_path).run()
    assert r["count"] == 1 and "f()" in r["violations"][0]["msg"]


def test_bare_except_flagged_typed_ok(tmp_path):
    _mk(tmp_path, "agent/e.py", "try:\n    x = 1\nexcept:\n    pass\ntry:\n    y = 1\nexcept ValueError:\n    pass\n")
    r = BareExceptCheck(root=tmp_path).run()
    assert r["count"] == 1
