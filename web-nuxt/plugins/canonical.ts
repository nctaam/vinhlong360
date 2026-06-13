export default defineNuxtPlugin(() => {
  const route = useRoute()
  useHead({
    link: [
      { rel: 'canonical', href: computed(() => `https://vinhlong360.vn${route.path}`) },
    ],
  })
})
