import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'
import UsersPage from '../pages/admin/users.vue'
import AuditLogPage from '../pages/admin/nhat-ky.vue'

const mocks = vi.hoisted(() => ({
  downloadBlob: vi.fn(),
  fetch: vi.fn(),
  showToast: vi.fn(),
}))

mockNuxtImport('useAuth', () => () => ({
  authHeaders: () => ({ 'X-Admin-Key': 'test-key' }),
  fetchMe: vi.fn(),
  user: { value: null },
}))
mockNuxtImport('useToast', () => () => ({ show: mocks.showToast }))
mockNuxtImport('downloadBlob', () => mocks.downloadBlob)

async function flushUi() {
  await new Promise(resolve => setTimeout(resolve, 0))
  await nextTick()
}

async function downloadedCsv(): Promise<string> {
  expect(mocks.downloadBlob).toHaveBeenCalledTimes(1)
  const [blob] = mocks.downloadBlob.mock.calls[0] as [Blob, string]
  return blob.text()
}

beforeEach(() => {
  mocks.downloadBlob.mockReset()
  mocks.fetch.mockReset()
  mocks.showToast.mockReset()
  vi.stubGlobal('$fetch', mocks.fetch)
})

describe('admin CSV exports', () => {
  it('exports user-controlled formula prefixes as literal text and preserves Unicode CSV quoting', async () => {
    const names = [
      '=SUM(1,1)',
      '+cmd',
      '-1',
      '@lookup',
      '\tcommand',
      '\rcommand',
      'Bình "An", Trà Vinh',
    ]
    mocks.fetch.mockResolvedValue({
      users: names.map((display_name, index) => ({
        id: `user-${index}`,
        display_name,
        phone: `090000000${index}`,
        role: 'user',
        is_banned: false,
        created_at: '',
      })),
      total: names.length,
    })

    const wrapper = await mountSuspended(UsersPage)
    await flushUi()
    await wrapper.get('.usr-head-actions .admin-refresh').trigger('click')
    const csv = await downloadedCsv()

    expect(csv).toContain('"\'=SUM(1,1)"')
    expect(csv).toContain("'+cmd")
    expect(csv).toContain("'-1")
    expect(csv).toContain("'@lookup")
    expect(csv).toContain("'\tcommand")
    expect(csv).toContain('"\'\rcommand"')
    expect(csv).toContain('"Bình ""An"", Trà Vinh"')
    wrapper.unmount()
  })

  it('neutralizes every dangerous audit-log prefix without changing columns or ordinary CSV data', async () => {
    mocks.fetch.mockResolvedValue({
      entries: [
        { ts: '\t2026-07-26', method: '@PATCH', path: '=HYPERLINK("x")', actor: '+admin', ip: '-1.2.3.4' },
        { ts: '\r2026-07-26', method: 'POST', path: '/đường, "mới"', actor: 'Nguyễn Văn A', ip: '127.0.0.1' },
      ],
      total: 2,
    })

    const wrapper = await mountSuspended(AuditLogPage)
    await flushUi()
    await wrapper.get('button.btn.btn-outline.btn-sm').trigger('click')
    const csv = await downloadedCsv()

    expect(csv).toContain("'\t2026-07-26,'@PATCH")
    expect(csv).toContain('"\'=HYPERLINK(""x"")"')
    expect(csv).toContain("'+admin,'-1.2.3.4")
    expect(csv).toContain('"\'\r2026-07-26"')
    expect(csv).toContain('"/đường, ""mới"""')
    expect(csv.split('\n', 1)[0]).toBe('\uFEFFThời gian,Method,Path,Actor,IP')
    wrapper.unmount()
  })
})
