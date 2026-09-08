import { ref, type Ref } from 'vue'
import type { Entity } from '~/types'
import type { AdminKind } from '~/utils/adminKinds'
import { getErrorDetail } from '~/composables/useFetchError'

export interface UseAdminEntityInlineEditOptions {
  currentKind: Ref<AdminKind | null>
  authHeaders: () => Record<string, string>
  showToast: (msg: string, type?: 'success' | 'warning' | 'error' | 'info') => void
}

export function useAdminEntityInlineEdit(options: UseAdminEntityInlineEditOptions) {
  const { currentKind, authHeaders, showToast } = options
  const inlineEdit = ref<{ id: string; field: string; value: string }>({ id: '', field: '', value: '' })

  function startInline(e: Entity, field: string, value: string) {
    inlineEdit.value = { id: e.id, field, value }
  }

  async function saveInline(e: Entity) {
    const { field, value } = inlineEdit.value
    if (field.startsWith('attr:')) {
      const key = field.slice(5)
      const def = currentKind.value?.columns.find(c => c.key === key)
      const attrs: Record<string, unknown> = { ...((e as Record<string, any>).attributes || {}) }
      const trimmed = value.trim()
      if (!trimmed) {
        delete attrs[key]
      } else if (def?.widget === 'number') {
        const n = Number(trimmed.replace(',', '.'))
        if (Number.isNaN(n)) {
          showToast('Giá trị phải là số', 'error')
          return
        }
        attrs[key] = n
      } else {
        attrs[key] = trimmed
      }
      try {
        await $fetch('/admin-api/entities/' + e.id, {
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
        showToast('Đã cập nhật', 'success')
        inlineEdit.value.id = ''
      } catch (err: unknown) {
        showToast(getErrorDetail(err, 'Lỗi khi cập nhật'), 'error')
      }
      return
    }

    if (!value.trim()) {
      inlineEdit.value.id = ''
      return
    }

    try {
      const body: Record<string, unknown> = {
        id: e.id,
        name: e.name,
        type: e.type,
        placeId: e.placeId || '',
        summary: e.summary || '',
      }
      body[field] = value.trim()
      await $fetch('/admin-api/entities/' + e.id, {
        method: 'PUT',
        headers: authHeaders(),
        body,
      })
      ;(e as Record<string, any>)[field] = value.trim()
      showToast('Đã cập nhật', 'success')
      inlineEdit.value.id = ''
    } catch (err: unknown) {
      showToast(getErrorDetail(err, 'Lỗi khi cập nhật'), 'error')
    }
  }

  async function toggleBoolAttr(e: Entity, key: string) {
    const attrs: Record<string, unknown> = { ...((e as Record<string, any>).attributes || {}) }
    attrs[key] = !attrs[key]
    try {
      await $fetch('/admin-api/entities/' + e.id, {
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
      showToast('Đã cập nhật', 'success')
    } catch (err: unknown) {
      showToast(getErrorDetail(err, 'Lỗi khi cập nhật'), 'error')
    }
  }

  return {
    inlineEdit,
    startInline,
    saveInline,
    toggleBoolAttr,
  }
}
