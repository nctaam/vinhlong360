import { describe, it, expect } from 'vitest'
import { ref } from 'vue'
import type { Entity } from '~/types'
import { useAdminEntityKinds } from '../composables/useAdminEntityKinds'

describe('Moc 170: Admin Entity Kinds & Chip Filtering Architecture', () => {
  function makeEntity(id: string, type: string, attributes: Record<string, unknown> = {}): Entity {
    return {
      id,
      name: `Entity ${id}`,
      type,
      summary: '',
      images: [],
      created_at: '2026-03-29T10:00:00Z',
      attributes,
    } as Entity
  }

  it('determines currentKind and kindTypes based on route query', () => {
    const route = { query: { kind: 'place' } }
    const entities = ref<Entity[]>([])
    const types = ['experience', 'attraction', 'cuisine']

    const kinds = useAdminEntityKinds({ route, entities, types })

    expect(kinds.currentKind.value).not.toBeNull()
    expect(kinds.currentKind.value?.kind).toBe('place')
    expect(kinds.kindTypes.value).toContain('attraction')
    expect(kinds.kindIcon('place')).toBeTruthy()
    expect(kinds.typeIcon('attraction')).toBeTruthy()
  })

  it('filters entities by active chips in currentKind', () => {
    const route = { query: { kind: 'place' } }
    const e1 = makeEntity('e1', 'attraction', { heritage_level: 'Di tích quốc gia' })
    const e2 = makeEntity('e2', 'attraction', { heritage_level: 'Di tích cấp tỉnh' })
    const entities = ref<Entity[]>([e1, e2])
    const types = ['attraction']

    const kinds = useAdminEntityKinds({ route, entities, types })

    expect(kinds.chipFiltered.value.length).toBe(2)

    // Toggle national ranking chip if available
    const nationalChip = kinds.currentKind.value?.chips.find(c => c.key === 'di-tich-qg')
    if (nationalChip) {
      kinds.toggleChip('di-tich-qg')
      expect(kinds.activeChips.value.has('di-tich-qg')).toBe(true)
      expect(kinds.chipFiltered.value.length).toBe(1)
      expect(kinds.chipFiltered.value[0]!.id).toBe('e1')

      kinds.toggleChip('di-tich-qg')
      expect(kinds.activeChips.value.has('di-tich-qg')).toBe(false)
      expect(kinds.chipFiltered.value.length).toBe(2)
    }
  })
})
