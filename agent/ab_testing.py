"""
vinhlong360 — A/B Testing Framework.

Cho phep:
  - Tao va quan ly cac experiment (prompt style, model, RAG strategy...)
  - Phan bao user vao variant (deterministic bang hash)
  - Ghi nhan ket qua (metric value)
  - Phan tich thong ke: mean, std, confidence interval, z-test / t-test
  - Persistence qua JSON file

Du lieu luu: agent/data/ab_tests.json

Usage:
  variant = ab_manager.assign_variant("prompt_style", session_id)
  # Use variant["config"]["prompt_template"] in _build_messages()
  # Later:
  ab_manager.record_outcome("prompt_style", session_id, quality_score)
"""

import hashlib
import json
import logging
import math
import os
import sys
import time
from pathlib import Path
from threading import Lock

logger = logging.getLogger(__name__)

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if hasattr(sys.stdout, "reconfigure") and sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(exist_ok=True)
AB_TESTS_FILE = DATA_DIR / "ab_tests.json"

# ---------------------------------------------------------------------------
# Normal distribution helpers (stdlib only, no scipy)
# ---------------------------------------------------------------------------

def _erf(x: float) -> float:
    """Approximation of the error function (Abramowitz & Stegun 7.1.26)."""
    sign = 1 if x >= 0 else -1
    x = abs(x)
    t = 1.0 / (1.0 + 0.3275911 * x)
    poly = t * (0.254829592
                + t * (-0.284496736
                       + t * (1.421413741
                              + t * (-1.453152027
                                     + t * 1.061405429))))
    return sign * (1.0 - poly * math.exp(-x * x))


def _norm_cdf(z: float) -> float:
    """Standard normal CDF: P(Z <= z)."""
    return 0.5 * (1.0 + _erf(z / math.sqrt(2.0)))


def _norm_ppf(p: float) -> float:
    """Inverse standard normal CDF (rational approximation, |error| < 4.5e-4).

    Uses Abramowitz & Stegun 26.2.23 for 0 < p < 1.
    """
    if p <= 0.0:
        return -math.inf
    if p >= 1.0:
        return math.inf
    if p == 0.5:
        return 0.0
    if p > 0.5:
        return -_norm_ppf(1.0 - p)
    # p < 0.5
    t = math.sqrt(-2.0 * math.log(p))
    c0, c1, c2 = 2.515517, 0.802853, 0.010328
    d1, d2, d3 = 1.432788, 0.189269, 0.001308
    return -(t - (c0 + c1 * t + c2 * t * t) / (1.0 + d1 * t + d2 * t * t + d3 * t * t * t))


# ---------------------------------------------------------------------------
# Experiment
# ---------------------------------------------------------------------------

class Experiment:
    """Describes a single A/B experiment."""

    def __init__(
        self,
        name: str,
        variants: list[dict],
        metric_name: str,
        description: str = "",
    ):
        """
        Args:
            name: Unique experiment identifier (e.g. "prompt_style").
            variants: List of variant dicts, each with:
                - "id": str   (e.g. "control", "variant_a")
                - "config": dict (arbitrary config handed to caller)
                - "weight": float (assignment probability, should sum to 1.0)
            metric_name: Human-readable metric being measured (e.g. "quality_score").
            description: Optional description.
        """
        self.name = name
        self.variants = variants
        self.metric_name = metric_name
        self.description = description
        self.active = True
        self.created_at = time.time()
        self.stopped_at: float | None = None

    # -- serialisation helpers ------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "variants": self.variants,
            "metric_name": self.metric_name,
            "description": self.description,
            "active": self.active,
            "created_at": self.created_at,
            "stopped_at": self.stopped_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Experiment":
        exp = cls(
            name=d["name"],
            variants=d["variants"],
            metric_name=d["metric_name"],
            description=d.get("description", ""),
        )
        exp.active = d.get("active", True)
        exp.created_at = d.get("created_at", time.time())
        exp.stopped_at = d.get("stopped_at")
        return exp


# ---------------------------------------------------------------------------
# ABTestManager
# ---------------------------------------------------------------------------

class ABTestManager:
    """Thread-safe manager for A/B experiments with JSON persistence."""

    def __init__(self, filepath: Path | str | None = None):
        self._filepath = Path(filepath) if filepath else AB_TESTS_FILE
        self._lock = Lock()
        # experiments: {name: Experiment}
        self._experiments: dict[str, Experiment] = {}
        # outcomes: {experiment_name: {user_id: [metric_values]}}
        self._outcomes: dict[str, dict[str, list[float]]] = {}
        # assignments: {experiment_name: {user_id: variant_id}}
        self._assignments: dict[str, dict[str, str]] = {}
        self._load()

    # -- persistence ----------------------------------------------------------

    def _load(self):
        """Load experiment state from JSON file."""
        if not self._filepath.exists():
            return
        try:
            with open(self._filepath, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return
        for ed in data.get("experiments", []):
            exp = Experiment.from_dict(ed)
            self._experiments[exp.name] = exp
        self._outcomes = data.get("outcomes", {})
        self._assignments = data.get("assignments", {})

    def _save(self):
        """Persist current state to JSON file (caller must hold _lock)."""
        data = {
            "experiments": [e.to_dict() for e in self._experiments.values()],
            "outcomes": self._outcomes,
            "assignments": self._assignments,
        }
        self._filepath.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._filepath.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp.replace(self._filepath)

    # -- public API -----------------------------------------------------------

    def create_experiment(
        self,
        name: str,
        variants: list[dict],
        metric_name: str,
        description: str = "",
    ) -> Experiment:
        """Register a new experiment.

        Args:
            name: Unique experiment name.
            variants: List of {"id", "config", "weight"} dicts.
            metric_name: Name of the metric being tracked.
            description: Optional description.

        Returns:
            The created Experiment.

        Raises:
            ValueError: If experiment already exists or variants are invalid.
        """
        if not variants or len(variants) < 2:
            raise ValueError("Need at least 2 variants")
        with self._lock:
            if name in self._experiments:
                raise ValueError(f"Experiment '{name}' already exists")
            exp = Experiment(name, variants, metric_name, description)
            self._experiments[name] = exp
            self._outcomes[name] = {}
            self._assignments[name] = {}
            self._save()
            return exp

    def assign_variant(self, experiment_name: str, user_id: str) -> dict:
        """Deterministically assign a user to a variant.

        Uses hash(user_id + experiment_name) so the same user always gets the
        same variant within an experiment, while getting independent assignments
        across different experiments.

        Args:
            experiment_name: Name of the experiment.
            user_id: Unique user / session identifier.

        Returns:
            The variant dict {"id", "config", "weight"} for this user.

        Raises:
            KeyError: If experiment does not exist.
        """
        with self._lock:
            exp = self._get_experiment(experiment_name)

            # Return cached assignment if already decided
            cached_vid = self._assignments.get(experiment_name, {}).get(user_id)
            if cached_vid is not None:
                for v in exp.variants:
                    if v["id"] == cached_vid:
                        return dict(v)

            # Deterministic assignment via hash
            seed = f"{user_id}:{experiment_name}"
            h = hashlib.sha256(seed.encode("utf-8")).hexdigest()
            bucket = int(h[:8], 16) / 0xFFFFFFFF  # [0, 1]

            cumulative = 0.0
            chosen = exp.variants[-1]  # fallback
            for v in exp.variants:
                cumulative += v.get("weight", 1.0 / len(exp.variants))
                if bucket < cumulative:
                    chosen = v
                    break

            self._assignments.setdefault(experiment_name, {})[user_id] = chosen["id"]
            self._save()
            return dict(chosen)

    def record_outcome(
        self, experiment_name: str, user_id: str, metric_value: float
    ):
        """Record a metric observation for a user in an experiment.

        Args:
            experiment_name: Name of the experiment.
            user_id: Unique user / session identifier.
            metric_value: Observed metric value (e.g. quality score 0-1, latency ms).

        Raises:
            KeyError: If experiment does not exist.
        """
        with self._lock:
            self._get_experiment(experiment_name)  # validate existence
            bucket = self._outcomes.setdefault(experiment_name, {})
            values = bucket.setdefault(user_id, [])
            values.append(float(metric_value))
            if len(values) > 100:
                bucket[user_id] = values[-100:]
            self._save()

    def get_results(self, experiment_name: str) -> dict:
        """Return per-variant statistics for an experiment.

        Returns:
            {
                "experiment": str,
                "metric_name": str,
                "active": bool,
                "variants": {
                    "control": {
                        "count": int,
                        "mean": float,
                        "std_dev": float,
                        "confidence_interval_95": [float, float],
                    },
                    ...
                }
            }

        Raises:
            KeyError: If experiment does not exist.
        """
        with self._lock:
            exp = self._get_experiment(experiment_name)
            assignments = self._assignments.get(experiment_name, {})
            outcomes = self._outcomes.get(experiment_name, {})

            # Group metric values by variant
            variant_values: dict[str, list[float]] = {v["id"]: [] for v in exp.variants}
            for uid, vid in assignments.items():
                if uid in outcomes:
                    variant_values.setdefault(vid, []).extend(outcomes[uid])

            result_variants = {}
            for vid, values in variant_values.items():
                result_variants[vid] = self._compute_stats(values)

            return {
                "experiment": experiment_name,
                "metric_name": exp.metric_name,
                "active": exp.active,
                "variants": result_variants,
            }

    def is_significant(self, experiment_name: str) -> dict:
        """Run a basic statistical significance test between the first two variants.

        Uses a z-test for binary/proportion metrics (all values are 0 or 1)
        and Welch's t-test otherwise.

        Returns:
            {
                "significant": bool,
                "p_value_approx": float,
                "winner": str | None,
                "test_used": "z-test" | "welch-t-test",
            }

        Raises:
            KeyError: If experiment does not exist.
        """
        with self._lock:
            exp = self._get_experiment(experiment_name)
            assignments = self._assignments.get(experiment_name, {})
            outcomes = self._outcomes.get(experiment_name, {})

            # Build per-variant value lists
            variant_values: dict[str, list[float]] = {v["id"]: [] for v in exp.variants}
            for uid, vid in assignments.items():
                if uid in outcomes:
                    variant_values.setdefault(vid, []).extend(outcomes[uid])

            # Need at least two variants with data
            populated = [(vid, vals) for vid, vals in variant_values.items() if len(vals) >= 2]
            if len(populated) < 2:
                return {
                    "significant": False,
                    "p_value_approx": 1.0,
                    "winner": None,
                    "test_used": "none",
                    "note": "Not enough data (need >= 2 observations per variant)",
                }

            vid_a, vals_a = populated[0]
            vid_b, vals_b = populated[1]

            # Decide test type: if all values are 0 or 1 -> z-test for proportions
            all_values = vals_a + vals_b
            is_binary = all(v == 0.0 or v == 1.0 for v in all_values)

            if is_binary:
                return self._z_test_proportions(vid_a, vals_a, vid_b, vals_b)
            else:
                return self._welch_t_test(vid_a, vals_a, vid_b, vals_b)

    def list_experiments(self) -> list[dict]:
        """Return a summary list of all experiments.

        Returns:
            List of dicts with name, metric_name, active, description, variant_count.
        """
        with self._lock:
            results = []
            for exp in self._experiments.values():
                n_outcomes = sum(
                    len(vals)
                    for vals in self._outcomes.get(exp.name, {}).values()
                )
                results.append({
                    "name": exp.name,
                    "metric_name": exp.metric_name,
                    "active": exp.active,
                    "description": exp.description,
                    "variant_count": len(exp.variants),
                    "total_outcomes": n_outcomes,
                    "created_at": exp.created_at,
                })
            return results

    def stop_experiment(self, experiment_name: str):
        """Stop an experiment. It remains visible but will not accept new assignments.

        Raises:
            KeyError: If experiment does not exist.
        """
        with self._lock:
            exp = self._get_experiment(experiment_name)
            exp.active = False
            exp.stopped_at = time.time()
            self._save()

    # -- internal helpers -----------------------------------------------------

    def _get_experiment(self, name: str) -> Experiment:
        """Return experiment or raise KeyError."""
        if name not in self._experiments:
            raise KeyError(f"Experiment '{name}' not found")
        return self._experiments[name]

    @staticmethod
    def _compute_stats(values: list[float]) -> dict:
        """Compute count, mean, std_dev, 95% confidence interval."""
        n = len(values)
        if n == 0:
            return {"count": 0, "mean": 0.0, "std_dev": 0.0, "confidence_interval_95": [0.0, 0.0]}
        mean = sum(values) / n
        if n < 2:
            return {"count": n, "mean": mean, "std_dev": 0.0, "confidence_interval_95": [mean, mean]}
        variance = sum((x - mean) ** 2 for x in values) / (n - 1)
        std_dev = math.sqrt(variance)
        z_95 = 1.96
        margin = z_95 * std_dev / math.sqrt(n)
        return {
            "count": n,
            "mean": round(mean, 6),
            "std_dev": round(std_dev, 6),
            "confidence_interval_95": [round(mean - margin, 6), round(mean + margin, 6)],
        }

    @staticmethod
    def _z_test_proportions(
        vid_a: str, vals_a: list[float],
        vid_b: str, vals_b: list[float],
    ) -> dict:
        """Two-proportion z-test (two-tailed)."""
        n_a, n_b = len(vals_a), len(vals_b)
        p_a = sum(vals_a) / n_a
        p_b = sum(vals_b) / n_b

        # Pooled proportion
        p_pool = (sum(vals_a) + sum(vals_b)) / (n_a + n_b)

        se = math.sqrt(p_pool * (1 - p_pool) * (1 / n_a + 1 / n_b)) if 0 < p_pool < 1 else 0.0

        if se == 0.0:
            return {
                "significant": False,
                "p_value_approx": 1.0,
                "winner": None,
                "test_used": "z-test",
            }

        z = (p_a - p_b) / se
        p_value = 2.0 * (1.0 - _norm_cdf(abs(z)))  # two-tailed

        significant = p_value < 0.05
        winner = None
        if significant:
            winner = vid_a if p_a > p_b else vid_b

        return {
            "significant": significant,
            "p_value_approx": round(p_value, 6),
            "winner": winner,
            "test_used": "z-test",
        }

    @staticmethod
    def _welch_t_test(
        vid_a: str, vals_a: list[float],
        vid_b: str, vals_b: list[float],
    ) -> dict:
        """Welch's t-test (two-tailed) with normal approximation for p-value.

        Uses the normal distribution as an approximation to the t-distribution.
        This is reasonable for moderate-to-large sample sizes (n >= 20) and
        provides a conservative estimate for smaller samples.
        """
        n_a, n_b = len(vals_a), len(vals_b)
        mean_a = sum(vals_a) / n_a
        mean_b = sum(vals_b) / n_b
        var_a = sum((x - mean_a) ** 2 for x in vals_a) / (n_a - 1)
        var_b = sum((x - mean_b) ** 2 for x in vals_b) / (n_b - 1)

        se = math.sqrt(var_a / n_a + var_b / n_b) if (var_a + var_b) > 0 else 0.0

        if se == 0.0:
            return {
                "significant": False,
                "p_value_approx": 1.0,
                "winner": None,
                "test_used": "welch-t-test",
            }

        t_stat = (mean_a - mean_b) / se

        # Welch-Satterthwaite degrees of freedom (informational)
        num = (var_a / n_a + var_b / n_b) ** 2
        denom = ((var_a / n_a) ** 2 / (n_a - 1) + (var_b / n_b) ** 2 / (n_b - 1))
        df = num / denom if denom > 0 else n_a + n_b - 2

        # Approximate p-value using normal CDF (conservative for small df)
        p_value = 2.0 * (1.0 - _norm_cdf(abs(t_stat)))

        significant = p_value < 0.05
        winner = None
        if significant:
            winner = vid_a if mean_a > mean_b else vid_b

        return {
            "significant": significant,
            "p_value_approx": round(p_value, 6),
            "winner": winner,
            "test_used": "welch-t-test",
            "degrees_of_freedom": round(df, 1),
        }


# ---------------------------------------------------------------------------
# Pre-configured experiments
# ---------------------------------------------------------------------------

_DEFAULT_EXPERIMENTS = [
    {
        "name": "prompt_style",
        "description": "Test concise vs detailed system prompt style for the Knowledge Agent",
        "metric_name": "quality_score",
        "variants": [
            {
                "id": "concise",
                "config": {
                    "prompt_template": "concise",
                    "system_instruction": (
                        "Ban la huong dan vien du lich Vinh Long. "
                        "Tra loi ngan gon, chinh xac."
                    ),
                },
                "weight": 0.5,
            },
            {
                "id": "detailed",
                "config": {
                    "prompt_template": "detailed",
                    "system_instruction": (
                        "Ban la huong dan vien du lich chuyen nghiep ve Vinh Long. "
                        "Hay tra loi chi tiet, co vi du cu the, dia chi, gio mo cua "
                        "va goi y them cac dia diem lien quan."
                    ),
                },
                "weight": 0.5,
            },
        ],
    },
    {
        "name": "model_selection",
        "description": "Test main model vs mini model for simple queries",
        "metric_name": "quality_score",
        "variants": [
            {
                "id": "main_model",
                "config": {"model": "cx/gpt-5.4"},
                "weight": 0.5,
            },
            {
                "id": "mini_model",
                "config": {"model": "cx/gpt-5.4-mini"},
                "weight": 0.5,
            },
        ],
    },
    {
        "name": "rag_strategy",
        "description": "Test keyword-heavy vs semantic-heavy RAG scoring weights",
        "metric_name": "relevance_score",
        "variants": [
            {
                "id": "keyword_heavy",
                "config": {
                    "keyword_weight": 0.7,
                    "semantic_weight": 0.3,
                },
                "weight": 0.5,
            },
            {
                "id": "semantic_heavy",
                "config": {
                    "keyword_weight": 0.3,
                    "semantic_weight": 0.7,
                },
                "weight": 0.5,
            },
        ],
    },
]


def create_default_experiments(manager: ABTestManager):
    """Register the pre-configured experiments if they don't already exist."""
    for exp_def in _DEFAULT_EXPERIMENTS:
        try:
            manager.create_experiment(
                name=exp_def["name"],
                variants=exp_def["variants"],
                metric_name=exp_def["metric_name"],
                description=exp_def["description"],
            )
        except ValueError:
            pass  # already exists


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

ab_manager = ABTestManager()
create_default_experiments(ab_manager)


# ---------------------------------------------------------------------------
# CLI quick-check
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import pprint

    print("=== A/B Testing Framework ===\n")

    # Show experiments
    print("Experiments:")
    for exp in ab_manager.list_experiments():
        print(f"  - {exp['name']} ({exp['metric_name']}, active={exp['active']})")

    # Demo: assign some users
    print("\nDemo assignments for 'prompt_style':")
    for uid in ["user_001", "user_002", "user_003", "user_004", "user_005"]:
        v = ab_manager.assign_variant("prompt_style", uid)
        print(f"  {uid} -> {v['id']}")

    # Record some outcomes
    import random
    random.seed(42)
    for uid in ["user_001", "user_002", "user_003", "user_004", "user_005"]:
        score = random.uniform(0.5, 1.0)
        ab_manager.record_outcome("prompt_style", uid, score)

    # Show results
    print("\nResults for 'prompt_style':")
    pprint.pprint(ab_manager.get_results("prompt_style"))

    print("\nSignificance test:")
    pprint.pprint(ab_manager.is_significant("prompt_style"))
