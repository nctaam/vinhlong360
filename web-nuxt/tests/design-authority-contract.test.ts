import { readFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const root = resolve(import.meta.dirname, '../..')

describe('approved public design authority', () => {
  it('declares Adaptive Nocturne as the public visual authority', async () => {
    const master = await readFile(resolve(root, 'design-system/vinhlong360/MASTER.md'), 'utf8')
    expect(master).toContain('Adaptive Nocturne System')
    expect(master).toContain('Nocturne Heritage')
    expect(master).toContain('Existing Stitch Screen Evolution')
    expect(master).not.toContain('draft-for-review')
  })

  it('keeps AdminCP as a separate dense workbench family', async () => {
    const admin = await readFile(resolve(root, 'design-system/vinhlong360/pages/admin-dashboard.md'), 'utf8')
    expect(admin).toContain('Bàn điều phối vận hành')
    expect(admin).toContain('mật độ cao')
  })
})
