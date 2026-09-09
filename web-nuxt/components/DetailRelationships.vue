<template>
  <div v-if="relationships.length" class="rel-block reveal" data-detail-region="related">
    <h2 class="sediment-head">{{ ss('labels.detail.relationships_heading', 'Liên kết') }}</h2>
    <ul class="rel-list">
      <li v-for="rel in relationships" :key="`${rel.target_id}-${rel.rel_type}`">
        <span class="rel-label">{{ rel.label }}</span>
        <span class="rel-main">
          <NuxtLink :to="entityPath(rel.target_id)">{{ rel.target_name }}</NuxtLink>
          <small v-if="rel.distance_km" class="rel-distance">{{ rel.distance_km }} km</small>
        </span>
      </li>
    </ul>
    <button
      v-if="hasMoreRelationships"
      class="rel-more"
      type="button"
      :disabled="loadingRelationships"
      @click="loadMoreRelationships"
    >
      {{ loadingRelationships ? ss('labels.detail.relationships_loading', 'Đang tải...') : `${ss('labels.detail.relationships_more', 'Xem thêm')} ${remainingRelationshipCount}` }}
    </button>
    <p v-if="relError" class="empty" role="alert">{{ relError }}</p>
  </div>
</template>

<script setup lang="ts">
import { TYPE_META, REL_FWD, REL_BWD } from '~/composables/useConstants'
import { encodePathId, entityPath } from '~/utils/routePaths'

interface Props {
  entityId: string
  initialRelationships?: Record<string, any>[]
  initialTotal?: number
}

const props = withDefaults(defineProps<Props>(), {
  initialRelationships: () => [],
  initialTotal: undefined,
})

const { get: ss } = useSiteSettings()

const RELATIONSHIP_BATCH_SIZE = 24
const relationshipRows = ref<Record<string, any>[]>([])
const relationshipTotal = ref(0)
const loadingRelationships = ref(false)
const relError = ref('')

watch(
  () => [props.initialRelationships, props.initialTotal],
  () => {
    relationshipRows.value = Array.isArray(props.initialRelationships)
      ? props.initialRelationships.map(rel => ({ ...rel }))
      : []
    relationshipTotal.value = Number(props.initialTotal ?? relationshipRows.value.length) || relationshipRows.value.length
  },
  { immediate: true },
)

function rawRelationshipKey(r: Record<string, any>) {
  return `${r.source_id || ''}|${r.target_id || ''}|${r.rel_type || ''}`
}

function normalizeRelationship(r: Record<string, any>) {
  const sourceId = r.source_id
  const targetId = r.target_id
  const relType = r.rel_type
  if (!sourceId || !targetId || !relType) return null
  const isNear = relType === 'near'
  const distance = typeof r.distance_km === 'number' ? r.distance_km : null
  if (isNear && (distance === null || distance > 50)) return null
  const isFwd = sourceId === props.entityId
  const otherId = r.other_id ?? (isFwd ? targetId : sourceId)
  const otherName = r.other_name ?? (isFwd ? (r.target_name ?? r.name) : (r.source_name ?? r.name))
  const otherType = r.other_type ?? ''
  let label = isFwd ? (REL_FWD[relType] || relType) : (REL_BWD[relType] || relType)
  if ((relType === 'related_to' || relType === 'associated_with') && otherType) {
    const meta = TYPE_META[otherType]
    if (meta) label = meta.emoji + ' ' + meta.label
  }
  return {
    target_id: otherId,
    target_name: otherName || otherId,
    rel_type: relType,
    distance_km: distance,
    label,
  }
}

const relationships = computed(() => {
  return relationshipRows.value
    .map(normalizeRelationship)
    .filter((rel): rel is NonNullable<ReturnType<typeof normalizeRelationship>> => Boolean(rel))
})

const remainingRelationshipCount = computed(() => Math.max(relationshipTotal.value - relationshipRows.value.length, 0))
const hasMoreRelationships = computed(() => remainingRelationshipCount.value > 0)

async function loadMoreRelationships() {
  if (loadingRelationships.value || !hasMoreRelationships.value) return
  const currentId = props.entityId
  loadingRelationships.value = true
  relError.value = ''
  try {
    const response = await $fetch<{ total?: number; relationships?: Record<string, any>[] }>(`/api/entities/${encodePathId(currentId)}/relationships`, {
      query: {
        limit: RELATIONSHIP_BATCH_SIZE,
        offset: relationshipRows.value.length,
      },
    })
    if (currentId !== props.entityId) return
    relationshipTotal.value = Number(response?.total ?? relationshipTotal.value) || relationshipTotal.value
    const seen = new Set(relationshipRows.value.map(rawRelationshipKey))
    for (const rel of response?.relationships || []) {
      const key = rawRelationshipKey(rel)
      if (!seen.has(key)) {
        relationshipRows.value.push(rel)
        seen.add(key)
      }
    }
  } catch {
    relError.value = ss('labels.detail.relationships_error', 'Không tải thêm được, thử lại sau.')
  } finally {
    loadingRelationships.value = false
  }
}
</script>
