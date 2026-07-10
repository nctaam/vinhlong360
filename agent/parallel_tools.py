"""
Parallel Tool Execution engine for vinhlong360 Knowledge Agent.

Provides concurrent execution of independent tool calls to reduce
total latency in multi-tool agent rounds. Designed to plug into
the existing ``call_tool(name, args)`` dispatcher in server.py.

Usage::

    from parallel_tools import ParallelToolExecutor

    executor = ParallelToolExecutor(call_tool, max_workers=4)

    # Automatic parallel / sequential split:
    results = executor.execute_smart(tool_calls)

    # Or explicit parallel execution:
    results = executor.execute_parallel(tool_calls)
"""

from __future__ import annotations

import logging
import time
import threading
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Callable, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Parallelisability rules
# ---------------------------------------------------------------------------

# Tools that are always safe to run concurrently with anything.
_ALWAYS_PARALLEL = frozenset({"search", "entity_detail", "weather", "web_search"})

# Tools that must run after everything else has completed.
_ALWAYS_SEQUENTIAL = frozenset({"suggest_followups", "generate_itinerary"})


def can_parallelize(
    tool_calls: list[dict],
) -> tuple[list[dict], list[dict]]:
    """Partition *tool_calls* into a parallel group and a sequential group.

    Rules
    -----
    * ``search`` calls with different parameters -> parallel.
    * ``entity_detail`` calls -> parallel.
    * ``weather`` -> parallel with anything.
    * ``web_search`` -> parallel with KB searches.
    * ``suggest_followups`` -> always last (sequential).
    * ``generate_itinerary`` -> sequential (may depend on prior search results).
    * Any unrecognised tool -> sequential (safe default).

    Parameters
    ----------
    tool_calls:
        Each item is ``{"id": str, "name": str, "args": dict}``.

    Returns
    -------
    (parallel_group, sequential_group)
        Both lists preserve the original relative ordering.
    """
    parallel: list[dict] = []
    sequential: list[dict] = []

    # Track search parameter signatures so we can detect duplicates.
    seen_search_sigs: set[str] = set()

    for tc in tool_calls:
        name = tc.get("name", "")

        if name in _ALWAYS_SEQUENTIAL:
            sequential.append(tc)
            continue

        if name in _ALWAYS_PARALLEL:
            # For "search", only parallelise when the params differ.
            if name == "search":
                sig = _search_signature(tc.get("args", {}))
                if sig in seen_search_sigs:
                    # Duplicate search -- still safe but pointless; keep it
                    # parallel so the caller decides.
                    pass
                seen_search_sigs.add(sig)
            parallel.append(tc)
            continue

        # Unknown / other tools -> sequential to be safe.
        sequential.append(tc)

    return parallel, sequential


def _search_signature(args: dict) -> str:
    """Create a hashable key from search arguments for dedup detection."""
    parts = [
        args.get("q", ""),
        args.get("entity_type", ""),
        args.get("area", ""),
        str(args.get("month", "")),
        str(args.get("ocop_only", "")),
    ]
    return "|".join(parts)


# ---------------------------------------------------------------------------
# Executor
# ---------------------------------------------------------------------------

class ParallelToolExecutor:
    """Execute multiple tool calls concurrently using a thread pool.

    Parameters
    ----------
    call_tool_fn:
        The synchronous ``call_tool(name: str, args: dict) -> str`` function
        from ``server.py``.
    max_workers:
        Maximum threads in the pool (default 4).
    default_timeout:
        Per-call timeout in seconds (default 10).
    on_tool_start:
        Optional callback ``(tool_name, tool_id) -> None`` fired just before
        a tool begins executing.  Thread-safe -- may be called from any
        worker thread.
    on_tool_done:
        Optional callback ``(tool_name, tool_id, duration_ms) -> None`` fired
        when a tool finishes (success or failure).
    """

    def __init__(
        self,
        call_tool_fn: Callable[[str, dict], str],
        max_workers: int = 4,
        default_timeout: float = 10.0,
        on_tool_start: Optional[Callable[[str, str], None]] = None,
        on_tool_done: Optional[Callable[[str, str, float], None]] = None,
    ) -> None:
        self._call_tool = call_tool_fn
        self._max_workers = max_workers
        self._default_timeout = default_timeout
        self.on_tool_start = on_tool_start
        self.on_tool_done = on_tool_done
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute_parallel(
        self,
        tool_calls: list[dict],
        timeout: float | None = None,
    ) -> list[dict]:
        """Execute *all* tool calls concurrently and return results in order.

        Parameters
        ----------
        tool_calls:
            ``[{"id": str, "name": str, "args": dict}, ...]``
        timeout:
            Per-call timeout in seconds.  Falls back to *default_timeout*.

        Returns
        -------
        list of result dicts::

            [{"id": str, "name": str, "result": str,
              "duration_ms": float, "error": str | None}, ...]

        Ordering matches the input list.  If an individual call fails or
        times out, its ``error`` field is populated and ``result`` contains
        a JSON-encoded error object; other calls are unaffected.
        """
        if not tool_calls:
            return []

        per_call_timeout = timeout if timeout is not None else self._default_timeout

        # Map from future -> index so we can reassemble in order.
        futures: list[tuple[int, dict, Future]] = []

        with ThreadPoolExecutor(max_workers=self._max_workers) as pool:
            for idx, tc in enumerate(tool_calls):
                future = pool.submit(
                    self._run_one,
                    tc["name"],
                    tc.get("args", {}),
                    tc["id"],
                )
                futures.append((idx, tc, future))

            # Collect results in original order.
            results: list[dict | None] = [None] * len(tool_calls)
            for idx, tc, future in futures:
                try:
                    result_str, duration_ms, error = future.result(
                        timeout=per_call_timeout,
                    )
                except Exception as exc:
                    # Timeout or unexpected error from the future itself.
                    result_str = _error_json(str(exc))
                    duration_ms = 0.0
                    error = str(exc)

                results[idx] = {
                    "id": tc["id"],
                    "name": tc["name"],
                    "result": result_str,
                    "duration_ms": duration_ms,
                    "error": error,
                }

        return results  # type: ignore[return-value]

    def execute_smart(
        self,
        tool_calls: list[dict],
        timeout: float | None = None,
    ) -> list[dict]:
        """Partition calls automatically, run parallel group first, then sequential.

        Returns all results in the *original* input order.
        """
        if not tool_calls:
            return []

        parallel_group, sequential_group = can_parallelize(tool_calls)

        # Build an index mapping id -> original position.
        id_to_pos = {tc["id"]: i for i, tc in enumerate(tool_calls)}

        all_results: list[dict | None] = [None] * len(tool_calls)

        # 1. Parallel group -- all at once.
        if parallel_group:
            par_results = self.execute_parallel(parallel_group, timeout=timeout)
            for r in par_results:
                pos = id_to_pos[r["id"]]
                all_results[pos] = r

        # 2. Sequential group -- one at a time, in order.
        for tc in sequential_group:
            try:
                result_str, duration_ms, error = self._run_one(
                    tc["name"], tc.get("args", {}), tc["id"],
                )
            except Exception as exc:
                result_str = _error_json(str(exc))
                duration_ms = 0.0
                error = str(exc)

            pos = id_to_pos[tc["id"]]
            all_results[pos] = {
                "id": tc["id"],
                "name": tc["name"],
                "result": result_str,
                "duration_ms": duration_ms,
                "error": error,
            }

        return all_results  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _run_one(
        self,
        name: str,
        args: dict,
        tool_id: str,
    ) -> tuple[str, float, str | None]:
        """Execute a single tool call with timing and callbacks.

        Returns ``(result_str, duration_ms, error_or_none)``.
        """
        # Notify start (thread-safe).
        if self.on_tool_start is not None:
            try:
                self.on_tool_start(name, tool_id)
            except Exception as exc:
                logger.debug("on_tool_start callback failed: %s", exc)

        t0 = time.perf_counter()
        error: str | None = None
        try:
            result_str = self._call_tool(name, args)
        except Exception as exc:
            result_str = _error_json(str(exc))
            error = str(exc)
            logger.warning("Tool call %s failed: %s", name, exc)
        duration_ms = (time.perf_counter() - t0) * 1000.0

        # Notify done (thread-safe).
        if self.on_tool_done is not None:
            try:
                self.on_tool_done(name, tool_id, duration_ms)
            except Exception as exc:
                logger.debug("on_tool_done callback failed: %s", exc)

        return result_str, duration_ms, error


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _error_json(message: str) -> str:
    """Return a JSON-encoded error string matching the call_tool convention."""
    import json
    return json.dumps({"error": message}, ensure_ascii=False)
