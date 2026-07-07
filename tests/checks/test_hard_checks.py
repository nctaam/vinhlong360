# -*- coding: utf-8 -*-
"""Test 4 module HARD (SP01 T3) — fixture vi-phạm bị bắt / sạch pass / neg-context pass."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from checks.check_api_contract import ApiContractCheck  # noqa: E402
from checks.check_banned_claims import build_checks as banned_checks  # noqa: E402
from checks.check_data_schema import DataSchemaCheck  # noqa: E402
from checks.check_secrets import SecretsCheck  # noqa: E402


def _mk(tmp_path: Path, rel: str, text: str) -> Path:
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


# ---------- secrets ----------

def test_secrets_catches_hardcoded_key(tmp_path):
    _mk(tmp_path, "agent/x.py", 'API_KEY = "sk-abcdefghijklmnop1234"\n')
    r = SecretsCheck(root=tmp_path).run()
    assert r["count"] == 1 and r["level"] == "hard"


def test_secrets_env_staged_blocked(tmp_path):
    r = SecretsCheck(root=tmp_path).run(files=[".env"])
    assert r["count"] == 1 and ".env" in r["violations"][0]["file"]


def test_secrets_allows_env_read_and_example(tmp_path):
    _mk(tmp_path, "agent/x.py", 'API_KEY = os.environ.get("IMAGE_API_KEY", "")\n')
    _mk(tmp_path, ".env.example", 'ADMIN_API_KEY="your_key_here_example_1234567890"\n')
    assert SecretsCheck(root=tmp_path).run()["count"] == 0


# ---------- banned claims ----------

def test_banned_claims_catches_verify_claim_and_image_source(tmp_path):
    _mk(tmp_path, "web-nuxt/pages/x.vue", "<p>1.532 điểm đến đã xác minh</p>\n")
    _mk(tmp_path, "docs/guide.md", "Lấy ảnh từ Pexels cho đẹp\n")
    _mk(tmp_path, "web-nuxt/composables/useConstants.ts", "export const TYPE_META = {\n}\n")
    results = [c.run() for c in banned_checks(root=tmp_path)]
    by_rule = {r["rule"]: r["count"] for r in results}
    assert by_rule["R40.3"] == 1 and by_rule["R10.6"] == 1


def test_banned_claims_neg_context_and_archive_pass(tmp_path):
    _mk(tmp_path, "docs/a.md", "CẤM claim đã xác minh khi verifiedAt = 0\n")
    _mk(tmp_path, "docs/archive/old.md", "ảnh Wikimedia rất đẹp\n")
    results = [c.run() for c in banned_checks(root=tmp_path)]
    assert all(r["count"] == 0 for r in results)


def test_banned_tailwind_in_web_nuxt(tmp_path):
    _mk(tmp_path, "web-nuxt/package.json", '{"dependencies": {"tailwindcss": "^3"}}\n')
    results = {r["rule"]: r["count"] for r in (c.run() for c in banned_checks(root=tmp_path))}
    assert results["R30.1"] == 1


# ---------- data schema ----------

TYPE_META_TS = """export const TYPE_META = {
  dish: { emoji: 'x', icon: 'bowl', label: 'Món', cat: 'food' },
  place: { emoji: 'x', icon: 'pin', label: 'Nơi', cat: 'place' },
}
"""


def _mk_data(tmp_path, entities):
    _mk(tmp_path, "web-nuxt/composables/useConstants.ts", TYPE_META_TS)
    _mk(tmp_path, "web/data.json", json.dumps({"entities": entities, "relationships": [], "itineraries": []}, ensure_ascii=False))


def test_data_schema_pass_clean(tmp_path):
    _mk_data(tmp_path, [{"id": "a", "type": "dish", "name": "A", "summary": "s", "coordinates": {"lat": 10.0, "lng": 106.0}}])
    assert DataSchemaCheck(root=tmp_path).run()["count"] == 0


def test_data_schema_catches_dup_badtype_missing_bbox(tmp_path):
    _mk_data(tmp_path, [
        {"id": "a", "type": "dish", "name": "A", "summary": "s"},
        {"id": "a", "type": "hotel", "name": "", "summary": "s", "coordinates": {"lat": 21.0, "lng": 105.8}},
    ])
    r = DataSchemaCheck(root=tmp_path).run()
    msgs = " | ".join(v["msg"] for v in r["violations"])
    assert "id trùng" in msgs and "ngoài enum" in msgs and "thiếu trường" in msgs and "ngoài bbox" in msgs


def test_data_schema_skips_when_not_staged(tmp_path):
    _mk_data(tmp_path, [{"id": "a", "type": "hotel", "name": "A", "summary": "s"}])
    assert DataSchemaCheck(root=tmp_path).run(files=["agent/x.py"])["count"] == 0


# ---------- R10.3b per-type required (SP2 T3) ----------

def test_typed_required_catches_missing_person_role(tmp_path):
    from checks.check_data_schema import DataTypedRequiredCheck

    _mk_data(tmp_path, [
        {"id": "p1", "type": "person", "name": "A", "summary": "s", "attributes": {}},
        {"id": "p2", "type": "person", "name": "B", "summary": "s", "attributes": {"role": "nghệ nhân"}},
        {"id": "d1", "type": "dish", "name": "C", "summary": "s", "attributes": {}},
    ])
    r = DataTypedRequiredCheck(root=tmp_path).run()
    assert r["level"] == "hard-ratchet" and r["rule"] == "R10.3b"
    assert r["count"] == 1 and "p1" in r["violations"][0]["msg"]


def test_typed_required_skips_when_not_staged(tmp_path):
    from checks.check_data_schema import DataTypedRequiredCheck

    _mk_data(tmp_path, [{"id": "p1", "type": "person", "name": "A", "summary": "s", "attributes": {}}])
    assert DataTypedRequiredCheck(root=tmp_path).run(files=["agent/x.py"])["count"] == 0


# ---------- R10.8 RICH-source (SP2 T3) ----------

RICH_TEXT = "chữ " * 140  # ≥130 từ → is_index_worthy


def test_rich_source_catches_rich_entity_without_source(tmp_path):
    from checks.check_data_schema import DataRichSourceCheck

    _mk_data(tmp_path, [
        {"id": "rich-0src", "type": "dish", "name": "A", "summary": "s", "description": RICH_TEXT, "source": []},
        {"id": "rich-ok", "type": "dish", "name": "B", "summary": "s", "description": RICH_TEXT,
         "source": [{"url": "https://example.org"}]},
        {"id": "thin-0src", "type": "dish", "name": "C", "summary": "s", "description": "ngắn", "source": []},
    ])
    r = DataRichSourceCheck(root=tmp_path).run()
    assert r["level"] == "hard-ratchet" and r["rule"] == "R10.8"
    assert r["count"] == 1 and "rich-0src" in r["violations"][0]["msg"]


def test_rich_source_skips_when_not_staged(tmp_path):
    from checks.check_data_schema import DataRichSourceCheck

    _mk_data(tmp_path, [{"id": "r", "type": "dish", "name": "A", "summary": "s",
                         "description": RICH_TEXT, "source": []}])
    assert DataRichSourceCheck(root=tmp_path).run(files=["agent/x.py"])["count"] == 0


# ---------- api contract ----------

def _git(root, *args):
    subprocess.run(["git", *args], cwd=str(root), check=True, capture_output=True)


def _mk_repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@t")
    _git(tmp_path, "config", "user.name", "t")
    _mk(tmp_path, "agent/server.py", "x = 1\n")
    _mk(tmp_path, "docs/api-contract.md", "# contract\n")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "init")
    return tmp_path


def test_api_contract_blocks_route_change_without_contract(tmp_path):
    repo = _mk_repo(tmp_path)
    _mk(repo, "agent/server.py", 'x = 1\n@router.get("/new")\ndef new(): ...\n')
    _git(repo, "add", "agent/server.py")
    r = ApiContractCheck(root=repo).run(files=["agent/server.py"])
    assert r["count"] == 1


def test_api_contract_passes_with_contract_staged(tmp_path):
    repo = _mk_repo(tmp_path)
    _mk(repo, "agent/server.py", 'x = 1\n@router.get("/new")\ndef new(): ...\n')
    _mk(repo, "docs/api-contract.md", "# contract\n/new\n")
    _git(repo, "add", "-A")
    r = ApiContractCheck(root=repo).run(files=["agent/server.py", "docs/api-contract.md"])
    assert r["count"] == 0


def test_api_contract_passes_non_route_change(tmp_path):
    repo = _mk_repo(tmp_path)
    _mk(repo, "agent/server.py", "x = 2\n")
    _git(repo, "add", "agent/server.py")
    assert ApiContractCheck(root=repo).run(files=["agent/server.py"])["count"] == 0
