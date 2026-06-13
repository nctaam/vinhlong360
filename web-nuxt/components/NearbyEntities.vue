<template>
  <div v-if="nearby.length" class="nearby-section">
    <h2>Gần đây tại {{ areaLabel }}</h2>
    <div class="nearby-grid">
      <NuxtLink
        v-for="e in nearby"
        :key="e.id"
        :to="`/dia-diem/${e.id}`"
        class="nearby-item"
      >
        <span class="nearby-emoji">{{ getTypeMeta(e.type).emoji }}</span>
        <div class="nearby-info">
          <strong>{{ e.name }}</strong>
          <small>{{ getTypeMeta(e.type).label }}</small>
        </div>
      </NuxtLink>
    </div>
  </div>
</template>

<script setup lang="ts">
import { TYPE_META, AREA_META } from '~/composables/useConstants'

const props = defineProps<{
  entityId: string
  entityType: string
  area: string
}>()

const areaLabel = computed(() => AREA_META[props.area]?.name || props.area)

const { data } = await useAsyncData(`nearby-${props.area}`, () =>
  $fetch<any>(`/api/entities?area=${encodeURIComponent(props.area)}&limit=50`)
)

const nearby = computed(() => {
  if (!data.value) return []
  const list = (data.value.entities || [])
    .filter((e: any) =>
      (e.place_area || e.area) === props.area &&
      e.id !== props.entityId &&
      e.type !== props.entityType
    )
  const byType: Record<string, any[]> = {}
  for (const e of list) {
    if (!byType[e.type]) byType[e.type] = []
    byType[e.type].push(e)
  }
  const picked: any[] = []
  for (const type of Object.keys(byType)) {
    picked.push(byType[type][0])
    if (picked.length >= 6) break
  }
  if (picked.length < 6) {
    for (const e of list) {
      if (!picked.find(p => p.id === e.id)) {
        picked.push(e)
        if (picked.length >= 6) break
      }
    }
  }
  return picked
})

function getTypeMeta(type: string) {
  return TYPE_META[type] || { emoji: '📍', label: type }
}
</script>
