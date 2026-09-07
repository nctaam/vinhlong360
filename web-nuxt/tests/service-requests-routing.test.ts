import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function readPage(relPath: string): string {
  return readFileSync(resolve(__dirname, '..', relPath), 'utf8')
}

describe('Service Requests, Access Control & Fallback Routing (Moc 134)', () => {
  describe('Correction Request Intake (pages/yeu-cau/sua-thong-tin.vue)', () => {
    it('integrates CorrectionIntakeForm and CaseReceiptCard with secure receipt flow', () => {
      const src = readPage('pages/yeu-cau/sua-thong-tin.vue')
      expect(src).toContain('<CorrectionIntakeForm')
      expect(src).toContain('<CaseReceiptCard')
      expect(src).toContain('Yêu cầu sửa thông tin')
      expect(src).toContain('role="alert"')
    })

    it('enforces purpose-based radius and tri-region color system', () => {
      const src = readPage('pages/yeu-cau/sua-thong-tin.vue')
      expect(src).toContain('data-color-system="tri-region-v1"')
      const style = src.match(/<style[^>]*>([\s\S]*?)<\/style>/)?.[1] || ''
      expect(style).toContain('--radius-control')
      expect(style).toContain('--radius-surface')
      expect(style).not.toMatch(/--radius-(?:xs|sm|md|lg|xl)\b/)
      expect(style).not.toMatch(/#[0-9a-fA-F]{3,8}\b/)
    })
  })

  describe('Receipt Lookup (pages/yeu-cau/tra-cuu.vue)', () => {
    it('provides accessible form inputs for reference and one-time capability', () => {
      const src = readPage('pages/yeu-cau/tra-cuu.vue')
      expect(src).toContain('id="lookup-reference"')
      expect(src).toContain('id="lookup-capability"')
      expect(src).toContain('type="password"')
      expect(src).toContain('role="alert"')
    })

    it('enforces purpose-based radius and token compliance', () => {
      const src = readPage('pages/yeu-cau/tra-cuu.vue')
      const style = src.match(/<style[^>]*>([\s\S]*?)<\/style>/)?.[1] || ''
      expect(style).toContain('--radius-control')
      expect(style).not.toMatch(/--radius-(?:xs|sm|md|lg|xl)\b/)
      expect(style).not.toMatch(/#[0-9a-fA-F]{3,8}\b/)
    })
  })

  describe('Case Status Dashboard (pages/yeu-cau/trang-thai.vue)', () => {
    it('integrates CaseStatusTimeline and rotation actions', () => {
      const src = readPage('pages/yeu-cau/trang-thai.vue')
      expect(src).toContain('<CaseStatusTimeline')
      expect(src).toContain('rotate')
      expect(src).toContain('signOut')
      expect(src).toContain('role="alert"')
    })

    it('enforces purpose-based radius and token compliance', () => {
      const src = readPage('pages/yeu-cau/trang-thai.vue')
      const style = src.match(/<style[^>]*>([\s\S]*?)<\/style>/)?.[1] || ''
      expect(style).toContain('--radius-control')
      expect(style).toContain('--radius-surface')
      expect(style).not.toMatch(/--radius-(?:xs|sm|md|lg|xl)\b/)
      expect(style).not.toMatch(/#[0-9a-fA-F]{3,8}\b/)
    })
  })

  describe('Access Denied 403 Page (pages/403.vue)', () => {
    it('integrates SystemSystemStatePanel with permission-denied kind', () => {
      const src = readPage('pages/403.vue')
      expect(src).toContain('<SystemSystemStatePanel')
      expect(src).toContain('kind="permission-denied"')
      expect(src).toContain('data-color-system="tri-region-v1"')
    })
  })

  describe('Not Found 404 Catch-All (pages/[...slug].vue)', () => {
    it('sets 404 response status and provides discovery shortcuts', () => {
      const src = readPage('pages/[...slug].vue')
      expect(src).toContain('setResponseStatus(event, 404)')
      expect(src).toContain('data-color-system="tri-region-v1"')
      expect(src).toContain('discoveryLinks')
    })

    it('uses modernized --radius-pill token without raw hex', () => {
      const src = readPage('pages/[...slug].vue')
      const style = src.match(/<style[^>]*>([\s\S]*?)<\/style>/)?.[1] || ''
      expect(style).toContain('--radius-pill')
      expect(style).not.toMatch(/--radius-(?:xs|sm|md|lg|xl)\b/)
      expect(style).not.toMatch(/#[0-9a-fA-F]{3,8}\b/)
    })
  })
})
