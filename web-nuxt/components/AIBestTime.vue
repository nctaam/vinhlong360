<template>
  <div class="ai-besttime">
    <h4>Thời điểm tốt nhất</h4>
    <button v-if="!result && !loading" class="ai-toggle-btn" @click="load">✨ Xem gợi ý AI</button>
    <div v-else-if="loading" class="ai-loading"><small>Đang tải…</small></div>
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
