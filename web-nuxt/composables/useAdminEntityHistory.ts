import { ref } from 'vue'

export interface EntityHistoryRecord {
  id: string | number
  field: string
  old_value?: string | null
  new_value?: string
  created_at: string
}

export function truncVal(v?: string): string {
  if (!v) return '(trống)'
  return v.length > 60 ? v.slice(0, 57) + '…' : v
}

export interface UseAdminEntityHistoryOptions {
  authHeaders: () => Record<string, string>
}

export function useAdminEntityHistory(options: UseAdminEntityHistoryOptions) {
  const { authHeaders } = options
  const entityHistory = ref<EntityHistoryRecord[]>([])

  async function fetchEntityHistory(id: string) {
    entityHistory.value = []
    try {
      const r = await $fetch<{ history: EntityHistoryRecord[] }>('/admin-api/entities/' + id + '/history', {
        headers: authHeaders(),
      })
      entityHistory.value = r.history || []
    } catch {
      /* ignore — table may not exist yet */
    }
  }

  return {
    entityHistory,
    fetchEntityHistory,
    truncVal,
  }
}
