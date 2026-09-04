export interface UserCollection {
  id: string
  name: string
  description: string
  is_public: boolean
  item_count: number
  created_at: string
}

/**
 * useCollections — CRUD for the current user's themed post collections.
 * Wraps `/me/collections*` (agent/social.py:2791+). `authHeaders()` already
 * carries the CSRF token (see useAuth.ts) — no manual x-csrf-token header needed.
 */
export function useCollections() {
  const collections = useState<UserCollection[]>('user-collections', () => [])
  const loading = ref(false)
  const { authFetch } = useAuth()
  const { show: showToast } = useToast()

  async function fetchCollections() {
    loading.value = true
    try {
      const res = await authFetch<{ collections: UserCollection[] }>('/api/me/collections')
      collections.value = res.collections || []
    } catch {
      showToast('Không thể tải danh sách', 'error')
    } finally {
      loading.value = false
    }
  }

  async function createCollection(name: string, description = '', isPublic = true) {
    try {
      const res = await authFetch<{ collection: UserCollection }>('/api/me/collections', {
        method: 'POST',
        body: { name, description, is_public: isPublic },
      })
      if (res.collection) collections.value.unshift({ ...res.collection, item_count: res.collection.item_count ?? 0 })
      return res.collection
    } catch (e: unknown) {
      showToast(extractErrorMessage(e, 'Không thể tạo danh sách'), 'error')
      throw e
    }
  }

  async function deleteCollection(id: string) {
    try {
      await authFetch(`/api/me/collections/${encodeURIComponent(id)}`, {
        method: 'DELETE',
      })
      collections.value = collections.value.filter(c => c.id !== id)
    } catch (e: unknown) {
      showToast(extractErrorMessage(e, 'Không thể xoá danh sách'), 'error')
      throw e
    }
  }

  async function addToCollection(collectionId: string, postId: string) {
    try {
      await authFetch(`/api/me/collections/${encodeURIComponent(collectionId)}/items`, {
        method: 'POST',
        query: { post_id: postId },
      })
      const c = collections.value.find(c => c.id === collectionId)
      if (c) c.item_count = (c.item_count || 0) + 1
    } catch (e: unknown) {
      showToast(extractErrorMessage(e, 'Không thể thêm vào danh sách'), 'error')
      throw e
    }
  }

  async function removeFromCollection(collectionId: string, postId: string) {
    try {
      await authFetch(`/api/me/collections/${encodeURIComponent(collectionId)}/items/${encodeURIComponent(postId)}`, {
        method: 'DELETE',
      })
      const c = collections.value.find(c => c.id === collectionId)
      if (c && c.item_count > 0) c.item_count--
    } catch (e: unknown) {
      showToast(extractErrorMessage(e, 'Không thể xoá khỏi danh sách'), 'error')
      throw e
    }
  }

  return { collections, loading, fetchCollections, createCollection, deleteCollection, addToCollection, removeFromCollection }
}
