"""Typed registry for personal-data purge and verification adapters."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Callable, Iterable

import ab_testing
import analytics
import cache as exact_cache
import cost_tracker
import experience_memory
import feedback_policy
import guardrails
import memory
import memory_graph
import prompt_compiler
import self_optimizer
import semantic_cache


_MAX_CACHE_SCAN_ITEMS = 5_000
_CLASSIFICATIONS = {"personal", "pseudonymous", "aggregate", "operational"}

EXPECTED_SUBJECT_STORES = frozenset({
    "hot_memory",
    "cold_memory",
    "memory_graph",
    "exact_cache",
    "semantic_cache",
    "semantic_leases",
    "pending_feedback_receipts",
    "feedback_receipts",
    "owner_analytics",
    "conversation_history",
    "guardrail_budget",
    "cost_attribution",
    "optimizer_records",
    "experience_memory",
    "prompt_demonstrations",
    "ab_outcomes",
})

EXPECTED_QUARANTINE_STORES = frozenset({
    "hot_memory",
    "exact_cache",
    "semantic_cache",
    "semantic_leases",
    "pending_feedback_receipts",
})


@dataclass(frozen=True)
class PurgeResult:
    store_name: str
    removed_count: int = 0
    complete: bool = True
    error_code: str | None = None

    def to_dict(self) -> dict:
        return {
            "store_name": self.store_name,
            "removed_count": max(0, int(self.removed_count)),
            "complete": bool(self.complete),
            "error_code": self.error_code,
        }


@dataclass(frozen=True)
class VerificationResult:
    store_name: str
    absent: bool
    residual_count: int = 0
    error_code: str | None = None

    @property
    def verified(self) -> bool:
        return self.absent and self.residual_count == 0 and self.error_code is None

    def to_dict(self) -> dict:
        return {
            "store_name": self.store_name,
            "absent": bool(self.absent),
            "residual_count": max(0, int(self.residual_count)),
            "verified": self.verified,
            "error_code": self.error_code,
        }


@dataclass(frozen=True)
class DataStorePolicy:
    name: str
    classification: str
    purge: Callable[[str], int | PurgeResult] | None
    verify: Callable[[str], bool | VerificationResult] | None
    description: str
    quarantine_on_request: bool = False
    subject_linked: bool = True
    retained_fields: tuple[str, ...] = ()

    def purge_owner(self, owner_key: str) -> PurgeResult:
        if not self.subject_linked or self.purge is None:
            return PurgeResult(store_name=self.name)
        try:
            result = self.purge(owner_key)
        except Exception:
            return PurgeResult(
                store_name=self.name,
                complete=False,
                error_code="STORE_UNAVAILABLE",
            )
        if isinstance(result, PurgeResult):
            return result
        return PurgeResult(store_name=self.name, removed_count=max(0, int(result)))

    def verify_owner_absent(self, owner_key: str) -> VerificationResult:
        if not self.subject_linked or self.verify is None:
            return VerificationResult(store_name=self.name, absent=True)
        try:
            result = self.verify(owner_key)
        except Exception:
            return VerificationResult(
                store_name=self.name,
                absent=False,
                residual_count=1,
                error_code="VERIFY_FAILED",
            )
        if isinstance(result, VerificationResult):
            return result
        absent = bool(result)
        return VerificationResult(
            store_name=self.name,
            absent=absent,
            residual_count=0 if absent else 1,
        )


class LifecycleRegistry:
    def __init__(self, policies: Iterable[DataStorePolicy]):
        self._policies = tuple(policies)

    @property
    def policies(self) -> tuple[DataStorePolicy, ...]:
        return self._policies

    def get(self, name: str) -> DataStorePolicy:
        for policy in self._policies:
            if policy.name == name:
                return policy
        raise KeyError(name)


def _exact_cache_entry_matches(owner_key: str, cache_key: str, entry: dict) -> bool:
    query = entry.get("query")
    if not isinstance(query, str):
        return False
    return cache_key == exact_cache._normalize_key(query, owner_key=owner_key)


def _purge_exact_cache_memory(owner_key: str) -> int:
    removed = 0
    with exact_cache._lock:
        for cache_key, entry in list(exact_cache._cache.items()):
            if _exact_cache_entry_matches(owner_key, cache_key, entry):
                exact_cache._cache.pop(cache_key, None)
                removed += 1
    return removed


def _verify_exact_cache_memory(owner_key: str) -> bool:
    with exact_cache._lock:
        return not any(
            _exact_cache_entry_matches(owner_key, cache_key, entry)
            for cache_key, entry in exact_cache._cache.items()
        )


def _redis_owner_keys(owner_key: str) -> tuple[list[str], bool]:
    matches: list[str] = []
    cursor = 0
    scanned = 0
    complete = True
    while True:
        cursor, keys = exact_cache._redis_client.scan(
            cursor,
            match=f"{exact_cache._KEY_PREFIX}*",
            count=200,
        )
        for redis_key in keys:
            scanned += 1
            if scanned > _MAX_CACHE_SCAN_ITEMS:
                complete = False
                break
            raw = exact_cache._redis_client.get(redis_key)
            if raw is None:
                continue
            try:
                entry = json.loads(raw)
            except (TypeError, json.JSONDecodeError):
                continue
            cache_key = str(redis_key).removeprefix(exact_cache._KEY_PREFIX)
            if _exact_cache_entry_matches(owner_key, cache_key, entry):
                matches.append(redis_key)
        if not complete or cursor == 0:
            break
    return matches, complete


def _purge_exact_cache(owner_key: str) -> PurgeResult:
    exact_cache._ensure_redis()
    if not exact_cache._use_redis:
        return PurgeResult(
            store_name="exact_cache",
            removed_count=_purge_exact_cache_memory(owner_key),
        )
    keys, complete = _redis_owner_keys(owner_key)
    if keys:
        exact_cache._redis_client.delete(*keys)
    return PurgeResult(
        store_name="exact_cache",
        removed_count=len(keys),
        complete=complete,
        error_code=None if complete else "STORE_UNAVAILABLE",
    )


def _verify_exact_cache(owner_key: str) -> VerificationResult:
    exact_cache._ensure_redis()
    if not exact_cache._use_redis:
        absent = _verify_exact_cache_memory(owner_key)
        return VerificationResult(
            store_name="exact_cache",
            absent=absent,
            residual_count=0 if absent else 1,
        )
    keys, complete = _redis_owner_keys(owner_key)
    absent = complete and not keys
    return VerificationResult(
        store_name="exact_cache",
        absent=absent,
        residual_count=len(keys) if keys else (0 if absent else 1),
        error_code=None if complete else "VERIFY_FAILED",
    )


lifecycle_registry = LifecycleRegistry((
    DataStorePolicy(
        "hot_memory",
        "personal",
        memory.memory_manager.purge_owner,
        memory.memory_manager.verify_owner_absent,
        "In-process conversation sessions",
        quarantine_on_request=True,
    ),
    DataStorePolicy(
        "cold_memory",
        "personal",
        memory.memory_manager.cold.purge_owner,
        memory.memory_manager.cold.verify_owner_absent,
        "Recoverable long-term profile memory",
    ),
    DataStorePolicy(
        "memory_graph",
        "pseudonymous",
        memory_graph.memory_graph.purge_owner,
        memory_graph.memory_graph.verify_owner_absent,
        "Owner graph node and incident edges",
    ),
    DataStorePolicy(
        "exact_cache",
        "pseudonymous",
        _purge_exact_cache,
        _verify_exact_cache,
        "Owner-namespaced exact response cache",
        quarantine_on_request=True,
    ),
    DataStorePolicy(
        "semantic_cache",
        "pseudonymous",
        semantic_cache.multi_tier_cache.purge_owner,
        semantic_cache.multi_tier_cache.verify_owner_absent,
        "Owner-namespaced semantic cache entries",
        quarantine_on_request=True,
    ),
    DataStorePolicy(
        "semantic_leases",
        "pseudonymous",
        semantic_cache.deduplicator.purge_owner,
        semantic_cache.deduplicator.verify_owner_absent,
        "In-flight semantic request leases",
        quarantine_on_request=True,
    ),
    DataStorePolicy(
        "pending_feedback_receipts",
        "pseudonymous",
        feedback_policy.purge_pending_feedback_owner,
        feedback_policy.verify_pending_feedback_owner_absent,
        "Unused owner-bound feedback credentials",
        quarantine_on_request=True,
    ),
    DataStorePolicy(
        "feedback_receipts",
        "pseudonymous",
        feedback_policy.purge_feedback_owner,
        feedback_policy.verify_feedback_owner_absent,
        "All remaining owner-bound feedback receipts",
    ),
    DataStorePolicy(
        "owner_analytics",
        "personal",
        analytics.purge_owner_records,
        analytics.verify_owner_records_absent,
        "Owner-attributed query and unanswered records",
    ),
    DataStorePolicy(
        "conversation_history",
        "personal",
        analytics.purge_owner_conversations,
        analytics.verify_owner_conversations_absent,
        "File-backed conversation histories",
    ),
    DataStorePolicy(
        "guardrail_budget",
        "pseudonymous",
        guardrails.budget_manager.purge_owner,
        guardrails.budget_manager.verify_owner_absent,
        "Owner-keyed chat abuse budget",
    ),
    DataStorePolicy(
        "cost_attribution",
        "personal",
        cost_tracker.cost_attribution.purge_owner,
        cost_tracker.cost_attribution.verify_owner_absent,
        "Owner-attributed model usage and cost records",
    ),
    DataStorePolicy(
        "optimizer_records",
        "personal",
        self_optimizer.performance_collector.purge_owner,
        self_optimizer.performance_collector.verify_owner_absent,
        "Owner-attributed optimizer performance rows",
    ),
    DataStorePolicy(
        "experience_memory",
        "personal",
        experience_memory.purge_owner,
        experience_memory.verify_owner_absent,
        "Owner-attributed learned experience records",
    ),
    DataStorePolicy(
        "prompt_demonstrations",
        "personal",
        prompt_compiler.purge_owner,
        prompt_compiler.verify_owner_absent,
        "Raw and compiled owner-attributed demonstrations",
    ),
    DataStorePolicy(
        "ab_outcomes",
        "pseudonymous",
        ab_testing.ab_manager.purge_owner,
        ab_testing.ab_manager.verify_owner_absent,
        "Owner-attributed A/B outcomes and linked assignments",
    ),
    DataStorePolicy(
        "deidentified_daily_rollups",
        "aggregate",
        None,
        None,
        "Daily request and session counts",
        subject_linked=False,
        retained_fields=("date", "request_count", "session_count"),
    ),
    DataStorePolicy(
        "public_entity_popularity",
        "aggregate",
        None,
        None,
        "Public catalog popularity counts",
        subject_linked=False,
        retained_fields=("public_entity_id", "count"),
    ),
    DataStorePolicy(
        "post_boundary_operational_logs",
        "operational",
        None,
        None,
        "Bounded non-subject operational events",
        subject_linked=False,
        retained_fields=("event_code", "store_name", "run_id", "count"),
    ),
))


def validate_lifecycle_registry(
    policies: Iterable[DataStorePolicy] | None = None,
) -> tuple[str, ...]:
    selected = tuple(
        lifecycle_registry.policies if policies is None else policies
    )
    errors: list[str] = []
    names = [policy.name for policy in selected]
    for name in sorted({name for name in names if names.count(name) > 1}):
        errors.append(f"DUPLICATE_STORE:{name}")

    subject_names = {policy.name for policy in selected if policy.subject_linked}
    for name in sorted(EXPECTED_SUBJECT_STORES - subject_names):
        errors.append(f"MISSING_SUBJECT_STORE:{name}")
    for name in sorted(subject_names - EXPECTED_SUBJECT_STORES):
        errors.append(f"UNDECLARED_SUBJECT_STORE:{name}")

    immediate = {policy.name for policy in selected if policy.quarantine_on_request}
    for name in sorted(EXPECTED_QUARANTINE_STORES - immediate):
        errors.append(f"MISSING_QUARANTINE_STORE:{name}")
    for name in sorted(immediate - EXPECTED_QUARANTINE_STORES):
        errors.append(f"UNEXPECTED_QUARANTINE_STORE:{name}")

    forbidden_retained = {
        "owner_key",
        "user_id",
        "session_id",
        "query",
        "response",
        "receipt",
        "entity_id",
    }
    for policy in selected:
        if policy.classification not in _CLASSIFICATIONS:
            errors.append(f"INVALID_CLASSIFICATION:{policy.name}")
        if policy.subject_linked and (
            not callable(policy.purge) or not callable(policy.verify)
        ):
            errors.append(f"MISSING_ADAPTER:{policy.name}")
        if not policy.subject_linked:
            if policy.classification not in {"aggregate", "operational"}:
                errors.append(f"INVALID_RETAINED_CLASSIFICATION:{policy.name}")
            if not policy.retained_fields:
                errors.append(f"MISSING_RETAINED_FIELDS:{policy.name}")
            if policy.name in {
                "deidentified_daily_rollups",
                "post_boundary_operational_logs",
            } and forbidden_retained.intersection(policy.retained_fields):
                errors.append(f"SUBJECT_FIELD_IN_RETAINED_STORE:{policy.name}")
    return tuple(sorted(errors))


def lifecycle_registry_readiness() -> dict:
    errors = validate_lifecycle_registry()
    stores = [
        {
            "name": policy.name,
            "classification": policy.classification,
            "status": "ready",
        }
        for policy in sorted(lifecycle_registry.policies, key=lambda item: item.name)
    ]
    return {
        "ok": not errors,
        "store_count": len(stores),
        "subject_store_count": sum(
            1 for policy in lifecycle_registry.policies if policy.subject_linked
        ),
        "errors": list(errors),
        "stores": stores,
    }
