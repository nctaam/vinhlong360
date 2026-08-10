import { mkdtemp, readFile, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

import { finalizeAxeReport } from '../../scripts/axe_scan_result.mjs'

describe('axe scan route coverage', () => {
  it('writes the partial report but fails when any route scan was skipped', async () => {
    const directory = await mkdtemp(join(tmpdir(), 'axe-report-test-'))
    const outFile = join(directory, 'axe-report.json')
    const report = [{ url: '/ [dark]', violations: [] }]

    try {
      await expect(finalizeAxeReport(report, ['/broken [dark]: timeout'], outFile, 2)).resolves.toBe(1)
      await expect(readFile(outFile, 'utf8')).resolves.toBe(JSON.stringify(report, null, 2))
    } finally {
      await rm(directory, { recursive: true, force: true })
    }
  })

  it('fails when configuration produces no route-mode targets', async () => {
    const directory = await mkdtemp(join(tmpdir(), 'axe-report-test-'))
    const outFile = join(directory, 'axe-report.json')

    try {
      await expect(finalizeAxeReport([], [], outFile, 0)).resolves.toBe(1)
      await expect(readFile(outFile, 'utf8')).resolves.toBe('[]')
    } finally {
      await rm(directory, { recursive: true, force: true })
    }
  })

  it('fails when completed reports do not cover every configured target', async () => {
    const directory = await mkdtemp(join(tmpdir(), 'axe-report-test-'))
    const outFile = join(directory, 'axe-report.json')
    const report = [{ url: '/ [dark]', violations: [] }]

    try {
      await expect(finalizeAxeReport(report, [], outFile, 2)).resolves.toBe(1)
      await expect(readFile(outFile, 'utf8')).resolves.toBe(JSON.stringify(report, null, 2))
    } finally {
      await rm(directory, { recursive: true, force: true })
    }
  })

  it('passes only when every configured target completed without skips', async () => {
    const directory = await mkdtemp(join(tmpdir(), 'axe-report-test-'))
    const outFile = join(directory, 'axe-report.json')
    const report = [{ url: '/ [dark]', violations: [] }]

    try {
      await expect(finalizeAxeReport(report, [], outFile, 1)).resolves.toBe(0)
    } finally {
      await rm(directory, { recursive: true, force: true })
    }
  })
})
