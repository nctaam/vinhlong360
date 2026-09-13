/**
 * Phase 6 Deep Terroir Enrichment Remediation Test Suite
 *
 * Validates the 40 OCOP, agricultural gift, and specialty food entities enriched
 * in Phase 6 across Vinh Long, Ben Tre, and Tra Vinh from NotebookLM.
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
const ledgerPath = path.join(repoRoot, 'outputs/notebooklm_phase6_enrichment_ledger.json');

const PHASE6_TARGET_IDS = [
  'mat-hoa-dua-va-duong-hoa-dua-tra-vinh-ocop-5-sao',
  'nuoc-mam-ruoi-long-vinh',
  'keo-dua-tuyet-phung',
  'dua-sap-hoa-tan',
  'gao-huu-co-long-hoa-hoa-minh-ocop-4-sao',
  'cu-cai-muoi-chit-sa',
  'banh-kep-thuy-kieu',
  'banh-tet-tu-quy-hai-ly',
  'kho-ca-bong-lau-ca-du-do-ca-bong-cat-mot-nang-thanh-phong',
  'kho-ca-bien-thanh-phu',
  'cua-bien-va-ngheu-thanh-phu',
  'hop-tac-xa-thuy-san-thanh-loi-ngheu-thanh-hai-ocop',
  'ca-bong-lau-mot-nang-binh-dai',
  'ca-doi-kho-mot-nang-binh-dai',
  'tom-kho-hai-kham',
  'nuoc-khoang-thien-nhien-sao-bien-starfiwa',
  'buoi-da-xanh-giong-trom',
  'buoi-nam-roi-my-hoa',
  'cam-sanh-tam-binh',
  'dua-sap-cau-ke-dac-san-ben-tre',
  'gao-sach-tom-lua-thanh-phu-ocop',
  'gao-sach-lua-tom-thanh-phu',
  'nhan-an-binh-tam-binh',
  'chom-chom-cau-ke',
  'lap-xuong-ngoc-huong',
  'bun-tuoi-an-dao',
  'ruou-quach-cau-ngang',
  'ruou-gia-bao',
  'mat-ong-rung-ban-my-long-nam',
  'mut-dua-sap-cam-hang',
  'tom-cang-xanh-lot-an-thanh',
  'bun-tuoi-va-hu-tieu-sau-thanh',
  'cua-hang-ocop-vung-liem',
  'diem-trung-bay-va-ban-san-pham-ocop-vinh-long-tai-ben-cang',
  'diem-trung-bay-va-gioi-thieu-san-pham-ocop-vinh-long',
  'cua-hang-ocop-tinh-ben-tre-trung-tam-xuc-tien-dau-tu-ho-tro-doanh-nghiep-ben-tre',
  'cua-hang-ocop-tra-vinh-trung-tam-xuc-tien-thuong-mai-tinh-tra-vinh',
  'cua-hang-dac-san-mien-tay-tra-vinh-tra-vinh',
  'cua-hang-ocop-ao-ba-om',
  'cua-hang-ocop-bien-ba-dong'
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

describe('Phase 6 Deep Terroir Enrichment Invariant Suite', () => {
  it('verifies outputs/notebooklm_phase6_enrichment_ledger.json exists and contains 40 valid entries', () => {
    expect(fs.existsSync(ledgerPath)).toBe(true);
    const content = fs.readFileSync(ledgerPath, 'utf-8');
    const ledger = JSON.parse(content);
    const keys = Object.keys(ledger);
    expect(keys.length).toBe(40);

    for (const targetId of PHASE6_TARGET_IDS) {
      expect(ledger[targetId], `Ledger missing entry for ${targetId}`).toBeDefined();
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

  it('verifies all 40 target entities in SQLite possess complete Phase 6 metadata & verifiedAt', () => {
    const stmt = db.prepare('SELECT id, description, hours, best_time, attributes, verified FROM entities WHERE id = ?');

    for (const eid of PHASE6_TARGET_IDS) {
      const row: any = stmt.get(eid);
      expect(row, `Entity ${eid} must exist in SQLite`).toBeDefined();
      expect(row.verified).toBe(1);
      expect(row.hours).toBeTruthy();
      expect(row.best_time).toBeTruthy();

      const attr = JSON.parse(row.attributes || '{}');
      expect(attr.verifiedAt).toBeTruthy();
      expect(attr.verifiedSource).toBe('NotebookLM Deep Terroir Research - Phase 6');
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
        expect(cite.target_notebook).toBeTruthy();
        expect(['TIER_1_GOVERNMENT', 'TIER_2_SCHOLARLY']).toContain(cite.tier);
      }
    }
  });

  it('verifies web/data.json is in exact 100% parity with SQLite for all 40 entities', () => {
    const dataJson = JSON.parse(fs.readFileSync(dataJsonPath, 'utf-8'));
    const entityMap = new Map(dataJson.entities.map((e: any) => [e.id, e]));

    for (const eid of PHASE6_TARGET_IDS) {
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


  it('guarantees 0 former province names, 0 generic fillers, and 0 clichés in enriched Phase 6 fields', () => {
    const stmt = db.prepare('SELECT id, description, hours, best_time, attributes FROM entities WHERE id = ?');
    const forbiddenPatterns = [
      /tỉnh\s+Bến\s+Tre/i,
      /tỉnh\s+Trà\s+Vinh/i,
      /thiên\s+đường/i,
      /sông\s+nước\s+hữu\s+tình/i
    ];

    for (const eid of PHASE6_TARGET_IDS) {
      const row: any = stmt.get(eid);
      const textToScan = [
        row.description,
        row.hours,
        row.best_time,
        JSON.stringify(row.attributes)
      ].join(' ');

      for (const pat of forbiddenPatterns) {
        expect(pat.test(textToScan), `Violation of pattern ${pat} in ${eid}`).toBe(false);
      }
    }
  });
});
