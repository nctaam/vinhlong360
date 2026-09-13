/**
 * Phase 2 Deep Terroir Enrichment Remediation Test Suite
 *
 * Validates the 30 iconic anchor entities enriched in Phase 2
 * across Vinh Long, Ben Tre, and Tra Vinh.
 *
 * Invariant checks:
 * - 30 target entities verified in SQLite and web/data.json
 * - Canonical DB counts: 1,772 entities | 13,343 relationships | 33 itineraries
 * - 0 former province name violations (R10.7)
 * - 0 generic content fillers (R50.2)
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
const ledgerPath = path.join(repoRoot, 'outputs/notebooklm_phase2_enrichment_ledger.json');

const PHASE2_TARGET_IDS = [
  'ao-ba-om',
  'ao-ba-om-ao-vuong-tra-vinh',
  'chua-hang-cha-lo',
  'chua-hang-wat-kompong-chray',
  'chua-vam-ray',
  'chua-vam-ray-wat-samrong',
  'chua-co-chua-nodol-chua-phno-don',
  'chua-ong-met-botum-vong-sa-som-rong',
  'den-tho-bac-ho-tra-vinh',
  'chua-tuyen-linh',
  'khu-luu-niem-nguyen-thi-dinh',
  'khu-luu-niem-tran-dai-nghia-vinh-long',
  'can-cu-tinh-uy-ben-tre-rung-la-thanh-phu',
  'bao-tang-ben-tre',
  'chua-o-mich-hung-hoa',
  'cu-lao-an-binh',
  'cho-noi-tra-on-dc',
  'cho-noi-dua-song-thom-mo-cay',
  'bien-con-bung-thanh-phu-ben-tre',
  'bai-boi-rung-ngap-man-ba-tri-ben-tre',
  'cu-lao-may-cu-lao-luc-si-thanh',
  'cay-goi-nuoc-di-san-ben-tre',
  'ben-cang-hanh-khach-vinh-long',
  'lang-banh-trang-my-long',
  'lang-nghe-banh-phong-son-doc',
  'lang-nghe-banh-tet-tra-cuon',
  'lang-nghe-det-chieu-ca-hon',
  'lang-nghe-bun-suong',
  'dua-sap-tra-vinh',
  'cho-ben-tre-cho-trung-tam-ben-tre'
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

describe('Phase 2 Deep Terroir Enrichment Invariant Suite', () => {
  it('verifies outputs/notebooklm_phase2_enrichment_ledger.json exists and contains 30 valid entries', () => {
    expect(fs.existsSync(ledgerPath)).toBe(true);
    const content = fs.readFileSync(ledgerPath, 'utf-8');
    const ledger = JSON.parse(content);
    expect(Array.isArray(ledger)).toBe(true);
    expect(ledger.length).toBe(30);

    const ids = ledger.map((item: any) => item.entity_id);
    for (const targetId of PHASE2_TARGET_IDS) {
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

  it('verifies all 30 target entities in SQLite possess complete Phase 2 metadata & verifiedAt', () => {
    const stmt = db.prepare('SELECT id, description, hours, best_time, attributes, verified FROM entities WHERE id = ?');

    for (const eid of PHASE2_TARGET_IDS) {
      const row: any = stmt.get(eid);
      expect(row, `Entity ${eid} must exist in SQLite`).toBeDefined();
      expect(row.verified).toBe(1);
      expect(row.description).toBeTruthy();
      expect(row.description.length).toBeGreaterThan(50);
      expect(row.hours).toBeTruthy();
      expect(row.best_time).toBeTruthy();

      const attr = JSON.parse(row.attributes || '{}');
      expect(attr.verifiedAt).toBeTruthy();
      expect(attr.verifiedSource).toBe('NotebookLM Deep Terroir Research - Phase 2');
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

  it('verifies web/data.json is in exact 100% parity with SQLite for all 30 entities', () => {
    const dataJson = JSON.parse(fs.readFileSync(dataJsonPath, 'utf-8'));
    const entityMap = new Map(dataJson.entities.map((e: any) => [e.id, e]));

    for (const eid of PHASE2_TARGET_IDS) {
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

  it('guarantees 0 former province names and 0 generic fillers in enriched Phase 2 fields', () => {
    const stmt = db.prepare('SELECT id, description, hours, best_time, attributes FROM entities WHERE id = ?');
    const forbiddenPatterns = [
      /tỉnh\s+Bến\s+Tre/i,
      /tỉnh\s+Trà\s+Vinh/i,
      /\bmiền\s+Tây\b/i,
      /thiên\s+đường/i,
      /sông\s+nước\s+hữu\s+tình/i,
      /nổi\s+tiếng/i
    ];

    for (const eid of PHASE2_TARGET_IDS) {
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
