import type { Map } from 'maplibre-gl'
import { ensureMapLibreStylesheet, loadMapLibre, type MapLibreModule } from '../utils/maplibre-loader'

const NDA_STYLE_BASE = 'https://maptiles.openmap.vn/styles'
const NDA_DATA_URL = 'https://maptiles.openmap.vn/data/base.json'

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
    return apiKey
      ? `${NDA_STYLE_BASE}/${theme}-v1/style.json?apikey=${apiKey}`
      : `${NDA_STYLE_BASE}/${theme}-v1/style.json`
  }

  function getFallbackStyle(theme: 'day' | 'night' = 'day') {
    const isNight = theme === 'night'
    const sourceUrl = apiKey ? `${NDA_DATA_URL}?apikey=${apiKey}` : NDA_DATA_URL
    return {
      version: 8,
      sources: {
        openmap: {
          type: 'vector',
          url: sourceUrl,
          attribution: '© <a href="https://openmap.vn">Openmap.vn</a> | Bản đồ Việt Nam',
        },
      },
      layers: [
        {
          id: 'background',
          type: 'background',
          paint: { 'background-color': isNight ? '#11161d' : '#f6f1e7' },
        },
        {
          id: 'water',
          type: 'fill',
          source: 'openmap',
          'source-layer': 'water',
          paint: { 'fill-color': isNight ? '#192a3d' : '#b7d4e8' },
        },
        {
          id: 'waterway',
          type: 'line',
          source: 'openmap',
          'source-layer': 'waterway',
          paint: { 'line-color': isNight ? '#192a3d' : '#b7d4e8', 'line-width': 1.5 },
        },
        {
          id: 'transportation',
          type: 'line',
          source: 'openmap',
          'source-layer': 'transportation',
          paint: { 'line-color': isNight ? '#334155' : '#dfd6c7', 'line-width': 1.2 },
        },
        {
          id: 'boundary',
          type: 'line',
          source: 'openmap',
          'source-layer': 'boundary',
          paint: { 'line-color': isNight ? '#64748b' : '#b89f7d', 'line-width': 1 },
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
      // MapLibre 6 phát hành entry, shared module và worker dưới dạng ESM tách
      // rời. Loader nạp graph cùng origin rồi chỉ trả về khi API Map đã sẵn sàng.
      maplibregl = await loadMapLibre()
      // Module worker cùng origin không cần blob: trong CSP.
      maplibregl.setWorkerUrl?.('/maplibre-gl-worker.mjs')
    } catch (error) {
      if (isActive()) mapOptions.onStateChange?.('error')
      throw error
    }
    if (!isActive()) return null
    try {
      ensureMapLibreStylesheet()
    } catch (error) {
      if (isActive()) mapOptions.onStateChange?.('error')
      throw error
    }
    if (!isActive()) return null

    const theme = mapOptions.theme ?? 'day'
    let map: Map
    try {
      map = new maplibregl.Map({
        container,
        // Chỉ sử dụng nền bản đồ vector OpenMap.vn (styles hoặc vector base.json).
        style: apiKey ? getStyleUrl(theme) : getFallbackStyle(theme) as any,
        center: mapOptions.center ?? [106.0, 10.25],
        zoom: mapOptions.zoom ?? 10,
        attributionControl: false,
      })
    } catch (error) {
      if (isActive()) mapOptions.onStateChange?.('error')
      throw error
    }
    if (!isActive()) {
      map.remove()
      return null
    }

    let fallbackApplied = !apiKey
    let fallbackFailed = false
    map.on('error', (event: { error?: unknown }) => {
      if (!isActive()) return
      if (isRecoverableMapResourceError(event?.error)) {
        if (!fallbackApplied) {
          fallbackApplied = true
          mapOptions.onStateChange?.('fallback')
          try {
            map.setStyle(getFallbackStyle(theme) as any)
            return
          } catch {
            fallbackFailed = true
          }
        } else if (!fallbackFailed) {
          return
        }
      }
      mapOptions.onStateChange?.('error')
    })
    map.on('load', () => { if (isActive()) mapOptions.onStateChange?.('ready') })
    if (!isActive()) {
      map.remove()
      return null
    }

    try {
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
    } catch (error) {
      map.remove()
      if (isActive()) mapOptions.onStateChange?.('error')
      throw error
    }

    return { map, maplibregl }
  }

  return { createMap, getStyleUrl, getFallbackStyle }
}
