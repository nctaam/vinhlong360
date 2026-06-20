<template>
  <div>
    <div class="admin-head-row">
      <div>
        <h1>Cài đặt trang</h1>
        <p class="cs-subtitle">Quản lý các yếu tố trên website mà không cần code</p>
      </div>
    </div>

    <div class="cs-grid">
      <NuxtLink v-for="(cat, i) in categories" :key="cat.slug" :to="`/admin/cai-dat/${cat.slug}`" class="cs-card" :style="{ '--stagger': `${i * 40}ms` }">
        <span class="cs-icon">{{ cat.icon }}</span>
        <div>
          <h3>{{ cat.title }}</h3>
          <p>{{ cat.desc }}</p>
        </div>
        <span class="cs-arrow" aria-hidden="true">›</span>
      </NuxtLink>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'admin', middleware: 'admin' })

const categories = [
  { slug: 'thuong-hieu', icon: '🎨', title: 'Thương hiệu', desc: 'Tên trang, slogan, ảnh OG' },
  { slug: 'seo', icon: '🔍', title: 'SEO', desc: 'Tiêu đề, mô tả, theme color' },
  { slug: 'dieu-huong', icon: '🧭', title: 'Điều hướng', desc: 'Menu chính (thêm/xoá/sắp xếp)' },
  { slug: 'footer', icon: '📋', title: 'Footer', desc: 'Cột footer, copyright, disclaimer' },
  { slug: 'trang-chu', icon: '🏠', title: 'Trang chủ', desc: 'Hero, pills, quick links, CTA' },
  { slug: 'lien-he', icon: '📬', title: 'Liên hệ', desc: 'Email, Zalo' },
  { slug: 'thong-bao', icon: '📢', title: 'Thông báo', desc: 'Banner trên đầu trang' },
  { slug: 'giao-dien', icon: '🎭', title: 'Giao diện', desc: 'Màu sắc tùy chỉnh' },
  { slug: 'danh-muc', icon: '🏷️', title: 'Danh mục', desc: 'Emoji & nhãn loại, khu vực' },
  { slug: 'trang', icon: '📄', title: 'Nội dung trang', desc: 'Hero & SEO từng trang' },
  { slug: 'tinh-nang', icon: '🎚️', title: 'Tính năng', desc: 'Bật/tắt khối nội dung' },
  { slug: 'phap-ly', icon: '⚖️', title: 'Trang pháp lý', desc: 'Chính sách bảo mật, điều khoản' },
  { slug: 'chao-mung', icon: '👋', title: 'Bảng chào mừng', desc: 'Onboarding khách lần đầu' },
  { slug: 'tuyen-duong', icon: '🛣️', title: 'Tuyến đường', desc: 'Dữ liệu tuyến gợi ý' },
  { slug: 'chat-ai', icon: '💬', title: 'Chat & AI', desc: 'Tiêu đề, gợi ý, minh bạch AI' },
]
</script>

<style scoped>
.cs-subtitle { font-size: .85rem; color: var(--muted); margin-top: 4px; }

.cs-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--space-4);
}
.cs-card {
  display: flex; align-items: center; gap: var(--space-4);
  padding: var(--space-5); border-radius: 14px;
  background: var(--bg); border: .5px solid var(--line);
  text-decoration: none; color: inherit; min-height: 80px;
  animation: cs-fade-in .4s cubic-bezier(.2,1,.4,1) both;
  animation-delay: var(--stagger, 0ms);
  transition: transform .3s cubic-bezier(.2,1,.4,1), box-shadow .3s, border-color .3s;
}
.cs-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(0,0,0,.06);
  border-color: var(--primary, #219653);
}
.cs-card:active { transform: scale(.98); }
.cs-card:focus-visible { outline: 2px solid var(--primary, #219653); outline-offset: 2px; }
.cs-icon { font-size: 1.8rem; flex-shrink: 0; width: 40px; text-align: center; }
.cs-card div { flex: 1; min-width: 0; }
.cs-card h3 { margin: 0; font-size: .95rem; font-weight: 600; }
.cs-card p { margin: 4px 0 0; font-size: .78rem; color: var(--muted); line-height: 1.4; }
.cs-arrow {
  font-size: 1.4rem; font-weight: 300; color: var(--muted); flex-shrink: 0;
  opacity: .4; transition: opacity .2s, transform .2s cubic-bezier(.2,1,.4,1);
}
.cs-card:hover .cs-arrow { opacity: .8; transform: translateX(3px); }

@keyframes cs-fade-in {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

/* ── Dark ── */
.dark .cs-card { background: var(--card, #2c2c2e); border-color: rgba(255,255,255,.06); }
.dark .cs-card:hover { box-shadow: 0 6px 20px rgba(0,0,0,.3); }

/* ── Reduced motion ── */
@media (prefers-reduced-motion: reduce) {
  .cs-card { animation: none; }
  .cs-card:hover, .cs-card:active { transform: none; }
  .cs-card:hover .cs-arrow { transform: none; }
}
</style>
