<template>
  <section class="legal-page about-page" data-color-system="tri-region-v1">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Giới thiệu' }]" :json-ld="true" />

    <!-- Brand masthead — river→clay wash, unique to this page family. -->
    <section class="brand-masthead about-masthead">
      <div class="bm-inner">
        <div class="bm-header-seal">
          <p class="bm-eyebrow"><span class="bm-tick" aria-hidden="true"></span>Về vinhlong360</p>
          <SourceMark tier="official" />
        </div>
        <h1>{{ doc.title }}</h1>
        <p class="bm-sub">Vĩnh Long không thiếu chỗ để đi. Cái thiếu là người kể cho bạn nghe vì sao nên ghé.</p>
      </div>
      <svg class="bm-motif" viewBox="0 0 160 120" aria-hidden="true" focusable="false">
        <path class="bm-river" d="M4 78 Q40 58 80 74 T156 66" fill="none" stroke-width="2" stroke-linecap="round" />
        <path class="bm-river bm-river--2" d="M4 96 Q44 80 84 92 T156 86" fill="none" stroke-width="1.4" stroke-linecap="round" />
        <path d="M56 68 q10-8 22 0 l-2 7 h-18 z" fill="none" stroke-width="1.6" stroke-linejoin="round" />
        <circle cx="118" cy="40" r="2.4" />
        <circle cx="130" cy="34" r="2.4" />
        <circle cx="142" cy="40" r="2.4" />
      </svg>
    </section>

    <p class="legal-updated">Cập nhật: {{ doc.updated_date }}</p>
    <div class="legal-body about-intro editorial-body drop-cap" v-html="introHtml"></div>

    <article
      v-for="(s, i) in doc.sections"
      :key="i"
      class="legal-section about-section reveal sediment-head"
      :class="{
        'highlight-badge': i < 3,
        'mission-section': i === 0,
        'noncommercial-section': i === 2,
        'tint-alt': i % 2 === 1,
      }"
    >
      <span class="about-section-num" aria-hidden="true">{{ String(i + 1).padStart(2, '0') }}</span>
      <div class="about-section-content">
        <template v-if="i === 0">
          <h2>{{ stripNum(s.heading) }}</h2>
          <blockquote class="pull-quote about-mission-quote">
            {{ missionQuote }}
            <cite>— Sứ mệnh vinhlong360</cite>
          </blockquote>
          <div class="legal-body" v-html="cleanBody(missionRest)"></div>
        </template>
        <template v-else>
          <h2>{{ stripNum(s.heading) }}</h2>
          <div class="legal-body" v-html="cleanBody(s.body)"></div>
        </template>
      </div>
    </article>

    <!-- Ban biên tập & Tôn chỉ biên tập — E-E-A-T, Tuyên ngôn độc lập, Quy trình thẩm định 3 tầng & Kiểm chứng thực địa minh bạch -->
    <article id="ban-bien-tap" class="editors-infobox reveal">
      <div class="about-section-content">
        <h2><IconLine name="shield-check" /> Tôn chỉ biên tập &amp; Phương pháp thẩm định thông tin</h2>
        <div class="legal-body">
          <p>Nội dung trên vinhlong360 do <strong>Ban biên tập vinhlong360</strong> độc lập xây dựng và quản trị. Chúng tôi theo đuổi sứ mệnh <strong>phi thương mại bảo tồn di sản và văn hóa sông nước Cửu Long</strong>: không thu phí xếp hạng điểm đến, không bán tour du lịch, không nhận quảng cáo ẩn làm sai lệch thông tin bản địa, và không làm trung gian thương mại.</p>

          <h3>1. Quy trình thẩm định dữ liệu 3 tầng (3-Tier Fact-Checking)</h3>
          <p>Mỗi mục thông tin về di tích, làng nghề, danh nhân và sản vật OCOP đều được đối chiếu qua 3 tầng thẩm định độc lập:</p>
          <ul>
            <li><strong>Tầng 1 (Nguồn thẩm quyền Nhà nước &amp; Pháp lý):</strong> Cổng thông tin điện tử UBND tỉnh và 124 xã/phường mới (<code>.gov.vn</code>), Cục Di sản Văn hóa, hồ sơ xếp hạng di tích lịch sử - văn hóa các cấp và các quyết định công nhận OCOP chính thức.</li>
            <li><strong>Tầng 2 (Khảo cứu địa chí &amp; Học thuật chuyên sâu):</strong> Tư liệu từ Viện Khoa học Xã hội vùng Nam Bộ, Địa chí Vĩnh Long, công trình nghiên cứu văn hóa dân gian Nam Bộ. Dữ liệu chỉ có một nguồn yếu hoặc không rõ xuất xứ sẽ bị loại bỏ thay vì phỏng đoán.</li>
            <li><strong>Tầng 3 (Kiểm chứng thực địa &amp; Nhân chứng bản xứ):</strong> Khảo sát trực tiếp của ban biên tập, ghi nhận tọa độ vệ tinh GPS chính xác, phỏng vấn nghệ nhân lão thành, đại diện hợp tác xã và tiếp thu ý kiến đối chứng từ cộng đồng cư dân địa hạt.</li>
          </ul>

          <h3>2. Minh bạch kiểm chứng thực địa &amp; Nhãn SourceMark</h3>
          <p><strong>“Kiểm chứng thực địa”</strong> chỉ được công nhận khi người của ban biên tập đã trực tiếp khảo sát tận nơi và xác nhận trạng thái thực tế. Nhãn <SourceMark tier="official" compact /> chỉ gắn mốc thời gian ISO <code>attributes.verifiedAt</code> khi việc kiểm chứng đã hoàn tất tại chỗ. Những địa điểm đang trong lộ trình xác thực đều được ghi chú công khai là <em>“Chưa kiểm chứng thực địa”</em> — chúng tôi không che giấu mức độ hoàn thiện của dữ liệu.</p>
          <p>Tuân thủ chính sách dữ liệu chân thực (Unavailable Policy per CLAUDE.md §1.7): khi chưa có dữ liệu thời gian thực hoặc số liệu ngoại vi, hệ thống thực hiện sụp đổ thanh lịch (graceful collapse), tuyệt đối không dựng khung rỗng hoặc bịa đặt số liệu thống kê ảo.</p>

          <h3>3. Tiếp nhận hiệu đính &amp; Trách nhiệm giải trình</h3>
          <p>Phát hiện thông tin sai sót hoặc có tư liệu bổ sung? Du khách và cư dân có thể gửi hồ sơ qua <NuxtLink to="/yeu-cau/sua-thong-tin">Cổng tiếp nhận hiệu đính thông tin</NuxtLink> để nhận mã biên nhận tra cứu độc lập theo dõi tiến độ, hoặc <NuxtLink to="/lien-he">liên hệ trực tiếp ban biên tập</NuxtLink> — người thật trực tiếp tiếp nhận và xử lý, không sử dụng chatbot tự động.</p>
        </div>
      </div>
    </article>

    <CatalogAeoPlaque
      kicker="Tôn chỉ biên tập · Sứ mệnh độc lập"
      title="Tôn chỉ số hóa di sản & kiến thức bản địa Vĩnh Long"
      accent="river"
      icon="book"
      :entries="aboutAeoEntries"
      cta-to="/huong-dan"
      cta-label="Tìm hiểu cách tham gia đóng góp dữ liệu"
    />

    <!-- declutter-3 T8: province-band 3-glyph → sediment-divider (motif phù-sa giữ)
         + 1 dòng narrative đắt nhất; 3 mệnh đề tỉnh đã có trong intro/sections. -->
    <div class="sediment-divider" aria-hidden="true"></div>
    <p class="merge-tagline reveal">Sáp nhập trên bản đồ. Chưa từng sáp nhập trong lòng người.</p>

    <!-- Closing band: About page should never dead-end. -->
    <section class="about-cta reveal">
      <NuxtLink to="/dia-diem" class="btn btn-primary">Xem hành trình mẫu</NuxtLink>
      <NuxtLink to="/lien-he" class="btn btn-outline">Liên hệ với chúng tôi</NuxtLink>
    </section>
  </section>
</template>

<script setup lang="ts">
import { mdLite } from '~/utils/mdLite'
import { ABOUT_PAGE, mergeAboutDoc } from '~/utils/legalContent'

useReveal()
const { get } = useSiteSettings()
const doc = computed(() => mergeAboutDoc(get('page.about', {}), ABOUT_PAGE))
const introHtml = computed(() => cleanBody(doc.value.intro))

function cleanBody(body?: string) {
  if (!body) return ''
  // Strip raw emojis to comply with anti-slop rules, normalize spaces
  const text = body.replace(/[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}]/gu, '').replace(/[ \t]{2,}/g, ' ')
  return mdLite(text)
}

// Headings carry their own "N. " prefix; the .about-section-num badge already
// shows the order, so strip the inline number to avoid duplicate numbering.
const stripNum = (h: string) => (h || '').replace(/^\s*\d+\.\s*/, '')

// Section 0 (Sứ mệnh) becomes a pull-quote spread: the first paragraph of the
// existing mission body IS the thesis statement already (bolded in-source) —
// pulled out as-is, not invented. Remaining paragraphs stay as supporting body.
// Falls back to the whole body as the quote if content is ever a single block
// (e.g. an admin override with no blank-line break).
const missionQuote = computed(() => {
  const raw = doc.value.sections?.[0]?.body || ''
  const [first] = raw.split(/\n\s*\n/)
  return (first || raw).replace(/\*\*/g, '').trim()
})
const missionRest = computed(() => {
  const raw = doc.value.sections?.[0]?.body || ''
  const parts = raw.split(/\n\s*\n/)
  return parts.slice(1).join('\n\n').trim()
})

const aboutAeoEntries = [
  {
    heading: 'Phi thương mại & Công tâm',
    text: 'VinhLong360 là dự án số hóa văn hóa - du lịch độc lập, không thu tiền vị trí địa điểm, không quảng cáo ẩn và không bán tour du lịch.',
  },
  {
    heading: 'Dữ liệu đa nguồn & Kiểm chứng thực địa',
    text: 'Mỗi điểm đến, làng nghề và sản vật OCOP đều được đối chiếu từ tư liệu địa phương, cổng thông tin chính thống và có lộ trình xác thực thực địa minh bạch.',
  },
  {
    heading: 'Đồng sáng tạo cùng cư dân địa hạt',
    text: 'Chúng tôi tin người kể chuyện hay nhất về Vĩnh Long chính là người dân bản xứ. Hệ thống mở cửa để mọi du khách và cư dân đóng góp, đính chính tri thức.',
  },
]

useSeoMeta({
  title: () => doc.value.seo_title,
  description: () => doc.value.seo_description,
  ogTitle: () => doc.value.seo_title,
  ogDescription: () => doc.value.seo_description,
  ogUrl: () => canonicalUrl('/gioi-thieu'),
  twitterCard: 'summary_large_image',
})

// Schema.org unified @graph: '@type': 'AboutPage'
// §1.6: areaServed: ['Vĩnh Long'] (một tỉnh sau sáp nhập 7-2025)
const aboutJsonLd = computed(() => buildAboutPageSchemaGraph({
  title: doc.value.seo_title,
  description: doc.value.seo_description,
  updatedDate: doc.value.updated_date,
}))

useHead(() => ({
  link: [{ rel: 'canonical', href: canonicalUrl('/gioi-thieu') }],
  script: [
    { type: 'application/ld+json', innerHTML: safeJsonLd(aboutJsonLd) },
  ],
}))
</script>

<style src="~/assets/css/legal.css"></style>
<style scoped>
.bm-motif { width: clamp(84px, 9vw + 40px, 140px); height: auto; flex-shrink: 0; color: var(--clay-400); opacity: .85; }
.bm-motif path, .bm-motif circle { stroke: currentColor; fill: none; }
.bm-motif circle { fill: currentColor; stroke: none; }
.bm-river { stroke-dasharray: 6 5; }
.bm-river--2 { opacity: .6; }

.legal-updated { color: var(--ink-tertiary); font-size: var(--text-sm); margin-bottom: var(--space-6); }
.about-intro { margin-bottom: var(--space-8); }

/* ── Section rhythm: open editorial chapter spreads ──────────────────── */
.about-section {
  display: flex;
  align-items: flex-start;
  gap: var(--space-5);
  margin: var(--space-6) 0 0;
  padding: var(--space-5) 0 0;
  border-block-start: 1px solid var(--line);
}
.about-section.tint-alt { background: transparent; }
.about-section h2 {
  font-size: var(--text-lg);
  margin: 0 0 var(--space-3);
}

/* Sections 1-3 read as open editorial callouts. */
.highlight-badge {
  background: transparent;
  border-block-start: 1.5px solid var(--color-brand);
  padding: var(--space-5) 0 0;
  margin-top: var(--space-6);
}
.highlight-badge.tint-alt { background: transparent; }

/* Section 1 — Mission emphasis (pull-quote spread lives inside). */
.mission-section {
  border-block-start: 2px solid var(--color-action);
  background: transparent;
}
.about-mission-quote { margin: var(--space-4) 0 var(--space-5); }
.about-mission-quote :deep(cite) { font-style: normal; }

/* Section 3 — Non-commercial trust signal. */
.noncommercial-section :deep(.legal-body > p:first-child) { font-weight: var(--weight-semibold); color: var(--color-brand); }
.noncommercial-section :deep(.legal-body ul) { list-style: none; padding-inline-start: 0; }
.noncommercial-section :deep(.legal-body li) { position: relative; padding-inline-start: var(--space-6); }
.noncommercial-section :deep(.legal-body li)::before {
  content: '';
  position: absolute;
  inset-inline-start: 0.25em;
  top: 0.42em;
  width: 0.3em;
  height: 0.58em;
  border: 0 solid var(--color-action);
  border-inline-end-width: 2px;
  border-block-end-width: 2px;
  transform: rotate(45deg);
}

/* ── declutter-3 T8: province-band → sediment-divider + merge-tagline ─
   (divider rule copy từ cong-dong — pattern 3-hairline river→amber→clay;
   .editors-infobox = trình bày compact cho khối Ban-biên-tập, nội dung giữ) */
.sediment-divider {
  position: relative; margin-top: var(--space-8); height: 7px;
  background:
    linear-gradient(90deg, transparent, var(--color-material-river) 26%, var(--color-material-river) 74%, transparent) top/100% 1px no-repeat,
    linear-gradient(90deg, transparent, var(--color-material-amber) 30%, var(--color-material-amber) 70%, transparent) center/100% 1px no-repeat,
    linear-gradient(90deg, transparent, var(--color-material-clay) 26%, var(--color-material-clay) 74%, transparent) bottom/100% 1.5px no-repeat;
  opacity: .5;
}
.dark .sediment-divider { opacity: .62; }
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; border: 0; }
.merge-tagline {
  font-family: var(--font-editorial); font-style: italic; font-weight: 500;
  font-size: clamp(1.15rem, 1rem + .8vw, 1.5rem);
  color: var(--ink); margin: var(--space-5) 0 var(--space-8); text-align: center; text-wrap: balance;
}
.editors-infobox {
  margin: var(--space-8) 0;
  padding: var(--space-6) 0;
  background: transparent;
  border: 0;
  border-block-start: 2px solid var(--color-brand);
  border-block-end: 1px solid var(--line);
  border-radius: 0;
  box-shadow: none;
}
.editors-infobox h2 {
  display: flex; align-items: center; gap: var(--space-2);
  font-family: var(--font-editorial);
  font-size: var(--text-xl);
  font-weight: 600;
  color: var(--ink);
  margin: 0 0 var(--space-4);
  padding-bottom: var(--space-3);
  border-bottom: 1px solid var(--line);
}
.editors-infobox h3 {
  font-family: var(--font-editorial);
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--ink);
  margin: var(--space-5) 0 var(--space-2);
}
.editors-infobox .legal-body p { font-size: var(--text-sm); line-height: var(--leading-relaxed); }
.editors-infobox .legal-body ul { margin: var(--space-2) 0 var(--space-4); padding-inline-start: var(--space-5); }
.editors-infobox .legal-body li { margin: var(--space-2) 0; font-size: var(--text-sm); }
.editors-infobox .legal-body code { font-family: var(--font-mono); font-size: 0.85em; background: var(--bg-alt); padding: 1px 4px; border-radius: var(--radius-control); }

/* ── Closing CTA — About should never dead-end. ───────────────────── */
.about-cta {
  display: flex; gap: var(--space-3); justify-content: center; flex-wrap: wrap;
  padding-bottom: var(--space-4);
}
.about-cta .btn {
  min-height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: transform .2s var(--ease-out), box-shadow .2s var(--ease-out);
}
.about-cta .btn:active { transform: scale(.97); }
.about-cta .btn:focus-visible { outline: 2px solid var(--color-focus); outline-offset: 2px; }

/* ── Body typography ──────────────────────────────────────────────── */
.legal-page :deep(p) { font-size: var(--text-sm); }
.about-intro :deep(p) { font-size: inherit; color: inherit; }

@media (max-width: 600px) {
  .about-section { flex-direction: column; gap: var(--space-2); }
}

.dark .bm-motif { color: var(--clay-400); opacity: .7; }

@media (prefers-reduced-motion: reduce) {
  .bm-river, .bm-river--2 { animation: none; stroke-dasharray: none; }
  .about-cta .btn:active { transform: none; }
}
</style>
