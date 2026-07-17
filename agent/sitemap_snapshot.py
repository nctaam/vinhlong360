"""Load the sitemap's PostgreSQL source rows from one consistent snapshot."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SitemapSnapshot:
    entities: tuple[dict, ...]
    relationships: tuple[dict, ...]
    wards: tuple[dict, ...]


def load_sitemap_snapshot(database) -> SitemapSnapshot:
    """Read sitemap inputs from one PostgreSQL repeatable-read transaction."""
    if not database._use_pg:
        raise RuntimeError("sitemap snapshots require PostgreSQL")

    with database._conn(commit_on_success=False) as conn:
        database._execute(
            conn,
            "BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY",
            (),
        )
        entity_rows = database._execute(conn, "SELECT * FROM entities", ()).fetchall()
        entities = tuple(database._row_to_dict(row) for row in entity_rows)

        relationship_rows = database._execute(
            conn,
            "SELECT from_id AS source_id, to_id AS target_id, type FROM relationships",
            (),
        ).fetchall()
        relationships = tuple(database._row_to_dict(row) for row in relationship_rows)
        wards = tuple(entity for entity in entities if entity.get("type") == "place")
        snapshot = SitemapSnapshot(
            entities=entities,
            relationships=relationships,
            wards=wards,
        )
        return snapshot
