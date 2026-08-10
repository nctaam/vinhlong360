import { writeFile } from 'node:fs/promises'

export async function finalizeAxeReport(report, skipped, outFile, expectedCoverage) {
  await writeFile(outFile, JSON.stringify(report, null, 2), 'utf8')
  return skipped.length || expectedCoverage <= 0 || report.length !== expectedCoverage ? 1 : 0
}
