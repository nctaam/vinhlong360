import type { Map, Marker, NavigationControl } from 'maplibre-gl'

const NDA_STYLE_BASE = 'https://maptiles.openmap.vn/styles'
const OSM_TILE_URL = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'

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

  async function createMap(container: HTMLElement, options?: {
    center?: [number, number]
    zoom?: number
    theme?: 'day' | 'night'
  }) {
    const maplibregl = await import('maplibre-gl')
    await import('maplibre-gl/dist/maplibre-gl.css')

    const map = new maplibregl.Map({
      container,
      style: getStyleUrl(options?.theme ?? 'day'),
      center: options?.center ?? [106.0, 10.25],
      zoom: options?.zoom ?? 10,
      attributionControl: false,
    })
    let fallbackApplied = false
    map.on('error', (event: { error?: unknown }) => {
      if (fallbackApplied || !isRecoverableMapResourceError(event?.error)) return
      fallbackApplied = true
      try {
        map.setStyle(getFallbackStyle(options?.theme ?? 'day') as any)
      } catch {
        // MapLibre can emit after teardown during route navigation; keep map failures non-fatal.
      }
    })

    map.addControl(new maplibregl.AttributionControl({
      compact: true,
      customAttribution: '© <a href="https://openmap.vn">Openmap.vn</a> | Bản đồ Việt Nam',
    }))

    map.addControl(new maplibregl.NavigationControl(), 'top-right')

    return { map, maplibregl }
  }

  return { createMap, getStyleUrl, getFallbackStyle }
}
