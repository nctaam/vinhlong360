<template>
  <main class="guide-page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Hướng dẫn sử dụng' }]" />

    <header class="guide-hero">
      <span class="guide-hero-icon" aria-hidden="true">📖</span>
      <div>
        <h1>Hướng dẫn sử dụng</h1>
        <p>Tất cả tính năng của vinhlong360 — từ khám phá địa điểm, tạo lịch trình đến tham gia cộng đồng.</p>
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
        </li>
      </ol>
    </nav>

    <!-- Sections -->
    <section v-for="s in sections" :key="s.id" :id="s.id" class="guide-section reveal">
      <h2>
        <span class="section-icon" aria-hidden="true">{{ s.icon }}</span>
        {{ s.title }}
      </h2>

      <div class="guide-cards">
        <div v-for="(item, i) in s.items" :key="i" class="guide-card">
          <div class="card-header">
            <span class="card-icon" aria-hidden="true">{{ item.icon }}</span>
            <strong>{{ item.title }}</strong>
          </div>
          <p>{{ item.desc }}</p>
          <NuxtLink v-if="item.link" :to="item.link" class="card-link">
            {{ item.linkLabel || 'Đi tới' }} →
          </NuxtLink>
        </div>
      </div>

      <div v-if="s.tips?.length" class="guide-tips">
        <p v-for="(tip, i) in s.tips" :key="i" class="tip-line">
          <span aria-hidden="true">💡</span> {{ tip }}
        </p>
      </div>
    </section>

    <!-- Quick reference -->
    <section id="phim-tat" class="guide-section reveal">
      <h2>
        <span class="section-icon" aria-hidden="true">⌨️</span>
        Phím tắt & thao tác nhanh
      </h2>
      <div class="shortcut-table-wrap">
        <table class="shortcut-table">
          <thead>
            <tr><th>Thao tác</th><th>Cách làm</th></tr>
          </thead>
          <tbody>
            <tr v-for="(sc, i) in shortcuts" :key="i">
              <td>{{ sc.action }}</td>
              <td>{{ sc.how }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- CTA -->
    <section class="guide-cta reveal">
      <h2>Bắt đầu khám phá ngay!</h2>
      <p>Mỗi tính năng đều miễn phí. Không cần đăng ký để duyệt — chỉ cần tài khoản khi muốn đóng góp nội dung.</p>
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

const sections = [
  {
    id: 'tim-kiem',
    icon: '🔍',
    title: 'Tìm kiếm & Khám phá',
    items: [
      { icon: '🔎', title: 'Thanh tìm kiếm', desc: 'Gõ tên địa điểm, món ăn, sản phẩm — kết quả gợi ý hiện ngay khi gõ. Nhấn Enter để xem đầy đủ (địa điểm, bài viết, người dùng).', link: '/tim-kiem', linkLabel: 'Tìm kiếm' },
      { icon: '📂', title: 'Danh mục', desc: 'Duyệt theo chủ đề: Du lịch, Ẩm thực, OCOP, Lễ hội, Sự kiện. Mỗi danh mục có bộ lọc riêng (loại hình, mùa, khu vực).', link: '/du-lich', linkLabel: 'Xem danh mục' },
      { icon: '🍊', title: 'Theo mùa', desc: 'Xem đặc sản và trải nghiệm đang vào mùa. Chọn tháng bất kỳ trên lưới 12 tháng để xem sản phẩm tương ứng.', link: '/theo-mua', linkLabel: 'Xem theo mùa' },
      { icon: '🧭', title: 'Khám phá theo chủ đề', desc: 'Bộ sưu tập theo sở thích: Ẩm thực, Thiên nhiên, Văn hóa, Làng nghề, Mua sắm — mỗi chủ đề có giới thiệu và lọc theo khu vực.', link: '/kham-pha/am-thuc', linkLabel: 'Khám phá' },
    ],
    tips: ['Trên trang chủ, nhấn vào các pill nhanh (Cuối tuần, Ẩm thực, OCOP...) để tìm nhanh theo nhu cầu.'],
  },
  {
    id: 'ban-do',
    icon: '🗺️',
    title: 'Bản đồ tương tác',
    items: [
      { icon: '📍', title: 'Xem trên bản đồ', desc: 'Tất cả địa điểm hiển thị trên bản đồ. Kéo, zoom, nhấn vào điểm đánh dấu để xem thông tin nhanh và liên kết chi tiết.', link: '/ban-do', linkLabel: 'Mở bản đồ' },
      { icon: '🏷️', title: 'Lọc theo loại', desc: 'Dùng chip lọc phía trên bản đồ: Tham quan, Trải nghiệm, Thiên nhiên, Lịch sử, Ẩm thực, Làng nghề, Lưu trú, Đặc sản.' },
      { icon: '🔵', title: 'Nhóm điểm (clustering)', desc: 'Khi zoom ra, các điểm gần nhau gom thành cụm với số lượng. Nhấn vào cụm để zoom vào xem chi tiết từng điểm.' },
    ],
  },
  {
    id: 'dia-diem',
    icon: '📋',
    title: 'Chi tiết địa điểm',
    items: [
      { icon: '📸', title: 'Thư viện ảnh', desc: 'Nhấn vào ảnh bìa hoặc nút "X ảnh" để mở lightbox toàn màn hình. Dùng phím ← → hoặc vuốt trên di động để chuyển ảnh.' },
      { icon: '📞', title: 'Liên hệ nhanh', desc: 'Số điện thoại (nhấn để gọi), Zalo, bản đồ, giờ mở cửa, giá — hiển thị ngay đầu trang.' },
      { icon: '📅', title: 'Mùa & thời điểm', desc: 'Lưới 12 tháng cho biết tháng nào cao điểm, tháng nào phù hợp. Kèm gợi ý thời điểm lý tưởng.' },
      { icon: '🔗', title: 'Liên kết & lân cận', desc: 'Địa điểm liên quan, điểm đến gần đó cùng khu vực — giúp lên kế hoạch dễ hơn.' },
    ],
    tips: ['Nhấn ❤️ Lưu để thêm vào danh sách yêu thích, sau đó dùng danh sách này khi tạo lịch trình.'],
  },
  {
    id: 'lich-trinh',
    icon: '📋',
    title: 'Lịch trình',
    items: [
      { icon: '📝', title: 'Xem lịch trình gợi ý', desc: 'Duyệt lịch trình sẵn có theo khu vực (Vĩnh Long, Bến Tre, Trà Vinh). Mỗi lịch trình gồm các điểm dừng, thời gian, quãng đường.', link: '/lich-trinh', linkLabel: 'Xem lịch trình' },
      { icon: '✏️', title: 'Tự tạo lịch trình', desc: 'Chọn điểm từ danh sách hoặc từ mục "Đã lưu". Sắp xếp thứ tự bằng nút ↑↓. Ghi thời gian, ghi chú cho từng điểm dừng.', link: '/tao-lich-trinh', linkLabel: 'Tạo mới' },
      { icon: '🚗', title: 'Phương tiện & khoảng cách', desc: 'Chọn ô tô, xe máy, hoặc xuồng — hệ thống tính tổng quãng đường và thời gian di chuyển giữa các điểm.' },
      { icon: '🔗', title: 'Chia sẻ & công khai', desc: 'Lịch trình đã lưu có thể đặt công khai hoặc riêng tư. Chia sẻ link cho bạn bè.' },
    ],
  },
  {
    id: 'cong-dong',
    icon: '👥',
    title: 'Cộng đồng',
    items: [
      { icon: '✍️', title: 'Viết bài & đánh giá', desc: 'Đăng nhập, chọn loại (Bài viết, Đánh giá, Ảnh...), viết nội dung, đính kèm ảnh. Gõ @ để tag người dùng hoặc địa điểm.', link: '/cong-dong', linkLabel: 'Cộng đồng' },
      { icon: '❤️', title: 'Tương tác', desc: 'Thích, bình luận, lưu bài viết. Theo dõi người dùng để xem bài mới trong tab "Đang theo dõi".' },
      { icon: '🏆', title: 'Bảng xếp hạng', desc: 'Thành viên tích cực nhất xếp theo điểm danh tiếng. Đóng góp đa dạng (đánh giá + ảnh + khám phá) để tăng điểm nhanh.', link: '/bang-xep-hang', linkLabel: 'Xem xếp hạng' },
      { icon: '🏅', title: 'Cấp bậc & huy hiệu', desc: 'Hệ thống 4 cấp (Người mới → Đại sứ) và huy hiệu thành tích. Điểm giảm dần khi tập trung một loại đóng góp.', link: '/huong-dan-thanh-vien', linkLabel: 'Chi tiết cấp bậc' },
    ],
    tips: [
      'Đánh giá mang nhiều điểm nhất (5 điểm/bài cho 10 bài đầu). Kèm ảnh để tăng thêm điểm.',
      'Dùng tab "Nổi bật" để xem bài hay nhất, "Mới nhất" để theo dõi cập nhật.',
    ],
  },
  {
    id: 'tai-khoan',
    icon: '👤',
    title: 'Tài khoản & Cài đặt',
    items: [
      { icon: '📱', title: 'Đăng ký / Đăng nhập', desc: 'Nhập số điện thoại → nhận mã OTP 6 số → xác nhận. Lần đầu có thể đặt mật khẩu (hoặc bỏ qua, dùng OTP mỗi lần).' },
      { icon: '🖼️', title: 'Hồ sơ cá nhân', desc: 'Cập nhật tên hiển thị, ảnh đại diện, ảnh bìa, tiểu sử trong Cài đặt → Hồ sơ.', link: '/cai-dat', linkLabel: 'Cài đặt' },
      { icon: '🔒', title: 'Bảo mật', desc: 'Đặt/đổi mật khẩu, xem phiên đăng nhập đang hoạt động (thu hồi nếu cần), xem lịch sử đăng nhập.' },
      { icon: '🔔', title: 'Thông báo', desc: 'Bật/tắt từng loại thông báo (thích, bình luận, theo dõi, nhắc đến). Xem tất cả trong trang Thông báo, lọc theo loại.', link: '/thong-bao', linkLabel: 'Thông báo' },
    ],
  },
  {
    id: 'cong-cu',
    icon: '🛠️',
    title: 'Công cụ tiện ích',
    items: [
      { icon: '💬', title: 'Chat AI', desc: 'Nhấn nút 💬 góc phải dưới để hỏi trợ lý AI. Gợi ý thay đổi theo trang bạn đang xem — hỏi về địa điểm, ẩm thực, lịch trình, mùa vụ...' },
      { icon: '🌙', title: 'Chế độ tối', desc: 'Nhấn biểu tượng ☀️/🌙 trên thanh header để chuyển đổi sáng/tối. Hệ thống ghi nhớ lựa chọn.' },
      { icon: '❤️', title: 'Lưu yêu thích', desc: 'Nhấn ❤️ trên bất kỳ địa điểm nào. Xem lại trong hồ sơ cá nhân (tab Đã lưu) hoặc khi tạo lịch trình.' },
      { icon: '📤', title: 'Chia sẻ', desc: 'Nhấn nút chia sẻ trên trang chi tiết để sao chép link hoặc gửi qua mạng xã hội.' },
    ],
  },
  {
    id: 'danh-ba',
    icon: '🏛️',
    title: 'Thông tin hành chính',
    items: [
      { icon: '📒', title: 'Danh bạ hành chính', desc: 'Thông tin liên hệ UBND xã/phường: số điện thoại, email, website — phục vụ tra cứu nhanh cho người dân và du khách.', link: '/danh-ba', linkLabel: 'Xem danh bạ' },
      { icon: '🏘️', title: 'Trang xã/phường', desc: 'Mỗi xã/phường có trang riêng với tóm tắt, sản phẩm, địa điểm, liên hệ — truy cập từ breadcrumb hoặc danh bạ.' },
      { icon: '🗺️', title: 'Khu vực', desc: 'Xem theo 3 vùng (Vĩnh Long, Bến Tre, Trà Vinh) — mỗi khu vực có bộ sưu tập địa điểm và đặc sản riêng.' },
      { icon: '🛣️', title: 'Tuyến đường gợi ý', desc: 'Các tuyến du lịch sẵn có với bản đồ, khoảng cách, và các điểm dừng trên đường.', link: '/tuyen-duong', linkLabel: 'Xem tuyến đường' },
    ],
  },
]

const shortcuts = [
  { action: 'Tìm kiếm nhanh', how: 'Nhấn vào thanh tìm kiếm trên header, gõ và chọn kết quả' },
  { action: 'Chuyển ảnh trong lightbox', how: 'Phím ← → hoặc vuốt trái/phải (di động)' },
  { action: 'Đóng lightbox/modal', how: 'Phím Esc hoặc nhấn nút ✕' },
  { action: 'Chuyển dark mode', how: 'Nhấn biểu tượng ☀️/🌙 trên header' },
  { action: 'Lưu yêu thích', how: 'Nhấn ❤️ trên trang chi tiết địa điểm' },
  { action: 'Tag người/địa điểm', how: 'Gõ @ khi viết bài trong cộng đồng' },
  { action: 'Gọi điện cho cơ sở', how: 'Nhấn số điện thoại trên trang chi tiết' },
  { action: 'Chat AI', how: 'Nhấn nút 💬 góc phải dưới màn hình' },
]

useSeoMeta({
  title: 'Hướng dẫn sử dụng — vinhlong360',
  description: 'Hướng dẫn đầy đủ cách sử dụng vinhlong360: tìm kiếm, bản đồ, lịch trình, cộng đồng, chat AI, cài đặt tài khoản và nhiều tính năng khác.',
  ogTitle: 'Hướng dẫn sử dụng — vinhlong360',
  ogDescription: 'Cẩm nang đầy đủ tất cả tính năng trên vinhlong360 — khám phá, lịch trình, cộng đồng, bản đồ, chat AI.',
})
useHead({ link: [{ rel: 'canonical', href: canonicalUrl('/huong-dan') }] })
</script>

<style scoped>
.guide-page { max-width: 800px; margin: 0 auto; padding: var(--space-6) var(--space-4) var(--space-10); }

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
  font-size: var(--text-sm); color: var(--ink); text-decoration: none;
  break-inside: avoid;
  transition: background .15s;
}
.toc-link:hover { background: var(--bg-warm); }
.toc-icon { font-size: 1.1rem; flex-shrink: 0; }

/* Sections */
.guide-section { margin-bottom: var(--space-8); scroll-margin-top: var(--space-10); }
.guide-section > h2 {
  display: flex; align-items: center; gap: var(--space-3);
  font-size: var(--text-xl); font-weight: var(--weight-bold); margin: 0 0 var(--space-4);
  padding-bottom: var(--space-2); border-bottom: .5px solid var(--line);
}
.section-icon { font-size: 1.4rem; }

/* Cards */
.guide-cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: var(--space-3); }
.guide-card {
  padding: var(--space-4); border-radius: var(--radius-lg);
  border: .5px solid var(--line); background: var(--card);
  transition: transform .2s var(--ease-spring-gentle), border-color .2s;
}
.guide-card:hover { transform: translateY(-2px); border-color: var(--primary-fg); }
.card-header { display: flex; align-items: center; gap: var(--space-2); margin-bottom: var(--space-2); }
.card-icon { font-size: 1.2rem; flex-shrink: 0; }
.card-header strong { font-size: var(--text-sm); }
.guide-card p { margin: 0 0 var(--space-2); font-size: var(--text-sm); color: var(--muted); line-height: var(--leading-relaxed); }
.card-link { font-size: var(--text-sm); font-weight: var(--weight-semibold); color: var(--primary-fg); text-decoration: none; }
.card-link:hover { text-decoration: underline; }

/* Tips */
.guide-tips { margin-top: var(--space-3); padding: var(--space-3) var(--space-4); background: var(--bg-warm); border-radius: var(--radius-lg); }
.tip-line { margin: 0; font-size: var(--text-sm); color: var(--muted); line-height: var(--leading-relaxed); }
.tip-line + .tip-line { margin-top: var(--space-2); }

/* Shortcuts */
.shortcut-table-wrap { overflow-x: auto; }
.shortcut-table { width: 100%; border-collapse: collapse; font-size: var(--text-sm); }
.shortcut-table th { text-align: left; padding: var(--space-2) var(--space-3); font-weight: var(--weight-semibold); color: var(--muted); border-bottom: 1.5px solid var(--line); font-size: var(--text-xs); text-transform: uppercase; letter-spacing: .04em; }
.shortcut-table td { padding: var(--space-3); border-bottom: .5px solid var(--line); }
.shortcut-table tbody tr:hover { background: var(--bg-warm); }

/* CTA */
.guide-cta {
  text-align: center; padding: var(--space-8) var(--space-4); margin-top: var(--space-4);
  background: linear-gradient(135deg, rgba(var(--primary-rgb, 46, 125, 50), .06) 0%, var(--bg-warm) 100%);
  border-radius: var(--radius-xl); border: .5px solid var(--line);
}
.guide-cta h2 { border-bottom: none; padding-bottom: 0; font-size: var(--text-xl); justify-content: center; }
.guide-cta p { color: var(--muted); font-size: var(--text-sm); margin: var(--space-2) 0 var(--space-5); }
.cta-btns { display: flex; gap: var(--space-3); justify-content: center; flex-wrap: wrap; }

.guide-updated { text-align: center; color: var(--ink-tertiary); font-size: var(--text-xs); margin-top: var(--space-6); }

/* Dark */
.dark .guide-hero,
.dark .guide-cta { background: linear-gradient(135deg, rgba(255,255,255,.03) 0%, rgba(255,255,255,.01) 100%); }
.dark .guide-toc { background: var(--bg-alt); }
.dark .guide-tips { background: var(--bg-alt); }

/* Reduced motion */
@media (prefers-reduced-motion: reduce) { .guide-card:hover { transform: none; } }

/* Mobile */
@media (max-width: 600px) {
  .guide-hero { flex-direction: column; text-align: center; padding: var(--space-5); }
  .toc-list { columns: 1; }
  .guide-cards { grid-template-columns: 1fr; }
}
</style>
