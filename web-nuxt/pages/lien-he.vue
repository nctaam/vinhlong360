<template>
  <div class="page contact-page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Liên hệ' }]" />

    <!-- Hero -->
    <section class="catalog-hero cat-contact">
      <div class="catalog-hero-inner">
        <span class="catalog-hero-icon" aria-hidden="true">📬</span>
        <div>
          <h1>{{ pc('hero_title') }}</h1>
          <p>{{ pc('hero_subtitle') }}</p>
        </div>
      </div>
    </section>

    <div class="contact-cards">
      <section v-if="isClaim" class="contact-card card-claim">
        <div class="card-icon">🏷️</div>
        <h2>Đăng ký quản lý trang</h2>
        <p>Bạn là chủ cơ sở kinh doanh, homestay, nhà vườn, hoặc điểm du lịch? Đăng ký để cập nhật thông tin, ảnh, giờ mở cửa và nhận đánh giá từ khách.</p>
        <div class="card-action">
          <a :href="`mailto:${claimEmail}?subject=${encodeURIComponent(claimSubject)}`" class="btn btn-primary">📧 Gửi email đăng ký</a>
        </div>
        <p class="card-note">Hoặc nhắn Zalo: <strong>{{ zaloName }}</strong></p>
      </section>

      <section class="contact-card card-general">
        <div class="card-icon">📬</div>
        <h2>Gửi yêu cầu</h2>
        <p>Mọi yêu cầu về nội dung, dữ liệu cá nhân, báo cáo vi phạm hoặc khiếu nại bản quyền.</p>
        <div class="card-action">
          <a :href="`mailto:${contactEmail}`" class="btn btn-primary">📧 {{ contactEmail }}</a>
        </div>
      </section>

      <section class="contact-card card-partner">
        <div class="card-icon">🤝</div>
        <h2>Hợp tác quảng bá</h2>
        <p>Đối tác du lịch, OCOP, cơ quan địa phương muốn giới thiệu sản phẩm, điểm đến trên vinhlong360.</p>
        <div class="card-action">
          <a :href="`mailto:${contactEmail}?subject=Hợp tác quảng bá`" class="btn btn-outline">📧 Liên hệ hợp tác</a>
        </div>
      </section>

      <section class="contact-card card-report">
        <div class="card-icon">🛡️</div>
        <h2>Báo cáo vi phạm</h2>
        <p>Dùng nút <strong>Báo cáo</strong> ngay trên mỗi bài đăng/bình luận. Chúng tôi xử lý trong vòng 48 giờ.</p>
      </section>

      <section class="contact-card card-privacy">
        <div class="card-icon">🔒</div>
        <h2>Dữ liệu cá nhân</h2>
        <p>Theo <NuxtLink to="/chinh-sach-bao-mat">Chính sách bảo mật</NuxtLink>: truy cập/chỉnh sửa (10 ngày), rút đồng ý (15 ngày), xoá dữ liệu (20 ngày). Bạn cũng có thể tự xoá tài khoản trong phần tài khoản.</p>
      </section>
    </div>

    <!-- Cross-links -->
    <section class="block catalog-cross reveal">
      <h2>Xem thêm</h2>
      <div class="cross-links">
        <NuxtLink to="/cong-dong" class="cross-card">
          <span class="cross-icon">💬</span>
          <div><strong>Cộng đồng</strong><p>Hỏi đáp & chia sẻ</p></div>
        </NuxtLink>
        <NuxtLink to="/chinh-sach-bao-mat" class="cross-card">
          <span class="cross-icon">🔒</span>
          <div><strong>Bảo mật</strong><p>Chính sách dữ liệu</p></div>
        </NuxtLink>
        <NuxtLink to="/dieu-khoan-su-dung" class="cross-card">
          <span class="cross-icon">📄</span>
          <div><strong>Điều khoản</strong><p>Điều khoản sử dụng</p></div>
        </NuxtLink>
        <NuxtLink to="/" class="cross-card">
          <span class="cross-icon">🏠</span>
          <div><strong>Trang chủ</strong><p>Về trang chủ</p></div>
        </NuxtLink>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
useReveal()
const { get: ss } = useSiteSettings()
const { f: pc } = usePageContent('lien_he')
const contactEmail = computed(() => ss('contact.email', 'lienhe@vinhlong360.vn'))
const claimEmail = computed(() => ss('contact.claim_email', 'lienhe@vinhlong360.vn'))
const zaloName = computed(() => ss('contact.zalo', 'vinhlong360'))

const route = useRoute()
const isClaim = computed(() => route.query.ref === 'claim')
const claimEntity = computed(() => route.query.entity ? decodeURIComponent(String(route.query.entity)) : '')
const claimSubject = computed(() => {
  const base = 'Đăng ký quản lý trang'
  return claimEntity.value ? `${base}: ${claimEntity.value}` : base
})

useSeoMeta({
  title: () => pc('seo_title'),
  description: () => pc('seo_description'),
  ogTitle: () => pc('og_title'),
  ogDescription: () => pc('og_description'),
})
useHead({
  link: [{ rel: 'canonical', href: canonicalUrl('/lien-he') }],
  script: [{
    type: 'application/ld+json',
    innerHTML: JSON.stringify({
      '@context': 'https://schema.org',
      '@type': 'ContactPage',
      name: 'Liên hệ vinhlong360',
      description: 'Liên hệ vinhlong360.vn: yêu cầu, báo cáo, hợp tác.',
      url: canonicalUrl('/lien-he'),
    }),
  }, {
    type: 'application/ld+json',
    innerHTML: JSON.stringify({
      '@context': 'https://schema.org',
      '@type': 'BreadcrumbList',
      itemListElement: [
        { '@type': 'ListItem', position: 1, name: 'Trang chủ', item: 'https://vinhlong360.vn/' },
        { '@type': 'ListItem', position: 2, name: 'Liên hệ' },
      ],
    }),
  }],
})
</script>

<style scoped>
.contact-page { max-width: 760px; }

.contact-cards {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

.contact-card {
  background: var(--card);
  border: .5px solid var(--line);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
  box-shadow: var(--shadow-xs);
  transition: transform .35s var(--ease-spring-gentle), box-shadow .35s var(--ease-out-expo), border-color .3s var(--ease-out);
}
.contact-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-md);
  border-color: var(--border);
}
.contact-card:active { transform: translateY(0) scale(.98); transition-duration: .08s; }
/* Inert info cards (no CTA) should not signal interactivity:
   no lift, no shadow/border shift, no icon motion. */
.card-report, .card-privacy { cursor: default; }
.card-report:hover, .card-privacy:hover {
  transform: none;
  box-shadow: var(--shadow-xs);
  border-color: var(--line);
}
.card-report:active, .card-privacy:active { transform: none; }

.card-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: radial-gradient(circle at 40% 40%, rgba(var(--primary-rgb), .08), rgba(var(--primary-rgb), .02) 70%);
  font-size: var(--text-2xl);
  line-height: 1;
  margin-bottom: var(--space-3);
  transition: transform .35s var(--ease-spring-gentle), background .3s var(--ease-out);
}
.contact-card:hover .card-icon { transform: scale(1.1) rotate(-3deg); }
.card-report:hover, .card-report:hover .card-icon, .card-privacy:hover, .card-privacy:hover .card-icon { transform: none; }

.contact-card h2 {
  font-size: var(--text-lg);
  font-weight: var(--weight-semibold);
  margin-bottom: var(--space-2);
}

.contact-card p {
  color: var(--muted);
  font-size: var(--text-sm);
  line-height: var(--leading-relaxed);
  margin-bottom: var(--space-3);
}
.contact-card p:last-child { margin-bottom: 0; }

.card-action { margin: var(--space-4) 0 var(--space-3); }
.card-action .btn { min-height: 44px; }

.contact-card .card-note {
  font-size: var(--text-xs);
  color: var(--muted);
  margin: var(--space-2) 0 0;
}

.card-claim {
  border-color: var(--accent);
  border-width: 2px;
  background: color-mix(in srgb, var(--accent) 4%, var(--card));
}

@media (min-width: 640px) {
  /* Intentional hierarchy: primary claim full-width, then a row of
     actionable cards (general + partner), then a row of informational
     cards (report + privacy). 6-col base lets thirds & halves coexist. */
  .contact-cards {
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    gap: var(--space-5);
  }
  .card-claim { grid-column: 1 / -1; }
  .card-general, .card-partner { grid-column: span 3; }
  .card-report, .card-privacy { grid-column: span 3; }
}

/* Focus & accessibility */
.contact-card a:focus-visible, .card-action .btn:focus-visible { outline: 2px solid var(--primary); outline-offset: 3px; border-radius: var(--radius-sm); }
.card-action .btn { transition: transform .35s var(--ease-spring-gentle), box-shadow .35s var(--ease-out-expo), background .3s var(--ease-out); }
.card-action .btn:hover { transform: translateY(-1px); box-shadow: var(--shadow-sm); }
.card-action .btn:active { transform: scale(.96); transition-duration: .08s; }

/* Dark mode */
.dark .contact-card { background: var(--bg-alt); border-color: var(--line); }
.dark .contact-card:hover { box-shadow: var(--shadow-lg); border-color: rgba(255,255,255,.1); }
.dark .card-report:hover, .dark .card-privacy:hover { box-shadow: var(--shadow-xs); border-color: var(--line); }
.dark .card-claim { background: color-mix(in srgb, var(--accent) 10%, var(--bg-alt)); border-color: rgba(var(--accent-rgb, 240,160,80), .35); }
.dark .contact-card p { color: var(--ink-secondary); }
.dark .contact-card h2 { color: var(--ink); }
.dark .card-icon { background: radial-gradient(circle at 40% 40%, rgba(255,255,255,.07), rgba(255,255,255,.02) 70%); }
.dark .card-claim .card-icon { background: radial-gradient(circle at 40% 40%, rgba(var(--accent-rgb, 240,160,80), .14), rgba(var(--accent-rgb, 240,160,80), .03) 70%); }

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .contact-card:hover,
  .contact-card:active,
  .contact-card:hover .card-icon,
  .card-action .btn:hover,
  .card-action .btn:active {
    transform: none;
  }
}
</style>
