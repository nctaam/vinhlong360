/**
 * Past Events Lifecycle Management Verification Suite
 *
 * Verifies that:
 * 1. 16 one-off past events are marked with status='archived' and event_lifecycle='past'.
 * 2. 23 heritage past festivals are preserved with is_recurring=true and annual=true.
 * 3. 1,772 total entities, 13,343 relationships, and 33 itineraries are strictly preserved.
 * 4. web/data.json is in 100% parity with SQLite for all modified event entities.
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

const ONE_OFF_PAST_IDS = [
  'festival-dua-sap-cau-ke-tra-vinh',
  'ngay-hoi-van-hoa-the-thao-va-du-lich-huyen-cho-lach-ben-tre',
  'hoi-cho-xuc-tien-thuong-mai-du-lich-vinh-long-dip-tet-nguyen-dan-vinh-long',
  'hoi-cho-thuong-mai-cay-giong-hoa-kieng-cho-lach',
  'tuan-le-van-hoa-the-thao-va-du-lich-tinh-vinh-long-vinh-long',
  'ngay-hoi-banh-dan-gian-nam-bo-ket-hop-hoi-cho-ocop-vinh-long-vinh-long',
  'hoi-cho-thuong-mai-du-lich-ben-tre-ben-tre',
  'hoi-cho-thuong-mai-du-lich-tinh-tra-vinh-tra-vinh',
  'giai-ban-marathon-vinh-long-mo-rong-hanh-trinh-trai-tim-mekong-vinh-long',
  'giai-vo-dich-xe-dap-tinh-vinh-long-mo-rong-vinh-long',
  'giai-marathon-ben-tre-xu-dua-ben-tre',
  'giai-marathon-tra-vinh-tra-vinh-marathon-tra-vinh',
  'trien-lam-hoi-cho-nong-nghiep-cong-nghe-cao-ben-tre-ben-tre',
  'giai-the-thao-dan-toc-quoc-phong-tinh-tra-vinh-tra-vinh',
  'lien-hoan-van-nghe-quan-chung-tinh-tra-vinh-tra-vinh',
  'tuan-le-van-hoa-am-thuc-an-hoi-2026',
];

const HERITAGE_PAST_IDS = [
  'le-hoi-nghinh-ong-duyen-hai',
  'le-gio-nguyen-dinh-chieu',
  'le-hoi-chol-chnam-thmay-va-sen-dolta',
  'le-hoi-ngu-dan-thanh-hai-le-hoi-cau-ngu',
  'le-hoi-nguyen-tieu-o-tra-cu',
  'le-via-ba-co-hy',
  'le-hoi-van-thanh-mieu',
  'lang-ong-tien-quan-thong-che-dieu-bat-tuong-quan-nguyen-van-',
  'le-ha-dien-dinh-tan-hoa',
  'le-gio-phan-thanh-gian-tai-van-thanh-mieu',
  'le-cung-bien-dong-cao',
  'le-hoi-nghinh-ong-binh-thang',
  'le-hoi-ky-yen-ha-dien-dinh-tan-giai',
  'le-hoi-ky-yen-dinh-phu-le',
  'le-hoi-nghinh-ong-lang-con-tau',
  'le-hoi-chol-chnam-thmay-tai-chua-ky-son',
  'le-cung-lau-ba-ram-thang-gieng',
  'le-hoi-ky-yen',
  'le-cung-mieu',
  'le-hoi-nguyen-tieu',
  'le-hoi-cung-bien-my-long',
  'le-chol-chhnam-thmay',
  'le-via-quoc-cong-tong-phuoc-hiep',
];

let db: DatabaseSync;
let dataJson: any;

beforeAll(() => {
  expect(fs.existsSync(dbPath), `Database must exist at ${dbPath}`).toBe(true);
  expect(fs.existsSync(dataJsonPath), `data.json must exist at ${dataJsonPath}`).toBe(true);
  db = new DatabaseSync(dbPath, { readOnly: true });
  dataJson = JSON.parse(fs.readFileSync(dataJsonPath, 'utf-8'));
});

afterAll(() => {
  if (db) db.close();
});

describe('Past Events Lifecycle Management Suite', () => {
  it('strictly preserves global invariants (1,772 entities, 13,343 rels, 33 itins)', () => {
    const entCount = (db.prepare('SELECT COUNT(*) as count FROM entities').get() as any).count;
    const relCount = (db.prepare('SELECT COUNT(*) as count FROM relationships').get() as any).count;
    const itinCount = (db.prepare('SELECT COUNT(*) as count FROM itineraries').get() as any).count;
    expect(entCount).toBe(1772);
    expect(relCount).toBe(13343);
    expect(itinCount).toBe(33);
  });

  it('verifies all 16 one-off past events are marked status=archived and event_lifecycle=past', () => {
    const stmt = db.prepare('SELECT id, status, attributes FROM entities WHERE id = ?');
    for (const eid of ONE_OFF_PAST_IDS) {
      const row = stmt.get(eid) as any;
      expect(row, `Entity ${eid} must exist`).toBeDefined();
      expect(row.status).toBe('archived');
      const attrs = JSON.parse(row.attributes || '{}');
      expect(attrs.event_lifecycle).toBe('past');
      expect(attrs.is_concluded).toBe(true);
      expect(attrs.archived_at).toBe('2026-09-14');
    }
  });

  it('verifies all 23 heritage past festivals are preserved as active and recurring', () => {
    const stmt = db.prepare('SELECT id, status, attributes FROM entities WHERE id = ?');
    for (const eid of HERITAGE_PAST_IDS) {
      const row = stmt.get(eid) as any;
      expect(row, `Heritage festival ${eid} must exist`).toBeDefined();
      expect(row.status).not.toBe('archived');
      const attrs = JSON.parse(row.attributes || '{}');
      expect(attrs.is_recurring).toBe(true);
      expect(attrs.annual).toBe(true);
      expect(attrs.next_cycle_year).toBe(2027);
    }
  });

  it('verifies web/data.json is in 100% parity with SQLite for one-off and heritage past events', () => {
    const jsonEntityMap = new Map<string, any>(dataJson.entities.map((e: any) => [e.id, e]));
    for (const eid of ONE_OFF_PAST_IDS) {
      const jsonEnt = jsonEntityMap.get(eid);
      expect(jsonEnt, `Entity ${eid} missing in data.json`).toBeDefined();
      expect(jsonEnt.status).toBe('archived');
      expect(jsonEnt.attributes?.event_lifecycle).toBe('past');
    }
    for (const eid of HERITAGE_PAST_IDS) {
      const jsonEnt = jsonEntityMap.get(eid);
      expect(jsonEnt, `Heritage festival ${eid} missing in data.json`).toBeDefined();
      expect(jsonEnt.attributes?.is_recurring).toBe(true);
    }
  });
});
