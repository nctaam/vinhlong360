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

export function useAdminEntityDuplicateCheck(options: UseAdminEntityDuplicateCheckOptions) {
  const { formName, editingEntity, authHeaders } = options
  const duplicates = ref<DuplicateEntityItem[]>([])
  let dupTimer: ReturnType<typeof setTimeout> | null = null

  function checkDuplicate() {
    if (editingEntity.value) return
    if (dupTimer) clearTimeout(dupTimer)
    const name = String(formName.value || '').trim()
    if (name.length < 3) {
      duplicates.value = []
      return
    }
    dupTimer = setTimeout(async () => {
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
    }, 400)
  }

  function clearDuplicates() {
    if (dupTimer) clearTimeout(dupTimer)
    duplicates.value = []
  }

  if (getCurrentInstance()) {
    onUnmounted(() => {
      if (dupTimer) clearTimeout(dupTimer)
    })
  }

  return {
    duplicates,
    checkDuplicate,
    clearDuplicates,
  }
}
