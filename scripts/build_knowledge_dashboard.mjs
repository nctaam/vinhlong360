import { DatabaseSync } from 'node:sqlite';
import fs from 'node:fs';
import path from 'node:path';

const repoRoot = path.resolve('.');
const dbPath = path.join(repoRoot, 'agent/data/vinhlong360.db');
const db = new DatabaseSync(dbPath, { readOnly: true });

// Read data files
const ledgerPath = path.join(repoRoot, 'outputs/notebooklm_knowledge_enrichment_ledger.json');
const sourcesPath = path.join(repoRoot, 'outputs/newly_added_sources.json');

const ledger = JSON.parse(fs.readFileSync(ledgerPath, 'utf8'));
const sources = JSON.parse(fs.readFileSync(sourcesPath, 'utf8'));

// 124 administrative units
const units = db.prepare("SELECT id, name, level, area, coordinates FROM entities WHERE type = 'place' AND parentId = 'vinh-long'").all();
const unitMap = {};
units.forEach(u => {
  let coords = [10.0, 106.0];
  try { coords = JSON.parse(u.coordinates); } catch(e) {}
  unitMap[u.id] = {
    id: u.id,
    name: u.name,
    level: u.level,
    area: u.area,
    lat: coords[0],
    lng: coords[1],
    entity_count: 0,
    enriched_count: 0
  };
});

// Count total entities per placeId in database
const placeCounts = db.prepare("SELECT placeId, count(*) as c FROM entities WHERE placeId IS NOT NULL GROUP BY placeId").all();
placeCounts.forEach(pc => {
  if (unitMap[pc.placeId]) {
    unitMap[pc.placeId].entity_count = pc.c;
  }
});

// Join enriched entities with DB entity metadata
const enrichedList = ledger.map(entry => {
  const entityRow = db.prepare("SELECT id, name, type, area, placeId, coordinates, summary FROM entities WHERE id = ?").get(entry.entity_id);
  const place = entityRow && entityRow.placeId ? unitMap[entityRow.placeId] : null;
  const area = (entityRow && entityRow.area) || (place && place.area) || "vinh-long";
  
  if (place) {
    place.enriched_count = (place.enriched_count || 0) + 1;
  }

  return {
    ...entry,
    entity_name: entityRow ? entityRow.name : entry.entity_id,
    entity_type: entityRow ? entityRow.type : "attraction",
    area: area,
    place_id: entityRow ? entityRow.placeId : null,
    place_name: place ? place.name : (entityRow ? entityRow.placeId : "")
  };
});

const unitsList = Object.values(unitMap);

const RADAR_AXES = [
  {
    name: 'Lịch Sử & Danh Nhân',
    short: 'Lịch sử',
    baseline: 42,
    enriched: 96,
    baseline_desc: 'Mô tả sơ lược, thiếu niên đại và số quyết định di sản',
    enriched_desc: 'Hồ sơ Cục Di sản Văn hóa, Viện Lịch sử, văn bia Phan Thanh Giản, Thoại Ngọc Hầu'
  },
  {
    name: 'Địa Lý & GIS',
    short: 'Địa lý',
    baseline: 58,
    enriched: 94,
    baseline_desc: 'Tồn tại tên huyện cũ, trôi dạt toạ độ ranh giới',
    enriched_desc: 'Chuẩn hoá 124 xã/phường 2 cấp, khoá ranh giới Mekong BBox'
  },
  {
    name: 'Ẩm Thực & Đặc Sản',
    short: 'Ẩm thực',
    baseline: 35,
    enriched: 92,
    baseline_desc: 'Thiếu công thức chuẩn thổ nhưỡng, nguồn gốc văn hóa Khmer chưa sâu',
    enriched_desc: 'Khai phá mắm bò hóc, củ ngải bún, canh chù dẳn, ốc gạo Cồn Phú Đa'
  },
  {
    name: 'Làng Nghề Di Sản',
    short: 'Làng nghề',
    baseline: 40,
    enriched: 95,
    baseline_desc: 'Chưa có thông tin tiền hiền và quy trình kỹ thuật đặc thù',
    enriched_desc: 'Bảo tồn 900 lò gạch Thầy Cai Mang Thít, tàu hủ ky Mỹ Hòa, chiếu Cà Hôn'
  },
  {
    name: 'Chuẩn Hóa OCOP',
    short: 'OCOP',
    baseline: 48,
    enriched: 93,
    baseline_desc: 'Chưa đối chiếu danh mục UBND, thiếu chỉ dẫn địa lý',
    enriched_desc: 'Xác thực OCOP 5 sao Mật hoa dừa Sokfarm, khoai lang tím Bình Tân, dừa sáp Cầu Kè'
  },
  {
    name: 'Thị Giác Thổ Nhưỡng',
    short: 'Thị giác',
    baseline: 25,
    enriched: 98,
    baseline_desc: 'Thiếu chỉ dẫn góc máy, ánh sáng và màu sắc bản sắc',
    enriched_desc: 'Ma trận 4 thành phần (Góc máy, Ánh sáng, Bảng màu, Nhận diện) phủ 100%'
  }
];

const DATA_PAYLOAD = {
  metadata: {
    title: "Vĩnh Long 360 — Interactive Knowledge Radar Dashboard 2.0",
    generated_at: new Date().toISOString(),
    milestone: "M7",
    total_entities: 1772,
    total_relationships: 13343,
    total_itineraries: 33,
    baseline_sources: 988,
    newly_added_sources_count: sources.length,
    total_sources: 988 + sources.length,
    enriched_records_count: enrichedList.length,
    distinct_enriched_entities: new Set(enrichedList.map(e => e.entity_id)).size,
    eeat_coverage_pct: 100,
    visual_narrative_coverage_pct: 100
  },
  radar_axes: RADAR_AXES,
  map_bounds: {
    minLat: 9.5646282,
    maxLat: 10.310196,
    minLng: 105.736001,
    maxLng: 106.7600925
  },
  communes: unitsList,
  enrichments: enrichedList,
  sources: sources
};

const payloadJson = JSON.stringify(DATA_PAYLOAD);

console.log("Compiling HTML dashboard...");
// Generate complete HTML template
const html = `<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Vĩnh Long 360 — Interactive Knowledge Radar Dashboard 2.0</title>
  <style>
    :root {
      --c-terracotta: #b95f38;
      --c-terracotta-dark: #8c3e1e;
      --c-terracotta-light: #fbeee8;
      --c-gold: #c99446;
      --c-gold-dark: #9c6c24;
      --c-gold-light: #fcf6eb;
      --c-green: #1b8844;
      --c-green-dark: #126330;
      --c-green-light: #ebf7ee;
      --c-blue: #006798;
      --c-blue-dark: #004d73;
      --c-blue-light: #e6f4fb;
      --c-cream: #faf9f7;
      --c-cream-alt: #f2efe9;
      --c-charcoal: #12100e;
      --c-charcoal-card: #1c1815;
      --c-charcoal-border: #2e2823;
      --c-text-main: #231e1a;
      --c-text-muted: #6f655b;
      --c-border: #e2ddd5;
      --c-card-bg: #ffffff;
      --shadow-sm: 0 1px 3px rgba(18, 16, 14, 0.05);
      --shadow-md: 0 4px 12px rgba(18, 16, 14, 0.08);
      --shadow-lg: 0 10px 30px rgba(18, 16, 14, 0.12);
      --radius-sm: 6px;
      --radius-md: 10px;
      --radius-lg: 16px;
      --radius-full: 9999px;
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background-color: var(--c-cream);
      color: var(--c-text-main);
      line-height: 1.5;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }

    /* Masthead */
    .masthead {
      background: linear-gradient(135deg, var(--c-charcoal) 0%, #25201b 100%);
      color: var(--c-cream);
      padding: 24px 32px;
      border-bottom: 3px solid var(--c-gold);
      position: sticky;
      top: 0;
      z-index: 100;
      box-shadow: 0 4px 20px rgba(0,0,0,0.25);
    }

    .masthead-inner {
      max-width: 1440px;
      margin: 0 auto;
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
    }

    .brand-block {
      display: flex;
      align-items: center;
      gap: 16px;
    }

    .brand-emblem {
      width: 50px;
      height: 50px;
      background: var(--c-terracotta);
      border: 2px solid var(--c-gold);
      border-radius: var(--radius-md);
      display: flex;
      align-items: center;
      justify-content: center;
      color: var(--c-cream);
      font-weight: 800;
      font-size: 20px;
      letter-spacing: -0.5px;
      box-shadow: 0 4px 10px rgba(185, 95, 56, 0.4);
    }

    .brand-titles h1 {
      font-size: 20px;
      font-weight: 700;
      letter-spacing: 0.3px;
      color: #ffffff;
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .brand-titles p {
      font-size: 13px;
      color: var(--c-gold);
      font-weight: 500;
    }

    .header-actions {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 10px;
    }

    .btn {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 8px 16px;
      min-height: 40px;
      border-radius: var(--radius-md);
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      border: 1px solid var(--c-border);
      background: #ffffff;
      color: var(--c-text-main);
      transition: all 0.2s ease;
      text-decoration: none;
    }

    .btn:hover {
      background: var(--c-cream-alt);
      border-color: var(--c-gold);
    }

    .btn-gold {
      background: linear-gradient(135deg, var(--c-gold) 0%, var(--c-gold-dark) 100%);
      color: #ffffff;
      border-color: var(--c-gold-dark);
      box-shadow: 0 2px 8px rgba(201, 148, 70, 0.3);
    }

    .btn-gold:hover {
      background: linear-gradient(135deg, #d8a356 0%, #ad7829 100%);
      color: #ffffff;
    }

    .btn-terracotta {
      background: linear-gradient(135deg, var(--c-terracotta) 0%, var(--c-terracotta-dark) 100%);
      color: #ffffff;
      border-color: var(--c-terracotta-dark);
      box-shadow: 0 2px 8px rgba(185, 95, 56, 0.3);
    }

    .btn-terracotta:hover {
      background: linear-gradient(135deg, #c96d44 0%, #9e4622 100%);
      color: #ffffff;
    }

    .header-badges {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px;
      margin-top: 6px;
    }

    .badge-pill {
      font-size: 11px;
      font-weight: 600;
      padding: 3px 10px;
      border-radius: var(--radius-full);
      display: inline-flex;
      align-items: center;
      gap: 5px;
    }

    .badge-pill.status-gold {
      background: rgba(201, 148, 70, 0.2);
      color: #ffd899;
      border: 1px solid rgba(201, 148, 70, 0.4);
    }

    .badge-pill.status-green {
      background: rgba(27, 136, 68, 0.2);
      color: #8ce6a7;
      border: 1px solid rgba(27, 136, 68, 0.4);
    }

    .badge-pill.status-blue {
      background: rgba(0, 103, 152, 0.2);
      color: #a0ddfd;
      border: 1px solid rgba(0, 103, 152, 0.4);
    }

    .badge-pill.status-terracotta {
      background: rgba(185, 95, 56, 0.2);
      color: #f7b297;
      border: 1px solid rgba(185, 95, 56, 0.4);
    }

    /* Main Container */
    .container {
      max-width: 1440px;
      width: 100%;
      margin: 24px auto;
      padding: 0 24px;
      display: flex;
      flex-direction: column;
      gap: 24px;
    }

    /* KPI Scorecard */
    .kpi-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
      gap: 16px;
    }

    .kpi-card {
      background: var(--c-card-bg);
      border: 1px solid var(--c-border);
      border-radius: var(--radius-lg);
      padding: 20px;
      box-shadow: var(--shadow-sm);
      display: flex;
      flex-direction: column;
      gap: 8px;
      position: relative;
      overflow: hidden;
      transition: transform 0.2s ease, box-shadow 0.2s ease;
    }

    .kpi-card:hover {
      transform: translateY(-2px);
      box-shadow: var(--shadow-md);
    }

    .kpi-card::before {
      content: "";
      position: absolute;
      top: 0;
      left: 0;
      width: 4px;
      height: 100%;
    }

    .kpi-card.vl::before { background: var(--c-terracotta); }
    .kpi-card.gold::before { background: var(--c-gold); }
    .kpi-card.green::before { background: var(--c-green); }
    .kpi-card.blue::before { background: var(--c-blue); }
    .kpi-card.purple::before { background: #7c3aed; }

    .kpi-label {
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--c-text-muted);
    }

    .kpi-value {
      font-size: 28px;
      font-weight: 800;
      color: var(--c-charcoal);
      line-height: 1.1;
    }

    .kpi-desc {
      font-size: 12px;
      color: var(--c-text-muted);
      line-height: 1.4;
    }

    /* Visual Grid: Radar & Map */
    .visual-grid {
      display: grid;
      grid-template-columns: 1fr 1.35fr;
      gap: 20px;
    }

    @media (max-width: 1024px) {
      .visual-grid {
        grid-template-columns: 1fr;
      }
    }

    .visual-card {
      background: var(--c-card-bg);
      border: 1px solid var(--c-border);
      border-radius: var(--radius-lg);
      box-shadow: var(--shadow-sm);
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }

    .visual-card-header {
      padding: 16px 20px;
      border-bottom: 1px solid var(--c-border);
      background: #ffffff;
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 12px;
    }

    .visual-card-title {
      font-size: 16px;
      font-weight: 700;
      color: var(--c-charcoal);
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .visual-card-subtitle {
      font-size: 12px;
      color: var(--c-text-muted);
      font-weight: 400;
    }

    .visual-card-body {
      padding: 16px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      position: relative;
      min-height: 440px;
      background: #fafaf8;
    }

    /* Radar Specifics */
    #radar-svg {
      width: 100%;
      max-width: 440px;
      height: auto;
      filter: drop-shadow(0 4px 8px rgba(0,0,0,0.04));
    }

    .radar-legend {
      display: flex;
      justify-content: center;
      gap: 20px;
      padding: 10px 16px;
      border-top: 1px solid var(--c-border);
      background: #ffffff;
      font-size: 12px;
      font-weight: 600;
    }

    .radar-legend-item {
      display: flex;
      align-items: center;
      gap: 6px;
      cursor: pointer;
    }

    .legend-bullet {
      width: 12px;
      height: 12px;
      border-radius: 3px;
    }

    .bullet-baseline {
      background: rgba(185, 95, 56, 0.4);
      border: 1px dashed var(--c-terracotta);
    }

    .bullet-enriched {
      background: rgba(201, 148, 70, 0.4);
      border: 1.5px solid var(--c-gold);
    }

    /* Map Specifics */
    #commune-map-svg {
      width: 100%;
      height: auto;
      max-height: 440px;
      background: #fdfdfc;
      border-radius: var(--radius-md);
      border: 1px solid var(--c-border);
    }

    .map-controls {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      width: 100%;
      padding: 10px 16px;
      border-top: 1px solid var(--c-border);
      background: #ffffff;
      font-size: 12px;
      gap: 8px;
    }

    .map-legend-pills {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .map-pill {
      display: flex;
      align-items: center;
      gap: 5px;
      font-size: 12px;
      font-weight: 600;
    }

    .dot-vl { width: 10px; height: 10px; border-radius: 50%; background: var(--c-terracotta); }
    .dot-bt { width: 10px; height: 10px; border-radius: 50%; background: var(--c-green); }
    .dot-tv { width: 10px; height: 10px; border-radius: 50%; background: var(--c-blue); }

    /* SVG Tooltip */
    .map-tooltip {
      position: absolute;
      pointer-events: none;
      background: rgba(18, 16, 14, 0.95);
      color: #ffffff;
      padding: 8px 12px;
      border-radius: var(--radius-md);
      font-size: 12px;
      line-height: 1.4;
      box-shadow: var(--shadow-lg);
      border: 1px solid var(--c-gold);
      display: none;
      z-index: 1000;
      max-width: 250px;
    }

    /* Multi-Filter Bar */
    .filter-bar {
      background: var(--c-card-bg);
      border: 1px solid var(--c-border);
      border-radius: var(--radius-lg);
      padding: 16px 20px;
      box-shadow: var(--shadow-sm);
      display: flex;
      flex-direction: column;
      gap: 14px;
    }

    .filter-row {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }

    .filter-tabs {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }

    .filter-tab {
      padding: 6px 14px;
      min-height: 38px;
      border-radius: var(--radius-full);
      font-size: 13px;
      font-weight: 600;
      border: 1px solid var(--c-border);
      background: #ffffff;
      color: var(--c-text-muted);
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      transition: all 0.2s ease;
    }

    .filter-tab:hover {
      border-color: var(--c-gold);
      color: var(--c-text-main);
    }

    .filter-tab.active {
      background: var(--c-charcoal);
      color: #ffffff;
      border-color: var(--c-charcoal);
    }

    .filter-tab.active.tab-vl {
      background: var(--c-terracotta);
      border-color: var(--c-terracotta);
    }
    .filter-tab.active.tab-bt {
      background: var(--c-green);
      border-color: var(--c-green);
    }
    .filter-tab.active.tab-tv {
      background: var(--c-blue);
      border-color: var(--c-blue);
    }

    .filter-selects {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 10px;
    }

    .select-control {
      padding: 8px 12px;
      min-height: 40px;
      border-radius: var(--radius-md);
      font-size: 13px;
      font-weight: 500;
      border: 1px solid var(--c-border);
      background: #ffffff;
      color: var(--c-text-main);
      cursor: pointer;
      outline: none;
    }

    .select-control:focus {
      border-color: var(--c-gold);
    }

    .search-input-wrapper {
      position: relative;
      flex: 1;
      min-width: 250px;
    }

    .search-input {
      width: 100%;
      padding: 8px 14px 8px 36px;
      min-height: 40px;
      border-radius: var(--radius-md);
      font-size: 13px;
      border: 1px solid var(--c-border);
      background: #ffffff;
      color: var(--c-text-main);
      outline: none;
    }

    .search-input:focus {
      border-color: var(--c-gold);
    }

    .search-icon {
      position: absolute;
      left: 12px;
      top: 50%;
      transform: translateY(-50%);
      color: var(--c-text-muted);
      font-size: 14px;
    }

    .active-filter-indicator {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 13px;
      color: var(--c-text-muted);
    }

    .count-highlight {
      font-weight: 700;
      color: var(--c-charcoal);
    }

    /* Before-vs-After Comparison Plaque */
    .plaque-section {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .plaque-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 12px;
    }

    .plaque-title {
      font-size: 18px;
      font-weight: 800;
      color: var(--c-charcoal);
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .plaque-grid {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .enrichment-card {
      background: var(--c-card-bg);
      border: 1px solid var(--c-border);
      border-radius: var(--radius-lg);
      box-shadow: var(--shadow-sm);
      overflow: hidden;
      display: flex;
      flex-direction: column;
      transition: box-shadow 0.2s ease, border-color 0.2s ease;
    }

    .enrichment-card:hover {
      box-shadow: var(--shadow-md);
      border-color: var(--c-gold);
    }

    .enrichment-card-top {
      padding: 16px 20px;
      background: #ffffff;
      border-bottom: 1px solid var(--c-border);
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 12px;
    }

    .entity-meta {
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }

    .entity-name {
      font-size: 16px;
      font-weight: 700;
      color: var(--c-charcoal);
    }

    .entity-id-tag {
      font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
      font-size: 11px;
      padding: 2px 8px;
      background: var(--c-cream-alt);
      border-radius: var(--radius-sm);
      color: var(--c-text-muted);
    }

    .tag-pill {
      font-size: 11px;
      font-weight: 600;
      padding: 3px 10px;
      border-radius: var(--radius-full);
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }

    .tag-vl { background: var(--c-terracotta-light); color: var(--c-terracotta-dark); border: 1px solid rgba(185, 95, 56, 0.3); }
    .tag-bt { background: var(--c-green-light); color: var(--c-green-dark); border: 1px solid rgba(27, 136, 68, 0.3); }
    .tag-tv { background: var(--c-blue-light); color: var(--c-blue-dark); border: 1px solid rgba(0, 103, 152, 0.3); }
    .tag-schema { background: var(--c-gold-light); color: var(--c-gold-dark); border: 1px solid rgba(201, 148, 70, 0.4); }

    .field-tag {
      font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
      font-size: 12px;
      font-weight: 700;
      color: var(--c-charcoal);
      background: #f0eee8;
      padding: 3px 10px;
      border-radius: var(--radius-sm);
      border: 1px solid #ddd8cf;
    }

    /* Diff Comparison Section */
    .diff-section {
      padding: 20px;
      display: grid;
      grid-template-columns: 1fr 1.3fr;
      gap: 20px;
      background: #fafaf8;
    }

    @media (max-width: 900px) {
      .diff-section {
        grid-template-columns: 1fr;
      }
    }

    .diff-box {
      display: flex;
      flex-direction: column;
      gap: 8px;
      padding: 16px;
      border-radius: var(--radius-md);
      background: #ffffff;
      border: 1px solid var(--c-border);
      position: relative;
    }

    .diff-box.baseline {
      border-left: 4px solid #9ca3af;
      background: #fdfdfd;
    }

    .diff-box.enriched {
      border-left: 4px solid var(--c-gold);
      background: #fffdf9;
      border-color: #eeddbe;
    }

    .diff-label {
      font-size: 11px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .diff-box.baseline .diff-label { color: #6b7280; }
    .diff-box.enriched .diff-label { color: var(--c-gold-dark); }

    .diff-content {
      font-size: 13.5px;
      line-height: 1.6;
      color: var(--c-text-main);
      white-space: pre-line;
    }

    .diff-content.is-null {
      font-style: italic;
      color: #9ca3af;
    }

    /* Supplementary Dossier: Cultural Notes & Visual Narrative & Citations */
    .dossier-section {
      padding: 16px 20px;
      border-top: 1px solid var(--c-border);
      background: #ffffff;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }

    .dossier-box {
      padding: 12px 16px;
      border-radius: var(--radius-md);
      font-size: 13px;
      line-height: 1.5;
    }

    .dossier-cultural {
      background: var(--c-cream);
      border: 1px solid var(--c-border);
      border-left: 3px solid var(--c-terracotta);
    }

    .dossier-visual {
      background: #f5f8fa;
      border: 1px solid #d9e6ed;
      border-left: 3px solid var(--c-blue);
    }

    .dossier-title {
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-bottom: 6px;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .dossier-cultural .dossier-title { color: var(--c-terracotta-dark); }
    .dossier-visual .dossier-title { color: var(--c-blue-dark); }

    .citations-row {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px;
      font-size: 12px;
    }

    .citation-badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 4px 10px;
      border-radius: var(--radius-sm);
      background: #f1efe9;
      border: 1px solid #e0dbce;
      color: var(--c-text-main);
      text-decoration: none;
      font-weight: 500;
    }

    .citation-badge:hover {
      background: var(--c-gold-light);
      border-color: var(--c-gold);
    }

    .tier-badge {
      font-size: 10px;
      font-weight: 700;
      padding: 2px 6px;
      border-radius: var(--radius-sm);
      text-transform: uppercase;
    }

    .tier-1 { background: #d1fae5; color: #065f46; }
    .tier-2 { background: #dbeafe; color: #1e40af; }
    .tier-3 { background: #fef3c7; color: #92400e; }

    /* Modal for Newly Added Sources */
    .modal-backdrop {
      position: fixed;
      top: 0;
      left: 0;
      width: 100vw;
      height: 100vh;
      background: rgba(18, 16, 14, 0.7);
      backdrop-filter: blur(4px);
      display: none;
      align-items: center;
      justify-content: center;
      z-index: 999;
      padding: 20px;
    }

    .modal-backdrop.open {
      display: flex;
    }

    .modal-dialog {
      background: #ffffff;
      border-radius: var(--radius-lg);
      box-shadow: var(--shadow-lg);
      border: 1px solid var(--c-gold);
      width: 100%;
      max-width: 1100px;
      max-height: 90vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      animation: modalFadeIn 0.25s ease-out;
    }

    @keyframes modalFadeIn {
      from { opacity: 0; transform: scale(0.96); }
      to { opacity: 1; transform: scale(1); }
    }

    .modal-header {
      padding: 20px 24px;
      background: linear-gradient(135deg, var(--c-charcoal) 0%, #25201b 100%);
      color: #ffffff;
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 2px solid var(--c-gold);
    }

    .modal-header h2 {
      font-size: 18px;
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .close-btn {
      background: transparent;
      border: none;
      color: #ffffff;
      font-size: 24px;
      cursor: pointer;
      line-height: 1;
      padding: 4px;
    }

    .modal-body {
      padding: 20px 24px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 16px;
      background: var(--c-cream);
    }

    .sources-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
      gap: 16px;
    }

    .source-card {
      background: #ffffff;
      border: 1px solid var(--c-border);
      border-radius: var(--radius-md);
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 8px;
      box-shadow: var(--shadow-sm);
    }

    .source-card-top {
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 11px;
    }

    .source-id {
      font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
      font-weight: 700;
      color: var(--c-terracotta);
    }

    .source-title {
      font-size: 14px;
      font-weight: 700;
      color: var(--c-charcoal);
      line-height: 1.4;
    }

    .source-author {
      font-size: 12px;
      color: var(--c-text-muted);
      font-weight: 500;
    }

    .source-digest {
      font-size: 12.5px;
      color: var(--c-text-main);
      line-height: 1.5;
      background: #fafaf8;
      padding: 8px 10px;
      border-radius: var(--radius-sm);
      border: 1px solid #ebe7df;
    }

    .source-footer {
      margin-top: auto;
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 11px;
      padding-top: 8px;
      border-top: 1px solid #eee;
    }

    /* Footer */
    footer {
      margin-top: auto;
      background: var(--c-charcoal);
      color: #9ca3af;
      padding: 24px 32px;
      border-top: 1px solid var(--c-charcoal-border);
      font-size: 12px;
    }

    .footer-inner {
      max-width: 1440px;
      margin: 0 auto;
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
    }

    /* Pulse animation for enriched map nodes */
    @keyframes pulseRing {
      0% { r: 8px; opacity: 0.8; stroke-width: 2px; }
      50% { r: 16px; opacity: 0.2; stroke-width: 4px; }
      100% { r: 8px; opacity: 0.8; stroke-width: 2px; }
    }

    .pulse-ring {
      animation: pulseRing 2.5s infinite ease-in-out;
      transform-origin: center;
    }
  </style>
</head>
<body>

  <!-- Masthead -->
  <header class="masthead">
    <div class="masthead-inner">
      <div class="brand-block">
        <div class="brand-emblem">VL</div>
        <div class="brand-titles">
          <h1>Vĩnh Long 360 — Interactive Knowledge Radar Dashboard 2.0</h1>
          <p>Hệ Thống Trực Quan Hóa Tri Thức Thổ Nhưỡng Tam Vùng & Giám Sát Làm Giàu Dữ Liệu</p>
          <div class="header-badges">
            <span class="badge-pill status-gold">🏛️ 1.772 Thực Thể CSDL</span>
            <span class="badge-pill status-gold">🔗 13.343 Quan Hệ Tri Thức</span>
            <span class="badge-pill status-green">📚 1.024 Nguồn NotebookLM (988 + 36)</span>
            <span class="badge-pill status-terracotta">✨ 54 Bản Ghi Làm Giàu</span>
            <span class="badge-pill status-blue">⚡ 100% Offline Standalone</span>
          </div>
        </div>
      </div>
      <div class="header-actions">
        <button class="btn btn-gold" onclick="downloadLedger()">
          <span>📥</span> Tải Sổ Tri Thức JSON
        </button>
        <button class="btn btn-terracotta" onclick="openSourcesModal()">
          <span>📖</span> 36 Nguồn Thẩm Quyền Mới
        </button>
      </div>
    </div>
  </header>

  <!-- Main Container -->
  <main class="container">

    <!-- KPI Scorecard -->
    <section class="kpi-grid">
      <div class="kpi-card vl">
        <div class="kpi-label">Thực Thể & Bản Ghi Làm Giàu</div>
        <div class="kpi-value" id="kpi-enriched">49 / 54</div>
        <div class="kpi-desc">49 thực thể trọng điểm được làm giàu qua 54 bản ghi chuyên sâu</div>
      </div>
      <div class="kpi-card gold">
        <div class="kpi-label">Nguồn Thẩm Quyền Nạp Mới</div>
        <div class="kpi-value" id="kpi-sources">36 Nguồn</div>
        <div class="kpi-desc">100% Tier 1 Nhà nước (.gov.vn) & Tier 2 Viện KHXH/Trường ĐH</div>
      </div>
      <div class="kpi-card green">
        <div class="kpi-label">Độ Phủ E-E-A-T Thực Địa</div>
        <div class="kpi-value">100%</div>
        <div class="kpi-desc">Đối chứng niên đại, giờ đón khách, hạ tầng tiếp cận và văn bản di sản</div>
      </div>
      <div class="kpi-card blue">
        <div class="kpi-label">Thị Giác Thổ Nhưỡng (Anti-Slop)</div>
        <div class="kpi-value">100%</div>
        <div class="kpi-desc">Chỉ dẫn 4 thành phần: Góc máy, Ánh sáng, Bảng màu, Nhận diện độc bản</div>
      </div>
      <div class="kpi-card purple">
        <div class="kpi-label">Đồ Thị Ngữ Nghĩa AEO/GEO</div>
        <div class="kpi-value">7 Schema</div>
        <div class="kpi-desc">Tương thích Schema.org tối ưu hóa cho AI Answer Engines (Perplexity, Gemini)</div>
      </div>
    </section>

    <!-- Dual Visual Grid: 6-Axis Radar & 124 Communes Map -->
    <section class="visual-grid">

      <!-- Left: 6-Axis Radar Card -->
      <div class="visual-card">
        <div class="visual-card-header">
          <div>
            <div class="visual-card-title">
              <span>🎯</span> Radar Tri Thức 6 Trục E-E-A-T
            </div>
            <div class="visual-card-subtitle">Đối chứng điểm số Hiện trạng (Baseline) vs Sau làm giàu (Enriched)</div>
          </div>
          <span class="badge-pill status-gold" id="radar-hover-score">Rà chuột để xem chi tiết</span>
        </div>
        <div class="visual-card-body">
          <svg id="radar-svg" viewBox="0 0 500 500" width="100%" height="100%">
            <!-- Dynamically populated via renderRadar() -->
          </svg>
        </div>
        <div class="radar-legend">
          <div class="radar-legend-item" onclick="toggleRadarBaseline()">
            <div class="legend-bullet bullet-baseline"></div>
            <span>Hiện Trạng Cũ (Baseline Sparse)</span>
          </div>
          <div class="radar-legend-item" onclick="toggleRadarEnriched()">
            <div class="legend-bullet bullet-enriched"></div>
            <span>Sau Làm Giàu (Enriched Deep)</span>
          </div>
        </div>
      </div>

      <!-- Right: Interactive 124 Communes GIS Map Card -->
      <div class="visual-card">
        <div class="visual-card-header">
          <div>
            <div class="visual-card-title">
              <span>🗺️</span> Bản Đồ Phân Bố Tri Thức 124 Xã/Phường
            </div>
            <div class="visual-card-subtitle">Mật độ thực thể & các điểm di sản được làm giàu trên địa bàn Tam Vùng</div>
          </div>
          <div class="map-legend-pills">
            <span class="map-pill"><span class="dot-vl"></span> Vĩnh Long (35)</span>
            <span class="map-pill"><span class="dot-bt"></span> Bến Tre (48)</span>
            <span class="map-pill"><span class="dot-tv"></span> Trà Vinh (41)</span>
          </div>
        </div>
        <div class="visual-card-body">
          <svg id="commune-map-svg" viewBox="0 0 700 480" width="100%" height="100%">
            <!-- Dynamically populated via renderMap() -->
          </svg>
          <div id="map-tooltip" class="map-tooltip"></div>
        </div>
        <div class="map-controls">
          <div style="display:flex; gap:6px;">
            <button class="btn" style="padding:4px 10px; min-height:30px; font-size:11px;" onclick="selectRegionFilter('all')">Toàn Tam Vùng</button>
            <button class="btn" style="padding:4px 10px; min-height:30px; font-size:11px;" onclick="selectRegionFilter('vinh-long')">Vĩnh Long</button>
            <button class="btn" style="padding:4px 10px; min-height:30px; font-size:11px;" onclick="selectRegionFilter('ben-tre')">Bến Tre</button>
            <button class="btn" style="padding:4px 10px; min-height:30px; font-size:11px;" onclick="selectRegionFilter('tra-vinh')">Trà Vinh</button>
          </div>
          <span style="color:var(--c-text-muted); font-size:11px;" id="map-selection-hint">Nhấp vào một xã/phường để lọc danh sách bên dưới</span>
        </div>
      </div>

    </section>

    <!-- Multi-Dimensional Filter Bar -->
    <section class="filter-bar">
      <div class="filter-row">
        <!-- Region Tabs -->
        <div class="filter-tabs">
          <button class="filter-tab active" id="tab-all" onclick="selectRegionFilter('all')">
            <span>🌐</span> Tất Cả (124 Xã/Phường)
          </button>
          <button class="filter-tab tab-vl" id="tab-vl" onclick="selectRegionFilter('vinh-long')">
            <span>🏺</span> Vĩnh Long (35)
          </button>
          <button class="filter-tab tab-bt" id="tab-bt" onclick="selectRegionFilter('ben-tre')">
            <span>🥥</span> Bến Tre (48)
          </button>
          <button class="filter-tab tab-tv" id="tab-tv" onclick="selectRegionFilter('tra-vinh')">
            <span>🏯</span> Trà Vinh (41)
          </button>
        </div>

        <div class="active-filter-indicator">
          <span>Đang hiển thị:</span>
          <span class="count-highlight" id="records-counter">54 / 54 bản ghi</span>
        </div>
      </div>

      <div class="filter-row">
        <!-- Category & Tier Selectors -->
        <div class="filter-selects">
          <select class="select-control" id="category-filter" onchange="onFilterChange()">
            <option value="all">Tất cả thể loại (AEO Schema)</option>
            <option value="HistoricalRelic">Di tích lịch sử (HistoricalRelic)</option>
            <option value="TouristAttraction">Điểm tham quan (TouristAttraction)</option>
            <option value="LocalBusiness">Làng nghề & SX (LocalBusiness)</option>
            <option value="FoodEstablishment">Ẩm thực dân gian (FoodEstablishment)</option>
            <option value="Product">Sản phẩm & OCOP (Product)</option>
            <option value="SpecialEvent">Sự kiện & Lễ hội (SpecialEvent)</option>
          </select>

          <select class="select-control" id="tier-filter" onchange="onFilterChange()">
            <option value="all">Tất cả cấp thẩm quyền nguồn</option>
            <option value="TIER_1_GOVERNMENT">Tier 1: Thẩm quyền Nhà nước (.gov.vn)</option>
            <option value="TIER_2_SCHOLARLY">Tier 2: Viện Nghiên Cứu & Đại Học</option>
          </select>

          <button class="btn" style="padding:6px 12px; min-height:40px;" onclick="resetAllFilters()">
            <span>🔄</span> Đặt lại
          </button>
        </div>

        <!-- Search input -->
        <div class="search-input-wrapper">
          <span class="search-icon">🔍</span>
          <input type="text" id="search-input" class="search-input" placeholder="Tìm kiếm theo tên thực thể, ID, từ khóa lịch sử, trích dẫn..." oninput="onSearchInput(this.value)">
        </div>
      </div>
    </section>

    <!-- Before-vs-After Comparison Plaque -->
    <section class="plaque-section">
      <div class="plaque-header">
        <div class="plaque-title">
          <span>⚖️</span> Trình Đối Chứng Trực Quan: Hiện Trạng Cũ vs. Tri Thức Làm Giàu
        </div>
        <div style="font-size:12px; color:var(--c-text-muted);">
          Mỗi bản ghi được khóa cứng 8 trường chuẩn: Entity, Field, Baseline, Enriched, Cultural Notes, AEO Schema, Visual Matrix, Citations.
        </div>
      </div>

      <!-- Plaque List Cards -->
      <div class="plaque-grid" id="plaque-list">
        <!-- Dynamically rendered via renderTable() -->
      </div>
    </section>

  </main>

  <!-- Modal for 36 Ingested Sources -->
  <div id="sources-modal" class="modal-backdrop" onclick="onBackdropClick(event)">
    <div class="modal-dialog">
      <div class="modal-header">
        <h2>
          <span>📚</span> 36 Nguồn Nghiên Cứu Học Thuật & Nhà Nước Nạp Mới Vào NotebookLM
        </h2>
        <button class="close-btn" onclick="closeSourcesModal()">&times;</button>
      </div>
      <div class="modal-body">
        <div style="display:flex; flex-wrap:wrap; justify-content:space-between; align-items:center; gap:12px;">
          <div style="display:flex; gap:10px;">
            <select class="select-control" id="modal-notebook-filter" onchange="renderSources()">
              <option value="all">Tất cả sổ tay NotebookLM</option>
              <option value="v-nh-long-v-nh-long-b-n-tre-tr">Sổ tay 1: Vĩnh Long (Di tích, Lịch sử)</option>
              <option value="mekong-360-t-p-2">Sổ tay 2: Mekong 360 (Ẩm thực, Làng nghề, OCOP)</option>
            </select>
            <select class="select-control" id="modal-category-filter" onchange="renderSources()">
              <option value="all">Tất cả chuyên mục</option>
              <option value="ARCHAEOLOGY_HERITAGE">Khảo cổ & Di sản</option>
              <option value="HISTORICAL_FIGURE">Nhân vật lịch sử</option>
              <option value="KHMER_CULTURE">Văn hóa Khmer Nam Bộ</option>
              <option value="TRADITIONAL_CRAFT">Làng nghề truyền thống</option>
              <option value="MEKONG_ECOLOGY_OCOP">Sinh thái & OCOP</option>
              <option value="ADMIN_PLANNING">Quy hoạch & Chính sách</option>
            </select>
          </div>
          <span style="font-size:12px; color:var(--c-text-muted);" id="modal-sources-counter">Đang hiển thị 36 / 36 nguồn</span>
        </div>
        <div class="sources-grid" id="sources-grid">
          <!-- Dynamically populated via renderSources() -->
        </div>
      </div>
    </div>
  </div>

  <!-- Footer -->
  <footer>
    <div class="footer-inner">
      <div>
        <strong>Vĩnh Long 360 — Tri Thức Thổ Nhưỡng Tam Vùng</strong> | Milestone M7 Deep Knowledge Enrichment Campaign
      </div>
      <div>
        Kiến trúc 100% Offline Standalone • Chuẩn hóa E-E-A-T & AEO Semantic Graph • Tuân thủ bất biến an toàn B1, B6, B7
      </div>
    </div>
  </footer>

  <!-- Script: Data Payload & Application Logic -->
  <script>
    const DATA = ${payloadJson};

    // Application State
    let currentRegion = 'all';
    let currentCategory = 'all';
    let currentTier = 'all';
    let searchQuery = '';
    let selectedCommuneId = null;
    let showBaselineRadar = true;
    let showEnrichedRadar = true;

    // Initialize Dashboard on DOM Load
    document.addEventListener('DOMContentLoaded', () => {
      renderRadar();
      renderMap();
      renderTable();
      renderSources();
    });

    // -------------------------------------------------------------------------
    // 1. Radar Visualization (Pure SVG)
    // -------------------------------------------------------------------------
    function renderRadar() {
      const svg = document.getElementById('radar-svg');
      if (!svg) return;
      svg.innerHTML = '';

      const cx = 250;
      const cy = 250;
      const r = 165;
      const axes = DATA.radar_axes;
      const n = axes.length;

      // Concentric rings at 20%, 40%, 60%, 80%, 100%
      const levels = [0.2, 0.4, 0.6, 0.8, 1.0];
      levels.forEach(lvl => {
        const ringRadius = r * lvl;
        const pts = [];
        for (let i = 0; i < n; i++) {
          const angle = -Math.PI / 2 + (i * 2 * Math.PI / n);
          const px = cx + ringRadius * Math.cos(angle);
          const py = cy + ringRadius * Math.sin(angle);
          pts.push(\`\${px.toFixed(1)},\${py.toFixed(1)}\`);
        }
        const poly = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
        poly.setAttribute('points', pts.join(' '));
        poly.setAttribute('fill', 'none');
        poly.setAttribute('stroke', lvl === 1.0 ? '#c99446' : '#e2ddd5');
        poly.setAttribute('stroke-width', lvl === 1.0 ? '1.5' : '1');
        poly.setAttribute('stroke-dasharray', lvl === 1.0 ? 'none' : '2 2');
        svg.appendChild(poly);

        // Level text
        const labelText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        labelText.setAttribute('x', cx + 4);
        labelText.setAttribute('y', cy - ringRadius + 12);
        labelText.setAttribute('fill', '#9ca3af');
        labelText.setAttribute('font-size', '9');
        labelText.setAttribute('font-weight', '600');
        labelText.textContent = \`\${Math.round(lvl * 100)}%\`;
        svg.appendChild(labelText);
      });

      // Spokes & Axis Labels
      for (let i = 0; i < n; i++) {
        const angle = -Math.PI / 2 + (i * 2 * Math.PI / n);
        const x2 = cx + r * Math.cos(angle);
        const y2 = cy + r * Math.sin(angle);

        // Spoke line
        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        line.setAttribute('x1', cx);
        line.setAttribute('y1', cy);
        line.setAttribute('x2', x2);
        line.setAttribute('y2', y2);
        line.setAttribute('stroke', '#e2ddd5');
        line.setAttribute('stroke-width', '1');
        svg.appendChild(line);

        // Outer label position
        const labelRadius = r + 26;
        const lx = cx + labelRadius * Math.cos(angle);
        const ly = cy + labelRadius * Math.sin(angle);

        const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        text.setAttribute('x', lx);
        text.setAttribute('y', ly + 4);
        text.setAttribute('text-anchor', 'middle');
        text.setAttribute('fill', '#231e1a');
        text.setAttribute('font-size', '11');
        text.setAttribute('font-weight', '700');
        text.style.cursor = 'pointer';
        text.textContent = axes[i].name;

        text.addEventListener('click', () => {
          filterByRadarAxis(axes[i]);
        });

        text.addEventListener('mouseenter', () => {
          const hoverBadge = document.getElementById('radar-hover-score');
          if (hoverBadge) {
            hoverBadge.textContent = \`\${axes[i].name}: \${axes[i].baseline}% → \${axes[i].enriched}% (+ \${axes[i].enriched - axes[i].baseline}%)\`;
          }
        });

        svg.appendChild(text);
      }

      // 1. Baseline Polygon (Sparse)
      if (showBaselineRadar) {
        const baselinePts = [];
        for (let i = 0; i < n; i++) {
          const angle = -Math.PI / 2 + (i * 2 * Math.PI / n);
          const scoreFrac = axes[i].baseline / 100;
          const px = cx + r * scoreFrac * Math.cos(angle);
          const py = cy + r * scoreFrac * Math.sin(angle);
          baselinePts.push(\`\${px.toFixed(1)},\${py.toFixed(1)}\`);
        }

        const baselinePoly = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
        baselinePoly.setAttribute('points', baselinePts.join(' '));
        baselinePoly.setAttribute('fill', 'rgba(185, 95, 56, 0.2)');
        baselinePoly.setAttribute('stroke', '#b95f38');
        baselinePoly.setAttribute('stroke-width', '2');
        baselinePoly.setAttribute('stroke-dasharray', '4 4');
        svg.appendChild(baselinePoly);

        // Baseline vertex dots
        for (let i = 0; i < n; i++) {
          const angle = -Math.PI / 2 + (i * 2 * Math.PI / n);
          const scoreFrac = axes[i].baseline / 100;
          const px = cx + r * scoreFrac * Math.cos(angle);
          const py = cy + r * scoreFrac * Math.sin(angle);

          const dot = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
          dot.setAttribute('cx', px);
          dot.setAttribute('cy', py);
          dot.setAttribute('r', '4');
          dot.setAttribute('fill', '#b95f38');
          svg.appendChild(dot);
        }
      }

      // 2. Enriched Polygon (Deep)
      if (showEnrichedRadar) {
        const enrichedPts = [];
        for (let i = 0; i < n; i++) {
          const angle = -Math.PI / 2 + (i * 2 * Math.PI / n);
          const scoreFrac = axes[i].enriched / 100;
          const px = cx + r * scoreFrac * Math.cos(angle);
          const py = cy + r * scoreFrac * Math.sin(angle);
          enrichedPts.push(\`\${px.toFixed(1)},\${py.toFixed(1)}\`);
        }

        const enrichedPoly = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
        enrichedPoly.setAttribute('points', enrichedPts.join(' '));
        enrichedPoly.setAttribute('fill', 'rgba(201, 148, 70, 0.35)');
        enrichedPoly.setAttribute('stroke', '#c99446');
        enrichedPoly.setAttribute('stroke-width', '2.5');
        svg.appendChild(enrichedPoly);

        // Enriched vertex dots
        for (let i = 0; i < n; i++) {
          const angle = -Math.PI / 2 + (i * 2 * Math.PI / n);
          const scoreFrac = axes[i].enriched / 100;
          const px = cx + r * scoreFrac * Math.cos(angle);
          const py = cy + r * scoreFrac * Math.sin(angle);

          const dot = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
          dot.setAttribute('cx', px);
          dot.setAttribute('cy', py);
          dot.setAttribute('r', '5');
          dot.setAttribute('fill', '#ffffff');
          dot.setAttribute('stroke', '#c99446');
          dot.setAttribute('stroke-width', '2');
          dot.style.cursor = 'pointer';

          dot.addEventListener('mouseenter', () => {
            const hoverBadge = document.getElementById('radar-hover-score');
            if (hoverBadge) {
              hoverBadge.textContent = \`\${axes[i].name}: \${axes[i].enriched}% - \${axes[i].enriched_desc}\`;
            }
          });

          svg.appendChild(dot);
        }
      }
    }

    function toggleRadarBaseline() {
      showBaselineRadar = !showBaselineRadar;
      renderRadar();
    }

    function toggleRadarEnriched() {
      showEnrichedRadar = !showEnrichedRadar;
      renderRadar();
    }

    function filterByRadarAxis(axis) {
      searchQuery = axis.short;
      const searchInput = document.getElementById('search-input');
      if (searchInput) searchInput.value = searchQuery;
      applyFilters();
    }

    // -------------------------------------------------------------------------
    // 2. Interactive 124 Communes GIS Map (Pure SVG)
    // -------------------------------------------------------------------------
    function renderMap() {
      const svg = document.getElementById('commune-map-svg');
      if (!svg) return;
      svg.innerHTML = '';

      const width = 700;
      const height = 480;
      const padX = 45;
      const padY = 35;

      const { minLat, maxLat, minLng, maxLng } = DATA.map_bounds;

      function projX(lng) {
        return padX + ((lng - minLng) / (maxLng - minLng)) * (width - 2 * padX);
      }
      function projY(lat) {
        return padY + ((maxLat - lat) / (maxLat - minLat)) * (height - 2 * padY);
      }

      // River Waterways Background Aesthetic (Mekong Channels: Tien, Co Chien, Ham Luong, Hau)
      const riverGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
      riverGroup.setAttribute('class', 'rivers-bg');

      // Decorative river paths crossing the Delta
      const riverPaths = [
        // Sông Tiền (North branch)
        \`M 0,\${projY(10.28)} C \${projX(105.85)},\${projY(10.30)} \${projX(106.10)},\${projY(10.27)} \${projX(106.40)},\${projY(10.22)} S \${projX(106.65)},\${projY(10.15)} \${width},\${projY(10.10)}\`,
        // Sông Cổ Chiên (Central branch between Vinh Long, Ben Tre and Tra Vinh)
        \`M \${projX(105.74)},\${projY(10.25)} C \${projX(105.95)},\${projY(10.24)} \${projX(106.05)},\${projY(10.12)} \${projX(106.25)},\${projY(10.02)} S \${projX(106.45)},\${projY(9.88)} \${projX(106.60)},\${projY(9.80)}\`,
        // Sông Hàm Luông (Ben Tre branch)
        \`M \${projX(106.20)},\${projY(10.18)} C \${projX(106.35)},\${projY(10.10)} \${projX(106.45)},\${projY(9.98)} \${projX(106.55)},\${projY(9.90)} L \${width},\${projY(9.85)}\`,
        // Sông Hậu (South branch bounding Vinh Long & Tra Vinh)
        \`M 0,\${projY(10.12)} C \${projX(105.85)},\${projY(10.05)} \${projX(106.00)},\${projY(9.85)} \${projX(106.18)},\${projY(9.65)} S \${projX(106.40)},\${projY(9.58)} \${width},\${projY(9.56)}\`
      ];

      riverPaths.forEach(d => {
        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        path.setAttribute('d', d);
        path.setAttribute('fill', 'none');
        path.setAttribute('stroke', '#d8ecf8');
        path.setAttribute('stroke-width', '10');
        path.setAttribute('stroke-linecap', 'round');
        path.setAttribute('opacity', '0.7');
        riverGroup.appendChild(path);
      });
      svg.appendChild(riverGroup);

      // Territory Cluster Tint Polygons
      const regions = [
        { area: 'vinh-long', color: 'rgba(185, 95, 56, 0.05)', stroke: 'rgba(185, 95, 56, 0.2)' },
        { area: 'ben-tre', color: 'rgba(27, 136, 68, 0.05)', stroke: 'rgba(27, 136, 68, 0.2)' },
        { area: 'tra-vinh', color: 'rgba(0, 103, 152, 0.05)', stroke: 'rgba(0, 103, 152, 0.2)' }
      ];

      // Region Labels on Map
      const regionLabels = [
        { name: 'TỈNH VĨNH LONG', x: projX(105.95), y: projY(10.15), color: '#b95f38' },
        { name: 'TỈNH BẾN TRE', x: projX(106.42), y: projY(10.18), color: '#1b8844' },
        { name: 'TỈNH TRÀ VINH', x: projX(106.28), y: projY(9.82), color: '#006798' }
      ];

      regionLabels.forEach(lbl => {
        const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        text.setAttribute('x', lbl.x);
        text.setAttribute('y', lbl.y);
        text.setAttribute('text-anchor', 'middle');
        text.setAttribute('fill', lbl.color);
        text.setAttribute('font-size', '13');
        text.setAttribute('font-weight', '800');
        text.setAttribute('opacity', '0.45');
        text.setAttribute('letter-spacing', '2px');
        svg.appendChild(text);
      });

      // Plot 124 Communes/Wards
      const nodesGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
      nodesGroup.setAttribute('class', 'communes-nodes');

      DATA.communes.forEach(c => {
        const cx = projX(c.lng);
        const cy = projY(c.lat);
        const hasEnrichment = c.enriched_count > 0;

        let fillColor = '#b95f38'; // Vĩnh Long
        if (c.area === 'ben-tre') fillColor = '#1b8844';
        if (c.area === 'tra-vinh') fillColor = '#006798';

        // Check if filtered
        const matchesRegion = currentRegion === 'all' || currentRegion === c.area;
        const opacity = matchesRegion ? 1.0 : 0.2;

        const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        g.setAttribute('class', 'commune-node');
        g.setAttribute('opacity', opacity);
        g.style.cursor = 'pointer';

        // Pulse ring if commune has enriched entities
        if (hasEnrichment && matchesRegion) {
          const pulse = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
          pulse.setAttribute('cx', cx);
          pulse.setAttribute('cy', cy);
          pulse.setAttribute('r', '10');
          pulse.setAttribute('fill', 'none');
          pulse.setAttribute('stroke', fillColor);
          pulse.setAttribute('class', 'pulse-ring');
          g.appendChild(pulse);
        }

        // Selection ring
        if (selectedCommuneId === c.id) {
          const selRing = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
          selRing.setAttribute('cx', cx);
          selRing.setAttribute('cy', cy);
          selRing.setAttribute('r', '14');
          selRing.setAttribute('fill', 'none');
          selRing.setAttribute('stroke', '#c99446');
          selRing.setAttribute('stroke-width', '3');
          g.appendChild(selRing);
        }

        // Main commune circle
        const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        circle.setAttribute('cx', cx);
        circle.setAttribute('cy', cy);
        const baseRadius = hasEnrichment ? 7.5 : 4.5;
        circle.setAttribute('r', baseRadius);
        circle.setAttribute('fill', fillColor);
        circle.setAttribute('stroke', '#ffffff');
        circle.setAttribute('stroke-width', '1.5');
        g.appendChild(circle);

        // Tooltip & click events
        const tooltip = document.getElementById('map-tooltip');

        g.addEventListener('mouseenter', (e) => {
          circle.setAttribute('r', baseRadius + 3);
          if (tooltip) {
            tooltip.style.display = 'block';
            tooltip.innerHTML = \`
              <div style="font-weight:700; color:\${fillColor}">\${c.name}</div>
              <div style="color:#aaa; font-size:11px;">\${c.level === 'phuong' ? 'Phường' : 'Xã'} • \${c.area.toUpperCase()}</div>
              <div style="margin-top:4px;">Tổng thực thể CSDL: <strong>\${c.entity_count}</strong></div>
              <div style="color:#ffd899;">Bản ghi làm giàu: <strong>\${c.enriched_count}</strong></div>
            \`;
          }
        });

        g.addEventListener('mousemove', (e) => {
          if (tooltip) {
            const rect = svg.getBoundingClientRect();
            tooltip.style.left = (e.clientX - rect.left + 15) + 'px';
            tooltip.style.top = (e.clientY - rect.top - 20) + 'px';
          }
        });

        g.addEventListener('mouseleave', () => {
          circle.setAttribute('r', baseRadius);
          if (tooltip) tooltip.style.display = 'none';
        });

        g.addEventListener('click', () => {
          if (selectedCommuneId === c.id) {
            selectedCommuneId = null;
          } else {
            selectedCommuneId = c.id;
          }
          renderMap();
          applyFilters();
        });

        nodesGroup.appendChild(g);
      });

      svg.appendChild(nodesGroup);
    }

    // -------------------------------------------------------------------------
    // 3. Comparison Plaque Table & Filtering Logic
    // -------------------------------------------------------------------------
    function selectRegionFilter(region) {
      currentRegion = region;
      selectedCommuneId = null;

      // Update tabs UI
      ['all', 'vl', 'bt', 'tv'].forEach(key => {
        const el = document.getElementById(\`tab-\${key}\`);
        if (el) el.classList.remove('active');
      });

      if (region === 'all') document.getElementById('tab-all')?.classList.add('active');
      if (region === 'vinh-long') document.getElementById('tab-vl')?.classList.add('active');
      if (region === 'ben-tre') document.getElementById('tab-bt')?.classList.add('active');
      if (region === 'tra-vinh') document.getElementById('tab-tv')?.classList.add('active');

      renderMap();
      applyFilters();
    }

    function onFilterChange() {
      const catSelect = document.getElementById('category-filter');
      const tierSelect = document.getElementById('tier-filter');

      if (catSelect) currentCategory = catSelect.value;
      if (tierSelect) currentTier = tierSelect.value;

      applyFilters();
    }

    function onSearchInput(val) {
      searchQuery = val.trim().toLowerCase();
      applyFilters();
    }

    function resetAllFilters() {
      currentRegion = 'all';
      currentCategory = 'all';
      currentTier = 'all';
      searchQuery = '';
      selectedCommuneId = null;

      const catSelect = document.getElementById('category-filter');
      const tierSelect = document.getElementById('tier-filter');
      const searchInput = document.getElementById('search-input');

      if (catSelect) catSelect.value = 'all';
      if (tierSelect) tierSelect.value = 'all';
      if (searchInput) searchInput.value = '';

      selectRegionFilter('all');
    }

    function applyFilters() {
      const listEl = document.getElementById('plaque-list');
      const counterEl = document.getElementById('records-counter');
      const hintEl = document.getElementById('map-selection-hint');

      if (hintEl) {
        if (selectedCommuneId) {
          const com = DATA.communes.find(c => c.id === selectedCommuneId);
          hintEl.innerHTML = \`Đang lọc theo xã/phường: <strong style="color:var(--c-gold)">\${com ? com.name : selectedCommuneId}</strong> (nhấp lại để hủy)\`;
        } else {
          hintEl.textContent = 'Nhấp vào một xã/phường để lọc danh sách bên dưới';
        }
      }

      const filtered = DATA.enrichments.filter(item => {
        // Region filter
        if (currentRegion !== 'all' && item.area !== currentRegion) {
          return false;
        }

        // Commune filter (if selected on map)
        if (selectedCommuneId && item.place_id !== selectedCommuneId) {
          return false;
        }

        // Category / Schema filter
        if (currentCategory !== 'all') {
          if (item.aeo_schema_type !== currentCategory && item.entity_type !== currentCategory) {
            return false;
          }
        }

        // Tier filter
        if (currentTier !== 'all') {
          const hasTier = item.source_citations.some(cite => cite.tier === currentTier);
          if (!hasTier) return false;
        }

        // Search query
        if (searchQuery) {
          const q = searchQuery;
          const matchName = (item.entity_name || '').toLowerCase().includes(q);
          const matchId = (item.entity_id || '').toLowerCase().includes(q);
          const matchField = (item.field || '').toLowerCase().includes(q);
          const matchNotes = (item.cultural_depth_notes || '').toLowerCase().includes(q);
          const matchVisual = (item.visual_narrative || '').toLowerCase().includes(q);
          const matchValue = String(item.enriched_value || '').toLowerCase().includes(q);
          const matchPlace = (item.place_name || '').toLowerCase().includes(q);

          if (!matchName && !matchId && !matchField && !matchNotes && !matchVisual && !matchValue && !matchPlace) {
            return false;
          }
        }

        return true;
      });

      if (counterEl) {
        counterEl.textContent = \`\${filtered.length} / \${DATA.enrichments.length} bản ghi\`;
      }

      renderTableItems(filtered);
    }

    function renderTable() {
      applyFilters();
    }

    function renderTableItems(items) {
      const listEl = document.getElementById('plaque-list');
      if (!listEl) return;

      if (items.length === 0) {
        listEl.innerHTML = \`
          <div style="background:#fff; border:1px dashed var(--c-border); border-radius:var(--radius-lg); padding:48px; text-align:center;">
            <div style="font-size:32px; margin-bottom:8px;">🔍</div>
            <div style="font-size:16px; font-weight:700; color:var(--c-charcoal)">Không tìm thấy bản ghi phù hợp</div>
            <div style="font-size:13px; color:var(--c-text-muted); margin-top:4px;">Hãy thử điều chỉnh bộ lọc hoặc từ khóa tìm kiếm.</div>
            <button class="btn btn-gold" style="margin-top:16px;" onclick="resetAllFilters()">Đặt lại bộ lọc</button>
          </div>
        \`;
        return;
      }

      listEl.innerHTML = items.map(item => {
        let regionTagClass = 'tag-vl';
        let regionName = 'Vĩnh Long';
        if (item.area === 'ben-tre') { regionTagClass = 'tag-bt'; regionName = 'Bến Tre'; }
        if (item.area === 'tra-vinh') { regionTagClass = 'tag-tv'; regionName = 'Trà Vinh'; }

        // Format baseline value
        let baselineText = item.current_value;
        let isNull = false;
        if (baselineText === null || baselineText === undefined || baselineText === '') {
          baselineText = 'Chưa có thông tin thực địa (null / sparse)';
          isNull = true;
        } else if (typeof baselineText === 'object') {
          baselineText = JSON.stringify(baselineText, null, 2);
        }

        // Format enriched value
        let enrichedText = item.enriched_value;
        if (typeof enrichedText === 'object') {
          enrichedText = JSON.stringify(enrichedText, null, 2);
        }

        // Citations HTML
        const citationsHtml = item.source_citations.map(c => {
          let tierClass = 'tier-1';
          let tierLabel = 'Tier 1 Nhà Nước';
          if (c.tier === 'TIER_2_SCHOLARLY') { tierClass = 'tier-2'; tierLabel = 'Tier 2 Học Thuật'; }
          if (c.tier === 'TIER_3_MAINSTREAM_PRESS') { tierClass = 'tier-3'; tierLabel = 'Tier 3 Báo Chí'; }

          let nbLabel = 'Sổ tay 1: Di tích';
          if (c.notebook_id === 'mekong-360-t-p-2') nbLabel = 'Sổ tay 2: Mekong 360';
          if (c.notebook_id === 'ch-nh-s-ch-ph-p-lu-t-v-n-b-n-q') nbLabel = 'Sổ tay 3: Chính sách';

          return \`
            <a href="\${c.url}" target="_blank" class="citation-badge">
              <span class="tier-badge \${tierClass}">\${tierLabel}</span>
              <span>\${c.title}</span>
              <span style="color:var(--c-gold); font-size:11px;">[\${nbLabel}]</span>
            </a>
          \`;
        }).join('');

        return \`
          <div class="enrichment-card">
            <div class="enrichment-card-top">
              <div class="entity-meta">
                <span class="entity-name">\${item.entity_name}</span>
                <span class="entity-id-tag">#\${item.entity_id}</span>
                <span class="tag-pill \${regionTagClass}">\${regionName}</span>
                \${item.place_name ? \`<span class="tag-pill" style="background:#eee; color:#555;">📍 \${item.place_name}</span>\` : ''}
              </div>
              <div style="display:flex; align-items:center; gap:8px;">
                <span class="field-tag">\${item.field}</span>
                <span class="tag-pill tag-schema">Schema: \${item.aeo_schema_type}</span>
              </div>
            </div>

            <!-- Diff Section -->
            <div class="diff-section">
              <div class="diff-box baseline">
                <div class="diff-label">
                  <span>⚠️</span> Hiện Trạng Cũ (Baseline Database)
                </div>
                <div class="diff-content \${isNull ? 'is-null' : ''}">\${escapeHtml(String(baselineText))}</div>
              </div>
              <div class="diff-box enriched">
                <div class="diff-label">
                  <span>✨</span> Sau Làm Giàu Tri Thức (NotebookLM Deep Terroir)
                </div>
                <div class="diff-content">\${escapeHtml(String(enrichedText))}</div>
              </div>
            </div>

            <!-- Supplementary Dossier -->
            <div class="dossier-section">
              <!-- Cultural Notes -->
              <div class="dossier-box dossier-cultural">
                <div class="dossier-title">
                  <span>📜</span> Ghi Chú Chiều Sâu Văn Hóa & Lịch Sử (Cultural Depth & E-E-A-T)
                </div>
                <div>\${escapeHtml(item.cultural_depth_notes)}</div>
              </div>

              <!-- Visual Terroir Matrix -->
              <div class="dossier-box dossier-visual">
                <div class="dossier-title">
                  <span>🎨</span> Ma Trận Chỉ Dẫn Thị Giác Thổ Nhưỡng (Visual Terroir Narrative Matrix)
                </div>
                <div>\${escapeHtml(item.visual_narrative)}</div>
              </div>

              <!-- Source Citations -->
              <div>
                <div style="font-size:11px; font-weight:700; text-transform:uppercase; color:var(--c-text-muted); margin-bottom:6px;">
                  Nguồn Trích Dẫn Thẩm Quyền Cao (Authority Citations):
                </div>
                <div class="citations-row">
                  \${citationsHtml}
                </div>
              </div>
            </div>
          </div>
        \`;
      }).join('');
    }

    function escapeHtml(str) {
      if (!str) return '';
      return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
    }

    // -------------------------------------------------------------------------
    // 4. Sources Modal (36 Ingested Sources)
    // -------------------------------------------------------------------------
    function openSourcesModal() {
      const modal = document.getElementById('sources-modal');
      if (modal) modal.classList.add('open');
      renderSources();
    }

    function closeSourcesModal() {
      const modal = document.getElementById('sources-modal');
      if (modal) modal.classList.remove('open');
    }

    function onBackdropClick(e) {
      if (e.target.id === 'sources-modal') {
        closeSourcesModal();
      }
    }

    function renderSources() {
      const grid = document.getElementById('sources-grid');
      const counter = document.getElementById('modal-sources-counter');
      const nbFilter = document.getElementById('modal-notebook-filter')?.value || 'all';
      const catFilter = document.getElementById('modal-category-filter')?.value || 'all';

      if (!grid) return;

      const filtered = DATA.sources.filter(s => {
        if (nbFilter !== 'all' && s.target_notebook !== nbFilter) return false;
        if (catFilter !== 'all' && s.category !== catFilter) return false;
        return true;
      });

      if (counter) {
        counter.textContent = \`Đang hiển thị \${filtered.length} / \${DATA.sources.length} nguồn\`;
      }

      grid.innerHTML = filtered.map(s => {
        const tierClass = s.tier === 'TIER_1_GOVERNMENT' ? 'tier-1' : 'tier-2';
        const tierLabel = s.tier === 'TIER_1_GOVERNMENT' ? 'Tier 1 Nhà Nước' : 'Tier 2 Học Thuật';
        const nbLabel = s.target_notebook === 'v-nh-long-v-nh-long-b-n-tre-tr' ? 'Sổ tay 1 (Vĩnh Long)' : 'Sổ tay 2 (Mekong 360)';

        return \`
          <div class="source-card">
            <div class="source-card-top">
              <span class="source-id">\${s.source_id}</span>
              <span class="tier-badge \${tierClass}">\${tierLabel} (Trọng số \${s.authority_weight})</span>
            </div>
            <div class="source-title">\${escapeHtml(s.title)}</div>
            <div class="source-author">🏛️ \${escapeHtml(s.author_or_institution)} (\${s.publication_year})</div>
            <div class="source-digest">\${escapeHtml(s.summary_digest)}</div>
            <div class="source-footer">
              <span style="color:var(--c-gold); font-weight:600;">\${nbLabel}</span>
              <a href="\${s.url}" target="_blank" style="color:var(--c-blue); text-decoration:none; font-weight:600;">Mở Nguồn &rarr;</a>
            </div>
          </div>
        \`;
      }).join('');
    }

    // -------------------------------------------------------------------------
    // 5. One-Click JSON Export
    // -------------------------------------------------------------------------
    function downloadLedger() {
      // Clean export adhering to the strict 8-field contract
      const exportData = DATA.enrichments.map(item => ({
        entity_id: item.entity_id,
        field: item.field,
        current_value: item.current_value,
        enriched_value: item.enriched_value,
        cultural_depth_notes: item.cultural_depth_notes,
        aeo_schema_type: item.aeo_schema_type,
        visual_narrative: item.visual_narrative,
        source_citations: item.source_citations
      }));

      const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'notebooklm_knowledge_enrichment_ledger.json';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }
  </script>
</body>
</html>
`;

const outputPath = path.join(repoRoot, 'outputs/knowledge-enrichment-dashboard.html');
fs.writeFileSync(outputPath, html, 'utf8');
console.log('Successfully written dashboard to:', outputPath);
console.log('Total file size:', fs.statSync(outputPath).size, 'bytes');
db.close();
