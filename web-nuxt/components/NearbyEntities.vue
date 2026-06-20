<template>
  <div v-if="nearby.length || sameType.length" class="nearby-section">
    <div v-if="nearby.length">
      <h2>Gần đây tại {{ areaLabel }}</h2>
      <div class="nearby-grid">
        <NuxtLink
          v-for="e in nearby"
          :key="e.id"
          :to="`/dia-diem/${e.id}`"
          class="nearby-item"
        >
          <NuxtImg v-if="getThumb(e) && !failedThumbs.has(e.id)" :src="getThumb(e)" :alt="e.name" class="nearby-thumb" width="56" height="56" loading="lazy" @error="failedThumbs.add(e.id)" />
          <span v-else class="nearby-emoji">{{ getTypeMeta(e.type).emoji }}</span>
          <div class="nearby-info">
            <strong>{{ e.name }}</strong>
            <small>{{ getTypeMeta(e.type).label }}</small>
          </div>
        </NuxtLink>
      </div>
    </div>
    <div v-if="sameType.length" class="nearby-sametype">
      <h2>{{ sameTypeLabel }} khác</h2>
      <div class="nearby-grid">
        <NuxtLink
          v-for="e in sameType"
          :key="e.id"
          :to="`/dia-diem/${e.id}`"
          class="nearby-item"
        >
          <NuxtImg v-if="getThumb(e) && !failedThumbs.has(e.id)" :src="getThumb(e)" :alt="e.name" class="nearby-thumb" width="56" height="56" loading="lazy" @error="failedThumbs.add(e.id)" />
          <span v-else class="nearby-emoji">{{ getTypeMeta(e.type).emoji }}</span>
          <div class="nearby-info">
            <strong>{{ e.name }}</strong>
            <small v-if="e.place_name">{{ e.place_name }}</small>
          </div>
        </NuxtLink>
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
  $fetch<any>(`/api/entities?area=${encodeURIComponent(props.area)}&limit=80`)
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

const failedThumbs = reactive(new Set<string>())

function getTypeMeta(type: string) {
  return TYPE_META[type] || { emoji: '📍', label: type }
}

function getThumb(e: Entity): string | null {
  const imgs = e.images || e.image_urls
  if (Array.isArray(imgs) && imgs.length > 0) return imgs[0]
  if (typeof e.image === 'string' && e.image) return e.image
  return null
}
</script>
