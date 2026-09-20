<template>
  <span class="tufte-sidenote-wrapper">
    <!-- Inline Trigger for Mobile (< 1024px) & Inline Anchor -->
    <button
      :id="triggerId"
      type="button"
      class="tufte-sidenote-trigger"
      :aria-expanded="isMobileOpen"
      :aria-controls="noteElementId"
      :aria-label="ariaTriggerLabel"
      @click="toggleMobileSheet"
    >
      <span class="tufte-trigger__glyph" aria-hidden="true">§</span>
      <sup class="tufte-trigger__num">{{ noteNumber }}</sup>
    </button>

    <!-- Desktop Gutter Marginalia (>= 1024px) -->
    <aside
      :id="noteElementId"
      class="tufte-sidenote"
      :data-notebook-id="notebookId"
      :data-authority-tier="authorityTier"
      role="note"
      :aria-labelledby="triggerId"
    >
      <div class="tufte-sidenote__header">
        <span class="tufte-sidenote__symbol" aria-hidden="true">§{{ noteNumber }}</span>
        <span v-if="authorityTierLabel" class="tufte-sidenote__tier-badge">
          {{ authorityTierLabel }}
        </span>
      </div>

      <div class="tufte-sidenote__body">
        <slot>{{ content }}</slot>
      </div>

      <footer v-if="hasCitation" class="tufte-sidenote__footer">
        <cite class="tufte-sidenote__cite">
          <a
            v-if="sourceUrl"
            :href="sourceUrl"
            target="_blank"
            rel="noopener noreferrer"
            class="tufte-sidenote__link"
          >
            {{ sourceTitle || sourceUrl }}
          </a>
          <span v-else>{{ sourceTitle }}</span>
        </cite>
        <span v-if="legalReference" class="tufte-sidenote__legal">
          {{ legalReference }}
        </span>
        <div v-if="showSourceMark" class="tufte-sidenote__sourcemark">
          <SourceMark
            :tier="mappedSourceTier"
            :source-title="sourceTitle"
            :source-url="sourceUrl"
            :verified-at="verifiedAt"
            compact
          />
        </div>
      </footer>
    </aside>

    <!-- Mobile Bottom Sheet Drawer (< 1024px) -->
    <Teleport to="body">
      <Transition name="tufte-fade">
        <div
          v-if="isMobileOpen"
          class="tufte-backdrop"
          aria-hidden="true"
          @click="closeMobileSheet"
        />
      </Transition>

      <Transition name="tufte-slide">
        <div
          v-if="isMobileOpen"
          class="tufte-bottom-sheet"
          role="dialog"
          aria-modal="true"
          :aria-label="mobileDialogLabel"
        >
          <div class="tufte-sheet-handle-bar" aria-hidden="true">
            <span class="tufte-sheet-drag-pill" />
          </div>

          <div class="tufte-sheet-header">
            <div class="tufte-sheet-title-group">
              <span class="tufte-sheet-glyph" aria-hidden="true">§{{ noteNumber }}</span>
              <h3 class="tufte-sheet-title">Chú giải học thuật · Edward Tufte</h3>
            </div>
            <button
              type="button"
              class="tufte-sheet-close"
              aria-label="Đóng chú giải"
              @click="closeMobileSheet"
            >
              <IconLine name="x" aria-hidden="true" />
            </button>
          </div>

          <div class="tufte-sheet-content">
            <slot>{{ content }}</slot>
          </div>

          <div v-if="hasCitation" class="tufte-sheet-citation">
            <cite class="tufte-sheet-cite">
              <a
                v-if="sourceUrl"
                :href="sourceUrl"
                target="_blank"
                rel="noopener noreferrer"
                class="tufte-sidenote__link"
              >
                {{ sourceTitle || sourceUrl }}
              </a>
              <span v-else>{{ sourceTitle }}</span>
            </cite>
            <p v-if="legalReference" class="tufte-sheet-legal">{{ legalReference }}</p>
            <div v-if="showSourceMark" class="tufte-sheet-sourcemark">
              <SourceMark
                :tier="mappedSourceTier"
                :source-title="sourceTitle"
                :source-url="sourceUrl"
                :verified-at="verifiedAt"
              />
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </span>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import SourceMark from './SourceMark.vue'
import IconLine from './IconLine.vue'
import type { SourceTier } from '../utils/regionalColor'

export interface TufteSidenoteProps {
  id?: string
  number?: number | string
  content?: string
  sourceTitle?: string
  sourceUrl?: string
  notebookId?: 'v-nh-long-v-nh-long-b-n-tre-tr' | 'mekong-360-t-p-2' | 'ch-nh-s-ch-ph-p-lu-t-v-n-b-n-q' | string
  authorityTier?: 'TIER_1_GOVERNMENT' | 'TIER_2_ACADEMIC' | 'TIER_3_PRESS' | 'official' | 'verified' | 'community' | string
  legalReference?: string
  verifiedAt?: string
  showSourceMark?: boolean
}

const props = withDefaults(defineProps<TufteSidenoteProps>(), {
  id: undefined,
  number: 1,
  content: '',
  sourceTitle: '',
  sourceUrl: '',
  notebookId: '',
  authorityTier: '',
  legalReference: '',
  verifiedAt: '',
  showSourceMark: true,
})

const isMobileOpen = ref(false)

const noteNumber = computed(() => props.number)
const noteElementId = computed(() => props.id || `tufte-note-${props.number}`)
const triggerId = computed(() => `tufte-trigger-${props.number}`)

const ariaTriggerLabel = computed(() => {
  return `Xem chú giải lề số ${props.number}${props.sourceTitle ? `: ${props.sourceTitle}` : ''}`
})

const mobileDialogLabel = computed(() => {
  return `Chú giải lề học thuật số ${props.number}`
})

const authorityTierLabel = computed(() => {
  switch (props.authorityTier) {
    case 'TIER_1_GOVERNMENT':
    case 'official':
      return 'Thẩm quyền Nhà nước'
    case 'TIER_2_ACADEMIC':
    case 'verified':
      return 'Khảo cứu Viện/Đại học'
    case 'TIER_3_PRESS':
    case 'community':
      return 'Báo chí & Lưu trữ'
    default:
      return ''
  }
})

const mappedSourceTier = computed<SourceTier>(() => {
  if (props.authorityTier === 'TIER_1_GOVERNMENT' || props.authorityTier === 'official') return 'official'
  if (props.authorityTier === 'TIER_2_ACADEMIC' || props.authorityTier === 'verified') return 'verified'
  if (props.authorityTier === 'TIER_3_PRESS' || props.authorityTier === 'community') return 'community'
  return 'verified'
})

const hasCitation = computed(() => Boolean(props.sourceTitle || props.sourceUrl || props.legalReference))

function toggleMobileSheet() {
  isMobileOpen.value = !isMobileOpen.value
}

function closeMobileSheet() {
  isMobileOpen.value = false
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape' && isMobileOpen.value) {
    closeMobileSheet()
  }
}

onMounted(() => {
  if (typeof window !== 'undefined') {
    window.addEventListener('keydown', handleKeydown)
  }
})

onUnmounted(() => {
  if (typeof window !== 'undefined') {
    window.removeEventListener('keydown', handleKeydown)
  }
})
</script>

<style scoped>
.tufte-sidenote-wrapper {
  position: relative;
  display: inline;
}

/* ── Mobile Trigger Button (>= 44x44px target) ── */
.tufte-sidenote-trigger {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 44px;
  min-height: 44px;
  padding: var(--space-1) var(--space-2);
  margin: 0 var(--space-05, 2px);
  background: transparent;
  border: 1px solid transparent;
  border-radius: var(--radius-full, 9999px);
  color: var(--alluvial-gold);
  cursor: pointer;
  vertical-align: baseline;
  touch-action: manipulation;
  transition: background-color 0.2s ease, border-color 0.2s ease, transform 0.15s ease;
}

.tufte-sidenote-trigger:hover {
  background: color-mix(in srgb, var(--alluvial-gold) 10%, transparent);
}

.tufte-sidenote-trigger:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 2px;
}

.tufte-trigger__glyph {
  font-family: var(--font-sans, 'Be Vietnam Pro', sans-serif);
  font-weight: var(--weight-bold, 700);
  font-size: var(--text-sm, 0.875rem);
  line-height: 1;
}

.tufte-trigger__num {
  font-size: var(--text-2xs, 0.6875rem);
  font-weight: var(--weight-bold, 700);
  margin-left: 1px;
}

/* ── Desktop Gutter Marginalia (>= 1024px) ── */
.tufte-sidenote {
  display: none;
}

@media (min-width: 1024px) {
  .tufte-sidenote {
    display: block;
    position: absolute;
    left: calc(100% + var(--space-4, 24px));
    top: 0;
    width: 220px;
    padding: 12px 16px;
    border: 1px solid color-mix(in srgb, var(--color-material-amber) 22%, var(--color-border));
    border-radius: var(--radius-control);
    background: color-mix(in srgb, var(--color-material-amber) 4%, var(--color-surface));
    font-family: var(--font-editorial);
    font-style: italic;
    font-size: 13px;
    line-height: 1.6;
    font-weight: 400;
    color: var(--color-text);
    box-shadow: var(--shadow-xs);
    z-index: var(--z-rel);
  }

  /* When viewport has wide gutter, inline trigger is discrete superscript */
  .tufte-sidenote-trigger {
    min-width: auto;
    min-height: auto;
    padding: 0 2px;
    border-radius: var(--radius-control);
    cursor: default;
  }
}

.tufte-sidenote__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  margin-bottom: var(--space-1h);
  font-style: normal;
}

.tufte-sidenote__symbol {
  font-family: var(--font-sans);
  font-weight: var(--weight-bold);
  font-size: var(--text-xs);
  color: var(--alluvial-gold);
}

.tufte-sidenote__tier-badge {
  font-family: var(--font-sans);
  font-size: var(--text-2xs);
  font-weight: var(--weight-medium);
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.tufte-sidenote__body {
  margin-bottom: var(--space-2);
  word-break: break-word;
}

.tufte-sidenote__footer {
  font-style: normal;
  font-family: var(--font-sans);
  font-size: 11px;
  color: var(--color-text-muted);
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.tufte-sidenote__cite {
  font-style: normal;
}

.tufte-sidenote__link {
  color: var(--color-action);
  text-decoration: underline;
  text-underline-offset: 2px;
}

.tufte-sidenote__legal {
  font-size: 10px;
  opacity: 0.85;
}

.tufte-sidenote__sourcemark {
  margin-top: var(--space-1);
}

/* ── Mobile Bottom Sheet Modal (< 1024px) ── */
.tufte-backdrop {
  position: fixed;
  inset: 0;
  background: color-mix(in srgb, var(--night-canvas) 60%, transparent);
  backdrop-filter: blur(16px);
  z-index: var(--z-overlay);
}

.tufte-bottom-sheet {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  width: 100%;
  max-width: 480px;
  margin-inline: auto;
  max-height: 80vh;
  overflow-y: auto;
  padding: var(--space-4) var(--space-5) calc(var(--space-6) + env(safe-area-inset-bottom, 0px));
  background: var(--color-surface);
  border-top-left-radius: var(--radius-sheet);
  border-top-right-radius: var(--radius-sheet);
  border: 1px solid var(--border-liquid-glass);
  border-bottom: none;
  box-shadow: var(--shadow-xl);
  z-index: var(--z-modal);
}

.tufte-sheet-handle-bar {
  display: flex;
  justify-content: center;
  padding-bottom: var(--space-3, 12px);
}

.tufte-sheet-drag-pill {
  width: 40px;
  height: 4px;
  border-radius: var(--radius-full, 9999px);
  background: var(--color-border);
}

.tufte-sheet-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-3, 12px);
}

.tufte-sheet-title-group {
  display: flex;
  align-items: center;
  gap: var(--space-2, 8px);
}

.tufte-sheet-glyph {
  font-family: var(--font-sans, 'Be Vietnam Pro', sans-serif);
  font-weight: var(--weight-bold, 700);
  font-size: var(--text-base, 1rem);
  color: var(--alluvial-gold);
}

.tufte-sheet-title {
  font-family: var(--font-editorial, 'Lora', serif);
  font-size: var(--text-base, 1rem);
  font-weight: var(--weight-semibold, 600);
  color: var(--color-text);
  margin: 0;
}

.tufte-sheet-close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 44px;
  min-height: 44px;
  background: transparent;
  border: none;
  border-radius: var(--radius-full, 9999px);
  color: var(--color-text-muted);
  font-size: var(--text-lg, 1.125rem);
  cursor: pointer;
  touch-action: manipulation;
}

.tufte-sheet-close:hover {
  background: color-mix(in srgb, var(--color-text) 8%, transparent);
}

.tufte-sheet-content {
  font-family: var(--font-editorial, 'Lora', serif);
  font-style: italic;
  font-size: var(--text-sm, 0.875rem);
  line-height: var(--leading-relaxed, 1.625);
  color: var(--color-text);
  margin-bottom: var(--space-4, 16px);
}

.tufte-sheet-citation {
  font-family: var(--font-sans, 'Be Vietnam Pro', sans-serif);
  font-size: var(--text-xs, 0.75rem);
  color: var(--color-text-muted);
  border-top: 1px solid var(--color-border);
  padding-top: var(--space-3, 12px);
  display: flex;
  flex-direction: column;
  gap: var(--space-2, 8px);
}

.tufte-sheet-cite {
  font-style: normal;
}

.tufte-sheet-legal {
  margin: 0;
  font-size: var(--text-2xs, 0.6875rem);
  opacity: 0.85;
}

/* ── Vue Transitions ── */
.tufte-fade-enter-active,
.tufte-fade-leave-active {
  transition: opacity 0.25s ease;
}

.tufte-fade-enter-from,
.tufte-fade-leave-to {
  opacity: 0;
}

.tufte-slide-enter-active,
.tufte-slide-leave-active {
  transition: transform 0.3s var(--ease-terroir-flow, cubic-bezier(0.22, 1, 0.36, 1));
}

.tufte-slide-enter-from,
.tufte-slide-leave-to {
  transform: translateY(100%);
}
</style>
