<template>
  <aside
    v-if="fact"
    class="interstitial catalog-interstitial reveal"
    :class="variant"
    :data-material-accent="materialAccent"
    role="complementary"
    :aria-label="ariaLabel"
  >
    <span class="catalog-interstitial-rule" aria-hidden="true"></span>
    <span class="interstitial-icon-chip" aria-hidden="true"><span class="interstitial-icon">{{ icon }}</span></span>
    <div class="interstitial-body">
      <p class="interstitial-text">{{ fact }}</p>
      <div v-if="links.length" class="interstitial-links">
        <NuxtLink v-for="l in links" :key="l.to" :to="l.to" class="interstitial-link">
          {{ l.label }} <span aria-hidden="true">→</span>
        </NuxtLink>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import type { RegionalAccent } from '~/utils/regionalColor'

const props = withDefaults(defineProps<{
  fact: string
  icon?: string
  links?: { to: string; label: string }[]
  variant?: 'default' | 'warm' | 'accent'
  ariaLabel?: string
  materialAccent?: RegionalAccent
}>(), {
  icon: '💡',
  links: () => [],
  variant: 'default',
  ariaLabel: 'Thông tin thú vị',
  materialAccent: 'neutral',
})
</script>

<style scoped>
.interstitial {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: var(--space-4);
  align-items: center;
  padding: var(--space-5) var(--space-6);
  border-radius: var(--radius-xl);
  border: .5px solid var(--line);
  background: linear-gradient(135deg, color-mix(in srgb, var(--tri-region-material-accent, var(--color-material-neutral)) 8%, transparent), transparent);
  margin: var(--space-4) 0;
  position: relative;
  overflow: hidden;
}
/* One ruled thread carries the explicit material accent through the interruption. */
.catalog-interstitial-rule {
  position: absolute; top: 0; left: 0; right: 0; height: 2px;
  background: var(--tri-region-material-accent, var(--color-material-neutral));
  opacity: .7;
}
.interstitial.warm {
  background: linear-gradient(135deg, color-mix(in srgb, var(--tri-region-material-accent, var(--color-material-neutral)) 12%, transparent), transparent);
  border-color: color-mix(in srgb, var(--tri-region-material-accent, var(--color-material-neutral)) 30%, transparent);
}
.interstitial.accent {
  background: linear-gradient(135deg, color-mix(in srgb, var(--tri-region-material-accent, var(--color-material-neutral)) 10%, transparent), transparent);
  border-color: color-mix(in srgb, var(--tri-region-material-accent, var(--color-material-neutral)) 30%, transparent);
}
/* icon sits in its own quiet chip rather than bare beside the text — keeps the emoji from
   reading as a slapped-on heading-marker next to the now-serif fact copy */
.interstitial-icon-chip {
  display: flex; align-items: center; justify-content: center;
  width: 40px; height: 40px; border-radius: var(--radius-full); flex-shrink: 0;
  background: color-mix(in srgb, var(--tri-region-material-accent, var(--color-material-neutral)) 12%, transparent);
}
.dark .interstitial-icon-chip { background: rgba(var(--white-rgb), .06); }
.interstitial-icon {
  font-size: 1.15rem;
  line-height: 1;
}
.interstitial-body {
  min-width: 0;
}
.interstitial-text {
  margin: 0;
  font-family: var(--font-editorial);
  font-size: var(--text-base);
  line-height: var(--leading-relaxed);
  color: var(--ink-secondary, var(--muted));
  font-weight: 500;
  letter-spacing: -.005em;
}
.interstitial-links {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  margin-top: var(--space-3);
}
.interstitial-link {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  color: var(--color-action);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  background: var(--color-action-surface);
  transition: background .2s var(--ease-out), transform .2s var(--ease-out);
  min-height: 44px;
}
.interstitial-link:hover {
  background: var(--color-action-surface-hover);
  transform: translateX(2px);
}
.interstitial-link:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 2px;
}

.dark .interstitial { border-color: var(--color-border); }

@media (max-width: 640px) {
  .interstitial {
    padding: var(--space-4);
    gap: var(--space-3);
  }
  .interstitial-icon-chip {
    width: 34px;
    height: 34px;
  }
  .interstitial-icon {
    font-size: 1rem;
  }
}

@media (prefers-reduced-motion: reduce) {
  .interstitial-link:hover {
    transform: none;
  }
}
</style>
