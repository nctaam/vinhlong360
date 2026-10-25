"""
Kiểm soát ngân sách cho agent TỰ ĐỘNG gọi LLM (ngoại lệ có-kiểm-soát của §B8).

Mục tiêu: agent nền CHỈ được gọi LLM trong hạn mức cứng/ngày → không lặp lại lỗi
"rò chi phí LLM 24/7". Cap đếm theo NGÀY (UTC), reset tự động. Atomic (lock + file)
để nhiều thread/task không vượt cap.

Env:
  AUTONOMOUS_AGENT_ENABLED            — bật agent nền (mặc định false = TẮT, giữ §B8).
  AUTONOMOUS_AGENT_MAX_CALLS_PER_DAY  — cap số lần gọi LLM/ngày (mặc định 20).
"""
import json
import logging
import os
import tempfile
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_DATA = Path(__file__).resolve().parent / "data" / "autonomous_budget.json"
_lock = threading.Lock()
_ram_count: dict = {"date": "", "count": 0}


@contextmanager
def _interprocess_file_lock(path: Path):
    """Serialize autonomous budget reads/writes across worker processes."""
    lock_path = path.with_suffix(path.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    with os.fdopen(fd, "r+b") as handle:
        if os.name == "nt":
            import msvcrt
            handle.seek(0)
            handle.write(b"0")
            handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def max_calls_per_day() -> int:
    try:
        return max(0, int(os.environ.get("AUTONOMOUS_AGENT_MAX_CALLS_PER_DAY", "20")))
    except (ValueError, TypeError):
        return 20


def enabled() -> bool:
    return os.environ.get("AUTONOMOUS_AGENT_ENABLED", "false").strip().lower() in ("1", "true", "yes", "on")


def _load() -> dict:
    try:
        return json.loads(_DATA.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except Exception as exc:
        logger.warning("Budget file corrupt or unreadable (%s), counter reset to 0", exc)
        return {}


def _count_today(d: dict) -> int:
    return d.get("count", 0) if d.get("date") == _today() else 0


def try_consume(n: int = 1) -> bool:
    """Đặt trước n lần gọi LLM cho hôm nay. True nếu còn trong cap (và đã ghi nhận);
    False nếu vượt cap (KHÔNG ghi nhận → caller phải bỏ qua, không gọi LLM)."""
    cap = max_calls_per_day()
    with _lock:
        today = _today()
        if _ram_count["date"] == today and _ram_count["count"] + n > cap:
            return False
        with _interprocess_file_lock(_DATA):
            d = _load()
            today = _today()
            disk_count = _count_today(d)
            ram_count = _ram_count["count"] if _ram_count["date"] == today else 0
            count = max(disk_count, ram_count)
            if count + n > cap:
                return False
            new_count = count + n
            _ram_count["date"] = today
            _ram_count["count"] = new_count
            tmp_path: Path | None = None
            try:
                _DATA.parent.mkdir(parents=True, exist_ok=True)
                fd, tmp_name = tempfile.mkstemp(
                    dir=_DATA.parent,
                    prefix=f".{_DATA.name}.",
                    suffix=".tmp",
                )
                tmp_path = Path(tmp_name)
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write(json.dumps({"date": today, "count": new_count}))
                    f.flush()
                    os.fsync(f.fileno())
                tmp_path.replace(_DATA)
            except Exception as exc:
                logger.warning("Budget file write failed (%s) — cap enforced in RAM only this session", exc)
            finally:
                if tmp_path is not None:
                    tmp_path.unlink(missing_ok=True)
            return True


def status() -> dict:
    cap = max_calls_per_day()
    with _lock, _interprocess_file_lock(_DATA):
        today = _today()
        disk_count = _count_today(_load())
        ram_count = _ram_count["count"] if _ram_count["date"] == today else 0
        used = max(disk_count, ram_count)
    return {"enabled": enabled(), "cap_per_day": cap, "used_today": used,
            "remaining_today": max(0, cap - used), "date": today}
