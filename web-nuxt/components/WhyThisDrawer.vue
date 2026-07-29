<template>
  <Teleport to="body">
    <Transition name="disclosure-drawer">
      <div v-if="open" class="disclosure-overlay" @click.self="emit('close')">
        <aside
          ref="drawerEl"
          class="disclosure-drawer why-this-drawer"
          role="dialog"
          aria-modal="true"
          aria-labelledby="why-this-title"
          data-why-this
        >
          <button type="button" class="disclosure-close" aria-label="Đóng giải thích" @click="emit('close')">
            <IconLine name="x" aria-hidden="true" />
          </button>

          <header class="disclosure-header">
            <span class="disclosure-kicker"><IconLine name="sparkles" aria-hidden="true" /> Gợi ý có giải thích</span>
            <h2 id="why-this-title">Vì sao bạn thấy nội dung này?</h2>
            <p>Chúng tôi chỉ hiển thị những tín hiệu khái quát dùng để sắp xếp gợi ý.</p>
          </header>

          <div class="why-signal-stack" aria-label="Các lý do khái quát">
            <div v-for="(reason, index) in broadReasons" :key="reason" class="why-signal" :class="{ primary: index === 0 }">
              <span class="why-signal-icon" aria-hidden="true"><IconLine :name="index === 0 ? 'compass' : 'list'" /></span>
              <span>{{ reason }}</span>
            </div>
            <div v-if="regionLabel" class="why-signal">
              <span class="why-signal-icon" aria-hidden="true"><IconLine name="pin" /></span>
              <span>Khu vực đã chọn: <strong>{{ regionLabel }}</strong></span>
            </div>
            <div v-if="interestLabels.length" class="why-signal">
              <span class="why-signal-icon" aria-hidden="true"><IconLine name="sliders" /></span>
              <span>Sở thích đã chọn: <strong>{{ interestLabels.join(', ') }}</strong></span>
            </div>
          </div>

          <p class="disclosure-privacy"><IconLine name="shield-check" aria-hidden="true" /> Không hiển thị điểm số, tuổi chính xác, truy vấn tìm kiếm, GPS, IP hoặc dữ liệu kỹ thuật.</p>

          <div class="why-secondary-actions" aria-label="Điều khiển đề xuất">
            <button type="button" data-action="reset" @click="emit('reset')">Làm mới đề xuất</button>
            <button type="button" data-action="disable-personalization" @click="emit('disable-personalization')">Tắt cá nhân hóa</button>
          </div>

          <div class="disclosure-primary-wrap">
            <NuxtLink class="disclosure-primary" :to="preferenceHref" data-action="open-preferences" @click="emit('open-preferences')">
              Mở thiết lập khu vực & đề xuất
              <IconLine name="sliders" aria-hidden="true" />
            </NuxtLink>
          </div>
        </aside>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { RecommendationExplanation } from '~/types/api'
import { projectRecommendationExplanation } from '~/utils/recommendationExplanation'
import IconLine from './IconLine.vue'

const props = withDefaults(defineProps<{
  open?: boolean
  explanation?: Partial<RecommendationExplanation> | null
  preferenceHref?: string
}>(), {
  open: false,
  explanation: null,
  preferenceHref: '/cai-dat#khu-vuc-de-xuat',
})

const emit = defineEmits<{
  close: []
  reset: []
  'open-preferences': []
  'disable-personalization': []
}>()

const drawerEl = ref<HTMLElement | null>(null)
const openState = computed(() => props.open)
const safeExplanation = computed(() => projectRecommendationExplanation(props.explanation))
const broadReasons = computed(() => safeExplanation.value.reasons)
const regionLabel = computed(() => safeExplanation.value.regionLabel)
const interestLabels = computed(() => safeExplanation.value.interestLabels)

useModalA11y(openState, drawerEl, { onClose: () => emit('close') })
</script>

<style scoped>
/* Stitch mapping: search 41df1bef12c443fe8247a62b3f50f419 informs the compact
   control density. Live Stitch retrieval is unavailable; existing Nuxt tokens govern. */
.disclosure-overlay {
  position: fixed;
  inset: 0;
  z-index: 1200;
  display: flex;
  justify-content: flex-end;
  background: rgba(var(--black-rgb), .38);
  backdrop-filter: blur(3px);
}
.disclosure-drawer {
  position: relative;
  display: flex;
  flex-direction: column;
  width: min(430px, calc(100vw - 24px));
  height: 100%;
  padding: var(--space-7) var(--space-6) var(--space-5);
  overflow-y: auto;
  border-left: 1px solid var(--line);
  color: var(--ink);
  background: var(--surface);
  box-shadow: -20px 0 48px rgba(var(--black-rgb), .16);
}
.disclosure-close {
  position: absolute;
  top: var(--space-4);
  right: var(--space-4);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border: 0;
  border-radius: var(--radius-full);
  color: var(--muted);
  background: var(--bg-warm);
  cursor: pointer;
}
.disclosure-close:hover { color: var(--ink); background: var(--bg-alt); }
.disclosure-close:focus-visible,
.why-secondary-actions button:focus-visible,
.disclosure-primary:focus-visible { outline: 2px solid var(--primary); outline-offset: 3px; }
.disclosure-header { padding-right: var(--space-7); }
.disclosure-kicker {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--primary-fg);
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  letter-spacing: var(--tracking-caps);
  text-transform: uppercase;
}
.disclosure-header h2 {
  margin: var(--space-3) 0 var(--space-2);
  font-family: var(--font-editorial);
  font-size: clamp(1.55rem, 3vw, 2rem);
  line-height: var(--leading-tight);
  letter-spacing: -.025em;
}
.disclosure-header p { margin: 0; color: var(--muted); font-size: var(--text-sm); line-height: var(--leading-relaxed); }
.why-signal-stack { display: grid; gap: var(--space-2); margin: var(--space-6) 0 var(--space-4); }
.why-signal {
  display: grid;
  grid-template-columns: 36px minmax(0, 1fr);
  align-items: center;
  gap: var(--space-3);
  min-height: 56px;
  padding: var(--space-3);
  border: .5px solid var(--line);
  border-radius: var(--radius-md);
  background: var(--bg-warm);
  font-size: var(--text-sm);
  line-height: var(--leading-snug);
}
.why-signal.primary { border-color: color-mix(in srgb, var(--primary-fg) 45%, var(--line)); background: color-mix(in srgb, var(--primary-fg) 8%, var(--bg-warm)); }
.why-signal-icon { display: inline-flex; align-items: center; justify-content: center; width: 36px; height: 36px; border-radius: var(--radius-sm); color: var(--primary-fg); background: var(--surface); }
.disclosure-privacy { display: flex; align-items: flex-start; gap: var(--space-2); margin: 0; color: var(--muted); font-size: var(--text-xs); line-height: var(--leading-relaxed); }
.disclosure-privacy .line-icon { margin-top: .15rem; color: var(--primary-fg); }
.why-secondary-actions { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-2); margin-top: var(--space-5); }
.why-secondary-actions button { min-height: 44px; padding: var(--space-2) var(--space-3); border: .5px solid var(--line); border-radius: var(--radius-sm); color: var(--ink-700); background: transparent; cursor: pointer; font: inherit; font-size: var(--text-xs); font-weight: var(--weight-semibold); }
.why-secondary-actions button:hover { border-color: var(--primary-fg); color: var(--primary-fg); background: var(--bg-warm); }
.disclosure-primary-wrap { position: sticky; bottom: calc(-1 * var(--space-5)); margin: auto calc(-1 * var(--space-6)) calc(-1 * var(--space-5)); padding: var(--space-4) var(--space-6) var(--space-5); border-top: .5px solid var(--line); background: var(--surface); }
.disclosure-primary { display: flex; align-items: center; justify-content: space-between; gap: var(--space-3); min-height: 48px; padding: 0 var(--space-4); border-radius: var(--radius-sm); color: var(--on-primary); background: var(--primary); font-size: var(--text-sm); font-weight: var(--weight-semibold); text-decoration: none; }
.disclosure-drawer-enter-active, .disclosure-drawer-leave-active { transition: opacity .2s var(--ease-out); }
.disclosure-drawer-enter-active .disclosure-drawer, .disclosure-drawer-leave-active .disclosure-drawer { transition: transform .25s var(--ease-out); }
.disclosure-drawer-enter-from, .disclosure-drawer-leave-to { opacity: 0; }
.disclosure-drawer-enter-from .disclosure-drawer, .disclosure-drawer-leave-to .disclosure-drawer { transform: translateX(24px); }
@media (max-width: 640px) {
  .disclosure-overlay { align-items: flex-end; }
  .disclosure-drawer { width: 100%; height: auto; max-height: min(88vh, 760px); padding: var(--space-6) var(--space-4) var(--space-4); border: 0; border-radius: var(--radius-lg) var(--radius-lg) 0 0; box-shadow: 0 -18px 44px rgba(var(--black-rgb), .2); }
  .why-secondary-actions { grid-template-columns: 1fr; }
  .disclosure-primary-wrap { bottom: calc(-1 * var(--space-4)); margin-right: calc(-1 * var(--space-4)); margin-bottom: calc(-1 * var(--space-4)); margin-left: calc(-1 * var(--space-4)); padding-right: var(--space-4); padding-bottom: calc(var(--space-4) + env(safe-area-inset-bottom)); padding-left: var(--space-4); }
  .disclosure-drawer-enter-from .disclosure-drawer, .disclosure-drawer-leave-to .disclosure-drawer { transform: translateY(24px); }
}
@media (prefers-reduced-motion: reduce) {
  .disclosure-drawer-enter-active, .disclosure-drawer-leave-active,
  .disclosure-drawer-enter-active .disclosure-drawer, .disclosure-drawer-leave-active .disclosure-drawer { transition: none; }
}
</style>
