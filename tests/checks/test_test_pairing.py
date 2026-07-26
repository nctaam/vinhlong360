from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from checks.check_test_pairing import TestPairingCheck  # noqa: E402


def _write(root: Path, relative_path: str, content: str = "def test_placeholder():\n    pass\n") -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


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


def test_syntax_error_candidate_does_not_crash_or_pair(tmp_path: Path) -> None:
    _write(tmp_path, "tests/test_server.py", "def broken(:\n")

    result = TestPairingCheck(root=tmp_path).run(
        files=["agent/server.py", "tests/test_server.py"]
    )

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
