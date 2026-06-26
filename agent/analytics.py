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

import json
import logging
import os
import sys
import time
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock

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


def _default_data() -> dict:
    return {
        "queries": [],           # [{text, timestamp, tools, has_answer}]
        "entity_hits": {},       # {entity_id: count}
        "tool_usage": {},        # {tool_name: count}
        "unanswered": [],        # [{text, timestamp}]
        "daily_stats": {},       # {"2026-06-09": {queries: N, unique_users: N}}
        "sessions": 0,
    }


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


def _save(data: dict):
    try:
        tmp = ANALYTICS_FILE.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp.replace(ANALYTICS_FILE)
    except OSError as exc:
        logger.warning("Failed to save analytics: %s", exc)


def track_query(message: str, tools_used: list[str], reply: str, session_id: str = None):
    """Ghi nhận 1 query từ user."""
    with _lock:
        data = _load()
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")

        # Query log (giữ 1000 gần nhất)
        has_answer = len(reply) > 20 and "không tìm thấy" not in reply.lower()
        data["queries"].append({
            "text": message[:200],
            "timestamp": now.isoformat(),
            "tools": tools_used,
            "has_answer": has_answer,
        })
        data["queries"] = data["queries"][-1000:]

        # Unanswered queries
        if not has_answer:
            data["unanswered"].append({
                "text": message[:200],
                "timestamp": now.isoformat(),
            })
            data["unanswered"] = data["unanswered"][-200:]

        # Tool usage
        for tool in tools_used:
            # Extract tool name from "tool_name({...})"
            name = tool.split("(")[0] if "(" in tool else tool
            data["tool_usage"][name] = data["tool_usage"].get(name, 0) + 1

        # Daily stats
        if today not in data["daily_stats"]:
            data["daily_stats"][today] = {"queries": 0, "sessions": 0}
        data["daily_stats"][today]["queries"] += 1

        _save(data)


def track_entity_hit(entity_id: str):
    """Ghi nhận entity được truy cập."""
    with _lock:
        data = _load()
        data["entity_hits"][entity_id] = data["entity_hits"].get(entity_id, 0) + 1
        _save(data)


def track_session():
    """Ghi nhận 1 session mới."""
    with _lock:
        data = _load()
        data["sessions"] += 1
        today = datetime.now().strftime("%Y-%m-%d")
        if today not in data["daily_stats"]:
            data["daily_stats"][today] = {"queries": 0, "sessions": 0}
        data["daily_stats"][today]["sessions"] += 1
        _save(data)


def save_conversation(session_id: str, messages: list[dict]):
    """Lưu lịch sử hội thoại."""
    filepath = CONVERSATIONS_DIR / f"{session_id}.json"
    tmp = filepath.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "messages": messages[-50:],
        }, f, ensure_ascii=False, indent=2)
    tmp.replace(filepath)


# ── Report functions ──

def get_popular_queries(limit: int = 20, since: str | None = None) -> list[dict]:
    """Top câu hỏi phổ biến (nhóm theo similarity)."""
    data = _load()
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
    data = _load()
    sorted_hits = sorted(data["entity_hits"].items(), key=lambda x: -x[1])
    return [{"entity_id": eid, "hits": count} for eid, count in sorted_hits[:limit]]


def get_knowledge_gaps(limit: int = 20, since: str | None = None) -> list[dict]:
    """Câu hỏi mà agent không trả lời được → cần bổ sung KB."""
    data = _load()
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
    data = _load()
    result = []
    for i in range(days):
        date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        stats = data["daily_stats"].get(date, {"queries": 0, "sessions": 0})
        result.append({"date": date, **stats})
    return result


def get_tool_usage() -> dict:
    """Thống kê tool usage."""
    data = _load()
    return data.get("tool_usage", {})


def get_summary(since: str | None = None) -> dict:
    """Tổng quan analytics."""
    data = _load()
    today = datetime.now().strftime("%Y-%m-%d")
    today_stats = data["daily_stats"].get(today, {"queries": 0, "sessions": 0})
    queries = data["queries"]
    unanswered = data.get("unanswered", [])
    if since:
        queries = [q for q in queries if q.get("timestamp", "") >= since]
        unanswered = [q for q in unanswered if q.get("timestamp", "") >= since]
    return {
        "total_queries": len(queries),
        "unique_queries": len({q["text"].lower().strip() for q in queries if q.get("text")}),
        "total_sessions": data["sessions"],
        "today_queries": today_stats["queries"],
        "today_sessions": today_stats["sessions"],
        "top_entities": get_top_entities(5),
        "knowledge_gaps": len(unanswered),
        "tool_usage": data.get("tool_usage", {}),
    }
