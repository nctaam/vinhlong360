import { ref, computed, type Ref } from 'vue'

export function useAdminEntitySorting<T extends Record<string, any>>(items: Ref<T[]>) {
  const sortKey = ref<string>('')
  const sortDir = ref<'asc' | 'desc'>('asc')

  function toggleSort(key: string) {
    if (sortKey.value === key) {
      if (sortDir.value === 'asc') sortDir.value = 'desc'
      else {
        sortKey.value = ''
        sortDir.value = 'asc'
      }
    } else {
      sortKey.value = key
      sortDir.value = 'asc'
    }
  }

  function sortIcon(key: string): string {
    if (sortKey.value !== key) return ''
    return sortDir.value === 'asc' ? 'chevron-up' : 'chevron-down'
  }

  const sortedEntities = computed(() => {
    if (!sortKey.value) return items.value
    const k = sortKey.value
    const dir = sortDir.value === 'asc' ? 1 : -1
    return [...items.value].sort((a, b) => {
      const va = String(a[k] || '').toLowerCase()
      const vb = String(b[k] || '').toLowerCase()
      return va < vb ? -dir : va > vb ? dir : 0
    })
  })

  return {
    sortKey,
    sortDir,
    toggleSort,
    sortIcon,
    sortedEntities,
  }
}
