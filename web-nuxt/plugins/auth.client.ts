export default defineNuxtPlugin(async () => {
  const { fetchMe, token } = useAuth()
  if (token.value) {
    await fetchMe()
  }
})
