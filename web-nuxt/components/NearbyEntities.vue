<template>
  <div v-if="nearby.length || sameType.length" class="nearby-section reveal">
    <div v-if="nearby.length">
      <h2>Gần đây tại {{ areaLabel }}</h2>
      <div class="scroll-row" role="region" :aria-label="`Gần đây tại ${areaLabel}`" tabindex="0">
        <EntityCard v-for="e in nearby" :key="e.id" :entity="e" />
      </div>
    </div>
    <div v-if="sameType.length" class="nearby-sametype">
      <h2>{{ sameTypeLabel }} khác</h2>
      <div class="scroll-row" role="region" :aria-label="`${sameTypeLabel} khác`" tabindex="0">
        <EntityCard v-for="e in sameType" :key="e.id" :entity="e" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Entity } from '~/types'
import { TYPE_META, AREA_META } from '~/composables/useConstants'

const props = defineProps<{
  entityId: string
  entityType: string
  area: string
}>()

const areaLabel = computed(() => AREA_META[props.area]?.name || props.area)
const sameTypeLabel = computed(() => TYPE_META[props.entityType]?.label || props.entityType)

const { data } = await useAsyncData(`nearby-${props.area}`, () =>
  apiFetch<any>(`/api/entities?area=${encodeURIComponent(props.area)}&limit=80`)
)

const nearby = computed(() => {
  if (!data.value) return []
  const list = (data.value.entities || [])
    .filter((e: Entity) =>
      (e.place_area || e.area) === props.area &&
      e.id !== props.entityId &&
      e.type !== props.entityType
    )
  const byType: Record<string, any[]> = {}
  for (const e of list) {
    if (!byType[e.type]) byType[e.type] = []
    byType[e.type]!.push(e)
  }
  const picked: Entity[] = []
  for (const type of Object.keys(byType)) {
    picked.push(byType[type]![0]!)
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

const sameType = computed(() => {
  if (!data.value) return []
  return (data.value.entities || [])
    .filter((e: Entity) =>
      (e.place_area || e.area) === props.area &&
      e.id !== props.entityId &&
      e.type === props.entityType
    )
    .slice(0, 4)
})


</script>

<style>
.nearby-section { margin-top: var(--space-8); }
.nearby-section h2 { font-size: var(--text-lg); font-weight: var(--weight-semibold); letter-spacing: var(--tracking-tight); margin: 0 0 var(--space-3); }
.nearby-sametype { margin-top: var(--space-6); }
</style>
