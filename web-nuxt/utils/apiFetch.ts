// SSR-safe API fetch.
//
// Server-side relative $fetch('/api/...') can miss Nitro proxy route rules in
// development and during prerender. Use the configured backend origin on SSR,
// while the browser keeps using relative URLs so cookies/proxy rules work as
// expected. API_BASE can therefore point either to local agent or production.
const FALLBACK_SSR_ORIGIN = import.meta.dev ? 'http://localhost:8360' : 'https://vinhlong360.vn'

function getServerApiBase() {
  const configured = useRuntimeConfig().public.apiBase
  const base = typeof configured === 'string' && configured.trim()
    ? configured
    : FALLBACK_SSR_ORIGIN
  return base.replace(/\/+$/, '')
}

export function apiFetch<T = unknown>(url: string, opts: Record<string, unknown> = {}): Promise<T> {
  if (/^https?:\/\//i.test(url)) return $fetch<T>(url, opts)
  const requestUrl = url.startsWith('/') ? url : `/${url}`
  const baseURL = import.meta.server ? getServerApiBase() : ''
  return $fetch<T>(requestUrl, baseURL ? { baseURL, ...opts } : opts)
}
