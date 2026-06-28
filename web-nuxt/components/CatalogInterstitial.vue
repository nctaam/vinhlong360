<template>
  <aside v-if="fact" class="interstitial" :class="variant" role="complementary" :aria-label="ariaLabel">
    <span class="interstitial-icon" aria-hidden="true">{{ icon }}</span>
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
const props = withDefaults(defineProps<{
  fact: string
  icon?: string
  links?: { to: string; label: string }[]
  variant?: 'default' | 'warm' | 'accent'
  ariaLabel?: string
}>(), {
  icon: '💡',
  links: () => [],
  variant: 'default',
  ariaLabel: 'Thông tin thú vị',
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
  background: linear-gradient(135deg, rgba(var(--primary-rgb), .04), transparent);
  margin: var(--space-4) 0;
}
.interstitial.warm {
  background: linear-gradient(135deg, rgba(var(--secondary-rgb), .06), rgba(var(--accent-rgb), .03));
  border-color: rgba(var(--secondary-rgb), .15);
}
.interstitial.accent {
  background: linear-gradient(135deg, rgba(var(--accent-rgb), .06), transparent);
  border-color: rgba(var(--accent-rgb), .15);
}
.interstitial-icon {
  font-size: 1.8rem;
  line-height: 1;
  flex-shrink: 0;
}
.interstitial-body {
  min-width: 0;
}
.interstitial-text {
  margin: 0;
  font-size: var(--text-sm);
  line-height: var(--leading-relaxed);
  color: var(--ink-secondary, var(--muted));
  font-weight: var(--weight-medium);
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
  color: var(--primary-fg);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  background: rgba(var(--primary-rgb), .06);
  transition: background .2s var(--ease-out), transform .2s var(--ease-out);
  min-height: 44px;
}
.interstitial-link:hover {
  background: rgba(var(--primary-rgb), .12);
  transform: translateX(2px);
}
.interstitial-link:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}

.dark .interstitial {
  background: linear-gradient(135deg, rgba(var(--primary-rgb), .06), transparent);
  border-color: rgba(255, 255, 255, .08);
}
.dark .interstitial.warm {
  background: linear-gradient(135deg, rgba(var(--secondary-rgb), .08), rgba(var(--accent-rgb), .04));
  border-color: rgba(var(--secondary-rgb), .18);
}
.dark .interstitial.accent {
  background: linear-gradient(135deg, rgba(var(--accent-rgb), .08), transparent);
  border-color: rgba(var(--accent-rgb), .18);
}
.dark .interstitial-link {
  background: rgba(var(--primary-rgb), .1);
}
.dark .interstitial-link:hover {
  background: rgba(var(--primary-rgb), .18);
}

@media (max-width: 640px) {
  .interstitial {
    padding: var(--space-4);
    gap: var(--space-3);
  }
  .interstitial-icon {
    font-size: 1.5rem;
  }
}

@media (prefers-reduced-motion: reduce) {
  .interstitial-link:hover {
    transform: none;
  }
}
</style>
