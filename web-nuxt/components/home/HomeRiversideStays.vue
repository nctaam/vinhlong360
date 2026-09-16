<template>
  <section class="home-riverside-stays block reveal" aria-label="Nghỉ Dưỡng Homestay Ven Sông & Trải Nghiệm Điền Dã" data-home-riverside-stays>
    <div class="home-riverside-stays__head section-head">
      <div class="sh-text">
        <span class="home-riverside-stays__eyebrow" data-color-role="brand">
          <IconLine name="home" />
          <span>Lưu trú sinh thái & Điền dã Nam Bộ</span>
        </span>
        <h2>Homestay Sông Nước & <em class="editorial-italic-accent" aria-hidden="true">Đêm Trăng Tài Tử</em></h2>
        <p class="sh-sub">Thức giấc giữa tiếng chim hót miệt vườn, cùng chủ nhà bơi xuồng hái trái cây và lắng nghe tiếng đàn kìm réo rắt bên bến sông Cổ Chiên.</p>
      </div>
      <NuxtLink to="/luu-tru" class="see-all">
        <span>Xem toàn bộ 164 nơi lưu trú</span>
        <IconLine name="arrow-right" class="inline-arrow" aria-hidden="true" />
      </NuxtLink>
    </div>

    <!-- Riverside Retreat Lookbook: 3 Featured Certified Homestays (Full-Bleed Widescreen) -->
    <div class="home-riverside-stays__stays-grid">
      <article
        v-for="stay in CURATED_HOMESTAYS"
        :key="stay.id"
        class="home-stay-card"
        data-homestay-card
      >
        <!-- Full-Bleed Homestay Photo (100% of card) -->
        <img
          class="home-stay-card__img"
          :src="stay.coverSrc"
          :alt="stay.name"
          width="640"
          height="360"
          loading="lazy"
          decoding="async"
          @error="onImgFallback"
        >

        <!-- Bottom Gradient Scrim Overlay -->
        <div class="home-stay-card__scrim" aria-hidden="true" />

        <!-- Floating Top Badge -->
        <div class="home-stay-card__top">
          <span class="home-stay-card__badge">{{ stay.badge }}</span>
        </div>

        <!-- Overlaid Bottom Content (<= 25% card height) -->
        <div class="home-stay-card__overlay home-stay-card__body">
          <div class="home-stay-card__meta">
            <span class="home-stay-card__area">
              <IconLine name="pin" />
              <span>{{ stay.area }}</span>
            </span>
            <span class="home-stay-card__type">{{ stay.typeLabel }}</span>
          </div>

          <h3 class="home-stay-card__title">
            <NuxtLink :to="stay.to">{{ stay.name }}</NuxtLink>
          </h3>
          <p class="home-stay-card__desc">{{ stay.desc }}</p>

          <div class="home-stay-card__perks">
            <span v-for="perk in stay.perks" :key="perk" class="home-stay-card__perk">
              <IconLine name="check" />
              <span>{{ perk }}</span>
            </span>
          </div>

          <div class="home-stay-card__action">
            <NuxtLink :to="stay.to" class="btn btn-outline" data-color-role="action-secondary">
              <IconLine name="phone" />
              <span>Đặt phòng & Trải nghiệm</span>
              <IconLine name="arrow-right" aria-hidden="true" />
            </NuxtLink>
          </div>
        </div>
      </article>
    </div>

    <!-- Folk Art & Living Fieldwork Strip -->
    <div class="home-riverside-stays__experiences">
      <div class="home-riverside-stays__exp-header">
        <h3 class="home-riverside-stays__exp-title">
          <IconLine name="route" />
          <span>Trải Nghiệm Điền Dã & Di Sản Dân Gian Đặc Sắc</span>
        </h3>
      </div>

      <div class="home-riverside-stays__exp-grid">
        <div
          v-for="exp in FOLK_EXPERIENCES"
          :key="exp.title"
          class="home-exp-card"
        >
          <span class="home-exp-card__icon" aria-hidden="true">
            <IconLine :name="exp.icon" />
          </span>
          <div class="home-exp-card__content">
            <h4 class="home-exp-card__title">{{ exp.title }}</h4>
            <p class="home-exp-card__desc">{{ exp.desc }}</p>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import IconLine from '~/components/IconLine.vue'

interface CuratedHomestay {
  readonly id: string
  readonly name: string
  readonly badge: string
  readonly area: string
  readonly typeLabel: string
  readonly desc: string
  readonly perks: readonly string[]
  readonly coverSrc: string
  readonly to: string
}

interface FolkExperience {
  readonly title: string
  readonly desc: string
  readonly icon: string
}

const CURATED_HOMESTAYS: readonly CuratedHomestay[] = [
  {
    id: 'homestay-ut-trinh',
    name: 'Út Trinh Homestay (ASEAN Standard)',
    badge: 'Chuẩn Homestay ASEAN',
    area: 'Xã Hòa Ninh, Cù Lao An Bình',
    typeLabel: 'Nhà Rường Nam Bộ',
    desc: 'Nhà rường gỗ quý cổ kính dưới bóng nhãn cù lao An Bình, trải nghiệm nấu bánh xèo và nghe đờn ca bến sông.',
    perks: ['Cơm gia đình cù lao', 'Chèo xuồng mương rạch', 'Xe đạp làng quê'],
    coverSrc: '/img/entities/homestay-ut-trinh.webp',
    to: '/dia-diem/homestay-ut-trinh',
  },
  {
    id: 'mekong-riverside-homestay',
    name: 'Mekong Riverside Homestay',
    badge: 'View Sông Hậu Lộng Gió',
    area: 'Thị xã Bình Minh, Vĩnh Long',
    typeLabel: 'Eco-Lodge Ven Sông',
    desc: 'Eco-lodge ven sông Hậu lộng gió, đón khách bằng cano riêng và ngắm hoàng hôn rực rỡ bên bến đò Bình Minh.',
    perks: ['Bến đón cano riêng', 'Câu cá bờ sông', 'Ngắm hoàng hôn sông Hậu'],
    coverSrc: '/img/entities/mekong-riverside-homestay.webp',
    to: '/dia-diem/mekong-riverside-homestay',
  },
  {
    id: 'ba-linh-homestay',
    name: 'Ba Linh Homestay Cù Lao',
    badge: 'Không Gian Vườn Cây Xưa',
    area: 'Xã An Bình, Long Hồ',
    typeLabel: 'Vườn Trái Cây Gia Đình',
    desc: 'Nhà vườn truyền thống rợp bóng dừa nước, mâm cơm miệt vườn mẹ nấu và những đêm trăng thanh bình cù lao.',
    perks: ['Vườn trái cây tự hái', 'Võng ngắm mương liếp', 'Đờn ca tài tử'],
    coverSrc: '/img/entities/ba-linh-homestay.webp',
    to: '/dia-diem/ba-linh-homestay',
  },
]

const FOLK_EXPERIENCES: readonly FolkExperience[] = [
  {
    title: 'Chèo xuồng ba lá mương liếp',
    desc: 'Lướt nhẹ tay chèo dưới bóng mát rượi của những rặng bần chua và hàng dừa nước rạch An Bình trong lành.',
    icon: 'route',
  },
  {
    title: 'Dỡ chà & Tát mương bắt cá đồng',
    desc: 'Mặc bộ bà ba mộc mạc, cùng người dân be bờ tát mương bắt cá lóc, cá trê rồi nướng trui rơm ngay tại vườn.',
    icon: 'flame',
  },
  {
    title: 'Đêm Đờn ca tài tử Nam Bộ',
    desc: 'Thưởng thức hòa tấu đàn kìm, đàn tranh và những bài bản ca tài tử mượt mà bên bến sông Cổ Chiên trăng thanh.',
    icon: 'moon',
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
.home-riverside-stays {
  max-width: var(--maxw);
  margin-inline: auto;
  padding-inline: var(--space-5);
  padding-block: clamp(var(--space-fib-4), 6vw, var(--space-fib-5));
}

.home-riverside-stays__eyebrow {
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

.home-riverside-stays__stays-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: var(--space-fib-4);
  margin-block-start: var(--space-fib-4);
}

/* Full-Bleed Photographic Lookbook Card (100% photo visual area) */
.home-stay-card {
  position: relative;
  min-height: 480px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  background: var(--color-canvas);
  border: 1px solid var(--border-liquid-glass, var(--color-border));
  border-radius: var(--radius-surface);
  overflow: hidden;
  box-shadow: var(--shadow-card-ambient);
  transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.2s ease, box-shadow 0.25s ease;
}

.home-stay-card:hover {
  transform: translateY(-3px);
  border-color: color-mix(in srgb, var(--mangthit-600) 45%, var(--color-border));
  box-shadow: 0 10px 24px rgba(var(--black-rgb), 0.16);
}

.home-stay-card:active {
  transform: scale(0.98);
}

/* Full-Bleed Image Fills 100% of Card */
.home-stay-card__img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1);
  z-index: 0;
}

.home-stay-card:hover .home-stay-card__img {
  transform: scale(1.04);
}

/* Gradient Scrim Overlay */
.home-stay-card__scrim {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    180deg,
    rgba(var(--black-rgb), 0.25) 0%,
    rgba(var(--black-rgb), 0.08) 30%,
    rgba(var(--black-rgb), 0.55) 50%,
    rgba(var(--black-rgb), 0.78) 65%,
    rgba(var(--black-rgb), 0.92) 85%,
    rgba(var(--black-rgb), 0.95) 100%
  );
  pointer-events: none;
  z-index: 1;
}

/* Floating Top Badge */
.home-stay-card__top {
  position: relative;
  z-index: 2;
  padding: var(--space-3) var(--space-4);
}

.home-stay-card__badge {
  display: inline-flex;
  align-items: center;
  padding: 3px 10px;
  background: rgba(var(--black-rgb), 0.78);
  color: var(--surface-white); /* WCAG 2.2 AAA >= 11:1 compliant */
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border: 1px solid var(--border-liquid-glass);
  border-radius: var(--radius-pill, 9999px);
  box-shadow: var(--shadow-card-ambient);
  font-size: 11px;
  font-weight: var(--weight-bold);
}

/* Bottom Content Overlay (<= 25% card height) */
.home-stay-card__overlay {
  position: relative;
  z-index: 2;
  padding: var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-2h);
  color: var(--surface-white);
}

.home-stay-card__meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: var(--text-xs);
}

.home-stay-card__area {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--surface-white);
  font-weight: var(--weight-bold);
}

.home-stay-card__area .line-icon {
  color: var(--surface-white);
}

.home-stay-card__type {
  color: var(--surface-white);
  opacity: 0.85;
}

.home-stay-card__title {
  margin: 0;
  font-family: var(--font-editorial-display);
  font-size: var(--text-base);
  line-height: 1.35;
}

.home-stay-card__title a {
  color: var(--surface-white);
  text-decoration: none;
  text-shadow: 0 1px 3px rgba(var(--black-rgb), 0.5);
  transition: opacity 0.2s ease;
}

.home-stay-card__title a:hover {
  opacity: 0.85;
}

.home-stay-card__desc {
  margin: 0;
  font-size: var(--text-xs);
  color: var(--surface-white);
  opacity: 0.9;
  line-height: 1.45;
  text-shadow: 0 1px 2px rgba(var(--black-rgb), 0.4);
}

.home-stay-card__perks {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-top: var(--space-1);
}

.home-stay-card__perk {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  background: rgba(var(--black-rgb), 0.65);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border: 1px solid var(--border-liquid-glass);
  border-radius: var(--radius-pill, 9999px);
  box-shadow: var(--shadow-card-ambient);
  font-size: 11px;
  color: var(--surface-white);
}

.home-stay-card__perk .line-icon {
  color: var(--surface-white);
  font-size: 10px;
}

.home-stay-card__action {
  margin-top: auto;
  padding-top: var(--space-2);
}

.home-stay-card__action .btn {
  width: 100%;
  min-height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  border-radius: var(--radius-control);
  text-decoration: none;
  background: var(--surface-white);
  color: var(--mekong-ink);
  border: 1px solid transparent;
  transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.2s ease;
}

.home-stay-card__action .btn:hover {
  opacity: 0.95;
}

.home-stay-card__action .btn:active {
  transform: scale(0.98);
}

/* Folk Experiences Strip */
.home-riverside-stays__experiences {
  margin-block-start: var(--space-fib-5);
  padding: var(--space-5);
  background: var(--color-surface);
  border: 1px solid var(--border-liquid-glass, var(--color-border));
  border-radius: var(--radius-surface);
  box-shadow: var(--shadow-card-ambient);
}

.home-riverside-stays__exp-header {
  margin-block-end: var(--space-4);
}

.home-riverside-stays__exp-title {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  margin: 0;
  font-family: var(--font-editorial-display);
  font-size: var(--text-base);
  color: var(--color-brand);
}

.home-riverside-stays__exp-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: var(--space-fib-3);
}

.home-exp-card {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  padding: var(--space-3);
  background: var(--color-canvas);
  border: 1px solid var(--border-liquid-glass, var(--color-border));
  border-radius: var(--radius-control);
  box-shadow: var(--shadow-card-ambient);
}

.home-exp-card__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  flex-shrink: 0;
  border-radius: var(--radius-control);
  background: color-mix(in srgb, var(--river-600) 12%, transparent);
  color: var(--river-600);
  font-size: 1.1rem;
}

.home-exp-card__content {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.home-exp-card__title {
  margin: 0;
  font-size: var(--text-sm);
  font-weight: var(--weight-bold);
  color: var(--color-text);
}

.home-exp-card__desc {
  margin: 0;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  line-height: 1.45;
}
</style>
