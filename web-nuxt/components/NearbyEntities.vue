<template>
  <div v-if="nearby.length || sameType.length" class="nearby-section reveal">
    <div v-if="nearby.length">
      <div class="sediment-head nb-head">
        <h2>Gần đây tại {{ areaLabel }}</h2>
      </div>
      <span class="nb-rule" aria-hidden="true"></span>
      <div class="scroll-row" role="region" :aria-label="`Gần đây tại ${areaLabel}`" tabindex="0">
        <EntityCard v-for="e in nearby" :key="e.id" :entity="e" />
      </div>
    </div>
    <div v-if="sameType.length" class="nearby-sametype">
      <div class="sediment-head nb-head">
        <h2>{{ sameTypeLabel }} khác</h2>
      </div>
      <span class="nb-rule" aria-hidden="true"></span>
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

<style scoped>
.nearby-section { margin-top: var(--space-8); }
.nb-head { margin: 0 0 var(--space-2); }
.nearby-section h2 {
  font-family: var(--font-editorial);
  font-size: var(--text-lg); font-weight: 600;
  letter-spacing: var(--tracking-tight);
  margin: 0;
}
.nearby-sametype { margin-top: var(--space-6); }

/* Tri-province sediment rule — card-scale hairline echo of the site-wide
   river→amber→clay thread (same idiom as PostCard.vue's .thread-rule),
   separating the section head from the scroll-row beneath it. */
.nb-rule {
  display: block;
  width: 48px;
  height: 2px;
  border-radius: var(--radius-full);
  margin: 0 0 var(--space-3);
  background: linear-gradient(90deg, var(--river-600) 0%, var(--amber-600) 52%, var(--clay-600) 100%);
}
.dark .nb-rule {
  background: linear-gradient(90deg, #74ABB5 0%, var(--amber-500) 52%, var(--clay-400) 100%);
}
</style>
