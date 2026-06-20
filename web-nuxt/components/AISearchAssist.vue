<template>
  <div class="ai-search-assist">
    <button type="button" v-if="!aiReply && !loading" class="ai-toggle-btn" @click="load">✨ Gợi ý AI cho "{{ query }}"</button>
    <div v-else-if="loading" class="ai-loading ai-loading-padded"><div class="spinner spinner-center"></div></div>
    <template v-else>
      <div class="ai-search-header">
        <span>Gợi ý nhanh</span>
        <button type="button" class="ai-toggle-btn" @click="expanded = !expanded">{{ expanded ? 'Thu gọn' : 'Xem thêm' }}</button>
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
const expanded = ref(true)

function sanitize(text: string) {
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

function formatReply(text: string) {
  return sanitize(text).replace(/\n/g, '<br>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
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
  const q = props.query
  if (!q || q.length < 2) return
  const cached = readCache(q)
  if (cached) {
    aiReply.value = cached.reply
    suggestions.value = cached.suggestions
    return
  }
  loading.value = true
  const { aiChat } = useAI()
  const res = await aiChat(`Người dùng tìm kiếm: "${q}". Trả lời ngắn gọn 2-3 câu về kết quả liên quan đến du lịch/đặc sản Vĩnh Long. Nếu không liên quan, nói "Không tìm thấy kết quả phù hợp".`)
  aiReply.value = res.reply
  suggestions.value = res.suggestions
  writeCache(q, res.reply, res.suggestions)
  loading.value = false
}

// Đổi truy vấn -> reset (hiện lại nút), KHÔNG tự gọi LLM.
watch(() => props.query, () => {
  aiReply.value = ''
  suggestions.value = []
  expanded.value = true
})
</script>

<style scoped>
.ai-loading-padded { padding: var(--space-4); }
.ai-disclaimer { margin: var(--space-2) 0 0; font-size: .75rem; color: var(--text-muted); }
.spinner-center { margin: 0 auto; }
.ai-search-body { animation: aiSlideIn .35s var(--ease-out-expo); }
@keyframes aiSlideIn { from { opacity: 0; transform: translateY(-8px) scale(.99); } to { opacity: 1; transform: translateY(0) scale(1); } }
@media (prefers-reduced-motion: reduce) { .ai-search-body { animation: none; } }
</style>
