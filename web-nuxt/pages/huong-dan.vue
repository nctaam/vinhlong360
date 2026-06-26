<template>
  <main class="guide-page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Hướng dẫn sử dụng' }]" />

    <header class="guide-hero">
      <span class="guide-hero-icon" aria-hidden="true">📖</span>
      <div>
        <h1>Hướng dẫn sử dụng</h1>
        <p>Cẩm nang đầy đủ mọi tính năng trên vinhlong360 — từ tìm kiếm, bản đồ, lịch trình đến cộng đồng và quản lý tài khoản.</p>
      </div>
    </header>

    <!-- TOC -->
    <nav class="guide-toc reveal" aria-label="Mục lục">
      <h2 class="toc-title">Mục lục</h2>
      <ol class="toc-list">
        <li v-for="s in sections" :key="s.id">
          <a :href="`#${s.id}`" class="toc-link">
            <span class="toc-icon" aria-hidden="true">{{ s.icon }}</span>
            {{ s.title }}
          </a>
          <ol v-if="s.topics.length > 3" class="toc-sub">
            <li v-for="t in s.topics" :key="t.title">
              <a :href="`#${s.id}--${slugify(t.title)}`" class="toc-sublink">{{ t.title }}</a>
            </li>
          </ol>
        </li>
      </ol>
    </nav>

    <!-- Sections -->
    <section v-for="s in sections" :key="s.id" :id="s.id" class="guide-section reveal">
      <h2>{{ s.title }}</h2>
      <p class="section-intro">{{ s.intro }}</p>

      <!-- Topics -->
      <article v-for="t in s.topics" :key="t.title" :id="`${s.id}--${slugify(t.title)}`" class="guide-topic">
        <h3>
          <span class="topic-icon" aria-hidden="true">{{ t.icon }}</span>
          {{ t.title }}
        </h3>
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

        <!-- Link -->
        <NuxtLink v-if="t.link" :to="t.link" class="topic-link">
          {{ t.linkLabel || 'Đi tới trang' }} →
        </NuxtLink>
      </article>

      <!-- FAQ -->
      <div v-if="s.faqs?.length" class="faq-block">
        <h3 class="faq-heading">Câu hỏi thường gặp</h3>
        <details v-for="(faq, i) in s.faqs" :key="i" class="faq-item">
          <summary>{{ faq.q }}</summary>
          <p>{{ faq.a }}</p>
        </details>
      </div>
    </section>

    <!-- Quick reference -->
    <section id="phim-tat" class="guide-section reveal">
      <h2>Phím tắt & thao tác nhanh</h2>
      <p class="section-intro">Các thao tác giúp sử dụng nhanh hơn trên máy tính và di động.</p>
      <div class="shortcut-table-wrap">
        <table class="shortcut-table">
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

    <!-- CTA -->
    <section class="guide-cta reveal">
      <h2>Bắt đầu khám phá ngay!</h2>
      <p>Mọi tính năng đều miễn phí. Không cần đăng ký để duyệt — chỉ cần tài khoản khi muốn đóng góp nội dung.</p>
      <div class="cta-btns">
        <NuxtLink to="/" class="btn btn-primary">Về trang chủ</NuxtLink>
        <NuxtLink to="/huong-dan-thanh-vien" class="btn btn-ghost">Hệ thống cấp bậc & điểm</NuxtLink>
      </div>
    </section>

    <p class="guide-updated">Cập nhật: {{ updatedDate }}</p>
  </main>
</template>

<script setup lang="ts">
useReveal()

const updatedDate = '26/06/2026'

function slugify(s: string) {
  return s.toLowerCase().replace(/[^a-z0-9À-ɏ]+/gi, '-').replace(/(^-|-$)/g, '')
}

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
        ],
        tips: [
          'Gõ tiếng Việt không dấu cũng tìm được — ví dụ "vinh long" sẽ trả kết quả "Vĩnh Long".',
          'Tìm kiếm trên trang chủ và trên header cho cùng kết quả — dùng cái nào tiện hơn.',
          'Phần "Đã xem gần đây" trên trang tìm kiếm giúp quay lại nhanh những địa điểm đã duyệt.',
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
            title: 'Du lịch & Trải nghiệm',
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
            title: 'Sản phẩm địa phương',
            desc: 'Đặc sản, thủ công mỹ nghệ, nông sản theo mùa. Có bộ lọc OCOP riêng.',
            steps: [
              'Truy cập /san-pham',
              'Hero hiển thị 3 chỉ số: tổng sản phẩm, số đạt OCOP, số đang vào mùa',
              'Bật nút "Chỉ OCOP" để chỉ xem sản phẩm đã được chứng nhận',
              'Lọc theo tháng để xem sản phẩm theo mùa',
            ],
          },
          {
            title: 'Sản phẩm OCOP',
            desc: 'Trang riêng cho sản phẩm đạt chứng nhận OCOP (Mỗi xã Một sản phẩm) với bộ lọc theo sao.',
            steps: [
              'Truy cập /ocop',
              'Lọc theo hạng sao: 3 sao, 4 sao, hoặc 5 sao',
              'Phần "Vinh danh" hiển thị riêng các sản phẩm 5 sao (biểu tượng vương miện)',
              'Lọc theo khu vực (Vĩnh Long, Bến Tre, Trà Vinh)',
            ],
          },
          {
            title: 'Lễ hội & Sự kiện',
            desc: 'Lễ hội truyền thống và sự kiện sắp diễn ra. Truy cập từ menu "Khám phá".',
          },
        ],
        tips: [
          'Mỗi danh mục có nút "Xem thêm" hoặc cuộn vô hạn — không bao giờ bị giới hạn số lượng kết quả.',
        ],
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
            title: 'Xem vị trí cụ thể',
            desc: 'Bạn có thể mở bản đồ với vị trí đã chọn sẵn từ trang chi tiết địa điểm.',
            steps: [
              'Trên trang chi tiết địa điểm, nhấn nút "Xem trên bản đồ"',
              'Bản đồ sẽ mở và zoom đến đúng vị trí đó, popup mở sẵn',
            ],
          },
        ],
        tips: [
          'Bản đồ có mã màu theo loại hình — mỗi emoji là 1 loại, dễ nhận biết khi zoom ra.',
          'Trên di động, dùng 2 ngón để zoom và 1 ngón để kéo.',
        ],
        link: '/ban-do',
        linkLabel: 'Mở bản đồ',
      },
    ],
    faqs: [
      { q: 'Bản đồ có chỉ đường không?', a: 'Hiện tại bản đồ chỉ hiển thị vị trí. Để chỉ đường, dùng tính năng Lịch trình — hệ thống sẽ tính quãng đường và thời gian giữa các điểm dừng.' },
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
        icon: '📸',
        title: 'Thư viện ảnh',
        desc: 'Ảnh bìa hiển thị ở đầu trang. Nhấn vào để mở lightbox toàn màn hình duyệt tất cả ảnh.',
        steps: [
          'Nhấn vào ảnh bìa hoặc nút "X ảnh" để mở lightbox',
          'Trong lightbox: nhấn ← → (hoặc vuốt trái/phải trên di động) để chuyển ảnh',
          'Nhấn Esc hoặc nút ✕ để đóng lightbox',
          'Ảnh trong lightbox hiển thị ở chất lượng cao nhất có sẵn',
        ],
        tips: [
          'Ảnh chỉ dùng nguồn bản quyền hợp lệ. Bạn có thể đóng góp ảnh bằng cách viết bài đánh giá kèm ảnh trong Cộng đồng.',
        ],
      },
      {
        icon: '📞',
        title: 'Thông tin liên hệ',
        desc: 'Phần đầu trang chi tiết hiển thị các thông tin thiết yếu để liên hệ và ghé thăm.',
        subtopics: [
          {
            title: 'Số điện thoại & Zalo',
            desc: 'Nhấn vào số điện thoại trên di động để gọi trực tiếp. Nếu có Zalo, biểu tượng Zalo sẽ hiện bên cạnh.',
          },
          {
            title: 'Giờ mở cửa & Giá',
            desc: 'Nếu địa điểm có thông tin giờ mở cửa hoặc khoảng giá, chúng hiển thị dưới tên.',
          },
          {
            title: 'Bản đồ vị trí',
            desc: 'Bản đồ nhỏ hiển thị vị trí chính xác. Nhấn "Xem trên bản đồ" để mở bản đồ lớn.',
          },
        ],
        warnings: [
          'Trang chỉ giới thiệu — KHÔNG có chức năng đặt hàng/booking. Liên hệ trực tiếp cơ sở qua điện thoại hoặc Zalo.',
        ],
      },
      {
        icon: '📅',
        title: 'Mùa vụ & Thời điểm',
        desc: 'Nhiều địa điểm/sản phẩm có tính mùa. Trang chi tiết hiển thị lưới 12 tháng và gợi ý thời điểm lý tưởng.',
        subtopics: [
          {
            title: 'Lưới 12 tháng',
            desc: 'Mỗi ô tháng có mã màu: xanh đậm = cao điểm, xanh nhạt = phù hợp, xám = không mùa. Giúp bạn chọn thời điểm ghé thăm tốt nhất.',
          },
          {
            title: 'Badge mùa trên card',
            desc: 'Trên trang danh mục, card địa điểm hiển thị badge "Đang mùa" nếu tháng hiện tại là tháng cao điểm.',
          },
        ],
      },
      {
        icon: '🔗',
        title: 'Địa điểm liên quan & Lân cận',
        desc: 'Cuối trang chi tiết hiển thị hai phần gợi ý giúp bạn khám phá thêm.',
        subtopics: [
          {
            title: 'Địa điểm liên quan',
            desc: 'Các địa điểm có mối quan hệ với địa điểm này — ví dụ: "Chợ nổi Cái Bè" liên quan đến "Cù lao An Bình" vì cùng tuyến tham quan.',
          },
          {
            title: 'Gần đây',
            desc: 'Các địa điểm khác trong cùng xã/phường hoặc trong bán kính gần — tiện để kết hợp khi đi.',
          },
        ],
      },
      {
        icon: '❤️',
        title: 'Lưu yêu thích',
        desc: 'Nhấn nút ❤️ "Lưu" trên trang chi tiết để đánh dấu địa điểm yêu thích.',
        steps: [
          'Nhấn nút ❤️ trên trang chi tiết bất kỳ địa điểm nào',
          'Địa điểm được lưu vào bộ nhớ trình duyệt (không cần đăng nhập)',
          'Nếu đã đăng nhập, danh sách yêu thích đồng bộ lên server — xem trên mọi thiết bị',
          'Xem lại danh sách trong hồ sơ cá nhân (tab "Đã lưu")',
          'Dùng danh sách này làm nguồn khi tạo lịch trình (tab "Đã lưu" trong trình tạo lịch trình)',
        ],
        tips: [
          'Lưu yêu thích trước khi tạo lịch trình — bạn sẽ có sẵn danh sách để chọn nhanh.',
          'Yêu thích hoạt động cả khi chưa đăng nhập (lưu trên trình duyệt). Khi đăng nhập, danh sách tự động gộp và đồng bộ.',
        ],
      },
      {
        icon: '⭐',
        title: 'Đánh giá từ cộng đồng',
        desc: 'Phần cuối trang chi tiết hiển thị các bài đánh giá từ thành viên cộng đồng (nếu có). Bạn cũng có thể viết đánh giá ngay tại đây.',
        steps: [
          'Cuộn xuống phần "Đánh giá" trên trang chi tiết',
          'Đọc đánh giá từ người đã đến — kèm ảnh thực tế',
          'Nhấn "Viết đánh giá" để đóng góp (cần đăng nhập)',
          'Chọn điểm số (1–5), viết nhận xét, đính kèm ảnh nếu có',
        ],
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
    icon: '📋',
    title: 'Lịch trình',
    intro: 'Tạo lịch trình du lịch cá nhân hoặc duyệt lịch trình gợi ý sẵn có. Hệ thống tính quãng đường, thời gian di chuyển, và hiển thị trên bản đồ.',
    topics: [
      {
        icon: '📝',
        title: 'Duyệt lịch trình gợi ý',
        desc: 'Các lịch trình được biên soạn sẵn theo khu vực, phù hợp cho người lần đầu đến.',
        steps: [
          'Truy cập /lich-trinh',
          'Hero hiển thị số lượng lịch trình theo từng khu vực',
          'Dùng chip lọc: Vĩnh Long, Bến Tre, Trà Vinh, hoặc Tất cả',
          'Nhấn vào card lịch trình để xem chi tiết: các điểm dừng, thời gian, quãng đường',
          'Nhấn "Lưu" để lưu vào danh sách cá nhân',
        ],
        subtopics: [
          {
            title: 'Lịch trình đã lưu',
            desc: 'Phần đầu trang hiển thị các lịch trình bạn đã lưu (tối đa 8 gần nhất). Nhấn để mở lại, hoặc "Bỏ lưu" để xóa khỏi danh sách.',
          },
        ],
        link: '/lich-trinh',
        linkLabel: 'Xem lịch trình gợi ý',
      },
      {
        icon: '✏️',
        title: 'Tự tạo lịch trình',
        desc: 'Trình tạo lịch trình cho phép bạn chọn điểm dừng, sắp xếp thứ tự, ghi chú, và xem trên bản đồ.',
        steps: [
          'Truy cập /tao-lich-trinh hoặc nhấn "Tạo lịch trình" từ menu',
          'Giao diện chia 2 phần: bên trái là danh sách địa điểm để chọn, bên phải là lịch trình đang xây',
          'Nhấn dấu "+" bên cạnh địa điểm để thêm vào lịch trình',
          'Sắp xếp thứ tự bằng nút ↑↓ hoặc kéo thả',
          'Thêm khung giờ (ví dụ "8:00–9:30") và ghi chú cho từng điểm dừng',
          'Đặt tên cho lịch trình bằng cách nhấn vào tiêu đề ở đầu',
          'Nhấn "Lưu" để lưu — lịch trình xuất hiện trong mục "Đã lưu" ở /lich-trinh',
        ],
        subtopics: [
          {
            title: 'Chọn từ danh sách yêu thích',
            desc: 'Tab "Đã lưu" (bên trái trình tạo) hiển thị những địa điểm bạn đã nhấn ❤️. Đây là cách nhanh nhất để tạo lịch trình từ những nơi bạn quan tâm.',
            steps: [
              'Chuyển sang tab "Đã lưu" trên panel bên trái',
              'Nhấn "+" để thêm từng địa điểm yêu thích vào lịch trình',
              'Hoặc nhấn "Tạo từ danh sách yêu thích" trên trang /lich-trinh để tự động thêm tất cả',
            ],
          },
          {
            title: 'Tìm và lọc địa điểm',
            desc: 'Trên tab "Tất cả", dùng ô tìm kiếm và chip lọc loại hình để tìm nhanh địa điểm muốn thêm.',
          },
          {
            title: 'Bản đồ tuyến đường',
            desc: 'Phía dưới lịch trình hiển thị bản đồ với đường nối giữa các điểm dừng (polyline). Bản đồ cập nhật tự động khi bạn thêm, xóa, hoặc sắp xếp lại.',
          },
        ],
        tips: [
          'Lưu yêu thích trước khi tạo lịch trình — rất tiện!',
          'Lịch trình lưu trên trình duyệt. Đăng nhập để đồng bộ và xem trên thiết bị khác.',
        ],
        link: '/tao-lich-trinh',
        linkLabel: 'Mở trình tạo lịch trình',
      },
      {
        icon: '🚗',
        title: 'Phương tiện & Khoảng cách',
        desc: 'Chọn phương tiện di chuyển để hệ thống tính quãng đường và thời gian phù hợp.',
        subtopics: [
          {
            title: 'Chọn phương tiện',
            desc: 'Ba lựa chọn: Ô tô, Xe máy, hoặc Xuồng. Hệ thống dùng dịch vụ OSRM (mã nguồn mở) để tính đường đi thực tế trên đường bộ.',
            steps: [
              'Trong trình tạo lịch trình, nhấn biểu tượng phương tiện (ô tô/xe máy/xuồng)',
              'Tổng quãng đường và thời gian cập nhật ngay',
              'Khoảng cách giữa từng cặp điểm dừng hiển thị trên danh sách',
            ],
          },
        ],
      },
      {
        icon: '🔗',
        title: 'Chia sẻ & Công khai',
        desc: 'Lịch trình đã lưu có thể đặt chế độ công khai (mọi người xem được) hoặc riêng tư.',
        steps: [
          'Mở lịch trình đã lưu',
          'Nhấn nút "Chia sẻ" để sao chép link',
          'Gửi link cho bạn bè qua Zalo, Messenger, hoặc mạng xã hội',
          'Nếu muốn hiện trên trang /lich-trinh cho mọi người, bật chế độ "Công khai"',
        ],
      },
    ],
    faqs: [
      { q: 'Có giới hạn số điểm dừng trong lịch trình không?', a: 'Không giới hạn. Nhưng lịch trình 1-2 ngày thường 5-10 điểm là hợp lý.' },
      { q: 'Lịch trình có tính chi phí không?', a: 'Chưa. Hệ thống chỉ tính quãng đường và thời gian di chuyển. Chi phí ăn uống, vé tham quan tùy thuộc từng địa điểm.' },
      { q: 'Sao khoảng cách không chính xác?', a: 'Hệ thống tính theo đường bộ (OSRM), có thể khác thực tế do đường tắt hoặc phà. Khoảng cách mang tính tham khảo.' },
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
        icon: '✍️',
        title: 'Viết bài',
        desc: 'Đăng bài chia sẻ, đánh giá, hỏi đáp, hoặc giới thiệu — mỗi loại có mục đích khác nhau.',
        steps: [
          'Truy cập /cong-dong và đăng nhập',
          'Nhấn vào ô soạn bài ở đầu trang',
          'Chọn loại bài: Chia sẻ, Đánh giá, Hỏi đáp, hoặc Giới thiệu',
          'Viết nội dung (tối đa 500 ký tự, bộ đếm hiện ở góc)',
          'Đính kèm ảnh: nhấn biểu tượng ảnh, chọn tối đa 5 ảnh',
          'Gõ @ để tag người dùng hoặc địa điểm (dropdown gợi ý hiện ra)',
          'Nhấn "Đăng" để xuất bản',
        ],
        subtopics: [
          {
            title: 'Loại bài viết',
            desc: 'Chọn đúng loại để bài hiện đúng nơi và được tính điểm phù hợp.',
            steps: [
              'Chia sẻ: Kể chuyện, chia sẻ kinh nghiệm du lịch — 3 điểm/bài',
              'Đánh giá: Nhận xét về địa điểm cụ thể, có điểm số 1-5 sao — 5 điểm/bài (10 bài đầu)',
              'Hỏi đáp: Đặt câu hỏi cho cộng đồng — 2 điểm',
              'Giới thiệu: Giới thiệu địa điểm mới, sản phẩm mới — 3 điểm',
            ],
          },
          {
            title: 'Đính kèm ảnh',
            desc: 'Ảnh được tự động nén (tối đa 1280px, JPEG chất lượng 82%) để tải nhanh mà vẫn rõ nét.',
            tips: ['Đánh giá kèm ảnh được cộng thêm điểm. Ảnh thực tế giúp người khác hình dung rõ hơn.'],
          },
          {
            title: 'Nhắc đến (@mention)',
            desc: 'Gõ @ trong ô soạn → dropdown gợi ý người dùng và địa điểm. Chọn để tag — người được tag nhận thông báo.',
            steps: [
              'Gõ @ rồi tiếp tục gõ tên (ví dụ: @Nguyên, @Chợ Nổi)',
              'Dropdown hiện danh sách khớp — nhấn để chọn',
              'Người/địa điểm được tag hiển thị dạng link trong bài',
            ],
          },
        ],
        tips: [
          'Bài nháp tự động lưu mỗi 5 giây — nếu thoát trang rồi quay lại, nội dung vẫn còn.',
          'Viết đánh giá mang nhiều điểm nhất (5 điểm/bài cho 10 bài đầu, giảm dần sau đó).',
        ],
      },
      {
        icon: '❤️',
        title: 'Tương tác với bài viết',
        desc: 'Thích, bình luận, lưu, chia sẻ lại — đầy đủ tương tác mạng xã hội.',
        subtopics: [
          {
            title: 'Thích bài viết',
            desc: 'Nhấn biểu tượng ❤️ trên bài. Tác giả nhận thông báo. Mỗi lượt thích tính 1 điểm cho tác giả.',
          },
          {
            title: 'Bình luận',
            desc: 'Nhấn biểu tượng 💬 để mở khung bình luận. Gõ và nhấn Enter để gửi. Bình luận cũng hỗ trợ @mention.',
          },
          {
            title: 'Lưu bài viết (bookmark)',
            desc: 'Nhấn biểu tượng 🔖 để lưu bài. Xem lại trong tab "Đã lưu" trên trang cộng đồng.',
          },
          {
            title: 'Chia sẻ lại (repost)',
            desc: 'Nhấn biểu tượng chia sẻ lại để đăng lại bài (kèm trích dẫn tác giả gốc) lên feed của bạn.',
          },
        ],
      },
      {
        icon: '📰',
        title: 'Feed và bộ lọc',
        desc: 'Feed cộng đồng có nhiều tab và bộ lọc để bạn xem nội dung phù hợp.',
        subtopics: [
          {
            title: 'Các tab feed',
            desc: 'Bốn tab: Mới nhất (tất cả bài mới), Nổi bật (bài nhiều tương tác), Đang theo dõi (chỉ từ người bạn follow), Đã lưu (bài bạn bookmark).',
          },
          {
            title: 'Lọc theo loại bài',
            desc: 'Chip lọc bên dưới tab: Tất cả, Chia sẻ, Đánh giá, Hỏi đáp, Giới thiệu — nhấn để chỉ xem loại đó.',
          },
          {
            title: 'Lọc theo hashtag',
            desc: 'Sidebar phải hiển thị "Trending hashtags" — nhấn vào tag để lọc bài theo chủ đề. Ví dụ: #ChợNổi, #MùaLũ.',
          },
        ],
      },
      {
        icon: '👤',
        title: 'Theo dõi người dùng',
        desc: 'Theo dõi thành viên khác để xem bài mới của họ trong tab "Đang theo dõi".',
        steps: [
          'Nhấn nút "Theo dõi" trên card người dùng (sidebar phải) hoặc trên trang hồ sơ',
          'Bài viết mới của họ sẽ hiện trong tab "Đang theo dõi"',
          'Bỏ theo dõi: nhấn lại nút hoặc vào cài đặt hồ sơ',
        ],
        subtopics: [
          {
            title: 'Gợi ý theo dõi',
            desc: 'Sidebar phải hiển thị "Gợi ý theo dõi" — những thành viên tích cực mà bạn chưa follow.',
          },
        ],
      },
      {
        icon: '🏆',
        title: 'Bảng xếp hạng & Cấp bậc',
        desc: 'Hệ thống điểm danh tiếng và cấp bậc khuyến khích đóng góp chất lượng.',
        subtopics: [
          {
            title: 'Bảng xếp hạng',
            desc: 'Trang /bang-xep-hang hiển thị top thành viên theo điểm danh tiếng. Top 3 có huy chương vàng/bạc/đồng.',
          },
          {
            title: 'Hệ thống cấp bậc',
            desc: 'Bốn cấp: 🌱 Người mới (0-49 điểm), 🤝 Thành viên (50-199), 🌟 Đóng góp viên (200-499), 👑 Đại sứ (500+). Cấp hiện bên cạnh tên trên mọi bài viết.',
          },
          {
            title: 'Cách tính điểm',
            desc: 'Điểm giảm dần khi bạn tập trung một loại đóng góp — khuyến khích đa dạng (viết bài + đánh giá + ảnh + khám phá). Xem chi tiết tại trang Hướng dẫn thành viên.',
          },
        ],
        link: '/huong-dan-thanh-vien',
        linkLabel: 'Xem chi tiết cấp bậc & điểm',
      },
    ],
    faqs: [
      { q: 'Bài viết có bị kiểm duyệt không?', a: 'Có. Hệ thống tự động lọc nội dung vi phạm (spam, quảng cáo, ngôn ngữ không phù hợp). Đội ngũ quản trị cũng xem xét bài được báo cáo. Bài vi phạm có thể bị ẩn.' },
      { q: 'Có xóa được bài đã đăng không?', a: 'Có. Nhấn menu (...) trên bài viết của mình → "Xóa". Bài xóa không khôi phục được.' },
      { q: 'Tại sao điểm không tăng khi đăng nhiều?', a: 'Điểm giảm dần theo số lượng cùng loại (diminishing returns). Để tăng nhanh: đa dạng hóa — viết đánh giá, đăng ảnh, khám phá địa điểm mới, trả lời câu hỏi.' },
      { q: 'Làm sao chặn người dùng gây phiền?', a: 'Vào trang hồ sơ người đó → nhấn "Chặn". Người bị chặn không xem được bài bạn, không bình luận, không theo dõi. Bạn cũng sẽ không thấy bài của họ.' },
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
        icon: '📱',
        title: 'Đăng ký & Đăng nhập',
        desc: 'Dùng số điện thoại + OTP — không cần email. An toàn, nhanh, phù hợp với thói quen người Việt.',
        steps: [
          'Nhấn "Đăng nhập" ở góc phải trên header',
          'Modal đăng nhập mở ra — nhập số điện thoại (10 số, bắt đầu 0)',
          'Nhấn "Gửi mã" — hệ thống gửi OTP 6 số qua SMS',
          'Nhập mã OTP vào 6 ô và nhấn "Xác nhận"',
          'Lần đầu: hệ thống tạo tài khoản mới tự động. Bạn có thể đặt mật khẩu (hoặc bỏ qua)',
          'Lần sau: nhập SĐT → OTP → đăng nhập ngay (hoặc dùng mật khẩu nếu đã đặt)',
        ],
        subtopics: [
          {
            title: 'Đăng nhập bằng mật khẩu',
            desc: 'Nếu đã đặt mật khẩu, bạn có thể đăng nhập bằng SĐT + mật khẩu mà không cần chờ OTP.',
            steps: [
              'Trên modal đăng nhập, nhấn "Dùng mật khẩu"',
              'Nhập SĐT và mật khẩu → nhấn "Đăng nhập"',
            ],
          },
          {
            title: 'Quên mật khẩu',
            desc: 'Dùng OTP để đăng nhập (luôn có sẵn), sau đó vào Cài đặt → Bảo mật để đặt lại mật khẩu.',
          },
        ],
        tips: [
          'OTP có hiệu lực 5 phút. Nếu không nhận được, kiểm tra tin nhắn SMS hoặc thử lại sau 60 giây.',
          'Không cần đăng ký riêng — lần đầu nhập SĐT chưa có tài khoản, hệ thống tự tạo.',
        ],
      },
      {
        icon: '🖼️',
        title: 'Hồ sơ cá nhân',
        desc: 'Cập nhật tên, ảnh đại diện, ảnh bìa, tiểu sử trong trang Cài đặt.',
        steps: [
          'Nhấn avatar/tên ở góc phải trên → chọn "Cài đặt" (hoặc vào /cai-dat)',
          'Tab "Hồ sơ" mở mặc định',
          'Nhấn vào vùng avatar để tải ảnh mới (JPEG/PNG/WebP, tự động resize)',
          'Nhấn vào ảnh bìa để thay đổi',
          'Sửa tên hiển thị và tiểu sử → nhấn "Lưu"',
        ],
        subtopics: [
          {
            title: 'Trang hồ sơ công khai',
            desc: 'Trang /nguoi-dung/[id] hiển thị hồ sơ của bạn (hoặc người khác). Gồm: ảnh bìa, avatar, tên, cấp bậc, số bài viết, số người theo dõi/đang theo dõi, và danh sách bài viết.',
          },
          {
            title: 'Thanh tiến trình hoàn thiện hồ sơ',
            desc: 'Trên trang hồ sơ của bạn, thanh tiến trình cho biết bạn đã điền bao nhiêu % (tên + avatar + bio + 1 bài viết + 1 đánh giá = 20% mỗi thứ).',
          },
        ],
        link: '/cai-dat',
        linkLabel: 'Mở Cài đặt',
      },
      {
        icon: '🔒',
        title: 'Bảo mật',
        desc: 'Quản lý mật khẩu, phiên đăng nhập, và lịch sử đăng nhập.',
        steps: [
          'Vào /cai-dat → tab "Bảo mật"',
        ],
        subtopics: [
          {
            title: 'Đặt/đổi mật khẩu',
            desc: 'Nếu chưa có mật khẩu, nhấn "Đặt mật khẩu". Nếu đã có, nhập mật khẩu cũ → mật khẩu mới → xác nhận.',
          },
          {
            title: 'Quản lý phiên đăng nhập',
            desc: 'Danh sách tất cả thiết bị đang đăng nhập tài khoản. Mỗi dòng hiện: thiết bị, IP, thời gian. Phiên hiện tại có badge "Hiện tại".',
            steps: [
              'Xem danh sách phiên trong tab Bảo mật',
              'Nhấn "Thu hồi" bên cạnh phiên lạ để đăng xuất thiết bị đó',
              'Phiên bị thu hồi sẽ phải đăng nhập lại',
            ],
            tips: ['Kiểm tra phiên thường xuyên nếu bạn đăng nhập trên máy công cộng.'],
          },
          {
            title: 'Lịch sử đăng nhập',
            desc: 'Bảng ghi lại mọi lần đăng nhập (thành công/thất bại), thời gian, IP, phương thức (OTP/mật khẩu). Giúp phát hiện đăng nhập trái phép.',
          },
        ],
      },
      {
        icon: '🔔',
        title: 'Thông báo',
        desc: 'Xem thông báo hoạt động và tùy chỉnh loại thông báo muốn nhận.',
        subtopics: [
          {
            title: 'Chuông thông báo',
            desc: 'Biểu tượng 🔔 trên header hiện số thông báo chưa đọc (chấm đỏ). Nhấn để xem 5 thông báo gần nhất trong dropdown.',
          },
          {
            title: 'Trang thông báo',
            desc: 'Truy cập /thong-bao để xem tất cả. Lọc theo loại: Tất cả, Thích, Bình luận, Theo dõi, Nhắc đến. Nhấn "Đọc tất cả" để đánh dấu đã đọc.',
            steps: [
              'Nhấn vào thông báo để đi tới bài viết/người dùng liên quan',
              'Thông báo nhóm: "A và 4 người khác đã thích bài viết" — nhấn để xem chi tiết',
            ],
          },
          {
            title: 'Tùy chỉnh thông báo',
            desc: 'Vào /cai-dat → tab "Thông báo" để bật/tắt từng loại: Thích, Bình luận, Nhắc đến, Theo dõi mới. Loại bị tắt sẽ không tạo thông báo.',
          },
        ],
        link: '/thong-bao',
        linkLabel: 'Xem thông báo',
      },
      {
        icon: '🚫',
        title: 'Vô hiệu hóa tài khoản',
        desc: 'Nếu muốn tạm ngừng sử dụng, bạn có thể vô hiệu hóa tài khoản thay vì xóa.',
        steps: [
          'Vào /cai-dat → tab "Bảo mật" → cuộn xuống phần "Vùng nguy hiểm"',
          'Nhấn "Vô hiệu hóa tài khoản"',
          'Tài khoản ẩn khỏi cộng đồng, bài viết vẫn giữ, phiên đăng nhập bị thu hồi',
          'Khi muốn quay lại: đăng nhập bằng OTP — tài khoản tự động kích hoạt lại',
        ],
        warnings: [
          'Vô hiệu hóa khác với xóa. Vô hiệu hóa = tạm ẩn, có thể kích hoạt lại. Xóa = vĩnh viễn.',
        ],
      },
    ],
    faqs: [
      { q: 'Dùng email đăng ký được không?', a: 'Không. Hiện tại chỉ hỗ trợ đăng ký bằng số điện thoại + OTP. Phù hợp với thói quen người dùng Việt Nam.' },
      { q: 'Đăng nhập trên nhiều thiết bị được không?', a: 'Được. Mỗi thiết bị tạo một phiên riêng. Bạn có thể xem và thu hồi phiên trong Cài đặt → Bảo mật.' },
      { q: 'Quên số điện thoại đã đăng ký thì sao?', a: 'Liên hệ quản trị qua trang Liên hệ để được hỗ trợ xác minh và khôi phục tài khoản.' },
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
        icon: '💬',
        title: 'Chat với trợ lý AI',
        desc: 'Trợ lý AI hiểu về du lịch, ẩm thực, văn hóa Vĩnh Long – Bến Tre – Trà Vinh. Hỏi bất cứ điều gì.',
        steps: [
          'Nhấn nút 💬 ở góc phải dưới màn hình (hiện trên mọi trang)',
          'Cửa sổ chat mở ra với gợi ý câu hỏi (thay đổi theo trang bạn đang xem)',
          'Gõ câu hỏi và nhấn Enter hoặc nút gửi',
          'Trợ lý trả lời dạng streaming (từng chữ hiện ra)',
          'Nhấn nút dừng nếu muốn ngắt giữa chừng',
          'Nhấn nút 💬 lần nữa hoặc Esc để đóng',
        ],
        subtopics: [
          {
            title: 'Gợi ý theo ngữ cảnh',
            desc: 'Khi bạn đang ở trang chi tiết "Chợ nổi Cái Bè", gợi ý sẽ là: "Nên đi chợ nổi lúc mấy giờ?", "Có gì ăn ở đây?". Ở trang khám phá sẽ là gợi ý khác. Nhấn vào gợi ý để hỏi nhanh.',
          },
          {
            title: 'Giới hạn',
            desc: 'Trợ lý trả lời dựa trên dữ liệu trong hệ thống. Không có thông tin giá vé real-time hoặc tình trạng phòng.',
            tips: ['Hỏi rõ ràng sẽ được câu trả lời tốt hơn. Ví dụ: "Ăn gì ở Vĩnh Long" tốt hơn "ăn gì".'],
          },
        ],
      },
      {
        icon: '🌙',
        title: 'Chế độ tối (Dark Mode)',
        desc: 'Chuyển đổi giữa giao diện sáng và tối. Hệ thống ghi nhớ lựa chọn.',
        steps: [
          'Nhấn biểu tượng ☀️/🌙 trên header (bên trái nút Đăng nhập)',
          'Giao diện chuyển đổi ngay lập tức',
          'Lựa chọn được lưu — lần sau mở lại vẫn giữ chế độ bạn chọn',
        ],
        tips: [
          'Chế độ tối giảm mỏi mắt khi duyệt buổi tối và tiết kiệm pin trên màn hình OLED.',
        ],
      },
      {
        icon: '📤',
        title: 'Chia sẻ trang',
        desc: 'Chia sẻ bất kỳ trang nào qua link — tất cả trang đều có SEO đầy đủ (ảnh, mô tả hiện khi paste link vào Zalo/Facebook).',
        subtopics: [
          {
            title: 'Chia sẻ địa điểm',
            desc: 'Trên trang chi tiết, nhấn nút "Chia sẻ" → sao chép link hoặc mở chia sẻ hệ thống (trên di động). Link paste vào Zalo/Facebook sẽ hiện ảnh + mô tả tự động.',
          },
          {
            title: 'Chia sẻ lịch trình',
            desc: 'Lịch trình công khai có link riêng — gửi cho bạn bè để họ xem và tham khảo.',
          },
        ],
      },
      {
        icon: '🛣️',
        title: 'Tuyến đường gợi ý',
        desc: 'Các tuyến du lịch biên soạn sẵn — phù hợp cho người đi tự túc bằng xe máy hoặc ô tô.',
        steps: [
          'Truy cập /tuyen-duong',
          'Lọc theo khu vực (Vĩnh Long, Bến Tre, Trà Vinh)',
          'Mỗi tuyến gồm: tên, emoji, thời gian, quãng đường, danh sách điểm dừng',
          'Đọc mẹo di chuyển ở cuối mỗi tuyến',
          'Nhấn vào điểm dừng để xem chi tiết hoặc mở trên bản đồ',
        ],
        tips: [
          'Tuyến đường là gợi ý — bạn có thể bỏ/thêm điểm dừng bằng cách tạo lịch trình riêng dựa trên tuyến này.',
        ],
        link: '/tuyen-duong',
        linkLabel: 'Xem tuyến đường',
      },
      {
        icon: '⬆️',
        title: 'Cuộn lên đầu trang',
        desc: 'Khi cuộn xuống xa, nút mũi tên ⬆️ hiện ở góc phải dưới. Nhấn để cuộn mượt về đầu trang.',
      },
    ],
    faqs: [
      { q: 'Chat AI có lưu lịch sử không?', a: 'Lịch sử chat giữ trong phiên trình duyệt. Khi đóng tab hoặc tải lại trang, lịch sử mất. Không có lưu trữ vĩnh viễn.' },
      { q: 'Có ứng dụng di động không?', a: 'Không. vinhlong360 là web app — truy cập trực tiếp trên trình duyệt di động. Có thể "Thêm vào màn hình chính" trên iOS/Android để dùng như app.' },
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
        icon: '📒',
        title: 'Danh bạ hành chính',
        desc: 'Thông tin liên hệ UBND xã/phường: địa chỉ, số điện thoại, email, website — phục vụ tra cứu nhanh.',
        steps: [
          'Truy cập /danh-ba',
          'Chọn khu vực: Vĩnh Long, Bến Tre, hoặc Trà Vinh',
          'Chọn xã/phường từ dropdown',
          'Xem thông tin liên hệ: địa chỉ, SĐT (nhấn để gọi), email, website',
          'Nhấn "Xem trên bản đồ" để mở vị trí',
        ],
        subtopics: [
          {
            title: 'Báo thông tin sai',
            desc: 'Nếu phát hiện SĐT, địa chỉ sai — nhấn "Báo sai" để gửi yêu cầu cập nhật. Đội ngũ quản trị xem xét và sửa.',
          },
        ],
        warnings: [
          'Thông tin có thể thay đổi sau khi sáp nhập đơn vị hành chính. Xác nhận trực tiếp nếu cần.',
        ],
        link: '/danh-ba',
        linkLabel: 'Mở danh bạ',
      },
      {
        icon: '🏘️',
        title: 'Trang xã/phường',
        desc: 'Mỗi xã/phường có trang riêng với tóm tắt, sản phẩm nổi bật, địa điểm, và thông tin liên hệ.',
        subtopics: [
          {
            title: 'Truy cập',
            desc: 'Từ breadcrumb trên trang chi tiết địa điểm (ví dụ: Vĩnh Long > Long Hồ > Phú Quới), nhấn vào tên xã/phường. Hoặc từ danh bạ.',
          },
          {
            title: 'Nội dung',
            desc: 'Trang xã/phường gồm: tóm tắt giới thiệu, danh sách địa điểm thuộc xã, sản phẩm địa phương, thông tin liên hệ UBND.',
          },
        ],
      },
      {
        icon: '🗺️',
        title: 'Khu vực (3 tỉnh)',
        desc: 'Duyệt theo 3 vùng chính: Vĩnh Long, Bến Tre, Trà Vinh — mỗi khu vực có bộ sưu tập riêng.',
        steps: [
          'Nhấn vào logo khu vực ở footer (🍊 Vĩnh Long, 🥥 Bến Tre, 🛕 Trà Vinh)',
          'Hoặc truy cập /khu-vuc/vinh-long, /khu-vuc/ben-tre, /khu-vuc/tra-vinh',
          'Xem tổng quan, địa điểm nổi bật, đặc sản riêng của vùng',
        ],
      },
    ],
    faqs: [
      { q: 'Danh bạ có cập nhật theo sáp nhập hành chính không?', a: 'Hệ thống cập nhật theo thông tin mới nhất. Tuy nhiên, trong giai đoạn chuyển tiếp sáp nhập, một số thông tin có thể chưa kịp cập nhật.' },
      { q: 'Có danh bạ bệnh viện, trường học không?', a: 'Hiện tại chỉ có danh bạ cơ quan hành chính (UBND). Bệnh viện, trường học có thể có trong mục Du lịch hoặc Danh bạ sắp tới.' },
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
.guide-page { max-width: 820px; margin: 0 auto; padding: var(--space-6) var(--space-4) var(--space-10); }

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

/* TOC */
.guide-toc {
  margin-bottom: var(--space-8); padding: var(--space-5);
  background: var(--card); border: .5px solid var(--line); border-radius: var(--radius-xl);
}
.toc-title { font-size: var(--text-sm); font-weight: var(--weight-semibold); color: var(--muted); text-transform: uppercase; letter-spacing: .06em; margin: 0 0 var(--space-3); }
.toc-list { margin: 0; padding: 0; list-style: none; columns: 2; column-gap: var(--space-4); }
.toc-link {
  display: flex; align-items: center; gap: var(--space-2);
  padding: var(--space-2) var(--space-3); border-radius: var(--radius-md);
  font-size: var(--text-sm); font-weight: var(--weight-semibold); color: var(--ink); text-decoration: none;
  break-inside: avoid; transition: background .15s;
}
.toc-link:hover { background: var(--bg-warm); }
.toc-icon { font-size: 1.1rem; flex-shrink: 0; }
.toc-sub { margin: 0 0 var(--space-2); padding: 0 0 0 var(--space-6); list-style: none; }
.toc-sublink {
  display: block; padding: var(--space-1) var(--space-3);
  font-size: var(--text-xs); color: var(--muted); text-decoration: none;
  border-radius: var(--radius-sm); transition: background .15s;
}
.toc-sublink:hover { background: var(--bg-warm); color: var(--ink); }

/* Sections */
.guide-section { margin-bottom: var(--space-10); scroll-margin-top: var(--space-10); }
.guide-section > h2 {
  font-size: var(--text-xl); font-weight: var(--weight-bold); margin: 0 0 var(--space-2);
  padding-bottom: var(--space-2); border-bottom: 2px solid var(--primary-fg);
}
.section-intro { color: var(--muted); font-size: var(--text-sm); line-height: var(--leading-relaxed); margin: 0 0 var(--space-5); }

/* Topics (h3) */
.guide-topic {
  margin-bottom: var(--space-6); padding: var(--space-5);
  border: .5px solid var(--line); border-radius: var(--radius-xl);
  background: var(--card); scroll-margin-top: var(--space-10);
}
.guide-topic > h3 {
  display: flex; align-items: center; gap: var(--space-2);
  font-size: var(--text-base); font-weight: var(--weight-bold); margin: 0 0 var(--space-2);
}
.topic-icon { font-size: 1.3rem; flex-shrink: 0; }
.topic-desc { color: var(--muted); font-size: var(--text-sm); line-height: var(--leading-relaxed); margin: 0 0 var(--space-3); }

/* Steps */
.guide-steps {
  margin: var(--space-3) 0; padding: 0 0 0 var(--space-5);
  font-size: var(--text-sm); line-height: var(--leading-relaxed);
  counter-reset: step;
  list-style: none;
}
.guide-steps > li {
  position: relative; padding: var(--space-2) 0 var(--space-2) var(--space-5);
  counter-increment: step;
}
.guide-steps > li::before {
  content: counter(step);
  position: absolute; left: 0; top: var(--space-2);
  width: 1.5rem; height: 1.5rem; border-radius: 50%;
  background: var(--primary-fg); color: #fff;
  font-size: var(--text-xs); font-weight: var(--weight-bold);
  display: flex; align-items: center; justify-content: center;
}
.guide-steps--sub > li::before { background: var(--muted); }
.guide-steps > li + li { border-top: .5px dashed var(--line); }

/* Subtopics (h4) */
.subtopics { margin: var(--space-3) 0; }
.subtopic {
  padding: var(--space-3) var(--space-4);
  border-left: 3px solid var(--primary-fg);
  margin-bottom: var(--space-3); background: var(--bg-warm);
  border-radius: 0 var(--radius-md) var(--radius-md) 0;
}
.subtopic > h4 { font-size: var(--text-sm); font-weight: var(--weight-bold); margin: 0 0 var(--space-1); }
.subtopic > p { font-size: var(--text-sm); color: var(--muted); margin: 0; line-height: var(--leading-relaxed); }

/* Tips & Warnings */
.tip-box, .warn-box {
  margin-top: var(--space-3); padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-lg); font-size: var(--text-sm);
}
.tip-box { background: rgba(var(--primary-rgb, 46, 125, 50), .06); border: .5px solid rgba(var(--primary-rgb, 46, 125, 50), .15); }
.warn-box { background: rgba(255, 152, 0, .06); border: .5px solid rgba(255, 152, 0, .2); }
.tip-line, .warn-line { margin: 0; line-height: var(--leading-relaxed); color: var(--ink); }
.tip-line + .tip-line, .warn-line + .warn-line { margin-top: var(--space-2); }

/* Topic link */
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
.dark .guide-hero,
.dark .guide-cta { background: linear-gradient(135deg, rgba(255,255,255,.03) 0%, rgba(255,255,255,.01) 100%); }
.dark .guide-toc { background: var(--bg-alt); }
.dark .guide-topic { background: var(--bg-alt); }
.dark .subtopic { background: rgba(255,255,255,.03); }
.dark .tip-box { background: rgba(255,255,255,.03); border-color: rgba(255,255,255,.08); }
.dark .warn-box { background: rgba(255, 152, 0, .05); border-color: rgba(255, 152, 0, .12); }

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .faq-item > summary::before { transition: none; }
}

/* Mobile */
@media (max-width: 600px) {
  .guide-hero { flex-direction: column; text-align: center; padding: var(--space-5); }
  .toc-list { columns: 1; }
  .toc-sub { display: none; }
  .guide-topic { padding: var(--space-4); }
  .subtopic { padding: var(--space-2) var(--space-3); }
}
</style>
