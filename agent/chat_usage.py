"""Request-scoped provider usage aggregation for chat turns."""

from __future__ import annotations

import json
from dataclasses import dataclass
from threading import Lock
from typing import Any

try:
    from cost_tracker import TokenCounter
except ImportError:  # pragma: no cover - package import mode
    from agent.cost_tracker import TokenCounter


@dataclass(frozen=True)
class UsageSnapshot:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost: float
    provider_call_count: int
    estimated_call_count: int
    settled: bool


class UsageAccumulator:
    """Accumulate each completed provider call exactly once for one request."""

    def __init__(self, counter: Any | None = None) -> None:
        self._counter = counter or TokenCounter()
        self._lock = Lock()
        self._prompt_tokens = 0
        self._completion_tokens = 0
        self._total_tokens = 0
        self._cost = 0.0
        self._provider_call_count = 0
        self._estimated_call_count = 0
        self._models: set[str] = set()
        self._guardrail_committed = False
        self._attribution_committed = False
        self._settlement_snapshot: UsageSnapshot | None = None

    @staticmethod
    def _completion_from_response(response: Any) -> str:
        try:
            message = response.choices[0].message
        except (AttributeError, IndexError, TypeError):
            return ""
        content = getattr(message, "content", None)
        if content:
            return str(content)
        tool_calls = getattr(message, "tool_calls", None)
        if not tool_calls:
            return ""
        serializable = []
        for call in tool_calls:
            function = getattr(call, "function", None)
            serializable.append({
                "id": getattr(call, "id", None),
                "name": getattr(function, "name", None),
                "arguments": getattr(function, "arguments", None),
            })
        return json.dumps(serializable, ensure_ascii=False, separators=(",", ":"))

    def add_response(
        self,
        response: Any,
        model: str,
        messages: list[dict],
        completion_text: str | None = None,
    ) -> UsageSnapshot:
        """Add one non-stream response or terminal stream usage chunk."""
        if getattr(response, "_skip_usage", False):
            return self.snapshot()
        tokens = self._counter.count_from_response(response)
        estimated = not tokens.get("total_tokens", 0)
        if estimated:
            tokens = self._estimate_missing_usage(
                response,
                messages,
                completion_text,
            )

        prompt_tokens = max(0, int(tokens.get("prompt_tokens", 0) or 0))
        completion_tokens = max(0, int(tokens.get("completion_tokens", 0) or 0))
        total_tokens = max(0, int(tokens.get("total_tokens", 0) or 0))
        if not total_tokens and (prompt_tokens or completion_tokens):
            total_tokens = prompt_tokens + completion_tokens
        call_tokens = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        }
        call_cost = self._counter.calculate_cost(call_tokens, model)

        with self._lock:
            if self._settlement_snapshot is not None:
                raise RuntimeError("Cannot add provider usage after settlement")
            self._prompt_tokens += prompt_tokens
            self._completion_tokens += completion_tokens
            self._total_tokens += total_tokens
            self._cost = round(self._cost + call_cost, 8)
            self._provider_call_count += 1
            self._estimated_call_count += int(estimated)
            self._models.add(model)
            return self._snapshot_locked(settled=False)

    def _estimate_missing_usage(
        self,
        response: Any,
        messages: list[dict],
        completion_text: str | None,
    ) -> dict[str, int]:
        completion = (
            completion_text
            if completion_text is not None
            else self._completion_from_response(response)
        )
        if hasattr(self._counter, "estimate_call_tokens"):
            return self._counter.estimate_call_tokens(messages, completion)
        serialized = json.dumps(
            messages,
            ensure_ascii=False,
            separators=(",", ":"),
            default=str,
        )
        prompt_tokens = self._counter.estimate_tokens(serialized)
        completion_tokens = self._counter.estimate_tokens(completion)
        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        }

    def _snapshot_locked(self, *, settled: bool) -> UsageSnapshot:
        return UsageSnapshot(
            prompt_tokens=self._prompt_tokens,
            completion_tokens=self._completion_tokens,
            total_tokens=self._total_tokens,
            cost=self._cost,
            provider_call_count=self._provider_call_count,
            estimated_call_count=self._estimated_call_count,
            settled=settled,
        )

    def snapshot(self) -> UsageSnapshot:
        with self._lock:
            if self._settlement_snapshot is not None:
                return self._settlement_snapshot
            return self._snapshot_locked(settled=False)

    def settle(
        self,
        *,
        owner_key: str,
        query: str,
        agent_name: str,
        guardrail_budget: Any | None,
        cost_attribution: Any | None,
    ) -> UsageSnapshot:
        """Commit aggregate totals once to the owner budget and attribution."""
        with self._lock:
            if self._settlement_snapshot is not None:
                return self._settlement_snapshot

            snapshot = self._snapshot_locked(settled=False)
            if not snapshot.provider_call_count:
                self._guardrail_committed = True
                self._attribution_committed = True

            if guardrail_budget is None:
                self._guardrail_committed = True
            elif not self._guardrail_committed:
                guardrail_budget.record_usage(owner_key, snapshot.total_tokens)
                self._guardrail_committed = True

            if cost_attribution is None:
                self._attribution_committed = True
            elif not self._attribution_committed:
                model = next(iter(self._models)) if len(self._models) == 1 else "multi-model"
                cost_attribution.record(
                    owner_key,
                    query,
                    agent_name,
                    None,
                    model,
                    {
                        "prompt_tokens": snapshot.prompt_tokens,
                        "completion_tokens": snapshot.completion_tokens,
                        "total_tokens": snapshot.total_tokens,
                        "provider_call_count": snapshot.provider_call_count,
                        "estimated_call_count": snapshot.estimated_call_count,
                    },
                    snapshot.cost,
                )
                self._attribution_committed = True

            if self._guardrail_committed and self._attribution_committed:
                self._settlement_snapshot = self._snapshot_locked(settled=True)
                return self._settlement_snapshot
            return snapshot
