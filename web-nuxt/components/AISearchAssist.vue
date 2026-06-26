<template>
  <div class="ai-search-assist">
    <button type="button" v-if="!aiReply && !loading && !errored" class="ai-toggle-btn" @click="load">✨ Gợi ý AI cho "{{ query }}"</button>
    <div v-else-if="loading" class="ai-loading ai-loading-padded" role="status" aria-label="Đang tải gợi ý"><div class="spinner spinner-center"></div></div>
    <div v-else-if="errored" class="ai-error" role="status">
      <small>Không tải được gợi ý.</small>
      <button type="button" class="ai-retry-btn" @click="retry">Thử lại</button>
    </div>
    <template v-else>
      <div class="ai-search-header">
        <span>Gợi ý nhanh</span>
        <button type="button" class="ai-toggle-btn" :aria-expanded="expanded" @click="expanded = !expanded">{{ expanded ? 'Thu gọn' : 'Xem thêm' }}</button>
      </div>
      <div v-if="expanded" class="ai-search-body" v-html="formatReply(aiReply)"></div>
      <div v-if="suggestions.length && expanded" class="ai-search-suggestions">
        <NuxtLink v-for="s in suggestions" :key="s" :to="`/tim-kiem?q=${encodeURIComponent(s)}`" class="chip">{{ s }}</NuxtLink>
      </div>
      <p v-if="expanded" class="ai-disclaimer">{{ disclaimerText }}</p>
    </template>
  </div>
</template>

<script setup lang="ts">
// GĐ4.3: chỉ gọi LLM khi người dùng bấm "Gợi ý AI" — không auto-fire mỗi lần tìm kiếm.
const props = defineProps<{ query: string }>()

const { get: ss } = useSiteSettings()
const disclaimerText = computed(() => ss('ai.disclaimer_text', 'Gợi ý do AI tạo — mang tính tham khảo.'))

const aiReply = ref('')
const suggestions = ref<string[]>([])
const loading = ref(false)
const errored = ref(false)
const expanded = ref(true)

function sanitize(text: string) {
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

function formatReply(text: string) {
  const s = sanitize(text)
  return s.replace(/\*\*(.*?)\*\*/g, (_, g) => `<strong>${g}</strong>`).replace(/\n/g, '<br>')
}

function cacheKey(q: string) {
  return `aisearch:${q}`
}

function readCache(q: string): { reply: string; suggestions: string[] } | null {
  if (typeof sessionStorage === 'undefined') return null
  try {
    const raw = sessionStorage.getItem(cacheKey(q))
    if (!raw) return null
    const parsed = JSON.parse(raw)
    return { reply: parsed.reply || '', suggestions: Array.isArray(parsed.suggestions) ? parsed.suggestions : [] }
  } catch { return null }
}

function writeCache(q: string, reply: string, sugg: string[]) {
  if (typeof sessionStorage === 'undefined' || !reply) return
  try { sessionStorage.setItem(cacheKey(q), JSON.stringify({ reply, suggestions: sugg })) } catch { /* quota/disabled — ignore */ }
}

async function load() {
  if (loading.value) return
  const q = props.query
  if (!q || q.length < 2) return
  const cached = readCache(q)
  if (cached) {
    aiReply.value = cached.reply
    suggestions.value = cached.suggestions
    return
  }
  loading.value = true
  errored.value = false
  try {
    const { aiChat } = useAI()
    const res = await aiChat(`Người dùng tìm kiếm: "${q}". Trả lời ngắn gọn 2-3 câu về kết quả liên quan đến du lịch/đặc sản Vĩnh Long. Nếu không liên quan, nói "Không tìm thấy kết quả phù hợp".`)
    aiReply.value = res.reply
    suggestions.value = res.suggestions
    writeCache(q, res.reply, res.suggestions)
  } catch {
    aiReply.value = ''
    suggestions.value = []
    errored.value = true
  } finally {
    loading.value = false
  }
}

function retry() {
  errored.value = false
  load()
}

// Đổi truy vấn -> reset (hiện lại nút), KHÔNG tự gọi LLM.
watch(() => props.query, () => {
  aiReply.value = ''
  suggestions.value = []
  errored.value = false
  expanded.value = true
})
</script>

<style scoped>
.ai-loading-padded { padding: var(--space-4); }
.ai-disclaimer { margin: var(--space-2) 0 0; font-size: .75rem; color: var(--text-muted); }
.ai-error { display: flex; align-items: center; gap: var(--space-2); padding: var(--space-3); font-size: var(--text-sm); color: var(--muted); }
.ai-retry-btn { font-size: var(--text-xs); font-weight: var(--weight-semibold); color: var(--primary-fg); background: none; border: none; cursor: pointer; text-decoration: underline; text-underline-offset: 2px; padding: var(--space-1); min-height: 36px; }
.spinner-center { margin: 0 auto; }
.ai-search-body { animation: aiSlideIn .35s var(--ease-out-expo); }
@keyframes aiSlideIn { from { opacity: 0; transform: translateY(-8px) scale(.99); } to { opacity: 1; transform: translateY(0) scale(1); } }
@media (prefers-reduced-motion: reduce) { .ai-search-body { animation: none; } }
@media (pointer: coarse) { .ai-retry-btn { min-height: 44px; } }
</style>
