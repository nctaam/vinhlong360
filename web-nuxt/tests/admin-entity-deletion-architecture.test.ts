import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ref } from 'vue'
import type { Entity } from '~/types'
import { useAdminEntityDeletion } from '../composables/useAdminEntityDeletion'

describe('Moc 170: Admin Entity Deletion & Bulk Operations Architecture', () => {
  const fetchMock = vi.fn()
  const showToastMock = vi.fn()
  const confirmDialogMock = vi.fn(() => Promise.resolve(true))
  const fetchEntitiesMock = vi.fn(() => Promise.resolve())

  function makeEntity(id: string): Entity {
    return {
      id,
      name: `Entity ${id}`,
      type: 'experience',
      summary: '',
      images: [],
      created_at: '2026-03-29T10:00:00Z',
    } as Entity
  }

  beforeEach(() => {
    fetchMock.mockReset()
    showToastMock.mockReset()
    confirmDialogMock.mockClear()
    confirmDialogMock.mockResolvedValue(true)
    fetchEntitiesMock.mockClear()
    vi.stubGlobal('$fetch', fetchMock)
  })

  it('manages single and select-all state across visible entities', () => {
    const selected = ref(new Set<string>())
    const entities = ref([makeEntity('e1'), makeEntity('e2'), makeEntity('e3')])

    const deletion = useAdminEntityDeletion({
      selected,
      entities,
      authHeaders: () => ({}),
      showToast: showToastMock,
      confirmDialog: confirmDialogMock,
      fetchEntities: fetchEntitiesMock,
    })

    expect(deletion.allSelected.value).toBe(false)

    deletion.toggleSel('e1')
    expect(selected.value.has('e1')).toBe(true)
    expect(selected.value.size).toBe(1)
    expect(deletion.allSelected.value).toBe(false)

    deletion.toggleAll()
    expect(selected.value.size).toBe(3)
    expect(deletion.allSelected.value).toBe(true)

    deletion.toggleAll()
    expect(selected.value.size).toBe(0)
    expect(deletion.allSelected.value).toBe(false)
  })

  it('deletes single entity with user confirmation and reloads list', async () => {
    const selected = ref(new Set<string>())
    const entities = ref([makeEntity('e1')])

    const deletion = useAdminEntityDeletion({
      selected,
      entities,
      authHeaders: () => ({ Authorization: 'Bearer token-1' }),
      showToast: showToastMock,
      confirmDialog: confirmDialogMock,
      fetchEntities: fetchEntitiesMock,
    })

    fetchMock.mockResolvedValueOnce({ success: true })

    await deletion.deleteEntity('e1')

    expect(confirmDialogMock).toHaveBeenCalledWith('Xóa entity "e1"?', { danger: true })
    expect(fetchMock).toHaveBeenCalledWith('/admin-api/entities/e1', expect.objectContaining({
      method: 'DELETE',
      headers: { Authorization: 'Bearer token-1' },
    }))
    expect(showToastMock).toHaveBeenCalledWith('Đã xóa entity', 'success')
    expect(fetchEntitiesMock).toHaveBeenCalled()
  })

  it('executes bulk delete operation on all selected entities and clears selection', async () => {
    const selected = ref(new Set<string>(['e1', 'e2']))
    const entities = ref([makeEntity('e1'), makeEntity('e2'), makeEntity('e3')])

    const deletion = useAdminEntityDeletion({
      selected,
      entities,
      authHeaders: () => ({ Authorization: 'Bearer token-1' }),
      showToast: showToastMock,
      confirmDialog: confirmDialogMock,
      fetchEntities: fetchEntitiesMock,
    })

    fetchMock.mockResolvedValueOnce({ count: 2 })

    await deletion.bulkDelete()

    expect(confirmDialogMock).toHaveBeenCalledWith('Xóa 2 entity đã chọn?', { danger: true })
    expect(fetchMock).toHaveBeenCalledWith('/admin-api/entities/bulk-delete', expect.objectContaining({
      method: 'POST',
      body: ['e1', 'e2'],
    }))
    expect(showToastMock).toHaveBeenCalledWith('Đã xóa 2/2 entity', 'success')
    expect(selected.value.size).toBe(0)
    expect(fetchEntitiesMock).toHaveBeenCalled()
  })
})
