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

<!-- Chuyển từ detail.css: chỉ NearbyEntities dùng .nearby-* → nạp theo component
     (bỏ khỏi global entry.css). Non-scoped + giữ đúng thứ tự base→override để cascade
     không đổi (không file nào khác style .nearby-*). -->
<style>
.nearby-section { margin-top: var(--space-8); }
.nearby-section h2 { font-size: var(--text-lg); font-weight: var(--weight-semibold); letter-spacing: var(--tracking-tight); margin: 0 0 var(--space-3); }
.nearby-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: var(--space-3);
  container-type: inline-size;
}
@media (max-width: 640px) {
  .nearby-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
@media (max-width: 480px) {
  .nearby-grid {
    grid-template-columns: 1fr;
  }
}
.nearby-item { display: flex; align-items: center; gap: var(--space-3); padding: var(--space-3) var(--space-3); background: var(--card); border: .5px solid var(--line); border-radius: var(--radius-md); transition: background .3s var(--ease-out), border-color .3s var(--ease-out), transform .35s var(--ease-spring-gentle), box-shadow .35s var(--ease-out-expo); }
.nearby-item:hover { background: var(--bg-warm); border-color: var(--primary-fg); transform: translateX(4px); box-shadow: var(--shadow-sm); }
.nearby-item:active { transform: translateX(1px) scale(.98); transition-duration: .1s; }
.nearby-item:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
.nearby-thumb { width: 56px; height: 56px; border-radius: var(--radius-sm); object-fit: cover; flex-shrink: 0; }
.nearby-sametype { margin-top: var(--space-6); }
.nearby-sametype h2 { font-size: var(--text-lg); font-weight: var(--weight-semibold); letter-spacing: var(--tracking-tight); margin: 0 0 var(--space-3); }
.nearby-emoji { font-size: var(--text-xl); flex-shrink: 0; }
.nearby-info { min-width: 0; }
.nearby-info strong { display: block; font-size: var(--text-sm); font-weight: var(--weight-semibold); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.nearby-info small { color: var(--muted); font-size: var(--text-xs); }
@media (prefers-reduced-motion: reduce) {
  .nearby-item:hover { transform: none; }
}
@media (min-width: 769px) and (max-width: 1024px) {
  .nearby-grid { grid-template-columns: repeat(2, 1fr); }
}
.dark .nearby-item { background: var(--card); border-color: var(--line); }
.dark .nearby-item:hover { background: rgba(255,255,255,.04); box-shadow: var(--shadow-sm); }
</style>
