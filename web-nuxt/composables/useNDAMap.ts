import type { Map, Marker, NavigationControl } from 'maplibre-gl'

const NDA_STYLE_BASE = 'https://maptiles.openmap.vn/styles'
const OSM_TILE_URL = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'

type MapLibreModule = typeof import('maplibre-gl')
type MapCreateResult = { map: Map; maplibregl: MapLibreModule }
type MapCreatePositionOptions = {
  center?: [number, number]
  zoom?: number
  theme?: 'day' | 'night'
}
type LifecycleMapCreateOptions = MapCreatePositionOptions & {
  isActive: () => boolean
}

export function useNDAMap() {
  const config = useRuntimeConfig()
  const apiKey = config.public.ndaMapKey as string

  function getStyleUrl(theme: 'day' | 'night' = 'day') {
    return `${NDA_STYLE_BASE}/${theme}-v1/style.json?apikey=${apiKey}`
  }

  function getFallbackStyle(theme: 'day' | 'night' = 'day') {
    const nightPaint = theme === 'night'
      ? { 'raster-brightness-max': 0.72, 'raster-saturation': -0.35 }
      : {}
    return {
      version: 8,
      sources: {
        osm: {
          type: 'raster',
          tiles: [OSM_TILE_URL],
          tileSize: 256,
          attribution: '© OpenStreetMap contributors',
        },
      },
      layers: [
        {
          id: 'osm',
          type: 'raster',
          source: 'osm',
          minzoom: 0,
          maxzoom: 19,
          paint: nightPaint,
        },
      ],
    }
  }

  function isRecoverableMapResourceError(error: unknown) {
    const text = String((error as { message?: string; url?: string })?.message || (error as { url?: string })?.url || '')
    return text.includes('maptiles.openmap.vn') || text.includes('/sprite') || text.includes('/data/base.json') || text.includes('Failed to fetch')
  }

  function createMap(container: HTMLElement, options: LifecycleMapCreateOptions): Promise<MapCreateResult | null>
  function createMap(container: HTMLElement, options?: MapCreatePositionOptions): Promise<MapCreateResult>
  async function createMap(container: HTMLElement, options?: MapCreatePositionOptions & { isActive?: () => boolean }): Promise<MapCreateResult | null> {
    const mapOptions = options ?? {}
    const isActive = mapOptions.isActive ?? (() => true)
    if (!isActive()) return null

    const maplibregl = await import('maplibre-gl')
    if (!isActive()) return null
    await import('maplibre-gl/dist/maplibre-gl.css')
    if (!isActive()) return null

    const map = new maplibregl.Map({
      container,
      // Không có khoá tile thì đi thẳng vào nền OpenStreetMap thay vì bắn một
      // request chắc chắn hỏng rồi mới rơi vào nhánh lỗi.
      style: apiKey ? getStyleUrl(mapOptions.theme ?? 'day') : getFallbackStyle(mapOptions.theme ?? 'day') as any,
      center: mapOptions.center ?? [106.0, 10.25],
      zoom: mapOptions.zoom ?? 10,
      attributionControl: false,
    })
    if (!isActive()) {
      map.remove()
      return null
    }

    let fallbackApplied = false
    map.on('error', (event: { error?: unknown }) => {
      if (!isActive() || fallbackApplied || !isRecoverableMapResourceError(event?.error)) return
      fallbackApplied = true
      try {
        map.setStyle(getFallbackStyle(mapOptions.theme ?? 'day') as any)
      } catch {
        // MapLibre can emit after teardown during route navigation; keep map failures non-fatal.
      }
    })
    if (!isActive()) {
      map.remove()
      return null
    }

    if (!isActive()) {
      map.remove()
      return null
    }
    const attributionControl = new maplibregl.AttributionControl({
      compact: true,
      customAttribution: '© <a href="https://openmap.vn">Openmap.vn</a> | Bản đồ Việt Nam',
    })
    if (!isActive()) {
      map.remove()
      return null
    }
    map.addControl(attributionControl)
    if (!isActive()) {
      map.remove()
      return null
    }

    const navigationControl = new maplibregl.NavigationControl()
    if (!isActive()) {
      map.remove()
      return null
    }
    map.addControl(navigationControl, 'top-right')
    if (!isActive()) {
      map.remove()
      return null
    }

    return { map, maplibregl }
  }

  return { createMap, getStyleUrl, getFallbackStyle }
}
