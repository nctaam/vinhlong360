<template>
  <div class="ai-besttime">
    <h4>Thời điểm tốt nhất</h4>
    <button type="button" v-if="!result && !loading && !errored" class="ai-toggle-btn" @click="load">✨ Xem gợi ý AI</button>
    <div v-else-if="loading" class="ai-loading" role="status" aria-label="Đang tải">
      <span class="ai-dot"></span><span class="ai-dot"></span><span class="ai-dot"></span>
    </div>
    <div v-else-if="errored" class="ai-error" role="status">
      <small>Không tải được gợi ý.</small>
      <button type="button" class="ai-retry-btn" @click="retry">Thử lại</button>
    </div>
    <template v-else>
      <p class="ai-besttime-text">{{ result }}</p>
      <p class="ai-disclaimer">{{ disclaimerText }}</p>
    </template>
  </div>
</template>

<script setup lang="ts">
// GĐ4.3: chỉ gọi LLM khi người dùng bấm — không auto-fire khi tải trang.
const props = defineProps<{ entityId: string; entityName: string }>()

const { get: ss } = useSiteSettings()
const disclaimerText = computed(() => ss('ai.disclaimer_text', 'Gợi ý do AI tạo — mang tính tham khảo.'))

const result = ref('')
const loading = ref(false)
const errored = ref(false)

function cacheKey() {
  return `aibest:${props.entityId}`
}

function readCache(): string {
  if (typeof sessionStorage === 'undefined') return ''
  try { return sessionStorage.getItem(cacheKey()) || '' } catch { return '' }
}

function writeCache(val: string) {
  if (typeof sessionStorage === 'undefined' || !val) return
  try { sessionStorage.setItem(cacheKey(), val) } catch { /* quota/disabled — ignore */ }
}

async function load() {
  if (loading.value) return
  const cached = readCache()
  if (cached) { result.value = cached; return }
  loading.value = true
  errored.value = false
  try {
    const { aiBestTime } = useAI()
    result.value = await aiBestTime(props.entityId, props.entityName)
    writeCache(result.value)
  } catch {
    result.value = ''
    errored.value = true
  } finally {
    loading.value = false
  }
}

function retry() {
  errored.value = false
  load()
}
</script>

<style scoped>
.ai-disclaimer { margin: var(--space-1) 0 0; font-size: .75rem; color: var(--text-muted); }
.ai-error { display: flex; align-items: center; gap: var(--space-2); padding: var(--space-2) 0; font-size: var(--text-sm); color: var(--muted); }
.ai-retry-btn { font-size: var(--text-xs); font-weight: var(--weight-semibold); color: var(--primary-fg); background: none; border: none; cursor: pointer; text-decoration: underline; text-underline-offset: 2px; padding: var(--space-1); min-height: 44px; }
.ai-loading { display: flex; gap: var(--space-1); padding: var(--space-2) 0; }
.ai-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--primary-fg); animation: aiBounce .6s infinite alternate; }
.ai-dot:nth-child(2) { animation-delay: .2s; }
.ai-dot:nth-child(3) { animation-delay: .4s; }
@keyframes aiBounce { to { opacity: .25; transform: translateY(-4px); } }
@media (prefers-reduced-motion: reduce) { .ai-dot { animation: none; } }
@media (pointer: coarse) { .ai-retry-btn { min-height: 44px; } }
</style>
