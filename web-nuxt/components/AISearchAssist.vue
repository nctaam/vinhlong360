<template>
  <div v-if="aiReply || loading" class="ai-search-assist">
    <div class="ai-search-header">
      <span>Gợi ý nhanh</span>
      <button v-if="aiReply" class="ai-toggle-btn" @click="expanded = !expanded">{{ expanded ? 'Thu gọn' : 'Xem thêm' }}</button>
    </div>
    <div v-if="loading" class="ai-loading" style="padding: 12px"><div class="spinner" style="margin: 0 auto"></div></div>
    <div v-else-if="expanded" class="ai-search-body" v-html="formatReply(aiReply)"></div>
    <div v-if="suggestions.length && expanded" class="ai-search-suggestions">
      <NuxtLink v-for="s in suggestions" :key="s" :to="`/tim-kiem?q=${encodeURIComponent(s)}`" class="chip">{{ s }}</NuxtLink>
    </div>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{ query: string }>()

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

watch(() => props.query, async (q) => {
  if (!q || q.length < 2) { aiReply.value = ''; return }
  loading.value = true
  const { aiChat } = useAI()
  const res = await aiChat(`Người dùng tìm kiếm: "${q}". Trả lời ngắn gọn 2-3 câu về kết quả liên quan đến du lịch/đặc sản Vĩnh Long. Nếu không liên quan, nói "Không tìm thấy kết quả phù hợp".`)
  aiReply.value = res.reply
  suggestions.value = res.suggestions
  loading.value = false
}, { immediate: true })
</script>
