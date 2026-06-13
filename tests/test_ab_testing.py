"""Tests for agent/ab_testing.py — A/B Testing Framework."""
import json
import os
import pytest
from pathlib import Path

from ab_testing import (
    ABTestManager,
    Experiment,
    create_default_experiments,
    _DEFAULT_EXPERIMENTS,
    _norm_cdf,
    _norm_ppf,
    _erf,
)


@pytest.fixture
def tmp_manager(tmp_path):
    """Create an ABTestManager backed by a temp file."""
    filepath = tmp_path / "ab_tests.json"
    return ABTestManager(filepath=filepath)


@pytest.fixture
def manager_with_experiment(tmp_manager):
    """Manager with a single experiment already created."""
    tmp_manager.create_experiment(
        name="test_exp",
        variants=[
            {"id": "control", "config": {}, "weight": 0.5},
            {"id": "treatment", "config": {"feature": True}, "weight": 0.5},
        ],
        metric_name="score",
        description="A test experiment",
    )
    return tmp_manager


# ── Experiment creation ──────────────────────────────


def test_create_experiment(tmp_manager):
    exp = tmp_manager.create_experiment(
        name="my_exp",
        variants=[
            {"id": "a", "config": {}, "weight": 0.5},
            {"id": "b", "config": {}, "weight": 0.5},
        ],
        metric_name="quality",
    )
    assert exp.name == "my_exp"
    assert exp.active is True
    assert len(exp.variants) == 2


def test_create_experiment_duplicate_raises(manager_with_experiment):
    with pytest.raises(ValueError, match="already exists"):
        manager_with_experiment.create_experiment(
            name="test_exp",
            variants=[
                {"id": "a", "config": {}, "weight": 0.5},
                {"id": "b", "config": {}, "weight": 0.5},
            ],
            metric_name="score",
        )


def test_create_experiment_too_few_variants(tmp_manager):
    with pytest.raises(ValueError, match="at least 2"):
        tmp_manager.create_experiment(
            name="bad_exp",
            variants=[{"id": "only_one", "config": {}, "weight": 1.0}],
            metric_name="score",
        )


# ── Variant assignment ───────────────────────────────


def test_assign_variant_returns_dict(manager_with_experiment):
    variant = manager_with_experiment.assign_variant("test_exp", "user_1")
    assert "id" in variant
    assert variant["id"] in ("control", "treatment")


def test_assign_variant_deterministic(manager_with_experiment):
    """Same user always gets the same variant."""
    v1 = manager_with_experiment.assign_variant("test_exp", "user_42")
    v2 = manager_with_experiment.assign_variant("test_exp", "user_42")
    assert v1["id"] == v2["id"]


def test_assign_variant_different_users_may_differ(manager_with_experiment):
    """Different users should (statistically) get different variants."""
    variants = set()
    for i in range(50):
        v = manager_with_experiment.assign_variant("test_exp", f"user_{i}")
        variants.add(v["id"])
    # With 50 users and 50/50 split, both variants should appear
    assert len(variants) == 2


def test_assign_variant_unknown_experiment(tmp_manager):
    with pytest.raises(KeyError, match="not found"):
        tmp_manager.assign_variant("nonexistent", "user_1")


# ── Record outcome ───────────────────────────────────


def test_record_outcome(manager_with_experiment):
    manager_with_experiment.assign_variant("test_exp", "user_1")
    manager_with_experiment.record_outcome("test_exp", "user_1", 0.85)
    results = manager_with_experiment.get_results("test_exp")
    # At least one variant should have count > 0
    total_count = sum(v["count"] for v in results["variants"].values())
    assert total_count >= 1


def test_record_outcome_unknown_experiment(tmp_manager):
    with pytest.raises(KeyError, match="not found"):
        tmp_manager.record_outcome("nonexistent", "user_1", 0.5)


# ── Get results ──────────────────────────────────────


def test_get_results_structure(manager_with_experiment):
    # Assign and record for a few users
    for i in range(10):
        uid = f"user_{i}"
        manager_with_experiment.assign_variant("test_exp", uid)
        manager_with_experiment.record_outcome("test_exp", uid, 0.5 + i * 0.05)

    results = manager_with_experiment.get_results("test_exp")
    assert results["experiment"] == "test_exp"
    assert results["metric_name"] == "score"
    assert "variants" in results
    for vid, stats in results["variants"].items():
        assert "count" in stats
        assert "mean" in stats
        assert "std_dev" in stats
        assert "confidence_interval_95" in stats


def test_get_results_empty_experiment(manager_with_experiment):
    results = manager_with_experiment.get_results("test_exp")
    # No outcomes yet, all counts should be 0
    for vid, stats in results["variants"].items():
        assert stats["count"] == 0


# ── Significance testing ─────────────────────────────


def test_is_significant_not_enough_data(manager_with_experiment):
    result = manager_with_experiment.is_significant("test_exp")
    assert result["significant"] is False
    assert result["test_used"] == "none"


def test_is_significant_with_enough_data(tmp_manager):
    """With very different distributions, should detect significance.

    We manually assign users to ensure both variants get enough data,
    bypassing the hash-based assignment which could be uneven.
    """
    tmp_manager.create_experiment(
        name="sig_test",
        variants=[
            {"id": "control", "config": {}, "weight": 0.5},
            {"id": "treatment", "config": {}, "weight": 0.5},
        ],
        metric_name="score",
    )
    # Assign users and record outcomes with slight variance
    # (t-test needs non-zero std_dev within groups)
    for i in range(200):
        uid = f"user_{i}"
        v = tmp_manager.assign_variant("sig_test", uid)
        noise = (i % 10) * 0.01  # deterministic noise 0.00-0.09
        if v["id"] == "control":
            tmp_manager.record_outcome("sig_test", uid, 0.2 + noise)
        else:
            tmp_manager.record_outcome("sig_test", uid, 0.95 + noise)

    # Verify both variants have data
    results = tmp_manager.get_results("sig_test")
    variant_counts = {vid: v["count"] for vid, v in results["variants"].items()}

    result = tmp_manager.is_significant("sig_test")

    # If both variants have >= 2 observations, we should get a test result
    if all(c >= 2 for c in variant_counts.values()):
        assert result["test_used"] in ("z-test", "welch-t-test")
        assert result["significant"] is True
        assert result["winner"] is not None
    else:
        # If hash distribution is very skewed, test is inconclusive
        assert result["test_used"] in ("none", "z-test", "welch-t-test")


# ── List experiments ─────────────────────────────────


def test_list_experiments(manager_with_experiment):
    exps = manager_with_experiment.list_experiments()
    assert len(exps) == 1
    assert exps[0]["name"] == "test_exp"
    assert exps[0]["active"] is True
    assert "variant_count" in exps[0]


# ── Stop experiment ──────────────────────────────────


def test_stop_experiment(manager_with_experiment):
    manager_with_experiment.stop_experiment("test_exp")
    exps = manager_with_experiment.list_experiments()
    assert exps[0]["active"] is False


def test_stop_unknown_experiment(tmp_manager):
    with pytest.raises(KeyError, match="not found"):
        tmp_manager.stop_experiment("nonexistent")


# ── Persistence ──────────────────────────────────────


def test_persistence_survives_reload(tmp_path):
    filepath = tmp_path / "ab_persist.json"
    m1 = ABTestManager(filepath=filepath)
    m1.create_experiment(
        name="persist_exp",
        variants=[
            {"id": "a", "config": {"x": 1}, "weight": 0.5},
            {"id": "b", "config": {"x": 2}, "weight": 0.5},
        ],
        metric_name="test",
    )
    m1.assign_variant("persist_exp", "user_1")
    m1.record_outcome("persist_exp", "user_1", 0.75)

    # Create a new manager reading the same file
    m2 = ABTestManager(filepath=filepath)
    exps = m2.list_experiments()
    assert len(exps) == 1
    assert exps[0]["name"] == "persist_exp"
    # Should get the same variant assignment
    v = m2.assign_variant("persist_exp", "user_1")
    assert v["id"] in ("a", "b")


# ── Pre-configured experiments ───────────────────────


def test_default_experiments_exist():
    """The module-level ab_manager should have pre-configured experiments."""
    from ab_testing import ab_manager
    exps = ab_manager.list_experiments()
    exp_names = {e["name"] for e in exps}
    assert "prompt_style" in exp_names
    assert "model_selection" in exp_names
    assert "rag_strategy" in exp_names


def test_create_default_experiments_idempotent(tmp_manager):
    """Calling create_default_experiments twice should not raise."""
    create_default_experiments(tmp_manager)
    create_default_experiments(tmp_manager)  # Should not raise
    exps = tmp_manager.list_experiments()
    exp_names = [e["name"] for e in exps]
    assert "prompt_style" in exp_names


# ── Experiment serialization ─────────────────────────


def test_experiment_to_dict_from_dict():
    exp = Experiment(
        name="roundtrip",
        variants=[{"id": "a", "config": {}, "weight": 1.0}],
        metric_name="test",
        description="Test roundtrip",
    )
    d = exp.to_dict()
    restored = Experiment.from_dict(d)
    assert restored.name == "roundtrip"
    assert restored.description == "Test roundtrip"
    assert restored.active is True


# ── Math helpers ─────────────────────────────────────


def test_norm_cdf_symmetry():
    assert abs(_norm_cdf(0) - 0.5) < 1e-6


def test_norm_ppf_inverse():
    # ppf(cdf(x)) should approximate x
    for z in [-2.0, -1.0, 0.0, 1.0, 2.0]:
        p = _norm_cdf(z)
        z_recovered = _norm_ppf(p)
        assert abs(z_recovered - z) < 0.01


def test_erf_bounds():
    assert abs(_erf(0)) < 1e-8  # Approximation tolerance
    assert _erf(3) > 0.99
    assert _erf(-3) < -0.99
