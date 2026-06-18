<template>
  <div class="ai-besttime">
    <h4>Thời điểm tốt nhất</h4>
    <button v-if="!result && !loading" class="ai-toggle-btn" @click="load">✨ Xem gợi ý AI</button>
    <div v-else-if="loading" class="ai-loading" role="status" aria-label="Đang tải">
      <span class="ai-dot"></span><span class="ai-dot"></span><span class="ai-dot"></span>
    </div>
    <p v-else class="ai-besttime-text">{{ result }}</p>
  </div>
</template>

<script setup lang="ts">
// GĐ4.3: chỉ gọi LLM khi người dùng bấm — không auto-fire khi tải trang.
const props = defineProps<{ entityId: string; entityName: string }>()

const result = ref('')
const loading = ref(false)

async function load() {
  loading.value = true
  const { aiBestTime } = useAI()
  result.value = await aiBestTime(props.entityId, props.entityName)
  loading.value = false
}
</script>

<style scoped>
.ai-loading { display: flex; gap: var(--space-1); padding: var(--space-2) 0; }
.ai-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--primary-fg); animation: aiBounce .6s infinite alternate; }
.ai-dot:nth-child(2) { animation-delay: .2s; }
.ai-dot:nth-child(3) { animation-delay: .4s; }
@keyframes aiBounce { to { opacity: .25; transform: translateY(-4px); } }
@media (prefers-reduced-motion: reduce) { .ai-dot { animation: none; } }
</style>
