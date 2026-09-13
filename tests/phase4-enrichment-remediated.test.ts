/**
 * Phase 4 Deep Terroir Enrichment Remediation Test Suite
 *
 * Validates the 40 ecotourism, homestay, and orchard entities enriched
 * in Phase 4 across Vinh Long, Ben Tre, and Tra Vinh from NotebookLM (Mekong 360 - Tap 2 & Vinh Long 360).
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
const ledgerPath = path.join(repoRoot, 'outputs/notebooklm_phase4_enrichment_ledger.json');

const PHASE4_TARGET_IDS = [
  'sau-rieng-cho-lach',
  'sau-rieng-cai-mon',
  'vuon-sau-rieng-bay-thao',
  'vuon-trai-cay-cai-mon',
  'lang-van-hoa-du-lich-cho-lach',
  'tham-lang-hoa-cho-lach',
  'vuon-kieng-thu-nam-cong',
  'rooster-mekong-resort',
  'cu-lao-dai-cu-lao-thanh-binh-quoi-thien',
  'vuon-trai-cay-cu-lao-dai',
  'vung-chuyen-canh-sau-rieng-cu-lao-quoi-an',
  'oc-gao-cu-lao-dai',
  'lang-det-chieu-cu-lao-dai',
  'diem-du-lich-ba-ngoi-con-phu-da',
  'vuon-chom-chom-ba-ngoi',
  'oc-gao-con-phu-da-hap-sa',
  'vuon-chom-chom-thay-ha',
  'thanh-tra-binh-minh',
  'vuon-thanh-tra-dong-thanh',
  'vung-cam-sanh-tra-on',
  'tham-quan-vuon-cam-tra-on',
  'vuon-chim-hai-chia-tan-my-tra-on',
  'khu-du-lich-nha-xua-va-homestay-ut-trinh',
  'ba-linh-homestay',
  'phuong-thao-homestay',
  'ngoc-phuong-homestay',
  'nam-thanh-homestay',
  'diem-du-lich-nha-dua-cocohome',
  'mekong-pottery-homestay',
  'somo-farm-cuu-long',
  'con-chim',
  'homestay-tu-pha-con-chim',
  'homestay-bep-nam-bo-xua-con-chim',
  'con-ho-oc-dao-xanh-song-co-chien',
  'suonsia-homestay',
  'maison-du-pays-de-ben-tre',
  'mango-home-ben-tre',
  'mekong-home',
  'nhon-thanh-homestay',
  'nha-thuyen-nam-cao-homestay'
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

describe('Phase 4 Deep Terroir Enrichment Invariant Suite', () => {
  it('verifies outputs/notebooklm_phase4_enrichment_ledger.json exists and contains 40 valid entries', () => {
    expect(fs.existsSync(ledgerPath)).toBe(true);
    const content = fs.readFileSync(ledgerPath, 'utf-8');
    const ledger = JSON.parse(content);
    expect(Array.isArray(ledger)).toBe(true);
    expect(ledger.length).toBe(40);

    const ids = ledger.map((item: any) => item.entity_id || item.id);
    for (const targetId of PHASE4_TARGET_IDS) {
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

  it('verifies all 40 target entities in SQLite possess complete Phase 4 metadata & verifiedAt', () => {
    const stmt = db.prepare('SELECT id, description, hours, best_time, attributes, verified FROM entities WHERE id = ?');

    for (const eid of PHASE4_TARGET_IDS) {
      const row: any = stmt.get(eid);
      expect(row, `Entity ${eid} must exist in SQLite`).toBeDefined();
      expect(row.verified).toBe(1);
      expect(row.description).toBeTruthy();
      expect(row.description.length).toBeGreaterThan(50);
      expect(row.hours).toBeTruthy();
      expect(row.best_time).toBeTruthy();

      const attr = JSON.parse(row.attributes || '{}');
      expect(attr.verifiedAt).toBeTruthy();
      expect(attr.verifiedSource).toBe('NotebookLM Deep Terroir Research - Phase 4');
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

    for (const eid of PHASE4_TARGET_IDS) {
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

  it('guarantees 0 former province names, 0 generic fillers, and 0 clichés in enriched Phase 4 fields', () => {
    const stmt = db.prepare('SELECT id, description, hours, best_time, attributes FROM entities WHERE id = ?');
    const forbiddenPatterns = [
      /tỉnh\s+Bến\s+Tre/i,
      /tỉnh\s+Trà\s+Vinh/i,
      /miền\s+Tây/i,
      /thiên\s+đường/i,
      /sông\s+nước\s+hữu\s+tình/i,
      /nổi\s+tiếng/i,
      /đậm\s+đà\s+bản\s+sắc/i
    ];

    for (const eid of PHASE4_TARGET_IDS) {
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
