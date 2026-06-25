<template>
  <div>
    <a href="#main-content" class="skip-link">Bỏ qua điều hướng</a>
    <header class="topbar" :class="{ scrolled: topbarScrolled }">
      <div class="topbar-inner">
        <NuxtLink class="brand" to="/">
          <span class="logo">{{ ss('branding.site_name', 'vinhlong360').replace('360', '') }}<span class="dot">360</span></span>
          <span class="tld">{{ ss('branding.logo_suffix', '.vn') }}</span>
        </NuxtLink>
        <button type="button" class="nav-toggle" :aria-expanded="mobileNav" aria-haspopup="true" aria-controls="main-nav" aria-label="Menu" @click="mobileNav = !mobileNav">
          <span></span><span></span><span></span>
        </button>
        <div class="nav-backdrop" :class="{ show: mobileNav }" aria-hidden="true" @click="mobileNav = false"></div>
        <nav id="main-nav" class="main-nav" :class="{ open: mobileNav }" @keydown="onNavKeydown">
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
          <ClientOnly>
            <button type="button" class="theme-toggle" :aria-label="colorMode.value === 'dark' ? 'Chuyển sang giao diện sáng' : 'Chuyển sang giao diện tối'" :title="colorMode.value === 'dark' ? 'Giao diện sáng' : 'Giao diện tối'" @click="toggleColorMode">
              <span v-if="colorMode.value === 'dark'">☀️</span>
              <span v-else>🌙</span>
            </button>
            <template #fallback>
              <button type="button" class="theme-toggle" aria-label="Đổi giao diện sáng/tối">🌙</button>
            </template>
          </ClientOnly>
          <template v-if="isLoggedIn">
            <NotificationBell />
            <UserMenu />
          </template>
          <button type="button" v-else class="auth-btn" @click="showAuth = true">Đăng nhập</button>
        </div>
      </div>
    </header>

    <Transition name="banner-slide">
      <div v-if="showBeta" class="beta-banner">
        <div class="beta-inner">
          <span class="beta-icon">{{ ss('announcements.icon', '🚧') }}</span>
          <p><strong>{{ ss('announcements.text', 'Trang đang trong giai đoạn xây dựng.') }}</strong> {{ ss('announcements.subtext', 'Một số tính năng có thể chưa hoàn thiện hoặc thay đổi. Cảm ơn bạn đã ghé thăm!') }}</p>
          <button type="button" class="beta-close" aria-label="Đóng thông báo" @click="dismissBeta">&times;</button>
        </div>
      </div>
    </Transition>

    <main id="main-content">
      <slot />
    </main>

    <AuthModal :visible="showAuth" @close="showAuth = false" />
    <ConfirmDialog />
    <ClientOnly>
      <ScrollToTop />
    </ClientOnly>
    <ChatWidget />
    <ClientOnly>
      <OnboardingSheet />
      <JourneyBar />
      <ReportModal />
      <ToastContainer />
    </ClientOnly>

    <footer class="site-footer">
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
              <h4>{{ col.title }}</h4>
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
            <nav class="footer-legal">
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
const { isLoggedIn } = useAuth()
const colorMode = useColorMode()
const { get: ss } = useSiteSettings()
function toggleColorMode() {
  colorMode.preference = colorMode.value === 'dark' ? 'light' : 'dark'
}
const { open: showAuth } = useAuthModal()
const mobileNav = ref(false)
const bannerEnabled = computed(() => ss('announcements.enabled', true))
const showBeta = ref(false)
onMounted(() => {
  if (bannerEnabled.value && localStorage.getItem('vl360_beta_dismissed') !== '1') showBeta.value = true
})
function dismissBeta() { showBeta.value = false; localStorage.setItem('vl360_beta_dismissed', '1') }

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
    { to: '/lich-trinh', label: 'Đã lưu ❤️' },
  ] },
  { label: 'Cộng đồng', to: '/cong-dong' },
]
const navGroups = computed(() => ss('navigation.nav_groups', DEFAULT_NAV_GROUPS) as typeof DEFAULT_NAV_GROUPS)

const DEFAULT_FOOTER_COLUMNS = [
  { title: 'Khám phá', links: [
    { to: '/du-lich', label: 'Du lịch & trải nghiệm' },
    { to: '/san-pham', label: 'Sản phẩm địa phương' },
    { to: '/ocop', label: 'Sản phẩm OCOP' },
    { to: '/theo-mua', label: 'Đặc sản theo mùa' },
    { to: '/luu-tru', label: 'Lưu trú' },
    { to: '/le-hoi', label: 'Lễ hội truyền thống' },
    { to: '/su-kien', label: 'Sự kiện' },
  ] },
  { title: 'Công cụ', links: [
    { to: '/ban-do', label: 'Bản đồ' },
    { to: '/lich-trinh', label: 'Lịch trình gợi ý' },
    { to: '/tao-lich-trinh', label: 'Tạo lịch trình' },
    { to: '/danh-ba', label: 'Danh bạ hành chính' },
    { to: '/cong-dong', label: 'Cộng đồng' },
    { to: '/huong-dan-thanh-vien', label: 'Hướng dẫn thành viên' },
  ] },
  { title: 'Khu vực', links: [
    { to: '/khu-vuc/vinh-long', label: '🍊 Vĩnh Long' },
    { to: '/khu-vuc/ben-tre', label: '🥥 Bến Tre' },
    { to: '/khu-vuc/tra-vinh', label: '🛕 Trà Vinh' },
  ] },
  { title: 'Dành cho cơ sở', links: [
    { to: '/lien-he?ref=claim', label: '🏷️ Đăng ký quản lý trang' },
    { to: '/lien-he', label: '🤝 Hợp tác quảng bá' },
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
function closeAll() { openGroup.value = null; mobileNav.value = false }
function isActive(g: { to?: string; children?: { to: string }[] }) {
  if (g.to) return route.path === g.to
  return !!g.children?.some(c => route.path === c.to || route.path.startsWith(c.to + '/'))
}

watch(() => route.path, () => { closeAll() })

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
  if (e.key === 'Escape') { mobileNav.value = false; return }
  if (e.key !== 'Tab') return
  const nav = document.getElementById('main-nav')
  if (!nav) return
  const focusable = Array.from(
    nav.querySelectorAll<HTMLElement>('a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])')
  ).filter(el => el.offsetParent !== null)
  if (!focusable.length) return
  const first = focusable[0], last = focusable[focusable.length - 1]
  if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus() }
  else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus() }
}

useScrollFade()

const topbarScrolled = ref(false)
function onPageScroll() { topbarScrolled.value = window.scrollY > 8 }

onMounted(() => {
  const onDoc = (e: MouseEvent) => { if (!(e.target as HTMLElement)?.closest('.main-nav')) openGroup.value = null }
  const onEsc = (e: KeyboardEvent) => { if (e.key === 'Escape') { openGroup.value = null; mobileNav.value = false } }
  document.addEventListener('click', onDoc)
  document.addEventListener('keydown', onEsc)
  window.addEventListener('scroll', onPageScroll, { passive: true })
  onPageScroll()
  onUnmounted(() => {
    document.removeEventListener('click', onDoc)
    document.removeEventListener('keydown', onEsc)
    window.removeEventListener('scroll', onPageScroll)
    document.body.style.overflow = ''
  })
})

</script>
