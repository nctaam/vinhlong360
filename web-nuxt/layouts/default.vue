<template>
  <div>
    <a href="#main-content" class="skip-link">Bỏ qua điều hướng</a>
    <header class="topbar" role="banner" :class="{ scrolled: topbarScrolled }">
      <div class="topbar-inner">
        <NuxtLink class="brand" to="/">
          <span class="logo">{{ ss('branding.site_name', 'vinhlong360').replace('360', '') }}<span class="dot">360</span></span>
          <span class="tld">{{ ss('branding.logo_suffix', '.vn') }}</span>
        </NuxtLink>
        <button type="button" class="nav-toggle" :aria-expanded="mobileNav" aria-haspopup="true" aria-controls="main-nav" aria-label="Menu" @click="mobileNav ? closeNav() : (mobileNav = true)">
          <span></span><span></span><span></span>
        </button>
        <div class="nav-backdrop" :class="{ show: mobileNav, closing: navClosing }" aria-hidden="true" @click="closeNav"></div>
        <nav id="main-nav" class="main-nav" aria-label="Menu chính" :class="{ open: mobileNav, closing: navClosing }" @keydown="onNavKeydown">
          <template v-for="(g, i) in navGroups" :key="g.label">
            <NuxtLink v-if="g.to" :to="g.to" :class="{ active: isActive(g) }" :aria-current="isActive(g) ? 'page' : undefined" @click="closeAll">{{ g.label }}</NuxtLink>
            <div v-else class="nav-group" :class="{ open: openGroup === i }">
              <button type="button" class="nav-group-btn" :class="{ active: isActive(g) }" :aria-expanded="openGroup === i" @click="toggleGroup(i)">
                {{ g.label }}<span class="caret" aria-hidden="true">▾</span>
              </button>
              <div class="nav-panel" :class="{ open: openGroup === i }">
                <NuxtLink v-for="c in g.children" :key="c.to" :to="c.to" :class="{ active: route.path === c.to }" :aria-current="route.path === c.to ? 'page' : undefined" @click="closeAll">{{ c.label }}</NuxtLink>
              </div>
            </div>
          </template>
        </nav>
        <SearchAutocomplete class="topbar-search" />
        <div class="auth-area">
          <template v-if="clientReady">
            <button type="button" class="theme-toggle" :aria-label="colorMode.value === 'dark' ? 'Chuyển sang giao diện sáng' : 'Chuyển sang giao diện tối'" :title="colorMode.value === 'dark' ? 'Giao diện sáng' : 'Giao diện tối'" @click="toggleColorMode">
              <IconLine v-if="colorMode.value === 'dark'" name="sun" />
              <IconLine v-else name="moon" />
            </button>
            <template v-if="isLoggedIn">
              <LazyNotificationBell />
              <LazyUserMenu />
            </template>
            <span v-else-if="hasAuthSession" class="auth-user auth-user-snapshot" aria-label="Tài khoản">
              <span class="avatar avatar-sm">{{ headerInitial }}</span>
              <span class="auth-user-name">{{ headerDisplayName }}</span>
            </span>
            <button type="button" v-else class="auth-btn" @click="showAuth = true">Đăng nhập</button>
          </template>
          <template v-else>
            <button type="button" class="theme-toggle" aria-label="Đổi giao diện sáng/tối"><IconLine name="moon" /></button>
            <span class="auth-user auth-user-snapshot auth-user-loading" aria-hidden="true">
              <span class="avatar avatar-sm">?</span>
              <span class="auth-user-name">Tài khoản</span>
            </span>
          </template>
        </div>
      </div>
    </header>

    <noscript class="noscript-banner">Trang web này cần JavaScript để hoạt động. Vui lòng bật JavaScript trong trình duyệt.</noscript>

    <main id="main-content" role="main" tabindex="-1">
      <slot />
    </main>

    <template v-if="clientReady">
      <LazyAuthModal :visible="showAuth" @close="showAuth = false" />
      <LazyConfirmDialog />
      <LazyScrollToTop />
      <LazyChatWidget />
      <LazyOnboardingSheet />
      <LazyJourneyBar />
      <LazyReportModal />
      <LazyToastContainer />
    </template>

    <footer class="site-footer" role="contentinfo">
      <div class="footer-inner">
        <div class="footer-top">
          <div class="footer-brand">
            <NuxtLink to="/" class="footer-logo">
              <span class="logo">{{ ss('branding.site_name', 'vinhlong360').replace('360', '') }}<span class="dot">360</span></span><span class="tld">{{ ss('branding.logo_suffix', '.vn') }}</span>
            </NuxtLink>
            <p>{{ ss('footer.tagline', 'Khám phá Vĩnh Long, Bến Tre, Trà Vinh\ntheo cách của người bản địa.') }}</p>
            <nav v-if="socialLinks.length" class="footer-social" aria-label="Mạng xã hội">
              <a v-for="s in socialLinks" :key="s.url" :href="s.url" target="_blank" rel="noopener noreferrer" :aria-label="s.label" :title="s.label">
                <span class="fs-icon" aria-hidden="true">{{ s.icon }}</span>
                <span class="fs-label">{{ s.label }}</span>
              </a>
            </nav>
          </div>
          <div class="footer-nav">
            <div v-for="col in footerColumns" :key="col.title" class="footer-col">
              <h2>{{ col.title }}</h2>
              <nav :aria-label="col.title">
                <NuxtLink v-for="link in col.links" :key="link.to" :to="link.to">{{ link.label }}</NuxtLink>
              </nav>
            </div>
          </div>
        </div>
        <div class="footer-bottom">
          <p class="disclaimer">{{ ss('footer.disclaimer', 'Thông tin mùa vụ, giá & địa điểm mang tính tham khảo — vui lòng xác nhận với địa phương trước khi sử dụng.') }}</p>
          <div class="footer-bottom-row">
            <p>{{ ss('footer.copyright', '© 2024–2026 vinhlong360') }}</p>
            <nav class="footer-legal" aria-label="Pháp lý">
              <NuxtLink v-for="link in footerLegalLinks" :key="link.to" :to="link.to">{{ link.label }}</NuxtLink>
            </nav>
          </div>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
const route = useRoute()
const { isLoggedIn, user } = useAuth()
const colorMode = useColorMode()
const { get: ss } = useSiteSettings()
const hasAuthSession = computed(() => isLoggedIn.value)
const headerDisplayName = computed(() => user.value?.display_name || user.value?.phone || 'Tài khoản')
const headerInitial = computed(() => headerDisplayName.value ? headerDisplayName.value.charAt(0).toUpperCase() : '?')
function toggleColorMode() {
  colorMode.preference = colorMode.value === 'dark' ? 'light' : 'dark'
}
const { open: showAuth } = useAuthModal()
useSeasonTheme()
const mobileNav = ref(false)
const clientReady = ref(false)
// A3a declutter: beta-banner đã bỏ — OnboardingSheet là kênh truyền thông beta duy nhất
// (hết 2 interrupt chồng nhau lần đầu vào). CMS key announcements.* không còn bề mặt render.
onMounted(() => {
  clientReady.value = true
  if (route.query.login === 'admin') showAuth.value = true
})

const DEFAULT_NAV_GROUPS: Array<{ label: string; to?: string; children?: { to: string; label: string }[] }> = [
  { label: 'Khám phá', children: [
    { to: '/dia-diem', label: 'Tất cả địa điểm' },
    { to: '/du-lich', label: 'Du lịch & trải nghiệm' },
    { to: '/luu-tru', label: 'Lưu trú' },
    { to: '/theo-mua', label: 'Đặc sản theo mùa' },
    { to: '/ban-do', label: 'Bản đồ' },
    { to: '/danh-ba', label: 'Danh bạ hành chính' },
    { to: '/tuyen-duong', label: 'Tuyến đường gợi ý' },
    { to: '/le-hoi', label: 'Lễ hội truyền thống' },
    { to: '/su-kien', label: 'Sự kiện' },
  ] },
  { label: 'Đặc sản', children: [
    { to: '/san-pham', label: 'Sản phẩm địa phương' },
    { to: '/ocop', label: 'Sản phẩm OCOP' },
  ] },
  { label: 'Lịch trình', children: [
    { to: '/lich-trinh', label: 'Lịch trình gợi ý' },
    { to: '/tao-lich-trinh', label: 'Tạo lịch trình' },
    { to: '/da-luu', label: 'Đã lưu' },
  ] },
  { label: 'Cộng đồng', children: [
    { to: '/cong-dong', label: 'Bảng tin cộng đồng' },
    { to: '/bang-xep-hang', label: 'Bảng xếp hạng' },
    { to: '/huong-dan', label: 'Hướng dẫn sử dụng' },
  ] },
]
const navGroups = computed(() => ss('navigation.nav_groups', DEFAULT_NAV_GROUPS) as typeof DEFAULT_NAV_GROUPS)

const DEFAULT_FOOTER_COLUMNS = [
  // declutter-2 A3b: 7 link → 4 curated (ocop tới được từ san-pham + nav; luu-tru/su-kien
  // có trong nav-group "Khám phá" topbar). CMS key footer.columns override được — DB prod
  // cập nhật qua AdminCP lúc deploy (ghi chú vận hành trong plan).
  { title: 'Gợi ý nhanh', links: [
    { to: '/du-lich', label: 'Du lịch & trải nghiệm' },
    { to: '/san-pham', label: 'Sản phẩm địa phương' },
    { to: '/theo-mua', label: 'Đặc sản theo mùa' },
    { to: '/le-hoi', label: 'Lễ hội truyền thống' },
  ] },
  { title: 'Công cụ', links: [
    { to: '/ban-do', label: 'Bản đồ' },
    { to: '/lich-trinh', label: 'Lịch trình gợi ý' },
    { to: '/tao-lich-trinh', label: 'Tạo lịch trình' },
    { to: '/danh-ba', label: 'Danh bạ hành chính' },
    { to: '/cong-dong', label: 'Cộng đồng' },
    { to: '/huong-dan', label: 'Hướng dẫn sử dụng' },
  ] },
  { title: 'Khu vực', links: [
    { to: '/khu-vuc/vinh-long', label: 'Vĩnh Long' },
    { to: '/khu-vuc/ben-tre', label: 'Bến Tre' },
    { to: '/khu-vuc/tra-vinh', label: 'Trà Vinh' },
  ] },
  { title: 'Dành cho cơ sở', links: [
    { to: '/lien-he?ref=claim', label: 'Đăng ký quản lý trang' },
    { to: '/lien-he', label: 'Hợp tác quảng bá' },
  ] },
]
const footerColumns = computed(() => ss('footer.columns', DEFAULT_FOOTER_COLUMNS) as typeof DEFAULT_FOOTER_COLUMNS)

const DEFAULT_FOOTER_LEGAL = [
  { to: '/gioi-thieu', label: 'Về chúng tôi' },
  { to: '/chinh-sach-bao-mat', label: 'Bảo mật' },
  { to: '/dieu-khoan-su-dung', label: 'Điều khoản' },
  { to: '/lien-he', label: 'Liên hệ' },
  { to: '/admin', label: 'Admin' },
]
const footerLegalLinks = computed(() => ss('footer.legal_links', DEFAULT_FOOTER_LEGAL) as typeof DEFAULT_FOOTER_LEGAL)

// Social links — empty by default (no row shown until an admin adds links).
const socialLinks = computed(() => ss('social.links', [] as { icon: string; label: string; url: string }[]))

const themeOverrideCss = computed(() => {
  const vars: string[] = []
  const primary = ss('theme.primary_color', '') as string
  const accent = ss('theme.accent_color', '') as string
  const secondary = ss('theme.secondary_color', '') as string
  const radius = ss('theme.radius', '') as string
  const fontScale = ss('theme.font_scale', '') as string
  // P0-5: chỉ nhận mã hex hợp lệ → chặn CSS-injection qua site_settings (vd "red;}body{...")
  const isHex = (c: string) => /^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/.test(c)
  if (isHex(primary)) vars.push(`--primary: ${primary}`)
  if (isHex(accent)) vars.push(`--accent: ${accent}`)
  if (isHex(secondary)) vars.push(`--secondary: ${secondary}`)
  // Validate radius is a plain CSS length (blocks any CSS injection via the setting).
  if (/^\d{1,3}(\.\d+)?(px|rem|em|%)$/.test(radius)) vars.push(`--radius: ${radius}`)
  let css = vars.length ? `:root { ${vars.join('; ')} }` : ''
  // Font scale: a bounded multiplier (0.8–1.3) applied to the root font size.
  const fs = parseFloat(fontScale)
  if (!Number.isNaN(fs) && fs >= 0.8 && fs <= 1.3) css += ` html { font-size: calc(100% * ${fs}); }`
  return css
})
useHead({ style: [{ innerHTML: themeOverrideCss }] })

const openGroup = ref<number | null>(null)
function toggleGroup(i: number) { openGroup.value = openGroup.value === i ? null : i }
const navClosing = ref(false)

function closeNav() {
  if (!mobileNav.value || navClosing.value) return
  navClosing.value = true
  setTimeout(() => {
    mobileNav.value = false
    navClosing.value = false
  }, 250)
}

function closeAll() { openGroup.value = null; closeNav() }
function isActive(g: { to?: string; children?: { to: string }[] }) {
  if (g.to) return route.path === g.to
  return !!g.children?.some(c => route.path === c.to || route.path.startsWith(c.to + '/'))
}

watch(() => route.path, () => {
  closeAll()
  // T4 a11y: move focus to main content on route change so screen readers
  // announce the new page. nextTick waits for DOM update after navigation.
  nextTick(() => {
    const main = document.getElementById('main-content')
    if (main) main.focus({ preventScroll: true })
  })
})

watch(mobileNav, (open) => {
  if (typeof document === 'undefined') return
  document.body.style.overflow = open ? 'hidden' : ''
  if (open) {
    nextTick(() => {
      const nav = document.getElementById('main-nav')
      const first = nav?.querySelector<HTMLElement>('a, button')
      first?.focus()
    })
  }
})

function onNavKeydown(e: KeyboardEvent) {
  if (!mobileNav.value) return
  if (e.key === 'Escape') { closeNav(); return }
  if (e.key !== 'Tab') return
  const nav = document.getElementById('main-nav')
  if (!nav) return
  const focusable = Array.from(
    nav.querySelectorAll<HTMLElement>('a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])')
  ).filter(el => el.offsetParent !== null)
  if (!focusable.length) return
  const first = focusable[0], last = focusable[focusable.length - 1]
  if (!first || !last) return
  if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus() }
  else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus() }
}

useScrollFade()

const topbarScrolled = ref(false)
let scrollRaf = 0
function onPageScroll() {
  if (!scrollRaf) scrollRaf = requestAnimationFrame(() => { scrollRaf = 0; topbarScrolled.value = window.scrollY > 8 })
}

const onDoc = (e: MouseEvent) => { if (!(e.target as HTMLElement)?.closest('.main-nav')) openGroup.value = null }
const onEsc = (e: KeyboardEvent) => { if (e.key === 'Escape') { openGroup.value = null; closeNav() } }
onMounted(() => {
  document.addEventListener('click', onDoc)
  document.addEventListener('keydown', onEsc)
  window.addEventListener('scroll', onPageScroll, { passive: true })
  topbarScrolled.value = window.scrollY > 8
})
onUnmounted(() => {
  document.removeEventListener('click', onDoc)
  document.removeEventListener('keydown', onEsc)
  window.removeEventListener('scroll', onPageScroll)
  cancelAnimationFrame(scrollRaf)
  document.body.style.overflow = ''
})

</script>

<style scoped>
/* ── Chrome editorial pass (Wave 6): footer as the publication's colophon ── */
/* Phù-sa crown — the river→amber→clay signature hairline across the footer top */
.site-footer { position: relative; }
.site-footer::before {
  content: ""; position: absolute; top: 0; left: 0; right: 0; height: 2px; z-index: 1;
  background: linear-gradient(90deg, var(--river-600) 0%, var(--amber-600) 50%, var(--clay-600) 100%);
  opacity: .55;
}
.dark .site-footer::before {
  background: linear-gradient(90deg, #74ABB5 0%, var(--amber-500) 50%, var(--clay-400) 100%);
  opacity: .65;
}
/* Footer column headings → serif section labels with a small phù-sa tick */
.footer-col h2 {
  font-family: var(--font-editorial);
  font-weight: 600;
  font-size: var(--text-base);
  position: relative;
  padding-left: var(--space-3);
}
.footer-col h2::before {
  content: ""; position: absolute; left: 0; top: 50%; transform: translateY(-50%);
  width: 3px; height: 1em; border-radius: var(--radius-full);
  background: linear-gradient(180deg, var(--river-600) 0%, var(--amber-600) 52%, var(--clay-600) 100%);
}
.dark .footer-col h2::before {
  background: linear-gradient(180deg, #74ABB5 0%, var(--amber-500) 52%, var(--clay-400) 100%);
}
/* Tagline → editorial serif italic, reads like a masthead motto */
.footer-brand p {
  font-family: var(--font-editorial);
  font-style: italic;
  font-size: var(--text-base);
  line-height: var(--leading-relaxed);
}
</style>
