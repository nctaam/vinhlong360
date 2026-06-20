export function useSiteSettings() {
  const { data } = useAsyncData('site-settings',
    () => $fetch<Record<string, unknown>>('/api/site-settings'),
    { server: true, default: () => ({}) }
  )

  function get<T>(key: string, fallback: T): T {
    const val = data.value?.[key]
    return (val !== undefined && val !== null ? val : fallback) as T
  }

  return { settings: data, get }
}
