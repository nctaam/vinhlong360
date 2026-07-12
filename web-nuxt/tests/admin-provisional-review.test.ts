import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const page = readFileSync(resolve(process.cwd(), 'pages/admin/duyet-tu-hoc.vue'), 'utf8')
  .replaceAll('\r\n', '\n')

describe('admin provisional review snapshot', () => {
  it('uses the explicit review envelope and complete entity snapshot', () => {
    expect(page).toContain('interface ProvisionalEntitySnapshot')
    expect(page).toContain('interface ProvisionalReview')
    expect(page).toContain('ref<ProvisionalReview[]>([])')
    expect(page).not.toContain('as Entity[]')
    expect(page).toContain('e.entity')
  })

  it('visibly exposes common and uncommon reviewed fields', () => {
    expect(page).toContain('e.entity.summary')
    expect(page).toContain('formatInspectable(e.entity.source)')
    expect(page).toContain('coordinateValue(e.entity)')
    expect(page).toContain('e.entity.images')
    expect(page).toContain('formatInspectable(e.entity.attributes)')
    expect(page).toContain('e.entity.address')
    expect(page).toContain('e.entity.area')
    expect(page).toContain('e.entity.placeId')
    expect(page).toContain('<details')
    expect(page).toContain('JSON.stringify(e.entity, null, 2)')
  })

  it('submits the token for the exact reviewed snapshot', () => {
    expect(page).toContain('body: { review_token: e.review_token }')
  })
})
