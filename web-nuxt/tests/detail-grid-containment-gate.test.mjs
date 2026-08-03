import { existsSync, mkdtempSync, readFileSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

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
      expect(isRunning(pids.parent)).toBe(false)
      expect(isRunning(pids.child)).toBe(false)
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
    const parentSource = timedTreeSource({ marker, pidPath, sideEffectPath, sideEffectDelayMs: 2600, lifetimeMs: 4500 })
    const startedAt = Date.now()
    let pids
    let timeoutError

    try {
      try {
        await gateCore.runControlHelper(process.execPath, ['-e', parentSource, marker], {
          timeoutMs: 1000,
          cleanupTimeoutMs: 8000,
          ownershipMarker: marker,
        })
      } catch (error) {
        timeoutError = error
      }

      expect(timeoutError).toBeInstanceOf(Error)
      expect(timeoutError?.message).toMatch(/timed out after 1000ms/)
      expect(existsSync(pidPath)).toBe(true)
      pids = JSON.parse(readFileSync(pidPath, 'utf8'))
      const cleanupDiagnostic = [timeoutError?.message, timeoutError?.cause?.message].filter(Boolean).join('; cause: ')
      expect(timeoutError?.cleanupVerified, cleanupDiagnostic).toBe(true)
      expect(isRunning(pids.parent)).toBe(false)
      expect(isRunning(pids.child)).toBe(false)
      await sleep(Math.max(0, 3200 - (Date.now() - startedAt)))
      expect(existsSync(sideEffectPath)).toBe(false)
    } finally {
      await sleep(Math.max(0, 5200 - (Date.now() - startedAt)))
      rmSync(directory, { recursive: true, force: true })
    }
  }, 30000)

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
