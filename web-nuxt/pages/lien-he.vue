<template>
  <main class="legal-page">
    <h1>Liên hệ</h1>
    <p class="legal-updated">vinhlong360.vn — Mạng xã hội du lịch & đặc sản Vĩnh Long (Vĩnh Long · Bến Tre · Trà Vinh)</p>

    <h2>Gửi yêu cầu</h2>
    <p>Mọi yêu cầu về nội dung, dữ liệu cá nhân (truy cập / chỉnh sửa / xoá tài khoản / rút đồng ý),
    báo cáo vi phạm hoặc khiếu nại bản quyền, vui lòng gửi tới:</p>
    <ul>
      <li><strong>Email:</strong> <a href="mailto:lienhe@vinhlong360.vn">lienhe@vinhlong360.vn</a></li>
    </ul>

    <h2>Báo cáo nội dung vi phạm</h2>
    <p>Bạn có thể dùng nút <strong>Báo cáo</strong> ngay trên mỗi bài đăng/bình luận. Chúng tôi xử lý
    trong vòng 48 giờ.</p>

    <h2>Yêu cầu về dữ liệu cá nhân</h2>
    <p>Theo <NuxtLink to="/chinh-sach-bao-mat">Chính sách bảo mật</NuxtLink>: truy cập/chỉnh sửa (10 ngày),
    rút đồng ý (15 ngày), xoá dữ liệu (20 ngày). Bạn cũng có thể tự xoá tài khoản trong phần tài khoản.</p>
  </main>
</template>

<script setup lang="ts">
useSeoMeta({
  title: 'Liên hệ — vinhlong360',
  description: 'Liên hệ vinhlong360.vn: yêu cầu dữ liệu cá nhân, báo cáo vi phạm, khiếu nại bản quyền.',
})
</script>

<style scoped>
.legal-page { max-width: 760px; margin: 0 auto; padding: 32px 20px 64px; line-height: 1.7; }
.legal-page h1 { font-size: 1.8rem; margin-bottom: 4px; }
.legal-page h2 { font-size: 1.15rem; margin: 28px 0 8px; }
.legal-updated { color: var(--text-muted, #888); font-size: .9rem; margin-bottom: 20px; }
.legal-page ul { padding-left: 20px; }
.legal-page li { margin: 6px 0; }
</style>
