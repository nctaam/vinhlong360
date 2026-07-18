const CACHE_VERSION = 'vl360-launch-v1'
const ASSET_CACHE = `${CACHE_VERSION}-assets`
const PRECACHE = ['/manifest.json', '/favicon.svg']

const REVIEWED_STATIC_ASSETS = [
  /^\/fonts\/.+\.(?:woff2?|ttf|otf)$/i,
  /^\/icons\/.+\.(?:avif|gif|ico|jpe?g|png|svg|webp)$/i,
  /^\/img\/.+\.(?:avif|gif|ico|jpe?g|png|svg|webp)$/i,
]

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(ASSET_CACHE)
      .then((cache) => cache.addAll(PRECACHE))
      .then(() => self.skipWaiting())
  )
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== ASSET_CACHE).map((key) => caches.delete(key))))
      .then(() => self.clients.claim())
  )
})

function isRootOrPrefix(pathname, root) {
  return pathname === root || pathname.startsWith(`${root}/`)
}

function mustBypass(request, url) {
  const accept = request.headers.get('accept') || ''
  return url.origin !== self.location.origin ||
    request.method !== 'GET' ||
    request.mode === 'navigate' ||
    accept.toLowerCase().includes('text/html') ||
    url.pathname === '/robots.txt' ||
    url.pathname.startsWith('/sitemap') ||
    isRootOrPrefix(url.pathname, '/_internal') ||
    isRootOrPrefix(url.pathname, '/api') ||
    url.pathname === '/events' ||
    url.pathname === '/recommend' ||
    isRootOrPrefix(url.pathname, '/seo') ||
    request.cache === 'no-store'
}

function isPolicyNeutralAsset(url) {
  return url.pathname.startsWith('/_nuxt/') ||
    PRECACHE.includes(url.pathname) ||
    url.pathname === '/apple-touch-icon.png' ||
    REVIEWED_STATIC_ASSETS.some((pattern) => pattern.test(url.pathname))
}

function hasNoStore(response) {
  const cacheControl = response.headers.get('cache-control') || ''
  return cacheControl.split(',').some((directive) => directive.trim().split('=', 1)[0].toLowerCase() === 'no-store')
}

function canCache(response) {
  return response.ok && response.type !== 'opaque' && response.type !== 'opaqueredirect' && !hasNoStore(response)
}

async function cacheFirst(request) {
  const cache = await caches.open(ASSET_CACHE)
  const cached = await cache.match(request)
  if (cached) return cached

  const response = await fetch(request)
  if (canCache(response)) await cache.put(request, response.clone())
  return response
}

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url)
  if (mustBypass(event.request, url) || !isPolicyNeutralAsset(url)) return

  event.respondWith(cacheFirst(event.request))
})
