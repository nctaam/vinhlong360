<template>
  <div class="ai-tips">
    <button type="button" class="ai-tips-header sediment-head" @click="toggle" :aria-expanded="expanded">
      <h3>Gợi ý cho bạn</h3>
      <span class="ai-tips-header-right">
        <span class="ai-label"><IconLine name="sparkles" class="emoji-chip" /> AI gợi ý</span>
        <span class="ai-toggle"><IconLine :name="expanded ? 'chevron-up' : 'chevron-down'" aria-hidden="true" /></span>
      </span>
    </button>
    <div v-if="expanded" class="ai-tips-body">
      <div v-if="loading" class="ai-loading"><div class="spinner spinner-center"></div><small>Đang tạo gợi ý…</small></div>
      <div v-else-if="errored" class="ai-error" role="status">
        <IconLine name="alert-triangle" class="ai-error-icon" aria-hidden="true" />
        <small>Không tải được gợi ý.</small>
        <button type="button" class="ai-retry-btn" @click="retryFetch">
          <IconLine name="repeat" class="retry-icon" aria-hidden="true" />
          <span>Thử lại</span>
        </button>
      </div>
      <template v-else-if="tips">
        <div class="ai-content editorial-body" v-html="formatTips(tips)"></div>
        <p class="ai-disclaimer">{{ disclaimerText }}</p>
      </template>
      <div v-else-if="fetched" class="ai-loading"><small>Không tạo được gợi ý lúc này.</small></div>
    </div>
  </div>
</template>

<script setup lang="ts">
// GĐ4.3: KHÔNG gọi LLM khi tải trang — chỉ tạo gợi ý khi người dùng bấm mở (tiết kiệm chi phí).
const props = defineProps<{ entityId: string; entityName: string }>()

const { get: ss } = useSiteSettings()
const disclaimerText = computed(() => ss('ai.disclaimer_text', 'Gợi ý do AI tạo — mang tính tham khảo.'))

const tips = ref('')
const loading = ref(false)
const errored = ref(false)
const expanded = ref(false)
const fetched = ref(false)

function sanitize(text: string) {
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

function formatTips(text: string) {
  const s = sanitize(text)
  return s.replace(/\n/g, '<br>').replace(/•\s*/g, '<span class="tip-bullet">•</span> ').replace(/- /g, '<span class="tip-bullet">•</span> ')
}

function cacheKey() {
  return `aitips:${props.entityId}`
}

function readCache(): string {
  if (typeof sessionStorage === 'undefined') return ''
  try { return sessionStorage.getItem(cacheKey()) || '' } catch { return '' }
}

function writeCache(val: string) {
  if (typeof sessionStorage === 'undefined' || !val) return
  try { sessionStorage.setItem(cacheKey(), val) } catch { /* quota/disabled — ignore */ }
}

async function toggle() {
  expanded.value = !expanded.value
  if (expanded.value && !fetched.value) {
    fetched.value = true
    const cached = readCache()
    if (cached) { tips.value = cached; return }
    loading.value = true
    errored.value = false
    try {
      const { aiEntityTips } = useAI()
      tips.value = await aiEntityTips(props.entityId, props.entityName)
      writeCache(tips.value)
    } catch {
      tips.value = ''
      errored.value = true
    } finally {
      loading.value = false
    }
  }
}

function retryFetch() {
  errored.value = false
  fetched.value = false
  toggle()
}
</script>

<style scoped>
/* .sediment-head's shared rule (components.css) only targets h2; this
   panel's clickable header uses h3 (heading rank unchanged) — re-declare
   the same serif + tick treatment scoped to this component only. */
.ai-tips-header h3 {
  font-family: var(--font-editorial);
  font-weight: 600;
  letter-spacing: -.01em;
  position: relative;
  padding-left: var(--space-4);
  margin: 0;
}
.ai-tips-header h3::before {
  content: "";
  position: absolute; left: 0; top: 50%; transform: translateY(-50%);
  width: 4px; height: 1.05em; border-radius: var(--radius-full);
  background: linear-gradient(180deg, var(--river-600) 0%, var(--amber-600) 52%, var(--clay-600) 100%);
}
.dark .ai-tips-header h3::before {
  background: linear-gradient(180deg, var(--river-legacy-dark) 0%, var(--amber-500) 52%, var(--clay-400) 100%);
}
.ai-tips-header-right { display: inline-flex; align-items: center; gap: var(--space-3); }
/* Quiet "AI-assisted" label — hairline tag, not a decorative badge. */
.ai-label {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-2xs);
  font-weight: var(--weight-semibold);
  letter-spacing: var(--tracking-caps);
  text-transform: uppercase;
  color: var(--muted);
  white-space: nowrap;
}
.ai-toggle { display: inline-flex; align-items: center; justify-content: center; font-size: var(--text-xs); color: var(--muted); }
.spinner-center { margin: 0 auto; }
:deep(.tip-bullet) { color: var(--color-brand); }
.ai-disclaimer { margin: var(--space-2) 0 0; font-size: .75rem; color: var(--text-muted); }
.ai-error { display: flex; align-items: center; gap: var(--space-2); padding: var(--space-3); font-size: var(--text-sm); color: var(--muted); }
.ai-error-icon { width: 16px; height: 16px; color: var(--color-material-clay); flex-shrink: 0; }
.ai-retry-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  color: var(--color-action);
  background: none;
  border: none;
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 2px;
  padding: var(--space-1) var(--space-2);
  min-height: 44px;
  border-radius: var(--radius-control);
  transition: opacity .2s var(--ease-out-expo), transform .15s var(--ease-out-expo);
}
.ai-retry-btn:hover { opacity: .85; }
.ai-retry-btn:active { transform: scale(.96); }
.ai-retry-btn:focus-visible { outline: 2px solid var(--color-focus); outline-offset: 2px; }
.retry-icon { width: 13px; height: 13px; flex-shrink: 0; }
.ai-tips-body { animation: tipsSlideIn .35s var(--ease-out-expo); }
@keyframes tipsSlideIn { from { opacity: 0; transform: translateY(-8px) scale(.99); } to { opacity: 1; transform: translateY(0) scale(1); } }
@media (prefers-reduced-motion: reduce) { .ai-tips-body { animation: none; } }
@media (pointer: coarse) { .ai-retry-btn { min-height: 44px; } }
</style>
