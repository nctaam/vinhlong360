<template>
  <div v-if="items.length" class="ai-recommend">
    <div class="section-head">
      <h2>{{ title }}</h2>
    </div>
    <div class="grid">
      <EntityCard v-for="e in items" :key="e.id" :entity="e" />
    </div>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{
  entityId?: string
  month?: number
  limit?: number
  title?: string
}>()

const items = ref<any[]>([])

onMounted(async () => {
  const { aiRecommend } = useAI()
  const res = await aiRecommend({
    entityId: props.entityId,
    month: props.month || new Date().getMonth() + 1,
    limit: props.limit || 6,
  })
  if (res?.recommendations) items.value = res.recommendations
  else if (res?.entities) items.value = res.entities
  else if (Array.isArray(res)) items.value = res
})
</script>
