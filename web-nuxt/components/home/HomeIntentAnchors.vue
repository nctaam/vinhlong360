<template>
  <nav class="home-intent-anchors" aria-label="Bộ phím tắt khám phá nhanh theo nhu cầu lữ khách">
    <div class="home-intent-anchors__inner">
      <div class="home-intent-anchors__header">
        <div class="home-intent-anchors__eyebrow-row">
          <span class="editorial-folio-tag" aria-hidden="true">FOLIO I · CHỌN GU TRẢI NGHIỆM</span>
          <span class="archival-gps-badge sr-only" aria-label="Tọa độ địa lý Vĩnh Long">
            <IconLine name="pin" aria-hidden="true" />
            <span>10°15'07"N 105°58'34"E · CỔ CHIÊN BASIN</span>
          </span>
        </div>

        <div class="home-intent-anchors__title-row">
          <div>
            <span class="home-intent-anchors__eyebrow">
              <IconLine name="compass" aria-hidden="true" />
              <span>Lối rẽ lữ hành theo gu</span>
            </span>
            <h2 class="home-intent-anchors__title" aria-label="Lối rẽ khám phá nhanh">Lối rẽ <em class="editorial-italic-accent" aria-hidden="true">khám phá nhanh</em></h2>
          </div>

          <div class="artisanal-terroir-seal sr-only" aria-hidden="true">
            <span class="artisanal-terroir-seal__ring">
              <span class="artisanal-terroir-seal__inner">BẢN ĐỊA<br>CHỨNG THỰC</span>
            </span>
          </div>
        </div>
      </div>

      <!-- Quick Anchors Grid -->
      <div class="home-intent-anchors__grid" role="list">
        <NuxtLink
          v-for="anchor in INTENT_ANCHORS"
          :key="anchor.key"
          :to="anchor.to"
          class="home-intent-anchor"
          :class="{ 'is-selected': activePersonaKey === anchor.key }"
          :data-intent="anchor.key"
          data-intent-anchor
          role="listitem"
          @mouseenter="activePersonaKey = anchor.key"
          @focus="activePersonaKey = anchor.key"
        >
          <span class="home-intent-anchor__media">
            <img
              class="home-intent-anchor__avatar"
              :src="anchor.avatarSrc"
              :alt="anchor.label"
              width="38"
              height="38"
              loading="lazy"
              decoding="async"
              @error="onAvatarFallback"
            >
            <span class="home-intent-anchor__icon-badge" :class="`home-intent-anchor__icon-badge--${anchor.accent}`" aria-hidden="true">
              <IconLine :name="anchor.icon" aria-hidden="true" />
            </span>
          </span>
          <span class="home-intent-anchor__content">
            <strong class="home-intent-anchor__label">{{ anchor.label }}</strong>
            <span class="home-intent-anchor__hint">{{ anchor.hint }}</span>
          </span>
          <IconLine name="arrow-right" class="home-intent-anchor__arrow" aria-hidden="true" />
        </NuxtLink>
      </div>

      <!-- Curator's Fast Persona Capsule -->
      <aside
        v-if="currentPersona"
        class="home-persona-capsule cinema-glass-plate alluvial-sheen"
        :aria-label="`Tuyển tập tiêu biểu cho gu ${currentPersona.label}`"
      >
        <div class="home-persona-capsule__header">
          <div class="home-persona-capsule__tag">
            <IconLine :name="currentPersona.icon" aria-hidden="true" />
            <span>ĐỀ CỬ BIÊN TẬP · {{ currentPersona.label.toUpperCase() }}</span>
          </div>
          <NuxtLink :to="currentPersona.to" class="home-persona-capsule__all-link">
            <span>Xem trọn danh mục</span>
            <IconLine name="arrow-right" aria-hidden="true" />
          </NuxtLink>
        </div>

        <div class="home-persona-capsule__spots">
          <NuxtLink
            v-for="spot in currentPersona.spots"
            :key="spot.title"
            :to="spot.to"
            class="home-persona-spot"
          >
            <div class="home-persona-spot__meta">
              <span class="home-persona-spot__distance">
                <IconLine name="pin" aria-hidden="true" />
                <span>{{ spot.distance }}</span>
              </span>
              <span class="home-persona-spot__duration">{{ spot.duration }}</span>
            </div>
            <strong class="home-persona-spot__title">{{ spot.title }}</strong>
            <p class="home-persona-spot__highlight">{{ spot.highlight }}</p>
          </NuxtLink>
        </div>
      </aside>
    </div>
  </nav>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import IconLine from '~/components/IconLine.vue'

interface PersonaSpot {
  readonly title: string
  readonly distance: string
  readonly duration: string
  readonly highlight: string
  readonly to: string
}

interface IntentAnchor {
  readonly key: string
  readonly label: string
  readonly hint: string
  readonly to: string
  readonly icon: string
  readonly avatarSrc: string
  readonly accent: 'orchard' | 'mangthit' | 'river' | 'amber' | 'clay'
  readonly spots: readonly PersonaSpot[]
}

const INTENT_ANCHORS: readonly IntentAnchor[] = [
  {
    key: 'eco-orchard',
    label: 'Miệt vườn Cù lao & Trái ngọt',
    hint: 'Vườn chôm chôm, sầu riêng Ri6 cù lao An Bình',
    to: '/tim-kiem?q=sinh+th%C3%A1i+mi%E1%BB%87t+v%C6%B0%E1%BB%9Dn',
    icon: 'sprout',
    avatarSrc: '/img/entities/cu-lao-an-binh.webp',
    accent: 'orchard',
    spots: [
      {
        title: 'Cù lao An Bình',
        distance: '1.2 km từ phà An Bình',
        duration: '2–4 giờ',
        highlight: 'Đạp xe len lỏi rợp bóng dừa, ngắm phù sa sông Cổ Chiên',
        to: '/dia-diem/cu-lao-an-binh',
      },
      {
        title: 'Vườn chôm chôm Bình Hòa Phước',
        distance: '4.5 km ven sông',
        duration: '1.5–2 giờ',
        highlight: 'Tự tay hái và thưởng thức chôm chôm trĩu cành lúc đọng sương',
        to: '/tim-kiem?q=vuon+chom+chom',
      },
      {
        title: 'Cù lao Mây (Trà Ôn)',
        distance: '18 km xuôi dòng',
        duration: 'Nửa ngày',
        highlight: 'Xứ sở cù lao thanh bình, vườn cây ăn trái quanh năm trĩu quả',
        to: '/tim-kiem?q=cu+lao+may',
      },
    ],
  },
  {
    key: 'heritage-craft',
    label: 'Làng gốm đỏ & Nghề thủ công',
    hint: 'Lò gạch gốm đỏ Mang Thít & làng đan lát',
    to: '/tim-kiem?q=l%C3%A0ng+ngh%E1%BB%81+g%E1%BB%91m',
    icon: 'vase',
    avatarSrc: '/img/entities/de-an-di-san-duong-dai-mang-thit.webp',
    accent: 'mangthit',
    spots: [
      {
        title: 'Di sản Đương đại Mang Thít',
        distance: '12 km từ trung tâm',
        duration: '2–3 giờ',
        highlight: 'Hàng ngàn lò gạch cổ thế kỷ bên dòng kênh Thầy Cai huyền ảo',
        to: '/dia-diem/de-an-di-san-duong-dai-mang-thit',
      },
      {
        title: 'Làng nghề gốm Vĩnh Long',
        distance: '8.5 km ven sông',
        duration: '1.5 giờ',
        highlight: 'Tận mắt xem nghệ nhân vuốt gốm đất sét nung đỏ đặc trưng',
        to: '/tim-kiem?q=gom+do+mang+thit',
      },
      {
        title: 'Làng đan lát Lục bình Tam Bình',
        distance: '16 km',
        duration: '1–2 giờ',
        highlight: 'Nét tài hoa từ cây lục bình dập dềnh bến nước Cửu Long',
        to: '/tim-kiem?q=lang+nghe+dan+lat',
      },
    ],
  },
  {
    key: 'spiritual-culture',
    label: 'Chốn cổ tự & Nếp xưa xứ sở',
    hint: 'Chùa Khmer Hạnh Phúc Tăng, Văn Thánh Miếu',
    to: '/tim-kiem?q=t%C3%A2m+linh+di+s%E1%BA%A3n',
    icon: 'landmark',
    avatarSrc: '/img/entities/chua-shanghamangala-khmer-vung-liem.webp',
    accent: 'clay',
    spots: [
      {
        title: 'Chùa Khmer Sanghamangala',
        distance: '28 km (Vũng Liêm)',
        duration: '1.5–2 giờ',
        highlight: 'Ngôi cổ tự Khmer cổ kính hơn 1.000 năm với kiến trúc Angkor rực rỡ',
        to: '/dia-diem/chua-shanghamangala-khmer-vung-liem',
      },
      {
        title: 'Văn Thánh Miếu Vĩnh Long',
        distance: '2.0 km từ bến phà',
        duration: '1 giờ',
        highlight: 'Một trong ba Văn Thánh Miếu đầu tiên của xứ Nam Kỳ lục tỉnh',
        to: '/dia-diem/van-thanh-mieu-vinh-long',
      },
      {
        title: 'Chùa Tiên Châu (Cù lao An Bình)',
        distance: '1.5 km qua phà',
        duration: '1 giờ',
        highlight: 'Chùa cổ thanh tịnh tọa lạc bên Bãi Tiên huyền thoại sông Tiền',
        to: '/tim-kiem?q=chua+tien+chau',
      },
    ],
  },
  {
    key: 'culinary-market',
    label: 'Thức ngon chợ nổi & Quán quê',
    hint: 'Cá tai tượng chiên xù, bánh xèo & Chợ nổi Trà Ôn',
    to: '/am-thuc',
    icon: 'bowl',
    avatarSrc: '/img/entities/ca-tai-tuong-chien-xu.webp',
    accent: 'amber',
    spots: [
      {
        title: 'Cá tai tượng chiên xù cuốn bánh tráng',
        distance: 'Tại các điểm miệt vườn',
        duration: 'Bữa trưa / tối',
        highlight: 'Cá chiên xù vảy giòn rụm, cuốn rau rừng chấm mắm me chua ngọt',
        to: '/dia-diem/ca-tai-tuong-chien-xu',
      },
      {
        title: 'Chợ nổi Trà Ôn',
        distance: '35 km xuôi sông Hậu',
        duration: '05:00 – 07:30',
        highlight: 'Ăn tô bún bò bốc khói ngắm ghe thuyền tấp nập giao thương',
        to: '/am-thuc',
      },
      {
        title: 'Khoai lang Bình Tân & Cam sành Tam Bình',
        distance: 'Xứ rau màu phù sa',
        duration: 'Thức quà mua về',
        highlight: 'Đặc sản nức tiếng củ bùi ngọt lịm, múi cam mọng nước mát lành',
        to: '/ocop',
      },
    ],
  },
  {
    key: 'riverside-homestay',
    label: 'Nhà vườn ven sông & Đờn ca',
    hint: 'Homestay Út Trinh, Mekong Riverside & đờn ca',
    to: '/luu-tru',
    icon: 'home',
    avatarSrc: '/img/entities/homestay-ut-trinh.webp',
    accent: 'river',
    spots: [
      {
        title: 'Homestay Út Trinh (An Bình)',
        distance: '1.8 km từ bến đò',
        duration: 'Lưu trú qua đêm',
        highlight: 'Nấu ăn cùng gia chủ, nghe đờn ca tài tử dưới ánh trăng miệt vườn',
        to: '/dia-diem/homestay-ut-trinh',
      },
      {
        title: 'Mekong Riverside Homestay',
        distance: '3.0 km ven sông',
        duration: 'Lưu trú sinh thái',
        highlight: 'Thức giấc cùng tiếng chim hót và sương sớm bến sông Cổ Chiên',
        to: '/luu-tru',
      },
      {
        title: 'Nhà xưa Ba Lình',
        distance: '2.5 km',
        duration: 'Nửa ngày / Qua đêm',
        highlight: 'Ngôi nhà rường ba gian hai chái đậm hồn kiến trúc Nam Bộ xưa',
        to: '/luu-tru',
      },
    ],
  },
]

const activePersonaKey = ref<string>('eco-orchard')

const currentPersona = computed(() => {
  return INTENT_ANCHORS.find(a => a.key === activePersonaKey.value) ?? INTENT_ANCHORS[0]!
})

function onAvatarFallback(e: Event) {
  const img = e.target as HTMLImageElement
  if (img && !img.dataset.fallbackApplied) {
    img.dataset.fallbackApplied = 'true'
    img.src = '/img/spread/song-nuoc.webp'
  }
}
</script>

<style scoped>
.home-intent-anchors {
  max-width: var(--maxw);
  margin-inline: auto;
  padding-inline: var(--space-5);
  padding-block: var(--space-6) var(--space-4);
}

.home-intent-anchors__inner {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.home-intent-anchors__header {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.home-intent-anchors__eyebrow-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  flex-wrap: wrap;
}

.editorial-folio-tag {
  font-family: var(--font-mono, monospace);
  font-size: 11px;
  font-weight: var(--weight-bold);
  letter-spacing: 0.12em;
  color: var(--mangthit-600);
  text-transform: uppercase;
}

.archival-gps-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-family: var(--font-mono, monospace);
  font-size: 10.5px;
  color: var(--color-text-muted);
  letter-spacing: 0.04em;
  opacity: 0.85;
}

.home-intent-anchors__title-row {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--space-4);
}

.home-intent-anchors__eyebrow {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--color-brand);
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  text-transform: uppercase;
  letter-spacing: var(--tracking-caps);
}

.home-intent-anchors__title {
  font-family: var(--font-editorial-display);
  font-size: clamp(var(--text-xl), 3vw, var(--text-2xl));
  color: var(--color-text);
  margin: 0;
  letter-spacing: -0.01em;
}

/* Artisanal Red Lacquer Seal */
.artisanal-terroir-seal {
  flex-shrink: 0;
  display: none;
}

@media (min-width: 640px) {
  .artisanal-terroir-seal {
    display: block;
  }
}

.artisanal-terroir-seal__ring {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  border: 1.5px solid color-mix(in srgb, var(--mangthit-600) 80%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--mangthit-600) 25%, transparent),
              inset 0 0 4px color-mix(in srgb, var(--mangthit-600) 20%, transparent);
}

.artisanal-terroir-seal__inner {
  font-family: var(--font-editorial-display);
  font-size: 8px;
  font-weight: var(--weight-bold);
  color: var(--mangthit-600);
  line-height: 1.15;
  text-align: center;
  letter-spacing: 0.08em;
}

.home-intent-anchors__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: var(--space-3);
}

.home-intent-anchor {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  min-height: 48px;
  padding: var(--space-2) var(--space-4) var(--space-2) var(--space-2);
  background: var(--color-surface);
  border: 1px solid var(--border-liquid-glass, var(--color-border));
  border-radius: var(--radius-pill, 999px);
  color: var(--color-text);
  text-decoration: none;
  box-shadow: 0 1px 3px rgba(var(--black-rgb), 0.04);
  transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1),
              border-color 0.2s ease,
              box-shadow 0.2s ease,
              background-color 0.2s ease;
}

.home-intent-anchor:hover,
.home-intent-anchor.is-selected {
  transform: translateY(-2px);
  border-color: color-mix(in srgb, var(--mangthit-600) 55%, var(--color-border));
  box-shadow: 0 6px 18px rgba(var(--black-rgb), 0.08);
  background: color-mix(in srgb, var(--color-surface) 97%, transparent);
}

.home-intent-anchor:active {
  transform: scale(0.98);
}

.home-intent-anchor:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 2px;
}

.home-intent-anchor__media {
  position: relative;
  width: 38px;
  height: 38px;
  flex-shrink: 0;
}

.home-intent-anchor__avatar {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  object-fit: cover;
  display: block;
  border: 1.5px solid var(--color-surface);
  box-shadow: 0 1px 3px rgba(var(--black-rgb), 0.12);
  transition: transform 0.25s var(--ease-out);
}

.home-intent-anchor:hover .home-intent-anchor__avatar {
  transform: scale(1.06);
}

.home-intent-anchor.is-selected .home-intent-anchor__avatar {
  transform: scale(1.06);
}

.home-intent-anchor__icon-badge {
  position: absolute;
  bottom: -2px;
  right: -2px;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  font-size: 10px;
  box-shadow: 0 1px 2px rgba(var(--black-rgb), 0.15);
}

.home-intent-anchor__icon-badge--orchard { color: var(--orchard-600); }
.home-intent-anchor__icon-badge--mangthit { color: var(--mangthit-600); }
.home-intent-anchor__icon-badge--clay { color: var(--clay-600); }
.home-intent-anchor__icon-badge--amber { color: var(--harvest-700); }
.home-intent-anchor__icon-badge--river { color: var(--river-600); }

.home-intent-anchor__content {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
  min-width: 0;
}

.home-intent-anchor__label {
  font-size: var(--text-sm);
  font-weight: var(--weight-bold);
  color: var(--color-text);
  line-height: 1.3;
}

.home-intent-anchor__hint {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  line-height: 1.35;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.home-intent-anchor__arrow {
  color: var(--color-text-muted);
  font-size: 1rem;
  flex-shrink: 0;
  transition: transform 0.2s ease, color 0.2s ease;
}

.home-intent-anchor:hover .home-intent-anchor__arrow,
.home-intent-anchor.is-selected .home-intent-anchor__arrow {
  transform: translateX(3px);
  color: var(--color-brand);
}

/* Curator's Fast Persona Capsule */
.home-persona-capsule {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-4);
  border-radius: var(--radius-surface, 20px);
  border: 1px solid color-mix(in srgb, var(--color-border) 80%, transparent);
  box-shadow: 0 8px 30px rgba(var(--black-rgb), 0.08);
  margin-top: var(--space-2);
  position: relative;
  overflow: hidden;
}

.home-persona-capsule__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding-bottom: var(--space-2);
  border-bottom: 1px dashed color-mix(in srgb, var(--color-border) 70%, transparent);
}

.home-persona-capsule__tag {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  font-size: 11px;
  font-weight: var(--weight-bold);
  letter-spacing: 0.08em;
  color: var(--mangthit-600);
}

.home-persona-capsule__all-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: var(--text-xs);
  font-weight: var(--weight-medium);
  color: var(--color-text-muted);
  text-decoration: none;
  transition: color 0.2s ease, transform 0.2s ease;
}

.home-persona-capsule__all-link:hover {
  color: var(--mangthit-600);
  transform: translateX(2px);
}

.home-persona-capsule__spots {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--space-3);
}

.home-persona-spot {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: var(--space-3);
  border-radius: var(--radius-control, 12px);
  background: color-mix(in srgb, var(--color-surface) 60%, transparent);
  border: 1px solid color-mix(in srgb, var(--color-border) 50%, transparent);
  color: var(--color-text);
  text-decoration: none;
  transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1),
              background 0.2s ease,
              border-color 0.2s ease,
              box-shadow 0.2s ease;
}

.home-persona-spot:hover {
  transform: translateY(-2px);
  background: var(--color-surface);
  border-color: color-mix(in srgb, var(--mangthit-600) 40%, transparent);
  box-shadow: 0 4px 14px rgba(var(--black-rgb), 0.06);
}

.home-persona-spot:active {
  transform: scale(0.98);
}

.home-persona-spot__meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  font-size: 11px;
}

.home-persona-spot__distance {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  color: var(--mangthit-600);
  font-weight: var(--weight-medium);
}

.home-persona-spot__duration {
  color: var(--color-text-muted);
  font-size: 10.5px;
}

.home-persona-spot__title {
  font-size: var(--text-sm);
  font-weight: var(--weight-bold);
  color: var(--color-text);
  line-height: 1.3;
}

.home-persona-spot__highlight {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  line-height: 1.4;
  margin: 0;
}

@media (prefers-reduced-motion: reduce) {
  .home-intent-anchor:hover .home-intent-anchor__avatar,
  .home-intent-anchor:hover .home-intent-anchor__arrow,
  .home-persona-spot {
    transform: none !important;
    transition: none !important;
  }
}
</style>
