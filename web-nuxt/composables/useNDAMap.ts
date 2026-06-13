import type { Map, Marker, NavigationControl } from 'maplibre-gl'

const NDA_STYLE_BASE = 'https://maptiles.openmap.vn/styles'

export function useNDAMap() {
  const config = useRuntimeConfig()
  const apiKey = config.public.ndaMapKey as string

  function getStyleUrl(theme: 'day' | 'night' = 'day') {
    return `${NDA_STYLE_BASE}/${theme}-v1/style.json?apikey=${apiKey}`
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

    map.addControl(new maplibregl.AttributionControl({
      compact: true,
      customAttribution: '© <a href="https://openmap.vn">Openmap.vn</a> | Bản đồ Việt Nam',
    }))

    map.addControl(new maplibregl.NavigationControl(), 'top-right')

    return { map, maplibregl }
  }

  return { createMap, getStyleUrl }
}
