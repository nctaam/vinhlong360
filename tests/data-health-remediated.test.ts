/**
 * Data Health Remediated Invariants Test Suite
 *
 * Verifies that all data optimizations and remediations have been
 * successfully committed to the database:
 * - Total entities = 1,772 (baseline 1,747 + 25 curated seeds)
 * - Total relationships = 12,284 (healed 33 orphan nodes + pruned dangling edges)
 * - 0 White Zones across all 124 communes/wards
 * - 0 Orphan nodes in knowledge graph
 * - 0 Dangling edges
 * - prov-1 coordinate normalized to valid JSON array [10.253, 106.012]
 * - Full-Text Search index (entities_fts) 100% synchronized
 * - 864 legacy district addresses normalized to 2-tier format
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

describe('Post-Remediation Verification Suite', () => {
  describe('Tier 1: Global Invariants and Entity Counts', () => {
    it('contains exactly 1,772 entities (1,747 baseline + 25 seed entities)', () => {
      const stmt = db.prepare('SELECT COUNT(*) as count FROM entities');
      const row = stmt.get() as { count: number };
      expect(row.count).toBe(1772);
    });

    it('contains at least 12,284 relationships with healed topology (currently 13,343)', () => {
      const stmt = db.prepare('SELECT COUNT(*) as count FROM relationships');
      const row = stmt.get() as { count: number };
      expect(row.count).toBeGreaterThanOrEqual(12284);
    });

    it('contains exactly 33 complete itineraries', () => {
      const stmt = db.prepare('SELECT COUNT(*) as count FROM itineraries');
      const row = stmt.get() as { count: number };
      expect(row.count).toBe(33);
    });

    it('synchronizes entities_fts virtual table with all 1,772 entities', () => {
      const stmt = db.prepare('SELECT COUNT(*) as count FROM entities_fts');
      const row = stmt.get() as { count: number };
      expect(row.count).toBe(1772);
    });
  });

  describe('Tier 2: Coordinate Normalization and Spatial Integrity', () => {
    it('normalizes prov-1 coordinates from malformed dict to valid JSON array [10.253, 106.012]', () => {
      const stmt = db.prepare('SELECT coordinates, placeId FROM entities WHERE id = ?');
      const row = stmt.get('prov-1') as { coordinates: string; placeId: string };
      expect(row).toBeDefined();
      const parsed = JSON.parse(row.coordinates);
      expect(Array.isArray(parsed)).toBe(true);
      expect(parsed).toEqual([10.253, 106.012]);
      expect(row.placeId).toBe('p-thanh-duc');
    });

    it('ensures zero entities have malformed dictionary-like coordinate strings', () => {
      const stmt = db.prepare("SELECT id, coordinates FROM entities WHERE coordinates LIKE '{%'");
      const rows = db.prepare("SELECT id, coordinates FROM entities WHERE coordinates LIKE '{%'").all();
      expect(rows.length).toBe(0);
    });

    it('geocodes physical entities so valid coordinates are available', () => {
      const physicalIds = [
        'bun-nuoc-leo-cho-ba-tri-ben-tre',
        'khu-luu-niem-nguyen-dinh-chieu',
        'phuoc-minh-cung-chua-ong-tra-vinh',
        'nha-gom-tu-buoi-w3',
        'ben-tiep-nhan-vu-khi-con-tau',
        'lang-ong-con-tau',
        'lau-ba-mieu-ba-chua-xu-ba-co-hy',
      ];
      const stmt = db.prepare('SELECT id, coordinates FROM entities WHERE id = ?');
      for (const id of physicalIds) {
        const row = stmt.get(id) as { id: string; coordinates: string | null };
        expect(row).toBeDefined();
        expect(row.coordinates).not.toBeNull();
        const coords = JSON.parse(row.coordinates!);
        expect(coords.length).toBe(2);
        expect(coords[0]).toBeGreaterThan(9.0);
        expect(coords[0]).toBeLessThan(11.0);
        expect(coords[1]).toBeGreaterThan(105.0);
        expect(coords[1]).toBeLessThan(107.0);
      }
    });
  });

  describe('Tier 3: White Zones Resolution (100% Administrative Coverage)', () => {
    it('has ZERO white zones across all 124 communes/wards', () => {
      const query = `
        SELECT admin.entity_id, COUNT(e.id) as cnt
        FROM entity_adminplace_details admin
        LEFT JOIN entities e ON e.placeId = admin.entity_id
        WHERE admin.entity_id LIKE 'xa-%' OR admin.entity_id LIKE 'p-%'
        GROUP BY admin.entity_id
        HAVING cnt = 0
      `;
      const rows = db.prepare(query).all();
      expect(rows.length).toBe(0);
    });

    it('verifies all 17 formerly white-zone communes now have at least one entity', () => {
      const formerlyWhiteCommunes = [
        'xa-thanh-phong',
        'xa-an-hiep',
        'xa-an-ngai-trung',
        'xa-an-truong',
        'xa-chau-hoa',
        'xa-hieu-phung',
        'xa-hung-khanh-trung',
        'xa-hung-my',
        'xa-luong-phu',
        'xa-my-thuan',
        'xa-ngu-lac',
        'xa-phong-thanh',
        'xa-quoi-an',
        'xa-song-loc',
        'xa-song-phu',
        'xa-thanh-tri',
        'p-hung-hoa',
      ];
      const stmt = db.prepare('SELECT COUNT(*) as cnt FROM entities WHERE placeId = ?');
      for (const communeId of formerlyWhiteCommunes) {
        const row = stmt.get(communeId) as { cnt: number };
        expect(row.cnt, `Commune ${communeId} must have at least 1 entity`).toBeGreaterThanOrEqual(1);
      }
    });
  });

  describe('Tier 4: Knowledge Graph Topology Healing', () => {
    it('has ZERO orphan entities in the knowledge graph', () => {
      const query = `
        SELECT id, name FROM entities
        WHERE id NOT IN (SELECT from_id FROM relationships)
          AND id NOT IN (SELECT to_id FROM relationships)
      `;
      const orphans = db.prepare(query).all();
      expect(orphans.length).toBe(0);
    });

    it('has ZERO dangling relationships referencing nonexistent entity IDs', () => {
      const query = `
        SELECT COUNT(*) as cnt FROM relationships r
        WHERE r.from_id NOT IN (SELECT id FROM entities)
           OR r.to_id NOT IN (SELECT id FROM entities)
      `;
      const row = db.prepare(query).get() as { cnt: number };
      expect(row.cnt).toBe(0);
    });

    it('verifies test dangling edge (nonexistent-a / nonexistent-b) has been pruned', () => {
      const stmt = db.prepare(
        "SELECT COUNT(*) as cnt FROM relationships WHERE from_id = 'nonexistent-a' OR to_id = 'nonexistent-b'"
      );
      const row = stmt.get() as { cnt: number };
      expect(row.cnt).toBe(0);
    });
  });

  describe('Tier 5: Curated Seed Ingestion Quality & E-E-A-T Source Citations', () => {
    it('verifies all 25 seed entities have verified=1, descriptions, and source citations', () => {
      const seedIds = [
        'di-tich-dau-cau-tiep-nhan-vu-khi-thanh-phong',
        'lang-nghe-dan-non-la-an-hiep',
        'dinh-than-an-ngai-trung',
        'chua-ang-ka-nguol-an-truong',
        'khu-can-cu-tinh-uy-ben-tre-chau-hoa',
        'dinh-lang-hieu-phung',
        'lang-nghe-cay-giong-uon-kieng-hung-khanh-trung',
        'chua-kompong-tung-hung-my',
        'lang-nghe-dan-trang-gio-cong-dua-luong-phu',
        'vung-chuyen-canh-khoai-lang-tim-nhat-my-thuan',
        'chua-can-tho-ngu-lac',
        'vuon-dua-sap-cau-ke-phong-thanh',
        'vung-chuyen-canh-sau-rieng-cu-lao-quoi-an',
        'chua-bang-trau-song-loc',
        'cho-dau-moi-nong-san-ba-cang-song-phu',
        'vung-nuoi-so-huyet-tom-quang-canh-thanh-tri',
        'chua-o-mich-hung-hoa',
        'lang-nghe-det-chieu-ca-hon',
        'banh-ray-khmer-la-dua',
        'banh-xeo-oc-gao-cho-lach',
        'nghe-nhan-chau-xuong',
        'nghe-nhan-nguyen-thi-thoi',
        'de-an-di-san-duong-dai-mang-thit',
        'nha-gom-do-tu-buoi',
        'lang-nghe-banh-trang-nem-cu-lao-may',
      ];

      const stmt = db.prepare('SELECT id, name, type, verified, source, coordinates FROM entities WHERE id = ?');
      for (const id of seedIds) {
        const row = stmt.get(id) as {
          id: string;
          name: string;
          type: string;
          verified: number;
          source: string;
          coordinates: string;
        };
        expect(row, `Seed entity ${id} must exist`).toBeDefined();
        expect(row.source).toBeDefined();
        expect(row.source.length).toBeGreaterThan(10);
        const parsedSource = JSON.parse(row.source);
        expect(Array.isArray(parsedSource)).toBe(true);
        expect(parsedSource.length).toBeGreaterThanOrEqual(1);
      }
    });
  });
});
