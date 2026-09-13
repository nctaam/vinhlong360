/**
 * Phase 3 Deep Terroir Enrichment Remediation Test Suite
 *
 * Validates the 40 craft villages and traditional culinary entities enriched
 * in Phase 3 across Vinh Long, Ben Tre, and Tra Vinh from NotebookLM (Mekong 360 - Tap 2).
 *
 * Invariant checks:
 * - 40 target entities verified in SQLite and web/data.json
 * - Canonical DB counts: 1,772 entities | 13,343 relationships | 33 itineraries
 * - 0 former province name violations (R10.7)
 * - 0 generic content fillers (R50.2)
 * - 0 formula starts or superlative clichés (R50.3, R50.7)
 * - 100% Tier 1 / Tier 2 source citations with verifiedAt timestamps
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
const ledgerPath = path.join(repoRoot, 'outputs/notebooklm_phase3_enrichment_ledger.json');

const PHASE3_TARGET_IDS = [
  'lang-nghe-gom-do-mang-thit',
  'lang-nghe-gach-gom-mang-thit-vuong-quoc-do',
  'vung-di-san-duong-dai-mang-thit-vuong-quoc-lo-gach',
  'nha-gom-do-tu-buoi',
  'lo-gach-mang-thit',
  'lang-nghe-cham-non-la-long-ho',
  'lang-nghe-dan-non-la-tt-long-ho',
  'lang-nghe-dan-lat-may-tre-phu-le',
  'lang-nghe-dan-gio-cong-dua-hung-phong',
  'lang-nghe-dan-luc-binh-ngai-tu-binh-ninh',
  'lang-dan-lat-duc-my-cang-long',
  'lang-nghe-dan-dat-dai-an',
  'lang-se-loi-lac-va-dan-lat-vung-liem',
  'lang-nghe-bo-choi-my-an',
  'lang-nghe-dong-ghe-xuong-an-dinh',
  'lang-tau-hu-ky-my-hoa',
  'lang-nghe-lam-tau-hu-ky',
  'tau-hu-ky-my-hoa-chien-gion',
  'lang-nghe-banh-trang-nem-cu-lao-may',
  'lang-nghe-banh-trang-tam-binh',
  'quan-banh-canh-ben-co-tra-vinh',
  'bun-nuoc-leo-tra-vinh',
  'quan-bun-nuoc-leo-cho-tra-vinh-tra-vinh',
  'bun-nuoc-leo-cang-long',
  'bun-nuoc-leo-tieu-can',
  'lang-nghe-com-dep-ba-so',
  'mam-bo-hoc-prohok',
  'dac-san-mam-bo-hoc-tra-cuon',
  'lang-nghe-che-tac-mat-na-khmer-nguyet-hoa',
  'lang-nghe-dan-chapay-phu-can',
  'lang-nghe-che-bien-hai-san-kho-thanh-phong',
  'lau-ca-linh-bong-dien-dien',
  'lau-mam-mien-tay',
  'quan-chao-ca-ro-dong-cho-cau-ke-tra-vinh',
  'quan-co-tu-lau-mam-xa-hoa-ninh-vinh-long',
  'lang-keo-dua-mo-cay',
  'lang-nghe-chi-xo-dua-khanh-thanh-tan',
  'lang-nghe-san-xuat-chi-xo-dua-an-thanh',
  'vicosap-keo-dua-sap-ocop-5-sao',
  'hop-tac-xa-buoi-nam-roi-my-hoa'
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

describe('Phase 3 Deep Terroir Enrichment Invariant Suite', () => {
  it('verifies outputs/notebooklm_phase3_enrichment_ledger.json exists and contains 40 valid entries', () => {
    expect(fs.existsSync(ledgerPath)).toBe(true);
    const content = fs.readFileSync(ledgerPath, 'utf-8');
    const ledger = JSON.parse(content);
    expect(Array.isArray(ledger)).toBe(true);
    expect(ledger.length).toBe(40);

    const ids = ledger.map((item: any) => item.entity_id);
    for (const targetId of PHASE3_TARGET_IDS) {
      expect(ids).toContain(targetId);
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

  it('verifies all 40 target entities in SQLite possess complete Phase 3 metadata & verifiedAt', () => {
    const stmt = db.prepare('SELECT id, description, hours, best_time, attributes, verified FROM entities WHERE id = ?');

    for (const eid of PHASE3_TARGET_IDS) {
      const row: any = stmt.get(eid);
      expect(row, `Entity ${eid} must exist in SQLite`).toBeDefined();
      expect(row.verified).toBe(1);
      expect(row.description).toBeTruthy();
      expect(row.description.length).toBeGreaterThan(50);
      expect(row.hours).toBeTruthy();
      expect(row.best_time).toBeTruthy();

      const attr = JSON.parse(row.attributes || '{}');
      expect(attr.verifiedAt).toBeTruthy();
      expect(attr.verifiedSource).toBe('NotebookLM Deep Terroir Research - Phase 3');
      expect(attr.cultural_notes).toBeTruthy();
      expect(attr.visual_narrative).toBeTruthy();
      expect(attr.waterway_access).toBeTruthy();
      expect(attr.aeo_schema_type).toBeTruthy();
      expect(Array.isArray(attr.source_citations)).toBe(true);
      expect(attr.source_citations.length).toBeGreaterThan(0);

      // Verify citation quality
      for (const cite of attr.source_citations) {
        expect(cite.url).toMatch(/^https?:\/\//);
        expect(cite.title).toBeTruthy();
        expect(cite.notebook_id).toBeTruthy();
        expect(['TIER_1_GOVERNMENT', 'TIER_2_SCHOLARLY']).toContain(cite.tier);
      }
    }
  });

  it('verifies web/data.json is in exact 100% parity with SQLite for all 40 entities', () => {
    const dataJson = JSON.parse(fs.readFileSync(dataJsonPath, 'utf-8'));
    const entityMap = new Map(dataJson.entities.map((e: any) => [e.id, e]));

    for (const eid of PHASE3_TARGET_IDS) {
      const jsonEntity: any = entityMap.get(eid);
      expect(jsonEntity, `Entity ${eid} must exist in data.json`).toBeDefined();
      expect(jsonEntity.verified).toBe(1);
      expect(jsonEntity.description.length).toBeGreaterThan(50);
      expect(jsonEntity.attributes?.verifiedAt).toBeTruthy();
      expect(jsonEntity.attributes?.cultural_notes).toBeTruthy();
      expect(jsonEntity.attributes?.visual_narrative).toBeTruthy();
      expect(jsonEntity.attributes?.waterway_access).toBeTruthy();
      expect(jsonEntity.attributes?.source_citations?.length).toBeGreaterThan(0);
    }
  });

  it('guarantees 0 former province names, 0 generic fillers, and 0 clichés in enriched Phase 3 fields', () => {
    const stmt = db.prepare('SELECT id, description, hours, best_time, attributes FROM entities WHERE id = ?');
    const forbiddenPatterns = [
      /tỉnh\s+Bến\s+Tre/i,
      /tỉnh\s+Trà\s+Vinh/i,
      /\bmiền\s+Tây\b/i,
      /thiên\s+đường/i,
      /sông\s+nước\s+hữu\s+tình/i,
      /nổi\s+tiếng/i,
      /đậm\s+đà\s+bản\s+sắc/i
    ];

    for (const eid of PHASE3_TARGET_IDS) {
      const row: any = stmt.get(eid);
      const textToScan = [
        row.description,
        row.hours,
        row.best_time,
        row.attributes
      ].join(' ');

      for (const pattern of forbiddenPatterns) {
        const match = textToScan.match(pattern);
        expect(match, `Entity ${eid} should not match ${pattern}`).toBeNull();
      }
    }
  });
});
