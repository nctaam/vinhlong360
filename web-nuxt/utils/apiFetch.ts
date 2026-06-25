// SSR-safe API fetch.
//
// VÌ SAO: internal $fetch('/api/...') trong ngữ-cảnh SSR render BỊ LỖI (Nitro proxy
// nội-bộ trả 502 / "fetch failed" khi render route) → useAsyncData trả rỗng →
// payload không có data → client tin payload, KHÔNG refetch → trang rỗng entity
// (đã gặp ở trang chủ /api/homepage; các trang catalog /api/entities dính y-hệt).
// Đã thử relative / 127.0.0.1 / useRequestURL().origin — đều fail; CHỈ URL công-khai
// (đi qua nginx→backend) chạy. Xem memory ref-vps-deploy "INCIDENT trang chủ fallback".
//
// CÁCH: trên SERVER fetch qua origin công-khai; trên CLIENT dùng relative (bình-thường).
// $fetch là global của Nuxt; utils/ auto-import → dùng apiFetch(...) thẳng trong page.
const SSR_ORIGIN = import.meta.dev ? 'http://localhost:8360' : 'https://vinhlong360.vn'

export function apiFetch<T = unknown>(url: string, opts: Record<string, unknown> = {}): Promise<T> {
  const base = import.meta.server ? SSR_ORIGIN : ''
  return $fetch<T>(url, base ? { baseURL: base, ...opts } : opts)
}
