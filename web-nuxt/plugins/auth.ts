export default defineNuxtPlugin(async () => {
  const { fetchMe, user } = useAuth()
  const hasServerAuthCookie = import.meta.server
    ? Boolean(useRequestHeaders(['cookie']).cookie?.includes('vl360_token='))
    : true
  if (hasServerAuthCookie && !user.value) {
    await fetchMe()
  }
})
