import { ref, computed } from 'vue'
import { getStatusCode } from '~/composables/useFetchError'
import { encodePathId } from '~/utils/routePaths'

export function useCommunityScheduledPosts() {
  const { isLoggedIn, authHeaders, handleSessionExpired } = useAuth()
  const { show: showToast } = useToast()

  const schedulePost = ref(false)
  const scheduledAt = ref('')
  const minScheduleDate = computed(() => {
    const d = new Date()
    d.setMinutes(d.getMinutes() + 10)
    return d.toISOString().slice(0, 16)
  })
  const scheduledPosts = ref<any[]>([])

  async function loadScheduledPosts() {
    if (!isLoggedIn.value) return
    try {
      const res = await $fetch<{ scheduled: any[] }>('/api/scheduled', { headers: authHeaders() })
      scheduledPosts.value = res.scheduled || []
    } catch { /* im lặng — mục lên lịch không quan trọng bằng bảng tin chính */ }
  }

  async function cancelScheduled(id: string) {
    try {
      await $fetch(`/api/scheduled/${encodePathId(id)}`, { method: 'DELETE', headers: authHeaders() })
      scheduledPosts.value = scheduledPosts.value.filter(s => s.id !== id)
      showToast('Đã hủy lịch đăng', 'success')
    } catch (e: unknown) {
      if (getStatusCode(e) === 401) { handleSessionExpired(); return }
      showToast('Không thể hủy lịch đăng', 'error')
    }
  }

  return {
    schedulePost,
    scheduledAt,
    minScheduleDate,
    scheduledPosts,
    loadScheduledPosts,
    cancelScheduled,
  }
}
