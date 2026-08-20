// Scope decides what the screen offers; the server decides what happens.
//
// These pin the navigation entry, the page's scope gate, and the rule that a
// hidden control is a tidiness measure — the composable never pre-authorizes,
// and a forged click still travels to the backend to be refused there.

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

import { canAccessAdminPath } from '../utils/adminAccess'
import { ADMIN_NAV_GROUPS } from '../utils/adminNavigation'

function source(relative: string): string {
  return readFileSync(resolve(__dirname, '..', relative), 'utf8')
}

describe('navigation', () => {
  it('offers the workbench to operators, under its own scope', () => {
    const items = ADMIN_NAV_GROUPS.flatMap(group => group.items)
    const entry = items.find(item => item.to === '/admin/yeu-cau')

    expect(entry).toBeTruthy()
    expect(entry!.scope).toBe('service.operator')
  })

  it('routes /admin/yeu-cau by the operator scope', () => {
    expect(canAccessAdminPath('/admin/yeu-cau', ['service.operator'])).toBe(true)
    expect(canAccessAdminPath('/admin/yeu-cau', ['content.editor'])).toBe(false)
  })
})

describe('the page', () => {
  const page = source('pages/admin/yeu-cau.vue')

  it('derives action visibility from held scopes', () => {
    expect(page).toContain(':scopes="scopes"')
    expect(page).toContain("scopes.includes('service.operator')")
  })

  it('sends the on-screen revision with every stateful command', () => {
    for (const marker of ['expected_revision', 'expected_case_revision']) {
      expect(page).toContain(marker)
    }
  })

  it('treats a conflict as a reload plus a human decision', () => {
    expect(page).toContain('RevisionConflictError')
    // No automatic retry mechanics: the person re-applies, or does not. Prose
    // may say "retrying"; code that does it may not.
    expect(page).not.toMatch(/[.]retry[(]|while\s*[(]|setTimeout[(][^)]*run/)
  })
})

describe('hidden is not authorized', () => {
  it('the composable forwards every command to the server unconditionally', () => {
    const composable = source('composables/useAdminCases.ts')

    // No scope check before a command: the client may hide a button, but the
    // decision to refuse belongs to the backend alone. A local check here
    // would drift from the server's table and become the real (wrong) gate.
    expect(composable).not.toContain('scopes')
    expect(composable).not.toContain('may_perform')
  })
})

describe('an empty queue that is not empty', () => {
  const page = readFileSync(resolve(__dirname, '..', 'pages', 'admin', 'yeu-cau.vue'), 'utf8')

  it('tells the operator when the queue was refused, not just nothing', () => {
    // `loadQueue().catch(() => {})` made a 403 look exactly like a quiet
    // morning, and an operator without the scope would never learn why.
    expect(page).not.toContain('cases.loadQueue().catch(() => {})')
    expect(page).toContain('data-role="queue-failure"')
    expect(page).toContain('chưa có quyền xử lý yêu cầu')
  })

  it('separates a missing permission from a broken connection', () => {
    expect(page).toContain('statusCode === 403')
    expect(page).toContain('Không tải được hàng đợi')
  })
})
