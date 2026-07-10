<template>
  <aside v-if="fact" class="interstitial reveal" :class="variant" role="complementary" :aria-label="ariaLabel">
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
  position: relative;
  overflow: hidden;
}
/* tri-province hairline along the top edge — same "one ruled thread" idiom as the card
   rule and sediment-head tick, so the mid-list interruption still reads as part of the
   same publication rather than a bare highlight box */
.interstitial::before {
  content: ""; position: absolute; top: 0; left: 0; right: 0; height: 2px;
  background: linear-gradient(90deg, var(--river-600) 0%, var(--amber-600) 52%, var(--clay-600) 100%);
  opacity: .7;
}
.dark .interstitial::before {
  background: linear-gradient(90deg, #74ABB5 0%, var(--amber-500) 52%, var(--clay-400) 100%);
}
.interstitial.warm {
  background: linear-gradient(135deg, rgba(var(--secondary-rgb), .06), rgba(var(--accent-rgb), .03));
  border-color: rgba(var(--secondary-rgb), .15);
}
.interstitial.accent {
  background: linear-gradient(135deg, rgba(var(--accent-rgb), .06), transparent);
  border-color: rgba(var(--accent-rgb), .15);
}
/* icon sits in its own quiet chip rather than bare beside the text — keeps the emoji from
   reading as a slapped-on heading-marker next to the now-serif fact copy */
.interstitial-icon-chip {
  display: flex; align-items: center; justify-content: center;
  width: 40px; height: 40px; border-radius: var(--radius-full); flex-shrink: 0;
  background: rgba(var(--primary-rgb), .07);
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
  border-color: rgba(var(--white-rgb), .08);
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
