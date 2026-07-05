<template>
  <div class="page contact-page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Liên hệ' }]" />

    <!-- Brand masthead — same river→clay wash family as Giới thiệu. -->
    <section class="brand-masthead contact-masthead">
      <div class="bm-inner">
        <p class="bm-eyebrow"><span class="bm-tick" aria-hidden="true"></span>Liên hệ</p>
        <h1>{{ pc('hero_title') }}</h1>
        <p class="bm-sub">{{ pc('hero_subtitle') }}</p>
        <p class="bm-sla"><span aria-hidden="true">●</span> Thường trả lời trong 24–48 giờ — hai người đọc từng tin nhắn, không phải chatbot.</p>
      </div>
      <svg class="bm-motif" viewBox="0 0 120 120" aria-hidden="true" focusable="false">
        <path d="M44 30c-10 6-16 18-14 30 2 13 12 22 25 24" fill="none" stroke-width="1.6" stroke-linecap="round" />
        <rect x="52" y="20" width="28" height="50" rx="6" fill="none" stroke-width="1.6" />
        <line x1="60" y1="60" x2="72" y2="60" stroke-width="1.6" stroke-linecap="round" />
        <circle cx="66" cy="24" r="9" fill="none" stroke-width="1.4" />
      </svg>
    </section>

    <blockquote class="pull-quote contact-quote">
      Chúng tôi không bán tour. Chúng tôi giới thiệu vùng đất.
    </blockquote>

    <div class="contact-cards">
      <section v-if="isClaim" class="contact-card card-claim">
        <div class="card-icon" aria-hidden="true">🏷️</div>
        <h2>Đăng ký quản lý trang</h2>
        <p>Bạn là chủ cơ sở kinh doanh, homestay, nhà vườn, hoặc điểm du lịch? Đăng ký để cập nhật thông tin, ảnh, giờ mở cửa và nhận đánh giá từ khách.</p>
        <div class="card-action">
          <a :href="`mailto:${claimEmail}?subject=${encodeURIComponent(claimSubject)}`" class="btn btn-primary">📧 Gửi email đăng ký</a>
        </div>
        <p class="card-note">Hoặc nhắn Zalo: <strong>{{ zaloName }}</strong></p>
      </section>

      <section class="contact-card card-general">
        <div class="card-icon" aria-hidden="true">📬</div>
        <h2>Gửi yêu cầu</h2>
        <p>Mọi yêu cầu về nội dung, dữ liệu cá nhân, báo cáo vi phạm hoặc khiếu nại bản quyền.</p>
        <div class="card-action">
          <a :href="`mailto:${contactEmail}`" class="btn btn-primary">📧 {{ contactEmail }}</a>
        </div>
      </section>

      <section class="contact-card card-partner">
        <div class="card-icon" aria-hidden="true">🤝</div>
        <h2>Hợp tác quảng bá</h2>
        <p>Đối tác du lịch, OCOP, cơ quan địa phương muốn giới thiệu sản phẩm, điểm đến trên vinhlong360.</p>
        <div class="card-action">
          <a :href="`mailto:${contactEmail}?subject=Hợp tác quảng bá`" class="btn btn-outline">📧 Liên hệ hợp tác</a>
        </div>
      </section>

      <section class="contact-card card-report">
        <div class="card-icon" aria-hidden="true">🛡️</div>
        <h2>Báo cáo vi phạm</h2>
        <p>Dùng nút <strong>Báo cáo</strong> ngay trên mỗi bài đăng/bình luận. Chúng tôi xử lý trong vòng 48 giờ.</p>
      </section>

      <section class="contact-card card-privacy">
        <div class="card-icon" aria-hidden="true">🔒</div>
        <h2>Dữ liệu cá nhân</h2>
        <p>Theo <NuxtLink to="/chinh-sach-bao-mat">Chính sách bảo mật</NuxtLink>: truy cập/chỉnh sửa (10 ngày), rút đồng ý (15 ngày), xoá dữ liệu (20 ngày). Bạn cũng có thể tự xoá tài khoản trong phần tài khoản.</p>
      </section>
    </div>

    <!-- Cross-links -->
    <section class="block band catalog-cross reveal sediment-head">
      <h2>Xem thêm</h2>
      <div class="cross-links">
        <NuxtLink to="/cong-dong" class="cross-card">
          <span class="cross-icon" aria-hidden="true">💬</span>
          <div><strong>Cộng đồng</strong><p>Hỏi đáp & chia sẻ</p></div>
        </NuxtLink>
        <NuxtLink to="/chinh-sach-bao-mat" class="cross-card">
          <span class="cross-icon" aria-hidden="true">🔒</span>
          <div><strong>Bảo mật</strong><p>Chính sách dữ liệu</p></div>
        </NuxtLink>
        <NuxtLink to="/dieu-khoan-su-dung" class="cross-card">
          <span class="cross-icon" aria-hidden="true">📄</span>
          <div><strong>Điều khoản</strong><p>Điều khoản sử dụng</p></div>
        </NuxtLink>
        <NuxtLink to="/" class="cross-card">
          <span class="cross-icon" aria-hidden="true">🏠</span>
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
const claimEntity = computed(() => {
  if (!route.query.entity) return ''
  const raw = decodeURIComponent(String(route.query.entity)).slice(0, 200)
  return /^[a-z][a-z0-9+\-.]*:/i.test(raw) ? '' : raw
})
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

/* ── Brand masthead — same river→clay wash family as Giới thiệu; each
   page keeps its own scoped copy (no shared component per unit scope). ── */
.brand-masthead {
  position: relative;
  overflow: clip;
  isolation: isolate;
  margin: 0 calc(-1 * var(--space-5)) var(--space-6);
  padding: var(--space-8) var(--space-5) var(--space-6);
  display: flex;
  align-items: center;
  gap: var(--space-6);
  background:
    var(--grain),
    linear-gradient(120deg, color-mix(in srgb, var(--river-600) 14%, transparent) 0%, var(--bg-warm) 55%, rgba(var(--primary-rgb), .16) 120%);
  background-blend-mode: overlay, normal;
}
.bm-inner { flex: 1 1 auto; min-width: 0; max-width: var(--measure-read); }
.bm-eyebrow {
  display: flex; align-items: center; gap: var(--space-2);
  font-family: var(--font-sans); font-size: var(--text-2xs); font-weight: 700;
  text-transform: uppercase; letter-spacing: var(--tracking-caps);
  color: var(--primary-fg-strong); margin: 0 0 var(--space-3);
}
.bm-tick { width: 14px; height: 1.5px; background: var(--accent, var(--amber-500)); flex-shrink: 0; }
.brand-masthead h1 {
  font-family: var(--font-editorial); font-weight: 600;
  font-size: clamp(1.9rem, 1.55rem + 1.8vw, 2.7rem);
  line-height: var(--leading-tight); letter-spacing: var(--tracking-tight);
  color: var(--ink); margin: 0 0 var(--space-2); text-wrap: balance;
}
.bm-sub {
  font-family: var(--font-editorial); font-style: italic;
  font-size: clamp(1rem, .92rem + .4vw, 1.2rem);
  line-height: var(--leading-snug); color: var(--ink-secondary, var(--muted));
  margin: 0 0 var(--space-3); max-width: 46ch;
}
/* Response-time SLA badge — published up front, not buried in card copy. */
.bm-sla {
  display: inline-flex; align-items: center; gap: var(--space-2);
  font-family: var(--font-sans); font-size: var(--text-xs); font-weight: var(--weight-semibold);
  color: var(--secondary-fg); margin: 0;
}
.bm-sla span { color: var(--leaf-600); font-size: .55rem; }
.bm-motif { width: clamp(80px, 8vw + 40px, 128px); height: auto; flex-shrink: 0; color: var(--clay-400); opacity: .85; }
.bm-motif path, .bm-motif rect, .bm-motif line, .bm-motif circle { stroke: currentColor; fill: none; }

.contact-quote {
  max-width: var(--measure-read);
  margin: 0 auto var(--space-8);
}

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
@media (max-width: 600px) {
  .brand-masthead { flex-direction: column; text-align: center; padding-block: var(--space-6); }
  .bm-inner { max-width: none; }
  .bm-sla { display: inline-flex; }
}

/* Focus & accessibility */
.contact-card a:focus-visible, .card-action .btn:focus-visible { outline: 2px solid var(--primary); outline-offset: 3px; border-radius: var(--radius-sm); }
.card-action .btn { transition: transform .35s var(--ease-spring-gentle), box-shadow .35s var(--ease-out-expo), background .3s var(--ease-out); }
.card-action .btn:hover { transform: translateY(-1px); box-shadow: var(--shadow-sm); }
.card-action .btn:active { transform: scale(.96); transition-duration: .08s; }

/* Dark mode */
.dark .brand-masthead {
  background:
    var(--grain),
    linear-gradient(120deg, rgba(116, 171, 181, .1) 0%, rgba(255,255,255,.02) 55%, rgba(var(--primary-rgb), .12) 120%);
}
.dark .bm-motif { color: var(--clay-400); opacity: .7; }
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
