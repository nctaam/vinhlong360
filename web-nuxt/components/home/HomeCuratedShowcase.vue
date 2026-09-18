<template>
  <section class="home-curated-showcase block reveal" aria-label="Chốn dừng chân đáng ghé Vĩnh Long" data-home-curated-showcase>
    <div class="home-curated-showcase__head section-head">
      <div class="sh-text">
        <span class="home-curated-showcase__eyebrow" data-color-role="brand">
          <IconLine name="landmark" aria-hidden="true" />
          <span>Kỳ quan sông nước · Di sản sống</span>
        </span>
        <h2 aria-label="Chốn dừng chân đáng ghé">Chốn dừng chân <em class="editorial-italic-accent" aria-hidden="true">đáng ghé</em></h2>
        <p class="sh-sub">Những bến bờ sông nước, lò gạch nung đỏ rực và vựa cây trái rợp bóng phù sa đất Vĩnh Long.</p>
      </div>
      <NuxtLink to="/du-lich" class="see-all">
        <span>Xem trọn 220 điểm đến</span>
        <IconLine name="arrow-right" class="inline-arrow" aria-hidden="true" />
      </NuxtLink>
    </div>

    <!-- Asymmetric Editorial Layout 62/38 Mosaic -->
    <div class="home-curated-showcase__layout">
      <!-- 62% Lead Heritage Showcase: Lò gạch Mang Thít (80% photo visual area) -->
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
            <!-- Terroir badge and capture time -->
            <div class="home-curated-lead__badge">
              <IconLine name="flame" aria-hidden="true" />
              <span>{{ leadItem.terroir }} · {{ leadItem.badge }}</span>
            </div>

            <!-- Interactive Bookmark Button -->
            <button
              type="button"
              class="home-bookmark-btn"
              :class="{ 'is-saved': isItemSaved(leadItem.id) }"
              :aria-label="isItemSaved(leadItem.id) ? `Bỏ lưu ${leadItem.title}` : `Lưu ${leadItem.title}`"
              :aria-pressed="isItemSaved(leadItem.id)"
              @click.prevent.stop="toggleBookmark(leadItem)"
            >
              <IconLine :name="isItemSaved(leadItem.id) ? 'heart' : 'bookmark'" aria-hidden="true" />
              <span class="sr-only">{{ isItemSaved(leadItem.id) ? 'Đã lưu' : 'Lưu điểm đến' }}</span>
            </button>
          </div>

          <div class="home-curated-lead__overlay">
            <div class="home-curated-lead__trust">
              <SourceMark tier="official" source-title="Sở VHTTDL Vĩnh Long" verified-at="2026-09-01" compact />
              <FreshnessLine status="fresh" updated-label="Mùa vụ 2026" />
            </div>

            <div class="home-curated-lead__meta">
              <span class="home-curated-lead__location">
                <IconLine name="pin" aria-hidden="true" />
                <span>{{ leadItem.location }}</span>
              </span>
              <span class="home-curated-lead__coords">{{ leadItem.coordinates }}</span>
            </div>

            <h3 class="home-curated-lead__title">
              <NuxtLink :to="leadItem.to">{{ leadItem.title }}</NuxtLink>
            </h3>
            
            <p class="home-curated-lead__desc">{{ leadItem.desc }}</p>

            <div class="home-curated-lead__tips">
              <span class="home-curated-lead__tip">
                <IconLine name="sun" aria-hidden="true" />
                <span><strong>Đẹp nhất:</strong> {{ leadItem.bestTime }}</span>
              </span>
              <span class="home-curated-lead__tip">
                <IconLine name="camera" aria-hidden="true" />
                <span><strong>Điểm nhấn:</strong> {{ leadItem.highlight }}</span>
              </span>
            </div>

            <div class="home-curated-lead__actions">
              <NuxtLink :to="leadItem.to" class="btn btn-primary" data-color-role="action-primary">
                <span>Khám phá di sản</span>
                <IconLine name="arrow-right" aria-hidden="true" />
              </NuxtLink>
              <NuxtLink :to="leadItem.mapTo" class="btn btn-outline" data-color-role="action-secondary">
                <IconLine name="map" aria-hidden="true" />
                <span>Mở bản đồ</span>
              </NuxtLink>
            </div>
          </div>
        </div>
      </article>

      <!-- 38% Satellite Cards (2x2 Grid, Full-Bleed 100% Photo with Bottom Scrim) -->
      <div class="home-curated-satellites">
        <article
          v-for="item in satelliteItems"
          :key="item.id"
          class="home-curated-satellite"
          data-curated-satellite
        >
          <!-- Full-Bleed Satellite Photo (100% of card) -->
          <img
            class="home-curated-satellite__img"
            :src="item.coverSrc"
            :alt="item.title"
            width="480"
            height="360"
            loading="lazy"
            decoding="async"
            @error="onImgFallback"
          >

          <!-- Bottom Gradient Scrim -->
          <div class="home-curated-satellite__scrim" aria-hidden="true" />

          <!-- Floating Top Bar -->
          <div class="home-curated-satellite__top">
            <div class="home-curated-satellite__top-badges">
              <span class="home-curated-satellite__tag">{{ item.tag }}</span>
              <span class="home-curated-satellite__terroir-badge">{{ item.terroir }}</span>
            </div>

            <!-- Satellite Bookmark Button -->
            <button
              type="button"
              class="home-bookmark-btn home-bookmark-btn--sm"
              :class="{ 'is-saved': isItemSaved(item.id) }"
              :aria-label="isItemSaved(item.id) ? `Bỏ lưu ${item.title}` : `Lưu ${item.title}`"
              :aria-pressed="isItemSaved(item.id)"
              @click.prevent.stop="toggleBookmark(item)"
            >
              <IconLine :name="isItemSaved(item.id) ? 'heart' : 'bookmark'" aria-hidden="true" />
              <span class="sr-only">{{ isItemSaved(item.id) ? 'Đã lưu' : 'Lưu điểm đến' }}</span>
            </button>
          </div>

          <!-- Overlaid Bottom Content (<= 25% card height) -->
          <div class="home-curated-satellite__overlay home-curated-satellite__content">
            <div class="home-curated-satellite__trust">
              <SourceMark tier="official" compact />
              <FreshnessLine status="fresh" updated-label="2026" />
            </div>
            <div class="home-curated-satellite__meta">
              <span class="home-curated-satellite__area">
                <IconLine name="pin" aria-hidden="true" />
                <span>{{ item.area }}</span>
              </span>
              <span v-if="item.coordinates" class="home-curated-satellite__coords">{{ item.coordinates }}</span>
            </div>
            <h4 class="home-curated-satellite__title">
              <NuxtLink :to="item.to">{{ item.title }}</NuxtLink>
            </h4>
            <p class="home-curated-satellite__summary">{{ item.summary }}</p>
            <NuxtLink :to="item.to" class="home-curated-satellite__link">
              <span>Xem trải nghiệm</span>
              <IconLine name="arrow-right" aria-hidden="true" />
            </NuxtLink>
          </div>
        </article>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import IconLine from '~/components/IconLine.vue'
import SourceMark from '~/components/SourceMark.vue'
import FreshnessLine from '~/components/FreshnessLine.vue'
import { useFavorites } from '~/composables/useFavorites'

interface CuratedLead {
  readonly id: string
  readonly title: string
  readonly terroir: string
  readonly badge: string
  readonly location: string
  readonly coordinates: string
  readonly desc: string
  readonly bestTime: string
  readonly highlight: string
  readonly coverSrc: string
  readonly to: string
  readonly mapTo: string
}

interface CuratedSatellite {
  readonly id: string
  readonly title: string
  readonly terroir: string
  readonly tag: string
  readonly area: string
  readonly coordinates?: string
  readonly summary: string
  readonly coverSrc: string
  readonly to: string
}

const { isSaved, toggle } = useFavorites()

function isItemSaved(id: string): boolean {
  return isSaved(id)
}

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
  id: 'de-an-di-san-duong-dai-mang-thit',
  title: 'Quần Thể Di Sản Lò Gạch Gốm Đỏ Mang Thít',
  terroir: 'Đất nung Mang Thít',
  badge: '16:30 – 17:45 · Hoàng hôn vòm gốm Kênh Thầy Cai',
  location: 'Huyện Mang Thít, Vĩnh Long',
  coordinates: "10°15'N · 105°58'E",
  desc: 'Quần thể gần 900 vòm gốm tháp chuông đỏ rực dọc kênh Thầy Cai, di sản đương đại sống bên bờ Cổ Chiên.',
  bestTime: '16:30 – 17:45 hoàng hôn vòm gốm',
  highlight: 'Thử tài nặn gốm & thăm Nhà Gốm Tư Buôi',
  coverSrc: '/img/entities/de-an-di-san-duong-dai-mang-thit.webp',
  to: '/dia-diem/de-an-di-san-duong-dai-mang-thit',
  mapTo: '/ban-do?selected=de-an-di-san-duong-dai-mang-thit',
}

const satelliteItems: readonly CuratedSatellite[] = [
  {
    id: 'cu-lao-an-binh',
    title: 'Cù Lao An Bình & Vườn Trái Cây',
    terroir: 'Xanh Cù Lao',
    tag: 'Sinh thái Miệt vườn',
    area: 'Long Hồ',
    coordinates: "10°16'N · 105°59'E",
    summary: 'Miệt vườn trái cây ngút ngàn, sầu riêng Ri6 chín bùi và rạch dừa nước thanh bình giữa sông Tiền.',
    coverSrc: '/img/entities/cu-lao-an-binh.webp',
    to: '/dia-diem/cu-lao-an-binh',
  },
  {
    id: 'khu-du-lich-cho-noi-tra-on',
    title: 'Chợ Nổi Trà Ôn Sông Hậu',
    terroir: 'Phù Sa Cổ Chiên',
    tag: 'Thương hồ Sông nước',
    area: 'Trà Ôn',
    coordinates: "9°58'N · 105°55'E",
    summary: 'Thương hồ sông Hậu họp chợ theo con nước sớm, rộn ràng tiếng cười nói và cây bẹo mời chào sản vật.',
    coverSrc: '/img/entities/khu-du-lich-cho-noi-tra-on.webp',
    to: '/dia-diem/khu-du-lich-cho-noi-tra-on',
  },
  {
    id: 'chua-shanghamangala-khmer-vung-liem',
    title: 'Chùa Hạnh Phúc Tăng (Sanghamangala)',
    terroir: 'Phù Sa Cổ Chiên',
    tag: 'Tâm linh Di sản',
    area: 'Vũng Liêm',
    coordinates: "10°07'N · 106°11'E",
    summary: 'Ngôi chùa Khmer cổ kính từ năm 632, kiến trúc tháp nhọn trầm mặc dưới bóng sao dầu nghìn năm.',
    coverSrc: '/img/entities/chua-shanghamangala-khmer-vung-liem.webp',
    to: '/dia-diem/chua-shanghamangala-khmer-vung-liem',
  },
  {
    id: 'khu-du-lich-sinh-thai-miet-vuon-vinh-sang',
    title: 'KDL Sinh Thái Miệt Vườn Vinh Sang',
    terroir: 'Xanh Cù Lao',
    tag: 'Điền dã Dân gian',
    area: 'An Bình, Long Hồ',
    coordinates: "10°16'N · 105°59'E",
    summary: 'Trải nghiệm tát mương bắt cá, chèo xuồng mương liếp và nghe đờn ca tài tử bên vườn dừa trĩu quả.',
    coverSrc: '/img/entities/khu-du-lich-sinh-thai-miet-vuon-vinh-sang.webp',
    to: '/dia-diem/khu-du-lich-sinh-thai-miet-vuon-vinh-sang',
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
  padding-block: clamp(var(--space-fib-4), 6vw, var(--space-fib-5));
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
  gap: var(--space-fib-4);
  margin-block-start: var(--space-fib-4);
}

@media (min-width: 960px) {
  .home-curated-showcase__layout {
    grid-template-columns: minmax(0, 1.35fr) minmax(0, 1fr);
    align-items: stretch;
  }
}

/* 80% Lead Photo Mosaic Tile */
.home-curated-lead {
  display: flex;
  flex-direction: column;
  background: var(--color-surface);
  border: 1px solid var(--border-liquid-glass, var(--color-border));
  border-radius: var(--radius-surface);
  overflow: hidden;
  box-shadow: var(--shadow-card-ambient);
  transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.25s ease, border-color 0.25s ease;
}

.home-curated-lead:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 32px rgba(var(--black-rgb), 0.12);
  border-color: color-mix(in srgb, var(--mangthit-600) 45%, var(--color-border));
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
  min-height: 520px;
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
  transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}

.home-curated-lead:hover .home-curated-lead__img {
  transform: scale(1.04);
}

.home-curated-lead__scrim {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    180deg,
    rgba(var(--black-rgb), 0.25) 0%,
    rgba(var(--black-rgb), 0.08) 30%,
    rgba(var(--black-rgb), 0.55) 50%,
    rgba(var(--black-rgb), 0.78) 65%,
    rgba(var(--black-rgb), 0.92) 85%,
    rgba(var(--black-rgb), 0.88) 100%
  );
  pointer-events: none;
}

.home-curated-lead__top-bar {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4);
}

.home-curated-lead__badge {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-1h) var(--space-3);
  background: rgba(var(--black-rgb), 0.75);
  color: var(--surface-white);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border: 1px solid var(--border-liquid-glass);
  border-radius: var(--radius-pill, 9999px);
  box-shadow: var(--shadow-card-ambient);
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  letter-spacing: 0.02em;
}

.home-curated-lead__badge .line-icon {
  color: var(--surface-white);
}

.home-bookmark-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 44px;
  min-height: 44px;
  border-radius: 50%;
  background: rgba(var(--black-rgb), 0.75);
  color: var(--surface-white);
  border: 1px solid var(--border-liquid-glass);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  box-shadow: var(--shadow-card-ambient);
  cursor: pointer;
  font-size: 1.1rem;
  transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1),
              background-color 0.2s ease,
              color 0.2s ease;
}

.home-bookmark-btn:hover {
  transform: scale(1.08);
  color: var(--coral-error);
  background: rgba(var(--black-rgb), 0.9);
}

.home-bookmark-btn:active {
  transform: scale(0.92);
}

.home-bookmark-btn:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 2px;
}

.home-bookmark-btn.is-saved {
  color: var(--coral-error);
  background: rgba(var(--black-rgb), 0.85);
  border-color: color-mix(in srgb, var(--coral-error) 40%, transparent);
}

.home-bookmark-btn--sm {
  min-width: 44px;
  min-height: 44px;
  position: absolute;
  top: var(--space-2);
  right: var(--space-2);
  z-index: 2;
}

.home-curated-lead__overlay {
  position: relative;
  z-index: 2;
  padding: var(--space-6);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  color: var(--surface-white);
}

.home-curated-lead__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  font-size: var(--text-xs);
  color: rgba(var(--white-rgb), 0.85);
}

.home-curated-lead__location {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  color: var(--surface-white);
  font-weight: var(--weight-bold);
}

.home-curated-lead__location .line-icon {
  color: var(--surface-white);
}

.home-curated-lead__coords {
  font-family: var(--font-mono, monospace);
  color: var(--alluvial-gold);
  font-weight: var(--weight-medium);
}

.home-curated-lead__title {
  margin: 0;
  font-family: var(--font-editorial-display);
  font-size: clamp(var(--text-xl), 3vw, var(--text-2xl));
  line-height: 1.25;
}

.home-curated-lead__title a {
  color: var(--surface-white);
  text-decoration: none;
  transition: color 0.2s ease;
}

.home-curated-lead__title a:hover {
  color: var(--alluvial-gold);
}

.home-curated-lead__desc {
  margin: 0;
  font-size: var(--text-sm);
  line-height: 1.55;
  color: rgba(var(--white-rgb), 0.92);
}

.home-curated-lead__tips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2) var(--space-4);
  font-size: var(--text-xs);
  color: rgba(var(--white-rgb), 0.8);
}

.home-curated-lead__tip {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1h);
}

.home-curated-lead__tip .line-icon {
  color: var(--surface-white);
  flex-shrink: 0;
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
  transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.2s ease;
}

.home-curated-lead__actions .btn:active {
  transform: scale(0.98);
}

.home-curated-lead__actions .btn:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 2px;
}

/* 38% Satellite Cards */
.home-curated-satellites {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--space-fib-3);
}

@media (min-width: 640px) {
  .home-curated-satellites {
    grid-template-columns: repeat(2, 1fr);
  }
}

/* Full-Bleed Satellite Card (100% Photo visual area) */
.home-curated-satellite {
  position: relative;
  min-height: 380px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  background: var(--color-canvas);
  border: 1px solid var(--border-liquid-glass, var(--color-border));
  border-radius: var(--radius-surface);
  overflow: hidden;
  box-shadow: var(--shadow-card-ambient);
  transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.2s ease, box-shadow 0.2s ease;
}

.home-curated-satellite:hover {
  transform: translateY(-2px);
  border-color: color-mix(in srgb, var(--mangthit-600) 40%, var(--color-border));
  box-shadow: 0 6px 18px rgba(var(--black-rgb), 0.16);
}

.home-curated-satellite:active {
  transform: scale(0.98);
}

.home-curated-satellite:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 3px;
  border-radius: var(--radius-surface);
}

/* Photo fills 100% of card */
.home-curated-satellite__img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1);
  z-index: 0;
}

.home-curated-satellite:hover .home-curated-satellite__img {
  transform: scale(1.04);
}

/* Bottom Gradient Scrim Overlay */
.home-curated-satellite__scrim {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    180deg,
    rgba(var(--black-rgb), 0.25) 0%,
    rgba(var(--black-rgb), 0.08) 30%,
    rgba(var(--black-rgb), 0.55) 50%,
    rgba(var(--black-rgb), 0.78) 65%,
    rgba(var(--black-rgb), 0.92) 85%,
    rgba(var(--black-rgb), 0.88) 100%
  );
  pointer-events: none;
  z-index: 1;
}

/* Floating Top Bar */
.home-curated-satellite__top {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3);
}

.home-curated-satellite__top-badges {
  display: flex;
  align-items: center;
  gap: var(--space-1h);
  flex-wrap: wrap;
}

.home-curated-satellite__terroir-badge {
  padding: 3px 8px;
  background: rgba(var(--black-rgb), 0.78);
  color: var(--alluvial-gold);
  border: 1px solid var(--border-liquid-glass);
  border-radius: var(--radius-pill, 9999px);
  font-size: 11px;
  font-weight: var(--weight-semibold);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  box-shadow: var(--shadow-card-ambient);
  transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1), background-color 0.2s ease;
}

.home-curated-satellite:hover .home-curated-satellite__terroir-badge {
  transform: translateY(-1px);
}

.home-curated-satellite__tag {
  padding: 3px 10px;
  background: rgba(var(--black-rgb), 0.78);
  color: var(--surface-white);
  border: 1px solid var(--border-liquid-glass);
  border-radius: var(--radius-pill, 9999px);
  font-size: 11px;
  font-weight: var(--weight-bold);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  box-shadow: var(--shadow-card-ambient);
}

.home-curated-lead__trust {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-1);
}

.home-curated-satellite__trust {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-1h);
  margin-bottom: 2px;
}

/* Bottom Content Overlay (<= 25% card height) */
.home-curated-satellite__overlay {
  position: relative;
  z-index: 2;
  display: flex;
  flex-direction: column;
  gap: var(--space-1h);
  padding: var(--space-4);
  color: var(--surface-white);
}

.home-curated-satellite__meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.home-curated-satellite__coords {
  font-family: var(--font-mono, monospace);
  font-size: 11px;
  color: var(--alluvial-gold);
  font-weight: var(--weight-medium);
}

.home-curated-satellite__area {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: var(--surface-white);
  font-weight: var(--weight-bold);
}

.home-curated-satellite__area .line-icon {
  color: var(--surface-white);
}

.home-curated-satellite__title {
  margin: 0;
  font-family: var(--font-editorial-display);
  font-size: var(--text-sm);
  line-height: 1.35;
}

.home-curated-satellite__title a {
  color: var(--surface-white);
  text-decoration: none;
  text-shadow: 0 1px 3px rgba(var(--black-rgb), 0.5);
  transition: opacity 0.2s ease;
}

.home-curated-satellite__title a:hover {
  opacity: 0.85;
}

.home-curated-satellite__summary {
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
}

.home-curated-satellite__link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  color: var(--surface-white);
  text-decoration: underline;
  text-shadow: 0 1px 2px rgba(var(--black-rgb), 0.4);
  margin-top: auto;
  min-height: var(--touch-min, 44px);
  min-width: var(--touch-min, 44px);
}

.home-curated-satellite__link:hover {
  opacity: 0.85;
}

.home-curated-satellite__link:active {
  transform: scale(0.96);
}

.home-curated-satellite__link:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 2px;
  border-radius: var(--radius-control);
}

.home-curated-satellite__title a:focus-visible,
.home-curated-lead__title a:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 2px;
  border-radius: var(--radius-control);
}
</style>
