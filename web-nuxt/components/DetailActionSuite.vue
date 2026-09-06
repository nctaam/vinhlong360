<template>
  <div class="dc-actions">
    <ClientOnly>
      <div class="dc-trip">
        <button
          v-if="entityType === 'event'"
          type="button"
          :class="['trip-btn', { active: rsvpGoing }]"
          :aria-pressed="rsvpGoing"
          :disabled="actionPending"
          @click="toggleRsvp"
        >
          {{ rsvpGoing ? 'Sẽ đi' : 'Tôi sẽ đi' }}<span v-if="rsvpCount" class="trip-count">{{ rsvpCount }}</span>
        </button>
        <template v-else>
          <button
            type="button"
            :class="['trip-btn', { active: visitStatus === 'visited' }]"
            :aria-pressed="visitStatus === 'visited'"
            :disabled="actionPending"
            @click="setVisit('visited')"
          >
            <IconLine name="check" aria-hidden="true" /> Đã đến
          </button>
          <button
            type="button"
            :class="['trip-btn', { active: visitStatus === 'want' }]"
            :aria-pressed="visitStatus === 'want'"
            :disabled="actionPending"
            @click="setVisit('want')"
          >
            <IconLine name="heart" aria-hidden="true" /> Muốn đến
          </button>
        </template>
        <button
          type="button"
          :class="['trip-btn', { active: isFollowingPlace }]"
          :aria-pressed="isFollowingPlace"
          :disabled="actionPending"
          @click="toggleFollowPlace"
        >
          <IconLine name="bell" aria-hidden="true" /> {{ isFollowingPlace ? 'Đang theo dõi' : 'Theo dõi' }}
        </button>
      </div>
    </ClientOnly>
  </div>
</template>

<script setup lang="ts">
interface Props {
  entityId: string
  entityType?: string
}

const props = defineProps<Props>()

const { isLoggedIn, authHeaders } = useAuth()
const { openAuth } = useAuthModal()
const { show: _showToast } = useToast()

const visitStatus = ref<string | null>(null)
const isFollowingPlace = ref(false)
const rsvpGoing = ref(false)
const rsvpCount = ref(0)
const actionPending = ref(false)

async function toggleRsvp() {
  if (!isLoggedIn.value) { openAuth(() => toggleRsvp()); return }
  if (actionPending.value) return
  actionPending.value = true
  const prevGoing = rsvpGoing.value
  const prevCount = rsvpCount.value
  rsvpGoing.value = !prevGoing
  rsvpCount.value += prevGoing ? -1 : 1
  try {
    const r = await $fetch<{ going: boolean; count: number }>(`/api/events/${encodeURIComponent(props.entityId)}/rsvp`, { method: 'POST', headers: authHeaders() })
    rsvpGoing.value = r.going
    rsvpCount.value = r.count
    if (r.going) _showToast('Đã đăng ký đi sự kiện này', 'success')
  } catch {
    rsvpGoing.value = prevGoing
    rsvpCount.value = prevCount
    _showToast('Không thể đăng ký, thử lại', 'error')
  } finally {
    actionPending.value = false
  }
}

async function setVisit(status: 'visited' | 'want') {
  if (!isLoggedIn.value) { openAuth(() => setVisit(status)); return }
  if (actionPending.value) return
  actionPending.value = true
  const prev = visitStatus.value
  try {
    if (visitStatus.value === status) {
      visitStatus.value = null
      await $fetch(`/api/me/visits/${encodeURIComponent(props.entityId)}`, { method: 'DELETE', headers: authHeaders() })
    } else {
      visitStatus.value = status
      await $fetch('/api/me/visits', { method: 'POST', headers: authHeaders(), body: { entity_id: props.entityId, status } })
      _showToast(status === 'visited' ? 'Đã đánh dấu Đã đến' : 'Đã thêm vào Muốn đến', 'success')
    }
  } catch {
    visitStatus.value = prev
    _showToast('Không thể lưu, thử lại', 'error')
  } finally {
    actionPending.value = false
  }
}

async function toggleFollowPlace() {
  if (!isLoggedIn.value) { openAuth(() => toggleFollowPlace()); return }
  if (actionPending.value) return
  actionPending.value = true
  const prev = isFollowingPlace.value
  isFollowingPlace.value = !prev
  try {
    await $fetch(`/api/follow/entity/${encodeURIComponent(props.entityId)}`, { method: 'POST', headers: authHeaders() })
    if (!prev) _showToast('Đang theo dõi — sẽ báo khi có bài mới', 'success')
  } catch {
    isFollowingPlace.value = prev
    _showToast('Không thể theo dõi, thử lại', 'error')
  } finally {
    actionPending.value = false
  }
}

async function fetchStatus() {
  if (!isLoggedIn.value || !props.entityId) return
  const tasks: Promise<void>[] = [
    $fetch<{ status: string | null }>(`/api/me/visits/check/${encodeURIComponent(props.entityId)}`, { headers: authHeaders() })
      .then(v => { visitStatus.value = v?.status ?? null }).catch(() => {}),
    $fetch<{ following: { target_id: string }[] }>('/api/following', { headers: authHeaders() })
      .then(f => { isFollowingPlace.value = (f?.following || []).some(x => String(x.target_id) === props.entityId) }).catch(() => {}),
  ]
  if (props.entityType === 'event') {
    tasks.push(
      $fetch<{ count: number; going: boolean }>(`/api/events/${encodeURIComponent(props.entityId)}/rsvp`, { headers: authHeaders() })
        .then(r => { rsvpGoing.value = r.going; rsvpCount.value = r.count }).catch(() => {}),
    )
  }
  await Promise.all(tasks)
}

watch(() => props.entityId, () => {
  fetchStatus()
})

onMounted(() => {
  fetchStatus()
})
</script>
