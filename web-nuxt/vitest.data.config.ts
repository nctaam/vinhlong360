import { resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  root: resolve(fileURLToPath(new URL('.', import.meta.url)), '..'),
  test: {
    environment: 'node',
    include: ['tests/*.test.ts'],
    exclude: ['web-nuxt/tests/**', '**/node_modules/**'],
    testTimeout: 30_000,
    hookTimeout: 30_000,
  },
})
