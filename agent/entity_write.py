"""The entity write boundary.

Every operation here runs on a connection the **caller** owns, and this module
never opens one of its own and never commits. That is the whole point: a
publication step can write the entity row, its change audit and the case's own
fulfilment records inside a single transaction, so a failure anywhere leaves the
entry exactly as it was. A nested connection would quietly break that guarantee
while every test still looked green, so a test asserts this module's source
contains neither.

Cache mutations are returned, not applied. The caller applies them after its
transaction commits, because a cache that is updated before the commit is a
cache that can advertise a change which never happened.

`verifiedAt` is not writable here. It is the single field that says a human
checked this on the ground, and it may only move through an authorised
verification command — never through a correction apply or an admin edit.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import entity_details as _entity_details

# Fields an ordinary content change may touch. Everything about publication
# status, ownership or verification is deliberately absent.
WRITABLE_FIELDS = (
    "name",
    "type",
    "summary",
    "description",
    "placeId",
    "confidence",
    "season",
    "attributes",
    "images",
    "coordinates",
    "area",
)
# Tracked for the change audit; mirrors database.log_entity_changes.
AUDITED_FIELDS = (
    "name", "type", "summary", "placeId", "confidence", "season",
    "attributes", "images", "coordinates", "area",
)
VERIFICATION_MARKERS = frozenset({"verifiedAt", "attributes.verifiedAt", "verified"})
MAX_AUDIT_VALUE = 2000


class EntityWriteRejected(RuntimeError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(code)
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class EntitySnapshot:
    entity_id: str
    revision: int
    values: dict


@dataclass(frozen=True)
class EntityWriteResult:
    entity_id: str
    revision: int
    changed_fields: tuple[str, ...]
    before: dict
    after: dict
    cache_mutations: tuple = field(default_factory=tuple)


class EntityWriteService:
    """Caller-owned entity mutation. Opens no connection, commits nothing."""

    def __init__(self, database) -> None:
        self._db = database

    def _placeholder(self) -> str:
        return "%s" if self._db._use_pg else "?"

    def load_for_update(self, conn, entity_id: str) -> EntitySnapshot:
        ph = self._placeholder()
        lock = " FOR UPDATE" if self._db._use_pg else ""
        row = self._db._fetchone(
            conn,
            f"SELECT id, name, type, summary, description, revision"
            f" FROM entities WHERE id = {ph}{lock}",
            (entity_id,),
        )
        if row is None:
            raise EntityWriteRejected("entity_not_found", "That entry does not exist.")
        item = self._db._row_to_dict(row)
        return EntitySnapshot(
            entity_id=str(item["id"]),
            revision=int(item["revision"] or 1),
            values={
                key: item.get(key)
                for key in ("name", "type", "summary", "description")
            },
        )

    def upsert(self, conn, entity: dict) -> tuple:
        """The whole-row write every legacy caller already performs, on `conn`.

        Detail-cache mutations are returned, not applied. The cache may only
        learn about a change the caller's transaction actually kept.
        """
        # Local import: database imports this module, so a top-level one loops.
        import database as _database

        _database._validate_place_level(entity)
        (season_val, attrs_val, source_val, images_val,
         coords_val, updated, attrs_store) = _database._normalize_upsert_fields(entity)
        self._db._write_entity_row(conn, entity, season_val, attrs_store,
                                   source_val, images_val, coords_val, updated)
        # GD-C dual-write: cot pho quat + bang CTI phan chieu attrs (cung transaction).
        mutation = _entity_details.sync_entity_details(
            conn, self._db._use_pg, entity["id"], entity["type"],
            attrs_val if isinstance(attrs_val, dict) else {})
        return (mutation,)

    @staticmethod
    def _reject_verification_markers(patch: dict) -> None:
        for key in patch:
            if key in VERIFICATION_MARKERS:
                raise EntityWriteRejected(
                    "verification_marker_not_writable",
                    "Verification only moves through an authorised verification command.",
                )

    def apply_patch(
        self,
        conn,
        entity_id: str,
        patch: dict,
        *,
        expected_revision: int,
        actor: str,
        provenance: str,
    ) -> EntityWriteResult:
        if not isinstance(patch, dict) or not patch:
            raise EntityWriteRejected("empty_entity_patch", "A patch needs at least one field.")
        self._reject_verification_markers(patch)
        unknown = set(patch) - set(WRITABLE_FIELDS)
        if unknown:
            raise EntityWriteRejected(
                "field_not_writable", "That field is not writable through this boundary."
            )

        snapshot = self.load_for_update(conn, entity_id)
        if snapshot.revision != expected_revision:
            raise EntityWriteRejected(
                "entity_revision_conflict", "That entry changed since it was read."
            )

        before = {key: snapshot.values.get(key) for key in patch}
        changed = tuple(
            sorted(key for key, value in patch.items() if before.get(key) != value)
        )
        if not changed:
            # A no-op must not burn a revision or move updatedAt: downstream
            # freshness signals read those, and a false bump is a false claim.
            return EntityWriteResult(
                entity_id=entity_id,
                revision=snapshot.revision,
                changed_fields=(),
                before=before,
                after=dict(patch),
                cache_mutations=(),
            )

        ph = self._placeholder()
        assignments = ", ".join(f"{name} = {ph}" for name in changed)
        params = tuple(patch[name] for name in changed) + (entity_id, expected_revision)
        row = self._db._fetchone(
            conn,
            f'UPDATE entities SET {assignments}, revision = revision + 1, "updatedAt" = NOW()'
            f' WHERE id = {ph} AND revision = {ph} RETURNING revision',
            params,
        )
        if row is None:
            # Somebody committed between the read and the write.
            raise EntityWriteRejected(
                "entity_revision_conflict", "That entry changed while it was being written."
            )
        return EntityWriteResult(
            entity_id=entity_id,
            revision=int(self._db._row_to_dict(row)["revision"]),
            changed_fields=changed,
            before=before,
            after={name: patch[name] for name in changed},
            cache_mutations=(),
        )

    def write_change_audit(
        self, conn, result: EntityWriteResult, *, actor: str, provenance: str
    ) -> None:
        """The audit rides the caller's transaction, so it cannot outlive a rollback."""
        if not result.changed_fields:
            return
        ph = self._placeholder()
        for name in result.changed_fields:
            if name not in AUDITED_FIELDS:
                continue
            old_value = "" if result.before.get(name) is None else str(result.before[name])
            new_value = "" if result.after.get(name) is None else str(result.after[name])
            self._db._execute(
                conn,
                f"INSERT INTO entity_changes (entity_id, field, old_value, new_value, actor)"
                f" VALUES ({ph}, {ph}, {ph}, {ph}, {ph})",
                (
                    result.entity_id,
                    name,
                    old_value[:MAX_AUDIT_VALUE],
                    new_value[:MAX_AUDIT_VALUE],
                    f"{actor}|{provenance}",
                ),
            )
