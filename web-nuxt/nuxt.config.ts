import { fileURLToPath } from 'node:url'

import { createLaunchRawArtifactPlugin } from './build/launchRawArtifactPlugin'

const apiBase = process.env.API_BASE || 'http://localhost:8360'
const siteNoindex = process.env.NUXT_PUBLIC_SITE_NOINDEX !== 'false'
const itineraryScheduleV2 = process.env.NUXT_PUBLIC_ITINERARY_SCHEDULE_V2 === '1'
const publicTelemetryEnabled = process.env.NUXT_PUBLIC_TELEMETRY_ENABLED === '1'
const publicTelemetryEndpoint = process.env.NUXT_PUBLIC_TELEMETRY_ENDPOINT || '/feedback/public-telemetry'

export default defineNuxtConfig({
  compatibilityDate: '2025-05-15',

  alias: {
    '#launch-config': fileURLToPath(new URL('../config', import.meta.url)),
    '#privacy-policy': fileURLToPath(new URL('../config/privacy-policy.json', import.meta.url)),
    // Nitro giữ nguyên specifier '.mjs' tương đối và resolve từ vị trí bundle,
    // nên import tương đối từ server/ đi lạc thư mục. Alias tuyệt đối tránh việc đó.
    '#launch-validators': fileURLToPath(new URL('./utils/launchArtifactValidators.mjs', import.meta.url)),
  },

  ssr: true,

  modules: ['@nuxt/fonts', '@nuxt/image', '@nuxtjs/color-mode'],

  // Public theme is explicit: Nocturne by default, Parchment only by user choice.
  colorMode: { classSuffix: '', preference: 'dark', fallback: 'dark', storageKey: 'vl360-color-mode' },

  // Self-host font (bỏ Google CDN) — giảm latency bên thứ 3 + CLS (font-metric optimization).
  fonts: {
    defaults: { weights: [400, 500, 600, 700], subsets: ['vietnamese', 'latin', 'latin-ext'] },
    // Fraunces khai TƯỜNG MINH. Trước đây nó chỉ lọt vào đây do @nuxt/fonts tự
    // quét CSS và giải quyết mọi font-family lạ (qua --font-editorial) — một phụ
    // thuộc ngầm, và nó tồn tại SONG SONG với bản tự-host ở assets/css/fonts.css.
    // Kết quả đo trên trang thật: 66 khối @font-face cho riêng Fraunces (48 từ
    // /_fonts/, 12 tự-host, 6 khối fallback-metric), khối THẮNG cascade là
    // /_fonts/, trong khi hai file DUY NHẤT được preload lại là hai file tự-host
    // thua cascade — 45,2 kB tải ở ưu tiên cao nhất rồi vứt.
    families: [
      { name: 'Be Vietnam Pro', provider: 'google' },
      { name: 'Fraunces', provider: 'google' },
    ],
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
    // fonts.css (tự-host Fraunces) ĐÃ GỠ khỏi đây: @nuxt/fonts nay khai Fraunces
    // tường minh và cũng tự-host (phục vụ từ /_fonts/, không gọi CDN Google lúc
    // chạy), nên giữ hai nguồn chỉ tạo trùng lặp và một preload sai đích.
    '~/assets/css/variables.css',
    '~/assets/css/base.css',
    '~/assets/css/shell.css',
    '~/assets/css/components.css',
    '~/assets/css/dossier.css',
    '~/assets/css/cards.css',
    // detail.css KHÔNG global: chỉ 3 trang chi tiết (dia-diem/xa-phuong/lich-trinh) dùng
    // → import qua <style src> trong 3 page đó (bỏ ~35KB khỏi entry.css mọi trang).
    // detail-shared.css = phần dùng-chung (breadcrumb/highlights/lightbox/map) GIỮ global.
    '~/assets/css/detail-shared.css',
    '~/assets/css/catalog.css',
    '~/assets/css/tri-region-color.css',
    '~/assets/css/editorial.css',   // drop-cap / pull-quote / editorial-body — small (6.4KB), site-wide editorial typography
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
        { name: 'description', content: 'Cổng du lịch và sản phẩm địa phương tỉnh Vĩnh Long (hợp nhất từ Vĩnh Long, Bến Tre, Trà Vinh cũ): miệt vườn, đặc sản theo mùa, OCOP, làng nghề, lịch trình gợi ý.' },
        { property: 'og:title', content: 'vinhlong360 — Du lịch & Sản phẩm địa phương' },
        { property: 'og:description', content: 'Khám phá tỉnh Vĩnh Long sau sáp nhập (gồm Bến Tre và Trà Vinh cũ): du lịch miệt vườn, đặc sản OCOP, làng nghề, lưu trú và lịch trình gợi ý.' },
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
        // Preload the editorial-serif subsets the masthead (LCP element on every page) actually
        // uses — Vietnamese headings need latin (base glyphs) + vietnamese (accents). Without this
        // the browser only discovers the @font-face after CSS parse, so the serif h1 renders in the
        // Palatino fallback then swaps (FOUT flash + metric shift). Only these 2 of the 6 subsets
        // (skip latin-ext + italic — not above-the-fold on load). `crossorigin` required for the
        // preload to match the woff2 fetch. Files are stable /fonts/*.woff2 (self-host, not hashed).
        // Hai preload /fonts/fraunces-*.woff2 ĐÃ GỠ: chúng trỏ vào bản tự-host THUA
        // cascade, nên trình duyệt tải 45,2 kB ở ưu tiên cao nhất rồi vẽ chữ bằng
        // bản /_fonts/. Chống nháy chữ nay do chính @nuxt/fonts lo, bằng họ
        // fallback có khớp metric ("Fraunces Fallback: Times New Roman"/Georgia/
        // Noto Serif — đo được trên document.fonts), đúng cơ chế chống CLS.
        { rel: 'canonical', href: 'https://vinhlong360.vn' },
        { rel: 'preconnect', href: 'https://vinhlong360.vn' },
        { rel: 'dns-prefetch', href: '//vinhlong360.vn' },
        { rel: 'preconnect', href: 'https://images.weserv.nl' },
        { rel: 'dns-prefetch', href: 'https://maptiles.openmap.vn' },
        { rel: 'icon', type: 'image/svg+xml', href: '/favicon.svg' },
        { rel: 'manifest', href: '/manifest.json' },
        { rel: 'apple-touch-icon', sizes: '180x180', href: '/apple-touch-icon.png' },
      ],
      script: [
        { innerHTML: "try{var d=document.documentElement,p=JSON.parse(localStorage.getItem('vl360-accessibility-profile')||'null')||{},s=[1,1.25,1.5,2].includes(p.textScale)?p.textScale:1,t=p.theme==='parchment'?'parchment':'nocturne',m=t==='parchment'?'light':'dark',n=p.density==='compact'?'compact':'comfortable';localStorage.setItem('vl360-color-mode',m);d.classList.remove('light','dark');d.classList.add(m);d.dataset.theme=t;d.dataset.density=n;d.style.setProperty('--a11y-text-scale',String(s));d.style.setProperty('--a11y-text-scale-percent',(s*100)+'%')}catch(_){ }", tagPosition: 'head' },
        // Add `js` to <html> BEFORE first paint so the JS-gated .reveal rule
        // (html.js .reveal { opacity:0 }) only ever hides content when JS is
        // present — no flash-of-hidden, and full visibility when JS is off/slow.
        { innerHTML: "document.documentElement.classList.add('js')", tagPosition: 'head' },
        { innerHTML: "if('serviceWorker' in navigator&&location.protocol==='https:'&&!['localhost','127.0.0.1','::1'].includes(location.hostname)){window.addEventListener('load',function(){navigator.serviceWorker.register('/sw.js')})}", type: 'text/javascript' },
        {
          type: 'application/ld+json',
          innerHTML: JSON.stringify({
            '@context': 'https://schema.org',
            '@type': 'WebSite',
            'name': 'VinhLong360',
            'alternateName': 'Khám phá tỉnh Vĩnh Long',
            'url': 'https://vinhlong360.vn',
            'description': 'Nền tảng khám phá du lịch, OCOP và cộng đồng cho tỉnh Vĩnh Long — tỉnh hợp nhất từ Vĩnh Long, Bến Tre và Trà Vinh cũ từ 7-2025',
            'potentialAction': {
              '@type': 'SearchAction',
              'target': {
                '@type': 'EntryPoint',
                'urlTemplate': 'https://vinhlong360.vn/tim-kiem?q={search_term_string}',
              },
              'query-input': 'required name=search_term_string',
            },
            'publisher': {
              '@type': 'Organization',
              'name': 'VinhLong360',
              'url': 'https://vinhlong360.vn',
            },
          }),
        },
      ],
    },
  },

  runtimeConfig: {
    // Backend origins are server-only. Browser requests stay relative and go
    // through the exclusive Nginx ingress, so this value is never serialized
    // into the public runtime payload.
    apiBase,
    public: {
      // Nhánh public được serialize xuống trình duyệt trên mọi trang, nên không
      // đặt khoá thật làm giá trị mặc định ở đây. Thiếu NDA_MAP_KEY thì bản đồ
      // tự chạy nền OpenStreetMap (xem composables/useNDAMap.ts).
      ndaMapKey: process.env.NDA_MAP_KEY || '',
      // Legacy launch switch remains closed by default. HTML robots metadata and
      // headers are now derived from the request-local launch safety decision.
      siteNoindex,
      itineraryScheduleV2,
      publicTelemetryEnabled,
      publicTelemetryEndpoint,
      // Support hours for phone-assisted corrections. Empty means the intake
      // page simply does not offer the phone lane — no fake availability.
      caseAssistedHours: process.env.NUXT_PUBLIC_CASE_ASSISTED_HOURS || '',
    },
  },

  routeRules: {
    '/admin/**': { ssr: false },
    '/api/**': { proxy: `${apiBase}/api/**` },
    '/auth/**': { proxy: `${apiBase}/auth/**` },
    '/chat/**': { proxy: `${apiBase}/chat/**` },
    '/seo/**': { proxy: `${apiBase}/seo/**` },
    '/feedback/**': { proxy: `${apiBase}/feedback/**` },
    '/weather/**': { proxy: `${apiBase}/weather/**` },
    '/admin-api/**': { proxy: `${apiBase}/admin/**` },
    '/health': { proxy: `${apiBase}/health` },
    '/health/**': { proxy: `${apiBase}/health/**` },
    '/reload': { proxy: `${apiBase}/reload` },
    '/recommend': { proxy: `${apiBase}/recommend` },
    '/freshness/**': { proxy: `${apiBase}/freshness/**` },
    '/events': { proxy: `${apiBase}/events` },
  },

  experimental: {
    viewTransition: true,
    defaults: {
      nuxtLink: {
        // Mặc định của Nuxt là prefetch mọi link vừa lọt viewport, nên trang chủ
        // kéo sẵn JS/CSS của hàng chục route khác. Với người dùng 3G/4G ở nông thôn
        // đó là băng thông trả cho thứ họ chưa bấm. Chuyển sang prefetch khi có
        // ý định thật (hover/focus) — vẫn kịp trước cú click, không tải mù.
        prefetch: true,
        prefetchOn: { visibility: false, interaction: true },
      },
    },
  },

  vite: {
    // maplibre-gl ~900KB: EXCLUDE khỏi pre-bundle để giữ nó là lazy dynamic-import chunk
    // (composables/useNDAMap.ts dùng `await import('maplibre-gl')`). 'include' trước đây
    // ép eager-bundle → phình bộ nhớ build (ARCH-006/D01). Map chỉ tải khi cần.
    optimizeDeps: {
      exclude: ['maplibre-gl'],
    },
    // Diagnostic-only: build with HYDRATION_DEBUG=1 to make the PROD bundle log the exact
    // node + server/client diff for hydration mismatches (off by default → no prod cost).
    define: {
      __VUE_PROD_HYDRATION_MISMATCH_DETAILS__: process.env.HYDRATION_DEBUG === '1' ? 'true' : 'false',
    },
  },

  devServer: {
    port: 3000,
  },

  nitro: {
    compressPublicAssets: true,
    rollupConfig: {
      output: { sourcemapExcludeSources: true },
      plugins: [createLaunchRawArtifactPlugin(fileURLToPath(new URL('..', import.meta.url)))],
    },
    routeRules: {
      '/_nuxt/**': { headers: { 'cache-control': 'public, max-age=31536000, immutable' } },
      // The worker URL is intentionally stable, so force revalidation whenever
      // MapLibre changes instead of allowing stale main/worker version pairs.
      '/maplibre-gl-csp-worker.js': { headers: { 'cache-control': 'no-cache, must-revalidate' } },
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
