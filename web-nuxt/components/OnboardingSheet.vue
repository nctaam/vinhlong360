<template>
  <Teleport to="body">
    <Transition name="sheet">
      <div v-if="visible && ff('onboarding')" class="onboarding-overlay" @click.self="dismiss">
        <div class="onboarding-sheet" role="dialog" aria-modal="true" aria-label="Chào mừng đến vinhlong360" ref="sheetEl">
          <button type="button" class="sheet-close" aria-label="Đóng" @click="dismiss">&times;</button>
          <div class="sheet-header">
            <span class="sheet-emoji-chip" aria-hidden="true"><span class="sheet-emoji">{{ ob.emoji }}</span></span>
            <h2 class="sheet-title">{{ ob.title }}</h2>
            <span class="sheet-rule" aria-hidden="true"></span>
            <p>{{ ob.intro }}</p>
          </div>
          <div class="sheet-features">
            <div class="sheet-feature" v-for="(f, i) in ob.features" :key="i">
              <span class="sf-icon" aria-hidden="true">{{ f.icon }}</span>
              <div>
                <strong>{{ f.title }}</strong>
                <p>{{ f.desc }}</p>
              </div>
            </div>
          </div>
          <div class="sheet-actions">
            <NuxtLink :to="ob.cta_primary_to" class="btn btn-primary" @click="dismiss">{{ ob.cta_primary_label }}</NuxtLink>
            <button type="button" class="btn btn-ghost" @click="dismiss">{{ ob.cta_secondary_label }}</button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { mergeOnboarding } from '~/utils/onboardingContent'
const { enabled: ff } = useFeature()
const { get: ss } = useSiteSettings()
const visible = ref(false)
const sheetEl = ref<HTMLElement | null>(null)

const ob = computed(() => mergeOnboarding(ss('onboarding', {})))

// Body-scroll lock, focus trap, Escape-to-close + focus restore (SSR-safe).
useModalA11y(visible, sheetEl, { onClose: dismiss })

const LS_ONBOARDING = 'vl360_onboarding_seen'
onMounted(() => {
  if (!localStorage.getItem(LS_ONBOARDING)) {
    setTimeout(() => { visible.value = true }, 5000)
  }
})

function dismiss() {
  visible.value = false
  localStorage.setItem(LS_ONBOARDING, '1')
}
</script>

<style scoped>
/* Editorial reskin layered on top of the shared .onboarding-* rules in
   assets/css/components.css (untouched — this component is their sole consumer,
   so scoped rules here safely take precedence for this instance only).
   Warm serif welcome + emoji-in-chip per the narrative system voice guide. */

/* Emoji-in-chip, not bare — quiet phù-sa-tinted disc instead of a floating glyph */
.sheet-emoji-chip {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 64px;
  margin: 0 auto var(--space-3);
  border-radius: var(--radius-full, 999px);
  background: var(--bg-warm);
}
.sheet-emoji {
  font-size: 1.8rem;
  display: block;
  margin-bottom: 0;
  line-height: 1;
}
.dark .sheet-emoji-chip { background: rgba(var(--white-rgb), 0.06); }

/* Warm serif welcome title */
.sheet-title {
  font-family: var(--font-editorial);
  font-weight: 600;
  letter-spacing: -.005em;
}

/* Tri-province hairline under the title — the card-scale sediment tick, quiet */
.sheet-rule {
  display: block;
  width: 30px;
  height: 2px;
  border-radius: 2px;
  margin: 0 auto var(--space-3);
  background: linear-gradient(90deg, var(--river-600) 0%, var(--amber-600) 52%, var(--clay-600) 100%);
}
.dark .sheet-rule { background: linear-gradient(90deg, #74ABB5 0%, var(--amber-500) 52%, var(--clay-400) 100%); }
</style>
