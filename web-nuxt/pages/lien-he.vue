<template>
  <div class="page contact-page" data-color-system="tri-region-v1">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Liên hệ' }]" :json-ld="true" />

    <!-- Brand masthead — same river→clay wash family as Giới thiệu. -->
    <section class="brand-masthead contact-masthead">
      <div class="bm-inner">
        <div class="bm-header-seal">
          <p class="bm-eyebrow"><span class="bm-tick" aria-hidden="true"></span>Liên hệ</p>
          <SourceMark tier="official" />
        </div>
        <h1>{{ pc('hero_title') }}</h1>
        <p class="bm-sub">{{ pc('hero_subtitle') }}</p>
        <p class="bm-sla"><span aria-hidden="true">●</span> Người thật đọc từng tin nhắn, không phải chatbot. Yêu cầu sửa thông tin có mã tra cứu và hạn cập nhật riêng.</p>
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
        <div class="card-icon" aria-hidden="true"><span class="card-icon-vector"><IconLine name="tag" /></span></div>
        <h2>Đăng ký quản lý trang</h2>
        <p>Bạn là chủ cơ sở kinh doanh, homestay, nhà vườn, hoặc điểm du lịch? Đăng ký để cập nhật thông tin, ảnh, giờ mở cửa và nhận đánh giá từ khách.</p>
        <div class="card-action">
          <a :href="`mailto:${claimEmail}?subject=${encodeURIComponent(claimSubject)}`" class="btn btn-primary"><IconLine name="message" /> Gửi email đăng ký</a>
        </div>
        <p class="card-note">Hoặc nhắn Zalo: <strong>{{ zaloName }}</strong></p>
      </section>

      <!-- Cổng hiệu đính công dân & Trách nhiệm giải trình độc lập (Civic Correction Bridge Card) -->
      <section class="contact-card card-correction card-correction--prominent">
        <div class="correction-card-header">
          <div class="card-icon" aria-hidden="true"><span class="card-icon-vector"><IconLine name="pencil" /></span></div>
          <span class="ombudsman-tag">Trách nhiệm giải trình · Ombudsman</span>
        </div>
        <h2>Sửa thông tin chưa đúng</h2>
        <p>Số điện thoại, địa chỉ, giờ mở cửa… hiển thị sai? Gửi yêu cầu có mã tra cứu — bạn theo dõi được từng bước và biết trước khi nào có cập nhật.</p>
        <p class="card-ombudsman-desc">Mọi đề xuất đính chính di tích, toạ độ thực địa, tiện ích du lịch và sản phẩm OCOP đều được đối chiếu công tâm theo quy trình thẩm định 3 tầng.</p>
        <div class="card-action correction-actions">
          <NuxtLink to="/yeu-cau/sua-thong-tin" class="btn btn-primary"><IconLine name="pencil" /> Gửi yêu cầu sửa thông tin</NuxtLink>
          <NuxtLink to="/yeu-cau/tra-cuu" class="btn btn-outline"><IconLine name="tag" /> Tra cứu tiến độ yêu cầu</NuxtLink>
        </div>
        <p class="card-note"><NuxtLink to="/yeu-cau/tra-cuu">Tra cứu yêu cầu đã gửi</NuxtLink> bằng mã trên biên nhận.</p>
      </section>

      <section class="contact-card card-general">
        <div class="card-icon" aria-hidden="true"><span class="card-icon-vector"><IconLine name="message" /></span></div>
        <h2>Gửi yêu cầu khác</h2>
        <p>Dữ liệu cá nhân, khiếu nại bản quyền, hoặc việc chưa có kênh riêng. Khiếu nại nội dung và khôi phục tài khoản hiện xử lý qua email — chưa có trang theo dõi trực tuyến.</p>
        <div class="card-action">
          <a :href="`mailto:${contactEmail}`" class="btn btn-primary"><IconLine name="message" /> {{ contactEmail }}</a>
        </div>
      </section>

      <section class="contact-card card-partner">
        <div class="card-icon" aria-hidden="true"><span class="card-icon-vector"><IconLine name="users" /></span></div>
        <h2>Hợp tác quảng bá</h2>
        <p>Đối tác du lịch, OCOP, cơ quan địa phương muốn giới thiệu sản phẩm, điểm đến trên vinhlong360.</p>
        <div class="card-action">
          <a :href="`mailto:${contactEmail}?subject=Hợp tác quảng bá`" class="btn btn-outline"><IconLine name="message" /> Liên hệ hợp tác</a>
        </div>
      </section>

      <section class="contact-card card-report">
        <div class="card-icon" aria-hidden="true"><span class="card-icon-vector"><IconLine name="flag" /></span></div>
        <h2>Báo cáo vi phạm</h2>
        <p>Dùng nút <strong>Báo cáo</strong> ngay trên mỗi bài đăng/bình luận. Đội kiểm duyệt xem xét theo thứ tự tiếp nhận.</p>
      </section>

      <section class="contact-card card-privacy">
        <div class="card-icon" aria-hidden="true"><span class="card-icon-vector"><IconLine name="shield-check" /></span></div>
        <h2>Dữ liệu cá nhân</h2>
        <p>Theo <NuxtLink to="/chinh-sach-bao-mat">Chính sách bảo mật</NuxtLink>: truy cập/chỉnh sửa (10 ngày), rút đồng ý (15 ngày), xoá dữ liệu ({{ accountErasureDeadlineDays }} ngày). Bạn cũng có thể tự xoá tài khoản trong phần tài khoản.</p>
      </section>
    </div>

    <CatalogAeoPlaque
      kicker="Đầu mối tiếp nhận · Trực tiếp 24/7"
      title="Cam kết tiếp nhận phản ánh & hỗ trợ du khách Vĩnh Long"
      accent="river"
      icon="message"
      :entries="contactAeoEntries"
      cta-to="/yeu-cau/tra-cuu"
      cta-label="Tra cứu tiến độ yêu cầu bằng mã biên nhận"
    />
  </div>
</template>

<script setup lang="ts">
import privacyPolicy from '#privacy-policy'

useReveal()
const accountErasureDeadlineDays = privacyPolicy.accountErasureDeadlineDays
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

const contactAeoEntries = [
  {
    heading: 'Thời gian phản hồi cam kết',
    text: 'Yêu cầu sửa đổi thông tin địa điểm được cấp mã tra cứu riêng để theo dõi tiến độ. Mọi phản hồi cộng đồng và liên hệ hợp tác được người thật tiếp nhận và xử lý theo thứ tự.',
  },
  {
    heading: 'Kênh hỗ trợ khẩn cấp & thực địa',
    text: 'Du khách cần trợ giúp tại thực địa có thể gọi trực tiếp Tổng đài hỗ trợ du lịch tỉnh Vĩnh Long hoặc sử dụng danh bạ hotline trên hệ thống.',
  },
  {
    heading: 'Minh bạch & độc lập biên tập',
    text: 'VinhLong360 hoạt động vì lợi ích cộng đồng, không bán tour, tôn trọng tính khách quan của dữ liệu và quyền tự quyết của cơ sở dịch vụ.',
  },
]

useSeoMeta({
  title: () => pc('seo_title'),
  description: () => pc('seo_description'),
  ogTitle: () => pc('og_title'),
  ogDescription: () => pc('og_description'),
  ogUrl: () => canonicalUrl('/lien-he'),
  twitterCard: 'summary_large_image',
})

// Schema.org unified @graph: '@type': 'ContactPage'
const contactJsonLd = computed(() => buildContactPageSchemaGraph({
  title: pc('seo_title'),
  description: pc('seo_description'),
  email: contactEmail.value,
  claimEmail: claimEmail.value,
}))

useHead(() => ({
  link: [{ rel: 'canonical', href: canonicalUrl('/lien-he') }],
  script: [
    { type: 'application/ld+json', innerHTML: safeJsonLd(contactJsonLd.value) },
  ],
}))
</script>

<style src="~/assets/css/legal.css"></style>
<style scoped>
.contact-page { max-width: 760px; }

/* Response-time SLA badge — published up front, not buried in card copy. */
.bm-sla {
  display: inline-flex; align-items: center; gap: var(--space-2);
  font-family: var(--font-sans); font-size: var(--text-xs); font-weight: var(--weight-semibold);
  color: var(--color-action); margin: 0;
}
.bm-sla span { color: var(--color-material-leaf); font-size: var(--text-2xs); }
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
  counter-reset: contact-channel;
}

/* Wave 9: Open Architectural Contact Ledger — unboxed from 4-sided cards */
.contact-card {
  counter-increment: contact-channel;
  background: transparent;
  border: 0;
  border-block-start: 1.5px solid var(--line);
  border-radius: 0;
  padding: var(--space-5) 0 var(--space-3);
  box-shadow: none;
  transition: border-color .3s var(--ease-out);
}
.contact-card::before {
  content: "KÊNH " counter(contact-channel, decimal-leading-zero);
  display: block;
  margin-bottom: var(--space-2);
  font-family: var(--font-editorial);
  font-style: italic;
  font-weight: 500;
  font-size: var(--text-xs);
  letter-spacing: 0.08em;
  color: var(--color-brand);
}
.contact-card:hover {
  border-block-start-color: var(--color-brand);
}
/* Inert info cards (no CTA) should not signal interactivity */
.card-report, .card-privacy { cursor: default; }
.card-report:hover, .card-privacy:hover {
  border-block-start-color: var(--line);
}

/* Open Architectural Glyph Mark — unboxed watermark with sediment rule accent */
.card-icon {
  position: relative;
  display: inline-flex;
  align-items: flex-end;
  justify-content: flex-start;
  width: var(--space-10, 40px);
  height: var(--space-10, 40px);
  padding: 0 0 var(--space-1);
  border-radius: 0;
  border: 0;
  border-bottom: 1px solid var(--line);
  background: transparent;
  margin-bottom: var(--space-3);
  overflow: clip;
  transition: transform .35s var(--ease-out-expo), border-color .3s var(--ease-out);
}
.card-icon::before {
  content: "";
  position: absolute; top: 0; right: 0;
  width: 3px; height: 15px;
  background: linear-gradient(180deg, var(--color-material-river), var(--color-material-clay));
  opacity: .7;
}
.card-icon-vector {
  display: inline-flex;
  font-size: 1.4rem;
  color: var(--color-action);
  opacity: .85;
  transform: translate(2px, 2px);
  transition: transform .35s var(--ease-out-expo), color .3s var(--ease-out);
}
.contact-card:hover .card-icon-vector {
  transform: translate(3px, 1px) scale(1.05);
}
.contact-card:hover .card-icon { transform: translateY(-2px); border-color: var(--border); }
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
  border-block-start-color: var(--color-action);
  border-block-start-width: 2px;
  background: transparent;
}

.card-correction--prominent {
  border-block-start-color: var(--mangthit-500);
  border-block-start-width: 2px;
  background: transparent;
  box-shadow: none;
}

.correction-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: var(--space-3);
  flex-wrap: wrap;
}
.correction-card-header .card-icon {
  margin-bottom: 0;
}

.ombudsman-tag {
  font-family: var(--font-sans);
  font-size: var(--text-2xs);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: var(--tracking-caps);
  color: var(--mangthit-500);
  background: color-mix(in srgb, var(--mangthit-500) 10%, transparent);
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-pill, 999px);
  border: 1px solid color-mix(in srgb, var(--mangthit-500) 24%, transparent);
}

.card-ombudsman-desc {
  font-size: var(--text-xs);
  color: var(--ink-secondary);
  line-height: var(--leading-snug);
  margin-bottom: var(--space-3);
}

.correction-actions {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-wrap: wrap;
}

.contact-card .card-note a {
  display: inline-flex;
  align-items: center;
  min-height: 44px;
}

@media (min-width: 640px) {
  /* Intentional hierarchy: primary claim and correction cards full-width, then a row of
     actionable cards (general + partner), then a row of informational
     cards (report + privacy). 6-col base lets thirds & halves coexist. */
  .contact-cards {
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    gap: var(--space-5);
  }
  .card-claim, .card-correction { grid-column: 1 / -1; }
  .card-general, .card-partner { grid-column: span 3; }
  .card-report, .card-privacy { grid-column: span 3; }
}
@media (max-width: 600px) {
  .brand-masthead { flex-direction: column; text-align: center; padding-block: var(--space-6); }
  .bm-inner { max-width: none; }
  .bm-sla { display: inline-flex; }
}

/* Focus & accessibility */
.contact-card a:focus-visible, .card-action .btn:focus-visible { outline: 2px solid var(--color-focus); outline-offset: 3px; border-radius: var(--radius-control); }
.card-action .btn { transition: transform .35s var(--ease-out-expo), box-shadow .35s var(--ease-out-expo), background .3s var(--ease-out); }
.card-action .btn:hover { transform: translateY(-1px); box-shadow: var(--shadow-sm); }
.card-action .btn:active { transform: scale(.96); transition-duration: .08s; }

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .contact-card:hover,
  .contact-card:active,
  .contact-card:hover .card-icon,
  .contact-card:hover .card-icon-vector,
  .card-action .btn:hover,
  .card-action .btn:active {
    transform: none;
  }
}
</style>
