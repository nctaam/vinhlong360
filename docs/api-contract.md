# VinhLong360 API Contract

Date: 2026-06-12
Status: Stabilization draft

This contract defines the shape that the FastAPI backend and Nuxt frontend should converge on.

## Entity

```json
{
  "id": "entity-id",
  "name": "Display name",
  "type": "attraction",
  "summary": "Short description",
  "description": "Long description",
  "coordinates": [10.0, 106.0],
  "area": "vinh-long",
  "placeId": "place-id",
  "source": "source label or URL",
  "season": { "months": [6, 7], "peak": [6] },
  "images": ["https://cdn/.../img1.webp"],
  "attributes": {}
}
```

Rules:

- `id`, `name`, and `type` are required.
- `coordinates` is the canonical coordinate field.
- `images` is an array of image URLs (DB column `images JSONB`; frontend đọc `entity.images[0]` làm cover + gallery). Mặc định `[]`.
- `season` (nếu có) gồm `months` và `peak` (mảng số tháng 1..12) — dùng cho wedge "theo mùa".
- Coordinates use `[lat, lng]` order.
- `coords` is legacy compatibility only.
- `area` identifies the province-level content bucket (`vinh-long`, `ben-tre`, or `tra-vinh`) when known.
- `placeId` may link an entity to a more specific place entity; `area` should not blindly inherit from `placeId` if entity text contradicts it.
- `attributes` must be an object when present.

## Relationship

Public relationship responses should use this canonical shape:

```json
{
  "source_id": "source-entity-id",
  "target_id": "target-entity-id",
  "rel_type": "near",
  "target_name": "Target display name",
  "target_type": "place",
  "source_name": "Source display name",
  "source_type": "attraction"
}
```

Compatibility aliases may be included during migration:

```json
{
  "from_id": "source-entity-id",
  "to_id": "target-entity-id",
  "type": "near"
}
```

Rules:

- New Nuxt code should prefer `source_id`, `target_id`, and `rel_type`.
- Backend may include both canonical fields and legacy aliases until all clients are migrated.
- Relationship endpoints must not return links to missing entity IDs.

## Core endpoints

### `GET /api/entities`

Returns a list of entities. Items should follow the Entity shape.

### `GET /api/entities/{id}`

Returns one entity by ID.

### `GET /api/entities/{id}/relationships`

Returns canonical Relationship items for direct relationships.

### `GET /api/places`

Returns place entities using the Entity shape.

### `GET /api/itineraries`

Returns itinerary summaries. Stop references should use entity IDs and normalized coordinates.

### `POST /chat`

Returns an assistant response. Tool/source metadata should use entity IDs that exist in the canonical dataset.

## Validation gates

The data contract is considered healthy when:

- No relationship references a missing entity ID.
- Entities with location data expose `coordinates`.
- `attributes` is always an object when present.
- Duplicate names are reviewed or explicitly allowed.
- Duplicate display names should be disambiguated when they represent different content records.
- Non-place summary coverage should remain at 100%.
- Public API relationship fields match Nuxt expectations.
