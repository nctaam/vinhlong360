import { computed, ref } from 'vue'

type JourneyIntent = 'explore' | 'plan' | 'contact' | 'contribute' | 'verify'

interface JourneyThreadStorage {
  getItem(key: string): string | null
  setItem(key: string, value: string): void
  removeItem(key: string): void
}

interface JourneyThreadSearchViewState {
  restoreBackStack(historyState?: unknown): unknown
}

export interface JourneyThreadSnapshot {
  version: 1
  ownerScope: string
  intent: JourneyIntent
  returnPath: string
  currentPath?: string
  recentItemIds: string[]
  savedItemIds: string[]
  createdAt: number
  updatedAt: number
  expiresAt: number
}

export interface JourneyThreadSnapshotInput {
  intent: JourneyIntent
  returnPath: string
  currentPath?: string
  recentItemIds?: string[]
  savedItemIds?: string[]
}

interface JourneyThreadOptions {
  storage?: JourneyThreadStorage | null
  ownerScope?: string | (() => string)
  now?: () => number
  ttlMs?: number
  searchViewState?: JourneyThreadSearchViewState
  storageKey?: string
}

const DEFAULT_THREAD_TTL_MS = 30 * 60 * 1_000
const MAX_CONTEXT_IDS = 12
const SAFE_CONTEXT_ID = /^[a-zA-Z0-9][a-zA-Z0-9:_-]{0,127}$/

function sessionStorageOrNull(): JourneyThreadStorage | null {
  if (typeof window === 'undefined') return null
  try { return window.sessionStorage } catch { return null }
}

function ownerFingerprint(value: string) {
  let hash = 2166136261
  for (const character of value) {
    hash ^= character.charCodeAt(0)
    hash = Math.imul(hash, 16777619)
  }
  return `scope-${(hash >>> 0).toString(36)}`
}

function safeLocalPath(value: unknown): string {
  if (typeof value !== 'string' || !value.startsWith('/') || value.startsWith('//')) return ''
  try {
    const url = new URL(value, 'https://vinhlong360.local')
    return `${url.pathname}${url.search}${url.hash}`.slice(0, 1_024)
  } catch {
    return ''
  }
}

function safeIds(value: unknown) {
  if (!Array.isArray(value)) return []
  const ids = value
    .filter((item): item is string => typeof item === 'string' && SAFE_CONTEXT_ID.test(item))
    .slice(0, MAX_CONTEXT_IDS)
  return [...new Set(ids)]
}

function isJourneyIntent(value: unknown): value is JourneyIntent {
  return value === 'explore' || value === 'plan' || value === 'contact' || value === 'contribute' || value === 'verify'
}

export function useJourneyThread(options: JourneyThreadOptions = {}) {
  const storage = options.storage === undefined ? sessionStorageOrNull() : options.storage
  const now = options.now || Date.now
  const ttlMs = Math.min(Math.max(Math.floor(options.ttlMs ?? DEFAULT_THREAD_TTL_MS), 1), 24 * 60 * 60 * 1_000)
  const storageKey = String(options.storageKey || 'vl360:journey-thread:v1').replace(/[^a-z0-9:_-]/gi, '').slice(0, 64) || 'vl360:journey-thread:v1'
  const current = ref<JourneyThreadSnapshot | null>(null)

  function currentOwnerScope() {
    const raw = typeof options.ownerScope === 'function' ? options.ownerScope() : options.ownerScope
    return ownerFingerprint(String(raw || 'guest'))
  }

  function clear() {
    current.value = null
    try { storage?.removeItem(storageKey) } catch {}
  }

  function normalize(value: unknown): JourneyThreadSnapshot | null {
    if (!value || typeof value !== 'object') return null
    const input = value as Partial<JourneyThreadSnapshot>
    const ownerScope = currentOwnerScope()
    const returnPath = safeLocalPath(input.returnPath)
    const createdAt = Number(input.createdAt)
    const updatedAt = Number(input.updatedAt)
    const expiresAt = Number(input.expiresAt)
    if (input.version !== 1 || input.ownerScope !== ownerScope || !isJourneyIntent(input.intent) || !returnPath) return null
    if (![createdAt, updatedAt, expiresAt].every(Number.isFinite) || expiresAt <= now()) return null
    return {
      version: 1,
      ownerScope,
      intent: input.intent,
      returnPath,
      ...(safeLocalPath(input.currentPath) ? { currentPath: safeLocalPath(input.currentPath) } : {}),
      recentItemIds: safeIds(input.recentItemIds),
      savedItemIds: safeIds(input.savedItemIds),
      createdAt,
      updatedAt,
      expiresAt,
    }
  }

  function read() {
    let parsed: unknown = null
    try {
      const raw = storage?.getItem(storageKey)
      parsed = raw ? JSON.parse(raw) : null
    } catch {}
    const normalized = normalize(parsed)
    if (!normalized) {
      if (parsed) clear()
      return null
    }
    current.value = normalized
    return normalized
  }

  function persist(value: JourneyThreadSnapshot) {
    current.value = value
    try { storage?.setItem(storageKey, JSON.stringify(value)) } catch {}
    return value
  }

  function snapshot(input?: JourneyThreadSnapshotInput): JourneyThreadSnapshot | null {
    if (!input) return read() || current.value
    const returnPath = safeLocalPath(input.returnPath)
    if (!returnPath || !isJourneyIntent(input.intent)) return null
    const timestamp = now()
    const previous = read()
    const ownerScope = currentOwnerScope()
    return persist({
      version: 1,
      ownerScope,
      intent: input.intent,
      returnPath,
      ...(safeLocalPath(input.currentPath) ? { currentPath: safeLocalPath(input.currentPath) } : {}),
      recentItemIds: safeIds(input.recentItemIds),
      savedItemIds: safeIds(input.savedItemIds),
      createdAt: previous?.createdAt || timestamp,
      updatedAt: timestamp,
      expiresAt: timestamp + ttlMs,
    })
  }

  function pushIntent(intent: JourneyIntent, input: { currentPath?: string; returnPath?: string } = {}) {
    if (!isJourneyIntent(intent)) return null
    const previous = read() || current.value
    const returnPath = safeLocalPath(input.returnPath) || previous?.returnPath || safeLocalPath(input.currentPath)
    if (!returnPath) return null
    return snapshot({
      intent,
      returnPath,
      currentPath: safeLocalPath(input.currentPath) || previous?.currentPath,
      recentItemIds: previous?.recentItemIds,
      savedItemIds: previous?.savedItemIds,
    })
  }

  function restore() {
    const restored = read()
    if (!restored) return null
    if (restored.returnPath.startsWith('/tim-kiem')) options.searchViewState?.restoreBackStack()
    return restored
  }

  read()

  return {
    snapshot,
    pushIntent,
    restore,
    clear,
    returnPath: computed(() => current.value?.returnPath || ''),
  }
}
