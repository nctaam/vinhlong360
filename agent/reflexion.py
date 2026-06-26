"""
vinhlong360 — Reflexion & Self-Improvement Engine.

Kiến trúc Reflexion (ICLR 2026):
  1. Agent trả lời câu hỏi
  2. Evaluator đánh giá chất lượng
  3. Nếu chất lượng thấp → Agent tự phản ánh lỗi
  4. Reflection được lưu vào episodic memory
  5. Lần sau gặp câu hỏi tương tự → dùng reflection để tránh lỗi cũ

Kết hợp với Skill Documents:
  - Câu trả lời tốt → tạo skill document (pattern thành công)
  - Câu trả lời kém → tạo reflection (pattern cần tránh)

Tham khảo: Reflexion đạt 91% pass@1 trên HumanEval (vs 80% GPT-4).
"""

import json
import logging
import os
import re
import time
from datetime import datetime
from pathlib import Path
from threading import Lock

logger = logging.getLogger(__name__)

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

REFLEXION_DIR = Path(__file__).resolve().parent / "data" / "memory"
REFLEXION_DIR.mkdir(parents=True, exist_ok=True)


class ReflexionEngine:
    """
    Self-evaluation & improvement engine.

    Evaluator pipeline:
      1. answer_quality_check() — Đánh giá câu trả lời (0-10)
      2. reflect_on_failure() — Tạo reflection cho câu trả lời kém
      3. create_skill_doc() — Tạo skill document cho câu trả lời tốt
      4. get_reflections() — Lấy reflections liên quan khi trả lời
    """

    def __init__(self):
        self._reflections_file = REFLEXION_DIR / "reflections.json"
        self._reflections: list[dict] = []
        self._lock = Lock()
        self._load()

    def _load(self):
        try:
            if self._reflections_file.exists():
                self._reflections = json.loads(
                    self._reflections_file.read_text(encoding="utf-8")
                )
        except Exception as exc:
            logger.warning("Failed to load reflections: %s", exc)
            self._reflections = []

    def _save(self):
        try:
            tmp = self._reflections_file.with_suffix(".tmp")
            tmp.write_text(
                json.dumps(self._reflections[-500:], ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            tmp.replace(self._reflections_file)
        except Exception as e:
            logger.warning("Failed to save reflections: %s", e)

    # ── Evaluation ──

    def evaluate_answer(self, query: str, answer: str, tools_used: list[str]) -> dict:
        """
        Đánh giá chất lượng câu trả lời bằng heuristics.
        Trả về {score: 0-10, issues: [str], good_points: [str]}.

        Dùng rule-based để tránh tốn LLM call.
        LLM-based evaluation dành cho batch review (chạy offline).
        """
        score = 5.0  # Baseline
        issues = []
        good_points = []

        # 1. Độ dài — quá ngắn hoặc quá dài
        answer_len = len(answer)
        if answer_len < 50:
            score -= 2
            issues.append("Câu trả lời quá ngắn")
        elif answer_len < 100:
            score -= 1
            issues.append("Câu trả lời hơi ngắn")
        elif answer_len > 200:
            score += 1
            good_points.append("Câu trả lời đầy đủ")
        if answer_len > 2000:
            score -= 0.5
            issues.append("Câu trả lời có thể quá dài")

        # 2. Tool usage — đã dùng tools hay chỉ đoán?
        if not tools_used:
            score -= 2
            issues.append("Không dùng tools tra cứu — có thể đoán")
        elif len(tools_used) >= 2:
            score += 1
            good_points.append("Dùng nhiều tools tra cứu")
        if "search" in tools_used or "entity_detail" in tools_used:
            score += 0.5
            good_points.append("Tra cứu knowledge base")
        if "web_search" in tools_used and "search" in tools_used:
            score += 0.5
            good_points.append("Kết hợp KB + web search")
        if "suggest_followups" in tools_used:
            score += 0.5
            good_points.append("Có gợi ý tiếp theo")

        # 3. Content quality signals
        if "xin lỗi" in answer.lower() and "không" in answer.lower():
            score -= 1.5
            issues.append("Agent xin lỗi không trả lời được")
        if "**" in answer:  # Markdown formatting
            score += 0.5
            good_points.append("Có định dạng markdown")
        if answer.count("- ") >= 3 or answer.count("• ") >= 3:
            score += 0.5
            good_points.append("Có cấu trúc danh sách")

        # 4. Vietnamese language quality
        vietnamese_chars = sum(1 for c in answer if ord(c) > 127)
        if vietnamese_chars / max(len(answer), 1) < 0.05:
            score -= 1
            issues.append("Ít ký tự tiếng Việt — có thể trả lời bằng tiếng Anh")

        # 5. Relevance check — query keywords in answer
        query_words = set(query.lower().split())
        answer_lower = answer.lower()
        matched = sum(1 for w in query_words if len(w) > 2 and w in answer_lower)
        relevance = matched / max(len(query_words), 1)
        if relevance < 0.2:
            score -= 1
            issues.append("Câu trả lời có thể không liên quan đến câu hỏi")
        elif relevance > 0.5:
            score += 0.5
            good_points.append("Câu trả lời liên quan tốt")

        # 6. Error patterns
        error_patterns = [
            "lỗi", "error", "exception", "timeout",
            "không kết nối", "thử lại",
        ]
        if any(p in answer.lower() for p in error_patterns):
            score -= 1.5
            issues.append("Có dấu hiệu lỗi trong câu trả lời")

        score = max(0, min(10, score))

        return {
            "score": round(score, 1),
            "issues": issues,
            "good_points": good_points,
            "tools_used": tools_used,
        }

    # ── Reflection ──

    def reflect_on_failure(self, query: str, answer: str, evaluation: dict):
        """
        Tạo reflection khi câu trả lời kém (score < 5).
        Reflection = bài học kinh nghiệm để tránh lỗi tương lai.
        """
        if evaluation["score"] >= 5:
            return  # Không cần reflection

        reflection = {
            "query": query[:200],
            "score": evaluation["score"],
            "issues": evaluation["issues"],
            "lesson": self._generate_lesson(query, evaluation),
            "created": datetime.now().isoformat(),
            "category": self._categorize_query(query),
        }

        with self._lock:
            self._reflections.append(reflection)
            if len(self._reflections) > 500:
                self._reflections = self._reflections[-500:]
            self._save()

        return reflection

    def _generate_lesson(self, query: str, evaluation: dict) -> str:
        """Tạo bài học từ failure."""
        lessons = []

        for issue in evaluation["issues"]:
            if "quá ngắn" in issue:
                lessons.append("Cần trả lời chi tiết hơn với ví dụ cụ thể")
            elif "không dùng tools" in issue:
                lessons.append("PHẢI dùng search/entity_detail trước khi trả lời")
            elif "xin lỗi" in issue:
                lessons.append("Thử web_search khi knowledge base không đủ thông tin")
            elif "không liên quan" in issue:
                lessons.append("Đọc kỹ câu hỏi, trả lời đúng chủ đề")
            elif "lỗi" in issue:
                lessons.append("Kiểm tra lỗi hệ thống và có fallback response")

        return " | ".join(lessons) if lessons else "Cần cải thiện chất lượng tổng thể"

    def _categorize_query(self, query: str) -> str:
        """Phân loại câu hỏi."""
        q = query.lower()
        if any(w in q for w in ["lịch trình", "đi đâu", "gợi ý", "plan"]):
            return "itinerary"
        if any(w in q for w in ["ăn gì", "món", "đặc sản", "ẩm thực"]):
            return "food"
        if any(w in q for w in ["lịch sử", "ai", "nhân vật", "người"]):
            return "history"
        if any(w in q for w in ["chùa", "lễ hội", "văn hóa", "khmer"]):
            return "culture"
        if any(w in q for w in ["so sánh", "khác nhau", "hơn"]):
            return "comparison"
        return "general"

    # ── Retrieval ──

    @staticmethod
    def _rel_tokens(text: str) -> set:
        import unicodedata as _ud
        s = _ud.normalize("NFD", (text or "").lower())
        s = re.sub(r"[̀-ͯ]", "", s).replace("đ", "d")
        return {t for t in re.split(r"[^a-z0-9]+", s) if len(t) >= 3}

    def get_relevant_reflections(self, query: str, limit: int = 3) -> list[dict]:
        """Tìm reflections liên quan để tránh lỗi cũ.

        Nâng cấp: thay vì chỉ lọc theo category (thô), xếp hạng theo độ trùng
        token với câu hỏi (semantic-lite) + ưu tiên cùng category + gần đây.
        """
        category = self._categorize_query(query)
        q_tokens = self._rel_tokens(query)

        scored = []
        for r in self._reflections:
            score = 0.0
            if r.get("category") == category:
                score += 2.0
            overlap = len(q_tokens & self._rel_tokens(r.get("query", "")))
            score += overlap * 1.5
            if score > 0:
                scored.append((score, r.get("created", ""), r))

        # Rank by relevance, then recency
        scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
        results = [r for _, _, r in scored[:limit]]

        # Fallback: if nothing overlapped, return most recent same-category
        if not results:
            same_cat = [r for r in self._reflections if r.get("category") == category]
            same_cat.sort(key=lambda r: r.get("created", ""), reverse=True)
            results = same_cat[:limit]
        return results

    def get_reflection_prompt(self, query: str) -> str:
        """Tạo prompt bổ sung từ reflections."""
        reflections = self.get_relevant_reflections(query)
        if not reflections:
            return ""

        lines = ["[Lưu ý từ kinh nghiệm trước]:"]
        for r in reflections:
            lines.append(f"- Khi hỏi '{r['query'][:60]}...': {r['lesson']}")
        return "\n".join(lines)

    # ── Stats ──

    def stats(self) -> dict:
        with self._lock:
            by_category = {}
            for r in self._reflections:
                cat = r.get("category", "unknown")
                by_category[cat] = by_category.get(cat, 0) + 1

            avg_score = 0
            if self._reflections:
                avg_score = round(
                    sum(r.get("score", 0) for r in self._reflections) /
                    len(self._reflections), 1
                )

            return {
                "total_reflections": len(self._reflections),
                "by_category": by_category,
                "avg_failure_score": avg_score,
                "recent": self._reflections[-5:],
            }


# ══════════════════════════════════════════════════
#  ANSWER QUALITY TRACKER — Aggregate metrics
# ══════════════════════════════════════════════════

class QualityTracker:
    """Track answer quality over time for monitoring.

    Now PERSISTED to disk so the quality trend survives restarts (previously it
    was in-memory only and reset on every restart — useless as a long-horizon
    self-improvement signal).
    """

    _FILE = REFLEXION_DIR / "quality_scores.json"

    def __init__(self, file_path: str | Path | None = None):
        self._file = Path(file_path) if file_path is not None else self._FILE
        self._scores: list[dict] = []
        self._lock = Lock()
        self._dirty_count = 0
        self._load()

    def _load(self):
        try:
            if self._file.exists():
                self._scores = json.loads(self._file.read_text(encoding="utf-8")) or []
        except Exception as exc:
            logger.warning("Failed to load quality scores: %s", exc)
            self._scores = []

    def _save(self):
        try:
            self._file.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._file.with_suffix(".tmp")
            tmp.write_text(json.dumps(self._scores, ensure_ascii=False), encoding="utf-8")
            tmp.replace(self._file)
        except Exception as exc:
            logger.warning("Failed to save quality scores: %s", exc)

    def record(self, query: str, score: float, tools_used: list[str]):
        with self._lock:
            self._scores.append({
                "query": query[:100],
                "score": score,
                "tools": len(tools_used),
                "ts": datetime.now().isoformat(),
            })
            # Keep last 1000
            if len(self._scores) > 1000:
                self._scores = self._scores[-1000:]
            # Persist periodically (every 5 records) to bound I/O
            self._dirty_count += 1
            if self._dirty_count >= 5:
                self._dirty_count = 0
                self._save()

    def stats(self) -> dict:
        with self._lock:
            if not self._scores:
                return {"avg_score": 0, "count": 0}

            scores = [s["score"] for s in self._scores]
            recent_50 = scores[-50:]
            return {
                "avg_score": round(sum(scores) / len(scores), 2),
                "avg_recent_50": round(sum(recent_50) / len(recent_50), 2) if recent_50 else 0,
                "count": len(scores),
                "score_distribution": {
                    "excellent_8_10": sum(1 for s in scores if s >= 8),
                    "good_5_8": sum(1 for s in scores if 5 <= s < 8),
                    "poor_0_5": sum(1 for s in scores if s < 5),
                },
            }


# Singletons
reflexion_engine = ReflexionEngine()
quality_tracker = QualityTracker()
