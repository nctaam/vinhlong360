<template>
  <div v-if="tips || loading" class="ai-tips">
    <button class="ai-tips-header" @click="expanded = !expanded" :aria-expanded="expanded">
      <h3>Gợi ý cho bạn</h3>
      <span class="ai-toggle">{{ expanded ? '▲' : '▼' }}</span>
    </button>
    <div v-if="expanded" class="ai-tips-body">
      <div v-if="loading" class="ai-loading"><div class="spinner" style="margin: 0 auto"></div><small>Đang tải…</small></div>
      <div v-else class="ai-content" v-html="formatTips(tips)"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{ entityId: string; entityName: string }>()

const tips = ref('')
const loading = ref(true)
const expanded = ref(true)

function sanitize(text: string) {
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

function formatTips(text: string) {
  return sanitize(text)
    .replace(/\n/g, '<br>')
    .replace(/•\s*/g, '<span style="color:var(--primary)">•</span> ')
    .replace(/- /g, '<span style="color:var(--primary)">•</span> ')
}

onMounted(async () => {
  const { aiEntityTips } = useAI()
  tips.value = await aiEntityTips(props.entityId, props.entityName)
  loading.value = false
})
</script>
