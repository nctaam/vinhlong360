// The one way any public surface links into the correction journey.
//
// Every entry point routes through here so the query carries exactly three
// non-secret hints — entity, field, source — and nothing else can creep in. The
// hints are a convenience: the canonical form re-fetches the entry's name,
// revision and allowed fields itself, so a stale or hand-edited link can
// mislead nobody.

export const CORRECTION_INTAKE_PATH = '/yeu-cau/sua-thong-tin'
export const CORRECTION_LOOKUP_PATH = '/yeu-cau/tra-cuu'

/** The field hints the intake form knows how to preselect. */
export const CORRECTION_FIELD_HINTS = new Set([
  'attributes.phone',
  'attributes.address',
  'attributes.opening_hours',
  'attributes.website',
  'attributes.price_range',
  'name',
  'summary',
  'description',
])

const ENTITY_ID_SHAPE = /^[a-z0-9][a-z0-9-]{0,199}$/i
const SOURCE_SHAPE = /^[a-z][a-z-]{0,39}$/

export function correctionIntakeLink(
  entityId: string,
  options: { field?: string | null, source?: string | null } = {},
): string {
  const id = String(entityId || '').trim()
  if (!ENTITY_ID_SHAPE.test(id)) return CORRECTION_INTAKE_PATH

  const query = new URLSearchParams({ entity: id })
  // Unknown hints are dropped, not forwarded: the URL is public surface, and
  // anything beyond these three names has no business riding it.
  if (options.field && CORRECTION_FIELD_HINTS.has(options.field)) {
    query.set('field', options.field)
  }
  if (options.source && SOURCE_SHAPE.test(options.source)) {
    query.set('source', options.source)
  }
  return `${CORRECTION_INTAKE_PATH}?${query.toString()}`
}
