// @vitest-environment node
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it, vi } from 'vitest'

import redirectMiddleware, { resolveEntityRedirect } from '../server/middleware/00-entity-redirects'

const ROOT = resolve(__dirname, '../..')

describe('Entity Canonical 301 Redirects', () => {
  const redirectMap = JSON.parse(
    readFileSync(resolve(ROOT, 'web-nuxt/data/entity-redirects.json'), 'utf8'),
  ) as Record<string, string>
  const dataJson = JSON.parse(
    readFileSync(resolve(ROOT, 'web/data.json'), 'utf8'),
  ) as { entities: Array<{ id: string }> }
  const survivingIds = new Set(dataJson.entities.map((entity) => entity.id))

  it('resolves merged and static alias slugs to canonical /dia-diem paths with query preservation', () => {
    expect(resolveEntityRedirect('/dia-diem/chua-ang-angkorajaborey')).toBe('/dia-diem/chua-ang')
    expect(resolveEntityRedirect('/dia-diem/chua-vam-ray-tra-vinh')).toBe('/dia-diem/chua-vam-ray')
    expect(resolveEntityRedirect('/dia-diem/van-thanh-mieu-vinh-long')).toBe('/dia-diem/van-thanh-mieu')
    expect(resolveEntityRedirect('/dia-diem/lang-gom-mang-thit')).toBe('/dia-diem/lang-nghe-gom-do-mang-thit')
    expect(resolveEntityRedirect('/dia-diem/cu-lao-an-binh-long-ho?from=share')).toBe('/dia-diem/cu-lao-an-binh?from=share')
    expect(resolveEntityRedirect('/dia-diem/van-thanh-mieu')).toBeNull()
    expect(resolveEntityRedirect('/am-thuc')).toBeNull()
  })

  it('guarantees every redirect target survives in web/data.json with zero loops or chains', () => {
    const entries = Object.entries(redirectMap)
    expect(entries.length).toBeGreaterThanOrEqual(115)
    for (const [source, target] of entries) {
      expect(source).not.toBe(target)
      expect(survivingIds.has(target)).toBe(true)
      expect(survivingIds.has(source)).toBe(false)
      expect(Object.prototype.hasOwnProperty.call(redirectMap, target)).toBe(false)
    }
  })

  it('invokes HTTP 301 redirect inside the Nitro middleware handler for GET and HEAD', async () => {
    const headers: Record<string, string> = {}
    let statusCode = 200
    const sendRes = {
      statusCode: 200,
      headersSent: false,
      writableEnded: false,
      getHeader(k: string) {
        return headers[k.toLowerCase()]
      },
      setHeader(k: string, v: string) {
        headers[k.toLowerCase()] = v
      },
      end() {
        this.writableEnded = true
      },
    }
    const event = {
      method: 'GET',
      path: '/dia-diem/chua-ang-angkorajaborey',
      node: {
        req: { method: 'GET', url: '/dia-diem/chua-ang-angkorajaborey' },
        res: new Proxy(sendRes, {
          set(target, prop, value) {
            if (prop === 'statusCode') statusCode = value
            ;(target as Record<string | symbol, unknown>)[prop] = value
            return true
          },
        }),
      },
    } as any

    const spyEnd = vi.spyOn(sendRes, 'end')
    await redirectMiddleware(event)
    expect(statusCode).toBe(301)
    expect(headers.location).toBe('/dia-diem/chua-ang')
    expect(spyEnd).toHaveBeenCalled()
  })
})
