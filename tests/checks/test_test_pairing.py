from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from checks.check_test_pairing import TestPairingCheck  # noqa: E402


BOM = "﻿"


def _write(root: Path, relative_path: str, content: str = "def test_placeholder():\n    pass\n") -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_bom_test_file_still_pairs_via_ast_import(tmp_path: Path) -> None:
    """BOM không được làm rơi file khỏi tập ứng viên.

    Tên file KHÔNG chứa 'search' → chỉ ghép cặp được nếu AST thực sự parse thành công,
    nên test này chứng minh BOM đã bị bóc chứ không chỉ chứng minh 'không crash'.
    """
    _write(tmp_path, "tests/test_query_contract.py", f"{BOM}from agent import search\n")

    result = TestPairingCheck(root=tmp_path).run(
        files=["agent/search.py", "tests/test_query_contract.py"]
    )

    assert result["count"] == 0, "file test có BOM bị bỏ qua âm thầm → R20.7 không được thực thi"


def test_bom_test_file_is_written_with_a_real_bom(tmp_path: Path) -> None:
    """Chốt chặn: nếu helper vô tình ghi mất BOM thì test trên thành vô nghĩa."""
    _write(tmp_path, "tests/test_query_contract.py", f"{BOM}from agent import search\n")

    assert (tmp_path / "tests/test_query_contract.py").read_bytes().startswith(b"\xef\xbb\xbf")


def test_bom_test_file_still_pairs_via_filename(tmp_path: Path) -> None:
    _write(tmp_path, "tests/test_server.py", f"{BOM}def test_placeholder():\n    pass\n")

    result = TestPairingCheck(root=tmp_path).run(
        files=["agent/server.py", "tests/test_server.py"]
    )

    assert result["count"] == 0


def test_bom_test_file_is_not_reported_as_unparseable(tmp_path: Path) -> None:
    _write(tmp_path, "tests/test_server.py", f"{BOM}def test_placeholder():\n    pass\n")

    result = TestPairingCheck(root=tmp_path).run(files=["tests/test_server.py"])

    assert result["violations"] == []


def test_filename_token_pairs_module_and_supports_windows_separators(tmp_path: Path) -> None:
    _write(tmp_path, "tests/test_unit_server_api.py")

    result = TestPairingCheck(root=tmp_path).run(
        files=[r"agent\server.py", r"tests\test_unit_server_api.py"]
    )

    assert result["count"] == 0


@pytest.mark.parametrize(
    "statement",
    [
        "import search",
        "import agent.search",
        "from search import run",
        "from agent.search import run",
        "from agent import search",
    ],
)
def test_direct_import_pairs_module(tmp_path: Path, statement: str) -> None:
    _write(tmp_path, "tests/test_query_contract.py", f"{statement}\n")

    result = TestPairingCheck(root=tmp_path).run(
        files=["agent/search.py", "tests/test_query_contract.py"]
    )

    assert result["count"] == 0


@pytest.mark.parametrize(
    "candidate",
    [
        "tests/test_seo.py",
        "tests/server.py",
        "tests/test_server.ts",
        "docs/test_server.py",
    ],
)
def test_unrelated_or_non_test_candidate_does_not_pair(tmp_path: Path, candidate: str) -> None:
    _write(tmp_path, candidate)

    result = TestPairingCheck(root=tmp_path).run(files=["agent/server.py", candidate])

    assert result["count"] == 1


def test_comments_and_strings_that_mention_import_do_not_pair(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "tests/test_unrelated.py",
        '# import server\nIMPORT_EXAMPLE = "from agent import server"\n',
    )

    result = TestPairingCheck(root=tmp_path).run(
        files=["agent/server.py", "tests/test_unrelated.py"]
    )

    assert result["count"] == 1


def test_every_staged_source_requires_its_own_pair(tmp_path: Path) -> None:
    _write(tmp_path, "tests/test_alpha.py")
    _write(tmp_path, "tests/test_contract.py", "from agent import beta\n")
    check = TestPairingCheck(root=tmp_path)

    missing = check.run(files=["agent/alpha.py", "agent/beta.py", "tests/test_alpha.py"])
    complete = check.run(
        files=[
            "agent/alpha.py",
            "agent/beta.py",
            "tests/test_alpha.py",
            "tests/test_contract.py",
        ]
    )

    assert missing["count"] == 1
    assert complete["count"] == 0


def test_syntax_error_candidate_is_reported_and_does_not_pair(tmp_path: Path) -> None:
    """File test hỏng cú pháp tự nó là defect — phải báo, không được nuốt im lặng."""
    _write(tmp_path, "tests/test_server.py", "def broken(:\n")

    result = TestPairingCheck(root=tmp_path).run(
        files=["agent/server.py", "tests/test_server.py"]
    )

    reported = {v["file"]: v["msg"] for v in result["violations"]}
    assert "tests/test_server.py" in reported  # không parse được → báo lên
    assert "không parse được" in reported["tests/test_server.py"]
    assert "agent/server.py" in reported  # và vẫn không tính là đã ghép cặp
    assert result["count"] == 2


def test_undecodable_candidate_is_reported(tmp_path: Path) -> None:
    path = tmp_path / "tests" / "test_server.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\xff\xfe def test_x(): pass\n")  # không phải UTF-8 hợp lệ

    result = TestPairingCheck(root=tmp_path).run(
        files=["agent/server.py", "tests/test_server.py"]
    )

    assert any(v["file"] == "tests/test_server.py" for v in result["violations"])


def test_missing_candidate_is_skipped_not_reported(tmp_path: Path) -> None:
    """OSError = 'không đọc được' (file đã xoá/đổi tên) — khác 'không phải Python hợp lệ'."""
    result = TestPairingCheck(root=tmp_path).run(
        files=["agent/server.py", "tests/test_server.py"]  # file test không tồn tại
    )

    assert [v["file"] for v in result["violations"]] == ["agent/server.py"]
    assert result["count"] == 1


def test_multiple_unpaired_sources_preserve_binary_violation_count(tmp_path: Path) -> None:
    result = TestPairingCheck(root=tmp_path).run(
        files=["agent/alpha.py", "agent/beta.py", "agent/gamma.py"]
    )

    assert result["count"] == 1
    assert len(result["violations"]) == 1


def test_test_only_change_is_ignored(tmp_path: Path) -> None:
    _write(tmp_path, "tests/test_server.py")

    result = TestPairingCheck(root=tmp_path).run(files=["tests/test_server.py"])

    assert result["count"] == 0
