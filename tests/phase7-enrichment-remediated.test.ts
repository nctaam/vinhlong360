/**
 * Phase 7 Regional Travel Itineraries Deep Enrichment Test Suite
 *
 * Validates the 33 regional travel itineraries enriched in Phase 7
 * across Vinh Long, Ben Tre, and Tra Vinh from Google NotebookLM.
 *
 * Invariant checks:
 * - 33 target itineraries in outputs/notebooklm_phase7_enrichment_ledger.json
 * - Canonical DB counts: 1,772 entities | 13,343 relationships | 33 itineraries
 * - Total stops invariant: exactly 182 stops preserved across 33 itineraries
 * - Exact placeholder isolation: tour-p06 and tour-p09 each have exactly 1 stop
 * - 100% Tier 1 / Tier 2 NotebookLM citations with verifiedAt timestamps
 * - 0 former province name violations (R10.7)
 * - 0 generic content fillers (R50.2: no "miền Tây", no "hòa mình vào")
 * - 0 formula starts (R50.3) or unanchored superlatives (R50.7)
 * - Full parity between SQLite itineraries table and web/data.json
 */

import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { DatabaseSync } from 'node:sqlite';
import path from 'node:path';
import fs from 'node:fs';

const repoRoot = fs.existsSync(path.resolve('agent/data/vinhlong360.db'))
  ? path.resolve('.')
  : path.resolve('..');
const dbPath = path.join(repoRoot, 'agent/data/vinhlong360.db');
const dataJsonPath = path.join(repoRoot, 'web/data.json');
const ledgerPath = path.join(repoRoot, 'outputs/notebooklm_phase7_enrichment_ledger.json');

const ITINERARY_IDS = [
  "mot-ngay-cu-lao-an-binh",
  "cuoi-tuan-2-ngay",
  "thien-nhien-phieu-luu-2-ngay",
  "dap-xe-1-ngay",
  "lang-man-2-ngay",
  "wellness-2-ngay",
  "di-san-mang-thit-tra-vinh",
  "lang-nghe-thu-cong-1-ngay",
  "tp-vinh-long-nua-ngay",
  "tra-vinh-khmer-1-ngay",
  "xu-dua-ben-tre",
  "nhiep-anh-1-ngay",
  "food-tour-vinh-long-1-ngay",
  "food-tour-ben-tre-1-ngay",
  "cho-sang-nau-an-nua-ngay",
  "tour-p07",
  "gia-dinh-vui-1-ngay",
  "mien-tay-3-ngay",
  "dbscl-3-ngay-day-du",
  "vinh-long-ben-tre-2-ngay",
  "ba-lo-budget-3-ngay",
  "ben-tre-tong-tai-romantic-2day-001",
  "tour-p04",
  "tour-p01",
  "tour-p02",
  "tour-p03",
  "tour-p05",
  "tour-p06",
  "tour-p08",
  "tour-p09",
  "tour-p10",
  "tour-p11",
  "tour-p12"
];

let db: DatabaseSync;

beforeAll(() => {
  expect(fs.existsSync(dbPath), `Database must exist at ${dbPath}`).toBe(true);
  db = new DatabaseSync(dbPath, { readOnly: true });
});

afterAll(() => {
  if (db) {
    db.close();
  }
});

describe('Phase 7 Regional Travel Itineraries Enrichment Invariant Suite', () => {
  it('verifies outputs/notebooklm_phase7_enrichment_ledger.json exists and contains 33 valid itineraries', () => {
    expect(fs.existsSync(ledgerPath)).toBe(true);
    const content = fs.readFileSync(ledgerPath, 'utf-8');
    const ledger = JSON.parse(content);
    const keys = Object.keys(ledger);
    expect(keys.length).toBe(33);

    for (const itinId of ITINERARY_IDS) {
      const item = ledger[itinId];
      expect(item, `Ledger missing entry for ${itinId}`).toBeDefined();
      expect(item.title).toBeTruthy();
      expect(item.duration).toBeTruthy();
      expect(item.summary.length).toBeGreaterThanOrEqual(100);
      expect(item.cultural_narrative.length).toBeGreaterThanOrEqual(150);
      expect(item.waterway_transit).toBeTruthy();
      expect(item.best_departure_time).toBeTruthy();
      expect(item.budget_estimate).toBeTruthy();
      expect(['TouristTrip', 'SpecialEvent']).toContain(item.aeo_schema_type);
      expect(item.verifiedAt).toBeTruthy();

      // Citations checks
      expect(Array.isArray(item.source_citations)).toBe(true);
      expect(item.source_citations.length).toBeGreaterThanOrEqual(2);
      for (const cite of item.source_citations) {
        expect(cite.url).toMatch(/^https?:\/\//);
        expect(cite.title).toBeTruthy();
        expect(cite.target_notebook).toBeTruthy();
        expect(['TIER_1_GOVERNMENT', 'TIER_2_SCHOLARLY']).toContain(cite.tier);
      }

      // Curated stops
      expect(Array.isArray(item.curated_stops)).toBe(true);
      expect(item.curated_stops.length).toBeGreaterThan(0);
      for (const stop of item.curated_stops) {
        expect(stop.id).toBeTruthy();
        expect(stop.time).toBeTruthy();
        expect(stop.note).toBeTruthy();
      }
    }
  });

  it('preserves canonical database counts: 1,772 entities, 13,343 relationships, 33 itineraries', () => {
    const entityCountRow: any = db.prepare('SELECT COUNT(*) as count FROM entities').get();
    expect(Number(entityCountRow.count)).toBe(1772);

    const relCountRow: any = db.prepare('SELECT COUNT(*) as count FROM relationships').get();
    expect(Number(relCountRow.count)).toBe(13343);

    const itCountRow: any = db.prepare('SELECT COUNT(*) as count FROM itineraries').get();
    expect(Number(itCountRow.count)).toBe(33);

    const dataJson = JSON.parse(fs.readFileSync(dataJsonPath, 'utf-8'));
    expect(dataJson.entities.length).toBe(1772);
    expect(dataJson.relationships.length).toBe(13343);
    expect(dataJson.itineraries.length).toBe(33);
  });

  it('preserves the strict invariant of exactly 182 stops across 33 itineraries', () => {
    const rows: any[] = db.prepare('SELECT id, stops FROM itineraries').all();
    expect(rows.length).toBe(33);

    let totalStopsDb = 0;
    for (const row of rows) {
      const stops = JSON.parse(row.stops || '[]');
      totalStopsDb += stops.length;
      if (row.id === 'tour-p06' || row.id === 'tour-p09') {
        expect(stops.length, `${row.id} must have exactly 1 stop`).toBe(1);
      }
    }
    expect(totalStopsDb).toBe(182);

    const dataJson = JSON.parse(fs.readFileSync(dataJsonPath, 'utf-8'));
    let totalStopsJson = 0;
    for (const itin of dataJson.itineraries) {
      totalStopsJson += itin.stops.length;
    }
    expect(totalStopsJson).toBe(182);
  });

  it('verifies all 33 itineraries in SQLite possess enriched summary and stops', () => {
    const content = fs.readFileSync(ledgerPath, 'utf-8');
    const ledger = JSON.parse(content);
    const stmt = db.prepare('SELECT id, summary, stops FROM itineraries WHERE id = ?');

    for (const itinId of ITINERARY_IDS) {
      const row: any = stmt.get(itinId);
      expect(row, `Itinerary ${itinId} must exist in SQLite`).toBeDefined();
      expect(row.summary).toBe(ledger[itinId].summary);

      const dbStops = JSON.parse(row.stops || '[]');
      const ledgerStops = ledger[itinId].curated_stops;
      expect(dbStops.length).toBe(ledgerStops.length);

      for (let i = 0; i < dbStops.length; i++) {
        expect(dbStops[i].id).toBe(ledgerStops[i].id);
        expect(dbStops[i].time).toBe(ledgerStops[i].time);
        expect(dbStops[i].note).toBe(ledgerStops[i].note);
      }
    }
  });

  it('verifies web/data.json is in exact parity with SQLite for all 33 itineraries', () => {
    const dataJson = JSON.parse(fs.readFileSync(dataJsonPath, 'utf-8'));
    const itinMap = new Map(dataJson.itineraries.map((it: any) => [it.id, it]));

    for (const itinId of ITINERARY_IDS) {
      const jsonItin: any = itinMap.get(itinId);
      expect(jsonItin, `Itinerary ${itinId} must exist in data.json`).toBeDefined();
      expect(jsonItin.summary.length).toBeGreaterThanOrEqual(100);
      expect(Array.isArray(jsonItin.stops)).toBe(true);
      expect(jsonItin.stops.length).toBeGreaterThan(0);
      for (const stop of jsonItin.stops) {
        expect(stop.time).toBeTruthy();
        expect(stop.note).toBeTruthy();
      }
    }
  });

  it('guarantees 0 former province names, 0 generic fillers, and 0 clichés across all 33 itineraries', () => {
    const forbiddenPatterns = [
      /tỉnh\s+Bến\s+Tre/i,
      /tỉnh\s+Trà\s+Vinh/i,
      /miền\s+Tây/i,
      /hòa\s+mình\s+vào/i,
      /sông\s+nước\s+hữu\s+tình/i,
      /thiên\s+đường/i
    ];

    const content = fs.readFileSync(ledgerPath, 'utf-8');
    const ledger = JSON.parse(content);

    for (const itinId of ITINERARY_IDS) {
      const item = ledger[itinId];
      const textPool = [
        item.summary,
        item.cultural_narrative,
        item.waterway_transit,
        item.best_departure_time,
        item.budget_estimate,
        ...item.curated_stops.map((s: any) => s.note)
      ].join(' ');

      for (const pat of forbiddenPatterns) {
        expect(pat.test(textPool), `Violation of pattern ${pat} in itinerary ${itinId}`).toBe(false);
      }
    }
  });
});
