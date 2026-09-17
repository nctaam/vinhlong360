import { mountSuspended } from '@nuxt/test-utils/runtime'
import { describe, expect, it } from 'vitest'
import SearchAutocomplete from '../components/SearchAutocomplete.vue'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('Header Editorial De-clutter - Task 1: Compact Search Capsule', () => {
  it('renders search autocomplete with refined compact proportions and kbd hint', async () => {
    const wrapper = await mountSuspended(SearchAutocomplete)
    expect(wrapper.find('input[type="search"]').exists()).toBe(true)
    expect(wrapper.find('.search-kbd-hint').exists()).toBe(true)
    expect(wrapper.find('.search-kbd-hint').text()).toBe('/')
  })

  it('enforces 32px height and compact adaptive width in shell.css', () => {
    const css = readFileSync(resolve(__dirname, '../assets/css/shell.css'), 'utf8')
    expect(css).toMatch(/\.public-shell-search\s+input\s*\{[^}]*height:\s*32px;/)
    expect(css).toMatch(/\.public-shell-search\s*\{[^}]*max-width:\s*220px;/)
  })
})

describe('Header Editorial De-clutter - Task 2: Seamless Editorial Navigation', () => {
  it('unifies catalog button typography with nav links and removes heavy boxed container', () => {
    const css = readFileSync(resolve(__dirname, '../assets/css/shell.css'), 'utf8')
    expect(css).toMatch(/\.public-shell-inline-nav\s*\{[^}]*gap:\s*var\(--space-3\);/)
    expect(css).toMatch(/\.public-shell-catalog-button\s*\{[^}]*background:\s*transparent;/)
    expect(css).toContain('--radius-control-refined')
  })
})

