"""Tests for scripts/backup_offsite.py."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.backup_offsite import _find_latest_backup, _file_size_human


class TestFindLatestBackup:
    def test_finds_latest_tarball(self, tmp_path):
        old = tmp_path / "backup_old.tar.gz"
        old.write_text("old")
        new = tmp_path / "backup_new.tar.gz"
        new.write_text("newest")
        # Ensure mtime differs
        import os
        os.utime(old, (1000, 1000))
        os.utime(new, (2000, 2000))

        result = _find_latest_backup(tmp_path)
        assert result is not None
        assert result.name == "backup_new.tar.gz"

    def test_empty_dir_returns_none(self, tmp_path):
        result = _find_latest_backup(tmp_path)
        assert result is None

    def test_nonexistent_dir_returns_none(self, tmp_path):
        result = _find_latest_backup(tmp_path / "nonexistent")
        assert result is None

    def test_finds_subdirectories(self, tmp_path):
        d = tmp_path / "backup_20260627"
        d.mkdir()
        result = _find_latest_backup(tmp_path)
        assert result is not None
        assert result.name == "backup_20260627"


class TestFileSizeHuman:
    def test_small_file(self, tmp_path):
        f = tmp_path / "small.txt"
        f.write_text("hello")
        result = _file_size_human(f)
        assert "B" in result

    def test_result_format(self, tmp_path):
        f = tmp_path / "test.bin"
        f.write_bytes(b"x" * 2048)
        result = _file_size_human(f)
        assert "KB" in result
