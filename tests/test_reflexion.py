"""Tests for the Reflexion engine (agent/reflexion.py)."""
import pytest
from reflexion import ReflexionEngine, QualityTracker


# ── ReflexionEngine.evaluate_answer ──

def test_evaluate_good_answer():
    engine = ReflexionEngine()
    answer = (
        "Vĩnh Long là tỉnh thuộc Đồng bằng sông Cửu Long, nổi tiếng với:\n"
        "- **Vườn trái cây** — chôm chôm, sầu riêng, bưởi Năm Roi\n"
        "- **Chợ nổi Cái Bè** — trải nghiệm văn hóa sông nước\n"
        "- **Làng nghề** — gốm, dệt chiếu\n"
        "Bạn có muốn biết thêm về khu vực nào không?"
    )
    result = engine.evaluate_answer(
        query="Vĩnh Long có gì nổi tiếng?",
        answer=answer,
        tools_used=["search", "entity_detail", "suggest_followups"],
    )
    assert result["score"] >= 5
    assert isinstance(result["issues"], list)
    assert isinstance(result["good_points"], list)


def test_evaluate_bad_answer():
    engine = ReflexionEngine()
    result = engine.evaluate_answer(
        query="Vĩnh Long có gì nổi tiếng?",
        answer="không biết",
        tools_used=[],
    )
    assert result["score"] < 5
    assert len(result["issues"]) > 0


def test_evaluate_medium_answer():
    engine = ReflexionEngine()
    result = engine.evaluate_answer(
        query="Chùa Âng ở đâu?",
        answer="Chùa Âng nằm ở Trà Vinh, là ngôi chùa Khmer nổi tiếng.",
        tools_used=["search"],
    )
    assert 0 <= result["score"] <= 10


# ── QualityTracker ──

def test_quality_tracker_empty(tmp_path):
    tracker = QualityTracker(tmp_path / "quality_scores.json")
    stats = tracker.stats()
    assert stats["count"] == 0
    assert stats["avg_score"] == 0


def test_quality_tracker(tmp_path):
    tracker = QualityTracker(tmp_path / "quality_scores.json")
    tracker.record("query1", 8.0, ["search", "entity_detail"])
    tracker.record("query2", 3.0, [])
    tracker.record("query3", 6.0, ["search"])
    stats = tracker.stats()
    assert stats["count"] == 3
    assert stats["avg_score"] == pytest.approx(5.67, abs=0.1)
    assert stats["score_distribution"]["excellent_8_10"] == 1
    assert stats["score_distribution"]["good_5_8"] == 1
    assert stats["score_distribution"]["poor_0_5"] == 1
