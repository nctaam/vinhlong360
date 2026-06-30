export default defineNuxtRouteMiddleware(async () => {
  const { user, fetchMe, token } = useAuth()

  if (!user.value && token.value) {
    await fetchMe()
  }

  if (!user.value) {
    return navigateTo('/?login=admin')
  }

  if (user.value.role !== 'admin') {
    return navigateTo('/')
  }
})
