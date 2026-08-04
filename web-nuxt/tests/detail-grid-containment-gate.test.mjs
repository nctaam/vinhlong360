import { EventEmitter } from 'node:events'
import { createHash } from 'node:crypto'
import { existsSync, mkdtempSync, readFileSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { PassThrough } from 'node:stream'
import { describe, expect, it, vi } from 'vitest'

import * as gateCore from '../scripts/detail-grid-gate-core.mjs'

import {
  captureThemeBoundAssets,
  classifyOwnedProcessTree,
  collectAssetSetFailures,
  collectStateFailures,
  compactGateEvidence,
  hasExactZeroMinWidth,
  hasStableOwnedHit,
  isFreshNavigationState,
  isOwnedBrowserProcess,
  matchesProcessIdentity,
  ownedBrowserProcessIds,
  runCaptured,
} from '../scripts/detail-grid-gate-core.mjs'

const LINUX_STAT = '4321 (node worker) S 123 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 987654321 19 20'
const LINUX_COMMAND_LINE = 'node\0worker.js\0vl360-linux-owned\0'
const LINUX_IDENTITY = Object.freeze({
  pid: 4321,
  parentPid: 123,
  startIdentity: 'linux:proc-start-ticks:987654321',
  executablePath: '/usr/bin/node',
  commandLine: LINUX_COMMAND_LINE,
  argv: ['node', 'worker.js', 'vl360-linux-owned'],
})

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

  it('normalizes only a fully ready SQLite or PostgreSQL readiness authority', () => {
    expect(typeof gateCore.normalizeReadinessBackend).toBe('function')
    const { normalizeReadinessBackend } = gateCore
    const validChecks = {
      database: true,
      schema: true,
      schema_version: { backend: 'sqlite' },
    }

    expect(normalizeReadinessBackend({ status: 200, payload: { ready: true, checks: validChecks } })).toBe('sqlite')
    expect(normalizeReadinessBackend({
      status: 200,
      payload: { ready: true, checks: { ...validChecks, schema_version: { backend: 'postgres' } } },
    })).toBe('postgres')

    for (const candidate of [
      { status: 503, payload: { ready: true, checks: validChecks } },
      { status: 200, payload: { ready: false, checks: validChecks } },
      { status: 200, payload: { ready: true, checks: { ...validChecks, database: false } } },
      { status: 200, payload: { ready: true, checks: { ...validChecks, schema: false } } },
      { status: 200, payload: { ready: true, checks: { ...validChecks, schema_version: { backend: 'postgresql' } } } },
      { status: 200, payload: { ready: true, checks: { ...validChecks, schema_version: null } } },
      { status: 200, payload: null },
    ]) {
      expect(normalizeReadinessBackend(candidate)).toBe('')
    }
  })

  it('classifies only the two exact same-origin entity-feed 503s when readiness proves SQLite', () => {
    expect(typeof gateCore.classifyBrowserError).toBe('function')
    const { classifyBrowserError } = gateCore
    const message = 'Failed to load resource: the server responded with a status of 503 (Service Unavailable)'
    const context = { baseUrl: 'http://127.0.0.1:4177', databaseBackend: 'sqlite' }
    const classify = entry => classifyBrowserError(entry, context)

    expect(classify({
      source: 'network',
      message,
      url: 'http://127.0.0.1:4177/api/entities/cong-vien-an-hoi/feed?limit=5',
    })).toBe('sqlite-lightweight-entity-feed-503')
    expect(classify({
      source: 'network',
      message,
      url: 'http://127.0.0.1:4177/api/entities/cong-vien-an-hoi/feed?limit=10&page=1',
    })).toBe('sqlite-lightweight-entity-feed-503')

    const rejected = [
      [{ source: 'network', message, url: 'http://127.0.0.1:4177/api/entities/cong-vien-an-hoi/feed?limit=5' }, { ...context, databaseBackend: '' }],
      [{ source: 'network', message, url: 'http://127.0.0.1:4177/api/entities/cong-vien-an-hoi/feed?limit=5' }, { ...context, databaseBackend: 'postgres' }],
      [{ source: 'console', message, url: 'http://127.0.0.1:4177/api/entities/cong-vien-an-hoi/feed?limit=5' }, context],
      [{ source: 'network', message, url: 'http://example.test/api/entities/cong-vien-an-hoi/feed?limit=5' }, context],
      [{ source: 'network', message, url: 'http://127.0.0.1:4177/api/entities/other/feed?limit=5' }, context],
      [{ source: 'network', message, url: 'http://127.0.0.1:4177/api/entities/cong-vien-an-hoi/feed/extra?limit=5' }, context],
      [{ source: 'network', message: 'Failed to load resource: the server responded with a status of 500 (Internal Server Error)', url: 'http://127.0.0.1:4177/api/entities/cong-vien-an-hoi/feed?limit=5' }, context],
      [{ source: 'network', message, url: 'http://127.0.0.1:4177/api/entities/cong-vien-an-hoi/feed' }, context],
      [{ source: 'network', message, url: 'http://127.0.0.1:4177/api/entities/cong-vien-an-hoi/feed?limit=10' }, context],
      [{ source: 'network', message, url: 'http://127.0.0.1:4177/api/entities/cong-vien-an-hoi/feed?page=1&limit=10&sort=newest' }, context],
      [{ source: 'network', message, url: 'http://127.0.0.1:4177/api/entities/cong-vien-an-hoi/feed?page=1&page=1&limit=10' }, context],
      [{ source: 'network', message, url: 'http://127.0.0.1:4177/api/entities/cong-vien-an-hoi/feed?limit=5&limit=5' }, context],
      [{ source: 'exception', message: 'uncaught', url: '' }, context],
    ]

    for (const [entry, candidateContext] of rejected) {
      expect(classifyBrowserError(entry, candidateContext)).toBe('')
    }
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
          trip_control_count: 3,
          trip_hits: [{ belongs: true }, { belongs: true }, { belongs: true }],
        },
        contact: {
          metric: { rect: { width: 390, height: 73 }, display: 'block', visibility: 'visible' },
          controls: [{ hit: { present: true, visible: true, belongs: false, stable: false } }],
        },
        bottom_nav: {
          metric: { rect: { width: 390, height: 64 }, display: 'grid', visibility: 'visible' },
          contact_intersection: { area: 0 },
          items: Array.from({ length: 5 }, () => ({ hit: { present: true, visible: true, belongs: true, stable: true } })),
        },
        bottom_reservation: { required_px: 137, main_padding_bottom_px: 145, footer_padding_bottom_px: 201 },
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
          trip_control_count: 3,
          trip_hits: [{ belongs: true }, { belongs: true }, { belongs: true }],
        },
        contact: {
          metric: { rect: { width: 390, height: 73 }, display: 'block', visibility: 'visible' },
          controls: [{ hit: { present: true, visible: true, belongs: true, stable: true } }],
        },
        bottom_nav: {
          metric: { rect: { width: 390, height: 64 }, display: 'grid', visibility: 'visible' },
          contact_intersection: { area: 0 },
          items: Array.from({ length: 5 }, () => ({ hit: { present: true, visible: true, belongs: true, stable: true } })),
        },
        bottom_reservation: { required_px: 137, main_padding_bottom_px: 145, footer_padding_bottom_px: 201 },
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

  it('fails closed when route-owned trip controls or the hidden sticky contract disappear', () => {
    const failures = collectStateFailures({
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
          trip_control_count: 0,
          trip_hits: [],
        },
        contact: {
          metric: { rect: { width: 390, height: 73 }, display: 'block', visibility: 'visible' },
          controls: [{ hit: { present: true, visible: true, belongs: true, stable: true } }],
        },
        bottom_nav: {
          metric: { rect: { width: 390, height: 64 }, display: 'grid', visibility: 'visible' },
          contact_intersection: { area: 0 },
          items: Array.from({ length: 5 }, () => ({ hit: { present: true, visible: true, belongs: true, stable: true } })),
        },
        bottom_reservation: { required_px: 137, main_padding_bottom_px: 145, footer_padding_bottom_px: 201 },
        sticky: null,
      },
      lightbox: {
        opened: true,
        aria_modal: true,
        surface_visible: true,
        media_visible: true,
        close_hit: { belongs: true, stable: true },
        closed: true,
      },
      console_errors: [],
    })

    expect(failures.map(failure => failure.code)).toEqual([
      'trip-controls-missing',
      'sticky-contract-missing',
    ])
  })

  it('fails when the mobile fixed action stack overlaps or lacks stable center ownership', () => {
    const failures = collectStateFailures({
      viewport_name: 'mobile',
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
          trip_control_count: 3,
          trip_hits: [{ belongs: true }, { belongs: true }, { belongs: true }],
        },
        contact: {
          metric: { rect: { width: 390, height: 73 }, display: 'block', visibility: 'visible' },
          controls: [{ hit: { present: true, visible: true, belongs: true, stable: false } }],
        },
        bottom_nav: {
          metric: { rect: { width: 390, height: 64 }, display: 'grid', visibility: 'visible' },
          contact_intersection: { area: 17160 },
          items: [
            { hit: { present: true, visible: true, belongs: true, stable: true } },
            { hit: { present: true, visible: true, belongs: false, stable: false } },
          ],
        },
        bottom_reservation: { required_px: 137, main_padding_bottom_px: 145, footer_padding_bottom_px: 201 },
        sticky: { rect: { width: 0, height: 0 }, display: 'none', visibility: 'visible' },
      },
      console_errors: [],
    })

    expect(failures.map(failure => failure.code)).toEqual([
      'contact-hit-owner',
      'contact-bottom-nav-overlap',
      'bottom-nav-items-missing',
      'bottom-nav-hit-owner',
    ])
  })

  it('requires consecutive owned lightbox close samples before interaction', () => {
    const owned = { present: true, visible: true, belongs: true, tag: 'button.lb-close' }
    const blocked = { present: true, visible: true, belongs: false, tag: 'img.lb-img' }

    expect(hasStableOwnedHit([owned], 3)).toBe(false)
    expect(hasStableOwnedHit([blocked, owned, owned, owned], 3)).toBe(true)
    expect(hasStableOwnedHit([owned, blocked, owned], 3)).toBe(false)
  })

  it('requires CSS and JavaScript assets and one exact state-bound asset set', () => {
    const shared = {
      detail_css_path: '/_nuxt/detail.hash.css',
      asset_paths: ['/_nuxt/app.hash.js', '/_nuxt/detail.hash.css'],
      css_paths: ['/_nuxt/detail.hash.css'],
      js_paths: ['/_nuxt/app.hash.js'],
      fingerprint_sha256: 'a'.repeat(64),
      theme_binding: {
        capture_started_before_navigation: true,
        opposite_mode_seeded_before_navigation: true,
        opposite_mode_confirmed_before_click: true,
        target_control_hit_owned: true,
        physical_transition_observed: true,
        requested_mode_selected_before_finalize: true,
        stable_readiness_before_finalize: true,
        requested_mode_revalidated_after_finalize: true,
      },
    }
    expect(collectAssetSetFailures([
      { preview_assets: shared },
      { preview_assets: { ...shared, js_paths: [] } },
      {
        preview_assets: {
          ...shared,
          asset_paths: ['/_nuxt/other.hash.js', '/_nuxt/detail.hash.css'],
          fingerprint_sha256: 'b'.repeat(64),
          theme_binding: { ...shared.theme_binding, physical_transition_observed: false },
        },
      },
    ]).map(failure => failure.code)).toEqual([
      'asset-binding-incomplete',
      'asset-theme-binding-incomplete',
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

  it('keeps asset capture open through an opposite-to-requested physical theme transition and stable readiness', async () => {
    const events = []
    const capture = eventCapture(events)

    const result = await captureThemeBoundAssets({
      capture,
      navigate: async () => { events.push('navigate') },
      assertOppositeTheme: async () => {
        events.push('theme:opposite')
        return { stored: 'dark' }
      },
      applyRequestedTheme: async () => {
        events.push('theme:apply')
        return { stored: 'light', transitionObserved: true }
      },
      waitForStableReadiness: async () => { events.push('theme:stable'); return { ready: true } },
      revalidateRequestedTheme: async phase => { events.push('theme:' + phase); return { ready: true } },
    })

    expect(events).toEqual([
      'capture:start',
      'navigate',
      'theme:opposite',
      'theme:apply',
      'theme:stable',
      'theme:before-finalize',
      'capture:verify',
      'theme:after-finalize',
      'capture:stop',
    ])
    expect(result).toEqual({
      oppositeThemeState: { stored: 'dark' },
      themeState: { stored: 'light', transitionObserved: true },
      stableReadinessState: { ready: true },
      preFinalizeThemeState: { ready: true },
      postFinalizeThemeState: { ready: true },
      previewAssets: { fingerprint_sha256: 'a'.repeat(64) },
    })
  })

  it.each([
    { phase: 'before-finalize', message: 'requested theme reverted before asset verification', verifies: false },
    { phase: 'after-finalize', message: 'requested theme reverted after fingerprint finalization', verifies: true },
  ])('fails when requested theme readiness reverts $phase', async ({ phase, message, verifies }) => {
    const events = []
    const capture = eventCapture(events)

    await expect(captureThemeBoundAssets({
      capture,
      navigate: async () => { events.push('navigate') },
      assertOppositeTheme: async () => ({ stored: 'dark' }),
      applyRequestedTheme: async () => ({ stored: 'light', transitionObserved: true }),
      waitForStableReadiness: async () => { events.push('theme:stable'); return { ready: true } },
      revalidateRequestedTheme: async observedPhase => {
        events.push('theme:' + observedPhase)
        if (observedPhase === phase) throw new Error(message)
        return { ready: true }
      },
    })).rejects.toThrow(message)

    expect(events).toEqual([
      'capture:start',
      'navigate',
      'theme:stable',
      'theme:before-finalize',
      ...(verifies ? ['capture:verify', 'theme:after-finalize'] : []),
      'capture:stop',
    ])
  })

  it('requires multiple consecutive requested-theme readiness samples and resets on a transient revert', async () => {
    const samples = [
      { ready: true, sequence: 1 },
      { ready: false, sequence: 2 },
      { ready: true, sequence: 3 },
      { ready: true, sequence: 4 },
      { ready: true, sequence: 5 },
    ]
    const waits = []
    let sampleIndex = 0

    const result = await gateCore.waitForStableCondition({
      sample: async () => samples[Math.min(sampleIndex++, samples.length - 1)],
      isReady: value => value.ready,
      requiredConsecutive: 3,
      intervalMs: 25,
      timeoutMs: 1000,
      wait: async ms => { waits.push(ms) },
    })

    expect(result).toEqual({ value: samples[4], consecutive: 3, requiredConsecutive: 3 })
    expect(sampleIndex).toBe(5)
    expect(waits).toEqual([25, 25, 25, 25])
  })

  it('matches only browser processes bound to the exact owned profile and executable', () => {
    const ownership = {
      profile: 'C:\\Temp\\vl360-detail-grid-owned',
      browserPath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
      marker: 'vl360-detail-grid-gate-unique-42',
    }

    expect(isOwnedBrowserProcess({
      executablePath: ownership.browserPath,
      commandLine: `"${ownership.browserPath}" --headless=new --user-data-dir="${ownership.profile}" --vl360-gate-marker=${ownership.marker}`,
    }, ownership)).toBe(true)
    expect(isOwnedBrowserProcess({
      executablePath: ownership.browserPath,
      commandLine: `"${ownership.browserPath}" --user-data-dir="${ownership.profile}-other" --vl360-gate-marker=${ownership.marker}`,
    }, ownership)).toBe(false)
    expect(isOwnedBrowserProcess({
      executablePath: 'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
      commandLine: `msedge.exe --user-data-dir="${ownership.profile}" --vl360-gate-marker=${ownership.marker}`,
    }, ownership)).toBe(false)
    expect(isOwnedBrowserProcess({
      executablePath: ownership.browserPath,
      commandLine: `"${ownership.browserPath}" --user-data-dir="${ownership.profile}" --vl360-gate-marker=another-invocation`,
    }, ownership)).toBe(false)

    expect(ownedBrowserProcessIds([
      { pid: 11, executablePath: ownership.browserPath, commandLine: `chrome.exe --user-data-dir="${ownership.profile}" --vl360-gate-marker=${ownership.marker}` },
      { pid: 12, executablePath: ownership.browserPath, commandLine: `chrome.exe --user-data-dir="${ownership.profile}-other" --vl360-gate-marker=${ownership.marker}` },
      { pid: 13, executablePath: 'C:\\Other\\chrome.exe', commandLine: `chrome.exe --user-data-dir="${ownership.profile}" --vl360-gate-marker=${ownership.marker}` },
    ], ownership)).toEqual([11])
  })

  it('resets stable-empty cleanup when a late reparented owned process appears during quiescence', async () => {
    const lateIdentity = {
      pid: 402,
      parentPid: 1,
      startIdentity: 'win:utc-ticks:639213500000000000',
      executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
      commandLine: 'chrome.exe --vl360-gate-marker=late-owned',
    }
    const snapshots = [[], [lateIdentity], [lateIdentity], [], [], []]
    const terminated = []
    const waits = []
    let snapshotIndex = 0

    const remaining = await gateCore.cleanupOwnedProcessSet({
      listOwnedProcesses: async () => snapshots[Math.min(snapshotIndex++, snapshots.length - 1)],
      terminateOwnedProcesses: async identities => { terminated.push(...identities) },
      timeoutMs: 5000,
      wait: async ms => { waits.push(ms) },
    })

    expect(terminated).toEqual([lateIdentity, lateIdentity])
    expect(snapshotIndex).toBe(6)
    expect(waits.filter(ms => ms > 0)).toHaveLength(5)
    expect(remaining).toEqual([])
  })

  it('returns the third full stable-empty snapshot without a redundant verification capture', async () => {
    const unrelated = {
      pid: 901,
      parentPid: 1,
      startIdentity: 'win:utc-ticks:639213500000000901',
      executablePath: 'C:\\Windows\\System32\\conhost.exe',
      commandLine: 'conhost.exe 0x4',
    }
    const lateOwned = {
      pid: 902,
      parentPid: 1,
      startIdentity: 'win:utc-ticks:639213500000000902',
      executablePath: 'C:\\Program Files\\nodejs\\node.exe',
      commandLine: 'node.exe worker.js vl360-owned',
    }
    const snapshots = [[lateOwned, unrelated], [unrelated], [unrelated], [unrelated]]
    const terminated = []
    let snapshotIndex = 0

    const finalSnapshot = await gateCore.waitForStableEmptyProcessSnapshot({
      captureSnapshot: async () => {
        if (snapshotIndex >= snapshots.length) throw new Error('redundant verification snapshot')
        return snapshots[snapshotIndex++]
      },
      selectOwnedProcesses: snapshot => snapshot.filter(identity => identity.commandLine.includes('vl360-owned')),
      terminateOwnedProcesses: async identities => { terminated.push(...identities) },
      timeoutMs: 5000,
      wait: async () => {},
    })

    expect(finalSnapshot).toBe(snapshots[3])
    expect(snapshotIndex).toBe(4)
    expect(terminated).toEqual([lateOwned])
  })

  it('rejects PID reuse and classifies only marker-owned descendants of the captured process identity', () => {
    const marker = 'vl360-owned-process-42'
    const root = {
      pid: 101,
      parentPid: 50,
      startIdentity: 'win:utc-ticks:639213480000000000',
      executablePath: 'C:\\Program Files\\nodejs\\node.exe',
      commandLine: `node.exe parent.js ${marker}`,
    }
    const child = {
      pid: 102,
      parentPid: 101,
      startIdentity: 'win:utc-ticks:639213480010000000',
      executablePath: root.executablePath,
      commandLine: `node.exe child.js ${marker}`,
    }
    const reusedRoot = { ...root, startIdentity: 'win:utc-ticks:639213480600000000' }
    const unrelatedChild = { ...child, pid: 103, commandLine: 'node.exe unrelated.js' }

    expect(matchesProcessIdentity(root, { ...root })).toBe(true)
    expect(matchesProcessIdentity(root, reusedRoot)).toBe(false)
    expect(classifyOwnedProcessTree(root, [reusedRoot, child], marker)).toEqual({ owned: [], unverified: [] })
    expect(classifyOwnedProcessTree(root, [root, child, unrelatedChild], marker)).toEqual({
      owned: [root, child],
      unverified: [unrelatedChild],
    })
  })

  it('distinguishes identities created in the same PID and second at different subsecond ticks', () => {
    const base = {
      pid: 101,
      parentPid: 50,
      startIdentity: 'win:utc-ticks:639213499535606110',
      executablePath: 'C:\\Program Files\\nodejs\\node.exe',
      commandLine: 'node.exe worker.js',
    }
    const sameSecondDifferentSubsecond = {
      ...base,
      startIdentity: 'win:utc-ticks:639213499539999999',
    }

    expect(matchesProcessIdentity(base, { ...base })).toBe(true)
    expect(matchesProcessIdentity(base, sameSecondDifferentSubsecond)).toBe(false)
  })

  it('parses Linux proc stat start ticks even when the process name contains spaces and parentheses', () => {
    const stat = '4321 (node worker (qa)) S 123 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 987654321 19 20'

    expect(gateCore.parseLinuxProcStat(stat)).toEqual({
      pid: 4321,
      parentPid: 123,
      startTicks: '987654321',
    })
  })

  it('treats a vanished Linux proc identity as gone instead of rejecting the helper', async () => {
    const missing = Object.assign(new Error('gone'), { code: 'ENOENT' })

    await expect(gateCore.readLinuxProcessIdentity(4321, {
      readFile: async () => { throw missing },
      readlink: async () => { throw missing },
    })).resolves.toBeNull()
  })

  it('captures a complete Linux identity and fails closed when proc reads exceed their deadline', async () => {
    const commandLine = Buffer.from(LINUX_COMMAND_LINE)
    const io = {
      readFile: async path => path.endsWith('/stat') ? LINUX_STAT : commandLine,
      readlink: async () => '/usr/bin/node',
      timeoutMs: 1000,
    }

    await expect(gateCore.readLinuxProcessIdentity(4321, io)).resolves.toEqual(LINUX_IDENTITY)

    const slowIo = {
      readFile: async path => {
        await sleep(100)
        return path.endsWith('/stat') ? LINUX_STAT : commandLine
      },
      readlink: async () => {
        await sleep(100)
        return '/usr/bin/node'
      },
      timeoutMs: 20,
    }
    await expect(gateCore.readLinuxProcessIdentity(4321, slowIo)).rejects.toThrow(/timed out/)
  })

  it('bounds Linux proc enumeration with the same explicit deadline', async () => {
    await expect(gateCore.captureLinuxProcessSnapshot({
      timeoutMs: 20,
      io: {
        readdir: async () => {
          await sleep(100)
          return []
        },
      },
    })).rejects.toThrow(/timed out/)
  })

  it('fails closed when a Linux proc identity cannot be read with permission', async () => {
    const denied = Object.assign(new Error('permission denied'), { code: 'EACCES' })
    await expect(gateCore.captureLinuxProcessSnapshot({
      timeoutMs: 1000,
      io: {
        readdir: async () => [{ name: '4321', isDirectory: () => true }],
        readFile: async () => { throw denied },
        readlink: async () => '/usr/bin/node',
      },
    })).rejects.toMatchObject({ code: 'EACCES' })
  })

  it('enforces the Linux signal deadline, skips marker mismatches, and escalates TERM to KILL', async () => {
    const identity = LINUX_IDENTITY
    const incompleteOsSignals = []
    await expect(gateCore.signalLinuxProcessIdentity({ ...identity, argv: undefined }, {
      marker: 'vl360-linux-owned',
      readIdentity: async () => identity,
      kill: (pid, signal) => { incompleteOsSignals.push([pid, signal]) },
    })).rejects.toThrow(/identity is incomplete/)
    expect(incompleteOsSignals).toEqual([])

    const expiredSignals = []
    await expect(gateCore.terminateLinuxProcessIdentity(identity, {
      marker: 'vl360-linux-owned',
      deadline: Date.now() - 1,
      signalIdentity: async (...args) => {
        expiredSignals.push(args)
        return { pid: identity.pid, status: 'identity-mismatch' }
      },
      waitForExit: async () => null,
    })).rejects.toThrow(/deadline/)
    expect(expiredSignals).toEqual([])

    const mismatchOsSignals = []
    const mismatch = await gateCore.signalLinuxProcessIdentity(identity, {
      marker: 'wrong-marker',
      signal: 'SIGTERM',
      timeoutMs: 1000,
      readIdentity: async () => identity,
      kill: (pid, signal) => { mismatchOsSignals.push([pid, signal]) },
    })
    expect(mismatch.status).toBe('identity-mismatch')
    expect(mismatchOsSignals).toEqual([])

    const escalationSignals = []
    const escalationOsSignals = []
    const waits = [identity, null]
    const escalated = await gateCore.terminateLinuxProcessIdentity(identity, {
      marker: 'vl360-linux-owned',
      timeoutMs: 1000,
      signalIdentity: async (...args) => {
        escalationSignals.push(args)
        return signalLinuxFixture(args, identity, escalationOsSignals)
      },
      waitForExit: async () => waits.shift(),
    })
    expect(escalated.status).toBe('signalled')
    expect(escalationSignals.map(([, marker, signal]) => [marker, signal])).toEqual([
      ['vl360-linux-owned', 'SIGTERM'],
      ['vl360-linux-owned', 'SIGKILL'],
    ])
    expect(escalationOsSignals).toEqual([
      [identity.pid, 'SIGTERM'],
      [identity.pid, 'SIGKILL'],
    ])
  })

  it('bounds Linux exit identity polling by the remaining shared deadline', async () => {
    const identity = LINUX_IDENTITY
    const pollTimeouts = []
    const startedAt = Date.now()
    const result = await gateCore.waitForProcessIdentityExit(identity, {
      timeoutMs: 20,
      deadline: startedAt + 20,
      pollTimeoutMs: 1000,
      captureIdentity: async (pid, timeoutMs) => {
        expect(pid).toBe(identity.pid)
        pollTimeouts.push(timeoutMs)
        return identity
      },
      wait: async () => { await sleep(25) },
    })

    expect(result).toBe(identity)
    expect(pollTimeouts).toHaveLength(1)
    expect(pollTimeouts[0]).toBeGreaterThan(0)
    expect(pollTimeouts[0]).toBeLessThanOrEqual(20)
  })

  it('fails closed on platforms without high-confidence process identity', () => {
    expect(() => gateCore.assertHighConfidenceProcessIdentityPlatform('darwin'))
      .toThrow(/high-confidence process identity is unsupported on darwin/)
  })

  it.runIf(process.platform === 'win32')('observes exact timed-out helper-tree exit and prevents delayed side effects', async () => {
    const directory = mkdtempSync(join(tmpdir(), 'vl360-run-captured-tree-'))
    const pidPath = join(directory, 'pids.json')
    const sideEffectPath = join(directory, 'late-side-effect.txt')
    const marker = `vl360-run-captured-tree-${Date.now()}-${Math.random()}`
    const parentSource = timedTreeSource({ marker, pidPath, sideEffectPath, lifetimeMs: 12000 })
    const startedAt = Date.now()
    let pids
    let timeoutError

    try {
      try {
        await runCaptured(process.execPath, ['-e', parentSource, marker], {
          timeoutMs: 1000,
          cleanupTimeoutMs: 12000,
          ownershipMarker: marker,
        })
      } catch (error) {
        timeoutError = error
      }

      expect(timeoutError).toBeInstanceOf(Error)
      expect(timeoutError?.message).toMatch(/timed out after 1000ms/)
      const cleanupDiagnostic = [timeoutError?.message, timeoutError?.cause?.message].filter(Boolean).join('; cause: ')
      expect(timeoutError?.cleanupVerified, cleanupDiagnostic).toBe(true)
      expect(existsSync(pidPath)).toBe(true)
      pids = JSON.parse(readFileSync(pidPath, 'utf8'))
      const captured = timeoutError?.capturedProcessIdentities || []
      const parentIdentity = captured.find(identity => identity.pid === pids.parent)
      const childIdentity = captured.find(identity => identity.pid === pids.child)
      expect(parentIdentity?.startIdentity).toMatch(/^win:utc-ticks:\d+$/u)
      expect(childIdentity?.startIdentity).toMatch(/^win:utc-ticks:\d+$/u)
      expect(parentIdentity?.startIdentity).not.toBe(childIdentity?.startIdentity)
      expect(parentIdentity?.commandLine).toContain(marker)
      expect(childIdentity?.commandLine).toContain(marker)
      const postCleanupSnapshot = await gateCore.captureProcessSnapshot(4000)
      expect(postCleanupSnapshot.some(identity => matchesProcessIdentity(parentIdentity, identity))).toBe(false)
      expect(postCleanupSnapshot.some(identity => matchesProcessIdentity(childIdentity, identity))).toBe(false)
      await sleep(Math.max(0, 8500 - (Date.now() - startedAt)))
      expect(existsSync(sideEffectPath)).toBe(false)
    } finally {
      const retained = (timeoutError?.capturedProcessIdentities || [])
        .filter(identity => [pids?.parent, pids?.child].includes(identity.pid) && isRunning(identity.pid))
      if (retained.length > 0) {
        await gateCore.terminateExactProcessIdentities(retained, { marker, timeoutMs: 5000 })
      }
      rmSync(directory, { recursive: true, force: true })
    }
  }, 30000)

  it.runIf(process.platform === 'win32')('prevents a control-helper descendant from surviving its timeout and writing a delayed side effect', async () => {
    const directory = mkdtempSync(join(tmpdir(), 'vl360-control-helper-tree-'))
    const pidPath = join(directory, 'pids.json')
    const sideEffectPath = join(directory, 'late-side-effect.txt')
    const marker = `vl360-control-helper-tree-${Date.now()}-${Math.random()}`
    const parentSource = timedTreeSource({ marker, pidPath, sideEffectPath, sideEffectDelayMs: 5000, lifetimeMs: 7000 })
    const startedAt = Date.now()
    let pids
    let timeoutError

    try {
      try {
        await gateCore.runControlHelper(process.execPath, ['-e', parentSource, marker], {
          timeoutMs: 3000,
          cleanupTimeoutMs: 8000,
          ownershipMarker: marker,
        })
      } catch (error) {
        timeoutError = error
      }

      expect(timeoutError).toBeInstanceOf(Error)
      expect(timeoutError?.message).toMatch(/timed out after 3000ms/)
      expect(existsSync(pidPath)).toBe(true)
      pids = JSON.parse(readFileSync(pidPath, 'utf8'))
      const cleanupDiagnostic = [timeoutError?.message, timeoutError?.cause?.message].filter(Boolean).join('; cause: ')
      expect(timeoutError?.cleanupVerified, cleanupDiagnostic).toBe(true)
      expect(isRunning(pids.parent)).toBe(false)
      expect(isRunning(pids.child)).toBe(false)
      await sleep(Math.max(0, 6000 - (Date.now() - startedAt)))
      expect(existsSync(sideEffectPath)).toBe(false)
    } finally {
      await sleep(Math.max(0, 8000 - (Date.now() - startedAt)))
      rmSync(directory, { recursive: true, force: true })
    }
  }, 30000)

  it('waits for control-helper pipes to close before returning complete buffered JSON', async () => {
    const child = new EventEmitter()
    child.stdout = new PassThrough({ highWaterMark: 16384 })
    child.stderr = new PassThrough({ highWaterMark: 16384 })
    child.exitCode = null
    child.signalCode = null
    child.kill = () => true
    const resultPromise = gateCore.observeJobBoundControlHelper(child, process.execPath, 5000, 5000)

    child.stdout.write('{"payload":"' + 'x'.repeat(100000) + '","tail":')
    child.exitCode = 0
    child.emit('exit', 0, null)
    setTimeout(() => {
      child.stdout.end('"VL360_CLOSE_SENTINEL"}')
      child.stderr.end()
      child.emit('close', 0, null)
    }, 0)

    const result = await resultPromise
    const parsed = JSON.parse(result.stdout)
    expect(parsed.payload).toHaveLength(100000)
    expect(parsed.tail).toBe('VL360_CLOSE_SENTINEL')
    expect(result.stdout.endsWith('"VL360_CLOSE_SENTINEL"}')).toBe(true)
  })

  it.each([
    {
      adapter: 'snapshot',
      run: deadline => gateCore.captureProcessSnapshot(1000, deadline),
    },
    {
      adapter: 'identity',
      run: deadline => gateCore.captureProcessIdentity(987654321, 1000, deadline),
    },
  ])('keeps a nearly-expired absolute deadline through the Linux $adapter adapter', async ({ run }) => {
    const platformDescriptor = Object.getOwnPropertyDescriptor(process, 'platform')
    let now = 1000
    const nowSpy = vi.spyOn(Date, 'now').mockImplementation(() => now)
    const deadline = Date.now() + 1
    now = 1002
    Object.defineProperty(process, 'platform', { ...platformDescriptor, value: 'linux' })

    try {
      await expect(run(deadline)).rejects.toThrow(/deadline|timed out/i)
    } finally {
      Object.defineProperty(process, 'platform', platformDescriptor)
      nowSpy.mockRestore()
    }
  })

  it('does not start a captured operation after its caller deadline has expired', async () => {
    const directory = mkdtempSync(join(tmpdir(), 'vl360-expired-captured-deadline-'))
    const sideEffectPath = join(directory, 'started.txt')
    const marker = `vl360-expired-captured-deadline-${Date.now()}-${Math.random()}`
    const source = `require('node:fs').writeFileSync(${JSON.stringify(sideEffectPath)}, 'started') // ${marker}`

    try {
      await expect(runCaptured(process.execPath, ['-e', source, marker], {
        timeoutMs: 1000,
        cleanupTimeoutMs: 5000,
        deadline: Date.now() - 1,
        ownershipMarker: marker,
      })).rejects.toThrow(/deadline/)
      expect(existsSync(sideEffectPath)).toBe(false)
    } finally {
      rmSync(directory, { recursive: true, force: true })
    }
  })

  it('preserves late global and cleanup blockers after more than the output reason limit', () => {
    const evidence = { states: [], reasons: [], cleanup_errors: [] }
    for (let index = 0; index < 40; index += 1) {
      gateCore.recordGateReason(evidence, `mobile:nocturne:state-${index}`, `state failure ${index}`)
    }
    gateCore.recordGateReason(evidence, 'revision-mismatch', 'manifest differs from expected revision')
    try {
      throw new Error('primary gate failure')
    } catch (error) {
      gateCore.recordGateReason(evidence, 'unexpected-error', error.message)
    } finally {
      evidence.cleanup_errors.push('chrome:owned process remained')
    }

    gateCore.finalizeGateEvidence(evidence)
    compactGateEvidence(evidence)

    expect(evidence.verdict).toBe('fail')
    expect(evidence.reasons.map(reason => reason.code)).toEqual(expect.arrayContaining([
      'revision-mismatch',
      'unexpected-error',
      'cleanup-failed',
    ]))
    expect(evidence.reason_summary).toMatchObject({
      total_count: 43,
      retained_count: 12,
      truncated_count: 31,
      truncated: true,
    })
    expect(evidence.reason_summary.blocker_codes).toEqual(expect.arrayContaining([
      'revision-mismatch',
      'unexpected-error',
      'cleanup-failed',
    ]))
  })

  it('preserves the original reason summary and late blockers across repeated compact serialization', () => {
    const makeEvidence = () => {
      const evidence = { states: [], reasons: [], cleanup_errors: [] }
      for (let index = 0; index < 20; index += 1) {
        gateCore.recordGateReason(
          evidence,
          `mobile:nocturne:state-${index}`,
          `state failure ${index} ${'s'.repeat(260)}`,
        )
      }
      gateCore.recordGateReason(evidence, 'revision-mismatch', `manifest differs ${'r'.repeat(260)}`)
      gateCore.recordGateReason(evidence, 'unexpected-error', `late global failure ${'u'.repeat(260)}`)
      evidence.cleanup_errors.push('profile:owned profile still exists after removal')
      gateCore.finalizeGateEvidence(evidence)
      return evidence
    }
    const expectedSummary = {
      total_count: 23,
      retained_count: 12,
      truncated_count: 11,
      truncated: true,
      blocker_codes: ['revision-mismatch', 'unexpected-error', 'cleanup-failed'],
    }
    const expectedBlockers = [
      { code: 'revision-mismatch', message: `manifest differs ${'r'.repeat(260)}` },
      { code: 'unexpected-error', message: `late global failure ${'u'.repeat(260)}` },
      { code: 'cleanup-failed', message: 'owned Chrome resources were not fully cleaned up' },
    ]

    const compacted = makeEvidence()
    compactGateEvidence(compacted)
    compactGateEvidence(compacted)

    expect(compacted.reason_summary).toEqual(expectedSummary)
    expect(compacted.reasons.filter(reason => !reason.code.startsWith('mobile:'))).toEqual(expectedBlockers)

    const serialized = makeEvidence()
    const first = JSON.parse(gateCore.serializeBoundedGateEvidence(serialized, 4096))
    const second = JSON.parse(gateCore.serializeBoundedGateEvidence(serialized, 4096))

    expect(first.reason_summary).toEqual(expectedSummary)
    expect(second.reason_summary).toEqual(expectedSummary)
    expect(second.reason_summary.blocker_codes).toEqual(first.reason_summary.blocker_codes)
    expect(second.reasons.filter(reason => !reason.code.startsWith('mobile:'))).toEqual(expectedBlockers)
  })

  it('compacts repeated per-state assets while preserving the exact global set and all target/error evidence', () => {
    const assetPaths = ['/_nuxt/app.hash.js', '/_nuxt/detail.hash.css']
    const evidence = {
      preview_assets: { asset_paths: assetPaths },
      states: [{
        preview_assets: { asset_paths: [...assetPaths], css_paths: [assetPaths[1]], js_paths: [assetPaths[0]] },
        console_errors: [{ message: 'one' }, { message: 'two' }, { message: 'three' }],
        relevant_console_errors: [{ message: 'one' }, { message: 'two' }, { message: 'three' }],
        geometry: { contact: { controls: [{}, {}, {}] } },
      }],
      reasons: [
        ...Array.from({ length: 14 }, (_, index) => ({ code: `mobile:nocturne:state-${index}` })),
        { code: 'revision-mismatch' },
        { code: 'cleanup-failed' },
      ],
    }

    compactGateEvidence(evidence)

    expect(evidence.preview_assets.asset_paths).toEqual(assetPaths)
    expect(evidence.states[0].preview_assets).toEqual({
      asset_paths: assetPaths,
      css_paths: [assetPaths[1]],
      js_paths: [assetPaths[0]],
    })
    expect(evidence.states[0].console_error_indexes).toEqual([0, 1, 2])
    expect(evidence.states[0].relevant_console_error_indexes).toEqual([0, 1, 2])
    expect(evidence.console_error_catalog).toEqual([
      { message: 'one' },
      { message: 'two' },
      { message: 'three' },
    ])
    expect(evidence.states[0].geometry.contact.controls).toHaveLength(3)
    expect(evidence.reasons).toHaveLength(12)
    expect(evidence.reasons.map(reason => reason.code)).toEqual(expect.arrayContaining(['revision-mismatch', 'cleanup-failed']))
    expect(evidence.reason_summary).toMatchObject({ total_count: 16, retained_count: 12, truncated_count: 4, truncated: true })
    expect(evidence.reason_summary.blocker_codes).toEqual(expect.arrayContaining(['revision-mismatch', 'cleanup-failed']))
  })

  it('produces equivalent ownership and console evidence when compacted twice', () => {
    const evidence = {
      preview_assets: {
        asset_groups: {
          mobile: {
            state_count: 1,
            asset_paths: ['/_nuxt/app.hash.js', '/_nuxt/detail.hash.css'],
            fingerprint_sha256: 'a'.repeat(64),
          },
        },
      },
      states: [{
        viewport_name: 'mobile',
        preview_assets: {
          count: 2,
          unique_count: 2,
          asset_paths: ['/_nuxt/app.hash.js', '/_nuxt/detail.hash.css'],
          css_paths: ['/_nuxt/detail.hash.css'],
          js_paths: ['/_nuxt/app.hash.js'],
          detail_css_path: '/_nuxt/detail.hash.css',
          fingerprint_sha256: 'a'.repeat(64),
        },
        console_errors: [{ source: 'network', message: 'expected 503', url: '/feed', allowed_reason: 'sqlite' }],
        relevant_console_errors: [],
        geometry: {
          contact: {
            controls: [{
              text: 'Xem bản đồ',
              hit: {
                present: true,
                visible: true,
                belongs: true,
                stable: true,
                sample_count: 3,
                required_consecutive: 3,
                tag: 'a.cw-btn',
                text: 'Xem bản đồ',
              },
            }],
          },
          bottom_nav: {
            items: [{
              text: 'Trang chủ',
              hit: {
                present: true,
                visible: true,
                belongs: true,
                stable: true,
                sample_count: 3,
                required_consecutive: 3,
                tag: 'a.public-bottom-nav-item',
                text: 'Trang chủ',
              },
            }],
          },
        },
      }],
      reasons: [],
    }

    compactGateEvidence(evidence)
    const once = structuredClone(evidence)
    compactGateEvidence(evidence)

    expect(evidence).toEqual(once)
    expect(evidence.states[0].geometry.contact.controls[0]).toMatchObject({
      present: true,
      visible: true,
      belongs: true,
      stable: true,
      sample_count: 3,
      required_consecutive: 3,
    })
    expect(evidence.states[0].console_error_indexes).toEqual([0])
  })

  it('preserves exact state assets when global aggregation has not run', () => {
    const assetPaths = ['/_nuxt/app.early.js', '/_nuxt/detail.early.css']
    const fingerprint = 'd'.repeat(64)
    const evidence = {
      preview_assets: { asset_groups: {} },
      states: [{
        viewport_name: 'mobile',
        preview_assets: {
          count: 2,
          unique_count: 2,
          asset_paths: [...assetPaths],
          css_paths: [assetPaths[1]],
          js_paths: [assetPaths[0]],
          detail_css_path: assetPaths[1],
          fingerprint_sha256: fingerprint,
        },
      }],
      reasons: [{ code: 'unexpected-error', message: 'global aggregation did not run' }],
    }

    compactGateEvidence(evidence)

    const assetSets = evidence.preview_assets.asset_sets
    expect(assetSets).toEqual([{ asset_paths: assetPaths, fingerprint_sha256: fingerprint }])
    expect(evidence.preview_assets.asset_groups.mobile).toEqual({ state_count: 1, asset_set_indexes: [0] })
    expect(evidence.states[0].preview_assets).toMatchObject({ asset_group: 'mobile', asset_set_index: 0 })
    expect(assetSets[evidence.states[0].preview_assets.asset_set_index]).toEqual({
      asset_paths: assetPaths,
      fingerprint_sha256: fingerprint,
    })
  })

  it('catalogs every distinct asset set when themes in one viewport mismatch', () => {
    const firstPaths = ['/_nuxt/app.first.js', '/_nuxt/detail.first.css']
    const secondPaths = ['/_nuxt/app.second.js', '/_nuxt/detail.second.css']
    const firstFingerprint = 'e'.repeat(64)
    const secondFingerprint = 'f'.repeat(64)
    const state = (theme, assetPaths, fingerprint) => ({
      viewport_name: 'mobile',
      theme,
      preview_assets: {
        count: 2,
        unique_count: 2,
        asset_paths: [...assetPaths],
        css_paths: [assetPaths[1]],
        js_paths: [assetPaths[0]],
        detail_css_path: assetPaths[1],
        fingerprint_sha256: fingerprint,
      },
    })
    const evidence = {
      preview_assets: {
        asset_groups: {
          mobile: { state_count: 2, asset_paths: [...firstPaths], fingerprint_sha256: firstFingerprint },
        },
      },
      states: [
        state('nocturne', firstPaths, firstFingerprint),
        state('parchment', secondPaths, secondFingerprint),
      ],
      reasons: [{ code: 'asset-set-state-mismatch', message: 'themes bound different assets' }],
    }

    compactGateEvidence(evidence)

    const assetSets = evidence.preview_assets.asset_sets
    expect(assetSets).toEqual([
      { asset_paths: firstPaths, fingerprint_sha256: firstFingerprint },
      { asset_paths: secondPaths, fingerprint_sha256: secondFingerprint },
    ])
    expect(evidence.preview_assets.asset_groups.mobile).toEqual({ state_count: 2, asset_set_indexes: [0, 1] })
    expect(evidence.states.map(candidate => candidate.preview_assets.asset_set_index)).toEqual([0, 1])
    expect(evidence.states.map(candidate => (
      assetSets[candidate.preview_assets.asset_set_index]
    ))).toEqual([
      { asset_paths: firstPaths, fingerprint_sha256: firstFingerprint },
      { asset_paths: secondPaths, fingerprint_sha256: secondFingerprint },
    ])
  })

  it('keeps complete four-state hit, asset, error, mutation, and late-blocker evidence below the output bound', () => {
    const maxEvidenceBytes = 64 * 1024
    const targetHeadroomBytes = 5 * 1024
    const mobileAssetPaths = Object.freeze(Array.from({ length: 48 }, (_, index) => (
      `/_nuxt/mobile-detail-${String(index).padStart(2, '0')}.${'a'.repeat(36)}.${index % 3 === 0 ? 'css' : 'js'}`
    )))
    const desktopAssetPaths = Object.freeze(Array.from({ length: 48 }, (_, index) => (
      `/_nuxt/desktop-detail-${String(index).padStart(2, '0')}.${'b'.repeat(36)}.${index % 4 === 0 ? 'css' : 'js'}`
    )))
    const metric = (left, top, width, height) => ({
      rect: { x: left, y: top, width, height, left, right: left + width, top, bottom: top + height },
      client_width: width,
      scroll_width: width,
      overflow_px: 0,
      min_width: '0px',
      overflow_x: 'visible',
      white_space: 'normal',
      display: 'flex',
      position: 'fixed',
      visibility: 'visible',
      z_index: '30',
      bottom: '64px',
      padding_bottom: '0px',
    })
    const stableHit = tag => ({
      present: true,
      visible: true,
      belongs: true,
      stable: true,
      sample_count: 3,
      required_consecutive: 3,
      tag,
      text: tag,
    })
    const uniquePayload = (seed, length) => {
      let value = ''
      for (let index = 0; value.length < length; index += 1) {
        value += createHash('sha256').update(`${seed}:${index}`).digest('base64url')
      }
      return value.slice(0, length)
    }
    const contactLabels = ['Gọi điện', 'Zalo', 'Chỉ đường']
    const bottomNavLabels = ['Trang chủ', 'Khám phá', 'Gần bạn', 'Lịch trình', 'Tài khoản']
    const themeBinding = {
      capture_started_before_navigation: true,
      opposite_mode_seeded_before_navigation: true,
      opposite_mode_confirmed_before_click: true,
      target_control_hit_owned: true,
      physical_transition_observed: true,
      requested_mode_selected_before_finalize: true,
      stable_readiness_before_finalize: true,
      requested_mode_revalidated_after_finalize: true,
      opposite_mode: 'light',
      requested_mode: 'dark',
      selected_mode: 'dark',
    }
    const makeState = (viewportName, theme, assetPaths, fingerprint) => ({
      viewport_name: viewportName,
      viewport: viewportName === 'mobile' ? { width: 390, height: 844 } : { width: 1440, height: 1000 },
      theme,
      requested_mode: theme === 'nocturne' ? 'dark' : 'light',
      selected_mode: theme === 'nocturne' ? 'dark' : 'light',
      preview_assets: {
        count: assetPaths.length,
        unique_count: assetPaths.length,
        asset_paths: [...assetPaths],
        css_paths: assetPaths.filter(path => path.endsWith('.css')),
        js_paths: assetPaths.filter(path => path.endsWith('.js')),
        detail_css_path: assetPaths.find(path => path.endsWith('.css')),
        fingerprint_sha256: fingerprint,
        theme_binding: { ...themeBinding },
      },
      mutation: {
        name: 'mobile-main-auto-min-width',
        selector_matches: 1,
        rule_selector: '.detail-main',
        declared_min_width: 'auto',
        declared_priority: 'important',
        computed_min_width: 'auto',
        source_guard_present: true,
      },
      geometry: {
        viewport: viewportName === 'mobile'
          ? { width: 390, height: 844, root_client_width: 390 }
          : { width: 1440, height: 1000, root_client_width: 1440 },
        class_name: theme === 'nocturne' ? 'dark' : 'light',
        grid_template_columns: viewportName === 'mobile' ? '390px' : '900px 360px',
        detail_body: metric(0, 0, viewportName === 'mobile' ? 390 : 1280, 2000),
        main: metric(0, 0, viewportName === 'mobile' ? 390 : 900, 1900),
        lead: metric(16, 420, viewportName === 'mobile' ? 358 : 868, 160),
        description: metric(16, 600, viewportName === 'mobile' ? 358 : 868, 720),
        aside: metric(viewportName === 'mobile' ? 0 : 920, 420, viewportName === 'mobile' ? 390 : 360, 760),
        trust: metric(16, 1340, viewportName === 'mobile' ? 358 : 868, 260),
        containment: {
          main_in_body: true,
          lead_in_body: true,
          description_in_body: true,
          aside_in_body: true,
          trust_in_body: true,
        },
        page_overflow_px: 0,
        hero: {
          cover_rect: { x: 0, y: 0, width: 390, height: 260, left: 0, right: 390, top: 0, bottom: 260 },
          image_rect: { x: 0, y: 0, width: 390, height: 260, left: 0, right: 390, top: 0, bottom: 260 },
          image_loaded_class: true,
          image_complete: true,
          image_natural_width: 1600,
          image_natural_height: 1067,
          image_src: '/images/detail/cong-vien-an-hoi.webp',
          image_in_cover: true,
        },
        actions: {
          trip_rect: { x: 16, y: 300, width: 260, height: 48, left: 16, right: 276, top: 300, bottom: 348 },
          photo_rect: { x: 292, y: 300, width: 82, height: 48, left: 292, right: 374, top: 300, bottom: 348 },
          trip_control_count: 3,
          trip_photo_intersection: { width: 0, height: 48, area: 0 },
          photo_hit: stableHit('button.dc-photo-btn'),
          trip_hits: ['Tạo lịch trình', 'Lưu', 'Chia sẻ'].map(label => stableHit(`button.trip-btn.${label}`)),
        },
        contact: {
          metric: metric(0, 707, 390, 73),
          controls: contactLabels.map((text, index) => ({
            text,
            metric: metric(index * 130, 707, 130, 73),
            hit: stableHit(`a.cw-btn.contact-${index}`),
          })),
        },
        bottom_nav: {
          metric: metric(0, 780, 390, 64),
          hit: stableHit('nav.public-bottom-nav'),
          items: bottomNavLabels.map((text, index) => ({
            text,
            metric: metric(index * 78, 780, 78, 64),
            hit: stableHit(`a.public-bottom-nav-item.nav-${index}`),
          })),
          contact_intersection: { width: 0, height: 0, area: 0 },
        },
        bottom_reservation: { required_px: 137, main_padding_bottom_px: 145, footer_padding_bottom_px: 201 },
        sticky: { intended_contract: 'present-hidden', present: true, ...metric(0, 0, 0, 0), display: 'none' },
      },
      lightbox: {
        opened: true,
        aria_modal: true,
        dialog_rect: { x: 20, y: 40, width: 350, height: 760, left: 20, right: 370, top: 40, bottom: 800 },
        surface_visible: true,
        media_visible: true,
        close_hit: stableHit('button.lb-close'),
        closed: true,
      },
      console_errors: Array.from({ length: 8 }, (_, index) => ({
        source: 'network',
        message: `${viewportName}-${theme}-${index}-${uniquePayload(`message-${viewportName}-${theme}-${index}`, 220)}`,
        url: `http://127.0.0.1:3000/api/evidence/${viewportName}/${theme}/${index}?detail=${uniquePayload(`url-${viewportName}-${theme}-${index}`, 160)}`,
        allowed_reason: `expected-${viewportName}-${theme}-${index}`,
      })),
      relevant_console_errors: [],
      failures: [],
    })
    const states = [
      makeState('mobile', 'nocturne', mobileAssetPaths, 'a'.repeat(64)),
      makeState('mobile', 'parchment', mobileAssetPaths, 'a'.repeat(64)),
      makeState('desktop', 'nocturne', desktopAssetPaths, 'b'.repeat(64)),
      makeState('desktop', 'parchment', desktopAssetPaths, 'b'.repeat(64)),
    ]
    const evidence = {
      preconditions: { database_backend: 'sqlite' },
      mutation: 'mobile-main-auto-min-width',
      states,
      reasons: Array.from({ length: 20 }, (_, index) => ({
        code: `mobile:nocturne:state-${index}`,
        message: `state failure ${index}`,
      })),
      cleanup_errors: ['profile:owned profile still exists after removal'],
      cleanup: { attempted: true, profile_removed: false, owned_processes_remaining: [4120] },
      preview_assets: {
        state_count: 4,
        all_states_bound: true,
        detail_css_path: mobileAssetPaths.find(path => path.endsWith('.css')),
        asset_paths: [...mobileAssetPaths],
        asset_groups: {
          mobile: { state_count: 2, asset_paths: [...mobileAssetPaths], fingerprint_sha256: 'a'.repeat(64) },
          desktop: { state_count: 2, asset_paths: [...desktopAssetPaths], fingerprint_sha256: 'b'.repeat(64) },
        },
        aggregate_fingerprint_sha256: 'c'.repeat(64),
      },
    }
    gateCore.recordGateReason(evidence, 'revision-mismatch', 'manifest differs from expected revision')
    gateCore.recordGateReason(evidence, 'unexpected-error', 'primary gate failure')
    gateCore.finalizeGateEvidence(evidence)

    const beforeBytes = Buffer.byteLength(JSON.stringify(evidence, null, 2) + '\n')
    expect(beforeBytes).toBeGreaterThan(maxEvidenceBytes)

    expect(typeof gateCore.serializeBoundedGateEvidence).toBe('function')
    if (typeof gateCore.serializeBoundedGateEvidence !== 'function') return

    const output = gateCore.serializeBoundedGateEvidence(evidence, maxEvidenceBytes)
    const serializedBytes = Buffer.byteLength(output)
    const compactedPrettyBytes = Buffer.byteLength(JSON.stringify(evidence, null, 2) + '\n')
    const parsed = JSON.parse(output)

    expect(compactedPrettyBytes).toBeGreaterThan(maxEvidenceBytes)
    expect(serializedBytes).toBeLessThanOrEqual(maxEvidenceBytes - targetHeadroomBytes)
    expect(output).toBe(JSON.stringify(evidence) + '\n')
    expect(parsed).toEqual(evidence)
    for (const state of parsed.states) {
      expect(state.geometry.contact.controls.map(control => control.text)).toEqual(contactLabels)
      expect(state.geometry.contact.controls).toHaveLength(3)
      expect(state.geometry.bottom_nav.items.map(item => item.text)).toEqual(bottomNavLabels)
      expect(state.geometry.bottom_nav.items).toHaveLength(5)
      for (const target of [...state.geometry.contact.controls, ...state.geometry.bottom_nav.items]) {
        expect(target).toMatchObject({
          present: true,
          visible: true,
          belongs: true,
          stable: true,
          sample_count: 3,
          required_consecutive: 3,
        })
      }
      const consoleErrors = state.console_error_indexes.map(index => parsed.console_error_catalog[index])
      expect(consoleErrors).toHaveLength(8)
      expect(consoleErrors.map(entry => entry.allowed_reason)).toEqual(Array.from(
        { length: 8 },
        (_, index) => `expected-${state.viewport_name}-${state.theme}-${index}`,
      ))
      expect(state.relevant_console_error_indexes).toEqual([])
      expect(state.mutation).toMatchObject({
        name: 'mobile-main-auto-min-width',
        declared_min_width: 'auto',
        computed_min_width: 'auto',
      })
      expect(state.geometry.main.overflow_px).toBe(0)
      expect(state.geometry.contact.metric.rect).toMatchObject({ width: 390, height: 73 })
      expect(state.geometry.bottom_nav.metric.rect).toMatchObject({ width: 390, height: 64 })
      expect(state.geometry.bottom_nav.contact_intersection.area).toBe(0)
      expect(state.geometry.bottom_reservation).toEqual({
        required_px: 137,
        main_padding_bottom_px: 145,
        footer_padding_bottom_px: 201,
      })
    }
    expect(parsed.preview_assets.asset_groups.mobile).toEqual({ state_count: 2, asset_set_indexes: [0] })
    expect(parsed.preview_assets.asset_groups.desktop).toEqual({ state_count: 2, asset_set_indexes: [1] })
    expect(parsed.preview_assets.asset_sets).toEqual([
      { asset_paths: [...mobileAssetPaths], fingerprint_sha256: 'a'.repeat(64) },
      { asset_paths: [...desktopAssetPaths], fingerprint_sha256: 'b'.repeat(64) },
    ])
    expect(parsed.console_error_catalog).toHaveLength(32)
    expect(parsed.verdict).toBe('fail')
    expect(parsed.reasons.map(reason => reason.code)).toEqual(expect.arrayContaining([
      'revision-mismatch',
      'unexpected-error',
      'cleanup-failed',
    ]))
    expect(parsed.reason_summary).toMatchObject({ total_count: 23, retained_count: 12, truncated_count: 11, truncated: true })
    expect(parsed.reason_summary.blocker_codes).toEqual(expect.arrayContaining([
      'revision-mismatch',
      'unexpected-error',
      'cleanup-failed',
    ]))
    expect(parsed.cleanup_errors).toEqual(['profile:owned profile still exists after removal'])
    expect(parsed.cleanup).toEqual({ attempted: true, profile_removed: false, owned_processes_remaining: [4120] })
  })

  it('keeps small evidence pretty and throws only when compact minified evidence exceeds the bound', () => {
    expect(typeof gateCore.serializeBoundedGateEvidence).toBe('function')
    if (typeof gateCore.serializeBoundedGateEvidence !== 'function') return

    const small = { verdict: 'pass', states: [], reasons: [], cleanup_errors: [] }
    expect(gateCore.serializeBoundedGateEvidence(small, 1024)).toBe(JSON.stringify(small, null, 2) + '\n')

    const irreducible = { states: [], reasons: [], payload: 'x'.repeat(2048) }
    expect(() => gateCore.serializeBoundedGateEvidence(irreducible, 512)).toThrow(
      'bounded evidence exceeded byte limit',
    )
  })
})

function isRunning(pid) {
  if (!Number.isInteger(pid) || pid <= 0) return false
  try {
    process.kill(pid, 0)
    return true
  } catch {
    return false
  }
}

function sleep(ms) {
  return new Promise(resolveSleep => setTimeout(resolveSleep, ms))
}

function eventCapture(events) {
  return {
    start() { events.push('capture:start') },
    async verify() { events.push('capture:verify'); return { fingerprint_sha256: 'a'.repeat(64) } },
    stop() { events.push('capture:stop') },
  }
}

function signalLinuxFixture([identity, marker, signal, timeoutMs], current, osSignals) {
  return gateCore.signalLinuxProcessIdentity(identity, {
    marker,
    signal,
    timeoutMs,
    readIdentity: async () => current,
    kill: (pid, requestedSignal) => { osSignals.push([pid, requestedSignal]) },
  })
}

function timedTreeSource({ marker, pidPath, sideEffectPath = '', sideEffectDelayMs = 8000, lifetimeMs }) {
  const childSource = timedChildSource({ marker, sideEffectPath, sideEffectDelayMs, lifetimeMs })
  return [
    "const { spawn } = require('node:child_process')",
    "const { writeFileSync } = require('node:fs')",
    `const child = spawn(process.execPath, ['-e', ${JSON.stringify(childSource)}, ${JSON.stringify(marker)}], { stdio: 'ignore' })`,
    `writeFileSync(${JSON.stringify(pidPath)}, JSON.stringify({ parent: process.pid, child: child.pid }))`,
    `setTimeout(() => process.exit(0), ${lifetimeMs})`,
    'setInterval(() => {}, 1000)',
  ].join('; ')
}

function timedChildSource({ marker, sideEffectPath = '', sideEffectDelayMs = 8000, lifetimeMs }) {
  return [
    sideEffectPath ? "const { writeFileSync } = require('node:fs')" : '',
    sideEffectPath ? `setTimeout(() => writeFileSync(${JSON.stringify(sideEffectPath)}, 'late'), ${sideEffectDelayMs})` : '',
    `setTimeout(() => process.exit(0), ${lifetimeMs})`,
    'setInterval(() => {}, 1000)',
    '// ' + marker,
  ].filter(Boolean).join('; ')
}
