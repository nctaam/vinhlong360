// @vitest-environment node

import { execFile } from 'node:child_process'
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join, resolve } from 'node:path'
import { promisify } from 'node:util'
import { afterEach, describe, expect, it } from 'vitest'

const execFileAsync = promisify(execFile)
const temporaryDirectories: string[] = []

afterEach(async () => {
  await Promise.all(temporaryDirectories.splice(0).map(path => rm(path, { recursive: true, force: true })))
})

describe('MapLibre static asset copier', () => {
  it('copies the v6 ESM graph and neutralizes stale v5 generated bundles', async () => {
    const target = await mkdtemp(join(tmpdir(), 'vl360-maplibre-assets-'))
    temporaryDirectories.push(target)
    await Promise.all([
      writeFile(join(target, 'maplibre-gl-csp.js'), 'vulnerable legacy main bundle'),
      writeFile(join(target, 'maplibre-gl-csp-worker.js'), 'vulnerable legacy worker bundle'),
    ])

    await execFileAsync(process.execPath, [
      resolve(process.cwd(), 'scripts/copy-maplibre-worker.mjs'),
      '--target',
      target,
    ], { cwd: process.cwd() })

    for (const asset of [
      'maplibre-gl.mjs',
      'maplibre-gl-shared.mjs',
      'maplibre-gl-worker.mjs',
      'maplibre-gl.css',
    ]) {
      const [actual, expected] = await Promise.all([
        readFile(join(target, asset), 'utf8'),
        readFile(resolve(process.cwd(), 'node_modules/maplibre-gl/dist', asset), 'utf8'),
      ])
      expect(actual).toBe(expected)
    }

    expect(await readFile(join(target, 'maplibre-gl-loader.mjs'), 'utf8')).toBe(
      "import * as maplibregl from './maplibre-gl.mjs'\nglobalThis.maplibregl = maplibregl\n",
    )
    await expect(readFile(join(target, 'maplibre-gl-csp.js'), 'utf8')).resolves.toContain('obsolete')
    await expect(readFile(join(target, 'maplibre-gl-csp-worker.js'), 'utf8')).resolves.toContain('obsolete')
  })
})
