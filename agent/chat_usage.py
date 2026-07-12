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
    def _field(value: Any, name: str, default: Any = None) -> Any:
        if isinstance(value, dict):
            return value.get(name, default)
        return getattr(value, name, default)

    @staticmethod
    def _completion_from_response(response: Any) -> str:
        try:
            choices = UsageAccumulator._field(response, "choices", [])
            message = UsageAccumulator._field(choices[0], "message")
        except (IndexError, TypeError):
            return ""
        content = UsageAccumulator._field(message, "content")
        if content:
            return str(content)
        tool_calls = UsageAccumulator._field(message, "tool_calls")
        if not tool_calls:
            return ""
        serializable = []
        for call in tool_calls:
            function = UsageAccumulator._field(call, "function")
            serializable.append({
                "id": UsageAccumulator._field(call, "id"),
                "name": UsageAccumulator._field(function, "name"),
                "arguments": UsageAccumulator._field(function, "arguments"),
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
        raw_tokens, reported = self._count_provider_usage(response)
        tokens, estimated = self._complete_call_tokens(
            raw_tokens,
            reported,
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

    def _count_provider_usage(
        self,
        response: Any,
    ) -> tuple[dict[str, int], dict[str, bool]]:
        if hasattr(self._counter, "count_with_provenance"):
            return self._counter.count_with_provenance(response)
        tokens = self._counter.count_from_response(response)
        reported = {
            name: bool(tokens.get(name, 0))
            for name in ("prompt_tokens", "completion_tokens", "total_tokens")
        }
        return tokens, reported

    def _complete_call_tokens(
        self,
        tokens: dict[str, int],
        reported: dict[str, bool],
        response: Any,
        messages: list[dict],
        completion_text: str | None,
    ) -> tuple[dict[str, int], bool]:
        prompt = max(0, int(tokens.get("prompt_tokens", 0) or 0))
        completion = max(0, int(tokens.get("completion_tokens", 0) or 0))
        total = max(0, int(tokens.get("total_tokens", 0) or 0))
        if not prompt and not completion and not total:
            return self._estimate_missing_usage(response, messages, completion_text), True
        prompt_reported = reported.get("prompt_tokens", False)
        completion_reported = reported.get("completion_tokens", False)
        total_reported = reported.get("total_tokens", False) and total > 0
        if not total_reported:
            return self._complete_without_total(
                prompt,
                completion,
                prompt_reported,
                completion_reported,
                response,
                messages,
                completion_text,
            )
        return self._complete_with_total(
            prompt,
            completion,
            total,
            prompt_reported,
            completion_reported,
            response,
            messages,
            completion_text,
        )

    def _complete_with_total(
        self,
        prompt: int,
        completion: int,
        total: int,
        prompt_reported: bool,
        completion_reported: bool,
        response: Any,
        messages: list[dict],
        completion_text: str | None,
    ) -> tuple[dict[str, int], bool]:
        if prompt_reported and completion_reported and prompt + completion == total:
            return self._token_dict(prompt, completion, total), False
        if prompt_reported and not completion_reported and prompt <= total:
            return self._token_dict(prompt, total - prompt, total), True
        if completion_reported and not prompt_reported and completion <= total:
            return self._token_dict(total - completion, completion, total), True
        estimated = self._estimate_missing_usage(response, messages, completion_text)
        return self._scale_components_to_total(estimated, total), True

    def _complete_without_total(
        self,
        prompt: int,
        completion: int,
        prompt_reported: bool,
        completion_reported: bool,
        response: Any,
        messages: list[dict],
        completion_text: str | None,
    ) -> tuple[dict[str, int], bool]:
        if prompt_reported and completion_reported:
            return self._token_dict(prompt, completion, prompt + completion), False
        estimated = self._estimate_missing_usage(response, messages, completion_text)
        if prompt_reported:
            estimated_completion = estimated["completion_tokens"]
            return self._token_dict(
                prompt,
                estimated_completion,
                prompt + estimated_completion,
            ), True
        if completion_reported:
            estimated_prompt = estimated["prompt_tokens"]
            return self._token_dict(
                estimated_prompt,
                completion,
                estimated_prompt + completion,
            ), True
        return estimated, True

    @staticmethod
    def _token_dict(prompt: int, completion: int, total: int) -> dict[str, int]:
        return {
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "total_tokens": total,
        }

    def _scale_components_to_total(
        self,
        estimated: dict[str, int],
        total: int,
    ) -> dict[str, int]:
        prompt = max(0, int(estimated.get("prompt_tokens", 0) or 0))
        completion = max(0, int(estimated.get("completion_tokens", 0) or 0))
        estimated_total = prompt + completion
        if not estimated_total:
            return self._token_dict(0, total, total)
        scaled_completion = round(total * completion / estimated_total)
        scaled_completion = min(total, max(0, scaled_completion))
        return self._token_dict(total - scaled_completion, scaled_completion, total)

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
        return self._token_dict(
            prompt_tokens,
            completion_tokens,
            prompt_tokens + completion_tokens,
        )

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
