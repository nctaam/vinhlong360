import { copyFile, mkdir } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const source = resolve(root, 'node_modules/maplibre-gl/dist/maplibre-gl-csp-worker.js')
const target = resolve(root, 'public/maplibre-gl-csp-worker.js')
const scriptSource = resolve(root, 'node_modules/maplibre-gl/dist/maplibre-gl-csp.js')
const scriptTarget = resolve(root, 'public/maplibre-gl-csp.js')
const cssSource = resolve(root, 'node_modules/maplibre-gl/dist/maplibre-gl.css')
const cssTarget = resolve(root, 'public/maplibre-gl.css')

await mkdir(dirname(target), { recursive: true })
await copyFile(source, target)
await copyFile(scriptSource, scriptTarget)
await copyFile(cssSource, cssTarget)
console.log('MapLibre CSP assets copied to public/')
