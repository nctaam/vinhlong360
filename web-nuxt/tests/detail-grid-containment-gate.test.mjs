import { execFileSync } from 'node:child_process'
import { existsSync, mkdtempSync, readFileSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

import * as gateCore from '../scripts/detail-grid-gate-core.mjs'

import {
  collectAssetSetFailures,
  collectStateFailures,
  compactGateEvidence,
  hasExactZeroMinWidth,
  hasStableOwnedHit,
  isFreshNavigationState,
  isOwnedBrowserProcess,
  ownedBrowserProcessIds,
  runCaptured,
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
          trip_control_count: 3,
          trip_hits: [{ belongs: true }, { belongs: true }, { belongs: true }],
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
          trip_control_count: 3,
          trip_hits: [{ belongs: true }, { belongs: true }, { belongs: true }],
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
        contact: { controls: [{ hit: { belongs: true } }] },
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

    expect(ownedBrowserProcessIds([
      { pid: 11, executablePath: ownership.browserPath, commandLine: `chrome.exe --user-data-dir="${ownership.profile}"` },
      { pid: 12, executablePath: ownership.browserPath, commandLine: `chrome.exe --user-data-dir="${ownership.profile}-other"` },
      { pid: 13, executablePath: 'C:\\Other\\chrome.exe', commandLine: `chrome.exe --user-data-dir="${ownership.profile}"` },
    ], ownership)).toEqual([11])
  })

  it('bounds owned command execution instead of waiting indefinitely', async () => {
    await expect(runCaptured(process.execPath, ['-e', 'setInterval(() => {}, 1000)'], { timeoutMs: 100 }))
      .rejects.toThrow(/timed out after 100ms/)
  })

  it.runIf(process.platform === 'win32')('verifies the timed-out parent and its owned descendant are gone before rejecting', async () => {
    const directory = mkdtempSync(join(tmpdir(), 'vl360-run-captured-tree-'))
    const pidPath = join(directory, 'pids.json')
    const marker = `vl360-run-captured-tree-${Date.now()}-${Math.random()}`
    const childSource = `setInterval(() => {}, 1000) // ${marker}`
    const parentSource = [
      "const { spawn } = require('node:child_process')",
      "const { writeFileSync } = require('node:fs')",
      `const child = spawn(process.execPath, ['-e', ${JSON.stringify(childSource)}, ${JSON.stringify(marker)}], { stdio: 'ignore' })`,
      `writeFileSync(${JSON.stringify(pidPath)}, JSON.stringify({ parent: process.pid, child: child.pid }))`,
      'setInterval(() => {}, 1000)',
    ].join('; ')
    let pids

    try {
      let timeoutError
      try {
        await runCaptured(process.execPath, ['-e', parentSource, marker], { timeoutMs: 300, cleanupTimeoutMs: 7000 })
      } catch (error) {
        timeoutError = error
      }

      expect(timeoutError).toBeInstanceOf(Error)
      expect(timeoutError?.message).toMatch(/timed out after 300ms/)
      expect(timeoutError?.cleanupVerified).toBe(true)
      expect(existsSync(pidPath)).toBe(true)
      pids = JSON.parse(readFileSync(pidPath, 'utf8'))
      expect(isRunning(pids.parent)).toBe(false)
      expect(isRunning(pids.child)).toBe(false)
    } finally {
      for (const pid of [pids?.parent, pids?.child]) {
        if (Number.isInteger(pid) && isRunning(pid)) {
          execFileSync('taskkill.exe', ['/PID', String(pid), '/F'], { stdio: 'ignore' })
        }
      }
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
      reasons: [
        ...Array.from({ length: 14 }, (_, index) => ({ code: `mobile:nocturne:state-${index}` })),
        { code: 'revision-mismatch' },
        { code: 'cleanup-failed' },
      ],
    }

    compactGateEvidence(evidence)

    expect(evidence.preview_assets.asset_paths).toEqual(assetPaths)
    expect(evidence.states[0].preview_assets).toMatchObject({ asset_paths: [], css_paths: [], js_paths: [], asset_set_recorded_globally: true })
    expect(evidence.states[0].console_errors).toHaveLength(2)
    expect(evidence.states[0].geometry.contact.controls).toHaveLength(2)
    expect(evidence.reasons).toHaveLength(12)
    expect(evidence.reasons.map(reason => reason.code)).toEqual(expect.arrayContaining(['revision-mismatch', 'cleanup-failed']))
    expect(evidence.reason_summary).toMatchObject({ total_count: 16, retained_count: 12, truncated_count: 4, truncated: true })
    expect(evidence.reason_summary.blocker_codes).toEqual(expect.arrayContaining(['revision-mismatch', 'cleanup-failed']))
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
