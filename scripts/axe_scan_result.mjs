import { writeFile } from 'node:fs/promises'

export async function finalizeAxeReport(report, skipped, outFile) {
  await writeFile(outFile, JSON.stringify(report, null, 2), 'utf8')
  return skipped.length ? 1 : 0
}
