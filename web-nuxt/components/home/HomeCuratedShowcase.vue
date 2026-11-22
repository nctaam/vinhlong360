<template>
  <section class="home-curated-showcase block reveal" aria-label="Bản đồ di sản hợp nhất Vĩnh Long" data-home-curated-showcase>
    <div class="home-curated-showcase__head section-head">
      <div class="sh-text">
        <span class="home-curated-showcase__eyebrow" data-color-role="brand">
          <IconLine name="landmark" aria-hidden="true" />
          <span>Di sản hợp nhất · Ba miền châu thổ</span>
        </span>
        <h2>Bản đồ di sản hợp nhất</h2>
        <p class="sh-sub">Những cổ tự Khmer, Văn Thánh Miếu và bến chợ nổi tiêu biểu trải dài khắp tỉnh Vĩnh Long thống nhất.</p>
      </div>
      <NuxtLink to="/du-lich" class="see-all">
        <span>Toàn bộ điểm đến</span>
        <IconLine name="arrow-right" class="inline-arrow" aria-hidden="true" />
      </NuxtLink>
    </div>

    <!-- Asymmetric Editorial Exhibition: 62% Monumental Plate + 38% Open Hairline Index -->
    <div class="home-curated-showcase__layout">
      <!-- 62% Lead Exhibition Plate: Chùa Âng (Trà Vinh cũ) -->
      <article class="home-curated-lead" data-curated-lead>
        <div class="home-curated-lead__media-container">
          <img
            class="home-curated-lead__img"
            :src="leadItem.coverSrc"
            :alt="leadItem.title"
            width="1200"
            height="800"
            loading="lazy"
            decoding="async"
            @error="onImgFallback"
          >
          <div class="home-curated-lead__scrim" aria-hidden="true" />

          <div class="home-curated-lead__top-bar">
            <button
              type="button"
              class="home-bookmark-btn"
              :class="{ 'is-saved': isSaved(leadItem.id) }"
              :aria-label="isSaved(leadItem.id) ? `Bỏ lưu ${leadItem.title}` : `Lưu ${leadItem.title}`"
              :aria-pressed="isSaved(leadItem.id)"
              @click.prevent.stop="toggleBookmark(leadItem)"
            >
              <IconLine :name="isSaved(leadItem.id) ? 'heart' : 'bookmark'" aria-hidden="true" />
              <span class="sr-only">{{ isSaved(leadItem.id) ? 'Đã lưu' : 'Lưu điểm đến' }}</span>
            </button>
          </div>

          <div class="home-curated-lead__overlay">
            <div class="home-curated-lead__meta">
              <span class="home-curated-lead__location">
                <IconLine name="pin" aria-hidden="true" />
                <span>{{ leadItem.location }}</span>
              </span>
            </div>

            <h3 class="home-curated-lead__title">
              <NuxtLink :to="leadItem.to">{{ leadItem.title }}</NuxtLink>
            </h3>

            <p class="home-curated-lead__desc">{{ leadItem.desc }}</p>

            <div class="home-curated-lead__actions">
              <NuxtLink :to="leadItem.to" class="btn btn-primary" data-color-role="action-primary">
                <span>Khám phá hồ sơ</span>
                <IconLine name="arrow-right" aria-hidden="true" />
              </NuxtLink>
              <NuxtLink :to="leadItem.mapTo" class="btn home-curated-lead__map-btn">
                <IconLine name="map" aria-hidden="true" />
                <span>Mở bản đồ</span>
              </NuxtLink>
            </div>
          </div>
        </div>
      </article>

      <!-- 38% Open Architectural Hairline Index (4 rows, zero dark scrims, zero pills) -->
      <div class="home-curated-satellites" role="list" aria-label="Chỉ mục di sản nổi bật">
        <article
          v-for="(item, idx) in satelliteItems"
          :key="item.id"
          class="home-curated-satellite"
          data-curated-satellite
          role="listitem"
        >
          <NuxtLink :to="item.to" class="home-curated-satellite__thumb-wrap" tabindex="-1" aria-hidden="true">
            <img
              class="home-curated-satellite__img"
              :src="item.coverSrc"
              :alt="item.title"
              width="208"
              height="156"
              loading="lazy"
              decoding="async"
              @error="onImgFallback"
            >
          </NuxtLink>

          <div class="home-curated-satellite__body">
            <div class="home-curated-satellite__meta">
              <span class="home-curated-satellite__num">0{{ idx + 1 }}</span>
              <span class="home-curated-satellite__area">{{ item.area }}</span>
            </div>
            <h4 class="home-curated-satellite__title">
              <NuxtLink :to="item.to">{{ item.title }}</NuxtLink>
            </h4>
            <p class="home-curated-satellite__summary">{{ item.summary }}</p>
            <NuxtLink :to="item.to" class="home-curated-satellite__link" :aria-label="`Xem hồ sơ ${item.title}`">
              <span>Xem hồ sơ</span>
              <IconLine name="arrow-right" aria-hidden="true" />
            </NuxtLink>
          </div>

          <button
            type="button"
            class="home-bookmark-btn home-bookmark-btn--sm"
            :class="{ 'is-saved': isSaved(item.id) }"
            :aria-label="isSaved(item.id) ? `Bỏ lưu ${item.title}` : `Lưu ${item.title}`"
            :aria-pressed="isSaved(item.id)"
            @click.prevent.stop="toggleBookmark(item)"
          >
            <IconLine :name="isSaved(item.id) ? 'heart' : 'bookmark'" aria-hidden="true" />
            <span class="sr-only">{{ isSaved(item.id) ? 'Đã lưu' : 'Lưu điểm đến' }}</span>
          </button>
        </article>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import IconLine from '~/components/IconLine.vue'
import { useFavorites } from '~/composables/useFavorites'

interface CuratedLead {
  readonly id: string
  readonly title: string
  readonly location: string
  readonly desc: string
  readonly coverSrc: string
  readonly to: string
  readonly mapTo: string
}

interface CuratedSatellite {
  readonly id: string
  readonly title: string
  readonly area: string
  readonly summary: string
  readonly coverSrc: string
  readonly to: string
}

const { isSaved, toggle } = useFavorites()

function toggleBookmark(target: { id: string; title: string; coverSrc?: string }) {
  toggle({
    id: target.id,
    name: target.title,
    title: target.title,
    type: 'attraction',
    image: target.coverSrc,
  })
}

const leadItem: CuratedLead = {
  id: 'chua-ang',
  title: 'Chùa Âng — Di tích kiến trúc Khmer bên Ao Bà Om',
  location: 'Phường Long Đức · Trà Vinh (cũ)',
  desc: 'Ngôi chùa Khmer cổ gần một thiên niên kỷ ẩn mình dưới tán dầu cổ thụ soi bóng xuống thắng cảnh Ao Bà Om.',
  coverSrc: '/img/entities/chua-ang.webp',
  to: '/dia-diem/chua-ang',
  mapTo: '/ban-do?selected=chua-ang',
}

const satelliteItems: readonly CuratedSatellite[] = [
  {
    id: 'van-thanh-mieu',
    title: 'Văn Thánh Miếu Vĩnh Long',
    area: 'Phường Phước Hậu · Di tích quốc gia',
    summary: 'Công trình Nho học phương Nam dựng năm 1864 bên rạch Long Hồ với hàng sao cổ thụ rợp bóng.',
    coverSrc: '/img/entities/van-thanh-mieu.webp',
    to: '/dia-diem/van-thanh-mieu',
  },
  {
    id: 'cho-noi-tra-on',
    title: 'Chợ nổi Trà Ôn lúc rạng sáng',
    area: 'Xã Lục Sĩ Thành · Sông Hậu',
    summary: 'Nếp thương hồ trăm năm họp chợ trên nhánh sông Hậu, rộn ràng ghe trái cây từ tinh mơ.',
    coverSrc: '/img/entities/cho-noi-tra-on.webp',
    to: '/dia-diem/cho-noi-tra-on',
  },
  {
    id: 'chua-vam-ray',
    title: 'Chùa Vàm Ray',
    area: 'Xã Trà Cú · Trà Vinh (cũ)',
    summary: 'Ngôi chùa Khmer mái tháp chạm trổ rực rỡ với tượng Phật nhập Niết Bàn quy mô lớn.',
    coverSrc: '/img/entities/chua-vam-ray.webp',
    to: '/dia-diem/chua-vam-ray',
  },
  {
    id: 'chua-tien-chau-tien-chau-tu',
    title: 'Chùa Tiên Châu cổ tự',
    area: 'Xã An Bình · Bãi Tiên',
    summary: 'Di tích lịch sử kiến trúc từ thế kỷ XVIII bên dòng Cổ Chiên xanh mát bóng cây cù lao.',
    coverSrc: '/img/entities/chua-tien-chau-tien-chau-tu.webp',
    to: '/dia-diem/chua-tien-chau-tien-chau-tu',
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
.home-curated-showcase {
  max-width: var(--maxw);
  margin-inline: auto;
  padding-inline: var(--space-5);
  padding-block: clamp(var(--space-8), 5vw, var(--space-12));
}

.home-curated-showcase__eyebrow {
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

.home-curated-showcase__layout {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--space-6);
  margin-block-start: var(--space-6);
}

@media (min-width: 960px) {
  .home-curated-showcase__layout {
    grid-template-columns: minmax(0, 1.35fr) minmax(0, 1fr);
    gap: var(--space-8);
    align-items: stretch;
  }
}

/* 62% Lead Architectural Plate */
.home-curated-lead {
  display: flex;
  flex-direction: column;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-surface);
  overflow: hidden;
  transition: border-color 0.25s ease;
}

.home-curated-lead:hover {
  border-color: color-mix(in srgb, var(--color-brand) 45%, var(--color-border));
}

.home-curated-lead:active {
  transform: scale(0.99);
}

.home-curated-lead:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 3px;
  border-radius: var(--radius-surface);
}

.home-curated-lead__media-container {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: clamp(22rem, 36vw, 31rem);
  overflow: hidden;
  background: var(--color-canvas);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.home-curated-lead__img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.55s cubic-bezier(0.16, 1, 0.3, 1);
}

.home-curated-lead:hover .home-curated-lead__img {
  transform: scale(1.03);
}

/* Calmed lower-third optical gradient only so sky and architecture breathe clean */
.home-curated-lead__scrim {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    180deg,
    transparent 45%,
    rgba(var(--black-rgb), 0.52) 72%,
    rgba(var(--black-rgb), 0.88) 100%
  );
  pointer-events: none;
}

.home-curated-lead__top-bar {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding: var(--space-4);
}

.home-bookmark-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 44px;
  min-height: 44px;
  border-radius: var(--radius-pill);
  background: rgba(var(--black-rgb), 0.72);
  color: var(--surface-white);
  border: 1px solid rgba(var(--white-rgb), 0.24);
  cursor: pointer;
  font-size: 1rem;
  flex-shrink: 0;
  transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1),
              background-color 0.2s ease,
              color 0.2s ease;
}

.home-bookmark-btn:hover {
  transform: scale(1.06);
  background: rgba(var(--black-rgb), 0.88);
}

.home-bookmark-btn:active {
  transform: scale(0.94);
}

.home-bookmark-btn:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 2px;
}

.home-bookmark-btn.is-saved {
  color: var(--surface-white);
  background: var(--color-brand);
  border-color: var(--color-brand);
}

.home-bookmark-btn--sm {
  min-width: 44px;
  min-height: 44px;
  background: transparent;
  color: var(--color-text-muted);
  border: 1px solid var(--color-border);
  align-self: flex-start;
}

.home-bookmark-btn--sm:hover {
  background: var(--color-surface-subtle);
  color: var(--color-brand);
  border-color: var(--color-brand);
}

.home-curated-lead__overlay {
  position: relative;
  z-index: 2;
  padding: var(--space-6);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  color: var(--surface-white);
}

.home-curated-lead__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-xs);
}

.home-curated-lead__location {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  color: var(--alluvial-gold);
  font-weight: var(--weight-bold);
  letter-spacing: var(--tracking-wide);
  text-transform: uppercase;
}

.home-curated-lead__title {
  margin: 0;
  font-family: var(--font-editorial);
  font-size: clamp(var(--text-xl), 2.8vw, var(--text-2xl));
  line-height: 1.25;
  text-wrap: balance;
  overflow-wrap: break-word;
}

.home-curated-lead__title a {
  color: var(--surface-white);
  text-decoration: none;
  transition: opacity 0.2s ease;
}

.home-curated-lead__title a:hover {
  opacity: 0.9;
}

.home-curated-lead__desc {
  margin: 0;
  font-size: var(--text-sm);
  line-height: 1.5;
  text-wrap: pretty;
  overflow-wrap: break-word;
  color: rgba(var(--white-rgb), 0.92);
  max-width: 52ch;
}

.home-curated-lead__actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  margin-top: var(--space-2);
}

.home-curated-lead__actions .btn {
  min-height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  border-radius: var(--radius-control);
  text-decoration: none;
  transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.2s ease;
}

.home-curated-lead__actions .btn .line-icon:last-child {
  transition: transform 0.2s ease;
}

.home-curated-lead:hover .home-curated-lead__actions .btn .line-icon:last-child,
.home-curated-lead__actions .btn:hover .line-icon:last-child {
  transform: translateX(3px);
}

.home-curated-lead__actions .btn:active {
  transform: scale(0.98);
}

.home-curated-lead__actions .btn:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 2px;
}

.home-curated-lead__map-btn {
  color: var(--surface-white);
  background: rgba(var(--black-rgb), 0.56);
  border: 1px solid rgba(var(--white-rgb), 0.45);
  backdrop-filter: blur(8px);
}

.home-curated-lead__map-btn:hover {
  background: rgba(var(--black-rgb), 0.74);
  border-color: rgba(var(--white-rgb), 0.72);
  color: var(--surface-white);
}

/* 38% Open Architectural Hairline Index */
.home-curated-satellites {
  display: grid;
  grid-template-columns: 1fr;
  border-block-start: 1px solid var(--color-border);
}

@media (min-width: 640px) {
  .home-curated-satellites {
    grid-template-columns: repeat(2, 1fr);
    gap: 0 var(--space-5);
  }
}

@media (min-width: 960px) {
  .home-curated-satellites {
    grid-template-columns: 1fr;
    gap: 0;
  }
}

.home-curated-satellite {
  display: grid;
  grid-template-columns: 100px minmax(0, 1fr) auto;
  gap: var(--space-4);
  align-items: start;
  padding-block: var(--space-4);
  border-block-end: 1px solid var(--color-border);
  background: transparent;
  transition: background-color 0.2s ease;
}

.home-curated-satellite:hover {
  background: color-mix(in srgb, var(--color-surface-subtle) 55%, transparent);
}

.home-curated-satellite:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 2px;
  border-radius: var(--radius-control);
}

.home-curated-satellite__thumb-wrap {
  display: block;
  width: 100px;
  aspect-ratio: 4 / 3;
  border-radius: var(--radius-control);
  overflow: hidden;
  border: 1px solid var(--color-border);
  background: var(--color-surface-subtle);
}

.home-curated-satellite__img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transition: transform 0.35s cubic-bezier(0.16, 1, 0.3, 1);
}

.home-curated-satellite:hover .home-curated-satellite__img {
  transform: scale(1.05);
}

.home-curated-satellite__body {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  min-width: 0;
}

.home-curated-satellite__meta {
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
  font-size: var(--text-2xs);
}

.home-curated-satellite__num {
  font-family: var(--font-editorial);
  font-style: italic;
  font-weight: var(--weight-semibold);
  font-variant-numeric: tabular-nums;
  color: var(--color-brand);
}

.home-curated-satellite__area {
  color: var(--color-text-muted);
  font-weight: var(--weight-bold);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
}

.home-curated-satellite__title {
  margin: 0;
  font-family: var(--font-editorial);
  font-size: var(--text-base);
  line-height: 1.3;
  text-wrap: balance;
  overflow-wrap: break-word;
}

.home-curated-satellite__title a {
  color: var(--color-text);
  text-decoration: none;
  transition: color 0.2s ease;
}

.home-curated-satellite__title a:hover {
  color: var(--color-action);
}

.home-curated-satellite__summary {
  margin: 0;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  line-height: 1.45;
  text-wrap: pretty;
  overflow-wrap: break-word;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.home-curated-satellite__link {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  color: var(--color-action);
  text-decoration: none;
  min-height: 44px;
  min-width: 44px;
  margin-block-start: -4px;
}

.home-curated-satellite__link .line-icon {
  transition: transform 0.2s ease;
}

.home-curated-satellite:hover .home-curated-satellite__link .line-icon,
.home-curated-satellite__link:hover .line-icon {
  transform: translateX(3px);
}

.home-curated-satellite__link:active {
  transform: scale(0.96);
}

.home-curated-satellite__link:focus-visible,
.home-curated-satellite__title a:focus-visible,
.home-curated-lead__title a:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 2px;
  border-radius: var(--radius-control);
}

@media (max-width: 480px) {
  .home-curated-satellite {
    grid-template-columns: 84px minmax(0, 1fr) auto;
    gap: var(--space-3);
  }
  .home-curated-satellite__thumb-wrap {
    width: 84px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .home-curated-lead,
  .home-curated-lead__img,
  .home-curated-satellite__img,
  .home-curated-lead__actions .btn .line-icon:last-child,
  .home-curated-satellite__link .line-icon {
    transition: none;
  }
}
</style>
