"""
vinhlong360 — Analytics & Conversation Intelligence.

Theo dõi:
  - Câu hỏi phổ biến (popular queries)
  - Entity được hỏi nhiều nhất
  - Câu hỏi không trả lời được (knowledge gaps)
  - Session tracking
  - Thống kê sử dụng theo thời gian

Dữ liệu lưu: agent/data/analytics.json
"""

import heapq
import json
import logging
import os
import sys
import tempfile
from collections import Counter
from datetime import datetime, timedelta, timezone
from itertools import islice
from pathlib import Path
from threading import Lock

from owner_write_gate import owner_write_gate

logger = logging.getLogger(__name__)

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if hasattr(sys.stdout, "reconfigure") and sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(exist_ok=True)
ANALYTICS_FILE = DATA_DIR / "analytics.json"
CONVERSATIONS_DIR = DATA_DIR / "conversations"
CONVERSATIONS_DIR.mkdir(exist_ok=True)

_lock = Lock()
_MAX_CONVERSATION_FILES = 5_000
_MAX_DAILY_STATS = 365
_MAX_TOOL_USAGE = 500
_cache_meta: tuple[str, int, int] | None = None
_cache_data: dict | None = None


def _default_data() -> dict:
    return {
        "queries": [],           # [{text, timestamp, tools, has_answer}]
        "entity_hits": {},       # {entity_id: count}
        "tool_usage": {},        # {tool_name: count}
        "unanswered": [],        # [{text, timestamp}]
        "daily_stats": {},       # {"2026-06-09": {queries: N, unique_users: N}}
        "sessions": 0,
    }


def _file_meta() -> tuple[str, int, int] | None:
    try:
        st = ANALYTICS_FILE.stat()
        return (str(ANALYTICS_FILE), st.st_mtime_ns, st.st_size)
    except OSError:
        return None


def _load() -> dict:
    if ANALYTICS_FILE.exists():
        try:
            content = ANALYTICS_FILE.read_text(encoding="utf-8").strip()
            if not content:
                return _default_data()
            return json.loads(content)
        except (json.JSONDecodeError, OSError):
            # Corrupt file — reset to default
            return _default_data()
    return _default_data()


def _read_snapshot() -> dict:
    global _cache_meta, _cache_data
    meta = _file_meta()
    if meta is not None and meta == _cache_meta and _cache_data is not None:
        return _cache_data
    data = _load()
    _cache_meta = meta
    _cache_data = data
    return data


def _save(data: dict):
    global _cache_meta, _cache_data
    try:
        from versioned_json_store import atomic_write_json

        atomic_write_json(ANALYTICS_FILE, data, indent=2)
        _cache_meta = _file_meta()
        _cache_data = data
    except OSError as exc:
        _cache_meta = None
        _cache_data = None
        logger.warning("Failed to save analytics: %s", exc)


def _prune_daily_stats(daily_stats: dict) -> dict:
    if len(daily_stats) <= _MAX_DAILY_STATS:
        return daily_stats
    recent_days = sorted(daily_stats.keys())[-_MAX_DAILY_STATS:]
    return {day: daily_stats[day] for day in recent_days}


def track_query(
    message: str,
    tools_used: list[str],
    reply: str,
    session_id: str = None,
    *,
    owner_key: str = "",
):
    """Ghi nhận 1 query từ user."""
    owner_write_gate.assert_writable(owner_key)
    with _lock:
        data = _read_snapshot()
        now = datetime.now(timezone.utc)
        today = now.strftime("%Y-%m-%d")

        # Query log (giữ 1000 gần nhất)
        has_answer = len(reply) > 20 and "không tìm thấy" not in reply.lower()
        data["queries"].append({
            "text": message[:200],
            "timestamp": now.isoformat(),
            "tools": tools_used,
            "has_answer": has_answer,
            "owner_key": owner_key,
        })
        data["queries"] = data["queries"][-1000:]

        # Unanswered queries
        if not has_answer:
            data["unanswered"].append({
                "text": message[:200],
                "timestamp": now.isoformat(),
                "owner_key": owner_key,
            })
            data["unanswered"] = data["unanswered"][-200:]

        # Tool usage
        for tool in tools_used:
            name = tool.split("(")[0] if "(" in tool else tool
            data["tool_usage"][name] = data["tool_usage"].get(name, 0) + 1
        if len(data["tool_usage"]) > _MAX_TOOL_USAGE:
            top_tools = heapq.nlargest(_MAX_TOOL_USAGE, data["tool_usage"].items(), key=lambda x: x[1])
            data["tool_usage"] = dict(top_tools)

        # Daily stats
        if today not in data["daily_stats"]:
            data["daily_stats"][today] = {"queries": 0, "sessions": 0}
        data["daily_stats"][today]["queries"] += 1
        data["daily_stats"] = _prune_daily_stats(data["daily_stats"])

        _save(data)


_MAX_ENTITY_HITS = 10_000


def track_entity_hit(entity_id: str):
    """Ghi nhận entity được truy cập."""
    with _lock:
        data = _read_snapshot()
        data["entity_hits"][entity_id] = data["entity_hits"].get(entity_id, 0) + 1
        if len(data["entity_hits"]) > _MAX_ENTITY_HITS:
            top = heapq.nlargest(_MAX_ENTITY_HITS, data["entity_hits"].items(), key=lambda x: x[1])
            data["entity_hits"] = dict(top)
        _save(data)


def track_session():
    """Ghi nhận 1 session mới."""
    with _lock:
        data = _read_snapshot()
        data["sessions"] += 1
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if today not in data["daily_stats"]:
            data["daily_stats"][today] = {"queries": 0, "sessions": 0}
        data["daily_stats"][today]["sessions"] += 1
        data["daily_stats"] = _prune_daily_stats(data["daily_stats"])
        _save(data)


def save_conversation(
    session_id: str, messages: list[dict], *, owner_key: str = ""
):
    """Lưu lịch sử hội thoại."""
    owner_write_gate.assert_writable(owner_key)
    tmp = None
    try:
        filepath = CONVERSATIONS_DIR / f"{session_id}.json"
        filepath.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            dir=str(filepath.parent),
            prefix=f".{filepath.name}.",
            suffix=".tmp",
        )
        tmp = Path(tmp_name)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({
                "session_id": session_id,
                "owner_key": owner_key,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "messages": messages[-50:],
            }, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        tmp.replace(filepath)
    except OSError as exc:
        logger.warning("Failed to save conversation %s: %s", session_id, exc)
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)


def purge_owner_records(owner_key: str) -> int:
    """Remove exact owner-attributed query and unanswered records."""
    with _lock:
        data = _read_snapshot()
        removed = 0
        for field in ("queries", "unanswered"):
            records = data.get(field, [])
            retained = [
                record
                for record in records
                if record.get("owner_key", "") != owner_key
            ]
            removed += len(records) - len(retained)
            data[field] = retained
        if removed:
            _save(data)
        return removed


def verify_owner_records_absent(owner_key: str) -> bool:
    with _lock:
        if not ANALYTICS_FILE.exists():
            return True
        content = ANALYTICS_FILE.read_text(encoding="utf-8").strip()
        if not content:
            raise ValueError("Invalid analytics store")
        data = json.loads(content)
        if not isinstance(data, dict):
            raise ValueError("Invalid analytics store")
        return not any(
            record.get("owner_key", "") == owner_key
            for field in ("queries", "unanswered")
            for record in data.get(field, [])
        )


def export_owner_records(owner_key: str) -> list[dict]:
    """Return owner-attributed analytics rows for lifecycle export."""
    with _lock:
        data = _read_snapshot()
        return [
            dict(record)
            for field in ("queries", "unanswered")
            for record in data.get(field, [])
            if record.get("owner_key", "") == owner_key
        ]


def _conversation_files() -> list[Path]:
    files = list(islice(CONVERSATIONS_DIR.glob("*.json"), _MAX_CONVERSATION_FILES + 1))
    if len(files) > _MAX_CONVERSATION_FILES:
        raise RuntimeError("Conversation store scan limit exceeded")
    return files


def _conversation_owner(filepath: Path) -> str:
    data = json.loads(filepath.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Invalid conversation store")
    return data.get("owner_key", "")


def purge_owner_conversations(owner_key: str) -> int:
    """Delete conversation files explicitly attributed to one exact owner."""
    removed = 0
    for filepath in _conversation_files():
        if _conversation_owner(filepath) != owner_key:
            continue
        filepath.unlink()
        removed += 1
    return removed


def verify_owner_conversations_absent(owner_key: str) -> bool:
    return not any(
        _conversation_owner(filepath) == owner_key
        for filepath in _conversation_files()
    )


def purge_owner(owner_key: str) -> int:
    return purge_owner_records(owner_key) + purge_owner_conversations(owner_key)


def verify_owner_absent(owner_key: str) -> bool:
    return verify_owner_records_absent(owner_key) and verify_owner_conversations_absent(
        owner_key
    )


# ── Report functions ──

def get_popular_queries(limit: int = 20, since: str | None = None) -> list[dict]:
    """Top câu hỏi phổ biến (nhóm theo similarity)."""
    with _lock:
        data = _read_snapshot()
        counter = Counter()
        for q in data["queries"]:
            if since and q.get("timestamp", "") < since:
                continue
            text = q["text"].lower().strip().rstrip("?").strip()
            if len(text) > 5:
                counter[text] += 1
        return [{"query": q, "count": c} for q, c in counter.most_common(limit)]


def get_top_entities(limit: int = 20) -> list[dict]:
    """Entities được truy cập nhiều nhất."""
    with _lock:
        data = _read_snapshot()
        top_hits = heapq.nlargest(limit, data["entity_hits"].items(), key=lambda x: x[1])
        return [{"entity_id": eid, "hits": count} for eid, count in top_hits]


def get_knowledge_gaps(limit: int = 20, since: str | None = None) -> list[dict]:
    """Câu hỏi mà agent không trả lời được → cần bổ sung KB."""
    with _lock:
        data = _read_snapshot()
        counter = Counter()
        for q in data["unanswered"]:
            if since and q.get("timestamp", "") < since:
                continue
            text = q["text"].lower().strip().rstrip("?").strip()
            if len(text) > 5:
                counter[text] += 1
        return [{"query": q, "count": c} for q, c in counter.most_common(limit)]


def get_daily_stats(days: int = 30) -> list[dict]:
    """Thống kê sử dụng theo ngày."""
    with _lock:
        data = _read_snapshot()
        now = datetime.now(timezone.utc)
        result = []
        for i in range(days):
            date = (now - timedelta(days=i)).strftime("%Y-%m-%d")
            stats = data["daily_stats"].get(date, {"queries": 0, "sessions": 0})
            result.append({"date": date, **stats})
        return result


def get_tool_usage() -> dict:
    """Thống kê tool usage."""
    with _lock:
        data = _read_snapshot()
        return dict(data.get("tool_usage", {}))


def get_summary(since: str | None = None) -> dict:
    """Tổng quan analytics."""
    with _lock:
        data = _read_snapshot()
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        today_stats = data["daily_stats"].get(today, {"queries": 0, "sessions": 0})
        queries = data["queries"]
        unanswered = data.get("unanswered", [])
        if since:
            queries = [q for q in queries if q.get("timestamp", "") >= since]
            unanswered = [q for q in unanswered if q.get("timestamp", "") >= since]
        sorted_hits = sorted(data["entity_hits"].items(), key=lambda x: -x[1])[:5]
        top_entities = [{"entity_id": eid, "hits": count} for eid, count in sorted_hits]
        return {
            "total_queries": len(queries),
            "unique_queries": len({q["text"].lower().strip() for q in queries if q.get("text")}),
            "total_sessions": data["sessions"],
            "today_queries": today_stats["queries"],
            "today_sessions": today_stats["sessions"],
            "top_entities": top_entities,
            "knowledge_gaps": len(unanswered),
            "tool_usage": dict(data.get("tool_usage", {})),
        }
