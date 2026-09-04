"""`.gitignore` phải thật sự che vật liệu khoá — đo bằng git, không đọc bằng mắt.

Vì sao cần test này: `.gitignore` từng chứa đúng một dòng `.key` (dòng 12). Một
pattern KHÔNG có dấu "/" là khớp **basename**, nên `.key` chỉ khớp file có tên
đúng bằng ".key" — nó KHÔNG che `*.key`. Hệ quả đo được ngày 2026-09-03:
`secrets/pilot-owner-signing.key` — đúng đường dẫn khoá ký của owner khai ở
`config/release-authority.json` — hoàn toàn KHÔNG được ignore. Nhìn file thì
tưởng đã che; chỉ `git check-ignore` mới nói thật.

Test hỏi chính git (`git check-ignore`), không tự diễn giải cú pháp gitignore.
`--no-index` để không cần tạo file thật, nên test không đụng đĩa và không tạo ra
đúng thứ nguy hiểm mà nó đang canh.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

# Đường dẫn PHẢI bị ignore. Gồm cả nested để bắt lỗi "pattern bị neo" (anchored),
# và đúng đường dẫn khoá owner trong config/release-authority.json.
MUST_BE_IGNORED = (
    ".key",
    "foo.key",
    "agent/foo.key",
    "config/foo.key",
    "artifacts/foo.key",
    "web-nuxt/deep/nest/foo.key",
    "secrets/pilot-owner-signing.key",
    "foo.pem",
    "agent/foo.pem",
    "foo.p12",
    "foo.pfx",
)

# Đường dẫn KHÔNG được ignore — chốt chặn để bản vá không quét quá tay và nuốt
# mất mã nguồn thật (ví dụ một pattern `*key*` cẩu thả sẽ ăn cả keyboard.ts).
MUST_NOT_BE_IGNORED = (
    "agent/config.py",
    "web-nuxt/utils/legalContent.ts",
    "docs/HANDOFF.md",
)


def _is_ignored(rel_path: str) -> bool:
    """Hỏi git xem đường dẫn có bị ignore không. Exit 0 = có, 1 = không."""
    result = subprocess.run(
        ["git", "check-ignore", "--no-index", "-q", "--", rel_path],
        cwd=ROOT,
        capture_output=True,
    )
    if result.returncode not in (0, 1):
        pytest.fail(
            f"git check-ignore lỗi bất thường cho {rel_path!r}: "
            f"rc={result.returncode} stderr={result.stderr.decode('utf-8', 'replace')}"
        )
    return result.returncode == 0


@pytest.mark.parametrize("rel_path", MUST_BE_IGNORED)
def test_secret_material_is_ignored(rel_path: str) -> None:
    assert _is_ignored(rel_path), (
        f"{rel_path!r} KHÔNG bị .gitignore che — vật liệu khoá có thể bị commit. "
        "Nhắc lại cái bẫy: pattern không có '/' là khớp basename, nên `.key` trần "
        "chỉ che file tên đúng '.key', không che '*.key'."
    )


@pytest.mark.parametrize("rel_path", MUST_NOT_BE_IGNORED)
def test_source_files_are_not_swept_up(rel_path: str) -> None:
    assert not _is_ignored(rel_path), (
        f"{rel_path!r} bị .gitignore che — bản vá secret quét quá tay và đang "
        "nuốt mã nguồn thật."
    )


def test_no_key_like_file_is_tracked() -> None:
    """Không có file khoá nào đã lỡ nằm trong index.

    `.gitignore` không gỡ được file ĐÃ tracked, nên che pattern thôi chưa đủ —
    phải khẳng định index đang sạch.
    """
    tracked = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.splitlines()
    suffixes = (".key", ".pem", ".p12", ".pfx", ".jks", ".keystore")
    offenders = [p for p in tracked if p.lower().endswith(suffixes)]
    assert not offenders, f"File khoá đang được git theo dõi: {offenders}"
