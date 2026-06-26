<template>
  <div class="ai-tips">
    <button type="button" class="ai-tips-header" @click="toggle" :aria-expanded="expanded">
      <h3>Gợi ý cho bạn</h3>
      <span class="ai-toggle">{{ expanded ? '▲' : '▼' }}</span>
    </button>
    <div v-if="expanded" class="ai-tips-body">
      <div v-if="loading" class="ai-loading"><div class="spinner spinner-center"></div><small>Đang tạo gợi ý…</small></div>
      <div v-else-if="errored" class="ai-error" role="status">
        <small>Không tải được gợi ý.</small>
        <button type="button" class="ai-retry-btn" @click="retryFetch">Thử lại</button>
      </div>
      <template v-else-if="tips">
        <div class="ai-content" v-html="formatTips(tips)"></div>
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
.spinner-center { margin: 0 auto; }
:deep(.tip-bullet) { color: var(--primary); }
.ai-disclaimer { margin: var(--space-2) 0 0; font-size: .75rem; color: var(--text-muted); }
.ai-error { display: flex; align-items: center; gap: var(--space-2); padding: var(--space-3); font-size: var(--text-sm); color: var(--muted); }
.ai-retry-btn { font-size: var(--text-xs); font-weight: var(--weight-semibold); color: var(--primary-fg); background: none; border: none; cursor: pointer; text-decoration: underline; text-underline-offset: 2px; padding: var(--space-1); min-height: 36px; }
.ai-tips-body { animation: tipsSlideIn .35s var(--ease-out-expo); }
@keyframes tipsSlideIn { from { opacity: 0; transform: translateY(-8px) scale(.99); } to { opacity: 1; transform: translateY(0) scale(1); } }
@media (prefers-reduced-motion: reduce) { .ai-tips-body { animation: none; } }
@media (pointer: coarse) { .ai-retry-btn { min-height: 44px; } }
</style>
