"""Focused contracts for the shared JSONL report writer."""

import inspect
import json
import subprocess
import sys
from pathlib import Path

import jsonl_store
import public_api
from community import api as community_api


def test_append_jsonl_writes_utf8_and_uses_rotation_policy(tmp_path, monkeypatch):
    path = tmp_path / "reports.jsonl"
    monkeypatch.setattr(jsonl_store, "JSONL_MAX_LINES", 2)

    jsonl_store.append_jsonl(path, {"detail": "Thông tin sai", "status": "open"})
    jsonl_store.append_jsonl(path, {"detail": "Dòng thứ hai"})
    jsonl_store.append_jsonl(path, {"detail": "Dòng thứ ba"})

    retained = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert [row["detail"] for row in retained] == ["Dòng thứ hai", "Dòng thứ ba"]
    archives = list(tmp_path.glob("reports.*.jsonl"))
    assert len(archives) == 1
    assert "Thông tin sai" in archives[0].read_text(encoding="utf-8")
    assert [json.loads(line)["detail"] for line in archives[0].read_text(encoding="utf-8").splitlines()] == [
        "Thông tin sai",
    ]


def test_report_handlers_delegate_to_the_shared_leaf_writer():
    assert public_api._append_jsonl is jsonl_store.append_jsonl
    assert community_api._append_jsonl is jsonl_store.append_jsonl

    for handler in (
        public_api.submit_report,
        public_api.report_stale_field,
        community_api.report_comment,
    ):
        source = inspect.getsource(handler)
        assert "_append_jsonl" in source
        assert "def _write" not in source
        assert "_maybe_rotate_jsonl(" not in source


def test_public_and_community_import_orders_share_one_jsonl_module():
    script = r'''
import sys
sys.path.insert(0, sys.argv[1])
__import__(sys.argv[2])
__import__(sys.argv[3])
import jsonl_store
import public_api
from community import api as community_api
assert public_api._append_jsonl is jsonl_store.append_jsonl
assert community_api._append_jsonl is jsonl_store.append_jsonl
assert public_api._jsonl_lock is jsonl_store.jsonl_lock
assert len([name for name in sys.modules if name.rsplit('.', 1)[-1] == 'jsonl_store']) == 1
'''
    agent_dir = str(Path(__file__).resolve().parents[1])
    for first, second in (("public_api", "community.api"), ("community.api", "public_api")):
        result = subprocess.run(
            [sys.executable, "-c", script, agent_dir, first, second],
            cwd=agent_dir,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr or result.stdout
