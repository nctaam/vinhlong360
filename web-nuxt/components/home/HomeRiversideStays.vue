<template>
  <section class="home-riverside-stays block reveal" aria-label="Nhà vườn và Đêm ven sông Vĩnh Long" data-home-riverside-stays>
    <div class="home-riverside-stays__head section-head">
      <div class="sh-text">
        <span class="home-riverside-stays__eyebrow" data-color-role="brand">
          <IconLine name="home" aria-hidden="true" />
          <span>Lưu trú miệt vườn · Đêm ven sông</span>
        </span>
        <h2>Nhà vườn &amp; Đêm ven sông</h2>
        <p class="sh-sub">Nghỉ đêm dưới tán nhãn cù lao và rặng dừa Bến Tre, đón con nước sớm bên hiên gỗ Nam Bộ.</p>
      </div>
      <NuxtLink to="/luu-tru" class="see-all">
        <span>164 nơi lưu trú</span>
        <IconLine name="arrow-right" class="inline-arrow" aria-hidden="true" />
      </NuxtLink>
    </div>

    <!-- Tier 1: Horizontal 58/42 Architectural Lookbook Lead -->
    <article class="home-stay-card home-stay-card--lead" data-homestay-card>
      <NuxtLink :to="leadStay.to" class="home-stay-card__media" tabindex="-1" aria-hidden="true">
        <img
          class="home-stay-card__img"
          :src="leadStay.coverSrc"
          :alt="leadStay.name"
          width="800"
          height="500"
          loading="lazy"
          decoding="async"
          @error="onImgFallback"
        >
      </NuxtLink>

      <div class="home-stay-card__body">
        <div class="home-stay-card__meta">
          <span class="home-stay-card__area">
            <IconLine name="pin" aria-hidden="true" />
            <span>{{ leadStay.area }}</span>
          </span>
          <span class="home-stay-card__price">{{ leadStay.price }}</span>
        </div>

        <h3 class="home-stay-card__title">
          <NuxtLink :to="leadStay.to">{{ leadStay.name }}</NuxtLink>
        </h3>
        <p class="home-stay-card__desc">{{ leadStay.desc }}</p>

        <div class="home-stay-card__action">
          <NuxtLink :to="leadStay.to" class="btn btn-outline" data-color-role="action-secondary">
            <IconLine name="phone" aria-hidden="true" />
            <span>Liên hệ & Đặt phòng</span>
            <IconLine name="arrow-right" aria-hidden="true" />
          </NuxtLink>
        </div>
      </div>
    </article>

    <!-- Tier 2: Twin Companion Split Prints (Zero Orphan Slots, Zero Floating Pills) -->
    <div class="home-riverside-stays__companions">
      <article
        v-for="stay in companionStays"
        :key="stay.id"
        class="home-stay-card"
        data-homestay-card
      >
        <NuxtLink :to="stay.to" class="home-stay-card__media" tabindex="-1" aria-hidden="true">
          <img
            class="home-stay-card__img"
            :src="stay.coverSrc"
            :alt="stay.name"
            width="640"
            height="400"
            loading="lazy"
            decoding="async"
            @error="onImgFallback"
          >
        </NuxtLink>

        <div class="home-stay-card__body">
          <div class="home-stay-card__meta">
            <span class="home-stay-card__area">
              <IconLine name="pin" aria-hidden="true" />
              <span>{{ stay.area }}</span>
            </span>
            <span class="home-stay-card__price">{{ stay.price }}</span>
          </div>

          <h3 class="home-stay-card__title">
            <NuxtLink :to="stay.to">{{ stay.name }}</NuxtLink>
          </h3>
          <p class="home-stay-card__desc">{{ stay.desc }}</p>

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
  </section>
</template>

<script setup lang="ts">
import IconLine from '~/components/IconLine.vue'

interface CuratedHomestay {
  readonly id: string
  readonly name: string
  readonly price: string
  readonly area: string
  readonly desc: string
  readonly coverSrc: string
  readonly to: string
}

const CURATED_HOMESTAYS: readonly CuratedHomestay[] = [
  {
    id: 'homestay-ut-trinh',
    name: 'Homestay Út Trinh',
    price: '450.000–850.000đ/đêm',
    area: 'Xã An Bình · Cù lao sông Tiền',
    desc: 'Nhà gỗ cổ giữa vườn nhãn cù lao với bữa cơm quê, đạp xe đường làng và đêm đờn ca.',
    coverSrc: '/img/entities/homestay-ut-trinh.webp',
    to: '/dia-diem/homestay-ut-trinh',
  },
  {
    id: 'mekong-riverside-homestay',
    name: 'Mekong Riverside Homestay',
    price: '600.000–1.200.000đ/đêm',
    area: 'Phường Bình Minh · Vĩnh Long',
    desc: 'Khu nghỉ ven sông đón khách bằng tàu gỗ, tầm nhìn thẳng ra bến phù sa xanh mát.',
    coverSrc: '/img/entities/mekong-riverside-homestay.webp',
    to: '/dia-diem/mekong-riverside-homestay',
  },
  {
    id: 'nha-dua-cocohome',
    name: 'Nhà dừa CocoHome',
    price: '350.000–600.000đ/đêm',
    area: 'Xã Phú Phụng · Bến Tre (cũ)',
    desc: 'Kiến trúc dựng hoàn toàn từ thân dừa già, mành tre đan tay và gian bếp ấm ánh đèn dầu.',
    coverSrc: '/img/entities/nha-dua-cocohome.webp',
    to: '/dia-diem/nha-dua-cocohome',
  },
]

const leadStay = CURATED_HOMESTAYS[0]!
const companionStays = CURATED_HOMESTAYS.slice(1)

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
  padding-block: clamp(var(--space-8), 5vw, var(--space-12));
  border-top: 1px solid var(--color-border);
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

/* Lookbook Lead Horizontal Split (58/42) */
.home-stay-card {
  display: flex;
  flex-direction: column;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-surface);
  overflow: hidden;
  transition: border-color 0.25s ease;
}

.home-stay-card--lead {
  margin-block-start: var(--space-6);
}

@media (min-width: 860px) {
  .home-stay-card--lead {
    display: grid;
    grid-template-columns: minmax(0, 1.38fr) minmax(0, 1fr);
    align-items: stretch;
  }
}

.home-riverside-stays__companions {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 260px), 1fr));
  gap: var(--space-6);
  margin-block-start: var(--space-6);
}

.home-stay-card:hover {
  border-color: color-mix(in srgb, var(--color-brand) 45%, var(--color-border));
}

.home-stay-card:active {
  transform: scale(0.99);
}

.home-stay-card:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 3px;
  border-radius: var(--radius-surface);
}

.home-stay-card__media {
  display: block;
  width: 100%;
  aspect-ratio: 16 / 10;
  overflow: hidden;
  background: var(--color-surface-subtle);
}

.home-stay-card--lead .home-stay-card__media {
  height: 100%;
}

.home-stay-card__img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transition: transform 0.5s cubic-bezier(0.16, 1, 0.3, 1);
}

.home-stay-card:hover .home-stay-card__img {
  transform: scale(1.03);
}

.home-stay-card__body {
  padding: var(--space-5);
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  gap: var(--space-2);
  min-width: 0;
}

@media (min-width: 860px) {
  .home-stay-card--lead .home-stay-card__body {
    padding: clamp(var(--space-6), 4vw, var(--space-8));
    justify-content: center;
  }
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
  gap: var(--space-1);
  color: var(--color-text-muted);
  font-weight: var(--weight-bold);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
}

.home-stay-card__area .line-icon {
  color: var(--color-brand);
}

.home-stay-card__price {
  font-variant-numeric: tabular-nums;
  font-size: var(--text-xs);
  color: var(--color-brand);
  font-weight: var(--weight-bold);
  white-space: nowrap;
}

.home-stay-card__title {
  margin: 0;
  font-family: var(--font-editorial);
  font-size: var(--text-xl);
  line-height: 1.28;
  text-wrap: balance;
  overflow-wrap: break-word;
}

.home-stay-card--lead .home-stay-card__title {
  font-size: clamp(var(--text-xl), 2.5vw, var(--text-2xl));
}

.home-stay-card__title a {
  color: var(--color-text);
  text-decoration: none;
  transition: color 0.2s ease;
}

.home-stay-card__title a:hover {
  color: var(--color-action);
}

.home-stay-card__title a:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 2px;
  border-radius: var(--radius-control);
}

.home-stay-card__desc {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-wrap: pretty;
}

.home-stay-card__action {
  margin-top: auto;
  padding-top: var(--space-3);
}

.home-stay-card__action .btn {
  width: fit-content;
  min-height: 44px;
  padding: var(--space-2) var(--space-4);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  border-radius: var(--radius-control);
  text-decoration: none;
  background: var(--color-action-surface);
  color: var(--color-action);
  border: 1px solid var(--color-action-border);
  transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1), background-color 0.2s ease;
}

.home-stay-card__action .btn:hover {
  background: var(--color-action-surface-hover);
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

@media (prefers-reduced-motion: reduce) {
  .home-stay-card,
  .home-stay-card__img,
  .home-stay-card__action .btn .line-icon:last-child {
    transition: none;
  }
}
</style>
