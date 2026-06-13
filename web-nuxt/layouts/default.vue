<template>
  <div>
    <a href="#main-content" class="skip-link">Bỏ qua điều hướng</a>
    <header class="topbar">
      <div class="topbar-inner">
        <NuxtLink class="brand" to="/">
          <span class="logo">vinhlong<span class="dot">360</span></span>
          <span class="tld">.vn</span>
        </NuxtLink>
        <button class="nav-toggle" aria-label="Menu" @click="mobileNav = !mobileNav">
          <span></span><span></span><span></span>
        </button>
        <div class="nav-backdrop" :class="{ show: mobileNav }" @click="mobileNav = false"></div>
        <nav class="main-nav" :class="{ open: mobileNav }">
          <NuxtLink to="/" :class="{ active: route.path === '/' }" @click="mobileNav = false">Trang chủ</NuxtLink>
          <NuxtLink to="/du-lich" :class="{ active: route.path === '/du-lich' }" @click="mobileNav = false">Du lịch</NuxtLink>
          <NuxtLink to="/luu-tru" :class="{ active: route.path === '/luu-tru' }" @click="mobileNav = false">Lưu trú</NuxtLink>
          <NuxtLink to="/san-pham" :class="{ active: route.path === '/san-pham' }" @click="mobileNav = false">Sản phẩm</NuxtLink>
          <NuxtLink to="/ocop" :class="{ active: route.path === '/ocop' }" @click="mobileNav = false">OCOP</NuxtLink>
          <NuxtLink to="/lich-trinh" :class="{ active: route.path.startsWith('/lich-trinh') || route.path === '/tao-lich-trinh' }" @click="mobileNav = false">Lịch trình</NuxtLink>
          <NuxtLink to="/hanh-trinh" :class="{ active: route.path === '/hanh-trinh' }" @click="mobileNav = false">❤️</NuxtLink>
          <NuxtLink to="/ban-do" no-prefetch :class="{ active: route.path === '/ban-do' }" @click="mobileNav = false">Bản đồ</NuxtLink>
          <NuxtLink to="/cong-dong" :class="{ active: route.path === '/cong-dong' }" @click="mobileNav = false">Cộng đồng</NuxtLink>
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
              <NuxtLink to="/san-pham">Sản phẩm</NuxtLink>
              <NuxtLink to="/ocop">OCOP</NuxtLink>
              <NuxtLink to="/luu-tru">Lưu trú</NuxtLink>
              <NuxtLink to="/ban-do" no-prefetch>Bản đồ</NuxtLink>
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
const searchQuery = ref('')
const showAuth = ref(false)
const mobileNav = ref(false)

watch(() => route.path, () => { mobileNav.value = false })

function onSearch() {
  if (searchQuery.value.trim()) {
    navigateTo(`/tim-kiem?q=${encodeURIComponent(searchQuery.value.trim())}`)
  }
}
</script>
