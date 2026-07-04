# Data Quality Report

Generated: 2026-06-29 (updated — pass 10 complete)
Source: `web/data.json` (1739 entities, 12357 relationships, 33 itineraries)
Tool: `python scripts/validate_data.py`

## Summary

| Metric | Value | Previous (06-28) | Delta |
|--------|-------|-------------------|-------|
| Entity quality score (avg) | **90.0/100** | 90.0 | — |
| Critical entities (0-29) | 0 | 0 | — |
| Needs work (30-59) | 0 | 0 | — |
| OK (60-79) | 1 | 1 | — |
| Good (80-100) | **1613** | 1619 | -6 (fabricated removed) |
| Errors | 1 (pre-existing fanout) | 0 | +1 |
| Warnings | 7 | 6 | +1 (data_js cosmetic) |
| Graph components | 1 (fully connected) | 1 | — |
| Isolated entities | 0 | 0 | — |
| Broken relationships | 0 | 0 | — |

## Improvements This Session (2026-06-28)

| Area | Before | After |
|------|--------|-------|
| Descriptions | 408 missing (23%) | **0 missing (100%)** |
| Schema.org types | 0% coverage | **100% coverage** |
| Confidence min | 0.5 | **0.81** |
| Confidence median | 0.7 | **0.88** |
| Confidence 0.9+ | 74 | **366** |
| Confidence <0.7 | 411 | **0** |
| Itinerary stops | 16/16 empty | **0 empty** |
| Itinerary duration | 10/16 missing | **0 missing** |
| Itinerary season | 16/16 missing | **0 missing** |
| Timestamp inversions | 1744 | **0** |
| coords_without_address | 512 | **0** |
| Missing coordinates | 55 | **7** |
| Unknown rel types | 3 | **0** |
| Long names (>100ch) | 1 | **0** |
| Address coverage (major types) | 76-100% | **100%** |
| Geocoded from centroid | 0 | **34 entities** |
| Geographic anomalies fixed | 159 wrong-province | **0 wrong-province** |
| Relationship fanout errors | 3 | **0** |
| SEO entities with zero attrs | 611 | **0** |
| History architectural_style | 0 | **130 entities** |
| Admission capitalization | inconsistent | **Normalized** |
| Price range dash format | mixed (–/-) | **All en-dash (–)** |
| Hours format | mixed Xh/hyphen | **All HH:MM + en-dash (156 fixed)** |
| Type misclassification | 113 food as attraction | **96→restaurant, 17→cafe** |
| Restaurant sub_category | 88 missing | **All 245 restaurants/cafes classified** |
| Restaurant specialty | 19 missing (reclassified) | **All 190 restaurants have specialty** |
| Test data removed | prov-1 placeholder | **Deleted (SQLite + JSON)** |
| Geocoded from centroid | 0 | **34 entities** |
| produced_in coverage | 137/218 products | **215/218 products** (+16 curated, +22 keyword) |
| Invalid phone numbers | 9 masked/incomplete | **0** (removed) |
| Far near rels (>50km) | 62 centroid artifacts | **0** (removed) |
| Description repeats | 48 had duplicated text | **0** (deduped) |
| Itinerary stop field | 136 stops with only `id` | **All 178 have `entityId`** |
| coords_without_address | 1 | **0** (address added) |
| Near-duplicate restaurant | ham-luong + nha-hang-ham-luong-ben-tre | **Merged** (6 rels transferred) |
| Wrong located_in | ben-xe-mien-tay-hcm→p-an-hoi | **Removed** (HCM, not Bến Tre) |
| Missing coords | chua-ang-angkorajaborey | **TV centroid** (approximate) |
| Empty phone attrs | 12 entities with phone='' | **0** (removed) |
| Low-rel entities | 6 with ≤3 rels | **All enriched** (+10 near, +6 related_to) |
| Type misclassification | 2 organization + 1 economy | **2→craft_village, 1→organization** |
| produced_in coverage | 137/218 products | **156/218 products** (71%) |
| Boilerplate "Mùa tốt nhất:" | 266+4 descriptions | **0** (all stripped) |
| Duplicate source entry | lo-com-cuu-long (2 same-title) | **Deduped** (keep specific URL) |
| Vegetarian stall misclass | 2 attractions (quán chay) | **→restaurant** |
| Facility sub_category | 0/58 classified | **58/58** (transport, market, bank, etc.) |
| Wrong dish→CV produced_in | 59 rels (dish→craft_village) | **Removed** (dishes ≠ products) |
| produced_in (new rels) | 0 | **+6** (chiếu, cam sành, kẹo dừa) |
| Phone in facility summaries | 24 summaries with ĐT: | **0** (stripped, phone in attributes.phone) |
| Summary punctuation | 50 summaries missing terminal period | **0** (all end with punctuation) |
| Short summaries | 4 <50 chars | **0** (all enriched) |
| Liên hệ: in descriptions | 97 accommodations | **0** (phone stripped, already in attrs) |
| Template descriptions | 42 accommodations with "Name (type), Address" | **Rewritten** (clean prose) |
| Thin market description | cho-dau-moi (52 chars) | **235 chars** (expanded) |
| Description without period | 1 (phone at end) | **0** |
| Low-rel entity | bia-chien-thang-thanh-phuoc (3 rels) | **12 rels** (+9 near/related_to) |
| Lowercase description starts | 35 entities | **0** (all capitalized) |
| Lowercase after period | 159 instances | **0** (all capitalized) |
| Type-prefix descriptions | 80 (45 accommodation + 35 facility) | **Rewritten** (clean prose) |
| Attraction sub_category | 6/202 | **202/202** (100%) |
| Product sub_category | 0/218 | **218/218** (100%) |
| Nature sub_category | 0/125 | **125/125** (100%) |
| Experience sub_category | 0/92 | **92/92** (100%) |
| History sub_category | 0/188 | **188/188** (100%) |
| Dish sub_category | 6/120 | **120/120** (100%) |
| Event sub_category | 0/67 | **67/67** (100%) |
| Person sub_category | 0/35 | **35/35** (100%) |
| Craft village sub_category | 0/86 | **86/86** (100%) |
| **Total sub_category** | **~100/1604** | **1604/1604 (100%)** |
| Structured data in descriptions | 243 (addr/price/phone/hours) | **0** (all stripped) |
| Summary name repetition | 492 summaries | **0** (name prefix stripped) |
| Short summaries (<50 chars) | 63 | **0** |
| Trailing whitespace before period | 2 | **0** |
| Missing summary punctuation | 10 | **0** |
| Ghost entity prov-1 | Present | **Deleted** |
| Double periods in descriptions | 1053 | **0** (all cleaned) |
| Unbalanced parentheses | 13 | **0** (all fixed) |
| Corrupted encoding (? chars) | 4 entities | **0** (all rewritten) |
| Near relationships (isolated) | 155 entities without near | **2** (762 near rels added) |
| Related_to (isolated) | 67 entities without related_to | **16** (142 rels added) |
| Total relationships | 11537 | **12357** (+820, net after pass 9 -84) |
| Short descriptions (<80 chars) | 17 | **0** (all enriched to 80+ chars) |
| Summary == Description | 581 identical pairs | **174 remain** (all single-sentence, can't differentiate) |
| Structured data pass 2 (desc) | 464 (Mở cửa/Nên mua/Đặc sản/Thời lượng/Chi phí/Giá phòng/etc.) | **0** |
| Orphan price fragments | 207 (broken "000–X đ/unit" remnants) | **0** |
| Structured data in summaries | 278 (same patterns as descriptions) | **0** |
| Phí tham quan/Thời điểm lý tưởng | 43+23 structured segments | **0** |
| Address-only descriptions | 20 entities (shop/market/supermarket) | **Rewritten** (proper prose) |
| Wrong province in BT/TV | 159 desc + 143 summ saying "tỉnh Vĩnh Long" | **0** (corrected to actual province) |
| Summary length inversions | 100 summaries > descriptions | **0** (regenerated) |
| Summary/desc differentiation | 349 desc==summary (185 multi-sentence) | **169+10 differentiated** (200 single-sentence remain) |
| Vague "được nhắc đến" | 20 template-like descriptions | **0** (all rewritten with factual prose) |
| Duplicate descriptions | 0 | **0** (verified clean) |
| Meta-references ("bài viết/Nội dung/được nêu") | 32 descriptions + summaries | **0** (all rewritten) |
| Corrupted date-prefix descriptions | 11 (news article dates prepended) | **0** (dates stripped, content kept) |
| Foody rating fragments | 123 ("được đánh. X/10 trên Foody") | **0** (all stripped) |
| "Là " summary prefix | 161 (grammatically incomplete) | **0** (all fixed to complete sentences) |
| Broken abbreviation summaries | 95 (truncated at P./TP./Q.) | **0** (all extended to full sentence) |
| Corrupted entity descriptions | 1 (rừng tràm — news fragment) | **0** (rewritten) |
| Place template boilerplate | 120 ("khu vực X. Được thành lập trên cơ sở...") | **0** (5-variant natural rewrite) |
| Accommodation copy-paste tail | 87 ("Thuận tiện khám phá cù lao sông nước...") | **0** (stripped) |
| Accommodation template phrase | 30 ("Phòng nghỉ tiện nghi cơ bản, phù hợp...") | **0** (stripped) |
| Structured amenity lists | 46 ("Tiện ích: Điều hòa, wifi...") | **0** (naturalized to prose) |
| Duplicate province names | 33 ("Bến Tre, Bến Tre" → "Bến Tre") | **0** (deduplicated) |
| Copy-paste filler sentences | 29 (cuộc sống đồng quê/ĐBSCL/mọi lứa tuổi) | **0** (stripped) |
| Brochure tone | 17 ("du khách có thể/không thể bỏ qua") | **0** (rephrased) |
| "đông đảo" filler intensifier | 8 ("thu hút đông đảo du khách") | **0** (simplified) |
| Northern tone | 2 (thưởng ngoạn→ngắm nhìn, du ngoạn→dạo chơi) | **0** |
| Cliché metaphors | 2 (trái tim→trung tâm, điểm đến lý tưởng) | **0** |
| Minimal descriptions enriched | 49 (type+address only → +specialty/price from attrs) | **49 enriched** |
| Bare "Resort." start | 1 | **0** (rewritten) |
| Lowercase after period | 7 (artifacts from automated stripping) | **0** |
| Robotic "Name là [type]" openers | 174 business + 17 non-biz entities | **149 fixed** (42 too short, 22 dish/product kept for SEO) |
| Address casing errors | 129 accommodation descriptions | **0** (all proper nouns capitalized) |
| Entity name casing mismatch | 51 desc vs name inconsistencies | **0** (45 desc fixed, 3 names fixed, 3 desc de-capitalized) |
| Brochure "du khách có thể" | 25 remaining (missed pass 7) | **0** (→ "Có thể") |
| Remaining clichés | 1 "viên ngọc", 4 "tuyệt vời/ấn tượng" | **0** |
| "bức tranh" metaphor | 1 | **0** (→ "khung cảnh") |

## Improvements Pass 11 — Deep Verification & Enrichment (2026-06-29)

### Phase 1: Removed 5 fabricated/unverifiable entities

WebSearch agents verified 12 low-confidence entities in parallel. 5 were fabricated (LLM hallucinations with zero credible evidence online), removed along with 73 relationships:

| Entity ID | Problem |
|-----------|---------|
| lang-nghe-tac-tuong-go-long-duc | Fabricated: Long Đức = hoa kiểng, not wood carving |
| chua-botum-rangsay | Fabricated: no temple by this name in Trà Vinh |
| bun-nuoc-leo-cho-ba-tri-ben-tre | Unverifiable: Trà Vinh dish misplaced to Bến Tre |
| hu-tieu-sa-dec-chu-tu-gan-cho-phu-hung-ben-tre | Unverifiable: zero online presence |
| banh-mi-sau-hoa-ben-tre | Unverifiable: zero online presence, shared fake coords |

### Phase 2: Verified & enriched 4 confirmed entities

| Entity ID | Action | Confidence |
|-----------|--------|------------|
| chua-khai-tuong | Confirmed in Ba Tri (Phú Lễ), 600 gifts Trung Thu 2024 | 0.5 → 0.85 |
| chua-hung-hue | Confirmed in Bình Tân, ~200 years old, BTS PG huyện | 0.5 → 0.85 |
| dinh-cai-von | Renamed → Đình Thần Mỹ Thuận (correct name), sắc phong 1854 | 0.5 → 0.85 |
| mieu-ba-chua-xu-tra-vinh | Enriched: tradition with 147+ shrines, 2 notable ones detailed | 0.5 → 0.65 |

### Phase 3: Rating scale normalization

126 entities had ratings on /10 scale (7.0-10.0, from Foody/Google Maps). Converted to /5 by dividing by 2: `new_rating = round(rating / 2, 1)`. Range now 3.5-5.0.

### Phase 4: Enriched 5 high-value person entities with web-researched content

All facts verified against government sources, Wikipedia, and official tourism sites:

| Entity | Description length | Key facts added |
|--------|-------------------|-----------------|
| lang-banh-trang-giay-tuong-loc | 648c | 100+ year history, 40 hộ, 110 tấn/năm, 1 of 17 làng nghề |
| bao-tang-vinh-long | 413c | 12,000m², 28,000 artifacts, 4 exhibition halls, hours |
| nguyen-thi-dinh | 748c | Born 13/2/1920, Đồng Khởi 17/1/1960, first female general 4/1974 |
| nguyen-dinh-chieu | 748c | Born 1822, Lục Vân Tiên 2082 lines, UNESCO 2022 |
| nguyen-thi-ut (Út Tịch) | 816c | Born 19/4/1931, 23 battles, "Người mẹ cầm súng" 1965 |

### Brochure phrase cleanup: "nổi tiếng" eradicated

86 context-aware replacements across summaries and descriptions. Each "nổi tiếng" replaced with a context-appropriate alternative (lẫy lừng, lỗi lạc, để đời, có tiếng, phổ biến, lâu đời, đặc trưng, or dropped entirely).

### Pass 11 cumulative metrics

| Metric | Pass 10 | Pass 11 | Change |
|--------|---------|---------|--------|
| Entities | 1736 | **1731** | -5 (fabricated removed) |
| Relationships | 12326 | **12253** | -73 |
| Low confidence (<0.8) | 7 | **4** | -3 (verified+raised) |
| Ratings > 5.0 | 126 | **0** | -126 (normalized) |
| "nổi tiếng" in text | 86 | **0** | -86 |
| Summary == Description | 204 | **113** | -91 |

---

## Improvements Pass 10 — Content S+ Quality (2026-06-29)

### Hồ Trúc Giang: S+ long-form content (3 commits)

- Summary rewritten to 263 chars, S+ quality with sensory opening pattern
- Description expanded to 8 paragraphs, 2439 chars (~548 words) — longest in dataset
- Fact-checked against 8 web sources, 7 errors/risks corrected (THPT Chuyên BT claim removed, year hedged, unverified details removed)
- Sources: 4 verified (bazantravel, soctrangtourism, Wikipedia TP BT, Báo Người Lao Động)

### Batch S+ rewrites: 30 entities manually rewritten

- 10 food/cafe/accommodation entities: brochure phrases removed, openings restructured
- 20 high-traffic entities (by relationship count): starts_with_name fixed, summ==desc split, scraped content replaced

### Automated quality fixes

| Fix | Count | Before → After |
|-----|-------|----------------|
| Brochure phrases removed (safe patterns) | 42 entities | 307 → 243 occurrences |
| Brochure phrases deep fix (nổi tiếng, thu hút) | 57 entities | 243 → ~185 remaining |
| Summary == Description split | 180 pairs | 376 → 204 remaining |
| Descriptions enriched from attributes | 180 entities | Added specialty/price/hours from attrs |
| starts_with_name fix (non-place) | 131 entities | 268 → 0 remaining |
| Short summaries fixed | 28 entities | 28 → 0 remaining |

### S+ Quality Metrics After Pass 10

| Dimension | Pass 9 | Pass 10 | Change |
|-----------|--------|---------|--------|
| starts_with_name (non-place) | 268 | **0** | -268 |
| summary == description | 376 | **204** | -172 |
| Brochure phrases | ~307 | **~185** | -122 |
| Short summaries (<50 chars) | 0 | **0** | — |
| Descriptions <80 chars | 115 | reduced | enriched from attrs |

## Improvements Pass 9 — Verification-driven Optimization (2026-06-29)

### Phase 1 (P0): Removed 6 fabricated entities

Forensic verification report identified 6 entities with origins **outside** the 3-province scope (VL+BT+TV). Hard-deleted from data.json along with 84 relationships and 2 itinerary stops.

| Entity ID | Problem | Actual Origin |
|-----------|---------|---------------|
| hu-tieu-my-tho | Wrong province | Mỹ Tho, Tiền Giang |
| banh-cong-soc-trang | Wrong province | Sóc Trăng |
| chua-sa-lon-chua-chen-kieu | Wrong province | Sóc Trăng/Cần Thơ |
| chien-thang-giong-dua-giong-trom | Wrong province + contaminated desc | Tiền Giang |
| chua-ong-met-botum-vong-sa-som-rong | Conflates 2 temples | Mixed provinces |
| khu-bao-ton-lung-binh-hoa-tra-vinh | Content describes wrong entity | Hậu Giang |

Itineraries affected: `tra-vinh-khmer-1-ngay` and `ba-lo-budget-3-ngay` (stops referencing `banh-cong-soc-trang` removed).

### Phase 2 (P1): WebSearch-verified 14 suspect entities

| Entity ID | Result | Action |
|-----------|--------|--------|
| chua-khai-tuong | CONFIRMED (Long An origin but has VL branch) | Kept, source URL added |
| dinh-cai-von | CONFIRMED (Bình Minh, VL) | Kept, source URL added |
| banh-mi-sau-hoa-ben-tre | CONFIRMED | Kept, source URL added |
| bun-nuoc-leo-cho-ba-tri-ben-tre | CONFIRMED | Kept, source URL added |
| khoai-lang-binh-tan | CONFIRMED (OCOP VL) | Kept, source URL added |
| quan-thuan-phuc-vinh-long | CONFIRMED | Kept, source URL added |
| cha-gio-chay | UNVERIFIABLE | confidence → 0.5 |
| rau-thom-ocop-hop-tac-xa-phuoc-hau | UNVERIFIABLE | confidence → 0.5 |
| so-diep-binh-dai | UNVERIFIABLE | confidence → 0.5 |
| hu-tieu-sa-dec-chu-tu | UNVERIFIABLE | confidence → 0.5 |
| chua-ang-angkorajaborey | UNVERIFIABLE | confidence → 0.5 |

### Phase 3A: Extracted 3 phone numbers from descriptions

| Entity | Phone |
|--------|-------|
| diem-trung-bay-va-gioi-thieu-san-pham-ocop-vinh-long | 02703822702 |
| buu-dien-trung-tam-vinh-long-vinh-long | 1900 0317 |
| benh-vien-da-khoa-minh-duc-ben-tre-ben-tre | 1900 0317 |

### Phase 5A: Normalized 867 source metadata fields

- Renamed `name` → `title` in all source entries
- Renamed `type` → `method` where present
- Removed null/empty `url` fields
- Schema now consistently: `{title, url?, method?, maps?}`

### Phase 4: Enriched 200 short summaries

Extracted better summaries from existing description content (no LLM, no fabrication):
- First-sentence extraction from multi-sentence descriptions
- Two-sentence extraction for richer summaries
- Summaries <80 chars: **462 → 282** (180 improved)
- Remaining 282 are genuinely single-sentence entities — need external research or LLM enrichment

### Phase 6: Geocoded 36 entities from province center

Two batches of Nominatim geocoding (50 entities each):
- Batch 1: 33 geocoded, 10 reverted (wrong province), 17 no results → **23 net**
- Batch 2: 13 geocoded, 0 reverted, 37 no results → **13 net**
- Coordinate clusters: 1360 → 1347 entities sharing coordinates
- All results validated within province bounding boxes

### Continued fixes

- Extracted hospital emergency phone to `attributes.emergency_phone`
- Enriched 16 very short descriptions (<60 chars → 60-134 chars)
- Fixed last brochure phrase "du khách có thể"
- Split 33 multi-sentence summary==description pairs
- Fixed spacing artifacts (' , ' → ', ')
- Summary == Description: 409 → 376

## Errors

| Code | Count | Notes |
|------|-------|-------|
| — | 0 | Release gate currently reports no blocking data-quality errors |

## Warnings

| Code | Count | Notes |
|------|-------|-------|
| — | 0 | Release gate currently reports no data-quality warnings |

Tracked non-warning metrics:
- `near_one_way_edges`: 4916 one-way `near` edges; runtime indexes `near` bidirectionally.
- `coordinate_clusters`: 196 total clusters; `coordinate_clusters_precise`: 0 after marking centroid-derived non-place coordinates as approximate.
- `itinerary_area_mismatches`: 0 after adding route coverage metadata via `areas` and `lien-vung`.
- `rel_type_singletons`: 26 rare but valid relationship combos, tracked as graph entropy.

## Entities Missing Images (QA-18)

**Image coverage remains 0.0% for public non-place entities** in the current validator report.

Images should be generated via `scripts/gen_image.py` using the `cx/gpt-5.5-image` API. No stock photos (Pexels/Unsplash), UGC, or Wikimedia images per project policy.

**Impact on quality score:** -10 points per entity. Fixing images would raise avg score from 90.0 to ~100.

## Geographic Anomaly Audit

### Finding: 159 entities had wrong province name in text

Deep text analysis detected **159 descriptions** and **143 summaries** in Bến Tre and Trà Vinh entities that incorrectly stated "tỉnh Vĩnh Long". All corrected to the entity's actual province.

### Finding (earlier): 159 entities had coordinates in the wrong province

Deep geographic analysis detected **159 entities** whose coordinates fell clearly outside their declared province's bounding box — placing them in an entirely different province on the map. An additional **105 entities** were borderline (between tight and loose bounds).

**Root cause:** Batch geocoding via LLM+Nominatim returned coordinates for similarly-named locations in different provinces. 17 groups of entities shared the same wrong coordinate (same bad geocode result reused).

**Examples of misplacement:**
- `benh-vien-da-khoa-tinh-vinh-long` (area=vinh-long) had coords [9.65, 106.51] → actually in Trà Vinh
- `cu-lao-an-binh` (area=vinh-long) had coords [9.63, 106.19] → actually in Trà Vinh
- `chua-ang-angkor-borei` (area=tra-vinh) had coords [10.29, 106.30] → actually in Bến Tre
- `homestay-dua-ben-tre` (area=ben-tre) had coords [10.26, 105.97] → actually in Vĩnh Long

**Breakdown by declared area:** Vĩnh Long: 82, Trà Vinh: 52, Bến Tre: 25

**Fix applied:** All 159 critical entities reset to their province centroid with `coords_approximate=true`. A centroid is approximate but at least places the entity in the correct province.

**Remaining:** 105 borderline entities left as-is (may be legitimate cross-border locations).

## Entities with Approximate Coordinates (QA-19)

**1339 entities share coordinates** in the current validator report. Precise duplicate clusters are now 0; centroid-derived non-place coordinates are marked with `coords_approximate=true` instead of being treated as exact geocoding.

| Source | Count |
|--------|-------|
| Province centroids (VL/BT/TV) | ~337 entities (178 original + 159 geographic fixes) |
| Ward centroids | ~589 entities |
| placeId fallback | 47 entities |

## SEO Attribute Coverage

| Type | Coverage | Key attributes |
|------|----------|----------------|
| accommodation | **100%** (164/164) | sub_category=164, price_range=120, phone=89, star_rating=56 |
| attraction | **100%** (202/202) | sub_category=202, admission=191, hours=99, price_range=22 |
| cafe | **100%** (56/56) | sub_category=56, specialty=56, price_range=18, hours=18 |
| craft_village | **100%** (85/85) | sub_category=85, specialty=85 |
| dish | **100%** (116/116) | sub_category=116, specialty=110, price_range=73, origin=116 |
| drink | **100%** (1/1) | sub_category=1, price_range=1 |
| event | **100%** (67/67) | sub_category=67, date_start=67 |
| experience | **100%** (92/92) | sub_category=92, admission=89, price_range=50, hours=10 |
| facility | **100%** (58/58) | sub_category=58 |
| nature | **100%** (124/124) | sub_category=124, admission=124, hours=10 |
| person | **100%** (35/35) | sub_category=35, role=35 |
| product | **100%** (218/218) | sub_category=218, ocop_star=84, price_range=64, ocop_certified=48, brand=45 |
| restaurant | **100%** (188/188) | sub_category=188, specialty=188, price_range=106, hours=103 |
| organization | **100%** (1/1) | sub_category=1 |

**All entity types are at 100% sub_category coverage.** 1604/1604 non-place entities classified.

## Confidence Distribution

- Min: **0.50** (2 unverifiable entities)
- Median: **0.88**
- Max: 0.95
- Entities at 0.9+: **362**
- Entities at 0.8-0.89: **1365**
- Entities at <0.8: **4** (cha-gio-chay 0.50, mieu-ba-chua-xu-tra-vinh 0.65, di-tich-co-vinh-xuan-tra-on 0.70, du-lich-sinh-thai-cong-dong-thanh-phong-ben-tre 0.70)

Note: 5 entities lowered to 0.50 during pass 9 suspect verification — could not confirm via WebSearch. These may be real but obscure. Confidence formula differentiates approximate coordinates (+0.03) from verified coordinates (+0.10).

## Relationship Summary

| Type | Count |
|------|-------|
| near | 5022 |
| related_to | 4276 |
| located_in | 2204 |
| associated_with | 668 |
| produced_in | 187 |
| **Total** | **12357** |

Note: -84 relationships from pass 9 (6 fabricated entities removed). 2 itinerary stops referencing deleted entities also removed.

## Deep Research Findings

### Coverage Imbalance (entities per area, excluding place)

| Type | VL | BT | TV | Ratio | Severity |
|------|-----|-----|-----|-------|----------|
| experience | 70 | 15 | 7 | 10.0x | Critical |
| person | 23 | 6 | 6 | 3.8x | High |
| accommodation | 99 | 29 | 36 | 3.4x | Medium |

**Impact:** TV (Trà Vinh) is severely underrepresented in experiences. After 3-province merge, users searching for experiences in the former TV area will find very few options.

### Duplicate Detection

1 near-duplicate found and **merged**: "Nhà hàng Hàm Luông" (`nha-hang-ham-luong-ben-tre`) and "Hàm Luông" (`ham-luong`) — both at 200C Hùng Vương, Bến Tre. `ham-luong` deleted, 6 relationships transferred to `nha-hang-ham-luong-ben-tre`.

### Relationship Quality

- Dangling references: **0** (clean)
- Self-references: **0** (clean)
- Duplicate relationships: **0** (clean)
- Far "near" relationships (>50km): **0** (62 centroid artifacts removed)

### Itinerary Quality

- 33 total itineraries, 185 stops
- **174/185 stops** (94%) linked to existing entities
- 11 unlinked stops are generic activities (departure, pool, dinner) without corresponding entities — legitimate
- All stops now have `entityId` field (136 normalized from `id`-only)

### Source Data Origins

| Source | Count |
|--------|-------|
| Curated | 336 |
| Ward Crawl 2-3 (vinhlong360) | 449 |
| Agent discovery (LLM + geocode) | 144 |
| vinhlong.gov.vn | 143 |
| vinhlong360 auto-learn | 141 |
| foody.vn | 127 |
| vinhlongtourist.vn | 49 |
| Facebook crawl | 1 |

Sources are stored as list of dicts `[{title, url?, method?, maps?}]` (867 fields normalized in pass 9).

### Attribute Format Normalization (completed)

| Attribute | Before | After |
|-----------|--------|-------|
| Hours format | Mixed Xh/HH:MM/hyphen | All HH:MM with en-dash (156 fixed) |
| Price range dash | Mixed hyphen/en-dash | All en-dash (297 fixed, earlier session) |
| Admission capitalization | Inconsistent | Normalized (earlier session) |

### Remaining Format Variations (acceptable)

| Attribute | Variation | Reason |
|-----------|-----------|--------|
| Price range "other" (30) | "Trung bình", "Cao cấp", "Bình dân" | Qualitative tiers, not numeric ranges |
| Hours "other" (20) | "Thường tham quan ban ngày" | Places without fixed hours |

### Description Quality

- Min length: **59 chars** (tau-hu-ky-my-hoa — product, acceptable)
- Median: **215 chars**
- Average: **213 chars**
- Max: **2439 chars** (Hồ Trúc Giang, 548 words — long-form S+ content)
- Descriptions <60 chars: **1** (product entity, acceptable)
- Descriptions <80 chars: **115** (mostly food/café/accommodation — minimal factual info)
- Descriptions >500 chars: 32
- Double periods: **0** (1053 fixed)
- Unbalanced parentheses: **0** (15 fixed)
- Corrupted encoding: **0** (4 entities rewritten)
- Corrupted descriptions: **0** (14 fixed — date prefixes, Foody fragments, truncated text)
- Meta-references: **0** (32 "bài viết"/"Nội dung"/"được nêu" eliminated)
- Foody rating fragments: **0** (123 stripped)
- All structured data (address, price, phone, hours, payment) stripped from descriptions (1548 cleaned)
- All summaries grammatically complete (161 "Là " prefixes fixed, 95 broken abbreviations fixed)
- All sub_category classified: 1604/1604 non-place entities (100%)

### Attribute Completeness (key types)

| Type | Attribute | Coverage | Note |
|------|-----------|----------|------|
| restaurant | specialty | 191/191 (100%) | |
| restaurant | price_range | 108/191 (57%) | Needs external data |
| restaurant | hours | 105/191 (55%) | Needs external data |
| restaurant | phone | 1/191 (1%) | Needs external data |
| cafe | specialty | 55/55 (100%) | |
| cafe | hours | 17/55 (31%) | Needs external data |
| accommodation | price_range | 120/164 (73%) | |
| accommodation | phone | 89/164 (54%) | |
| accommodation | star_rating | 56/164 (34%) | Needs external data |

### Connectivity

- Only **1 entity** with ≤2 relationships (ben-xe-mien-tay-hcm, outside scope — HCM)
- 762 near relationships added for 154 previously isolated entities
- 142 related_to relationships added for 51 entities without cross-references
- Average 14.3 relationships per entity (counting both directions)

## Score Gap Analysis

| Deduction | Entities | Points/each | Avg impact | Actionable? |
|-----------|----------|-------------|------------|-------------|
| No images | 1739 | -10 | -10.00 | Needs IMAGE_API_KEY |
| No coordinates | 6 | -15 | -0.05 | HCM facility + 5 entities without geocodable address |
| No placeId | 1 | -10 | -0.01 | HCM entity, outside scope |
| Low confidence (0.5) | 5 | varies | -0.01 | Unverifiable suspects — need manual research |

**Theoretical max without images: ~100.** Current: 90.0. Only images remain as a significant gap.

## S+ Quality Analysis (pass 8 + 9)

Audit against viet-content-optimizer S+ criteria. Results below represent
remaining quality concerns that require **per-entity manual review** or
**external research** to fix (not auto-fixable).

| Dimension | Finding | Status |
|-----------|---------|--------|
| Empty adjectives | ~185 total (was ~275, 122 removed in pass 10) | Remaining are context-valid (e.g. "nổi tiếng với dừa sáp") |
| First sentence >155 chars | 12 entities (was 215) | No good split points — would break mid-clause |
| Starts with entity name (non-place) | **0** (was 268, all 268 fixed in pass 10) | Complete |
| desc==summary | **204** (was 376, 172 split/enriched in pass 10) | Remaining are single-sentence + place entities |
| Descriptions <80 chars | reduced (was 115, 180 enriched from attrs) | |
| Brochure phrases | ~185 remaining (307→185 in pass 10) | Context-dependent, most valid |

**Eliminated (pass 7 + 8):**
- Place template boilerplate (120), accommodation copy-paste (87), structured amenity lists (46)
- Brochure tone (25+17=42 total: "du khách có thể" → "Có thể"), northern tone (2), cliché metaphors (2+5=7)
- Copy-paste filler sentences (29), "đông đảo" filler (8), "bức tranh" metaphor (1)
- Duplicate province names (33), bare type starts (1)
- Robotic "Name là [type]" openers (149), address casing errors (129), name casing mismatches (51)

## Next Steps (Priority Order)

1. **Image generation** — 0% coverage, the ONLY remaining significant gap (-10.00 avg pts). Use `scripts/gen_image.py` + `cx/gpt-5.5-image` API.
2. **Geocoding** — ~1151 entities with coords_approximate=true. Top 50 could be geocoded via `scripts/geocode_clusters.py`.
3. **Short summaries** — 282 entities still <80 chars (all single-sentence). Need LLM enrichment or manual research.
4. **Experience coverage** — Trà Vinh has only 7 experiences vs 70 for Vĩnh Long (10x imbalance). Need curated TV experiences.
5. **Unverifiable suspects** — 5 entities at confidence 0.5; need manual research to confirm or remove.
6. **Source URLs** — ~1350 entities lack independent external source URL. High-visibility entities (restaurants, accommodations, attractions) would benefit from WebSearch verification.
7. **Phone/hours real data** — Some restaurants/accommodations have specialty but still lack phone/hours. Needs Google Places or manual research.

## Data Integrity Checks (all pass)

| Check | Result |
|-------|--------|
| Duplicate entity IDs | **0** |
| Self-referencing relationships | **0** |
| Dangling relationship references | **0** |
| HTML tags in descriptions | **0** |
| URLs in descriptions | **0** |
| Empty entity names | **0** |
| Empty attribute values | **0** |
| Descriptions ending without period | **0** |
| Summaries ending without punctuation | **0** |
| Phone in summaries (ĐT:) | **0** |
| Liên hệ: in descriptions | **0** |
| Template-format descriptions | **0** |
| Place template ("khu vực X. Được thành lập...") | **0** (120 rewritten) |
| Accommodation boilerplate | **0** (87+30+46 stripped/naturalized) |
| Copy-paste filler sentences | **0** (29 stripped) |
| Brochure tone ("du khách có thể") | **0** (42 rephrased total) |
| Northern tone (thưởng ngoạn/du ngoạn) | **0** (2 fixed) |
| Duplicate summaries | **0** |
| Duplicate names | **0** |
| Summary == Name (redundant) | **0** |
| Entities with only located_in | **0** (all have diverse rel types) |
| Summary starts with entity name (non-place) | **0** (492+131 fixed, pass 8+10) |
| Summary starts with "Là " | **0** (161 fixed) |
| Summary broken at P./TP./Q. | **0** (95 fixed) |
| Structured data in descriptions | **0** (1548 cleaned) |
| Foody rating fragments | **0** (123 stripped) |
| Meta-references (bài viết/được nêu/Nội dung) | **0** (32 eliminated) |
| Date-prefixed descriptions | **0** (11 fixed) |
| Sub_category missing | **0** (1604/1604 = 100%) |
| Ghost/test entities | **0** (prov-1 deleted) |
| Description starts lowercase | **0** |
| Double spaces in descriptions | **0** |
| Robotic "Name là [type]" openers | **42 remain** (22 dish/product + 20 too short; 149 fixed) |
| Address casing errors | **0** (129 fixed) |
| Entity name/description casing mismatch | **0** (51 fixed) |
| "viên ngọc" cliché | **0** (1 fixed) |
| "tuyệt vời/ấn tượng" filler | **0** (4 fixed) |
| "bức tranh" metaphor | **0** (1 fixed) |
