<template>
  <main class="legal-page">
    <h1>Điều khoản sử dụng</h1>
    <p class="legal-updated">Cập nhật: 13/06/2026</p>

    <p>Khi sử dụng vinhlong360.vn, bạn đồng ý với các điều khoản dưới đây.</p>

    <h2>1. Tài khoản</h2>
    <p>Bạn đăng nhập bằng số điện thoại qua mã OTP. Bạn chịu trách nhiệm về hoạt động dưới tài khoản của mình
    và phải xác thực số điện thoại trước khi đăng nội dung.</p>

    <h2>2. Nội dung người dùng</h2>
    <ul>
      <li>Bạn giữ quyền với nội dung mình đăng, nhưng cấp cho chúng tôi quyền hiển thị nội dung đó trên nền tảng.</li>
      <li>Không đăng nội dung vi phạm pháp luật, sai sự thật, xúc phạm, spam, hoặc xâm phạm bản quyền/quyền riêng tư của người khác.</li>
      <li>Chúng tôi có quyền gỡ nội dung vi phạm và khoá tài khoản tái phạm.</li>
    </ul>

    <h2>3. Báo cáo & gỡ nội dung</h2>
    <p>Bạn có thể <strong>báo cáo</strong> nội dung vi phạm bằng nút Báo cáo. Chúng tôi xử lý khiếu nại của người dùng
    trong vòng 48 giờ và yêu cầu gỡ bỏ từ cơ quan có thẩm quyền trong vòng 24 giờ theo Nghị định 147/2024/NĐ-CP.</p>

    <h2>4. Nội dung từ nguồn bên thứ ba</h2>
    <p>Một số thông tin được tổng hợp từ nguồn công khai, có <strong>trích dẫn nguồn và liên kết gốc</strong>.
    Bản quyền thuộc về tác giả/đơn vị gốc.</p>

    <h2>5. Miễn trừ trách nhiệm</h2>
    <p>Thông tin du lịch/đặc sản mang tính tham khảo; giá, giờ mở cửa, mùa vụ có thể thay đổi.
    Vui lòng kiểm chứng trước khi sử dụng.</p>

    <h2>6. Liên hệ</h2>
    <p>Thắc mắc về điều khoản: xem trang <NuxtLink to="/lien-he">Liên hệ</NuxtLink>.
    Xem thêm <NuxtLink to="/chinh-sach-bao-mat">Chính sách bảo mật</NuxtLink>.</p>
  </main>
</template>

<script setup lang="ts">
useReveal()
useSeoMeta({
  title: 'Điều khoản sử dụng — vinhlong360',
  description: 'Điều khoản sử dụng nền tảng vinhlong360.vn: tài khoản, nội dung người dùng, báo cáo & gỡ nội dung.',
})
</script>

<style scoped>
.legal-page { max-width: 760px; margin: 0 auto; padding: var(--space-8) var(--space-5) var(--space-16); line-height: var(--leading-relaxed); }
.legal-page h1 { font-size: var(--text-2xl); font-weight: var(--weight-bold); letter-spacing: var(--tracking-tight); margin-bottom: var(--space-1); }
.legal-page h2 { font-size: var(--text-lg); font-weight: var(--weight-semibold); margin: var(--space-8) 0 var(--space-3); padding-bottom: var(--space-2); border-bottom: .5px solid var(--line); }
.legal-updated { color: var(--muted); font-size: var(--text-sm); margin-bottom: var(--space-6); }
.legal-page p { font-size: var(--text-sm); color: var(--ink-secondary, var(--ink)); }
.legal-page ul { padding-left: var(--space-5); }
.legal-page li { margin: var(--space-2) 0; font-size: var(--text-sm); color: var(--ink-secondary, var(--ink)); }
.legal-page a { color: var(--primary-fg); font-weight: var(--weight-semibold); text-decoration-line: underline; text-decoration-color: transparent; text-underline-offset: 3px; transition: text-decoration-color .3s var(--ease-out); }
.legal-page a:hover { text-decoration-color: var(--primary-fg); }
.legal-page a:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
</style>
