<template>
  <nav class="home-intent-anchors" aria-label="Bộ phím tắt khám phá nhanh theo nhu cầu lữ khách">
    <div class="home-intent-anchors__inner">
      <div class="home-intent-anchors__header">
        <span class="home-intent-anchors__eyebrow">
          <IconLine name="compass" />
          <span>Lối rẽ lữ hành</span>
        </span>
        <h2 class="home-intent-anchors__title">Nhu Cầu Khám Phá Nhanh</h2>
      </div>

      <div class="home-intent-anchors__grid" role="list">
        <NuxtLink
          v-for="anchor in INTENT_ANCHORS"
          :key="anchor.key"
          :to="anchor.to"
          class="home-intent-anchor"
          :data-intent="anchor.key"
          data-intent-anchor
          role="listitem"
        >
          <span class="home-intent-anchor__icon" :class="`home-intent-anchor__icon--${anchor.accent}`" aria-hidden="true">
            <IconLine :name="anchor.icon" />
          </span>
          <span class="home-intent-anchor__content">
            <strong class="home-intent-anchor__label">{{ anchor.label }}</strong>
            <span class="home-intent-anchor__hint">{{ anchor.hint }}</span>
          </span>
          <IconLine name="arrow-right" class="home-intent-anchor__arrow" aria-hidden="true" />
        </NuxtLink>
      </div>
    </div>
  </nav>
</template>

<script setup lang="ts">
import IconLine from '~/components/IconLine.vue'

interface IntentAnchor {
  readonly key: string
  readonly label: string
  readonly hint: string
  readonly to: string
  readonly icon: string
  readonly accent: 'orchard' | 'mangthit' | 'river' | 'amber' | 'clay'
}

const INTENT_ANCHORS: readonly IntentAnchor[] = [
  {
    key: 'eco-orchard',
    label: 'Du lịch Sinh thái Miệt vườn',
    hint: 'Vườn chôm chôm, sầu riêng Ri6 trĩu quả cù lao An Bình',
    to: '/tim-kiem?q=sinh+th%C3%A1i+mi%E1%BB%87t+v%C6%B0%E1%BB%9Dn',
    icon: 'sprout',
    accent: 'orchard',
  },
  {
    key: 'heritage-craft',
    label: 'Ký sự Làng nghề Truyền thống',
    hint: 'Lò gạch gốm đỏ Mang Thít & làng dệt chiếu, đan lát',
    to: '/tim-kiem?q=l%C3%A0ng+ngh%E1%BB%81+g%E1%BB%91m',
    icon: 'vase',
    accent: 'mangthit',
  },
  {
    key: 'spiritual-culture',
    label: 'Hành trình Tâm linh Di sản',
    hint: 'Chùa Khmer Hạnh Phúc Tăng (Phù Ly), Văn Thánh Miếu',
    to: '/tim-kiem?q=t%C3%A2m+linh+di+s%E1%BA%A3n',
    icon: 'landmark',
    accent: 'clay',
  },
  {
    key: 'culinary-market',
    label: 'Ẩm thực & Chợ nổi',
    hint: 'Cá tai tượng chiên xù, bánh xèo hến & Chợ nổi Trà Ôn',
    to: '/kham-pha/am-thuc',
    icon: 'bowl',
    accent: 'amber',
  },
  {
    key: 'riverside-homestay',
    label: 'Nghỉ dưỡng Homestay Ven sông',
    hint: 'Homestay Út Trinh, Mekong Riverside & đờn ca tài tử',
    to: '/luu-tru',
    icon: 'home',
    accent: 'river',
  },
]
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
  gap: var(--space-1);
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
  padding: var(--space-3) var(--space-4);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-surface);
  color: var(--color-text);
  text-decoration: none;
  box-shadow: 0 1px 3px rgba(var(--black-rgb), 0.04);
  transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1),
              border-color 0.2s ease,
              box-shadow 0.2s ease,
              background-color 0.2s ease;
}

.home-intent-anchor:hover {
  transform: translateY(-2px);
  border-color: color-mix(in srgb, var(--mangthit-600) 45%, var(--color-border));
  box-shadow: 0 6px 16px rgba(var(--black-rgb), 0.08);
}

.home-intent-anchor:active {
  transform: scale(0.98);
}

.home-intent-anchor:focus-visible {
  outline: 3px solid var(--color-action);
  outline-offset: 2px;
}

.home-intent-anchor__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  flex-shrink: 0;
  border-radius: var(--radius-control);
  background: var(--color-canvas);
  color: var(--color-text);
  font-size: 1.2rem;
  transition: background-color 0.2s ease, color 0.2s ease;
}

.home-intent-anchor__icon--orchard {
  color: var(--orchard-600);
  background: color-mix(in srgb, var(--orchard-600) 12%, transparent);
}

.home-intent-anchor__icon--mangthit {
  color: var(--mangthit-600);
  background: color-mix(in srgb, var(--mangthit-600) 12%, transparent);
}

.home-intent-anchor__icon--clay {
  color: var(--clay-600);
  background: color-mix(in srgb, var(--clay-600) 12%, transparent);
}

.home-intent-anchor__icon--amber {
  color: var(--harvest-700);
  background: color-mix(in srgb, var(--harvest-700) 12%, transparent);
}

.home-intent-anchor__icon--river {
  color: var(--river-600);
  background: color-mix(in srgb, var(--river-600) 12%, transparent);
}

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

.home-intent-anchor:hover .home-intent-anchor__arrow {
  transform: translateX(3px);
  color: var(--color-brand);
}
</style>
