export type MapLibreModule = typeof import('maplibre-gl') & {
  setWorkerUrl?: (url: string) => void
}

const MAPLIBRE_SCRIPT_URL = '/maplibre-gl-csp.js'
const MAPLIBRE_STYLESHEET_URL = '/maplibre-gl.css'
const MAPLIBRE_SCRIPT_MARKER = 'data-vl360-maplibre'

type MapLibreWindow = typeof globalThis & {
  maplibregl?: MapLibreModule
}

let mapLibrePromise: Promise<MapLibreModule> | undefined

export async function loadMapLibre(): Promise<MapLibreModule> {
  const globalObject = globalThis as MapLibreWindow
  if (typeof globalObject.maplibregl?.Map === 'function') return globalObject.maplibregl
  if (typeof document === 'undefined') throw new Error('MapLibre can only load in a browser')

  // The CSP build is UMD: it registers `globalThis.maplibregl` instead of
  // exporting an ES module namespace, so native dynamic import is incorrect.
  mapLibrePromise ??= new Promise<MapLibreModule>((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(`script[${MAPLIBRE_SCRIPT_MARKER}]`)
    const script = existing ?? document.createElement('script')
    const finish = () => {
      const loaded = (globalThis as MapLibreWindow).maplibregl
      if (typeof loaded?.Map === 'function') resolve(loaded)
      else reject(new Error('MapLibre CSP asset loaded without a global API'))
    }
    script.addEventListener('load', finish, { once: true })
    script.addEventListener('error', () => reject(new Error('Failed to load MapLibre CSP asset')), { once: true })
    if (!existing) {
      script.async = true
      script.src = MAPLIBRE_SCRIPT_URL
      script.setAttribute(MAPLIBRE_SCRIPT_MARKER, 'true')
      document.head.appendChild(script)
    }
  })

  try {
    return await mapLibrePromise
  } catch (error) {
    mapLibrePromise = undefined
    throw error
  }
}

export function ensureMapLibreStylesheet(): void {
  if (typeof document === 'undefined' || document.querySelector(`link[href="${MAPLIBRE_STYLESHEET_URL}"]`)) return
  const link = document.createElement('link')
  link.rel = 'stylesheet'
  link.href = MAPLIBRE_STYLESHEET_URL
  document.head.appendChild(link)
}
