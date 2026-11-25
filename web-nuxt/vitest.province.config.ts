import { defineVitestConfig } from '@nuxt/test-utils/config'
import { PROVINCE_TEST_FILES } from './tests/testSuites.mjs'

export default defineVitestConfig({
  test: {
    environment: 'nuxt',
    testTimeout: 30_000,
    hookTimeout: 30_000,
    include: PROVINCE_TEST_FILES.map(file => `tests/${file}`),
    environmentOptions: {
      nuxt: {
        domEnvironment: 'happy-dom',
      },
    },
  },
})
