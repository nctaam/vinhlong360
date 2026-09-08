import type { Ref } from 'vue'
import type { Post } from '~/types'

export interface CommunityPostInteractionsOptions {
  posts: Ref<Post[]>
  bookmarks: Ref<Post[]>
  searchResults: Ref<Post[]>
  sessionBookmarked: Ref<boolean>
}

export function useCommunityPostInteractions(options: CommunityPostInteractionsOptions) {
  const { posts, bookmarks, searchResults, sessionBookmarked } = options
  const { toggleLike: _like, toggleBookmark: _bookmark, deletePost: _delete } = usePostActions()

  function getCopies(postId: string) {
    return [...posts.value, ...bookmarks.value, ...searchResults.value].filter(p => p.id === postId)
  }

  function toggleLike(postId: string) {
    _like(postId, getCopies(postId))
  }

  function toggleBookmark(postId: string) {
    _bookmark(postId, getCopies(postId), () => {
      if (!sessionBookmarked.value) sessionBookmarked.value = true
    })
  }

  function deletePost(postId: string) {
    _delete(postId, () => {
      posts.value = posts.value.filter(p => p.id !== postId)
      bookmarks.value = bookmarks.value.filter(p => p.id !== postId)
      searchResults.value = searchResults.value.filter(p => p.id !== postId)
    })
  }

  return {
    _copies: getCopies,
    toggleLike,
    toggleBookmark,
    deletePost,
  }
}
