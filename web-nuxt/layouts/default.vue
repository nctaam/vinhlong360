<template>
  <div>
    <a href="#main-content" class="skip-link">Bỏ qua điều hướng</a>
    <header class="topbar">
      <div class="topbar-inner">
        <NuxtLink class="brand" to="/">
          <span class="logo">vinhlong<span class="dot">360</span></span>
          <span class="tld">.vn</span>
        </NuxtLink>
        <button class="nav-toggle" :aria-expanded="mobileNav" aria-controls="main-nav" aria-label="Menu" @click="mobileNav = !mobileNav">
          <span></span><span></span><span></span>
        </button>
        <div class="nav-backdrop" :class="{ show: mobileNav }" @click="mobileNav = false"></div>
        <nav id="main-nav" class="main-nav" :class="{ open: mobileNav }">
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
        <form class="topbar-search" role="search" @submit.prevent="onSearch">
          <input
            v-model="searchQuery"
            type="search"
            placeholder="Tìm đặc sản, trải nghiệm…"
            aria-label="Tìm kiếm"
          />
        </form>
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

    <main id="main-content">
      <slot />
    </main>

    <AuthModal :visible="showAuth" @close="showAuth = false" />
    <ClientOnly>
      <ScrollToTop />
    </ClientOnly>
    <ChatWidget />
    <ClientOnly>
      <JourneyBar />
      <ToastContainer />
    </ClientOnly>

    <footer class="site-footer">
      <div class="footer-inner">
        <div class="footer-grid">
          <div class="footer-brand">
            <strong class="footer-logo">vinhlong360<span style="color: var(--accent)">.vn</span></strong>
            <p>Cổng du lịch &amp; sản phẩm địa phương — khám phá Vĩnh Long, Bến Tre, Trà Vinh theo cách của người bản địa.</p>
          </div>
          <div class="footer-links">
            <h4>Khám phá</h4>
            <nav>
              <NuxtLink to="/du-lich">Du lịch</NuxtLink>
              <NuxtLink to="/theo-mua">Theo mùa</NuxtLink>
              <NuxtLink to="/san-pham">Sản phẩm</NuxtLink>
              <NuxtLink to="/ocop">OCOP</NuxtLink>
              <NuxtLink to="/luu-tru">Lưu trú</NuxtLink>
              <NuxtLink to="/ban-do" no-prefetch>Bản đồ</NuxtLink>
              <NuxtLink to="/danh-ba">Danh bạ hành chính</NuxtLink>
              <NuxtLink to="/tuyen-duong">Tuyến đường</NuxtLink>
            </nav>
          </div>
          <div class="footer-links">
            <h4>Theo sở thích</h4>
            <nav>
              <NuxtLink to="/kham-pha/am-thuc">Ẩm thực</NuxtLink>
              <NuxtLink to="/kham-pha/thien-nhien">Thiên nhiên</NuxtLink>
              <NuxtLink to="/kham-pha/van-hoa">Văn hóa</NuxtLink>
              <NuxtLink to="/kham-pha/lang-nghe">Làng nghề</NuxtLink>
              <NuxtLink to="/kham-pha/mua-sam">Mua sắm</NuxtLink>
            </nav>
          </div>
          <div class="footer-links">
            <h4>Công cụ</h4>
            <nav>
              <NuxtLink to="/tao-lich-trinh" no-prefetch>Tạo lịch trình</NuxtLink>
              <NuxtLink to="/lich-trinh">Lịch trình gợi ý</NuxtLink>
              <NuxtLink to="/hanh-trinh">Đã lưu</NuxtLink>
              <NuxtLink to="/cong-dong">Cộng đồng</NuxtLink>
            </nav>
          </div>
        </div>
        <div class="footer-bottom">
          <p class="disclaimer">Thông tin mùa vụ, giá &amp; địa điểm mang tính tham khảo — vui lòng xác nhận với địa phương trước khi sử dụng.</p>
          <nav class="footer-legal" style="display:flex; gap:16px; flex-wrap:wrap; margin:8px 0;">
            <NuxtLink to="/chinh-sach-bao-mat" style="color:var(--muted)">Chính sách bảo mật</NuxtLink>
            <NuxtLink to="/dieu-khoan-su-dung" style="color:var(--muted)">Điều khoản sử dụng</NuxtLink>
            <NuxtLink to="/lien-he" style="color:var(--muted)">Liên hệ</NuxtLink>
          </nav>
          <p>&copy; 2024–2026 vinhlong360. <NuxtLink to="/admin" style="color: var(--muted)">AdminCP</NuxtLink></p>
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
const searchQuery = ref('')
const showAuth = ref(false)
const mobileNav = ref(false)

// Nav theo intent + region-first (deep-research: NN/g mega-menu, Visit California)
const navGroups: Array<{ label: string; to?: string; children?: { to: string; label: string }[] }> = [
  { label: 'Khám phá', children: [
    { to: '/du-lich', label: 'Du lịch & trải nghiệm' },
    { to: '/luu-tru', label: 'Lưu trú' },
    { to: '/theo-mua', label: 'Đặc sản theo mùa' },
    { to: '/ban-do', label: 'Bản đồ' },
    { to: '/danh-ba', label: 'Danh bạ hành chính' },
    { to: '/tuyen-duong', label: 'Tuyến đường gợi ý' },
  ] },
  { label: 'Đặc sản', children: [
    { to: '/san-pham', label: 'Sản phẩm địa phương' },
    { to: '/ocop', label: 'Sản phẩm OCOP' },
  ] },
  { label: 'Lịch trình', children: [
    { to: '/lich-trinh', label: 'Lịch trình gợi ý' },
    { to: '/tao-lich-trinh', label: 'Tạo lịch trình' },
    { to: '/hanh-trinh', label: 'Đã lưu ❤️' },
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

onMounted(() => {
  const onDoc = (e: MouseEvent) => { if (!(e.target as HTMLElement)?.closest('.main-nav')) openGroup.value = null }
  const onEsc = (e: KeyboardEvent) => { if (e.key === 'Escape') openGroup.value = null }
  document.addEventListener('click', onDoc)
  document.addEventListener('keydown', onEsc)
  onUnmounted(() => { document.removeEventListener('click', onDoc); document.removeEventListener('keydown', onEsc) })
})

function onSearch() {
  if (searchQuery.value.trim()) {
    navigateTo(`/tim-kiem?q=${encodeURIComponent(searchQuery.value.trim())}`)
  }
}
</script>
