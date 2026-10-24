<template>
  <section class="home-riverside-stays block reveal" aria-label="Nghỉ Dưỡng Homestay Ven Sông & Trải Nghiệm Điền Dã" data-home-riverside-stays>
    <div class="home-riverside-stays__head section-head">
      <div class="sh-text">
        <span class="home-riverside-stays__eyebrow" data-color-role="brand">
          <IconLine name="home" aria-hidden="true" />
          <span>Lưu trú sinh thái & Điền dã Nam Bộ</span>
        </span>
        <h2>Homestay ven sông & <em class="editorial-italic-accent" aria-hidden="true">đêm trăng tài tử</em></h2>
        <p class="sh-sub">Thức giấc giữa tiếng chim hót miệt vườn, cùng chủ nhà bơi xuồng hái trái cây và lắng nghe tiếng đàn kìm réo rắt bên bến sông Cổ Chiên.</p>
      </div>
      <NuxtLink to="/luu-tru" class="see-all">
        <span>164 nơi lưu trú</span>
        <IconLine name="arrow-right" class="inline-arrow" aria-hidden="true" />
      </NuxtLink>
    </div>

    <!-- Riverside Retreat Lookbook: 3 Featured Certified Homestays (Asymmetric Editorial Grid) -->
    <div class="home-riverside-stays__stays-grid">
      <article
        v-for="(stay, index) in CURATED_HOMESTAYS"
        :key="stay.id"
        class="home-stay-card"
        :class="{ 'home-stay-card--lead': index === 0 }"
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
          <div class="home-stay-card__top-left">
            <span class="home-stay-card__terroir">{{ stay.terroir }}</span>
            <span class="home-stay-card__badge">{{ stay.badge }}</span>
          </div>
          <span v-if="stay.ecoBadge" class="home-stay-card__eco-badge">
            <IconLine name="shield-check" aria-hidden="true" />
            <span>{{ stay.ecoBadge }}</span>
          </span>
        </div>

        <!-- Overlaid Bottom Content (<= 25% card height) -->
        <div class="home-stay-card__overlay home-stay-card__body">
          <div class="home-stay-card__trust sr-only">
            <SourceMark tier="official" source-title="Chuẩn Homestay ASEAN" compact />
            <FreshnessLine status="fresh" updated-label="Thực địa 2026" />
          </div>

          <div class="home-stay-card__meta">
            <span class="home-stay-card__area">
              <IconLine name="pin" aria-hidden="true" />
              <span>{{ stay.area }}</span>
            </span>
            <span v-if="stay.coordinates" class="home-stay-card__coords" :title="`Tọa độ thực địa: ${stay.coordinates}`">
              <span class="home-stay-card__coords-sep" aria-hidden="true">·</span>
              <IconLine name="compass" aria-hidden="true" />
              <span>{{ stay.coordinates }}</span>
            </span>
            <span class="home-stay-card__price"><strong>{{ stay.price }}</strong></span>
          </div>

          <h3 class="home-stay-card__title">
            <NuxtLink :to="stay.to">{{ stay.name }}</NuxtLink>
          </h3>
          <p class="home-stay-card__desc">{{ stay.desc }}</p>

          <div class="home-stay-card__perks sr-only">
            <span v-for="perk in stay.perks" :key="perk" class="home-stay-card__perk">
              <IconLine name="check" aria-hidden="true" />
              <span>{{ perk }}</span>
            </span>
          </div>

          <div class="home-stay-card__action">
            <NuxtLink :to="stay.to" class="btn btn-outline" data-color-role="action-secondary">
              <IconLine name="phone" aria-hidden="true" />
              <span>Liên hệ & Đặt phòng</span>
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
          <span>Trải nghiệm bản địa & di sản dân gian</span>
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
import SourceMark from '~/components/SourceMark.vue'
import FreshnessLine from '~/components/FreshnessLine.vue'

interface CuratedHomestay {
  readonly id: string
  readonly name: string
  readonly terroir: string
  readonly badge: string
  readonly ecoBadge: string
  readonly price: string
  readonly area: string
  readonly typeLabel: string
  readonly desc: string
  readonly perks: readonly string[]
  readonly coverSrc: string
  readonly to: string
  readonly coordinates: string
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
    terroir: 'Xanh Cù Lao',
    badge: 'Chuẩn Homestay ASEAN',
    ecoBadge: 'Chứng nhận Sinh Thái ASEAN',
    price: 'Từ 650.000đ/đêm',
    area: 'Xã Hòa Ninh, Cù Lao An Bình',
    typeLabel: 'Nhà Rường Nam Bộ',
    desc: 'Nhà rường gỗ quý cổ kính dưới bóng nhãn cù lao An Bình, trải nghiệm nấu bánh xèo và nghe đờn ca bến sông.',
    perks: ['Cơm gia đình cù lao', 'Chèo xuồng mương rạch', 'Xe đạp làng quê'],
    coverSrc: '/img/spread/cu-lao-an-binh.webp',
    to: '/dia-diem/homestay-ut-trinh',
    coordinates: "10°17'N · 105°59'E",
  },
  {
    id: 'mekong-riverside-homestay',
    name: 'Mekong Riverside Homestay',
    terroir: 'Phù Sa Cổ Chiên',
    badge: 'View Sông Hậu Lộng Gió',
    ecoBadge: 'Vườn sinh thái không rác thải',
    price: 'Từ 450.000đ/đêm',
    area: 'Thị xã Bình Minh, Vĩnh Long',
    typeLabel: 'Eco-Lodge Ven Sông',
    desc: 'Eco-lodge ven sông Hậu lộng gió, đón khách bằng cano riêng và ngắm hoàng hôn rực rỡ bên bến đò Bình Minh.',
    perks: ['Bến đón cano riêng', 'Câu cá bờ sông', 'Ngắm hoàng hôn sông Hậu'],
    coverSrc: '/img/spread/song-nuoc.webp',
    to: '/dia-diem/mekong-riverside-homestay',
    coordinates: "10°05'N · 105°49'E",
  },
  {
    id: 'ba-linh-homestay',
    name: 'Ba Linh Homestay Cù Lao',
    terroir: 'Xanh Cù Lao',
    badge: 'Không Gian Vườn Cây Xưa',
    ecoBadge: 'Nông nghiệp hữu cơ tuần hoàn',
    price: 'Từ 380.000đ/đêm',
    area: 'Xã An Bình, Long Hồ',
    typeLabel: 'Vườn Trái Cây Gia Đình',
    desc: 'Nhà vườn truyền thống rợp bóng dừa nước, mâm cơm miệt vườn mẹ nấu và những đêm trăng thanh bình cù lao.',
    perks: ['Vườn trái cây tự hái', 'Võng ngắm mương liếp', 'Đờn ca tài tử'],
    coverSrc: '/img/entities/nha-vuon-tu-hien.webp',
    to: '/dia-diem/ba-linh-homestay',
    coordinates: "10°16'N · 105°59'E",
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
  grid-template-columns: minmax(0, 1fr);
  gap: var(--space-fib-4);
  margin-block-start: var(--space-fib-4);
}

@media (min-width: 960px) {
  /* Asymmetric Panorama + Twin Portrait Architectural Row (prevents orphan 3rd card) */
  .home-riverside-stays__stays-grid {
    grid-template-columns: minmax(0, 1.38fr) minmax(0, 0.81fr) minmax(0, 0.81fr);
    align-items: stretch;
  }

  .home-stay-card--lead {
    grid-column: span 1;
    min-height: 500px;
  }
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

.home-stay-card:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 3px;
  border-radius: var(--radius-surface);
}

/* Full-Bleed Image Fills 100% of Card */
.home-stay-card__img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  aspect-ratio: 16 / 9;
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
    rgba(var(--black-rgb), 0.18) 0%,
    transparent 28%,
    rgba(var(--black-rgb), 0.35) 58%,
    rgba(var(--black-rgb), 0.72) 78%,
    rgba(var(--black-rgb), 0.88) 100%
  );
  pointer-events: none;
  z-index: 1;
}

/* Floating Top Badge */
.home-stay-card__top {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
}

.home-stay-card__top-left {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
}

.home-stay-card__terroir {
  display: inline-flex;
  align-items: center;
  padding: 3px 10px;
  background: rgba(var(--black-rgb), 0.86);
  color: var(--alluvial-gold);
  border: 1px solid var(--border-liquid-glass);
  border-radius: var(--radius-pill, 9999px);
  box-shadow: var(--shadow-card-ambient);
  font-size: var(--text-2xs);
  font-weight: var(--weight-bold);
}

.home-stay-card__trust {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-1h);
  margin-bottom: var(--space-1);
}

.home-stay-card__badge {
  display: inline-flex;
  align-items: center;
  padding: 3px 10px;
  background: rgba(var(--black-rgb), 0.86);
  color: var(--surface-white); /* WCAG 2.2 AAA >= 11:1 compliant */
  border: 1px solid var(--border-liquid-glass);
  border-radius: var(--radius-pill, 9999px);
  box-shadow: var(--shadow-card-ambient);
  font-size: var(--text-2xs);
  font-weight: var(--weight-bold);
}

.home-stay-card__eco-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px;
  background: rgba(var(--black-rgb), 0.86);
  color: var(--alluvial-gold);
  border: 1px solid var(--border-liquid-glass);
  border-radius: var(--radius-pill, 9999px);
  box-shadow: var(--shadow-card-ambient);
  font-size: var(--text-2xs);
  font-weight: var(--weight-bold);
}

.home-stay-card__eco-badge .line-icon {
  color: var(--alluvial-gold);
  font-size: var(--text-2xs);
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
  min-width: 0;
}

.home-stay-card__meta {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--space-2);
  font-size: var(--text-xs);
  min-width: 0;
}

.home-stay-card__area {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--surface-white);
  font-weight: var(--weight-bold);
  min-width: 0;
  flex: 1 1 auto;
}

.home-stay-card__area .line-icon {
  color: var(--surface-white);
}

.home-stay-card__coords {
  display: none !important;
}

.home-stay-card__coords-sep {
  display: none !important;
}

.home-stay-card__price {
  font-variant-numeric: tabular-nums;
  font-size: var(--text-xs);
  color: var(--alluvial-gold);
  font-weight: var(--weight-bold);
  flex-shrink: 0;
  white-space: nowrap;
}

.home-stay-card__title {
  margin: 0;
  font-family: var(--font-editorial-display);
  font-size: var(--text-base);
  line-height: 1.35;
  text-wrap: pretty;
  min-width: 0;
}

.home-stay-card__title a {
  color: var(--surface-white);
  text-decoration: none;
  text-shadow: 0 1px 3px rgba(var(--black-rgb), 0.5);
  transition: opacity 0.2s ease;
  display: inline-block;
  max-width: 100%;
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
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-wrap: pretty;
  min-width: 0;
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
  background: rgba(var(--black-rgb), 0.80);
  border: 1px solid var(--border-liquid-glass);
  border-radius: var(--radius-pill, 9999px);
  box-shadow: var(--shadow-card-ambient);
  font-size: var(--text-2xs);
  color: var(--surface-white);
}

.home-stay-card__perk .line-icon {
  color: var(--surface-white);
  font-size: var(--text-2xs);
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

.home-stay-card__action .btn .line-icon:last-child {
  transition: transform 0.2s ease;
}

.home-stay-card:hover .home-stay-card__action .btn .line-icon:last-child,
.home-stay-card__action .btn:hover .line-icon:last-child {
  transform: translateX(3px);
}

.home-stay-card__action .btn:active {
  transform: scale(0.98);
}

.home-stay-card__action .btn:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 2px;
}

/* Folk Experiences Strip — Editorial Hairline Ledger (no nested card-in-card) */
.home-riverside-stays__experiences {
  margin-block-start: var(--space-fib-5);
  padding-block-start: var(--space-5);
  border-top: 1px solid var(--border-liquid-glass, var(--color-border));
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
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 260px), 1fr));
  gap: var(--space-6);
  counter-reset: folk-exp;
}

.home-exp-card {
  counter-increment: folk-exp;
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  padding: var(--space-1) 0 var(--space-1) var(--space-5);
  background: transparent;
  border: 0;
  border-inline-start: 1px solid color-mix(in srgb, var(--color-material-river) 38%, var(--color-border));
  border-radius: 0;
  box-shadow: none;
  transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.2s ease;
}

.home-exp-card::before {
  content: counter(folk-exp, decimal-leading-zero);
  font-family: var(--font-editorial-display);
  font-style: italic;
  font-size: 1.45rem;
  font-weight: var(--weight-semibold);
  color: var(--color-brand);
  line-height: 1;
  flex-shrink: 0;
}

.home-exp-card:hover {
  transform: translateX(3px);
  border-color: var(--color-material-river);
}

.home-exp-card:active {
  transform: scale(0.98);
}

.home-exp-card__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: auto;
  height: auto;
  flex-shrink: 0;
  border-radius: 0;
  background: transparent;
  color: var(--color-material-river);
  font-size: 1.15rem;
  margin-block-start: 2px;
  transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1), color 0.2s ease;
}

.home-exp-card:hover .home-exp-card__icon {
  transform: scale(1.08);
  color: var(--color-brand);
}

.home-exp-card__content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.home-exp-card__title {
  margin: 0;
  font-family: var(--font-editorial-display);
  font-size: clamp(1.04rem, 1.3vw, 1.18rem);
  font-weight: var(--weight-semibold);
  color: var(--color-text);
  line-height: 1.3;
}

.home-exp-card__desc {
  margin: 0;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  line-height: 1.5;
}
</style>
