const STORAGE_KEY = 'vl360_post_draft'

export function useDrafts() {
  function saveDraft(content: string, postType: string) {
    if (typeof localStorage === 'undefined') return
    if (!content.trim()) { clearDraft(); return }
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ content, postType, ts: Date.now() }))
  }

  function loadDraft(): { content: string; postType: string } | null {
    if (typeof localStorage === 'undefined') return null
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (!raw) return null
      const d = JSON.parse(raw)
      if (Date.now() - d.ts > 7 * 24 * 3600 * 1000) { clearDraft(); return null }
      return { content: d.content || '', postType: d.postType || 'share' }
    } catch { return null }
  }

  function clearDraft() {
    if (typeof localStorage !== 'undefined') localStorage.removeItem(STORAGE_KEY)
  }

  return { saveDraft, loadDraft, clearDraft }
}
