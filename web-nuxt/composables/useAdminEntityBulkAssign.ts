import { ref, computed, type Ref } from 'vue'
import type { Entity } from '~/types'
import type { AdminKind } from '~/utils/adminKinds'

export interface BulkColumnDef {
  key: string
  label: string
  widget: 'text' | 'number' | 'select' | 'bool'
  options?: (string | number)[]
}

export const UNIVERSAL_BULK: BulkColumnDef[] = [
  { key: 'address', label: 'Địa chỉ', widget: 'text' },
  { key: 'phone', label: 'Điện thoại', widget: 'text' },
  { key: 'website', label: 'Website', widget: 'text' },
  { key: 'hours', label: 'Giờ mở cửa', widget: 'text' },
  { key: 'price_range', label: 'Khoảng giá', widget: 'text' },
  { key: 'sub_category', label: 'Phân loại', widget: 'text' },
  { key: 'best_time', label: 'Thời điểm đẹp', widget: 'text' },
  { key: 'highlight', label: 'Điểm nhấn', widget: 'text' },
]

export interface UseAdminEntityBulkAssignOptions {
  currentKind: Ref<AdminKind | null>
  selected: Ref<Set<string>>
  entities: Ref<Entity[]>
  authHeaders: () => Record<string, string>
  showToast: (msg: string, type?: 'success' | 'warning' | 'error' | 'info') => void
}

export function useAdminEntityBulkAssign(options: UseAdminEntityBulkAssignOptions) {
  const { currentKind, selected, entities, authHeaders, showToast } = options

  const bulkField = ref('')
  const bulkValue = ref('')
  const bulkAssignBusy = ref(false)
  const bulkProgress = ref('')

  const bulkFields = computed(() => {
    if (!currentKind.value) return []
    const kindKeys = new Set(currentKind.value.columns.map(c => c.key))
    return [...currentKind.value.columns, ...UNIVERSAL_BULK.filter(u => !kindKeys.has(u.key))]
  })

  const bulkFieldDef = computed(() => bulkFields.value.find(c => c.key === bulkField.value) || null)

  async function applyBulkAssign() {
    const def = bulkFieldDef.value
    if (!def || !selected.value.size || bulkAssignBusy.value) return
    if (selected.value.size > 100) {
      showToast('Tối đa 100 entity mỗi lần gán', 'error')
      return
    }
    let value: unknown = bulkValue.value
    if (def.widget === 'number') value = bulkValue.value === '' ? '' : Number(bulkValue.value)
    if (def.widget === 'bool') value = bulkValue.value === '' ? '' : bulkValue.value === 'true'
    bulkAssignBusy.value = true
    const ids = [...selected.value]
    const errs: string[] = []
    let done = 0
    for (const id of ids) {
      const e = entities.value.find(x => x.id === id)
      if (!e) continue
      const attrs: Record<string, unknown> = { ...((e as Record<string, any>).attributes || {}) }
      if (value === '' || value === null || value === undefined) delete attrs[def.key]
      else attrs[def.key] = value
      try {
        await $fetch('/admin-api/entities/' + id, {
          method: 'PUT',
          headers: authHeaders(),
          body: {
            id: e.id,
            name: e.name,
            type: e.type,
            placeId: e.placeId || '',
            summary: e.summary || '',
            attributes: attrs,
          },
        })
        ;(e as Record<string, any>).attributes = attrs
      } catch {
        errs.push(e.name)
      }
      done += 1
      bulkProgress.value = done + '/' + ids.length
    }
    bulkAssignBusy.value = false
    bulkProgress.value = ''
    showToast(
      errs.length
        ? ('Gán xong nhưng lỗi ' + errs.length + ': ' + errs.slice(0, 3).join(', ') + (errs.length > 3 ? '…' : ''))
        : ('Đã gán "' + def.label + '" cho ' + (ids.length - errs.length) + ' entity'),
      errs.length ? 'warning' : 'success',
    )
    selected.value = new Set()
    bulkField.value = ''
    bulkValue.value = ''
  }

  return {
    bulkField,
    bulkValue,
    bulkAssignBusy,
    bulkProgress,
    bulkFields,
    bulkFieldDef,
    applyBulkAssign,
  }
}
