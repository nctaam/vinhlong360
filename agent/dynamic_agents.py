"""
vinhlong360 — Self-Creating Specialist Agent Module.

Tu dong tao va quan ly cac agent chuyen biet (dynamic agents):
  - PatternAnalyzer  — phat hien nhom cau hoi chua duoc phuc vu tot
  - AgentFactory     — tao, luu tru, (de)activate dynamic agent
  - DynamicRouter    — route query toi dynamic agent phu hop (uu tien cao)
  - AgentEvolution   — danh gia, tu deactivate, goi y merge, evolve agent

Pre-seeded agents: FoodAgent, FestivalAgent, TransportAgent.

Du lieu luu: agent/data/agents/registry.json
Thread-safe: moi class co threading.Lock rieng.
Persistence: atomic writes (ghi .tmp roi rename).
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
import uuid
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from threading import Lock

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).resolve().parent / "data" / "agents"
DATA_DIR.mkdir(parents=True, exist_ok=True)

REGISTRY_FILE = DATA_DIR / "registry.json"

DYNAMIC_AGENT_MAX = int(os.environ.get("DYNAMIC_AGENT_MAX", "10"))

# ---------------------------------------------------------------------------
# Atomic I/O helpers (same pattern as self_optimizer.py)
# ---------------------------------------------------------------------------


def _atomic_write(path: Path, data: dict | list) -> None:
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


# ---------------------------------------------------------------------------
# AgentSpec dataclass
# ---------------------------------------------------------------------------


@dataclass
class AgentSpec:
    """Mutable specification for a dynamic specialist agent."""

    agent_id: str
    name: str
    description: str
    system_prompt_addon: str
    trigger_patterns: list[str]
    tool_whitelist: list[str] | None  # None = all tools allowed
    priority: int  # higher = checked first in routing
    created_at: float
    created_by: str  # "auto" | "manual"
    performance: dict = field(default_factory=lambda: {
        "queries_handled": 0,
        "avg_score": 0.0,
        "last_used": 0.0,
    })
    active: bool = True

    # -- serialization -------------------------------------------------------

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> AgentSpec:
        # Ensure performance dict has required keys
        perf = d.get("performance", {})
        perf.setdefault("queries_handled", 0)
        perf.setdefault("avg_score", 0.0)
        perf.setdefault("last_used", 0.0)
        d["performance"] = perf
        d.setdefault("active", True)
        return cls(**d)


# ---------------------------------------------------------------------------
# PatternAnalyzer — detect recurring unhandled query patterns
# ---------------------------------------------------------------------------

# Simple Vietnamese stop words to ignore during keyword extraction
_STOP_WORDS = frozenset({
    "la", "cua", "co", "va", "o", "tai", "cho", "toi", "minh", "ban",
    "nhu", "the", "nao", "gi", "cac", "nhung", "nay", "do", "day",
    "rat", "lam", "duoc", "khong", "da", "se", "dang", "roi", "ma",
    "bao", "nhieu", "mot", "hai", "ba", "bon", "nam", "sau",
    "voi", "tu", "den", "trong", "ngoai", "tren", "duoi",
    "de", "khi", "neu", "thi", "cung", "hon", "nhat",
})


class PatternAnalyzer:
    """Analyze unhandled or low-scoring queries to suggest new agents."""

    def __init__(self) -> None:
        self._lock = Lock()

    def extract_keywords(self, queries: list[str]) -> dict[str, int]:
        """Extract keyword frequency from a list of query strings.

        Returns dict mapping keyword -> count, excluding stop words and
        tokens shorter than 2 characters.
        """
        counter: dict[str, int] = {}
        for q in queries:
            tokens = re.findall(r"[a-zA-ZÀ-ỹ]+", q.lower())
            seen = set()
            for tok in tokens:
                if tok in _STOP_WORDS or len(tok) < 2:
                    continue
                if tok not in seen:
                    counter[tok] = counter.get(tok, 0) + 1
                    seen.add(tok)
        return counter

    def _keyword_overlap(self, q1: str, q2: str) -> float:
        """Compute keyword overlap ratio between two queries."""
        t1 = {t for t in re.findall(r"[a-zA-ZÀ-ỹ]+", q1.lower())
               if t not in _STOP_WORDS and len(t) >= 2}
        t2 = {t for t in re.findall(r"[a-zA-ZÀ-ỹ]+", q2.lower())
               if t not in _STOP_WORDS and len(t) >= 2}
        if not t1 or not t2:
            return 0.0
        intersection = t1 & t2
        union = t1 | t2
        return len(intersection) / len(union) if union else 0.0

    def cluster_queries(
        self,
        queries: list[dict],
        threshold: float = 0.6,
    ) -> list[list[dict]]:
        """Group similar queries by keyword overlap.

        Each query dict should have at least a ``"text"`` key.
        Returns list of clusters, each cluster a list of query dicts.
        """
        with self._lock:
            clusters: list[list[dict]] = []
            assigned: set[int] = set()

            for i, qi in enumerate(queries):
                if i in assigned:
                    continue
                cluster = [qi]
                assigned.add(i)
                for j, qj in enumerate(queries):
                    if j in assigned:
                        continue
                    if self._keyword_overlap(qi["text"], qj["text"]) >= threshold:
                        cluster.append(qj)
                        assigned.add(j)
                clusters.append(cluster)

            return clusters

    def analyze_unhandled(self, queries: list[dict]) -> list[dict]:
        """Find recurring query patterns not well served.

        Parameters
        ----------
        queries : list[dict]
            Each dict should have keys: ``text``, ``score`` (float 0-10),
            and optionally ``tools_used``.

        Returns
        -------
        list[dict]
            Each dict: ``pattern``, ``count``, ``example_queries``,
            ``suggested_agent`` (AgentSpec).
        """
        # Filter low-scoring queries (score < 5.0)
        low_score = [q for q in queries if q.get("score", 10) < 5.0]
        if not low_score:
            return []

        clusters = self.cluster_queries(low_score, threshold=0.6)

        suggestions: list[dict] = []
        for cluster in clusters:
            if len(cluster) < 5:
                continue

            # Determine dominant keywords
            texts = [c["text"] for c in cluster]
            kw_freq = self.extract_keywords(texts)
            top_kw = sorted(kw_freq, key=kw_freq.get, reverse=True)[:5]
            if not top_kw:
                continue

            # Build trigger patterns from top keywords
            patterns = [r"\b" + re.escape(kw) + r"\b" for kw in top_kw[:3]]

            # Build suggested agent name
            agent_name = top_kw[0].capitalize() + "Agent"
            description = (
                f"Auto-suggested agent for queries about: "
                f"{', '.join(top_kw[:5])}"
            )
            prompt_addon = (
                f"\n\n## Vai tro chuyen biet\n"
                f"Ban la {agent_name} chuyen ve {', '.join(top_kw[:3])}. "
                f"Tap trung tra loi cac cau hoi lien quan den "
                f"{', '.join(top_kw[:5])}."
            )

            suggested = AgentSpec(
                agent_id=str(uuid.uuid4()),
                name=agent_name,
                description=description,
                system_prompt_addon=prompt_addon,
                trigger_patterns=patterns,
                tool_whitelist=None,
                priority=50,
                created_at=time.time(),
                created_by="auto",
            )

            suggestions.append({
                "pattern": " | ".join(top_kw[:3]),
                "count": len(cluster),
                "example_queries": texts[:5],
                "suggested_agent": suggested,
            })

        return suggestions


# ---------------------------------------------------------------------------
# AgentFactory — create, persist, manage dynamic agents
# ---------------------------------------------------------------------------


class AgentFactory:
    """Create and manage dynamic specialist agents.

    Persists to ``agent/data/agents/registry.json``.
    Max active dynamic agents: ``DYNAMIC_AGENT_MAX`` (env-configurable).
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._agents: dict[str, AgentSpec] = {}
        self._load()
        self._ensure_seeds()

    # -- persistence ---------------------------------------------------------

    def _load(self) -> None:
        raw = _load_json(REGISTRY_FILE, default={"agents": []})
        agents_list = raw.get("agents", [])
        for entry in agents_list:
            try:
                spec = AgentSpec.from_dict(entry)
                self._agents[spec.agent_id] = spec
            except Exception as e:
                logger.warning("Skipping malformed agent entry: %s", e)

    def _save(self) -> None:
        payload = {
            "agents": [a.to_dict() for a in self._agents.values()],
        }
        _atomic_write(REGISTRY_FILE, payload)

    # -- seed agents (created once on first run) -----------------------------

    def _ensure_seeds(self) -> None:
        """Create pre-seeded agents if they don't exist yet."""
        seed_names = {a.name for a in self._agents.values()}

        seeds: list[dict] = [
            {
                "name": "FoodAgent",
                "description": (
                    "Chuyen gia am thuc Vinh Long: mon an, dac san, "
                    "quan an, nha hang, banh, bun, ca dia phuong."
                ),
                "trigger_patterns": [
                    r"am\s*thuc", r"mon\s*an", r"dac\s*san",
                    r"quan\s*an", r"nha\s*hang", r"banh", r"bun",
                ],
                "system_prompt_addon": (
                    "\n\n## Vai tro chuyen biet\n"
                    "Ban la FoodAgent — chuyen gia am thuc Vinh Long. "
                    "Tap trung vao gioi thieu mon an dac san, "
                    "quan an ngon, nha hang uy tin, va cac trai nghiem "
                    "am thuc dia phuong. Luon goi y mon dac trung theo mua."
                ),
                "tool_whitelist": ["search", "entity_detail", "seasonal_now"],
                "priority": 80,
                "created_by": "manual",
            },
            {
                "name": "FestivalAgent",
                "description": (
                    "Chuyen gia le hoi va su kien truyen thong Vinh Long: "
                    "le hoi, Tet, su kien van hoa."
                ),
                "trigger_patterns": [
                    r"le\s*hoi", r"tet", r"su\s*kien",
                    r"festival", r"truyen\s*thong",
                ],
                "system_prompt_addon": (
                    "\n\n## Vai tro chuyen biet\n"
                    "Ban la FestivalAgent — chuyen gia le hoi va van hoa "
                    "Vinh Long. Tap trung vao le hoi truyen thong, "
                    "su kien van hoa, phong tuc tap quan, va lich trinh "
                    "le hoi theo mua. Cung cap thong tin chi tiet ve "
                    "thoi gian, dia diem, va y nghia cua tung le hoi."
                ),
                "tool_whitelist": None,
                "priority": 75,
                "created_by": "manual",
            },
            {
                "name": "TransportAgent",
                "description": (
                    "Chuyen gia giao thong va di chuyen tai Vinh Long: "
                    "xe, duong di, phuong tien, tau, pha."
                ),
                "trigger_patterns": [
                    r"di\s*chuyen", r"\bxe\b", r"duong\s*di",
                    r"phuong\s*tien", r"\btau\b", r"\bpha\b",
                ],
                "system_prompt_addon": (
                    "\n\n## Vai tro chuyen biet\n"
                    "Ban la TransportAgent — chuyen gia giao thong "
                    "Vinh Long. Tap trung vao huong dan di chuyen, "
                    "phuong tien cong cong, duong di, thoi gian, "
                    "chi phi, va meo di chuyen hieu qua. Bao gom "
                    "tau, pha, xe buyt, va cac tuyen duong chinh."
                ),
                "tool_whitelist": None,
                "priority": 70,
                "created_by": "manual",
            },
        ]

        changed = False
        for seed in seeds:
            if seed["name"] in seed_names:
                continue
            spec = AgentSpec(
                agent_id=str(uuid.uuid4()),
                name=seed["name"],
                description=seed["description"],
                system_prompt_addon=seed["system_prompt_addon"],
                trigger_patterns=seed["trigger_patterns"],
                tool_whitelist=seed["tool_whitelist"],
                priority=seed["priority"],
                created_at=time.time(),
                created_by=seed["created_by"],
            )
            self._agents[spec.agent_id] = spec
            changed = True
            logger.info("Seeded dynamic agent: %s", spec.name)

        if changed:
            self._save()

    # -- public API ----------------------------------------------------------

    def create_agent(
        self,
        name: str,
        description: str,
        trigger_patterns: list[str],
        system_prompt_addon: str,
        tool_whitelist: list[str] | None = None,
    ) -> AgentSpec:
        """Create a new dynamic specialist agent.

        Raises ValueError if max active agents reached.
        """
        with self._lock:
            active_count = sum(1 for a in self._agents.values() if a.active)
            if active_count >= DYNAMIC_AGENT_MAX:
                raise ValueError(
                    f"Max active dynamic agents ({DYNAMIC_AGENT_MAX}) reached. "
                    f"Deactivate an agent first."
                )

            spec = AgentSpec(
                agent_id=str(uuid.uuid4()),
                name=name,
                description=description,
                system_prompt_addon=system_prompt_addon,
                trigger_patterns=trigger_patterns,
                tool_whitelist=tool_whitelist,
                priority=50,
                created_at=time.time(),
                created_by="manual",
            )
            self._agents[spec.agent_id] = spec
            self._save()
            logger.info("Created dynamic agent: %s (%s)", name, spec.agent_id)
            return spec

    def create_from_pattern(self, pattern_analysis: dict) -> AgentSpec:
        """Auto-create a specialist from PatternAnalyzer output.

        Parameters
        ----------
        pattern_analysis : dict
            A single entry from ``PatternAnalyzer.analyze_unhandled()``.
        """
        suggested: AgentSpec = pattern_analysis["suggested_agent"]
        with self._lock:
            active_count = sum(1 for a in self._agents.values() if a.active)
            if active_count >= DYNAMIC_AGENT_MAX:
                raise ValueError(
                    f"Max active dynamic agents ({DYNAMIC_AGENT_MAX}) reached."
                )

            # Assign a fresh ID to avoid conflicts
            spec = AgentSpec(
                agent_id=str(uuid.uuid4()),
                name=suggested.name,
                description=suggested.description,
                system_prompt_addon=suggested.system_prompt_addon,
                trigger_patterns=suggested.trigger_patterns,
                tool_whitelist=suggested.tool_whitelist,
                priority=suggested.priority,
                created_at=time.time(),
                created_by="auto",
            )
            self._agents[spec.agent_id] = spec
            self._save()
            logger.info(
                "Auto-created dynamic agent from pattern: %s (%s)",
                spec.name, spec.agent_id,
            )
            return spec

    def deactivate(self, agent_id: str) -> None:
        """Disable an agent (keep for records)."""
        with self._lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                logger.warning("Agent %s not found for deactivation", agent_id)
                return
            agent.active = False
            self._save()
            logger.info("Deactivated agent: %s (%s)", agent.name, agent_id)

    def update_performance(self, agent_id: str, score: float) -> None:
        """Update running performance stats for an agent."""
        with self._lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                return
            perf = agent.performance
            n = perf["queries_handled"]
            old_avg = perf["avg_score"]
            # Incremental average
            new_n = n + 1
            new_avg = (old_avg * n + score) / new_n
            perf["queries_handled"] = new_n
            perf["avg_score"] = round(new_avg, 2)
            perf["last_used"] = time.time()
            self._save()

    def get_active_agents(self) -> list[AgentSpec]:
        """Return all active dynamic agents, sorted by priority (desc)."""
        with self._lock:
            return sorted(
                [a for a in self._agents.values() if a.active],
                key=lambda a: a.priority,
                reverse=True,
            )

    def get_agent(self, agent_id: str) -> AgentSpec | None:
        """Return an agent by ID, or None."""
        with self._lock:
            return self._agents.get(agent_id)

    def get_all_agents(self) -> list[AgentSpec]:
        """Return all agents (including inactive)."""
        with self._lock:
            return list(self._agents.values())


# ---------------------------------------------------------------------------
# DynamicRouter — route queries to matching dynamic agents
# ---------------------------------------------------------------------------


class DynamicRouter:
    """Route queries to dynamic agents by regex pattern matching.

    Checks dynamic agents first (sorted by priority desc). Returns the
    first match, or ``None`` to fall through to the existing orchestrator.
    Compiled regex patterns are cached for performance.
    """

    def __init__(self, factory: AgentFactory) -> None:
        self._factory = factory
        self._lock = Lock()
        self._pattern_cache: dict[str, re.Pattern] = {}

    def _compile(self, pattern: str) -> re.Pattern:
        """Compile and cache a regex pattern."""
        cached = self._pattern_cache.get(pattern)
        if cached is not None:
            return cached
        try:
            compiled = re.compile(pattern, re.IGNORECASE | re.UNICODE)
            self._pattern_cache[compiled.pattern] = compiled
            # Also cache under the original key
            self._pattern_cache[pattern] = compiled
            return compiled
        except re.error as e:
            logger.warning("Invalid regex pattern %r: %s", pattern, e)
            return re.compile(r"(?!)")  # never matches

    def _match_patterns(self, query: str, patterns: list[str]) -> bool:
        """Return True if *query* matches any of the regex *patterns*."""
        text = query.lower().strip()
        for pat in patterns:
            compiled = self._compile(pat)
            if compiled.search(text):
                return True
        return False

    def route(self, query: str) -> AgentSpec | None:
        """Check dynamic agents (by priority), return matching or None."""
        with self._lock:
            agents = self._factory.get_active_agents()

        for agent in agents:
            if self._match_patterns(query, agent.trigger_patterns):
                logger.debug(
                    "Dynamic route: %s matched agent %s",
                    query[:60], agent.name,
                )
                return agent

        return None


# ---------------------------------------------------------------------------
# AgentEvolution — lifecycle management, auto-deactivation, merge hints
# ---------------------------------------------------------------------------

_SEVEN_DAYS = 7 * 24 * 3600.0


class AgentEvolution:
    """Evaluate, evolve, and prune dynamic agents based on performance."""

    def __init__(self, factory: AgentFactory) -> None:
        self._factory = factory
        self._lock = Lock()

    def evaluate_agents(self) -> list[dict]:
        """Check performance of all dynamic agents.

        Returns list of dicts with keys: ``agent_id``, ``name``,
        ``status`` (ok/warning/deactivated), ``reason``.
        Auto-deactivates agents meeting deactivation criteria.
        """
        results: list[dict] = []
        now = time.time()

        with self._lock:
            for agent in self._factory.get_all_agents():
                if not agent.active:
                    continue

                perf = agent.performance
                age = now - agent.created_at

                # Rule 1: <20 queries AND >7 days old -> deactivate
                if perf["queries_handled"] < 20 and age > _SEVEN_DAYS:
                    self._factory.deactivate(agent.agent_id)
                    results.append({
                        "agent_id": agent.agent_id,
                        "name": agent.name,
                        "status": "deactivated",
                        "reason": (
                            f"Low usage ({perf['queries_handled']} queries) "
                            f"after {age / 86400:.0f} days"
                        ),
                    })
                    continue

                # Rule 2: avg_score < 3.0 -> deactivate
                if perf["queries_handled"] >= 5 and perf["avg_score"] < 3.0:
                    self._factory.deactivate(agent.agent_id)
                    results.append({
                        "agent_id": agent.agent_id,
                        "name": agent.name,
                        "status": "deactivated",
                        "reason": (
                            f"Low avg score ({perf['avg_score']:.1f}) "
                            f"over {perf['queries_handled']} queries"
                        ),
                    })
                    continue

                # Warning: low score but not enough data to deactivate
                if perf["avg_score"] < 4.0 and perf["queries_handled"] >= 3:
                    results.append({
                        "agent_id": agent.agent_id,
                        "name": agent.name,
                        "status": "warning",
                        "reason": (
                            f"Below-average score ({perf['avg_score']:.1f}), "
                            f"monitoring"
                        ),
                    })
                else:
                    results.append({
                        "agent_id": agent.agent_id,
                        "name": agent.name,
                        "status": "ok",
                        "reason": "Healthy",
                    })

        return results

    def _pattern_overlap(self, a: AgentSpec, b: AgentSpec) -> float:
        """Compute overlap ratio between two agents' trigger patterns."""
        set_a = set(a.trigger_patterns)
        set_b = set(b.trigger_patterns)
        if not set_a or not set_b:
            return 0.0
        intersection = set_a & set_b
        union = set_a | set_b
        return len(intersection) / len(union) if union else 0.0

    def suggest_merges(self) -> list[dict]:
        """Suggest merging agents with >70% trigger pattern overlap."""
        agents = self._factory.get_active_agents()
        suggestions: list[dict] = []
        seen: set[tuple[str, str]] = set()

        for i, a in enumerate(agents):
            for j, b in enumerate(agents):
                if i >= j:
                    continue
                pair = (a.agent_id, b.agent_id)
                if pair in seen:
                    continue
                seen.add(pair)

                overlap = self._pattern_overlap(a, b)
                if overlap > 0.7:
                    suggestions.append({
                        "agent_a": {"id": a.agent_id, "name": a.name},
                        "agent_b": {"id": b.agent_id, "name": b.name},
                        "overlap": round(overlap, 2),
                        "suggestion": (
                            f"Consider merging {a.name} and {b.name} "
                            f"(pattern overlap: {overlap:.0%})"
                        ),
                    })

        return suggestions

    def evolve_agent(
        self,
        agent_id: str,
        new_patterns: list[str],
        new_prompt: str,
    ) -> None:
        """Update an agent's trigger patterns and system prompt."""
        with self._lock:
            agent = self._factory.get_agent(agent_id)
            if agent is None:
                logger.warning("Agent %s not found for evolution", agent_id)
                return
            agent.trigger_patterns = new_patterns
            agent.system_prompt_addon = new_prompt
            self._factory._save()
            logger.info("Evolved agent: %s (%s)", agent.name, agent_id)

    def get_evolution_report(self) -> dict:
        """Return full agent lifecycle stats."""
        all_agents = self._factory.get_all_agents()
        active = [a for a in all_agents if a.active]
        inactive = [a for a in all_agents if not a.active]

        total_queries = sum(
            a.performance["queries_handled"] for a in all_agents
        )
        avg_scores = [
            a.performance["avg_score"]
            for a in active
            if a.performance["queries_handled"] > 0
        ]
        overall_avg = (
            round(sum(avg_scores) / len(avg_scores), 2)
            if avg_scores else 0.0
        )

        auto_created = [a for a in all_agents if a.created_by == "auto"]
        manual_created = [a for a in all_agents if a.created_by == "manual"]

        return {
            "total_agents": len(all_agents),
            "active_agents": len(active),
            "inactive_agents": len(inactive),
            "auto_created": len(auto_created),
            "manual_created": len(manual_created),
            "total_queries_handled": total_queries,
            "overall_avg_score": overall_avg,
            "merge_suggestions": self.suggest_merges(),
            "agents": [
                {
                    "agent_id": a.agent_id,
                    "name": a.name,
                    "active": a.active,
                    "created_by": a.created_by,
                    "priority": a.priority,
                    "queries_handled": a.performance["queries_handled"],
                    "avg_score": a.performance["avg_score"],
                    "trigger_patterns": a.trigger_patterns,
                }
                for a in all_agents
            ],
        }


# ---------------------------------------------------------------------------
# Module-level singletons
# ---------------------------------------------------------------------------

agent_factory = AgentFactory()
dynamic_router = DynamicRouter(agent_factory)
pattern_analyzer = PatternAnalyzer()
agent_evolution = AgentEvolution(agent_factory)


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------


def check_dynamic_route(query: str) -> dict | None:
    """Check if a dynamic agent should handle this query.

    Returns dict with ``agent_id``, ``name``, ``system_prompt_addon``,
    ``tool_whitelist``; or ``None`` if no match.
    """
    agent = dynamic_router.route(query)
    if agent is None:
        return None
    return {
        "agent_id": agent.agent_id,
        "name": agent.name,
        "system_prompt_addon": agent.system_prompt_addon,
        "tool_whitelist": agent.tool_whitelist,
        "priority": agent.priority,
    }


def get_agent_report() -> dict:
    """Full report for /system/dynamic-agents endpoint."""
    eval_results = agent_evolution.evaluate_agents()
    evolution = agent_evolution.get_evolution_report()

    return {
        "dynamic_agent_max": DYNAMIC_AGENT_MAX,
        "evaluation": eval_results,
        "evolution_report": evolution,
    }
