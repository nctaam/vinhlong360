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
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

_DATA = Path(__file__).resolve().parent / "data" / "autonomous_budget.json"
_lock = threading.Lock()


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
    except Exception:
        return {}


def _count_today(d: dict) -> int:
    return d.get("count", 0) if d.get("date") == _today() else 0


def try_consume(n: int = 1) -> bool:
    """Đặt trước n lần gọi LLM cho hôm nay. True nếu còn trong cap (và đã ghi nhận);
    False nếu vượt cap (KHÔNG ghi nhận → caller phải bỏ qua, không gọi LLM)."""
    cap = max_calls_per_day()
    with _lock:
        d = _load()
        count = _count_today(d)
        if count + n > cap:
            return False
        try:
            _DATA.parent.mkdir(parents=True, exist_ok=True)
            tmp = _DATA.with_suffix(".tmp")
            tmp.write_text(json.dumps({"date": _today(), "count": count + n}), encoding="utf-8")
            tmp.replace(_DATA)
        except Exception:
            pass  # ghi log thất bại không nên chặn (nhưng cap vẫn tính trong RAM phiên này)
        return True


def status() -> dict:
    cap = max_calls_per_day()
    with _lock:
        used = _count_today(_load())
    return {"enabled": enabled(), "cap_per_day": cap, "used_today": used,
            "remaining_today": max(0, cap - used), "date": _today()}
