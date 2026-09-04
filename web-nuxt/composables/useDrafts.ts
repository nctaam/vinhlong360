export const DRAFT_STORAGE_KEY = 'vl360_post_draft'
const LIFECYCLE_CLEAR_VERSION = 'v1'
const STORAGE_KEY = DRAFT_STORAGE_KEY

export function clearDraftStorage(storage: Pick<Storage, 'removeItem'>): void {
  storage.removeItem(STORAGE_KEY)
}

export function useDrafts() {
  function saveDraft(content: string, postType: string) {
    if (!import.meta.client) return
    if (!content.trim()) { clearDraft(); return }
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify({ content, postType, ts: Date.now() })) } catch {}
  }

  function loadDraft(): { content: string; postType: string } | null {
    if (!import.meta.client) return null
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (!raw) return null
      const d = JSON.parse(raw)
      if (!d || typeof d !== 'object' || typeof d.ts !== 'number') { clearDraft(); return null }
      if (Date.now() - d.ts > 7 * 24 * 3600 * 1000) { clearDraft(); return null }
      return { content: typeof d.content === 'string' ? d.content : '', postType: typeof d.postType === 'string' ? d.postType : 'share' }
    } catch { return null }
  }

  function clearDraft() {
    if (!import.meta.client) return
    try { clearDraftStorage(localStorage) } catch {}
  }

  return { saveDraft, loadDraft, clearDraft }
}
