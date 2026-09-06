import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('Error Masking Prevention Contract (§12.4)', () => {
  const root = resolve(__dirname, '..')

  it('cong-dong.vue does not mask 503 errors as coming soon empty state', () => {
    const content = readFileSync(resolve(root, 'pages/cong-dong.vue'), 'utf8')

    // Rule: When 503 occurs in ugcUnavailable, it must not display "Cộng đồng sắp mở"
    expect(content).not.toMatch(/ugcUnavailable[\s\S]*?title="Cộng đồng sắp mở"/)
    expect(content).not.toMatch(/title="Cộng đồng sắp mở"[\s\S]*?v-else-if="ugcUnavailable"/)

    // Rule: Must present a truthful service error state with retry
    expect(content).toMatch(/data-service-state="503"/)
    expect(content).toContain('Dịch vụ cộng đồng đang tạm thời gián đoạn (503)')
  })

  it('bai-viet/[id].vue differentiates 429, 503 and server errors', () => {
    const content = readFileSync(resolve(root, 'pages/bai-viet/[id].vue'), 'utf8')

    // Rule: Must not mask all post fetch errors with a single generic string
    expect(content).not.toContain('message="Lỗi kết nối. Vui lòng thử lại."')

    // Rule: Must compute specific error message differentiating 429 and 503
    expect(content).toContain('postErrorMessage')
    expect(content).toContain('429')
    expect(content).toContain('503')
  })
})
