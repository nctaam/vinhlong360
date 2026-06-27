<script setup lang="ts">
const props = defineProps<{
  entity: Record<string, any>
}>()

const phone = computed(() => props.entity.attributes?.phone || '')
const zalo = computed(() => props.entity.attributes?.zalo || '')
const website = computed(() => props.entity.attributes?.website || '')
const hours = computed(() => props.entity.attributes?.hours || '')
const placeName = computed(() => props.entity.place_name || props.entity.placeName || '')

const rating = computed(() => {
  const r = parseFloat(props.entity.attributes?.rating)
  return r > 0 ? r : null
})
const reviewCount = computed(() => parseInt(props.entity.attributes?.review_count) || 0)
const stars = computed(() => {
  if (!rating.value) return ''
  const full = Math.floor(rating.value)
  const half = rating.value - full >= 0.5 ? '½' : ''
  return '★'.repeat(full) + half
})

const hasContact = computed(() => !!phone.value || !!zalo.value)
const mapUrl = computed(() => `/ban-do?highlight=${encodeURIComponent(props.entity.id)}`)
</script>

<template>
  <aside class="cw" aria-label="Liên hệ">
    <div class="cw-inner">
      <!-- Rating -->
      <div v-if="rating" class="cw-rating">
        <span class="cw-stars" aria-hidden="true">{{ stars }}</span>
        <span class="cw-score">{{ rating.toFixed(1) }}</span>
        <span class="cw-count">({{ reviewCount }} đánh giá)</span>
      </div>

      <!-- Location -->
      <div v-if="placeName" class="cw-row">
        <span class="cw-icon" aria-hidden="true">📍</span>
        <span class="cw-text">{{ placeName }}</span>
      </div>

      <!-- Hours -->
      <div v-if="hours" class="cw-row">
        <span class="cw-icon" aria-hidden="true">🕒</span>
        <span class="cw-text">{{ hours }}</span>
      </div>

      <hr v-if="hasContact" class="cw-divider" />

      <!-- CTA buttons -->
      <div class="cw-ctas">
        <a v-if="zalo" :href="`https://zalo.me/${zalo}`" target="_blank" rel="noopener" class="cw-btn cw-btn-primary" :aria-label="`Nhắn Zalo cho ${entity.name}`">
          💬 Nhắn Zalo
        </a>
        <a v-if="phone" :href="`tel:${phone}`" class="cw-btn cw-btn-secondary" :aria-label="`Gọi điện cho ${entity.name}`">
          📞 Gọi điện
        </a>
        <NuxtLink v-if="!hasContact" :to="mapUrl" class="cw-btn cw-btn-secondary">
          📍 Xem bản đồ
        </NuxtLink>
      </div>

      <!-- Website -->
      <a v-if="website" :href="website" target="_blank" rel="noopener" class="cw-website">
        🌐 {{ website.replace(/^https?:\/\//, '').replace(/\/$/, '') }}
      </a>
    </div>
  </aside>
</template>

<style scoped>
/* Desktop: sticky sidebar */
.cw {
  position: sticky;
  top: calc(var(--header-height, 60px) + var(--space-4));
  width: var(--contact-widget-width);
  background: var(--card);
  border-radius: var(--radius-xl, 16px);
  border: 1px solid var(--line);
  box-shadow: var(--shadow-md);
  padding: var(--space-5);
}

.cw-inner {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

/* Rating */
.cw-rating {
  display: flex;
  align-items: baseline;
  gap: var(--space-1h);
}
.cw-stars { color: var(--accent); font-size: var(--text-lg); letter-spacing: -1px; }
.cw-score { font-size: var(--text-lg); font-weight: var(--weight-bold, 700); color: var(--ink); }
.cw-count { font-size: var(--text-sm); color: var(--muted); }

/* Info rows */
.cw-row {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  font-size: var(--text-sm);
  color: var(--ink);
}
.cw-icon { flex-shrink: 0; font-size: 1em; }
.cw-text { line-height: 1.5; }

/* Divider */
.cw-divider {
  border: none;
  border-top: var(--detail-divider);
  margin: var(--space-1) 0;
}

/* CTA buttons */
.cw-ctas {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.cw-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  height: var(--contact-cta-height);
  border-radius: var(--contact-cta-radius);
  font-size: var(--text-base);
  font-weight: var(--weight-semibold, 600);
  text-decoration: none;
  cursor: pointer;
  transition: background 200ms, transform 200ms, box-shadow 200ms;
  border: none;
  min-height: 44px;
}
.cw-btn:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}
.cw-btn:active { transform: scale(0.97); }

.cw-btn-primary {
  background: var(--primary);
  color: var(--text-on-dark, #fff);
}
.cw-btn-primary:hover {
  background: var(--primary-dark, var(--primary));
  box-shadow: var(--shadow-sm);
}

.cw-btn-secondary {
  background: rgba(var(--primary-rgb), 0.08);
  color: var(--primary);
  border: 1px solid rgba(var(--primary-rgb), 0.2);
}
.cw-btn-secondary:hover {
  background: rgba(var(--primary-rgb), 0.14);
}

/* Website link */
.cw-website {
  display: block;
  text-align: center;
  font-size: var(--text-xs);
  color: var(--muted);
  text-decoration: none;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.cw-website:hover { color: var(--primary); text-decoration: underline; }

/* Mobile: fixed bottom bar */
@media (max-width: 767px) {
  .cw {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    top: auto;
    width: 100%;
    border-radius: var(--radius-xl, 16px) var(--radius-xl, 16px) 0 0;
    box-shadow: var(--shadow-lg);
    padding: var(--space-3) var(--space-4) calc(var(--space-3) + env(safe-area-inset-bottom, 0px));
    z-index: var(--z-sticky);
    border-bottom: none;
  }

  .cw-rating,
  .cw-row,
  .cw-divider,
  .cw-website { display: none; }

  .cw-ctas {
    flex-direction: row;
  }
  .cw-btn {
    flex: 1;
    height: 48px;
    font-size: var(--text-sm);
  }
}
</style>
