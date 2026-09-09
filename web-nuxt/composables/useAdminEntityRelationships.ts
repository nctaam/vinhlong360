import { ref, type Ref } from 'vue'
import { getErrorDetail } from '~/composables/useFetchError'

export interface AdminRelationship {
  from_id: string
  to_id: string
  type: string
  target_name?: string
  source_name?: string
}

export interface UseAdminEntityRelationshipsOptions {
  formId: Ref<string>
  editingEntity: Ref<unknown>
  authHeaders: () => Record<string, string>
  showToast: (msg: string, type?: 'success' | 'warning' | 'error' | 'info') => void
  confirmDialog: (msg: string, opts?: { danger?: boolean }) => Promise<boolean>
}

export function useAdminEntityRelationships(options: UseAdminEntityRelationshipsOptions) {
  const { formId, editingEntity, authHeaders, showToast, confirmDialog } = options

  const relTypes = ['related_to', 'near', 'produced_in', 'located_in', 'associated_with', 'part_of', 'hosts']
  const rels = ref<AdminRelationship[]>([])
  const newRel = ref<{ to_id: string; type: string }>({ to_id: '', type: 'related_to' })

  async function fetchRels(id: string) {
    rels.value = []
    try {
      const r = await $fetch<{ relationships?: AdminRelationship[] }>('/api/entities/' + id + '/relationships?limit=100')
      rels.value = r.relationships || []
    } catch {
      showToast('Không tải được quan hệ', 'error')
    }
  }

  async function addRel() {
    const to = newRel.value.to_id.trim()
    if (!to || !editingEntity.value) return
    try {
      await $fetch('/admin-api/relationships', {
        method: 'POST',
        headers: authHeaders(),
        body: { from_id: formId.value, to_id: to, type: newRel.value.type },
      })
      newRel.value.to_id = ''
      await fetchRels(formId.value)
      showToast('Đã thêm quan hệ', 'success')
    } catch (e: unknown) {
      showToast(getErrorDetail(e, 'Thêm quan hệ lỗi (id đích tồn tại?)'), 'error')
    }
  }

  async function removeRel(r: Pick<AdminRelationship, 'to_id' | 'type'> & Partial<AdminRelationship>) {
    if (!await confirmDialog('Xóa quan hệ "' + r.type + '" → ' + (r.target_name || r.to_id) + '?', { danger: true })) return
    const params = new URLSearchParams({ from_id: r.from_id || formId.value, to_id: r.to_id, type: r.type })
    try {
      await $fetch('/admin-api/relationships?' + params, { method: 'DELETE', headers: authHeaders() })
      await fetchRels(formId.value)
    } catch {
      showToast('Xóa quan hệ lỗi', 'error')
    }
  }

  const bulkRelType = ref('related_to')
  const bulkRelIds = ref('')
  const bulkRelSaving = ref(false)

  async function addBulkRels() {
    if (!editingEntity.value || !bulkRelIds.value.trim()) return
    const pairs = bulkRelIds.value
      .split('\n')
      .map(l => l.trim())
      .filter(Boolean)
      .map(id => ({ to_id: id, type: bulkRelType.value }))
    if (!pairs.length) return
    bulkRelSaving.value = true
    try {
      const r = await $fetch<{ added: number; errors: unknown[] }>('/admin-api/relationships/bulk', {
        method: 'POST',
        headers: authHeaders(),
        body: { from_id: formId.value, pairs },
      })
      showToast('Đã thêm ' + r.added + ' quan hệ' + (r.errors?.length ? (', ' + r.errors.length + ' lỗi') : ''), r.errors?.length ? 'warning' : 'success')
      if (!r.errors?.length) bulkRelIds.value = ''
      await fetchRels(formId.value)
    } catch {
      showToast('Thêm hàng loạt lỗi', 'error')
    }
    bulkRelSaving.value = false
  }

  function resetRels() {
    newRel.value = { to_id: '', type: 'related_to' }
    bulkRelType.value = 'related_to'
    bulkRelIds.value = ''
  }

  return {
    relTypes,
    rels,
    newRel,
    bulkRelType,
    bulkRelIds,
    bulkRelSaving,
    fetchRels,
    addRel,
    removeRel,
    addBulkRels,
    resetRels,
  }
}
