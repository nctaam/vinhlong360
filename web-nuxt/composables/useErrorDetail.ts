export function getErrorDetail(e: unknown, fallback = 'Đã xảy ra lỗi'): string {
  const data = (e as any)?.data
  if (typeof data?.detail === 'string') return data.detail
  if (typeof data?.message === 'string') return data.message
  if (typeof (e as any)?.message === 'string') return (e as any).message
  return fallback
}
