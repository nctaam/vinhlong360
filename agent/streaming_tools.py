"""
Progressive tool result streaming and adaptive tool selection for
vinhlong360 Knowledge Agent.

Provides:
  1. ToolResultStream   -- wrap a tool call to emit progressive partial results
  2. AdaptiveToolSelector -- early-exit rules and next-tool suggestions
  3. ToolPipeline       -- pre-defined category pipelines with conditional steps
  4. ProgressTracker    -- track multi-step progress per session
  5. StreamingToolExecutor -- execute tool calls with partial-result callbacks

Module singletons:
  tool_stream, adaptive_selector, progress_tracker, streaming_executor

Thread-safe: all mutable state guarded by threading.Lock.
"""

from __future__ import annotations

import json
import logging
import time
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass, field
from enum import Enum
from queue import Queue, Empty
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


# ======================================================================
#  1. ToolResultStream
# ======================================================================

class _StreamState(str, Enum):
    RUNNING = "running"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class _StreamEntry:
    """Internal bookkeeping for a single streaming tool call."""
    stream_id: str
    tool_name: str
    args: dict
    state: _StreamState = _StreamState.RUNNING
    partials: list[dict] = field(default_factory=list)
    final_result: str | None = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)


class ToolResultStream:
    """Wrap a tool call so that intermediate (partial) results can be
    polled while the tool executes in the background.

    For tools that return batch results (``search``, ``web_search``),
    the final result is split into chunks and queued as partials so that
    callers can display progressive output.
    """

    # Tools whose batch result (a JSON list) should be chunked.
    _CHUNKED_TOOLS = frozenset({"search", "web_search"})
    _CHUNK_SIZE = 3  # items per partial for chunked tools

    def __init__(self, max_workers: int = 4) -> None:
        self._streams: dict[str, _StreamEntry] = {}
        self._lock = threading.Lock()
        self._pool = ThreadPoolExecutor(max_workers=max_workers)

    # -- public API ---------------------------------------------------

    def start(
        self,
        tool_name: str,
        args: dict,
        call_fn: Callable[[str, dict], str],
    ) -> str:
        """Start *call_fn(tool_name, args)* in a background thread.

        Returns a ``stream_id`` that can be used to poll partial / final
        results.
        """
        stream_id = uuid.uuid4().hex[:12]
        entry = _StreamEntry(stream_id=stream_id, tool_name=tool_name, args=args)

        with self._lock:
            self._streams[stream_id] = entry

        self._pool.submit(self._run, stream_id, tool_name, args, call_fn)
        logger.debug("ToolResultStream started stream_id=%s tool=%s", stream_id, tool_name)
        return stream_id

    def get_partial(self, stream_id: str) -> dict | None:
        """Return the latest partial result dict, or *None* if nothing
        new is available yet."""
        with self._lock:
            entry = self._streams.get(stream_id)
            if entry is None or not entry.partials:
                return None
            return entry.partials[-1]

    def get_final(self, stream_id: str, timeout: float = 30.0) -> str:
        """Block until the tool finishes (up to *timeout* seconds) and
        return the full result string.

        Raises ``TimeoutError`` if the tool does not finish in time.
        Raises ``RuntimeError`` if the tool raised an exception.
        """
        deadline = time.monotonic() + timeout
        while True:
            with self._lock:
                entry = self._streams.get(stream_id)
                if entry is None:
                    raise KeyError(f"Unknown stream_id: {stream_id}")
                if entry.state == _StreamState.COMPLETE:
                    return entry.final_result  # type: ignore[return-value]
                if entry.state == _StreamState.ERROR:
                    raise RuntimeError(entry.error)

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(
                    f"Tool stream {stream_id} did not complete within {timeout}s"
                )
            time.sleep(min(0.05, remaining))

    def is_complete(self, stream_id: str) -> bool:
        with self._lock:
            entry = self._streams.get(stream_id)
            if entry is None:
                return True  # unknown id treated as done
            return entry.state != _StreamState.RUNNING

    # -- internal -----------------------------------------------------

    def _run(
        self,
        stream_id: str,
        tool_name: str,
        args: dict,
        call_fn: Callable[[str, dict], str],
    ) -> None:
        """Execute the tool and, for chunked tools, split the result
        into progressive partials."""
        try:
            result_str = call_fn(tool_name, args)

            # Emit progressive partials for batch-result tools.
            if tool_name in self._CHUNKED_TOOLS:
                self._emit_chunked_partials(stream_id, result_str)

            with self._lock:
                entry = self._streams.get(stream_id)
                if entry is not None:
                    entry.final_result = result_str
                    entry.state = _StreamState.COMPLETE
        except Exception as exc:
            with self._lock:
                entry = self._streams.get(stream_id)
                if entry is not None:
                    entry.error = str(exc)
                    entry.state = _StreamState.ERROR
            logger.warning(
                "ToolResultStream error stream_id=%s: %s",
                stream_id, exc,
            )

    def _emit_chunked_partials(self, stream_id: str, result_str: str) -> None:
        """Parse a JSON list result and emit progressive partial dicts
        containing accumulating items."""
        try:
            items = json.loads(result_str)
        except (json.JSONDecodeError, TypeError):
            return
        if not isinstance(items, list):
            return

        accumulated: list[Any] = []
        for i, item in enumerate(items):
            accumulated.append(item)
            if (i + 1) % self._CHUNK_SIZE == 0 or i == len(items) - 1:
                partial = {
                    "items": list(accumulated),
                    "count": len(accumulated),
                    "total": len(items),
                    "done": i == len(items) - 1,
                }
                with self._lock:
                    entry = self._streams.get(stream_id)
                    if entry is not None:
                        entry.partials.append(partial)


# ======================================================================
#  2. AdaptiveToolSelector
# ======================================================================

# Canonical tool ordering used for next-tool suggestions.
_TOOL_ORDER: list[str] = [
    "search",
    "entity_detail",
    "nearby_entities",
    "web_search",
    "suggest_followups",
]

# Minimum number of high-confidence results to skip web_search.
_HIGH_CONFIDENCE_THRESHOLD = 10
_CONFIDENCE_SCORE_MIN = 0.7


class AdaptiveToolSelector:
    """Decide whether additional tool calls are worthwhile and suggest
    which tool to invoke next, based on results gathered so far."""

    # -- early-exit rules -----------------------------------------------

    @staticmethod
    def should_continue(
        tools_used: list[str],
        results_so_far: list[dict],
        query: str,
    ) -> bool:
        """Return *False* when enough information has already been gathered.

        Early-exit rules:
        1. ``search`` returned >= 10 high-confidence results  -> skip ``web_search``
        2. ``entity_detail`` returned complete info            -> skip ``nearby_entities``
        3. ``suggest_followups`` already called                -> never call again
        """
        # Rule 3: suggest_followups already done -> nothing left
        if "suggest_followups" in tools_used:
            remaining = [t for t in _TOOL_ORDER if t not in tools_used]
            # Only suggest_followups or nothing remains
            if not remaining or remaining == ["suggest_followups"]:
                return False

        # Rule 1: abundant high-confidence search results
        search_results = _extract_search_results(results_so_far)
        high_conf = [
            r for r in search_results
            if r.get("confidence", r.get("score", 0)) >= _CONFIDENCE_SCORE_MIN
        ]
        if "search" in tools_used and len(high_conf) >= _HIGH_CONFIDENCE_THRESHOLD:
            # web_search would be redundant
            remaining_needed = [
                t for t in _TOOL_ORDER
                if t not in tools_used and t != "web_search"
            ]
            if not remaining_needed or remaining_needed == ["suggest_followups"]:
                return False

        # Rule 2: entity_detail returned complete info
        if "entity_detail" in tools_used:
            detail = _extract_entity_detail(results_so_far)
            if detail and _is_entity_complete(detail):
                remaining_needed = [
                    t for t in _TOOL_ORDER
                    if t not in tools_used and t != "nearby_entities"
                ]
                if not remaining_needed or remaining_needed == ["suggest_followups"]:
                    return False

        return True

    # -- next-tool suggestion -------------------------------------------

    @staticmethod
    def suggest_next_tool(
        query: str,
        tools_used: list[str],
        results: list[dict],
    ) -> str | None:
        """Return the name of the next tool to call, or *None* if nothing
        is recommended.

        Follows the canonical pattern:
            search -> entity_detail -> nearby_entities -> suggest_followups

        Skips tools that the early-exit rules have made unnecessary.
        """
        used_set = set(tools_used)

        # Step 1: search (always first)
        if "search" not in used_set:
            return "search"

        # Step 2: entity_detail (if search found something)
        search_results = _extract_search_results(results)
        if "entity_detail" not in used_set and search_results:
            return "entity_detail"

        # Step 3: web_search (only if search was insufficient)
        high_conf = [
            r for r in search_results
            if r.get("confidence", r.get("score", 0)) >= _CONFIDENCE_SCORE_MIN
        ]
        if (
            "web_search" not in used_set
            and len(high_conf) < _HIGH_CONFIDENCE_THRESHOLD
        ):
            return "web_search"

        # Step 4: nearby_entities (if entity_detail did not have full info)
        if "nearby_entities" not in used_set and "entity_detail" in used_set:
            detail = _extract_entity_detail(results)
            if not detail or not _is_entity_complete(detail):
                return "nearby_entities"

        # Step 5: suggest_followups (always last)
        if "suggest_followups" not in used_set:
            return "suggest_followups"

        return None


# -- helpers for AdaptiveToolSelector ----------------------------------

def _extract_search_results(results: list[dict]) -> list[dict]:
    """Pull search result items from accumulated tool results."""
    items: list[dict] = []
    for r in results:
        if r.get("tool") != "search":
            continue
        data = r.get("data")
        if data is None:
            continue
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except (json.JSONDecodeError, TypeError):
                continue
        if isinstance(data, list):
            items.extend(data)
    return items


def _extract_entity_detail(results: list[dict]) -> dict | None:
    """Return the first entity_detail result dict, or None."""
    for r in results:
        if r.get("tool") != "entity_detail":
            continue
        data = r.get("data")
        if data is None:
            continue
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except (json.JSONDecodeError, TypeError):
                continue
        if isinstance(data, dict):
            return data
    return None


def _is_entity_complete(detail: dict) -> bool:
    """Heuristic: an entity is 'complete' when it has a name, description,
    and at least one of (location, season, price)."""
    has_name = bool(detail.get("name") or detail.get("title"))
    has_desc = bool(detail.get("description") or detail.get("content"))
    has_extra = bool(
        detail.get("location")
        or detail.get("season")
        or detail.get("price")
        or detail.get("address")
    )
    return has_name and has_desc and has_extra


# ======================================================================
#  3. ToolPipeline
# ======================================================================

@dataclass
class ToolStep:
    """A single step in a tool pipeline."""
    tool_name: str
    args_template: dict  # may contain ``"{query}"`` placeholders
    condition: Callable[[list[dict]], bool]  # receives results so far
    priority: int = 0  # lower = runs first


def _always(_results: list[dict]) -> bool:
    return True


def _has_search_results(results: list[dict]) -> bool:
    """True when at least one search result exists."""
    return bool(_extract_search_results(results))


def _has_entity_detail(results: list[dict]) -> bool:
    """True when entity_detail has been collected."""
    return _extract_entity_detail(results) is not None


class ToolPipeline:
    """Build and execute pre-defined tool pipelines per query category.

    Each pipeline is a list of ``ToolStep`` objects executed in priority
    order.  Steps whose *condition* returns ``False`` are skipped.
    """

    # -- pipeline definitions (class-level, immutable) ------------------

    @staticmethod
    def create_pipeline(query: str, category: str) -> list[ToolStep]:
        """Return the pipeline for *category*.

        Supported categories: ``search``, ``comparison``, ``itinerary``,
        ``recommendation``.  Unknown categories fall back to the search
        pipeline.
        """
        builders = {
            "search": ToolPipeline._pipeline_search,
            "comparison": ToolPipeline._pipeline_comparison,
            "itinerary": ToolPipeline._pipeline_itinerary,
            "recommendation": ToolPipeline._pipeline_recommendation,
        }
        builder = builders.get(category, ToolPipeline._pipeline_search)
        return builder(query)

    @staticmethod
    def execute_pipeline(
        pipeline: list[ToolStep],
        call_fn: Callable[[str, dict], str],
        on_result: Callable[[str, str], None] | None = None,
    ) -> list[dict]:
        """Execute *pipeline* steps sequentially, honouring conditions.

        Parameters
        ----------
        pipeline:
            Ordered list of ``ToolStep``.
        call_fn:
            ``call_fn(tool_name, args) -> json_str``.
        on_result:
            Optional callback ``(tool_name, result_json) -> None`` fired
            after each step completes.

        Returns
        -------
        list of ``{"tool": str, "args": dict, "data": str}`` for each
        step that actually executed.
        """
        # Sort by priority (stable sort preserves definition order for ties).
        ordered = sorted(pipeline, key=lambda s: s.priority)
        results: list[dict] = []

        for step in ordered:
            if not step.condition(results):
                logger.debug(
                    "Pipeline: skipping %s (condition not met)", step.tool_name,
                )
                continue

            args = dict(step.args_template)  # shallow copy

            try:
                result_str = call_fn(step.tool_name, args)
            except Exception as exc:
                logger.warning("Pipeline step %s failed: %s", step.tool_name, exc)
                result_str = json.dumps({"error": str(exc)}, ensure_ascii=False)

            entry = {"tool": step.tool_name, "args": args, "data": result_str}
            results.append(entry)

            if on_result is not None:
                try:
                    on_result(step.tool_name, result_str)
                except Exception:
                    pass  # callback errors must not break the pipeline

        return results

    # -- private builders -----------------------------------------------

    @staticmethod
    def _pipeline_search(query: str) -> list[ToolStep]:
        return [
            ToolStep(
                tool_name="search",
                args_template={"q": query},
                condition=_always,
                priority=0,
            ),
            ToolStep(
                tool_name="entity_detail",
                args_template={"entity_id": ""},  # filled by caller
                condition=_has_search_results,
                priority=1,
            ),
            ToolStep(
                tool_name="suggest_followups",
                args_template={"context": query},
                condition=_always,
                priority=2,
            ),
        ]

    @staticmethod
    def _pipeline_comparison(query: str) -> list[ToolStep]:
        return [
            ToolStep(
                tool_name="compare_areas",
                args_template={"area_1": "vinh-long", "area_2": "ben-tre"},
                condition=_always,
                priority=0,
            ),
            ToolStep(
                tool_name="suggest_followups",
                args_template={"context": query},
                condition=_always,
                priority=1,
            ),
        ]

    @staticmethod
    def _pipeline_itinerary(query: str) -> list[ToolStep]:
        return [
            ToolStep(
                tool_name="generate_itinerary",
                args_template={"days": 1},
                condition=_always,
                priority=0,
            ),
            ToolStep(
                tool_name="suggest_followups",
                args_template={"context": query},
                condition=_always,
                priority=1,
            ),
        ]

    @staticmethod
    def _pipeline_recommendation(query: str) -> list[ToolStep]:
        return [
            ToolStep(
                tool_name="seasonal_now",
                args_template={"month": time.localtime().tm_mon},
                condition=_always,
                priority=0,
            ),
            ToolStep(
                tool_name="search",
                args_template={"q": query},
                condition=_always,
                priority=1,
            ),
            ToolStep(
                tool_name="suggest_followups",
                args_template={"context": query},
                condition=_always,
                priority=2,
            ),
        ]


# ======================================================================
#  4. ProgressTracker
# ======================================================================

_PROGRESS_TTL = 300.0  # auto-cleanup after 5 minutes


@dataclass
class _ProgressEntry:
    total: int
    completed: int = 0
    current_tool: str = ""
    status: str = "pending"
    created_at: float = field(default_factory=time.time)
    finished: bool = False


class ProgressTracker:
    """Track multi-step tool execution progress per session.

    Thread-safe.  Entries are automatically evicted after
    ``_PROGRESS_TTL`` seconds.
    """

    def __init__(self) -> None:
        self._entries: dict[str, _ProgressEntry] = {}
        self._lock = threading.Lock()

    def start_tracking(self, session_id: str, total_steps: int) -> None:
        """Begin tracking for *session_id*."""
        self._cleanup()
        with self._lock:
            self._entries[session_id] = _ProgressEntry(total=total_steps)
        logger.debug("ProgressTracker: start session=%s steps=%d", session_id, total_steps)

    def update(
        self,
        session_id: str,
        step: int,
        tool_name: str,
        status: str,
    ) -> None:
        """Record progress for *session_id*."""
        with self._lock:
            entry = self._entries.get(session_id)
            if entry is None:
                return
            entry.completed = step
            entry.current_tool = tool_name
            entry.status = status

    def get_progress(self, session_id: str) -> dict:
        """Return a progress snapshot.

        Returns ``{"total": int, "completed": int, "current_tool": str,
        "pct": float}`` or an empty dict if the session is unknown.
        """
        with self._lock:
            entry = self._entries.get(session_id)
            if entry is None:
                return {}
            pct = (entry.completed / entry.total * 100.0) if entry.total else 0.0
            return {
                "total": entry.total,
                "completed": entry.completed,
                "current_tool": entry.current_tool,
                "pct": round(pct, 1),
            }

    def complete(self, session_id: str) -> None:
        """Mark *session_id* as done."""
        with self._lock:
            entry = self._entries.get(session_id)
            if entry is None:
                return
            entry.completed = entry.total
            entry.finished = True
            entry.status = "complete"
        logger.debug("ProgressTracker: complete session=%s", session_id)

    # -- housekeeping ---------------------------------------------------

    def _cleanup(self) -> None:
        """Remove stale entries older than ``_PROGRESS_TTL``."""
        now = time.time()
        with self._lock:
            stale = [
                sid for sid, e in self._entries.items()
                if now - e.created_at > _PROGRESS_TTL
            ]
            for sid in stale:
                del self._entries[sid]


# ======================================================================
#  5. StreamingToolExecutor
# ======================================================================

# Tools that depend on the results of prior tools (must run serially).
_DEPENDENT_TOOLS = frozenset({
    "entity_detail",       # needs entity_id from search
    "nearby_entities",     # needs entity_id from search / entity_detail
    "suggest_followups",   # should run last
    "generate_itinerary",  # may depend on prior search context
})


class StreamingToolExecutor:
    """Execute a batch of tool calls with streaming partial-result
    callbacks.

    Independent tools run in parallel; dependent tools run serially
    after independent ones finish.
    """

    def __init__(self, max_workers: int = 4) -> None:
        self._max_workers = max_workers

    def execute_with_streaming(
        self,
        tool_calls: list[dict],
        call_fn: Callable[[str, dict], str],
        on_partial: Callable[[str, str, str], None] | None = None,
    ) -> list[dict]:
        """Execute *tool_calls* and return final results.

        Parameters
        ----------
        tool_calls:
            ``[{"id": str, "name": str, "args": dict}, ...]``
        call_fn:
            ``call_fn(name, args) -> json_str``
        on_partial:
            Optional ``(tool_id, tool_name, partial_json) -> None``
            callback invoked with intermediate output for chunked tools.

        Returns
        -------
        ``[{"id": str, "name": str, "result": str,
            "duration_ms": float, "error": str|None}, ...]``
        in the same order as *tool_calls*.
        """
        if not tool_calls:
            return []

        independent, dependent = self._partition(tool_calls)

        # Index for re-ordering results.
        id_to_pos = {tc["id"]: i for i, tc in enumerate(tool_calls)}
        all_results: list[dict | None] = [None] * len(tool_calls)

        # --- Phase 1: independent tools in parallel -------------------
        if independent:
            with ThreadPoolExecutor(max_workers=self._max_workers) as pool:
                futures: list[tuple[dict, Future]] = []
                for tc in independent:
                    fut = pool.submit(
                        self._run_one, tc, call_fn, on_partial,
                    )
                    futures.append((tc, fut))

                for tc, fut in futures:
                    try:
                        res = fut.result(timeout=30)
                    except Exception as exc:
                        res = {
                            "id": tc["id"],
                            "name": tc["name"],
                            "result": json.dumps(
                                {"error": str(exc)}, ensure_ascii=False,
                            ),
                            "duration_ms": 0.0,
                            "error": str(exc),
                        }
                    all_results[id_to_pos[tc["id"]]] = res

        # --- Phase 2: dependent tools serially -------------------------
        for tc in dependent:
            try:
                res = self._run_one(tc, call_fn, on_partial)
            except Exception as exc:
                res = {
                    "id": tc["id"],
                    "name": tc["name"],
                    "result": json.dumps(
                        {"error": str(exc)}, ensure_ascii=False,
                    ),
                    "duration_ms": 0.0,
                    "error": str(exc),
                }
            all_results[id_to_pos[tc["id"]]] = res

        return all_results  # type: ignore[return-value]

    # -- internal -------------------------------------------------------

    @staticmethod
    def _partition(
        tool_calls: list[dict],
    ) -> tuple[list[dict], list[dict]]:
        """Split tool_calls into independent and dependent groups,
        preserving relative order."""
        independent: list[dict] = []
        dependent: list[dict] = []
        for tc in tool_calls:
            if tc.get("name", "") in _DEPENDENT_TOOLS:
                dependent.append(tc)
            else:
                independent.append(tc)
        return independent, dependent

    @staticmethod
    def _run_one(
        tc: dict,
        call_fn: Callable[[str, dict], str],
        on_partial: Callable[[str, str, str], None] | None,
    ) -> dict:
        """Execute a single tool call with timing, emitting chunked
        partials for batch-result tools."""
        tool_name = tc["name"]
        args = tc.get("args", {})
        tool_id = tc["id"]

        t0 = time.perf_counter()
        error: str | None = None
        try:
            result_str = call_fn(tool_name, args)
        except Exception as exc:
            result_str = json.dumps({"error": str(exc)}, ensure_ascii=False)
            error = str(exc)
        duration_ms = (time.perf_counter() - t0) * 1000.0

        # Emit chunked partials for list-type results.
        if on_partial is not None and error is None:
            try:
                parsed = json.loads(result_str)
                if isinstance(parsed, list) and len(parsed) > 3:
                    chunk_size = 3
                    for end in range(chunk_size, len(parsed) + 1, chunk_size):
                        chunk = parsed[:end]
                        partial_json = json.dumps(
                            {"items": chunk, "count": len(chunk), "total": len(parsed)},
                            ensure_ascii=False,
                        )
                        try:
                            on_partial(tool_id, tool_name, partial_json)
                        except Exception:
                            pass
            except (json.JSONDecodeError, TypeError):
                pass

        return {
            "id": tool_id,
            "name": tool_name,
            "result": result_str,
            "duration_ms": round(duration_ms, 2),
            "error": error,
        }


# ======================================================================
#  Module singletons
# ======================================================================

tool_stream: ToolResultStream = ToolResultStream()
adaptive_selector: AdaptiveToolSelector = AdaptiveToolSelector()
progress_tracker: ProgressTracker = ProgressTracker()
streaming_executor: StreamingToolExecutor = StreamingToolExecutor()
