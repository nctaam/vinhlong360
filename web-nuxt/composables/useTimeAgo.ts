export function useTimeAgo() {
  function timeAgo(dateStr: string): string {
    if (!dateStr) return ''
    const now = Date.now()
    const then = new Date(dateStr).getTime()
    const diff = Math.floor((now - then) / 1000)
    if (diff < 60) return 'Vừa xong'
    if (diff < 3600) return `${Math.floor(diff / 60)} phút trước`
    if (diff < 86400) return `${Math.floor(diff / 3600)} giờ trước`
    if (diff < 604800) return `${Math.floor(diff / 86400)} ngày trước`
    return new Date(dateStr).toLocaleDateString('vi-VN', { day: 'numeric', month: 'short' })
  }
  return { timeAgo }
}
