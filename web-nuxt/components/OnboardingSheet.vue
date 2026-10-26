<template>
  <PersonalizeSetupSheet
    v-if="ff('onboarding') && ff('preference_ui_v1')"
    v-model="personalizeVisible"
    @complete="dismissPersonalize"
    @skip="dismissPersonalize"
  />
  <Teleport to="body">
    <Transition name="sheet">
      <div v-if="visible && ff('onboarding')" class="onboarding-overlay" @click.self="dismiss">
        <div class="onboarding-sheet" role="dialog" aria-modal="true" aria-label="Chào mừng đến vinhlong360" ref="sheetEl">
          <button type="button" class="sheet-close" aria-label="Đóng" @click="dismiss"><IconLine name="x" /></button>
          <div class="sheet-header">
            <span class="sheet-emoji-chip" aria-hidden="true"><IconLine :name="resolveOnboardingIcon(ob.emoji, 'leaf')" class="sheet-emoji" /></span>
            <h2 class="sheet-title">{{ ob.title }}</h2>
            <span class="sheet-rule" aria-hidden="true"></span>
            <p>{{ ob.intro }}</p>
          </div>
          <div class="sheet-features">
            <div class="sheet-feature" v-for="(f, i) in ob.features" :key="i">
              <span class="sf-icon" aria-hidden="true"><IconLine :name="resolveOnboardingIcon(f.icon, 'sparkle')" /></span>
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
import { onMounted, onUnmounted, ref, watch } from 'vue'
import PersonalizeSetupSheet from './PersonalizeSetupSheet.vue'
import { mergeOnboarding, resolveOnboardingIcon } from '~/utils/onboardingContent'
const { enabled: ff } = useFeature()
const { get: ss } = useSiteSettings()
const { isLoggedIn, user } = useAuth()
const preferences = usePersonalizationPreferences()
const visible = ref(false)
const personalizeVisible = ref(false)
const sheetEl = ref<HTMLElement | null>(null)

const ob = computed(() => mergeOnboarding(ss('onboarding', {})))

// Body-scroll lock, focus trap, Escape-to-close + focus restore (SSR-safe).
useModalA11y(visible, sheetEl, { onClose: dismiss })

const LS_ONBOARDING = 'vl360_onboarding_seen'

onMounted(() => {
  if (isLoggedIn.value) void maybePromptPersonalization()
  else scheduleWelcome()
})

watch(() => isLoggedIn.value, (authenticated) => {
  if (authenticated) void maybePromptPersonalization()
  else {
    personalizeVisible.value = false
    scheduleWelcome()
  }
})

let welcomeTimer: ReturnType<typeof setTimeout> | null = null

function scheduleWelcome() {
  if (welcomeTimer || localStorage.getItem(LS_ONBOARDING)) return
  welcomeTimer = setTimeout(() => { visible.value = true }, 5000)
}

async function maybePromptPersonalization() {
  if (!ff('onboarding') || !ff('preference_ui_v1')) return
  const owner = user.value?.id
  if (!isLoggedIn.value || !owner) return
  visible.value = false
  if (welcomeTimer) {
    clearTimeout(welcomeTimer)
    welcomeTimer = null
  }
  const refreshed = await preferences.refresh()
  if (!refreshed || !isLoggedIn.value || user.value?.id !== owner) return
  const snapshot = preferences.snapshot.value
  const hasExplicitPreference = snapshot.location_source === 'manual'
    || !!snapshot.region_id
    || snapshot.explicit_interests.length > 0
  personalizeVisible.value = snapshot.location_reconfirm_required || !hasExplicitPreference
}

function dismissPersonalize() {
  personalizeVisible.value = false
  if (import.meta.client) localStorage.setItem(LS_ONBOARDING, '1')
}

function dismiss() {
  visible.value = false
  if (import.meta.client) localStorage.setItem(LS_ONBOARDING, '1')
}

onUnmounted(() => {
  if (welcomeTimer) clearTimeout(welcomeTimer)
})
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
  width: 48px;
  height: 48px;
  margin: 0 auto var(--space-2h);
  border-radius: var(--radius-pill, 999px);
  background: var(--bg-warm);
}
.sheet-emoji {
  font-size: 1.45rem;
  display: block;
  margin-bottom: 0;
  line-height: 1;
}

/* Warm serif welcome title */
.sheet-title {
  font-family: var(--font-editorial);
  font-weight: 600;
  letter-spacing: -.005em;
  font-size: 1.25rem;
  line-height: var(--leading-snug);
  text-wrap: balance;
  overflow-wrap: break-word;
  margin-bottom: var(--space-1h);
}

/* Tri-province hairline under the title — the card-scale sediment tick, quiet */
.sheet-rule {
  display: block;
  width: 24px;
  height: 2px;
  border-radius: 2px;
  margin: 0 auto var(--space-2);
  background: linear-gradient(90deg, var(--color-material-river) 0%, var(--color-material-amber) 52%, var(--color-material-clay) 100%);
}
</style>
