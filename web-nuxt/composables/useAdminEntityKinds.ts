import { ref, computed, type Ref } from 'vue'
import type { Entity } from '~/types'
import { TYPE_META } from '~/composables/useConstants'
import { ADMIN_KINDS, type KindDef } from '~/utils/adminKinds'

export interface UseAdminEntityKindsOptions {
  route: { query: Record<string, unknown> }
  entities: Ref<Entity[]>
  types: string[]
}

export function useAdminEntityKinds(options: UseAdminEntityKindsOptions) {
  const { route, entities, types } = options

  function kindIcon(kind: string): string {
    return ADMIN_KINDS.find(k => k.kind === kind)?.icon || 'tag'
  }

  function typeIcon(type: string): string {
    return TYPE_META[type]?.icon || 'tag'
  }

  const currentKind = computed<KindDef | null>(() => (
    ADMIN_KINDS.find(k => k.kind === String(route.query.kind || '')) || null
  ))

  const kindTypes = computed<string[]>(() => (
    currentKind.value ? currentKind.value.types : types
  ))

  const activeChips = ref<Set<string>>(new Set())

  function toggleChip(key: string): void {
    const s = new Set(activeChips.value)
    if (s.has(key)) s.delete(key)
    else s.add(key)
    activeChips.value = s
  }

  const chipFiltered = computed<Entity[]>(() => {
    if (!currentKind.value || !activeChips.value.size) return entities.value
    const chips = currentKind.value.chips.filter(c => activeChips.value.has(c.key))
    return entities.value.filter(e => chips.every(c => c.test(e)))
  })

  return {
    kindIcon,
    typeIcon,
    currentKind,
    kindTypes,
    activeChips,
    toggleChip,
    chipFiltered,
  }
}
