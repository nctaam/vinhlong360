// @vitest-environment node

import { afterEach, describe, expect, it } from 'vitest'
import { createTask8SmokeServer } from '../scripts/task8-smoke-backend.mjs'

const servers: Array<{ close: () => Promise<void> }> = []

afterEach(async () => {
  await Promise.all(servers.splice(0).map(server => server.close()))
})

describe('Task 8 local smoke backend', () => {
  it('requires the fixed local login before exposing personalized recommendations', async () => {
    const server = await createTask8SmokeServer({ port: 0 })
    servers.push(server)

    const anonymous = await fetch(`${server.origin}/api/me/recommendations/contextual?context=search`)
    expect(anonymous.status).toBe(401)

    const rejected = await fetch(`${server.origin}/auth/login`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ phone: '0900000000', password: 'wrong-password' }),
    })
    expect(rejected.status).toBe(401)
    expect(rejected.headers.get('set-cookie')).toBeNull()

    const accepted = await fetch(`${server.origin}/auth/login`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ phone: '0900000000', password: 'task8-smoke-only' }),
    })
    expect(accepted.status).toBe(200)
    const fixtureCookie = accepted.headers.get('set-cookie')
    expect(fixtureCookie).toMatch(/^vl360_token=task8-smoke-session;/)

    const personalized = await fetch(`${server.origin}/api/me/recommendations/contextual?context=search`, {
      headers: { cookie: fixtureCookie!.split(';')[0]! },
    })
    expect(personalized.status).toBe(200)
    const payload = await personalized.json() as { items: Array<{ id: string; reason_vi?: string }> }
    expect(payload.items.map(item => item.id)).toEqual(['smoke-generic', 'smoke-adaptive'])
    expect(payload.items[1]?.reason_vi).toBe('Cùng khu vực bạn quan tâm')
  })

  it('enables only the explanation flags needed by the rendered smoke surface', async () => {
    const server = await createTask8SmokeServer({ port: 0 })
    servers.push(server)

    const response = await fetch(`${server.origin}/api/site-settings`)
    expect(await response.json()).toEqual({
      'features.flags': {
        ai_recommendations: true,
        recommendation_explanations_v1: true,
      },
    })
  })
})
