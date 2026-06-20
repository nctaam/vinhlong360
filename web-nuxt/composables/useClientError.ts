/**
 * useClientError — thu lỗi phía client, gửi best-effort về backend (POST /api/client-error).
 *
 * Mục tiêu (P3 — quan sát lỗi, B8-compliant, KHÔNG Sentry/dịch vụ trả phí):
 *  - Fire-and-forget: KHÔNG bao giờ chặn UI, KHÔNG bao giờ throw (mọi lỗi nuốt im lặng).
 *  - Client-only: bỏ qua hoàn toàn khi SSR.
 *  - Opt-in/kill-switch: tôn trọng runtimeConfig.public.enableErrorCapture (mặc định BẬT
 *    nếu không khai báo) và query `?disable-error-capture` để tắt nhanh khi test.
 *  - Dedup + cap: mỗi (message::error) chỉ gửi 1 lần/phiên; tối đa N lỗi/phiên để chống loop.
 *  - Cắt kích thước trước khi gửi (backend cũng cap + che PII, đây là phòng thủ tầng client).
 *
 * Dùng:
 *  - captureClientError(message, err, ctx?) — gọi thủ công (vd ErrorBoundary, error.vue).
 *  - installGlobalErrorCapture() — gắn window.onerror + unhandledrejection (gọi 1 lần).
 */

const MAX_PER_SESSION = 20
const _seen = new Set<string>()
let _sent = 0
let _globalInstalled = false

function _enabled(): boolean {
  if (!import.meta.client) return false
  try {
    const cfg = useRuntimeConfig()
    if (cfg?.public?.enableErrorCapture === false) return false
  } catch {
    // useRuntimeConfig có thể không sẵn ngoài context Nuxt — vẫn cho phép chạy.
  }
  try {
    const sp = new URLSearchParams(window.location.search)
    if (sp.has('disable-error-capture')) return false
  } catch {
    /* noop */
  }
  return true
}

function _str(v: unknown): string {
  if (v == null) return ''
  if (typeof v === 'string') return v
  if (v instanceof Error) return v.message || String(v)
  try {
    return String(v)
  } catch {
    return ''
  }
}

/**
 * Gửi 1 lỗi client lên backend. An toàn tuyệt đối — không throw, không await ở caller.
 */
export function captureClientError(message: string, err?: unknown, ctx?: Record<string, unknown>): void {
  if (!_enabled()) return
  if (_sent >= MAX_PER_SESSION) return

  try {
    const errStr = _str(err)
    const stack = err instanceof Error && err.stack ? err.stack : ''
    const key = `${message}::${errStr}`.slice(0, 300)
    if (_seen.has(key)) return
    _seen.add(key)
    _sent += 1

    let sessionId = ''
    try {
      sessionId = _str(useState<string>('ai-session-id', () => '').value)
    } catch {
      /* state có thể không có — không sao */
    }

    const body = {
      message: String(message || '').slice(0, 500),
      error: errStr.slice(0, 500),
      stack: stack.slice(0, 2000),
      url: typeof window !== 'undefined' ? window.location.href.slice(0, 300) : '',
      level: 'error',
      timestamp: new Date().toISOString(),
      user_agent: typeof navigator !== 'undefined' ? navigator.userAgent.slice(0, 300) : '',
      session_id: sessionId.slice(0, 64),
      ...(ctx ? { ctx_keys: Object.keys(ctx).join(',').slice(0, 100) } : {}),
    }

    // Fire-and-forget: không await, nuốt mọi lỗi mạng để không sinh lỗi-của-lỗi.
    void $fetch('/api/client-error', { method: 'POST', body }).catch(() => {})
  } catch {
    /* capture không bao giờ được làm vỡ luồng gọi */
  }
}

/**
 * Gắn handler toàn cục cho lỗi chưa bắt + promise rejection chưa xử lý.
 * Idempotent: gọi nhiều lần chỉ gắn 1 lần.
 */
export function installGlobalErrorCapture(): void {
  if (!import.meta.client || _globalInstalled) return
  if (!_enabled()) return
  _globalInstalled = true
  try {
    window.addEventListener('error', (ev: ErrorEvent) => {
      captureClientError('window.onerror', ev.error || ev.message)
    })
    window.addEventListener('unhandledrejection', (ev: PromiseRejectionEvent) => {
      captureClientError('unhandledrejection', ev.reason)
    })
  } catch {
    /* noop */
  }
}

export function useClientError() {
  return { captureClientError, installGlobalErrorCapture }
}
