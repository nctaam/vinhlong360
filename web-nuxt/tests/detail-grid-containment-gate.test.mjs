import { describe, expect, it } from 'vitest'

import {
  collectAssetSetFailures,
  collectStateFailures,
  compactGateEvidence,
  hasExactZeroMinWidth,
  isFreshNavigationState,
  isOwnedBrowserProcess,
} from '../scripts/detail-grid-gate-core.mjs'

describe('Detail grid containment gate contracts', () => {
  it('accepts only exact zero-length min-width declarations', () => {
    expect(hasExactZeroMinWidth('display: block; min-width: 0; color: red')).toBe(true)
    expect(hasExactZeroMinWidth('min-width: 0px')).toBe(true)
    expect(hasExactZeroMinWidth('min-width: 0.5rem;')).toBe(false)
    expect(hasExactZeroMinWidth('min-width: 0foo;')).toBe(false)
  })

  it('fails on every non-allowlisted browser error', () => {
    const failures = collectStateFailures({
      console_errors: [
        { source: 'console', message: 'boom', url: '', allowed_reason: '' },
        { source: 'exception', message: 'uncaught', url: '', allowed_reason: '' },
        { source: 'network', message: 'net::ERR_FAILED', url: 'http://127.0.0.1/image.webp', allowed_reason: '' },
      ],
    })

    expect(failures.map(failure => failure.code)).toEqual(['console-errors'])
    expect(failures[0]?.message).toContain('3 relevant browser error(s)')
  })

  it('keeps the narrow auth health-check allowance non-blocking', () => {
    const failures = collectStateFailures({
      console_errors: [{
        source: 'network',
        message: 'Failed to load resource: the server responded with a status of 503 (Service Unavailable)',
        url: 'http://127.0.0.1:4177/auth/me',
        allowed_reason: 'sqlite-lightweight-auth-me-503',
      }],
    })

    expect(failures).toEqual([])
  })

  it('requires the exact new URL, a complete document, and a changed document token', () => {
    const expectedUrl = 'http://127.0.0.1:4177/dia-diem/cong-vien-an-hoi'
    const previousDocumentToken = 'old-document'

    expect(isFreshNavigationState({
      expectedUrl,
      previousDocumentToken,
      href: expectedUrl,
      readyState: 'complete',
      documentToken: 'new-document',
    })).toBe(true)
    expect(isFreshNavigationState({
      expectedUrl,
      previousDocumentToken,
      href: 'about:blank',
      readyState: 'complete',
      documentToken: '',
    })).toBe(false)
    expect(isFreshNavigationState({
      expectedUrl,
      previousDocumentToken,
      href: expectedUrl,
      readyState: 'complete',
      documentToken: previousDocumentToken,
    })).toBe(false)
    expect(isFreshNavigationState({
      expectedUrl,
      previousDocumentToken,
      href: expectedUrl,
      readyState: 'complete',
      documentToken: '',
    })).toBe(false)
    expect(isFreshNavigationState({
      expectedUrl,
      previousDocumentToken,
      href: expectedUrl,
      readyState: 'interactive',
      documentToken: '',
    })).toBe(false)
  })

  it('requires the requested viewport and every collected user-facing behavior to pass', () => {
    const failures = collectStateFailures({
      viewport: { width: 390, height: 844 },
      geometry: {
        viewport: { width: 391, height: 844 },
        hero: {
          cover_rect: { width: 350, height: 260 },
          image_rect: { width: 350, height: 260 },
          image_loaded_class: true,
          image_complete: true,
          image_natural_width: 800,
          image_natural_height: 533,
          image_in_cover: true,
        },
        actions: {
          trip_photo_intersection: { area: 12 },
          photo_hit: { belongs: false },
          trip_hits: [{ belongs: true }],
        },
        contact: { controls: [{ hit: { belongs: false } }] },
        sticky: { rect: { width: 390, height: 64 }, display: 'flex', visibility: 'visible' },
      },
      lightbox: {
        opened: true,
        aria_modal: true,
        surface_visible: true,
        media_visible: true,
        close_hit: { belongs: false },
        closed: false,
      },
      console_errors: [],
    })

    expect(failures.map(failure => failure.code)).toEqual([
      'viewport-mismatch',
      'trip-photo-overlap',
      'photo-hit-owner',
      'contact-hit-owner',
      'sticky-visible',
      'lightbox-close-hit-owner',
      'lightbox-close-failed',
    ])
  })

  it('accepts a stable hero, owned actions, hidden legacy sticky bar, and exercised lightbox', () => {
    expect(collectStateFailures({
      viewport: { width: 390, height: 844 },
      geometry: {
        viewport: { width: 390, height: 844 },
        hero: {
          cover_rect: { width: 350, height: 260 },
          image_rect: { width: 350, height: 260 },
          image_loaded_class: true,
          image_complete: true,
          image_natural_width: 800,
          image_natural_height: 533,
          image_in_cover: true,
        },
        actions: {
          trip_photo_intersection: { area: 0 },
          photo_hit: { belongs: true },
          trip_hits: [{ belongs: true }, { belongs: true }],
        },
        contact: { controls: [{ hit: { belongs: true } }] },
        sticky: { rect: { width: 0, height: 0 }, display: 'none', visibility: 'visible' },
      },
      lightbox: {
        opened: true,
        aria_modal: true,
        surface_visible: true,
        media_visible: true,
        close_hit: { belongs: true },
        closed: true,
      },
      console_errors: [],
    })).toEqual([])
  })

  it('requires CSS and JavaScript assets and one exact state-bound asset set', () => {
    const shared = {
      detail_css_path: '/_nuxt/detail.hash.css',
      asset_paths: ['/_nuxt/app.hash.js', '/_nuxt/detail.hash.css'],
      css_paths: ['/_nuxt/detail.hash.css'],
      js_paths: ['/_nuxt/app.hash.js'],
      fingerprint_sha256: 'a'.repeat(64),
    }
    expect(collectAssetSetFailures([
      { preview_assets: shared },
      { preview_assets: { ...shared, js_paths: [] } },
      { preview_assets: { ...shared, asset_paths: ['/_nuxt/other.hash.js', '/_nuxt/detail.hash.css'], fingerprint_sha256: 'b'.repeat(64) } },
    ]).map(failure => failure.code)).toEqual([
      'asset-binding-incomplete',
      'asset-set-state-mismatch',
    ])

    expect(collectAssetSetFailures([
      { preview_assets: shared },
      { preview_assets: { ...shared } },
    ])).toEqual([])

    expect(collectAssetSetFailures([
      { viewport_name: 'mobile', preview_assets: shared },
      { viewport_name: 'mobile', preview_assets: { ...shared } },
      { viewport_name: 'desktop', preview_assets: { ...shared, asset_paths: ['/_nuxt/desktop.hash.js', '/_nuxt/detail.hash.css'], fingerprint_sha256: 'b'.repeat(64) } },
      { viewport_name: 'desktop', preview_assets: { ...shared, asset_paths: ['/_nuxt/desktop.hash.js', '/_nuxt/detail.hash.css'], fingerprint_sha256: 'b'.repeat(64) } },
    ])).toEqual([])
  })

  it('matches only browser processes bound to the exact owned profile and executable', () => {
    const ownership = {
      profile: 'C:\\Temp\\vl360-detail-grid-owned',
      browserPath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    }

    expect(isOwnedBrowserProcess({
      executablePath: ownership.browserPath,
      commandLine: `"${ownership.browserPath}" --headless=new --user-data-dir="${ownership.profile}"`,
    }, ownership)).toBe(true)
    expect(isOwnedBrowserProcess({
      executablePath: ownership.browserPath,
      commandLine: `"${ownership.browserPath}" --user-data-dir="${ownership.profile}-other"`,
    }, ownership)).toBe(false)
    expect(isOwnedBrowserProcess({
      executablePath: 'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
      commandLine: `msedge.exe --user-data-dir="${ownership.profile}"`,
    }, ownership)).toBe(false)
  })

  it('compacts repeated per-state assets while preserving the exact global asset set', () => {
    const assetPaths = ['/_nuxt/app.hash.js', '/_nuxt/detail.hash.css']
    const evidence = {
      preview_assets: { asset_paths: assetPaths },
      states: [{
        preview_assets: { asset_paths: [...assetPaths], css_paths: [assetPaths[1]], js_paths: [assetPaths[0]] },
        console_errors: [{ message: 'one' }, { message: 'two' }, { message: 'three' }],
        relevant_console_errors: [{ message: 'one' }, { message: 'two' }, { message: 'three' }],
        geometry: { contact: { controls: [{}, {}, {}] } },
      }],
      reasons: Array.from({ length: 14 }, (_, index) => ({ code: String(index) })),
    }

    compactGateEvidence(evidence)

    expect(evidence.preview_assets.asset_paths).toEqual(assetPaths)
    expect(evidence.states[0].preview_assets).toMatchObject({ asset_paths: [], css_paths: [], js_paths: [], asset_set_recorded_globally: true })
    expect(evidence.states[0].console_errors).toHaveLength(2)
    expect(evidence.states[0].geometry.contact.controls).toHaveLength(2)
    expect(evidence.reasons).toHaveLength(12)
  })
})
