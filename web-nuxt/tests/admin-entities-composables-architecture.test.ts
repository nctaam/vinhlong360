import { describe, it, expect, vi } from 'vitest'
import { ref } from 'vue'
import {
  useAdminEntityAttributes,
} from '../composables/useAdminEntityAttributes'
import {
  useAdminEntityRelationships,
} from '../composables/useAdminEntityRelationships'
import {
  useAdminEntityBulkAssign,
} from '../composables/useAdminEntityBulkAssign'
import {
  useAdminEntityHistory,
  truncVal,
} from '../composables/useAdminEntityHistory'
import {
  useAdminEntityInlineEdit,
} from '../composables/useAdminEntityInlineEdit'
import {
  useAdminEntityDuplicateCheck,
} from '../composables/useAdminEntityDuplicateCheck'
import {
  useAdminEntitySchema,
} from '../composables/useAdminEntitySchema'
import {
  useAdminEntitySorting,
} from '../composables/useAdminEntitySorting'
import {
  useAdminEntityExport,
} from '../composables/useAdminEntityExport'
import {
  useAdminEntityValidation,
} from '../composables/useAdminEntityValidation'

describe('Moc 165: Admin Entities Composables Architecture', () => {
  describe('useAdminEntityAttributes', () => {
    it('initializes and merges KBYG amenities and details correctly', () => {
      const {
        kbygTips,
        kbygAmenities,
        toggleAmenity,
        initKbyg,
        mergeKbygIntoAttrs,
      } = useAdminEntityAttributes()

      initKbyg({
        kbyg_tips: ['Mẹo 1', 'Mẹo 2'],
        amenity_badges: ['wifi'],
      })

      expect(kbygTips.value).toBe('Mẹo 1\nMẹo 2')
      expect(kbygAmenities.value).toEqual(['wifi'])

      toggleAmenity('wheelchair')
      expect(kbygAmenities.value).toEqual(['wifi', 'wheelchair'])

      toggleAmenity('wifi')
      expect(kbygAmenities.value).toEqual(['wheelchair'])

      const merged = mergeKbygIntoAttrs({ existing: 'preserved' })
      expect(merged.kbyg_tips).toEqual(['Mẹo 1', 'Mẹo 2'])
      expect(merged.amenity_badges).toEqual(['wheelchair'])
      expect(merged.existing).toBe('preserved')
    })

    it('cycles seasons accurately between off -> in -> peak -> off', () => {
      const {
        seasonMonths,
        seasonPeak,
        seasonTouched,
        initSeason,
        monthState,
        cycleMonth,
      } = useAdminEntityAttributes()

      initSeason(null)
      expect(seasonMonths.value).toEqual([])
      expect(seasonPeak.value).toEqual([])
      expect(seasonTouched.value).toBe(false)
      expect(monthState(5)).toBe('off')

      // cycle 1: off -> in
      cycleMonth(5)
      expect(monthState(5)).toBe('in')
      expect(seasonMonths.value).toContain(5)
      expect(seasonPeak.value).not.toContain(5)
      expect(seasonTouched.value).toBe(true)

      // cycle 2: in -> peak
      cycleMonth(5)
      expect(monthState(5)).toBe('peak')
      expect(seasonPeak.value).toContain(5)

      // cycle 3: peak -> off
      cycleMonth(5)
      expect(monthState(5)).toBe('off')
      expect(seasonMonths.value).not.toContain(5)
      expect(seasonPeak.value).not.toContain(5)
    })

    it('validates advanced JSON and correctly assembles final entity attributes', () => {
      const {
        advancedJson,
        advancedError,
        initAdvanced,
        parseAdvancedJson,
        assembleAttributes,
      } = useAdminEntityAttributes()

      initAdvanced({ sac_phong: 'Tự Đức ngũ niên', custom_key: 'custom' }, ['address'])
      expect(advancedJson.value).toContain('sac_phong')
      expect(advancedJson.value).toContain('custom_key')

      const parsed = parseAdvancedJson()
      expect(parsed.ok).toBe(true)
      if (parsed.ok) {
        expect(parsed.data.sac_phong).toBe('Tự Đức ngũ niên')
      }

      advancedJson.value = '{ invalid json'
      const invalidParsed = parseAdvancedJson()
      expect(invalidParsed.ok).toBe(false)
      expect(advancedError.value).toBeTruthy()

      // Assemble attributes
      advancedJson.value = '{"bespoke": "value"}'
      const res = assembleAttributes({
        existingAttrs: { old_custom: 'old', address: 'Old Address' },
        currentSchemaKeys: ['address', 'phone'],
        typedAttrs: { address: 'New Address', phone: '' },
        advancedObj: { bespoke: 'value' },
      })

      expect(res.bespoke).toBe('value')
      expect(res.address).toBe('New Address')
      expect(res.phone).toBeUndefined()
      expect(res.old_custom).toBeUndefined()
    })
  })

  describe('useAdminEntitySorting', () => {
    it('manages sorting state, toggles directions, and orders items correctly', () => {
      const items = ref([
        { id: 'b', name: 'Bến Tre' },
        { id: 'a', name: 'An Giang' },
        { id: 'c', name: 'Cần Thơ' },
      ])

      const {
        sortKey,
        sortDir,
        toggleSort,
        sortIcon,
        sortedEntities,
      } = useAdminEntitySorting(items)

      expect(sortIcon('name')).toBe('')
      expect(sortedEntities.value[0].name).toBe('Bến Tre')

      toggleSort('name')
      expect(sortKey.value).toBe('name')
      expect(sortDir.value).toBe('asc')
      expect(sortIcon('name')).toBe('chevron-up')
      expect(sortedEntities.value[0].name).toBe('An Giang')

      toggleSort('name')
      expect(sortDir.value).toBe('desc')
      expect(sortIcon('name')).toBe('chevron-down')
      expect(sortedEntities.value[0].name).toBe('Cần Thơ')

      toggleSort('name')
      expect(sortKey.value).toBe('')
      expect(sortIcon('name')).toBe('')
    })
  })

  describe('useAdminEntityExport', () => {
    it('formats entities correctly for JSON and CSV download', () => {
      const mockDownload = vi.fn()
      vi.stubGlobal('downloadBlob', mockDownload)

      const entities = ref<any[]>([
        { id: 'ent-1', name: 'Đền Thờ "Ông"', type: 'place', placeId: 'p-1', summary: 'Tóm tắt' },
      ])

      const { exportJSON, exportCSV } = useAdminEntityExport(entities, mockDownload)

      exportJSON()
      expect(mockDownload).toHaveBeenCalledWith(expect.any(Blob), expect.stringMatching(/^entities-\d{4}-\d{2}-\d{2}\.json$/))

      exportCSV()
      expect(mockDownload).toHaveBeenCalledWith(expect.any(Blob), expect.stringMatching(/^entities-\d{4}-\d{2}-\d{2}\.csv$/))
    })
  })

  describe('useAdminEntityValidation', () => {
    it('validates required fields, slug format, and error clearing', () => {
      const form = ref({ id: '', name: '', type: '' })
      const editingEntity = ref<any>(null)

      const {
        fieldErrors,
        clearFieldError,
        validateForm,
        resetFieldErrors,
      } = useAdminEntityValidation({ form, editingEntity })

      expect(validateForm()).toBe(false)
      expect(fieldErrors.value.name).toBeTruthy()
      expect(fieldErrors.value.id).toBeTruthy()
      expect(fieldErrors.value.type).toBeTruthy()

      form.value.name = 'Chùa Ông'
      clearFieldError('name')
      expect(fieldErrors.value.name).toBeUndefined()

      form.value.id = 'INVALID ID WITH SPACES'
      expect(validateForm()).toBe(false)
      expect(fieldErrors.value.id).toContain('chữ thường')

      form.value.id = 'chua-ong'
      form.value.type = 'place'
      expect(validateForm()).toBe(true)

      resetFieldErrors()
      expect(Object.keys(fieldErrors.value).length).toBe(0)
    })
  })

  describe('useAdminEntityRelationships', () => {
    it('manages relationship addition and removal with confirmation', async () => {
      const mockFetch = vi.fn().mockImplementation((url) => {
        if (url.includes('/api/entities/ent-1/relationships')) return Promise.resolve({ relationships: [{ from_id: 'ent-1', to_id: 'ent-2', type: 'related_to' }] })
        return Promise.resolve({ added: 1 })
      })
      vi.stubGlobal('$fetch', mockFetch)
      const toastMock = vi.fn()
      const confirmMock = vi.fn().mockResolvedValue(true)

      const formId = ref('ent-1')
      const editingEntity = ref({ id: 'ent-1' })

      const {
        rels,
        newRel,
        fetchRels,
        addRel,
        removeRel,
      } = useAdminEntityRelationships({
        formId,
        editingEntity,
        authHeaders: () => ({}),
        showToast: toastMock,
        confirmDialog: confirmMock,
      })

      await fetchRels('ent-1')
      expect(rels.value.length).toBe(1)

      newRel.value = { to_id: 'ent-3', type: 'near' }
      await addRel()
      expect(mockFetch).toHaveBeenCalledWith('/admin-api/relationships', expect.objectContaining({
        method: 'POST',
        body: { from_id: 'ent-1', to_id: 'ent-3', type: 'near' },
      }))

      await removeRel(rels.value[0])
      expect(confirmMock).toHaveBeenCalled()
      expect(mockFetch).toHaveBeenCalledWith(expect.stringContaining('/admin-api/relationships?'), expect.objectContaining({
        method: 'DELETE',
      }))
    })
  })

  describe('useAdminEntityBulkAssign', () => {
    it('applies bulk attribute assignments to selected entities', async () => {
      const mockFetch = vi.fn().mockResolvedValue({})
      vi.stubGlobal('$fetch', mockFetch)
      const toastMock = vi.fn()

      const currentKind = ref<any>({
        kind: 'experience',
        columns: [{ key: 'open_hours', label: 'Giờ mở cửa', widget: 'text' }],
      })
      const selected = ref(new Set(['ent-1', 'ent-2']))
      const entities = ref<any[]>([
        { id: 'ent-1', name: 'Entity 1', type: 'place', attributes: {} },
        { id: 'ent-2', name: 'Entity 2', type: 'place', attributes: {} },
      ])

      const {
        bulkField,
        bulkValue,
        applyBulkAssign,
      } = useAdminEntityBulkAssign({
        currentKind,
        selected,
        entities,
        authHeaders: () => ({}),
        showToast: toastMock,
      })

      bulkField.value = 'open_hours'
      bulkValue.value = '7h - 17h'

      await applyBulkAssign()

      expect(mockFetch).toHaveBeenCalledTimes(2)
      expect(entities.value[0].attributes.open_hours).toBe('7h - 17h')
      expect(entities.value[1].attributes.open_hours).toBe('7h - 17h')
      expect(selected.value.size).toBe(0)
      expect(toastMock).toHaveBeenCalledWith('Đã gán "Giờ mở cửa" cho 2 entity', 'success')
    })
  })

  describe('useAdminEntityHistory', () => {
    it('truncates long diff values and fetches history records', async () => {
      expect(truncVal('')).toBe('(trống)')
      expect(truncVal('Short text')).toBe('Short text')
      expect(truncVal('A'.repeat(70))).toBe('A'.repeat(57) + '…')

      const mockFetch = vi.fn().mockResolvedValue({
        history: [{ id: 1, field: 'name', old_value: 'A', new_value: 'B', created_at: '2026-01-01' }],
      })
      vi.stubGlobal('$fetch', mockFetch)

      const { entityHistory, fetchEntityHistory } = useAdminEntityHistory({
        authHeaders: () => ({}),
      })

      await fetchEntityHistory('ent-1')
      expect(entityHistory.value.length).toBe(1)
      expect(entityHistory.value[0].field).toBe('name')
    })
  })

  describe('useAdminEntityInlineEdit', () => {
    it('handles starting, canceling, and saving inline field updates', async () => {
      const mockFetch = vi.fn().mockResolvedValue({})
      vi.stubGlobal('$fetch', mockFetch)
      const toastMock = vi.fn()

      const currentKind = ref<any>({
        kind: 'experience',
        columns: [{ key: 'price', label: 'Giá', widget: 'number' }],
      })

      const {
        inlineEdit,
        startInline,
        saveInline,
        toggleBoolAttr,
      } = useAdminEntityInlineEdit({
        currentKind,
        authHeaders: () => ({}),
        showToast: toastMock,
      })

      const entity = { id: 'ent-1', name: 'Đền Thờ', type: 'place', attributes: { is_active: false } } as any

      startInline(entity, 'name', 'Đền Thờ Mới')
      expect(inlineEdit.value).toEqual({ id: 'ent-1', field: 'name', value: 'Đền Thờ Mới' })

      await saveInline(entity)
      expect(mockFetch).toHaveBeenCalledWith('/admin-api/entities/ent-1', expect.objectContaining({
        method: 'PUT',
        body: expect.objectContaining({ name: 'Đền Thờ Mới' }),
      }))
      expect(entity.name).toBe('Đền Thờ Mới')
      expect(inlineEdit.value.id).toBe('')

      await toggleBoolAttr(entity, 'is_active')
      expect(entity.attributes.is_active).toBe(true)
    })
  })

  describe('useAdminEntityDuplicateCheck', () => {
    it('debounces and checks for duplicate entity names', async () => {
      vi.useFakeTimers()
      const mockFetch = vi.fn().mockResolvedValue({
        duplicates: [{ id: 'dup-1', name: 'Chùa Bà', type: 'place' }],
      })
      vi.stubGlobal('$fetch', mockFetch)

      const formName = ref('Chùa')
      const editingEntity = ref(null)

      const {
        duplicates,
        checkDuplicate,
        clearDuplicates,
      } = useAdminEntityDuplicateCheck({
        formName,
        editingEntity,
        authHeaders: () => ({}),
      })

      checkDuplicate()
      await vi.advanceTimersByTimeAsync(450)

      expect(mockFetch).toHaveBeenCalledWith(expect.stringContaining('/admin-api/entities/check-duplicate?name=Ch%C3%B9a'), expect.any(Object))
      expect(duplicates.value.length).toBe(1)

      clearDuplicates()
      expect(duplicates.value.length).toBe(0)
      vi.useRealTimers()
    })
  })

  describe('useAdminEntitySchema', () => {
    it('loads schemas, partitions fields by group, and initializes typed attributes', async () => {
      const mockFetch = vi.fn().mockImplementation((url) => {
        if (url === '/admin-api/entity-schema') {
          return Promise.resolve({
            types: {
              food: {
                type: 'food',
                label: 'Ẩm thực',
                emoji: '🍜',
                kind: 'food',
                fields: [
                  { key: 'signature_dish', label: 'Món đặc trưng', widget: 'text', group: 'Ẩm thực' },
                  { key: 'spice_level', label: 'Độ cay', widget: 'select', group: 'Chi tiết' },
                ],
              },
            },
          })
        }
        if (url === '/admin-api/entity-kinds') {
          return Promise.resolve({
            kinds: [{ kind: 'food', label: 'Ẩm thực', emoji: '🍜', total: 10, types: [] }],
            grand_total: 10,
          })
        }
        return Promise.resolve({})
      })
      vi.stubGlobal('$fetch', mockFetch)

      const formType = ref('food')
      const {
        entitySchemas,
        typedAttrs,
        fetchEntitySchema,
        fetchKinds,
        currentSchemaGroups,
        currentSchemaKeys,
        initTypedAttrs,
      } = useAdminEntitySchema({
        formType,
        authHeaders: () => ({}),
        showToast: vi.fn(),
      })

      await fetchEntitySchema()
      await fetchKinds()

      expect(entitySchemas.value.food).toBeDefined()
      expect(currentSchemaKeys.value).toEqual(['signature_dish', 'spice_level'])
      expect(currentSchemaGroups.value.length).toBe(2)
      expect(currentSchemaGroups.value[0].legend).toBe('Ẩm thực')

      initTypedAttrs({ signature_dish: 'Kho quẹt', extra_unrelated: 'ignored' })
      expect(typedAttrs.value.signature_dish).toBe('Kho quẹt')
      expect(typedAttrs.value.extra_unrelated).toBeUndefined()
    })
  })
})
