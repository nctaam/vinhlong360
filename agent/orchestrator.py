"""
Multi-agent orchestrator for vinhlong360 Knowledge Agent.

Routes incoming queries to specialized sub-agents, each with a focused
tool subset and tailored system prompt.  The orchestrator does NOT call
the LLM directly -- it prepares messages and the tool whitelist, then
the caller (server.py) feeds them to the LLM client.

Architecture:
    QueryRouter  -> classifies query into a category (no LLM call)
    AgentSpec    -> dataclass describing a specialist agent
    Orchestrator -> picks specialist, builds messages, runs via caller-supplied fns
"""

from __future__ import annotations

import logging
import re
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional
import unicodedata

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Query categories
# ---------------------------------------------------------------------------

class QueryCategory(str, Enum):
    SEARCH = "search"
    RECOMMENDATION = "recommendation"
    ITINERARY = "itinerary"
    COMPARISON = "comparison"
    GENERAL = "general"


# ---------------------------------------------------------------------------
# QueryRouter -- fast keyword + pattern classifier (no LLM call)
# ---------------------------------------------------------------------------

# Pre-compiled patterns per category, ordered by priority (first match wins).
# Each entry: (compiled regex, category).
_ROUTE_PATTERNS: list[tuple[re.Pattern, QueryCategory]] = []


def _build_patterns() -> list[tuple[re.Pattern, QueryCategory]]:
    """Build and return compiled routing patterns."""
    specs: list[tuple[str, QueryCategory]] = [
        # --- Itinerary (highest priority -- overlaps with recommendation) ---
        (
            r"(?:lịch\s*trình|kế\s*hoạch|plan|schedule|hành\s*trình|"
            r"ngày\s*\d|(\d+)\s*ngày|lên\s*kế|sắp\s*xếp\s*chuyến|"
            r"chuyến\s*đi|tour\s*\d|đi\s*chơi\s*\d|itinerary)",
            QueryCategory.ITINERARY,
        ),
        # --- Comparison ---
        (
            r"(?:so\s*sánh|khác\s*(?:nhau|biệt|gì)|compare|difference|"
            r"hay\s*hơn|hơn\s*(?:không|chứ|nhỉ)|versus|vs\.?\b|"
            r"nên\s*(?:chọn|đi)\s*(?:.*?)\s*hay\s)",
            QueryCategory.COMPARISON,
        ),
        # --- Recommendation ---
        (
            r"(?:gợi\s*ý|đề\s*xuất|recommend|suggest|nên\s*(?:đi|ăn|mua|thử|xem|ghé|tham\s*quan)|"
            r"có\s*gì\s*(?:hay|ngon|đẹp|thú\s*vị|nổi\s*bật|đặc\s*biệt|nên)|"
            r"(?:ở|tại)\s*đâu\s*(?:ngon|hay|đẹp|vui)|"
            r"top\s*\d|best|must\s*(?:try|visit|see)|"
            r"đặc\s*sản\s*(?:gì|nào)|món\s*(?:gì|nào)\s*ngon)",
            QueryCategory.RECOMMENDATION,
        ),
        # --- Search ---
        (
            r"(?:tìm|search|tra\s*cứu|thông\s*tin\s*về|cho\s*(?:tôi|mình)\s*biết|"
            r"(?:là|ở)\s*(?:gì|đâu|nào)|giới\s*thiệu|chi\s*tiết|"
            r"lịch\s*sử|nguồn\s*gốc|xuất\s*xứ|"
            r"(?:mấy|bao\s*nhiêu)\s*(?:giờ|km|phút)|"
            r"bao\s*nhiêu|"
            r"(?:giá|vé)\s*(?:bao\s*nhiêu|là)|"
            r"gần\s*(?:đó|đây|chùa|cồn|cổn|nhà|chợ|bến|sông|cầu|đền|miếu)|"
            r"quanh\s*(?:đây|khu\s*vực)|"
            r"weather|thời\s*tiết|"
            r"(?:ai|người)\s*(?:là|nào)\b)",
            QueryCategory.SEARCH,
        ),
    ]
    return [(re.compile(pat, re.IGNORECASE | re.UNICODE), cat) for pat, cat in specs]


_ROUTE_PATTERNS = _build_patterns()


def _strip_diacritics(text: str) -> str:
    """Remove Vietnamese diacritics for fuzzy matching fallback."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


# ASCII-friendly fallback patterns (no diacritics)
def _build_ascii_patterns() -> list[tuple[re.Pattern, QueryCategory]]:
    """Build diacritic-stripped patterns for partial-diacritic queries."""
    specs: list[tuple[str, QueryCategory]] = [
        (r"(?:lich\s*trinh|ke\s*hoach|hanh\s*trinh|chuyen\s*di|tour\s*\d|di\s*choi\s*\d)", QueryCategory.ITINERARY),
        (r"(?:so\s*sanh|khac\s*nhau|compare|hay\s*hon|hon\s*khong|versus|vs\.?\b)", QueryCategory.COMPARISON),
        (r"(?:goi\s*y|de\s*xuat|recommend|nen\s*(?:di|an|mua|thu|ghe)|co\s*gi\s*(?:hay|ngon|dep)|dac\s*san)", QueryCategory.RECOMMENDATION),
        (r"(?:tim|search|tra\s*cuu|thong\s*tin\s*ve|cho\s*(?:toi|minh)\s*biet|gan\s*(?:do|day)|thoi\s*tiet)", QueryCategory.SEARCH),
    ]
    return [(re.compile(pat, re.IGNORECASE | re.UNICODE), cat) for pat, cat in specs]


_ASCII_ROUTE_PATTERNS = _build_ascii_patterns()


class QueryRouter:
    """Classify a user query into a QueryCategory using keyword/pattern matching.

    Thread-safe, stateless, no side effects.
    """

    @staticmethod
    def classify(message: str) -> QueryCategory:
        """Return the best-matching category for *message*.

        Falls back to ``QueryCategory.GENERAL`` when no pattern matches.
        Two-pass matching: first with original diacritics, then with
        diacritics stripped for partial-diacritic queries (common when
        autocorrect only fixes proper nouns but not verbs).
        """
        text = message.strip()
        if not text:
            return QueryCategory.GENERAL

        # Pass 1: match with diacritics (highest precision)
        for pattern, category in _ROUTE_PATTERNS:
            if pattern.search(text):
                return category

        # Pass 2: match with diacritics stripped (fuzzy fallback)
        ascii_text = _strip_diacritics(text)
        for pattern, category in _ASCII_ROUTE_PATTERNS:
            if pattern.search(ascii_text):
                return category

        return QueryCategory.GENERAL


# ---------------------------------------------------------------------------
# AgentSpec -- description of a specialist agent
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AgentSpec:
    """Immutable specification for a specialist agent."""

    name: str
    system_prompt_addon: str  # appended to the base system prompt
    allowed_tools: list[str]  # tool function names this agent may use
    max_rounds: int = 8       # max ReAct loop iterations
    temperature: float = 0.3  # LLM sampling temperature
    use_mini: bool = False    # route to MODEL_MINI for faster responses


# ---------------------------------------------------------------------------
# Pre-configured specialist agents
# ---------------------------------------------------------------------------

SEARCH_AGENT = AgentSpec(
    name="SearchAgent",
    system_prompt_addon=(
        "\n\n## Vai trò chuyên biệt\n"
        "Bạn là SearchAgent chuyên về tra cứu thông tin. "
        "Tập trung vào việc tìm kiếm chính xác, trả về dữ liệu chi tiết, "
        "và trích dẫn nguồn đáng tin cậy. Nếu knowledge base không đủ, "
        "dùng web_search bổ sung. Luôn gọi suggest_followups cuối cùng."
    ),
    allowed_tools=[
        "search", "entity_detail", "nearby_entities", "web_search",
        "suggest_followups",
    ],
    max_rounds=3,
    temperature=0.2,
    use_mini=True,
)

RECOMMEND_AGENT = AgentSpec(
    name="RecommendAgent",
    system_prompt_addon=(
        "\n\n## Vai trò chuyên biệt\n"
        "Bạn là RecommendAgent chuyên về gợi ý và đề xuất. "
        "Tập trung vào sở thích người dùng, mùa vụ hiện tại, "
        "và xếp hạng theo mức độ phù hợp. Luôn kiểm tra seasonal_now "
        "để ưu tiên trải nghiệm đang mùa. Gọi suggest_followups cuối cùng."
    ),
    allowed_tools=[
        "search", "entity_detail", "seasonal_now", "suggest_followups",
    ],
    max_rounds=4,
    temperature=0.4,
)

ITINERARY_AGENT = AgentSpec(
    name="ItineraryAgent",
    system_prompt_addon=(
        "\n\n## Vai trò chuyên biệt\n"
        "Bạn là ItineraryAgent chuyên về lập lịch trình du lịch. "
        "Tập trung vào tạo lịch trình chi tiết theo timeline, "
        "kiểm tra thời tiết và mùa vụ, kết hợp các điểm đến hợp lý. "
        "Ưu tiên generate_itinerary cho lịch trình tùy chỉnh, "
        "hoặc list_itineraries + itinerary_detail cho lịch trình có sẵn. "
        "Gọi suggest_followups cuối cùng."
    ),
    allowed_tools=[
        "search", "entity_detail", "list_itineraries", "itinerary_detail",
        "generate_itinerary", "weather", "seasonal_now", "suggest_followups",
    ],
    max_rounds=8,
    temperature=0.3,
)

COMPARE_AGENT = AgentSpec(
    name="CompareAgent",
    system_prompt_addon=(
        "\n\n## Vai trò chuyên biệt\n"
        "Bạn là CompareAgent chuyên về so sánh và phân tích. "
        "Tập trung vào so sánh khách quan, trình bày bảng/danh sách "
        "rõ ràng, nêu ưu nhược điểm từng lựa chọn. "
        "Dùng compare_areas cho so sánh khu vực, stats cho số liệu tổng quan. "
        "Gọi suggest_followups cuối cùng."
    ),
    allowed_tools=[
        "search", "entity_detail", "compare_areas", "places_in_area",
        "stats", "suggest_followups",
    ],
    max_rounds=4,
    temperature=0.2,
)

GENERAL_AGENT = AgentSpec(
    name="GeneralAgent",
    system_prompt_addon="",  # uses base prompt as-is
    allowed_tools=[
        "search", "entity_detail", "seasonal_now", "list_itineraries",
        "itinerary_detail", "places_in_area", "stats", "compare_areas",
        "nearby_entities", "web_search", "suggest_followups",
        "generate_itinerary", "weather",
    ],
    max_rounds=4,
    temperature=0.3,
    use_mini=True,
)

# Map category -> specialist
_CATEGORY_AGENTS: dict[QueryCategory, AgentSpec] = {
    QueryCategory.SEARCH: SEARCH_AGENT,
    QueryCategory.RECOMMENDATION: RECOMMEND_AGENT,
    QueryCategory.ITINERARY: ITINERARY_AGENT,
    QueryCategory.COMPARISON: COMPARE_AGENT,
    QueryCategory.GENERAL: GENERAL_AGENT,
}


# ---------------------------------------------------------------------------
# Handoff log -- lightweight, thread-safe, bounded
# ---------------------------------------------------------------------------

@dataclass
class HandoffRecord:
    """Single entry in the handoff log."""
    timestamp: float
    session_id: str
    query_snippet: str  # first 120 chars
    category: str
    agent_name: str


class HandoffLog:
    """Thread-safe, bounded log of agent handoffs.

    Keeps at most *maxlen* records (FIFO eviction).
    """

    def __init__(self, maxlen: int = 500) -> None:
        self._records: list[HandoffRecord] = []
        self._maxlen = maxlen
        self._lock = threading.Lock()

    def record(
        self,
        session_id: str,
        query: str,
        category: QueryCategory,
        agent: AgentSpec,
    ) -> None:
        entry = HandoffRecord(
            timestamp=time.time(),
            session_id=session_id,
            query_snippet=query[:120],
            category=category.value,
            agent_name=agent.name,
        )
        with self._lock:
            self._records.append(entry)
            if len(self._records) > self._maxlen:
                self._records = self._records[-self._maxlen:]

    def recent(self, n: int = 20) -> list[HandoffRecord]:
        with self._lock:
            return list(self._records[-n:])

    def stats(self) -> dict[str, int]:
        """Return count of handoffs per agent."""
        with self._lock:
            counts: dict[str, int] = {}
            for r in self._records:
                counts[r.agent_name] = counts.get(r.agent_name, 0) + 1
            return counts


# Module-level log instance (shared, thread-safe)
handoff_log = HandoffLog()


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class Orchestrator:
    """Routes queries to specialist agents, builds messages, and runs them.

    Stateless per call -- all mutable state lives in the HandoffLog or is
    passed explicitly by the caller.
    """

    def __init__(self, tools_list: list[dict[str, Any]] | None = None) -> None:
        """
        Parameters
        ----------
        tools_list : list[dict], optional
            Full OpenAI-format tool definitions. If *None*, they are imported
            from ``agent.tools.TOOLS`` at first use.
        """
        self._all_tools: list[dict[str, Any]] | None = tools_list
        self._router = QueryRouter()

    # -- lazy import of TOOLS to avoid circular imports at module load --------
    @property
    def all_tools(self) -> list[dict[str, Any]]:
        if self._all_tools is None:
            try:
                from tools import TOOLS  # noqa: WPS433
            except ImportError:
                from agent.tools import TOOLS  # noqa: WPS433
            self._all_tools = TOOLS
        return self._all_tools

    # -- public API -----------------------------------------------------------

    def route(self, message: str) -> tuple[QueryCategory, AgentSpec]:
        """Classify *message* and return the matching specialist."""
        category = self._router.classify(message)
        agent = _CATEGORY_AGENTS[category]
        return category, agent

    def filter_tools(self, agent: AgentSpec) -> list[dict[str, Any]]:
        """Return the subset of tool definitions allowed for *agent*."""
        allowed = set(agent.allowed_tools)
        return [t for t in self.all_tools if t["function"]["name"] in allowed]

    def build_specialist_messages(
        self,
        message: str,
        history: list[dict[str, str]],
        agent_spec: AgentSpec,
        base_system_prompt: str,
    ) -> list[dict[str, str]]:
        """Construct the message list for a specialist agent.

        Appends the specialist's addon and a handoff note to the system
        prompt, keeps the last 20 history messages, and appends the user
        query.
        """
        # Handoff note in Vietnamese
        _DOMAIN_MAP = {
            "SearchAgent": "tra cứu thông tin",
            "RecommendAgent": "gợi ý và đề xuất",
            "ItineraryAgent": "lập lịch trình du lịch",
            "CompareAgent": "so sánh và phân tích",
            "GeneralAgent": "hỗ trợ du lịch tổng hợp",
        }
        _FOCUS_MAP = {
            "SearchAgent": "tìm kiếm chính xác và trích dẫn nguồn",
            "RecommendAgent": "đề xuất phù hợp sở thích và mùa vụ",
            "ItineraryAgent": "lịch trình chi tiết, thời tiết, logistics",
            "CompareAgent": "so sánh khách quan, bảng biểu rõ ràng",
            "GeneralAgent": "trả lời đa dạng mọi chủ đề du lịch",
        }

        domain = _DOMAIN_MAP.get(agent_spec.name, "hỗ trợ du lịch")
        focus = _FOCUS_MAP.get(agent_spec.name, "trả lời chính xác")

        handoff_note = (
            f"\n\n---\n"
            f"Bạn là **{agent_spec.name}** chuyên về {domain}. "
            f"Tập trung vào {focus}."
        )

        system_content = base_system_prompt + agent_spec.system_prompt_addon + handoff_note

        messages: list[dict[str, str]] = [
            {"role": "system", "content": system_content},
        ]

        # History (bounded)
        if history:
            messages.extend(history[-20:])

        messages.append({"role": "user", "content": message})
        return messages

    def run(
        self,
        message: str,
        history: list[dict[str, str]],
        session_id: str,
        base_system_prompt: str,
        call_tool_fn: Callable[[str, dict], str],
        llm_call_fn: Callable[[list[dict], list[dict], float], Any],
        *,
        max_tool_calls: int = 15,
        get_params_fn: Callable[[str], dict] | None = None,
        tool_executor: Any = None,
        tool_order_fn: Callable[[str], list] | None = None,
    ) -> dict[str, Any]:
        """Orchestrate a full agent turn.

        Parameters
        ----------
        message : str
            The user's query.
        history : list[dict]
            Conversation history (role/content dicts).
        session_id : str
            Current session identifier.
        base_system_prompt : str
            The base SYSTEM_PROMPT from tools.py.
        call_tool_fn : callable(name, args) -> str
            Function that executes a tool and returns JSON string result.
        llm_call_fn : callable(messages, tools, temperature) -> response
            Function that calls the LLM.  Must return an object whose
            ``.choices[0].message`` has ``.content`` and ``.tool_calls``.
        max_tool_calls : int
            Hard cap on total tool invocations.

        Returns
        -------
        dict with keys:
            reply        : str   -- final text answer
            tools_used   : list[str]
            suggestions  : list[str]
            agent_used   : str   -- name of the specialist that handled it
            category     : str   -- detected query category
            fallback     : bool  -- True if we fell back to GeneralAgent
        """
        import json  # local import to keep top-level lightweight

        category, agent = self.route(message)
        handoff_log.record(session_id, message, category, agent)
        logger.info(
            "Orchestrator routed query",
            extra={
                "session_id": session_id,
                "category": category.value,
                "agent": agent.name,
                "use_mini": agent.use_mini,
            },
        )

        # Resolve tuned params (self_optimizer) for this category, falling back
        # to the specialist's hardcoded defaults. Previously the tuned params
        # computed by self_optimizer were never read — this wires them in.
        _temp = agent.temperature
        _rounds = agent.max_rounds
        _tool_cap = max_tool_calls
        if get_params_fn is not None:
            try:
                tuned = get_params_fn(category.value)
                if tuned:
                    _temp = tuned.get("temperature", _temp)
                    _rounds = int(tuned.get("max_rounds", _rounds))
                    _tool_cap = int(tuned.get("max_tool_calls", _tool_cap))
            except Exception:
                logger.debug("get_params_fn failed for category %s, using defaults", category.value, exc_info=True)

        # Try specialist first, fall back to general on failure.
        # Outer try/except catches the case where BOTH agents fail —
        # returns a safe fallback instead of propagating to the caller.
        try:
            for attempt, current_agent in enumerate([agent, GENERAL_AGENT]):
                if attempt == 1 and agent.name == GENERAL_AGENT.name:
                    break  # already tried general, don't retry

                messages = self.build_specialist_messages(
                    message, history, current_agent, base_system_prompt,
                )
                tools = self.filter_tools(current_agent)

                # Build allowed tool name set for validation inside the loop
                _allowed_names = {t["function"]["name"] for t in tools}

                # Reorder tools by learned effectiveness (tool_weight_optimizer).
                # Order is a soft signal for the model; safe + reversible.
                if tool_order_fn is not None:
                    try:
                        order = tool_order_fn(category.value)
                        rank = {name: i for i, name in enumerate(order)}
                        tools.sort(key=lambda t: rank.get(t["function"]["name"], 999))
                    except Exception:
                        logger.debug("tool_order_fn failed for category %s, using default order", category.value, exc_info=True)

                try:
                    result = self._agent_loop(
                        messages=messages,
                        tools=tools,
                        temperature=_temp,
                        max_rounds=_rounds,
                        max_tool_calls=_tool_cap,
                        call_tool_fn=call_tool_fn,
                        llm_call_fn=llm_call_fn,
                        tool_executor=tool_executor,
                        allowed_tool_names=_allowed_names,
                    )
                    return {
                        "reply": result["reply"],
                        "tools_used": result["tools_used"],
                        "suggestions": result["suggestions"],
                        "agent_used": current_agent.name,
                        "category": category.value,
                        "fallback": attempt > 0,
                        "use_mini": current_agent.use_mini,
                    }
                except Exception:
                    if attempt == 0:
                        logger.warning(
                            "Specialist failed, falling back to GeneralAgent",
                            extra={"agent": current_agent.name},
                            exc_info=True,
                        )
                        continue
                    raise
        except Exception:
            logger.error(
                "All agents failed for query",
                extra={"session_id": session_id, "category": category.value},
                exc_info=True,
            )

        return {
            "reply": "Xin lỗi, tôi không thể trả lời câu hỏi này lúc này.",
            "tools_used": [],
            "suggestions": [],
            "agent_used": "none",
            "category": category.value,
            "fallback": True,
        }

    # -- private helpers ------------------------------------------------------

    # Maximum total size (bytes) of message content before truncation kicks in.
    _MAX_MESSAGES_BYTES = 128 * 1024  # 128 KB

    @staticmethod
    def _agent_loop(
        messages: list[dict],
        tools: list[dict],
        temperature: float,
        max_rounds: int,
        max_tool_calls: int,
        call_tool_fn: Callable[[str, dict], str],
        llm_call_fn: Callable[[list[dict], list[dict], float], Any],
        tool_executor: Any = None,
        allowed_tool_names: set | None = None,
        total_timeout: float = 120.0,
    ) -> dict[str, Any]:
        """ReAct-style agent loop.  Returns dict(reply, tools_used, suggestions).

        When ``tool_executor`` (a ParallelToolExecutor) is supplied and a round
        contains more than one tool call, the independent calls run concurrently
        instead of serially — cutting latency on multi-tool rounds.
        """
        import json

        def _post_process(fn_name, result):
            """Collect suggestions + emit empty-search self-correction hint.
            Returns True if an empty-search hint should be injected."""
            if fn_name == "suggest_followups":
                try:
                    data = json.loads(result)
                    sug = data.get("suggestions", [])
                    if sug:
                        suggestions.clear()
                        suggestions.extend(sug)
                except Exception:
                    logger.debug("Failed to parse suggest_followups result", exc_info=True)
            if fn_name == "search":
                try:
                    parsed = json.loads(result)
                    if isinstance(parsed, list) and len(parsed) == 0:
                        return True
                except Exception:
                    logger.debug("Failed to parse search result for empty-check", exc_info=True)
            return False

        tools_used: list[str] = []
        suggestions: list[str] = []
        total_tool_calls = 0
        empty_results_count = 0
        last_content = ""
        _loop_start = time.monotonic()

        for _round in range(max_rounds):
            # Wall-clock timeout guard — break if total elapsed exceeds budget.
            elapsed = time.monotonic() - _loop_start
            if elapsed > total_timeout:
                logger.warning(
                    "Agent loop wall-clock timeout after %.1fs (limit %.0fs, round %d)",
                    elapsed, total_timeout, _round,
                )
                break

            response = llm_call_fn(messages, tools, temperature)
            msg = response.choices[0].message

            if not msg.tool_calls:
                last_content = msg.content or ""
                break

            messages.append(msg)

            # Partition this round's calls: execute up to the global cap, stub the rest.
            pending: list[dict] = []
            for tc in msg.tool_calls:
                if total_tool_calls >= max_tool_calls:
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps({
                            "error": "Tool call limit reached. Please respond with available information.",
                        }),
                    })
                    continue
                try:
                    fn_args = json.loads(tc.function.arguments)
                except Exception:
                    logger.warning("Failed to parse tool call arguments for %s, using empty dict", tc.function.name, exc_info=True)
                    fn_args = {}
                fn_name = tc.function.name
                if allowed_tool_names and fn_name not in allowed_tool_names:
                    logger.warning("LLM hallucinated unknown tool: %s", fn_name)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps({
                            "error": f"Unknown tool '{fn_name}'. Use only: {', '.join(sorted(allowed_tool_names))}",
                        }),
                    })
                    continue
                tools_used.append(f"{fn_name}({json.dumps(fn_args, ensure_ascii=False)})")
                total_tool_calls += 1
                pending.append({"id": tc.id, "name": fn_name, "args": fn_args})

            if not pending:
                continue

            # Execute — parallel for multi-call rounds when an executor is available.
            if tool_executor is not None and len(pending) > 1:
                try:
                    exec_results = tool_executor.execute_smart(pending)
                except Exception:
                    logger.warning("Parallel tool executor failed, falling back to serial execution", exc_info=True)
                    exec_results = [
                        {"id": c["id"], "name": c["name"], "result": call_tool_fn(c["name"], c["args"])}
                        for c in pending
                    ]
            else:
                exec_results = [
                    {"id": c["id"], "name": c["name"], "result": call_tool_fn(c["name"], c["args"])}
                    for c in pending
                ]

            saw_empty_search = False
            for r in exec_results:
                messages.append({
                    "role": "tool",
                    "tool_call_id": r["id"],
                    "content": r["result"],
                })
                if _post_process(r["name"], r["result"]):
                    saw_empty_search = True

            # Self-correction on empty search (at most twice per turn)
            if saw_empty_search:
                empty_results_count += 1
                if empty_results_count <= 2:
                    messages.append({
                        "role": "system",
                        "content": (
                            "[Observation]: Search returned 0 results. "
                            "Try broader keywords, remove filters, "
                            "or use web_search as fallback."
                        ),
                    })

            # Message size guard — truncate oldest tool results when
            # total payload exceeds the threshold to prevent unbounded growth.
            total_bytes = sum(len(str(m.get("content", ""))) for m in messages if isinstance(m, dict))
            if total_bytes > Orchestrator._MAX_MESSAGES_BYTES:
                for m in messages:
                    if isinstance(m, dict) and m.get("role") == "tool":
                        content = m.get("content", "")
                        if len(content) > 500:
                            m["content"] = content[:500] + "…[truncated]"
                logger.debug("Truncated old tool results (%d bytes over limit)", total_bytes)
        else:
            # Rounds exhausted while the model was still calling tools. Instead of
            # discarding the gathered tool results and returning a canned apology,
            # force ONE final synthesis turn with no tools so the model must answer
            # from the evidence it already collected.
            if not last_content:
                try:
                    messages.append({
                        "role": "system",
                        "content": (
                            "[Hệ thống]: Đã đạt giới hạn số vòng suy luận. "
                            "Hãy tổng hợp câu trả lời tốt nhất có thể TỪ thông tin "
                            "đã thu thập ở trên. KHÔNG gọi thêm công cụ nào nữa, "
                            "trả lời trực tiếp bằng tiếng Việt."
                        ),
                    })
                    final_resp = llm_call_fn(messages, [], temperature)
                    last_content = (final_resp.choices[0].message.content or "").strip()
                except Exception:
                    logger.warning("Final synthesis LLM call failed after rounds exhausted", exc_info=True)
                    last_content = ""
            if not last_content:
                last_content = "Xin lỗi, tôi không thể trả lời đầy đủ câu hỏi này."

        if not last_content:
            last_content = "Xin lỗi, tôi không thể trả lời đầy đủ câu hỏi này."

        return {
            "reply": last_content,
            "tools_used": tools_used,
            "suggestions": suggestions,
        }


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("Orchestrator -- QueryRouter test")
    print("=" * 60)

    router = QueryRouter()

    test_cases = [
        # (query, expected_category)
        # Search
        ("Chùa Vĩnh Tràng ở đâu?", "search"),
        ("Thông tin về cam sành Tam Bình", "search"),
        ("Giá vé vào cổn An Bình bao nhiêu?", "search"),
        ("Gần chùa Vam Ray có gì?", "search"),
        ("Thời tiết Vĩnh Long hôm nay", "search"),
        ("Ai là người sáng lập làng nghề gốm?", "search"),
        # Recommendation
        ("Nên đi đâu ở Vĩnh Long?", "recommendation"),
        ("Gợi ý món ngon Bến Tre", "recommendation"),
        ("Top 5 điểm tham quan nổi bật", "recommendation"),
        ("Có gì hay ở Trà Vinh?", "recommendation"),
        ("Đặc sản nào ngon nhất?", "recommendation"),
        # Itinerary
        ("Lịch trình 2 ngày Vĩnh Long", "itinerary"),
        ("Lên kế hoạch đi chơi 3 ngày", "itinerary"),
        ("Plan a 1-day tour", "itinerary"),
        ("Sắp xếp chuyến đi cuối tuần", "itinerary"),
        # Comparison
        ("So sánh Vĩnh Long và Bến Tre", "comparison"),
        ("Bến Tre hay Trà Vinh hay hơn?", "comparison"),
        ("Khác nhau giữa 3 khu vực", "comparison"),
        ("Nên chọn Vĩnh Long hay Bến Tre?", "comparison"),
        # General
        ("Xin chào", "general"),
        ("Cảm ơn bạn", "general"),
        ("Bạn là ai?", "general"),
    ]

    passed = 0
    failed = 0
    for query, expected in test_cases:
        result = router.classify(query)
        status = "PASS" if result.value == expected else "FAIL"
        if status == "PASS":
            passed += 1
        else:
            failed += 1
        print(f"  [{status}] '{query}' -> {result.value} (expected: {expected})")

    print(f"\nResults: {passed}/{len(test_cases)} passed, {failed} failed")

    print("\n" + "=" * 60)
    print("Orchestrator -- route() test")
    print("=" * 60)

    orchestrator = Orchestrator(tools_list=[
        {"type": "function", "function": {"name": "search"}},
        {"type": "function", "function": {"name": "entity_detail"}},
        {"type": "function", "function": {"name": "nearby_entities"}},
        {"type": "function", "function": {"name": "web_search"}},
        {"type": "function", "function": {"name": "suggest_followups"}},
        {"type": "function", "function": {"name": "seasonal_now"}},
        {"type": "function", "function": {"name": "list_itineraries"}},
        {"type": "function", "function": {"name": "itinerary_detail"}},
        {"type": "function", "function": {"name": "generate_itinerary"}},
        {"type": "function", "function": {"name": "weather"}},
        {"type": "function", "function": {"name": "compare_areas"}},
        {"type": "function", "function": {"name": "places_in_area"}},
        {"type": "function", "function": {"name": "stats"}},
    ])

    for query, expected in test_cases:
        category, agent = orchestrator.route(query)
        tools = orchestrator.filter_tools(agent)
        tool_names = [t["function"]["name"] for t in tools]
        print(f"  '{query}'")
        print(f"    -> {agent.name} | tools: {tool_names}")

    print("\n" + "=" * 60)
    print("Orchestrator -- build_specialist_messages() test")
    print("=" * 60)

    base_prompt = "Base system prompt for testing."
    cat, agent = orchestrator.route("Gợi ý món ngon Bến Tre")
    msgs = orchestrator.build_specialist_messages(
        message="Gợi ý món ngon Bến Tre",
        history=[
            {"role": "user", "content": "Xin chào"},
            {"role": "assistant", "content": "Chào bạn!"},
        ],
        agent_spec=agent,
        base_system_prompt=base_prompt,
    )
    print(f"  Agent: {agent.name}")
    print(f"  Messages count: {len(msgs)}")
    print(f"  System prompt length: {len(msgs[0]['content'])} chars")
    print(f"  System contains handoff note: {'SearchAgent' in msgs[0]['content'] or 'RecommendAgent' in msgs[0]['content']}")
    print(f"  Last message role: {msgs[-1]['role']}")
    print(f"  Last message content: {msgs[-1]['content']}")

    print("\n" + "=" * 60)
    print("HandoffLog test")
    print("=" * 60)

    handoff_log.record("sess-1", "test query 1", QueryCategory.SEARCH, SEARCH_AGENT)
    handoff_log.record("sess-1", "test query 2", QueryCategory.ITINERARY, ITINERARY_AGENT)
    handoff_log.record("sess-2", "test query 3", QueryCategory.COMPARISON, COMPARE_AGENT)

    print(f"  Recent: {len(handoff_log.recent())} records")
    print(f"  Stats: {handoff_log.stats()}")

    print("\nAll tests completed.")
