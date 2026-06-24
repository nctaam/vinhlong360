import type { Ref } from 'vue'

// @-mention dùng chung (composer cong-dong + ô bình luận bai-viet).
// Quản lý dropdown gợi ý khi gõ "@..." và chèn mention vào `text`.
export interface MentionItem { type: 'user' | 'entity'; id: string; label: string; sub?: string }

export function useMentionAutocomplete(
  text: Ref<string>,
  inputEl: Ref<HTMLTextAreaElement | HTMLInputElement | null>,
) {
  const mentionResults = ref<MentionItem[]>([])
  const mentionOpen = ref(false)
  const mentionActive = ref(0)
  const mentionAt = ref(-1)        // vị trí ký tự '@' trong text
  const mentionQueryLen = ref(0)   // độ dài chuỗi truy vấn sau '@'
  const selectedMentions = ref<MentionItem[]>([])
  let timer: ReturnType<typeof setTimeout> | null = null

  function onInput(e: Event) {
    const el = e.target as HTMLInputElement | HTMLTextAreaElement
    const cursor = el.selectionStart || 0
    const before = text.value.slice(0, cursor)
    // @ + token đơn (không dấu cách) ngay trước con trỏ, sau khoảng-trắng/đầu dòng
    const m = before.match(/(?:^|\s)@([\p{L}\p{N}_]{1,30})$/u)
    if (m) {
      mentionAt.value = cursor - m[1]!.length - 1
      mentionQueryLen.value = m[1]!.length
      if (timer) clearTimeout(timer)
      const q = m[1]!
      timer = setTimeout(() => search(q), 180)
    } else {
      mentionOpen.value = false
    }
  }

  async function search(q: string) {
    try {
      const res = await $fetch<{ results: MentionItem[] }>(`/api/mentions?q=${encodeURIComponent(q)}`)
      mentionResults.value = res.results || []
      mentionActive.value = 0
      mentionOpen.value = mentionResults.value.length > 0
    } catch { mentionOpen.value = false }
  }

  function pick(m: MentionItem) {
    const at = mentionAt.value
    const before = text.value.slice(0, at)
    const after = text.value.slice(at + 1 + mentionQueryLen.value)
    text.value = `${before}@${m.label} ${after}`
    if (!selectedMentions.value.some(x => x.type === m.type && x.id === m.id)) {
      selectedMentions.value.push({ type: m.type, id: m.id, label: m.label })
    }
    mentionOpen.value = false
    nextTick(() => inputEl.value?.focus())
  }

  // Trả true nếu phím được tiêu thụ (menu đang mở) → caller bỏ qua hành vi mặc định.
  function onKeydown(e: KeyboardEvent) {
    if (!mentionOpen.value || !mentionResults.value.length) return false
    if (e.key === 'ArrowDown') { e.preventDefault(); mentionActive.value = (mentionActive.value + 1) % mentionResults.value.length; return true }
    if (e.key === 'ArrowUp') { e.preventDefault(); mentionActive.value = (mentionActive.value - 1 + mentionResults.value.length) % mentionResults.value.length; return true }
    if (e.key === 'Enter') { e.preventDefault(); const item = mentionResults.value[mentionActive.value]; if (item) pick(item); return true }
    if (e.key === 'Escape') { mentionOpen.value = false; return true }
    return false
  }

  function reset() { selectedMentions.value = []; mentionOpen.value = false; mentionResults.value = [] }

  // Chỉ giữ mention còn xuất hiện trong text (user có thể đã xoá tay).
  function activeMentions(): MentionItem[] {
    return selectedMentions.value.filter(m => text.value.includes(`@${m.label}`))
  }

  return { mentionResults, mentionOpen, mentionActive, selectedMentions, onInput, pick, onKeydown, reset, activeMentions }
}
