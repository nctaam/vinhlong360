"""
vinhlong360 -- LLM-based Quality Evaluation Module.

Thay the rule-based reflexion scoring bang LLM Judge:
  1. JudgeCriteria -- dinh nghia tieu chi danh gia (weight + prompt)
  2. LLMJudge      -- goi LLM de cham diem, fallback rule-based
  3. JudgeResult   -- ket qua danh gia (scores, weighted, feedback)
  4. RuleBasedFallback -- scoring khi LLM khong kha dung
  5. JudgeAnalytics -- phan tich xu huong, diem yeu, goi y cai thien

Criteria mac dinh:
  Relevance (0.3), Accuracy (0.25), Completeness (0.2),
  Helpfulness (0.15), Format (0.1)

Rate limit: 10 judge calls/phut (token bucket).
Cache: agent/data/judge/evaluations.json (toi da 5000 records).
Persistence: atomic write (.tmp roi rename).
Thread-safe: moi state mutation qua threading.Lock.
"""

import json
import logging
import os
import re
import time
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from threading import Lock

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).resolve().parent / "data" / "judge"
DATA_DIR.mkdir(parents=True, exist_ok=True)
EVALUATIONS_FILE = DATA_DIR / "evaluations.json"

MAX_CACHE = 5000

# ---------------------------------------------------------------------------
# LLM config
# ---------------------------------------------------------------------------

_LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
_LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "")  # P1-3: KHÔNG hardcode tunnel URL chết
_LLM_MODEL_DEFAULT = os.environ.get("LLM_MODEL_MINI", "cx/gpt-5.4-mini")

# ---------------------------------------------------------------------------
# Atomic write helper
# ---------------------------------------------------------------------------


def _atomic_write(path: Path, data) -> None:
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
        default = []
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("Failed to load %s: %s", path, e)
    return default


# ============================================================================
#  JudgeCriteria
# ============================================================================


@dataclass
class JudgeCriteria:
    """Single evaluation criterion with weight and prompt template."""

    name: str
    weight: float
    prompt_template: str
    scale: tuple = (1, 10)


DEFAULT_CRITERIA: list[JudgeCriteria] = [
    JudgeCriteria(
        name="relevance",
        weight=0.3,
        prompt_template="Does the reply directly answer the query about Vinh Long tourism?",
        scale=(1, 10),
    ),
    JudgeCriteria(
        name="accuracy",
        weight=0.25,
        prompt_template="Are all facts, place names, and descriptions accurate?",
        scale=(1, 10),
    ),
    JudgeCriteria(
        name="completeness",
        weight=0.2,
        prompt_template="Does the reply cover all aspects the user asked about?",
        scale=(1, 10),
    ),
    JudgeCriteria(
        name="helpfulness",
        weight=0.15,
        prompt_template="Would a tourist find this reply useful for planning?",
        scale=(1, 10),
    ),
    JudgeCriteria(
        name="format",
        weight=0.1,
        prompt_template="Is the reply well-structured with clear formatting?",
        scale=(1, 10),
    ),
]


# ============================================================================
#  JudgeResult
# ============================================================================


@dataclass
class JudgeResult:
    """Outcome of a single quality evaluation."""

    query: str
    reply_preview: str          # first 100 chars of reply
    scores: dict                # {criterion_name: float}
    weighted_score: float
    feedback: str               # LLM-generated improvement suggestion
    timestamp: float
    is_llm_judged: bool         # True = LLM scored, False = rule-based fallback

    def to_dict(self) -> dict:
        return asdict(self)


# ============================================================================
#  RuleBasedFallback
# ============================================================================


class RuleBasedFallback:
    """Heuristic scoring when the LLM judge is unavailable.

    Returns the same dict structure as LLM judge for drop-in compatibility.
    """

    def score(self, query: str, reply: str) -> dict:
        """Return {relevance, accuracy, completeness, helpfulness, format, feedback}."""

        scores: dict[str, float] = {}
        reply_lower = reply.lower()
        rlen = len(reply)

        # -- Relevance: keyword overlap between query and reply ---------------
        scores["relevance"] = self._score_relevance(query, reply_lower)

        # -- Accuracy: assume neutral (no factual verification possible) ------
        scores["accuracy"] = 5.0

        # -- Completeness: based on reply length adequacy ---------------------
        scores["completeness"] = self._score_completeness(rlen)

        # -- Helpfulness: combination of length + practical keywords ----------
        scores["helpfulness"] = self._score_helpfulness(reply_lower, rlen)

        # -- Format: markdown, bullet lists, proper sentences -----------------
        scores["format"] = self._score_format(reply)

        # -- Feedback ---------------------------------------------------------
        scores["feedback"] = self._build_feedback(scores)
        return scores

    @staticmethod
    def _score_relevance(query: str, reply_lower: str) -> float:
        """Relevance from keyword overlap between query and reply."""
        query_words = set(w for w in query.lower().split() if len(w) > 2)
        if query_words:
            matched = sum(1 for w in query_words if w in reply_lower)
            ratio = matched / len(query_words)
        else:
            ratio = 0.5
        return max(1, min(10, round(ratio * 10, 1)))

    @staticmethod
    def _score_completeness(rlen: int) -> float:
        """Completeness from reply length adequacy."""
        if rlen < 50:
            return 2.0
        if rlen < 100:
            return 4.0
        if rlen < 300:
            return 6.0
        if rlen < 800:
            return 8.0
        return 9.0

    @staticmethod
    def _score_helpfulness(reply_lower: str, rlen: int) -> float:
        """Helpfulness from length plus practical-keyword hits."""
        practical_kw = [
            "gia", "gio", "dia chi", "cach", "nen", "goi y",
            "luu y", "kinh nghiem", "meo", "chi phi",
        ]
        practical_hits = sum(1 for kw in practical_kw if kw in reply_lower)
        base_helpful = min(10, 4 + practical_hits * 0.8)
        if rlen > 200:
            base_helpful += 1
        return max(1, min(10, round(base_helpful, 1)))

    @staticmethod
    def _score_format(reply: str) -> float:
        """Format from markdown, bullet lists, proper sentences."""
        fmt_score = 4.0
        if "**" in reply or "##" in reply:
            fmt_score += 2.0
        if reply.count("- ") >= 3 or reply.count("* ") >= 3:
            fmt_score += 1.5
        if reply.count("\n") >= 3:
            fmt_score += 1.0
        if reply.endswith(".") or reply.endswith("!") or reply.endswith("?"):
            fmt_score += 0.5
        return max(1, min(10, round(fmt_score, 1)))

    @staticmethod
    def _build_feedback(scores: dict) -> str:
        """Compose feedback string from low-scoring criteria."""
        issues = []
        if scores["relevance"] < 5:
            issues.append("Reply may not address the query directly.")
        if scores["completeness"] < 5:
            issues.append("Reply is too short; consider adding more detail.")
        if scores["format"] < 5:
            issues.append("Consider using markdown formatting for clarity.")
        return " ".join(issues) if issues else "Acceptable quality (rule-based estimate)."


# ============================================================================
#  Token Bucket Rate Limiter
# ============================================================================


class _TokenBucket:
    """Simple token bucket: max_tokens refill per interval_sec."""

    def __init__(self, max_tokens: int = 10, interval_sec: float = 60.0):
        self._max = max_tokens
        self._interval = interval_sec
        self._tokens = float(max_tokens)
        self._last_refill = time.monotonic()
        self._lock = Lock()

    def acquire(self) -> bool:
        """Try to acquire one token.  Return True if allowed."""
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill
            self._tokens = min(
                self._max, self._tokens + elapsed * (self._max / self._interval)
            )
            self._last_refill = now
            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return True
            return False


# ============================================================================
#  LLMJudge
# ============================================================================


class LLMJudge:
    """LLM-based quality evaluator with rate limiting and caching.

    Calls the LLM to score a (query, reply) pair against multiple criteria.
    Falls back to RuleBasedFallback when the LLM is unreachable or rate-limited.
    """

    def __init__(self, criteria: list[JudgeCriteria] | None = None,
                 model: str | None = None):
        self._criteria = criteria or DEFAULT_CRITERIA
        self._model = model or _LLM_MODEL_DEFAULT
        self._fallback = RuleBasedFallback()
        self._bucket = _TokenBucket(max_tokens=10, interval_sec=60.0)
        self._lock = Lock()
        self._cache: list[dict] = _load_json(EVALUATIONS_FILE, default=[])

    # -- OpenAI client (lazy init to avoid import error when key missing) -----

    def _get_client(self):
        from openai import OpenAI
        return OpenAI(
            api_key=os.environ.get("LLM_API_KEY", _LLM_API_KEY),
            base_url=os.environ.get("LLM_BASE_URL", _LLM_BASE_URL),
            timeout=20,  # P1-2: tránh treo nếu judge LLM chậm
        )

    def _can_use_llm(self) -> bool:
        api_key = os.environ.get("LLM_API_KEY", _LLM_API_KEY)
        if not api_key or api_key.startswith("test"):
            return False
        if not os.environ.get("LLM_BASE_URL", _LLM_BASE_URL):
            return False  # P1-3: không có base_url thật → không gọi (tránh host lạ)
        if os.environ.get("ENVIRONMENT", "").lower() == "test":
            return False
        return True

    # -- Evaluation prompt ----------------------------------------------------

    def _build_prompt(self, query: str, reply: str,
                      context: dict | None = None) -> str:
        criteria_lines = []
        for c in self._criteria:
            criteria_lines.append(
                f"- {c.name} ({c.scale[0]}-{c.scale[1]}): {c.prompt_template}"
            )
        criteria_block = "\n".join(criteria_lines)

        context_block = ""
        if context:
            context_block = (
                "\n\nAdditional context about the conversation:\n"
                + json.dumps(context, ensure_ascii=False, default=str)
            )

        return (
            "You are a strict quality evaluator for a Vietnamese tourism chatbot "
            "about Vinh Long province.\n\n"
            f"USER QUERY:\n{query}\n\n"
            f"CHATBOT REPLY:\n{reply}\n"
            f"{context_block}\n\n"
            "Score the reply on each criterion below (integer 1-10).\n"
            f"{criteria_block}\n\n"
            "Also provide a brief 'feedback' string: one concrete suggestion "
            "to improve the reply.\n\n"
            "Respond ONLY with valid JSON (no markdown fences):\n"
            '{"relevance": <int>, "accuracy": <int>, "completeness": <int>, '
            '"helpfulness": <int>, "format": <int>, "feedback": "<string>"}'
        )

    # -- Parse LLM response ---------------------------------------------------

    def _parse_scores(self, raw: str) -> dict | None:
        """Extract JSON from LLM response, tolerating markdown fences."""
        text = raw.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # Try to find JSON object in the text
            match = re.search(r"\{[^{}]+\}", text, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group())
                except json.JSONDecodeError:
                    return None
            else:
                return None

        # Validate expected keys
        expected = {c.name for c in self._criteria}
        for key in expected:
            if key not in data:
                return None
            val = data[key]
            if isinstance(val, (int, float)):
                data[key] = max(1, min(10, float(val)))
            else:
                return None
        # feedback is optional in parse; fill empty if missing
        if "feedback" not in data or not isinstance(data["feedback"], str):
            data["feedback"] = ""
        return data

    # -- Calculate weighted score ---------------------------------------------

    def _weighted_score(self, scores: dict) -> float:
        total = 0.0
        for c in self._criteria:
            total += scores.get(c.name, 5.0) * c.weight
        return round(total, 2)

    # -- Core evaluate --------------------------------------------------------

    def evaluate(self, query: str, reply: str,
                 context: dict | None = None) -> JudgeResult:
        """Evaluate a (query, reply) pair.

        Tries LLM-based scoring first.  Falls back to rule-based if:
          - Rate limit exceeded
          - API key missing
          - LLM call fails or returns unparseable response
        """
        is_llm = False
        scores: dict | None = None
        feedback = ""

        # Attempt LLM judge if API key is available and rate limit allows
        if self._can_use_llm() and self._bucket.acquire():
            try:
                client = self._get_client()
                prompt = self._build_prompt(query, reply, context)
                response = client.chat.completions.create(
                    model=self._model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=300,
                    timeout=20,  # P0-6: explicit per-call timeout (matches client-level)
                )
                raw = response.choices[0].message.content or ""
                parsed = self._parse_scores(raw)
                if parsed is not None:
                    feedback = parsed.pop("feedback", "")
                    scores = {c.name: parsed[c.name] for c in self._criteria}
                    is_llm = True
                else:
                    logger.warning("LLM judge returned unparseable response")
            except Exception as e:
                logger.warning("LLM judge call failed: %s", e)

        # Fallback to rule-based
        if scores is None:
            fb = self._fallback.score(query, reply)
            feedback = fb.pop("feedback", "")
            scores = {c.name: fb.get(c.name, 5.0) for c in self._criteria}

        ws = self._weighted_score(scores)
        result = JudgeResult(
            query=query,
            reply_preview=reply[:100],
            scores=scores,
            weighted_score=ws,
            feedback=feedback,
            timestamp=time.time(),
            is_llm_judged=is_llm,
        )

        # Cache
        self._cache_result(result)
        return result

    # -- Batch evaluate -------------------------------------------------------

    def evaluate_batch(self, items: list[dict]) -> list[JudgeResult]:
        """Evaluate multiple (query, reply) pairs.

        Each item: {"query": str, "reply": str, "context": dict | None}
        """
        results = []
        for item in items:
            r = self.evaluate(
                query=item["query"],
                reply=item["reply"],
                context=item.get("context"),
            )
            results.append(r)
        return results

    # -- Pairwise comparison --------------------------------------------------

    def compare(self, query: str, reply_a: str, reply_b: str) -> dict:
        """Compare two replies for the same query.

        Returns {"winner": "a"|"b"|"tie", "score_a": float, "score_b": float,
                 "details_a": dict, "details_b": dict}
        """
        result_a = self.evaluate(query, reply_a)
        result_b = self.evaluate(query, reply_b)

        if abs(result_a.weighted_score - result_b.weighted_score) < 0.3:
            winner = "tie"
        elif result_a.weighted_score > result_b.weighted_score:
            winner = "a"
        else:
            winner = "b"

        return {
            "winner": winner,
            "score_a": result_a.weighted_score,
            "score_b": result_b.weighted_score,
            "details_a": result_a.to_dict(),
            "details_b": result_b.to_dict(),
        }

    # -- Cache management -----------------------------------------------------

    def _cache_result(self, result: JudgeResult) -> None:
        with self._lock:
            self._cache.append(result.to_dict())
            if len(self._cache) > MAX_CACHE:
                self._cache = self._cache[-MAX_CACHE:]
            self._save()

    def _save(self) -> None:
        _atomic_write(EVALUATIONS_FILE, self._cache)

    def get_cache(self) -> list[dict]:
        with self._lock:
            return list(self._cache)


# ============================================================================
#  JudgeAnalytics
# ============================================================================


class JudgeAnalytics:
    """Analytics over cached judge evaluations."""

    def __init__(self, judge: LLMJudge):
        self._judge = judge

    def _get_evals(self) -> list[dict]:
        return self._judge.get_cache()

    # -- Daily average scores -------------------------------------------------

    def get_quality_trend(self, days: int = 7) -> list[dict]:
        """Return daily average weighted scores for the last *days* days."""
        cutoff = time.time() - days * 86400
        evals = self._get_evals()

        daily: dict[str, list[float]] = defaultdict(list)
        for e in evals:
            ts = e.get("timestamp", 0)
            if ts < cutoff:
                continue
            day = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
            daily[day].append(e.get("weighted_score", 0))

        trend = []
        for day in sorted(daily):
            vals = daily[day]
            trend.append({
                "date": day,
                "avg_score": round(sum(vals) / len(vals), 2),
                "count": len(vals),
            })
        return trend

    # -- Worst queries --------------------------------------------------------

    def get_worst_queries(self, limit: int = 10) -> list[dict]:
        """Return the lowest-scored queries for targeted improvement."""
        evals = self._get_evals()
        sorted_evals = sorted(evals, key=lambda e: e.get("weighted_score", 10))
        results = []
        for e in sorted_evals[:limit]:
            results.append({
                "query": e.get("query", ""),
                "reply_preview": e.get("reply_preview", ""),
                "weighted_score": e.get("weighted_score", 0),
                "feedback": e.get("feedback", ""),
                "is_llm_judged": e.get("is_llm_judged", False),
                "timestamp": e.get("timestamp", 0),
            })
        return results

    # -- Criteria breakdown ---------------------------------------------------

    def get_criteria_breakdown(self) -> dict:
        """Return average score per criterion across all evaluations."""
        evals = self._get_evals()
        if not evals:
            return {}

        totals: dict[str, list[float]] = defaultdict(list)
        for e in evals:
            scores = e.get("scores", {})
            for crit, val in scores.items():
                if isinstance(val, (int, float)):
                    totals[crit].append(val)

        breakdown = {}
        for crit, vals in totals.items():
            breakdown[crit] = {
                "avg": round(sum(vals) / len(vals), 2),
                "min": round(min(vals), 2),
                "max": round(max(vals), 2),
                "count": len(vals),
            }
        return breakdown

    # -- Improvement suggestions from LLM feedback ----------------------------

    def get_improvement_suggestions(self) -> list[str]:
        """Extract unique improvement suggestions from LLM feedback.

        Groups similar feedback, returns most common patterns.
        """
        evals = self._get_evals()
        feedback_counts: dict[str, int] = defaultdict(int)
        for e in evals:
            fb = e.get("feedback", "").strip()
            if fb and fb != "Acceptable quality (rule-based estimate).":
                # Normalize to first sentence for grouping
                first_sentence = fb.split(".")[0].strip()
                if first_sentence:
                    feedback_counts[first_sentence] += 1

        # Sort by frequency and return top suggestions
        sorted_fb = sorted(feedback_counts.items(), key=lambda x: -x[1])
        return [fb for fb, _ in sorted_fb[:20]]


# ============================================================================
#  Convenience functions
# ============================================================================

# Module singletons
llm_judge = LLMJudge()
judge_analytics = JudgeAnalytics(llm_judge)


def judge(query: str, reply: str, context: dict | None = None) -> dict:
    """Quick evaluate, return dict."""
    result = llm_judge.evaluate(query, reply, context)
    return result.to_dict()


def get_judge_report() -> dict:
    """Full report for /system/judge endpoint."""
    cache = llm_judge.get_cache()
    total = len(cache)
    llm_count = sum(1 for e in cache if e.get("is_llm_judged"))
    rule_count = total - llm_count

    if total > 0:
        avg_score = round(
            sum(e.get("weighted_score", 0) for e in cache) / total, 2
        )
    else:
        avg_score = 0.0

    return {
        "total_evaluations": total,
        "llm_judged": llm_count,
        "rule_based": rule_count,
        "avg_weighted_score": avg_score,
        "quality_trend": judge_analytics.get_quality_trend(),
        "worst_queries": judge_analytics.get_worst_queries(),
        "criteria_breakdown": judge_analytics.get_criteria_breakdown(),
        "improvement_suggestions": judge_analytics.get_improvement_suggestions(),
    }
