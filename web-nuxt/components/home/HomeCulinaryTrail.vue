<template>
  <section class="home-culinary-trail block reveal" aria-label="Thức ngon miệt vườn Vĩnh Long" data-home-culinary-trail>
    <div class="home-culinary-trail__head section-head">
      <div class="sh-text">
        <span class="home-culinary-trail__eyebrow" data-color-role="brand">
          <IconLine name="bowl" aria-hidden="true" />
          <span>Ký sự Ẩm thực Cửu Long · Vị ngon đất phù sa</span>
        </span>
        <h2 aria-label="Thức ngon miệt vườn">Thức ngon <em class="editorial-italic-accent" aria-hidden="true">miệt vườn</em></h2>
        <p class="sh-sub">Năm thức ngon nức tiếng miệt Cửu Long, đượm vị tôm cá sông Cổ Chiên cùng mớ rau vườn tươi rói bến phù sa.</p>
      </div>
      <NuxtLink to="/am-thuc" class="see-all">
        <span>Xem trọn 120 món ngon di sản</span>
        <IconLine name="arrow-right" class="inline-arrow" aria-hidden="true" />
      </NuxtLink>
    </div>

    <!-- 5 Full-Bleed Macro Food Cards (100% photo visual area) -->
    <div class="home-culinary-trail__grid">
      <article
        v-for="(dish, index) in SIGNATURE_DISHES"
        :key="dish.id"
        class="home-culinary-card"
        :class="{ 'home-culinary-card--lead': index === 0 }"
        data-culinary-card
      >
        <!-- Full-Bleed Macro Photo (100% of card) -->
        <img
          class="home-culinary-card__img"
          :src="dish.coverSrc"
          :alt="dish.name"
          width="600"
          height="450"
          loading="lazy"
          decoding="async"
          @error="onImgFallback"
        >

        <!-- Bottom Gradient Scrim Overlay -->
        <div class="home-culinary-card__scrim" aria-hidden="true" />

        <!-- Floating Top Bar -->
        <div class="home-culinary-card__top">
          <div class="home-culinary-card__top-left">
            <span class="home-culinary-card__rank">#0{{ index + 1 }}</span>
            <span class="home-culinary-card__terroir">{{ dish.terroir }}</span>
            <span class="home-culinary-card__badge sr-only">{{ dish.badge }}</span>
          </div>
          <span v-if="dish.priceRange" class="home-culinary-card__price-badge">{{ dish.priceRange }}</span>
        </div>

        <!-- Overlaid Bottom Content (<= 25% card height) -->
        <div class="home-culinary-card__overlay home-culinary-card__body">
          <div class="home-culinary-card__trust sr-only">
            <SourceMark tier="verified" source-title="Mỹ vị bản địa uy tín" compact />
            <FreshnessLine status="fresh" updated-label="Thực địa 2026" />
          </div>
          <span class="home-culinary-card__origin">{{ dish.origin }}</span>
          <h3 class="home-culinary-card__title">
            <NuxtLink :to="dish.to">{{ dish.name }}</NuxtLink>
          </h3>

          <!-- Reputable Venue Pill Badge with Field Coordinates -->
          <div class="home-culinary-card__venue-pill">
            <IconLine name="pin" aria-hidden="true" />
            <span>{{ dish.reputableVenue || dish.venues }}</span>
            <span v-if="dish.coordinates" class="home-culinary-card__coords" :title="`Tọa độ thực địa: ${dish.coordinates}`">
              <span class="home-culinary-card__coords-sep" aria-hidden="true">·</span>
              <IconLine name="compass" aria-hidden="true" />
              <span>{{ dish.coordinates }}</span>
            </span>
          </div>

          <div class="home-culinary-card__action home-culinary-card__footer">
            <NuxtLink :to="dish.mapTo" class="home-culinary-card__btn">
              <IconLine name="map" aria-hidden="true" />
              <span>Xem vị trí & Chỉ đường</span>
              <IconLine name="arrow-right" class="home-culinary-card__arrow" aria-hidden="true" />
            </NuxtLink>
          </div>
        </div>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
import IconLine from '~/components/IconLine.vue'
import SourceMark from '~/components/SourceMark.vue'
import FreshnessLine from '~/components/FreshnessLine.vue'

interface CulinaryDish {
  readonly id: string
  readonly name: string
  readonly terroir: string
  readonly badge: string
  readonly origin: string
  readonly guide: string
  readonly reputableVenue: string
  readonly venues: string
  readonly priceRange: string
  readonly coverSrc: string
  readonly to: string
  readonly mapTo: string
  readonly coordinates: string
}

const SIGNATURE_DISHES: readonly CulinaryDish[] = [
  {
    id: 'ca-tai-tuong-chien-xu',
    name: 'Cá Tai Tượng Chiên Xù Cuốn Bánh Tráng Cù Lao',
    terroir: 'Phù Sa Cổ Chiên',
    badge: 'Cá tai tượng sông Tiền',
    origin: 'Cá tai tượng sông Tiền',
    guide: 'Đệ nhất mỹ vị sông Tiền vảy giòn rụm màu cánh gián, cuốn bánh tráng nem cù lao và rau thơm miệt vườn.',
    reputableVenue: 'Quán Chín Thảo · KDL Vinh Sang · Homestay Út Trinh',
    venues: 'Quán Cá Tai Tượng Chín Thảo · KDL Vinh Sang · Homestay Út Trinh',
    priceRange: '150.000đ – 250.000đ/con',
    coverSrc: '/img/entities/ca-tai-tuong-chien-xu.webp',
    to: '/dia-diem/ca-tai-tuong-chien-xu',
    mapTo: '/ban-do?selected=ca-tai-tuong-chien-xu',
    coordinates: "10°17'N · 105°59'E",
  },
  {
    id: 'banh-xeo-hen-cu-lao-dai',
    name: 'Bánh Xèo Hến Cổ Chiên (Cù Lao Dài)',
    terroir: 'Phù Sa Cổ Chiên',
    badge: 'Hến cào Vũng Liêm',
    origin: 'Hến cào Vũng Liêm',
    guide: 'Vỏ bánh giòn rụm tráng mỏng, nhân hến ngọt xào củ hủ dừa sông Cổ Chiên cuốn cùng 15 loại rau rừng.',
    reputableVenue: 'Quán Bánh Xèo Hến Ba Năm · Các nhà vườn Cù Lao Dài',
    venues: 'Quán Bánh Xèo Hến Ba Năm · Các nhà vườn sông Cổ Chiên',
    priceRange: '45.000đ – 70.000đ/cái',
    coverSrc: '/img/entities/banh-xeo-hen-cu-lao-dai.webp',
    to: '/dia-diem/banh-xeo-hen-cu-lao-dai',
    mapTo: '/ban-do?selected=banh-xeo-hen-cu-lao-dai',
    coordinates: "10°07'N · 106°11'E",
  },
  {
    id: 'khoai-lang-mam-song-cuon-la-cach',
    name: 'Khoai Lang Chấm Mắm Sống Cuốn Lá Cách',
    terroir: 'Đất nung Mang Thít',
    badge: 'Khoai lang tím Bình Tân OCOP 4 sao',
    origin: 'Khoai lang tím Bình Tân OCOP 4 sao',
    guide: 'Khoai lang tím Bình Tân bùi ngọt hòa quyện mắm cá linh đậm đà, gói trong lá cách thơm cay độc đáo.',
    reputableVenue: 'Điểm dừng chân Bình Tân · Nhà Dừa Cocohome Cù Lao',
    venues: 'Điểm dừng chân Bình Tân · Nhà hàng miệt vườn Cù Lao An Bình',
    priceRange: '30.000đ – 50.000đ/phần',
    coverSrc: '/img/entities/khoai-lang-mam-song-cuon-la-cach.webp',
    to: '/dia-diem/khoai-lang-mam-song-cuon-la-cach',
    mapTo: '/ban-do?selected=khoai-lang-mam-song-cuon-la-cach',
    coordinates: "10°05'N · 105°49'E",
  },
  {
    id: 'chao-cua-dong',
    name: 'Lẩu Cua Đồng Phù Sa (Cháo Cua Đồng)',
    terroir: 'Xanh Cù Lao',
    badge: 'Cua đồng Tam Bình',
    origin: 'Cua đồng Tam Bình',
    guide: 'Nồi lẩu riêu cua đồng ngọt thanh tự nhiên, nhúng kèm rau đay mồng tơi tươi non thanh mát miệt vườn.',
    reputableVenue: 'Phố ẩm thực Bờ kè Phường 1 · Quán cá đồng Long Hồ',
    venues: 'Phố ẩm thực bờ kè Phường 1 (TP Vĩnh Long) · Quán cá đồng Long Hồ',
    priceRange: '120.000đ – 180.000đ/nồi',
    coverSrc: '/img/entities/chao-cua-dong.webp',
    to: '/dia-diem/chao-cua-dong',
    mapTo: '/ban-do?selected=chao-cua-dong',
    coordinates: "10°16'N · 105°58'E",
  },
  {
    id: 'oc-lac-hap-la-gung',
    name: 'Ốc Lác Nướng Tiêu Xanh / Hấp Lá Gừng',
    terroir: 'Phù Sa Cổ Chiên',
    badge: 'Ốc lác bến sông Cổ Chiên',
    origin: 'Bờ kè sông Cổ Chiên',
    guide: 'Ốc mương vườn béo giòn sần sật, nướng tiêu cay nồng hoặc hấp gừng thơm lừng bên bến sông Cổ Chiên.',
    reputableVenue: 'Phố ăn vặt bờ kè sông Cổ Chiên · Bến phà Đình Khao',
    venues: 'Phố ăn vặt bờ kè sông Cổ Chiên · Bến phà Đình Khao',
    priceRange: '50.000đ – 80.000đ/dĩa',
    coverSrc: '/img/entities/oc-lac-hap-la-gung.webp',
    to: '/dia-diem/oc-lac-hap-la-gung',
    mapTo: '/ban-do?selected=oc-lac-hap-la-gung',
    coordinates: "10°15'N · 105°58'E",
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
  padding-block: clamp(var(--space-fib-4), 6vw, var(--space-fib-5));
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
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: var(--space-fib-4);
  margin-block-start: var(--space-fib-4);
}

@media (min-width: 1024px) {
  .home-culinary-card--lead {
    grid-column: span 2;
  }
}

/* Full-Bleed Photographic Food Card (100% photo visual area) */
.home-culinary-card {
  position: relative;
  min-height: 440px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  border: 1px solid var(--border-liquid-glass, var(--color-border));
  border-radius: var(--radius-surface);
  overflow: hidden;
  box-shadow: var(--shadow-card-ambient);
  transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.2s ease, box-shadow 0.25s ease;
  background: var(--color-canvas);
}

@media (min-width: 1024px) {
  .home-culinary-card--lead {
    min-height: 460px;
  }
}

.home-culinary-card:hover {
  transform: translateY(-3px);
  border-color: color-mix(in srgb, var(--mangthit-600) 45%, var(--color-border));
  box-shadow: 0 10px 24px rgba(var(--black-rgb), 0.16);
}

.home-culinary-card:active {
  transform: scale(0.98);
}

.home-culinary-card:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 3px;
  border-radius: var(--radius-surface);
}

/* Macro Food Photo Fills 100% of Card */
.home-culinary-card__img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1);
  z-index: 0;
}

.home-culinary-card:hover .home-culinary-card__img {
  transform: scale(1.04);
}

/* Bottom Gradient Scrim Overlay */
.home-culinary-card__scrim {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    180deg,
    rgba(var(--black-rgb), 0.15) 0%,
    rgba(var(--black-rgb), 0.45) 45%,
    rgba(var(--black-rgb), 0.85) 75%,
    rgba(var(--black-rgb), 0.96) 100%
  );
  pointer-events: none;
  z-index: 1;
}

/* Floating Top Bar */
.home-culinary-card__top {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
}

.home-culinary-card__top-left {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
}

.home-culinary-card__rank {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 3px 10px;
  background: rgba(var(--black-rgb), 0.78);
  color: var(--surface-white);
  backdrop-filter: blur(20px) saturate(180%);
  border: 1px solid var(--border-liquid-glass);
  border-radius: var(--radius-pill, 9999px);
  box-shadow: var(--shadow-card-ambient);
  font-family: var(--font-mono, monospace);
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
}

.home-culinary-card__terroir {
  padding: 3px 8px;
  background: rgba(var(--black-rgb), 0.78);
  color: var(--alluvial-gold);
  backdrop-filter: blur(20px) saturate(180%);
  border: 1px solid var(--border-liquid-glass);
  border-radius: var(--radius-pill, 9999px);
  box-shadow: var(--shadow-card-ambient);
  font-size: 11px;
  font-weight: var(--weight-bold);
}

.home-culinary-card__badge {
  padding: 3px 10px;
  background: rgba(var(--black-rgb), 0.78);
  color: var(--surface-white);
  backdrop-filter: blur(20px) saturate(180%);
  border: 1px solid var(--border-liquid-glass);
  border-radius: var(--radius-pill, 9999px);
  box-shadow: var(--shadow-card-ambient);
  font-size: 11px;
  font-weight: var(--weight-semibold);
}

.home-culinary-card__trust {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-1h);
  margin-bottom: var(--space-1);
}

.home-culinary-card__price-badge {
  display: inline-flex;
  align-items: center;
  padding: 3px 10px;
  background: rgba(var(--black-rgb), 0.78);
  color: var(--alluvial-gold);
  backdrop-filter: blur(20px) saturate(180%);
  border: 1px solid var(--border-liquid-glass);
  border-radius: var(--radius-pill, 9999px);
  box-shadow: var(--shadow-card-ambient);
  font-family: var(--font-mono, monospace);
  font-size: 11px;
  font-weight: var(--weight-bold);
  letter-spacing: 0.02em;
}

/* Bottom Overlay (<= 25% card height) */
.home-culinary-card__overlay {
  position: relative;
  z-index: 2;
  padding: var(--space-4) var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  color: var(--surface-white);
}

.home-culinary-card__origin {
  font-size: var(--text-xs);
  color: var(--surface-white);
  opacity: 0.9;
  font-weight: var(--weight-bold);
  text-transform: uppercase;
  letter-spacing: var(--tracking-caps);
}

.home-culinary-card__title {
  margin: 0;
  font-family: var(--font-editorial-display);
  font-size: var(--text-base);
  line-height: 1.35;
}

.home-culinary-card__title a {
  color: var(--surface-white);
  text-decoration: none;
  text-shadow: 0 1px 3px rgba(var(--black-rgb), 0.5);
  transition: opacity 0.2s ease;
}

.home-culinary-card__title a:hover {
  opacity: 0.85;
}

.home-culinary-card__title a:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 2px;
  border-radius: var(--radius-control);
}

.home-culinary-card__venue-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background: rgba(var(--black-rgb), 0.70);
  border: 1px solid var(--border-liquid-glass);
  backdrop-filter: blur(20px) saturate(180%);
  border-radius: var(--radius-pill, 9999px);
  box-shadow: var(--shadow-card-ambient);
  font-size: 11px;
  color: var(--surface-white);
  width: fit-content;
  transition: transform 0.2s ease, border-color 0.2s ease;
}

.home-culinary-card:hover .home-culinary-card__venue-pill {
  transform: translateY(-1px);
  border-color: var(--alluvial-gold);
}

.home-culinary-card__venue-pill .line-icon {
  color: var(--surface-white);
  flex-shrink: 0;
}

.home-culinary-card__action {
  padding-top: var(--space-1);
}

.home-culinary-card__btn {
  min-height: 44px;
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--surface-white);
  font-size: var(--text-sm);
  font-weight: var(--weight-bold);
  text-decoration: none;
  text-shadow: 0 1px 2px rgba(var(--black-rgb), 0.4);
  transition: transform 0.2s ease, opacity 0.2s ease;
}

.home-culinary-card__btn:hover {
  text-decoration: underline;
  transform: translateX(2px);
}

.home-culinary-card__btn:active {
  transform: scale(0.98);
}

.home-culinary-card__btn:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 2px;
  border-radius: var(--radius-control);
}

.home-culinary-card__arrow {
  transition: transform 0.2s ease;
}

.home-culinary-card__btn:hover .home-culinary-card__arrow {
  transform: translateX(3px);
}

.home-culinary-card__coords {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 0.72rem;
  opacity: 0.88;
}

.home-culinary-card__coords-sep {
  margin: 0 4px;
  opacity: 0.45;
}
</style>
