"""Scoped scrub tooling for pre-boundary file-backed personal data.

The scrubber deliberately operates on a declared inventory and structured owner
fields. It is not a general-purpose text replacement utility.
"""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from cryptography.fernet import Fernet, InvalidToken

from guardrails import pii_masker
from privacy_boundary import redact_log_value


TOOL_VERSION = "legacy-scrub-1"

# Keep this inventory explicit: adding a store requires a reviewed adapter and
# a matching test rather than silently widening the filesystem scope.
DECLARED_STORES = {
    "analytics": ("analytics.json", "json"),
    "cost_attribution": ("costs.json", "json"),
    "ab_outcomes": ("ab_tests.json", "json"),
    "semantic_cache": ("semantic_cache/entries.json", "json"),
    "memory_graph": ("memory/graph.json", "json"),
    "cold_memory": ("memory/user_profiles.json", "profiles"),
    "experience_memory": ("memory/experience_bank.json", "json"),
    "optimizer_records": ("optimizer/performance.json", "json"),
    "prompt_demonstrations_raw": ("optimizer/demo_pool.json", "json"),
    "prompt_demonstrations_compiled": ("optimizer/compiled_demos.json", "json"),
    "guardrail_budget": ("guardrails_budget.json", "json"),
    "conversation_history": ("conversations", "conversation_dir"),
    "learn_loop": ("learn_loop_log.jsonl", "jsonl"),
    "admin_audit": ("admin_audit.jsonl", "jsonl"),
}

# A prior layout used ``demos/``. Supporting that exact alias keeps the tool
# useful during migration without permitting arbitrary directory traversal.
_OPTIONAL_ALIASES = {
    "prompt_demonstrations_raw": ("demos/demo_pool.json", "json"),
    "prompt_demonstrations_compiled": ("demos/compiled_demos.json", "json"),
}


class ScrubError(RuntimeError):
    """Base class for fail-closed scrub errors."""


class BackupEvidenceRequired(ScrubError):
    """Mutation requires an existing backup evidence file."""


class StaleScrubPlan(ScrubError):
    """A planned file changed before the apply phase."""


class ScrubDataError(ScrubError):
    """A declared store could not be parsed or safely transformed."""


@dataclass(frozen=True)
class _ProfileStore:
    data: Mapping[str, Any]
    encrypted: bool
    key: bytes | None = None


@dataclass(frozen=True)
class ScrubFile:
    store_name: str
    path: Path
    kind: str
    before_digest: str
    before_bytes: int
    owner_matches: int
    pii_findings: int

    @property
    def relative_path(self) -> str:
        return self.path.as_posix()


@dataclass(frozen=True)
class ScrubPlan:
    root: Path
    owner_ids: tuple[str, ...]
    files: tuple[ScrubFile, ...]
    created_at: str

    @property
    def store_count(self) -> int:
        return len({item.store_name for item in self.files})

    @property
    def total_matches(self) -> int:
        return sum(item.owner_matches for item in self.files)


@dataclass(frozen=True)
class ScrubManifest:
    tool_version: str
    mode: str
    generated_at: str
    owner_count: int
    stores: tuple[str, ...]
    before_digests: Mapping[str, str]
    after_digests: Mapping[str, str | None]
    counts: Mapping[str, int]
    scanner: Mapping[str, Any]
    sentinels: Mapping[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_version": self.tool_version,
            "mode": self.mode,
            "generated_at": self.generated_at,
            "owner_count": self.owner_count,
            "stores": list(self.stores),
            "before_digests": dict(self.before_digests),
            "after_digests": dict(self.after_digests),
            "counts": dict(self.counts),
            "scanner": dict(self.scanner),
            "sentinels": dict(self.sentinels),
        }


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _digest_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _validate_owner_ids(owner_ids: Iterable[str]) -> tuple[str, ...]:
    if isinstance(owner_ids, (str, bytes)):
        raise ValueError("owner_ids must be a sequence of non-empty strings")
    values = tuple(dict.fromkeys(owner_ids))
    if not values or any(not isinstance(item, str) or not item or "\x00" in item for item in values):
        raise ValueError("owner_ids must contain non-empty strings")
    return values


def _conversation_files(path: Path, relative: str) -> tuple[Path, ...]:
    if not path.is_dir():
        return ()
    if path.is_symlink():
        raise ScrubDataError(f"symlinked declared store: {relative}")
    files = []
    for child in sorted(path.glob("*.json")):
        if child.is_symlink():
            raise ScrubDataError(f"symlinked declared file: {child.name}")
        if child.is_file():
            files.append(child)
    return tuple(files)


def _checked_optional_file(root: Path, relative: str, kind: str):
    path = root / relative
    if path.is_symlink():
        raise ScrubDataError(f"symlinked declared file: {relative}")
    return (path, kind) if path.is_file() else None


def _single_store_files(root: Path, store_name: str, relative: str, kind: str):
    selected = []
    primary = _checked_optional_file(root, relative, kind)
    if primary:
        selected.append(primary)
    alias = _OPTIONAL_ALIASES.get(store_name)
    if alias:
        legacy = _checked_optional_file(root, alias[0], alias[1])
        if legacy:
            selected.append(legacy)
    return tuple(selected)


def _iter_declared_files(root: Path):
    for store_name, (relative, kind) in DECLARED_STORES.items():
        if kind == "conversation_dir":
            for path in _conversation_files(root / relative, relative):
                yield store_name, path, "conversation"
            continue
        for selected in _single_store_files(root, store_name, relative, kind):
            yield store_name, selected[0], selected[1]


def _load_file(path: Path, kind: str):
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ScrubDataError(f"cannot read declared store: {path.name}") from exc
    if kind == "profiles":
        return _load_profiles(path, text)
    if kind in {"json", "conversation"}:
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise ScrubDataError(f"invalid JSON in declared store: {path.name}") from exc
    if kind == "jsonl":
        rows = []
        for line_number, line in enumerate(text.splitlines(), 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ScrubDataError(f"invalid JSONL at line {line_number}: {path.name}") from exc
        return rows
    raise ScrubDataError(f"unsupported declared store kind: {kind}")


def _profile_encryption_key(path: Path) -> bytes:
    env_key = os.environ.get("MEMORY_ENCRYPTION_KEY")
    if env_key:
        return env_key.encode("utf-8")
    key_path = path.parent / ".key"
    if not key_path.is_file():
        raise ScrubDataError("encrypted cold memory is missing its key file")
    return key_path.read_bytes().strip()


def _load_profiles(path: Path, text: str) -> _ProfileStore:
    encrypted = not text.lstrip().startswith("{")
    key = _profile_encryption_key(path) if encrypted else None
    try:
        plaintext = Fernet(key).decrypt(text.strip().encode("utf-8")).decode("utf-8") if encrypted else text
        data = json.loads(plaintext)
    except (InvalidToken, ValueError, json.JSONDecodeError) as exc:
        raise ScrubDataError("invalid or undecryptable cold memory store") from exc
    if not isinstance(data, dict):
        raise ScrubDataError("invalid cold memory store")
    return _ProfileStore(data=data, encrypted=encrypted, key=key)


def _owner_match(value: Any, owner_ids: set[str]) -> bool:
    return isinstance(value, str) and value in owner_ids


def _record_owner_match(record: Mapping[str, Any], owner_ids: set[str]) -> bool:
    return any(
        _owner_match(record.get(field), owner_ids)
        for field in ("owner_key", "user_id", "user_key", "actor")
    )


def _redact(value: Any) -> Any:
    return redact_log_value(value)


def _graph_collections(payload: Any) -> tuple[list, list]:
    if not isinstance(payload, dict):
        raise ScrubDataError("invalid memory graph")
    nodes = payload.get("nodes", [])
    edges = payload.get("edges", [])
    if not isinstance(nodes, list) or not isinstance(edges, list):
        raise ScrubDataError("invalid memory graph collections")
    if any(not isinstance(node, dict) for node in nodes) or any(not isinstance(edge, dict) for edge in edges):
        raise ScrubDataError("invalid memory graph records")
    return nodes, edges


def _scrub_graph(payload: Any, owner_ids: set[str]) -> tuple[Any, int, bool]:
    nodes, edges = _graph_collections(payload)
    retained_nodes = [node for node in nodes if not (isinstance(node, dict) and _owner_match(node.get("id"), owner_ids))]
    retained_edges = [edge for edge in edges if not _edge_owner_match(edge, owner_ids)]
    result = dict(payload)
    result["nodes"] = [_redact(node) for node in retained_nodes]
    result["edges"] = [_redact(edge) for edge in retained_edges]
    removed = len(nodes) - len(retained_nodes) + len(edges) - len(retained_edges)
    return _redact(result), removed, False


def _edge_owner_match(edge: Any, owner_ids: set[str]) -> bool:
    return isinstance(edge, dict) and (
        _owner_match(edge.get("source"), owner_ids)
        or _owner_match(edge.get("target"), owner_ids)
    )


def _scrub_semantic_cache(payload: Any, owner_ids: set[str]) -> tuple[Any, int, bool]:
    if not isinstance(payload, dict):
        raise ScrubDataError("invalid semantic cache")
    if any(not isinstance(entry, dict) for entry in payload.values()):
        raise ScrubDataError("invalid semantic cache entry")
    retained = {
        key: _redact(entry)
        for key, entry in payload.items()
        if not (isinstance(entry, dict) and _owner_match(entry.get("owner_key"), owner_ids))
    }
    return retained, len(payload) - len(retained), False


def _scrub_ab_outcomes(payload: Any, owner_ids: set[str]) -> tuple[Any, int, bool]:
    if not isinstance(payload, dict):
        raise ScrubDataError("invalid A/B store")
    result = _redact(payload)
    owners = payload.get("outcome_owners", {})
    if not isinstance(owners, dict):
        raise ScrubDataError("invalid A/B owner map")
    result["outcome_owners"] = {}
    removed = 0
    for experiment, sessions in owners.items():
        if not isinstance(sessions, dict):
            raise ScrubDataError("invalid A/B owner map")
        removed_sessions = {sid for sid, owner in sessions.items() if _owner_match(owner, owner_ids)}
        removed += len(removed_sessions)
        result["outcome_owners"][experiment] = {
            sid: owner for sid, owner in sessions.items() if sid not in removed_sessions
        }
        _drop_ab_sessions(result, experiment, removed_sessions)
    return result, removed, False


def _drop_ab_sessions(result: dict[str, Any], experiment: str, removed: set[str]) -> None:
    for field in ("outcomes", "assignments"):
        section = result.get(field)
        if section is None:
            continue
        if not isinstance(section, dict):
            raise ScrubDataError(f"invalid A/B {field} map")
        experiment_rows = section.get(experiment, {})
        if not isinstance(experiment_rows, dict):
            raise ScrubDataError(f"invalid A/B {field} experiment")
        section[experiment] = {
            sid: value for sid, value in experiment_rows.items() if sid not in removed
        }


def _scrub_record_list(payload: Any, owner_ids: set[str], label: str) -> tuple[Any, int, bool]:
    if not isinstance(payload, list):
        raise ScrubDataError(f"invalid list store: {label}")
    if any(not isinstance(row, dict) for row in payload):
        raise ScrubDataError(f"invalid record in list store: {label}")
    retained = [row for row in payload if not _record_owner_match(row, owner_ids)]
    return _redact(retained), len(payload) - len(retained), False


def _scrub_mapping_records(payload: Any, owner_ids: set[str], label: str) -> tuple[Any, int, bool]:
    if not isinstance(payload, dict):
        raise ScrubDataError(f"invalid mapping store: {label}")
    result = _redact(payload)
    removed = 0
    fields = ("queries", "unanswered") if label == "analytics" else ("records",)
    for field in fields:
        rows = payload.get(field, [])
        cleaned, count, _ = _scrub_record_list(rows, owner_ids, label)
        result[field] = cleaned
        removed += count
    return result, removed, False


def _scrub_keyed_owners(payload: Any, owner_ids: set[str], label: str) -> tuple[Any, int, bool]:
    if not isinstance(payload, dict):
        raise ScrubDataError(f"invalid keyed owner store: {label}")
    retained = {key: value for key, value in payload.items() if key not in owner_ids}
    return _redact(retained), len(payload) - len(retained), False


def _scrub_cold_memory(payload: Any, owner_ids: set[str]) -> tuple[Any, int, bool]:
    if not isinstance(payload, _ProfileStore):
        raise ScrubDataError("invalid cold memory store")
    cleaned, removed, _ = _scrub_keyed_owners(payload.data, owner_ids, "cold_memory")
    return _ProfileStore(cleaned, payload.encrypted, payload.key), removed, False


def _scrub_guardrail_budget(payload: Any, owner_ids: set[str]) -> tuple[Any, int, bool]:
    if not isinstance(payload, dict) or not isinstance(payload.get("sessions"), dict):
        raise ScrubDataError("invalid guardrail budget store")
    cleaned, removed, _ = _scrub_keyed_owners(payload["sessions"], owner_ids, "guardrail_budget")
    result = _redact(payload)
    result["sessions"] = cleaned
    return result, removed, False


def _scrub_compiled_demos(payload: Any, owner_ids: set[str]) -> tuple[Any, int, bool]:
    if not isinstance(payload, dict) or not isinstance(payload.get("demos", {}), dict):
        raise ScrubDataError("invalid compiled prompt store")
    result = _redact(payload)
    result["demos"] = {}
    removed = 0
    for intent, rows in payload["demos"].items():
        cleaned, count, _ = _scrub_record_list(rows, owner_ids, "compiled demos")
        result["demos"][intent] = cleaned
        removed += count
    return result, removed, False


def _scrub_jsonl(payload: Any, owner_ids: set[str], label: str) -> tuple[Any, int, bool]:
    if not isinstance(payload, list):
        raise ScrubDataError(f"invalid JSONL store: {label}")
    rows = []
    removed = 0
    for row in payload:
        if not isinstance(row, dict):
            raise ScrubDataError(f"invalid JSONL record: {label}")
        if label == "learn_loop" and _record_owner_match(row, owner_ids):
            removed += 1
            continue
        cleaned = _redact(row)
        if label == "admin_audit" and _owner_match(row.get("actor"), owner_ids):
            cleaned["actor"] = None
        rows.append(cleaned)
    return rows, removed, False


def _scrub_conversation(payload: Any, owner_ids: set[str]) -> tuple[Any, int, bool]:
    if not isinstance(payload, dict):
        raise ScrubDataError("invalid conversation store")
    return (None, 1, True) if _owner_match(payload.get("owner_key"), owner_ids) else (_redact(payload), 0, False)


def _scrub_learn_loop(payload: Any, owner_ids: set[str]) -> tuple[Any, int, bool]:
    return _scrub_jsonl(payload, owner_ids, "learn_loop")


def _scrub_admin_audit(payload: Any, owner_ids: set[str]) -> tuple[Any, int, bool]:
    return _scrub_jsonl(payload, owner_ids, "admin_audit")


def _scrub_experience_memory(payload: Any, owner_ids: set[str]) -> tuple[Any, int, bool]:
    return _scrub_record_list(payload, owner_ids, "experience_memory")


def _scrub_prompt_demonstrations_raw(payload: Any, owner_ids: set[str]) -> tuple[Any, int, bool]:
    return _scrub_record_list(payload, owner_ids, "prompt_demonstrations_raw")


def _scrub_analytics(payload: Any, owner_ids: set[str]) -> tuple[Any, int, bool]:
    return _scrub_mapping_records(payload, owner_ids, "analytics")


def _scrub_cost_attribution(payload: Any, owner_ids: set[str]) -> tuple[Any, int, bool]:
    return _scrub_mapping_records(payload, owner_ids, "cost_attribution")


def _scrub_optimizer_records(payload: Any, owner_ids: set[str]) -> tuple[Any, int, bool]:
    return _scrub_mapping_records(payload, owner_ids, "optimizer_records")


_SCRUB_ADAPTERS = {
    "memory_graph": _scrub_graph,
    "cold_memory": _scrub_cold_memory,
    "semantic_cache": _scrub_semantic_cache,
    "ab_outcomes": _scrub_ab_outcomes,
    "conversation_history": _scrub_conversation,
    "experience_memory": _scrub_experience_memory,
    "prompt_demonstrations_raw": _scrub_prompt_demonstrations_raw,
    "analytics": _scrub_analytics,
    "cost_attribution": _scrub_cost_attribution,
    "optimizer_records": _scrub_optimizer_records,
    "prompt_demonstrations_compiled": _scrub_compiled_demos,
    "learn_loop": _scrub_learn_loop,
    "admin_audit": _scrub_admin_audit,
    "guardrail_budget": _scrub_guardrail_budget,
}


def _scrub_payload(store_name: str, payload: Any, owner_ids: set[str]) -> tuple[Any, int, bool]:
    """Return scrubbed payload, exact owner-match count, and delete marker."""
    adapter = _SCRUB_ADAPTERS.get(store_name)
    if adapter is None:
        raise ScrubDataError(f"no scrub adapter for {store_name}")
    return adapter(payload, owner_ids)


def _render(payload: Any, kind: str) -> bytes:
    if kind == "profiles":
        if not isinstance(payload, _ProfileStore):
            raise ScrubDataError("invalid rendered cold memory store")
        plaintext = json.dumps(payload.data, ensure_ascii=False, indent=2)
        if payload.encrypted:
            if payload.key is None:
                raise ScrubDataError("cold memory encryption key is unavailable")
            return Fernet(payload.key).encrypt(plaintext.encode("utf-8"))
        return (plaintext + "\n").encode("utf-8")
    if kind == "jsonl":
        return "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in payload).encode("utf-8")
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _scan_value(value: Any) -> tuple[int, set[str]]:
    findings = 0
    types: set[str] = set()
    if isinstance(value, _ProfileStore):
        return _scan_value(value.data)
    if isinstance(value, str):
        spans = pii_masker.detect_spans(value)
        findings += len(spans)
        types.update(span.kind for span in spans)
    elif isinstance(value, Mapping):
        for key, item in value.items():
            if isinstance(key, str):
                key_findings, key_types = _scan_value(key)
                findings += key_findings
                types.update(key_types)
            child_findings, child_types = _scan_value(item)
            findings += child_findings
            types.update(child_types)
    elif isinstance(value, (list, tuple)):
        for item in value:
            child_findings, child_types = _scan_value(item)
            findings += child_findings
            types.update(child_types)
    return findings, types


def _file_preview(item: ScrubFile, owner_ids: set[str]) -> tuple[Any, int, bool, int, set[str]]:
    payload = _load_file(item.path, item.kind)
    scrubbed, matches, delete = _scrub_payload(item.store_name, payload, owner_ids)
    findings, types = _scan_value(payload)
    return scrubbed, matches, delete, findings, types


def build_scrub_plan(root: str | Path, *, owner_ids: Sequence[str]) -> ScrubPlan:
    root_path = Path(root).resolve()
    if not root_path.is_dir():
        raise ValueError("scrub root must be an existing directory")
    owners = _validate_owner_ids(owner_ids)
    files: list[ScrubFile] = []
    owner_set = set(owners)
    for store_name, path, kind in _iter_declared_files(root_path):
        content = path.read_bytes()
        _scrubbed, matches, _delete, pii_findings, _types = _file_preview(
            ScrubFile(store_name, path, kind, _digest_bytes(content), len(content), 0, 0),
            owner_set,
        )
        files.append(
            ScrubFile(
                store_name=store_name,
                path=path,
                kind=kind,
                before_digest=_digest_bytes(content),
                before_bytes=len(content),
                owner_matches=matches,
                pii_findings=pii_findings,
            )
        )
    if not files:
        raise ScrubDataError("no declared stores found under scrub root")
    return ScrubPlan(root_path, owners, tuple(files), _utc_now())


def _manifest_key(plan: ScrubPlan, item: ScrubFile) -> str:
    try:
        relative = item.path.resolve().relative_to(plan.root).as_posix()
    except ValueError:
        relative = item.path.name
    opaque_id = hashlib.sha256(
        f"legacy-scrub-file:{item.store_name}:{relative}".encode("utf-8")
    ).hexdigest()[:24]
    return f"{item.store_name}:{opaque_id}"


def scrub_plan_summary(plan: ScrubPlan) -> dict[str, Any]:
    return {
        "mode": "dry-run",
        "store_count": plan.store_count,
        "file_count": len(plan.files),
        "owner_matches": plan.total_matches,
        "pii_findings": sum(item.pii_findings for item in plan.files),
        "files": [
            {
                "file_id": _manifest_key(plan, item),
                "store_name": item.store_name,
                "before_digest": item.before_digest,
                "before_bytes": item.before_bytes,
                "owner_matches": item.owner_matches,
                "pii_findings": item.pii_findings,
            }
            for item in plan.files
        ],
    }


def _validate_plan_scope(plan: ScrubPlan) -> None:
    root = plan.root.resolve()
    if not root.is_dir():
        raise ScrubError("scrub root is no longer available")
    for item in plan.files:
        if item.path.is_symlink():
            raise ScrubError(f"symlinked declared file: {item.relative_path}")
        try:
            item.path.resolve().relative_to(root)
        except ValueError as exc:
            raise ScrubError("scrub plan contains a path outside its root") from exc


def _inventory_snapshot(root: Path) -> tuple[tuple[str, str, str], ...]:
    return tuple(sorted(
        (
            store_name,
            path.resolve().relative_to(root).as_posix(),
            kind,
        )
        for store_name, path, kind in _iter_declared_files(root)
    ))


def _validate_inventory_snapshot(plan: ScrubPlan) -> None:
    expected = tuple(sorted(
        (
            item.store_name,
            item.path.resolve().relative_to(plan.root).as_posix(),
            item.kind,
        )
        for item in plan.files
    ))
    if _inventory_snapshot(plan.root) != expected:
        raise StaleScrubPlan("declared store inventory changed after planning")


def _validate_post_apply_inventory(plan: ScrubPlan, rendered) -> None:
    expected = tuple(sorted(
        (
            item.store_name,
            item.path.resolve().relative_to(plan.root).as_posix(),
            item.kind,
        )
        for item, _content, delete, _matches, _types in rendered
        if not delete
    ))
    if _inventory_snapshot(plan.root) != expected:
        raise StaleScrubPlan("declared store inventory changed after scrub")


def _assert_backup_evidence(plan: ScrubPlan, backup_evidence: str | Path | None) -> Path:
    if backup_evidence is None:
        raise BackupEvidenceRequired("--apply requires explicit backup evidence")
    path = Path(backup_evidence).resolve()
    try:
        if not path.is_file() or path.stat().st_size <= 0:
            raise BackupEvidenceRequired("backup evidence must be a non-empty file")
    except OSError as exc:
        raise BackupEvidenceRequired("backup evidence could not be inspected") from exc
    if any(path == item.path.resolve() for item in plan.files):
        raise ScrubError("backup evidence overlaps a declared scrub input")
    return path


def _count_owner_rows(rows: Any, owners: set[str]) -> int:
    if not isinstance(rows, list):
        return 0
    return sum(
        1
        for row in rows
        if isinstance(row, dict) and _record_owner_match(row, owners)
    )


def _remaining_graph(payload: Any, owners: set[str]) -> int:
    if not isinstance(payload, dict):
        return 0
    nodes = sum(
        1
        for node in payload.get("nodes", [])
        if isinstance(node, dict) and _owner_match(node.get("id"), owners)
    )
    edges = sum(1 for edge in payload.get("edges", []) if _edge_owner_match(edge, owners))
    return nodes + edges


def _remaining_cold_memory(payload: Any, owners: set[str]) -> int:
    if not isinstance(payload, _ProfileStore):
        return 0
    return sum(1 for key in payload.data if key in owners)


def _remaining_semantic(payload: Any, owners: set[str]) -> int:
    if not isinstance(payload, dict):
        return 0
    return sum(
        1
        for entry in payload.values()
        if isinstance(entry, dict) and _owner_match(entry.get("owner_key"), owners)
    )


def _remaining_ab(payload: Any, owners: set[str]) -> int:
    if not isinstance(payload, dict):
        return 0
    owner_maps = payload.get("outcome_owners", {})
    if not isinstance(owner_maps, dict):
        return 0
    return sum(
        1
        for sessions in owner_maps.values()
        if isinstance(sessions, dict)
        for owner in sessions.values()
        if _owner_match(owner, owners)
    )


def _remaining_compiled(payload: Any, owners: set[str]) -> int:
    if not isinstance(payload, dict):
        return 0
    demos = payload.get("demos", {})
    if not isinstance(demos, dict):
        return 0
    return sum(_count_owner_rows(rows, owners) for rows in demos.values())


def _remaining_conversation(payload: Any, owners: set[str]) -> int:
    if not isinstance(payload, dict):
        return 0
    return int(_owner_match(payload.get("owner_key"), owners))


def _remaining_guardrail(payload: Any, owners: set[str]) -> int:
    if not isinstance(payload, dict) or not isinstance(payload.get("sessions"), dict):
        return 0
    return sum(1 for key in payload["sessions"] if key in owners)


def _remaining_mapping(payload: Any, owners: set[str]) -> int:
    if not isinstance(payload, dict):
        return 0
    return sum(
        _count_owner_rows(payload.get(field), owners)
        for field in ("queries", "unanswered", "records")
    )


_REMAINING_HANDLERS = {
    "memory_graph": _remaining_graph,
    "cold_memory": _remaining_cold_memory,
    "semantic_cache": _remaining_semantic,
    "ab_outcomes": _remaining_ab,
    "prompt_demonstrations_compiled": _remaining_compiled,
    "conversation_history": _remaining_conversation,
    "guardrail_budget": _remaining_guardrail,
}


def _remaining_for_store(store_name: str, payload: Any, owners: set[str]) -> int:
    _scrub_payload(store_name, payload, set())
    handler = _REMAINING_HANDLERS.get(store_name)
    if handler:
        return handler(payload, owners)
    if isinstance(payload, list):
        return _count_owner_rows(payload, owners)
    return _remaining_mapping(payload, owners)


def _remaining_owner_references(plan: ScrubPlan) -> int:
    owners = set(plan.owner_ids)
    return sum(
        _remaining_for_store(item.store_name, _load_file(item.path, item.kind), owners)
        for item in plan.files
        if item.path.exists()
    )


def _prepare_apply(plan: ScrubPlan):
    owner_set = set(plan.owner_ids)
    rendered = []
    for item in plan.files:
        if not item.path.exists() or _digest_bytes(item.path.read_bytes()) != item.before_digest:
            raise StaleScrubPlan(f"before digest changed for {item.relative_path}")
        scrubbed, matches, delete, _pii_before, types = _file_preview(item, owner_set)
        if not delete and _remaining_for_store(item.store_name, scrubbed, owner_set):
            raise ScrubError("owner references remain in planned output")
        if not delete and _scan_value(scrubbed)[0]:
            raise ScrubError("PII remains in planned output")
        content = None if delete else _render(scrubbed, item.kind)
        rendered.append((item, content, delete, matches, types))
    return rendered


def _write_rendered(plan: ScrubPlan, rendered) -> tuple[dict, dict, set[str]]:
    after_digests: dict[str, str | None] = {}
    counts = {"files_rewritten": 0, "files_deleted": 0, "records_removed": 0}
    pii_types: set[str] = set()
    for item, content, delete, matches, types in rendered:
        counts["records_removed"] += matches
        pii_types.update(types)
        key = _manifest_key(plan, item)
        if delete:
            item.path.unlink()
            after_digests[key] = None
            counts["files_deleted"] += 1
            continue
        if content == item.path.read_bytes():
            after_digests[key] = item.before_digest
            continue
        temp_path = item.path.with_name(f".{item.path.name}.scrub.tmp")
        temp_path.write_bytes(content or b"")
        temp_path.replace(item.path)
        after_digests[key] = _digest_bytes(content or b"")
        counts["files_rewritten"] += 1
    return after_digests, counts, pii_types


def _scan_after_apply(plan: ScrubPlan) -> tuple[int, set[str]]:
    findings = 0
    pii_types: set[str] = set()
    for item in plan.files:
        if not item.path.exists():
            continue
        file_findings, file_types = _scan_value(_load_file(item.path, item.kind))
        findings += file_findings
        pii_types.update(file_types)
    return findings, pii_types


def apply_scrub_plan(
    plan: ScrubPlan,
    *,
    backup_evidence: str | Path | None = None,
) -> ScrubManifest:
    _assert_backup_evidence(plan, backup_evidence)
    _validate_plan_scope(plan)
    _validate_inventory_snapshot(plan)
    rendered = _prepare_apply(plan)
    before_digests = {_manifest_key(plan, item): item.before_digest for item in plan.files}
    after_digests, apply_counts, pii_types = _write_rendered(plan, rendered)
    _validate_post_apply_inventory(plan, rendered)
    remaining = _remaining_owner_references(plan)
    if remaining:
        raise ScrubError("owner references remain after scrub")
    pii_after, after_types = _scan_after_apply(plan)
    if pii_after:
        raise ScrubError("PII remains after scrub")
    return ScrubManifest(
        tool_version=TOOL_VERSION,
        mode="apply",
        generated_at=_utc_now(),
        owner_count=len(plan.owner_ids),
        stores=tuple(sorted({item.store_name for item in plan.files})),
        before_digests=before_digests,
        after_digests=after_digests,
        counts={
            "files_seen": len(plan.files),
            **apply_counts,
            "pii_findings_before": sum(item.pii_findings for item in plan.files),
        },
        scanner={
            "files_scanned": len(plan.files),
            "pii_findings": pii_after,
            "pii_types_before": sorted(pii_types),
            "pii_types_after": sorted(after_types),
        },
        sentinels={"owner_references_remaining": remaining},
    )


def write_scrub_manifest(manifest: ScrubManifest, path: str | Path) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError(destination)
    encoded = json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2) + "\n"
    temporary = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(encoded, encoding="utf-8")
    try:
        os.link(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination
