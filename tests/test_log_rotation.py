"""Log runtime phải tự xoay vòng, kể cả khi file đã lớn sẵn từ phiên trước.

server.log.jsonl trên máy dev đã phình tới 81,7 MB dù StructuredLogger có sẵn
_rotate(). Hai lý do trong code:
  - ngưỡng xoay dựa trên _flush_count, là biến của PHIÊN hiện tại; mỗi lần
    khởi động lại server nó về 0 nên file tồn từ trước không bao giờ bị xét;
  - _rotate() đọc bằng readlines() dù docstring ghi "streaming", nên file càng
    to càng tốn RAM đúng lúc không nên tốn.
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "agent"))


@pytest.fixture
def logger(tmp_path, monkeypatch):
    import middleware

    monkeypatch.setattr(middleware, "LOG_DIR", tmp_path)
    instance = middleware.StructuredLogger(name="test-logger", max_entries=100)
    instance.log_file = tmp_path / "server.log.jsonl"
    return instance


def _write_lines(path: Path, count: int):
    with open(path, "w", encoding="utf-8") as f:
        for i in range(count):
            f.write(json.dumps({"ts": "2026-08-05", "level": "info", "msg": f"line-{i}"}) + "\n")


def test_rotate_keeps_only_the_newest_entries(logger):
    _write_lines(logger.log_file, 1000)

    logger._rotate()

    lines = logger.log_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 100
    assert json.loads(lines[-1])["msg"] == "line-999", "phải giữ phần mới nhất"
    assert json.loads(lines[0])["msg"] == "line-900"


def test_oversized_file_from_a_previous_run_gets_rotated(logger):
    """Đây là ca thật: file to sẵn, tiến trình vừa khởi động nên bộ đếm bằng 0."""
    _write_lines(logger.log_file, 5000)
    assert logger._flush_count == 0

    logger.info("dòng mới sau khi khởi động lại")
    logger._flush()

    lines = logger.log_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) <= 100 + 1, (
        f"file cũ {5000} dòng không được xoay vòng sau khi tiến trình khởi động lại "
        f"(còn {len(lines)} dòng)"
    )


def test_rotate_handles_a_large_file_without_losing_the_tail(logger):
    """File lớn là đúng lúc xoay vòng phải chạy được, không phải lúc nó gục."""
    _write_lines(logger.log_file, 20_000)

    logger._rotate()

    lines = logger.log_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 100
    assert json.loads(lines[-1])["msg"] == "line-19999"


def test_rotate_survives_a_malformed_line(logger):
    """Log hỏng một dòng không được làm kẹt xoay vòng — đó là cách file phình mãi."""
    _write_lines(logger.log_file, 300)
    with open(logger.log_file, "a", encoding="utf-8") as f:
        f.write("{dòng hỏng không phải json\n")

    logger._rotate()

    lines = logger.log_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 100
