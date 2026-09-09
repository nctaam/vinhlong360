import { ref, computed, getCurrentInstance } from 'vue'

export interface UseUserProfileCollectionsOptions {
  confirmDialog?: (message: string, options?: { title?: string; confirmText?: string; danger?: boolean }) => Promise<boolean>
}

export function useUserProfileCollections(options: UseUserProfileCollectionsOptions = {}) {
  const confirmDialog = options.confirmDialog ?? (() => Promise.resolve(true))

  const {
    collections: userCollections,
    loading: collectionsLoading,
    fetchCollections,
    createCollection,
    deleteCollection,
  } = useCollections()

  const collectionsCount = computed(() => userCollections.value.length)
  const showCreateCollection = ref(false)
  const newCollectionName = ref('')
  const newCollectionDesc = ref('')
  const creatingCollection = ref(false)
  const createCollectionModalEl = ref<HTMLElement | null>(null)

  if (getCurrentInstance()) {
    useModalA11y(showCreateCollection, createCollectionModalEl, {
      onClose: () => { showCreateCollection.value = false },
    })
  }

  function closeCreateCollection() {
    showCreateCollection.value = false
  }

  async function handleCreateCollection() {
    if (!newCollectionName.value.trim() || creatingCollection.value) return
    creatingCollection.value = true
    try {
      await createCollection(newCollectionName.value.trim(), newCollectionDesc.value.trim())
      showCreateCollection.value = false
      newCollectionName.value = ''
      newCollectionDesc.value = ''
    } catch {
      /* toast đã hiển thị trong composable */
    } finally {
      creatingCollection.value = false
    }
  }

  async function handleDeleteCollection(id: string, name: string) {
    const ok = await confirmDialog(
      `Xoá danh sách "${name}"? Hành động không thể hoàn tác.`,
      { title: 'Xoá danh sách?', confirmText: 'Xoá', danger: true },
    )
    if (!ok) return
    try {
      await deleteCollection(id)
    } catch {
      /* toast đã hiển thị trong composable */
    }
  }

  return {
    userCollections,
    collectionsLoading,
    collectionsCount,
    showCreateCollection,
    newCollectionName,
    newCollectionDesc,
    creatingCollection,
    createCollectionModalEl,
    closeCreateCollection,
    handleCreateCollection,
    handleDeleteCollection,
    fetchCollections,
  }
}
