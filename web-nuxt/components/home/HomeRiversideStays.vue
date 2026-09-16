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

    <!-- 3 Featured Certified Homestays -->
    <div class="home-riverside-stays__stays-grid">
      <article
        v-for="stay in CURATED_HOMESTAYS"
        :key="stay.id"
        class="home-stay-card"
        data-homestay-card
      >
        <div class="home-stay-card__media">
          <img
            class="home-stay-card__img"
            :src="stay.coverSrc"
            :alt="stay.name"
            width="600"
            height="400"
            loading="lazy"
            decoding="async"
            @error="onImgFallback"
          >
          <span class="home-stay-card__badge">{{ stay.badge }}</span>
        </div>

        <div class="home-stay-card__body">
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
              <span>Xem phòng & Liên hệ</span>
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
    desc: 'Ngôi nhà rường 3 gian bằng gỗ quý cổ kính nép mình dưới rặng nhãn, tổ chức nấu bánh xèo, làm kẹo chuối và xuồng chèo đêm trăng trên bến sông.',
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
    desc: 'Bến cano riêng biệt đón khách vượt sông Hậu, phòng nghỉ bungalow mái lá thân thiện môi trường, ngắm cầu Cần Thơ lung linh về đêm.',
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
    desc: 'Khuôn viên nhà vườn truyền thống lâu đời rợp bóng dừa nước, thưởng thức trà hoa quả tươi và mâm cơm dân dã mẹ nấu đậm tình đất phương Nam.',
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
  padding-block: var(--space-8);
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
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: var(--space-5);
  margin-block-start: var(--space-6);
}

.home-stay-card {
  display: flex;
  flex-direction: column;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-surface);
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(var(--black-rgb), 0.04);
  transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.2s ease, box-shadow 0.25s ease;
}

.home-stay-card:hover {
  transform: translateY(-3px);
  border-color: color-mix(in srgb, var(--mangthit-600) 45%, var(--color-border));
  box-shadow: 0 10px 24px rgba(var(--black-rgb), 0.1);
}

.home-stay-card:active {
  transform: scale(0.98);
}

.home-stay-card__media {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 10;
  overflow: hidden;
  background: var(--color-canvas);
}

.home-stay-card__img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.4s ease;
}

.home-stay-card:hover .home-stay-card__img {
  transform: scale(1.04);
}

.home-stay-card__badge {
  position: absolute;
  top: var(--space-3);
  left: var(--space-3);
  padding: 3px 10px;
  background: rgba(var(--black-rgb), 0.72);
  color: var(--leaf-600);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  border: 1px solid rgba(var(--white-rgb), 0.2);
  border-radius: var(--radius-pill, 9999px);
  font-size: 11px;
  font-weight: var(--weight-bold);
}

.home-stay-card__body {
  display: flex;
  flex-direction: column;
  flex: 1;
  padding: var(--space-5);
  gap: var(--space-3);
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
  color: var(--color-brand);
  font-weight: var(--weight-bold);
}

.home-stay-card__type {
  color: var(--color-text-muted);
}

.home-stay-card__title {
  margin: 0;
  font-family: var(--font-editorial-display);
  font-size: var(--text-lg);
  line-height: 1.3;
}

.home-stay-card__title a {
  color: var(--color-text);
  text-decoration: none;
  transition: color 0.2s ease;
}

.home-stay-card__title a:hover {
  color: var(--color-brand);
}

.home-stay-card__desc {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--color-text);
  line-height: 1.55;
  opacity: 0.9;
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
  background: var(--color-canvas);
  border-radius: var(--radius-pill, 9999px);
  font-size: 11px;
  color: var(--color-text-muted);
}

.home-stay-card__perk .line-icon {
  color: var(--orchard-600);
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
  transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.home-stay-card__action .btn:active {
  transform: scale(0.98);
}

/* Folk Experiences Strip */
.home-riverside-stays__experiences {
  margin-block-start: var(--space-8);
  padding: var(--space-5);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-surface);
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
  gap: var(--space-4);
}

.home-exp-card {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  padding: var(--space-3);
  background: var(--color-canvas);
  border-radius: var(--radius-control);
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
