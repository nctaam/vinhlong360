export default defineNuxtRouteMiddleware(async () => {
  const { user, fetchMe } = useAuth()

  if (!user.value) {
    await fetchMe()
  }

  if (!user.value) {
    return navigateTo('/?login=admin')
  }

  if (!['admin', 'superadmin'].includes(user.value.role || '')) {
    return navigateTo('/')
  }
})
