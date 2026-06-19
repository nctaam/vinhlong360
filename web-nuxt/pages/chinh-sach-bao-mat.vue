<template>
  <main class="legal-page">
    <h1>Chính sách bảo mật</h1>
    <p class="legal-updated">Cập nhật: 13/06/2026</p>

    <p>vinhlong360.vn ("chúng tôi") tôn trọng quyền riêng tư của bạn và tuân thủ Luật Bảo vệ
    dữ liệu cá nhân (Luật 91/2025/QH15) cùng Nghị định 356/2025/NĐ-CP của Việt Nam.</p>

    <h2>1. Dữ liệu chúng tôi thu thập</h2>
    <ul>
      <li><strong>Số điện thoại</strong> — để xác thực đăng nhập bằng OTP.</li>
      <li><strong>Tên hiển thị, ảnh đại diện</strong> (tuỳ chọn) — để hiển thị trong cộng đồng.</li>
      <li><strong>Nội dung bạn đăng</strong> — bài viết, đánh giá, bình luận, ảnh.</li>
      <li><strong>Dữ liệu sử dụng</strong> — truy vấn tìm kiếm/hỏi đáp để cải thiện dịch vụ (ẩn danh khi có thể).</li>
    </ul>

    <h2>2. Mục đích sử dụng</h2>
    <p>Xác thực tài khoản, hiển thị nội dung cộng đồng, kiểm duyệt, cải thiện chất lượng tìm kiếm
    và gợi ý du lịch. Chúng tôi <strong>không bán</strong> dữ liệu cá nhân của bạn.</p>

    <h2>3. Lưu trữ & bảo mật</h2>
    <p>Dữ liệu được lưu trên hạ tầng có kiểm soát truy cập. Mã OTP được băm (hash), không lưu dạng thô.
    Chúng tôi giữ dữ liệu trong thời gian cần thiết cho mục đích nêu trên hoặc theo yêu cầu pháp luật.</p>

    <h2>4. Quyền của bạn</h2>
    <ul>
      <li><strong>Truy cập / chỉnh sửa</strong> thông tin tài khoản — phản hồi trong vòng 10 ngày.</li>
      <li><strong>Rút lại đồng ý</strong> — trong vòng 15 ngày.</li>
      <li><strong>Xoá tài khoản & dữ liệu</strong> — trong vòng 20 ngày. Bạn có thể tự xoá trong phần tài khoản,
      hoặc gửi yêu cầu qua trang <NuxtLink to="/lien-he">Liên hệ</NuxtLink>.</li>
    </ul>

    <h2>5. Sự cố dữ liệu</h2>
    <p>Khi xảy ra rò rỉ dữ liệu cá nhân, chúng tôi thông báo cho cơ quan có thẩm quyền trong vòng 72 giờ
    và thông báo cho người dùng bị ảnh hưởng theo quy định.</p>

    <h2>6. Liên hệ</h2>
    <p>Mọi yêu cầu về dữ liệu cá nhân, vui lòng liên hệ qua trang
    <NuxtLink to="/lien-he">Liên hệ</NuxtLink>.</p>
  </main>
</template>

<script setup lang="ts">
useReveal()
useSeoMeta({
  title: 'Chính sách bảo mật — vinhlong360',
  description: 'Chính sách bảo mật dữ liệu cá nhân của vinhlong360.vn theo Luật Bảo vệ dữ liệu cá nhân Việt Nam.',
})
</script>

<style scoped>
.legal-page { max-width: 760px; margin: 0 auto; padding: var(--space-8) var(--space-5) var(--space-16); line-height: var(--leading-relaxed); }
.legal-page h1 { font-size: var(--text-2xl); font-weight: var(--weight-bold); letter-spacing: var(--tracking-tight); margin-bottom: var(--space-1); }
.legal-page h2 { font-size: var(--text-lg); font-weight: var(--weight-semibold); margin: var(--space-8) 0 var(--space-3); padding-bottom: var(--space-2); border-bottom: .5px solid var(--line); }
.legal-updated { color: var(--muted); font-size: var(--text-sm); margin-bottom: var(--space-6); }
.legal-page p { font-size: var(--text-sm); color: var(--ink-secondary, var(--ink)); }
.legal-page ul { padding-inline-start: var(--space-5); }
.legal-page li { margin: var(--space-2) 0; font-size: var(--text-sm); color: var(--ink-secondary, var(--ink)); }
.legal-page a { color: var(--primary-fg); font-weight: var(--weight-semibold); text-decoration-line: underline; text-decoration-color: transparent; text-underline-offset: 3px; transition: text-decoration-color .3s var(--ease-out); }
.legal-page a:hover { text-decoration-color: var(--primary-fg); }
.legal-page a:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
</style>
