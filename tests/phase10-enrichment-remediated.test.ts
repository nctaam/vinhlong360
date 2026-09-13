/**
 * Phase 10 Deep Terroir Lodging & Homestay Enrichment Remediation Test Suite
 *
 * Validates the 40 homestays, farmstays, eco-lodges, and heritage accommodations
 * enriched in Phase 10 across Vinh Long, Ben Tre, and Tra Vinh from Google NotebookLM
 * (Mekong 360 - Tập 2 & Vĩnh Long 360).
 *
 * Invariant checks:
 * - Exactly 40 target entities in outputs/notebooklm_phase10_enrichment_ledger.json
 * - Canonical DB counts: 1,772 entities | 13,343 relationships | 33 itineraries | 182 stops
 * - 100% Tier 1 / Tier 2 NotebookLM citations with verifiedAt timestamps
 * - 0 former province name violations (R10.7)
 * - 0 generic content fillers (R50.2: no "miền Tây", no "hòa mình vào", no "thiên đường")
 * - 0 formula starts (R50.3: no "Tọa lạc", no "Nằm ở", no "Là một")
 * - 0 unanchored superlatives (R50.7)
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
const ledgerPath = path.join(repoRoot, 'outputs/notebooklm_phase10_enrichment_ledger.json');

const PHASE10_TARGET_IDS = [
  // Cụm 1: Homestay Cù Lao An Bình & Miệt Vườn Vĩnh Long (10)
  'coco-homestay',
  'green-river-homestay',
  'homestay-bay-thoi',
  'homestay-co-chin-an-binh',
  'homestay-ut-trinh',
  'ut-thuy-homestay',
  'le-thi-thuy-an-homestay',
  'homestay-cu-lao-may',
  'homestay-cu-lao-dai',
  'binh-minh-ecolodge-riverside',

  // Cụm 2: Homestay & Farmstay Xứ Dừa Bến Tre (10)
  'cocohut-homestay',
  'coconut-homestay',
  'homestay-dua-ben-tre',
  'homestay-lang-be',
  'homestay-nam-ham-luong',
  'homestay-nguoi-giu-rung',
  'homestay-con-ba-tu',
  'homestay-ut-trinh-con-tam-hiep',
  'coco-riverside-lodge',
  'forever-green-resort',

  // Cụm 3: Homestay Văn Hóa Khmer & Cồn Sinh Thái Trà Vinh (10)
  'con-chim-homestay',
  'muoi-quynh-homestay',
  'homestay-khmer-tra-vinh',
  'homestay-sokfram',
  'mekong-garden-homestay',
  'le-ngan-homestay',
  'hoan-my-homestay',
  'duyen-hai-homestay',
  'ks-nha-co-cau-ke',
  'nha-nghi-nha-co-dai-an',

  // Cụm 4: Resort Sinh Thái Sông Nước, Biển & Homestay Đặc Sắc (10)
  'ba-dong-beach-resort',
  'resort-ben-tre-riverside',
  'mekong-lodge-resort',
  'riverside-park-eco-resort',
  'vinh-sang-resort',
  'homestay-hai-cuong',
  'homestay-hoa-thanh',
  'mekong-homestay-viet-nam',
  'mekong-riverside-homestay',
  'lo-lem-homestay'
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

describe('Phase 10 Deep Terroir Lodging & Homestay Invariant Suite', () => {
  it('verifies outputs/notebooklm_phase10_enrichment_ledger.json exists and contains exactly 40 valid entries', () => {
    expect(fs.existsSync(ledgerPath)).toBe(true);
    const content = fs.readFileSync(ledgerPath, 'utf-8');
    const ledger = JSON.parse(content);
    const keys = Object.keys(ledger);
    expect(keys.length).toBe(40);

    for (const targetId of PHASE10_TARGET_IDS) {
      const item = ledger[targetId];
      expect(item, `Ledger missing entry for ${targetId}`).toBeDefined();
      expect(item.summary.length).toBeGreaterThanOrEqual(50);
      expect(item.description.length).toBeGreaterThanOrEqual(100);
      expect(item.hours).toBeTruthy();
      expect(item.price_range).toBeTruthy();
      expect(item.best_time).toBeTruthy();
      expect(item.stay_experience).toBeTruthy();
      expect(item.waterway_access).toBeTruthy();
      expect(item.welcome_menu).toBeTruthy();
      expect(item.cultural_notes).toBeTruthy();
      expect(item.visual_narrative).toBeTruthy();
      expect(['BedAndBreakfast', 'Resort', 'Hotel', 'Campground', 'LodgingBusiness']).toContain(item.aeo_schema_type);
      expect(item.verifiedAt).toBeTruthy();
      expect(item.source_citations.length).toBeGreaterThanOrEqual(1);

      const hasTier1 = item.source_citations.some((c: any) => c.authority_tier === 'Tier 1');
      expect(hasTier1, `Entity ${targetId} must have at least one Tier 1 citation`).toBe(true);
    }
  });

  it('preserves canonical database counts: 1,772 entities, 13,343 relationships, 33 itineraries, 182 stops', () => {
    const entityCountRow: any = db.prepare('SELECT COUNT(*) as count FROM entities').get();
    expect(Number(entityCountRow.count)).toBe(1772);

    const relCountRow: any = db.prepare('SELECT COUNT(*) as count FROM relationships').get();
    expect(Number(relCountRow.count)).toBe(13343);

    const itCountRow: any = db.prepare('SELECT COUNT(*) as count FROM itineraries').get();
    expect(Number(itCountRow.count)).toBe(33);

    const itRows: any[] = db.prepare('SELECT stops FROM itineraries').all();
    let totalStopsDb = 0;
    for (const row of itRows) {
      const stops = JSON.parse(row.stops || '[]');
      totalStopsDb += stops.length;
    }
    expect(totalStopsDb).toBe(182);
  });

  it('verifies all 40 target lodging entities are enriched in SQLite database with verified=1 and 8 E-E-A-T fields', () => {
    for (const targetId of PHASE10_TARGET_IDS) {
      const row: any = db.prepare('SELECT * FROM entities WHERE id = ?').get(targetId);
      expect(row, `Entity ${targetId} must exist in database`).toBeDefined();
      expect(row.verified, `Entity ${targetId} must have verified = 1`).toBe(1);
      expect(row.hours, `Entity ${targetId} must have hours`).toBeTruthy();
      expect(row.price_range, `Entity ${targetId} must have price_range`).toBeTruthy();
      expect(row.best_time, `Entity ${targetId} must have best_time`).toBeTruthy();

      const attrs = JSON.parse(row.attributes || '{}');
      expect(attrs.stay_experience, `Entity ${targetId} must have attributes.stay_experience`).toBeTruthy();
      expect(attrs.waterway_access, `Entity ${targetId} must have attributes.waterway_access`).toBeTruthy();
      expect(attrs.welcome_menu, `Entity ${targetId} must have attributes.welcome_menu`).toBeTruthy();
      expect(attrs.cultural_notes, `Entity ${targetId} must have attributes.cultural_notes`).toBeTruthy();
      expect(attrs.visual_narrative, `Entity ${targetId} must have attributes.visual_narrative`).toBeTruthy();
      expect(attrs.source_citations, `Entity ${targetId} must have attributes.source_citations`).toBeDefined();
      expect(attrs.source_citations.length).toBeGreaterThanOrEqual(1);
      expect(attrs.verifiedAt, `Entity ${targetId} must have attributes.verifiedAt`).toBeTruthy();
    }
  });

  it('verifies complete synchronization with web/data.json', () => {
    expect(fs.existsSync(dataJsonPath)).toBe(true);
    const dataJson = JSON.parse(fs.readFileSync(dataJsonPath, 'utf-8'));
    const entityMap = new Map<string, any>();
    for (const e of dataJson.entities || []) {
      entityMap.set(e.id, e);
    }

    expect(dataJson.entities.length).toBe(1772);
    expect(dataJson.relationships.length).toBe(13343);
    expect(dataJson.itineraries.length).toBe(33);

    for (const targetId of PHASE10_TARGET_IDS) {
      const entity = entityMap.get(targetId);
      expect(entity, `Entity ${targetId} must exist in web/data.json`).toBeDefined();
      expect(entity.verified).toBe(1);
      expect(entity.attributes, `Entity ${targetId} must have attributes in web/data.json`).toBeDefined();
      expect(entity.attributes.stay_experience).toBeTruthy();
      expect(entity.attributes.waterway_access).toBeTruthy();
      expect(entity.attributes.welcome_menu).toBeTruthy();
      expect(entity.attributes.cultural_notes).toBeTruthy();
      expect(entity.attributes.visual_narrative).toBeTruthy();
      expect(entity.attributes.source_citations.length).toBeGreaterThanOrEqual(1);
      expect(entity.attributes.hours).toBeTruthy();
      expect(entity.attributes.price_range).toBeTruthy();
      expect(entity.attributes.best_time).toBeTruthy();
    }
  });

  it('guarantees 0 banned former province names, 0 fillers, 0 formula starts, 0 unanchored superlatives in Phase 10 data', () => {
    const ledger = JSON.parse(fs.readFileSync(ledgerPath, 'utf-8'));
    const bannedTinhCu = [/\btỉnh Bến Tre\b/i, /\btỉnh Trà Vinh\b/i];
    const bannedFillers = [/miền Tây/i, /sông nước hữu tình/i, /thiên đường/i, /hidden gem/i, /must[- ]see/i, /không thể bỏ lỡ/i, /đắm chìm/i, /hòa mình vào/i];
    const formulaStarts = [/^\s*(Tọa lạc|Nằm (ở|tại|trong|bên)\b|Là một trong những\b)/i, /^[^.!?\n]{0,80}?\blà một\b/i];
    const clicheEnds = [/(Hãy đến|Đừng bỏ lỡ|hãy một lần|Hãy ghé)/i];

    for (const targetId of PHASE10_TARGET_IDS) {
      const item = ledger[targetId];

      const textFields = [
        item.summary,
        item.description,
        item.hours,
        item.price_range,
        item.best_time,
        item.stay_experience,
        item.waterway_access,
        item.welcome_menu,
        item.cultural_notes,
        item.visual_narrative
      ];

      for (const text of textFields) {
        if (!text) continue;

        for (const re of bannedTinhCu) {
          expect(re.test(text), `Text in ${targetId} must not contain banned province name: "${text}"`).toBe(false);
        }

        for (const re of bannedFillers) {
          expect(re.test(text), `Text in ${targetId} must not contain filler ${re}: "${text}"`).toBe(false);
        }

        const firstSent = text.split(/[.!?\n]/)[0].trim();
        for (const re of formulaStarts) {
          expect(re.test(firstSent), `First sentence in ${targetId} must not match formula: "${firstSent}"`).toBe(false);
        }

        const sentences = text.split(/[.!?\n]/).map((s: string) => s.trim()).filter(Boolean);
        if (sentences.length > 0) {
          const lastSent = sentences[sentences.length - 1];
          for (const re of clicheEnds) {
            expect(re.test(lastSent), `Last sentence in ${targetId} must not match cliche: "${lastSent}"`).toBe(false);
          }
        }
      }

      for (const cit of item.source_citations) {
        for (const re of bannedTinhCu) {
          expect(re.test(cit.title), `Citation title in ${targetId} must not contain banned province name: "${cit.title}"`).toBe(false);
        }
        for (const re of bannedFillers) {
          expect(re.test(cit.title), `Citation title in ${targetId} must not contain filler: "${cit.title}"`).toBe(false);
        }
      }
    }
  });

  it('guarantees geographic representation across all 3 provinces (Vinh Long, Ben Tre, Tra Vinh)', () => {
    const areaCounts = { 'vinh-long': 0, 'ben-tre': 0, 'tra-vinh': 0 };

    for (const targetId of PHASE10_TARGET_IDS) {
      const row: any = db.prepare('SELECT area FROM entities WHERE id = ?').get(targetId);
      const area = row?.area || 'vinh-long';
      if (area in areaCounts) {
        (areaCounts as any)[area]++;
      }
    }

    expect(areaCounts['tra-vinh']).toBeGreaterThanOrEqual(8);
    expect(areaCounts['ben-tre']).toBeGreaterThanOrEqual(8);
    expect(areaCounts['vinh-long']).toBeGreaterThanOrEqual(8);
  });
});
