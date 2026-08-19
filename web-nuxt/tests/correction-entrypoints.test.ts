// Every public door into the correction journey leads to the same room.
//
// Before this, each surface had its own idea of reporting: the directory posted
// into a JSONL file nobody tracked, and the detail page's trust CTA dropped the
// reader into a community search. One link builder now owns the path and the
// query, so the journey — and what may ride its URL — is decided in one place.

import { mount } from '@vue/test-utils'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

import CorrectionIntakeForm from '../components/cases/CorrectionIntakeForm.vue'
import {
  CORRECTION_FIELD_HINTS,
  CORRECTION_INTAKE_PATH,
  correctionIntakeLink,
} from '../utils/correctionLink'

function source(relative: string): string {
  return readFileSync(resolve(__dirname, '..', relative), 'utf8')
}

describe('the shared link builder', () => {
  it('carries exactly the three non-secret hints', () => {
    const link = correctionIntakeLink('p-quan-com', {
      field: 'attributes.phone', source: 'dia-diem',
    })

    expect(link).toBe('/yeu-cau/sua-thong-tin?entity=p-quan-com&field=attributes.phone&source=dia-diem')
  })

  it('drops a field hint the intake form does not offer', () => {
    const link = correctionIntakeLink('p-quan-com', { field: 'attributes.verifiedAt' })

    // The URL is public surface. A hint the form cannot honour is noise at
    // best; at worst it teaches people that arbitrary keys ride this query.
    expect(link).not.toContain('verifiedAt')
    expect(link).toBe('/yeu-cau/sua-thong-tin?entity=p-quan-com')
  })

  it('drops a source that does not look like a page name', () => {
    const link = correctionIntakeLink('p-quan-com', { source: 'https://evil.example' })

    expect(link).toBe('/yeu-cau/sua-thong-tin?entity=p-quan-com')
  })

  it('falls back to the bare journey when the entity id is not one', () => {
    for (const bad of ['', '  ', 'a b', 'x'.repeat(201), '<script>']) {
      expect(correctionIntakeLink(bad)).toBe(CORRECTION_INTAKE_PATH)
    }
  })
})

describe('the public entry points', () => {
  it('detail page trust CTA files a correction, not a community search', () => {
    const page = source('pages/dia-diem/[id].vue')

    expect(page).toContain("correctionIntakeLink(id.value, { source: 'dia-diem' })")
    // The old destination recorded nothing and promised less.
    expect(page).not.toContain('/cong-dong?report=')
  })

  it('ward page routes its freshness CTA the same way', () => {
    const page = source('pages/xa-phuong/[id].vue')

    expect(page).toContain("correctionIntakeLink(id.value, { source: 'xa-phuong' })")
    expect(page).not.toContain('/cong-dong?report=')
  })

  it('directory links to the canonical journey instead of posting JSONL', () => {
    const page = source('pages/danh-ba.vue')

    expect(page).toContain("correctionIntakeLink(f.id, { source: 'danh-ba' })")
    // The inline form and its fire-and-forget write are gone entirely.
    expect(page).not.toContain("'/api/report'")
    expect(page).not.toMatch(/submitReport|reportDetail/)
  })

  it('the intake page treats query context as a hint, never as data', () => {
    const page = source('pages/yeu-cau/sua-thong-tin.vue')

    // Name and revision come from the live projection; the query may only
    // preselect a field the form already offers.
    expect(page).toContain('CORRECTION_FIELD_HINTS.has(raw)')
    expect(page).not.toMatch(/route\.query\.(revision|name|value)/)
  })
})

describe('the field hint on the form', () => {
  function form(initialFieldPath: string | null) {
    return mount(CorrectionIntakeForm, {
      props: {
        entityId: 'p-quan-com',
        entityName: 'Quán Cơm Bà Tư',
        baseEntityRevision: 7,
        initialFieldPath,
      },
    })
  }

  it('preselects a field the form offers', () => {
    const mounted = form('attributes.phone')

    const select = mounted.get('#item-0-field').element as HTMLSelectElement
    expect(select.value).toBe('attributes.phone')
    // Progressive reveal follows the hint: the value fields are already open.
    expect(mounted.find('#item-0-proposed').exists()).toBe(true)
  })

  it('ignores a hint it does not recognise', () => {
    const mounted = form('attributes.verifiedAt')

    const select = mounted.get('#item-0-field').element as HTMLSelectElement
    expect(select.value).toBe('')
  })

  it('agrees with the builder about which hints exist', () => {
    const offered = source('components/cases/CorrectionIntakeForm.vue')

    // A hint the builder forwards but the form cannot honour would quietly
    // no-op for every reader arriving through that link.
    for (const hint of CORRECTION_FIELD_HINTS) {
      expect(offered, `form does not offer ${hint}`).toContain(`'${hint}'`)
    }
  })
})
