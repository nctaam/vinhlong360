# -*- coding: utf-8 -*-
"""Test scripts/fix_tinh_moi.py — apply/extract an toàn (campaign tỉnh-mới T2). B3."""
import json
import io
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import fix_tinh_moi as fx  # noqa: E402

ENT = {
    "id": "e1",
    "type": "dish",
    "name": "Bánh test",
    "summary": "Đặc sản của tỉnh Bến Tre.",
    "description": "Mô tả dài.",
    "attributes": {"address": "Xã A, huyện B, tỉnh Trà Vinh"},
}
PATCH_OK = {"entity_id": "e1", "field": "summary", "old_value": "Đặc sản của tỉnh Bến Tre.", "new_value": "Đặc sản vùng Bến Tre."}
PATCH_ATTR = {"entity_id": "e1", "field": "attr:address", "old_value": "Xã A, huyện B, tỉnh Trà Vinh", "new_value": "Xã A, huyện B, tỉnh Vĩnh Long"}
PATCH_STALE = {"entity_id": "e1", "field": "summary", "old_value": "GIÁ TRỊ KHÔNG KHỚP", "new_value": "x"}


def _mk_json(tmp_path):
    p = tmp_path / "d.json"
    io.open(p, "w", encoding="utf-8").write(json.dumps({"entities": [json.loads(json.dumps(ENT))], "relationships": [], "itineraries": []}, ensure_ascii=False))
    return str(p)


def test_apply_json_matches_and_skips(tmp_path):
    p = _mk_json(tmp_path)
    r = fx.apply_json(p, [PATCH_OK, PATCH_ATTR, PATCH_STALE], dry_run=False)
    assert r["applied"] == 2 and r["skipped"] == 1
    data = json.load(io.open(p, encoding="utf-8"))
    e = data["entities"][0]
    assert e["summary"] == "Đặc sản vùng Bến Tre."
    assert e["attributes"]["address"].endswith("tỉnh Vĩnh Long")
    assert e["updatedAt"] == fx.TODAY


def test_apply_json_dry_run_writes_nothing(tmp_path):
    p = _mk_json(tmp_path)
    before = io.open(p, encoding="utf-8").read()
    r = fx.apply_json(p, [PATCH_OK], dry_run=True)
    assert r["applied"] == 1
    assert io.open(p, encoding="utf-8").read() == before


def test_apply_sqlite(tmp_path):
    dbp = str(tmp_path / "t.db")
    conn = sqlite3.connect(dbp)
    conn.execute("CREATE TABLE entities (id TEXT PRIMARY KEY, name TEXT, description TEXT, summary TEXT, attributes TEXT, updatedAt TEXT)")
    conn.execute("INSERT INTO entities VALUES (?,?,?,?,?,?)", ("e1", ENT["name"], ENT["description"], ENT["summary"], json.dumps(ENT["attributes"], ensure_ascii=False), "2026-01-01"))
    conn.commit(); conn.close()
    r = fx.apply_sqlite(dbp, [PATCH_OK, PATCH_ATTR, PATCH_STALE], dry_run=False)
    assert r["applied"] == 2 and r["skipped"] == 1
    conn = sqlite3.connect(dbp)
    row = conn.execute("SELECT summary, attributes, updatedAt FROM entities WHERE id='e1'").fetchone()
    conn.close()
    assert row[0] == "Đặc sản vùng Bến Tre."
    assert json.loads(row[1])["address"].endswith("tỉnh Vĩnh Long")
    assert row[2] == fx.TODAY


def test_extract_classifies(tmp_path):
    src = tmp_path / "in.json"
    io.open(src, "w", encoding="utf-8").write(json.dumps([
        dict(ENT, attributes=json.dumps(ENT["attributes"], ensure_ascii=False)),  # attributes dạng chuỗi như dump PG
        {"id": "e2", "name": "Bảo tàng tỉnh Bến Tre", "description": "x", "summary": "y", "attributes": "{}"},
    ], ensure_ascii=False))
    out = tmp_path / "occ.json"

    class A:  # giả args
        infile = str(src); pass
    A.out = str(out)
    fx.cmd_extract(A)
    occ = json.load(io.open(out, encoding="utf-8"))
    cats = {(r["entity_id"], r["field"]): r["category"] for r in occ["records"]}
    assert cats[("e1", "summary")] == "cat23-context"
    assert cats[("e1", "attr:address")] == "cat1-address"
    assert cats[("e2", "name")] == "cat4-ten-rieng"
