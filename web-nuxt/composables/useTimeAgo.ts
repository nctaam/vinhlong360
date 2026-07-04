let relativeTimeTimer: ReturnType<typeof setInterval> | null = null

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

  if (import.meta.client) {
    onMounted(() => {
      now.value = Date.now()
      hydrated.value = true
      if (!relativeTimeTimer) {
        relativeTimeTimer = setInterval(() => {
          now.value = Date.now()
        }, 60_000)
      }
    })
  }

  function timeAgo(dateStr: string): string {
    if (!dateStr) return ''
    const date = new Date(dateStr)
    const then = date.getTime()
    if (Number.isNaN(then)) return ''
    if (!hydrated.value) return formatAbsoluteDate(date)

    const diff = Math.floor(((now.value || Date.now()) - then) / 1000)
    if (diff < 0) return 'Vừa xong'
    if (diff < 60) return 'Vừa xong'
    if (diff < 3600) return `${Math.floor(diff / 60)} phút trước`
    if (diff < 86400) return `${Math.floor(diff / 3600)} giờ trước`
    if (diff < 604800) return `${Math.floor(diff / 86400)} ngày trước`
    return formatAbsoluteDate(date)
  }

  return { timeAgo }
}
