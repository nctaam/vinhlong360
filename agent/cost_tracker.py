"""
vinhlong360 — Token Usage & Cost Attribution Module.

Theo doi chi phi su dung LLM cho Knowledge Agent:
  1. TokenCounter  — trich xuat token usage tu response, uoc tinh fallback,
                     tinh chi phi theo bang gia model.
  2. CostAttribution — ghi nhan chi phi theo session/agent/tool,
                       luu tru agent/data/costs.json (atomic write).
  3. BudgetManager — gioi han chi phi daily/monthly/session,
                     canh bao khi vuot 80% ngan sach.

Convenience:
  track_llm_call()   — 1 buoc: extract tokens + tinh cost + record
  get_cost_report()  — bao cao toan bo cho /system/costs endpoint

Persistence: agent/data/costs.json (write .tmp roi os.replace)
Thread-safe: moi state mutation deu qua threading.Lock.
"""

import json
import logging
import os
import re
from collections import deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Deque, Dict, List, Optional

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(exist_ok=True)
COSTS_FILE = DATA_DIR / "costs.json"


# ══════════════════════════════════════════════════
#  PRICING TABLE
# ══════════════════════════════════════════════════

# Gia tinh theo USD per 1K tokens
_PRICING: Dict[str, Dict[str, float]] = {
    "cx/gpt-5.4": {
        "input": 0.005,
        "output": 0.015,
    },
    "cx/gpt-5.4-mini": {
        "input": 0.0002,
        "output": 0.0006,
    },
}

_DEFAULT_PRICING: Dict[str, float] = {
    "input": 0.001,
    "output": 0.003,
}


# ══════════════════════════════════════════════════
#  TOKEN COUNTER
# ══════════════════════════════════════════════════

# Pattern phat hien ky tu Vietnamese (dau + Unicode block)
_VIETNAMESE_RE = re.compile(
    r"[À-ɏḀ-ỿ̀-ͯ]"
)


class TokenCounter:
    """Trich xuat va uoc tinh token usage, tinh chi phi."""

    def count_from_response(self, response: Any) -> Dict[str, int]:
        """Extract prompt_tokens, completion_tokens, total_tokens
        tu OpenAI-compatible response object.

        Tra ve dict voi cac key: prompt_tokens, completion_tokens, total_tokens.
        Neu response khong co usage info, tra ve tat ca = 0.
        """
        try:
            usage = response.usage
            prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
            completion_tokens = getattr(usage, "completion_tokens", 0) or 0
            total_tokens = getattr(usage, "total_tokens", 0) or 0
            # Dam bao total nhat quan
            if total_tokens == 0 and (prompt_tokens or completion_tokens):
                total_tokens = prompt_tokens + completion_tokens
            return {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
            }
        except (AttributeError, TypeError):
            logger.warning("Khong the trich xuat token usage tu response")
            return {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            }

    def estimate_tokens(self, text: str) -> int:
        """Uoc tinh so token cho text (fallback khi khong co usage info).

        Vietnamese text: ~2 chars/token (nhieu dau, Unicode).
        English text:    ~4 chars/token.
        Mixed: tinh ty le Vietnamese roi noi suy.
        """
        if not text:
            return 0
        total_chars = len(text)
        # Dem ky tu co dau Vietnamese
        viet_chars = len(_VIETNAMESE_RE.findall(text))
        viet_ratio = viet_chars / total_chars if total_chars > 0 else 0
        # Noi suy chars_per_token tu 2 (VN) den 4 (EN)
        chars_per_token = 2.0 + (1.0 - viet_ratio) * 2.0
        return max(1, int(total_chars / chars_per_token + 0.5))

    def calculate_cost(self, tokens: Dict[str, int], model: str) -> float:
        """Tinh chi phi USD tu token usage va model name.

        tokens: {"prompt_tokens": int, "completion_tokens": int, ...}
        model:  ten model (e.g. "cx/gpt-5.4-mini")

        Tra ve chi phi (float, USD).
        """
        pricing = _PRICING.get(model, _DEFAULT_PRICING)
        prompt_tokens = tokens.get("prompt_tokens", 0)
        completion_tokens = tokens.get("completion_tokens", 0)
        input_cost = (prompt_tokens / 1000.0) * pricing["input"]
        output_cost = (completion_tokens / 1000.0) * pricing["output"]
        return round(input_cost + output_cost, 8)


# ══════════════════════════════════════════════════
#  COST ATTRIBUTION
# ══════════════════════════════════════════════════

_MAX_RECORDS = 10_000
_AUTO_SAVE_INTERVAL = 20


class CostAttribution:
    """Ghi nhan va phan tich chi phi theo session/agent/tool.

    Luu toi da 10,000 records (FIFO eviction).
    Tu dong save moi 50 records vao agent/data/costs.json.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._records: Deque[Dict[str, Any]] = deque(maxlen=_MAX_RECORDS)
        self._unsaved_count: int = 0
        self._load()

    # ── Persistence ─────────────────────────────────

    def _load(self) -> None:
        """Doc records tu costs.json (neu ton tai)."""
        if not COSTS_FILE.exists():
            return
        try:
            with open(COSTS_FILE, encoding="utf-8") as f:
                data = json.load(f)
            records = data.get("records", [])
            # Chi giu _MAX_RECORDS records gan nhat
            for rec in records[-_MAX_RECORDS:]:
                self._records.append(rec)
            logger.info("Da load %d cost records tu %s", len(self._records), COSTS_FILE)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Khong doc duoc costs.json: %s", exc)

    def _save(self) -> None:
        """Atomic write: ghi .tmp roi os.replace."""
        data = {
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "total_records": len(self._records),
            "records": list(self._records),
        }
        tmp_file = COSTS_FILE.with_suffix(".json.tmp")
        try:
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(str(tmp_file), str(COSTS_FILE))
            self._unsaved_count = 0
            logger.debug("Saved %d cost records to %s", len(self._records), COSTS_FILE)
        except OSError as exc:
            logger.error("Loi khi save costs.json: %s", exc)

    # ── Record ──────────────────────────────────────

    def record(
        self,
        session_id: str,
        query: str,
        agent_name: str,
        tool_name: Optional[str],
        model: str,
        tokens: Dict[str, int],
        cost: float,
    ) -> None:
        """Ghi nhan 1 LLM call voi chi phi."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "session_id": session_id,
            "query": query[:200],
            "agent_name": agent_name,
            "tool_name": tool_name,
            "model": model,
            "tokens": tokens,
            "cost": cost,
        }
        with self._lock:
            self._records.append(entry)
            self._unsaved_count += 1
            if self._unsaved_count >= _AUTO_SAVE_INTERVAL:
                self._save()

    # ── Queries ─────────────────────────────────────

    def get_session_cost(self, session_id: str) -> Dict[str, Any]:
        """Tong chi phi cho 1 session."""
        with self._lock:
            records = [r for r in self._records if r["session_id"] == session_id]
        total_cost = sum(r["cost"] for r in records)
        total_tokens = sum(r["tokens"].get("total_tokens", 0) for r in records)
        return {
            "session_id": session_id,
            "total_cost": round(total_cost, 6),
            "total_tokens": total_tokens,
            "query_count": len(records),
        }

    def get_agent_costs(self) -> Dict[str, Any]:
        """Chi phi phan theo agent name."""
        with self._lock:
            records = list(self._records)
        agents: Dict[str, Dict[str, Any]] = {}
        for r in records:
            name = r["agent_name"]
            if name not in agents:
                agents[name] = {"cost": 0.0, "tokens": 0, "queries": 0}
            agents[name]["cost"] += r["cost"]
            agents[name]["tokens"] += r["tokens"].get("total_tokens", 0)
            agents[name]["queries"] += 1
        # Round costs
        for info in agents.values():
            info["cost"] = round(info["cost"], 6)
        return agents

    def get_tool_costs(self) -> Dict[str, Any]:
        """Chi phi phan theo tool name."""
        with self._lock:
            records = list(self._records)
        tools: Dict[str, Dict[str, Any]] = {}
        for r in records:
            name = r["tool_name"] or "(no tool)"
            if name not in tools:
                tools[name] = {"cost": 0.0, "tokens": 0, "calls": 0}
            tools[name]["cost"] += r["cost"]
            tools[name]["tokens"] += r["tokens"].get("total_tokens", 0)
            tools[name]["calls"] += 1
        for info in tools.values():
            info["cost"] = round(info["cost"], 6)
        return tools

    def get_daily_costs(self, days: int = 30) -> List[Dict[str, Any]]:
        """Xu huong chi phi theo ngay (days ngay gan nhat)."""
        with self._lock:
            records = list(self._records)
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
        daily: Dict[str, Dict[str, Any]] = {}
        for r in records:
            date = r.get("date", "")
            if date < cutoff:
                continue
            if date not in daily:
                daily[date] = {"date": date, "cost": 0.0, "tokens": 0, "queries": 0}
            daily[date]["cost"] += r["cost"]
            daily[date]["tokens"] += r["tokens"].get("total_tokens", 0)
            daily[date]["queries"] += 1
        # Round va sap xep
        result = sorted(daily.values(), key=lambda d: d["date"])
        for day in result:
            day["cost"] = round(day["cost"], 6)
        return result

    def get_summary(self) -> Dict[str, Any]:
        """Tong hop: tong chi phi, trung binh, queries count, top expensive."""
        with self._lock:
            records = list(self._records)
        if not records:
            return {
                "total_cost": 0.0,
                "avg_cost_per_query": 0.0,
                "total_queries": 0,
                "total_tokens": 0,
                "top_expensive_queries": [],
            }
        total_cost = sum(r["cost"] for r in records)
        total_tokens = sum(r["tokens"].get("total_tokens", 0) for r in records)
        avg_cost = total_cost / len(records) if records else 0.0
        # Top 10 queries dat nhat
        sorted_by_cost = sorted(records, key=lambda r: r["cost"], reverse=True)
        top_expensive = [
            {
                "query": r["query"],
                "cost": round(r["cost"], 6),
                "model": r["model"],
                "agent": r["agent_name"],
                "tokens": r["tokens"].get("total_tokens", 0),
                "timestamp": r["timestamp"],
            }
            for r in sorted_by_cost[:10]
        ]
        return {
            "total_cost": round(total_cost, 6),
            "avg_cost_per_query": round(avg_cost, 8),
            "total_queries": len(records),
            "total_tokens": total_tokens,
            "top_expensive_queries": top_expensive,
        }

    def force_save(self) -> None:
        """Bat buoc save ngay (goi khi shutdown)."""
        with self._lock:
            self._save()


# ══════════════════════════════════════════════════
#  BUDGET MANAGER
# ══════════════════════════════════════════════════

_DEFAULT_DAILY_LIMIT = float(os.environ.get("COST_DAILY_LIMIT", "10.0"))
_DEFAULT_MONTHLY_LIMIT = float(os.environ.get("COST_MONTHLY_LIMIT", "200.0"))
_ALERT_THRESHOLD = 0.80  # Canh bao tai 80% ngan sach


class BudgetManager:
    """Quan ly gioi han chi phi theo daily/monthly/session."""

    def __init__(self, attribution: CostAttribution) -> None:
        self._lock = Lock()
        self._attribution = attribution
        self._limits: Dict[str, float] = {
            "daily": _DEFAULT_DAILY_LIMIT,
            "monthly": _DEFAULT_MONTHLY_LIMIT,
            "session": 0.0,  # 0 = khong gioi han
        }
        self.alert_threshold: float = _ALERT_THRESHOLD

    def set_limit(self, scope: str, limit: float) -> None:
        """Dat gioi han chi phi cho scope ("daily", "monthly", "session")."""
        if scope not in ("daily", "monthly", "session"):
            raise ValueError(f"Invalid scope: {scope}. Must be daily/monthly/session.")
        with self._lock:
            self._limits[scope] = float(limit)
            logger.info("Budget limit set: %s = $%.4f", scope, limit)

    def check_budget(self, scope: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Kiem tra tinh trang ngan sach cho scope.

        Tra ve:
          within_budget:  bool
          spent:          float
          limit:          float
          remaining:      float
          utilization_pct: float (0-100)
        """
        with self._lock:
            limit = self._limits.get(scope, 0.0)

        spent = self._calculate_spent(scope, session_id)

        if limit <= 0:
            return {
                "within_budget": True,
                "spent": round(spent, 6),
                "limit": 0.0,
                "remaining": float("inf"),
                "utilization_pct": 0.0,
            }

        remaining = max(0.0, limit - spent)
        utilization = (spent / limit * 100.0) if limit > 0 else 0.0
        within_budget = spent <= limit

        if utilization >= self.alert_threshold * 100:
            logger.warning(
                "Budget alert [%s]: %.1f%% utilized ($%.4f / $%.4f)",
                scope, utilization, spent, limit,
            )

        return {
            "within_budget": within_budget,
            "spent": round(spent, 6),
            "limit": round(limit, 6),
            "remaining": round(remaining, 6),
            "utilization_pct": round(utilization, 2),
        }

    def _calculate_spent(self, scope: str, session_id: Optional[str] = None) -> float:
        """Tinh tong chi phi da su dung trong scope."""
        if scope == "session":
            if not session_id:
                return 0.0
            info = self._attribution.get_session_cost(session_id)
            return info["total_cost"]

        daily_costs = self._attribution.get_daily_costs(days=31)

        if scope == "daily":
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            for day in daily_costs:
                if day["date"] == today:
                    return day["cost"]
            return 0.0

        if scope == "monthly":
            month_prefix = datetime.now(timezone.utc).strftime("%Y-%m")
            total = 0.0
            for day in daily_costs:
                if day["date"].startswith(month_prefix):
                    total += day["cost"]
            return total

        return 0.0


# ══════════════════════════════════════════════════
#  MODULE SINGLETONS
# ══════════════════════════════════════════════════

token_counter = TokenCounter()
cost_attribution = CostAttribution()
budget_manager = BudgetManager(cost_attribution)


# ══════════════════════════════════════════════════
#  CONVENIENCE FUNCTIONS
# ══════════════════════════════════════════════════

def track_llm_call(
    session_id: str,
    agent_name: str,
    model: str,
    response: Any,
    query: str = "",
    tool_name: Optional[str] = None,
) -> Dict[str, Any]:
    """1-step: extract tokens + tinh cost + record.

    Tra ve dict voi tokens, cost, budget_status.
    """
    tokens = token_counter.count_from_response(response)
    cost = token_counter.calculate_cost(tokens, model)

    cost_attribution.record(
        session_id=session_id,
        query=query,
        agent_name=agent_name,
        tool_name=tool_name,
        model=model,
        tokens=tokens,
        cost=cost,
    )

    budget_daily = budget_manager.check_budget("daily")
    budget_monthly = budget_manager.check_budget("monthly")

    return {
        "tokens": tokens,
        "cost": cost,
        "budget": {
            "daily": budget_daily,
            "monthly": budget_monthly,
        },
    }


def get_cost_report() -> Dict[str, Any]:
    """Bao cao toan bo chi phi cho /system/costs endpoint."""
    return {
        "summary": cost_attribution.get_summary(),
        "by_agent": cost_attribution.get_agent_costs(),
        "by_tool": cost_attribution.get_tool_costs(),
        "daily_trend": cost_attribution.get_daily_costs(days=30),
        "budget": {
            "daily": budget_manager.check_budget("daily"),
            "monthly": budget_manager.check_budget("monthly"),
        },
    }
