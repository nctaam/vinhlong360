<template>
  <Teleport to="body">
    <Transition name="sheet">
      <div v-if="visible && ff('onboarding')" class="onboarding-overlay" @click.self="dismiss">
        <div class="onboarding-sheet" role="dialog" aria-modal="true" aria-label="Chào mừng đến vinhlong360" ref="sheetEl">
          <button type="button" class="sheet-close" aria-label="Đóng" @click="dismiss">&times;</button>
          <div class="sheet-header">
            <span class="sheet-emoji" aria-hidden="true">{{ ob.emoji }}</span>
            <h2>{{ ob.title }}</h2>
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

onMounted(() => {
  const key = 'vl360_onboarding_seen'
  if (!localStorage.getItem(key)) {
    setTimeout(() => { visible.value = true }, 1500)
  }
})

function dismiss() {
  visible.value = false
  localStorage.setItem('vl360_onboarding_seen', '1')
}
</script>
