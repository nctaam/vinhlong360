# -*- coding: utf-8 -*-
"""R20.5 phải kiểm NỘI DUNG hợp đồng API, không chỉ kiểm file có được staged.

Cổng cũ chỉ hỏi "docs/api-contract.md có nằm trong danh sách file staged không".
Stage một sửa đổi vô nghĩa trong file đó là qua cổng, nên hợp đồng vẫn trôi dạt
khỏi code — đúng lớp phòng thủ đáng lẽ chặn được vụ /api/me/activity bị khai báo
hai lần với hai payload khác nhau.
"""
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from checks.check_api_contract import ApiContractCheck  # noqa: E402


def _git(repo: Path, *args):
    return subprocess.run(["git", *args], cwd=str(repo), capture_output=True,
                          encoding="utf-8", errors="replace")


@pytest.fixture
def repo(tmp_path):
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@t.t")
    _git(tmp_path, "config", "user.name", "t")
    (tmp_path / "agent").mkdir()
    (tmp_path / "docs").mkdir()
    (tmp_path / "agent" / "public_api.py").write_text(
        '@router.get("/existing")\nasync def existing():\n    return {}\n', encoding="utf-8")
    (tmp_path / "docs" / "api-contract.md").write_text(
        "| GET | `/api/existing` | mô tả |\n", encoding="utf-8")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "base")
    return tmp_path


def _add_route(repo: Path, path: str):
    f = repo / "agent" / "public_api.py"
    f.write_text(f.read_text(encoding="utf-8") + f'\n@router.get("{path}")\nasync def added():\n    return {{}}\n',
                 encoding="utf-8")


def _run(repo: Path, files):
    return ApiContractCheck(root=repo).run(files)


def test_blocks_new_route_when_contract_untouched(repo):
    _add_route(repo, "/brand-new")
    _git(repo, "add", "agent/public_api.py")

    result = _run(repo, ["agent/public_api.py"])

    assert result["count"] == 1


def test_blocks_new_route_when_contract_staged_but_does_not_document_it(repo):
    """Đây là lỗ hổng thật: sửa vu vơ file hợp đồng là qua cổng."""
    _add_route(repo, "/brand-new")
    contract = repo / "docs" / "api-contract.md"
    contract.write_text(contract.read_text(encoding="utf-8") + "\nGhi chú không liên quan.\n", encoding="utf-8")
    _git(repo, "add", "-A")

    result = _run(repo, ["agent/public_api.py", "docs/api-contract.md"])

    assert result["count"] == 1, "hợp đồng được staged nhưng không hề mô tả route mới"
    assert "brand-new" in result["violations"][0]["msg"]


def test_passes_when_contract_actually_documents_the_new_route(repo):
    _add_route(repo, "/brand-new")
    contract = repo / "docs" / "api-contract.md"
    contract.write_text(contract.read_text(encoding="utf-8") + "| GET | `/api/brand-new` | mô tả |\n",
                        encoding="utf-8")
    _git(repo, "add", "-A")

    result = _run(repo, ["agent/public_api.py", "docs/api-contract.md"])

    assert result["count"] == 0


def test_removed_route_must_disappear_from_the_contract(repo):
    f = repo / "agent" / "public_api.py"
    f.write_text("", encoding="utf-8")
    _git(repo, "add", "-A")

    result = _run(repo, ["agent/public_api.py", "docs/api-contract.md"])

    assert result["count"] == 1, "route bị xoá nhưng hợp đồng vẫn còn mô tả nó"


def test_all_mode_reports_contract_entries_for_routes_that_no_longer_exist(repo):
    contract = repo / "docs" / "api-contract.md"
    contract.write_text(contract.read_text(encoding="utf-8") + "| GET | `/api/ghost-route` | đã bị xoá |\n",
                        encoding="utf-8")

    result = _run(repo, None)

    assert result["count"] >= 1, "--all phải phát hiện hợp đồng mô tả route không tồn tại"
    assert any("ghost-route" in v["msg"] for v in result["violations"])
