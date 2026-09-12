import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('Typography Anti-Slop & Editorial Constitution Verification', () => {
  const root = resolve(__dirname, '..')
  const nuxtConfig = readFileSync(resolve(root, 'nuxt.config.ts'), 'utf8')
  const variablesCss = readFileSync(resolve(root, 'assets/css/variables.css'), 'utf8')

  it('declares Lora in @nuxt/fonts configuration in nuxt.config.ts', () => {
    expect(nuxtConfig).toMatch(/\{\s*name:\s*'Lora',\s*provider:\s*'google'\s*\}/)
  })

  it('enforces Lora at front of --font-editorial in variables.css', () => {
    expect(variablesCss).toMatch(/--font-editorial:\s*'Lora'/)
  })

  it('strictly bans Times New Roman from typography variables', () => {
    expect(variablesCss).not.toContain('Times New Roman')
  })
})
