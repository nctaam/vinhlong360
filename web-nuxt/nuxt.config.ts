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
    '~/assets/css/detail.css',
    '~/assets/css/catalog.css',
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
        { name: 'twitter:card', content: 'summary_large_image' },
        { name: 'twitter:site', content: '@vinhlong360' },
      ],
      link: [
        { rel: 'dns-prefetch', href: 'https://maptiles.openmap.vn' },
        { rel: 'sitemap', type: 'application/xml', href: '/sitemap.xml' },
        { rel: 'icon', type: 'image/svg+xml', href: '/favicon.svg' },
        { rel: 'manifest', href: '/manifest.json' },
        { rel: 'apple-touch-icon', sizes: '180x180', href: '/apple-touch-icon.png' },
      ],
      script: [
        { innerHTML: "if('serviceWorker' in navigator){navigator.serviceWorker.register('/sw.js')}", type: 'text/javascript' },
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
    '/admin/**': { ssr: false },
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

  vite: {
    optimizeDeps: {
      include: ['maplibre-gl'],
    },
  },

  devServer: {
    port: 3000,
  },

  nitro: {
    compressPublicAssets: true,
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
