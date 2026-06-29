<template>
  <div class="guide-layout">
    <!-- Sidebar TOC (desktop sticky) -->
    <aside class="guide-sidebar" aria-label="Điều hướng hướng dẫn">
      <div class="sidebar-inner">
        <div class="sidebar-search">
          <input v-model="search" type="search" enterkeyhint="search" placeholder="Tìm trong hướng dẫn..." aria-label="Tìm trong hướng dẫn" class="search-input" />
        </div>
        <nav class="sidebar-nav" aria-label="Mục lục hướng dẫn">
          <a href="#bat-dau" class="snav-link" :class="{ active: activeId === 'bat-dau' }" @click.prevent="scrollTo('bat-dau')">🚀 Bắt đầu nhanh</a>
          <template v-for="s in filteredSections" :key="s.id">
            <a :href="`#${s.id}`" class="snav-link" :class="{ active: activeId === s.id }" @click.prevent="scrollTo(s.id)">
              {{ s.icon }} {{ s.title }}
            </a>
          </template>
          <a href="#phim-tat" class="snav-link" :class="{ active: activeId === 'phim-tat' }" @click.prevent="scrollTo('phim-tat')">⌨️ Phím tắt</a>
          <a href="#khac-phuc" class="snav-link" :class="{ active: activeId === 'khac-phuc' }" @click.prevent="scrollTo('khac-phuc')">🔧 Khắc phục sự cố</a>
        </nav>
        <p v-if="search && !filteredSections.length" class="sidebar-empty">Không tìm thấy mục nào.</p>
      </div>
    </aside>

    <!-- Main content -->
    <section class="guide-main">
      <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Hướng dẫn sử dụng' }]" />

      <header class="guide-hero">
        <span class="guide-hero-icon" aria-hidden="true">📖</span>
        <div>
          <h1>Hướng dẫn sử dụng</h1>
          <p>Cẩm nang đầy đủ mọi tính năng trên vinhlong360 — từ tìm kiếm, bản đồ, lịch trình đến cộng đồng và quản lý tài khoản.</p>
        </div>
      </header>

      <!-- Mobile TOC -->
      <details class="mobile-toc reveal">
        <summary class="mobile-toc-toggle">📑 Mục lục ({{ sections.length + 3 }} phần)</summary>
        <nav class="mobile-toc-nav" aria-label="Mục lục hướng dẫn">
          <a href="#bat-dau" @click.prevent="scrollTo('bat-dau')">🚀 Bắt đầu nhanh</a>
          <a v-for="s in sections" :key="s.id" :href="`#${s.id}`" @click.prevent="scrollTo(s.id)">{{ s.icon }} {{ s.title }}</a>
          <a href="#phim-tat" @click.prevent="scrollTo('phim-tat')">⌨️ Phím tắt</a>
          <a href="#khac-phuc" @click.prevent="scrollTo('khac-phuc')">🔧 Khắc phục sự cố</a>
        </nav>
      </details>

      <!-- Mobile search -->
      <div class="mobile-search reveal">
        <input v-model="search" type="search" placeholder="Tìm trong hướng dẫn..." aria-label="Tìm trong hướng dẫn" class="search-input" />
      </div>

      <!-- ==================== BẮT ĐẦU NHANH ==================== -->
      <section id="bat-dau" class="guide-section guide-quickstart reveal">
        <h2>🚀 Bắt đầu nhanh</h2>
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
                <p>Nhấn vào bất kỳ địa điểm nào. Xem ảnh, liên hệ, mùa vụ. Nhấn ❤️ để lưu — danh sách lưu trên trình duyệt, không cần tài khoản.</p>
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
          <p class="tip-line"><span aria-hidden="true">💡</span> Nhấn nút 💬 góc phải dưới bất kỳ trang nào để hỏi trợ lý AI — trả lời ngay về ẩm thực, du lịch, mùa vụ.</p>
        </div>
      </section>

      <!-- ==================== SECTIONS ==================== -->
      <section v-for="s in filteredSections" :key="s.id" :id="s.id" class="guide-section reveal">
        <h2>{{ s.title }}</h2>
        <p class="section-intro">{{ s.intro }}</p>

        <!-- Topics -->
        <details v-for="t in s.topics" :key="t.title" :id="`${s.id}--${slugify(t.title)}`" class="guide-topic" :open="!search">
          <summary class="topic-summary">
            <span class="topic-icon" aria-hidden="true">{{ t.icon }}</span>
            <span class="topic-title">{{ t.title }}</span>
            <span class="topic-chevron" aria-hidden="true">▾</span>
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
                <h4>{{ sub.title }}</h4>
                <p>{{ sub.desc }}</p>
                <ol v-if="sub.steps?.length" class="guide-steps guide-steps--sub">
                  <li v-for="(step, i) in sub.steps" :key="i">{{ step }}</li>
                </ol>
                <div v-if="sub.tips?.length" class="tip-box">
                  <p v-for="(tip, i) in sub.tips" :key="i" class="tip-line"><span aria-hidden="true">💡</span> {{ tip }}</p>
                </div>
              </div>
            </div>

            <!-- Tips -->
            <div v-if="t.tips?.length" class="tip-box">
              <p v-for="(tip, i) in t.tips" :key="i" class="tip-line"><span aria-hidden="true">💡</span> {{ tip }}</p>
            </div>

            <!-- Warnings -->
            <div v-if="t.warnings?.length" class="warn-box">
              <p v-for="(w, i) in t.warnings" :key="i" class="warn-line"><span aria-hidden="true">⚠️</span> {{ w }}</p>
            </div>

            <!-- Did-you-know -->
            <div v-if="t.didYouKnow" class="dyk-box">
              <p><span aria-hidden="true">🎓</span> <strong>Bạn có biết?</strong> {{ t.didYouKnow }}</p>
            </div>

            <!-- Cross-refs -->
            <div v-if="t.seeAlso?.length" class="see-also">
              <span class="see-also-label">Xem thêm:</span>
              <a v-for="ref in t.seeAlso" :key="ref.href" :href="ref.href" class="see-also-link" @click.prevent="scrollTo(ref.href.replace('#', ''))">{{ ref.label }}</a>
            </div>

            <!-- Link -->
            <NuxtLink v-if="t.link" :to="t.link" class="topic-link">
              {{ t.linkLabel || 'Đi tới trang' }} →
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

      <!-- ==================== PHÍM TẮT ==================== -->
      <section id="phim-tat" class="guide-section reveal">
        <h2>⌨️ Phím tắt & Thao tác nhanh</h2>
        <p class="section-intro">Các thao tác giúp sử dụng nhanh hơn trên máy tính và di động.</p>
        <div class="shortcut-table-wrap">
          <table class="shortcut-table" aria-label="Phím tắt và thao tác nhanh">
            <thead>
              <tr><th>Thao tác</th><th>Trên máy tính</th><th>Trên di động</th></tr>
            </thead>
            <tbody>
              <tr v-for="(sc, i) in shortcuts" :key="i">
                <td>{{ sc.action }}</td>
                <td>{{ sc.desktop }}</td>
                <td>{{ sc.mobile }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <!-- ==================== KHẮC PHỤC SỰ CỐ ==================== -->
      <section id="khac-phuc" class="guide-section reveal">
        <h2>🔧 Khắc phục sự cố</h2>
        <p class="section-intro">Gặp vấn đề khi sử dụng? Thử các giải pháp dưới đây trước khi liên hệ hỗ trợ.</p>

        <details v-for="issue in troubleshooting" :key="issue.title" class="guide-topic" open>
          <summary class="topic-summary">
            <span class="topic-icon" aria-hidden="true">{{ issue.icon }}</span>
            <span class="topic-title">{{ issue.title }}</span>
            <span class="topic-chevron" aria-hidden="true">▾</span>
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

      <!-- ==================== CTA ==================== -->
      <section class="guide-cta reveal">
        <h2>Bắt đầu khám phá ngay!</h2>
        <p>Mọi tính năng đều miễn phí. Không cần đăng ký để duyệt — chỉ cần tài khoản khi muốn đóng góp nội dung.</p>
        <div class="cta-btns">
          <NuxtLink to="/" class="btn btn-primary">Về trang chủ</NuxtLink>
          <NuxtLink to="/huong-dan-thanh-vien" class="btn btn-ghost">Hệ thống cấp bậc & điểm</NuxtLink>
        </div>
      </section>

      <p class="guide-updated">Cập nhật: {{ updatedDate }}</p>
    </section>
  </div>
</template>

<script setup lang="ts">
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
  const ids = ['bat-dau', ...sections.map(s => s.id), 'phim-tat', 'khac-phuc']
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

interface SubTopic {
  title: string
  desc: string
  steps?: string[]
  tips?: string[]
}

interface Topic {
  icon: string
  title: string
  desc: string
  steps?: string[]
  subtopics?: SubTopic[]
  tips?: string[]
  warnings?: string[]
  didYouKnow?: string
  seeAlso?: { href: string; label: string }[]
  link?: string
  linkLabel?: string
}

interface FAQ { q: string; a: string }

interface Section {
  id: string
  icon: string
  title: string
  intro: string
  topics: Topic[]
  faqs?: FAQ[]
}

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

const sections: Section[] = [
  // ═══════════════════════════════════════════════════
  // 1. TÌM KIẾM & KHÁM PHÁ
  // ═══════════════════════════════════════════════════
  {
    id: 'tim-kiem',
    icon: '🔍',
    title: 'Tìm kiếm & Khám phá',
    intro: 'Hệ thống tìm kiếm thông minh giúp bạn tìm địa điểm, sản phẩm, bài viết và người dùng chỉ trong vài giây. Hỗ trợ gợi ý khi gõ, tìm không dấu, và lọc theo nhiều tiêu chí.',
    topics: [
      {
        icon: '🔎',
        title: 'Thanh tìm kiếm',
        desc: 'Thanh tìm kiếm nằm trên header mọi trang. Kết quả gợi ý hiện ngay khi bạn gõ (autocomplete) — không cần chờ nhấn Enter.',
        steps: [
          'Nhấn vào thanh tìm kiếm trên header (hoặc ô tìm kiếm lớn trên trang chủ)',
          'Gõ từ khóa — ví dụ: "bánh tráng", "chợ nổi", "homestay"',
          'Danh sách gợi ý hiện ngay dưới thanh tìm kiếm với biểu tượng emoji và tên địa điểm',
          'Nhấn vào kết quả gợi ý để đi thẳng tới trang chi tiết',
          'Hoặc nhấn Enter để mở trang kết quả đầy đủ với bộ lọc',
        ],
        subtopics: [
          {
            title: 'Trang kết quả tìm kiếm',
            desc: 'Khi nhấn Enter, trang kết quả hiển thị với nhiều loại kết quả và bộ lọc nâng cao.',
            steps: [
              'Kết quả được chia theo danh mục: Địa điểm, Sản phẩm, Bài viết cộng đồng, Người dùng',
              'Dùng chip lọc phía trên để thu hẹp theo loại hình (du lịch, ẩm thực, lưu trú, OCOP...)',
              'Dùng chip lọc khu vực (Vĩnh Long, Bến Tre, Trà Vinh) để giới hạn theo vùng',
              'Mỗi kết quả hiển thị dưới dạng card với ảnh, tên, loại, mùa vụ (nếu có)',
            ],
          },
          {
            title: 'Tìm kiếm nhanh trên trang chủ',
            desc: 'Trang chủ có các pill nhanh (Cuối tuần, Ẩm thực, OCOP, Thiên nhiên...) — nhấn vào để tìm ngay theo chủ đề mà không cần gõ.',
          },
          {
            title: 'Trợ lý tìm kiếm AI',
            desc: 'Khi kết quả tìm kiếm không đủ rõ, hệ thống hiện gợi ý "Hỏi trợ lý AI". Nhấn vào để chuyển sang chat AI với câu hỏi đã điền sẵn.',
          },
        ],
        tips: [
          'Gõ tiếng Việt không dấu cũng tìm được — ví dụ "vinh long" sẽ trả kết quả "Vĩnh Long".',
          'Tìm kiếm trên trang chủ và trên header cho cùng kết quả — dùng cái nào tiện hơn.',
          'Phần "Đã xem gần đây" trên trang tìm kiếm giúp quay lại nhanh những địa điểm đã duyệt.',
        ],
        didYouKnow: 'Hệ thống tìm kiếm tổng hợp từ 3 nguồn cùng lúc: cơ sở dữ liệu địa điểm, bài viết cộng đồng, và hồ sơ người dùng — chỉ trong 1 truy vấn.',
        seeAlso: [
          { href: '#cong-cu', label: 'Chat AI' },
          { href: '#ban-do', label: 'Bản đồ' },
        ],
        link: '/tim-kiem',
        linkLabel: 'Mở trang tìm kiếm',
      },
      {
        icon: '📂',
        title: 'Duyệt theo danh mục',
        desc: 'Ngoài tìm kiếm, bạn có thể duyệt qua từng danh mục chuyên đề. Mỗi danh mục có bộ lọc và cách sắp xếp riêng.',
        subtopics: [
          {
            title: 'Du lịch & Trải nghiệm (/du-lich)',
            desc: 'Tất cả điểm tham quan, trải nghiệm, thiên nhiên, lịch sử, làng nghề. Lọc theo 8 loại hình và 12 tháng/mùa lũ.',
            steps: [
              'Truy cập /du-lich hoặc nhấn menu "Khám phá" → "Du lịch & trải nghiệm"',
              'Phần hero hiển thị số liệu thống kê (tổng điểm, đang vào mùa)',
              'Cuộn xuống thấy spotlight (bài viết nổi bật kiểu tạp chí) và hàng scroll ngang các điểm đáng xem',
              'Dùng chip lọc: Tham quan, Trải nghiệm, Thiên nhiên, Lịch sử, Ẩm thực, Làng nghề, Lưu trú, Đặc sản',
              'Dùng chip tháng (1–12) hoặc "Mùa lũ" để lọc theo mùa',
              'Nhấn "Xem thêm" ở cuối danh sách để tải thêm kết quả',
            ],
          },
          {
            title: 'Sản phẩm địa phương (/san-pham)',
            desc: 'Đặc sản, thủ công mỹ nghệ, nông sản theo mùa.',
            steps: [
              'Truy cập /san-pham',
              'Hero hiển thị 3 chỉ số: tổng sản phẩm, số đạt OCOP, số đang vào mùa',
              'Bật nút "Chỉ OCOP" để chỉ xem sản phẩm đã được chứng nhận',
              'Lọc theo tháng để xem sản phẩm theo mùa',
            ],
          },
          {
            title: 'Sản phẩm OCOP (/ocop)',
            desc: 'Trang riêng cho sản phẩm đạt chứng nhận OCOP (Mỗi xã Một sản phẩm) với bộ lọc theo sao.',
            steps: [
              'Truy cập /ocop',
              'Lọc theo hạng sao: 3 sao, 4 sao, hoặc 5 sao',
              'Phần "Vinh danh" hiển thị riêng các sản phẩm 5 sao (biểu tượng vương miện 👑)',
              'Lọc theo khu vực (Vĩnh Long, Bến Tre, Trà Vinh)',
            ],
          },
          {
            title: 'Lễ hội & Sự kiện',
            desc: 'Lễ hội truyền thống theo mùa và sự kiện sắp diễn ra. Truy cập từ menu "Khám phá" → "Lễ hội truyền thống" hoặc "Sự kiện".',
          },
        ],
        tips: [
          'Mỗi danh mục có nút "Xem thêm" hoặc cuộn vô hạn — không bao giờ bị giới hạn số lượng kết quả.',
          'Phần editorial (giới thiệu kiểu tạp chí) ở đầu mỗi danh mục giúp người mới hiểu bối cảnh vùng miền.',
        ],
        didYouKnow: 'Trang Du lịch có chế độ "spotlight" — hiển thị 1 địa điểm nổi bật dạng card lớn giống tạp chí, xoay vòng theo dữ liệu.',
      },
      {
        icon: '🍊',
        title: 'Đặc sản theo mùa',
        desc: 'Trang /theo-mua cho biết tháng hiện tại đang có gì hay, và cho phép xem bất kỳ tháng nào trong năm.',
        steps: [
          'Truy cập /theo-mua — mặc định hiển thị tháng hiện tại',
          'Nhấn vào bất kỳ nút tháng nào (1–12) trên thanh chọn tháng',
          'Phần "Cao điểm" (scroll ngang) hiển thị những sản phẩm/trải nghiệm đúng mùa nhất',
          'Cuộn xuống xem toàn bộ danh sách theo loại hình',
          'Badge mùa trên mỗi card cho biết đây là "đúng mùa" hay "quanh năm"',
        ],
        tips: [
          'Vòng tròn mùa trên hero thay đổi emoji và tagline theo mùa (Xuân, Hè, Thu, Đông, Lũ).',
          'Trang này rất hữu ích khi bạn chưa biết đi đâu — chọn tháng dự kiến đi để xem gợi ý.',
        ],
        seeAlso: [{ href: '#lich-trinh', label: 'Tạo lịch trình từ gợi ý mùa' }],
        link: '/theo-mua',
        linkLabel: 'Xem theo mùa',
      },
      {
        icon: '🧭',
        title: 'Khám phá theo chủ đề',
        desc: 'Bộ sưu tập theo sở thích: Ẩm thực, Thiên nhiên, Văn hóa, Làng nghề, Mua sắm — mỗi chủ đề có giới thiệu editorial và lọc theo khu vực.',
        steps: [
          'Truy cập từ footer hoặc trang chủ → phần "Khám phá"',
          'Chọn chủ đề quan tâm (ví dụ: /kham-pha/am-thuc)',
          'Đọc giới thiệu tổng quan về chủ đề',
          'Duyệt danh sách địa điểm/sản phẩm thuộc chủ đề, lọc theo khu vực',
        ],
        link: '/kham-pha/am-thuc',
        linkLabel: 'Thử khám phá Ẩm thực',
      },
    ],
    faqs: [
      { q: 'Tìm kiếm có hỗ trợ tiếng Anh không?', a: 'Hiện tại nội dung chủ yếu bằng tiếng Việt. Bạn có thể tìm bằng tên riêng tiếng Anh (như "homestay", "Cai Be") và hệ thống sẽ trả kết quả phù hợp.' },
      { q: 'Tại sao một số địa điểm không có ảnh?', a: 'Ảnh chỉ hiển thị khi có nguồn bản quyền hợp lệ (UGC, Pexels, Unsplash). Bạn có thể đóng góp ảnh qua bài viết cộng đồng.' },
      { q: 'Kết quả tìm kiếm có bao gồm bài viết cộng đồng không?', a: 'Có. Trang kết quả đầy đủ (nhấn Enter) hiển thị cả bài viết, đánh giá từ cộng đồng và hồ sơ người dùng.' },
      { q: 'Có bao nhiêu địa điểm trên hệ thống?', a: 'Hiện có hơn 1.700 địa điểm và 9.500 mối quan hệ liên kết, trải rộng Vĩnh Long, Bến Tre, Trà Vinh. Dữ liệu liên tục được bổ sung.' },
    ],
  },

  // ═══════════════════════════════════════════════════
  // 2. BẢN ĐỒ TƯƠNG TÁC
  // ═══════════════════════════════════════════════════
  {
    id: 'ban-do',
    icon: '🗺️',
    title: 'Bản đồ tương tác',
    intro: 'Bản đồ hiển thị hơn 500 địa điểm trên bản đồ tương tác. Lọc theo loại, nhấn vào điểm đánh dấu để xem thông tin nhanh và dẫn tới trang chi tiết.',
    topics: [
      {
        icon: '📍',
        title: 'Xem và điều hướng bản đồ',
        desc: 'Bản đồ dùng MapLibre (mã nguồn mở) với giao diện Việt hóa. Bạn có thể kéo, zoom, và nhấn vào từng điểm.',
        steps: [
          'Truy cập /ban-do hoặc nhấn menu "Khám phá" → "Bản đồ"',
          'Bản đồ hiển thị toàn vùng Vĩnh Long – Bến Tre – Trà Vinh',
          'Kéo để di chuyển, cuộn chuột (hoặc chụm 2 ngón trên di động) để zoom',
          'Mỗi điểm đánh dấu là một biểu tượng emoji tương ứng loại hình',
          'Nhấn vào điểm đánh dấu để mở popup thông tin nhanh',
          'Popup hiển thị: emoji, tên, loại hình, và nút "Xem chi tiết"',
          'Nhấn "Xem chi tiết" để mở trang đầy đủ của địa điểm',
        ],
        subtopics: [
          {
            title: 'Lọc theo loại hình',
            desc: 'Thanh chip lọc phía trên bản đồ cho phép bật/tắt từng loại địa điểm.',
            steps: [
              'Nhấn vào chip để bật/tắt loại: Tham quan, Trải nghiệm, Thiên nhiên, Lịch sử, Ẩm thực, Làng nghề, Lưu trú, Đặc sản',
              'Có thể bật nhiều loại cùng lúc',
              'Số lượng kết quả cập nhật ngay khi thay đổi bộ lọc',
              'Tắt tất cả rồi bật lại loại cần xem để tập trung vào 1 loại',
            ],
          },
          {
            title: 'Nhóm điểm (clustering)',
            desc: 'Khi zoom ra xa, các điểm gần nhau tự động gom thành cụm với số lượng hiển thị trên cụm.',
            steps: [
              'Khi thấy hình tròn có số (ví dụ "12") — đó là cụm gồm 12 điểm',
              'Nhấn vào cụm để zoom vào và tách các điểm ra',
              'Tiếp tục nhấn cho đến khi thấy từng điểm riêng lẻ',
            ],
          },
          {
            title: 'Xem vị trí cụ thể từ trang chi tiết',
            desc: 'Trên trang chi tiết địa điểm, nhấn nút "Xem trên bản đồ" — bản đồ sẽ mở và zoom đến đúng vị trí đó, popup mở sẵn.',
          },
        ],
        tips: [
          'Bản đồ có mã màu theo loại hình — mỗi emoji là 1 loại, dễ nhận biết khi zoom ra.',
          'Trên di động, dùng 2 ngón để zoom và 1 ngón để kéo.',
        ],
        didYouKnow: 'Bản đồ có chế độ screen reader — mỗi thao tác (zoom, lọc, nhấn điểm) đều có thông báo ARIA cho người dùng khiếm thị.',
        seeAlso: [
          { href: '#lich-trinh', label: 'Xem tuyến đường trên bản đồ lịch trình' },
          { href: '#dia-diem', label: 'Xem chi tiết sau khi nhấn điểm' },
        ],
        link: '/ban-do',
        linkLabel: 'Mở bản đồ',
      },
    ],
    faqs: [
      { q: 'Bản đồ có chỉ đường không?', a: 'Bản đồ này hiển thị vị trí. Để xem đường đi, dùng tính năng Lịch trình — hệ thống tính quãng đường và thời gian giữa các điểm dừng, hiển thị polyline trên bản đồ riêng.' },
      { q: 'Bản đồ có hoạt động offline không?', a: 'Không. Bản đồ cần kết nối internet để tải tile bản đồ và dữ liệu điểm đánh dấu.' },
      { q: 'Sao một số địa điểm không hiện trên bản đồ?', a: 'Địa điểm cần có toạ độ GPS (latitude, longitude) mới hiện trên bản đồ. Một số địa điểm chưa được geocode sẽ chỉ hiện trong danh sách.' },
    ],
  },

  // ═══════════════════════════════════════════════════
  // 3. CHI TIẾT ĐỊA ĐIỂM
  // ═══════════════════════════════════════════════════
  {
    id: 'dia-diem',
    icon: '📋',
    title: 'Chi tiết địa điểm',
    intro: 'Mỗi địa điểm có trang riêng với thông tin đầy đủ: ảnh, liên hệ, mùa vụ, bản đồ vị trí, đánh giá cộng đồng, và các địa điểm liên quan.',
    topics: [
      {
        icon: '📸', title: 'Thư viện ảnh',
        desc: 'Ảnh bìa hiển thị ở đầu trang. Nhấn vào để mở lightbox toàn màn hình duyệt tất cả ảnh.',
        steps: ['Nhấn vào ảnh bìa hoặc nút "X ảnh" để mở lightbox', 'Trong lightbox: nhấn ← → (hoặc vuốt trái/phải trên di động) để chuyển ảnh', 'Nhấn Esc hoặc nút ✕ để đóng lightbox', 'Ảnh trong lightbox hiển thị ở chất lượng cao nhất có sẵn'],
        tips: ['Ảnh chỉ dùng nguồn bản quyền hợp lệ. Bạn có thể đóng góp ảnh bằng cách viết bài đánh giá kèm ảnh trong Cộng đồng.'],
      },
      {
        icon: '📞', title: 'Thông tin liên hệ',
        desc: 'Phần đầu trang chi tiết hiển thị các thông tin thiết yếu để liên hệ và ghé thăm.',
        subtopics: [
          { title: 'Số điện thoại & Zalo', desc: 'Nhấn vào số điện thoại trên di động để gọi trực tiếp. Nếu có Zalo, biểu tượng Zalo sẽ hiện bên cạnh.' },
          { title: 'Giờ mở cửa & Giá', desc: 'Nếu địa điểm có thông tin giờ mở cửa hoặc khoảng giá, chúng hiển thị dưới tên. Giá mang tính tham khảo.' },
          { title: 'Bản đồ vị trí nhúng', desc: 'Bản đồ nhỏ hiển thị vị trí chính xác ngay trên trang. Nhấn "Xem trên bản đồ" để mở bản đồ lớn.' },
        ],
        warnings: ['Trang chỉ giới thiệu — KHÔNG có chức năng đặt hàng/booking. Liên hệ trực tiếp cơ sở qua điện thoại hoặc Zalo.'],
      },
      {
        icon: '📅', title: 'Mùa vụ & Thời điểm',
        desc: 'Nhiều địa điểm/sản phẩm có tính mùa. Trang chi tiết hiển thị lưới 12 tháng và gợi ý thời điểm lý tưởng.',
        subtopics: [
          { title: 'Lưới 12 tháng', desc: 'Mỗi ô tháng có mã màu: xanh đậm = cao điểm, xanh nhạt = phù hợp, xám = không mùa. Giúp bạn chọn thời điểm ghé thăm tốt nhất.' },
          { title: 'Badge mùa trên card', desc: 'Trên trang danh mục, card địa điểm hiển thị badge "Đang mùa" nếu tháng hiện tại là tháng cao điểm.' },
        ],
        seeAlso: [{ href: '#tim-kiem--đặc-sản-theo-mùa', label: 'Trang Theo mùa' }],
      },
      {
        icon: '🔗', title: 'Địa điểm liên quan & Lân cận',
        desc: 'Cuối trang chi tiết hiển thị hai phần gợi ý.',
        subtopics: [
          { title: 'Địa điểm liên quan', desc: 'Các địa điểm có mối quan hệ — ví dụ: "Chợ nổi Cái Bè" liên quan đến "Cù lao An Bình" vì cùng tuyến tham quan. Quan hệ do dữ liệu hệ thống quyết định (hơn 9.500 mối quan hệ).' },
          { title: 'Gần đây', desc: 'Các địa điểm khác trong cùng xã/phường hoặc trong bán kính gần — tiện để kết hợp khi đi.' },
        ],
      },
      {
        icon: '❤️', title: 'Lưu yêu thích',
        desc: 'Nhấn nút ❤️ "Lưu" trên trang chi tiết để đánh dấu địa điểm yêu thích.',
        steps: ['Nhấn nút ❤️ trên trang chi tiết bất kỳ địa điểm nào', 'Địa điểm được lưu vào bộ nhớ trình duyệt (không cần đăng nhập)', 'Nếu đã đăng nhập, danh sách yêu thích đồng bộ lên server — xem trên mọi thiết bị', 'Xem lại danh sách trong hồ sơ cá nhân (tab "Đã lưu")', 'Dùng danh sách này làm nguồn khi tạo lịch trình (tab "Đã lưu" trong trình tạo lịch trình)'],
        tips: ['Lưu yêu thích trước khi tạo lịch trình — bạn sẽ có sẵn danh sách để chọn nhanh.', 'Yêu thích hoạt động cả khi chưa đăng nhập (lưu trên trình duyệt). Khi đăng nhập, danh sách tự động gộp và đồng bộ.'],
        didYouKnow: 'Yêu thích dùng cơ chế "fire-and-forget" — nhấn ❤️ xong có thể rời trang ngay, dữ liệu vẫn đồng bộ lên server ở nền.',
        seeAlso: [{ href: '#lich-trinh', label: 'Tạo lịch trình từ yêu thích' }],
      },
      {
        icon: '⭐', title: 'Đánh giá từ cộng đồng',
        desc: 'Phần cuối trang chi tiết hiển thị các bài đánh giá từ thành viên cộng đồng.',
        steps: ['Cuộn xuống phần "Đánh giá" trên trang chi tiết', 'Đọc đánh giá từ người đã đến — kèm ảnh thực tế', 'Nhấn "Viết đánh giá" để đóng góp (cần đăng nhập)', 'Chọn điểm số (1–5 sao), viết nhận xét, đính kèm ảnh nếu có'],
        seeAlso: [{ href: '#cong-dong', label: 'Viết bài & đánh giá trong Cộng đồng' }],
      },
      {
        icon: '🏷️', title: 'JSON-LD & SEO',
        desc: 'Mỗi trang chi tiết có dữ liệu cấu trúc JSON-LD (Schema.org) — khi chia sẻ link lên Zalo, Facebook, Google sẽ hiện ảnh, tên, mô tả đẹp và đầy đủ.',
        didYouKnow: 'Trang chi tiết đạt chuẩn TouristAttraction/LocalBusiness của Google — giúp hiện thông tin phong phú trên kết quả tìm kiếm Google.',
      },
    ],
    faqs: [
      { q: 'Làm sao báo thông tin sai trên trang chi tiết?', a: 'Nhấn nút "Báo sai" (biểu tượng cờ) ở cuối trang — mô tả ngắn gọn thông tin cần sửa. Đội ngũ quản trị sẽ xem xét.' },
      { q: 'Tại sao có địa điểm chưa có mô tả?', a: 'Hệ thống đang được bổ sung dần. Bạn có thể giúp bằng cách viết đánh giá kèm mô tả chi tiết trong cộng đồng.' },
      { q: 'Giá cả có chính xác không?', a: 'Giá mang tính tham khảo và có thể thay đổi. Luôn xác nhận trực tiếp với cơ sở trước khi đến.' },
    ],
  },

  // ═══════════════════════════════════════════════════
  // 4. LỊCH TRÌNH
  // ═══════════════════════════════════════════════════
  {
    id: 'lich-trinh',
    icon: '🗓️',
    title: 'Lịch trình',
    intro: 'Tạo lịch trình du lịch cá nhân hoặc duyệt lịch trình gợi ý sẵn có. Hệ thống tính quãng đường, thời gian di chuyển, và hiển thị trên bản đồ.',
    topics: [
      {
        icon: '📝', title: 'Duyệt lịch trình gợi ý',
        desc: 'Các lịch trình được biên soạn sẵn theo khu vực, phù hợp cho người lần đầu đến.',
        steps: ['Truy cập /lich-trinh', 'Hero hiển thị số lượng lịch trình theo từng khu vực', 'Dùng chip lọc: Vĩnh Long, Bến Tre, Trà Vinh, hoặc Tất cả', 'Nhấn vào card lịch trình để xem chi tiết: các điểm dừng, thời gian, quãng đường', 'Nhấn "Lưu" để lưu vào danh sách cá nhân'],
        subtopics: [
          { title: 'Lịch trình đã lưu', desc: 'Phần đầu trang hiển thị các lịch trình bạn đã lưu (tối đa 8 gần nhất). Nhấn để mở lại, hoặc "Bỏ lưu" để xóa khỏi danh sách. Nút "Xóa tất cả" cần xác nhận trước khi xóa.' },
        ],
        link: '/lich-trinh', linkLabel: 'Xem lịch trình gợi ý',
      },
      {
        icon: '✏️', title: 'Tự tạo lịch trình',
        desc: 'Trình tạo lịch trình 3 bước cho phép bạn chọn điểm dừng, sắp xếp thứ tự, ghi chú, và xem trên bản đồ.',
        steps: ['Truy cập /tao-lich-trinh hoặc nhấn "Tạo lịch trình" từ menu', 'Giao diện chia 2 phần: bên trái là danh sách địa điểm để chọn, bên phải là lịch trình đang xây', 'Chọn tab "Tất cả" (tìm kiếm + lọc) hoặc "Đã lưu" (yêu thích)', 'Nhấn dấu "+" bên cạnh địa điểm để thêm vào lịch trình', 'Sắp xếp thứ tự bằng nút ↑↓ hoặc kéo thả', 'Thêm khung giờ (ví dụ "8:00–9:30") và ghi chú cho từng điểm dừng', 'Đặt tên cho lịch trình bằng cách nhấn vào tiêu đề ở đầu', 'Nhấn "Lưu" để lưu — lịch trình xuất hiện trong mục "Đã lưu" ở /lich-trinh'],
        subtopics: [
          { title: 'Chọn từ danh sách yêu thích', desc: 'Tab "Đã lưu" (bên trái trình tạo) hiển thị những địa điểm bạn đã nhấn ❤️. Đây là cách nhanh nhất để tạo lịch trình.', steps: ['Chuyển sang tab "Đã lưu" trên panel bên trái', 'Nhấn "+" để thêm từng địa điểm yêu thích vào lịch trình', 'Hoặc nhấn "Tạo từ danh sách yêu thích" trên trang /lich-trinh để tự động thêm tất cả'] },
          { title: 'Bản đồ tuyến đường', desc: 'Phía dưới lịch trình hiển thị bản đồ với đường nối giữa các điểm dừng (polyline). Bản đồ cập nhật tự động khi bạn thêm, xóa, hoặc sắp xếp lại.' },
          { title: 'Thanh tiến trình 3 bước', desc: 'Trình tạo có thanh tiến trình: Bước 1 (chọn điểm) → Bước 2 (sắp xếp & ghi chú) → Bước 3 (xem lại & lưu). Bạn có thể quay lại bước trước bất kỳ lúc nào.' },
        ],
        tips: ['Lưu yêu thích trước khi tạo lịch trình — rất tiện!', 'Lịch trình lưu trên trình duyệt. Đăng nhập để đồng bộ và xem trên thiết bị khác.'],
        didYouKnow: 'Hệ thống dùng OSRM (Open Source Routing Machine) để tính đường đi thực tế trên đường bộ — không phải đường chim bay.',
        link: '/tao-lich-trinh', linkLabel: 'Mở trình tạo lịch trình',
      },
      {
        icon: '🚗', title: 'Phương tiện & Khoảng cách',
        desc: 'Chọn phương tiện di chuyển để hệ thống tính quãng đường và thời gian phù hợp.',
        subtopics: [
          { title: 'Ba lựa chọn phương tiện', desc: 'Ô tô, Xe máy, hoặc Xuồng. Nhấn biểu tượng phương tiện trong trình tạo lịch trình để chuyển đổi. Tổng quãng đường và thời gian cập nhật ngay.' },
          { title: 'Khoảng cách giữa các điểm', desc: 'Khoảng cách giữa từng cặp điểm dừng liên tiếp hiển thị trên danh sách. Tổng quãng đường toàn tuyến ở cuối.' },
        ],
      },
      {
        icon: '🔗', title: 'Chia sẻ & Công khai',
        desc: 'Lịch trình đã lưu có thể đặt chế độ công khai hoặc riêng tư.',
        steps: ['Mở lịch trình đã lưu', 'Nhấn nút "Chia sẻ" để sao chép link hoặc mở native share trên di động', 'Gửi link cho bạn bè qua Zalo, Messenger, hoặc mạng xã hội', 'Bật "Công khai" nếu muốn hiện trên trang /lich-trinh cho mọi người'],
      },
    ],
    faqs: [
      { q: 'Có giới hạn số điểm dừng trong lịch trình không?', a: 'Không giới hạn. Nhưng lịch trình 1-2 ngày thường 5-10 điểm là hợp lý.' },
      { q: 'Lịch trình có tính chi phí không?', a: 'Chưa. Hệ thống chỉ tính quãng đường và thời gian di chuyển. Chi phí ăn uống, vé tham quan tùy thuộc từng địa điểm.' },
      { q: 'Sao khoảng cách không chính xác?', a: 'Hệ thống tính theo đường bộ (OSRM), có thể khác thực tế do đường tắt hoặc phà. Khoảng cách mang tính tham khảo.' },
      { q: 'Lịch trình mất khi xóa lịch sử trình duyệt?', a: 'Có, nếu chưa đăng nhập. Khi đăng nhập, lịch trình đồng bộ lên server và không mất khi xóa lịch sử trình duyệt.' },
    ],
  },

  // ═══════════════════════════════════════════════════
  // 5. CỘNG ĐỒNG
  // ═══════════════════════════════════════════════════
  {
    id: 'cong-dong',
    icon: '👥',
    title: 'Cộng đồng',
    intro: 'Mạng xã hội mini dành cho du khách và người bản địa. Chia sẻ trải nghiệm, đánh giá địa điểm, hỏi đáp, và theo dõi nhau.',
    topics: [
      {
        icon: '✍️', title: 'Viết bài',
        desc: 'Đăng bài chia sẻ, đánh giá, hỏi đáp, hoặc giới thiệu — mỗi loại có mục đích khác nhau.',
        steps: ['Truy cập /cong-dong và đăng nhập', 'Nhấn vào ô soạn bài ở đầu trang', 'Chọn loại bài: Chia sẻ, Đánh giá, Hỏi đáp, hoặc Giới thiệu', 'Viết nội dung (tối đa 500 ký tự, bộ đếm hiện ở góc)', 'Đính kèm ảnh: nhấn biểu tượng ảnh, chọn tối đa 5 ảnh', 'Gõ @ để tag người dùng hoặc địa điểm (dropdown gợi ý hiện ra)', 'Nhấn "Đăng" để xuất bản'],
        subtopics: [
          { title: 'Loại bài viết & Điểm', desc: 'Chọn đúng loại để bài hiện đúng nơi và được tính điểm phù hợp.', steps: ['Chia sẻ: Kể chuyện, chia sẻ kinh nghiệm du lịch — 3 điểm/bài', 'Đánh giá: Nhận xét về địa điểm cụ thể, có điểm số 1-5 sao — 5 điểm/bài (10 bài đầu)', 'Hỏi đáp: Đặt câu hỏi cho cộng đồng — 2 điểm', 'Giới thiệu: Giới thiệu địa điểm mới, sản phẩm mới — 3 điểm'] },
          { title: 'Đính kèm ảnh', desc: 'Tối đa 5 ảnh/bài. Ảnh tự động nén (tối đa 1280px, JPEG chất lượng 82%) để tải nhanh mà vẫn rõ nét. Preview hiện trước khi đăng.', tips: ['Đánh giá kèm ảnh được cộng thêm điểm. Ảnh thực tế giúp người khác hình dung rõ hơn.'] },
          { title: 'Nhắc đến (@mention)', desc: 'Gõ @ trong ô soạn → dropdown gợi ý người dùng và địa điểm. Người được tag nhận thông báo.', steps: ['Gõ @ rồi tiếp tục gõ tên (ví dụ: @Nguyên, @Chợ Nổi)', 'Dropdown hiện danh sách khớp — nhấn để chọn', 'Người/địa điểm được tag hiển thị dạng link trong bài'] },
        ],
        tips: ['Bài nháp tự động lưu mỗi 5 giây — nếu thoát trang rồi quay lại, nội dung vẫn còn.', 'Viết đánh giá mang nhiều điểm nhất (5 điểm/bài cho 10 bài đầu, giảm dần sau đó).'],
        didYouKnow: 'Điểm danh tiếng có cơ chế "diminishing returns" — cùng 1 loại đóng góp, bài thứ 10 cho ít điểm hơn bài thứ 1. Đa dạng hóa (viết + đánh giá + ảnh + khám phá) là cách tăng nhanh nhất.',
      },
      {
        icon: '❤️', title: 'Tương tác với bài viết',
        desc: 'Thích, bình luận, lưu, chia sẻ lại — đầy đủ tương tác mạng xã hội.',
        subtopics: [
          { title: 'Thích ❤️', desc: 'Nhấn biểu tượng ❤️ trên bài. Tác giả nhận thông báo. Mỗi lượt thích tính 1 điểm cho tác giả.' },
          { title: 'Bình luận 💬', desc: 'Nhấn biểu tượng 💬 để mở khung bình luận. Gõ và nhấn Enter để gửi. Bình luận cũng hỗ trợ @mention.' },
          { title: 'Lưu bài (bookmark) 🔖', desc: 'Nhấn biểu tượng 🔖 để lưu bài. Xem lại trong tab "Đã lưu" trên trang cộng đồng.' },
          { title: 'Chia sẻ lại (repost) 🔁', desc: 'Nhấn biểu tượng chia sẻ lại để đăng lại bài (kèm trích dẫn tác giả gốc) lên feed.' },
        ],
      },
      {
        icon: '📰', title: 'Feed và bộ lọc',
        desc: 'Feed cộng đồng có nhiều tab và bộ lọc.',
        subtopics: [
          { title: 'Bốn tab feed', desc: 'Mới nhất (tất cả bài mới), Nổi bật (bài nhiều tương tác), Đang theo dõi (chỉ từ người bạn follow), Đã lưu (bài bạn bookmark).' },
          { title: 'Lọc theo loại bài', desc: 'Chip lọc bên dưới tab: Tất cả, Chia sẻ, Đánh giá, Hỏi đáp, Giới thiệu.' },
          { title: 'Lọc theo hashtag', desc: 'Sidebar phải hiển thị "Trending hashtags" — nhấn vào tag để lọc bài. Ví dụ: #ChợNổi, #MùaLũ.' },
          { title: 'Tìm kiếm trong cộng đồng', desc: 'Ô tìm kiếm trên trang cộng đồng tìm trong nội dung bài viết, không chỉ tiêu đề.' },
        ],
      },
      {
        icon: '👤', title: 'Theo dõi người dùng',
        desc: 'Theo dõi thành viên khác để xem bài mới trong tab "Đang theo dõi".',
        steps: ['Nhấn nút "Theo dõi" trên card người dùng (sidebar phải) hoặc trên trang hồ sơ', 'Bài viết mới của họ sẽ hiện trong tab "Đang theo dõi"', 'Bỏ theo dõi: nhấn lại nút hoặc vào trang hồ sơ'],
        subtopics: [{ title: 'Gợi ý theo dõi', desc: 'Sidebar phải hiển thị "Gợi ý theo dõi" — những thành viên tích cực mà bạn chưa follow.' }],
      },
      {
        icon: '🏆', title: 'Bảng xếp hạng & Cấp bậc',
        desc: 'Hệ thống điểm danh tiếng và cấp bậc khuyến khích đóng góp chất lượng.',
        subtopics: [
          { title: 'Bảng xếp hạng (/bang-xep-hang)', desc: 'Top thành viên theo điểm danh tiếng. Top 3 có huy chương vàng 🥇/bạc 🥈/đồng 🥉. Nhấn vào tên để xem hồ sơ.' },
          { title: 'Bốn cấp bậc', desc: '🌱 Người mới (0-49 điểm), 🤝 Thành viên (50-199), 🌟 Đóng góp viên (200-499), 👑 Đại sứ (500+). Cấp hiện bên cạnh tên trên mọi bài viết.' },
          { title: 'Huy hiệu thành tích', desc: 'Huy hiệu đặc biệt cho thành tựu: Nhà đánh giá (25+ đánh giá), Nhiếp ảnh gia (20+ ảnh), Hướng dẫn viên (5+ câu trả lời hay)...' },
        ],
        link: '/huong-dan-thanh-vien', linkLabel: 'Xem chi tiết cấp bậc & điểm',
      },
    ],
    faqs: [
      { q: 'Bài viết có bị kiểm duyệt không?', a: 'Có. Hệ thống tự động lọc nội dung vi phạm (spam, quảng cáo, ngôn ngữ không phù hợp). Đội ngũ quản trị cũng xem xét bài được báo cáo. Bài vi phạm có thể bị ẩn.' },
      { q: 'Có xóa được bài đã đăng không?', a: 'Có. Nhấn menu (...) trên bài viết của mình → "Xóa". Bài xóa không khôi phục được.' },
      { q: 'Tại sao điểm không tăng khi đăng nhiều?', a: 'Điểm giảm dần theo số lượng cùng loại (diminishing returns). Để tăng nhanh: đa dạng hóa — viết đánh giá, đăng ảnh, khám phá địa điểm mới, trả lời câu hỏi.' },
      { q: 'Làm sao chặn người dùng gây phiền?', a: 'Vào trang hồ sơ người đó → nhấn "Chặn". Người bị chặn không xem được bài bạn, không bình luận, không theo dõi. Bạn cũng sẽ không thấy bài của họ.' },
      { q: 'Bao lâu thì lên cấp "Đại sứ"?', a: 'Cần 500 điểm. Nếu đa dạng đóng góp (đánh giá + chia sẻ + ảnh + khám phá), trung bình 2-3 tháng hoạt động thường xuyên.' },
    ],
  },

  // ═══════════════════════════════════════════════════
  // 6. TÀI KHOẢN & CÀI ĐẶT
  // ═══════════════════════════════════════════════════
  {
    id: 'tai-khoan',
    icon: '👤',
    title: 'Tài khoản & Cài đặt',
    intro: 'Đăng ký bằng số điện thoại, quản lý hồ sơ, bảo mật, thông báo, và quyền riêng tư — tất cả trong trang Cài đặt.',
    topics: [
      {
        icon: '📱', title: 'Đăng ký & Đăng nhập',
        desc: 'Dùng số điện thoại + OTP — không cần email. An toàn, nhanh, phù hợp với thói quen người Việt.',
        steps: ['Nhấn "Đăng nhập" ở góc phải trên header', 'Modal đăng nhập mở ra — nhập số điện thoại (10 số, bắt đầu 0)', 'Nhấn "Gửi mã" — hệ thống gửi OTP 6 số qua SMS', 'Nhập mã OTP vào 6 ô và nhấn "Xác nhận"', 'Lần đầu: hệ thống tạo tài khoản mới tự động. Bạn có thể đặt mật khẩu (hoặc bỏ qua)', 'Lần sau: nhập SĐT → OTP → đăng nhập ngay (hoặc dùng mật khẩu nếu đã đặt)'],
        subtopics: [
          { title: 'Đăng nhập bằng mật khẩu', desc: 'Nếu đã đặt mật khẩu, trên modal đăng nhập nhấn "Dùng mật khẩu" → nhập SĐT và mật khẩu → đăng nhập không cần chờ OTP.' },
          { title: 'Quên mật khẩu', desc: 'Dùng OTP để đăng nhập (luôn có sẵn), sau đó vào Cài đặt → Bảo mật để đặt lại mật khẩu.' },
        ],
        tips: ['OTP có hiệu lực 5 phút. Nếu không nhận được, kiểm tra tin nhắn SMS hoặc thử lại sau 60 giây.', 'Không cần đăng ký riêng — lần đầu nhập SĐT chưa có tài khoản, hệ thống tự tạo.'],
      },
      {
        icon: '🖼️', title: 'Hồ sơ cá nhân',
        desc: 'Cập nhật tên, ảnh đại diện, ảnh bìa, tiểu sử trong trang Cài đặt.',
        steps: ['Nhấn avatar/tên ở góc phải trên → chọn "Cài đặt" (hoặc vào /cai-dat)', 'Tab "Hồ sơ" mở mặc định', 'Nhấn vào vùng avatar để tải ảnh mới (JPEG/PNG/WebP, tự động resize)', 'Nhấn vào ảnh bìa để thay đổi', 'Sửa tên hiển thị và tiểu sử → nhấn "Lưu"'],
        subtopics: [
          { title: 'Trang hồ sơ công khai', desc: 'Trang /nguoi-dung/[id] hiển thị hồ sơ công khai: ảnh bìa, avatar, tên, cấp bậc, số bài viết, số người theo dõi/đang theo dõi, và danh sách bài viết.' },
          { title: 'Thanh tiến trình hồ sơ', desc: 'Trên trang hồ sơ của bạn, thanh tiến trình cho biết % hoàn thiện (tên + avatar + bio + 1 bài viết + 1 đánh giá = 20% mỗi thứ).' },
        ],
        link: '/cai-dat', linkLabel: 'Mở Cài đặt',
      },
      {
        icon: '🔒', title: 'Bảo mật',
        desc: 'Quản lý mật khẩu, phiên đăng nhập, và lịch sử đăng nhập. Tất cả trong tab "Bảo mật" của trang Cài đặt.',
        subtopics: [
          { title: 'Đặt/đổi mật khẩu', desc: 'Nếu chưa có mật khẩu, nhấn "Đặt mật khẩu". Nếu đã có, nhập mật khẩu cũ → mật khẩu mới → xác nhận.' },
          { title: 'Quản lý phiên đăng nhập', desc: 'Danh sách tất cả thiết bị đang đăng nhập. Mỗi dòng hiện: thiết bị, IP, thời gian. Phiên hiện tại có badge "Hiện tại".', steps: ['Xem danh sách phiên trong tab Bảo mật', 'Nhấn "Thu hồi" bên cạnh phiên lạ để đăng xuất thiết bị đó'], tips: ['Kiểm tra phiên thường xuyên nếu bạn đăng nhập trên máy công cộng.'] },
          { title: 'Lịch sử đăng nhập', desc: 'Bảng ghi lại mọi lần đăng nhập (thành công/thất bại), thời gian, IP, phương thức (OTP/mật khẩu). Giúp phát hiện đăng nhập trái phép.' },
        ],
      },
      {
        icon: '🔔', title: 'Thông báo',
        desc: 'Xem thông báo hoạt động và tùy chỉnh loại thông báo muốn nhận.',
        subtopics: [
          { title: 'Chuông thông báo trên header', desc: 'Biểu tượng 🔔 trên header hiện chấm đỏ khi có thông báo chưa đọc. Nhấn để xem 5 thông báo gần nhất trong dropdown.' },
          { title: 'Trang thông báo (/thong-bao)', desc: 'Xem tất cả thông báo. Lọc theo loại: Tất cả, Thích, Bình luận, Theo dõi, Nhắc đến. Thông báo nhóm: "A và 4 người khác đã thích bài viết". Nhấn "Đọc tất cả" để đánh dấu đã đọc.' },
          { title: 'Tùy chỉnh (/cai-dat → Thông báo)', desc: 'Bật/tắt từng loại thông báo: Thích, Bình luận, Nhắc đến, Theo dõi mới. Loại bị tắt sẽ không tạo thông báo nữa.' },
        ],
        link: '/thong-bao', linkLabel: 'Xem thông báo',
      },
      {
        icon: '🚫', title: 'Vô hiệu hóa tài khoản',
        desc: 'Tạm ngừng sử dụng mà không mất dữ liệu.',
        steps: ['Vào /cai-dat → tab "Bảo mật" → cuộn xuống phần "Vùng nguy hiểm"', 'Nhấn "Vô hiệu hóa tài khoản"', 'Tài khoản ẩn khỏi cộng đồng, bài viết vẫn giữ, phiên đăng nhập bị thu hồi', 'Khi muốn quay lại: đăng nhập bằng OTP — tài khoản tự động kích hoạt lại'],
        warnings: ['Vô hiệu hóa khác với xóa. Vô hiệu hóa = tạm ẩn, có thể kích hoạt lại bất kỳ lúc nào.'],
      },
    ],
    faqs: [
      { q: 'Dùng email đăng ký được không?', a: 'Không. Hiện tại chỉ hỗ trợ số điện thoại + OTP. Phù hợp với thói quen người dùng Việt Nam.' },
      { q: 'Đăng nhập trên nhiều thiết bị được không?', a: 'Được. Mỗi thiết bị tạo một phiên riêng. Xem và thu hồi trong Cài đặt → Bảo mật.' },
      { q: 'Quên số điện thoại đã đăng ký thì sao?', a: 'Liên hệ quản trị qua trang Liên hệ để được hỗ trợ xác minh và khôi phục tài khoản.' },
      { q: 'Tài khoản có bị xóa tự động nếu không dùng lâu không?', a: 'Không. Tài khoản tồn tại vĩnh viễn trừ khi bạn chủ động xóa.' },
    ],
  },

  // ═══════════════════════════════════════════════════
  // 7. CÔNG CỤ TIỆN ÍCH
  // ═══════════════════════════════════════════════════
  {
    id: 'cong-cu',
    icon: '🛠️',
    title: 'Công cụ tiện ích',
    intro: 'Các tính năng bổ trợ giúp trải nghiệm mượt mà hơn: chat AI, chế độ tối, lưu yêu thích, chia sẻ, tuyến đường gợi ý.',
    topics: [
      {
        icon: '💬', title: 'Chat với trợ lý AI',
        desc: 'Trợ lý AI hiểu về du lịch, ẩm thực, văn hóa vùng Vĩnh Long – Bến Tre – Trà Vinh. Hỏi bất cứ điều gì.',
        steps: ['Nhấn nút 💬 ở góc phải dưới màn hình (hiện trên mọi trang)', 'Cửa sổ chat mở ra với gợi ý câu hỏi (thay đổi theo trang bạn đang xem)', 'Gõ câu hỏi và nhấn Enter hoặc nút gửi', 'Trợ lý trả lời dạng streaming (từng chữ hiện ra)', 'Nhấn nút dừng nếu muốn ngắt giữa chừng', 'Nhấn nút 💬 lần nữa hoặc Esc để đóng'],
        subtopics: [
          { title: 'Gợi ý theo ngữ cảnh', desc: 'Khi đang ở trang "Chợ nổi Cái Bè", gợi ý sẽ là: "Nên đi chợ nổi lúc mấy giờ?", "Có gì ăn ở đây?". Ở trang khác sẽ có gợi ý khác. Nhấn vào gợi ý để hỏi nhanh mà không cần gõ.' },
          { title: 'Ví dụ câu hỏi hay', desc: '"Đi Vĩnh Long 2 ngày nên đi đâu?", "Món gì ngon ở Bến Tre?", "Mùa nước nổi có gì thú vị?", "So sánh homestay ở Cù lao An Bình", "Quà mang về từ Trà Vinh".' },
          { title: 'Giới hạn', desc: 'Trợ lý trả lời dựa trên dữ liệu trong hệ thống. Không có thông tin giá vé real-time, tình trạng phòng, hoặc thời tiết hiện tại.' },
        ],
        tips: ['Hỏi rõ ràng sẽ được câu trả lời tốt hơn. "Ăn gì ở TP Vĩnh Long buổi tối" > "ăn gì".', 'Tiêu đề cửa sổ chat và disclaimer có thể thay đổi tùy cấu hình admin.'],
        didYouKnow: 'Gợi ý câu hỏi tự động thay đổi dựa trên trang bạn đang xem — hệ thống phân tích URL và nội dung trang để đưa ra gợi ý phù hợp nhất.',
      },
      {
        icon: '🌙', title: 'Chế độ tối (Dark Mode)',
        desc: 'Chuyển đổi giữa giao diện sáng và tối. Ghi nhớ lựa chọn.',
        steps: ['Nhấn biểu tượng ☀️/🌙 trên header (bên trái nút Đăng nhập)', 'Giao diện chuyển đổi ngay lập tức — tất cả trang, bản đồ, card', 'Lựa chọn được lưu — lần sau mở lại vẫn giữ chế độ bạn chọn'],
        tips: ['Chế độ tối giảm mỏi mắt khi duyệt buổi tối và tiết kiệm pin trên màn hình OLED.'],
      },
      {
        icon: '📤', title: 'Chia sẻ trang',
        desc: 'Chia sẻ bất kỳ trang nào — SEO đầy đủ (ảnh, mô tả hiện khi paste link vào Zalo/Facebook).',
        subtopics: [
          { title: 'Chia sẻ địa điểm', desc: 'Trên trang chi tiết, nhấn nút "Chia sẻ" → sao chép link hoặc mở native share (trên di động). Link paste vào Zalo/Facebook hiện ảnh + mô tả tự động nhờ Open Graph metadata.' },
          { title: 'Chia sẻ lịch trình', desc: 'Lịch trình công khai có link riêng — gửi cho bạn bè để họ xem và tham khảo.' },
          { title: 'Thêm vào màn hình chính', desc: 'Trên di động: nhấn menu trình duyệt → "Thêm vào màn hình chính" → dùng vinhlong360 như app, mở nhanh từ icon.' },
        ],
      },
      {
        icon: '🛣️', title: 'Tuyến đường gợi ý',
        desc: 'Các tuyến du lịch biên soạn sẵn — phù hợp cho người đi tự túc bằng xe máy hoặc ô tô.',
        steps: ['Truy cập /tuyen-duong', 'Lọc theo khu vực (Vĩnh Long, Bến Tre, Trà Vinh)', 'Mỗi tuyến gồm: tên, emoji, thời gian, quãng đường, danh sách điểm dừng', 'Đọc mẹo di chuyển ở cuối mỗi tuyến', 'Nhấn vào điểm dừng để xem chi tiết hoặc mở trên bản đồ'],
        tips: ['Tuyến đường là gợi ý — bạn có thể bỏ/thêm điểm dừng bằng cách tạo lịch trình riêng.'],
        seeAlso: [{ href: '#lich-trinh', label: 'Tạo lịch trình tùy chỉnh' }],
        link: '/tuyen-duong', linkLabel: 'Xem tuyến đường',
      },
      {
        icon: '⬆️', title: 'Cuộn lên đầu trang',
        desc: 'Khi cuộn xuống xa, nút mũi tên ⬆️ hiện ở góc phải dưới. Nhấn để cuộn mượt về đầu trang. Nút tự ẩn khi bạn ở đầu trang.',
      },
      {
        icon: '🎓', title: 'Onboarding cho thành viên mới',
        desc: 'Lần đầu đăng nhập, hệ thống hiện sheet hướng dẫn nhanh (OnboardingSheet) giới thiệu các tính năng chính. Sheet chỉ hiện 1 lần — sau đó bạn có thể tham khảo trang này.',
      },
    ],
    faqs: [
      { q: 'Chat AI có lưu lịch sử không?', a: 'Lịch sử chat giữ trong phiên trình duyệt. Khi đóng tab hoặc tải lại trang, lịch sử mất. Không có lưu trữ vĩnh viễn.' },
      { q: 'Có ứng dụng di động không?', a: 'Không có app riêng. vinhlong360 là web app — truy cập trên trình duyệt di động. "Thêm vào màn hình chính" để dùng như app.' },
      { q: 'Chat AI có trả lời sai không?', a: 'Có thể. AI trả lời dựa trên dữ liệu hệ thống, không phải nguồn sống. Luôn xác nhận thông tin quan trọng (giá, giờ mở cửa) trực tiếp với cơ sở.' },
    ],
  },

  // ═══════════════════════════════════════════════════
  // 8. THÔNG TIN HÀNH CHÍNH
  // ═══════════════════════════════════════════════════
  {
    id: 'danh-ba',
    icon: '🏛️',
    title: 'Thông tin hành chính',
    intro: 'Tra cứu thông tin liên hệ cơ quan hành chính, trang xã/phường, và các khu vực trong vùng.',
    topics: [
      {
        icon: '📒', title: 'Danh bạ hành chính',
        desc: 'Thông tin liên hệ UBND xã/phường: địa chỉ, số điện thoại, email, website.',
        steps: ['Truy cập /danh-ba', 'Chọn khu vực: Vĩnh Long, Bến Tre, hoặc Trà Vinh', 'Chọn xã/phường từ dropdown', 'Xem thông tin liên hệ: địa chỉ, SĐT (nhấn để gọi), email, website', 'Nhấn "Xem trên bản đồ" để mở vị trí'],
        subtopics: [{ title: 'Báo thông tin sai', desc: 'Nếu phát hiện SĐT, địa chỉ sai — nhấn "Báo sai" để gửi yêu cầu cập nhật.' }],
        warnings: ['Thông tin có thể thay đổi sau khi sáp nhập đơn vị hành chính. Xác nhận trực tiếp nếu cần.'],
        link: '/danh-ba', linkLabel: 'Mở danh bạ',
      },
      {
        icon: '🏘️', title: 'Trang xã/phường',
        desc: 'Mỗi xã/phường có trang riêng với tóm tắt, sản phẩm nổi bật, địa điểm, và thông tin liên hệ.',
        subtopics: [
          { title: 'Cách truy cập', desc: 'Từ breadcrumb trên trang chi tiết (ví dụ: Vĩnh Long > Long Hồ > Phú Quới), nhấn vào tên xã/phường. Hoặc từ danh bạ.' },
          { title: 'Nội dung trang xã/phường', desc: 'Gồm: tóm tắt giới thiệu, danh sách địa điểm thuộc xã, sản phẩm địa phương, thông tin liên hệ UBND, link bản đồ.' },
        ],
      },
      {
        icon: '🗺️', title: 'Ba khu vực',
        desc: 'Duyệt theo 3 vùng chính: Vĩnh Long (🍊), Bến Tre (🥥), Trà Vinh (🛕).',
        steps: ['Nhấn vào khu vực ở footer hoặc truy cập /khu-vuc/vinh-long, /khu-vuc/ben-tre, /khu-vuc/tra-vinh', 'Xem tổng quan, địa điểm nổi bật, đặc sản riêng của vùng', 'Lọc danh sách theo loại hình hoặc mùa'],
      },
    ],
    faqs: [
      { q: 'Danh bạ có cập nhật theo sáp nhập hành chính không?', a: 'Hệ thống cập nhật theo thông tin mới nhất. Trong giai đoạn chuyển tiếp, một số thông tin có thể chưa kịp cập nhật.' },
      { q: 'Có danh bạ bệnh viện, trường học không?', a: 'Hiện tại chỉ có danh bạ cơ quan hành chính (UBND). Các loại danh bạ khác có thể được bổ sung trong tương lai.' },
    ],
  },
]

const shortcuts = [
  { action: 'Tìm kiếm', desktop: 'Nhấn vào thanh tìm kiếm trên header', mobile: 'Nhấn biểu tượng 🔍 trên header' },
  { action: 'Chuyển ảnh trong lightbox', desktop: 'Phím ← →', mobile: 'Vuốt trái/phải' },
  { action: 'Đóng lightbox / modal / chat', desktop: 'Phím Esc', mobile: 'Nhấn nút ✕ hoặc vuốt xuống' },
  { action: 'Chuyển dark mode', desktop: 'Nhấn ☀️/🌙 trên header', mobile: 'Nhấn ☀️/🌙 trên header' },
  { action: 'Lưu yêu thích', desktop: 'Nhấn ❤️ trên trang chi tiết', mobile: 'Nhấn ❤️ trên trang chi tiết' },
  { action: 'Tag người/địa điểm', desktop: 'Gõ @ khi soạn bài', mobile: 'Gõ @ khi soạn bài' },
  { action: 'Gọi điện cho cơ sở', desktop: 'Nhấn SĐT (mở app gọi nếu có)', mobile: 'Nhấn SĐT → gọi trực tiếp' },
  { action: 'Chat AI', desktop: 'Nhấn nút 💬 góc phải dưới', mobile: 'Nhấn nút 💬 góc phải dưới' },
  { action: 'Cuộn lên đầu trang', desktop: 'Nhấn nút ⬆️ góc phải dưới', mobile: 'Nhấn nút ⬆️ góc phải dưới' },
  { action: 'Zoom bản đồ', desktop: 'Cuộn chuột hoặc nút +/−', mobile: 'Chụm/mở 2 ngón tay' },
  { action: 'Điều hướng bản đồ', desktop: 'Kéo chuột', mobile: 'Kéo 1 ngón tay' },
  { action: 'Mở menu di động', desktop: '—', mobile: 'Nhấn ☰ góc phải trên' },
]

interface TroubleshootItem {
  symptom: string
  cause: string
  fix: string[]
}

const troubleshooting = [
  {
    icon: '🔐', title: 'Đăng nhập & Tài khoản',
    items: [
      { symptom: 'Không nhận được mã OTP', cause: 'SMS bị chặn bởi nhà mạng hoặc SĐT nhập sai.', fix: ['Kiểm tra lại SĐT (10 số, bắt đầu 0)', 'Chờ 60 giây rồi nhấn "Gửi lại mã"', 'Kiểm tra tin nhắn SMS (không phải tin rác)', 'Nếu vẫn không nhận được, thử SĐT khác hoặc liên hệ hỗ trợ'] },
      { symptom: 'Đăng nhập bằng mật khẩu bị sai', cause: 'Nhập sai mật khẩu hoặc chưa từng đặt mật khẩu.', fix: ['Dùng OTP để đăng nhập thay thế', 'Sau khi vào, đặt lại mật khẩu trong Cài đặt → Bảo mật'] },
      { symptom: 'Bị đăng xuất bất ngờ', cause: 'Phiên hết hạn hoặc bị thu hồi từ thiết bị khác.', fix: ['Đăng nhập lại bằng OTP hoặc mật khẩu', 'Kiểm tra mục "Phiên đăng nhập" trong Cài đặt để phát hiện truy cập lạ'] },
    ] as TroubleshootItem[],
  },
  {
    icon: '🗺️', title: 'Bản đồ & Hiển thị',
    items: [
      { symptom: 'Bản đồ trắng hoặc không tải', cause: 'Kết nối internet yếu hoặc trình duyệt cũ không hỗ trợ WebGL.', fix: ['Kiểm tra kết nối internet', 'Tải lại trang (Ctrl+R hoặc kéo xuống trên di động)', 'Dùng trình duyệt mới (Chrome, Firefox, Safari, Edge phiên bản mới nhất)', 'Tắt VPN nếu đang bật — một số VPN chặn tile bản đồ'] },
      { symptom: 'Không thấy địa điểm trên bản đồ', cause: 'Địa điểm chưa có tọa độ GPS hoặc bị ẩn bởi bộ lọc.', fix: ['Kiểm tra chip lọc phía trên bản đồ — đảm bảo loại hình đang bật', 'Zoom vào khu vực — điểm có thể nằm trong cụm (cluster)', 'Địa điểm không có tọa độ chỉ hiện trong danh sách, không trên bản đồ'] },
    ] as TroubleshootItem[],
  },
  {
    icon: '✍️', title: 'Cộng đồng & Bài viết',
    items: [
      { symptom: 'Không đăng được bài', cause: 'Chưa đăng nhập, bài trống, hoặc vượt 500 ký tự.', fix: ['Đảm bảo đã đăng nhập (nút "Đăng nhập" biến mất khi đã đăng)', 'Kiểm tra bộ đếm ký tự — tối đa 500', 'Nếu đăng ảnh, đợi ảnh upload xong rồi mới nhấn "Đăng"'] },
      { symptom: 'Bài viết bị ẩn sau khi đăng', cause: 'Hệ thống kiểm duyệt phát hiện nội dung vi phạm.', fix: ['Kiểm tra nội dung có từ ngữ không phù hợp', 'Bài quảng cáo thương mại có thể bị ẩn', 'Liên hệ quản trị nếu cho rằng bài bị ẩn nhầm'] },
      { symptom: 'Ảnh không upload được', cause: 'File quá lớn hoặc định dạng không hỗ trợ.', fix: ['Dùng ảnh JPEG, PNG hoặc WebP', 'Ảnh tự động nén — nếu vẫn lỗi, thử ảnh nhỏ hơn 10MB', 'Kiểm tra kết nối internet — upload cần kết nối ổn định'] },
    ] as TroubleshootItem[],
  },
  {
    icon: '📱', title: 'Hiển thị & Trình duyệt',
    items: [
      { symptom: 'Trang hiển thị lỗi hoặc vỡ layout', cause: 'Trình duyệt cũ hoặc cache bị lỗi.', fix: ['Tải lại trang cứng: Ctrl+Shift+R (PC) hoặc kéo xuống giữ (di động)', 'Xóa cache trình duyệt cho vinhlong360.vn', 'Cập nhật trình duyệt lên phiên bản mới nhất'] },
      { symptom: 'Dark mode không lưu', cause: 'Trình duyệt chặn localStorage hoặc duyệt ẩn danh.', fix: ['Kiểm tra không ở chế độ duyệt ẩn danh (Incognito)', 'Cho phép cookie và localStorage cho vinhlong360.vn'] },
      { symptom: 'Yêu thích biến mất', cause: 'Xóa lịch sử trình duyệt hoặc dùng thiết bị khác khi chưa đăng nhập.', fix: ['Đăng nhập tài khoản để đồng bộ yêu thích lên server', 'Yêu thích trên server không mất khi xóa lịch sử trình duyệt'] },
    ] as TroubleshootItem[],
  },
]

useSeoMeta({
  title: 'Hướng dẫn sử dụng — vinhlong360',
  description: 'Cẩm nang đầy đủ cách sử dụng vinhlong360: tìm kiếm, bản đồ, lịch trình, cộng đồng, chat AI, cài đặt tài khoản và nhiều tính năng khác.',
  ogTitle: 'Hướng dẫn sử dụng — vinhlong360',
  ogDescription: 'Hướng dẫn từng bước tất cả tính năng trên vinhlong360 — khám phá, lịch trình, cộng đồng, bản đồ, chat AI.',
})
useHead({ link: [{ rel: 'canonical', href: canonicalUrl('/huong-dan') }] })
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
  border: 1px solid var(--line); border-radius: var(--radius-md);
  font-size: var(--text-sm); background: var(--card); color: var(--ink);
  outline: none; transition: border-color .15s;
}
.search-input:focus { border-color: var(--primary-fg); }
.sidebar-nav { display: flex; flex-direction: column; gap: 1px; }
.snav-link {
  display: block; padding: var(--space-2) var(--space-3);
  font-size: var(--text-xs); color: var(--muted); text-decoration: none;
  border-radius: var(--radius-sm); transition: background .15s, color .15s;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.snav-link:hover { background: var(--bg-warm); color: var(--ink); }
.snav-link.active { background: rgba(var(--primary-rgb, 46, 125, 50), .1); color: var(--primary-fg); font-weight: var(--weight-semibold); }
.sidebar-empty { font-size: var(--text-xs); color: var(--muted); padding: var(--space-2) var(--space-3); }

/* Mobile TOC + search */
.mobile-toc, .mobile-search { display: none; }

/* Hero */
.guide-hero {
  display: flex; align-items: center; gap: var(--space-4);
  padding: var(--space-6); margin-bottom: var(--space-6);
  background: linear-gradient(135deg, rgba(var(--primary-rgb, 46, 125, 50), .08) 0%, var(--bg-warm) 100%);
  border-radius: var(--radius-xl); border: .5px solid var(--line);
}
.guide-hero-icon { font-size: 2.5rem; flex-shrink: 0; }
.guide-hero h1 { margin: 0 0 var(--space-1); font-size: var(--text-2xl); font-weight: var(--weight-bold); letter-spacing: var(--tracking-tight); }
.guide-hero p { margin: 0; color: var(--muted); font-size: var(--text-sm); line-height: var(--leading-relaxed); }

/* Quickstart */
.quickstart-steps { list-style: none; padding: 0; margin: 0 0 var(--space-4); counter-reset: none; }
.quickstart-steps > li + li { margin-top: var(--space-3); }
.qs-step { display: flex; gap: var(--space-3); align-items: flex-start; padding: var(--space-4); background: var(--card); border: .5px solid var(--line); border-radius: var(--radius-xl); }
.qs-num {
  width: 2.2rem; height: 2.2rem; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  background: var(--primary-fg); color: var(--text-on-dark, #fff); font-weight: var(--weight-bold);
  font-size: var(--text-base); border-radius: 50%;
}
.qs-step strong { display: block; margin-bottom: var(--space-1); font-size: var(--text-sm); }
.qs-step p { margin: 0; font-size: var(--text-sm); color: var(--muted); line-height: var(--leading-relaxed); }

/* Sections */
.guide-section { margin-bottom: var(--space-8); scroll-margin-top: 80px; }
.guide-section > h2 {
  font-size: var(--text-xl); font-weight: var(--weight-bold); margin: 0 0 var(--space-2);
  padding-bottom: var(--space-2); border-bottom: 2px solid var(--primary-fg);
}
.section-intro { color: var(--muted); font-size: var(--text-sm); line-height: var(--leading-relaxed); margin: 0 0 var(--space-5); }

/* Topics (collapsible) */
.guide-topic {
  margin-bottom: var(--space-3); border: .5px solid var(--line);
  border-radius: var(--radius-xl); background: var(--card); overflow: hidden;
  scroll-margin-top: 80px;
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
.topic-chevron { font-size: .75rem; color: var(--muted); transition: transform .2s; }
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
  background: var(--primary-fg); color: var(--text-on-dark, #fff);
  font-size: var(--text-xs); font-weight: var(--weight-bold);
  display: flex; align-items: center; justify-content: center;
}
.guide-steps--sub > li::before { background: var(--muted); }
.guide-steps > li + li { border-top: .5px dashed var(--line); }

/* Subtopics */
.subtopics { margin: var(--space-3) 0; }
.subtopic {
  padding: var(--space-3) var(--space-4);
  border-left: 3px solid var(--primary-fg);
  margin-bottom: var(--space-3); background: var(--bg-warm);
  border-radius: 0 var(--radius-md) var(--radius-md) 0;
}
.subtopic > h4 { font-size: var(--text-sm); font-weight: var(--weight-bold); margin: 0 0 var(--space-1); }
.subtopic > p { font-size: var(--text-sm); color: var(--muted); margin: 0; line-height: var(--leading-relaxed); }

/* Tip, Warn, DYK, See-also */
.tip-box, .warn-box, .dyk-box {
  margin-top: var(--space-3); padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-lg); font-size: var(--text-sm);
}
.tip-box { background: rgba(var(--primary-rgb, 46, 125, 50), .06); border: .5px solid rgba(var(--primary-rgb, 46, 125, 50), .15); }
.warn-box { background: rgba(var(--warning-rgb), .06); border: .5px solid rgba(var(--warning-rgb), .2); }
.dyk-box { background: rgba(var(--blue-rgb), .06); border: .5px solid rgba(var(--blue-rgb), .15); }
.tip-line, .warn-line { margin: 0; line-height: var(--leading-relaxed); color: var(--ink); }
.tip-line + .tip-line, .warn-line + .warn-line { margin-top: var(--space-2); }
.dyk-box p { margin: 0; line-height: var(--leading-relaxed); }

.see-also { margin-top: var(--space-3); display: flex; flex-wrap: wrap; gap: var(--space-2); align-items: center; font-size: var(--text-xs); }
.see-also-label { color: var(--muted); font-weight: var(--weight-semibold); }
.see-also-link { color: var(--primary-fg); text-decoration: none; padding: 2px var(--space-2); background: rgba(var(--primary-rgb, 46, 125, 50), .06); border-radius: var(--radius-sm); }
.see-also-link:hover { text-decoration: underline; }

.topic-link {
  display: inline-block; margin-top: var(--space-3);
  font-size: var(--text-sm); font-weight: var(--weight-semibold);
  color: var(--primary-fg); text-decoration: none;
}
.topic-link:hover { text-decoration: underline; }

/* FAQ */
.faq-block { margin-top: var(--space-4); }
.faq-heading {
  font-size: var(--text-sm); font-weight: var(--weight-semibold);
  color: var(--muted); text-transform: uppercase; letter-spacing: .05em;
  margin: 0 0 var(--space-3);
}
.faq-item {
  border: .5px solid var(--line); border-radius: var(--radius-lg);
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
.no-results a { color: var(--primary-fg); }

/* Shortcuts table */
.shortcut-table-wrap { overflow-x: auto; }
.shortcut-table { width: 100%; border-collapse: collapse; font-size: var(--text-sm); }
.shortcut-table th {
  text-align: left; padding: var(--space-2) var(--space-3);
  font-weight: var(--weight-semibold); color: var(--muted);
  border-bottom: 1.5px solid var(--line); font-size: var(--text-xs);
  text-transform: uppercase; letter-spacing: .04em;
}
.shortcut-table td { padding: var(--space-3); border-bottom: .5px solid var(--line); }
.shortcut-table tbody tr:hover { background: var(--bg-warm); }

/* CTA */
.guide-cta {
  text-align: center; padding: var(--space-8) var(--space-4); margin-top: var(--space-4);
  background: linear-gradient(135deg, rgba(var(--primary-rgb, 46, 125, 50), .06) 0%, var(--bg-warm) 100%);
  border-radius: var(--radius-xl); border: .5px solid var(--line);
}
.guide-cta h2 { border-bottom: none; padding-bottom: 0; font-size: var(--text-xl); }
.guide-cta p { color: var(--muted); font-size: var(--text-sm); margin: var(--space-2) 0 var(--space-5); }
.cta-btns { display: flex; gap: var(--space-3); justify-content: center; flex-wrap: wrap; }

.guide-updated { text-align: center; color: var(--ink-tertiary); font-size: var(--text-xs); margin-top: var(--space-6); }

/* Dark */
.dark .guide-hero, .dark .guide-cta { background: linear-gradient(135deg, rgba(255,255,255,.03) 0%, rgba(255,255,255,.01) 100%); }
.dark .guide-topic { background: var(--bg-alt); }
.dark .qs-step { background: var(--bg-alt); }
.dark .subtopic { background: rgba(255,255,255,.03); }
.dark .tip-box { background: rgba(255,255,255,.03); border-color: rgba(255,255,255,.08); }
.dark .warn-box { background: rgba(var(--warning-rgb), .05); border-color: rgba(var(--warning-rgb), .12); }
.dark .dyk-box { background: rgba(var(--blue-rgb), .04); border-color: rgba(var(--blue-rgb), .1); }

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .topic-chevron, .faq-item > summary::before { transition: none; }
}

/* Print */
@media print {
  .guide-sidebar, .mobile-toc, .mobile-search, .guide-cta, .topic-chevron, .see-also { display: none; }
  .guide-layout { display: block; max-width: 100%; }
  .guide-topic { border: none; break-inside: avoid; }
  .guide-topic[open] > .topic-summary, .topic-summary { pointer-events: none; }
  .topic-body { display: block !important; }
  .guide-section { break-before: auto; }
}

/* Mobile */
@media (max-width: 900px) {
  .guide-sidebar { display: none; }
  .mobile-toc, .mobile-search { display: block; margin-bottom: var(--space-4); }
  .mobile-toc { border: .5px solid var(--line); border-radius: var(--radius-xl); }
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
    border-radius: var(--radius-sm);
  }
  .mobile-toc-nav a:hover { background: var(--bg-warm); }
  .guide-layout { padding: var(--space-3); }
  .guide-hero { flex-direction: column; text-align: center; padding: var(--space-5); }
  .qs-step { flex-direction: column; align-items: center; text-align: center; }
  .guide-topic { border-radius: var(--radius-lg); }
  .topic-body { padding: 0 var(--space-3) var(--space-3); }
  .subtopic { padding: var(--space-2) var(--space-3); }
}
</style>
