import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'
import EntitiesPage from '../pages/admin/entities.vue'
import MediaPage from '../pages/admin/media.vue'
import ProvisionalReviewPage from '../pages/admin/duyet-tu-hoc.vue'
import { aiDisclosure } from '../utils/aiDisclosure'
import { normalizeEntityEditorialUpload } from '../utils/imageDescriptors'

const mocks = vi.hoisted(() => ({
  authHeaders: vi.fn(() => ({ 'X-Admin-Key': 'test-key' })),
  confirmDialog: vi.fn(() => Promise.resolve(true)),
  fetch: vi.fn(),
  fetchMe: vi.fn(() => Promise.resolve()),
  showToast: vi.fn(),
  setPref: vi.fn(),
}))

mockNuxtImport('useAuth', () => () => ({
  authHeaders: mocks.authHeaders,
  fetchMe: mocks.fetchMe,
  user: { value: null },
}))
mockNuxtImport('useConfirm', () => () => ({ confirmDialog: mocks.confirmDialog }))
mockNuxtImport('useToast', () => () => ({ show: mocks.showToast }))
mockNuxtImport('useTimeAgo', () => () => ({ timeAgo: (value: string) => value }))
mockNuxtImport('useAdminPrefs', () => () => ({
  prefs: { value: { pageSize: 30, entityTypeFilter: '' } },
  setPref: mocks.setPref,
}))
mockNuxtImport('useModalA11y', () => () => undefined)

const safeEntityUrl = 'https://safe.example/entity.webp'
const canonicalEntityUrl = '/img/entities/dia-diem-thu.webp'
const canonicalMediaUrl = '/img/entities/dia-diem-thu-media.webp'
const invalidJavascript = 'javascript:alert(1)'
const invalidObject = { url: 'not-a-url', note: '<script>bad</script>' }

interface FetchDispatchOptions {
  entityImages?: string[]
  addedImages?: string[]
  uploadedImages?: string[]
  uploadError?: unknown
  mediaItems?: Array<Record<string, unknown>>
}

function installFetchDispatch(options: FetchDispatchOptions = {}) {
  const entityImages = options.entityImages ?? [canonicalEntityUrl]
  mocks.fetch.mockImplementation((input: unknown, init?: { method?: string }) => {
    const url = String(input)
    if (url === '/admin-api/entity-schema') return Promise.resolve({ types: {} })
    if (url === '/admin-api/entity-kinds') return Promise.resolve({ kinds: [], grand_total: 0 })
    if (url.startsWith('/admin-api/entities?')) {
      return Promise.resolve({
        entities: [{ id: 'entity-1', name: 'Địa điểm thử', type: 'experience', summary: 'Tóm tắt', images: entityImages }],
        total: 1,
      })
    }
    if (url === '/admin-api/entities/places') return Promise.resolve([])
    if (url.startsWith('/api/entities/entity-1/relationships')) return Promise.resolve({ relationships: [] })
    if (url === '/admin-api/entities/entity-1/history') return Promise.resolve({ history: [] })
    if (url === '/admin-api/entities/entity-1/images' && init?.method === 'POST') {
      return Promise.resolve({ images: options.addedImages ?? [...entityImages, canonicalMediaUrl] })
    }
    if (url === '/admin-api/entities/entity-1' && !init?.method) {
      return Promise.resolve({ id: 'entity-1', name: 'Địa điểm thử', images: entityImages })
    }
    if (url === '/admin-api/entities/entity-1/images/0' && init?.method === 'DELETE') {
      return Promise.resolve({ status: 'removed', images: entityImages.slice(1) })
    }
    if (url === '/admin-api/entities/entity-1/images/upload' && init?.method === 'POST') {
      if (options.uploadError !== undefined) return Promise.reject(options.uploadError)
      return Promise.resolve({ images: options.uploadedImages ?? [...entityImages, canonicalMediaUrl] })
    }
    if (url.startsWith('/admin-api/media?')) {
      return Promise.resolve({
        items: options.mediaItems ?? [{ url: canonicalMediaUrl, entity_id: 'entity-1', entity_name: 'Địa điểm thử', entity_type: 'experience', credit: '', license: '', usage_count: 1 }],
        total: 1,
        stats: { total_images: 1, duplicates: 0, missing_credit: 1 },
      })
    }
    if (url === '/admin-api/provisional') {
      return Promise.resolve({
        provisional: [{
          id: 'prov-1',
          review_token: 'a'.repeat(64),
          entity: {
            id: 'prov-1',
            name: 'Entity tự học',
            type: 'experience',
            summary: 'Nội dung cần duyệt',
            images: [canonicalEntityUrl, invalidJavascript, invalidObject],
          },
        }],
      })
    }
    return Promise.resolve({})
  })
}

async function flushUi() {
  await new Promise(resolve => setTimeout(resolve, 0))
  await nextTick()
}

beforeEach(() => {
  mocks.authHeaders.mockClear()
  mocks.confirmDialog.mockClear()
  mocks.confirmDialog.mockResolvedValue(true)
  mocks.fetchMe.mockClear()
  mocks.showToast.mockClear()
  mocks.setPref.mockClear()
  mocks.fetch.mockReset()
  installFetchDispatch()
  vi.stubGlobal('$fetch', mocks.fetch)
})

describe('admin entity/media/self-learning image disclosure', () => {
  it('associates dense entity thumbnails and media cards with short and full disclosure', async () => {
    const entities = await mountSuspended(EntitiesPage, {
      global: { stubs: { LazyAdminKindCompleteness: true } },
    })
    await flushUi()

    const thumbnail = entities.get('.ent-thumb img')
    expect(thumbnail.attributes('src')).toBe(canonicalEntityUrl)
    expect(thumbnail.attributes('aria-describedby')).toBeTruthy()
    expect(entities.get(`[id="${thumbnail.attributes('aria-describedby')}"]`).text()).toBe(aiDisclosure.entity_ai.full_disclosure)
    expect(entities.text()).toContain(aiDisclosure.entity_ai.short_label)

    const media = await mountSuspended(MediaPage)
    await flushUi()
    const grid = media.get('[data-admin-media-grid]')
    const card = grid.get('[data-open-preview]')
    const cardImage = card.get('img')
    expect(cardImage.attributes('src')).toBe(canonicalMediaUrl)
    expect(cardImage.attributes('aria-describedby')).toBeTruthy()
    expect(media.get(`[id="${cardImage.attributes('aria-describedby')}"]`).text()).toBe(aiDisclosure.entity_ai.full_disclosure)
    await card.trigger('click')
    await nextTick()
    expect(media.get('[data-expanded-preview]').text()).toContain(aiDisclosure.entity_ai.full_disclosure)

    entities.unmount()
    media.unmount()
  })

  it('renders full disclosure in entity editor, media preview, and self-learning inspector', async () => {
    const entities = await mountSuspended(EntitiesPage, {
      global: { stubs: { LazyAdminKindCompleteness: true } },
    })
    await flushUi()
    await entities.get('button[aria-label="Sửa Địa điểm thử"]').trigger('click')
    await flushUi()
    expect(entities.get('[data-expanded-preview]').text()).toContain(aiDisclosure.entity_ai.full_disclosure)
    await entities.get('input[aria-label="URL ảnh AI biên tập mới"]').setValue(canonicalMediaUrl)
    await entities.findAll('button').find(button => button.text() === 'Thêm ảnh')!.trigger('click')
    await flushUi()
    expect(mocks.fetch).toHaveBeenCalledWith('/admin-api/entities/entity-1/images', expect.objectContaining({
      body: { url: canonicalMediaUrl },
    }))

    const media = await mountSuspended(MediaPage)
    await flushUi()
    await media.get('[data-open-preview]').trigger('click')
    await nextTick()
    expect(media.get('[data-expanded-preview]').text()).toContain(aiDisclosure.entity_ai.full_disclosure)

    const provisional = await mountSuspended(ProvisionalReviewPage)
    await flushUi()
    expect(provisional.get('[data-self-learning-inspector]').text()).toContain(aiDisclosure.entity_ai.full_disclosure)

    entities.unmount()
    media.unmount()
    provisional.unmount()
  })

  it('keeps noncanonical stored media inspectable and removable in admin moderation', async () => {
    const rawMediaUrl = '/uploads/community-photo.webp'
    installFetchDispatch({
      entityImages: [rawMediaUrl],
      mediaItems: [{ url: rawMediaUrl, entity_id: 'entity-1', entity_name: 'Địa điểm thử', entity_type: 'experience', credit: '', license: '', usage_count: 1 }],
    })

    const media = await mountSuspended(MediaPage)
    await flushUi()
    const card = media.get('[data-open-preview]')
    expect(card.get('img').attributes('src')).toBe(rawMediaUrl)
    await card.trigger('click')
    await nextTick()
    await media.get('.media-preview-actions button').trigger('click')
    await flushUi()

    expect(mocks.fetch).toHaveBeenCalledWith('/admin-api/entities/entity-1/images/0', expect.objectContaining({
      method: 'DELETE',
    }))
    expect(media.find('[data-expanded-preview]').exists()).toBe(false)
    media.unmount()
  })

  it('fails closed for malformed provisional values while preserving an audit trail', async () => {
    const provisional = await mountSuspended(ProvisionalReviewPage)
    await flushUi()

    expect(provisional.findAll('img')).toHaveLength(0)
    expect(provisional.findAll('[data-provisional-image-link]').map(node => node.attributes('href'))).toEqual([canonicalEntityUrl])
    expect(provisional.text()).toContain(invalidJavascript)
    expect(provisional.text()).toContain(JSON.stringify(invalidObject, null, 2))
    expect(provisional.findAll('pre').some(node => node.text().includes(invalidJavascript))).toBe(true)
    expect(provisional.findAll('pre').some(node => node.text().includes('not-a-url'))).toBe(true)
    provisional.unmount()
  })

  it('keeps a successful URL add truthful when the response includes a malformed legacy entry', async () => {
    installFetchDispatch({
      entityImages: [canonicalEntityUrl, invalidJavascript],
      addedImages: [canonicalEntityUrl, invalidJavascript, canonicalMediaUrl],
    })
    const entities = await mountSuspended(EntitiesPage, {
      global: { stubs: { LazyAdminKindCompleteness: true } },
    })
    await flushUi()
    await entities.get('button[aria-label="Sửa Địa điểm thử"]').trigger('click')
    await flushUi()

    const input = entities.get('input[aria-label="URL ảnh AI biên tập mới"]')
    await input.setValue(canonicalMediaUrl)
    await entities.findAll('button').find(button => button.text() === 'Thêm ảnh')!.trigger('click')
    await flushUi()

    expect((input.element as HTMLInputElement).value).toBe('')
    expect(mocks.showToast).toHaveBeenCalledWith('Đã thêm ảnh', 'success')
    expect(entities.findAll('[data-admin-entity-image-row] img').map(node => node.attributes('src'))).toEqual([
      canonicalEntityUrl,
      canonicalMediaUrl,
    ])
    expect(entities.findAll('[data-admin-entity-image-row] pre').map(node => node.text())).toContain(invalidJavascript)
    entities.unmount()
  })

  it('rejects unproven file uploads with ai_only_media without changing the image rows', async () => {
    installFetchDispatch({
      entityImages: [canonicalEntityUrl, invalidJavascript],
      uploadError: {
        response: {
          status: 400,
          _data: {
            detail: {
              code: 'ai_only_media',
              message: 'Only canonical AI-generated entity media is accepted.',
            },
          },
        },
      },
    })
    const entities = await mountSuspended(EntitiesPage, {
      global: { stubs: { LazyAdminKindCompleteness: true } },
    })
    await flushUi()
    await entities.get('button[aria-label="Sửa Địa điểm thử"]').trigger('click')
    await flushUi()

    const input = entities.get('input[type="file"]')
    Object.defineProperty(input.element, 'files', {
      configurable: true,
      value: [new File(['ai-image'], 'editorial.webp', { type: 'image/webp' })],
    })
    await input.trigger('change')
    await flushUi()

    expect(mocks.showToast).toHaveBeenCalledWith({
      code: 'ai_only_media',
      message: 'Only canonical AI-generated entity media is accepted.',
    }, 'error')
    expect(entities.findAll('[data-admin-entity-image-row] img').map(node => node.attributes('src'))).toEqual([
      canonicalEntityUrl,
    ])
    expect(entities.findAll('[data-admin-entity-image-row] pre').map(node => node.text())).toContain(invalidJavascript)
    entities.unmount()
  })

  it('normalizes only canonical AI editorial entity uploads', () => {
    const descriptor = normalizeEntityEditorialUpload({
      url: safeEntityUrl,
      alt: 'Địa điểm thử — ảnh minh họa',
      credit: null,
      width: null,
      height: null,
      source_class: 'ai-generated',
      source_kind: 'entity-editorial',
      disclosure_key: 'entity-ai',
      short_label: aiDisclosure.entity_ai.short_label,
      full_disclosure: aiDisclosure.entity_ai.full_disclosure,
    })
    expect(descriptor.url).toBe(safeEntityUrl)
    expect(() => normalizeEntityEditorialUpload({
      ...descriptor,
      source_class: 'user-uploaded',
    })).toThrow(/entity\.images accepts AI editorial media only.*entity\.images chỉ nhận AI editorial/s)
    expect(() => normalizeEntityEditorialUpload({
      ...descriptor,
      source_kind: 'review-ugc',
    })).toThrow(/entity\.images accepts AI editorial media only.*entity\.images chỉ nhận AI editorial/s)
    expect(() => normalizeEntityEditorialUpload({
      ...descriptor,
      disclosure_key: 'ugc-photo',
    })).toThrow(/entity\.images accepts AI editorial media only.*entity\.images chỉ nhận AI editorial/s)
    expect(() => normalizeEntityEditorialUpload({
      ...descriptor,
      unexpected: true,
    })).toThrow(/entity\.images accepts AI editorial media only.*entity\.images chỉ nhận AI editorial/s)
  })
})
