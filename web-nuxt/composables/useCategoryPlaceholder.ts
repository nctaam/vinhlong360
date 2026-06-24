// useCategoryPlaceholder — deterministic per-entity SVG placeholder + category glyph.
//
// 0/1817 entities have real photos. Instead of repeating ~15 stock category tiles
// (which looks crude + makes every card of a type identical), we generate a unique
// pastel gradient per entity, seeded by a 32-bit hash of its id. Same id → same
// gradient forever (deterministic, SSR-safe, no random). A centered white-on-
// transparent motif glyph per category keeps it legible + on-theme.
//
// ADDITIVE: callers fall back to this only when there is no real photo. The output
// is a plain CSS background-image string + an inline SVG string, so it degrades to
// a flat gradient with no JS interaction needed.

// ── 32-bit FNV-ish string hash → stable unsigned int ──────────────────────────
function hashString(input: string): number {
  let h = 2166136261 >>> 0
  for (let i = 0; i < input.length; i++) {
    h ^= input.charCodeAt(i)
    // h *= 16777619 (FNV prime) via shifts to stay in 32-bit range
    h = (h + ((h << 1) + (h << 4) + (h << 7) + (h << 8) + (h << 24))) >>> 0
  }
  return h >>> 0
}

// Base hue (degrees) NEO theo BẢN-SẮC category + hệ màu vùng (clay/amber/leaf/river)
// → mọi card cùng loại chung một họ màu (nhận-diện được loại qua màu), mỗi entity vẫn
// khác nhau nhờ jitter ±15° + sáng/góc theo hash. Loại lạ → hue ngẫu-nhiên theo hash.
const CATEGORY_HUE: Record<string, number> = {
  nature: 132, experience: 122,                                  // xanh lá miệt vườn
  dish: 22, product: 30, craft: 16, economy: 34,                 // ấm cam–đất (đặc sản/làng nghề)
  attraction: 196, history: 204, place: 200, facility: 206, org: 200, // teal sông nước
  accommodation: 40,                                             // sand ấm
  event: 344, person: 350,                                       // lễ hội rực hồng–đỏ
  itinerary: 168,                                                // ngọc–lam
}

/**
 * Build a CSS `background-image` value: a URI-encoded data-uri SVG carrying a
 * deterministic pastel linear-gradient. Hue + angle are derived from a hash of
 * the entity id, so each entity is visually distinct yet stable across renders.
 */
export function generateCategoryPlaceholder(entityId: string | number, category: string): string {
  const h = hashString(String(entityId))

  // Hue NEO theo category (nhất-quán bản-sắc) + jitter ±15° cho khác-biệt từng entity.
  const base = CATEGORY_HUE[category] ?? (h % 360)
  const hue = (base + (h % 31) - 15 + 360) % 360
  const hue2 = (hue + 24) % 360

  // Sâu + bão-hoà hơn (không còn pastel nhạt): sat 64–77%, light 39–56% → màu "có chủ-ý",
  // watermark trắng + chữ trắng đọc rõ; chênh light giữa 2 stop tạo chiều sâu.
  const sat1 = 64 + (h % 14)            // 64..77
  const light1 = 47 + ((h >>> 4) % 10)  // 47..56
  const sat2 = 66 + ((h >>> 8) % 12)    // 66..77
  const light2 = 39 + ((h >>> 12) % 9)  // 39..47

  // Gradient angle 0–359° from the hash (independent bits from the hue).
  const angle = (h >>> 16) % 360

  const c1 = `hsl(${hue}, ${sat1}%, ${light1}%)`
  const c2 = `hsl(${hue2}, ${sat2}%, ${light2}%)`

  // gradientTransform rotate() works in the gradient's bounding-box space (0..1),
  // so rotate around its centre (0.5, 0.5). radialGradient 'hl' = vầng sáng góc
  // trên-trái tạo chiều sâu (đỡ phẳng).
  const svg =
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 240" preserveAspectRatio="xMidYMid slice">` +
    `<defs>` +
    `<linearGradient id="g" gradientTransform="rotate(${angle} 0.5 0.5)">` +
    `<stop offset="0" stop-color="${c1}"/>` +
    `<stop offset="1" stop-color="${c2}"/>` +
    `</linearGradient>` +
    `<radialGradient id="hl" cx="0.26" cy="0.18" r="0.9">` +
    `<stop offset="0" stop-color="rgba(255,255,255,0.22)"/>` +
    `<stop offset="0.55" stop-color="rgba(255,255,255,0)"/>` +
    `</radialGradient>` +
    `</defs>` +
    `<rect width="400" height="240" fill="url(#g)"/>` +
    `<rect width="400" height="240" fill="url(#hl)"/>` +
    `</svg>`

  // Single quotes inside the url(): the value lands in a double-quoted SSR
  // `style="..."` attribute, so double quotes here would terminate the attribute
  // (server renders empty → hydration style mismatch). Single quotes are safe
  // because the SVG is URI-encoded (no raw single quotes survive).
  return `url('data:image/svg+xml,${encodeURIComponent(svg)}')`
}

// ── Category motif glyphs ─────────────────────────────────────────────────────
// White-on-transparent SVG strings, centred via the wrapper. fill uses translucent
// white so the glyph reads as a watermark over the gradient; stroke uses
// currentColor so callers can tint it. viewBox 0 0 48 48 to match CategoryIcon.vue.
const ICONS: Record<string, string> = {
  // Attraction: mái chùa / núi
  attraction:
    `<rect x="14" y="24" width="20" height="18" rx="2" fill="rgba(255,255,255,.25)"/>` +
    `<path d="M10 24 L24 10 L38 24Z" fill="rgba(255,255,255,.35)"/>` +
    `<path d="M16 24 L24 14 L32 24Z" fill="rgba(255,255,255,.18)"/>` +
    `<rect x="21" y="30" width="6" height="12" rx="3" fill="rgba(255,255,255,.22)"/>` +
    `<circle cx="24" cy="18" r="2.5" fill="rgba(255,255,255,.5)"/>`,
  // Dish: đĩa / bát có khói
  dish:
    `<ellipse cx="24" cy="30" rx="16" ry="6" fill="rgba(255,255,255,.3)"/>` +
    `<path d="M8 28 Q8 20 24 20 Q40 20 40 28" fill="rgba(255,255,255,.18)"/>` +
    `<path d="M16 18 Q18 12 20 14" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round"/>` +
    `<path d="M24 16 Q26 10 28 12" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round"/>` +
    `<path d="M32 18 Q34 12 36 14" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round"/>` +
    `<line x1="8" y1="36" x2="40" y2="36" stroke="rgba(255,255,255,.25)" stroke-width="2"/>`,
  // Product: trái cây tròn
  product:
    `<circle cx="24" cy="26" r="14" fill="rgba(255,255,255,.3)"/>` +
    `<circle cx="24" cy="26" r="10" fill="rgba(255,255,255,.2)"/>` +
    `<path d="M24 12 Q26 6 30 8" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round"/>` +
    `<path d="M24 12 Q22 7 18 9" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round"/>` +
    `<ellipse cx="20" cy="24" rx="3" ry="4" fill="rgba(255,255,255,.18)" transform="rotate(-15 20 24)"/>`,
  // Accommodation: nhà
  accommodation:
    `<rect x="12" y="22" width="24" height="18" rx="2" fill="rgba(255,255,255,.28)"/>` +
    `<path d="M8 22 L24 10 L40 22" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>` +
    `<rect x="20" y="30" width="8" height="10" rx="1" fill="rgba(255,255,255,.22)"/>` +
    `<rect x="15" y="26" width="5" height="5" rx=".5" fill="rgba(255,255,255,.18)"/>` +
    `<rect x="28" y="26" width="5" height="5" rx=".5" fill="rgba(255,255,255,.18)"/>`,
  // Craft: gốm / bình
  craft:
    `<path d="M18 38 Q16 30 17 24 Q18 18 22 16 Q24 15 26 16 Q30 18 31 24 Q32 30 30 38Z" fill="rgba(255,255,255,.3)"/>` +
    `<path d="M20 16 Q22 12 24 12 Q26 12 28 16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>` +
    `<line x1="20" y1="26" x2="28" y2="26" stroke="rgba(255,255,255,.3)" stroke-width="1.5"/>` +
    `<line x1="19" y1="30" x2="29" y2="30" stroke="rgba(255,255,255,.3)" stroke-width="1.5"/>` +
    `<line x1="18" y1="34" x2="30" y2="34" stroke="rgba(255,255,255,.3)" stroke-width="1.5"/>`,
  // Nature: lá
  nature:
    `<path d="M14 34 Q14 16 34 14 Q36 32 18 36 Q16 36 14 34Z" fill="rgba(255,255,255,.3)"/>` +
    `<path d="M16 34 Q26 24 34 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>` +
    `<path d="M22 30 Q24 26 28 26" fill="none" stroke="rgba(255,255,255,.35)" stroke-width="1.4" stroke-linecap="round"/>` +
    `<path d="M20 26 Q22 22 26 22" fill="none" stroke="rgba(255,255,255,.35)" stroke-width="1.4" stroke-linecap="round"/>`,
  // Experience: lúa / lá đôi
  experience:
    `<path d="M24 42 Q24 28 18 18 Q14 12 10 10" stroke="currentColor" stroke-width="2.5" fill="none" stroke-linecap="round"/>` +
    `<path d="M24 42 Q24 26 30 16 Q34 10 38 8" stroke="currentColor" stroke-width="2.5" fill="none" stroke-linecap="round"/>` +
    `<path d="M18 18 Q14 16 8 18" stroke="rgba(255,255,255,.4)" stroke-width="2" fill="none" stroke-linecap="round"/>` +
    `<path d="M20 24 Q16 22 10 24" stroke="rgba(255,255,255,.4)" stroke-width="2" fill="none" stroke-linecap="round"/>` +
    `<path d="M30 16 Q34 14 40 16" stroke="rgba(255,255,255,.4)" stroke-width="2" fill="none" stroke-linecap="round"/>` +
    `<path d="M28 22 Q32 20 38 22" stroke="rgba(255,255,255,.4)" stroke-width="2" fill="none" stroke-linecap="round"/>`,
  // Itinerary: tuyến đường
  itinerary:
    `<circle cx="14" cy="14" r="4" fill="rgba(255,255,255,.4)"/>` +
    `<circle cx="34" cy="34" r="4" fill="rgba(255,255,255,.4)"/>` +
    `<path d="M14 18 Q14 30 24 30 Q34 30 34 30" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-dasharray="1 5"/>` +
    `<path d="M14 18 Q14 30 26 30 L34 30" fill="none" stroke="rgba(255,255,255,.3)" stroke-width="2.4" stroke-linecap="round"/>`,
  // Event: lồng đèn
  event:
    `<line x1="24" y1="6" x2="24" y2="12" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>` +
    `<rect x="20" y="11" width="8" height="3" rx="1" fill="rgba(255,255,255,.35)"/>` +
    `<path d="M16 16 Q24 12 32 16 Q34 26 32 34 Q24 38 16 34 Q14 26 16 16Z" fill="rgba(255,255,255,.3)"/>` +
    `<line x1="22" y1="15" x2="22" y2="35" stroke="rgba(255,255,255,.3)" stroke-width="1.2"/>` +
    `<line x1="26" y1="15" x2="26" y2="35" stroke="rgba(255,255,255,.3)" stroke-width="1.2"/>` +
    `<line x1="24" y1="36" x2="24" y2="42" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>`,
}

// Aliases — categories that share a motif.
ICONS.org = ICONS.accommodation!
ICONS.facility = ICONS.accommodation!
ICONS.history = ICONS.attraction!
ICONS.place = ICONS.attraction!
ICONS.economy = ICONS.product!
ICONS.person = ICONS.experience!

// Fallback motif: a soft target.
const DEFAULT_ICON =
  `<circle cx="24" cy="24" r="12" fill="rgba(255,255,255,.2)"/>` +
  `<circle cx="24" cy="24" r="4" fill="rgba(255,255,255,.32)"/>`

/**
 * Return a full inline SVG string (a centred white-on-transparent motif) for the
 * given category. Safe to bind with v-html. Uses currentColor for strokes so the
 * caller can tint via CSS `color`.
 */
export function generateCategoryIcon(category: string): string {
  const motif = ICONS[category] ?? DEFAULT_ICON
  return (
    `<svg viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg" aria-hidden="true" ` +
    `width="64" height="64" fill="none">${motif}</svg>`
  )
}

export default function useCategoryPlaceholder() {
  return { generateCategoryPlaceholder, generateCategoryIcon }
}
