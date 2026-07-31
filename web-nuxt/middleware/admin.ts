import {
  canAccessAdminPath,
  firstAdminRoute,
  hasAdminEntry,
  requiredAdminScope,
  resolveAdminScopes,
} from '~/utils/adminAccess'

export default defineNuxtRouteMiddleware(async (to) => {
  const { user, fetchMe } = useAuth()

  if (!user.value) {
    await fetchMe()
  }

  if (!user.value) {
    return navigateTo({ path: '/', query: { login: 'admin', redirect: to.fullPath } })
  }

  const scopes = resolveAdminScopes(user.value)
  if (!hasAdminEntry(scopes)) {
    return navigateTo({ path: '/', query: { login: 'admin' } })
  }

  const landing = firstAdminRoute(scopes)
  if (to.path === '/admin' && landing !== '/admin') {
    return navigateTo(landing)
  }

  if (!canAccessAdminPath(to.path, scopes)) {
    return navigateTo({
      path: '/403',
      query: {
        from: to.path,
        required: requiredAdminScope(to.path) || '',
      },
    })
  }
})
