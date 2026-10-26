import { ref, getCurrentInstance, onUnmounted, type Ref } from 'vue'

export interface DuplicateEntityItem {
  id: string
  name: string
  type: string
}

export interface UseAdminEntityDuplicateCheckOptions {
  formName: Ref<string>
  editingEntity: Ref<unknown>
  authHeaders: () => Record<string, string>
}

const WHITESPACE_RE = /\s+/g
const MIN_DUPLICATE_NAME_LEN = 3
const DUPLICATE_DEBOUNCE_MS = 400

export function useAdminEntityDuplicateCheck(options: UseAdminEntityDuplicateCheckOptions) {
  const { formName, editingEntity, authHeaders } = options
  const duplicates = ref<DuplicateEntityItem[]>([])
  let dupTimer: ReturnType<typeof setTimeout> | null = null

  function clearTimer() {
    if (dupTimer !== null) {
      clearTimeout(dupTimer)
      dupTimer = null
    }
  }

  function checkDuplicate() {
    if (editingEntity.value) return
    clearTimer()
    const name = String(formName.value || '').replace(WHITESPACE_RE, ' ').trim()
    if (name.length < MIN_DUPLICATE_NAME_LEN) {
      duplicates.value = []
      return
    }
    dupTimer = setTimeout(async () => {
      dupTimer = null
      try {
        const res = await $fetch<{ duplicates: DuplicateEntityItem[] }>(
          '/admin-api/entities/check-duplicate?name=' + encodeURIComponent(name),
          { headers: authHeaders() },
        )
        duplicates.value = res.duplicates || []
      } catch (err) {
        console.error('[entities] duplicate check failed', err)
        duplicates.value = []
      }
    }, DUPLICATE_DEBOUNCE_MS)
  }

  function clearDuplicates() {
    clearTimer()
    duplicates.value = []
  }

  if (getCurrentInstance()) {
    onUnmounted(clearTimer)
  }

  return {
    duplicates,
    checkDuplicate,
    clearDuplicates,
  }
}
