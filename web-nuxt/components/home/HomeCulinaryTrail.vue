<template>
  <section class="home-culinary-trail block reveal" aria-label="Thiên Đường Ẩm Thực Miệt Vườn Vĩnh Long" data-home-culinary-trail>
    <div class="home-culinary-trail__head section-head">
      <div class="sh-text">
        <span class="home-culinary-trail__eyebrow" data-color-role="brand">
          <IconLine name="bowl" />
          <span>Vinh Long Culinary Trail · Vị ngon đất phù sa</span>
        </span>
        <h2>Thiên Đường Ẩm Thực <em class="editorial-italic-accent" aria-hidden="true">Miệt Vườn</em></h2>
        <p class="sh-sub">5 món ăn trứ danh đã làm say lòng bao thế hệ lữ khách, kết tinh từ cá tôm sông Cổ Chiên và rau vườn phù sa màu mỡ.</p>
      </div>
      <NuxtLink to="/kham-pha/am-thuc" class="see-all">
        <span>Xem trọn bộ 120 món ngon di sản</span>
        <IconLine name="arrow-right" class="inline-arrow" aria-hidden="true" />
      </NuxtLink>
    </div>

    <div class="home-culinary-trail__grid">
      <article
        v-for="(dish, index) in SIGNATURE_DISHES"
        :key="dish.id"
        class="home-culinary-card"
        :class="{ 'home-culinary-card--lead': index === 0 }"
        data-culinary-card
      >
        <div class="home-culinary-card__media">
          <img
            class="home-culinary-card__img"
            :src="dish.coverSrc"
            :alt="dish.name"
            width="600"
            height="400"
            loading="lazy"
            decoding="async"
            @error="onImgFallback"
          >
          <span class="home-culinary-card__rank">#0{{ index + 1 }}</span>
          <span class="home-culinary-card__badge">{{ dish.badge }}</span>
        </div>

        <div class="home-culinary-card__body">
          <div class="home-culinary-card__header">
            <h3 class="home-culinary-card__title">
              <NuxtLink :to="dish.to">{{ dish.name }}</NuxtLink>
            </h3>
            <span class="home-culinary-card__origin">{{ dish.origin }}</span>
          </div>

          <p class="home-culinary-card__guide">{{ dish.guide }}</p>

          <div class="home-culinary-card__venues">
            <span class="home-culinary-card__venue-label">
              <IconLine name="pin" />
              <span>Tọa độ quán uy tín:</span>
            </span>
            <span class="home-culinary-card__venue-names">{{ dish.venues }}</span>
          </div>

          <div class="home-culinary-card__footer">
            <NuxtLink :to="dish.to" class="home-culinary-card__btn">
              <span>Xem công thức & tọa độ</span>
              <IconLine name="arrow-right" aria-hidden="true" />
            </NuxtLink>
          </div>
        </div>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
import IconLine from '~/components/IconLine.vue'

interface CulinaryDish {
  readonly id: string
  readonly name: string
  readonly badge: string
  readonly origin: string
  readonly guide: string
  readonly venues: string
  readonly coverSrc: string
  readonly to: string
}

const SIGNATURE_DISHES: readonly CulinaryDish[] = [
  {
    id: 'ca-tai-tuong-chien-xu',
    name: 'Cá Tai Tượng Chiên Xù Cuốn Bánh Tráng Cù Lao',
    badge: 'Đệ nhất mỹ vị sông Tiền',
    origin: 'Cù Lao An Bình & Sông Cổ Chiên',
    guide: 'Cá tươi thả ngập dầu sôi để vây xòe giòn rụm màu cánh gián, thịt trắng mềm ngọt đậm đà, cuốn bánh tráng nem cù lao, rau rừng và chấm nước mắm me sánh mịn.',
    venues: 'Quán Cá Tai Tượng Chín Thảo · KDL Sinh Thái Vinh Sang · Homestay Út Trinh',
    coverSrc: '/img/entities/ca-tai-tuong-chien-xu.webp',
    to: '/dia-diem/ca-tai-tuong-chien-xu',
  },
  {
    id: 'banh-xeo-hen-cu-lao-dai',
    name: 'Bánh Xèo Hến Cổ Chiên (Cù Lao Dài)',
    badge: 'Đặc sản độc bản bãi cồn',
    origin: 'Cù Lao Dài, Vũng Liêm',
    guide: 'Ruột hến nước ngọt đãi từ cồn bãi sông Cổ Chiên xào củ hủ dừa ngọt bùi, vỏ bánh giòn tan tráng chảo gang mỏng tang, thưởng thức cùng mâm 15 loại rau rừng.',
    venues: 'Quán Bánh Xèo Hến Ba Năm (Cù Lao Dài) · Các nhà vườn sông Cổ Chiên',
    coverSrc: '/img/entities/banh-xeo-hen-cu-lao-dai.webp',
    to: '/dia-diem/banh-xeo-hen-cu-lao-dai',
  },
  {
    id: 'khoai-lang-mam-song-cuon-la-cach',
    name: 'Khoai Lang Chấm Mắm Sống Cuốn Lá Cách',
    badge: 'Huy chương Vàng Ẩm thực Nam Bộ',
    origin: 'Vựa khoai Bình Tân',
    guide: 'Khoai lang tím bùi ngọt kẹp miếng mắm sống cá linh hoặc cá sặc đậm đà, gói trọn trong lá cách tươi xanh và ớt hiểm tạo dư vị bùi mặn cay nồng khó quên.',
    venues: 'Điểm dừng chân Bình Tân · Nhà hàng miệt vườn Cù Lao An Bình',
    coverSrc: '/img/entities/khoai-lang-mam-song-cuon-la-cach.webp',
    to: '/dia-diem/khoai-lang-mam-song-cuon-la-cach',
  },
  {
    id: 'chao-cua-dong',
    name: 'Lẩu Cua Đồng Phù Sa (Cháo Cua Đồng)',
    badge: 'Vị ngọt ruộng đồng Tây Nam Bộ',
    origin: 'Long Hồ & Trà Ôn',
    guide: 'Cua đồng tự nhiên giã cối đá lọc lấy riêu cua đỏ au béo bùi, nước dùng thanh ngọt nấu cùng rau đay, mồng tơi, mướp hương xoa dịu nắng trưa miệt vườn.',
    venues: 'Phố ẩm thực bờ kè Phường 1 (TP Vĩnh Long) · Quán cá đồng Long Hồ',
    coverSrc: '/img/entities/chao-cua-dong.webp',
    to: '/dia-diem/chao-cua-dong',
  },
  {
    id: 'oc-lac-hap-la-gung',
    name: 'Ốc Lác Nướng Tiêu Xanh / Hấp Lá Gừng',
    badge: 'Đậm đà phong vị bến đò',
    origin: 'Bờ kè sông Cổ Chiên',
    guide: 'Ốc mương vườn ngâm sạch bùn, nướng cùng hạt tiêu sọ cay nồng nàn hoặc hấp lá gừng non giòn sần sật, chấm nước mắm gừng ớt chua ngọt chuẩn vị sông nước.',
    venues: 'Phố ăn vặt bờ kè sông Cổ Chiên · Các quán ven bến phà Đình Khao',
    coverSrc: '/img/entities/oc-lac-hap-la-gung.webp',
    to: '/dia-diem/oc-lac-hap-la-gung',
  },
]

function onImgFallback(e: Event) {
  const img = e.target as HTMLImageElement
  if (img && !img.dataset.fallbackApplied) {
    img.dataset.fallbackApplied = 'true'
    img.src = '/img/spread/song-nuoc.webp'
  }
}
</script>

<style scoped>
.home-culinary-trail {
  max-width: var(--maxw);
  margin-inline: auto;
  padding-inline: var(--space-5);
  padding-block: var(--space-8);
}

.home-culinary-trail__eyebrow {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--color-brand);
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  text-transform: uppercase;
  letter-spacing: var(--tracking-caps);
  margin-block-end: var(--space-2);
}

.home-culinary-trail__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: var(--space-5);
  margin-block-start: var(--space-6);
}

@media (min-width: 1024px) {
  .home-culinary-card--lead {
    grid-column: span 2;
  }
  .home-culinary-card--lead .home-culinary-card__media {
    aspect-ratio: 21 / 9;
  }
}

.home-culinary-card {
  display: flex;
  flex-direction: column;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-surface);
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(var(--black-rgb), 0.04);
  transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.2s ease, box-shadow 0.25s ease;
}

.home-culinary-card:hover {
  transform: translateY(-3px);
  border-color: color-mix(in srgb, var(--mangthit-600) 45%, var(--color-border));
  box-shadow: 0 10px 24px rgba(var(--black-rgb), 0.1);
}

.home-culinary-card:active {
  transform: scale(0.98);
}

.home-culinary-card__media {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 10;
  overflow: hidden;
  background: var(--color-canvas);
}

.home-culinary-card__img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.4s ease;
}

.home-culinary-card:hover .home-culinary-card__img {
  transform: scale(1.04);
}

.home-culinary-card__rank {
  position: absolute;
  top: var(--space-3);
  left: var(--space-3);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 2px 8px;
  background: rgba(var(--black-rgb), 0.75);
  color: var(--alluvial-gold);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  border-radius: var(--radius-pill, 9999px);
  font-family: var(--font-mono, monospace);
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
}

.home-culinary-card__badge {
  position: absolute;
  bottom: var(--space-3);
  left: var(--space-3);
  padding: 3px 10px;
  background: rgba(var(--black-rgb), 0.72);
  color: var(--surface-white);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  border-radius: var(--radius-pill, 9999px);
  font-size: 11px;
  font-weight: var(--weight-semibold);
}

.home-culinary-card__body {
  display: flex;
  flex-direction: column;
  flex: 1;
  padding: var(--space-5);
  gap: var(--space-3);
}

.home-culinary-card__header {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.home-culinary-card__title {
  margin: 0;
  font-family: var(--font-editorial-display);
  font-size: var(--text-lg);
  line-height: 1.3;
}

.home-culinary-card__title a {
  color: var(--color-text);
  text-decoration: none;
  transition: color 0.2s ease;
}

.home-culinary-card__title a:hover {
  color: var(--color-brand);
}

.home-culinary-card__origin {
  font-size: var(--text-xs);
  color: var(--color-brand);
  font-weight: var(--weight-bold);
}

.home-culinary-card__guide {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--color-text);
  line-height: 1.55;
  opacity: 0.9;
}

.home-culinary-card__venues {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: var(--space-2) var(--space-3);
  background: var(--color-canvas);
  border-radius: var(--radius-control);
  font-size: var(--text-xs);
}

.home-culinary-card__venue-label {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--color-brand);
  font-weight: var(--weight-bold);
}

.home-culinary-card__venue-names {
  color: var(--color-text-muted);
  line-height: 1.4;
}

.home-culinary-card__footer {
  margin-top: auto;
  padding-top: var(--space-2);
}

.home-culinary-card__btn {
  min-height: 44px;
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--color-action);
  font-size: var(--text-sm);
  font-weight: var(--weight-bold);
  text-decoration: none;
  transition: transform 0.2s ease, color 0.2s ease;
}

.home-culinary-card__btn:hover {
  text-decoration: underline;
  transform: translateX(2px);
}
</style>
