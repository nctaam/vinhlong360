import { createHash } from 'node:crypto'
import fs from 'node:fs'
import path from 'node:path'
import { DatabaseSync } from 'node:sqlite'
import { pathToFileURL } from 'node:url'

export const repoRoot = fs.existsSync(path.resolve('agent/data/vinhlong360.db'))
  ? path.resolve('.')
  : path.resolve('..')

export function resolveRepoPath(relativePath: string): string {
  return path.join(repoRoot, ...relativePath.split('/'))
}

export function openReadOnlyDatabase(
  relativePath = 'agent/data/vinhlong360.db',
): DatabaseSync {
  const dbPath = resolveRepoPath(relativePath)
  if (!fs.existsSync(dbPath)) {
    throw new Error(`Required read-only database is missing: ${dbPath}`)
  }
  const dbUri = pathToFileURL(dbPath)
  dbUri.searchParams.set('mode', 'ro')
  dbUri.searchParams.set('immutable', '1')
  return new DatabaseSync(dbUri.href, { readOnly: true })
}

export function readJsonArtifact<T>(relativePath: string): T {
  return JSON.parse(fs.readFileSync(resolveRepoPath(relativePath), 'utf8')) as T
}

export type RelationshipTriple = { from: string; to: string; type: string }

function relationshipKey(item: RelationshipTriple): string {
  return `${item.from}\u0000${item.to}\u0000${item.type}`
}

export function relationshipParitySummary(): {
  sqliteRows: number
  jsonRows: number
  duplicateJsonTriples: number
  sqliteOnlyTriples: number
  jsonOnlyTriples: number
} {
  const db = openReadOnlyDatabase()
  try {
    const sqlite = db.prepare(
      'SELECT from_id AS "from", to_id AS "to", type FROM relationships',
    ).all() as RelationshipTriple[]
    const json = readJsonArtifact<{ relationships: RelationshipTriple[] }>(
      'web/data.json',
    ).relationships
    const sqliteSet = new Set(sqlite.map(relationshipKey))
    const jsonSet = new Set(json.map(relationshipKey))
    return {
      sqliteRows: sqlite.length,
      jsonRows: json.length,
      duplicateJsonTriples: json.length - jsonSet.size,
      sqliteOnlyTriples: [...sqliteSet].filter(key => !jsonSet.has(key)).length,
      jsonOnlyTriples: [...jsonSet].filter(key => !sqliteSet.has(key)).length,
    }
  } finally {
    db.close()
  }
}

export function sha256File(relativePath: string): string {
  return createHash('sha256')
    .update(fs.readFileSync(resolveRepoPath(relativePath)))
    .digest('hex')
}
