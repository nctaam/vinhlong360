import type { UseFetchOptions } from 'nuxt/app'

export function useApi<T>(path: string, opts?: UseFetchOptions<T>) {
  return useFetch<T>(path, {
    ...opts,
  })
}
