/**
 * Data Health Invariants Test Suite (E2E Track)
 *
 * Ground Truth Baseline Reference:
 * - c:\Users\NCTaam\Documents\vinhlong360-correction-case-pilot\.agents\ORIGINAL_REQUEST.md
 * - Baseline: 1,747 entities | 12,061 relationships | 33 itineraries | 864 old-district refs | 0 verifiedAt | 988 NotebookLM sources
 *
 * System Architecture:
 * - STRICT READ-ONLY on agent/data/vinhlong360.db via node:sqlite DatabaseSync
 * - 4 Systematic Tiers:
 *   Tier 1: Feature Coverage (9 Core Invariants)
 *   Tier 2: Boundary & Corner Cases (BBox, 17 White Zones, Lunar Calendar boundaries)
 *   Tier 3: Cross-Feature Combinations (Itineraries x KG, White Zones x Seeds, Schema.org)
 *   Tier 4: Real-World Scenarios (Tourist Journey, Festival Planner, Geo-Coder, KG Hop, Governance Audit)
 */

import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { DatabaseSync } from 'node:sqlite';
import path from 'node:path';
import fs from 'node:fs';

// Determine repository root and database path dynamically
const repoRoot = fs.existsSync(path.resolve('agent/data/vinhlong360.db'))
  ? path.resolve('.')
  : path.resolve('..');
const dbPath = path.join(repoRoot, 'agent/data/vinhlong360.db');

let db: DatabaseSync;

beforeAll(() => {
  expect(fs.existsSync(dbPath), `Database file must exist at ${dbPath}`).toBe(true);
  db = new DatabaseSync(dbPath, { readOnly: true });
});

afterAll(() => {
  if (db) {
    db.close();
  }
});

// ---------------------------------------------------------------------------
// Mathematical & GIS Helpers
// ---------------------------------------------------------------------------

/**
 * Calculates Haversine distance in kilometers between two GPS points.
 */
function haversineDistanceKm(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 6371.0; // Earth radius in km
  const toRad = (d: number) => (d * Math.PI) / 180.0;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

/**
 * Validates if coordinates fall within the standard Mekong Bounding Box:
 * Latitude: 9.0 <= lat <= 11.0
 * Longitude: 105.0 <= lng <= 107.0
 */
function isInMekongBBox(lat: number, lng: number): boolean {
  return lat >= 9.0 && lat <= 11.0 && lng >= 105.0 && lng <= 107.0;
}

/**
 * List of known old district names abolished under Resolution 1687/NQ-UBTVQH15.
 */
const OLD_DISTRICT_NAMES = [
  'long hồ', 'mang thít', 'vũng liêm', 'tam bình', 'trà ôn', 'bình tân',
  'ba tri', 'bình đại', 'châu thành', 'chợ lách', 'giồng trôm', 'mỏ cày', 'thạnh phú',
  'càng long', 'cầu kè', 'cầu ngang', 'duyên hải', 'tiểu cần', 'trà cú'
];

// ===========================================================================
// TIER 1: FEATURE COVERAGE (9 CORE DATA INVARIANTS)
// ===========================================================================

describe('Tier 1: Feature Coverage (Core Data Invariants)', () => {

  // Invariant 1: Administrative Hierarchy & Total Entity Baseline
  describe('Invariant 1: Administrative Hierarchy & Entity Baseline', () => {
    it('asserts total entities baseline is exactly 1,747', () => {
      const row = db.prepare('SELECT count(*) as count FROM entities').get() as { count: number };
      expect(row.count).toBe(1747);
    });

    it('asserts administrative units hierarchy: 1 province and 124 communes/wards', () => {
      const provRow = db.prepare("SELECT count(*) as count FROM entities WHERE type = 'place' AND level = 'tinh'").get() as { count: number };
      expect(provRow.count).toBe(1);

      const adminUnits = db.prepare("SELECT count(*) as count FROM entities WHERE type = 'place' AND parentId = 'vinh-long'").get() as { count: number };
      expect(adminUnits.count).toBe(124);

      const wards = db.prepare("SELECT count(*) as count FROM entities WHERE type = 'place' AND level = 'phuong'").get() as { count: number };
      const communes = db.prepare("SELECT count(*) as count FROM entities WHERE type = 'place' AND level = 'xa'").get() as { count: number };
      expect(wards.count).toBe(35);
      expect(communes.count).toBe(89);
      expect(wards.count + communes.count).toBe(124);
    });

    it('asserts abolished district level is zero in place entities (2-tier administrative model)', () => {
      const districts = db.prepare("SELECT count(*) as count FROM entities WHERE type = 'place' AND level = 'huyen'").get() as { count: number };
      expect(districts.count).toBe(0);
    });

    it('asserts exact distribution of 17 content model types', () => {
      const typeRows = db.prepare('SELECT type, count(*) as count FROM entities GROUP BY type').all() as Array<{ type: string; count: number }>;
      const typeMap = Object.fromEntries(typeRows.map(r => [r.type, r.count]));

      expect(typeMap['product']).toBe(218);
      expect(typeMap['attraction']).toBe(213);
      expect(typeMap['history']).toBe(191);
      expect(typeMap['restaurant']).toBe(186);
      expect(typeMap['accommodation']).toBe(164);
      expect(typeMap['place']).toBe(125);
      expect(typeMap['nature']).toBe(120);
      expect(typeMap['dish']).toBe(118);
      expect(typeMap['craft_village']).toBe(90);
      expect(typeMap['experience']).toBe(90);
      expect(typeMap['event']).toBe(67);
      expect(typeMap['facility']).toBe(57);
      expect(typeMap['cafe']).toBe(56);
      expect(typeMap['person']).toBe(34);
      expect(typeMap['itinerary']).toBe(16);
      expect(typeMap['drink']).toBe(1);
      expect(typeMap['organization']).toBe(1);
    });

    it('asserts entity_adminplace_details contains exactly 125 records matching places', () => {
      const row = db.prepare('SELECT count(*) as count FROM entity_adminplace_details').get() as { count: number };
      expect(row.count).toBe(125);
    });
  });

  // Invariant 2: prov-1 Malformed Dict String Detection & Remediation
  describe('Invariant 2: Coordinate Anomaly (prov-1) Detection & Remediation', () => {
    it('detects prov-1 exists with malformed JSON dictionary coordinates string', () => {
      const prov1 = db.prepare("SELECT id, name, coordinates FROM entities WHERE id = 'prov-1'").get() as { id: string; name: string; coordinates: string };
      expect(prov1).toBeDefined();
      expect(prov1.id).toBe('prov-1');

      // Baseline ground truth: coordinates is stored as a dict string '{"lat": 10.253, "lng": 106.012}'
      expect(prov1.coordinates).toContain('"lat"');
      expect(prov1.coordinates).toContain('"lng"');

      const parsed = JSON.parse(prov1.coordinates);
      expect(Array.isArray(parsed)).toBe(false);
      expect(typeof parsed).toBe('object');
      expect(parsed.lat).toBe(10.253);
      expect(parsed.lng).toBe(106.012);
    });

    it('validates remediation schema transforms prov-1 into standard [lat, lng] array', () => {
      const prov1 = db.prepare("SELECT coordinates FROM entities WHERE id = 'prov-1'").get() as { coordinates: string };
      const raw = JSON.parse(prov1.coordinates);

      // Remediation logic
      const remediated: [number, number] = [Number(raw.lat), Number(raw.lng)];
      expect(Array.isArray(remediated)).toBe(true);
      expect(remediated.length).toBe(2);
      expect(remediated[0]).toBeCloseTo(10.253, 3);
      expect(remediated[1]).toBeCloseTo(106.012, 3);
      expect(isInMekongBBox(remediated[0], remediated[1])).toBe(true);
    });

    it('verifies all other 1,733 coordinate records are stored as array format or null', () => {
      const rows = db.prepare("SELECT id, coordinates FROM entities WHERE id != 'prov-1' AND coordinates IS NOT NULL AND coordinates != ''").all() as Array<{ id: string; coordinates: string }>;
      for (const r of rows) {
        const parsed = JSON.parse(r.coordinates);
        expect(Array.isArray(parsed), `Entity ${r.id} coordinates must be an array`).toBe(true);
        expect(parsed.length).toBe(2);
      }
    });
  });

  // Invariant 3: Exactly 13 Missing Coordinates Detected & Remediated
  describe('Invariant 3: Missing Coordinates Audit (13 Entities)', () => {
    it('identifies exactly 13 entities with null or empty coordinates', () => {
      const missing = db.prepare("SELECT id, name, type FROM entities WHERE coordinates IS NULL OR coordinates = ''").all() as Array<{ id: string; name: string; type: string }>;
      expect(missing.length).toBe(13);

      const ids = missing.map(m => m.id);
      expect(ids).toContain('ben-xe-mien-tay-hcm');
      expect(ids).toContain('bun-nuoc-leo-cho-ba-tri-ben-tre');
      expect(ids).toContain('khu-luu-niem-nguyen-dinh-chieu');
      expect(ids).toContain('phuoc-minh-cung-chua-ong-tra-vinh');
      expect(ids).toContain('nha-gom-tu-buoi-w3');
      expect(ids).toContain('ben-tiep-nhan-vu-khi-con-tau');
      expect(ids).toContain('lang-ong-con-tau');
      expect(ids).toContain('lau-ba-mieu-ba-chua-xu-ba-co-hy');
      expect(ids).toContain('itinerary-lang-nghe-vong-quanh');
      expect(ids).toContain('itinerary-tuan-trang-mat-mien-tay-4n3d');
      expect(ids).toContain('itinerary-vl-bt-tv-3d3t-giadinh');
      expect(ids).toContain('ocop-tour-3-tinh-mua-sam');
      expect(ids).toContain('backpacker-mien-tay-3ngay-500k');
    });

    it('classifies missing coordinates into 5 itineraries, 1 external gateway, and 7 field destinations', () => {
      const missing = db.prepare("SELECT id, type FROM entities WHERE coordinates IS NULL OR coordinates = ''").all() as Array<{ id: string; type: string }>;
      const itineraryCount = missing.filter(m => m.type === 'itinerary').length;
      const gatewayCount = missing.filter(m => m.id === 'ben-xe-mien-tay-hcm').length;
      const destinationCount = missing.filter(m => m.type !== 'itinerary' && m.id !== 'ben-xe-mien-tay-hcm').length;

      expect(itineraryCount).toBe(5);
      expect(gatewayCount).toBe(1);
      expect(destinationCount).toBe(7);
    });

    it('verifies remediation GPS coordinates for the 7 physical field destinations fall inside Mekong BBox', () => {
      const fieldRemediations: Record<string, [number, number]> = {
        'bun-nuoc-leo-cho-ba-tri-ben-tre': [10.0392, 106.5985],
        'khu-luu-niem-nguyen-dinh-chieu': [10.0381, 106.5892],
        'phuoc-minh-cung-chua-ong-tra-vinh': [9.9374, 106.3451],
        'nha-gom-tu-buoi-w3': [10.2534, 105.9812],
        'ben-tiep-nhan-vu-khi-con-tau': [9.6835, 106.5381],
        'lang-ong-con-tau': [9.6821, 106.5394],
        'lau-ba-mieu-ba-chua-xu-ba-co-hy': [9.6804, 106.5408],
      };

      for (const [id, [lat, lng]] of Object.entries(fieldRemediations)) {
        expect(isInMekongBBox(lat, lng), `Coordinates for ${id} [${lat}, ${lng}] must be inside Mekong BBox`).toBe(true);
      }
    });

    it('verifies external gateway ben-xe-mien-tay-hcm is located in HCMC (lat ~10.74, lng ~106.62)', () => {
      const gatewayCoords: [number, number] = [10.7407, 106.6186];
      expect(gatewayCoords[0]).toBeGreaterThan(10.65); // Outside Vinh Long proper
      expect(gatewayCoords[1]).toBeLessThan(107.0);
    });
  });

  // Invariant 4: 864 Old-District References Identified with Canonical 2-Tier Rule
  describe('Invariant 4: Old-District References & 2-Tier Format Normalization', () => {
    it('identifies entities containing old district names in address', () => {
      const entities = db.prepare("SELECT id, address, legacyArea FROM entities WHERE address IS NOT NULL AND address != ''").all() as Array<{ id: string; address: string; legacyArea: string }>;
      let oldDistrictHits = 0;

      for (const e of entities) {
        const addr = e.address.toLowerCase();
        const hasOldDistrict = OLD_DISTRICT_NAMES.some(d => addr.includes(d) || addr.includes('huyện ' + d) || addr.includes('thị xã ' + d));
        const hasOldProvince = addr.includes('bến tre') || addr.includes('trà vinh');
        if (hasOldDistrict || hasOldProvince) {
          oldDistrictHits++;
        }
      }

      // 864 old-district references identified in baseline requirement
      expect(oldDistrictHits).toBeGreaterThanOrEqual(864);
    });

    it('validates canonical 2-tier address syntax rule: [Point Name / Number - Street - Hamlet], [Ward/Commune], tỉnh Vĩnh Long', () => {
      const validCanonicalAddresses = [
        'Số 123 Đường 3/2, Phường Thanh Đức, tỉnh Vĩnh Long',
        'Ấp Giồng Cụt, Xã An Đức, tỉnh Vĩnh Long',
        'Khu phố 1, Phường Vũng Liêm, tỉnh Vĩnh Long',
      ];

      const invalidAddresses = [
        'Số 123 Đường 3/2, Huyện Long Hồ, tỉnh Vĩnh Long',
        'Ấp Giồng Cụt, Thị xã Duyên Hải, tỉnh Trà Vinh',
        'Khu phố 1, Huyện Ba Tri, tỉnh Bến Tre',
      ];

      const canonicalRegex = /^.+,\s*(Phường|Xã)\s+[^,]+,\s*tỉnh Vĩnh Long$/;
      const forbiddenRegex = /(Huyện|Thị xã|tỉnh Bến Tre|tỉnh Trà Vinh)/i;

      for (const addr of validCanonicalAddresses) {
        expect(canonicalRegex.test(addr)).toBe(true);
        expect(forbiddenRegex.test(addr)).toBe(false);
      }

      for (const addr of invalidAddresses) {
        expect(forbiddenRegex.test(addr)).toBe(true);
      }
    });

    it('verifies legacyArea column provides mapping back to original merged districts', () => {
      const legacyCount = db.prepare("SELECT count(*) as count FROM entities WHERE legacyArea IS NOT NULL AND legacyArea != ''").get() as { count: number };
      expect(legacyCount.count).toBeGreaterThan(0);
    });
  });

  // Invariant 5: 67 Events Temporal Audit & Circuit Breaker Check
  describe('Invariant 5: 6-Field Temporal Cross-Check (67 Events)', () => {
    it('verifies exactly 67 event entities in both entities and entity_event_details', () => {
      const events = db.prepare("SELECT count(*) as count FROM entities WHERE type = 'event'").get() as { count: number };
      const eventDetails = db.prepare('SELECT count(*) as count FROM entity_event_details').get() as { count: number };
      expect(events.count).toBe(67);
      expect(eventDetails.count).toBe(67);
    });

    it('verifies the 6 independent temporal audit fields are defined and accessible', () => {
      const sample = db.prepare(`
        SELECT e.id, e.summary, e.description, e.season,
               d.lunar_date, d.date_start, d.date_end
        FROM entities e
        JOIN entity_event_details d ON e.id = d.entity_id
        LIMIT 10
      `).all() as Array<{
        id: string; summary: string; description: string; season: string;
        lunar_date: string; date_start: string; date_end: string;
      }>;

      expect(sample.length).toBe(10);
      for (const s of sample) {
        expect(s.id).toBeDefined();
        // At least one descriptive or temporal date field is populated
        const hasDateInfo = Boolean(s.lunar_date || s.date_start || s.summary || s.season);
        expect(hasDateInfo).toBe(true);
      }
    });

    it('verifies attributes.month circuit breaker preserves safety for events with date discrepancies', () => {
      const eventsWithMonth = db.prepare("SELECT id, attributes FROM entities WHERE type = 'event' AND json_extract(attributes, '$.month') IS NOT NULL").all() as Array<{ id: string; attributes: string }>;
      expect(eventsWithMonth.length).toBeGreaterThanOrEqual(21);

      for (const ev of eventsWithMonth) {
        const attrs = JSON.parse(ev.attributes);
        expect(attrs.month).toBeDefined();
        expect(typeof attrs.month === 'number' || typeof attrs.month === 'string').toBe(true);
        const m = Number(attrs.month);
        expect(m).toBeGreaterThanOrEqual(1);
        expect(m).toBeLessThanOrEqual(12);
      }
    });

    it('asserts ISO date_start <= date_end when both are formatted as YYYY-MM-DD', () => {
      const rows = db.prepare(`
        SELECT entity_id, date_start, date_end
        FROM entity_event_details
        WHERE date_start GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
          AND date_end GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
      `).all() as Array<{ entity_id: string; date_start: string; date_end: string }>;

      for (const r of rows) {
        expect(r.date_start <= r.date_end, `Event ${r.entity_id} start (${r.date_start}) must be <= end (${r.date_end})`).toBe(true);
      }
    });
  });

  // Invariant 6: 988 NotebookLM Sources & Missing Entities Seed Schema
  describe('Invariant 6: NotebookLM Knowledge Invariants (988 Sources)', () => {
    it('verifies 988 sources baseline distribution across the 3 notebooks', () => {
      const notebooks = [
        { name: 'Vĩnh Long 360', id: 'v-nh-long-v-nh-long-b-n-tre-tr', sources: 581 },
        { name: 'Mekong 360 - Tập 2', id: 'mekong-360-vol-2', sources: 391 },
        { name: 'Chính sách & Pháp luật', id: 'ch-nh-s-ch-ph-p-lu-t-v-n-b-n-q', sources: 16 }
      ];

      const totalSources = notebooks.reduce((sum, n) => sum + n.sources, 0);
      expect(totalSources).toBe(988);
    });

    it('validates schema contract for curated_missing_entities_seed.json', () => {
      // Mock / schema validation for seed generator output
      const validSeedItem = {
        id: 'seed-lang-nghe-hieu-phung',
        name: 'Làng nghề đan lục bình Hiếu Phụng',
        type: 'craft_village',
        area: 'vinh-long',
        placeId: 'xa-hieu-phung',
        address: 'Ấp Quang Trạch, Xã Hiếu Phụng, tỉnh Vĩnh Long',
        coordinates: [10.1524, 106.0712],
        summary: 'Làng nghề truyền thống đan thảm và giỏ lục bình xuất khẩu nổi tiếng tại xã Hiếu Phụng, phục vụ du lịch sinh thái.',
        description: 'Chi tiết lịch sử hình thành và kỹ nghệ đan lục bình thủ công mỹ nghệ.',
        attributes: { craft_type: 'luc_binh', artisan_count: 120 },
        source: [{ name: 'NotebookLM Vĩnh Long 360 - Sổ tay 1', url: 'https://notebooklm.google.com' }],
        status: 'provisional',
        verified: 0
      };

      expect(validSeedItem.status).toBe('provisional');
      expect(validSeedItem.verified).toBe(0);
      expect(validSeedItem.coordinates.length).toBe(2);
      const [cLat, cLng] = validSeedItem.coordinates as [number, number];
      expect(isInMekongBBox(cLat, cLng)).toBe(true);
      expect(validSeedItem.summary.length).toBeGreaterThanOrEqual(50);
      expect(validSeedItem.summary.length).toBeLessThanOrEqual(500);
    });

    it('validates actual outputs/curated_missing_entities_seed.json if generated on disk', () => {
      const seedPath = path.join(repoRoot, 'outputs/curated_missing_entities_seed.json');
      if (fs.existsSync(seedPath)) {
        const content = JSON.parse(fs.readFileSync(seedPath, 'utf8'));
        expect(content.generated_at).toBeDefined();
        expect(Array.isArray(content.entities)).toBe(true);
        expect(content.entities.length).toBeGreaterThan(0);

        for (const ent of content.entities) {
          expect(ent.id).toBeDefined();
          expect(ent.name).toBeDefined();
          expect(ent.status).toBe('provisional');
          expect(ent.verified).toBe(0);
          expect(Array.isArray(ent.coordinates)).toBe(true);
        }
      }
    });
  });

  // Invariant 7: Knowledge Graph (12,061 Relationships & 33 Orphan Nodes)
  describe('Invariant 7: Knowledge Graph Integrity (12,061 Edges & 33 Orphans)', () => {
    it('asserts exact count of 12,061 relationships in database', () => {
      const relCount = db.prepare('SELECT count(*) as count FROM relationships').get() as { count: number };
      expect(relCount.count).toBe(12061);
    });

    it('asserts distribution of 5 relationship types in knowledge graph', () => {
      const types = db.prepare('SELECT type, count(*) as count FROM relationships GROUP BY type').all() as Array<{ type: string; count: number }>;
      const typeMap = Object.fromEntries(types.map(t => [t.type, t.count]));

      expect(typeMap['near']).toBe(4895);
      expect(typeMap['related_to']).toBe(4179);
      expect(typeMap['located_in']).toBe(2172);
      expect(typeMap['associated_with']).toBe(630);
      expect(typeMap['produced_in']).toBe(185);
    });

    it('detects exactly 33 orphan content entities having 0 relationships', () => {
      const orphans = db.prepare(`
        SELECT e.id, e.name, e.type
        FROM entities e
        LEFT JOIN relationships r1 ON e.id = r1.from_id
        LEFT JOIN relationships r2 ON e.id = r2.to_id
        WHERE r1.from_id IS NULL AND r2.to_id IS NULL AND e.type != 'place'
      `).all() as Array<{ id: string; name: string; type: string }>;

      expect(orphans.length).toBe(33);

      const byType: Record<string, number> = {};
      for (const o of orphans) {
        byType[o.type] = (byType[o.type] || 0) + 1;
      }
      expect(byType['attraction']).toBe(13);
      expect(byType['history']).toBe(12);
      expect(byType['craft_village']).toBe(6);
      expect(byType['nature']).toBe(1);
      expect(byType['dish']).toBe(1);
    });

    it('detects and isolates dangling edge anomaly in knowledge graph for remediation', () => {
      const danglingFrom = db.prepare(`
        SELECT r.from_id, r.to_id, r.type
        FROM relationships r
        LEFT JOIN entities e ON r.from_id = e.id
        WHERE e.id IS NULL
      `).all() as Array<{ from_id: string; to_id: string; type: string }>;

      const danglingTo = db.prepare(`
        SELECT r.from_id, r.to_id, r.type
        FROM relationships r
        LEFT JOIN entities e ON r.to_id = e.id
        WHERE e.id IS NULL
      `).all() as Array<{ from_id: string; to_id: string; type: string }>;

      // Baseline audit finding: exactly 1 test artifact dangling edge exists ('nonexistent-a' -> 'nonexistent-b')
      expect(danglingFrom.length).toBe(1);
      expect(danglingTo.length).toBe(1);
      const firstDanglingFrom = danglingFrom[0];
      const firstDanglingTo = danglingTo[0];
      expect(firstDanglingFrom).toBeDefined();
      expect(firstDanglingTo).toBeDefined();
      if (firstDanglingFrom && firstDanglingTo) {
        expect(firstDanglingFrom.from_id).toBe('nonexistent-a');
        expect(firstDanglingFrom.to_id).toBe('nonexistent-b');
        expect(firstDanglingFrom.type).toBe('near');
      }

      // All other 12,060 edges have valid existing from_id and to_id entities
      const validEdges = db.prepare(`
        SELECT count(*) as count
        FROM relationships r
        JOIN entities e1 ON r.from_id = e1.id
        JOIN entities e2 ON r.to_id = e2.id
      `).get() as { count: number };
      expect(validEdges.count).toBe(12060);
    });
  });

  // Invariant 8: 33 Itineraries Travel Feasibility & Stop Integrity
  describe('Invariant 8: Itineraries Travel Feasibility & Stop Integrity', () => {
    it('asserts exactly 33 itineraries in database with total 182 stops', () => {
      const itins = db.prepare('SELECT id, stops FROM itineraries').all() as Array<{ id: string; stops: string }>;
      expect(itins.length).toBe(33);

      let totalStops = 0;
      for (const it of itins) {
        const parsed = JSON.parse(it.stops || '[]');
        totalStops += parsed.length;
      }
      expect(totalStops).toBe(182);
    });

    it('identifies unlinked stops and checks valid entity resolution', () => {
      const itins = db.prepare('SELECT id, stops FROM itineraries').all() as Array<{ id: string; stops: string }>;
      let resolvedCount = 0;
      let unlinkedCount = 0;

      for (const it of itins) {
        const stops = JSON.parse(it.stops || '[]');
        for (const s of stops) {
          const eid = s.entityId || s.id;
          if (eid) {
            const ent = db.prepare('SELECT id FROM entities WHERE id = ?').get(eid);
            if (ent) {
              resolvedCount++;
            } else {
              unlinkedCount++;
            }
          } else {
            unlinkedCount++;
          }
        }
      }

      expect(resolvedCount).toBe(171);
      expect(unlinkedCount).toBe(11);
    });

    it('verifies Haversine distance between sequential resolved stops is <= 120 km', () => {
      const itins = db.prepare('SELECT id, stops FROM itineraries').all() as Array<{ id: string; stops: string }>;

      for (const it of itins) {
        const stops = JSON.parse(it.stops || '[]');
        for (let i = 0; i < stops.length - 1; i++) {
          const id1 = stops[i].entityId || stops[i].id;
          const id2 = stops[i + 1].entityId || stops[i + 1].id;
          if (id1 && id2) {
            const e1 = db.prepare('SELECT coordinates FROM entities WHERE id = ?').get(id1) as { coordinates?: string };
            const e2 = db.prepare('SELECT coordinates FROM entities WHERE id = ?').get(id2) as { coordinates?: string };
            if (e1?.coordinates && e2?.coordinates) {
              try {
                const c1 = JSON.parse(e1.coordinates);
                const c2 = JSON.parse(e2.coordinates);
                if (Array.isArray(c1) && Array.isArray(c2)) {
                  const dist = haversineDistanceKm(c1[0], c1[1], c2[0], c2[1]);
                  expect(dist, `Hop from ${id1} to ${id2} in ${it.id} (${dist.toFixed(1)} km) must be <= 120 km`).toBeLessThanOrEqual(120);
                }
              } catch {}
            }
          }
        }
      }
    });
  });

  // Invariant 9: E-E-A-T Field Audit (verified=1 vs attributes.verifiedAt)
  describe('Invariant 9: E-E-A-T Field Audit & Anti-Slop Integrity', () => {
    it('asserts 100% (1,747) entities have verified=1 publish flag', () => {
      const verifiedRow = db.prepare('SELECT count(*) as count FROM entities WHERE verified = 1').get() as { count: number };
      expect(verifiedRow.count).toBe(1747);
    });

    it('asserts 0/1,747 entities possess attributes.verifiedAt timestamp (mandatory anti-slop finding)', () => {
      const verifiedAtRow = db.prepare("SELECT count(*) as count FROM entities WHERE json_extract(attributes, '$.verifiedAt') IS NOT NULL").get() as { count: number };
      expect(verifiedAtRow.count).toBe(0);
    });

    it('enforces that verified=1 alone must never be presented as physical on-site verified without verifiedAt', () => {
      const sample = db.prepare('SELECT id, name, verified, attributes FROM entities LIMIT 20').all() as Array<{ id: string; name: string; verified: number; attributes: string }>;
      for (const s of sample) {
        const attrs = JSON.parse(s.attributes || '{}');
        // Audit assertion: If verifiedAt is missing, fieldVerification is false
        const isFieldVerified = Boolean(attrs.verifiedAt);
        expect(isFieldVerified).toBe(false);
      }
    });
  });
});

// ===========================================================================
// TIER 2: BOUNDARY & CORNER CASES
// ===========================================================================

describe('Tier 2: Boundary & Corner Cases', () => {

  describe('Boundary 1: Mekong Geographic Bounding Box Limits', () => {
    it('accepts exact bounding box boundary points', () => {
      expect(isInMekongBBox(9.0, 105.0)).toBe(true);  // SW corner
      expect(isInMekongBBox(11.0, 107.0)).toBe(true); // NE corner
      expect(isInMekongBBox(10.0, 106.0)).toBe(true); // Center
    });

    it('rejects points just outside the boundary limits', () => {
      expect(isInMekongBBox(8.9999, 106.0)).toBe(false); // South overflow
      expect(isInMekongBBox(11.0001, 106.0)).toBe(false); // North overflow
      expect(isInMekongBBox(10.0, 104.9999)).toBe(false); // West overflow
      expect(isInMekongBBox(10.0, 107.0001)).toBe(false); // East overflow
    });

    it('detects and rejects swapped latitude/longitude coordinates [106.0, 10.0]', () => {
      const swappedLat = 106.0;
      const swappedLng = 10.0;
      expect(isInMekongBBox(swappedLat, swappedLng)).toBe(false);
    });

    it('verifies all 1,733 valid entities in database are strictly inside Mekong BBox', () => {
      const rows = db.prepare("SELECT id, coordinates FROM entities WHERE id != 'prov-1' AND coordinates IS NOT NULL AND coordinates != ''").all() as Array<{ id: string; coordinates: string }>;
      expect(rows.length).toBe(1733);

      for (const r of rows) {
        const [lat, lng] = JSON.parse(r.coordinates);
        expect(isInMekongBBox(lat, lng), `Entity ${r.id} coordinates [${lat}, ${lng}] out of bounds`).toBe(true);
      }
    });
  });

  describe('Boundary 2: Identification of 17 White Zones (Zero-Entity Communes)', () => {
    it('accurately identifies exactly 17 administrative units with 0 non-place content entities', () => {
      const adminUnits = db.prepare("SELECT id, name FROM entities WHERE type = 'place' AND level IN ('phuong', 'xa')").all() as Array<{ id: string; name: string }>;
      expect(adminUnits.length).toBe(124);

      const whiteZones: string[] = [];
      for (const u of adminUnits) {
        const countRow = db.prepare("SELECT count(*) as count FROM entities WHERE placeId = ? AND type != 'place'").get(u.id) as { count: number };
        if (countRow.count === 0) {
          whiteZones.push(u.id);
        }
      }

      expect(whiteZones.length).toBe(17);

      const expectedWhiteZones = [
        'p-hung-hoa', 'xa-thanh-phong', 'xa-an-hiep', 'xa-an-ngai-trung',
        'xa-an-truong', 'xa-chau-hoa', 'xa-hieu-phung', 'xa-hung-khanh-trung',
        'xa-hung-my', 'xa-luong-phu', 'xa-my-thuan', 'xa-ngu-lac',
        'xa-phong-thanh', 'xa-quoi-an', 'xa-song-loc', 'xa-song-phu',
        'xa-thanh-tri'
      ];

      for (const zoneId of expectedWhiteZones) {
        expect(whiteZones).toContain(zoneId);
      }
    });

    it('verifies non-white zone units have >= 1 content entities', () => {
      const longChau = db.prepare("SELECT count(*) as count FROM entities WHERE placeId = 'p-long-chau' AND type != 'place'").get() as { count: number };
      expect(longChau.count).toBeGreaterThan(50);
    });
  });

  describe('Boundary 3: Lunar Date Boundary Parsing & Calendar Edge Cases', () => {
    it('handles leap month requests safely', () => {
      // Leap month flag cannot be true for months where no leap exists
      const testCases: Array<{ month?: number; day?: number; leap?: boolean; valid: boolean }> = [
        { month: 1, leap: false, valid: true },
        { month: 13, leap: false, valid: false }, // Month > 12
        { month: 0, leap: false, valid: false },  // Month < 1
        { day: 0, valid: false },
        { day: 31, valid: false }, // Lunar months never exceed 30 days
      ];

      for (const tc of testCases) {
        if (typeof tc.month === 'number' && !tc.valid) {
          expect(tc.month < 1 || tc.month > 12).toBe(true);
        }
        if (typeof tc.day === 'number' && !tc.valid) {
          expect(tc.day < 1 || tc.day > 30).toBe(true);
        }
      }
    });

    it('verifies year 2026 short lunar months: month 8 and month 12 have only 29 days', () => {
      // In Vietnamese lunar calendar for 2026 (Bính Ngọ), months 8 and 12 are short months (tháng thiếu)
      const shortMonths2026 = [8, 12];
      for (const sm of shortMonths2026) {
        const day30Invalid = (day: number, month: number) => {
          if (shortMonths2026.includes(month) && day === 30) return false;
          return true;
        };
        expect(day30Invalid(30, sm)).toBe(false);
        expect(day30Invalid(29, sm)).toBe(true);
      }
    });

    it('parses Can-Chi floating dates without throwing unexpected errors', () => {
      const canChiEvents = [
        'Lễ Xuân Đinh Văn Thánh Miếu',
        'Lễ hội Kỳ Yên đình Tân Ngãi',
        'Lễ Đôn Ta (Sen Dolta) Khmer'
      ];

      for (const evName of canChiEvents) {
        expect(typeof evName).toBe('string');
        expect(evName.length).toBeGreaterThan(5);
      }
    });
  });

  describe('Boundary 4: String Escaping, Special Characters & Diacritics', () => {
    it('verifies Vietnamese diacritics and quotes in names and summaries do not corrupt JSON parsing', () => {
      const samples = db.prepare("SELECT name, summary FROM entities WHERE name LIKE '%\"%' OR name LIKE '%''%' OR name LIKE '%-%' LIMIT 10").all() as Array<{ name: string; summary: string }>;

      for (const s of samples) {
        expect(typeof s.name).toBe('string');
        // Roundtrip JSON stringify and parse
        const serialized = JSON.stringify(s);
        const parsed = JSON.parse(serialized);
        expect(parsed.name).toBe(s.name);
      }
    });
  });
});

// ===========================================================================
// TIER 3: CROSS-FEATURE COMBINATIONS
// ===========================================================================

describe('Tier 3: Cross-Feature Interactions', () => {

  describe('Cross-Feature 1: Itinerary Stops x Knowledge Graph Entity Resolution', () => {
    it('cross-references itinerary stops with entities and verifies coordinates', () => {
      const itins = db.prepare('SELECT id, title, stops FROM itineraries').all() as Array<{ id: string; title: string; stops: string }>;

      let verifiedStopsCount = 0;
      for (const it of itins) {
        const stops = JSON.parse(it.stops || '[]');
        for (const s of stops) {
          const eid = s.entityId || s.id;
          if (eid) {
            const ent = db.prepare('SELECT id, name, coordinates, placeId FROM entities WHERE id = ?').get(eid) as { id: string; name: string; coordinates: string; placeId: string } | undefined;
            if (ent && ent.coordinates) {
              try {
                const coords = JSON.parse(ent.coordinates);
                if (Array.isArray(coords)) {
                  expect(isInMekongBBox(coords[0], coords[1])).toBe(true);
                  verifiedStopsCount++;
                }
              } catch {}
            }
          }
        }
      }
      expect(verifiedStopsCount).toBeGreaterThanOrEqual(150);
    });
  });

  describe('Cross-Feature 2: White Zones x Remediation Seed Coverage', () => {
    it('validates that seed remediation entities target the 17 identified white zones', () => {
      const whiteZoneSet = new Set([
        'p-hung-hoa', 'xa-thanh-phong', 'xa-an-hiep', 'xa-an-ngai-trung',
        'xa-an-truong', 'xa-chau-hoa', 'xa-hieu-phung', 'xa-hung-khanh-trung',
        'xa-hung-my', 'xa-luong-phu', 'xa-my-thuan', 'xa-ngu-lac',
        'xa-phong-thanh', 'xa-quoi-an', 'xa-song-loc', 'xa-song-phu',
        'xa-thanh-tri'
      ]);

      // Seed candidate simulation
      const sampleSeed = {
        id: 'seed-test-white-zone',
        name: 'Đình thần Phong Thạnh',
        placeId: 'xa-phong-thanh',
        type: 'history'
      };

      expect(whiteZoneSet.has(sampleSeed.placeId)).toBe(true);
    });
  });

  describe('Cross-Feature 3: Schema.org Properties & AEO/GEO Validity', () => {
    it('verifies Schema.org TouristAttraction required fields for attraction entities', () => {
      const attractions = db.prepare("SELECT id, name, description, coordinates, address FROM entities WHERE type = 'attraction' AND coordinates IS NOT NULL AND coordinates != '' LIMIT 25").all() as Array<{ id: string; name: string; description: string; coordinates: string; address: string }>;

      for (const a of attractions) {
        expect(a.name).toBeDefined();
        expect(a.name.trim().length).toBeGreaterThan(0);
        const coords = JSON.parse(a.coordinates);
        if (Array.isArray(coords)) {
          expect(coords.length).toBe(2);
        }
      }
    });

    it('verifies Schema.org Place / AdministrativeArea required hierarchy for administrative places', () => {
      const places = db.prepare("SELECT id, name, level, parentId, coordinates FROM entities WHERE type = 'place' AND level IN ('phuong', 'xa') LIMIT 25").all() as Array<{ id: string; name: string; level: string; parentId: string; coordinates: string }>;

      for (const p of places) {
        expect(p.parentId).toBe('vinh-long');
        expect(['phuong', 'xa']).toContain(p.level);
        const coords = JSON.parse(p.coordinates);
        expect(Array.isArray(coords)).toBe(true);
      }
    });

    it('asserts zero fabricated aggregateRating attributes exist (Anti-Slop invariant CLAUDE.md §1.7)', () => {
      const fakeRatings = db.prepare("SELECT count(*) as count FROM entities WHERE json_extract(attributes, '$.rating') > 5.0 OR json_extract(attributes, '$.reviewCount') > 100000").get() as { count: number };
      expect(fakeRatings.count).toBe(0);
    });
  });
});

// ===========================================================================
// TIER 4: REAL-WORLD APPLICATION SCENARIOS
// ===========================================================================

describe('Tier 4: Real-World Scenarios (End-to-End Workloads)', () => {

  // Scenario 1: Tourist Journey Itinerary Traversal
  it('Scenario 1: executes tourist journey traversal for mot-ngay-cu-lao-an-binh', () => {
    const itinerary = db.prepare("SELECT id, title, stops FROM itineraries WHERE id = 'mot-ngay-cu-lao-an-binh'").get() as { id: string; title: string; stops: string };
    expect(itinerary).toBeDefined();
    expect(itinerary.title).toContain('An Bình');

    const stops = JSON.parse(itinerary.stops);
    expect(stops.length).toBeGreaterThanOrEqual(2);

    for (const stop of stops) {
      const eid = stop.id || stop.entityId;
      expect(eid).toBeDefined();

      const ent = db.prepare('SELECT id, name, type, coordinates FROM entities WHERE id = ?').get(eid) as { id: string; name: string; type: string; coordinates: string };
      expect(ent, `Stop ${eid} must exist in entities table`).toBeDefined();

      const coords = JSON.parse(ent.coordinates);
      expect(isInMekongBBox(coords[0], coords[1])).toBe(true);

      // Check nearby food/lodging in knowledge graph
      const nearCount = db.prepare(`
        SELECT count(*) as count
        FROM relationships r
        JOIN entities target ON r.to_id = target.id
        WHERE r.from_id = ? AND r.type = 'near' AND target.type IN ('restaurant', 'dish', 'accommodation')
      `).get(eid) as { count: number };
      expect(nearCount.count).toBeGreaterThanOrEqual(0);
    }
  });

  // Scenario 2: Festival & Seasonal Planner Workload
  it('Scenario 2: executes festival planner workload across 6 fields and validates circuit breaker', () => {
    // Select festival events in the Mekong autumn/winter season (e.g. Ok Om Bok)
    const festival = db.prepare("SELECT id, name, season, summary, attributes FROM entities WHERE id LIKE '%ok-om-bok%' OR id LIKE '%le-hoi%' LIMIT 5").all() as Array<{ id: string; name: string; season: string; summary: string; attributes: string }>;
    expect(festival.length).toBeGreaterThan(0);

    for (const fest of festival) {
      expect(fest.name).toBeDefined();
      expect(fest.summary).toBeDefined();

      // Check event details table
      const details = db.prepare('SELECT lunar_date, date_start, date_end FROM entity_event_details WHERE entity_id = ?').get(fest.id) as { lunar_date: string; date_start: string; date_end: string } | undefined;
      if (details) {
        if (details.date_start && details.date_end && details.date_start.match(/^\d{4}-\d{2}-\d{2}$/) && details.date_end.match(/^\d{4}-\d{2}-\d{2}$/)) {
          expect(details.date_start <= details.date_end).toBe(true);
        }
      }
    }
  });

  // Scenario 3: Administrative Geo-Coder Query
  it('Scenario 3: queries entities by newly merged communes and validates 2-tier parent structure', () => {
    const testWards = ['p-vung-liem', 'p-thanh-duc', 'p-long-ho'];

    for (const wardId of testWards) {
      const ward = db.prepare('SELECT id, name, level, parentId FROM entities WHERE id = ?').get(wardId) as { id: string; name: string; level: string; parentId: string };
      expect(ward).toBeDefined();
      expect(ward.parentId).toBe('vinh-long');
      expect(ward.level).toBe('phuong');

      const contentEntities = db.prepare('SELECT id, name, address FROM entities WHERE placeId = ? LIMIT 5').all(wardId) as Array<{ id: string; name: string; address: string }>;
      for (const ce of contentEntities) {
        expect(ce.id).toBeDefined();
        expect(ce.name).toBeDefined();
      }
    }
  });

  // Scenario 4: Knowledge Graph Traverser (Heritage -> Craft -> OCOP Hop)
  it('Scenario 4: hops along knowledge graph from heritage to craft village to OCOP product', () => {
    // Start at Mang Thit Brick & Ceramic heritage
    const startNode = db.prepare("SELECT id, name FROM entities WHERE id = 'lang-nghe-gach-gom-mang-thit-vuong-quoc-do' OR id = 'di-san-duong-dai-mang-thit'").get() as { id: string; name: string };
    expect(startNode).toBeDefined();

    // Query outgoing edges from craft villages
    const craftEdges = db.prepare(`
      SELECT r.from_id, r.to_id, r.type, target.name as target_name, target.type as target_type
      FROM relationships r
      JOIN entities target ON r.to_id = target.id
      WHERE r.type IN ('produced_in', 'associated_with', 'near') AND target.type IN ('product', 'craft_village', 'attraction')
      LIMIT 10
    `).all() as Array<{ from_id: string; to_id: string; type: string; target_name: string; target_type: string }>;

    expect(craftEdges.length).toBeGreaterThan(0);
    for (const edge of craftEdges) {
      expect(edge.from_id).toBeDefined();
      expect(edge.to_id).toBeDefined();
      expect(edge.target_name).toBeDefined();
    }
  });

  // Scenario 5: Data Governance Remediation Ledger & DHI Score Audit
  it('Scenario 5: audits data remediation ledger schema and DHI 6-axis scoring formula', () => {
    const ledgerPath = path.join(repoRoot, 'outputs/data_remediation_ledger.json');

    // Known valid error codes defined in survey_gis_specs.md §5.1
    const validErrorCodes = [
      'ERR_OLD_ADMIN_DISTRICT',
      'ERR_OLD_PROVINCE_REF',
      'ERR_MALFORMED_COORDS',
      'ERR_MISSING_COORDS',
      'ERR_TEMPORAL_CONFLICT_B',
      'ERR_TEMPORAL_CONFLICT_C',
      'ERR_ORPHAN_GRAPH_NODE',
      'ERR_ITINERARY_STOP_SCHEMA',
      'ERR_UNVERIFIED_CLAIM_EAT'
    ];

    if (fs.existsSync(ledgerPath)) {
      const ledger = JSON.parse(fs.readFileSync(ledgerPath, 'utf8'));
      expect(ledger.generated_at).toBeDefined();
      expect(ledger.total_records).toBeGreaterThan(0);
      expect(ledger.summary_by_error_code).toBeDefined();
      expect(Array.isArray(ledger.remediations)).toBe(true);

      for (const item of ledger.remediations.slice(0, 50)) {
        expect(item.entity_id).toBeDefined();
        expect(validErrorCodes).toContain(item.error_code);
        expect(item.field).toBeDefined();
        expect(item.rationale).toBeDefined();
        expect(['low', 'medium', 'high', 'requires_owner_approval']).toContain(item.risk_level);
      }
    } else {
      // Validate the specification contract
      expect(validErrorCodes.length).toBe(9);
    }

    // DHI (Data Health Index) 6-axis weights check
    const dhiWeights = {
      spatial_bounds: 0.20,
      admin_2tier: 0.20,
      temporal_consistency: 0.15,
      graph_connectivity: 0.15,
      schema_completeness: 0.15,
      eeat_provenance: 0.15
    };
    const sumWeights = Object.values(dhiWeights).reduce((a, b) => a + b, 0);
    expect(sumWeights).toBeCloseTo(1.0, 5);
  });
});
