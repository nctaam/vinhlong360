<template>
  <section class="guide-page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Cộng đồng', to: '/cong-dong' }, { label: 'Hướng dẫn thành viên' }]" />

    <header class="guide-hero">
      <span class="guide-hero-icon" aria-hidden="true">🏅</span>
      <div>
        <p class="dateline-eyebrow">SỔ TAY CỘNG ĐỒNG · CẤP BẬC &amp; HUY HIỆU</p>
        <h1>Hướng dẫn thành viên</h1>
        <p>Tìm hiểu hệ thống cấp bậc, điểm danh tiếng và huy hiệu trên vinhlong360.</p>
      </div>
    </header>

    <!-- Levels -->
    <section class="guide-section reveal sediment-head">
      <h2>Hệ thống cấp bậc</h2>
      <p class="guide-intro editorial-body">Cấp bậc phản ánh mức độ đóng góp tổng thể của bạn. Điểm được tính từ nhiều hoạt động — không thể đạt cấp cao chỉ bằng một loại đóng góp duy nhất.</p>
      <div class="level-grid">
        <div v-for="lv in levels" :key="lv.level" class="level-card" :class="`level-${lv.level}`">
          <span class="lv-icon" aria-hidden="true">{{ lv.icon }}</span>
          <div class="lv-info">
            <strong class="lv-name">{{ lv.label }}</strong>
            <span class="lv-req">{{ lv.req }}</span>
          </div>
          <span class="lv-tag">Cấp {{ lv.level }}</span>
        </div>
      </div>
    </section>

    <!-- Points -->
    <section class="guide-section reveal sediment-head">
      <h2>Cách tính điểm danh tiếng</h2>
      <p class="guide-intro editorial-body">Điểm được tính tự động từ các đóng góp đã duyệt. Để tránh lạm phát, mỗi loại hoạt động có <strong>giới hạn tối đa</strong> — điểm giảm dần khi số lượng tăng lên.</p>
      <div class="points-table-wrap" role="region" aria-label="Bảng tính điểm danh tiếng" tabindex="0">
        <table class="points-table">
          <thead>
            <tr>
              <th scope="col">Hoạt động</th>
              <th scope="col">Cách tính</th>
              <th scope="col">Tối đa</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="cat in categories" :key="cat.name">
              <td>
                <span class="cat-icon" aria-hidden="true">{{ cat.icon }}</span>
                {{ cat.name }}
              </td>
              <td class="cat-formula">{{ cat.formula }}</td>
              <td class="cat-max">{{ cat.max }}</td>
            </tr>
          </tbody>
          <tfoot>
            <tr>
              <td colspan="2"><strong>Tổng tối đa lý thuyết</strong></td>
              <td class="cat-max"><strong>315</strong></td>
            </tr>
          </tfoot>
        </table>
      </div>
      <div class="guide-note">
        <strong>Ví dụ:</strong> Một thành viên có 8 đánh giá, 5 bài viết, 3 ảnh, 12 người theo dõi, 4 địa điểm và 15 lượt thích sẽ có khoảng <strong>{{ examplePoints }} điểm</strong> — đạt cấp <strong>{{ exampleLevel }}</strong>.
      </div>
    </section>

    <!-- Badges -->
    <section class="guide-section reveal sediment-head">
      <h2>Huy hiệu</h2>
      <p class="guide-intro editorial-body">Huy hiệu ghi nhận thành tích cụ thể. Chúng được trao tự động khi bạn đạt đủ điều kiện.</p>
      <div class="badge-grid">
        <div v-for="b in badges" :key="b.id" class="badge-card">
          <span class="badge-icon" aria-hidden="true">{{ b.icon }}</span>
          <div class="badge-info">
            <strong>{{ b.label }}</strong>
            <span class="badge-req">{{ b.req }}</span>
          </div>
        </div>
      </div>
    </section>

    <!-- Tips -->
    <section class="guide-section reveal sediment-head">
      <h2>Mẹo tăng điểm hiệu quả</h2>
      <div class="tips-list">
        <div v-for="(tip, i) in tips" :key="i" class="tip-item">
          <span class="tip-num" aria-hidden="true">{{ i + 1 }}</span>
          <div>
            <strong>{{ tip.title }}</strong>
            <p>{{ tip.desc }}</p>
          </div>
        </div>
      </div>
    </section>

  </section>
</template>

<script lang="ts">
const levels = [
  { level: 1, icon: '🌱', label: 'Người mới', req: '0 – 19 điểm' },
  { level: 2, icon: '🤝', label: 'Người đóng góp', req: '20 – 79 điểm' },
  { level: 3, icon: '🌟', label: 'Đóng góp tích cực', req: '80 – 199 điểm' },
  { level: 4, icon: '👑', label: 'Đại sứ', req: '200+ điểm' },
]

const categories = [
  { icon: '✍️', name: 'Đánh giá', formula: '10 đầu ×5, 20 tiếp ×3, 20 tiếp ×1', max: 130 },
  { icon: '📝', name: 'Bài viết (không tính đánh giá)', formula: '15 đầu ×2, 15 tiếp ×1', max: 45 },
  { icon: '📸', name: 'Ảnh đính kèm', formula: '10 đầu ×3, 10 tiếp ×1', max: 40 },
  { icon: '👥', name: 'Người theo dõi', formula: '20 đầu ×1', max: 20 },
  { icon: '📍', name: 'Địa điểm khác nhau', formula: '10 đầu ×2, 10 tiếp ×1', max: 30 },
  { icon: '❤️', name: 'Lượt thích nhận được', formula: '50 đầu ×1', max: 50 },
]

const examplePoints = 40 + 0 + 9 + 12 + 8 + 15
const exampleLevel = examplePoints >= 200 ? 'Đại sứ' : examplePoints >= 80 ? 'Đóng góp tích cực' : examplePoints >= 20 ? 'Người đóng góp' : 'Người mới'

const badges = [
  { id: 'first_review', icon: '✍️', label: 'Đánh giá đầu tiên', req: '1 đánh giá' },
  { id: 'reviewer_25', icon: '⭐', label: 'Nhà phê bình', req: '25 đánh giá' },
  { id: 'photographer', icon: '📸', label: 'Nhiếp ảnh cộng đồng', req: '10 bài có ảnh' },
  { id: 'explorer', icon: '🧭', label: 'Người khám phá', req: '10 địa điểm khác nhau' },
  { id: 'popular', icon: '💛', label: 'Được yêu thích', req: '20 người theo dõi' },
  { id: 'quality', icon: '🏆', label: 'Nội dung chất lượng', req: '50 lượt thích' },
  { id: 'allrounder', icon: '🌟', label: 'Đa năng', req: '3+ địa điểm, 5+ đánh giá, 3+ ảnh' },
]

const tips = [
  { title: 'Đa dạng hóa đóng góp', desc: 'Điểm giảm dần khi tập trung một loại. Kết hợp đánh giá, ảnh và khám phá nhiều địa điểm để tăng nhanh nhất.' },
  { title: 'Viết đánh giá chất lượng', desc: 'Đánh giá mang lại nhiều điểm nhất (5 điểm/bài cho 10 bài đầu). Chia sẻ trải nghiệm thực tế, mẹo hay và lưu ý.' },
  { title: 'Đính kèm ảnh', desc: 'Ảnh vừa tăng điểm ảnh (3 điểm/bài), vừa giúp bài viết nhận nhiều lượt thích hơn.' },
  { title: 'Khám phá nhiều nơi', desc: 'Đánh giá ở nhiều địa điểm khác nhau thay vì lặp lại một chỗ — mỗi địa điểm mới mang thêm 2 điểm.' },
]
</script>

<script setup lang="ts">
useReveal()

useSeoMeta({
  title: 'Hướng dẫn thành viên — Hệ thống cấp bậc & điểm danh tiếng — vinhlong360',
  description: 'Tìm hiểu cách tính điểm danh tiếng, cấp bậc thành viên và huy hiệu trên cộng đồng vinhlong360.',
  ogTitle: 'Hướng dẫn thành viên — vinhlong360',
  ogDescription: 'Cách tính điểm danh tiếng, cấp bậc và huy hiệu trên vinhlong360.',
})
useHead({
  link: [{ rel: 'canonical', href: canonicalUrl('/huong-dan-thanh-vien') }],
  script: [{
    type: 'application/ld+json',
    innerHTML: JSON.stringify({
      '@context': 'https://schema.org',
      '@type': 'BreadcrumbList',
      itemListElement: [
        { '@type': 'ListItem', position: 1, name: 'Trang chủ', item: 'https://vinhlong360.vn/' },
        { '@type': 'ListItem', position: 2, name: 'Cộng đồng', item: 'https://vinhlong360.vn/cong-dong' },
        { '@type': 'ListItem', position: 3, name: 'Hướng dẫn thành viên' },
      ],
    }),
  }],
})
</script>

<style scoped>
.guide-page { max-width: 760px; margin: 0 auto; padding: var(--space-6) var(--space-4) var(--space-10); }

/* Hero */
.guide-hero {
  display: flex; align-items: center; gap: var(--space-4);
  padding: var(--space-6); margin-bottom: var(--space-8);
  background: linear-gradient(135deg, rgba(var(--secondary-rgb), .1) 0%, var(--bg-warm) 100%);
  border-radius: var(--radius-xl); border: .5px solid var(--line);
}
.guide-hero-icon { font-size: 2.5rem; flex-shrink: 0; }
/* Local page masthead eyebrow — small-caps dateline, matches the site's
   area/ward eyebrow pattern but scoped here (not promoted global). */
.dateline-eyebrow {
  font-family: var(--font-sans); font-size: var(--text-xs); font-weight: 700;
  text-transform: uppercase; letter-spacing: var(--tracking-caps);
  color: var(--muted); margin: 0 0 var(--space-1); padding-left: var(--space-3);
  position: relative;
}
.dateline-eyebrow::before {
  content: ""; position: absolute; left: 0; top: 50%; transform: translateY(-50%);
  width: var(--space-2); height: 1.5px; background: var(--primary);
}
.guide-hero h1 { margin: 0 0 var(--space-1); font-family: var(--font-editorial); font-size: var(--text-2xl); font-weight: 600; letter-spacing: var(--tracking-tight); }
.guide-hero p { margin: 0; color: var(--muted); font-size: var(--text-sm); }

/* Sections */
.guide-section { margin-bottom: var(--space-8); }
.guide-section h2 { font-size: var(--text-xl); font-weight: var(--weight-bold); margin: 0 0 var(--space-2); padding-bottom: var(--space-2); border-bottom: .5px solid var(--line); }
.guide-intro { color: var(--muted); font-size: var(--text-sm); margin: 0 0 var(--space-5); line-height: var(--leading-relaxed); }

/* Levels */
.level-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: var(--space-3); }
.level-card {
  display: flex; align-items: center; gap: var(--space-3);
  padding: var(--space-4); border-radius: var(--radius-lg);
  border: .5px solid var(--line); background: var(--card);
  transition: transform .25s var(--ease-spring-gentle), border-color .25s var(--ease-out);
}
.level-card:hover { transform: translateY(-2px); border-color: var(--primary-fg); }
.lv-icon { font-size: 1.75rem; flex-shrink: 0; }
.lv-info { flex: 1; min-width: 0; }
.lv-name { display: block; font-weight: var(--weight-semibold); }
.lv-req { font-size: var(--text-xs); color: var(--muted); }
.lv-tag { font-size: var(--text-xs); font-weight: var(--weight-semibold); color: var(--primary-fg); background: rgba(var(--primary-rgb, 46, 125, 50), .1); padding: .15rem .5rem; border-radius: var(--radius-full); white-space: nowrap; }

.level-1 { --level-color: var(--leaf-600); border-left: 3px solid var(--level-color); }
.level-2 { --level-color: var(--river-600); border-left: 3px solid var(--level-color); }
.level-3 { --level-color: var(--amber-500); border-left: 3px solid var(--level-color); }
.level-4 { --level-color: var(--amber-700); border-left: 3px solid var(--level-color); }

/* Points table */
.points-table-wrap { overflow-x: auto; margin-bottom: var(--space-4); }
.points-table { width: 100%; border-collapse: collapse; font-size: var(--text-sm); }
.points-table th { text-align: left; padding: var(--space-2) var(--space-3); font-weight: var(--weight-semibold); color: var(--muted); border-bottom: 1.5px solid var(--line); font-size: var(--text-xs); text-transform: uppercase; letter-spacing: .04em; }
.points-table td { padding: var(--space-3); border-bottom: .5px solid var(--line); }
.points-table tbody tr:hover { background: var(--bg-warm); }
.cat-icon { margin-right: var(--space-2); }
.cat-formula { color: var(--muted); font-size: var(--text-xs); }
.cat-max { text-align: right; font-weight: var(--weight-semibold); font-variant-numeric: tabular-nums; color: var(--primary-fg); }
.points-table tfoot td { border-bottom: none; padding-top: var(--space-3); }

.guide-note {
  background: var(--bg-warm); border-radius: var(--radius-lg); padding: var(--space-4);
  font-size: var(--text-sm); color: var(--ink-secondary, var(--ink)); line-height: var(--leading-relaxed);
  border: .5px solid var(--line);
}

/* Badges */
.badge-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: var(--space-3); }
.badge-card {
  display: flex; align-items: center; gap: var(--space-3);
  padding: var(--space-3) var(--space-4); border-radius: var(--radius-lg);
  border: .5px solid var(--line); background: var(--card);
  transition: transform .2s var(--ease-spring-gentle);
}
.badge-card:hover { transform: translateY(-1px); }
.badge-icon { font-size: 1.5rem; flex-shrink: 0; }
.badge-info { flex: 1; min-width: 0; }
.badge-info strong { display: block; font-size: var(--text-sm); }
.badge-req { font-size: var(--text-xs); color: var(--muted); }

/* Tips */
.tips-list { display: flex; flex-direction: column; gap: var(--space-3); }
.tip-item {
  display: flex; gap: var(--space-4); align-items: flex-start;
  padding: var(--space-4); border-radius: var(--radius-lg);
  background: var(--card); border: .5px solid var(--line);
}
.tip-num {
  flex-shrink: 0; width: 28px; height: 28px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 50%; background: var(--primary-fg); color: var(--text-on-dark, var(--white));
  font-size: var(--text-xs); font-weight: var(--weight-bold);
}
.tip-item strong { display: block; margin-bottom: var(--space-1); }
.tip-item p { margin: 0; font-size: var(--text-sm); color: var(--muted); line-height: var(--leading-relaxed); }

/* Dark */
.dark .guide-hero { background: linear-gradient(135deg, rgba(255,255,255,.03) 0%, rgba(255,255,255,.01) 100%); }
.dark .guide-note { background: var(--bg-alt); }
.dark .level-1 { --level-color: var(--secondary-fg); border-left-color: var(--level-color); }
.dark .level-2 { --level-color: var(--tertiary-fg); border-left-color: var(--level-color); }
.dark .level-3 { --level-color: var(--accent-text); border-left-color: var(--level-color); }
.dark .level-4 { --level-color: color-mix(in oklab, var(--amber-700) 70%, white); border-left-color: var(--level-color); }

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .level-card:hover, .badge-card:hover, .tip-item:hover { transform: none; }
}

/* Mobile */
@media (max-width: 600px) {
  .guide-hero { flex-direction: column; text-align: center; padding: var(--space-5); }
  .level-grid, .badge-grid { grid-template-columns: 1fr; }
  .points-table { font-size: var(--text-xs); }
}
</style>
