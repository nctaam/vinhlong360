import type { Map } from 'maplibre-gl'
import { ensureMapLibreStylesheet, loadMapLibre, type MapLibreModule } from '../utils/maplibre-loader'

const NDA_STYLE_BASE = 'https://maptiles.openmap.vn/styles'
const OSM_TILE_URL = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'

type MapCreateResult = { map: Map; maplibregl: MapLibreModule }
export type NDAMapState = 'loading' | 'ready' | 'fallback' | 'error'
type MapCreatePositionOptions = {
  center?: [number, number]
  zoom?: number
  theme?: 'day' | 'night'
  onStateChange?: (state: NDAMapState) => void
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

    mapOptions.onStateChange?.('loading')

    let maplibregl: MapLibreModule
    try {
      // Interop CJS/ESM BẮT BUỘC ở đây. maplibre-gl 5.24.0 khai "type": "module"
      // trong package.json nhưng `main` trỏ tới dist/maplibre-gl.js — một bundle
      // UMD kết thúc bằng `}));` và KHÔNG có một câu `export` nào. Namespace thu
      // được vì thế không có `.Map`, nên `new maplibregl.Map(...)` ném
      // "maplibregl.Map is not a constructor" và MỌI bản đồ trên site chết:
      // /ban-do dựng 0 canvas, data-map-state="error" (đo 2026-08-23).
      // Chọn theo NĂNG LỰC chứ không theo hình dạng: hỏi "đối tượng nào có
      // constructor Map" thay vì "có khoá default không". Đọc `.default` trước
      // sẽ ném trên namespace giả của vitest khi mock không khai default —
      // tests/use-nda-map-lifecycle.test.ts:57 mock đúng như vậy.
      maplibregl = await loadMapLibre()
      // CSP build keeps the worker in a separately cached asset instead of
      // embedding it as a 100KB+ inline string in the client chunk.
      maplibregl.setWorkerUrl?.('/maplibre-gl-csp-worker.js')
    } catch (error) {
      mapOptions.onStateChange?.('error')
      throw error
    }
    if (!isActive()) return null
    try {
      ensureMapLibreStylesheet()
    } catch (error) {
      mapOptions.onStateChange?.('error')
      throw error
    }
    if (!isActive()) return null

    let map: Map
    try {
      map = new maplibregl.Map({
        container,
        // Không có khoá tile thì đi thẳng vào nền OpenStreetMap thay vì bắn một
        // request chắc chắn hỏng rồi mới rơi vào nhánh lỗi.
        style: apiKey ? getStyleUrl(mapOptions.theme ?? 'day') : getFallbackStyle(mapOptions.theme ?? 'day') as any,
        center: mapOptions.center ?? [106.0, 10.25],
        zoom: mapOptions.zoom ?? 10,
        attributionControl: false,
      })
    } catch (error) {
      mapOptions.onStateChange?.('error')
      throw error
    }
    if (!isActive()) {
      map.remove()
      return null
    }

    let fallbackApplied = !apiKey
    map.on('error', (event: { error?: unknown }) => {
      if (!isActive()) return
      if (!fallbackApplied && isRecoverableMapResourceError(event?.error)) {
        fallbackApplied = true
        mapOptions.onStateChange?.('fallback')
        try {
          map.setStyle(getFallbackStyle(mapOptions.theme ?? 'day') as any)
          return
        } catch {
          // Fall through to the list-preserving error state.
        }
      }
      mapOptions.onStateChange?.('error')
    })
    map.on('load', () => { if (isActive()) mapOptions.onStateChange?.('ready') })
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
