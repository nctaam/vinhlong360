<template>
  <div>
    <a href="#main-content" class="skip-link">Bỏ qua điều hướng</a>
    <header class="topbar">
      <div class="topbar-inner">
        <NuxtLink class="brand" to="/">
          <span class="logo">vinhlong<span class="dot">360</span></span>
          <span class="tld">.vn</span>
        </NuxtLink>
        <button class="nav-toggle" :aria-expanded="mobileNav" aria-haspopup="true" aria-controls="main-nav" aria-label="Menu" @click="mobileNav = !mobileNav">
          <span></span><span></span><span></span>
        </button>
        <div class="nav-backdrop" :class="{ show: mobileNav }" aria-hidden="true" @click="mobileNav = false"></div>
        <nav id="main-nav" class="main-nav" :class="{ open: mobileNav }" @keydown="onNavKeydown">
          <template v-for="(g, i) in navGroups" :key="g.label">
            <NuxtLink v-if="g.to" :to="g.to" :class="{ active: isActive(g) }" @click="closeAll">{{ g.label }}</NuxtLink>
            <div v-else class="nav-group" :class="{ open: openGroup === i }">
              <button type="button" class="nav-group-btn" :class="{ active: isActive(g) }" :aria-expanded="openGroup === i" @click="toggleGroup(i)">
                {{ g.label }}<span class="caret" aria-hidden="true">▾</span>
              </button>
              <div class="nav-panel" :class="{ open: openGroup === i }">
                <NuxtLink v-for="c in g.children" :key="c.to" :to="c.to" :class="{ active: route.path === c.to }" @click="closeAll">{{ c.label }}</NuxtLink>
              </div>
            </div>
          </template>
        </nav>
        <SearchAutocomplete class="topbar-search" />
        <div class="auth-area">
          <ClientOnly>
            <button class="theme-toggle" :aria-label="colorMode.value === 'dark' ? 'Chuyển sang giao diện sáng' : 'Chuyển sang giao diện tối'" :title="colorMode.value === 'dark' ? 'Giao diện sáng' : 'Giao diện tối'" @click="toggleColorMode">
              <span v-if="colorMode.value === 'dark'">☀️</span>
              <span v-else>🌙</span>
            </button>
            <template #fallback>
              <button class="theme-toggle" aria-label="Đổi giao diện sáng/tối">🌙</button>
            </template>
          </ClientOnly>
          <template v-if="isLoggedIn">
            <NotificationBell />
            <UserMenu />
          </template>
          <button v-else class="auth-btn" @click="showAuth = true">Đăng nhập</button>
        </div>
      </div>
    </header>

    <div v-if="showBeta" class="beta-banner">
      <div class="beta-inner">
        <span class="beta-icon">🚧</span>
        <p><strong>Trang đang trong giai đoạn xây dựng.</strong> Một số tính năng có thể chưa hoàn thiện hoặc thay đổi. Cảm ơn bạn đã ghé thăm!</p>
        <button class="beta-close" aria-label="Đóng thông báo" @click="dismissBeta">&times;</button>
      </div>
    </div>

    <main id="main-content">
      <slot />
    </main>

    <AuthModal :visible="showAuth" @close="showAuth = false" />
    <ClientOnly>
      <ScrollToTop />
    </ClientOnly>
    <ChatWidget />
    <ClientOnly>
      <OnboardingSheet />
      <JourneyBar />
      <ToastContainer />
    </ClientOnly>

    <footer class="site-footer">
      <div class="footer-inner">
        <div class="footer-top">
          <div class="footer-brand">
            <NuxtLink to="/" class="footer-logo">
              <span class="logo">vinhlong<span class="dot">360</span></span><span class="tld">.vn</span>
            </NuxtLink>
            <p>Khám phá Vĩnh Long, Bến Tre, Trà Vinh<br>theo cách của người bản địa.</p>
          </div>
          <div class="footer-nav">
            <div class="footer-col">
              <h4>Khám phá</h4>
              <nav>
                <NuxtLink to="/du-lich">Du lịch & trải nghiệm</NuxtLink>
                <NuxtLink to="/san-pham">Sản phẩm địa phương</NuxtLink>
                <NuxtLink to="/ocop">Sản phẩm OCOP</NuxtLink>
                <NuxtLink to="/theo-mua">Đặc sản theo mùa</NuxtLink>
                <NuxtLink to="/luu-tru">Lưu trú</NuxtLink>
                <NuxtLink to="/le-hoi">Lễ hội truyền thống</NuxtLink>
                <NuxtLink to="/su-kien">Sự kiện</NuxtLink>
              </nav>
            </div>
            <div class="footer-col">
              <h4>Công cụ</h4>
              <nav>
                <NuxtLink to="/ban-do" no-prefetch>Bản đồ</NuxtLink>
                <NuxtLink to="/lich-trinh">Lịch trình gợi ý</NuxtLink>
                <NuxtLink to="/tao-lich-trinh" no-prefetch>Tạo lịch trình</NuxtLink>
                <NuxtLink to="/danh-ba">Danh bạ hành chính</NuxtLink>
                <NuxtLink to="/cong-dong">Cộng đồng</NuxtLink>
              </nav>
            </div>
            <div class="footer-col">
              <h4>3 vùng</h4>
              <nav>
                <NuxtLink to="/khu-vuc/vinh-long">🍊 Vĩnh Long</NuxtLink>
                <NuxtLink to="/khu-vuc/ben-tre">🥥 Bến Tre</NuxtLink>
                <NuxtLink to="/khu-vuc/tra-vinh">🛕 Trà Vinh</NuxtLink>
              </nav>
            </div>
            <div class="footer-col">
              <h4>Dành cho cơ sở</h4>
              <nav>
                <NuxtLink to="/lien-he?ref=claim">🏷️ Đăng ký quản lý trang</NuxtLink>
                <NuxtLink to="/lien-he">🤝 Hợp tác quảng bá</NuxtLink>
              </nav>
            </div>
          </div>
        </div>
        <div class="footer-bottom">
          <p class="disclaimer">Thông tin mùa vụ, giá &amp; địa điểm mang tính tham khảo — vui lòng xác nhận với địa phương trước khi sử dụng.</p>
          <div class="footer-bottom-row">
            <p>&copy; 2024–2026 vinhlong360</p>
            <nav class="footer-legal">
              <NuxtLink to="/chinh-sach-bao-mat">Bảo mật</NuxtLink>
              <NuxtLink to="/dieu-khoan-su-dung">Điều khoản</NuxtLink>
              <NuxtLink to="/lien-he">Liên hệ</NuxtLink>
              <NuxtLink to="/admin">Admin</NuxtLink>
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
function toggleColorMode() {
  colorMode.preference = colorMode.value === 'dark' ? 'light' : 'dark'
}
const showAuth = ref(false)
const mobileNav = ref(false)
const showBeta = ref(false)
onMounted(() => {
  if (localStorage.getItem('vl360_beta_dismissed') !== '1') showBeta.value = true
})
function dismissBeta() { showBeta.value = false; localStorage.setItem('vl360_beta_dismissed', '1') }

// Nav theo intent + region-first (deep-research: NN/g mega-menu, Visit California)
const navGroups: Array<{ label: string; to?: string; children?: { to: string; label: string }[] }> = [
  { label: 'Khám phá', children: [
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

onMounted(() => {
  const onDoc = (e: MouseEvent) => { if (!(e.target as HTMLElement)?.closest('.main-nav')) openGroup.value = null }
  const onEsc = (e: KeyboardEvent) => { if (e.key === 'Escape') { openGroup.value = null; mobileNav.value = false } }
  document.addEventListener('click', onDoc)
  document.addEventListener('keydown', onEsc)
  onUnmounted(() => {
    document.removeEventListener('click', onDoc)
    document.removeEventListener('keydown', onEsc)
    document.body.style.overflow = ''
  })
})

</script>
