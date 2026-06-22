const apiBase = process.env.API_BASE || 'http://localhost:8360'

export default defineNuxtConfig({
  compatibilityDate: '2025-05-15',

  ssr: true,

  modules: ['@nuxt/fonts', '@nuxt/image', '@nuxtjs/color-mode'],

  // Dark mode: thêm class .dark vào <html>; mặc định theo OS, nút toggle ghi đè.
  colorMode: { classSuffix: '', preference: 'system', fallback: 'light', storageKey: 'vl360-color-mode' },

  // Self-host font (bỏ Google CDN) — giảm latency bên thứ 3 + CLS (font-metric optimization).
  fonts: {
    defaults: { weights: [400, 600, 700, 800], subsets: ['vietnamese', 'latin', 'latin-ext'] },
    families: [{ name: 'Inter', provider: 'google' }],
    display: 'swap',
  },

  // Ảnh: provider weserv (miễn phí, transcode WebP off-VPS) — KHÔNG dùng IPX
  // (VPS 1GB/1CPU không kham transcode remote-image server-side; xem docs/design-system-plan.md).
  image: {
    provider: 'weserv',
    weserv: { baseURL: 'https://images.weserv.nl' },
    format: ['webp'],
    quality: 72,
    screens: { sm: 360, md: 480, lg: 720, xl: 960 },
  },

  css: [
    '~/assets/css/variables.css',
    '~/assets/css/base.css',
    '~/assets/css/components.css',
    '~/assets/css/cards.css',
    // detail.css KHÔNG global: chỉ 3 trang chi tiết (dia-diem/xa-phuong/lich-trinh) dùng
    // → import qua <style src> trong 3 page đó (bỏ ~35KB khỏi entry.css mọi trang).
    // detail-shared.css = phần dùng-chung (breadcrumb/highlights/lightbox/map) GIỮ global.
    '~/assets/css/detail-shared.css',
    '~/assets/css/catalog.css',
    // events.css KHÔNG global: chỉ le-hoi.vue + su-kien.vue dùng (xem <style src> trong 2 page đó)
    // → bỏ ~10.5KB khỏi entry.css mọi trang. Verify usage: scratch/analyze_css.py.
    '~/assets/css/dark-overrides.css',
  ],

  app: {
    pageTransition: { name: 'page', mode: 'out-in' },
    head: {
      htmlAttrs: { lang: 'vi' },
      charset: 'utf-8',
      viewport: 'width=device-width, initial-scale=1, viewport-fit=cover',
      title: 'vinhlong360 — Du lịch & Sản phẩm địa phương',
      meta: [
        { name: 'description', content: 'Cổng du lịch và sản phẩm địa phương Vĩnh Long: trải nghiệm miệt vườn, đặc sản theo mùa, OCOP, làng nghề và lịch trình gợi ý.' },
        { name: 'theme-color', content: '#9C3D22', media: '(prefers-color-scheme: light)' },
        { name: 'theme-color', content: '#1a1a1a', media: '(prefers-color-scheme: dark)' },
        { name: 'color-scheme', content: 'light dark' },
        { name: 'format-detection', content: 'telephone=no' },
        { name: 'apple-mobile-web-app-capable', content: 'yes' },
        { name: 'apple-mobile-web-app-status-bar-style', content: 'black-translucent' },
        { name: 'apple-mobile-web-app-title', content: 'VinhLong360' },
        { property: 'og:site_name', content: 'vinhlong360' },
        { property: 'og:locale', content: 'vi_VN' },
        { property: 'og:type', content: 'website' },
        { property: 'og:image', content: 'https://vinhlong360.vn/img/og-default.jpg' },
        { property: 'og:image:width', content: '1536' },
        { property: 'og:image:height', content: '1024' },
        { name: 'twitter:card', content: 'summary_large_image' },
        { name: 'twitter:site', content: '@vinhlong360' },
        { name: 'twitter:image', content: 'https://vinhlong360.vn/img/og-default.jpg' },
      ],
      link: [
        { rel: 'preconnect', href: 'https://images.weserv.nl' },
        { rel: 'dns-prefetch', href: 'https://maptiles.openmap.vn' },
        { rel: 'sitemap', type: 'application/xml', href: '/sitemap.xml' },
        { rel: 'icon', type: 'image/svg+xml', href: '/favicon.svg' },
        { rel: 'manifest', href: '/manifest.json' },
        { rel: 'apple-touch-icon', sizes: '180x180', href: '/apple-touch-icon.png' },
      ],
      script: [
        // Add `js` to <html> BEFORE first paint so the JS-gated .reveal rule
        // (html.js .reveal { opacity:0 }) only ever hides content when JS is
        // present — no flash-of-hidden, and full visibility when JS is off/slow.
        { children: "document.documentElement.classList.add('js')", tagPosition: 'head' },
        { innerHTML: "if('serviceWorker' in navigator){window.addEventListener('load',function(){navigator.serviceWorker.register('/sw.js')})}", type: 'text/javascript' },
      ],
    },
  },

  runtimeConfig: {
    public: {
      apiBase,
      ndaMapKey: process.env.NDA_MAP_KEY || 'J2TnJ4JIEP3WTBnFwzVPAxTP7KKfW1OD',
    },
  },

  routeRules: {
    // ISR: entity detail pages cached 1h, revalidate in background
    '/dia-diem/**': { swr: 3600 },
    '/khu-vuc/**': { swr: 3600 },
    '/xa-phuong/**': { swr: 3600 },
    // Listing pages: shorter cache
    '/du-lich': { swr: 600 },
    '/san-pham': { swr: 600 },
    '/ocop': { swr: 600 },
    '/le-hoi': { swr: 600 },
    '/luu-tru': { swr: 600 },
    '/lich-trinh': { swr: 600 },
    '/lich-trinh/**': { swr: 1800 },
    '/su-kien': { swr: 300 },
    '/theo-mua': { swr: 600 },
    // Static pages: long cache
    '/': { swr: 300 },
    '/ban-do': { swr: 1800 },
    '/admin/**': { ssr: false },
    '/api/site-settings': { proxy: `${apiBase}/api/site-settings`, swr: 60 },
    '/api/stats': { proxy: `${apiBase}/api/stats`, swr: 300 },
    '/api/places': { proxy: `${apiBase}/api/places`, swr: 600 },
    '/api/entities': { proxy: `${apiBase}/api/entities`, swr: 120 },
    '/api/entities/**': { proxy: `${apiBase}/api/entities/**`, swr: 300 },
    '/api/itineraries': { proxy: `${apiBase}/api/itineraries`, swr: 300 },
    '/api/**': { proxy: `${apiBase}/api/**` },
    '/auth/**': { proxy: `${apiBase}/auth/**` },
    '/chat/**': { proxy: `${apiBase}/chat/**` },
    '/seo/**': { proxy: `${apiBase}/seo/**` },
    '/feedback/**': { proxy: `${apiBase}/feedback/**` },
    '/weather/**': { proxy: `${apiBase}/weather/**` },
    '/admin-api/**': { proxy: `${apiBase}/admin/**` },
    '/health': { proxy: `${apiBase}/health` },
    '/reload': { proxy: `${apiBase}/reload` },
    '/recommend': { proxy: `${apiBase}/recommend` },
    '/freshness/**': { proxy: `${apiBase}/freshness/**` },
    '/events': { proxy: `${apiBase}/events` },
    '/sitemap.xml': { proxy: `${apiBase}/sitemap.xml` },
    '/robots.txt': { proxy: `${apiBase}/robots.txt` },
  },

  experimental: {
    viewTransition: true,
  },

  vite: {
    // maplibre-gl ~900KB: EXCLUDE khỏi pre-bundle để giữ nó là lazy dynamic-import chunk
    // (composables/useNDAMap.ts dùng `await import('maplibre-gl')`). 'include' trước đây
    // ép eager-bundle → phình bộ nhớ build (ARCH-006/D01). Map chỉ tải khi cần.
    optimizeDeps: {
      exclude: ['maplibre-gl'],
    },
  },

  devServer: {
    port: 3000,
  },

  nitro: {
    compressPublicAssets: true,
    // Dev-only: route the SWR/route cache to memory. The default fs cache driver
    // hits EISDIR on Windows ('.nuxt/cache/nuxt/payload' written as both dir + file),
    // 500-ing every SWR route in `nuxt dev`. Memory driver sidesteps it; prod cache
    // (storage, used by the built .output) is untouched.
    devStorage: {
      cache: { driver: 'memory' },
    },
    prerender: {
      routes: ['/', '/du-lich', '/san-pham', '/ocop', '/le-hoi', '/luu-tru',
               '/lich-trinh', '/su-kien', '/theo-mua', '/ban-do', '/danh-ba',
               '/lien-he', '/cong-dong'],
      crawlLinks: false,
    },
    routeRules: {
      '/_nuxt/**': { headers: { 'cache-control': 'public, max-age=31536000, immutable' } },
      '/**': {
        headers: {
          'X-Content-Type-Options': 'nosniff',
          'X-Frame-Options': 'SAMEORIGIN',
          'Referrer-Policy': 'strict-origin-when-cross-origin',
          'Permissions-Policy': 'geolocation=(), microphone=(), camera=(), payment=()',
          'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        },
      },
    },
  },
})
