export default defineNitroPlugin((nitroApp) => {
  nitroApp.hooks.hook('request', (event) => {
    const path = event.path || event.node?.req?.url || ''
    if (path.startsWith('/api/v1/terroir')) {
      event.context._nitro = event.context._nitro || {}
      event.context._nitro.routeRules = {}
    }
  })
})
