# Data Quality Report

Generated: 2026-06-27
Source: `web/data.json` (1753 entities, 8415 relationships, 33 itineraries)
Tool: `python scripts/validate_data.py`

## Summary

| Metric | Value |
|--------|-------|
| Entity quality score (avg) | 81.7/100 |
| Critical entities (0-29) | 0 |
| Needs work (30-59) | 5 |
| OK (60-79) | 955 |
| Good (80-100) | 668 |
| Errors | 1 |
| Warnings | 13 |
| Graph components | 1 (fully connected) |
| Isolated entities | 0 |
| Broken relationships | 0 |

## Errors

| Code | Count | Description |
|------|-------|-------------|
| `produced_in_target_type` | 2 | `produced_in` relationships target an entity that is not place or craft_village |

## Warnings

| Code | Count | Notes |
|------|-------|-------|
| `near_asymmetric` | 3096 | Near relationships are one-way (A->B without B->A) |
| `timestamp_inversions` | 1753 | updatedAt before created_at (all entities — likely import artifact) |
| `coordinate_clusters` | 229 clusters (1374 entities) | Entities share exact same coordinates (ward centroids) |
| `missing_place_id` | 66 | Non-place entities missing placeId assignment |
| `itinerary_area_mismatch` | 59 | Itinerary stops reference entities outside declared area |
| `summary_long` | 53 | Summary > 500 chars |
| `invalid_phone_format` | 44 | Phone not matching VN format (+84/0 + 9-10 digits) |
| `rel_type_singletons` | 38 | Relationship combos appearing only once |
| `missing_location` | 5 | Non-place entities with no coordinates |
| `unknown_rel_types` | 3 | Unknown types: hosts, offered_by, supplies_to |
| `summary_short` | 1 | Summary < 50 chars: `banh-nhat-ngoc` (38 chars) |
| `name_too_long` | 1 | Entity name > 100 chars |
| `data_js_unknown_shape` | 1 | web/data.js shape not recognized |

## Entities Missing Images (QA-18)

**All 1753 entities have `images: []`** — 0% image coverage.

This is expected at the current project stage. Images are served via external URLs (Pexels/Unsplash/UGC) and are being added through the admin CMS as content is curated. The `images` field exists on every entity as an empty array, ready for population.

Top entity types by count (all at 0% image coverage):

| Type | Count |
|------|-------|
| attraction | 320 |
| product | 218 |
| history | 192 |
| accommodation | 164 |
| nature | 125 |
| place | 125 |
| dish | 120 |
| restaurant | 94 |
| experience | 92 |
| craft_village | 85 |
| event | 67 |
| facility | 58 |
| cafe | 38 |
| person | 35 |

## Entities with Approximate Coordinates (QA-19)

**0 entities have `coords_approximate=true`** — the field is not yet populated in `data.json`.

The `coords_approximate` flag was introduced in the API contract (GD3) to mark entities whose coordinates were derived from ward centroids rather than exact locations. However, the 229 coordinate clusters (1374 entities sharing exact coordinates) suggest many entities likely use centroid-derived coordinates but have not been flagged.

**Recommendation:** A future data pass should set `coords_approximate=true` for entities in coordinate clusters, especially those sharing coordinates with their parent place entity.

## SEO Attribute Coverage

| Type | Coverage | Key attributes |
|------|----------|----------------|
| accommodation | 76% (124/164) | star_rating=48, price_range=82, phone=105 |
| event | 85% (57/67) | date_start=57 |
| person | 60% (21/35) | role=21 |
| dish | 33% (40/120) | specialty=5, price_range=40 |
| product | 33% (72/218) | price=51, ocop=24 |
| attraction | 24% (76/320) | admission=76 |
| nature | 14% (17/125) | admission=17 |
| experience | 11% (10/92) | admission=10 |
| restaurant | 10% (9/94) | specialty=6, price_range=7 |
| craft_village | 4% (3/85) | specialty=1, phone=2 |
| cafe | 0% (0/38) | specialty=0, price_range=0 |

## Confidence Distribution

- Min: 0.5
- Median: 0.7
- Max: 1.0
- Entities with confidence score: 1628/1753
