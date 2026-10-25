import { getCurrentInstance } from 'vue'

let relativeTimeTimer: ReturnType<typeof setInterval> | null = null
let activeSubscribers = 0

const absoluteDateFormatter = new Intl.DateTimeFormat('vi-VN', {
  timeZone: 'Asia/Ho_Chi_Minh',
  day: 'numeric',
  month: 'short',
})

function formatAbsoluteDate(date: Date): string {
  return absoluteDateFormatter.format(date)
}

export function useTimeAgo() {
  const hydrated = useState('relative-time-hydrated', () => false)
  const now = useState('relative-time-now', () => 0)

  if (import.meta.client && getCurrentInstance()) {
    onMounted(() => {
      activeSubscribers += 1
      now.value = Date.now()
      hydrated.value = true
      if (!relativeTimeTimer) {
        relativeTimeTimer = setInterval(() => {
          now.value = Date.now()
        }, 60_000)
      }
    })
    onUnmounted(() => {
      activeSubscribers = Math.max(0, activeSubscribers - 1)
      if (activeSubscribers === 0 && relativeTimeTimer) {
        clearInterval(relativeTimeTimer)
        relativeTimeTimer = null
      }
    })
  }

  function timeAgo(dateStr: string): string {
    if (!dateStr) return ''
    const date = new Date(dateStr)
    const then = date.getTime()
    if (Number.isNaN(then)) return ''
    if (!hydrated.value || !now.value) return formatAbsoluteDate(date)

    const diff = Math.floor((now.value - then) / 1000)
    if (diff < 60) return 'Vừa xong'
    if (diff < 3600) return `${Math.floor(diff / 60)} phút trước`
    if (diff < 86400) return `${Math.floor(diff / 3600)} giờ trước`
    if (diff < 604800) return `${Math.floor(diff / 86400)} ngày trước`
    return formatAbsoluteDate(date)
  }

  return { timeAgo }
}
