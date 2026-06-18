<template>
  <div class="page contact-page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Liên hệ' }]" />

    <!-- Hero -->
    <section class="catalog-hero cat-contact">
      <div class="catalog-hero-inner">
        <span class="catalog-hero-icon">📬</span>
        <div>
          <h1>Liên hệ</h1>
          <p>vinhlong360.vn — Mạng xã hội du lịch & đặc sản Vĩnh Long · Bến Tre · Trà Vinh</p>
        </div>
      </div>
    </section>

    <div class="contact-cards">
      <section v-if="isClaim" class="contact-card card-claim">
        <div class="card-icon">🏷️</div>
        <h2>Đăng ký quản lý trang</h2>
        <p>Bạn là chủ cơ sở kinh doanh, homestay, nhà vườn, hoặc điểm du lịch? Đăng ký để cập nhật thông tin, ảnh, giờ mở cửa và nhận đánh giá từ khách.</p>
        <div class="card-action">
          <a href="mailto:lienhe@vinhlong360.vn?subject=Đăng ký quản lý trang" class="btn btn-primary">📧 Gửi email đăng ký</a>
        </div>
        <p class="card-note">Hoặc nhắn Zalo: <strong>vinhlong360</strong></p>
      </section>

      <section class="contact-card card-general">
        <div class="card-icon">📬</div>
        <h2>Gửi yêu cầu</h2>
        <p>Mọi yêu cầu về nội dung, dữ liệu cá nhân, báo cáo vi phạm hoặc khiếu nại bản quyền.</p>
        <div class="card-action">
          <a href="mailto:lienhe@vinhlong360.vn" class="btn btn-primary">📧 lienhe@vinhlong360.vn</a>
        </div>
      </section>

      <section class="contact-card card-partner">
        <div class="card-icon">🤝</div>
        <h2>Hợp tác quảng bá</h2>
        <p>Đối tác du lịch, OCOP, cơ quan địa phương muốn giới thiệu sản phẩm, điểm đến trên vinhlong360.</p>
        <div class="card-action">
          <a href="mailto:lienhe@vinhlong360.vn?subject=Hợp tác quảng bá" class="btn btn-outline">📧 Liên hệ hợp tác</a>
        </div>
      </section>

      <section class="contact-card card-report">
        <div class="card-icon">🛡️</div>
        <h2>Báo cáo vi phạm</h2>
        <p>Dùng nút <strong>Báo cáo</strong> ngay trên mỗi bài đăng/bình luận. Chúng tôi xử lý trong vòng 48 giờ.</p>
      </section>

      <section class="contact-card card-privacy">
        <div class="card-icon">🔒</div>
        <h2>Dữ liệu cá nhân</h2>
        <p>Theo <NuxtLink to="/chinh-sach-bao-mat">Chính sách bảo mật</NuxtLink>: truy cập/chỉnh sửa (10 ngày), rút đồng ý (15 ngày), xoá dữ liệu (20 ngày). Bạn cũng có thể tự xoá tài khoản trong phần tài khoản.</p>
      </section>
    </div>

    <!-- Cross-links -->
    <section class="block catalog-cross reveal">
      <h2>Xem thêm</h2>
      <div class="cross-links">
        <NuxtLink to="/cong-dong" class="cross-card">
          <span class="cross-icon">💬</span>
          <div><strong>Cộng đồng</strong><p>Hỏi đáp & chia sẻ</p></div>
        </NuxtLink>
        <NuxtLink to="/chinh-sach-bao-mat" class="cross-card">
          <span class="cross-icon">🔒</span>
          <div><strong>Bảo mật</strong><p>Chính sách dữ liệu</p></div>
        </NuxtLink>
        <NuxtLink to="/dieu-khoan-su-dung" class="cross-card">
          <span class="cross-icon">📄</span>
          <div><strong>Điều khoản</strong><p>Điều khoản sử dụng</p></div>
        </NuxtLink>
        <NuxtLink to="/" class="cross-card">
          <span class="cross-icon">🏠</span>
          <div><strong>Trang chủ</strong><p>Về trang chủ</p></div>
        </NuxtLink>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
useReveal()

const route = useRoute()
const isClaim = computed(() => route.query.ref === 'claim')

useSeoMeta({
  title: 'Liên hệ — vinhlong360',
  description: 'Liên hệ vinhlong360.vn: yêu cầu dữ liệu cá nhân, báo cáo vi phạm, khiếu nại bản quyền, đăng ký quản lý trang.',
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

.card-icon {
  font-size: var(--text-2xl);
  margin-bottom: var(--space-2);
  transition: transform .35s var(--ease-spring-gentle);
}
.contact-card:hover .card-icon { transform: scale(1.1) rotate(-3deg); }

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

.card-action { margin: var(--space-4) 0 var(--space-2); }
.card-action .btn { min-height: 44px; }

.card-note {
  font-size: var(--text-xs) !important;
  color: var(--muted) !important;
  margin-top: var(--space-1);
}

.card-claim {
  border-color: var(--accent);
  border-width: 2px;
  background: color-mix(in srgb, var(--accent) 4%, var(--card));
}

@media (min-width: 640px) {
  .contact-cards {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--space-5);
  }
  .card-claim, .card-general { grid-column: span 2; }
}

</style>
