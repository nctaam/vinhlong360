"""
vinhlong360 — Auto Prompt Tuning & Parameter Optimization.

Tu dong toi uu hoa:
  - Thu thap performance data tu moi phien hoi thoai
  - Phan tich diem yeu theo category (comparison, itinerary, food, ...)
  - De xuat prompt variant moi (rules-based, khong dung LLM)
  - Tinh chinh temperature, max_rounds, max_tool_calls theo category
  - Danh gia hieu qua tung tool va goi y thu tu su dung

Du lieu luu: agent/data/optimizer/
  - performance.json — ban ghi hieu suat
  - variants.json    — lich su prompt variant
  - params.json      — tham so toi uu hoa theo category
  - tool_scores.json — diem hieu qua tung tool

Thread-safe: moi class dung threading.Lock rieng.
Persistence: atomic writes (ghi .tmp roi rename).
"""

import json
import logging
import statistics
import time
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from threading import Lock

logger = logging.getLogger(__name__)

# ── Paths ────────────────────────────────────────────────────────────────────

DATA_DIR = Path(__file__).resolve().parent / "data" / "optimizer"
DATA_DIR.mkdir(parents=True, exist_ok=True)

PERFORMANCE_FILE = DATA_DIR / "performance.json"
VARIANTS_FILE = DATA_DIR / "variants.json"
PARAMS_FILE = DATA_DIR / "params.json"
TOOL_SCORES_FILE = DATA_DIR / "tool_scores.json"

MAX_RECORDS = 5000

# ── Query categories (mirroring reflexion._categorize_query) ─────────────────

QUERY_CATEGORIES = [
    "itinerary", "food", "history", "culture", "comparison", "general",
]

# ── Atomic write helper ──────────────────────────────────────────────────────


def _atomic_write(path: Path, data: dict) -> None:
    """Write JSON atomically: write to .tmp then rename."""
    try:
        content = json.dumps(data, ensure_ascii=False, indent=2)
        tmp_path = path.with_suffix(".tmp")
        tmp_path.write_text(content, encoding="utf-8")
        if path.exists():
            path.unlink()
        tmp_path.rename(path)
    except Exception as e:
        logger.error("Failed to write %s: %s", path, e)


def _load_json(path: Path, default=None):
    """Load JSON file, return *default* on any failure."""
    if default is None:
        default = {}
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("Failed to load %s: %s", path, e)
    return default


def _empty_stats() -> dict:
    """Zeroed stats payload for an empty time window."""
    return {
        "total_records": 0,
        "avg_score": 0.0,
        "avg_duration": 0.0,
        "avg_tokens": 0,
        "by_agent": {},
        "by_category": {},
        "tool_usage_rate": 0.0,
        "hallucination_rate": 0.0,
        "avg_reply_length": 0,
    }


def _stats_by_agent(window: list[dict]) -> dict:
    """Aggregate per-agent count + avg_score over *window* records."""
    by_agent: dict[str, list[dict]] = defaultdict(list)
    for r in window:
        by_agent[r["agent_name"]].append(r)
    agent_stats = {}
    for agent, recs in by_agent.items():
        agent_scores = [r["quality_score"] for r in recs]
        agent_stats[agent] = {
            "count": len(recs),
            "avg_score": round(statistics.mean(agent_scores), 2),
        }
    return agent_stats


def _stats_by_category(window: list[dict]) -> dict:
    """Aggregate per-category count/avg_score/avg_duration/score_std."""
    by_cat: dict[str, list[dict]] = defaultdict(list)
    for r in window:
        by_cat[r["category"]].append(r)
    cat_stats = {}
    for cat, recs in by_cat.items():
        cat_scores = [r["quality_score"] for r in recs]
        cat_durations = [r["duration"] for r in recs]
        cat_stats[cat] = {
            "count": len(recs),
            "avg_score": round(statistics.mean(cat_scores), 2),
            "avg_duration": round(statistics.mean(cat_durations), 2),
            "score_std": round(statistics.pstdev(cat_scores), 2) if len(cat_scores) > 1 else 0.0,
        }
    return cat_stats


def _categorize_query(query: str) -> str:
    """Classify a query into a category (same logic as reflexion module)."""
    q = query.lower()
    if any(w in q for w in ["lịch trình", "đi đâu", "gợi ý", "plan", "itinerary"]):
        return "itinerary"
    if any(w in q for w in ["ăn gì", "món", "đặc sản", "ẩm thực", "food"]):
        return "food"
    if any(w in q for w in ["lịch sử", "ai", "nhân vật", "người", "history"]):
        return "history"
    if any(w in q for w in ["chùa", "lễ hội", "văn hóa", "khmer", "culture"]):
        return "culture"
    if any(w in q for w in ["so sánh", "khác nhau", "hơn", "compare"]):
        return "comparison"
    return "general"


# ═════════════════════════════════════════════════════════════════════════════
#  1. PerformanceCollector
# ═════════════════════════════════════════════════════════════════════════════


class PerformanceCollector:
    """
    Thu thap va luu tru performance data cua moi phien hoi thoai.

    Giu toi da MAX_RECORDS ban ghi trong memory, persist xuong disk.
    """

    def __init__(self):
        self._lock = Lock()
        self._records: list[dict] = []
        self._load()

    def _load(self):
        data = _load_json(PERFORMANCE_FILE, default={"records": []})
        self._records = data.get("records", [])[-MAX_RECORDS:]

    def _save(self):
        _atomic_write(PERFORMANCE_FILE, {
            "records": self._records[-MAX_RECORDS:],
            "saved_at": time.time(),
        })

    # ── Public API ───────────────────────────────────────────────────────

    def record(
        self,
        session_id: str,
        query: str,
        agent_name: str,
        tools_used: list[str],
        quality_score: float,
        duration: float,
        token_count: int,
    ) -> None:
        """Ghi nhan mot ket qua tuong tac."""
        entry = {
            "session_id": session_id,
            "query": query,
            "category": _categorize_query(query),
            "agent_name": agent_name,
            "tools_used": tools_used,
            "quality_score": quality_score,
            "duration": duration,
            "token_count": token_count,
            "timestamp": time.time(),
        }
        with self._lock:
            self._records.append(entry)
            # Trim to MAX_RECORDS
            if len(self._records) > MAX_RECORDS:
                self._records = self._records[-MAX_RECORDS:]
            self._save()

    def get_stats(self, window_hours: float = 24) -> dict:
        """
        Thong ke hieu suat trong khung thoi gian.

        Returns: {
            total_records, avg_score, avg_duration, avg_tokens,
            by_agent: {agent: {count, avg_score}},
            by_category: {cat: {count, avg_score, avg_duration}},
            tool_usage_rate, hallucination_rate, avg_reply_length,
        }
        """
        cutoff = time.time() - window_hours * 3600
        with self._lock:
            window = [r for r in self._records if r["timestamp"] >= cutoff]

        if not window:
            return _empty_stats()

        scores = [r["quality_score"] for r in window]
        durations = [r["duration"] for r in window]
        tokens = [r["token_count"] for r in window]

        # By agent
        agent_stats = _stats_by_agent(window)

        # By category
        cat_stats = _stats_by_category(window)

        # Tool usage rate
        tool_used_count = sum(1 for r in window if r["tools_used"])
        tool_usage_rate = round(tool_used_count / len(window) * 100, 1)

        # Hallucination rate (approximate: low score + no tools = likely hallucination)
        hallucination_count = sum(
            1 for r in window
            if r["quality_score"] < 4 and not r["tools_used"]
        )
        hallucination_rate = round(hallucination_count / len(window) * 100, 1)

        # Avg reply length (approximate from tokens)
        avg_reply_length = round(statistics.mean(tokens) * 0.75)  # ~0.75 chars/token

        return {
            "total_records": len(window),
            "avg_score": round(statistics.mean(scores), 2),
            "avg_duration": round(statistics.mean(durations), 2),
            "avg_tokens": round(statistics.mean(tokens)),
            "by_agent": agent_stats,
            "by_category": cat_stats,
            "tool_usage_rate": tool_usage_rate,
            "hallucination_rate": hallucination_rate,
            "avg_reply_length": avg_reply_length,
        }

    def get_records(self, window_hours: float = 24) -> list[dict]:
        """Raw records within window (for internal use by other optimizers)."""
        cutoff = time.time() - window_hours * 3600
        with self._lock:
            return [r for r in self._records if r["timestamp"] >= cutoff]

    @property
    def total_count(self) -> int:
        with self._lock:
            return len(self._records)


# ═════════════════════════════════════════════════════════════════════════════
#  2. PromptOptimizer
# ═════════════════════════════════════════════════════════════════════════════


class PromptOptimizer:
    """
    Rules-based prompt variant manager.

    Phan tich performance data va de xuat prompt addon moi.
    Khong dung LLM — chi dua tren nguong diem va quy tac.
    """

    def __init__(self):
        self._lock = Lock()
        self._variants: list[dict] = []
        self._active_id: str = "default"
        self._load()

    def _load(self):
        data = _load_json(VARIANTS_FILE, default={
            "variants": [self._default_variant()],
            "active_id": "default",
        })
        self._variants = data.get("variants", [self._default_variant()])
        self._active_id = data.get("active_id", "default")
        # Ensure default variant always exists
        if not any(v["id"] == "default" for v in self._variants):
            self._variants.insert(0, self._default_variant())

    def _save(self):
        _atomic_write(VARIANTS_FILE, {
            "variants": self._variants[-50:],  # keep last 50 variants
            "active_id": self._active_id,
            "saved_at": time.time(),
        })

    @staticmethod
    def _default_variant() -> dict:
        return {
            "id": "default",
            "prompt_addon": "",
            "created_at": 0,
            "score_at_creation": 0.0,
            "rules_applied": [],
        }

    # ── Public API ───────────────────────────────────────────────────────

    def get_current_variant(self) -> dict:
        """Return the active prompt variant."""
        with self._lock:
            for v in self._variants:
                if v["id"] == self._active_id:
                    return dict(v)
            return self._default_variant()

    def propose_variant(self, performance_data: dict) -> dict:
        """
        Phan tich performance_data va tao variant moi.

        Rules:
          - avg score for "comparison" < 6 -> comparison instructions
          - avg score for "itinerary" < 6  -> itinerary formatting
          - tool_usage_rate < 50%          -> tool-use instructions
          - avg_reply_length < 200         -> "provide detailed responses"
          - hallucination_rate > 10%       -> "only use verified data"
        """
        addons = []
        rules_applied = []
        by_cat = performance_data.get("by_category", {})

        # Rule 1: comparison quality
        comp_data = by_cat.get("comparison", {})
        if comp_data.get("count", 0) >= 3 and comp_data.get("avg_score", 10) < 6:
            addons.append(
                "Khi so sanh: PHAI dung tool compare_areas hoac search cho TUNG doi tuong, "
                "trinh bay bang so sanh ro rang voi cac tieu chi cu the (vi tri, gia, diem noi bat)."
            )
            rules_applied.append("comparison_quality")

        # Rule 2: itinerary quality
        itin_data = by_cat.get("itinerary", {})
        if itin_data.get("count", 0) >= 3 and itin_data.get("avg_score", 10) < 6:
            addons.append(
                "Khi lap lich trinh: chia theo buoi (sang/trua/chieu/toi), "
                "ghi ro thoi gian di chuyen, goi y mon an cu the, "
                "dung generate_itinerary tool, kem chi phi uoc tinh."
            )
            rules_applied.append("itinerary_formatting")

        # Rule 3: tool usage rate
        if performance_data.get("tool_usage_rate", 100) < 50:
            addons.append(
                "QUAN TRONG: LUON su dung it nhat 1 tool (search, entity_detail, nearby_entities) "
                "TRUOC khi tra loi. KHONG BAO GIO tra loi tu bo nho ma khong verify bang tool."
            )
            rules_applied.append("strengthen_tool_use")

        # Rule 4: reply length
        if performance_data.get("avg_reply_length", 500) < 200:
            addons.append(
                "Tra loi chi tiet hon: moi cau tra loi nen co it nhat 3-4 doan, "
                "bao gom vi du cu the, dia chi, gio mo cua, va goi y lien quan."
            )
            rules_applied.append("increase_detail")

        # Rule 5: hallucination rate
        if performance_data.get("hallucination_rate", 0) > 10:
            addons.append(
                "CHI su dung thong tin da xac minh qua tool. "
                "Neu khong tim thay du lieu, noi ro 'toi khong co thong tin nay' "
                "thay vi tu dien vao."
            )
            rules_applied.append("reduce_hallucination")

        # Build variant
        variant_id = f"v_{int(time.time())}"
        prompt_addon = "\n".join(addons) if addons else ""

        variant = {
            "id": variant_id,
            "prompt_addon": prompt_addon,
            "created_at": time.time(),
            "score_at_creation": performance_data.get("avg_score", 0),
            "rules_applied": rules_applied,
        }

        with self._lock:
            self._variants.append(variant)
            self._save()

        logger.info(
            "Proposed variant %s with %d rules: %s",
            variant_id, len(rules_applied), rules_applied,
        )
        return variant

    def activate_variant(self, variant_id: str) -> bool:
        """Kich hoat mot variant. Tra ve True neu thanh cong."""
        with self._lock:
            if not any(v["id"] == variant_id for v in self._variants):
                logger.warning("Variant %s not found", variant_id)
                return False
            self._active_id = variant_id
            self._save()
        logger.info("Activated variant %s", variant_id)
        return True

    def rollback(self) -> bool:
        """Quay lai variant truoc do."""
        with self._lock:
            # Find current variant index
            ids = [v["id"] for v in self._variants]
            try:
                idx = ids.index(self._active_id)
            except ValueError:
                idx = len(ids)

            if idx <= 0:
                # Already at earliest, revert to default
                self._active_id = "default"
            else:
                self._active_id = ids[idx - 1]

            self._save()

        logger.info("Rolled back to variant %s", self._active_id)
        return True

    def get_variant_history(self) -> list[dict]:
        """Return all variants (newest first)."""
        with self._lock:
            return list(reversed(self._variants))


# ═════════════════════════════════════════════════════════════════════════════
#  3. ParameterTuner
# ═════════════════════════════════════════════════════════════════════════════

# Bounded ranges
TEMP_MIN, TEMP_MAX = 0.1, 0.8
ROUNDS_MIN, ROUNDS_MAX = 4, 12
TOOL_CALLS_MIN, TOOL_CALLS_MAX = 5, 20

DEFAULT_PARAMS: dict[str, dict] = {
    "general":    {"temperature": 0.5, "max_rounds": 6,  "max_tool_calls": 10},
    "itinerary":  {"temperature": 0.4, "max_rounds": 8,  "max_tool_calls": 15},
    "food":       {"temperature": 0.5, "max_rounds": 6,  "max_tool_calls": 10},
    "history":    {"temperature": 0.3, "max_rounds": 6,  "max_tool_calls": 10},
    "culture":    {"temperature": 0.4, "max_rounds": 6,  "max_tool_calls": 10},
    "comparison": {"temperature": 0.3, "max_rounds": 8,  "max_tool_calls": 15},
}


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


class ParameterTuner:
    """
    Tu dong tinh chinh temperature, max_rounds, max_tool_calls theo category.

    Hoc tu performance data:
      - Category co phuong sai diem cao -> giam temperature (can on dinh hon)
      - Category co tool usage thap      -> tang max_rounds (cho nhieu co hoi goi tool)
    Auto-adjust moi 100 queries.
    """

    def __init__(self):
        self._lock = Lock()
        self._params: dict[str, dict] = {}
        self._queries_since_tune: int = 0
        self._load()

    def _load(self):
        data = _load_json(PARAMS_FILE, default={
            "params": {},
            "queries_since_tune": 0,
        })
        # Merge defaults with saved
        self._params = dict(DEFAULT_PARAMS)
        for cat, saved in data.get("params", {}).items():
            if cat in self._params:
                self._params[cat].update(saved)
            else:
                self._params[cat] = saved
        self._queries_since_tune = data.get("queries_since_tune", 0)

    def _save(self):
        _atomic_write(PARAMS_FILE, {
            "params": self._params,
            "queries_since_tune": self._queries_since_tune,
            "saved_at": time.time(),
        })

    # ── Public API ───────────────────────────────────────────────────────

    def get_optimal_params(self, query_category: str) -> dict:
        """Tra ve tham so toi uu cho category."""
        with self._lock:
            params = self._params.get(query_category, DEFAULT_PARAMS["general"])
            return dict(params)

    def tune(self, performance_data: dict) -> dict[str, dict]:
        """
        Tinh chinh tham so dua tren performance data.

        Returns: updated params dict.
        """
        by_cat = performance_data.get("by_category", {})
        adjustments = {}

        with self._lock:
            for cat, cat_data in by_cat.items():
                if cat_data.get("count", 0) < 5:
                    continue  # not enough data

                current = self._params.get(cat, dict(DEFAULT_PARAMS.get(cat, DEFAULT_PARAMS["general"])))
                new_params = dict(current)

                # High variance -> lower temperature for more consistency
                score_std = cat_data.get("score_std", 0)
                if score_std > 2.5:
                    new_params["temperature"] = _clamp(
                        current["temperature"] - 0.05, TEMP_MIN, TEMP_MAX,
                    )
                elif score_std < 1.0 and cat_data.get("avg_score", 0) > 7:
                    # Low variance + high quality -> can afford slightly higher temp
                    new_params["temperature"] = _clamp(
                        current["temperature"] + 0.02, TEMP_MIN, TEMP_MAX,
                    )

                # Low avg score -> increase max_rounds for deeper reasoning
                if cat_data.get("avg_score", 10) < 6:
                    new_params["max_rounds"] = _clamp(
                        current["max_rounds"] + 1, ROUNDS_MIN, ROUNDS_MAX,
                    )

                # Check tool usage from records (need collector data)
                # If category has low tool usage, increase max_tool_calls
                # This is detected indirectly: low score + general category
                # tends to mean tools weren't used enough
                if cat_data.get("avg_score", 10) < 5:
                    new_params["max_tool_calls"] = _clamp(
                        current["max_tool_calls"] + 2, TOOL_CALLS_MIN, TOOL_CALLS_MAX,
                    )

                # Round floats
                new_params["temperature"] = round(new_params["temperature"], 2)
                new_params["max_rounds"] = int(new_params["max_rounds"])
                new_params["max_tool_calls"] = int(new_params["max_tool_calls"])

                if new_params != current:
                    adjustments[cat] = new_params
                    self._params[cat] = new_params

            self._queries_since_tune = 0
            self._save()

        if adjustments:
            logger.info("Parameter tuning adjustments: %s", adjustments)
        return adjustments

    def increment_query_count(self) -> bool:
        """Increment and return True if tune threshold reached (100 queries)."""
        with self._lock:
            self._queries_since_tune += 1
            should = self._queries_since_tune >= 100
        return should

    def get_all_params(self) -> dict[str, dict]:
        """Return all category params."""
        with self._lock:
            return {cat: dict(p) for cat, p in self._params.items()}


# ═════════════════════════════════════════════════════════════════════════════
#  4. ToolWeightOptimizer
# ═════════════════════════════════════════════════════════════════════════════


class ToolWeightOptimizer:
    """
    Danh gia hieu qua cua tung tool va goi y thu tu su dung.

    Tinh diem: trung binh quality_score cua cac phien co dung tool do
    so voi cac phien khong dung no.
    """

    # All known tools in the system
    ALL_TOOLS = [
        "search", "entity_detail", "nearby_entities", "compare_areas",
        "seasonal_now", "generate_itinerary", "suggest_followups",
        "web_search", "image_search",
    ]

    def __init__(self):
        self._lock = Lock()
        self._tool_data: dict = {}
        self._load()

    def _load(self):
        self._tool_data = _load_json(TOOL_SCORES_FILE, default={
            "scores": {},
            "usage_log": {},
        })

    def _save(self):
        _atomic_write(TOOL_SCORES_FILE, self._tool_data)

    # ── Public API ───────────────────────────────────────────────────────

    def update_scores(self, records: list[dict]) -> None:
        """Recalculate tool effectiveness from recent records."""
        if not records:
            return

        # Baseline: avg score when no tools used
        no_tool_records = [r for r in records if not r.get("tools_used")]
        baseline = statistics.mean(
            [r["quality_score"] for r in no_tool_records]
        ) if no_tool_records else 5.0

        # Per-tool: avg score when tool was used
        tool_scores: dict[str, list[float]] = defaultdict(list)
        tool_last_used: dict[str, float] = {}

        for r in records:
            for tool in r.get("tools_used", []):
                tool_scores[tool].append(r["quality_score"])
                ts = r.get("timestamp", 0)
                if ts > tool_last_used.get(tool, 0):
                    tool_last_used[tool] = ts

        scores = {}
        for tool in self.ALL_TOOLS:
            if tool in tool_scores:
                avg = statistics.mean(tool_scores[tool])
                # Effectiveness = (avg_with_tool - baseline) / baseline * 100
                # Positive = tool helps, negative = tool hurts
                effectiveness = round((avg - baseline) / max(baseline, 0.1) * 100, 1)
                scores[tool] = {
                    "avg_quality": round(avg, 2),
                    "usage_count": len(tool_scores[tool]),
                    "effectiveness": effectiveness,
                    "last_used": tool_last_used.get(tool, 0),
                }
            else:
                # Keep old data if available
                old = self._tool_data.get("scores", {}).get(tool)
                if old:
                    scores[tool] = old
                else:
                    scores[tool] = {
                        "avg_quality": 0,
                        "usage_count": 0,
                        "effectiveness": 0,
                        "last_used": 0,
                    }

        with self._lock:
            self._tool_data["scores"] = scores
            self._tool_data["baseline"] = round(baseline, 2)
            self._tool_data["updated_at"] = time.time()
            self._save()

    def get_tool_scores(self) -> dict[str, float]:
        """Tra ve effectiveness score cho moi tool."""
        with self._lock:
            scores = self._tool_data.get("scores", {})
        return {
            tool: data.get("effectiveness", 0)
            for tool, data in scores.items()
        }

    def suggest_tool_order(self, query_category: str) -> list[str]:
        """
        Goi y thu tu tool theo category va effectiveness.

        Uu tien: tools hay dung cho category do + effectiveness cao.
        """
        # Category-specific primary tools
        category_tools: dict[str, list[str]] = {
            "itinerary": ["seasonal_now", "generate_itinerary", "search", "suggest_followups"],
            "comparison": ["compare_areas", "search", "entity_detail"],
            "food": ["search", "entity_detail", "nearby_entities"],
            "history": ["search", "entity_detail", "web_search"],
            "culture": ["search", "entity_detail", "web_search"],
            "general": ["search", "entity_detail", "nearby_entities", "suggest_followups"],
        }

        primary = category_tools.get(query_category, category_tools["general"])

        # Sort remaining tools by effectiveness
        scores = self.get_tool_scores()
        remaining = [t for t in self.ALL_TOOLS if t not in primary]
        remaining.sort(key=lambda t: scores.get(t, 0), reverse=True)

        return primary + remaining

    def get_unused_tools(self, window_hours: float = 168) -> list[str]:
        """Tools khong duoc goi trong 7 ngay (default)."""
        cutoff = time.time() - window_hours * 3600
        unused = []
        with self._lock:
            scores = self._tool_data.get("scores", {})
        for tool in self.ALL_TOOLS:
            data = scores.get(tool, {})
            last_used = data.get("last_used", 0)
            if last_used < cutoff:
                unused.append(tool)
        return unused

    def get_detailed_scores(self) -> dict:
        """Full tool data for reporting."""
        with self._lock:
            return dict(self._tool_data)


# ═════════════════════════════════════════════════════════════════════════════
#  5. OptimizationReport
# ═════════════════════════════════════════════════════════════════════════════


@dataclass
class OptimizationReport:
    """Bao cao toi uu hoa tong hop."""

    current_variant: dict = field(default_factory=dict)
    param_recommendations: dict = field(default_factory=dict)
    tool_effectiveness: dict = field(default_factory=dict)
    quality_trend: dict = field(default_factory=dict)
    action_items: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# ═════════════════════════════════════════════════════════════════════════════
#  6. Convenience functions & module singletons
# ═════════════════════════════════════════════════════════════════════════════

# Singletons
performance_collector = PerformanceCollector()
prompt_optimizer = PromptOptimizer()
parameter_tuner = ParameterTuner()
tool_weight_optimizer = ToolWeightOptimizer()

# Track optimization state
_last_optimization_count: int = performance_collector.total_count
_optimization_lock = Lock()


def record_outcome(
    session_id: str,
    query: str,
    agent_name: str,
    tools_used: list[str],
    score: float,
    duration: float,
    tokens: int,
) -> None:
    """Ghi nhan ket qua va kiem tra xem can toi uu hoa chua."""
    performance_collector.record(
        session_id=session_id,
        query=query,
        agent_name=agent_name,
        tools_used=tools_used,
        quality_score=score,
        duration=duration,
        token_count=tokens,
    )

    # Check if we need to tune parameters
    if parameter_tuner.increment_query_count():
        _run_optimization()


def should_optimize() -> bool:
    """True neu co 100+ ban ghi moi tu lan toi uu hoa cuoi."""
    global _last_optimization_count
    with _optimization_lock:
        current = performance_collector.total_count
        return (current - _last_optimization_count) >= 100


def _run_optimization() -> None:
    """Execute a full optimization pass."""
    global _last_optimization_count

    logger.info("Running optimization pass...")

    stats = performance_collector.get_stats(window_hours=72)  # 3-day window
    if stats["total_records"] < 10:
        logger.info("Not enough data for optimization (%d records)", stats["total_records"])
        return

    # 1. Propose new prompt variant
    variant = prompt_optimizer.propose_variant(stats)
    if variant["rules_applied"]:
        prompt_optimizer.activate_variant(variant["id"])

    # 2. Tune parameters
    parameter_tuner.tune(stats)

    # 3. Update tool scores
    records = performance_collector.get_records(window_hours=72)
    tool_weight_optimizer.update_scores(records)

    with _optimization_lock:
        _last_optimization_count = performance_collector.total_count

    logger.info("Optimization pass complete")


def _compute_quality_trend(stats_24h: dict, stats_72h: dict) -> dict:
    """Compare recent vs older performance."""
    trend = {
        "last_24h_avg": stats_24h.get("avg_score", 0),
        "last_72h_avg": stats_72h.get("avg_score", 0),
        "direction": "stable",
        "delta": 0.0,
    }
    if stats_72h.get("avg_score", 0) > 0:
        delta = stats_24h.get("avg_score", 0) - stats_72h.get("avg_score", 0)
        trend["delta"] = round(delta, 2)
        if delta > 0.3:
            trend["direction"] = "improving"
        elif delta < -0.3:
            trend["direction"] = "declining"

    # Per-category trends
    cat_trends = {}
    for cat in QUERY_CATEGORIES:
        recent = stats_24h.get("by_category", {}).get(cat, {})
        older = stats_72h.get("by_category", {}).get(cat, {})
        if recent.get("count", 0) > 0 and older.get("count", 0) > 0:
            cat_delta = recent["avg_score"] - older["avg_score"]
            cat_trends[cat] = {
                "recent_score": recent["avg_score"],
                "older_score": older["avg_score"],
                "delta": round(cat_delta, 2),
                "direction": "improving" if cat_delta > 0.3 else "declining" if cat_delta < -0.3 else "stable",
            }
    trend["by_category"] = cat_trends
    return trend


def _build_action_items(stats: dict, tool_scores: dict, unused_tools: list[str]) -> list[str]:
    """Generate human-readable action items."""
    items = []

    if stats.get("avg_score", 10) < 6:
        items.append("CRITICAL: Overall quality score below 6.0 — review prompt and tool usage")

    by_cat = stats.get("by_category", {})
    for cat, data in by_cat.items():
        if data.get("count", 0) >= 5 and data.get("avg_score", 10) < 5:
            items.append(f"Category '{cat}' has very low score ({data['avg_score']}) — needs targeted improvement")

    if stats.get("tool_usage_rate", 100) < 40:
        items.append("Tool usage rate is critically low — agent may be hallucinating")

    if stats.get("hallucination_rate", 0) > 20:
        items.append(f"High hallucination rate ({stats['hallucination_rate']}%) — strengthen grounding instructions")

    if unused_tools:
        items.append(f"Unused tools in last 7 days: {', '.join(unused_tools)}")

    # Tool effectiveness warnings
    for tool, eff in tool_scores.items():
        if eff < -10:
            items.append(f"Tool '{tool}' has negative effectiveness ({eff}%) — investigate")

    return items


def get_optimization_report() -> dict:
    """Full optimization report cho /system/optimizer endpoint."""
    stats_24h = performance_collector.get_stats(window_hours=24)
    stats_72h = performance_collector.get_stats(window_hours=72)

    tool_scores = tool_weight_optimizer.get_tool_scores()
    unused_tools = tool_weight_optimizer.get_unused_tools()

    quality_trend = _compute_quality_trend(stats_24h, stats_72h)
    action_items = _build_action_items(stats_72h, tool_scores, unused_tools)

    report = OptimizationReport(
        current_variant=prompt_optimizer.get_current_variant(),
        param_recommendations=parameter_tuner.get_all_params(),
        tool_effectiveness=tool_weight_optimizer.get_detailed_scores(),
        quality_trend=quality_trend,
        action_items=action_items,
    )
    return report.to_dict()
