"""
vinhlong360 — Database Layer (PostgreSQL + SQLite fallback).

Supports PostgreSQL (production) via psycopg2 and SQLite (dev) as fallback.
Backend is selected by DATABASE_URL env var:
  - Set → PostgreSQL (postgresql://user:pass@host/db)
  - Not set → SQLite at agent/data/vinhlong360.db

Usage:
  from database import db
  db.search_entities(q="cam", area="vinh-long")
  db.upsert_entity({...})
"""

import json
import math
import os
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from threading import Lock

# ── Config ──

DB_DIR = Path(__file__).resolve().parent / "data"
DB_DIR.mkdir(exist_ok=True)
DB_PATH = DB_DIR / "vinhlong360.db"

DATABASE_URL = os.getenv("DATABASE_URL", "")
USE_PG = DATABASE_URL.startswith("postgresql")

RELATIONSHIP_TYPE_PRIORITY = {
    "hosts": 0,
    "offered_by": 1,
    "supplies_to": 2,
    "produced_in": 3,
    "associated_with": 4,
    "related_to": 5,
    "near": 9,
}

if USE_PG:
    import psycopg2
    import psycopg2.extras


# Bbox vùng VL+Bến Tre+Trà Vinh — guard validate toạ độ geocode (chống khớp nhầm tỉnh khác)
_REGION_BBOX = (9.2, 10.65, 105.6, 106.95)  # lat_min, lat_max, lng_min, lng_max


def _validate_place_level(entity: dict):
    """Auto-fix level khi name prefix mâu thuẫn — phòng lỗi sáp nhập 2026-06-15."""
    if entity.get("type") != "place":
        return
    name = entity.get("name", "")
    level = entity.get("level")
    if name.startswith("Phường ") and level == "xa":
        entity["level"] = "phuong"
    elif name.startswith("Xã ") and level == "phuong":
        entity["level"] = "xa"
    eid = entity.get("id", "")
    if eid.startswith("p-") and entity.get("level") == "xa":
        entity["level"] = "phuong"
    elif eid.startswith("xa-") and entity.get("level") == "phuong":
        entity["level"] = "xa"


def _coords_in_region(c) -> bool:
    """True nếu [lat, lng] nằm trong vùng 3 tỉnh. Toạ độ ngoài vùng = geocode sai → loại."""
    try:
        lat, lng = float(c[0]), float(c[1])
    except (TypeError, IndexError, ValueError):
        return False
    return _REGION_BBOX[0] <= lat <= _REGION_BBOX[1] and _REGION_BBOX[2] <= lng <= _REGION_BBOX[3]


# ══════════════════════════════════════════════════
#  DATABASE CLASS
# ══════════════════════════════════════════════════

class Database:
    """Database with thread-safe connections. PostgreSQL or SQLite."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(DB_PATH)
        self._lock = Lock()
        self._initialized = False
        self._use_pg = USE_PG
        self._dsn = DATABASE_URL if USE_PG else None

    @contextmanager
    def _conn(self):
        """Thread-safe connection context manager."""
        if self._use_pg:
            conn = psycopg2.connect(self._dsn)
            conn.autocommit = False
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()
        else:
            conn = sqlite3.connect(self.db_path, timeout=30)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA busy_timeout=5000")
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def _cursor(self, conn):
        if self._use_pg:
            return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        return conn

    def _param(self, idx: int = 0) -> str:
        return "%s" if self._use_pg else "?"

    @property
    def _ph(self) -> str:
        return "%s" if self._use_pg else "?"

    def _execute(self, conn, sql: str, params=None):
        """Execute with param style conversion."""
        if self._use_pg:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute(sql, params or ())
            return cur
        else:
            return conn.execute(sql, params or ())

    def _fetchone(self, conn, sql: str, params=None):
        if self._use_pg:
            cur = self._execute(conn, sql, params)
            return cur.fetchone()
        else:
            return conn.execute(sql, params or ()).fetchone()

    def _fetchall(self, conn, sql: str, params=None):
        if self._use_pg:
            cur = self._execute(conn, sql, params)
            return cur.fetchall()
        else:
            return conn.execute(sql, params or ()).fetchall()

    def _row_to_dict(self, row) -> dict:
        if row is None:
            return None
        if isinstance(row, dict):
            return row
        return dict(row)

    def initialize(self):
        """Create tables if they don't exist (SQLite only; PG uses init.sql)."""
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return

            if self._use_pg:
                with self._conn() as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT 1 FROM entities LIMIT 1")
                self._initialized = True
                return

            with self._conn() as conn:
                conn.executescript("""
                    CREATE TABLE IF NOT EXISTS entities (
                        id TEXT PRIMARY KEY,
                        type TEXT NOT NULL,
                        name TEXT NOT NULL,
                        summary TEXT DEFAULT '',
                        description TEXT DEFAULT '',
                        placeId TEXT,
                        confidence REAL DEFAULT 1.0,
                        season TEXT,
                        attributes TEXT DEFAULT '{}',
                        source TEXT DEFAULT '{}',
                        images TEXT DEFAULT '[]',
                        coordinates TEXT,
                        area TEXT,
                        level TEXT,
                        parentId TEXT,
                        legacyArea TEXT,
                        updatedAt TEXT,
                        created_at TEXT DEFAULT (datetime('now'))
                    );

                    CREATE TABLE IF NOT EXISTS relationships (
                        from_id TEXT NOT NULL,
                        to_id TEXT NOT NULL,
                        type TEXT NOT NULL,
                        PRIMARY KEY (from_id, to_id, type)
                    );

                    CREATE TABLE IF NOT EXISTS itineraries (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        area TEXT,
                        duration TEXT,
                        summary TEXT DEFAULT '',
                        stops TEXT DEFAULT '[]',
                        created_at TEXT DEFAULT (datetime('now'))
                    );

                    CREATE TABLE IF NOT EXISTS feedback (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT,
                        query TEXT,
                        rating INTEGER,
                        entity_id TEXT,
                        created_at TEXT DEFAULT (datetime('now'))
                    );

                    CREATE TABLE IF NOT EXISTS query_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        query TEXT,
                        tools TEXT,
                        reply_length INTEGER,
                        score REAL,
                        session_id TEXT,
                        created_at TEXT DEFAULT (datetime('now'))
                    );

                    CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(type);
                    CREATE INDEX IF NOT EXISTS idx_entities_placeId ON entities(placeId);
                    CREATE INDEX IF NOT EXISTS idx_entities_updated ON entities(updatedAt DESC);
                    CREATE INDEX IF NOT EXISTS idx_itineraries_area ON itineraries(area);
                    CREATE INDEX IF NOT EXISTS idx_relationships_from ON relationships(from_id);
                    CREATE INDEX IF NOT EXISTS idx_relationships_to ON relationships(to_id);
                    CREATE INDEX IF NOT EXISTS idx_feedback_user ON feedback(user_id);
                    CREATE INDEX IF NOT EXISTS idx_query_log_session ON query_log(session_id);
                    CREATE INDEX IF NOT EXISTS idx_query_log_created ON query_log(created_at);
                """)

                try:
                    conn.execute("""
                        CREATE VIRTUAL TABLE IF NOT EXISTS entities_fts USING fts5(
                            id, name, summary, type,
                            content=entities,
                            content_rowid=rowid
                        )
                    """)
                except sqlite3.OperationalError:
                    pass

            self._initialized = True

    # ── Entity CRUD ──

    def upsert_entity(self, entity: dict):
        """Insert or update an entity."""
        self.initialize()
        _validate_place_level(entity)
        season_val = entity.get("season")
        attrs_val = entity.get("attributes", {})
        source_val = entity.get("source", {})
        # Normalize attribute key aliases on write
        if isinstance(attrs_val, dict):
            _ATTR_ALIASES = {
                "open_hours": "hours", "opening_hours": "hours",
                "operating_hours": "hours", "open_on": "hours",
                "foodyRating": "rating", "foodyComments": "review_count",
                "bestTime": "best_time", "best_time_to_visit": "best_time",
                "priceRange": "price_range", "bestSeason": "season_note",
                "checkin": "check_in", "checkout": "check_out",
                "highlights": "highlight", "booking": "booking_note",
                "admission_fee": "admission", "location": "address",
            }
            attrs_val = {_ATTR_ALIASES.get(k, k): v for k, v in attrs_val.items()}
        # Normalize source to list[dict] on write
        if isinstance(source_val, str):
            source_val = [{"url": source_val}] if source_val.startswith("http") else [{"name": source_val}] if source_val else []
        elif isinstance(source_val, dict):
            source_val = [source_val] if source_val else []
        elif not isinstance(source_val, list):
            source_val = []
        images_val = entity.get("images", [])
        # GĐ-audit: chấp nhận alias legacy "coords" để ETL/auto_learn không mất toạ độ
        # đã geocode (nhiều path ghi entity["coords"] thay vì "coordinates").
        coords_val = entity.get("coordinates") or entity.get("coords")
        # Guard geocode: bỏ toạ độ NGOÀI vùng VL+Bến Tre+Trà Vinh (crawler/geocoder hay
        # khớp nhầm tên → pin sai tỉnh). Thà null còn hơn sai (xem fix data 2026-06-14).
        if coords_val and not _coords_in_region(coords_val):
            coords_val = None
        updated = entity.get("updatedAt", datetime.now().strftime("%Y-%m-%d"))

        with self._conn() as conn:
            if self._use_pg:
                self._execute(conn, """
                    INSERT INTO entities
                    (id, type, name, summary, "placeId", confidence, season, attributes, source, images, "updatedAt",
                     coordinates, area, level, "parentId", "legacyArea")
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (id) DO UPDATE SET
                        type = EXCLUDED.type, name = EXCLUDED.name, summary = EXCLUDED.summary,
                        "placeId" = EXCLUDED."placeId", confidence = EXCLUDED.confidence,
                        season = EXCLUDED.season, attributes = EXCLUDED.attributes,
                        source = EXCLUDED.source, images = EXCLUDED.images,
                        "updatedAt" = EXCLUDED."updatedAt",
                        coordinates = EXCLUDED.coordinates, area = EXCLUDED.area,
                        level = EXCLUDED.level, "parentId" = EXCLUDED."parentId",
                        "legacyArea" = EXCLUDED."legacyArea"
                """, (
                    entity["id"], entity["type"], entity["name"],
                    entity.get("summary", ""), entity.get("placeId"),
                    entity.get("confidence", 1.0),
                    json.dumps(season_val, ensure_ascii=False) if season_val else None,
                    json.dumps(attrs_val, ensure_ascii=False),
                    json.dumps(source_val, ensure_ascii=False),
                    json.dumps(images_val, ensure_ascii=False),
                    updated,
                    json.dumps(coords_val) if coords_val else None,
                    entity.get("area"), entity.get("level"), entity.get("parentId"),
                    entity.get("legacyArea"),
                ))
            else:
                conn.execute("""
                    INSERT OR REPLACE INTO entities
                    (id, type, name, summary, placeId, confidence, season, attributes, source, images, updatedAt,
                     coordinates, area, level, parentId, legacyArea)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    entity["id"], entity["type"], entity["name"],
                    entity.get("summary", ""), entity.get("placeId"),
                    entity.get("confidence", 1.0),
                    json.dumps(season_val, ensure_ascii=False) if season_val else None,
                    json.dumps(attrs_val, ensure_ascii=False),
                    json.dumps(source_val, ensure_ascii=False),
                    json.dumps(images_val, ensure_ascii=False),
                    updated,
                    json.dumps(coords_val) if coords_val else None,
                    entity.get("area"), entity.get("level"), entity.get("parentId"),
                    entity.get("legacyArea"),
                ))
                try:
                    conn.execute(
                        "INSERT OR REPLACE INTO entities_fts(id, name, summary, type) VALUES (?, ?, ?, ?)",
                        (entity["id"], entity["name"], entity.get("summary", ""), entity["type"]))
                except sqlite3.OperationalError:
                    pass

    def update_description(self, entity_id: str, description: str):
        """Update only the description field (won't be overwritten by upsert_entity)."""
        self.initialize()
        ph = self._ph
        with self._conn() as conn:
            self._execute(conn, f"UPDATE entities SET description = {ph} WHERE id = {ph}", (description, entity_id))

    def get_entity(self, entity_id: str) -> dict | None:
        """Get single entity by ID."""
        self.initialize()
        ph = self._ph
        with self._conn() as conn:
            row = self._fetchone(conn, f"SELECT * FROM entities WHERE id = {ph}", (entity_id,))
            return self._parse_entity(row) if row else None

    def delete_entity(self, entity_id: str) -> bool:
        """Delete entity and its relationships."""
        self.initialize()
        ph = self._ph
        with self._conn() as conn:
            cur = self._execute(conn, f"DELETE FROM entities WHERE id = {ph}", (entity_id,))
            self._execute(conn, f"DELETE FROM relationships WHERE from_id = {ph} OR to_id = {ph}",
                          (entity_id, entity_id))
            if not self._use_pg:
                try:
                    conn.execute("DELETE FROM entities_fts WHERE id = ?", (entity_id,))
                except sqlite3.OperationalError:
                    pass
            return cur.rowcount > 0

    def search_entities(self, q: str = None, entity_type: str = None,
                        area: str = None, limit: int = 20) -> list[dict]:
        """Search entities with filters."""
        self.initialize()
        ph = self._ph
        conditions = ["e.type NOT IN ('place')"]
        params = []

        if entity_type:
            conditions.append(f"e.type = {ph}")
            params.append(entity_type)

        if area:
            place_col = 'e."placeId"' if self._use_pg else "e.placeId"
            conditions.append(f"""
                (e.area = {ph} OR {place_col} IN (
                    SELECT id FROM entities WHERE type = 'place' AND area = {ph}
                ))
            """)
            params.extend([area, area])

        if q:
            if self._use_pg:
                conditions.append(f"(e.name ILIKE {ph} OR e.summary ILIKE {ph})")
            else:
                conditions.append(f"(e.name LIKE {ph} OR e.summary LIKE {ph})")
            params.extend([f"%{q}%", f"%{q}%"])

        where = " AND ".join(conditions)
        params.append(limit)

        with self._conn() as conn:
            rows = self._fetchall(conn, f"""
                SELECT e.* FROM entities e
                WHERE {where}
                ORDER BY e.confidence DESC
                LIMIT {ph}
            """, params)
            return [self._parse_entity(r) for r in rows]

    def list_entities(self, entity_type: str = None, area: str = None,
                      limit: int = 500, offset: int = 0) -> list[dict]:
        """List entities with pagination."""
        self.initialize()
        ph = self._ph
        conditions = ["e.type != 'place'"]
        params = []
        if entity_type:
            conditions.append(f"e.type = {ph}")
            params.append(entity_type)
        if area:
            place_col = 'e."placeId"' if self._use_pg else "e.placeId"
            conditions.append(f"""
                (e.area = {ph} OR {place_col} IN (
                    SELECT id FROM entities WHERE type = 'place' AND area = {ph}
                ))
            """)
            params.extend([area, area])

        where = " AND ".join(conditions)
        params.extend([limit, offset])

        col = 'e."updatedAt"' if self._use_pg else "e.updatedAt"
        with self._conn() as conn:
            rows = self._fetchall(conn, f"""
                SELECT e.* FROM entities e WHERE {where}
                ORDER BY {col} DESC LIMIT {ph} OFFSET {ph}
            """, params)
            return [self._parse_entity(r) for r in rows]

    def count_entities_filtered(self, entity_type: str = None, area: str = None,
                                q: str = None) -> int:
        """Count non-place entities with the same public filters as list/search."""
        self.initialize()
        ph = self._ph
        conditions = ["e.type != 'place'"]
        params = []

        if entity_type:
            conditions.append(f"e.type = {ph}")
            params.append(entity_type)
        if area:
            place_col = 'e."placeId"' if self._use_pg else "e.placeId"
            conditions.append(f"""
                (e.area = {ph} OR {place_col} IN (
                    SELECT id FROM entities WHERE type = 'place' AND area = {ph}
                ))
            """)
            params.extend([area, area])
        if q:
            if self._use_pg:
                conditions.append(f"(e.name ILIKE {ph} OR e.summary ILIKE {ph})")
            else:
                conditions.append(f"(e.name LIKE {ph} OR e.summary LIKE {ph})")
            params.extend([f"%{q}%", f"%{q}%"])

        where = " AND ".join(conditions)
        with self._conn() as conn:
            row = self._fetchone(conn, f"SELECT COUNT(*) as c FROM entities e WHERE {where}", params)
            return int(row["c"] if row else 0)

    def count_entities(self) -> dict:
        """Count entities by type."""
        self.initialize()
        with self._conn() as conn:
            rows = self._fetchall(conn, """
                SELECT type, COUNT(*) as count FROM entities
                WHERE type != 'place'
                GROUP BY type
            """)
            return {r["type"]: r["count"] for r in rows}

    # ── Bulk load (GĐ3.4: nguồn cho knowledge in-memory; KHÔNG loại trừ place) ──

    def all_entities(self) -> list[dict]:
        """Toàn bộ entity (gồm cả place) — dùng để nạp knowledge in-memory."""
        self.initialize()
        with self._conn() as conn:
            rows = self._fetchall(conn, "SELECT * FROM entities")
            return [self._parse_entity(r) for r in rows]

    def all_relationships(self) -> list[dict]:
        """Toàn bộ quan hệ ở shape {from,to,type} (khớp data.json/knowledge)."""
        self.initialize()
        with self._conn() as conn:
            rows = self._fetchall(conn, "SELECT from_id, to_id, type FROM relationships")
            return [{"from": r["from_id"], "to": r["to_id"], "type": r["type"]} for r in rows]

    def all_itineraries(self) -> list[dict]:
        """Toàn bộ itinerary (stops đã parse)."""
        self.initialize()
        with self._conn() as conn:
            rows = self._fetchall(conn, "SELECT * FROM itineraries")
            return [self._parse_itinerary(r) for r in rows]

    def entities_by_place(self, place_id: str) -> list[dict]:
        """Tất cả entity nội dung thuộc 1 xã/phường (placeId), trừ chính các đơn vị place.
        Phục vụ trang hub per-xã/phường (du lịch/lưu trú/sản phẩm/...)."""
        self.initialize()
        ph = self._ph
        pcol = '"placeId"' if self._use_pg else "placeId"
        with self._conn() as conn:
            rows = self._fetchall(
                conn,
                f"SELECT * FROM entities WHERE {pcol} = {ph} AND type != {ph} ORDER BY type, name",
                (place_id, "place"))
            return [self._parse_entity(r) for r in rows]

    def facilities_by_place(self, place_id: str | None = None) -> list[dict]:
        """GĐ13.3: cơ quan hành chính (type=facility) theo xã/phường (placeId). Danh bạ hành chính."""
        self.initialize()
        ph = self._ph
        pcol = '"placeId"' if self._use_pg else "placeId"
        with self._conn() as conn:
            if place_id:
                rows = self._fetchall(
                    conn, f"SELECT * FROM entities WHERE type = {ph} AND {pcol} = {ph}",
                    ("facility", place_id))
            else:
                rows = self._fetchall(conn, f"SELECT * FROM entities WHERE type = {ph}", ("facility",))
            return [self._parse_entity(r) for r in rows]

    # ── Relationships ──

    def add_relationship(self, from_id: str, to_id: str, rel_type: str):
        self.initialize()
        ph = self._ph
        with self._conn() as conn:
            if self._use_pg:
                self._execute(conn, f"""
                    INSERT INTO relationships (from_id, to_id, type) VALUES ({ph}, {ph}, {ph})
                    ON CONFLICT DO NOTHING
                """, (from_id, to_id, rel_type))
            else:
                conn.execute(
                    "INSERT OR IGNORE INTO relationships (from_id, to_id, type) VALUES (?, ?, ?)",
                    (from_id, to_id, rel_type))

    def _parse_coordinates(self, value) -> list[float] | None:
        current = value
        for _ in range(4):
            if not isinstance(current, str):
                break
            text = current.strip()
            if not text:
                return None
            try:
                current = json.loads(text)
            except Exception:
                return None
        if isinstance(current, dict):
            lat = current.get("lat", current.get("latitude"))
            lng = current.get("lng", current.get("lon", current.get("longitude")))
            current = [lat, lng]
        if not isinstance(current, (list, tuple)) or len(current) != 2:
            return None
        try:
            lat = float(current[0])
            lng = float(current[1])
        except (TypeError, ValueError):
            return None
        if -90 <= lat <= 90 and -180 <= lng <= 180:
            return [lat, lng]
        if -180 <= lat <= 180 and -90 <= lng <= 90:
            return [lng, lat]
        return None

    def _haversine_km(self, left: list[float] | None, right: list[float] | None) -> float | None:
        if not left or not right:
            return None
        lat1, lng1 = math.radians(left[0]), math.radians(left[1])
        lat2, lng2 = math.radians(right[0]), math.radians(right[1])
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        val = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
        return 6371.0 * 2 * math.asin(math.sqrt(val))

    def _relationship_sort_key(self, rel: dict, entity_id: str, entity_area: str = ""):
        rel_type = rel.get("rel_type") or rel.get("type") or ""
        source_id = rel.get("source_id") or rel.get("from_id")
        other_name = rel.get("target_name") if source_id == entity_id else rel.get("source_name")
        other_area = rel.get("other_area") or ""
        distance = rel.get("distance_km") if isinstance(rel.get("distance_km"), (int, float)) else 999999
        same_area = 0 if (entity_area and other_area and entity_area == other_area) else 1
        return (
            same_area,
            1 if rel_type == "near" else 0,
            RELATIONSHIP_TYPE_PRIORITY.get(rel_type, 50),
            distance,
            str(other_name or ""),
        )

    def get_relationships(
        self,
        entity_id: str,
        *,
        limit: int | None = None,
        offset: int = 0,
        rel_type: str | None = None,
        include_near: bool = True,
    ) -> list[dict]:
        self.initialize()
        ph = self._ph
        with self._conn() as conn:
            rows = self._fetchall(conn, f"""
                SELECT
                    r.from_id,
                    r.to_id,
                    r.type,
                    src.name AS source_name,
                    src.type AS source_type,
                    src.area AS source_area,
                    src.coordinates AS source_coordinates,
                    dst.name AS target_name,
                    dst.type AS target_type,
                    dst.area AS target_area,
                    dst.coordinates AS target_coordinates
                FROM relationships r
                JOIN entities src ON src.id = r.from_id
                JOIN entities dst ON dst.id = r.to_id
                WHERE r.from_id = {ph} OR r.to_id = {ph}
            """, (entity_id, entity_id))

        entity_area = ""
        relationships = []
        for row in rows:
            rel = self._row_to_dict(row)
            source_id = rel.get("from_id")
            target_id = rel.get("to_id")
            kind = rel.get("type")
            if rel_type and kind != rel_type:
                continue
            if kind == "near" and not include_near:
                continue

            source_coords = self._parse_coordinates(rel.pop("source_coordinates", None))
            target_coords = self._parse_coordinates(rel.pop("target_coordinates", None))
            distance = self._haversine_km(source_coords, target_coords)
            is_source = source_id == entity_id
            other_id = target_id if is_source else source_id
            other_name = rel.get("target_name") if is_source else rel.get("source_name")
            other_type = rel.get("target_type") if is_source else rel.get("source_type")
            other_area = rel.get("target_area") if is_source else rel.get("source_area")
            if not entity_area:
                entity_area = rel.get("source_area") if is_source else rel.get("target_area")

            item = {
                "source_id": source_id,
                "target_id": target_id,
                "rel_type": kind,
                "other_id": other_id,
                "other_name": other_name,
                "other_type": other_type,
                "other_area": other_area or "",
                "from_id": source_id,
                "to_id": target_id,
                "type": kind,
                "source_name": rel.get("source_name"),
                "target_name": rel.get("target_name"),
                "source_type": rel.get("source_type"),
                "target_type": rel.get("target_type"),
            }
            if distance is not None:
                item["distance_km"] = round(distance, 1)
            relationships.append(item)

        relationships.sort(key=lambda rel: self._relationship_sort_key(rel, entity_id, entity_area))
        offset = max(int(offset or 0), 0)
        if offset:
            relationships = relationships[offset:]
        if limit is not None:
            relationships = relationships[:max(int(limit), 0)]
        return relationships

    def count_relationships(self, entity_id: str, *, rel_type: str | None = None, include_near: bool = True) -> int:
        return len(self.get_relationships(entity_id, rel_type=rel_type, include_near=include_near))

    # ── Itineraries ──

    def upsert_itinerary(self, itinerary: dict):
        self.initialize()
        ph = self._ph
        stops = json.dumps(itinerary.get("stops", []), ensure_ascii=False)
        with self._conn() as conn:
            if self._use_pg:
                self._execute(conn, f"""
                    INSERT INTO itineraries (id, title, area, duration, summary, stops)
                    VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})
                    ON CONFLICT (id) DO UPDATE SET
                        title = EXCLUDED.title, area = EXCLUDED.area,
                        duration = EXCLUDED.duration, summary = EXCLUDED.summary,
                        stops = EXCLUDED.stops
                """, (
                    itinerary["id"], itinerary["title"], itinerary.get("area"),
                    itinerary.get("duration"), itinerary.get("summary", ""), stops))
            else:
                conn.execute("""
                    INSERT OR REPLACE INTO itineraries (id, title, area, duration, summary, stops)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    itinerary["id"], itinerary["title"], itinerary.get("area"),
                    itinerary.get("duration"), itinerary.get("summary", ""), stops))

    def get_itinerary(self, itin_id: str) -> dict | None:
        self.initialize()
        ph = self._ph
        with self._conn() as conn:
            row = self._fetchone(conn, f"SELECT * FROM itineraries WHERE id = {ph}", (itin_id,))
            return self._parse_itinerary(row) if row else None

    def list_itineraries(self, area: str = None) -> list[dict]:
        self.initialize()
        ph = self._ph
        with self._conn() as conn:
            if area:
                rows = self._fetchall(conn, f"SELECT * FROM itineraries WHERE area = {ph}", (area,))
            else:
                rows = self._fetchall(conn, "SELECT * FROM itineraries")
            return [self._parse_itinerary(r) for r in rows]

    # ── Feedback ──

    def save_feedback(self, user_id: str, query: str, rating: int, entity_id: str = None):
        self.initialize()
        ph = self._ph
        with self._conn() as conn:
            self._execute(conn, f"""
                INSERT INTO feedback (user_id, query, rating, entity_id)
                VALUES ({ph}, {ph}, {ph}, {ph})
            """, (user_id, query, rating, entity_id))

    def get_feedback_stats(self) -> dict:
        self.initialize()
        with self._conn() as conn:
            total = self._fetchone(conn, "SELECT COUNT(*) as c FROM feedback")["c"]
            positive = self._fetchone(conn, "SELECT COUNT(*) as c FROM feedback WHERE rating > 0")["c"]
            return {
                "total": total,
                "positive": positive,
                "negative": total - positive,
                "positive_rate": round(positive / max(total, 1) * 100, 1),
            }

    # ── Query Log ──

    def log_query(self, query: str, tools: list, reply_length: int, score: float = None, session_id: str = ""):
        self.initialize()
        ph = self._ph
        tools_val = json.dumps(tools) if not self._use_pg else json.dumps(tools)
        with self._conn() as conn:
            self._execute(conn, f"""
                INSERT INTO query_log (query, tools, reply_length, score, session_id)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph})
            """, (query, tools_val, reply_length, score, session_id))

    def get_query_stats(self, days: int = 7) -> dict:
        self.initialize()
        ph = self._ph
        with self._conn() as conn:
            if self._use_pg:
                total = self._fetchone(conn, f"""
                    SELECT COUNT(*) as c FROM query_log
                    WHERE created_at >= NOW() - INTERVAL '{days} days'
                """)["c"]
                avg_score = self._fetchone(conn, f"""
                    SELECT AVG(score) as a FROM query_log
                    WHERE score IS NOT NULL AND created_at >= NOW() - INTERVAL '{days} days'
                """)["a"]
            else:
                cutoff = datetime.now().strftime("%Y-%m-%d")
                total = conn.execute(
                    "SELECT COUNT(*) as c FROM query_log WHERE created_at >= date(?, ?)",
                    (cutoff, f"-{days} days")).fetchone()["c"]
                avg_score = conn.execute(
                    "SELECT AVG(score) as a FROM query_log WHERE score IS NOT NULL AND created_at >= date(?, ?)",
                    (cutoff, f"-{days} days")).fetchone()["a"]
            return {
                "total_queries": total,
                "avg_score": round(avg_score or 0, 2),
                "period_days": days,
            }

    # ── Migration ──

    def migrate_from_json(self, json_path: str) -> dict:
        """Import data from data.json. Works with both PG and SQLite."""
        self.initialize()

        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)

        entities_count = 0
        rels_count = 0
        its_count = 0

        for e in data.get("entities", []):
            self.upsert_entity(e)
            entities_count += 1

        for r in data.get("relationships", []):
            source_id = r.get("from") or r.get("from_id") or r.get("source_id")
            target_id = r.get("to") or r.get("to_id") or r.get("target_id")
            rel_type = r.get("type") or r.get("rel_type")
            if source_id and target_id and rel_type:
                self.add_relationship(source_id, target_id, rel_type)
                rels_count += 1

        for it in data.get("itineraries", []):
            self.upsert_itinerary(it)
            its_count += 1

        return {
            "status": "migrated",
            "entities": entities_count,
            "relationships": rels_count,
            "itineraries": its_count,
            "backend": "postgresql" if self._use_pg else "sqlite",
        }

    def replace_from_json(self, json_path: str) -> dict:
        """Replace knowledge tables from data.json, backing up SQLite first."""
        self.initialize()

        # GĐ0.5: khoá replace trong giai đoạn ổn định. Migrate có chủ đích (GĐ3.3) dùng
        # ALLOW_DESTRUCTIVE_DB_REPLACE=1 để vượt; mở khoá hẳn ở GĐ3.8.
        if os.environ.get("DESTRUCTIVE_OPS_LOCKED", "1") == "1" and os.environ.get("ALLOW_DESTRUCTIVE_DB_REPLACE") != "1":
            raise RuntimeError(
                "replace_from_json bị khoá (DESTRUCTIVE_OPS_LOCKED=1). "
                "Đặt ALLOW_DESTRUCTIVE_DB_REPLACE=1 cho migrate có chủ đích (GĐ3.3)."
            )

        if self._use_pg and os.environ.get("ALLOW_DESTRUCTIVE_DB_REPLACE") != "1":
            raise RuntimeError("Refusing to replace PostgreSQL data without ALLOW_DESTRUCTIVE_DB_REPLACE=1")

        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)

        backup_path = None
        if not self._use_pg and os.path.exists(self.db_path):
            backup_path = self.backup()

        # F1 (atomic): DELETE + INSERT trong CÙNG 1 transaction cho CẢ PG lẫn SQLite.
        # Crash giữa chừng → rollback → data CŨ còn nguyên (KHÔNG để DB rỗng). Trước đây
        # PG xoá ở transaction này rồi nạp ở migrate_from_json (transaction KHÁC) → không atomic.
        with self._conn() as conn:
            self._execute(conn, "DELETE FROM relationships")
            self._execute(conn, "DELETE FROM itineraries")
            if not self._use_pg:
                try:
                    conn.execute("DELETE FROM entities_fts")
                except sqlite3.OperationalError:
                    pass
            self._execute(conn, "DELETE FROM entities")

            result = self._bulk_load(conn, data)
            if result.get("relationships_dropped", 0) > 0:
                print(f"[replace_from_json] CANH BAO: {result['relationships_dropped']} quan he trung "
                      f"(from,to,type) bi bo khi luu (input {result['relationships']} -> stored "
                      f"{result['relationships_stored']})")

        result["mode"] = "replace"
        if backup_path:
            result["backup"] = backup_path
        return result

    def _bulk_load(self, conn, data: dict) -> dict:
        """Nạp entities+relationships+itineraries vào DB trên CONNECTION đã cho (không tự
        commit) — để replace_from_json gói DELETE+INSERT trong 1 transaction (F1 atomic).
        SQLite + PostgreSQL dùng chung cấu trúc; SQL theo từng backend (copy từ upsert_*)."""
        now = datetime.now().strftime("%Y-%m-%d")
        entity_rows, fts_rows = [], []
        for entity in data.get("entities", []):
            season_val = entity.get("season")
            coords_val = entity.get("coordinates")
            entity_rows.append((
                entity["id"], entity["type"], entity["name"],
                entity.get("summary", ""), entity.get("placeId"),
                entity.get("confidence", 1.0),
                json.dumps(season_val, ensure_ascii=False) if season_val else None,
                json.dumps(entity.get("attributes", {}), ensure_ascii=False),
                json.dumps(entity.get("source", {}), ensure_ascii=False),
                json.dumps(entity.get("images", []), ensure_ascii=False),
                entity.get("updatedAt", now),
                json.dumps(coords_val) if coords_val else None,
                entity.get("area"), entity.get("level"), entity.get("parentId"),
                entity.get("legacyArea"),
            ))
            fts_rows.append((entity["id"], entity["name"], entity.get("summary", ""), entity["type"]))

        rel_rows = []
        for rel in data.get("relationships", []):
            s = rel.get("from") or rel.get("from_id") or rel.get("source_id")
            t = rel.get("to") or rel.get("to_id") or rel.get("target_id")
            rt = rel.get("type") or rel.get("rel_type")
            if s and t and rt:
                rel_rows.append((s, t, rt))

        itin_rows = []
        for it in data.get("itineraries", []):
            itin_rows.append((
                it["id"], it["title"], it.get("area"), it.get("duration"),
                it.get("summary", ""), json.dumps(it.get("stops", []), ensure_ascii=False),
            ))

        if self._use_pg:
            cur = conn.cursor()
            cur.executemany(
                'INSERT INTO entities (id, type, name, summary, "placeId", confidence, season, '
                'attributes, source, images, "updatedAt", coordinates, area, level, "parentId", "legacyArea") '
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (id) DO NOTHING",
                entity_rows)
            cur.executemany(
                "INSERT INTO relationships (from_id, to_id, type) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING",
                rel_rows)
            cur.executemany(
                "INSERT INTO itineraries (id, title, area, duration, summary, stops) "
                "VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (id) DO NOTHING",
                itin_rows)
            stored = self._fetchone(conn, "SELECT COUNT(*) as c FROM relationships")["c"]
        else:
            conn.executemany(
                "INSERT OR REPLACE INTO entities (id, type, name, summary, placeId, confidence, season, "
                "attributes, source, images, updatedAt, coordinates, area, level, parentId, legacyArea) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", entity_rows)
            try:
                conn.executemany(
                    "INSERT OR REPLACE INTO entities_fts(id, name, summary, type) VALUES (?, ?, ?, ?)",
                    fts_rows)
            except sqlite3.OperationalError:
                pass
            conn.executemany(
                "INSERT OR IGNORE INTO relationships (from_id, to_id, type) VALUES (?, ?, ?)", rel_rows)
            conn.executemany(
                "INSERT OR REPLACE INTO itineraries (id, title, area, duration, summary, stops) "
                "VALUES (?, ?, ?, ?, ?, ?)", itin_rows)
            stored = conn.execute("SELECT COUNT(*) as c FROM relationships").fetchone()["c"]

        return {
            "status": "migrated",
            "entities": len(entity_rows),
            "relationships": len(rel_rows),
            "relationships_stored": stored,
            "relationships_dropped": len(rel_rows) - stored,
            "itineraries": len(itin_rows),
            "backend": "postgresql" if self._use_pg else "sqlite",
        }

    def backup(self, backup_path: str = None) -> str:
        """Create a backup (SQLite only; PG uses pg_dump)."""
        if self._use_pg:
            raise NotImplementedError("Use pg_dump for PostgreSQL backups")
        self.initialize()
        if not backup_path:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = str(DB_DIR / f"vinhlong360_backup_{ts}.db")
        with self._conn() as conn:
            backup_conn = sqlite3.connect(backup_path)
            conn.backup(backup_conn)
            backup_conn.close()
        return backup_path

    def stats(self) -> dict:
        """Database statistics."""
        self.initialize()
        with self._conn() as conn:
            entities = self._fetchone(conn, "SELECT COUNT(*) as c FROM entities WHERE type != 'place'")["c"]
            places = self._fetchone(conn, "SELECT COUNT(*) as c FROM entities WHERE type = 'place'")["c"]
            rels = self._fetchone(conn, "SELECT COUNT(*) as c FROM relationships")["c"]
            its = self._fetchone(conn, "SELECT COUNT(*) as c FROM itineraries")["c"]
            feedback = self._fetchone(conn, "SELECT COUNT(*) as c FROM feedback")["c"]
            queries = self._fetchone(conn, "SELECT COUNT(*) as c FROM query_log")["c"]

            result = {
                "entities": entities,
                "places": places,
                "relationships": rels,
                "itineraries": its,
                "feedback_entries": feedback,
                "query_log_entries": queries,
                "backend": "postgresql" if self._use_pg else "sqlite",
            }

            if not self._use_pg:
                db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
                result["db_size_kb"] = round(db_size / 1024, 1)
                result["db_path"] = self.db_path

            return result

    # ── User methods (PG only, used by auth) ──

    def get_user_by_phone(self, phone: str) -> dict | None:
        self.initialize()
        ph = self._ph
        with self._conn() as conn:
            row = self._fetchone(conn, f"SELECT * FROM users WHERE phone = {ph}", (phone,))
            return self._row_to_dict(row)

    def get_user_by_id(self, user_id: str) -> dict | None:
        self.initialize()
        ph = self._ph
        with self._conn() as conn:
            row = self._fetchone(conn, f"SELECT * FROM users WHERE id::text = {ph}", (str(user_id),))
            return self._row_to_dict(row)

    def create_user(self, phone: str, display_name: str = None, consent_version: str = "1.0") -> dict:
        self.initialize()
        ph = self._ph
        with self._conn() as conn:
            row = self._fetchone(conn, f"""
                INSERT INTO users (phone, display_name, consent_at, consent_version)
                VALUES ({ph}, {ph}, NOW(), {ph})
                RETURNING *
            """, (phone, display_name or f"User_{phone[-4:]}", consent_version))
            return self._row_to_dict(row)

    def update_user(self, user_id: str, **fields) -> dict | None:
        self.initialize()
        ph = self._ph
        sets = []
        params = []
        for k, v in fields.items():
            if k in ("display_name", "avatar_url", "bio", "role", "is_active", "password_hash"):
                sets.append(f"{k} = {ph}")
                params.append(v)
        if not sets:
            return self.get_user_by_id(user_id)
        params.append(str(user_id))
        with self._conn() as conn:
            row = self._fetchone(conn,
                f"UPDATE users SET {', '.join(sets)} WHERE id::text = {ph} RETURNING *", params)
            return self._row_to_dict(row)

    # ── Helpers ──

    def _parse_entity(self, row) -> dict:
        if row is None:
            return None
        d = self._row_to_dict(row)
        json_fields = ("season", "attributes", "source", "images")
        if not self._use_pg:
            json_fields = (*json_fields, "coordinates")
        for field in json_fields:
            if d.get(field) and isinstance(d[field], str):
                try:
                    d[field] = json.loads(d[field])
                except Exception:
                    pass
        _normalize_entity_timestamps(d)
        return d

    def _parse_itinerary(self, row) -> dict:
        d = self._row_to_dict(row)
        if not self._use_pg:
            if d.get("stops") and isinstance(d["stops"], str):
                try:
                    d["stops"] = json.loads(d["stops"])
                except Exception:
                    d["stops"] = []
        return d


# ══════════════════════════════════════════════════
#  P4 TRUST: timestamp normalization (no fabrication)
# ══════════════════════════════════════════════════

def _coerce_iso_date(value) -> str | None:
    """Trả ISO-8601 UTC (…Z) từ một giá trị ngày đã có sẵn trong DB/data.
    KHÔNG bịa ngày: chỉ chuẩn hoá định dạng. Trả None nếu không phân giải được.
    Track-H: không bao giờ thay bằng datetime.now()."""
    if not value or not isinstance(value, str):
        return None
    s = value.strip()
    if not s:
        return None
    # Đã là ISO có Z → giữ nguyên
    if "T" in s and s.endswith("Z"):
        return s
    # Có 'T' nhưng thiếu Z (vd "2026-06-11T00:00:00") → thêm Z
    if "T" in s:
        return s.rstrip("Z") + "Z"
    # SQLite "datetime('now')" cho dạng "2026-06-13 04:00:38"
    candidate = s.replace(" ", "T", 1) if " " in s else s
    try:
        # Bỏ phần phân số giây nếu có (fromisoformat đời cũ kén)
        core = candidate.split(".")[0]
        parsed = datetime.fromisoformat(core)
        return parsed.strftime("%Y-%m-%dT%H:%M:%SZ")
    except (ValueError, AttributeError):
        # Date-only "2026-06-10" không qua được fromisoformat ở mọi runtime?
        # fromisoformat xử lý được date-only từ 3.11; fallback an toàn:
        return candidate + ("T00:00:00Z" if "T" not in candidate else "Z")


def _normalize_entity_timestamps(d: dict) -> dict:
    """Đảm bảo entity luôn phơi ra mốc thời gian ổn định, KHÔNG bịa.

    - updatedAt: chuẩn hoá ISO-8601 UTC. Nếu thiếu → suy từ created_at (DB luôn có).
    - createdAt: phơi created_at của DB (audit) nếu chưa có.
    - verifiedAt: mặc định = updatedAt (lần cập nhật gần nhất ngụ ý lần kiểm gần nhất);
      nếu sau này có attributes.verifiedAt riêng thì giữ cái đó.
    Tất cả nguồn đều là field DB/data sẵn có — không dùng ngày hiện tại.
    """
    if not isinstance(d, dict):
        return d

    updated = d.get("updatedAt")
    iso_updated = _coerce_iso_date(updated) if updated else None
    if not iso_updated:
        # Fallback an toàn: dùng created_at của hàng DB (không bao giờ là "now")
        iso_updated = _coerce_iso_date(d.get("created_at"))
    if iso_updated:
        d["updatedAt"] = iso_updated

    # createdAt (audit) — chỉ phơi nếu DB có created_at
    if d.get("created_at") and not d.get("createdAt"):
        iso_created = _coerce_iso_date(d.get("created_at"))
        if iso_created:
            d["createdAt"] = iso_created

    # verifiedAt — ưu tiên giá trị tường minh trong attributes (admin có thể set sau)
    attrs = d.get("attributes")
    explicit_verified = attrs.get("verifiedAt") if isinstance(attrs, dict) else None
    if explicit_verified:
        coerced = _coerce_iso_date(explicit_verified)
        if coerced:
            d["verifiedAt"] = coerced
    elif not d.get("verifiedAt") and d.get("updatedAt"):
        d["verifiedAt"] = d["updatedAt"]

    return d


# Singleton
db = Database()


# ══════════════════════════════════════════════════
#  CLI: Migration tool
# ══════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    ROOT = Path(__file__).resolve().parent.parent
    JSON_PATH = ROOT / "web" / "data.json"

    if "--migrate" in sys.argv:
        print(f"Migrating {JSON_PATH} → {'PostgreSQL' if USE_PG else 'SQLite'}")
        result = db.migrate_from_json(str(JSON_PATH))
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif "--replace" in sys.argv:
        print(f"Replacing {'PostgreSQL' if USE_PG else 'SQLite'} knowledge data from {JSON_PATH}")
        result = db.replace_from_json(str(JSON_PATH))
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif "--backup" in sys.argv:
        path = db.backup()
        print(f"Backup created: {path}")

    elif "--stats" in sys.argv:
        print(json.dumps(db.stats(), indent=2, ensure_ascii=False))

    else:
        print("Usage:")
        print("  python database.py --migrate   # Import data.json")
        print("  python database.py --replace   # Replace knowledge tables from data.json")
        print("  python database.py --backup    # Create database backup (SQLite only)")
        print("  python database.py --stats     # Show database statistics")
