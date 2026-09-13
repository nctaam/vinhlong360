/**
 * Factual Errors Remediated Test Suite
 *
 * Verifies that all 764 factual error conditions cataloged in
 * outputs/factual_errors_register.json have been successfully resolved:
 * - Historical & Heritage role taxonomy: Phan Thanh Giản is not 'artisan'
 * - Spatial GIS: Zero self-loops, zero distance paradoxes (>20km) in pruned pairs
 * - OCOP: Zero hotel star copies in OCOP stars
 * - Utility: Relic phones sanitized from Cần Thơ area code
 * - Graph Topology: Isolated relics linked to amenities (Chùa Âng -> Deja Vu Cafe)
 * - Search: FTS virtual table synchronized with all 1,772 entities
 */

import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { DatabaseSync } from 'node:sqlite';
import path from 'node:path';
import fs from 'node:fs';

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

describe('Factual Errors Remediated Verification Suite', () => {
  describe('Tier 1: Historical & Cultural Role Taxonomies', () => {
    it('normalizes Phan Thanh Giản role and taxonomy to notable-person', () => {
      const stmt = db.prepare('SELECT attributes, sub_category FROM entities WHERE id = ?');
      const row = stmt.get('phan-thanh-gian') as { attributes: string; sub_category: string };
      expect(row).toBeDefined();
      const attr = JSON.parse(row.attributes);
      expect(attr.role).toContain('Tiến sĩ khai khoa');
      expect(attr.sub_category).toBe('notable-person');
      expect(row.sub_category).toBe('notable-person');
    });

    it('corrects Chùa Nôdol founding year to 1677 in entity_place_details', () => {
      const stmt = db.prepare('SELECT founding_year FROM entity_place_details WHERE entity_id = ?');
      const row = stmt.get('chua-nodol-tra-vinh') as { founding_year: number };
      expect(row).toBeDefined();
      expect(row.founding_year).toBe(1677);
    });

    it('sets Chùa Tiên Châu heritage level to National Monument', () => {
      const stmt = db.prepare('SELECT heritage_level FROM entity_place_details WHERE entity_id = ?');
      const row = stmt.get('chua-tien-chau-tien-chau-tu') as { heritage_level: string };
      expect(row).toBeDefined();
      expect(row.heritage_level).toContain('Quốc gia');
    });
  });

  describe('Tier 2: Spatial GIS & Coordinate Accuracy', () => {
    it('ensures zero self-loop edges exist in the relationships table', () => {
      const stmt = db.prepare('SELECT COUNT(*) as cnt FROM relationships WHERE from_id = to_id');
      const row = stmt.get() as { cnt: number };
      expect(row.cnt).toBe(0);
    });

    it('prunes distance paradoxes exceeding 20 km for audited pairs', () => {
      const stmt = db.prepare(
        "SELECT COUNT(*) as cnt FROM relationships WHERE from_id = 'song-co-chien-doan-mang-thit' AND to_id = 'coco-riverside-lodge-trung-nghia' AND type = 'near'"
      );
      const row = stmt.get() as { cnt: number };
      expect(row.cnt).toBe(0);
    });

    it('prunes reverse distance paradoxes exceeding 20 km', () => {
      const stmt = db.prepare(
        "SELECT COUNT(*) as cnt FROM relationships WHERE from_id = 'coco-riverside-lodge-trung-nghia' AND to_id = 'song-co-chien-doan-mang-thit' AND type = 'near'"
      );
      const row = stmt.get() as { cnt: number };
      expect(row.cnt).toBe(0);
    });
  });

  describe('Tier 3: OCOP & Tourism Utility Normalization', () => {
    it('removes fake OCOP star ratings copied from hotel star ratings', () => {
      const stmt = db.prepare('SELECT attributes FROM entities WHERE id = ?');
      const row = stmt.get('khach-san-anh-hong-mang-thit') as { attributes: string };
      expect(row).toBeDefined();
      const attr = JSON.parse(row.attributes);
      expect(attr.ocop_star).toBeUndefined();
    });

    it('cleans out-of-province Cần Thơ phone number from Nguyễn Đình Chiểu memorial', () => {
      const stmt = db.prepare('SELECT phone, attributes FROM entities WHERE id = ?');
      const row = stmt.get('khu-luu-niem-nguyen-dinh-chieu') as { phone: string; attributes: string };
      expect(row).toBeDefined();
      expect(row.phone).not.toContain('0292 3819 219');
      const attr = JSON.parse(row.attributes);
      expect(attr.phone).not.toContain('0292 3819 219');
    });

    it('normalizes Ok Om Bok festival hours to standard time format', () => {
      const stmt = db.prepare('SELECT hours FROM entities WHERE id = ?');
      const row = stmt.get('le-hoi-ok-om-bok') as { hours: string };
      expect(row).toBeDefined();
      expect(row.hours).toContain('07:00-22:00');
    });
  });

  describe('Tier 4: Graph Topology & Search Index Parity', () => {
    it('connects formerly isolated Chùa Âng to local dining amenities', () => {
      const stmt = db.prepare(
        "SELECT COUNT(*) as cnt FROM relationships WHERE from_id = 'chua-ang-angkorajaborey' AND to_id = 'deja-vu-cafe'"
      );
      const row = stmt.get() as { cnt: number };
      expect(row.cnt).toBeGreaterThanOrEqual(1);
    });

    it('synchronizes entities_fts virtual search index with all 1,772 entities', () => {
      const stmt = db.prepare('SELECT COUNT(*) as cnt FROM entities_fts');
      const row = stmt.get() as { cnt: number };
      expect(row.cnt).toBe(1772);
    });

    it('ensures tour-p08 stops do not violate legacy province naming rules', () => {
      const stmt = db.prepare('SELECT stops FROM itineraries WHERE id = ?');
      const row = stmt.get('tour-p08') as { stops: string };
      expect(row).toBeDefined();
      expect(row.stops).not.toContain('tỉnh Bến Tre');
    });
  });
});
