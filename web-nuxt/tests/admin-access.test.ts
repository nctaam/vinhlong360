import { readFileSync } from 'node:fs'
import { join } from 'node:path'

import { describe, expect, it } from 'vitest'

import {
  canAccessAdminPath,
  firstAdminRoute,
  hasAdminEntry,
  requiredAdminScope,
  resolveAdminScopes,
} from '../utils/adminAccess'
import { ADMIN_NAV_GROUPS, filterAdminNavGroups } from '../utils/adminNavigation'

describe('AdminCP access resolver', () => {
  it('resolves canonical scopes from role and ignores unknown client scopes', () => {
    expect(resolveAdminScopes({ id: 'm1', role: 'moderator' })).toEqual(['moderation.manager'])
    expect(resolveAdminScopes({
      id: 'u1',
      role: 'user',
      admin_scopes: ['content.editor', 'unknown.scope', 'content.editor'],
    })).toEqual(['content.editor'])
    expect(resolveAdminScopes({ id: 's1', role: 'superadmin' })).toEqual(['*'])
  })

  it('ignores malformed scope payloads instead of breaking AdminCP navigation', () => {
    expect(resolveAdminScopes({
      role: 'user',
      admin_scopes: 'moderation.manager' as unknown as string[],
    })).toEqual([])
    expect(resolveAdminScopes({
      role: 'user',
      admin_scopes: { scope: 'content.editor' } as unknown as string[],
    })).toEqual([])
    expect(resolveAdminScopes({
      role: 'moderator',
      admin_scopes: null as unknown as string[],
    })).toEqual(['moderation.manager'])
  })

  it('allows moderator routes and denies unrelated workstreams', () => {
    const scopes = ['moderation.manager'] as const

    expect(hasAdminEntry(scopes)).toBe(true)
    expect(canAccessAdminPath('/admin', scopes)).toBe(true)
    expect(canAccessAdminPath('/admin/kiem-duyet', scopes)).toBe(true)
    expect(canAccessAdminPath('/admin/bao-cao', scopes)).toBe(true)
    expect(canAccessAdminPath('/admin/users', scopes)).toBe(false)
    expect(canAccessAdminPath('/admin/entities', scopes)).toBe(false)
    expect(firstAdminRoute(scopes)).toBe('/admin/kiem-duyet')
  })

  it('uses longest-prefix matching and fails closed for unknown AdminCP paths', () => {
    expect(requiredAdminScope('/admin/cai-dat/seo')).toBe('settings.admin')
    expect(requiredAdminScope('/admin/entities?kind=product')).toBe('content.editor')
    expect(requiredAdminScope('/admin/khong-ton-tai')).toBeNull()
    expect(canAccessAdminPath('/admin/khong-ton-tai', ['*'])).toBe(false)
  })

  it('uses the dashboard only when the actor has operational scope', () => {
    expect(firstAdminRoute(['content.editor', 'moderation.manager'])).toBe('/admin/entities')
    expect(firstAdminRoute(['content.editor', 'moderation.manager', 'ops.deploy'])).toBe('/admin')
    expect(firstAdminRoute(['*'])).toBe('/admin')
    expect(firstAdminRoute([])).toBe('/')
  })

  it('filters navigation to the workstreams granted to a moderator', () => {
    const groups = filterAdminNavGroups(ADMIN_NAV_GROUPS, ['moderation.manager'])
    const ids = groups.flatMap(group => group.items.map(item => item.id))

    expect(ids).toEqual(['moderation', 'reports'])
    expect(ids).not.toContain('users')
    expect(ids).not.toContain('entities-all')
    expect(ids).not.toContain('knowledge-agent')
  })

  it('keeps middleware authorization on the shared access resolver', () => {
    const source = readFileSync(join(process.cwd(), 'middleware', 'admin.ts'), 'utf8')

    expect(source).toContain('resolveAdminScopes')
    expect(source).toContain('canAccessAdminPath')
    expect(source).toContain('firstAdminRoute')
    expect(source).not.toContain("['admin', 'superadmin']")
  })
})
