import { describe, expect, it } from 'vitest'
import { extractNuxtCssPaths, extractPageStyleEntries } from './helpers/installHomepageStyles'

describe('Homepage production style installer', () => {
  it('preserves Nuxt CSS paths written with either quote style', () => {
    expect(extractNuxtCssPaths(`export default { css: [
      '~/assets/css/variables.css',
      "~/assets/css/tri-region-color.css",
    ] }`)).toEqual(['variables.css', 'tri-region-color.css'])
  })

  it('preserves every inline and asset style block in page order', () => {
    expect(extractPageStyleEntries(`
      <style>.first { color: red; }</style>
      <style src="~/assets/css/home-nocturne.css"></style>
      <style media='print'>.last { color: black; }</style>
    `)).toEqual([
      { kind: 'inline', css: '.first { color: red; }' },
      { kind: 'asset', path: 'home-nocturne.css' },
      { kind: 'inline', css: '.last { color: black; }' },
    ])
  })

  it('fails loudly when required CSS or Homepage style inputs disappear', () => {
    expect(() => extractNuxtCssPaths('export default {}')).toThrow('Missing Nuxt css array')
    expect(() => extractPageStyleEntries('<template><main /></template>')).toThrow('Homepage contains no style blocks')
    expect(() => extractPageStyleEntries('<style>.only {}</style>')).toThrow('home-nocturne.css style block is missing')
  })
})
