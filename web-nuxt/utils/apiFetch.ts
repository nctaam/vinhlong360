import { DEFAULT_API_TIMEOUT_MS } from './requestDeadline'

// SSR-safe API fetch.
//
// Server-side relative $fetch('/api/...') can miss Nitro proxy route rules in
// development and during prerender. Use the configured backend origin on SSR,
// while the browser keeps using relative URLs so cookies/proxy rules work as
// expected. API_BASE can therefore point either to local agent or production.
const FALLBACK_SSR_ORIGIN = import.meta.dev ? 'http://localhost:8360' : 'https://vinhlong360.vn'

function getServerApiBase() {
  const configured = useRuntimeConfig().apiBase
  const base = typeof configured === 'string' && configured.trim()
    ? configured
    : FALLBACK_SSR_ORIGIN
  return base.replace(/\/+$/, '')
}

export function apiFetch<T = unknown>(url: string, opts: Record<string, unknown> = {}): Promise<T> {
  // retry: 0 là CHỦ Ý, không phải bỏ sót. ofetch mặc định tự thử lại GET/HEAD
  // một lần, TỨC THÌ, khi gặp 408/409/425/429/500/502/503/504 — không ai khai và
  // không ai thấy. Đo trên trang chủ (2026-08-23): GET /weather?area=vinh-long
  // trả 502 và xuất hiện HAI LẦN trong network log vì đúng cơ chế này.
  //
  // Thử lại tức thì là sai hướng với dự án này: backend chạy VPS 1GB/1CPU
  // (§B8 ngân sách), và 502 thường nghĩa là backend đang quá tải — nện thêm một
  // phát ngay lập tức chỉ làm nó tệ hơn. Bên gọi nào thật sự cần chống nhiễu
  // tạm thời thì tự truyền `retry`/`retryDelay`, để lựa chọn đó nhìn thấy được
  // tại chỗ gọi.
  const requestOptions = { retry: 0 as const, timeout: DEFAULT_API_TIMEOUT_MS, ...opts }
  if (/^https?:\/\//i.test(url)) return $fetch<T, string>(url, requestOptions)
  const requestUrl = url.startsWith('/') ? url : `/${url}`
  const baseURL = import.meta.server ? getServerApiBase() : ''
  return $fetch<T, string>(requestUrl, baseURL ? { baseURL, ...requestOptions } : requestOptions)
}
