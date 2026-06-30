export default defineNuxtPlugin(async () => {
  const { fetchMe, token, user } = useAuth()
  if (token.value && !user.value) {
    await fetchMe()
  }
})
