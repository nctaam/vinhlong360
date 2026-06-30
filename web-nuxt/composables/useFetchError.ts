import type { FetchError } from '~/types'

export function extractErrorMessage(e: unknown, fallback = 'Đã xảy ra lỗi'): string {
  const err = e as FetchError
  return err?.response?._data?.detail
    || err?.response?._data?.message
    || err?.data?.detail
    || err?.data?.message
    || err?.message
    || fallback
}

export const getErrorDetail = extractErrorMessage

export function getStatusCode(e: unknown): number | undefined {
  const err = e as FetchError
  return err?.response?.status ?? err?.statusCode
}
