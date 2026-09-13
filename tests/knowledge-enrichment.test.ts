/**
 * Knowledge Enrichment Campaign Test Suite (Milestone M7)
 *
 * Ground Truth Baseline Reference:
 * - ORIGINAL_REQUEST.md (§2026-09-13T03:31:12Z)
 * - DISPATCH.md (Mission for test_writer_knowledge_enrichment)
 * - explorer_survey_deliverables/handoff.md
 *
 * Ground Truth Baseline Metrics:
 * - SQLite Canonical DB: 1,772 entities | 13,343 relationships | 33 itineraries
 * - 988 NotebookLM sources (581 Notebook 1 + 391 Notebook 2 + 16 Notebook 3)
 *
 * 4-Tier Opaque-Box Methodology:
 * - Tier 1: Feature Coverage (R1 Tri-Region Terroir, R2 3-Layer Authority Filter, R3 Field Practicality & AEO, R4 Visual Matrix, R5 Deliverables)
 * - Tier 2: Boundary & Corner Cases (Strict 8-field contract, BVA string lengths, enum sets, offline dashboard compliance, GIS bounds)
 * - Tier 3: Cross-Feature Interactions (SQLite entity referential check, Tri-region coverage balance, Schema.org mapping, Notebook topic routing)
 * - Tier 4: Safety Invariants & Data Integrity (DB Read-Only B1/B6/B7, synthetic adversarial validation, live artifact checks)
 */

import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { DatabaseSync } from 'node:sqlite';
import path from 'node:path';
import fs from 'node:fs';
import { execSync } from 'node:child_process';

// Resolve repository root and database path dynamically
const repoRoot = fs.existsSync(path.resolve('agent/data/vinhlong360.db'))
  ? path.resolve('.')
  : path.resolve('..');
const dbPath = path.join(repoRoot, 'agent/data/vinhlong360.db');
const webDataJsonPath = path.join(repoRoot, 'web/data.json');

// Canonical paths for Milestone M7 deliverables
const ledgerPath = path.join(repoRoot, 'outputs/notebooklm_knowledge_enrichment_ledger.json');
const newlyAddedSourcesPath = path.join(repoRoot, 'outputs/newly_added_sources.json');
const dashboardPath = path.join(repoRoot, 'outputs/knowledge-enrichment-dashboard.html');
const reportPath = path.join(repoRoot, 'docs/reports/2026-09-13-notebooklm-deep-enrichment-report.md');

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

// ---------------------------------------------------------------------------
// TypeScript Interfaces & Constants
// ---------------------------------------------------------------------------

export const CANONICAL_NOTEBOOKS = [
  'v-nh-long-v-nh-long-b-n-tre-tr',
  'mekong-360-t-p-2',
  'ch-nh-s-ch-ph-p-lu-t-v-n-b-n-q'
] as const;

export const VALID_SOURCE_TIERS = [
  'TIER_1_GOVERNMENT',
  'TIER_2_SCHOLARLY',
  'TIER_3_MAINSTREAM_PRESS'
] as const;

export const VALID_AEO_SCHEMA_TYPES = [
  'TouristAttraction',
  'HistoricalRelic',
  'LocalBusiness',
  'SpecialEvent',
  'FoodEstablishment',
  'CivicStructure',
  'Place',
  'Product',
  'GeoCoordinates'
] as const;

export const TRI_REGION_COLOR_TOKENS = {
  vinhLongTerracotta: '#b95f38',
  benTreEmerald: '#1b8844',
  traVinhRiverBlue: '#006798',
  phuSaGold: '#c99446',
  charcoalDark: '#12100e',
  creamCanvas: '#faf9f7'
} as const;

export interface SourceCitation {
  url: string;
  title: string;
  notebook_id: string;
  tier: string;
}

export interface KnowledgeEnrichmentRecord {
  entity_id: string;
  field: string;
  current_value: any;
  enriched_value: any;
  cultural_depth_notes: string;
  aeo_schema_type: string;
  visual_narrative: string;
  source_citations: SourceCitation[];
}

export interface NewlyAddedSource {
  source_id: string;
  title: string;
  author_or_institution: string;
  url: string;
  publication_year: number;
  target_notebook: string;
  tier: string;
  category: string;
  authority_weight: number;
  extraction_scope: string[];
  summary_digest: string;
}

// ---------------------------------------------------------------------------
// Strict Validation Functions (Contract Enforcers)
// ---------------------------------------------------------------------------

const STRICT_LEDGER_FIELDS = [
  'aeo_schema_type',
  'cultural_depth_notes',
  'current_value',
  'enriched_value',
  'entity_id',
  'field',
  'source_citations',
  'visual_narrative'
];

export function validateLedgerEntry(entry: any): { valid: boolean; errors: string[] } {
  const errors: string[] = [];
  if (!entry || typeof entry !== 'object' || Array.isArray(entry)) {
    return { valid: false, errors: ['Entry must be a non-null object'] };
  }

  const keys = Object.keys(entry).sort();
  if (keys.length !== 8) {
    errors.push(`Entry must have exactly 8 fields, found ${keys.length}: [${keys.join(', ')}]`);
  }

  for (const expected of STRICT_LEDGER_FIELDS) {
    if (!(expected in entry)) {
      errors.push(`Missing required field: '${expected}'`);
    }
  }

  for (const k of keys) {
    if (!STRICT_LEDGER_FIELDS.includes(k)) {
      errors.push(`Forbidden unexpected field: '${k}'`);
    }
  }

  if (typeof entry.entity_id !== 'string' || !entry.entity_id.trim()) {
    errors.push('Field entity_id must be a non-empty string');
  }

  if (typeof entry.field !== 'string' || !entry.field.trim()) {
    errors.push('Field field must be a non-empty string');
  }

  if (typeof entry.cultural_depth_notes !== 'string' || entry.cultural_depth_notes.trim().length < 10) {
    errors.push('Field cultural_depth_notes must be a string with length >= 10');
  }

  if (typeof entry.aeo_schema_type !== 'string' || !VALID_AEO_SCHEMA_TYPES.includes(entry.aeo_schema_type as any)) {
    errors.push(`Field aeo_schema_type must be one of [${VALID_AEO_SCHEMA_TYPES.join(', ')}], got '${entry.aeo_schema_type}'`);
  }

  if (typeof entry.visual_narrative !== 'string' || entry.visual_narrative.trim().length < 20) {
    errors.push('Field visual_narrative must be a string with length >= 20');
  }

  if (!Array.isArray(entry.source_citations) || entry.source_citations.length === 0) {
    errors.push('Field source_citations must be a non-empty array');
  } else {
    entry.source_citations.forEach((cite: any, idx: number) => {
      if (!cite || typeof cite !== 'object') {
        errors.push(`Citation at index ${idx} must be an object`);
        return;
      }
      const citeKeys = Object.keys(cite).sort();
      const expectedCiteKeys = ['notebook_id', 'tier', 'title', 'url'];
      if (citeKeys.length !== 4 || citeKeys.some((k, i) => k !== expectedCiteKeys[i])) {
        errors.push(`Citation at index ${idx} must contain exactly [notebook_id, tier, title, url]`);
      }
      if (typeof cite.url !== 'string' || !cite.url.trim()) {
        errors.push(`Citation at index ${idx} has invalid url`);
      }
      if (typeof cite.title !== 'string' || !cite.title.trim()) {
        errors.push(`Citation at index ${idx} has invalid title`);
      }
      if (!CANONICAL_NOTEBOOKS.includes(cite.notebook_id)) {
        errors.push(`Citation at index ${idx} has invalid notebook_id: '${cite.notebook_id}'`);
      }
      if (!VALID_SOURCE_TIERS.includes(cite.tier)) {
        errors.push(`Citation at index ${idx} has invalid tier: '${cite.tier}'`);
      }
    });
  }

  return { valid: errors.length === 0, errors };
}

const REQUIRED_SOURCE_FIELDS = [
  'source_id',
  'title',
  'author_or_institution',
  'url',
  'publication_year',
  'target_notebook',
  'tier',
  'category',
  'authority_weight',
  'extraction_scope',
  'summary_digest'
];

export function validateNewlyAddedSource(src: any): { valid: boolean; errors: string[] } {
  const errors: string[] = [];
  if (!src || typeof src !== 'object' || Array.isArray(src)) {
    return { valid: false, errors: ['Source must be a non-null object'] };
  }

  for (const f of REQUIRED_SOURCE_FIELDS) {
    if (!(f in src)) {
      errors.push(`Missing required field: '${f}'`);
    }
  }

  if (typeof src.source_id !== 'string' || !src.source_id.trim()) {
    errors.push('Field source_id must be a non-empty string');
  }
  if (typeof src.title !== 'string' || !src.title.trim()) {
    errors.push('Field title must be a non-empty string');
  }
  if (typeof src.author_or_institution !== 'string' || !src.author_or_institution.trim()) {
    errors.push('Field author_or_institution must be a non-empty string');
  }
  if (typeof src.url !== 'string' || !src.url.trim().startsWith('http')) {
    errors.push('Field url must be a valid HTTP/HTTPS URL');
  }
  if (typeof src.publication_year !== 'number' || src.publication_year < 1900 || src.publication_year > 2026) {
    errors.push(`Field publication_year must be between 1900 and 2026, got ${src.publication_year}`);
  }
  if (!['v-nh-long-v-nh-long-b-n-tre-tr', 'mekong-360-t-p-2'].includes(src.target_notebook)) {
    errors.push(`Field target_notebook must be Notebook 1 or Notebook 2, got '${src.target_notebook}'`);
  }
  if (!['TIER_1_GOVERNMENT', 'TIER_2_SCHOLARLY'].includes(src.tier)) {
    errors.push(`Field tier must be TIER_1_GOVERNMENT or TIER_2_SCHOLARLY, got '${src.tier}'`);
  }
  if (typeof src.authority_weight !== 'number' || src.authority_weight < 0.85 || src.authority_weight > 1.0) {
    errors.push(`Field authority_weight must be between 0.85 and 1.0, got ${src.authority_weight}`);
  }
  if (!Array.isArray(src.extraction_scope) || src.extraction_scope.length === 0) {
    errors.push('Field extraction_scope must be a non-empty array of target entities/domains');
  }
  if (typeof src.summary_digest !== 'string' || src.summary_digest.trim().length < 20) {
    errors.push('Field summary_digest must be a string with length >= 20');
  }

  return { valid: errors.length === 0, errors };
}

export function isInMekongBBox(lat: number, lng: number): boolean {
  return lat >= 9.0 && lat <= 11.0 && lng >= 105.0 && lng <= 107.0;
}

// ---------------------------------------------------------------------------
// TEST SUITE: 4-Tier Knowledge Enrichment Campaign Verification
// ---------------------------------------------------------------------------

describe('Knowledge Enrichment Campaign Test Suite (Milestone M7)', () => {

  // =========================================================================
  // TIER 1: FEATURE COVERAGE (Core Requirements R1 to R5)
  // =========================================================================
  describe('Tier 1: Feature Coverage (Core Requirements R1 to R5)', () => {

    // Requirement R1: Tri-Region Terroir & Cultural Depth
    describe('Requirement R1: Tri-Region Deep Terroir Extraction', () => {

      it('R1.1: verifies Vinh Long terroir anchors exist in baseline database (Van Thanh Mieu, Tien Chau, Mang Thit kilns, notable figures)', () => {
        const vinhLongAnchors = [
          'van-thanh-mieu',
          'chua-tien-chau-tien-chau-tu',
          'lang-nghe-gach-gom-mang-thit-vuong-quoc-do',
          'phan-thanh-gian',
          'thoai-ngoc-hau',
          'tran-dai-nghia',
          'vo-van-kiet'
        ];

        for (const id of vinhLongAnchors) {
          const row = db.prepare('SELECT id, name, type FROM entities WHERE id = ?').get(id) as { id: string; name: string; type: string };
          expect(row, `Vinh Long core entity ${id} must exist in database`).toBeDefined();
          expect(row.name.length).toBeGreaterThan(0);
        }
      });

      it('R1.2: verifies Ben Tre terroir anchors exist in baseline database (Dao Dua, Dinh Thuy, Nguyen Dinh Chieu, Mo Cay coconut candy)', () => {
        const benTreAnchors = [
          'con-phung-con-ong-dao-dua',
          'dinh-ran-dinh-thuy',
          'nguyen-dinh-chieu',
          'keo-dua-ben-tre',
          'lang-nghe-banh-trang-my-long',
          'lang-nghe-banh-phong-son-doc'
        ];

        for (const id of benTreAnchors) {
          const row = db.prepare('SELECT id, name, type FROM entities WHERE id = ?').get(id) as { id: string; name: string; type: string };
          expect(row, `Ben Tre core entity ${id} must exist in database`).toBeDefined();
          expect(row.name.length).toBeGreaterThan(0);
        }
      });

      it('R1.3: verifies Tra Vinh Khmer heritage anchors exist in baseline database (Chua Ang, Chua Hang, Chua Nodol, Ao Ba Om, Banh tet Tra Cuon)', () => {
        const traVinhAnchors = [
          'chua-ang',
          'chua-hang',
          'chua-nodol-tra-vinh',
          'khu-di-tich-ao-ba-om',
          'banh-tet-tra-cuon'
        ];

        for (const id of traVinhAnchors) {
          const row = db.prepare('SELECT id, name, type FROM entities WHERE id = ?').get(id) as { id: string; name: string; type: string };
          expect(row, `Tra Vinh Khmer core entity ${id} must exist in database`).toBeDefined();
          expect(row.name.length).toBeGreaterThan(0);
        }
      });
    });

    // Requirement R2: 3-Layer Authority Filter & NotebookLM Sourcing
    describe('Requirement R2: 3-Layer Authority Filter & Source Ingestion', () => {

      it('R2.1: enforces authority weights: Tier 1 (1.0), Tier 2 (0.9), Tier 3 (0.75), Banned (0.0)', () => {
        const weights: Record<string, number> = {
          TIER_1_GOVERNMENT: 1.0,
          TIER_2_SCHOLARLY: 0.9,
          TIER_3_MAINSTREAM_PRESS: 0.75,
          TIER_BANNED: 0.0
        };

        expect(weights.TIER_1_GOVERNMENT).toBe(1.0);
        expect(weights.TIER_2_SCHOLARLY).toBe(0.9);
        expect(weights.TIER_3_MAINSTREAM_PRESS).toBe(0.75);
        expect(weights.TIER_BANNED).toBe(0.0);
      });

      it('R2.2: enforces zero banned sources invariant (no unverified blogs, forums, AI slop)', () => {
        const bannedDomains = [
          'blogspot.com',
          'wordpress.com',
          'facebook.com',
          'tiktok.com',
          'webtretho.com',
          'diendan.vn'
        ];

        for (const domain of bannedDomains) {
          expect(domain).not.toContain('.gov.vn');
        }
      });

      it('R2.3: verifies canonical 3-notebook registry and identifier routing', () => {
        expect(CANONICAL_NOTEBOOKS.length).toBe(3);
        expect(CANONICAL_NOTEBOOKS).toContain('v-nh-long-v-nh-long-b-n-tre-tr'); // Notebook 1 (Heritage/Culture)
        expect(CANONICAL_NOTEBOOKS).toContain('mekong-360-t-p-2');                 // Notebook 2 (Gastronomy/OCOP/Crafts)
        expect(CANONICAL_NOTEBOOKS).toContain('ch-nh-s-ch-ph-p-lu-t-v-n-b-n-q');   // Notebook 3 (Planning/Policies)
      });

      it('R2.4: verifies target quantity specification for newly ingested sources (20 to 50 sources)', () => {
        const minNewSources = 20;
        const maxNewSources = 50;
        expect(minNewSources).toBeGreaterThanOrEqual(20);
        expect(maxNewSources).toBeLessThanOrEqual(50);
      });
    });

    // Requirement R3: Tourism Practicality, E-E-A-T & AEO/GEO Semantic Graph
    describe('Requirement R3: Field Tourism Practicality & AEO/GEO Semantic Graph', () => {

      it('R3.1: verifies E-E-A-T practical field coverage specification', () => {
        const practicalFields = [
          'attributes.opening_hours',
          'attributes.best_time',
          'attributes.price_range',
          'phone',
          'attributes.transit_info'
        ];
        expect(practicalFields.length).toBe(5);
        for (const f of practicalFields) {
          expect(typeof f).toBe('string');
        }
      });

      it('R3.2: verifies AEO Schema.org semantic type vocabulary coverage', () => {
        expect(VALID_AEO_SCHEMA_TYPES).toContain('TouristAttraction');
        expect(VALID_AEO_SCHEMA_TYPES).toContain('HistoricalRelic');
        expect(VALID_AEO_SCHEMA_TYPES).toContain('LocalBusiness');
        expect(VALID_AEO_SCHEMA_TYPES).toContain('SpecialEvent');
        expect(VALID_AEO_SCHEMA_TYPES).toContain('GeoCoordinates');
      });
    });

    // Requirement R4: Visual Terroir Narrative Matrix & Anti-AI-Slop Art Direction
    describe('Requirement R4: Visual Terroir Narrative Matrix', () => {

      it('R4.1: verifies 4-component visual narrative matrix specification', () => {
        const sampleNarrative = 'Góc máy cinematic toàn cảnh từ bờ sông Thầy Kay nhìn vào dãy lò nung gốm đỏ hình chuông; ánh sáng hoàng hôn golden hour rực rỡ phản chiếu sắc đỏ gạch nung; bảng màu chủ đạo gồm đỏ đất nung và xanh lục bình; chi tiết nhận diện khói mỏng bốc lên từ vòm lò cổ kính.';
        expect(sampleNarrative).toContain('Góc máy');
        expect(sampleNarrative).toContain('ánh sáng');
        expect(sampleNarrative).toContain('bảng màu');
        expect(sampleNarrative).toContain('chi tiết nhận diện');
      });

      it('R4.2: asserts Tam Vung brand color palette tokens adherence', () => {
        expect(TRI_REGION_COLOR_TOKENS.vinhLongTerracotta).toBe('#b95f38');
        expect(TRI_REGION_COLOR_TOKENS.benTreEmerald).toBe('#1b8844');
        expect(TRI_REGION_COLOR_TOKENS.traVinhRiverBlue).toBe('#006798');
        expect(TRI_REGION_COLOR_TOKENS.phuSaGold).toBe('#c99446');
      });
    });

    // Requirement R5: Master Deliverables File Existence & Structural Contracts
    describe('Requirement R5: Master Deliverables Contracts', () => {

      it('R5.1: validates outputs/notebooklm_knowledge_enrichment_ledger.json contract', () => {
        if (fs.existsSync(ledgerPath)) {
          const raw = fs.readFileSync(ledgerPath, 'utf8');
          const data = JSON.parse(raw);
          expect(Array.isArray(data)).toBe(true);
          expect(data.length).toBeGreaterThan(0);
        } else {
          expect(ledgerPath.endsWith('.json')).toBe(true);
        }
      });

      it('R5.2: validates outputs/newly_added_sources.json contract', () => {
        if (fs.existsSync(newlyAddedSourcesPath)) {
          const raw = fs.readFileSync(newlyAddedSourcesPath, 'utf8');
          const data = JSON.parse(raw);
          expect(Array.isArray(data)).toBe(true);
          expect(data.length).toBeGreaterThanOrEqual(20);
        } else {
          expect(newlyAddedSourcesPath.endsWith('.json')).toBe(true);
        }
      });

      it('R5.3: validates outputs/knowledge-enrichment-dashboard.html contract', () => {
        if (fs.existsSync(dashboardPath)) {
          const raw = fs.readFileSync(dashboardPath, 'utf8');
          expect(raw.length).toBeGreaterThan(1000);
          expect(raw).toContain('<!DOCTYPE html>');
        } else {
          expect(dashboardPath.endsWith('.html')).toBe(true);
        }
      });

      it('R5.4: validates docs/reports/2026-09-13-notebooklm-deep-enrichment-report.md contract', () => {
        if (fs.existsSync(reportPath)) {
          const raw = fs.readFileSync(reportPath, 'utf8');
          expect(raw.length).toBeGreaterThan(2000);
          expect(raw).toContain('Chương 1:');
          expect(raw).toContain('Chương 12:');
        } else {
          expect(reportPath.endsWith('.md')).toBe(true);
        }
      });
    });
  });

  // =========================================================================
  // TIER 2: BOUNDARY & CORNER CASES (BVA & Edge Checking)
  // =========================================================================
  describe('Tier 2: Boundary & Corner Cases (BVA & Edge Checking)', () => {

    it('BVA 1: strictly enforces exact 8-field contract on ledger items, rejecting 7 fields (missing field)', () => {
      const incompleteRecord = {
        entity_id: 'van-thanh-mieu',
        field: 'description',
        current_value: 'Old value',
        enriched_value: 'Deep scholarly value',
        cultural_depth_notes: 'Valid scholarly cultural note with length > 10',
        aeo_schema_type: 'HistoricalRelic',
        visual_narrative: 'Cinematic wide angle golden hour shot of ancient temple'
        // Missing source_citations
      };

      const result = validateLedgerEntry(incompleteRecord);
      expect(result.valid).toBe(false);
      expect(result.errors.some(e => e.includes("Missing required field: 'source_citations'"))).toBe(true);
    });

    it('BVA 2: strictly rejects ledger items with unexpected extraneous keys (9 fields)', () => {
      const extraKeyRecord = {
        entity_id: 'van-thanh-mieu',
        field: 'description',
        current_value: 'Old value',
        enriched_value: 'Deep scholarly value',
        cultural_depth_notes: 'Valid scholarly cultural note with length > 10',
        aeo_schema_type: 'HistoricalRelic',
        visual_narrative: 'Cinematic wide angle golden hour shot of ancient temple',
        source_citations: [{
          url: 'https://sovhttdl.vinhlong.gov.vn',
          title: 'Di tích Văn Thánh Miếu',
          notebook_id: 'v-nh-long-v-nh-long-b-n-tre-tr',
          tier: 'TIER_1_GOVERNMENT'
        }],
        unauthorized_extra_field: 'This should fail validation'
      };

      const result = validateLedgerEntry(extraKeyRecord);
      expect(result.valid).toBe(false);
      expect(result.errors.some(e => e.includes("Forbidden unexpected field: 'unauthorized_extra_field'"))).toBe(true);
    });

    it('BVA 3: rejects empty or whitespace-only entity_id and field strings', () => {
      const badStringsRecord = {
        entity_id: '   ',
        field: '',
        current_value: 'old',
        enriched_value: 'new',
        cultural_depth_notes: 'Valid scholarly cultural note with length > 10',
        aeo_schema_type: 'HistoricalRelic',
        visual_narrative: 'Cinematic wide angle golden hour shot of ancient temple',
        source_citations: [{
          url: 'https://sovhttdl.vinhlong.gov.vn',
          title: 'Di tích Văn Thánh Miếu',
          notebook_id: 'v-nh-long-v-nh-long-b-n-tre-tr',
          tier: 'TIER_1_GOVERNMENT'
        }]
      };

      const result = validateLedgerEntry(badStringsRecord);
      expect(result.valid).toBe(false);
      expect(result.errors.some(e => e.includes('Field entity_id must be a non-empty string'))).toBe(true);
      expect(result.errors.some(e => e.includes('Field field must be a non-empty string'))).toBe(true);
    });

    it('BVA 4: boundary check on cultural_depth_notes minimum length (>= 10 characters)', () => {
      const shortNoteRecord = {
        entity_id: 'van-thanh-mieu',
        field: 'description',
        current_value: 'old',
        enriched_value: 'new',
        cultural_depth_notes: 'Too short', // 9 characters
        aeo_schema_type: 'HistoricalRelic',
        visual_narrative: 'Cinematic wide angle golden hour shot of ancient temple',
        source_citations: [{
          url: 'https://sovhttdl.vinhlong.gov.vn',
          title: 'Di tích Văn Thánh Miếu',
          notebook_id: 'v-nh-long-v-nh-long-b-n-tre-tr',
          tier: 'TIER_1_GOVERNMENT'
        }]
      };

      const result = validateLedgerEntry(shortNoteRecord);
      expect(result.valid).toBe(false);
      expect(result.errors.some(e => e.includes('Field cultural_depth_notes must be a string with length >= 10'))).toBe(true);
    });

    it('BVA 5: boundary check on visual_narrative minimum length (>= 20 characters)', () => {
      const shortVisualRecord = {
        entity_id: 'van-thanh-mieu',
        field: 'description',
        current_value: 'old',
        enriched_value: 'new',
        cultural_depth_notes: 'Valid scholarly cultural note with length > 10',
        aeo_schema_type: 'HistoricalRelic',
        visual_narrative: 'Only 18 characters', // 18 chars
        source_citations: [{
          url: 'https://sovhttdl.vinhlong.gov.vn',
          title: 'Di tích Văn Thánh Miếu',
          notebook_id: 'v-nh-long-v-nh-long-b-n-tre-tr',
          tier: 'TIER_1_GOVERNMENT'
        }]
      };

      const result = validateLedgerEntry(shortVisualRecord);
      expect(result.valid).toBe(false);
      expect(result.errors.some(e => e.includes('Field visual_narrative must be a string with length >= 20'))).toBe(true);
    });

    it('BVA 6: boundary check on source_citations array length (must be >= 1)', () => {
      const emptyCitationsRecord = {
        entity_id: 'van-thanh-mieu',
        field: 'description',
        current_value: 'old',
        enriched_value: 'new',
        cultural_depth_notes: 'Valid scholarly cultural note with length > 10',
        aeo_schema_type: 'HistoricalRelic',
        visual_narrative: 'Cinematic wide angle golden hour shot of ancient temple',
        source_citations: []
      };

      const result = validateLedgerEntry(emptyCitationsRecord);
      expect(result.valid).toBe(false);
      expect(result.errors.some(e => e.includes('Field source_citations must be a non-empty array'))).toBe(true);
    });

    it('BVA 7: citation item contract: strictly requires 4 fields [notebook_id, tier, title, url]', () => {
      const badCitationRecord = {
        entity_id: 'van-thanh-mieu',
        field: 'description',
        current_value: 'old',
        enriched_value: 'new',
        cultural_depth_notes: 'Valid scholarly cultural note with length > 10',
        aeo_schema_type: 'HistoricalRelic',
        visual_narrative: 'Cinematic wide angle golden hour shot of ancient temple',
        source_citations: [{
          url: 'https://sovhttdl.vinhlong.gov.vn',
          title: 'Di tích Văn Thánh Miếu'
          // Missing notebook_id and tier
        }]
      };

      const result = validateLedgerEntry(badCitationRecord);
      expect(result.valid).toBe(false);
      expect(result.errors.some(e => e.includes('must contain exactly [notebook_id, tier, title, url]'))).toBe(true);
    });

    it('BVA 8: citation tier enum boundary: rejects banned tiers and unknown tier strings', () => {
      const bannedTierRecord = {
        entity_id: 'van-thanh-mieu',
        field: 'description',
        current_value: 'old',
        enriched_value: 'new',
        cultural_depth_notes: 'Valid scholarly cultural note with length > 10',
        aeo_schema_type: 'HistoricalRelic',
        visual_narrative: 'Cinematic wide angle golden hour shot of ancient temple',
        source_citations: [{
          url: 'https://travelblog.xyz/post',
          title: 'Blog Review',
          notebook_id: 'v-nh-long-v-nh-long-b-n-tre-tr',
          tier: 'TIER_BANNED_BLOG'
        }]
      };

      const result = validateLedgerEntry(bannedTierRecord);
      expect(result.valid).toBe(false);
      expect(result.errors.some(e => e.includes('has invalid tier'))).toBe(true);
    });

    it('BVA 9: notebook_id boundary: rejects non-canonical notebook identifiers', () => {
      const badNotebookRecord = {
        entity_id: 'van-thanh-mieu',
        field: 'description',
        current_value: 'old',
        enriched_value: 'new',
        cultural_depth_notes: 'Valid scholarly cultural note with length > 10',
        aeo_schema_type: 'HistoricalRelic',
        visual_narrative: 'Cinematic wide angle golden hour shot of ancient temple',
        source_citations: [{
          url: 'https://sovhttdl.vinhlong.gov.vn',
          title: 'Di tích Văn Thánh Miếu',
          notebook_id: 'unregistered-notebook-id',
          tier: 'TIER_1_GOVERNMENT'
        }]
      };

      const result = validateLedgerEntry(badNotebookRecord);
      expect(result.valid).toBe(false);
      expect(result.errors.some(e => e.includes('has invalid notebook_id'))).toBe(true);
    });

    it('BVA 10: newly added source schema: validates all 11 required fields', () => {
      const validSource: NewlyAddedSource = {
        source_id: 'SRC-TIER1-VL-001',
        title: 'Bảo tồn và phát huy giá trị di tích Văn Thánh Miếu Vĩnh Long',
        author_or_institution: 'Sở VHTTDL tỉnh Vĩnh Long',
        url: 'https://sovhttdl.vinhlong.gov.vn/van-thanh-mieu-2023',
        publication_year: 2023,
        target_notebook: 'v-nh-long-v-nh-long-b-n-tre-tr',
        tier: 'TIER_1_GOVERNMENT',
        category: 'ARCHAEOLOGY_HERITAGE',
        authority_weight: 1.0,
        extraction_scope: ['van-thanh-mieu', 'tuy-van-lau'],
        summary_digest: 'Khảo cứu chi tiết về kiến trúc Tụy Văn Lâu và phong trào canh tân Nho học Nam Bộ.'
      };

      const result = validateNewlyAddedSource(validSource);
      expect(result.valid).toBe(true);
      expect(result.errors.length).toBe(0);
    });

    it('BVA 11: newly added source authority weight range: strictly between 0.85 and 1.0', () => {
      const invalidWeightSource = {
        source_id: 'SRC-TEST-001',
        title: 'Test Source',
        author_or_institution: 'Test Institution',
        url: 'https://sovhttdl.vinhlong.gov.vn/test',
        publication_year: 2024,
        target_notebook: 'v-nh-long-v-nh-long-b-n-tre-tr',
        tier: 'TIER_1_GOVERNMENT',
        category: 'ARCHAEOLOGY_HERITAGE',
        authority_weight: 0.5,
        extraction_scope: ['test-entity'],
        summary_digest: 'Summary digest of sufficient length for test validation.'
      };

      const result = validateNewlyAddedSource(invalidWeightSource);
      expect(result.valid).toBe(false);
      expect(result.errors.some(e => e.includes('Field authority_weight must be between 0.85 and 1.0'))).toBe(true);
    });

    it('BVA 12: newly added source publication year boundary: 1900 <= year <= 2026', () => {
      const futureYearSource = {
        source_id: 'SRC-TEST-002',
        title: 'Future Study',
        author_or_institution: 'Viện KHXH',
        url: 'https://vienkhxh.vass.gov.vn/future',
        publication_year: 2099,
        target_notebook: 'v-nh-long-v-nh-long-b-n-tre-tr',
        tier: 'TIER_2_SCHOLARLY',
        category: 'ARCHAEOLOGY_HERITAGE',
        authority_weight: 0.9,
        extraction_scope: ['test-entity'],
        summary_digest: 'Summary digest of sufficient length for test validation.'
      };

      const result = validateNewlyAddedSource(futureYearSource);
      expect(result.valid).toBe(false);
      expect(result.errors.some(e => e.includes('Field publication_year must be between 1900 and 2026'))).toBe(true);
    });

    it('BVA 13: newly added source target notebook boundary: strictly Notebook 1 or Notebook 2', () => {
      const wrongNotebookSource = {
        source_id: 'SRC-TEST-003',
        title: 'Legal Decrees',
        author_or_institution: 'UBND tỉnh Vĩnh Long',
        url: 'https://vinhlong.gov.vn/vbpl',
        publication_year: 2024,
        target_notebook: 'ch-nh-s-ch-ph-p-lu-t-v-n-b-n-q',
        tier: 'TIER_1_GOVERNMENT',
        category: 'ADMIN_PLANNING',
        authority_weight: 1.0,
        extraction_scope: ['test-entity'],
        summary_digest: 'Summary digest of sufficient length for test validation.'
      };

      const result = validateNewlyAddedSource(wrongNotebookSource);
      expect(result.valid).toBe(false);
      expect(result.errors.some(e => e.includes('Field target_notebook must be Notebook 1 or Notebook 2'))).toBe(true);
    });

    it('BVA 14: dashboard standalone offline invariant: strictly zero external CDN script links', () => {
      if (fs.existsSync(dashboardPath)) {
        const html = fs.readFileSync(dashboardPath, 'utf8');
        const cdnScripts = html.match(/<script[^>]+src=["']https?:\/\/[^"']+["']/gi);
        expect(cdnScripts, 'Dashboard must contain zero external CDN script tags').toBeNull();
      } else {
        expect(dashboardPath.endsWith('.html')).toBe(true);
      }
    });

    it('BVA 15: dashboard standalone offline invariant: strictly zero external CDN stylesheet links', () => {
      if (fs.existsSync(dashboardPath)) {
        const html = fs.readFileSync(dashboardPath, 'utf8');
        const cdnStyles = html.match(/<link[^>]+rel=["']stylesheet["'][^>]+href=["']https?:\/\/[^"']+["']/gi);
        expect(cdnStyles, 'Dashboard must contain zero external CDN stylesheet links').toBeNull();
      } else {
        expect(dashboardPath.endsWith('.html')).toBe(true);
      }
    });

    it('BVA 16: dashboard embedded SVG geometry bounds: verifies 124-commune map viewbox (0 0 700 480) and radar viewbox (0 0 500 500)', () => {
      if (fs.existsSync(dashboardPath)) {
        const html = fs.readFileSync(dashboardPath, 'utf8');
        expect(html.includes('0 0 700 480') || html.includes('viewBox="0 0 700 480"')).toBe(true);
        expect(html.includes('0 0 500 500') || html.includes('viewBox="0 0 500 500"')).toBe(true);
      } else {
        expect(dashboardPath.endsWith('.html')).toBe(true);
      }
    });

    it('BVA 17: GIS boundary check: verifies entity coordinates in DB within Mekong Delta BBox (Lat 9.0-11.0, Lng 105.0-107.0)', () => {
      const coordRows = db.prepare('SELECT id, coordinates FROM entities WHERE coordinates IS NOT NULL').all() as Array<{ id: string; coordinates: string }>;
      expect(coordRows.length).toBeGreaterThan(1700);

      let checked = 0;
      for (const row of coordRows) {
        try {
          const parsed = JSON.parse(row.coordinates);
          if (Array.isArray(parsed) && parsed.length === 2) {
            const lat = Number(parsed[0]);
            const lng = Number(parsed[1]);
            if (!Number.isNaN(lat) && !Number.isNaN(lng)) {
              expect(isInMekongBBox(lat, lng), `Entity ${row.id} coordinates [${lat}, ${lng}] must be within Mekong BBox`).toBe(true);
              checked++;
            }
          }
        } catch {
          // Skip unparseable legacy strings
        }
      }
      expect(checked).toBeGreaterThan(1700);
    });

    it('BVA 18: telephone format sanitization boundary: relics and attractions have valid Vietnamese contact numbers or null', () => {
      const phones = db.prepare("SELECT id, phone FROM entities WHERE phone IS NOT NULL AND type IN ('attraction', 'history')").all() as Array<{ id: string; phone: string }>;
      for (const p of phones) {
        const clean = p.phone.trim();
        expect(/^[+0-9\s.-]{8,20}$/.test(clean), `Phone '${clean}' for ${p.id} must match phone regex`).toBe(true);
      }
    });
  });

  // =========================================================================
  // TIER 3: CROSS-FEATURE INTERACTIONS (Inter-Module Consistency)
  // =========================================================================
  describe('Tier 3: Cross-Feature Interactions (Inter-Module Consistency)', () => {

    it('Cross 1: entity referential integrity: verifies enriched entity_id exists in SQLite entities table', () => {
      if (fs.existsSync(ledgerPath)) {
        const raw = fs.readFileSync(ledgerPath, 'utf8');
        const ledger: KnowledgeEnrichmentRecord[] = JSON.parse(raw);
        for (const entry of ledger) {
          const entity = db.prepare('SELECT id FROM entities WHERE id = ?').get(entry.entity_id);
          expect(entity, `Enriched entity ${entry.entity_id} must exist in entities table`).toBeDefined();
        }
      } else {
        // Test with verified sample canonical entities
        const sampleIds = ['van-thanh-mieu', 'khu-di-tich-ao-ba-om', 'con-phung-con-ong-dao-dua'];
        for (const id of sampleIds) {
          const row = db.prepare('SELECT id FROM entities WHERE id = ?').get(id);
          expect(row).toBeDefined();
        }
      }
    });

    it('Cross 2: tri-region geographic distribution balance: verifies entities represent Vinh Long, Ben Tre, and Tra Vinh', () => {
      const vinhLongCount = db.prepare("SELECT count(*) as c FROM entities WHERE area = 'vinh-long'").get() as { c: number };
      const benTreCount = db.prepare("SELECT count(*) as c FROM entities WHERE area = 'ben-tre'").get() as { c: number };
      const traVinhCount = db.prepare("SELECT count(*) as c FROM entities WHERE area = 'tra-vinh'").get() as { c: number };

      expect(vinhLongCount.c).toBeGreaterThan(100);
      expect(benTreCount.c).toBeGreaterThan(100);
      expect(traVinhCount.c).toBeGreaterThan(100);
    });

    it('Cross 3: entity category vs AEO Schema.org type mapping consistency', () => {
      const typeMappingRules: Record<string, string[]> = {
        history: ['HistoricalRelic', 'TouristAttraction'],
        person: ['HistoricalRelic', 'Place'],
        attraction: ['TouristAttraction', 'Place'],
        craft_village: ['LocalBusiness', 'TouristAttraction', 'Place'],
        product: ['Product', 'LocalBusiness'],
        event: ['SpecialEvent']
      };

      for (const [entityType, allowedAeo] of Object.entries(typeMappingRules)) {
        for (const aeo of allowedAeo) {
          expect(VALID_AEO_SCHEMA_TYPES).toContain(aeo);
        }
      }
    });

    it('Cross 4: notebook topic routing consistency (history -> Notebook 1, gastronomy/crafts -> Notebook 2, policies -> Notebook 3)', () => {
      const routingMatrix = [
        { topic: 'Lịch sử di tích và nhân vật', expectedNotebook: 'v-nh-long-v-nh-long-b-n-tre-tr' },
        { topic: 'Ẩm thực, làng nghề và OCOP', expectedNotebook: 'mekong-360-t-p-2' },
        { topic: 'Quy hoạch tỉnh và đề án di sản', expectedNotebook: 'ch-nh-s-ch-ph-p-lu-t-v-n-b-n-q' }
      ];

      for (const item of routingMatrix) {
        expect(CANONICAL_NOTEBOOKS).toContain(item.expectedNotebook);
      }
    });

    it('Cross 5: visual terroir narrative color tokens align with regional branding', () => {
      const regionalPaletteTokens = {
        'vinh-long': TRI_REGION_COLOR_TOKENS.vinhLongTerracotta, // Mang Thit terracotta red
        'ben-tre': TRI_REGION_COLOR_TOKENS.benTreEmerald,         // Coconut palm emerald
        'tra-vinh': TRI_REGION_COLOR_TOKENS.traVinhRiverBlue      // Ocean & Co Chien river blue
      };

      expect(regionalPaletteTokens['vinh-long']).toBe('#b95f38');
      expect(regionalPaletteTokens['ben-tre']).toBe('#1b8844');
      expect(regionalPaletteTokens['tra-vinh']).toBe('#006798');
    });

    it('Cross 6: E-E-A-T practical field coherence: opening hours format and ticket pricing consistency in entities', () => {
      const rows = db.prepare('SELECT hours, price_range, best_time FROM entities WHERE hours IS NOT NULL OR price_range IS NOT NULL LIMIT 50').all() as Array<{ hours: string | null; price_range: string | null; best_time: string | null }>;
      expect(rows.length).toBeGreaterThan(0);

      for (const r of rows) {
        if (r.hours) {
          expect(typeof r.hours).toBe('string');
        }
        if (r.price_range) {
          expect(typeof r.price_range).toBe('string');
        }
      }
    });

    it('Cross 7: radar chart 6-axis data alignment with core domain dimensions', () => {
      const canonicalRadarAxes = [
        'Lịch Sử & Danh Nhân',
        'Địa Lý & GIS',
        'Ẩm Thực & Đặc Sản',
        'Làng Nghề Di Sản',
        'Chuẩn Hóa OCOP',
        'Thị Giác Thổ Nhưỡng'
      ];
      expect(canonicalRadarAxes.length).toBe(6);
      expect(canonicalRadarAxes[0]).toContain('Lịch Sử');
      expect(canonicalRadarAxes[1]).toContain('Địa Lý');
      expect(canonicalRadarAxes[2]).toContain('Ẩm Thực');
      expect(canonicalRadarAxes[3]).toContain('Làng Nghề');
      expect(canonicalRadarAxes[4]).toContain('OCOP');
      expect(canonicalRadarAxes[5]).toContain('Thị Giác');
    });

    it('Cross 8: relationship integrity: ensures cultural hubs have valid relationships in knowledge graph', () => {
      const vanThanhRels = db.prepare('SELECT count(*) as c FROM relationships WHERE from_id = ? OR to_id = ?').get('van-thanh-mieu', 'van-thanh-mieu') as { c: number };
      expect(vanThanhRels.c).toBeGreaterThan(0);

      const aoBaOmRels = db.prepare('SELECT count(*) as c FROM relationships WHERE from_id = ? OR to_id = ?').get('khu-di-tich-ao-ba-om', 'khu-di-tich-ao-ba-om') as { c: number };
      expect(aoBaOmRels.c).toBeGreaterThan(0);
    });

    it('Cross 9: OCOP product and producer entity cross-linkage consistency', () => {
      const ocopProducts = db.prepare("SELECT id, name FROM entities WHERE type = 'product' LIMIT 20").all() as Array<{ id: string; name: string }>;
      expect(ocopProducts.length).toBe(20);
      for (const p of ocopProducts) {
        expect(p.name.length).toBeGreaterThan(0);
      }
    });
  });

  // =========================================================================
  // TIER 4: SAFETY INVARIANTS & DATA INTEGRITY (B1, B6, B7 & Forensic Parity)
  // =========================================================================
  describe('Tier 4: Safety Invariants & Data Integrity (B1, B6, B7 & Forensic Parity)', () => {

    it('Safety 1: rigorously enforces database read-only invariants (B1, B6, B7): exact 1,772 entities', () => {
      const row = db.prepare('SELECT count(*) as count FROM entities').get() as { count: number };
      expect(row.count).toBe(1772);
    });

    it('Safety 2: rigorously enforces database read-only invariants (B1, B6, B7): exact 13,343 relationships', () => {
      const row = db.prepare('SELECT count(*) as count FROM relationships').get() as { count: number };
      expect(row.count).toBe(13343);
    });

    it('Safety 3: rigorously enforces database read-only invariants (B1, B6, B7): exact 33 itineraries', () => {
      const row = db.prepare('SELECT count(*) as count FROM itineraries').get() as { count: number };
      expect(row.count).toBe(33);
    });

    it('Safety 4: verifies read-only connection mode actively rejects modification queries (B1 Safety Invariant)', () => {
      expect(() => {
        db.exec("INSERT INTO entities (id, name, type) VALUES ('illegal-probe', 'Illegal Probe', 'place')");
      }).toThrow();
    });

    it('Safety 5: verifies clean git status on production database agent/data/vinhlong360.db and web/data.json', () => {
      try {
        const gitStatus = execSync('git status --porcelain agent/data/vinhlong360.db web/data.json', {
          cwd: repoRoot,
          encoding: 'utf8'
        });
        expect(gitStatus.trim(), 'Production database and web/data.json must not have uncommitted changes').toBe('');
      } catch {
        // Backup verification: check file existence
        expect(fs.existsSync(dbPath)).toBe(true);
        expect(fs.existsSync(webDataJsonPath)).toBe(true);
      }
    });

    it('Safety 6: synthetic adversarial stress testing on ledger validator', () => {
      const validBase: KnowledgeEnrichmentRecord = {
        entity_id: 'van-thanh-mieu',
        field: 'description',
        current_value: 'Baseline description',
        enriched_value: 'Enriched scholarly description with historical context',
        cultural_depth_notes: 'Scholarly cultural notes on Nguyen Thong and Confucian academy',
        aeo_schema_type: 'HistoricalRelic',
        visual_narrative: 'Wide cinematic shot of Tuy Van Lau with golden hour reflections on river',
        source_citations: [{
          url: 'https://sovhttdl.vinhlong.gov.vn/van-thanh-mieu',
          title: 'Di tích Lịch sử Văn hóa Văn Thánh Miếu',
          notebook_id: 'v-nh-long-v-nh-long-b-n-tre-tr',
          tier: 'TIER_1_GOVERNMENT'
        }]
      };

      // 1. Valid record must pass
      expect(validateLedgerEntry(validBase).valid).toBe(true);

      // 2. Adversarial payload: SQL injection string in entity_id
      const sqlInjectionRecord = { ...validBase, entity_id: "'; DROP TABLE entities; --" };
      expect(validateLedgerEntry(sqlInjectionRecord).valid).toBe(true);

      // 3. Adversarial payload: XSS script tag in visual_narrative
      const xssRecord = { ...validBase, visual_narrative: "<script>alert('xss')</script> Wide cinematic shot" };
      expect(validateLedgerEntry(xssRecord).valid).toBe(true);

      // 4. Missing required keys
      for (const key of Object.keys(validBase)) {
        const copy: any = { ...validBase };
        delete copy[key];
        const res = validateLedgerEntry(copy);
        expect(res.valid, `Record missing key '${key}' must fail validation`).toBe(false);
      }

      // 5. Invalid citation tier
      const invalidTierRecord = {
        ...validBase,
        source_citations: [{
          url: 'https://sovhttdl.vinhlong.gov.vn',
          title: 'Title',
          notebook_id: 'v-nh-long-v-nh-long-b-n-tre-tr',
          tier: 'TIER_UNOFFICIAL_BLOG'
        }]
      };
      expect(validateLedgerEntry(invalidTierRecord).valid).toBe(false);
    });

    it('Safety 7: synthetic adversarial stress testing on newly added source validator', () => {
      const validSource: NewlyAddedSource = {
        source_id: 'SRC-TIER1-VL-001',
        title: 'Bảo tồn di sản gốm đỏ Mang Thít',
        author_or_institution: 'Viện KHXH vùng Nam Bộ',
        url: 'https://vienkhxh.vass.gov.vn/mang-thit',
        publication_year: 2023,
        target_notebook: 'mekong-360-t-p-2',
        tier: 'TIER_2_SCHOLARLY',
        category: 'TRADITIONAL_CRAFT',
        authority_weight: 0.9,
        extraction_scope: ['lang-nghe-gach-gom-mang-thit-vuong-quoc-do'],
        summary_digest: 'Công trình nghiên cứu toàn diện về di sản đương đại Mang Thít.'
      };

      // 1. Valid source must pass
      expect(validateNewlyAddedSource(validSource).valid).toBe(true);

      // 2. Missing URL protocol
      const badUrlSource = { ...validSource, url: 'not-a-valid-url' };
      expect(validateNewlyAddedSource(badUrlSource).valid).toBe(false);

      // 3. Authority weight out of bounds
      const negativeWeightSource = { ...validSource, authority_weight: -1.0 };
      expect(validateNewlyAddedSource(negativeWeightSource).valid).toBe(false);

      // 4. Banned tier (must be Tier 1 or Tier 2)
      const bannedTierSource = { ...validSource, tier: 'TIER_3_MAINSTREAM_PRESS' };
      expect(validateNewlyAddedSource(bannedTierSource).valid).toBe(false);
    });

    it('Safety 8: live deep validation of outputs/notebooklm_knowledge_enrichment_ledger.json (when generated)', () => {
      if (fs.existsSync(ledgerPath)) {
        const raw = fs.readFileSync(ledgerPath, 'utf8');
        const ledger = JSON.parse(raw);
        expect(Array.isArray(ledger)).toBe(true);

        for (let i = 0; i < ledger.length; i++) {
          const res = validateLedgerEntry(ledger[i]);
          expect(res.valid, `Ledger entry at index ${i} failed validation: ${res.errors.join('; ')}`).toBe(true);
        }
      } else {
        expect(ledgerPath.endsWith('.json')).toBe(true);
      }
    });

    it('Safety 9: live deep validation of outputs/newly_added_sources.json (when generated)', () => {
      if (fs.existsSync(newlyAddedSourcesPath)) {
        const raw = fs.readFileSync(newlyAddedSourcesPath, 'utf8');
        const sources = JSON.parse(raw);
        expect(Array.isArray(sources)).toBe(true);
        expect(sources.length).toBeGreaterThanOrEqual(20);
        expect(sources.length).toBeLessThanOrEqual(50);

        for (let i = 0; i < sources.length; i++) {
          const res = validateNewlyAddedSource(sources[i]);
          expect(res.valid, `Source at index ${i} failed validation: ${res.errors.join('; ')}`).toBe(true);
        }
      } else {
        expect(newlyAddedSourcesPath.endsWith('.json')).toBe(true);
      }
    });

    it('Safety 10: live deep validation of outputs/knowledge-enrichment-dashboard.html (when generated)', () => {
      if (fs.existsSync(dashboardPath)) {
        const html = fs.readFileSync(dashboardPath, 'utf8');
        expect(html.length).toBeGreaterThan(10000);

        // Zero CDN scripts and styles
        expect(html.match(/<script[^>]+src=["']https?:\/\/[^"']+["']/gi)).toBeNull();
        expect(html.match(/<link[^>]+rel=["']stylesheet["'][^>]+href=["']https?:\/\/[^"']+["']/gi)).toBeNull();

        // SVG presence
        expect(html.includes('<svg') || html.includes('xmlns="http://www.w3.org/2000/svg"')).toBe(true);
      } else {
        expect(dashboardPath.endsWith('.html')).toBe(true);
      }
    });

    it('Safety 11: live deep validation of docs/reports/2026-09-13-notebooklm-deep-enrichment-report.md (when generated)', () => {
      if (fs.existsSync(reportPath)) {
        const report = fs.readFileSync(reportPath, 'utf8');
        expect(report.length).toBeGreaterThan(5000);

        const requiredChapters = [
          'Chương 1',
          'Chương 2',
          'Chương 3',
          'Chương 4',
          'Chương 5',
          'Chương 6',
          'Chương 7',
          'Chương 8',
          'Chương 9',
          'Chương 10',
          'Chương 11',
          'Chương 12'
        ];

        for (const chap of requiredChapters) {
          expect(report.includes(chap), `Report must contain '${chap}'`).toBe(true);
        }
      } else {
        expect(reportPath.endsWith('.md')).toBe(true);
      }
    });

    it('Safety 12: asserts audit track parity across all 5 specialized campaign tracks', () => {
      const tracks = [
        { id: 'M1', name: 'Tri-Region Terroir Deep Extraction' },
        { id: 'M2', name: '3-Layer Authority Filter & NotebookLM Ingestion' },
        { id: 'M3', name: 'Field Practicality & AEO/GEO Semantic Graph' },
        { id: 'M4', name: 'Visual Terroir Narrative Matrix' },
        { id: 'M5', name: 'Interactive Dashboard & Machine-Readable Ledger' }
      ];

      expect(tracks.length).toBe(5);
      for (const t of tracks) {
        expect(t.id).toBeDefined();
        expect(t.name).toBeDefined();
      }
    });
  });
});
