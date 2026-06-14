const CACHE_VERSION = 'vl360-v3'
const ASSET_CACHE = `${CACHE_VERSION}-assets`
const HTML_CACHE = `${CACHE_VERSION}-html`
const PRECACHE = ['/manifest.json', '/favicon.svg']

const BYPASS_PREFIXES = [
  '/api/',
  '/admin',
  '/admin-api/',
  '/auth/',
  '/chat/',
  '/events',
  '/feedback/',
  '/freshness/',
  '/health',
  '/recommend',
  '/reload',
  '/weather/',
]

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(ASSET_CACHE)
      .then((cache) => cache.addAll(PRECACHE))
      .then(() => self.skipWaiting())
  )
})

self.addEventListener('activate', (event) => {
  const keep = new Set([ASSET_CACHE, HTML_CACHE])
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((key) => !keep.has(key)).map((key) => caches.delete(key))))
      .then(() => self.clients.claim())
  )
})

function shouldBypass(url) {
  if (url.origin !== self.location.origin) return true
  return BYPASS_PREFIXES.some((prefix) => url.pathname === prefix || url.pathname.startsWith(prefix))
}

function isAsset(url, request) {
  return url.pathname.startsWith('/_nuxt/') ||
    request.destination === 'style' ||
    request.destination === 'script' ||
    request.destination === 'font' ||
    request.destination === 'image' ||
    /\.(?:css|js|mjs|png|jpg|jpeg|webp|svg|ico|woff2?|json)$/i.test(url.pathname)
}

async function networkFirst(request, cacheName) {
  const cache = await caches.open(cacheName)
  try {
    const response = await fetch(request)
    if (response.ok) cache.put(request, response.clone())
    return response
  } catch (_error) {
    return (await cache.match(request)) || Response.error()
  }
}

async function cacheFirst(request, cacheName) {
  const cache = await caches.open(cacheName)
  const cached = await cache.match(request)
  if (cached) return cached
  const response = await fetch(request)
  if (response.ok) cache.put(request, response.clone())
  return response
}

// Phục vụ cache ngay + cập nhật nền → ảnh tên-cố-định (/img/*) tự refresh sau 1 lần tải
async function staleWhileRevalidate(request, cacheName) {
  const cache = await caches.open(cacheName)
  const cached = await cache.match(request)
  const fetching = fetch(request)
    .then((response) => { if (response.ok) cache.put(request, response.clone()); return response })
    .catch(() => cached || Response.error())
  return cached || fetching
}

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return
  const url = new URL(event.request.url)
  if (shouldBypass(url)) return

  const accept = event.request.headers.get('accept') || ''
  if (event.request.mode === 'navigate' || accept.includes('text/html')) {
    event.respondWith(networkFirst(event.request, HTML_CACHE))
    return
  }

  if (isAsset(url, event.request)) {
    // /_nuxt/ = file content-hashed (bất biến) → cacheFirst; còn lại (/img/* tên cố định) → SWR
    if (url.pathname.startsWith('/_nuxt/')) {
      event.respondWith(cacheFirst(event.request, ASSET_CACHE))
    } else {
      event.respondWith(staleWhileRevalidate(event.request, ASSET_CACHE))
    }
    return
  }

  event.respondWith(networkFirst(event.request, ASSET_CACHE))
})
