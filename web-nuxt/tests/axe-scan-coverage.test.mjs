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
      await expect(finalizeAxeReport(report, ['/broken [dark]: timeout'], outFile)).resolves.toBe(1)
      await expect(readFile(outFile, 'utf8')).resolves.toBe(JSON.stringify(report, null, 2))
    } finally {
      await rm(directory, { recursive: true, force: true })
    }
  })
})
