<template>
  <div class="ai-tips">
    <button class="ai-tips-header" @click="toggle" :aria-expanded="expanded">
      <h3>Gợi ý cho bạn</h3>
      <span class="ai-toggle">{{ expanded ? '▲' : '▼' }}</span>
    </button>
    <div v-if="expanded" class="ai-tips-body">
      <div v-if="loading" class="ai-loading"><div class="spinner" style="margin: 0 auto"></div><small>Đang tạo gợi ý…</small></div>
      <div v-else-if="tips" class="ai-content" v-html="formatTips(tips)"></div>
      <div v-else class="ai-loading"><small>Không tạo được gợi ý lúc này.</small></div>
    </div>
  </div>
</template>

<script setup lang="ts">
// GĐ4.3: KHÔNG gọi LLM khi tải trang — chỉ tạo gợi ý khi người dùng bấm mở (tiết kiệm chi phí).
const props = defineProps<{ entityId: string; entityName: string }>()

const tips = ref('')
const loading = ref(false)
const expanded = ref(false)
const fetched = ref(false)

function sanitize(text: string) {
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

function formatTips(text: string) {
  return sanitize(text)
    .replace(/\n/g, '<br>')
    .replace(/•\s*/g, '<span style="color:var(--primary)">•</span> ')
    .replace(/- /g, '<span style="color:var(--primary)">•</span> ')
}

async function toggle() {
  expanded.value = !expanded.value
  if (expanded.value && !fetched.value) {
    fetched.value = true
    loading.value = true
    const { aiEntityTips } = useAI()
    tips.value = await aiEntityTips(props.entityId, props.entityName)
    loading.value = false
  }
}
</script>
