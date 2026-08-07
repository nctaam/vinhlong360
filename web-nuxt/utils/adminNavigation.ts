import { ADMIN_KINDS, kindByKey } from './adminKinds'
import { firstAdminRoute, type AdminScope } from './adminAccess'

export type AdminBadgeKey = 'moderation' | 'images' | 'unclassified' | 'provisional' | 'reports'

export interface AdminNavItem {
  id: string
  label: string
  to: string | { path: string; query?: Record<string, string> }
  icon: string
  badge?: AdminBadgeKey
  scope?: AdminScope
  prefix?: boolean
  matchKind?: string
  children?: AdminNavItem[]
}

export interface AdminNavGroup {
  id: 'overview' | 'content' | 'community' | 'system'
  label: string
  items: AdminNavItem[]
}

const entityKindItems: AdminNavItem[] = ADMIN_KINDS.map(kind => ({
  id: `kind-${kind.kind}`,
  label: kind.label,
  to: { path: '/admin/entities', query: { kind: kind.kind } },
  icon: kind.icon,
  scope: 'content.editor',
  matchKind: kind.kind,
}))

export const ADMIN_NAV_GROUPS: AdminNavGroup[] = [
  {
    id: 'overview',
    label: 'Tổng quan',
    items: [
      { id: 'dashboard', label: 'Bàn điều phối', to: '/admin', icon: 'layout-dashboard' },
      { id: 'analytics', label: 'Thống kê', to: '/admin/thong-ke', icon: 'chart', scope: 'ops.deploy' },
    ],
  },
  {
    id: 'content',
    label: 'Nội dung & dữ liệu',
    items: [
      {
        id: 'entities-all',
        label: 'Tất cả nội dung',
        to: '/admin/entities',
        icon: 'clipboard-list',
        scope: 'content.editor',
        matchKind: '',
        children: entityKindItems,
      },
      { id: 'unclassified', label: 'Chưa phân loại', to: '/admin/chua-phan-loai', icon: 'pin', badge: 'unclassified', scope: 'content.editor' },
      { id: 'directory', label: 'Danh bạ hành chính', to: '/admin/danh-ba', icon: 'landmark', scope: 'content.editor' },
      { id: 'itineraries', label: 'Lịch trình', to: '/admin/lich-trinh', icon: 'route', scope: 'content.editor' },
      { id: 'data-quality', label: 'Chất lượng dữ liệu', to: '/admin/data-quality', icon: 'database', scope: 'content.editor' },
      { id: 'media', label: 'Thư viện ảnh', to: '/admin/media', icon: 'images', scope: 'content.editor' },
    ],
  },
  {
    id: 'community',
    label: 'Cộng đồng & tin cậy',
    items: [
      { id: 'moderation', label: 'Kiểm duyệt', to: '/admin/kiem-duyet', icon: 'shield-check', badge: 'moderation', scope: 'moderation.manager' },
      { id: 'image-review', label: 'Duyệt ảnh', to: '/admin/duyet-anh', icon: 'images', badge: 'images', scope: 'content.editor' },
      { id: 'users', label: 'Thành viên', to: '/admin/users', icon: 'users', scope: 'security.admin' },
      { id: 'reports', label: 'Báo cáo', to: '/admin/bao-cao', icon: 'flag', badge: 'reports', scope: 'moderation.manager' },
    ],
  },
  {
    id: 'system',
    label: 'Hệ thống',
    items: [
      { id: 'provisional', label: 'Duyệt & công cụ', to: '/admin/duyet-tu-hoc', icon: 'flask', badge: 'provisional', scope: 'content.editor' },
      { id: 'knowledge-agent', label: 'Knowledge Agent', to: '/admin/ai', icon: 'bot', scope: 'ops.deploy' },
      { id: 'audit-log', label: 'Nhật ký', to: '/admin/nhat-ky', icon: 'file-text', scope: 'security.admin' },
      { id: 'settings', label: 'Cài đặt trang', to: '/admin/cai-dat', icon: 'settings', scope: 'settings.admin', prefix: true },
    ],
  },
]

export const ADMIN_PAGE_LABELS: Record<string, string> = {
  '/admin/thong-ke': 'Thống kê',
  '/admin/entities': 'Nội dung',
  '/admin/chua-phan-loai': 'Chưa phân loại',
  '/admin/danh-ba': 'Danh bạ hành chính',
  '/admin/lich-trinh': 'Lịch trình',
  '/admin/data-quality': 'Chất lượng dữ liệu',
  '/admin/kiem-duyet': 'Kiểm duyệt',
  '/admin/duyet-anh': 'Duyệt ảnh',
  '/admin/users': 'Thành viên',
  '/admin/bao-cao': 'Báo cáo',
  '/admin/duyet-tu-hoc': 'Duyệt & công cụ',
  '/admin/ai': 'Knowledge Agent',
  '/admin/nhat-ky': 'Nhật ký',
  '/admin/media': 'Thư viện ảnh',
  '/admin/cai-dat': 'Cài đặt trang',
}

function hasScope(item: AdminNavItem, scopes: readonly string[]) {
  if (item.id === 'dashboard') return firstAdminRoute(scopes) === '/admin'
  return !!item.scope && (scopes.includes('*') || scopes.includes(item.scope))
}

export function filterAdminNavGroups(groups: readonly AdminNavGroup[], scopes: readonly string[]): AdminNavGroup[] {
  return groups.flatMap((group) => {
    const items = group.items
      .filter(item => hasScope(item, scopes))
      .map(item => ({
        ...item,
        children: item.children?.filter(child => hasScope(child, scopes)),
      }))
    return items.length ? [{ ...group, items }] : []
  })
}

export function isAdminNavItemActive(item: AdminNavItem, path: string, kind = ''): boolean {
  const targetPath = typeof item.to === 'string' ? item.to : item.to.path
  const targetKind = item.matchKind ?? (typeof item.to === 'string' ? undefined : item.to.query?.kind)

  if (targetKind !== undefined) return path === targetPath && kind === targetKind
  return item.prefix ? path === targetPath || path.startsWith(`${targetPath}/`) : path === targetPath
}

export function resolveAdminPageLabel(path: string, kind = ''): string {
  if (path === '/admin' || path === '/admin/') return ''
  if (path === '/admin/entities' && kind) return kindByKey(kind)?.label || 'Nội dung'
  if (ADMIN_PAGE_LABELS[path]) return ADMIN_PAGE_LABELS[path]

  const prefix = Object.keys(ADMIN_PAGE_LABELS)
    .filter(candidate => path.startsWith(`${candidate}/`))
    .sort((a, b) => b.length - a.length)[0]
  return prefix ? ADMIN_PAGE_LABELS[prefix]! : ''
}
