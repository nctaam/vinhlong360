<template>
  <div>
    <div class="admin-head-row">
      <div>
        <h1>Cài đặt trang</h1>
        <p class="cs-subtitle">Quản lý các yếu tố trên website mà không cần code</p>
      </div>
    </div>

    <!-- Quick links: tác vụ hay dùng -->
    <div class="cs-quick-links" aria-label="Lối tắt tác vụ thường dùng">
      <NuxtLink v-for="q in quickLinks" :key="q.slug" :to="`/admin/cai-dat/${q.slug}`" class="cs-chip">
        <span aria-hidden="true">{{ q.icon }}</span> {{ q.label }}
      </NuxtLink>
    </div>

    <!-- Tìm nhanh danh mục -->
    <div class="cs-search-row">
      <div class="cs-search-wrap">
        <span class="cs-search-icon" aria-hidden="true">🔍</span>
        <input
          ref="searchEl"
          v-model="query"
          type="search"
          class="cs-search-input"
          placeholder="Tìm danh mục cài đặt… (Ctrl+K)"
          aria-label="Tìm danh mục cài đặt"
          @keydown.enter.prevent="gotoFirstMatch"
          @keydown.esc="query = ''"
        />
        <span v-if="query" class="cs-search-count">{{ flatMatches.length }} kết quả</span>
      </div>
    </div>

    <!-- Trạng thái rỗng khi tìm không thấy -->
    <div v-if="query && flatMatches.length === 0" class="admin-empty-state">
      <span class="admin-empty-state-icon" aria-hidden="true">🔍</span>
      <span class="admin-empty-state-text">Không tìm thấy danh mục nào khớp “{{ query }}”.</span>
      <span class="admin-empty-state-hint">Thử từ khoá khác hoặc xoá ô tìm kiếm.</span>
    </div>

    <!-- Kết quả tìm kiếm: danh sách phẳng -->
    <div v-else-if="query" class="cs-grid">
      <NuxtLink
        v-for="(cat, i) in flatMatches"
        :key="cat.slug"
        :to="`/admin/cai-dat/${cat.slug}`"
        class="cs-card"
        :style="{ '--stagger': `${i * 40}ms` }"
      >
        <span class="cs-icon" aria-hidden="true">{{ cat.icon }}</span>
        <div>
          <h3>{{ cat.title }}</h3>
          <p>{{ cat.desc }}</p>
        </div>
        <span class="cs-arrow" aria-hidden="true">›</span>
      </NuxtLink>
    </div>

    <!-- Mặc định: nhóm theo lĩnh vực -->
    <template v-else>
      <section v-for="grp in groups" :key="grp.key" class="cs-group" :aria-label="grp.title">
        <h2 class="cs-group-title">
          <span class="cs-group-icon" aria-hidden="true">{{ grp.icon }}</span>
          {{ grp.title }}
          <span class="cs-group-count">{{ grp.items.length }}</span>
        </h2>
        <div class="cs-grid">
          <NuxtLink
            v-for="(cat, i) in grp.items"
            :key="cat.slug"
            :to="`/admin/cai-dat/${cat.slug}`"
            class="cs-card"
            :style="{ '--stagger': `${i * 40}ms` }"
          >
            <span class="cs-icon" aria-hidden="true">{{ cat.icon }}</span>
            <div>
              <h3>{{ cat.title }}</h3>
              <p>{{ cat.desc }}</p>
            </div>
            <span class="cs-arrow" aria-hidden="true">›</span>
          </NuxtLink>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'admin', middleware: 'admin' })
useHead({ title: 'Cài đặt — Admin' })

interface Category { slug: string; icon: string; title: string; desc: string; group: string }

const categories: Category[] = [
  { slug: 'thuong-hieu', icon: '🎨', title: 'Thương hiệu', desc: 'Tên trang, slogan, ảnh OG', group: 'brand' },
  { slug: 'seo', icon: '🔍', title: 'SEO', desc: 'Tiêu đề, mô tả, theme color', group: 'brand' },
  { slug: 'giao-dien', icon: '🎭', title: 'Giao diện', desc: 'Màu sắc tùy chỉnh', group: 'brand' },
  { slug: 'dieu-huong', icon: '🧭', title: 'Điều hướng', desc: 'Menu chính (thêm/xoá/sắp xếp)', group: 'structure' },
  { slug: 'footer', icon: '📋', title: 'Footer', desc: 'Cột footer, copyright, disclaimer', group: 'structure' },
  { slug: 'danh-muc', icon: '🏷️', title: 'Danh mục', desc: 'Emoji & nhãn loại, khu vực', group: 'structure' },
  { slug: 'trang-chu', icon: '🏠', title: 'Trang chủ', desc: 'Hero, pills, quick links, CTA', group: 'content' },
  { slug: 'trang', icon: '📄', title: 'Nội dung trang', desc: 'Hero & SEO từng trang', group: 'content' },
  { slug: 'thong-bao', icon: '📢', title: 'Thông báo', desc: 'Banner trên đầu trang', group: 'content' },
  { slug: 'chao-mung', icon: '👋', title: 'Bảng chào mừng', desc: 'Onboarding khách lần đầu', group: 'content' },
  { slug: 'tinh-nang', icon: '🎚️', title: 'Tính năng', desc: 'Bật/tắt khối nội dung', group: 'features' },
  { slug: 'tuyen-duong', icon: '🛣️', title: 'Tuyến đường', desc: 'Dữ liệu tuyến gợi ý', group: 'features' },
  { slug: 'chat-ai', icon: '💬', title: 'Chat & AI', desc: 'Tiêu đề, gợi ý, minh bạch AI', group: 'features' },
  { slug: 'lien-he', icon: '📬', title: 'Liên hệ', desc: 'Email, Zalo', group: 'legal' },
  { slug: 'phap-ly', icon: '⚖️', title: 'Trang pháp lý', desc: 'Chính sách bảo mật, điều khoản', group: 'legal' },
]

const GROUP_META: { key: string; icon: string; title: string }[] = [
  { key: 'brand', icon: '🎨', title: 'Thương hiệu & Nhận diện' },
  { key: 'structure', icon: '🗂️', title: 'Cấu trúc & Điều hướng' },
  { key: 'content', icon: '📝', title: 'Nội dung' },
  { key: 'features', icon: '🎚️', title: 'Tính năng' },
  { key: 'legal', icon: '⚖️', title: 'Liên hệ & Pháp lý' },
]

const groups = computed(() =>
  GROUP_META
    .map(g => ({ ...g, items: categories.filter(c => c.group === g.key) }))
    .filter(g => g.items.length > 0)
)

// Lối tắt: 3 tác vụ hay dùng nhất
const quickLinks = [
  { slug: 'trang-chu', icon: '🏠', label: 'Sửa Hero trang chủ' },
  { slug: 'seo', icon: '🔍', label: 'Mặc định SEO' },
  { slug: 'dieu-huong', icon: '🧭', label: 'Menu điều hướng' },
]

// Tìm kiếm phía client (khớp tiêu đề + mô tả)
const query = ref('')
const searchEl = ref<HTMLInputElement | null>(null)

function normalize(s: string): string {
  return s.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/đ/g, 'd')
}

const flatMatches = computed(() => {
  const q = normalize(query.value.trim())
  if (!q) return categories
  return categories.filter(c => normalize(`${c.title} ${c.desc}`).includes(q))
})

function gotoFirstMatch() {
  const first = flatMatches.value[0]
  if (first) navigateTo(`/admin/cai-dat/${first.slug}`)
}

function onKeydown(e: KeyboardEvent) {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
    e.preventDefault()
    searchEl.value?.focus()
  }
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>

<style scoped>
.cs-subtitle { font-size: .85rem; color: var(--muted); margin-top: var(--space-1); }

/* ── Quick-link chips ── */
.cs-quick-links {
  display: flex; gap: var(--space-2); flex-wrap: wrap;
  margin: var(--space-4) 0 var(--space-3);
}
.cs-chip {
  display: inline-flex; align-items: center; gap: 6px;
  min-height: 36px; padding: 6px 14px; border-radius: 999px;
  background: var(--bg-alt, rgba(0,0,0,.03)); border: .5px solid var(--line);
  color: inherit; text-decoration: none;
  font-size: .8rem; font-weight: 500; line-height: 1;
  transition: transform .2s cubic-bezier(.2,1,.4,1), border-color .2s, background .2s, box-shadow .2s;
}
.cs-chip:hover { border-color: var(--primary, #219653); color: var(--primary, #219653); transform: translateY(-1px); }
.cs-chip:active { transform: scale(.96); transition-duration: .08s; }
.cs-chip:focus-visible { outline: 2px solid var(--primary, #219653); outline-offset: 2px; }

/* ── Search row ── */
.cs-search-row { margin-bottom: var(--space-5); }
.cs-search-wrap { position: relative; display: flex; align-items: center; max-width: 480px; }
.cs-search-icon {
  position: absolute; left: 14px; font-size: .95rem; opacity: .5; pointer-events: none;
}
.cs-search-input {
  width: 100%; min-height: 44px; padding: 10px 14px 10px 40px;
  border-radius: 12px; border: .5px solid var(--line);
  background: var(--bg); color: inherit; font-size: .9rem;
  transition: border-color .2s, box-shadow .2s;
}
.cs-search-input::placeholder { color: var(--muted); }
.cs-search-input:focus-visible {
  outline: none; border-color: var(--primary, #219653);
  box-shadow: 0 0 0 3px color-mix(in oklab, var(--primary, #219653) 18%, transparent);
}
.cs-search-count {
  position: absolute; right: 14px; font-size: .72rem; color: var(--muted);
  pointer-events: none; white-space: nowrap;
}

/* ── Group sections ── */
.cs-group { margin-bottom: var(--space-7); }
.cs-group-title {
  display: flex; align-items: center; gap: var(--space-2);
  font-size: .82rem; font-weight: 700; letter-spacing: .04em; text-transform: uppercase;
  color: var(--muted); margin: 0 0 var(--space-3);
}
.cs-group-icon { font-size: 1rem; }
.cs-group-count {
  display: inline-flex; align-items: center; justify-content: center;
  min-width: 20px; height: 20px; padding: 0 6px; border-radius: 999px;
  background: var(--bg-alt, rgba(0,0,0,.05)); border: .5px solid var(--line);
  font-size: .7rem; font-weight: 600; letter-spacing: 0; color: var(--muted);
}

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
.cs-card:focus-visible {
  outline: 2px solid var(--primary, #219653); outline-offset: 2px;
  box-shadow: 0 0 0 5px color-mix(in oklab, var(--primary, #219653) 14%, transparent);
}
.cs-icon { font-size: 1.8rem; flex-shrink: 0; width: 40px; text-align: center; }
.cs-card div { flex: 1; min-width: 0; }
.cs-card h3 { margin: 0; font-size: .95rem; font-weight: 600; }
.cs-card p { margin: var(--space-1) 0 0; font-size: .78rem; color: var(--muted); line-height: 1.4; }
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
.dark .cs-chip { background: rgba(255,255,255,.05); border-color: rgba(255,255,255,.06); }
.dark .cs-chip:hover { background: rgba(255,255,255,.08); }
.dark .cs-search-input { background: var(--card, #2c2c2e); border-color: rgba(255,255,255,.06); }
.dark .cs-group-count { background: rgba(255,255,255,.06); border-color: rgba(255,255,255,.08); }
.dark .cs-card { background: var(--card, #2c2c2e); border-color: rgba(255,255,255,.06); }
.dark .cs-card:hover {
  box-shadow: 0 6px 20px rgba(0,0,0,.3);
  border-color: rgba(255,255,255,.18);
}

/* ── Reduced motion ── */
@media (prefers-reduced-motion: reduce) {
  .cs-card { animation: none; }
  .cs-card:hover, .cs-card:active,
  .cs-chip:hover, .cs-chip:active { transform: none; }
  .cs-card:hover .cs-arrow { transform: none; }
}

/* ── Mobile ── */
@media (max-width: 600px) {
  .cs-search-wrap { max-width: 100%; }
}
</style>
