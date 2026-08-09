interface BudgetStorage {
  getItem(key: string): string | null
  setItem(key: string, value: string): void
  removeItem(key: string): void
}

interface AttentionBudgetOptions {
  sessionStorage?: BudgetStorage | null
  persistentStorage?: BudgetStorage | null
  maxSuggestions?: number
  dismissalTtlMs?: number
  now?: () => number
  storageNamespace?: string
}

const DEFAULT_MAX_SUGGESTIONS = 3
const DEFAULT_DISMISSAL_TTL_MS = 30 * 24 * 60 * 60 * 1_000
const MAX_DISMISSALS = 50
const SAFE_SUGGESTION_ID = /^[a-z0-9][a-z0-9:_-]{0,63}$/

function browserStorage(name: 'sessionStorage' | 'localStorage'): BudgetStorage | null {
  if (typeof window === 'undefined') return null
  try { return window[name] } catch { return null }
}

function safeParse(raw: string | null): unknown {
  if (!raw) return null
  try { return JSON.parse(raw) } catch { return null }
}

function safeSuggestionId(value: unknown): string | null {
  if (typeof value !== 'string') return null
  const normalized = value.trim().toLowerCase()
  return SAFE_SUGGESTION_ID.test(normalized) ? normalized : null
}

export function useAttentionBudget(options: AttentionBudgetOptions = {}) {
  const session = options.sessionStorage === undefined ? browserStorage('sessionStorage') : options.sessionStorage
  const persistent = options.persistentStorage === undefined ? browserStorage('localStorage') : options.persistentStorage
  const namespace = String(options.storageNamespace || 'vl360:attention:v1').replace(/[^a-z0-9:_-]/gi, '').slice(0, 48) || 'vl360:attention:v1'
  const sessionKey = `${namespace}:session`
  const dismissalKey = `${namespace}:dismissed`
  const maxSuggestions = Math.min(Math.max(Math.floor(options.maxSuggestions ?? DEFAULT_MAX_SUGGESTIONS), 1), 10)
  const dismissalTtlMs = Math.min(Math.max(Math.floor(options.dismissalTtlMs ?? DEFAULT_DISMISSAL_TTL_MS), 1), DEFAULT_DISMISSAL_TTL_MS)
  const now = options.now || Date.now

  function readShown() {
    const parsed = safeParse(session?.getItem(sessionKey) || null)
    const shown = parsed && typeof parsed === 'object' && Array.isArray((parsed as { shown?: unknown }).shown)
      ? (parsed as { shown: unknown[] }).shown.map(safeSuggestionId).filter((value): value is string => !!value)
      : []
    return [...new Set(shown)].slice(0, maxSuggestions)
  }

  function writeShown(shown: string[]) {
    try { session?.setItem(sessionKey, JSON.stringify({ shown: shown.slice(0, maxSuggestions) })) } catch {}
  }

  function readDismissals() {
    const parsed = safeParse(persistent?.getItem(dismissalKey) || null)
    const source = parsed && typeof parsed === 'object' && !Array.isArray(parsed)
      ? (parsed as Record<string, unknown>)
      : {}
    const current = now()
    const active: Record<string, number> = {}
    for (const [rawId, rawExpiry] of Object.entries(source)) {
      const id = safeSuggestionId(rawId)
      const expiry = Number(rawExpiry)
      if (id && Number.isFinite(expiry) && expiry > current) active[id] = expiry
      if (Object.keys(active).length === MAX_DISMISSALS) break
    }
    try {
      if (Object.keys(active).length) persistent?.setItem(dismissalKey, JSON.stringify(active))
      else persistent?.removeItem(dismissalKey)
    } catch {}
    return active
  }

  function canSuggest(value: string) {
    const id = safeSuggestionId(value)
    if (!id || readDismissals()[id]) return false
    const shown = readShown()
    if (shown.includes(id)) return true
    if (shown.length >= maxSuggestions) return false
    shown.push(id)
    writeShown(shown)
    return true
  }

  function dismiss(value: string) {
    const id = safeSuggestionId(value)
    if (!id) return false
    const dismissals = readDismissals()
    dismissals[id] = now() + dismissalTtlMs
    const bounded = Object.fromEntries(Object.entries(dismissals).sort((left, right) => right[1] - left[1]).slice(0, MAX_DISMISSALS))
    try { persistent?.setItem(dismissalKey, JSON.stringify(bounded)) } catch { return false }
    return true
  }

  function resetSession() {
    try { session?.removeItem(sessionKey) } catch {}
  }

  return { canSuggest, dismiss, resetSession }
}
