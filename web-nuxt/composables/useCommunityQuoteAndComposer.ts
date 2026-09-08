import { ref, nextTick, type Ref } from 'vue'
import type { Post } from '~/types'

export interface CommunityQuoteAndComposerOptions {
  posts: Ref<Post[]>
  isLoggedIn: Ref<boolean>
  openAuth: (cb?: () => void) => void
  authHeaders: () => Record<string, string>
  activeTab: Ref<string>
  schedulePost: Ref<boolean>
  scheduledAt: Ref<string>
  onMentionInput: (e: Event) => void
  onMentionKeydownComposer: (e: KeyboardEvent) => boolean
  submitPost: () => void
  closeMention: () => void
  mentionOpen: Ref<boolean>
  firstQueryValue: (value: unknown) => string
  route: { query: Record<string, any>; hash: string }
  quotingPost?: Ref<Record<string, any> | null>
}

export function useCommunityQuoteAndComposer(options: CommunityQuoteAndComposerOptions) {
  const {
    posts,
    isLoggedIn,
    openAuth,
    authHeaders,
    activeTab,
    schedulePost,
    scheduledAt,
    onMentionInput,
    onMentionKeydownComposer,
    submitPost,
    closeMention,
    mentionOpen,
    firstQueryValue,
    route,
  } = options

  const composeEl = ref<HTMLElement | null>(null)
  const composeInputEl = ref<HTMLTextAreaElement | null>(null)
  const quotingPost = options.quotingPost || ref<Record<string, any> | null>(null)

  function focusComposer() {
    const prefersReduced = typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    composeEl.value?.scrollIntoView({ behavior: prefersReduced ? 'auto' : 'smooth', block: 'center' })
    nextTick(() => composeInputEl.value?.focus())
  }

  async function startQuote(postId: string) {
    if (!isLoggedIn.value) { openAuth(() => startQuote(postId)); return }
    let p: any = posts.value.find((x: any) => x.id === postId)
    if (!p) {
      try {
        const r = await $fetch<any>(`/api/posts/${encodePathId(postId)}`, { headers: authHeaders() })
        p = r?.post
      } catch { /* post may be deleted */ }
    }
    quotingPost.value = p || { id: postId, content: '(Bài viết không khả dụng)' }
    schedulePost.value = false
    scheduledAt.value = ''
    activeTab.value = 'latest'
    focusComposer()
  }

  function cancelQuote() {
    quotingPost.value = null
  }

  function autoGrow(e: Event) {
    const el = e.target as HTMLTextAreaElement
    el.style.height = 'auto'
    el.style.height = el.scrollHeight + 'px'
  }

  function onComposerKeydown(e: KeyboardEvent) {
    if (onMentionKeydownComposer(e)) return
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') { e.preventDefault(); submitPost() }
  }

  function onComposerInput(e: Event) {
    autoGrow(e)
    onMentionInput(e)
  }

  function focusComposerFromRoute() {
    const composeIntent = firstQueryValue(route.query.compose).trim().toLowerCase()
    if (composeIntent !== 'draft' && route.hash !== '#compose') return
    nextTick(() => {
      composeEl.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      composeInputEl.value?.focus()
    })
  }

  function onClickOutsideMention(e: MouseEvent) {
    if (mentionOpen.value && !(e.target as HTMLElement)?.closest('.compose-mention-wrap')) {
      closeMention()
    }
  }

  return {
    composeEl,
    composeInputEl,
    quotingPost,
    focusComposer,
    startQuote,
    cancelQuote,
    autoGrow,
    onComposerKeydown,
    onComposerInput,
    focusComposerFromRoute,
    onClickOutsideMention,
  }
}
