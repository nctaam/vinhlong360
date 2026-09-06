<template>
  <div class="guide-layout" data-color-system="tri-region-v1">
    <!-- Sidebar TOC (desktop sticky) -->
    <aside class="guide-sidebar" aria-label="Điều hướng hướng dẫn">
      <div class="sidebar-inner">
        <div class="sidebar-search">
          <input v-model="search" type="search" enterkeyhint="search" placeholder="Tìm trong hướng dẫn..." aria-label="Tìm trong hướng dẫn" class="search-input" />
        </div>
        <nav class="sidebar-nav" aria-label="Mục lục hướng dẫn">
          <a href="#bat-dau" class="snav-link" :class="{ active: activeId === 'bat-dau' }" @click.prevent="scrollTo('bat-dau')"><IconLine name="sparkles" /> Bắt đầu nhanh</a>
          <template v-for="s in filteredSections" :key="s.id">
            <a :href="`#${s.id}`" class="snav-link" :class="{ active: activeId === s.id }" @click.prevent="scrollTo(s.id)">
              {{ s.icon }} {{ s.title }}
            </a>
          </template>
          <a href="#khac-phuc" class="snav-link" :class="{ active: activeId === 'khac-phuc' }" @click.prevent="scrollTo('khac-phuc')"><IconLine name="settings" /> Khắc phục sự cố</a>
        </nav>
        <p v-if="search && !filteredSections.length" class="sidebar-empty">Không tìm thấy mục nào.</p>
      </div>
    </aside>

    <!-- Main content -->
    <section class="guide-main">
      <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Hướng dẫn sử dụng' }]" :json-ld="true" />

      <header class="brand-masthead guide-hero">
        <div class="bm-inner">
          <p class="bm-eyebrow"><span class="bm-tick" aria-hidden="true"></span>Cẩm nang</p>
          <h1>Hướng dẫn sử dụng</h1>
          <p class="bm-sub">Cẩm nang đầy đủ mọi tính năng trên vinhlong360 — từ tìm kiếm, bản đồ, lịch trình đến cộng đồng và quản lý tài khoản.</p>
        </div>
        <svg class="bm-motif" viewBox="0 0 120 120" aria-hidden="true" focusable="false">
          <path d="M24 26h72v70a4 4 0 0 1-4 4H28a4 4 0 0 1-4-4Z" fill="none" stroke-width="1.6" stroke-linejoin="round" />
          <line x1="60" y1="26" x2="60" y2="100" stroke-width="1.4" />
          <circle cx="60" cy="18" r="14" fill="none" stroke-width="1.4" />
          <path d="M60 8v20M50 18h20M53 11l14 14M67 11 53 25" stroke-width="1" />
        </svg>
      </header>

      <!-- Mobile TOC (declutter-3 T7: gộp search vào trong details — mobile 2 khối
           xếp chồng → 1; desktop dùng sidebar. Số phần: sections + bắt-đầu + khắc-phục) -->
      <details class="mobile-toc reveal">
        <summary class="mobile-toc-toggle"><IconLine name="list" /> Mục lục ({{ sections.length + 2 }} phần)</summary>
        <div class="mobile-toc-search">
          <input v-model="search" type="search" placeholder="Tìm trong hướng dẫn..." aria-label="Tìm trong hướng dẫn" class="search-input" />
        </div>
        <nav class="mobile-toc-nav" aria-label="Mục lục hướng dẫn">
          <a href="#bat-dau" @click.prevent="scrollTo('bat-dau')"><IconLine name="sparkles" /> Bắt đầu nhanh</a>
          <a v-for="s in sections" :key="s.id" :href="`#${s.id}`" @click.prevent="scrollTo(s.id)">{{ s.icon }} {{ s.title }}</a>
          <a href="#khac-phuc" @click.prevent="scrollTo('khac-phuc')"><IconLine name="settings" /> Khắc phục sự cố</a>
        </nav>
      </details>

      <!-- ==================== BẮT ĐẦU NHANH ==================== -->
      <section id="bat-dau" class="guide-section guide-quickstart reveal sediment-head">
        <h2><span class="gs-icon" aria-hidden="true">🚀</span>Bắt đầu nhanh</h2>
        <p class="section-intro">Lần đầu dùng vinhlong360? Chỉ cần 5 bước để khám phá đầy đủ.</p>
        <ol class="quickstart-steps">
          <li>
            <div class="qs-step">
              <span class="qs-num">1</span>
              <div>
                <strong>Duyệt và tìm kiếm</strong>
                <p>Mở <NuxtLink to="/">trang chủ</NuxtLink>, gõ tên địa điểm trên thanh tìm kiếm hoặc nhấn vào danh mục (Du lịch, Ẩm thực, OCOP...). Không cần đăng ký.</p>
              </div>
            </div>
          </li>
          <li>
            <div class="qs-step">
              <span class="qs-num">2</span>
              <div>
                <strong>Xem chi tiết & lưu yêu thích</strong>
                <p>Nhấn vào bất kỳ địa điểm nào. Xem ảnh, liên hệ, mùa vụ. Nhấn <IconLine name="heart" /> để lưu — danh sách lưu trên trình duyệt, không cần tài khoản.</p>
              </div>
            </div>
          </li>
          <li>
            <div class="qs-step">
              <span class="qs-num">3</span>
              <div>
                <strong>Tạo lịch trình</strong>
                <p>Vào <NuxtLink to="/tao-lich-trinh">Tạo lịch trình</NuxtLink> → chọn điểm dừng từ tab "Đã lưu" → sắp xếp → xem bản đồ tuyến → lưu.</p>
              </div>
            </div>
          </li>
          <li>
            <div class="qs-step">
              <span class="qs-num">4</span>
              <div>
                <strong>Đăng ký tài khoản</strong>
                <p>Nhấn "Đăng nhập" → nhập SĐT → nhận OTP → xong. Mở khoá: viết bài, đánh giá, theo dõi, đồng bộ yêu thích lên cloud.</p>
              </div>
            </div>
          </li>
          <li>
            <div class="qs-step">
              <span class="qs-num">5</span>
              <div>
                <strong>Tham gia cộng đồng</strong>
                <p>Vào <NuxtLink to="/cong-dong">Cộng đồng</NuxtLink> → viết bài đầu tiên → nhận điểm danh tiếng → leo bảng xếp hạng.</p>
              </div>
            </div>
          </li>
        </ol>
        <div class="tip-box">
          <p class="tip-line"><IconLine name="bulb" class="callout-icon" aria-hidden="true" /> Nhấn nút <IconLine name="message" class="inline-chat-icon" aria-hidden="true" /> góc phải dưới bất kỳ trang nào để hỏi trợ lý AI — trả lời ngay về ẩm thực, du lịch, mùa vụ.</p>
        </div>
      </section>

      <!-- ==================== SECTIONS ==================== -->
      <section v-for="s in filteredSections" :key="s.id" :id="s.id" class="guide-section reveal sediment-head">
        <h2><span class="gs-icon" aria-hidden="true">{{ s.icon }}</span>{{ s.title }}</h2>
        <p class="section-intro">{{ s.intro }}</p>

        <!-- Topics -->
        <details v-for="t in s.topics" :key="t.title" :id="`${s.id}--${slugify(t.title)}`" class="guide-topic" :open="!search">
          <summary class="topic-summary">
            <span class="topic-icon" aria-hidden="true">{{ t.icon }}</span>
            <span class="topic-title">{{ t.title }}</span>
            <IconLine name="chevron-down" class="topic-chevron" aria-hidden="true" />
          </summary>

          <div class="topic-body">
            <p class="topic-desc">{{ t.desc }}</p>

            <!-- Steps -->
            <ol v-if="t.steps?.length" class="guide-steps">
              <li v-for="(step, i) in t.steps" :key="i">{{ step }}</li>
            </ol>

            <!-- Sub-topics -->
            <div v-if="t.subtopics?.length" class="subtopics">
              <div v-for="sub in t.subtopics" :key="sub.title" class="subtopic">
                <h3>{{ sub.title }}</h3>
                <p>{{ sub.desc }}</p>
                <ol v-if="sub.steps?.length" class="guide-steps guide-steps--sub">
                  <li v-for="(step, i) in sub.steps" :key="i">{{ step }}</li>
                </ol>
                <div v-if="sub.tips?.length" class="tip-box">
                  <p v-for="(tip, i) in sub.tips" :key="i" class="tip-line"><IconLine name="bulb" class="callout-icon" aria-hidden="true" /> {{ tip }}</p>
                </div>
              </div>
            </div>

            <!-- Tips -->
            <div v-if="t.tips?.length" class="tip-box">
              <p v-for="(tip, i) in t.tips" :key="i" class="tip-line"><IconLine name="bulb" class="callout-icon" aria-hidden="true" /> {{ tip }}</p>
            </div>

            <!-- Warnings -->
            <div v-if="t.warnings?.length" class="warn-box">
              <p v-for="(w, i) in t.warnings" :key="i" class="warn-line"><IconLine name="alert-triangle" class="callout-icon" aria-hidden="true" /> {{ w }}</p>
            </div>

            <!-- Did-you-know -->
            <div v-if="t.didYouKnow" class="dyk-box">
              <p><IconLine name="info" class="callout-icon" aria-hidden="true" /> <strong>Bạn có biết?</strong> {{ t.didYouKnow }}</p>
            </div>

            <!-- Cross-refs -->
            <div v-if="t.seeAlso?.length" class="see-also">
              <span class="see-also-label">Xem thêm:</span>
              <a v-for="ref in t.seeAlso" :key="ref.href" :href="ref.href" class="see-also-link" @click.prevent="scrollTo(ref.href.replace('#', ''))">{{ ref.label }}</a>
            </div>

            <!-- Link -->
            <NuxtLink v-if="t.link" :to="t.link" class="topic-link">
              <span>{{ t.linkLabel || 'Đi tới trang' }}</span>
              <IconLine name="arrow-right" class="topic-link-icon" aria-hidden="true" />
            </NuxtLink>
          </div>
        </details>

        <!-- FAQ -->
        <div v-if="s.faqs?.length" class="faq-block">
          <h3 class="faq-heading">Câu hỏi thường gặp</h3>
          <details v-for="(faq, i) in s.faqs" :key="i" class="faq-item">
            <summary>{{ faq.q }}</summary>
            <p>{{ faq.a }}</p>
          </details>
        </div>
      </section>

      <p v-if="search && !filteredSections.length" class="no-results reveal">
        Không tìm thấy nội dung nào cho "{{ search }}". Thử từ khóa khác hoặc <button type="button" class="link-btn" @click="search = ''">xóa bộ lọc</button>.
      </p>

      <!-- ==================== KHẮC PHỤC SỰ CỐ ====================
           (declutter-3 T7: section Phím-tắt 11-hàng đã bỏ — thao tác đã rải trong
           từng mục; giữ 3 mẹo trọng yếu inline dưới đây) -->
      <section id="khac-phuc" class="guide-section reveal sediment-head">
        <h2><span class="gs-icon" aria-hidden="true">🔧</span>Khắc phục sự cố</h2>
        <p class="section-intro">Gặp vấn đề khi sử dụng? Thử các giải pháp dưới đây trước khi liên hệ hỗ trợ.</p>
        <p class="section-intro"><strong>Mẹo nhanh:</strong> phím <kbd>Esc</kbd> đóng lightbox/chat, phím <kbd>←</kbd> <kbd>→</kbd> (hoặc vuốt) chuyển ảnh, gõ <kbd>@</kbd> khi soạn bài để tag người/địa điểm.</p>

        <details v-for="issue in troubleshooting" :key="issue.title" class="guide-topic" open>
          <summary class="topic-summary">
            <span class="topic-icon" aria-hidden="true">{{ issue.icon }}</span>
            <span class="topic-title">{{ issue.title }}</span>
            <IconLine name="chevron-down" class="topic-chevron" aria-hidden="true" />
          </summary>
          <div class="topic-body">
            <div v-for="(item, i) in issue.items" :key="i" class="troubleshoot-item">
              <p class="ts-symptom"><strong>Triệu chứng:</strong> {{ item.symptom }}</p>
              <p class="ts-cause"><strong>Nguyên nhân:</strong> {{ item.cause }}</p>
              <div class="ts-fix">
                <strong>Cách khắc phục:</strong>
                <ol class="guide-steps guide-steps--sub">
                  <li v-for="(step, j) in item.fix" :key="j">{{ step }}</li>
                </ol>
              </div>
            </div>
          </div>
        </details>

        <div class="tip-box" style="margin-top: var(--space-4);">
          <p class="tip-line"><span aria-hidden="true">💡</span> Nếu vẫn gặp sự cố, liên hệ qua trang <NuxtLink to="/lien-he">Liên hệ</NuxtLink> — mô tả lỗi, trình duyệt và thiết bị đang dùng.</p>
        </div>
      </section>

      <!-- declutter-3 T7: CTA band đã bỏ — thay 1 dòng hỗ trợ -->
      <p class="guide-support-line">Cần thêm giúp đỡ? <NuxtLink to="/lien-he">Liên hệ hỗ trợ</NuxtLink> · <NuxtLink to="/huong-dan-thanh-vien">Hệ thống cấp bậc &amp; điểm</NuxtLink></p>

      <p class="guide-updated">Cập nhật: {{ updatedDate }}</p>
    </section>
  </div>
</template>

<script setup lang="ts">
import {
  guideSections as sections,
  guideTroubleshooting as troubleshooting,
  getCoreGuideFaqs,
  type GuideSection as Section,
} from '~/utils/guideContent'

useReveal()

const updatedDate = '26/06/2026'
const search = ref('')
const activeId = ref('')

function slugify(s: string) {
  return s.toLowerCase().replace(/[^a-z0-9À-ɏ]+/gi, '-').replace(/(^-|-$)/g, '')
}

function scrollTo(id: string) {
  const el = document.getElementById(id)
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'start' })
    history.replaceState(null, '', `#${id}`)
  }
}

// Intersection Observer for active section tracking
onMounted(() => {
  if (typeof IntersectionObserver === 'undefined') return
  const ids = ['bat-dau', ...sections.map(s => s.id), 'khac-phuc']
  const observer = new IntersectionObserver(
    entries => {
      for (const e of entries) {
        if (e.isIntersecting) { activeId.value = e.target.id; break }
      }
    },
    { rootMargin: '-80px 0px -60% 0px', threshold: 0 }
  )
  for (const id of ids) {
    const el = document.getElementById(id)
    if (el) observer.observe(el)
  }
  onUnmounted(() => observer.disconnect())
})

const filteredSections = computed(() => {
  if (!search.value.trim()) return sections
  const q = search.value.toLowerCase()
  return sections
    .map(s => {
      const topics = s.topics.filter(t =>
        t.title.toLowerCase().includes(q) ||
        t.desc.toLowerCase().includes(q) ||
        t.steps?.some(st => st.toLowerCase().includes(q)) ||
        t.subtopics?.some(sub => sub.title.toLowerCase().includes(q) || sub.desc.toLowerCase().includes(q))
      )
      if (
        s.title.toLowerCase().includes(q) ||
        s.intro.toLowerCase().includes(q) ||
        s.faqs?.some(f => f.q.toLowerCase().includes(q) || f.a.toLowerCase().includes(q)) ||
        topics.length
      ) {
        return { ...s, topics: topics.length ? topics : s.topics }
      }
      return null
    })
    .filter(Boolean) as Section[]
})

useSeoMeta({
  title: 'Hướng dẫn sử dụng — vinhlong360',
  description: 'Cẩm nang đầy đủ cách sử dụng vinhlong360: tìm kiếm, bản đồ, lịch trình, cộng đồng, chat AI, cài đặt tài khoản và nhiều tính năng khác.',
  ogTitle: 'Hướng dẫn sử dụng — vinhlong360',
  ogDescription: 'Cẩm nang đầy đủ cách sử dụng vinhlong360: tìm kiếm, bản đồ, lịch trình, cộng đồng, chat AI, cài đặt tài khoản và nhiều tính năng khác.',
  ogUrl: () => canonicalUrl('/huong-dan'),
  ogType: 'website',
  twitterCard: 'summary_large_image',
})

// Schema.org unified @graph: WebPage, Organization, WebSite, FAQPage (no BreadcrumbList duplicate)
const guideSchema = computed(() =>
  buildGuideSchemaGraph({
    title: 'Hướng dẫn sử dụng vinhlong360',
    description: 'Cẩm nang đầy đủ cách sử dụng vinhlong360: tìm kiếm, bản đồ, lịch trình, cộng đồng, chat AI, cài đặt tài khoản và nhiều tính năng khác.',
    faqs: getCoreGuideFaqs(),
  })
)

useHead({
  link: [{ rel: 'canonical', href: canonicalUrl('/huong-dan') }],
  script: [
    {
      type: 'application/ld+json',
      innerHTML: safeJsonLd(guideSchema.value),
    },
  ],
})
</script>

<style scoped>
/* Layout: sidebar + main */
.guide-layout { display: flex; gap: var(--space-6); max-width: 1100px; margin: 0 auto; padding: var(--space-4); }
.guide-main { flex: 1; min-width: 0; max-width: 820px; }

/* Sidebar */
.guide-sidebar { width: 240px; flex-shrink: 0; }
.sidebar-inner { position: sticky; top: 72px; max-height: calc(100vh - 88px); overflow-y: auto; padding: var(--space-3) 0; }
.sidebar-search { margin-bottom: var(--space-3); }
.search-input {
  width: 100%; padding: var(--space-2) var(--space-3);
  border: 1px solid var(--line); border-radius: var(--radius-surface);
  font-size: var(--text-sm); background: var(--card); color: var(--ink);
  outline: none; transition: border-color .15s;
}
.search-input:focus { border-color: var(--color-action); }
.search-input:focus-visible { outline: 2px solid var(--color-focus); outline-offset: 1px; }
.sidebar-nav { display: flex; flex-direction: column; gap: 1px; }
.snav-link {
  display: block; padding: var(--space-2) var(--space-3);
  font-size: var(--text-xs); color: var(--muted); text-decoration: none;
  border-radius: var(--radius-control); transition: background .15s, color .15s;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.snav-link:hover { background: var(--bg-warm); color: var(--ink); }
.snav-link:focus-visible { outline: 2px solid var(--color-focus); outline-offset: 2px; }
.snav-link.active { background: rgba(var(--color-action-rgb), .1); color: var(--color-action); font-weight: var(--weight-semibold); }
.sidebar-empty { font-size: var(--text-xs); color: var(--muted); padding: var(--space-2) var(--space-3); }

/* Mobile TOC (declutter-3 T7: search gộp vào trong details) */
.mobile-toc { display: none; }
.mobile-toc-search { padding: var(--space-2) var(--space-3) var(--space-1); }

/* Hero — brand-masthead treatment: river→clay wash, serif h1, SVG cẩm-nang
   motif, unique to this page family (matches Giới thiệu/Liên hệ masthead). */
.guide-hero.brand-masthead {
  position: relative; overflow: clip; isolation: isolate;
  display: flex; align-items: center; gap: var(--space-6);
  padding: var(--space-7) var(--space-6); margin-bottom: var(--space-6);
  background:
    var(--grain),
    linear-gradient(120deg, color-mix(in srgb, var(--river-600) 14%, transparent) 0%, var(--bg-warm) 55%, rgba(var(--color-brand-rgb), .14) 120%);
  background-blend-mode: overlay, normal;
  border-radius: var(--radius-sheet); border: .5px solid var(--line);
}
.bm-inner { flex: 1 1 auto; min-width: 0; max-width: var(--measure-read); }
.bm-eyebrow {
  display: flex; align-items: center; gap: var(--space-2);
  font-family: var(--font-sans); font-size: var(--text-2xs); font-weight: 700;
  text-transform: uppercase; letter-spacing: var(--tracking-caps);
  color: var(--color-brand); margin: 0 0 var(--space-2);
}
.bm-tick { width: 14px; height: 1.5px; background: var(--accent, var(--amber-500)); flex-shrink: 0; }
.guide-hero h1 {
  font-family: var(--font-editorial); font-weight: 600;
  margin: 0 0 var(--space-1); font-size: var(--text-2xl); letter-spacing: var(--tracking-tight);
  color: var(--ink);
}
.bm-sub { margin: 0; color: var(--muted); font-size: var(--text-sm); line-height: var(--leading-relaxed); max-width: 60ch; }
.bm-motif { width: clamp(64px, 6vw + 36px, 104px); height: auto; flex-shrink: 0; color: var(--clay-400); opacity: .8; }
.bm-motif path, .bm-motif line, .bm-motif circle { stroke: currentColor; fill: none; }

/* Quickstart */
.quickstart-steps { list-style: none; padding: 0; margin: 0 0 var(--space-4); counter-reset: none; }
.quickstart-steps > li + li { margin-top: var(--space-3); }
.qs-step { display: flex; gap: var(--space-3); align-items: flex-start; padding: var(--space-4); background: var(--card); border: .5px solid var(--line); border-radius: var(--radius-sheet); }
.qs-num {
  width: 2.2rem; height: 2.2rem; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  background: var(--color-brand); color: var(--color-on-action, var(--white)); font-weight: var(--weight-bold);
  font-size: var(--text-base); border-radius: 50%;
}
.qs-step strong { display: block; margin-bottom: var(--space-1); font-size: var(--text-sm); }
.qs-step p { margin: 0; font-size: var(--text-sm); color: var(--muted); line-height: var(--leading-relaxed); }

/* Sections — h2 typography (serif + tick) now comes from .sediment-head;
   keep only spacing/rule here. */
.guide-section { margin-bottom: var(--space-8); scroll-margin-top: calc(var(--header-h) + 0.5rem); }
.guide-section > h2 {
  display: flex; align-items: center;
  font-size: var(--text-xl); margin: 0 0 var(--space-2);
  padding-bottom: var(--space-2); border-bottom: .5px solid var(--line);
}
.gs-icon { font-size: 1.15em; margin-right: var(--space-2); line-height: 1; }
.section-intro { color: var(--muted); font-size: var(--text-sm); line-height: var(--leading-relaxed); margin: 0 0 var(--space-5); }

/* Topics (collapsible) */
.guide-topic {
  margin-bottom: var(--space-3); border: .5px solid var(--line);
  border-radius: var(--radius-sheet); background: var(--card); overflow: hidden;
  scroll-margin-top: calc(var(--header-h) + 0.5rem);
}
.topic-summary {
  display: flex; align-items: center; gap: var(--space-2);
  padding: var(--space-4); cursor: pointer; list-style: none;
  font-size: var(--text-sm); font-weight: var(--weight-bold);
  user-select: none;
}
.topic-summary::-webkit-details-marker { display: none; }
.topic-icon { font-size: 1.3rem; flex-shrink: 0; }
.topic-title { flex: 1; }
.topic-chevron { width: 14px; height: 14px; color: var(--muted); transition: transform .2s var(--ease-out-expo); flex-shrink: 0; }
.guide-topic[open] > .topic-summary .topic-chevron { transform: rotate(180deg); }
.topic-body { padding: 0 var(--space-4) var(--space-4); }
.topic-desc { color: var(--muted); font-size: var(--text-sm); line-height: var(--leading-relaxed); margin: 0 0 var(--space-3); }

/* Steps */
.guide-steps {
  margin: var(--space-3) 0; padding: 0 0 0 var(--space-5);
  font-size: var(--text-sm); line-height: var(--leading-relaxed);
  counter-reset: step; list-style: none;
}
.guide-steps > li {
  position: relative; padding: var(--space-2) 0 var(--space-2) var(--space-5);
  counter-increment: step;
}
.guide-steps > li::before {
  content: counter(step);
  position: absolute; left: 0; top: var(--space-2);
  width: 1.5rem; height: 1.5rem; border-radius: 50%;
  background: var(--color-brand); color: var(--color-on-action, var(--white));
  font-size: var(--text-xs); font-weight: var(--weight-bold);
  display: flex; align-items: center; justify-content: center;
}
.guide-steps--sub > li::before { background: var(--muted); }
.guide-steps > li + li { border-top: .5px dashed var(--line); }

/* Subtopics */
.subtopics { margin: var(--space-3) 0; }
.subtopic {
  padding: var(--space-3) var(--space-4);
  margin-bottom: var(--space-3); background: var(--bg-warm);
  border: 1px solid var(--line);
  box-shadow: inset 3px 0 0 var(--color-brand);
  border-radius: var(--radius-surface);
}
/* WCAG 1.3.1 fix: was h4, skipping h3 under the section's h2 — bumped to h3
   (font-size/weight/margin unchanged, so no visual difference from the level bump). */
.subtopic > h3 { font-size: var(--text-sm); font-weight: var(--weight-bold); margin: 0 0 var(--space-1); }
.subtopic > p { font-size: var(--text-sm); color: var(--muted); margin: 0; line-height: var(--leading-relaxed); }

/* Tip, Warn, DYK, See-also */
.tip-box, .warn-box, .dyk-box {
  margin-top: var(--space-3); padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-sheet); font-size: var(--text-sm);
}
.tip-box { background: rgba(var(--color-action-rgb), .06); border: .5px solid rgba(var(--color-action-rgb), .15); }
.warn-box { background: rgba(var(--warning-rgb), .06); border: .5px solid rgba(var(--warning-rgb), .2); }
.dyk-box { background: rgba(var(--blue-rgb), .06); border: .5px solid rgba(var(--blue-rgb), .15); }
.tip-line, .warn-line { margin: 0; line-height: var(--leading-relaxed); color: var(--ink); }
.tip-line + .tip-line, .warn-line + .warn-line { margin-top: var(--space-2); }
.dyk-box p { margin: 0; line-height: var(--leading-relaxed); }
.callout-icon { margin-right: var(--space-1); vertical-align: -0.15em; font-size: 1.1em; }
.tip-box .callout-icon { color: var(--color-material-amber); }
.warn-box .callout-icon { color: var(--color-material-clay); }
.dyk-box .callout-icon { color: var(--color-material-river); }

.inline-chat-icon { width: 15px; height: 15px; vertical-align: -0.15em; color: var(--color-action); margin: 0 2px; }

.see-also { margin-top: var(--space-3); display: flex; flex-wrap: wrap; gap: var(--space-2); align-items: center; font-size: var(--text-xs); }
.see-also-label { color: var(--muted); font-weight: var(--weight-semibold); }
.see-also-link { color: var(--color-action); text-decoration: none; padding: 2px var(--space-2); background: rgba(var(--color-action-rgb), .06); border-radius: var(--radius-control); }
.see-also-link:hover { text-decoration: underline; }

.topic-link {
  display: inline-flex; align-items: center; gap: var(--space-1); margin-top: var(--space-3);
  font-size: var(--text-sm); font-weight: var(--weight-semibold);
  color: var(--color-action); text-decoration: none;
}
.topic-link:hover { text-decoration: underline; }
.topic-link-icon { width: 14px; height: 14px; transition: transform .2s var(--ease-out-expo); }
.topic-link:hover .topic-link-icon { transform: translateX(3px); }
@media (prefers-reduced-motion: reduce) {
  .topic-link:hover .topic-link-icon { transform: none; }
}

/* FAQ */
.faq-block { margin-top: var(--space-4); }
.faq-heading {
  font-size: var(--text-sm); font-weight: var(--weight-semibold);
  color: var(--muted); text-transform: uppercase; letter-spacing: .05em;
  margin: 0 0 var(--space-3);
}
.faq-item {
  border: .5px solid var(--line); border-radius: var(--radius-sheet);
  margin-bottom: var(--space-2); overflow: hidden;
}
.faq-item > summary {
  padding: var(--space-3) var(--space-4); cursor: pointer;
  font-size: var(--text-sm); font-weight: var(--weight-semibold);
  list-style: none; display: flex; align-items: center; gap: var(--space-2);
}
.faq-item > summary::before { content: '▸'; transition: transform .2s; flex-shrink: 0; }
.faq-item[open] > summary::before { transform: rotate(90deg); }
.faq-item > summary::-webkit-details-marker { display: none; }
.faq-item > p {
  padding: 0 var(--space-4) var(--space-4); margin: 0;
  font-size: var(--text-sm); color: var(--muted); line-height: var(--leading-relaxed);
}

/* Troubleshoot items */
.troubleshoot-item { padding: var(--space-3) 0; }
.troubleshoot-item + .troubleshoot-item { border-top: .5px dashed var(--line); }
.ts-symptom, .ts-cause { font-size: var(--text-sm); margin: 0 0 var(--space-1); }
.ts-fix { font-size: var(--text-sm); }
.ts-fix > strong { display: block; margin-bottom: var(--space-1); }

/* No results */
.no-results { text-align: center; padding: var(--space-8); color: var(--muted); font-size: var(--text-sm); }
.no-results a { color: var(--color-action); }

.guide-support-line { text-align: center; color: var(--muted); font-size: var(--text-sm); margin-top: var(--space-6); }
.guide-support-line a { color: var(--color-action); }

.guide-updated { text-align: center; color: var(--ink-tertiary); font-size: var(--text-xs); margin-top: var(--space-6); }

/* Dark */
.dark .guide-hero.brand-masthead {
  background:
    var(--grain),
    linear-gradient(120deg, color-mix(in srgb, var(--river-legacy-dark) 10%, transparent) 0%, rgba(var(--white-rgb),.02) 55%, rgba(var(--color-brand-rgb), .1) 120%);
}
.dark .bm-motif { color: var(--clay-400); opacity: .65; }
.dark .guide-topic { background: var(--bg-alt); }
.dark .qs-step { background: var(--bg-alt); }
.dark .subtopic { background: rgba(var(--white-rgb),.03); }
.dark .tip-box { background: rgba(var(--white-rgb),.03); border-color: rgba(var(--white-rgb),.08); }
.dark .warn-box { background: rgba(var(--warning-rgb), .05); border-color: rgba(var(--warning-rgb), .12); }
.dark .dyk-box { background: rgba(var(--blue-rgb), .04); border-color: rgba(var(--blue-rgb), .1); }

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .topic-chevron, .faq-item > summary::before { transition: none; }
}

/* Print */
@media print {
  .guide-sidebar, .mobile-toc, .guide-support-line, .topic-chevron, .see-also { display: none; }
  .guide-layout { display: block; max-width: 100%; }
  .guide-hero.brand-masthead { background: none; border: none; padding: 0; }
  .bm-motif { display: none; }
  .guide-topic { border: none; break-inside: avoid; }
  .guide-topic[open] > .topic-summary, .topic-summary { pointer-events: none; }
  .topic-body { display: block !important; }
  .guide-section { break-before: auto; }
}

/* Mobile */
@media (max-width: 900px) {
  .guide-sidebar { display: none; }
  .mobile-toc { display: block; margin-bottom: var(--space-4); }
  .mobile-toc { border: .5px solid var(--line); border-radius: var(--radius-sheet); }
  .mobile-toc-toggle {
    padding: var(--space-3) var(--space-4); cursor: pointer; list-style: none;
    font-size: var(--text-sm); font-weight: var(--weight-semibold);
  }
  .mobile-toc-toggle::-webkit-details-marker { display: none; }
  .mobile-toc-nav {
    display: flex; flex-direction: column; gap: 1px;
    padding: 0 var(--space-3) var(--space-3);
  }
  .mobile-toc-nav a {
    display: block; padding: var(--space-2) var(--space-3);
    font-size: var(--text-sm); color: var(--ink); text-decoration: none;
    border-radius: var(--radius-control);
  }
  .mobile-toc-nav a:hover { background: var(--bg-warm); }
  .guide-layout { padding: var(--space-3); }
  .guide-hero { flex-direction: column; text-align: center; padding: var(--space-5); }
  .guide-hero .bm-inner { max-width: none; }
  .bm-eyebrow { justify-content: center; }
  .qs-step { flex-direction: column; align-items: center; text-align: center; }
  .guide-topic { border-radius: var(--radius-sheet); }
  .topic-body { padding: 0 var(--space-3) var(--space-3); }
  .subtopic { padding: var(--space-2) var(--space-3); }
}
</style>
