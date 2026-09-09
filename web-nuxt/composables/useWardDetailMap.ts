import { ref, watch, onUnmounted, type Ref, type ComputedRef } from 'vue'
import type { Entity } from '~/types'
import { TYPE_META } from '~/composables/useConstants'
import { normalizeCoords } from '~/composables/useCoords'
import { escapeHtml } from '~/utils/safe'
import { useNDAMap } from '~/composables/useNDAMap'

export interface UseWardDetailMapOptions {
  place: Ref<Entity | null | undefined> | ComputedRef<Entity | null | undefined>
  entities: Ref<Entity[]> | ComputedRef<Entity[]>
}

export function useWardDetailMap(options: UseWardDetailMapOptions) {
  const { place, entities } = options
  const mapEl = ref<HTMLElement | null>(null)
  const mapLoadError = ref(false)
  const mapReady = ref(false)
  const { createMap } = useNDAMap()

  let mapInstance: any = null
  let mapLoadTimer: ReturnType<typeof setTimeout> | undefined

  onUnmounted(() => {
    if (mapLoadTimer) clearTimeout(mapLoadTimer)
    if (mapInstance) {
      mapInstance.remove()
      mapInstance = null
    }
  })

  watch(mapEl, async (el) => {
    const currentPlace = place.value
    const center = normalizeCoords(currentPlace?.coordinates)
    if (!el || !center) return
    const coords = center
    let map: any, maplibregl: any
    try {
      const r = await createMap(el, { center: [coords[1], coords[0]], zoom: 14 })
      map = r.map
      maplibregl = r.maplibregl
      mapInstance = map
    } catch {
      mapLoadError.value = true
      return
    }

    map.on('styleimagemissing', (e: any) => {
      if (!map.hasImage(e.id)) map.addImage(e.id, { width: 1, height: 1, data: new Uint8Array(4) })
    })
    mapLoadTimer = setTimeout(() => {
      if (!map.isStyleLoaded()) mapLoadError.value = true
    }, 15000)
    map.on('load', () => {
      clearTimeout(mapLoadTimer)
      mapLoadError.value = false
      mapReady.value = true
    })

    map.addControl(new maplibregl.FullscreenControl(), 'top-right')

    // Ward center marker — popup mở mặc định
    const centerPopup = new maplibregl.Popup({ offset: 25, closeOnClick: false })
      .setHTML(`<strong>${escapeHtml(currentPlace?.name || '')}</strong>`)
    new maplibregl.Marker({ color: 'var(--clay-600)', scale: 1.1 })
      .setLngLat([coords[1], coords[0]])
      .setPopup(centerPopup)
      .addTo(map)
      .togglePopup()

    // Entity markers
    const bounds = new maplibregl.LngLatBounds()
    bounds.extend([coords[1], coords[0]])
    const wardEntities = entities.value

    for (const ent of wardEntities) {
      const c = normalizeCoords(ent.coordinates)
      if (!c) continue
      const meta = TYPE_META[ent.type] || { icon: 'pin', label: '' }
      const markerEl = document.createElement('div')
      markerEl.className = 'wp-marker'
      markerEl.title = ent.name
      new maplibregl.Marker({ element: markerEl })
        .setLngLat([c[1], c[0]])
        .setPopup(new maplibregl.Popup({ offset: 20, maxWidth: '220px' }).setHTML(
          `<a href="/dia-diem/${encodeURIComponent(ent.id)}" class="map-popup-link">${escapeHtml(ent.name)}</a><br><small>${escapeHtml(meta.label)}</small>`
        ))
        .addTo(map)
      bounds.extend([c[1], c[0]])
    }

    if (wardEntities.length && !bounds.isEmpty()) {
      map.fitBounds(bounds, { padding: 60, maxZoom: 16 })
    }
  }, { once: true })

  return {
    mapEl,
    mapReady,
    mapLoadError,
  }
}
