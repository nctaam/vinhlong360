import type { User } from '~/types'

export const ADMIN_SCOPES = [
  'content.editor',
  'moderation.manager',
  'ops.deploy',
  'settings.admin',
  'security.admin',
] as const

export type AdminScope = typeof ADMIN_SCOPES[number]
export type AdminScopeGrant = AdminScope | '*'
export type AdminActor = Partial<Pick<User, 'id' | 'role' | 'admin_scopes'>>

const ADMIN_SCOPE_SET = new Set<string>(ADMIN_SCOPES)

const ROLE_SCOPES: Record<string, readonly AdminScopeGrant[]> = {
  moderator: ['moderation.manager'],
  admin: ADMIN_SCOPES,
  superadmin: ['*'],
}

const ADMIN_ROUTE_SCOPE_RULES: Array<readonly [string, AdminScope]> = [
  ['/admin/cai-dat', 'settings.admin'],
  ['/admin/chua-phan-loai', 'content.editor'],
  ['/admin/data-quality', 'content.editor'],
  ['/admin/duyet-tu-hoc', 'content.editor'],
  ['/admin/duyet-anh', 'content.editor'],
  ['/admin/kiem-duyet', 'moderation.manager'],
  ['/admin/lich-trinh', 'content.editor'],
  ['/admin/thong-ke', 'ops.deploy'],
  ['/admin/danh-ba', 'content.editor'],
  ['/admin/bao-cao', 'moderation.manager'],
  ['/admin/entities', 'content.editor'],
  ['/admin/nhat-ky', 'security.admin'],
  ['/admin/media', 'content.editor'],
  ['/admin/users', 'security.admin'],
  ['/admin/ai', 'ops.deploy'],
]
ADMIN_ROUTE_SCOPE_RULES.sort((a, b) => b[0].length - a[0].length)

const FIRST_ROUTE_BY_SCOPE: Record<AdminScope, string> = {
  'content.editor': '/admin/entities',
  'moderation.manager': '/admin/kiem-duyet',
  'ops.deploy': '/admin/thong-ke',
  'settings.admin': '/admin/cai-dat',
  'security.admin': '/admin/users',
}

function normalizeAdminPath(path: string) {
  const clean = `/${String(path || '').split(/[?#]/, 1)[0]!.replace(/^\/+|\/+$/g, '')}`
  return clean === '/' ? '/admin' : clean
}

function normalizeScopeValues(values: readonly unknown[] = []): AdminScopeGrant[] {
  const result = new Set<AdminScopeGrant>()
  for (const value of values) {
    if (value === '*') return ['*']
    if (typeof value === 'string' && ADMIN_SCOPE_SET.has(value)) result.add(value as AdminScope)
  }
  return [...result].sort()
}

export function resolveAdminScopes(user: AdminActor | null | undefined): AdminScopeGrant[] {
  if (!user) return []
  const roleScopes = ROLE_SCOPES[String(user.role || '')] || []
  const explicitScopes = Array.isArray(user.admin_scopes) ? user.admin_scopes : []
  return normalizeScopeValues([...roleScopes, ...explicitScopes])
}

export function hasAdminEntry(scopes: readonly string[]): boolean {
  return scopes.includes('*') || scopes.some(scope => ADMIN_SCOPE_SET.has(scope))
}

export function requiredAdminScope(path: string): AdminScope | null {
  const normalized = normalizeAdminPath(path)
  if (normalized === '/admin') return null
  const rule = ADMIN_ROUTE_SCOPE_RULES.find(([prefix]) => normalized === prefix || normalized.startsWith(`${prefix}/`))
  return rule?.[1] || null
}

export function canAccessAdminPath(path: string, scopes: readonly string[]): boolean {
  const normalized = normalizeAdminPath(path)
  if (normalized === '/admin') return hasAdminEntry(scopes)
  const required = requiredAdminScope(normalized)
  if (!required) return false
  return scopes.includes('*') || scopes.includes(required)
}

export function firstAdminRoute(scopes: readonly string[]): string {
  const normalized = normalizeScopeValues(scopes)
  if (!normalized.length) return '/'
  if (normalized.includes('*') || normalized.includes('ops.deploy')) return '/admin'
  return FIRST_ROUTE_BY_SCOPE[normalized[0] as AdminScope] || '/'
}
