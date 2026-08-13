import { describe, expect, it } from 'vitest'
import { canAccessAdminPath, resolveAdminScopes } from '../utils/adminAccess'

describe('case admin access', () => {
  it('requires service.operator for correction requests', () => {
    expect(canAccessAdminPath('/admin/yeu-cau', ['service.operator'])).toBe(true)
    expect(canAccessAdminPath('/admin/yeu-cau', ['content.editor'])).toBe(false)
  })
  it('normalizes new scopes and denies unknown scopes', () => {
    expect(resolveAdminScopes({ role: 'user', admin_scopes: ['service.operator', 'wat'] })).toEqual(['service.operator'])
    expect(canAccessAdminPath('/admin/yeu-cau', ['wat'])).toBe(false)
  })
})
