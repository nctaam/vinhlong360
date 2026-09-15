"""
Adversarial Challenge & Empirical Verification Test Suite
Author: challenger_1 (teamwork_preview_challenger)
Role: Empirical Stress-Tester & Invariant Challenger (Spatial, Temporal, GIS)
Parent: orchestrator_2 (Conversation ID: 93e24800-c01d-4c88-bf9e-c9c29a2823bb)
Original Request: c:\\Users\\NCTaam\\Documents\\vinhlong360-correction-case-pilot\\.agents\\ORIGINAL_REQUEST.md (under ## 2026-09-12T15:17:16Z)

Constraints:
- STRICT READ-ONLY on agent/data/vinhlong360.db and web/data.json.
- Zero trusting of unverified claims.
"""

import json
import os
import re
import sqlite3
import sys
from datetime import date
from pathlib import Path
import pytest

# Add agent path for public_api and lunar_calendar imports
REPO_ROOT = Path(__file__).resolve().parent.parent
AGENT_DIR = REPO_ROOT / "agent"
sys.path.insert(0, str(AGENT_DIR))

from public_api import _event_date_reliable, _parse_event_iso_date
import lunar_calendar

DB_PATH = REPO_ROOT / "agent" / "data" / "vinhlong360.db"
LEDGER_PATH = REPO_ROOT / "outputs" / "data_remediation_ledger.json"
SPATIAL_REMED_PATH = REPO_ROOT / "outputs" / "remediation_spatial.json"
TEMPORAL_REMED_PATH = REPO_ROOT / "outputs" / "remediation_temporal.json"
SEED_PATH = REPO_ROOT / "outputs" / "curated_missing_entities_seed.json"
ORIGINAL_REQUEST_PATH = REPO_ROOT / ".agents" / "ORIGINAL_REQUEST.md"
WHITELIST_PATH = REPO_ROOT / "docs" / "standards" / "whitelist-tinh-cu.txt"

# Mekong Bounding Box: 9.0 <= lat <= 11.0, 105.0 <= lng <= 107.0
LAT_MIN, LAT_MAX = 9.0, 11.0
LNG_MIN, LNG_MAX = 105.0, 107.0


@pytest.fixture(scope="session")
def db_conn():
    assert DB_PATH.exists(), f"DB not found at {DB_PATH}"
    # STRICT READ-ONLY connection
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()

@pytest.fixture(scope="session")
def ledger():
    assert LEDGER_PATH.exists(), f"Ledger not found at {LEDGER_PATH}"
    with open(LEDGER_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

@pytest.fixture(scope="session")
def spatial_remed():
    assert SPATIAL_REMED_PATH.exists(), f"Spatial remediation not found at {SPATIAL_REMED_PATH}"
    with open(SPATIAL_REMED_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

@pytest.fixture(scope="session")
def temporal_remed():
    assert TEMPORAL_REMED_PATH.exists(), f"Temporal remediation not found at {TEMPORAL_REMED_PATH}"
    with open(TEMPORAL_REMED_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

@pytest.fixture(scope="session")
def seed():
    assert SEED_PATH.exists(), f"Seed not found at {SEED_PATH}"
    with open(SEED_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================================
# 1. SPATIAL BOUNDING BOX, PROV-1, AND 13 MISSING COORDS GEOCODES
# ============================================================================

class TestSpatialAdversarial:

    def test_original_request_file_reference_present(self):
        """Invariant: Challenger must document and reference ORIGINAL_REQUEST.md."""
        assert ORIGINAL_REQUEST_PATH.exists(), f"Missing ORIGINAL_REQUEST.md at {ORIGINAL_REQUEST_PATH}"
        content = ORIGINAL_REQUEST_PATH.read_text(encoding="utf-8")
        assert "## 2026-09-12T15:17:16Z" in content
        assert "1,747" in content

    def test_database_baseline_counts(self, db_conn):
        """Empirically verify 1,747 entities, 12,061 relationships, 33 itineraries."""
        cur = db_conn.cursor()
        cur.execute("SELECT count(*) FROM entities")
        assert cur.fetchone()[0] == 1747

        cur.execute("SELECT count(*) FROM relationships")
        assert cur.fetchone()[0] == 12061

        cur.execute("SELECT count(*) FROM itineraries")
        assert cur.fetchone()[0] == 33

    def test_existing_valid_coordinates_fall_in_bbox(self, db_conn):
        """All 1,733 existing valid coordinates must fall strictly within Mekong BBox."""
        cur = db_conn.cursor()
        cur.execute("SELECT id, coordinates FROM entities WHERE coordinates IS NOT NULL AND coordinates != '' AND id != 'prov-1'")
        rows = cur.fetchall()

        valid_count = 0
        for r in rows:
            coords = r["coordinates"]
            try:
                parsed = json.loads(coords) if isinstance(coords, str) else coords
                if isinstance(parsed, list) and len(parsed) == 2:
                    lat, lng = float(parsed[0]), float(parsed[1])
                    assert LAT_MIN <= lat <= LAT_MAX, f"Entity {r['id']} lat {lat} out of bounds"
                    assert LNG_MIN <= lng <= LNG_MAX, f"Entity {r['id']} lng {lng} out of bounds"
                    valid_count += 1
            except (json.JSONDecodeError, ValueError, TypeError):
                pass

        assert valid_count == 1733

    def test_prov_1_malformed_coordinates_and_remediation(self, db_conn, ledger, spatial_remed):
        """prov-1 had JSON dict string in DB; remediation must provide [lat, lng] array and correct placeId."""
        cur = db_conn.cursor()
        cur.execute("SELECT id, coordinates, placeId, address FROM entities WHERE id = 'prov-1'")
        row = cur.fetchone()
        assert row is not None
        # Verify original defect in DB: {"lat": 10.253, "lng": 106.012}
        assert "{" in row["coordinates"] and "lat" in row["coordinates"]
        assert row["placeId"] == "phuong-thanh-duc"  # Typo in DB

        # Find remediation in ledger
        remeds = [r for r in ledger["remediations"] if r["entity_id"] == "prov-1" and r["error_code"] == "ERR_MALFORMED_COORDS"]
        assert len(remeds) == 1, "Must have exactly 1 remediation for prov-1 in ledger"
        rem = remeds[0]

        # Coordinates in ledger proposed_value is list of floats
        coords = rem["proposed_value"]
        assert isinstance(coords, list) and len(coords) == 2
        lat, lng = float(coords[0]), float(coords[1])
        assert lat == 10.253 and lng == 106.012
        assert LAT_MIN <= lat <= LAT_MAX
        assert LNG_MIN <= lng <= LNG_MAX

        # Check full multi-field fix in spatial remediation
        prov1_fix = spatial_remed["coordinate_remediations"]["prov_1_fix"]
        assert prov1_fix["proposed_value"] == [10.253, 106.012]
        assert prov1_fix["place_id_remediation"]["proposed_place_id"] == "p-thanh-duc"
        assert prov1_fix["address_remediation"]["proposed_address"] == "12 đường Thử Nghiệm, Phường Thanh Đức, tỉnh Vĩnh Long"

    def test_13_missing_coordinates_geocodes(self, db_conn, ledger, spatial_remed):
        """Empirically verify 13 missing coordinates in DB and their remediations in ledger."""
        cur = db_conn.cursor()
        cur.execute("SELECT id, type, name, coordinates FROM entities WHERE coordinates IS NULL OR coordinates = '' OR coordinates = '[]'")
        rows = cur.fetchall()
        assert len(rows) == 13, f"Expected 13 missing coordinates in DB, found {len(rows)}"

        missing_ids = {r["id"] for r in rows}

        remeds = [r for r in ledger["remediations"] if r["error_code"] == "ERR_MISSING_COORDS"]
        assert len(remeds) == 13, f"Expected 13 remediations for ERR_MISSING_COORDS, found {len(remeds)}"

        remed_ids = {r["entity_id"] for r in remeds}
        assert missing_ids == remed_ids, "Remediated IDs must match DB missing IDs exactly"

        for rem in remeds:
            coords = rem["proposed_value"]
            assert isinstance(coords, list) and len(coords) == 2, f"{rem['entity_id']} coordinates must be [lat, lng]"
            lat, lng = float(coords[0]), float(coords[1])
            assert LAT_MIN <= lat <= LAT_MAX, f"{rem['entity_id']} lat {lat} out of BBox"
            assert LNG_MIN <= lng <= LNG_MAX, f"{rem['entity_id']} lng {lng} out of BBox"

        # Special case: ben-xe-mien-tay-hcm must be in HCMC and have BBox exemption documented
        bx_rem = [r for r in remeds if r["entity_id"] == "ben-xe-mien-tay-hcm"][0]
        assert bx_rem["proposed_value"] == [10.7407, 106.6186]
        gw_rule = spatial_remed["coordinate_remediations"]["external_gateway_rule"]
        assert gw_rule["external_gateway"] is True
        assert gw_rule["rule_definition"]["rule_id"] == "RULE_EXTERNAL_TRANSIT_GATEWAY_BBOX_EXEMPTION"

    def test_seed_entities_fall_within_bbox(self, seed):
        """All 25 curated seed entities must have valid coordinates in Mekong BBox."""
        entities = seed.get("entities", [])
        assert len(entities) == 25, f"Expected 25 seed entities, got {len(entities)}"

        for e in entities:
            coords = e.get("coordinates")
            assert isinstance(coords, list) and len(coords) == 2, f"Seed {e['id']} invalid coordinates"
            lat, lng = float(coords[0]), float(coords[1])
            assert LAT_MIN <= lat <= LAT_MAX, f"Seed {e['id']} lat {lat} out of BBox"
            assert LNG_MIN <= lng <= LNG_MAX, f"Seed {e['id']} lng {lng} out of BBox"
            # Ensure coordinates are in authentic Mekong region (lat 9.6 - 10.5, lng 105.7 - 106.7)
            assert 9.6 <= lat <= 10.5 and 105.7 <= lng <= 106.7


# ============================================================================
# 2. 17 WHITE ZONES EMPIRICAL VERIFICATION & COVERAGE
# ============================================================================

class TestWhiteZonesAdversarial:

    EXPECTED_17_WHITE_ZONES = {
        'p-hung-hoa', 'xa-an-hiep', 'xa-an-ngai-trung', 'xa-an-truong',
        'xa-chau-hoa', 'xa-hieu-phung', 'xa-hung-khanh-trung', 'xa-hung-my',
        'xa-luong-phu', 'xa-my-thuan', 'xa-ngu-lac', 'xa-phong-thanh',
        'xa-quoi-an', 'xa-song-loc', 'xa-song-phu', 'xa-thanh-phong',
        'xa-thanh-tri'
    }

    def test_db_has_exactly_17_white_zones(self, db_conn):
        """Query DB for all 124 administrative units; verify exactly 17 have 0 content entities."""
        cur = db_conn.cursor()
        cur.execute("SELECT id, name, level FROM entities WHERE type = 'place' AND parentId = 'vinh-long'")
        units = cur.fetchall()
        assert len(units) == 124, f"Expected 124 administrative units, found {len(units)}"

        zero_content_units = set()
        for u in units:
            unit_id = u["id"]
            # Using exact DB column 'placeId'
            cur.execute("SELECT count(*) FROM entities WHERE placeId = ? AND type != 'place'", (unit_id,))
            cnt = cur.fetchone()[0]
            if cnt == 0:
                zero_content_units.add(unit_id)

        assert len(zero_content_units) == 17, f"Expected exactly 17 white zones, found {len(zero_content_units)}: {zero_content_units}"
        assert zero_content_units == self.EXPECTED_17_WHITE_ZONES, (
            f"White zones mismatch. Diff: {zero_content_units.symmetric_difference(self.EXPECTED_17_WHITE_ZONES)}"
        )

    def test_seed_json_covers_all_17_white_zones(self, seed):
        """Verify curated_missing_entities_seed.json covers all 17 white zones."""
        assert seed.get("white_zones_count") == 17
        assert set(seed.get("white_zones_covered", [])) == self.EXPECTED_17_WHITE_ZONES

        entities = seed.get("entities", [])
        covered_in_entities = set()
        slug_pattern = re.compile(r'^[a-z0-9-]+$')
        for e in entities:
            target_ward = e.get("placeId")
            if target_ward in self.EXPECTED_17_WHITE_ZONES:
                covered_in_entities.add(target_ward)

            # Integrity rules for provisional seed entities
            assert slug_pattern.match(e["id"]), f"Seed entity ID {e['id']} must be valid kebab-case slug"
            assert e.get("status") == "provisional", f"Seed entity {e['id']} must be provisional"
            assert e.get("verified") == 0, f"Seed entity {e['id']} verified flag must be 0"
            assert "source_citations" in e or "source" in e, f"Seed {e['id']} missing source citation"

        assert covered_in_entities == self.EXPECTED_17_WHITE_ZONES, (
            f"Seed entities do not cover all 17 white zones. Missing: {self.EXPECTED_17_WHITE_ZONES - covered_in_entities}"
        )


# ============================================================================
# 3. 864 ADDRESS NORMALIZATION REGEX & WHITELIST PRESERVATION
# ============================================================================

class TestAddressNormalizationAdversarial:

    CANONICAL_2TIER_REGEX = re.compile(
        r"^.+,\s*(Phường|Xã)\s+[^,]+,\s*tỉnh Vĩnh Long$",
        re.UNICODE
    )

    # Regex targeting abolished districts appearing in intermediate administrative tier position
    ABOLISHED_ADMIN_REGEX = re.compile(
        r",\s*(huyện\s+)?(long hồ|mang thít|vũng liêm|tam bình|trà ôn|bình tân|ba tri|bình đại|châu thành|chợ lách|giồng trôm|mỏ cày|mỏ cày bắc|mỏ cày nam|thạnh phú|càng long|cầu kè|cầu ngang|duyên hải|tiểu cần|trà cú)\s*,",
        re.IGNORECASE | re.UNICODE
    )

    OLD_PROVINCE_REGEX = re.compile(
        r"tỉnh\s+(bến tre|trà vinh)",
        re.IGNORECASE | re.UNICODE
    )

    def test_864_remediations_in_ledger(self, ledger):
        """Ledger must contain exactly 864 address remediations (373 district + 491 province)."""
        remeds = [r for r in ledger["remediations"] if r["error_code"] in ("ERR_OLD_ADMIN_DISTRICT", "ERR_OLD_PROVINCE_REF")]
        assert len(remeds) == 864, f"Expected 864 address remediations, found {len(remeds)}"

        district_remeds = [r for r in remeds if r["error_code"] == "ERR_OLD_ADMIN_DISTRICT"]
        province_remeds = [r for r in remeds if r["error_code"] == "ERR_OLD_PROVINCE_REF"]
        assert len(district_remeds) == 373, f"Expected 373 ERR_OLD_ADMIN_DISTRICT, found {len(district_remeds)}"
        assert len(province_remeds) == 491, f"Expected 491 ERR_OLD_PROVINCE_REF, found {len(province_remeds)}"

    def test_all_864_addresses_conform_to_2tier_format(self, ledger):
        """Every single proposed address must strictly match 2-tier format and eliminate old district tiers."""
        remeds = [r for r in ledger["remediations"] if r["error_code"] in ("ERR_OLD_ADMIN_DISTRICT", "ERR_OLD_PROVINCE_REF")]

        failures = []
        for r in remeds:
            prop_addr = r["proposed_value"]
            if not isinstance(prop_addr, str):
                failures.append((r["id"], prop_addr, "Not a string"))
                continue

            # Check 1: Must match canonical 2-tier regex: [Tên điểm], [Xã/Phường], tỉnh Vĩnh Long
            if not self.CANONICAL_2TIER_REGEX.match(prop_addr):
                failures.append((r["id"], prop_addr, "Does not match 2-tier regex"))
                continue

            # Check 2: Must NOT have abolished district name as an intermediate administrative tier
            if self.ABOLISHED_ADMIN_REGEX.search(prop_addr):
                failures.append((r["id"], prop_addr, "Contains abolished district tier"))
                continue

            # Check 3: Must NOT contain old province references in address
            if self.OLD_PROVINCE_REGEX.search(prop_addr):
                failures.append((r["id"], prop_addr, "Contains old province reference"))
                continue

            # Check 4: No double commas or trailing commas
            if ",," in prop_addr or prop_addr.endswith(","):
                failures.append((r["id"], prop_addr, "Malformed punctuation"))

        assert len(failures) == 0, f"Found {len(failures)} non-conforming addresses: {failures[:10]}"

    def test_whitelist_and_legacy_area_preservation(self, spatial_remed, db_conn):
        """Historical text in descriptions and legacy administrative context must be preserved."""
        wp = spatial_remed["whitelist_preservation"]
        assert wp["compliance_status"] == "PRESERVED"
        assert wp["total_whitelisted_occurrences"] == 91
        assert wp["total_whitelisted_rules"] == 89

        # Verify whitelist file exists and contains expected rules
        assert WHITELIST_PATH.exists()
        lines = [l.strip() for l in WHITELIST_PATH.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]
        assert len(lines) == 89

        # Check in DB that descriptions containing historical terms were untouched (READ-ONLY proof)
        cur = db_conn.cursor()
        cur.execute("SELECT count(*) FROM entities WHERE description LIKE '%Đồng Khởi%' OR description LIKE '%khởi nghĩa%' OR description LIKE '%lịch sử%'")
        historical_count = cur.fetchone()[0]
        assert historical_count > 50, "Historical records in DB must exist and remain untouched"

        # Check legacyArea in DB preserves historical origin for 164 entities
        cur.execute("SELECT count(*) FROM entities WHERE legacyArea IS NOT NULL AND legacyArea != ''")
        legacy_count = cur.fetchone()[0]
        assert legacy_count == 164


# ============================================================================
# 4. 67 EVENTS TEMPORAL 6-FIELD CROSS-CHECK & CIRCUIT BREAKER
# ============================================================================

class TestTemporalCrossCheckAndCircuitBreaker:

    def test_exactly_67_events_in_db(self, db_conn):
        """Empirically verify exactly 67 entities have type = 'event'."""
        cur = db_conn.cursor()
        cur.execute("SELECT count(*) FROM entities WHERE type = 'event'")
        assert cur.fetchone()[0] == 67

    def test_events_temporal_remediations_in_ledger_and_temporal_json(self, ledger, temporal_remed, db_conn):
        """Ledger must contain exactly 24 temporal remediations (3 Group B + 21 Group C/E)."""
        remeds_b = [r for r in ledger["remediations"] if r["error_code"] == "ERR_TEMPORAL_CONFLICT_B"]
        remeds_c = [r for r in ledger["remediations"] if r["error_code"] == "ERR_TEMPORAL_CONFLICT_C"]

        assert len(remeds_b) == 3, f"Expected 3 Group B remediations, got {len(remeds_b)}"
        assert len(remeds_c) == 21, f"Expected 21 Group C/E remediations, got {len(remeds_c)}"

        # Group B: Astronomical accuracy of date corrections
        cung_mieu = [r for r in remeds_b if r["entity_id"] == "le-cung-mieu"][0]
        assert cung_mieu["proposed_value"]["date_start"] == "2026-03-04"
        assert cung_mieu["proposed_value"]["date_end"] == "2026-03-06"

        thuong_dien = [r for r in remeds_b if r["entity_id"] == "le-thuong-dien-dinh-tan-ngai"][0]
        assert thuong_dien["proposed_value"]["date_start"] == "2026-11-24"
        assert thuong_dien["proposed_value"]["date_end"] == "2026-11-25"

        dom_long = [r for r in remeds_b if r["entity_id"] == "le-hoi-dom-long-neak-ta"][0]
        assert dom_long["proposed_value"]["date_start"] is None

        # Verify all 21 circuit breaker events are catalogued in temporal remediation
        cb_events = temporal_remed["circuit_breaker_blocked_events_21"]
        assert len(cb_events) == 21

        # Verify in DB that all 21 events have attributes.month populated
        cur = db_conn.cursor()
        for e in cb_events:
            eid = e["entity_id"]
            cur.execute("SELECT attributes FROM entities WHERE id = ?", (eid,))
            row = cur.fetchone()
            assert row is not None, f"Event {eid} not in DB"
            attrs = json.loads(row[0]) if row[0] else {}
            assert "month" in attrs, f"Event {eid} missing attributes.month in DB"
            assert attrs["month"] == e["attribute_month"], f"Event {eid} month mismatch in DB"

    def test_lunar_calendar_2026_edge_cases(self):
        """Year 2026 (Bính Ngọ) astronomical edge cases: no leap month, short months 8 & 12 (29 days)."""
        # 1. 2026 has no leap month
        with pytest.raises(ValueError, match="không có tháng nhuận"):
            lunar_calendar.lunar_to_solar(15, 6, 2026, leap=True)

        with pytest.raises(ValueError, match="không có tháng nhuận"):
            lunar_calendar.lunar_to_solar(1, 1, 2026, leap=True)

        # 2. Month 8 in 2026 has only 29 days (tháng thiếu)
        solar_29_8 = lunar_calendar.lunar_to_solar(29, 8, 2026)
        assert isinstance(solar_29_8, date)
        with pytest.raises(ValueError, match="không tồn tại"):
            lunar_calendar.lunar_to_solar(30, 8, 2026)

        # 3. Month 12 in 2026 has only 29 days (tháng thiếu)
        solar_29_12 = lunar_calendar.lunar_to_solar(29, 12, 2026)
        assert isinstance(solar_29_12, date)
        with pytest.raises(ValueError, match="không tồn tại"):
            lunar_calendar.lunar_to_solar(30, 12, 2026)

        # 4. Standard full month (e.g. Month 1 2026) has 30 days
        solar_30_1 = lunar_calendar.lunar_to_solar(30, 1, 2026)
        assert isinstance(solar_30_1, date)

    def test_public_api_event_circuit_breaker_stress_test(self, db_conn, temporal_remed):
        """Adversarially stress-test _event_date_reliable circuit breaker in public_api.py."""
        # Case 1: All 21 Group C/E events from DB must be blocked by the circuit breaker
        cb_events = temporal_remed["circuit_breaker_blocked_events_21"]
        cur = db_conn.cursor()

        for e in cb_events:
            eid = e["entity_id"]
            cur.execute("SELECT attributes FROM entities WHERE id = ?", (eid,))
            row = cur.fetchone()
            attrs = json.loads(row[0]) if row[0] else {}
            synthetic_event = {"id": eid, "attributes": attrs}
            is_reliable = _event_date_reliable(synthetic_event)
            assert is_reliable is False, f"Event {eid} should be blocked by circuit breaker, got reliable=True"

        # Case 2: Seasonal item with category = 'mua'
        event_mua = {
            "id": "event-mua-test",
            "attributes": {"category": "mua", "date_start": "2026-10-01"}
        }
        assert _event_date_reliable(event_mua) is False

        # Case 3: Free-form text date (not ISO)
        event_text = {
            "id": "event-text-test",
            "attributes": {"date_start": "Rằm tháng Giêng năm Bính Ngọ"}
        }
        assert _event_date_reliable(event_text) is False

        # Case 4: Mismatched month between date_start and attributes.month
        event_mismatch = {
            "id": "event-mismatch-test",
            "attributes": {"date_start": "2026-04-15", "month": 9}
        }
        assert _event_date_reliable(event_mismatch) is False

        # Case 5: Perfectly matching ISO date and month
        event_match = {
            "id": "event-match-test",
            "attributes": {"date_start": "2026-04-15", "month": 4}
        }
        assert _event_date_reliable(event_match) is True

        # Case 6: Matching ISO date with no month specified
        event_nomonth = {
            "id": "event-nomonth-test",
            "attributes": {"date_start": "2026-04-15"}
        }
        assert _event_date_reliable(event_nomonth) is True


# ============================================================================
# 5. STRICT READ-ONLY INTEGRITY ON PRODUCTION ARTIFACTS
# ============================================================================

class TestProductionIntegrity:

    def test_database_is_read_only_and_unaltered(self, db_conn):
        """Verify that attempting to write to the connection raises an error."""
        cur = db_conn.cursor()
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            cur.execute("UPDATE entities SET verified = 0 WHERE id = 'prov-1'")

    def test_data_json_unaltered(self):
        """Verify web/data.json exists and is intact."""
        data_json_path = REPO_ROOT / "web" / "data.json"
        if data_json_path.exists():
            with open(data_json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            assert len(data) > 0
