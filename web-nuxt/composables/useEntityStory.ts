// Turns attributes already present on an entity into a one-line STORY HOOK + a dateline
// eyebrow. No backend/schema change — pure re-sequencing of existing fields.
// Fallback chain (narrative §1): attributes.hook → attributes.highlight →
// famous_for / signature_dish → first sentence of description → summary.
import { AREA_META } from '~/composables/useConstants'

const PROVENANCE_TYPES = new Set(['product', 'craft_village'])

function firstSentence(s: string): string {
  const t = (s || '').trim()
  if (!t) return ''
  const m = t.split(/(?<=[.!?…])\s/)[0]
  return (m || t).trim()
}

// Many auto-imported summaries are literally "{name} — {address}". The name already
// shows as the card <h3>, so drop a leading, full-name + separator prefix to avoid the echo.
function stripLeadingName(teaser: string, name: string): string {
  const nm = (name || '').trim()
  if (!nm || teaser.length <= nm.length) return teaser
  const esc = nm.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const out = teaser.replace(new RegExp('^' + esc + '\\s*[—:·-]\\s*'), '').trim()
  return out || teaser
}

/** One-line story hook. '' when nothing usable. Provenance-prefixed for product/craft_village. */
export function entityStoryTeaser(entity: Record<string, any>): string {
  const a = entity?.attributes || {}
  let teaser = (a.hook || a.highlight || a.famous_for || a.signature_dish || '').toString().trim()
  if (!teaser) teaser = firstSentence(entity?.description || '')
  if (!teaser) teaser = (entity?.summary || '').toString().trim()
  if (!teaser) return ''
  teaser = stripLeadingName(teaser, entity?.name || '')
  // provenance-first (place before price/anything): prefix maker/place if not already named
  if (PROVENANCE_TYPES.has(entity?.type)) {
    const place = (entity?.place_name || entity?.placeName || a.origin || a.maker || '').toString().trim()
    if (place && !teaser.includes(place)) teaser = `${place} — ${teaser}`
  }
  return teaser
}

/** "{TYPE LABEL} · {AREA}" — area omitted when unknown. */
export function entityDateline(entity: Record<string, any>, typeLabel: string): string {
  const key = entity?.area || entity?.place_area || ''
  const area = key && (AREA_META as Record<string, { name: string }>)[key]?.name
  return area ? `${typeLabel} · ${area}` : typeLabel
}

export default function useEntityStory() {
  return { entityStoryTeaser, entityDateline }
}
