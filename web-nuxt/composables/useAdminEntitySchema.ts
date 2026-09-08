import { ref, computed, type Ref } from 'vue'

export interface SchemaFieldDef {
  key: string
  label: string
  widget: string
  required?: boolean
  options?: (string | number)[]
  help?: string
  placeholder?: string
  group?: string
  min?: number
  max?: number
  step?: number
}

export interface TypeSchema {
  type: string
  label: string
  emoji: string
  kind: string
  fields: SchemaFieldDef[]
}

export interface KindTypeCount {
  type: string
  label: string
  emoji: string
  count: number
}

export interface KindGroup {
  kind: string
  label: string
  emoji: string
  total: number
  types: KindTypeCount[]
}

export interface UseAdminEntitySchemaOptions {
  formType: Ref<string>
  authHeaders: () => Record<string, string>
  showToast: (msg: string, type?: 'success' | 'warning' | 'error' | 'info') => void
}

export function useAdminEntitySchema(options: UseAdminEntitySchemaOptions) {
  const { formType, authHeaders, showToast } = options

  const entitySchemas = ref<Record<string, TypeSchema>>({})
  const typedAttrs = ref<Record<string, unknown>>({})

  async function fetchEntitySchema() {
    if (Object.keys(entitySchemas.value).length) return
    try {
      const r = await $fetch<{ types: Record<string, TypeSchema> }>('/admin-api/entity-schema', {
        headers: authHeaders(),
      })
      entitySchemas.value = r.types || {}
    } catch {
      showToast('Không tải được schema loại entity', 'warning')
    }
  }

  const kindGroups = ref<KindGroup[]>([])
  const kindGrandTotal = ref(0)

  async function fetchKinds() {
    try {
      const r = await $fetch<{ kinds: KindGroup[]; grand_total: number }>('/admin-api/entity-kinds', {
        headers: authHeaders(),
      })
      kindGroups.value = (r.kinds || []).filter(k => k.total > 0)
      kindGrandTotal.value = r.grand_total || 0
    } catch {
      showToast('Không tải được tổng quan danh mục', 'warning')
    }
  }

  const currentSchemaGroups = computed(() => {
    const s = entitySchemas.value[formType.value]
    if (!s || !s.fields?.length) return [] as { legend: string; fields: SchemaFieldDef[] }[]
    const groups: { legend: string; fields: SchemaFieldDef[] }[] = []
    const byLegend = new Map<string, SchemaFieldDef[]>()
    for (const f of s.fields) {
      const g = f.group || 'Chi tiết'
      if (!byLegend.has(g)) {
        byLegend.set(g, [])
        groups.push({ legend: g, fields: byLegend.get(g)! })
      }
      byLegend.get(g)!.push(f)
    }
    return groups
  })

  const currentSchemaKeys = computed(() => (entitySchemas.value[formType.value]?.fields || []).map(f => f.key))

  function initTypedAttrs(attrs?: Record<string, unknown>) {
    const a = attrs || {}
    const next: Record<string, unknown> = {}
    for (const k of currentSchemaKeys.value) {
      if (a[k] !== undefined) next[k] = a[k]
    }
    typedAttrs.value = next
  }

  return {
    entitySchemas,
    typedAttrs,
    fetchEntitySchema,
    kindGroups,
    kindGrandTotal,
    fetchKinds,
    currentSchemaGroups,
    currentSchemaKeys,
    initTypedAttrs,
  }
}
