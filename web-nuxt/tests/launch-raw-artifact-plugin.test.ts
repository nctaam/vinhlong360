// @vitest-environment node

import { createHash } from 'node:crypto'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

import { createLaunchRawArtifactPlugin } from '../build/launchRawArtifactPlugin'

const repositoryRoot = fileURLToPath(new URL('../..', import.meta.url))
const configDirectory = resolve(repositoryRoot, 'config')
const artifactNames = [
  'launch-indexing-policy.json',
  'ai-disclosure.json',
] as const

function extractDefaultString(code: string): string {
  const prefix = 'export default '
  expect(code.startsWith(prefix)).toBe(true)
  return JSON.parse(code.slice(prefix.length)) as string
}

describe('launch raw artifact Nitro plugin', () => {
  it.each(artifactNames)('loads %s without changing its bytes', async (artifactName) => {
    const artifactPath = resolve(configDirectory, artifactName)
    const canonicalBytes = readFileSync(artifactPath)
    const canonicalSource = canonicalBytes.toString('utf8')
    const plugin = createLaunchRawArtifactPlugin(repositoryRoot)

    const loaded = await plugin.load(`${artifactPath}?raw`)

    expect(loaded).not.toBeNull()
    expect(typeof loaded).toBe('object')
    const result = loaded as { code: string, map: unknown }
    const loadedSource = extractDefaultString(result.code)
    expect(result.map).toEqual({
      version: 3,
      sources: [artifactPath],
      sourcesContent: [canonicalSource],
      names: [],
      mappings: '',
    })
    expect(loadedSource).toBe(canonicalSource)
    expect(createHash('sha256').update(loadedSource, 'utf8').digest('hex'))
      .toBe(createHash('sha256').update(canonicalBytes).digest('hex'))
  })

  it.each([
    ['queryless artifact', resolve(configDirectory, artifactNames[0])],
    ['url query', `${resolve(configDirectory, artifactNames[0])}?url`],
    ['extended raw query', `${resolve(configDirectory, artifactNames[0])}?raw&x=1`],
    ['lookalike filename', `${resolve(configDirectory, 'launch-indexing-policy.json.backup')}?raw`],
    ['outside config', `${resolve(repositoryRoot, 'launch-indexing-policy.json')}?raw`],
    ['literal traversal', `${resolve(configDirectory, 'nested')}/../launch-indexing-policy.json?raw`],
    ['other JSON artifact', `${resolve(configDirectory, 'other.json')}?raw`],
  ])('ignores %s', async (_label, id) => {
    const plugin = createLaunchRawArtifactPlugin(repositoryRoot)

    expect(await plugin.load(id)).toBeNull()
  })

  it('is registered only for the Nitro Rollup build', () => {
    const configSource = readFileSync(resolve(dirname(import.meta.filename), '../nuxt.config.ts'), 'utf8')
    const viteBlock = configSource.slice(configSource.indexOf('  vite:'), configSource.indexOf('  devServer:'))
    const nitroBlock = configSource.slice(configSource.indexOf('  nitro:'))

    expect(viteBlock).not.toContain('createLaunchRawArtifactPlugin')
    expect(nitroBlock).toContain('rollupConfig:')
    expect(nitroBlock).toContain('sourcemapExcludeSources: true')
    expect(nitroBlock).toContain('plugins: [createLaunchRawArtifactPlugin(')
  })
})
