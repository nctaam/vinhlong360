export const LIFECYCLE_CLEAR_INSTRUCTION_KEY = 'vl360_erasure_clear_instruction'
export const LIFECYCLE_CLEAR_APPLIED_KEY = 'vl360_erasure_clear_applied'

export function consumeLifecycleClearInstruction(instruction?: unknown): boolean {
  if (typeof window === 'undefined') return false
  let value: any = instruction
  if (!value) {
    try { value = JSON.parse(localStorage.getItem(LIFECYCLE_CLEAR_INSTRUCTION_KEY) || 'null') } catch { return false }
  }
  if (!value || typeof value.version !== 'string' || value.action !== 'clear' || !Array.isArray(value.keys)) return false
  const marker = `${LIFECYCLE_CLEAR_APPLIED_KEY}:${value.version}:${String(value.subject_hash || 'anonymous')}`
  if (localStorage.getItem(marker) === '1') return false
  const keys = value.keys.filter((key: unknown): key is string => typeof key === 'string')
  for (const key of keys) {
    try { localStorage.removeItem(key) } catch { /* storage may be unavailable */ }
    try { sessionStorage.removeItem(key) } catch { /* storage may be unavailable */ }
  }
  try { localStorage.setItem(marker, '1') } catch { /* best effort marker */ }
  try { localStorage.removeItem(LIFECYCLE_CLEAR_INSTRUCTION_KEY) } catch { /* noop */ }
  return true
}
