import { describe, expect, it } from 'vitest'
import { canAccessAdminPath, firstAdminRoute, resolveAdminScopes } from '../utils/adminAccess'

describe('case admin access', () => {
  it('requires service.operator for correction requests', () => {
    expect(canAccessAdminPath('/admin/yeu-cau', ['service.operator'])).toBe(true)
    expect(canAccessAdminPath('/admin/yeu-cau', ['content.editor'])).toBe(false)
  })
  it('normalizes new scopes and denies unknown scopes', () => {
    expect(resolveAdminScopes({ role: 'user', admin_scopes: ['service.operator', 'wat'] })).toEqual(['service.operator'])
    expect(canAccessAdminPath('/admin/yeu-cau', ['wat'])).toBe(false)
  })
  it.each(['service.operator', 'correction.decide', 'truth.review', 'publication.apply', 'case.supervisor'])('normalizes %s', scope => {
    expect(resolveAdminScopes({ role: 'user', admin_scopes: [scope] })).toEqual([scope])
  })
  it('does not route non-operators to the correction operator page', () => {
    expect(firstAdminRoute(['truth.review'])).toBe('/')
  })
})
