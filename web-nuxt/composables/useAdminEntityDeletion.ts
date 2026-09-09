import { ref, computed, type Ref } from 'vue'
import type { Entity } from '~/types'
import { getErrorDetail } from '~/composables/useFetchError'

export interface UseAdminEntityDeletionOptions {
  selected: Ref<Set<string>>
  entities: Ref<Entity[]>
  authHeaders: () => Record<string, string>
  showToast: (message: string, type?: 'info' | 'success' | 'warning' | 'error') => void
  confirmDialog: (message: string, options?: { title?: string; confirmText?: string; danger?: boolean }) => Promise<boolean>
  fetchEntities: () => Promise<void>
}

export function useAdminEntityDeletion(options: UseAdminEntityDeletionOptions) {
  const { selected, entities, authHeaders, showToast, confirmDialog, fetchEntities } = options

  const acting = ref<string | null>(null)
  const bulkBusy = ref(false)

  function toggleSel(id: string) {
    const s = new Set(selected.value)
    s.has(id) ? s.delete(id) : s.add(id)
    selected.value = s
  }

  const allSelected = computed(() => entities.value.length > 0 && entities.value.every(e => selected.value.has(e.id)))

  function toggleAll() {
    selected.value = allSelected.value ? new Set() : new Set(entities.value.map(e => e.id))
  }

  async function executeBulkDelete(ids: string[]) {
    bulkBusy.value = true
    try {
      const r = await $fetch<Record<string, unknown>>('/admin-api/entities/bulk-delete', {
        method: 'POST',
        headers: authHeaders(),
        body: ids,
      })
      const deleted = Number(r.count) || 0
      showToast(`Đã xóa ${deleted}/${ids.length} entity`, deleted === ids.length ? 'success' : 'warning')
      selected.value = new Set()
      await fetchEntities()
    } catch (e: unknown) {
      showToast(getErrorDetail(e, 'Xóa hàng loạt lỗi'), 'error')
    }
    bulkBusy.value = false
  }

  async function bulkDelete() {
    if (bulkBusy.value) return
    const ids = [...selected.value]
    if (!ids.length || !await confirmDialog(`Xóa ${ids.length} entity đã chọn?`, { danger: true })) return
    await executeBulkDelete(ids)
  }

  async function deleteEntity(id: string) {
    if (acting.value) return
    if (!await confirmDialog(`Xóa entity "${id}"?`, { danger: true })) return
    acting.value = id
    try {
      await $fetch(`/admin-api/entities/${id}`, { method: 'DELETE', headers: authHeaders() })
      showToast('Đã xóa entity', 'success')
      acting.value = null
      await fetchEntities()
    } catch (e: unknown) {
      showToast(getErrorDetail(e, 'Lỗi khi xóa entity'), 'error')
      acting.value = null
    }
  }

  return {
    acting,
    bulkBusy,
    toggleSel,
    allSelected,
    toggleAll,
    executeBulkDelete,
    bulkDelete,
    deleteEntity,
  }
}
