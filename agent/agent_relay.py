"""
Inter-agent communication and task decomposition for vinhlong360 Knowledge Agent.

Provides a message bus, shared scratchpad, pattern-based task decomposer, and
relay orchestrator so that specialist agents can collaborate on complex queries
that span multiple categories (e.g. "lịch trình + so sánh").

Architecture:
    MessageBus       -> thread-safe message queues between named agents
    SharedScratchpad -> session-scoped key/value store for intermediate results
    TaskDecomposer   -> pattern-based query decomposition into SubTasks
    RelayOrchestrator-> execute decomposed tasks (parallel where possible)
    RelayLog         -> bounded audit log of inter-agent messages
"""

from __future__ import annotations

import collections
import json
import logging
import re
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MAX_QUEUE_SIZE = 100
_MAX_SESSIONS = 50
_SESSION_TTL = 3600.0  # 1 hour
_SUBTASK_TIMEOUT = 60.0
_RELAY_LOG_MAXLEN = 1000

# Known agent names (must match orchestrator.py)
AGENT_NAMES = frozenset({
    "SearchAgent",
    "RecommendAgent",
    "ItineraryAgent",
    "CompareAgent",
    "GeneralAgent",
})


# ---------------------------------------------------------------------------
# MessageType enum
# ---------------------------------------------------------------------------

class MessageType(str, Enum):
    REQUEST = "request"
    RESPONSE = "response"
    DELEGATE = "delegate"
    INFORM = "inform"
    ESCALATE = "escalate"


# ---------------------------------------------------------------------------
# AgentMessage dataclass
# ---------------------------------------------------------------------------

@dataclass
class AgentMessage:
    """A single message exchanged between agents."""

    sender: str
    receiver: str
    message_type: MessageType
    payload: dict
    session_id: str
    priority: int = 3  # 1=highest, 5=lowest
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    parent_id: Optional[str] = None

    def __post_init__(self) -> None:
        if not 1 <= self.priority <= 5:
            raise ValueError(f"priority must be 1-5, got {self.priority}")

    def to_dict(self) -> dict:
        """Serialize to a plain dict."""
        return {
            "id": self.id,
            "sender": self.sender,
            "receiver": self.receiver,
            "message_type": self.message_type.value,
            "payload": self.payload,
            "priority": self.priority,
            "timestamp": self.timestamp,
            "parent_id": self.parent_id,
            "session_id": self.session_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> AgentMessage:
        """Deserialize from a plain dict."""
        return cls(
            id=data["id"],
            sender=data["sender"],
            receiver=data["receiver"],
            message_type=MessageType(data["message_type"]),
            payload=data["payload"],
            priority=data["priority"],
            timestamp=data["timestamp"],
            parent_id=data.get("parent_id"),
            session_id=data["session_id"],
        )


# ---------------------------------------------------------------------------
# MessageBus -- thread-safe inter-agent queues
# ---------------------------------------------------------------------------

class MessageBus:
    """Thread-safe message bus with per-agent bounded queues.

    Each agent has a deque of at most ``_MAX_QUEUE_SIZE`` messages.
    When the queue is full, the lowest-priority (highest number) message
    is evicted to make room (FIFO within same priority).
    """

    def __init__(self) -> None:
        self._queues: dict[str, collections.deque[AgentMessage]] = {}
        self._lock = threading.Lock()

    def _ensure_queue(self, agent_name: str) -> collections.deque[AgentMessage]:
        """Return (and lazily create) the queue for *agent_name*."""
        if agent_name not in self._queues:
            self._queues[agent_name] = collections.deque()
        return self._queues[agent_name]

    def _evict_if_full(self, q: collections.deque[AgentMessage]) -> None:
        """Evict the lowest-priority (highest number) oldest message if full."""
        if len(q) < _MAX_QUEUE_SIZE:
            return
        # Find index of message with highest priority number (lowest priority)
        worst_idx = 0
        worst_pri = q[0].priority
        for i, msg in enumerate(q):
            if msg.priority > worst_pri:
                worst_pri = msg.priority
                worst_idx = i
        # Remove by rotating the deque
        q.rotate(-worst_idx)
        q.popleft()
        q.rotate(worst_idx)

    def send(self, message: AgentMessage) -> None:
        """Put *message* into the receiver's queue."""
        with self._lock:
            q = self._ensure_queue(message.receiver)
            self._evict_if_full(q)
            q.append(message)
        logger.debug(
            "MessageBus: %s -> %s [%s]",
            message.sender,
            message.receiver,
            message.message_type.value,
        )

    def receive(
        self,
        agent_name: str,
        timeout: float = 0,
    ) -> Optional[AgentMessage]:
        """Non-blocking get of the next message for *agent_name*.

        Parameters
        ----------
        agent_name : str
            Name of the receiving agent.
        timeout : float
            If > 0, wait up to this many seconds for a message.
            If 0, return immediately (None if empty).

        Returns
        -------
        AgentMessage or None
        """
        deadline = time.monotonic() + timeout if timeout > 0 else 0.0

        while True:
            with self._lock:
                q = self._ensure_queue(agent_name)
                if q:
                    return q.popleft()
            if time.monotonic() >= deadline:
                return None
            time.sleep(0.01)  # brief sleep to avoid busy-wait

    def receive_all(self, agent_name: str) -> list[AgentMessage]:
        """Drain and return all messages for *agent_name*."""
        with self._lock:
            q = self._ensure_queue(agent_name)
            messages = list(q)
            q.clear()
            return messages

    def broadcast(
        self,
        sender: str,
        payload: dict,
        session_id: str,
    ) -> None:
        """Send an INFORM message to every known agent (except sender)."""
        for name in AGENT_NAMES:
            if name == sender:
                continue
            msg = AgentMessage(
                sender=sender,
                receiver=name,
                message_type=MessageType.INFORM,
                payload=payload,
                session_id=session_id,
                priority=4,
            )
            self.send(msg)


# ---------------------------------------------------------------------------
# SharedScratchpad -- session-scoped key/value store
# ---------------------------------------------------------------------------

class SharedScratchpad:
    """Thread-safe session-scoped scratchpad for intermediate results.

    Sessions auto-expire after ``_SESSION_TTL`` seconds.
    At most ``_MAX_SESSIONS`` are kept (LRU eviction).
    """

    def __init__(self) -> None:
        # session_id -> {key: (value, agent_name, timestamp)}
        self._data: dict[str, dict[str, tuple[Any, str, float]]] = {}
        # session_id -> last_access timestamp (for LRU)
        self._access: dict[str, float] = {}
        self._lock = threading.Lock()

    def _touch(self, session_id: str) -> None:
        """Update last-access time (must hold lock)."""
        self._access[session_id] = time.time()

    def _auto_cleanup(self) -> None:
        """Remove expired sessions and enforce LRU cap (must hold lock)."""
        now = time.time()

        # Remove expired
        expired = [
            sid for sid, ts in self._access.items()
            if now - ts > _SESSION_TTL
        ]
        for sid in expired:
            self._data.pop(sid, None)
            self._access.pop(sid, None)

        # LRU eviction
        while len(self._data) > _MAX_SESSIONS:
            oldest_sid = min(self._access, key=self._access.get)  # type: ignore[arg-type]
            self._data.pop(oldest_sid, None)
            self._access.pop(oldest_sid, None)

    def write(
        self,
        session_id: str,
        key: str,
        value: Any,
        agent_name: str,
    ) -> None:
        """Store an intermediate result."""
        with self._lock:
            self._auto_cleanup()
            if session_id not in self._data:
                self._data[session_id] = {}
            self._data[session_id][key] = (value, agent_name, time.time())
            self._touch(session_id)

    def read(self, session_id: str, key: str) -> Any:
        """Read a value; returns None if not found."""
        with self._lock:
            session = self._data.get(session_id)
            if session is None:
                return None
            entry = session.get(key)
            if entry is None:
                return None
            self._touch(session_id)
            return entry[0]  # value

    def read_all(self, session_id: str) -> dict:
        """Return all key/value pairs for a session."""
        with self._lock:
            session = self._data.get(session_id)
            if session is None:
                return {}
            self._touch(session_id)
            return {k: v[0] for k, v in session.items()}

    def cleanup(self, session_id: str) -> None:
        """Remove all data for a session."""
        with self._lock:
            self._data.pop(session_id, None)
            self._access.pop(session_id, None)


# ---------------------------------------------------------------------------
# SubTask dataclass
# ---------------------------------------------------------------------------

class SubTaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


@dataclass
class SubTask:
    """A single unit of work produced by TaskDecomposer."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""
    assigned_agent: str = "GeneralAgent"
    dependencies: list[str] = field(default_factory=list)
    status: SubTaskStatus = SubTaskStatus.PENDING
    result: Optional[str] = None


# ---------------------------------------------------------------------------
# TaskDecomposer -- pattern-based (NOT LLM) query decomposition
# ---------------------------------------------------------------------------

# Pre-compiled keyword detectors for multi-category queries.
_KW_ITINERARY = re.compile(
    r"(?:lịch\s*trình|kế\s*hoạch|hành\s*trình|sắp\s*xếp\s*chuyến|"
    r"chuyến\s*đi|\d+\s*ngày|ngày\s*\d|tour\s*\d|plan|schedule|itinerary)",
    re.IGNORECASE | re.UNICODE,
)
_KW_COMPARE = re.compile(
    r"(?:so\s*sánh|khác\s*(?:nhau|biệt|gì)|compare|difference|"
    r"hay\s*hơn|hơn\s*(?:không|chứ|nhỉ)|versus|vs\.?\b|"
    r"nên\s*(?:chọn|đi)\s*(?:.*?)\s*hay\s)",
    re.IGNORECASE | re.UNICODE,
)
_KW_SEARCH = re.compile(
    r"(?:tìm|search|tra\s*cứu|thông\s*tin\s*về|cho\s*(?:tôi|mình)\s*biết)",
    re.IGNORECASE | re.UNICODE,
)
_KW_RECOMMEND = re.compile(
    r"(?:gợi\s*ý|đề\s*xuất|recommend|suggest|nên\s*(?:đi|ăn|mua|thử|ghé)|"
    r"có\s*gì\s*(?:hay|ngon|đẹp|thú\s*vị|nổi\s*bật)|top\s*\d|best|"
    r"nên\s*đi\b)",
    re.IGNORECASE | re.UNICODE,
)

# Mapping from keyword detector -> agent name
_KW_AGENT_MAP: list[tuple[re.Pattern, str]] = [
    (_KW_ITINERARY, "ItineraryAgent"),
    (_KW_COMPARE, "CompareAgent"),
    (_KW_SEARCH, "SearchAgent"),
    (_KW_RECOMMEND, "RecommendAgent"),
]

# Decomposition rules: (frozenset of agent names detected) -> ordered list of agents
_DECOMPOSITION_RULES: dict[frozenset[str], list[str]] = {
    frozenset({"ItineraryAgent", "CompareAgent"}): ["ItineraryAgent", "CompareAgent"],
    frozenset({"SearchAgent", "RecommendAgent"}): ["SearchAgent", "RecommendAgent"],
    frozenset({"CompareAgent", "RecommendAgent"}): ["CompareAgent", "RecommendAgent"],
}

# Category string -> primary agent
_CATEGORY_AGENT_MAP: dict[str, str] = {
    "search": "SearchAgent",
    "recommendation": "RecommendAgent",
    "itinerary": "ItineraryAgent",
    "comparison": "CompareAgent",
    "general": "GeneralAgent",
}


class TaskDecomposer:
    """Break complex queries into sub-tasks using pattern matching.

    Decomposition is purely rule-based (no LLM calls).  Multi-category
    queries are detected by checking which keyword groups fire, then
    mapped to predefined agent chains.
    """

    def decompose(self, query: str, category: str) -> list[SubTask]:
        """Decompose *query* into a list of SubTasks.

        Parameters
        ----------
        query : str
            The user's raw query.
        category : str
            The primary category as classified by QueryRouter.

        Returns
        -------
        list[SubTask]
            One or more subtasks.  A single-element list means no
            decomposition was needed.
        """
        text = query.strip()
        if not text:
            return [self._single_task(text, category)]

        # Detect which keyword groups fire
        detected_agents: list[str] = []
        for pattern, agent_name in _KW_AGENT_MAP:
            if pattern.search(text):
                detected_agents.append(agent_name)

        # Need at least 2 distinct agents for decomposition
        unique_agents = list(dict.fromkeys(detected_agents))  # preserve order, dedupe
        if len(unique_agents) < 2:
            return [self._single_task(text, category)]

        # Check decomposition rules for known pairs
        agent_set = frozenset(unique_agents)
        for rule_key, agent_chain in _DECOMPOSITION_RULES.items():
            if rule_key.issubset(agent_set):
                return self._build_chain(text, agent_chain)

        # No matching rule -- try to build a chain from the first two detected
        return self._build_chain(text, unique_agents[:2])

    @staticmethod
    def _single_task(query: str, category: str) -> SubTask:
        """Create a single subtask (no decomposition)."""
        agent = _CATEGORY_AGENT_MAP.get(category, "GeneralAgent")
        return SubTask(
            description=query,
            assigned_agent=agent,
        )

    @staticmethod
    def _build_chain(query: str, agents: list[str]) -> list[SubTask]:
        """Build a dependency chain of subtasks.

        The first task has no dependencies.  Each subsequent task depends
        on the previous one (sequential pipeline).
        """
        subtasks: list[SubTask] = []
        for i, agent in enumerate(agents):
            deps = [subtasks[i - 1].id] if i > 0 else []
            subtasks.append(SubTask(
                description=query,
                assigned_agent=agent,
                dependencies=deps,
            ))
        return subtasks

    @staticmethod
    def merge_results(subtasks: list[SubTask]) -> str:
        """Combine results from completed subtasks into a coherent response."""
        parts: list[str] = []
        for st in subtasks:
            if st.status == SubTaskStatus.DONE and st.result:
                parts.append(st.result.strip())
            elif st.status == SubTaskStatus.FAILED:
                logger.warning(
                    "SubTask %s (%s) failed, skipping in merge",
                    st.id,
                    st.assigned_agent,
                )
        if not parts:
            return "Xin lỗi, tôi không thể xử lý yêu cầu này lúc này."

        if len(parts) == 1:
            return parts[0]

        # Join multiple results with a separator
        return "\n\n---\n\n".join(parts)


# ---------------------------------------------------------------------------
# RelayOrchestrator -- decompose, assign, execute, merge
# ---------------------------------------------------------------------------

class RelayOrchestrator:
    """Execute decomposed queries across specialist agents.

    Steps:
        1. decompose query into subtasks
        2. assign subtasks to agents
        3. execute (parallel where no dependencies, sequential otherwise)
        4. merge results

    Uses ``ThreadPoolExecutor`` for parallel sub-task execution.
    """

    def __init__(
        self,
        decomposer: Optional[TaskDecomposer] = None,
        bus: Optional[MessageBus] = None,
        pad: Optional[SharedScratchpad] = None,
        log: Optional[RelayLog] = None,  # type: ignore[name-defined]  # forward ref
    ) -> None:
        self._decomposer = decomposer or task_decomposer
        self._bus = bus or message_bus
        self._pad = pad or scratchpad
        self._log = log  # set after relay_log is created

    def execute(
        self,
        query: str,
        session_id: str,
        call_tool_fn: Callable[[str, dict], str],
        llm_call_fn: Callable[[list[dict], list[dict], float], Any],
    ) -> dict:
        """Run a full relay-orchestrated turn.

        Parameters
        ----------
        query : str
            The user's query.
        session_id : str
            Session identifier.
        call_tool_fn : callable(name, args) -> str
            Tool execution function.
        llm_call_fn : callable(messages, tools, temperature) -> response
            LLM call function.

        Returns
        -------
        dict with keys: reply, tools_used, subtasks, agents_used
        """
        # Import orchestrator lazily to avoid circular imports
        try:
            from orchestrator import QueryRouter, Orchestrator
        except ImportError:
            from agent.orchestrator import QueryRouter, Orchestrator

        router = QueryRouter()
        category = router.classify(query)

        # Decompose
        try:
            subtasks = self._decomposer.decompose(query, category.value)
        except Exception:
            logger.warning("Decomposition failed, running as single task", exc_info=True)
            subtasks = [SubTask(
                description=query,
                assigned_agent=_CATEGORY_AGENT_MAP.get(category.value, "GeneralAgent"),
            )]

        if len(subtasks) == 1:
            # Single task -- no relay needed, run directly
            return self._execute_single(
                subtasks[0], query, session_id, call_tool_fn, llm_call_fn,
            )

        # Multi-task execution
        return self._execute_multi(
            subtasks, query, session_id, call_tool_fn, llm_call_fn,
        )

    def _execute_single(
        self,
        subtask: SubTask,
        query: str,
        session_id: str,
        call_tool_fn: Callable,
        llm_call_fn: Callable,
    ) -> dict:
        """Execute a single subtask without relay overhead."""
        try:
            from orchestrator import Orchestrator
        except ImportError:
            from agent.orchestrator import Orchestrator

        orch = Orchestrator()

        try:
            from tools import SYSTEM_PROMPT
        except ImportError:
            from agent.tools import SYSTEM_PROMPT

        subtask.status = SubTaskStatus.RUNNING
        try:
            result = orch.run(
                message=query,
                history=[],
                session_id=session_id,
                base_system_prompt=SYSTEM_PROMPT,
                call_tool_fn=call_tool_fn,
                llm_call_fn=llm_call_fn,
            )
            subtask.status = SubTaskStatus.DONE
            subtask.result = result.get("reply", "")

            return {
                "reply": result.get("reply", ""),
                "tools_used": result.get("tools_used", []),
                "subtasks": [self._subtask_to_dict(subtask)],
                "agents_used": [result.get("agent_used", subtask.assigned_agent)],
            }
        except Exception:
            subtask.status = SubTaskStatus.FAILED
            logger.error("Single subtask execution failed", exc_info=True)
            return {
                "reply": "Xin lỗi, tôi không thể xử lý yêu cầu này lúc này.",
                "tools_used": [],
                "subtasks": [self._subtask_to_dict(subtask)],
                "agents_used": [subtask.assigned_agent],
            }

    def _execute_multi(
        self,
        subtasks: list[SubTask],
        query: str,
        session_id: str,
        call_tool_fn: Callable,
        llm_call_fn: Callable,
    ) -> dict:
        """Execute multiple subtasks, respecting dependency order."""
        try:
            from orchestrator import Orchestrator
        except ImportError:
            from agent.orchestrator import Orchestrator

        orch = Orchestrator()

        try:
            from tools import SYSTEM_PROMPT
        except ImportError:
            from agent.tools import SYSTEM_PROMPT

        all_tools_used: list[str] = []
        agents_used: list[str] = []
        completed: dict[str, SubTask] = {}  # id -> subtask

        # Build dependency graph
        id_to_task = {st.id: st for st in subtasks}

        # Execute in waves: each wave contains tasks whose deps are all done
        max_waves = len(subtasks) + 1  # safety cap
        for _wave in range(max_waves):
            # Find ready tasks
            ready = [
                st for st in subtasks
                if st.status == SubTaskStatus.PENDING
                and all(d in completed for d in st.dependencies)
            ]
            if not ready:
                break

            # Execute ready tasks in parallel
            with ThreadPoolExecutor(max_workers=len(ready)) as pool:
                futures = {}
                for st in ready:
                    st.status = SubTaskStatus.RUNNING

                    # Notify via message bus
                    msg = AgentMessage(
                        sender="RelayOrchestrator",
                        receiver=st.assigned_agent,
                        message_type=MessageType.DELEGATE,
                        payload={"query": query, "subtask_id": st.id},
                        session_id=session_id,
                    )
                    self._bus.send(msg)
                    if self._log:
                        self._log.record(msg)

                    futures[pool.submit(
                        self._run_subtask,
                        st, query, session_id, orch,
                        SYSTEM_PROMPT, call_tool_fn, llm_call_fn,
                    )] = st

                for future in as_completed(futures, timeout=_SUBTASK_TIMEOUT):
                    st = futures[future]
                    try:
                        result = future.result(timeout=_SUBTASK_TIMEOUT)
                        st.status = SubTaskStatus.DONE
                        st.result = result.get("reply", "")
                        all_tools_used.extend(result.get("tools_used", []))
                        agents_used.append(result.get("agent_used", st.assigned_agent))

                        # Write result to scratchpad
                        self._pad.write(
                            session_id,
                            f"subtask_{st.id}",
                            st.result,
                            st.assigned_agent,
                        )

                        # Send RESPONSE back
                        resp_msg = AgentMessage(
                            sender=st.assigned_agent,
                            receiver="RelayOrchestrator",
                            message_type=MessageType.RESPONSE,
                            payload={
                                "subtask_id": st.id,
                                "status": "done",
                            },
                            session_id=session_id,
                            parent_id=st.id,
                        )
                        self._bus.send(resp_msg)
                        if self._log:
                            self._log.record(resp_msg)

                    except Exception:
                        st.status = SubTaskStatus.FAILED
                        logger.error(
                            "SubTask %s (%s) failed",
                            st.id, st.assigned_agent,
                            exc_info=True,
                        )

                    completed[st.id] = st

        # Merge
        merged = self._decomposer.merge_results(subtasks)

        return {
            "reply": merged,
            "tools_used": all_tools_used,
            "subtasks": [self._subtask_to_dict(st) for st in subtasks],
            "agents_used": list(dict.fromkeys(agents_used)),  # dedupe, preserve order
        }

    @staticmethod
    def _run_subtask(
        subtask: SubTask,
        query: str,
        session_id: str,
        orch: Any,
        system_prompt: str,
        call_tool_fn: Callable,
        llm_call_fn: Callable,
    ) -> dict:
        """Run a single subtask via the Orchestrator (called in a thread)."""
        from agent.orchestrator import _CATEGORY_AGENTS, QueryCategory

        # Find the matching category for this agent
        agent_spec = None
        for cat, spec in _CATEGORY_AGENTS.items():
            if spec.name == subtask.assigned_agent:
                agent_spec = spec
                break

        if agent_spec is None:
            # Fallback to GeneralAgent
            agent_spec = _CATEGORY_AGENTS[QueryCategory.GENERAL]

        messages = orch.build_specialist_messages(
            message=query,
            history=[],
            agent_spec=agent_spec,
            base_system_prompt=system_prompt,
        )
        tools = orch.filter_tools(agent_spec)

        result = orch._agent_loop(
            messages=messages,
            tools=tools,
            temperature=agent_spec.temperature,
            max_rounds=agent_spec.max_rounds,
            max_tool_calls=15,
            call_tool_fn=call_tool_fn,
            llm_call_fn=llm_call_fn,
        )
        result["agent_used"] = agent_spec.name
        return result

    @staticmethod
    def _subtask_to_dict(st: SubTask) -> dict:
        """Serialize a SubTask to a plain dict."""
        return {
            "id": st.id,
            "description": st.description,
            "assigned_agent": st.assigned_agent,
            "dependencies": st.dependencies,
            "status": st.status.value,
            "result": st.result,
        }


# ---------------------------------------------------------------------------
# RelayLog -- bounded audit log of inter-agent messages
# ---------------------------------------------------------------------------

class RelayLog:
    """Thread-safe, bounded log of inter-agent messages.

    Keeps at most ``_RELAY_LOG_MAXLEN`` entries (FIFO eviction).
    """

    def __init__(self, maxlen: int = _RELAY_LOG_MAXLEN) -> None:
        self._records: list[dict] = []
        self._maxlen = maxlen
        self._lock = threading.Lock()

    def record(self, message: AgentMessage) -> None:
        """Log an inter-agent message."""
        entry = message.to_dict()
        with self._lock:
            self._records.append(entry)
            if len(self._records) > self._maxlen:
                self._records = self._records[-self._maxlen:]

    def recent(self, n: int = 50) -> list[dict]:
        """Return the *n* most recent logged messages."""
        with self._lock:
            return list(self._records[-n:])

    def stats(self) -> dict:
        """Return message counts by type and by agent pair.

        Returns
        -------
        dict with keys:
            by_type       : dict[str, int]
            by_agent_pair : dict[str, int]  (format: "sender->receiver")
            total         : int
        """
        with self._lock:
            by_type: dict[str, int] = {}
            by_pair: dict[str, int] = {}
            for rec in self._records:
                mt = rec.get("message_type", "unknown")
                by_type[mt] = by_type.get(mt, 0) + 1

                pair = f"{rec.get('sender', '?')}->{rec.get('receiver', '?')}"
                by_pair[pair] = by_pair.get(pair, 0) + 1

            return {
                "by_type": by_type,
                "by_agent_pair": by_pair,
                "total": len(self._records),
            }


# ---------------------------------------------------------------------------
# Module-level singletons
# ---------------------------------------------------------------------------

message_bus = MessageBus()
scratchpad = SharedScratchpad()
task_decomposer = TaskDecomposer()
relay_log = RelayLog()

# RelayOrchestrator needs relay_log, which is now created
relay_orchestrator = RelayOrchestrator(
    decomposer=task_decomposer,
    bus=message_bus,
    pad=scratchpad,
    log=relay_log,
)


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("agent_relay -- unit tests")
    print("=" * 60)

    # -- MessageType ---------------------------------------------------------
    print("\n--- MessageType ---")
    for mt in MessageType:
        print(f"  {mt.name} = {mt.value}")

    # -- AgentMessage --------------------------------------------------------
    print("\n--- AgentMessage ---")
    msg = AgentMessage(
        sender="SearchAgent",
        receiver="CompareAgent",
        message_type=MessageType.REQUEST,
        payload={"query": "test query"},
        session_id="sess-1",
        priority=2,
    )
    d = msg.to_dict()
    print(f"  to_dict keys: {sorted(d.keys())}")
    msg2 = AgentMessage.from_dict(d)
    print(f"  round-trip OK: {msg2.id == msg.id and msg2.sender == msg.sender}")

    # -- MessageBus ----------------------------------------------------------
    print("\n--- MessageBus ---")
    bus = MessageBus()
    bus.send(AgentMessage(
        sender="SearchAgent",
        receiver="CompareAgent",
        message_type=MessageType.INFORM,
        payload={"data": "hello"},
        session_id="sess-1",
    ))
    bus.send(AgentMessage(
        sender="RecommendAgent",
        receiver="CompareAgent",
        message_type=MessageType.INFORM,
        payload={"data": "world"},
        session_id="sess-1",
    ))
    received = bus.receive("CompareAgent")
    print(f"  receive 1: {received.sender if received else None}")
    all_msgs = bus.receive_all("CompareAgent")
    print(f"  receive_all: {len(all_msgs)} messages")
    empty = bus.receive("CompareAgent")
    print(f"  empty after drain: {empty is None}")

    bus.broadcast("SearchAgent", {"alert": "new data"}, "sess-2")
    for name in sorted(AGENT_NAMES):
        if name == "SearchAgent":
            continue
        msgs = bus.receive_all(name)
        print(f"  broadcast to {name}: {len(msgs)} messages")

    # -- SharedScratchpad ----------------------------------------------------
    print("\n--- SharedScratchpad ---")
    pad = SharedScratchpad()
    pad.write("sess-1", "key1", "value1", "SearchAgent")
    pad.write("sess-1", "key2", {"nested": True}, "CompareAgent")
    print(f"  read key1: {pad.read('sess-1', 'key1')}")
    print(f"  read_all: {pad.read_all('sess-1')}")
    pad.cleanup("sess-1")
    print(f"  after cleanup: {pad.read_all('sess-1')}")

    # -- TaskDecomposer ------------------------------------------------------
    print("\n--- TaskDecomposer ---")
    td = TaskDecomposer()

    test_queries = [
        ("Lịch trình 2 ngày và so sánh các khu vực", "itinerary"),
        ("Tìm thông tin và gợi ý món ngon", "search"),
        ("So sánh Vĩnh Long Bến Tre và gợi ý nên đi đâu", "comparison"),
        ("Lịch trình 3 ngày Vĩnh Long", "itinerary"),
        ("Xin chào", "general"),
    ]

    for query, cat in test_queries:
        subtasks = td.decompose(query, cat)
        agents = [st.assigned_agent for st in subtasks]
        deps = [st.dependencies for st in subtasks]
        print(f"  '{query}'")
        print(f"    -> {len(subtasks)} subtask(s): {agents}, deps: {deps}")

    # -- Merge results -------------------------------------------------------
    print("\n--- merge_results ---")
    tasks = [
        SubTask(description="q", assigned_agent="SearchAgent",
                status=SubTaskStatus.DONE, result="Found 3 places."),
        SubTask(description="q", assigned_agent="RecommendAgent",
                status=SubTaskStatus.DONE, result="I recommend place A."),
    ]
    merged = td.merge_results(tasks)
    print(f"  merged: {merged[:80]}...")

    tasks_with_fail = [
        SubTask(description="q", assigned_agent="SearchAgent",
                status=SubTaskStatus.FAILED),
        SubTask(description="q", assigned_agent="RecommendAgent",
                status=SubTaskStatus.DONE, result="Fallback result."),
    ]
    merged2 = td.merge_results(tasks_with_fail)
    print(f"  partial: {merged2[:80]}")

    # -- RelayLog ------------------------------------------------------------
    print("\n--- RelayLog ---")
    rlog = RelayLog()
    for i in range(5):
        rlog.record(AgentMessage(
            sender="SearchAgent",
            receiver="CompareAgent",
            message_type=MessageType.REQUEST,
            payload={"i": i},
            session_id="sess-1",
        ))
    rlog.record(AgentMessage(
        sender="CompareAgent",
        receiver="SearchAgent",
        message_type=MessageType.RESPONSE,
        payload={"ok": True},
        session_id="sess-1",
    ))
    print(f"  recent(3): {len(rlog.recent(3))} entries")
    stats = rlog.stats()
    print(f"  stats: {stats}")

    print("\n" + "=" * 60)
    print("All agent_relay tests completed.")
