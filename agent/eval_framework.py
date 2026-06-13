"""
vinhlong360 — Evaluation & Benchmark Framework.

Domain-specific evaluation cho Knowledge Agent (du lich Vinh Long, 327 entities).

Chuc nang:
  - Benchmark suite 50+ test cases (factual, comparison, itinerary, seasonal,
    recommendation, edge_case)
  - Scorer pipeline: Factuality, ToolUsage, Completeness, Hallucination, Format
  - EvalRunner: chay suite, so sanh reports, phat hien regression
  - Persistence: agent/data/eval/

Usage:
  from eval_framework import run_benchmark, get_latest_report

  # call_fn(query) -> (reply: str, tools_used: list[str])
  result = run_benchmark(call_fn)

  # Xem report gan nhat
  report = get_latest_report()
"""

import json
import logging
import os
import re
import sys
import time
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path
from threading import Lock
from typing import Callable, Dict, List, Optional, Tuple

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if hasattr(sys.stdout, "reconfigure") and sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).resolve().parent / "data"
EVAL_DIR = DATA_DIR / "eval"
EVAL_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize_vn(text: str) -> str:
    """Remove Vietnamese diacritics for fuzzy matching."""
    s = unicodedata.normalize("NFD", text.lower())
    s = re.sub(r"[̀-ͯ]", "", s)
    s = s.replace("đ", "d").replace("Đ", "D")
    return s


def _text_contains(haystack: str, needle: str) -> bool:
    """Check if needle appears in haystack (diacritic-insensitive)."""
    return _normalize_vn(needle) in _normalize_vn(haystack)


# ---------------------------------------------------------------------------
# TestCase
# ---------------------------------------------------------------------------

VALID_CATEGORIES = frozenset([
    "factual", "comparison", "itinerary", "seasonal",
    "recommendation", "edge_case",
])
VALID_DIFFICULTIES = frozenset(["easy", "medium", "hard"])


@dataclass
class TestCase:
    """A single benchmark test case for the Knowledge Agent."""

    __test__ = False

    query: str
    expected_entities: List[str] = field(default_factory=list)
    expected_tools: List[str] = field(default_factory=list)
    expected_keywords: List[str] = field(default_factory=list)
    category: str = "factual"
    difficulty: str = "medium"
    max_score: float = 10.0

    def __post_init__(self):
        if self.category not in VALID_CATEGORIES:
            raise ValueError(
                f"Invalid category '{self.category}', "
                f"must be one of {sorted(VALID_CATEGORIES)}"
            )
        if self.difficulty not in VALID_DIFFICULTIES:
            raise ValueError(
                f"Invalid difficulty '{self.difficulty}', "
                f"must be one of {sorted(VALID_DIFFICULTIES)}"
            )

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "TestCase":
        return cls(**d)


# ---------------------------------------------------------------------------
# BENCHMARK_SUITE — 52 test cases
# ---------------------------------------------------------------------------

BENCHMARK_SUITE: List[TestCase] = [
    # ══════════════════════════════════════════════════
    #  FACTUAL (16 cases)
    # ══════════════════════════════════════════════════
    TestCase(
        query="Chua Ang o dau?",
        expected_entities=["chua-ang"],
        expected_tools=["search"],
        expected_keywords=["Tra Vinh"],
        category="factual",
        difficulty="easy",
    ),
    TestCase(
        query="Cho noi Cai Be co gi dac biet?",
        expected_entities=["cho-noi-cai-be"],
        expected_tools=["entity_detail"],
        expected_keywords=["cho noi", "Cai Be"],
        category="factual",
        difficulty="easy",
    ),
    TestCase(
        query="Cu lao An Binh nam o dau?",
        expected_entities=["cu-lao-an-binh"],
        expected_tools=["search"],
        expected_keywords=["Vinh Long"],
        category="factual",
        difficulty="easy",
    ),
    TestCase(
        query="Ao Ba Om la gi?",
        expected_entities=["ao-ba-om"],
        expected_tools=["entity_detail"],
        expected_keywords=["Tra Vinh"],
        category="factual",
        difficulty="easy",
    ),
    TestCase(
        query="Chua Vam Ray o tinh nao?",
        expected_entities=["chua-vam-ray"],
        expected_tools=["search"],
        expected_keywords=["Tra Vinh", "Khmer"],
        category="factual",
        difficulty="easy",
    ),
    TestCase(
        query="Cam sanh Vinh Long co gi noi bat?",
        expected_entities=["cam-sanh-vinh-long"],
        expected_tools=["entity_detail"],
        expected_keywords=["cam sanh"],
        category="factual",
        difficulty="easy",
    ),
    TestCase(
        query="Banh trang My Long lam tu gi?",
        expected_entities=["banh-trang-my-long"],
        expected_tools=["entity_detail"],
        expected_keywords=["banh trang", "My Long"],
        category="factual",
        difficulty="medium",
    ),
    TestCase(
        query="Lang nghe nao o Ben Tre noi tieng?",
        expected_entities=[],
        expected_tools=["search"],
        expected_keywords=["lang nghe", "Ben Tre"],
        category="factual",
        difficulty="medium",
    ),
    TestCase(
        query="Co bao nhieu diem tham quan o Vinh Long?",
        expected_entities=[],
        expected_tools=["stats"],
        expected_keywords=["diem tham quan"],
        category="factual",
        difficulty="medium",
    ),
    TestCase(
        query="Cau My Thuan dai bao nhieu?",
        expected_entities=["cau-my-thuan"],
        expected_tools=["entity_detail"],
        expected_keywords=["My Thuan", "cau"],
        category="factual",
        difficulty="medium",
    ),
    TestCase(
        query="Khu du lich Vinh Sang o dau?",
        expected_entities=["khu-du-lich-vinh-sang"],
        expected_tools=["search"],
        expected_keywords=["Vinh Sang"],
        category="factual",
        difficulty="easy",
    ),
    TestCase(
        query="Nem Lai Vung la dac san gi?",
        expected_entities=["nem-lai-vung"],
        expected_tools=["entity_detail"],
        expected_keywords=["nem", "Lai Vung"],
        category="factual",
        difficulty="easy",
    ),
    TestCase(
        query="Dua Ben Tre co nhung loai nao?",
        expected_entities=["dua-ben-tre"],
        expected_tools=["entity_detail"],
        expected_keywords=["dua", "Ben Tre"],
        category="factual",
        difficulty="medium",
    ),
    TestCase(
        query="Cac xa phuong o Vinh Long?",
        expected_entities=[],
        expected_tools=["places_in_area"],
        expected_keywords=["xa", "phuong"],
        category="factual",
        difficulty="hard",
    ),
    TestCase(
        query="Gan chua Vam Ray co gi?",
        expected_entities=["chua-vam-ray"],
        expected_tools=["nearby_entities"],
        expected_keywords=["gan", "Vam Ray"],
        category="factual",
        difficulty="medium",
    ),
    TestCase(
        query="San pham OCOP o Vinh Long?",
        expected_entities=[],
        expected_tools=["search"],
        expected_keywords=["OCOP"],
        category="factual",
        difficulty="medium",
    ),

    # ══════════════════════════════════════════════════
    #  COMPARISON (8 cases)
    # ══════════════════════════════════════════════════
    TestCase(
        query="So sanh Ben Tre va Tra Vinh",
        expected_entities=[],
        expected_tools=["compare_areas"],
        expected_keywords=["Ben Tre", "Tra Vinh"],
        category="comparison",
        difficulty="medium",
    ),
    TestCase(
        query="Vinh Long va Ben Tre noi nao co nhieu diem du lich hon?",
        expected_entities=[],
        expected_tools=["compare_areas"],
        expected_keywords=["Vinh Long", "Ben Tre", "du lich"],
        category="comparison",
        difficulty="medium",
    ),
    TestCase(
        query="Am thuc Tra Vinh khac gi Vinh Long?",
        expected_entities=[],
        expected_tools=["compare_areas"],
        expected_keywords=["am thuc", "Tra Vinh", "Vinh Long"],
        category="comparison",
        difficulty="hard",
    ),
    TestCase(
        query="So sanh dac san 3 khu vuc",
        expected_entities=[],
        expected_tools=["compare_areas"],
        expected_keywords=["dac san"],
        category="comparison",
        difficulty="hard",
    ),
    TestCase(
        query="Ben Tre hay Tra Vinh co nhieu chua Khmer hon?",
        expected_entities=[],
        expected_tools=["compare_areas"],
        expected_keywords=["chua Khmer"],
        category="comparison",
        difficulty="hard",
    ),
    TestCase(
        query="Chua nao dep hon, Chua Ang hay Chua Vam Ray?",
        expected_entities=["chua-ang", "chua-vam-ray"],
        expected_tools=["entity_detail"],
        expected_keywords=["Chua Ang", "Chua Vam Ray"],
        category="comparison",
        difficulty="medium",
    ),
    TestCase(
        query="Lang nghe Ben Tre nhieu hon Vinh Long khong?",
        expected_entities=[],
        expected_tools=["compare_areas"],
        expected_keywords=["lang nghe"],
        category="comparison",
        difficulty="medium",
    ),
    TestCase(
        query="Tra Vinh co gi hon Ben Tre?",
        expected_entities=[],
        expected_tools=["compare_areas"],
        expected_keywords=["Tra Vinh", "Ben Tre"],
        category="comparison",
        difficulty="medium",
    ),

    # ══════════════════════════════════════════════════
    #  ITINERARY (9 cases)
    # ══════════════════════════════════════════════════
    TestCase(
        query="Lich trinh 2 ngay am thuc Vinh Long",
        expected_entities=[],
        expected_tools=["generate_itinerary"],
        expected_keywords=["lich trinh", "am thuc"],
        category="itinerary",
        difficulty="medium",
    ),
    TestCase(
        query="Di Vinh Long 1 ngay nen di dau?",
        expected_entities=[],
        expected_tools=["generate_itinerary"],
        expected_keywords=["1 ngay"],
        category="itinerary",
        difficulty="easy",
    ),
    TestCase(
        query="Lap ke hoach 3 ngay kham pha Ben Tre",
        expected_entities=[],
        expected_tools=["generate_itinerary"],
        expected_keywords=["3 ngay", "Ben Tre"],
        category="itinerary",
        difficulty="medium",
    ),
    TestCase(
        query="Lich trinh tham quan chua Khmer Tra Vinh",
        expected_entities=[],
        expected_tools=["generate_itinerary"],
        expected_keywords=["chua Khmer", "Tra Vinh"],
        category="itinerary",
        difficulty="hard",
    ),
    TestCase(
        query="Di choi cuoi tuan o mien Tay",
        expected_entities=[],
        expected_tools=["generate_itinerary"],
        expected_keywords=["cuoi tuan"],
        category="itinerary",
        difficulty="easy",
    ),
    TestCase(
        query="Lich trinh gia dinh 2 ngay co tre nho",
        expected_entities=[],
        expected_tools=["generate_itinerary"],
        expected_keywords=["gia dinh", "tre nho"],
        category="itinerary",
        difficulty="hard",
    ),
    TestCase(
        query="Goi y lich trinh 5 ngay du lich Vinh Long Ben Tre Tra Vinh",
        expected_entities=[],
        expected_tools=["generate_itinerary"],
        expected_keywords=["5 ngay", "Vinh Long", "Ben Tre", "Tra Vinh"],
        category="itinerary",
        difficulty="hard",
    ),
    TestCase(
        query="Tour thien nhien sinh thai 2 ngay",
        expected_entities=[],
        expected_tools=["generate_itinerary"],
        expected_keywords=["thien nhien", "sinh thai"],
        category="itinerary",
        difficulty="medium",
    ),
    TestCase(
        query="Lich trinh ngan sach thap 1 ngay Vinh Long",
        expected_entities=[],
        expected_tools=["generate_itinerary"],
        expected_keywords=["ngan sach", "1 ngay"],
        category="itinerary",
        difficulty="medium",
    ),

    # ══════════════════════════════════════════════════
    #  SEASONAL (8 cases)
    # ══════════════════════════════════════════════════
    TestCase(
        query="Thang 6 nen di dau?",
        expected_entities=[],
        expected_tools=["seasonal_now"],
        expected_keywords=["thang 6"],
        category="seasonal",
        difficulty="easy",
    ),
    TestCase(
        query="Mua nao trai cay ngon nhat?",
        expected_entities=[],
        expected_tools=["seasonal_now"],
        expected_keywords=["trai cay", "mua"],
        category="seasonal",
        difficulty="medium",
    ),
    TestCase(
        query="Thoi diem tot nhat de tham quan Vinh Long?",
        expected_entities=[],
        expected_tools=["seasonal_now"],
        expected_keywords=["thoi diem"],
        category="seasonal",
        difficulty="medium",
    ),
    TestCase(
        query="Thang 12 co su kien gi?",
        expected_entities=[],
        expected_tools=["seasonal_now"],
        expected_keywords=["thang 12", "su kien"],
        category="seasonal",
        difficulty="easy",
    ),
    TestCase(
        query="Cam sanh mua nao chin?",
        expected_entities=["cam-sanh-vinh-long"],
        expected_tools=["entity_detail", "seasonal_now"],
        expected_keywords=["cam sanh", "mua"],
        category="seasonal",
        difficulty="medium",
    ),
    TestCase(
        query="Mua mua co anh huong du lich khong?",
        expected_entities=[],
        expected_tools=["weather"],
        expected_keywords=["mua mua"],
        category="seasonal",
        difficulty="hard",
    ),
    TestCase(
        query="Tet co le hoi gi o Vinh Long?",
        expected_entities=[],
        expected_tools=["seasonal_now", "search"],
        expected_keywords=["Tet", "le hoi"],
        category="seasonal",
        difficulty="medium",
    ),
    TestCase(
        query="Thang 3 nen an gi o Ben Tre?",
        expected_entities=[],
        expected_tools=["seasonal_now"],
        expected_keywords=["thang 3", "Ben Tre"],
        category="seasonal",
        difficulty="medium",
    ),

    # ══════════════════════════════════════════════════
    #  RECOMMENDATION (8 cases)
    # ══════════════════════════════════════════════════
    TestCase(
        query="Dac san ngon o Vinh Long?",
        expected_entities=[],
        expected_tools=["search"],
        expected_keywords=["OCOP", "dac san"],
        category="recommendation",
        difficulty="easy",
    ),
    TestCase(
        query="Cho toi nhung mon an ngon nhat Ben Tre",
        expected_entities=[],
        expected_tools=["search"],
        expected_keywords=["mon an", "Ben Tre"],
        category="recommendation",
        difficulty="easy",
    ),
    TestCase(
        query="Khach san tot o Vinh Long?",
        expected_entities=[],
        expected_tools=["search"],
        expected_keywords=["khach san", "luu tru"],
        category="recommendation",
        difficulty="medium",
    ),
    TestCase(
        query="Qua bieu dac san mien Tay?",
        expected_entities=[],
        expected_tools=["search"],
        expected_keywords=["qua", "dac san"],
        category="recommendation",
        difficulty="medium",
    ),
    TestCase(
        query="Hoat dong vui choi cho tre em?",
        expected_entities=[],
        expected_tools=["search"],
        expected_keywords=["tre em", "vui choi"],
        category="recommendation",
        difficulty="medium",
    ),
    TestCase(
        query="Diem chup hinh dep o Tra Vinh?",
        expected_entities=[],
        expected_tools=["search"],
        expected_keywords=["chup hinh", "Tra Vinh"],
        category="recommendation",
        difficulty="medium",
    ),
    TestCase(
        query="San pham OCOP nao dang mua?",
        expected_entities=[],
        expected_tools=["search"],
        expected_keywords=["OCOP"],
        category="recommendation",
        difficulty="easy",
    ),
    TestCase(
        query="Trai nghiem van hoa Khmer hay nhat?",
        expected_entities=[],
        expected_tools=["search"],
        expected_keywords=["van hoa", "Khmer"],
        category="recommendation",
        difficulty="hard",
    ),

    # ══════════════════════════════════════════════════
    #  EDGE CASES (5 cases)
    # ══════════════════════════════════════════════════
    TestCase(
        query="",
        expected_entities=[],
        expected_tools=[],
        expected_keywords=[],
        category="edge_case",
        difficulty="easy",
    ),
    TestCase(
        query="a" * 5000,
        expected_entities=[],
        expected_tools=[],
        expected_keywords=[],
        category="edge_case",
        difficulty="hard",
    ),
    TestCase(
        query="Thanh pho Atlantis o Vinh Long o dau?",
        expected_entities=[],
        expected_tools=["search"],
        expected_keywords=[],
        category="edge_case",
        difficulty="medium",
    ),
    TestCase(
        query="'; DROP TABLE entities; --",
        expected_entities=[],
        expected_tools=[],
        expected_keywords=[],
        category="edge_case",
        difficulty="hard",
    ),
    TestCase(
        query="Tell me about Paris France tourist attractions",
        expected_entities=[],
        expected_tools=[],
        expected_keywords=["Vinh Long"],
        category="edge_case",
        difficulty="medium",
    ),
]

assert len(BENCHMARK_SUITE) >= 50, (
    f"BENCHMARK_SUITE must have >= 50 cases, got {len(BENCHMARK_SUITE)}"
)


# ---------------------------------------------------------------------------
# Scorer classes
# ---------------------------------------------------------------------------

class FactualityScorer:
    """Score based on expected entities mentioned and keywords present."""

    @staticmethod
    def score(reply: str, test_case: TestCase, entities: Dict[str, dict]) -> float:
        if not reply:
            return 0.0

        max_pts = test_case.max_score
        entity_weight = 0.6
        keyword_weight = 0.4

        # --- Entity score ---
        entity_score = 0.0
        if test_case.expected_entities:
            found = 0
            for eid in test_case.expected_entities:
                entity = entities.get(eid, {})
                name = entity.get("name", eid.replace("-", " "))
                if _text_contains(reply, name) or _text_contains(reply, eid):
                    found += 1
            entity_score = found / len(test_case.expected_entities)
        else:
            # No expected entities => full entity score if reply exists
            entity_score = 1.0

        # --- Keyword score ---
        keyword_score = 0.0
        if test_case.expected_keywords:
            found = 0
            for kw in test_case.expected_keywords:
                if _text_contains(reply, kw):
                    found += 1
            keyword_score = found / len(test_case.expected_keywords)
        else:
            keyword_score = 1.0

        return round(
            max_pts * (entity_weight * entity_score + keyword_weight * keyword_score),
            2,
        )


class ToolUsageScorer:
    """Score based on whether expected tools were called."""

    @staticmethod
    def score(tools_used: List[str], test_case: TestCase) -> float:
        if not test_case.expected_tools:
            # No tools expected; penalise if tools were used for edge cases
            if test_case.category == "edge_case" and tools_used:
                return test_case.max_score * 0.5
            return test_case.max_score

        max_pts = test_case.max_score
        tools_set = set(tools_used)
        expected_set = set(test_case.expected_tools)

        # At least one expected tool used => partial credit
        matched = expected_set & tools_set
        if not matched:
            return 0.0

        recall = len(matched) / len(expected_set)

        # Penalise excessive irrelevant tool calls
        extra = len(tools_set - expected_set)
        penalty = min(extra * 0.1, 0.3)

        return round(max_pts * max(recall - penalty, 0.0), 2)


class CompletenessScorer:
    """Score based on reply length adequacy and all expected elements present."""

    # Minimum reply lengths by difficulty
    MIN_LENGTHS = {"easy": 30, "medium": 80, "hard": 150}

    @staticmethod
    def score(reply: str, test_case: TestCase) -> float:
        if not reply:
            return 0.0

        max_pts = test_case.max_score
        length_weight = 0.4
        elements_weight = 0.6

        # --- Length adequacy ---
        min_len = CompletenessScorer.MIN_LENGTHS.get(test_case.difficulty, 80)
        actual_len = len(reply.strip())
        if actual_len >= min_len:
            length_score = 1.0
        elif actual_len == 0:
            length_score = 0.0
        else:
            length_score = actual_len / min_len

        # --- Elements present (entities + keywords combined) ---
        all_expected = test_case.expected_entities + test_case.expected_keywords
        if all_expected:
            found = 0
            for item in all_expected:
                name = item.replace("-", " ")
                if _text_contains(reply, name) or _text_contains(reply, item):
                    found += 1
            elements_score = found / len(all_expected)
        else:
            elements_score = 1.0 if actual_len > 0 else 0.0

        return round(
            max_pts * (length_weight * length_score + elements_weight * elements_score),
            2,
        )


class HallucinationScorer:
    """Detect entity names in reply that don't exist in the knowledge base.

    Returns a score where max_score = no hallucinations, lower = more hallucinations.
    """

    # Common Vietnamese tourism words that look like entity names but aren't
    IGNORE_PATTERNS = frozenset([
        "vinh long", "ben tre", "tra vinh", "mien tay", "mekong",
        "viet nam", "vietnam", "ho chi minh", "can tho", "dong thap",
        "sai gon", "ha noi",
    ])

    @staticmethod
    def score(reply: str, entities: Dict[str, dict]) -> float:
        if not reply:
            return 10.0  # No reply = no hallucination

        max_pts = 10.0
        reply_lower = _normalize_vn(reply)

        # Extract entity names from knowledge base
        known_names = set()
        for eid, entity in entities.items():
            known_names.add(_normalize_vn(entity.get("name", "")))
            known_names.add(_normalize_vn(eid.replace("-", " ")))

        # Look for capitalized phrases that might be entity references
        # Vietnamese place names are typically capitalized
        potential_names = re.findall(
            r"[A-ZÀ-ɏ][a-zÀ-ɏ]+(?:\s+[A-ZÀ-ɏ][a-zÀ-ɏ]+)*",
            reply,
        )

        if not potential_names:
            return max_pts

        hallucinated = 0
        checked = 0
        for name in potential_names:
            norm = _normalize_vn(name)
            if len(norm) < 4:
                continue
            if norm in HallucinationScorer.IGNORE_PATTERNS:
                continue
            checked += 1
            # Check if this name exists in knowledge base
            if not any(norm in kn or kn in norm for kn in known_names if len(kn) > 3):
                hallucinated += 1

        if checked == 0:
            return max_pts

        hallucination_rate = hallucinated / checked
        # Allow some unknown names (20% threshold before penalising)
        if hallucination_rate <= 0.2:
            return max_pts
        adjusted_rate = (hallucination_rate - 0.2) / 0.8
        return round(max_pts * (1.0 - adjusted_rate), 2)


class FormatScorer:
    """Score reply formatting: markdown structure and Vietnamese quality."""

    @staticmethod
    def score(reply: str) -> float:
        if not reply:
            return 0.0

        max_pts = 10.0
        scores = []

        # --- Markdown structure (headings, lists, bold) ---
        has_heading = bool(re.search(r"^#{1,3}\s", reply, re.MULTILINE))
        has_list = bool(re.search(r"^[\-\*]\s", reply, re.MULTILINE))
        has_bold = bool(re.search(r"\*\*[^*]+\*\*", reply))
        has_emoji = bool(re.search(r"[\U0001F300-\U0001F9FF]", reply))

        md_features = sum([has_heading, has_list, has_bold, has_emoji])
        # Short replies don't need heavy formatting
        if len(reply) < 100:
            md_score = min(md_features / 2.0, 1.0)
        else:
            md_score = min(md_features / 3.0, 1.0)
        scores.append(md_score)

        # --- Vietnamese quality: proper sentences ---
        sentences = re.split(r"[.!?\n]", reply)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        if sentences:
            # Check that sentences start with uppercase or Vietnamese chars
            proper = sum(
                1 for s in sentences
                if s[0].isupper() or s[0] in "Đđ"
            )
            vn_score = proper / len(sentences)
        else:
            vn_score = 0.5  # Short reply, can't tell
        scores.append(vn_score)

        # --- Not too short, not excessively long ---
        reply_len = len(reply.strip())
        if reply_len < 20:
            len_score = 0.2
        elif reply_len > 5000:
            len_score = 0.7  # Verbose penalty
        else:
            len_score = 1.0
        scores.append(len_score)

        avg = sum(scores) / len(scores)
        return round(max_pts * avg, 2)


# ---------------------------------------------------------------------------
# EvalReport
# ---------------------------------------------------------------------------

@dataclass
class EvalReport:
    """Results from an evaluation run."""

    timestamp: float = 0.0
    total_cases: int = 0
    passed: int = 0
    failed: int = 0
    avg_score: float = 0.0
    scores_by_category: Dict[str, dict] = field(default_factory=dict)
    regressions: List[dict] = field(default_factory=list)
    duration_seconds: float = 0.0
    details: List[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "EvalReport":
        return cls(
            timestamp=d.get("timestamp", 0.0),
            total_cases=d.get("total_cases", 0),
            passed=d.get("passed", 0),
            failed=d.get("failed", 0),
            avg_score=d.get("avg_score", 0.0),
            scores_by_category=d.get("scores_by_category", {}),
            regressions=d.get("regressions", []),
            duration_seconds=d.get("duration_seconds", 0.0),
            details=d.get("details", []),
        )

    def summary(self) -> str:
        """Human-readable summary of the evaluation."""
        lines = [
            "=" * 60,
            "  VINHLONG360 EVALUATION REPORT",
            "=" * 60,
            f"  Timestamp : {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.timestamp))}",
            f"  Duration  : {self.duration_seconds:.1f}s",
            f"  Cases     : {self.total_cases} total, {self.passed} passed, {self.failed} failed",
            f"  Avg Score : {self.avg_score:.2f} / 10.0",
            "",
            "  Scores by Category:",
        ]
        for cat, info in sorted(self.scores_by_category.items()):
            avg = info.get("avg_score", 0.0)
            cnt = info.get("count", 0)
            lines.append(f"    {cat:<16s} : {avg:5.2f} / 10.0  ({cnt} cases)")

        if self.regressions:
            lines.append("")
            lines.append(f"  REGRESSIONS ({len(self.regressions)}):")
            for reg in self.regressions:
                lines.append(
                    f"    [{reg['category']}] {reg['query'][:50]}: "
                    f"{reg['old_score']:.1f} -> {reg['new_score']:.1f} "
                    f"({reg['change']:+.1f}%)"
                )

        lines.append("=" * 60)
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# EvalRunner
# ---------------------------------------------------------------------------

# Type alias for the agent call function
CallFn = Callable[[str], Tuple[str, List[str]]]

# Pass threshold: avg of all scorer scores >= this fraction of max_score
PASS_THRESHOLD = 0.5


class EvalRunner:
    """Run evaluation suites against the Knowledge Agent."""

    def __init__(self):
        self._lock = Lock()
        self._entities: Dict[str, dict] = {}
        self._load_entities()

    def _load_entities(self):
        """Load entity names from knowledge base for scorer use."""
        try:
            json_path = Path(__file__).resolve().parent.parent / "web" / "data.json"
            if json_path.exists():
                with open(json_path, encoding="utf-8") as f:
                    data = json.load(f)
                self._entities = {e["id"]: e for e in data.get("entities", [])}
                logger.info("Eval: loaded %d entities from knowledge base", len(self._entities))
            else:
                logger.warning("Eval: data.json not found, hallucination scoring limited")
        except Exception as exc:
            logger.warning("Eval: failed to load entities: %s", exc)

    def run_single(self, call_fn: CallFn, test_case: TestCase) -> dict:
        """Run one test case through call_fn, return all scores.

        call_fn(query) -> (reply: str, tools_used: list[str])
        """
        start = time.time()
        try:
            reply, tools_used = call_fn(test_case.query)
        except Exception as exc:
            logger.error("Eval: call_fn failed for %r: %s", test_case.query[:60], exc)
            reply = ""
            tools_used = []
        elapsed = time.time() - start

        factuality = FactualityScorer.score(reply, test_case, self._entities)
        tool_usage = ToolUsageScorer.score(tools_used, test_case)
        completeness = CompletenessScorer.score(reply, test_case)
        hallucination = HallucinationScorer.score(reply, self._entities)
        formatting = FormatScorer.score(reply)

        avg_score = round(
            (factuality + tool_usage + completeness + hallucination + formatting) / 5.0,
            2,
        )
        passed = avg_score >= (test_case.max_score * PASS_THRESHOLD)

        return {
            "query": test_case.query[:200],
            "category": test_case.category,
            "difficulty": test_case.difficulty,
            "scores": {
                "factuality": factuality,
                "tool_usage": tool_usage,
                "completeness": completeness,
                "hallucination": hallucination,
                "format": formatting,
            },
            "avg_score": avg_score,
            "passed": passed,
            "tools_used": tools_used,
            "reply_length": len(reply),
            "duration_seconds": round(elapsed, 3),
        }

    def run_suite(
        self,
        call_fn: CallFn,
        suite: Optional[List[TestCase]] = None,
    ) -> EvalReport:
        """Run all test cases through call_fn and produce an EvalReport."""
        if suite is None:
            suite = BENCHMARK_SUITE

        start_time = time.time()
        details: List[dict] = []
        cat_scores: Dict[str, List[float]] = defaultdict(list)

        logger.info("Eval: running %d test cases", len(suite))

        for i, tc in enumerate(suite):
            logger.info("Eval: [%d/%d] %s", i + 1, len(suite), tc.query[:60])
            result = self.run_single(call_fn, tc)
            details.append(result)
            cat_scores[tc.category].append(result["avg_score"])

        total_time = time.time() - start_time
        all_scores = [d["avg_score"] for d in details]
        avg_score = round(sum(all_scores) / len(all_scores), 2) if all_scores else 0.0
        passed = sum(1 for d in details if d["passed"])
        failed = len(details) - passed

        scores_by_category = {}
        for cat, scores in sorted(cat_scores.items()):
            scores_by_category[cat] = {
                "count": len(scores),
                "avg_score": round(sum(scores) / len(scores), 2) if scores else 0.0,
                "min_score": round(min(scores), 2) if scores else 0.0,
                "max_score": round(max(scores), 2) if scores else 0.0,
            }

        # Detect regressions against last report
        regressions = self._detect_regressions(details)

        report = EvalReport(
            timestamp=time.time(),
            total_cases=len(suite),
            passed=passed,
            failed=failed,
            avg_score=avg_score,
            scores_by_category=scores_by_category,
            regressions=regressions,
            duration_seconds=round(total_time, 2),
            details=details,
        )

        # Persist report
        self._save_report(report)
        logger.info("Eval: done. Avg=%.2f, Pass=%d/%d in %.1fs",
                     avg_score, passed, len(suite), total_time)

        return report

    def compare_reports(self, report_a: EvalReport, report_b: EvalReport) -> dict:
        """Compare two reports. Flag regressions where score drops > 5%.

        Returns dict with overall comparison and per-category breakdown.
        """
        result = {
            "overall": {
                "a_avg": report_a.avg_score,
                "b_avg": report_b.avg_score,
                "change_pct": 0.0,
                "regressed": False,
            },
            "by_category": {},
            "regressions": [],
        }

        if report_a.avg_score > 0:
            change = ((report_b.avg_score - report_a.avg_score) / report_a.avg_score) * 100
            result["overall"]["change_pct"] = round(change, 2)
            result["overall"]["regressed"] = change < -5.0

        # Per-category comparison
        all_cats = set(report_a.scores_by_category) | set(report_b.scores_by_category)
        for cat in sorted(all_cats):
            a_info = report_a.scores_by_category.get(cat, {})
            b_info = report_b.scores_by_category.get(cat, {})
            a_avg = a_info.get("avg_score", 0.0)
            b_avg = b_info.get("avg_score", 0.0)
            if a_avg > 0:
                change = ((b_avg - a_avg) / a_avg) * 100
            else:
                change = 0.0

            cat_result = {
                "a_avg": a_avg,
                "b_avg": b_avg,
                "change_pct": round(change, 2),
                "regressed": change < -5.0,
            }
            result["by_category"][cat] = cat_result

            if cat_result["regressed"]:
                result["regressions"].append({
                    "category": cat,
                    "old_score": a_avg,
                    "new_score": b_avg,
                    "change_pct": round(change, 2),
                })

        return result

    # --- Persistence ---

    def _save_report(self, report: EvalReport):
        """Save report to agent/data/eval/ with timestamp filename."""
        with self._lock:
            ts = time.strftime("%Y%m%d_%H%M%S", time.localtime(report.timestamp))
            path = EVAL_DIR / f"report_{ts}.json"
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)
                logger.info("Eval: report saved to %s", path)
            except Exception as exc:
                logger.error("Eval: failed to save report: %s", exc)

    def _load_latest_report(self) -> Optional[EvalReport]:
        """Load the most recent report from disk."""
        reports = sorted(EVAL_DIR.glob("report_*.json"), reverse=True)
        if not reports:
            return None
        try:
            with open(reports[0], encoding="utf-8") as f:
                return EvalReport.from_dict(json.load(f))
        except Exception as exc:
            logger.warning("Eval: failed to load report %s: %s", reports[0], exc)
            return None

    def _detect_regressions(self, current_details: List[dict]) -> List[dict]:
        """Compare current run against latest saved report, flag >5% drops."""
        prev = self._load_latest_report()
        if prev is None or not prev.details:
            return []

        # Build lookup: query -> avg_score from previous run
        prev_scores: Dict[str, dict] = {}
        for d in prev.details:
            prev_scores[d["query"]] = d

        regressions = []
        for d in current_details:
            prev_d = prev_scores.get(d["query"])
            if prev_d is None:
                continue
            old = prev_d["avg_score"]
            new = d["avg_score"]
            if old > 0:
                change_pct = ((new - old) / old) * 100
                if change_pct < -5.0:
                    regressions.append({
                        "query": d["query"],
                        "category": d["category"],
                        "old_score": old,
                        "new_score": new,
                        "change": round(change_pct, 2),
                    })

        return regressions

    def _load_report_history(self, limit: int = 10) -> List[EvalReport]:
        """Load recent reports from disk."""
        report_files = sorted(EVAL_DIR.glob("report_*.json"), reverse=True)[:limit]
        reports = []
        for path in report_files:
            try:
                with open(path, encoding="utf-8") as f:
                    reports.append(EvalReport.from_dict(json.load(f)))
            except Exception as exc:
                logger.warning("Eval: skipping %s: %s", path, exc)
        return reports


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

eval_runner = EvalRunner()


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------

def run_benchmark(call_fn: CallFn) -> dict:
    """Run full benchmark suite, save report, return summary dict.

    call_fn(query) -> (reply: str, tools_used: list[str])
    """
    report = eval_runner.run_suite(call_fn)
    return {
        "summary": report.summary(),
        "avg_score": report.avg_score,
        "passed": report.passed,
        "failed": report.failed,
        "total": report.total_cases,
        "duration": report.duration_seconds,
        "scores_by_category": report.scores_by_category,
        "regressions": report.regressions,
    }


def get_latest_report() -> Optional[dict]:
    """Load most recent evaluation report as dict."""
    report = eval_runner._load_latest_report()
    if report is None:
        return None
    return report.to_dict()


def get_report_history(limit: int = 10) -> List[dict]:
    """Load recent evaluation reports as list of dicts."""
    reports = eval_runner._load_report_history(limit=limit)
    return [r.to_dict() for r in reports]
