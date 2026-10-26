import { access, copyFile, mkdir, writeFile } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const dist = resolve(root, 'node_modules/maplibre-gl/dist')
const targetFlagIndex = process.argv.indexOf('--target')
const targetArgument = targetFlagIndex >= 0 ? process.argv[targetFlagIndex + 1] : undefined
if (targetFlagIndex >= 0 && !targetArgument) throw new Error('--target requires a directory')

const targetDirectory = targetArgument ? resolve(targetArgument) : resolve(root, 'public')
const assets = [
  'maplibre-gl.mjs',
  'maplibre-gl-shared.mjs',
  'maplibre-gl-worker.mjs',
  'maplibre-gl.css',
]
const moduleLoader = "import * as maplibregl from './maplibre-gl.mjs'\nglobalThis.maplibregl = maplibregl\n"
const obsoleteAsset = '/* obsolete MapLibre v5 generated asset; reload the page */\n'

async function neutralizeIfPresent(path) {
  try {
    await access(path)
  } catch (error) {
    if (error?.code === 'ENOENT') return
    throw error
  }
  await writeFile(path, obsoleteAsset)
}

await mkdir(targetDirectory, { recursive: true })
await Promise.all(assets.map(asset => copyFile(resolve(dist, asset), resolve(targetDirectory, asset))))
await writeFile(resolve(targetDirectory, 'maplibre-gl-loader.mjs'), moduleLoader)
await Promise.all([
  neutralizeIfPresent(resolve(targetDirectory, 'maplibre-gl-csp.js')),
  neutralizeIfPresent(resolve(targetDirectory, 'maplibre-gl-csp-worker.js')),
])
console.log(`MapLibre ESM assets copied to ${targetDirectory}`)
