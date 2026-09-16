<template>
  <section class="home-curated-showcase block reveal" aria-label="Top Điểm Đến Phải Đến Vĩnh Long" data-home-curated-showcase>
    <div class="home-curated-showcase__head section-head">
      <div class="sh-text">
        <span class="home-curated-showcase__eyebrow" data-color-role="brand">
          <IconLine name="landmark" />
          <span>Kỳ quan sông nước · Di sản sống</span>
        </span>
        <h2>Top Điểm Đến <em class="editorial-italic-accent" aria-hidden="true">Phải Đến</em></h2>
        <p class="sh-sub">Tuyển tập những điểm chạm văn hóa, sinh thái và di sản độc bản tạo nên hồn cốt đất Vĩnh Long.</p>
      </div>
      <NuxtLink to="/du-lich" class="see-all">
        <span>Xem toàn bộ 220 điểm đến</span>
        <IconLine name="arrow-right" class="inline-arrow" aria-hidden="true" />
      </NuxtLink>
    </div>

    <!-- Asymmetric Editorial Layout 62/38 -->
    <div class="home-curated-showcase__layout">
      <!-- 62% Lead Heritage Showcase: Lò gạch Mang Thít -->
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
          <div class="home-curated-lead__badge">
            <IconLine name="flame" />
            <span>{{ leadItem.badge }}</span>
          </div>
        </div>

        <div class="home-curated-lead__body">
          <div class="home-curated-lead__meta">
            <span class="home-curated-lead__location">
              <IconLine name="pin" />
              <span>{{ leadItem.location }}</span>
            </span>
            <span class="home-curated-lead__coords">{{ leadItem.coordinates }}</span>
          </div>

          <h3 class="home-curated-lead__title">
            <NuxtLink :to="leadItem.to">{{ leadItem.title }}</NuxtLink>
          </h3>
          <p class="home-curated-lead__desc">{{ leadItem.desc }}</p>

          <div class="home-curated-lead__tips">
            <div class="home-curated-lead__tip">
              <IconLine name="sun" />
              <span><strong>Thời điểm đẹp nhất:</strong> {{ leadItem.bestTime }}</span>
            </div>
            <div class="home-curated-lead__tip">
              <IconLine name="camera" />
              <span><strong>Trải nghiệm độc bản:</strong> {{ leadItem.highlight }}</span>
            </div>
          </div>

          <div class="home-curated-lead__actions">
            <NuxtLink :to="leadItem.to" class="btn btn-primary" data-color-role="action-primary">
              <span>Khám phá di sản</span>
              <IconLine name="arrow-right" aria-hidden="true" />
            </NuxtLink>
            <NuxtLink :to="leadItem.mapTo" class="btn btn-outline" data-color-role="action-secondary">
              <IconLine name="map" />
              <span>Mở bản đồ thực địa</span>
            </NuxtLink>
          </div>
        </div>
      </article>

      <!-- 38% Satellite Cards (2x2 Grid) -->
      <div class="home-curated-satellites">
        <article
          v-for="item in satelliteItems"
          :key="item.id"
          class="home-curated-satellite"
          data-curated-satellite
        >
          <div class="home-curated-satellite__media">
            <img
              class="home-curated-satellite__img"
              :src="item.coverSrc"
              :alt="item.title"
              width="480"
              height="320"
              loading="lazy"
              decoding="async"
              @error="onImgFallback"
            >
            <span class="home-curated-satellite__tag">{{ item.tag }}</span>
          </div>
          <div class="home-curated-satellite__content">
            <span class="home-curated-satellite__area">
              <IconLine name="pin" />
              <span>{{ item.area }}</span>
            </span>
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

interface CuratedLead {
  readonly id: string
  readonly title: string
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
  readonly tag: string
  readonly area: string
  readonly summary: string
  readonly coverSrc: string
  readonly to: string
}

const leadItem: CuratedLead = {
  id: 'de-an-di-san-duong-dai-mang-thit',
  title: 'Quần Thể Di Sản Lò Gạch Gốm Đỏ Mang Thít',
  badge: 'Di sản Đương đại Sống · Kênh Thầy Cai',
  location: 'Huyện Mang Thít, Vĩnh Long',
  coordinates: '10.183° N, 106.096° E',
  desc: 'Gần 900 lò gạch gốm truyền thống hình vòm tháp chuông trải dọc bờ sông Cổ Chiên và kênh Thầy Cai — được ví như "những kim tự tháp đỏ phương Đông" có tuổi đời hơn một thế kỷ.',
  bestTime: '16:00 – 17:30 hoàng hôn đổ bóng vòm gốm',
  highlight: 'Thử tài nặn gốm đỏ tại xưởng gốm thủ công Thầy Kay & thăm Nhà Gốm Tư Buôi',
  coverSrc: '/img/entities/de-an-di-san-duong-dai-mang-thit.webp',
  to: '/dia-diem/de-an-di-san-duong-dai-mang-thit',
  mapTo: '/ban-do?selected=de-an-di-san-duong-dai-mang-thit',
}

const satelliteItems: readonly CuratedSatellite[] = [
  {
    id: 'cu-lao-an-binh',
    title: 'Cù Lao An Bình & Vườn Trái Cây',
    tag: 'Sinh thái Miệt vườn',
    area: 'Long Hồ',
    summary: 'Thủ phủ cây ăn trái nhiệt đới: chôm chôm chín rộ, sầu riêng Ri6 Bình Hòa Phước và mương rạch dừa nước.',
    coverSrc: '/img/entities/cu-lao-an-binh.webp',
    to: '/dia-diem/cu-lao-an-binh',
  },
  {
    id: 'khu-du-lich-cho-noi-tra-on',
    title: 'Chợ Nổi Trà Ôn Sông Hậu',
    tag: 'Thương hồ Sông nước',
    area: 'Trà Ôn',
    summary: 'Nét sinh hoạt giao thương độc bản theo con nước lớn rạng sáng, ghe thuyền buôn bán rộn ràng cây bẹo.',
    coverSrc: '/img/entities/khu-du-lich-cho-noi-tra-on.webp',
    to: '/dia-diem/khu-du-lich-cho-noi-tra-on',
  },
  {
    id: 'chua-shanghamangala-khmer-vung-liem',
    title: 'Chùa Hạnh Phúc Tăng (Sanghamangala)',
    tag: 'Tâm linh Di sản',
    area: 'Vũng Liêm',
    summary: 'Ngôi chùa Phật giáo Nam tông Khmer cổ kính nhất Vĩnh Long khởi lập năm 632 rợp bóng sao dầu trăm tuổi.',
    coverSrc: '/img/entities/chua-shanghamangala-khmer-vung-liem.webp',
    to: '/dia-diem/chua-shanghamangala-khmer-vung-liem',
  },
  {
    id: 'khu-du-lich-sinh-thai-miet-vuon-vinh-sang',
    title: 'KDL Sinh Thái Miệt Vườn Vinh Sang',
    tag: 'Điền dã Dân gian',
    area: 'An Bình, Long Hồ',
    summary: 'Hóa thân nông dân tát mương bắt cá đồng, chèo xuồng ba lá mương liếp và thưởng thức đờn ca tài tử.',
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
  padding-block: var(--space-8);
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
    align-items: stretch;
  }
}

/* 62% Lead Card */
.home-curated-lead {
  display: flex;
  flex-direction: column;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-surface);
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(var(--black-rgb), 0.06);
  transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.25s ease;
}

.home-curated-lead:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 32px rgba(var(--black-rgb), 0.12);
  border-color: color-mix(in srgb, var(--mangthit-600) 45%, var(--color-border));
}

.home-curated-lead__media-container {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 10;
  overflow: hidden;
  background: var(--color-canvas);
}

.home-curated-lead__img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.4s ease;
}

.home-curated-lead:hover .home-curated-lead__img {
  transform: scale(1.03);
}

.home-curated-lead__scrim {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(var(--black-rgb), 0.1) 0%, rgba(var(--black-rgb), 0.65) 100%);
}

.home-curated-lead__badge {
  position: absolute;
  top: var(--space-4);
  left: var(--space-4);
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-1h) var(--space-3);
  background: rgba(var(--black-rgb), 0.72);
  color: var(--surface-white);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border: 1px solid rgba(var(--white-rgb), 0.2);
  border-radius: var(--radius-pill, 9999px);
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  letter-spacing: 0.02em;
}

.home-curated-lead__badge .line-icon {
  color: var(--mangthit-500);
}

.home-curated-lead__body {
  display: flex;
  flex-direction: column;
  flex: 1;
  padding: var(--space-6);
  gap: var(--space-4);
}

.home-curated-lead__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.home-curated-lead__location {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  color: var(--color-brand);
  font-weight: var(--weight-bold);
}

.home-curated-lead__coords {
  font-family: var(--font-mono, monospace);
  color: var(--color-text-muted);
}

.home-curated-lead__title {
  margin: 0;
  font-family: var(--font-editorial-display);
  font-size: clamp(var(--text-xl), 3vw, var(--text-2xl));
  line-height: 1.25;
}

.home-curated-lead__title a {
  color: var(--color-text);
  text-decoration: none;
  transition: color 0.2s ease;
}

.home-curated-lead__title a:hover {
  color: var(--color-brand);
}

.home-curated-lead__desc {
  margin: 0;
  font-size: var(--text-sm);
  line-height: 1.6;
  color: var(--color-text);
  opacity: 0.9;
}

.home-curated-lead__tips {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  background: var(--color-canvas);
  border-radius: var(--radius-control);
  border-left: 3px solid var(--color-brand);
}

.home-curated-lead__tip {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  font-size: var(--text-xs);
  color: var(--color-text);
  line-height: 1.45;
}

.home-curated-lead__tip .line-icon {
  color: var(--color-brand);
  flex-shrink: 0;
  margin-top: 2px;
}

.home-curated-lead__actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  margin-top: auto;
  padding-top: var(--space-2);
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

/* 38% Satellite Cards */
.home-curated-satellites {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--space-4);
}

@media (min-width: 640px) and (max-width: 959px) {
  .home-curated-satellites {
    grid-template-columns: repeat(2, 1fr);
  }
}

.home-curated-satellite {
  display: grid;
  grid-template-columns: 120px 1fr;
  gap: var(--space-4);
  align-items: center;
  padding: var(--space-3);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-surface);
  box-shadow: 0 1px 4px rgba(var(--black-rgb), 0.04);
  transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.2s ease, box-shadow 0.2s ease;
}

.home-curated-satellite:hover {
  transform: translateY(-2px);
  border-color: color-mix(in srgb, var(--mangthit-600) 40%, var(--color-border));
  box-shadow: 0 6px 18px rgba(var(--black-rgb), 0.08);
}

.home-curated-satellite:active {
  transform: scale(0.98);
}

.home-curated-satellite__media {
  position: relative;
  width: 120px;
  height: 96px;
  border-radius: var(--radius-control);
  overflow: hidden;
  background: var(--color-canvas);
}

.home-curated-satellite__img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.home-curated-satellite__tag {
  position: absolute;
  bottom: 4px;
  left: 4px;
  padding: 1px 6px;
  background: rgba(var(--black-rgb), 0.75);
  color: var(--surface-white);
  border-radius: var(--radius-pill, 9999px);
  font-size: 10px;
  font-weight: var(--weight-bold);
}

.home-curated-satellite__content {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}

.home-curated-satellite__area {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: var(--color-brand);
  font-weight: var(--weight-bold);
}

.home-curated-satellite__title {
  margin: 0;
  font-family: var(--font-editorial-display);
  font-size: var(--text-base);
  line-height: 1.3;
}

.home-curated-satellite__title a {
  color: var(--color-text);
  text-decoration: none;
}

.home-curated-satellite__title a:hover {
  color: var(--color-brand);
}

.home-curated-satellite__summary {
  margin: 0;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  line-height: 1.4;
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
  color: var(--color-action);
  text-decoration: none;
  margin-top: 2px;
  min-height: var(--touch-min, 44px);
  min-width: var(--touch-min, 44px);
}

.home-curated-satellite__link:hover {
  text-decoration: underline;
}
</style>
