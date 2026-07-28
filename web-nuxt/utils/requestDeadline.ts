export const DEFAULT_API_TIMEOUT_MS = 10_000
export const ATTESTATION_TIMEOUT_MS = 3_000
export const SITEMAP_TIMEOUT_MS = 5_000

export function withRequestDeadline<T>(
  timeoutMs: number,
  operation: (signal: AbortSignal) => Promise<T>,
): Promise<T> {
  const controller = new AbortController()
  let timer: ReturnType<typeof setTimeout> | undefined
  const deadline = new Promise<never>((_resolve, reject) => {
    timer = setTimeout(() => {
      const error = new Error(`Request deadline exceeded after ${timeoutMs}ms`)
      reject(error)
      controller.abort(error)
    }, timeoutMs)
  })

  let operationPromise: Promise<T>
  try {
    operationPromise = operation(controller.signal)
  } catch (error) {
    operationPromise = Promise.reject(error)
  }

  return Promise.race([operationPromise, deadline]).finally(() => {
    if (timer !== undefined) clearTimeout(timer)
  })
}
