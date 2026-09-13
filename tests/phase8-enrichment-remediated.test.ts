/**
 * Phase 8 Deep Terroir Enrichment Remediation Test Suite
 *
 * Validates the 36 waterway piers, ferry docks, interprovincial bus stations,
 * district bus stations, and transit bridge entities enriched in Phase 8
 * across Vinh Long, Ben Tre, and Tra Vinh from Google NotebookLM.
 *
 * Invariant checks:
 * - 36 target entities in outputs/notebooklm_phase8_enrichment_ledger.json
 * - Canonical DB counts: 1,772 entities | 13,343 relationships | 33 itineraries
 * - 100% Tier 1 / Tier 2 NotebookLM citations with verifiedAt timestamps
 * - 0 former province name violations (R10.7)
 * - 0 generic content fillers (R50.2: no "miền Tây", no "hòa mình vào")
 * - 0 formula starts (R50.3) or unanchored superlatives (R50.7)
 * - Full parity between SQLite entities table and web/data.json
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
const ledgerPath = path.join(repoRoot, 'outputs/notebooklm_phase8_enrichment_ledger.json');

const PHASE8_TARGET_IDS = [
  'ben-cang-hanh-khach-vinh-long',
  'ben-pha-dinh-khao-vinh-long',
  'ben-pha-an-binh-vinh-long',
  'ben-pha-tran-phu-can-tho-vinh-long-vinh-long',
  'ben-tau-du-lich-tp-ben-tre-ben-tre',
  'ben-pha-ham-luong-ben-tre',
  'ben-pha-tan-phu-chau-thanh-ben-tre',
  'ben-pha-dai-ngai-dau-cau-quan-tra-vinh-tra-vinh',
  'cang-ca-binh-thang',
  'vuot-song-co-chien',
  'tuyen-song-co-chien-hoang-hon-bo-ke-vinh-long',
  'ben-xe-vinh-long-trung-tam-vinh-long',
  'ben-xe-ben-tre-trung-tam-ben-tre',
  'ben-xe-tra-vinh-ben-xe-trung-tam-tra-vinh',
  'ben-xe-mien-tay-hcm',
  'tram-xe-buyt-noi-tinh-ben-xe-ben-tre-diem-dau-cac-tuyen-buyt-ben-tre',
  'diem-xe-buyt-phuong-trang-vinh-long-can-tho-tuyen-lien-tinh-vinh-long',
  'ben-xe-vung-liem-vinh-long',
  'ben-xe-tra-on-tich-thien-vinh-long',
  'ben-xe-cho-lach-ben-tre',
  'ben-xe-ba-tri-ben-tre',
  'ben-xe-mo-cay-nam-ben-tre',
  'ben-xe-cau-ke-tra-vinh',
  'ben-xe-cau-ngang-tra-vinh',
  'ben-xe-tieu-can-tra-vinh',
  'ben-xe-tra-cu-tra-vinh',
  'ben-xe-duyen-hai-tx-duyen-hai-tra-vinh',
  'cau-my-thuan',
  'cau-can-tho',
  'cau-lang-chim',
  'cau-truong-long-hoa',
  'quan-ca-ong-bo-song-co-chien-khu-vuc-ben-pha-co-chien-tra-vinh',
  'quan-an-song-hau-ben-do-tra-on-vinh-long',
  'quan-hu-tieu-go-khu-vuc-cau-ham-luong-ben-tre',
  'nha-hang-hai-san-lung-cot-cau-gan-cot-cau-co-chien-tra-vinh',
  'quan-oc-co-ba-gan-cau-my-thuan-phia-vinh-long'
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

describe('Phase 8 Deep Transit & Gateway Enrichment Invariant Suite', () => {
  it('verifies outputs/notebooklm_phase8_enrichment_ledger.json exists and contains 36 valid entries', () => {
    expect(fs.existsSync(ledgerPath)).toBe(true);
    const content = fs.readFileSync(ledgerPath, 'utf-8');
    const ledger = JSON.parse(content);
    const keys = Object.keys(ledger);
    expect(keys.length).toBe(36);

    for (const targetId of PHASE8_TARGET_IDS) {
      const item = ledger[targetId];
      expect(item, `Ledger missing entry for ${targetId}`).toBeDefined();
      expect(item.summary.length).toBeGreaterThanOrEqual(40);
      expect(item.description.length).toBeGreaterThanOrEqual(60);
      expect(item.hours).toBeTruthy();
      expect(item.price_range).toBeTruthy();
      expect(item.best_time).toBeTruthy();
      expect(item.waterway_access).toBeTruthy();
      expect(item.transit_guidance).toBeTruthy();
      expect(item.cultural_notes).toBeTruthy();
      expect(item.visual_narrative).toBeTruthy();
      expect(['CivicStructure', 'TouristAttraction', 'BusStation', 'LocalBusiness']).toContain(item.aeo_schema_type);
      expect(item.verifiedAt).toBeTruthy();
      expect(item.source_citations.length).toBeGreaterThanOrEqual(2);

      const hasTier1 = item.source_citations.some((c: any) => c.tier === 'TIER_1_GOVERNMENT');
      expect(hasTier1, `Entity ${targetId} must have at least one Tier 1 government citation`).toBe(true);
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

  it('confirms all 36 Phase 8 entities are verified=1 with full attributes in SQLite', () => {
    for (const targetId of PHASE8_TARGET_IDS) {
      const row: any = db.prepare('SELECT * FROM entities WHERE id = ?').get(targetId);
      expect(row, `Entity ${targetId} must exist in DB`).toBeDefined();
      expect(row.verified).toBe(1);
      expect(row.hours).toBeTruthy();
      expect(row.price_range).toBeTruthy();
      expect(row.best_time).toBeTruthy();
      expect(row.summary.length).toBeGreaterThanOrEqual(40);
      expect(row.description.length).toBeGreaterThanOrEqual(60);

      const attrs = JSON.parse(row.attributes || '{}');
      expect(attrs.waterway_access, `Entity ${targetId} missing waterway_access`).toBeTruthy();
      expect(attrs.transit_guidance, `Entity ${targetId} missing transit_guidance`).toBeTruthy();
      expect(attrs.cultural_notes, `Entity ${targetId} missing cultural_notes`).toBeTruthy();
      expect(attrs.visual_narrative, `Entity ${targetId} missing visual_narrative`).toBeTruthy();
      expect(attrs.verifiedAt, `Entity ${targetId} missing verifiedAt`).toMatch(/^\d{4}-\d{2}-\d{2}T/);
      expect(attrs.source_citations.length).toBeGreaterThanOrEqual(2);
    }
  });

  it('confirms 1:1 parity between SQLite and web/data.json for Phase 8 entities', () => {
    const dataJson = JSON.parse(fs.readFileSync(dataJsonPath, 'utf-8'));
    const entitiesMap = new Map(dataJson.entities.map((e: any) => [e.id, e]));

    for (const targetId of PHASE8_TARGET_IDS) {
      const dbRow: any = db.prepare('SELECT * FROM entities WHERE id = ?').get(targetId);
      const jsonEntity: any = entitiesMap.get(targetId);

      expect(jsonEntity, `Entity ${targetId} missing in web/data.json`).toBeDefined();
      expect(jsonEntity.verified).toBe(1);
      expect(jsonEntity.summary).toBe(dbRow.summary);
      expect(jsonEntity.description).toBe(dbRow.description);

      const dbAttrs = JSON.parse(dbRow.attributes || '{}');
      const jsonAttrs = jsonEntity.attributes || {};

      expect(jsonAttrs.waterway_access).toBe(dbAttrs.waterway_access);
      expect(jsonAttrs.transit_guidance).toBe(dbAttrs.transit_guidance);
      expect(jsonAttrs.cultural_notes).toBe(dbAttrs.cultural_notes);
      expect(jsonAttrs.visual_narrative).toBe(dbAttrs.visual_narrative);
      expect(jsonAttrs.verifiedAt).toBe(dbAttrs.verifiedAt);
      expect(jsonAttrs.hours).toBe(dbRow.hours);
      expect(jsonAttrs.price_range).toBe(dbRow.price_range);
      expect(jsonAttrs.best_time).toBe(dbRow.best_time);
    }
  });

  it('audits Phase 8 entities for 0 former province names outside historical context (R10.7)', () => {
    const formerProvinceRegexes = [
      /tỉnh Bến Tre/i,
      /tỉnh Trà Vinh/i
    ];

    const dataJson = JSON.parse(fs.readFileSync(dataJsonPath, 'utf-8'));
    const entitiesMap = new Map(dataJson.entities.map((e: any) => [e.id, e]));

    for (const targetId of PHASE8_TARGET_IDS) {
      const entity: any = entitiesMap.get(targetId);
      const fieldsToCheck = [
        entity.name,
        entity.summary,
        entity.description,
        entity.attributes?.hours,
        entity.attributes?.price_range,
        entity.attributes?.best_time,
        entity.attributes?.waterway_access,
        entity.attributes?.transit_guidance,
        entity.attributes?.cultural_notes,
        entity.attributes?.visual_narrative
      ].filter(Boolean);

      for (const text of fieldsToCheck) {
        for (const re of formerProvinceRegexes) {
          expect(re.test(text), `Violation of R10.7 in entity ${targetId}: "${text}"`).toBe(false);
        }
      }
    }
  });

  it('audits Phase 8 entities for 0 generic content fillers and formula starts (R50.2, R50.3, R50.7)', () => {
    const fillerRegexes = [
      /miền Tây/i,
      /sông nước hữu tình/i,
      /thiên đường/i,
      /hidden gem/i,
      /must[- ]see/i,
      /không thể bỏ lỡ/i,
      /đắm chìm/i,
      /hòa mình vào/i,
      /điểm đến lý tưởng/i
    ];

    const formulaStartRegex = /^\s*(Tọa lạc|Nằm (ở|tại|trong|bên)\b|Là một trong những\b)/i;
    const laMotRegex = /^[^.!?\n]{0,80}?\blà một\b/i;
    const clicheEndRegex = /(Hãy đến|Đừng bỏ lỡ|hãy một lần|Hãy ghé)[.!?]?$/i;
    const superlativeRegex = /nổi tiếng|nhất vùng|đậm đà bản sắc/i;
    const hasEvidenceRegex = /\d/;

    const dataJson = JSON.parse(fs.readFileSync(dataJsonPath, 'utf-8'));
    const entitiesMap = new Map(dataJson.entities.map((e: any) => [e.id, e]));

    for (const targetId of PHASE8_TARGET_IDS) {
      const entity: any = entitiesMap.get(targetId);
      const fieldsToCheck = [
        entity.summary,
        entity.description,
        entity.attributes?.hours,
        entity.attributes?.price_range,
        entity.attributes?.best_time,
        entity.attributes?.waterway_access,
        entity.attributes?.transit_guidance,
        entity.attributes?.cultural_notes,
        entity.attributes?.visual_narrative
      ].filter(Boolean);

      for (const text of fieldsToCheck) {
        // Filler check
        for (const re of fillerRegexes) {
          expect(re.test(text), `R50.2 Filler violation in entity ${targetId}: "${text}"`).toBe(false);
        }

        // Formula start check
        const firstSentence = text.split(/[.!?\n]/)[0].trim();
        expect(formulaStartRegex.test(firstSentence), `R50.3 formula start in entity ${targetId}: "${firstSentence}"`).toBe(false);
        expect(laMotRegex.test(firstSentence), `R50.3 "là một" early in entity ${targetId}: "${firstSentence}"`).toBe(false);

        // Cliche end check
        const sentences = text.split(/[.!?\n]/).map((s: string) => s.trim()).filter(Boolean);
        if (sentences.length > 0) {
          const lastSentence = sentences[sentences.length - 1];
          expect(clicheEndRegex.test(lastSentence), `R50.3 cliche end in entity ${targetId}: "${lastSentence}"`).toBe(false);
        }

        // Superlative without evidence check
        for (const sentence of sentences) {
          if (superlativeRegex.test(sentence)) {
            expect(hasEvidenceRegex.test(sentence), `R50.7 superlative without number/evidence in entity ${targetId}: "${sentence}"`).toBe(true);
          }
        }
      }
    }
  });
});
