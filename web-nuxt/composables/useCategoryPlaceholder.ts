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
    `<pattern id="grain" width="40" height="6" patternUnits="userSpaceOnUse">` +
    `<line x1="0" y1="3" x2="40" y2="3" stroke="rgba(255,255,255,0.05)" stroke-width="1"/>` +
    `</pattern>` +
    `</defs>` +
    `<rect width="400" height="240" fill="url(#g)"/>` +
    `<rect width="400" height="240" fill="url(#hl)"/>` +
    `<rect width="400" height="240" fill="url(#grain)"/>` +
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
  // Attraction: Mái đình Tiên Châu / Chùa cổ uốn cong di sản Nam Bộ
  attraction:
    `<path d="M6 22 C12 21 18 17 24 11 C30 17 36 21 42 22 C39 23 35 24 24 17 C13 24 9 23 6 22 Z" fill="rgba(255,255,255,.38)" stroke="currentColor" stroke-width="1.4"/>` +
    `<path d="M10 28 C16 27 20 25 24 21 C28 25 32 27 38 28 C35 29 32 30 24 25 C16 30 13 29 10 28 Z" fill="rgba(255,255,255,.25)"/>` +
    `<rect x="14" y="28" width="3" height="14" rx=".5" fill="rgba(255,255,255,.3)"/>` +
    `<rect x="31" y="28" width="3" height="14" rx=".5" fill="rgba(255,255,255,.3)"/>` +
    `<path d="M20 42 V31 H28 V42" stroke="currentColor" stroke-width="1.2" fill="none"/>` +
    `<line x1="8" y1="42" x2="40" y2="42" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>` +
    `<circle cx="24" cy="9" r="2" fill="rgba(255,255,255,.6)"/>`,
  // Dish: Nồi đất kho tiêu Nam Bộ bốc khói mộc mạc
  dish:
    `<ellipse cx="24" cy="31" rx="16" ry="7" fill="rgba(255,255,255,.35)"/>` +
    `<path d="M8 31 C8 39 15 42 24 42 C33 42 40 39 40 31" fill="rgba(255,255,255,.22)" stroke="currentColor" stroke-width="1.4"/>` +
    `<path d="M5 29 C4 31 5 33 8 33" stroke="currentColor" stroke-width="1.8" fill="none" stroke-linecap="round"/>` +
    `<path d="M43 29 C44 31 43 33 40 33" stroke="currentColor" stroke-width="1.8" fill="none" stroke-linecap="round"/>` +
    `<path d="M18 22 C16 16 20 13 18 8" stroke="currentColor" stroke-width="1.6" fill="none" stroke-linecap="round"/>` +
    `<path d="M24 20 C22 14 26 11 24 6" stroke="currentColor" stroke-width="1.8" fill="none" stroke-linecap="round"/>` +
    `<path d="M30 22 C28 16 32 13 30 8" stroke="currentColor" stroke-width="1.6" fill="none" stroke-linecap="round"/>`,
  // Product: Bưởi Năm Roi Bình Minh tròn mọng & Cành lá cù lao
  product:
    `<ellipse cx="24" cy="27" rx="14" ry="15" fill="rgba(255,255,255,.3)" stroke="currentColor" stroke-width="1.5"/>` +
    `<ellipse cx="21" cy="23" rx="4" ry="6" fill="rgba(255,255,255,.18)" transform="rotate(-15 21 23)"/>` +
    `<path d="M24 12 C24 8 26 6 28 5" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round"/>` +
    `<path d="M24 10 C29 10 33 7 35 4 C31 4 26 6 24 10 Z" fill="rgba(255,255,255,.45)" stroke="currentColor" stroke-width="1"/>` +
    `<circle cx="24" cy="41" r="1.5" fill="currentColor"/>`,
  // Accommodation: Nhà rường Nam Bộ homestay cù lao ven sông
  accommodation:
    `<path d="M7 23 L24 10 L41 23 L37 25 L24 15 L11 25 Z" fill="rgba(255,255,255,.4)" stroke="currentColor" stroke-width="1.4"/>` +
    `<rect x="12" y="24" width="24" height="15" fill="rgba(255,255,255,.22)" stroke="currentColor" stroke-width="1.4"/>` +
    `<rect x="21" y="29" width="6" height="10" fill="rgba(255,255,255,.35)"/>` +
    `<line x1="16" y1="28" x2="16" y2="33" stroke="currentColor" stroke-width="1.2"/>` +
    `<line x1="32" y1="28" x2="32" y2="33" stroke="currentColor" stroke-width="1.2"/>` +
    `<line x1="5" y1="41" x2="43" y2="41" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>` +
    `<line x1="10" y1="39" x2="10" y2="43" stroke="currentColor" stroke-width="1.5"/>` +
    `<line x1="38" y1="39" x2="38" y2="43" stroke="currentColor" stroke-width="1.5"/>`,
  // Craft: Lò gạch nung gốm đỏ Mang Thít hình vòm cổ kính
  craft:
    `<path d="M16 42 L18 20 C18 14 22 10 24 10 C26 10 30 14 32 20 L34 42 Z" fill="rgba(255,255,255,.28)" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>` +
    `<path d="M21 42 V32 C21 30 22.5 28 24 28 C25.5 28 27 30 27 32 V42 Z" fill="rgba(255,255,255,.45)"/>` +
    `<path d="M19 24 H29 M18 30 H30 M17 36 H31" stroke="rgba(255,255,255,.3)" stroke-width="1.2" stroke-linecap="round"/>` +
    `<path d="M24 8 C23 5 25 3 24 1" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" fill="none"/>` +
    `<path d="M27 9 C28 6 26 4 27 2" stroke="rgba(255,255,255,.4)" stroke-width="1.2" stroke-linecap="round" fill="none"/>`,
  // Nature: Hoa lục bình tím & sóng nước phù sa Cổ Chiên
  nature:
    `<path d="M24 8 C20 16 16 22 24 30 C32 22 28 16 24 8 Z" fill="rgba(255,255,255,.4)" stroke="currentColor" stroke-width="1.4"/>` +
    `<path d="M12 20 C18 20 22 24 24 30 C18 30 14 26 12 20 Z" fill="rgba(255,255,255,.28)" stroke="currentColor" stroke-width="1.2"/>` +
    `<path d="M36 20 C30 20 26 24 24 30 C30 30 34 26 36 20 Z" fill="rgba(255,255,255,.28)" stroke="currentColor" stroke-width="1.2"/>` +
    `<circle cx="24" cy="18" r="2.5" fill="rgba(255,255,255,.7)"/>` +
    `<path d="M6 38 C12 36 16 40 22 38 C28 36 32 40 42 38" stroke="currentColor" stroke-width="1.8" fill="none" stroke-linecap="round"/>` +
    `<path d="M10 42 C15 41 18 43 24 42 C30 41 34 43 38 42" stroke="rgba(255,255,255,.3)" stroke-width="1.4" fill="none" stroke-linecap="round"/>`,
  // Experience: Ghe tam bản Nam Bộ & Mái chèo sông Tiền
  experience:
    `<path d="M4 27 C12 32 28 32 44 24 C38 34 16 38 4 27 Z" fill="rgba(255,255,255,.38)" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>` +
    `<path d="M8 28 C16 26 28 26 38 23" stroke="rgba(255,255,255,.3)" stroke-width="1.2"/>` +
    `<path d="M16 28 C17 21 25 20 28 26" fill="rgba(255,255,255,.25)" stroke="currentColor" stroke-width="1.4"/>` +
    `<line x1="32" y1="12" x2="22" y2="38" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>` +
    `<path d="M22 38 L19 44 L24 43 Z" fill="rgba(255,255,255,.6)"/>` +
    `<path d="M38 28 C41 29 44 28 46 29" stroke="rgba(255,255,255,.4)" stroke-width="1.5" fill="none" stroke-linecap="round"/>`,
  // Itinerary: Dòng Cổ Chiên uốn lượn & Trạm dừng chân cù lao
  itinerary:
    `<path d="M8 12 C18 12 16 28 28 28 C36 28 36 38 42 40" stroke="rgba(255,255,255,.35)" stroke-width="6" fill="none" stroke-linecap="round"/>` +
    `<path d="M8 12 C18 12 16 28 28 28 C36 28 36 38 42 40" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-dasharray="3 3"/>` +
    `<circle cx="12" cy="12" r="3.5" fill="rgba(255,255,255,.6)" stroke="currentColor" stroke-width="1.5"/>` +
    `<circle cx="28" cy="28" r="3.5" fill="rgba(255,255,255,.6)" stroke="currentColor" stroke-width="1.5"/>` +
    `<circle cx="39" cy="38" r="3.5" fill="rgba(255,255,255,.6)" stroke="currentColor" stroke-width="1.5"/>`,
  // Event: Đầu rồng ghe Ngo & Tiếng trống hội giục giã
  event:
    `<path d="M12 36 C18 36 28 32 38 25 C40 23 42 20 40 18 C37 16 35 19 32 23 C24 28 16 30 10 32" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round"/>` +
    `<path d="M38 18 C41 14 45 13 46 16 C45 20 40 22 38 18 Z" fill="rgba(255,255,255,.5)"/>` +
    `<ellipse cx="20" cy="22" rx="7" ry="10" fill="rgba(255,255,255,.35)" stroke="currentColor" stroke-width="1.4"/>` +
    `<path d="M20 12 C24 12 27 16 27 22 C27 28 24 32 20 32" fill="none" stroke="rgba(255,255,255,.4)" stroke-width="1.2"/>` +
    `<line x1="16" y1="14" x2="26" y2="30" stroke="currentColor" stroke-width="1.5"/>`,
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
