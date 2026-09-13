/**
 * Phase 5 Deep Terroir Enrichment Test Suite
 *
 * Verifies that all 40 festival and cultural event entities cataloged in
 * outputs/notebooklm_phase5_enrichment_ledger.json have been successfully
 * enriched with full E-E-A-T fields, strict content gate compliance, and Tier 1/2 citations.
 */

import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { DatabaseSync } from 'node:sqlite';
import path from 'node:path';
import fs from 'node:fs';

const repoRoot = fs.existsSync(path.resolve('agent/data/vinhlong360.db'))
  ? path.resolve('.')
  : path.resolve('..');
const dbPath = path.join(repoRoot, 'agent/data/vinhlong360.db');
const ledgerPath = path.join(repoRoot, 'outputs/notebooklm_phase5_enrichment_ledger.json');

let db: DatabaseSync;
let ledger: Record<string, any>;

beforeAll(() => {
  expect(fs.existsSync(dbPath), `Database file must exist at ${dbPath}`).toBe(true);
  expect(fs.existsSync(ledgerPath), `Phase 5 ledger must exist at ${ledgerPath}`).toBe(true);
  db = new DatabaseSync(dbPath, { readOnly: true });
  ledger = JSON.parse(fs.readFileSync(ledgerPath, 'utf-8'));
});

afterAll(() => {
  if (db) {
    db.close();
  }
});

describe('Phase 5 Deep Terroir Enrichment Verification Suite', () => {
  it('verifies ledger contains exactly 40 target festival entities', () => {
    const keys = Object.keys(ledger);
    expect(keys.length).toBe(40);
  });

  it('verifies all 40 entities exist in SQLite database and are type=event', () => {
    const stmt = db.prepare('SELECT id, type, hours, best_time, attributes FROM entities WHERE id = ?');
    for (const eid of Object.keys(ledger)) {
      const row = stmt.get(eid) as any;
      expect(row, `Entity ${eid} must exist in DB`).toBeDefined();
      expect(row.type).toBe('event');
      expect(row.hours, `Entity ${eid} must have non-empty hours`).toBeTruthy();
      expect(row.best_time, `Entity ${eid} must have non-empty best_time`).toBeTruthy();
    }
  });

  it('verifies all 40 entities have all 6 E-E-A-T attributes properly populated', () => {
    const stmt = db.prepare('SELECT attributes FROM entities WHERE id = ?');
    const validSchemaTypes = [
      'Festival',
      'Event',
      'SocialEvent',
      'SportsEvent',
      'VisualArtsEvent',
      'FoodEvent',
      'ExhibitionEvent'
    ];

    for (const eid of Object.keys(ledger)) {
      const row = stmt.get(eid) as any;
      const attrs = JSON.parse(row.attributes);

      expect(attrs.waterway_access, `${eid} missing waterway_access`).toBeTruthy();
      expect(attrs.waterway_access.length).toBeGreaterThan(15);

      expect(attrs.aeo_schema_type, `${eid} missing aeo_schema_type`).toBeTruthy();
      expect(validSchemaTypes).toContain(attrs.aeo_schema_type);

      expect(attrs.cultural_notes, `${eid} missing cultural_notes`).toBeTruthy();
      expect(attrs.cultural_notes.length).toBeGreaterThan(80);

      expect(attrs.visual_narrative, `${eid} missing visual_narrative`).toBeTruthy();
      expect(attrs.visual_narrative.length).toBeGreaterThan(80);

      expect(attrs.source_citations, `${eid} missing source_citations`).toBeTruthy();
      expect(Array.isArray(attrs.source_citations)).toBe(true);
      expect(attrs.source_citations.length).toBeGreaterThanOrEqual(1);

      for (const cit of attrs.source_citations) {
        expect(cit.source_id).toBeTruthy();
        expect(cit.title).toBeTruthy();
        expect(cit.url).toMatch(/^https?:\/\//);
        expect(['TIER_1_GOVERNMENT', 'TIER_2_SCHOLARLY']).toContain(cit.tier);
      }

      expect(attrs.verifiedAt).toBe('2026-09-13T16:30:00+07:00');
    }
  });

  it('verifies strict content gate invariants (R10.7, R50.3, R50.7, R30.2) across all 40 entities', () => {
    const stmt = db.prepare('SELECT attributes, hours, best_time FROM entities WHERE id = ?');
    const patTinhCu = /tỉnh (Bến Tre|Trà Vinh)/i;
    const patLaMot = /^.{0,80}là một\b/i;
    const patSuperlatives = /\b(nổi tiếng|đậm đà bản sắc|nhất vùng|tuyệt vời)\b/i;
    const patEvidence = /\d/;

    for (const eid of Object.keys(ledger)) {
      const row = stmt.get(eid) as any;
      const attrs = JSON.parse(row.attributes);

      for (const field of ['cultural_notes', 'visual_narrative', 'waterway_access']) {
        const text = attrs[field] || '';
        expect(patTinhCu.test(text), `${eid}.${field} contains forbidden province name: ${text}`).toBe(false);
        expect(patLaMot.test(text), `${eid}.${field} starts with formula 'là một': ${text}`).toBe(false);

        const sentences = text.split(/[.!?\n]/);
        for (const sent of sentences) {
          if (patSuperlatives.test(sent)) {
            expect(patEvidence.test(sent), `${eid}.${field} has unanchored superlative without evidence: ${sent}`).toBe(true);
          }
        }
      }
    }
  });

  it('verifies DB integrity invariants B1/B6/B7 remain intact', () => {
    const entCount = (db.prepare('SELECT count(*) as c FROM entities').get() as any).c;
    const relCount = (db.prepare('SELECT count(*) as c FROM relationships').get() as any).c;
    const itiCount = (db.prepare('SELECT count(*) as c FROM itineraries').get() as any).c;

    expect(entCount).toBe(1772);
    expect(relCount).toBe(13343);
    expect(itiCount).toBe(33);
  });
});
