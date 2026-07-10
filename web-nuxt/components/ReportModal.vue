<template>
  <Teleport to="body">
    <Transition name="rm-fade">
      <div v-if="modal.open" class="rm-overlay" @click.self="close">
        <div class="rm-sheet" role="dialog" aria-modal="true" aria-labelledby="rm-title" ref="sheetEl">
          <button type="button" class="rm-close" aria-label="Đóng" @click="close">&times;</button>
          <div class="rm-head">
            <h3 id="rm-title">Báo cáo nội dung</h3>
            <p class="rm-sub">Chọn lý do và mô tả ngắn. Chúng tôi xử lý theo quy định — không tự động gỡ/khoá.</p>
          </div>

          <div class="rm-body">
            <div class="rm-reasons" role="group" aria-label="Lý do báo cáo">
              <button
                v-for="r in REASONS" :key="r" type="button"
                class="rm-chip" :class="{ active: reason === r }"
                :aria-pressed="reason === r"
                @click="reason = r"
              >{{ r }}</button>
            </div>

            <textarea
              ref="textEl"
              v-model="detail"
              rows="3"
              class="rm-textarea"
              aria-label="Mô tả chi tiết"
              placeholder="Mô tả chi tiết (tối thiểu 5 ký tự)…"
            ></textarea>
          </div>

          <div class="rm-actions">
            <button type="button" class="btn btn-ghost" @click="close">Huỷ</button>
            <button type="button" class="btn btn-primary" :disabled="submitting || combined.length < 5" @click="submit">
              {{ submitting ? 'Đang gửi…' : 'Gửi báo cáo' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import type { ReportModalState } from '~/composables/useReport'

const modal = useState<ReportModalState>('report-modal', () => ({ open: false, targetType: 'post', targetId: '' }))
const { authHeaders } = useAuth()
const { show: showToast } = useToast()

const REASONS = ['Spam/quảng cáo', 'Sai sự thật', 'Xúc phạm/quấy rối', 'Nội dung không phù hợp', 'Vi phạm bản quyền', 'Khác']
const reason = ref('')
const detail = ref('')
const submitting = ref(false)
const sheetEl = ref<HTMLElement | null>(null)
const textEl = ref<HTMLTextAreaElement | null>(null)

const combined = computed(() => [reason.value, detail.value.trim()].filter(Boolean).join(' — '))

function close() { modal.value = { ...modal.value, open: false } }

const isOpen = computed(() => modal.value.open)
// Body-scroll lock, focus trap, Escape-to-close + focus restore (SSR-safe).
useModalA11y(isOpen, sheetEl, { onClose: close })

// Reset form + prefer focusing the textarea when the sheet opens.
watch(isOpen, (open) => {
  if (open) {
    reason.value = ''
    detail.value = ''
    nextTick(() => textEl.value?.focus())
  }
})

async function submit() {
  if (combined.value.length < 5) return
  submitting.value = true
  try {
    await $fetch('/api/report', {
      method: 'POST',
      headers: authHeaders(),
      body: { target_type: modal.value.targetType, target_id: modal.value.targetId, reason: combined.value },
    })
    showToast('Đã gửi báo cáo. Cảm ơn bạn!', 'success')
    close()
  } catch (e: unknown) {
    const err = e as { data?: { detail?: string; message?: string } }
    showToast(err?.data?.detail || err?.data?.message || 'Không thể gửi báo cáo', 'error')
  }
  submitting.value = false
}
</script>

<style scoped>
.rm-overlay {
  position: fixed; inset: 0; z-index: var(--z-lightbox);
  background: rgba(var(--black-rgb),.45); backdrop-filter: blur(2px);
  display: flex; align-items: flex-end; justify-content: center;
  padding: 0;
}
@media (min-width: 560px) { .rm-overlay { align-items: center; padding: var(--space-5); } }

.rm-sheet {
  background: var(--card); width: 100%; max-width: 460px;
  border-radius: 18px 18px 0 0; padding: var(--space-6);
  box-shadow: 0 -8px 40px rgba(var(--black-rgb),.18); position: relative;
  /* Flex column + capped height: middle scrolls, actions stay reachable. */
  display: flex; flex-direction: column;
  max-height: min(90vh, calc(100vh - 40px)); overflow: hidden;
}
@media (min-width: 560px) { .rm-sheet { border-radius: 18px; box-shadow: 0 12px 48px rgba(var(--black-rgb),.22); } }

.rm-head { flex-shrink: 0; }
.rm-body { flex: 1; min-height: 0; overflow-y: auto; overscroll-behavior-y: contain; }

.rm-close { position: absolute; top: 10px; right: 12px; background: none; border: none; font-size: 1.6rem; line-height: 1; color: var(--muted); cursor: pointer; padding: var(--space-1) var(--space-2); border-radius: 8px; }
.rm-close:hover { background: var(--bg-warm); color: var(--ink); }
.rm-sheet h3 { margin: 0 0 4px; font-size: 1.1rem; font-weight: 700; }
.rm-sub { margin: 0 0 var(--space-4); font-size: .84rem; color: var(--muted); line-height: 1.45; }

.rm-reasons { display: flex; flex-wrap: wrap; gap: var(--space-2); margin-bottom: var(--space-3); }
.rm-chip {
  font-size: .82rem; padding: 7px 14px; border-radius: 20px; min-height: var(--touch-min);
  border: .5px solid var(--line); background: var(--bg); color: var(--ink); cursor: pointer;
  transition: background .2s, border-color .2s, color .2s, transform .15s var(--ease-soft);
}
.rm-chip:hover { border-color: var(--primary); }
.rm-chip:active { transform: scale(.96); }
.rm-chip.active { background: var(--primary); color: var(--on-primary); border-color: var(--primary); }
.rm-chip:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }

.rm-textarea {
  width: 100%; box-sizing: border-box; padding: 11px 14px; border: .5px solid var(--line);
  border-radius: 12px; font: inherit; font-size: .9rem; background: var(--bg); color: var(--ink);
  resize: vertical; min-height: 72px; transition: border-color .2s, box-shadow .2s;
}
.rm-textarea:focus { outline: none; border-color: var(--primary); box-shadow: 0 0 0 3px rgba(var(--primary-rgb),.1); }

.rm-actions { display: flex; justify-content: flex-end; gap: var(--space-3); margin-top: var(--space-4); flex-shrink: 0; }
.rm-actions .btn { min-height: 44px; }

.rm-fade-enter-active, .rm-fade-leave-active { transition: opacity .25s ease; }
.rm-fade-enter-active .rm-sheet, .rm-fade-leave-active .rm-sheet { transition: transform .3s var(--ease-soft); }
.rm-fade-enter-from, .rm-fade-leave-to { opacity: 0; }
.rm-fade-enter-from .rm-sheet, .rm-fade-leave-to .rm-sheet { transform: translateY(16px); }

.dark .rm-sheet { background: var(--card); }
.dark .rm-chip { background: var(--glass-subtle); border-color: var(--glass-border); }
.dark .rm-textarea { background: var(--glass-subtle); border-color: var(--glass-border); }

@media (prefers-reduced-motion: reduce) {
  .rm-fade-enter-active, .rm-fade-leave-active,
  .rm-fade-enter-active .rm-sheet, .rm-fade-leave-active .rm-sheet { transition: none; }
  .rm-chip:active { transform: none; }
}
@media (forced-colors: active) {
  .rm-sheet { border: 2px solid CanvasText; background: Canvas; }
  .rm-close { border: 1px solid ButtonText; }
  .rm-chip { border: 1px solid ButtonText; }
  .rm-chip.active { background: Highlight; color: HighlightText; }
  .rm-textarea { border: 1px solid ButtonBorder; }
}
</style>
