<template>
  <div v-if="result || loading" class="ai-besttime">
    <h4>Thời điểm tốt nhất</h4>
    <div v-if="loading" class="ai-loading"><small>Đang tải…</small></div>
    <p v-else class="ai-besttime-text">{{ result }}</p>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{ entityId: string; entityName: string }>()

const result = ref('')
const loading = ref(true)

onMounted(async () => {
  const { aiBestTime } = useAI()
  result.value = await aiBestTime(props.entityId, props.entityName)
  loading.value = false
})
</script>
