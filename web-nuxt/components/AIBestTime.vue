<template>
  <div class="ai-besttime">
    <div class="ai-besttime-head sediment-head"><h4>Thời điểm tốt nhất</h4><span class="ai-label"><span class="emoji-chip" aria-hidden="true">✨</span> AI gợi ý</span></div>
    <button type="button" v-if="!result && !loading && !errored" class="ai-toggle-btn" @click="load">Xem gợi ý AI</button>
    <div v-else-if="loading" class="ai-loading" role="status" aria-label="Đang tải">
      <span class="ai-dot"></span><span class="ai-dot"></span><span class="ai-dot"></span>
    </div>
    <div v-else-if="errored" class="ai-error" role="status">
      <small>Không tải được gợi ý.</small>
      <button type="button" class="ai-retry-btn" @click="retry">Thử lại</button>
    </div>
    <template v-else>
      <p class="ai-besttime-text editorial-body">{{ result }}</p>
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
/* .sediment-head's shared rule (components.css) only targets h2; this panel's
   heading is an h4 (unchanged from before — no markup-level change to
   heading rank), so the tick + serif treatment is re-declared here for h4
   scoped to this component only. Values mirror the shared h2 rule exactly. */
.ai-besttime-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: var(--space-2);
}
.ai-besttime-head h4 {
  font-family: var(--font-editorial);
  font-weight: 600;
  letter-spacing: -.01em;
  position: relative;
  padding-left: var(--space-4);
  margin: 0;
}
.ai-besttime-head h4::before {
  content: "";
  position: absolute; left: 0; top: 50%; transform: translateY(-50%);
  width: 4px; height: 1.05em; border-radius: var(--radius-full);
  background: linear-gradient(180deg, var(--river-600) 0%, var(--amber-600) 52%, var(--clay-600) 100%);
}
.dark .ai-besttime-head h4::before {
  background: linear-gradient(180deg, #74ABB5 0%, var(--amber-500) 52%, var(--clay-400) 100%);
}
/* Quiet "AI-assisted" label — a hairline-bordered tag, not a decorative badge,
   so the panel reads as clearly-machine-authored without shouting about it. */
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
