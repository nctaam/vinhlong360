import { readFile } from 'node:fs/promises'
import { resolve } from 'node:path'

const RAW_QUERY = '?raw'
const LAUNCH_ARTIFACTS = [
  'launch-indexing-policy.json',
  'ai-disclosure.json',
] as const

interface LaunchRawArtifactLoadResult {
  readonly code: string
  readonly map: {
    readonly version: 3
    readonly sources: string[]
    readonly sourcesContent: string[]
    readonly names: string[]
    readonly mappings: string
  }
}

interface LaunchRawArtifactPlugin {
  readonly name: string
  load(id: string): Promise<LaunchRawArtifactLoadResult | null>
}

function normalizeSeparators(path: string): string {
  return path.replaceAll('\\', '/')
}

export function createLaunchRawArtifactPlugin(repositoryRoot: string): LaunchRawArtifactPlugin {
  const artifactPaths = new Map<string, string>(LAUNCH_ARTIFACTS.map((artifactName) => {
    const artifactPath = resolve(repositoryRoot, 'config', artifactName)
    return [`${normalizeSeparators(artifactPath)}${RAW_QUERY}`, artifactPath] as const
  }))

  return {
    name: 'launch-raw-artifact',
    async load(id) {
      const artifactPath = artifactPaths.get(normalizeSeparators(id))
      if (!artifactPath) return null

      const source = await readFile(artifactPath, 'utf8')
      return {
        code: `export default ${JSON.stringify(source)}`,
        map: {
          version: 3,
          sources: [artifactPath],
          sourcesContent: [source],
          names: [],
          mappings: '',
        },
      }
    },
  }
}
