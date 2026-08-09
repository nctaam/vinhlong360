import { createServer } from 'node:http'
import { fileURLToPath } from 'node:url'
import { resolve } from 'node:path'

const HOST = '127.0.0.1'
const FIXTURE_PHONE = '0900000000'
const FIXTURE_PASSWORD = 'task8-smoke-only'
const FIXTURE_COOKIE = 'vl360_token=task8-smoke-session'
const FIXTURE_USER = {
  id: 'task8-smoke-user',
  phone: FIXTURE_PHONE,
  display_name: 'Khách smoke Task 8',
  role: 'user',
  has_password: true,
}
const RECOMMENDATIONS = [
  {
    id: 'smoke-generic',
    type: 'attraction',
    name: 'Gợi ý smoke chung',
    summary: 'Dữ liệu cục bộ chỉ dùng để xác minh giao diện Task 8.',
    reason_vi: 'Được cộng đồng quan tâm',
    explanation: {
      primary_reason: 'Được cộng đồng quan tâm',
      reasons: ['Được cộng đồng quan tâm'],
    },
    source_tier: 'official',
    freshness_status: 'fresh',
  },
  {
    id: 'smoke-adaptive',
    type: 'craft_village',
    name: 'Gợi ý smoke theo khu vực',
    summary: 'Dữ liệu cục bộ tạo một quyết định ưu tiên có thể đảo ngược.',
    reason_vi: 'Cùng khu vực bạn quan tâm',
    explanation: {
      primary_reason: 'Cùng khu vực bạn quan tâm',
      reasons: ['Cùng khu vực bạn quan tâm'],
      region_label: 'Vĩnh Long',
    },
    source_tier: 'official',
    freshness_status: 'fresh',
  },
]

function sendJson(response, status, body, headers = {}) {
  response.writeHead(status, {
    'content-type': 'application/json; charset=utf-8',
    'cache-control': 'no-store',
    ...headers,
  })
  response.end(JSON.stringify(body))
}

function hasFixtureSession(request) {
  return String(request.headers.cookie || '').split(';').some(value => value.trim() === FIXTURE_COOKIE)
}

async function readJson(request) {
  let raw = ''
  for await (const chunk of request) {
    raw += chunk
    if (raw.length > 16_384) throw new Error('request too large')
  }
  return raw ? JSON.parse(raw) : {}
}

async function handleRequest(request, response) {
  const url = new URL(request.url || '/', `http://${HOST}`)

  if (request.method === 'GET' && url.pathname === '/api/site-settings') {
    return sendJson(response, 200, {
      'features.flags': {
        ai_recommendations: true,
        recommendation_explanations_v1: true,
      },
    })
  }

  if (request.method === 'GET' && url.pathname === '/api/search') {
    const entities = [{ id: 'gom-do-mang-thit', type: 'craft_village', name: 'Gốm đỏ Mang Thít', summary: 'Kết quả smoke cục bộ.' }]
    return sendJson(response, 200, { entities, posts: [], users: [], totals: { entities: 1, posts: 0, users: 0 } })
  }

  if (request.method === 'GET' && url.pathname === '/api/entities/popular') {
    return sendJson(response, 200, { entities: RECOMMENDATIONS })
  }

  if (request.method === 'GET' && url.pathname === '/auth/me') {
    return hasFixtureSession(request)
      ? sendJson(response, 200, { user: FIXTURE_USER })
      : sendJson(response, 401, { detail: 'Local smoke session required' })
  }

  if (request.method === 'GET' && url.pathname === '/auth/csrf') {
    return sendJson(response, 200, { csrf_token: 'task8-smoke-csrf' })
  }

  if (request.method === 'POST' && url.pathname === '/auth/check-phone') {
    const body = await readJson(request)
    return sendJson(response, 200, { exists: body.phone === FIXTURE_PHONE })
  }

  if (request.method === 'POST' && url.pathname === '/auth/login') {
    const body = await readJson(request)
    if (body.phone !== FIXTURE_PHONE || body.password !== FIXTURE_PASSWORD) {
      return sendJson(response, 401, { detail: 'Local smoke credentials rejected' })
    }
    return sendJson(response, 200, { user: FIXTURE_USER }, {
      'set-cookie': `${FIXTURE_COOKIE}; Path=/; HttpOnly; SameSite=Lax`,
    })
  }

  if (request.method === 'GET' && url.pathname === '/api/me/recommendations/contextual') {
    if (!hasFixtureSession(request)) return sendJson(response, 401, { detail: 'Local smoke session required' })
    return sendJson(response, 200, {
      items: RECOMMENDATIONS,
      reasons: Object.fromEntries(RECOMMENDATIONS.map(item => [item.id, item.explanation.reasons])),
      profile: { signal_count: 1 },
    })
  }

  if (request.method === 'GET' && url.pathname === '/api/me/preferences') {
    if (!hasFixtureSession(request)) return sendJson(response, 401, { detail: 'Local smoke session required' })
    return sendJson(response, 200, {
      region_id: 'vinh-long',
      region_label: 'Vĩnh Long',
      region_scope: 'province',
      location_source: 'manual',
      location_accuracy: 'province',
      location_consent_state: 'granted',
      location_enabled: true,
      personalization_enabled: true,
      explicit_interests: [],
      recommendation_reset_at: null,
      consent_version: 'task8-smoke',
      revision: 1,
    })
  }

  return sendJson(response, 200, {})
}

export async function createTask8SmokeServer({ port = 8468 } = {}) {
  const server = createServer((request, response) => {
    void handleRequest(request, response).catch(() => sendJson(response, 500, { detail: 'Local smoke fixture error' }))
  })
  await new Promise((resolveReady, reject) => {
    server.once('error', reject)
    server.listen(port, HOST, resolveReady)
  })
  const address = server.address()
  const selectedPort = typeof address === 'object' && address ? address.port : port
  return {
    origin: `http://${HOST}:${selectedPort}`,
    close: () => new Promise((resolveClosed, reject) => server.close(error => error ? reject(error) : resolveClosed())),
  }
}

const invokedPath = process.argv[1] ? resolve(process.argv[1]) : ''
if (invokedPath === fileURLToPath(import.meta.url)) {
  const portIndex = process.argv.indexOf('--port')
  const requestedPort = portIndex >= 0 ? Number(process.argv[portIndex + 1]) : 8468
  const fixture = await createTask8SmokeServer({ port: Number.isInteger(requestedPort) ? requestedPort : 8468 })
  console.log(`Task 8 smoke backend listening at ${fixture.origin}`)
}
