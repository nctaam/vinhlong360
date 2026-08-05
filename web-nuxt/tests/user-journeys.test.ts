// Test tầng NGƯỜI DÙNG cho bốn luồng chính: tìm kiếm, khám phá, xem chi tiết,
// và trạng thái thiếu dữ liệu.
//
// Nguyên tắc của file này (rút từ bài học nội bộ 2026-08-04):
//   - Mount trang thật bằng mountSuspended, chỉ giả lập ĐÚNG một ranh giới: mạng
//     (utils/apiFetch). Mọi composable, mọi component hiển thị đều chạy thật.
//   - Chỉ assert thứ người dùng thấy hoặc trình đọc màn hình đọc được: chữ trên
//     màn hình, role, aria-*, liên kết. KHÔNG assert chuỗi trong source — loại
//     test đó đỏ khi refactor đúng và xanh khi hành vi sai.
import { clearNuxtData } from '#app'
import { mountSuspended } from '@nuxt/test-utils/runtime'
import { defineComponent, h, nextTick } from 'vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import EntityDetailPage from '../pages/dia-diem/[id].vue'
import SearchPage from '../pages/tim-kiem.vue'
import TourismPage from '../pages/du-lich.vue'
import { aiDisclosure } from '../utils/aiDisclosure'

const apiFetchMock = vi.hoisted(() => vi.fn())
vi.mock('../utils/apiFetch', () => ({ apiFetch: apiFetchMock }))

// ── Mạng giả: mỗi test khai báo backend trả gì cho từng đường dẫn thật ────────
type Backend = (url: string) => unknown
let backend: Backend = () => ({})

const wrappers: Array<{ unmount: () => void }> = []

const NuxtImgStub = defineComponent({
  inheritAttrs: false,
  props: { src: String, alt: String },
  setup(props, { attrs }) {
    return () => h('img', { ...attrs, src: props.src, alt: props.alt })
  },
})
const IconLineStub = { props: ['name'], template: '<i :data-icon="name" />' }

// Chỉ stub thứ KHÔNG thuộc luồng đang kiểm (widget nền, lazy island, ảnh CDN).
// EntityCard, EmptyState, ImageDisclosure, SourceMark, EntityTrustPanel,
// EntityHeroPlaceholder, FilterChips đều để chạy thật — chúng chính là thứ
// người dùng nhìn.
const searchStubs = {
  NuxtImg: NuxtImgStub,
  IconLine: IconLineStub,
  Breadcrumb: true,
  SkeletonGrid: { props: ['count'], template: '<div data-skeleton-grid />' },
  SaveButton: true,
  AISearchAssist: true,
  LazyAISearchAssist: true,
  SmartRecommendations: true,
  LazySmartRecommendations: true,
  JourneyActionRail: true,
  JourneyBar: true,
  LazyJourneyBar: true,
}

const tourismStubs = {
  NuxtImg: NuxtImgStub,
  IconLine: IconLineStub,
  Breadcrumb: true,
  CountUp: { props: ['value'], template: '<span>{{ value }}</span>' },
  SkeletonGrid: true,
  SaveButton: true,
  JourneyBar: true,
  LazyJourneyBar: true,
}

const detailStubs = {
  NuxtImg: NuxtImgStub,
  IconLine: IconLineStub,
  Breadcrumb: true,
  SaveButton: true,
  ShareButton: true,
  EntityMap: true,
  LazyEntityMap: true,
  EntityFeed: true,
  LazyEntityFeed: true,
  EntityReviews: true,
  LazyEntityReviews: true,
  ReviewSection: true,
  PhotoGallery: true,
  LazyPhotoGallery: true,
  ImageLightbox: true,
  LazyImageLightbox: true,
  NearbyEntities: true,
  LazyNearbyEntities: true,
  SmartRecommendations: true,
  LazySmartRecommendations: true,
  AIRecommendations: true,
  LazyAIRecommendations: true,
  AITravelTips: true,
  LazyAITravelTips: true,
  AIBestTime: true,
  LazyAIBestTime: true,
  ContactWidget: true,
  LazyContactWidget: true,
  JourneyBar: true,
  LazyJourneyBar: true,
}

function aiImage(url: string, alt: string) {
  return {
    url,
    alt,
    source_class: 'ai-generated',
    source_kind: 'entity-editorial',
    disclosure_key: 'entity-ai',
    short_label: aiDisclosure.entity_ai.short_label,
    full_disclosure: aiDisclosure.entity_ai.full_disclosure,
    credit: null,
    width: 1200,
    height: 800,
  }
}

function emptySearchPayload() {
  return { entities: [], posts: [], users: [], totals: { entities: 0, posts: 0, users: 0 } }
}

async function flushUi() {
  await new Promise(resolve => setTimeout(resolve, 0))
  await nextTick()
  await new Promise(resolve => setTimeout(resolve, 0))
}

async function mountPage(component: unknown, route: string, stubs: Record<string, unknown>) {
  const wrapper = await mountSuspended(component as never, { route, global: { stubs } })
  wrappers.push(wrapper)
  await flushUi()
  return wrapper
}

/** Đọc chữ của phần tử mà aria-describedby trỏ tới — đúng thứ trình đọc màn hình đọc. */
function describedText(wrapper: { get: (selector: string) => { text: () => string } }, id: string | undefined) {
  expect(id, 'phần tử phải có aria-describedby').toBeTruthy()
  return wrapper.get(`#${id}`).text()
}

beforeEach(() => {
  backend = () => ({})
  apiFetchMock.mockReset()
  apiFetchMock.mockImplementation((url: unknown) => {
    try {
      return Promise.resolve(backend(String(url)))
    } catch (error) {
      return Promise.reject(error)
    }
  })
  localStorage.clear()
  sessionStorage.clear()
})

afterEach(async () => {
  for (const wrapper of wrappers.splice(0)) wrapper.unmount()
  await clearNuxtData()
})

// ── Luồng 1: Tìm kiếm ────────────────────────────────────────────────────────
describe('Luồng người dùng: tìm kiếm', () => {
  it('gõ từ khoá có kết quả thì thấy kết quả bấm được, không thấy báo lỗi', async () => {
    backend = url => url.startsWith('/api/search')
      ? {
          ...emptySearchPayload(),
          entities: [{
            id: 'gom-do-mang-thit',
            type: 'craft_village',
            name: 'Gốm đỏ Mang Thít',
            summary: 'Lò gạch gốm dọc sông Cổ Chiên, nghề còn đỏ lửa mỗi sáng.',
            images: ['/img/entities/gom-do-mang-thit.webp'],
            quality: { source_tier: 'official' },
          }],
          totals: { entities: 1, posts: 0, users: 0 },
        }
      : {}

    const wrapper = await mountPage(SearchPage, '/tim-kiem?q=g%E1%BB%91m', searchStubs)

    const grid = wrapper.get('.grid')
    expect(grid.text()).toContain('Gốm đỏ Mang Thít')
    expect(grid.get('a.card-body-link').attributes('href')).toBe('/dia-diem/gom-do-mang-thit')
    expect(wrapper.text()).toContain('„gốm"')
    expect(wrapper.find('[role="alert"]').exists()).toBe(false)
    expect(wrapper.find('.empty-state').exists()).toBe(false)
  })

  it('không có kết quả thì thấy trạng thái rỗng có nghĩa kèm lối đi tiếp', async () => {
    backend = url => url.startsWith('/api/search') ? emptySearchPayload() : {}

    const wrapper = await mountPage(SearchPage, '/tim-kiem?q=kh%C3%B4ng-c%C3%B3', searchStubs)

    const empty = wrapper.get('.empty-state')
    expect(empty.attributes('role')).toBe('status')
    expect(empty.get('.empty-title').text()).toBe('Chưa thấy đúng ý bạn')
    // "Có nghĩa" = có câu giải thích thật, không phải một ô trống hay dấu ba chấm.
    expect(empty.get('.empty-text').text().length).toBeGreaterThan(20)
    // Và có ít nhất một lối đi tiếp, để đây không phải ngõ cụt.
    const exits = empty.findAll('a').map(link => link.attributes('href'))
    expect(exits).toContain('/du-lich')
    expect(exits).toContain('/san-pham')
    expect(wrapper.find('.grid').exists()).toBe(false)
  })

  it('API lỗi thì thấy thông báo lỗi role=alert và ô tìm kiếm vẫn dùng được', async () => {
    backend = (url) => {
      if (url.startsWith('/api/search')) throw new Error('backend sập')
      return {}
    }

    const wrapper = await mountPage(SearchPage, '/tim-kiem?q=g%E1%BB%91m', searchStubs)

    const alert = wrapper.get('[role="alert"]')
    expect(alert.text()).toContain('Lỗi tìm kiếm')
    expect(alert.text()).toContain('Vui lòng thử lại')
    // Không phải trang trắng: người dùng vẫn còn ô tìm kiếm và biết nó đang lỗi.
    const input = wrapper.get('input[type="search"]')
    expect(input.attributes('aria-invalid')).toBe('true')
    expect(wrapper.get('h1').text().length).toBeGreaterThan(0)

    // Và nút "Thử lại" phải thật sự gọi lại backend rồi hiện kết quả.
    const retry = alert.findAll('button').find(button => button.text().includes('Thử lại'))
    expect(retry, 'trạng thái lỗi phải có nút thử lại').toBeTruthy()
    backend = url => url.startsWith('/api/search')
      ? {
          ...emptySearchPayload(),
          entities: [{ id: 'gom-1', type: 'craft_village', name: 'Gốm đỏ Mang Thít' }],
          totals: { entities: 1, posts: 0, users: 0 },
        }
      : {}
    await retry!.trigger('click')
    await vi.waitFor(() => expect(wrapper.text()).toContain('Gốm đỏ Mang Thít'))
    expect(wrapper.find('[role="alert"]').exists()).toBe(false)
    expect(wrapper.get('input[type="search"]').attributes('aria-invalid')).toBeUndefined()
  })
})

// ── Luồng 2: Khám phá ────────────────────────────────────────────────────────
describe('Luồng người dùng: khám phá', () => {
  const craft = {
    id: 'lang-gom-mang-thit',
    type: 'craft_village',
    name: 'Làng gốm Mang Thít',
    summary: 'Hàng ngàn lò gạch gốm dọc sông Cổ Chiên.',
    quality: { source_tier: 'official' },
  }
  const stay = {
    id: 'nha-vuon-cu-lao',
    type: 'accommodation',
    name: 'Nhà vườn Cù Lao An Bình',
    summary: 'Ngủ đêm giữa vườn chôm chôm, sáng dậy nghe chim.',
    quality: { source_tier: 'community' },
  }

  it('đổi chế độ lọc thì danh sách đổi theo và nút được chọn có aria-pressed', async () => {
    backend = url => url.startsWith('/api/entities') ? { entities: [craft, stay], total: 2 } : {}

    const wrapper = await mountPage(TourismPage, '/du-lich', tourismStubs)

    const browse = wrapper.get('section[aria-label="Duyệt tất cả du lịch"]')
    expect(browse.text()).toContain('Làng gốm Mang Thít')
    expect(browse.text()).toContain('Nhà vườn Cù Lao An Bình')
    expect(browse.get('.result-meta').text()).toContain('2 kết quả')

    const typeGroup = wrapper.get('[aria-label="Lọc theo loại"]')
    const chips = typeGroup.findAll('button')
    const craftChip = chips.find(chip => chip.text().includes('Làng nghề'))
    const allChip = chips.find(chip => chip.text().includes('Tất cả'))
    expect(craftChip && allChip, 'phải có chip "Tất cả" và "Làng nghề"').toBeTruthy()
    expect(allChip!.attributes('aria-pressed')).toBe('true')

    await craftChip!.trigger('click')
    await flushUi()

    // Danh sách đổi theo…
    expect(browse.text()).toContain('Làng gốm Mang Thít')
    expect(browse.text()).not.toContain('Nhà vườn Cù Lao An Bình')
    expect(browse.get('.result-meta').text()).toContain('1 kết quả')
    // …và trạng thái chọn đọc được không cần nhìn màu.
    expect(craftChip!.attributes('aria-pressed')).toBe('true')
    expect(allChip!.attributes('aria-pressed')).toBe('false')
  })

  it('đổi cách hiển thị thì bố cục đổi và nút được chọn có aria-pressed', async () => {
    backend = url => url.startsWith('/api/entities') ? { entities: [craft, stay], total: 2 } : {}

    const wrapper = await mountPage(TourismPage, '/du-lich', tourismStubs)
    const browse = wrapper.get('section[aria-label="Duyệt tất cả du lịch"]')
    expect(browse.find('.grid').exists()).toBe(true)

    const listButton = wrapper.get('.vt-btn[aria-label="Dạng danh sách"]')
    const gridButton = wrapper.get('.vt-btn[aria-label="Dạng lưới"]')
    expect(gridButton.attributes('aria-pressed')).toBe('true')

    await listButton.trigger('click')
    await flushUi()

    expect(browse.find('.list-view').exists()).toBe(true)
    expect(browse.find('.grid').exists()).toBe(false)
    expect(listButton.attributes('aria-pressed')).toBe('true')
    expect(gridButton.attributes('aria-pressed')).toBe('false')
    // Đổi bố cục không được làm mất nội dung.
    expect(browse.text()).toContain('Làng gốm Mang Thít')
    expect(browse.text()).toContain('Nhà vườn Cù Lao An Bình')
  })
})

// ── Luồng 3: Chi tiết ────────────────────────────────────────────────────────
describe('Luồng người dùng: mở trang chi tiết', () => {
  it('thấy tên, nhãn nguồn tin và nhãn ảnh minh hoạ AI', async () => {
    const hero = aiImage('/img/entities/chua-vam-ray.webp', 'Chùa Vàm Ray — ảnh minh họa')
    backend = (url) => {
      if (url.startsWith('/seo/jsonld/')) return null
      if (url === '/api/entities/chua-vam-ray/gallery') return { images: [hero] }
      if (url.startsWith('/api/entities/chua-vam-ray/relationships')) return { relationships: [], total: 0 }
      if (url === '/api/entities/chua-vam-ray') {
        return {
          id: 'chua-vam-ray',
          type: 'attraction',
          name: 'Chùa Vàm Ray',
          summary: 'Ngôi chùa Khmer mái vàng giữa vườn dừa.',
          place_name: 'Xã Hàm Tân',
          attributes: {},
          images: [hero.url],
          quality: { source_tier: 'official', source_title: 'Cổng thông tin tỉnh Vĩnh Long' },
        }
      }
      return {}
    }

    const wrapper = await mountPage(EntityDetailPage, '/dia-diem/chua-vam-ray', detailStubs)

    // 1. Tên
    expect(wrapper.get('h1').text()).toBe('Chùa Vàm Ray')

    // 2. Nhãn nguồn tin — hạng nguồn đọc được thành chữ, không chỉ bằng màu.
    const sourceMark = wrapper.get('[data-source-mark]')
    expect(sourceMark.attributes('data-source-tier')).toBe('official')
    expect(sourceMark.text()).toContain('Chính thức')
    const trust = wrapper.get('[data-entity-trust-panel]')
    expect(trust.text()).toContain('Cổng thông tin tỉnh Vĩnh Long')
    expect(trust.get('[data-report-action]').text()).toContain('Báo sai')
    // Byline không được khai khống "đã kiểm chứng" khi chưa có verifiedAt.
    expect(wrapper.text()).toContain('chưa kiểm chứng thực địa')

    // 3. Nhãn ảnh minh hoạ AI — thấy nhãn ngắn, và mô tả đầy đủ được gắn vào ảnh.
    const heroFigure = wrapper.get('[data-entity-hero]')
    const heroImage = heroFigure.get('img')
    expect(heroImage.attributes('alt')).toBe('Chùa Vàm Ray — ảnh minh họa')
    expect(heroFigure.text()).toContain(aiDisclosure.entity_ai.short_label)
    expect(describedText(wrapper, heroImage.attributes('aria-describedby')))
      .toBe(aiDisclosure.entity_ai.full_disclosure)
    // Ảnh AI không được tự nhận là ảnh thật.
    expect(heroFigure.text()).not.toContain('ảnh thật')
  })
})

// ── Luồng 4: Thiếu dữ liệu ───────────────────────────────────────────────────
describe('Luồng người dùng: entity chưa có ảnh', () => {
  it('kết quả tìm kiếm không ảnh vẫn có placeholder được dán nhãn, không phải ô trống câm', async () => {
    backend = url => url.startsWith('/api/search')
      ? {
          ...emptySearchPayload(),
          entities: [{
            id: 'dinh-long-thanh',
            type: 'attraction',
            name: 'Đình Long Thanh',
            summary: 'Đình làng thời khẩn hoang bên rạch Long Hồ.',
          }],
          totals: { entities: 1, posts: 0, users: 0 },
        }
      : {}

    const wrapper = await mountPage(SearchPage, '/tim-kiem?q=%C4%91%C3%ACnh', searchStubs)

    const cover = wrapper.get('article.card .cover')
    expect(cover.classes()).toContain('cover-generated')
    expect(cover.find('img').exists()).toBe(false)
    // Ô ảnh vẫn có motif loại được vẽ thật — không phải khoảng trắng.
    // (Nền gradient data-URI không kiểm được ở đây: happy-dom loại bỏ giá trị
    // background-image dạng url('data:image/svg+xml,...'), nên ta kiểm motif.)
    const glyph = cover.get('.cover-svg-icon')
    expect(glyph.find('svg').exists()).toBe(true)
    expect(glyph.element.innerHTML).toMatch(/<(path|rect|circle|ellipse|line)\b/)
    // Và nó tự khai là minh hoạ đồ hoạ, không phải ảnh thật.
    expect(cover.text()).toContain(aiDisclosure.placeholder.full_disclosure)
    expect(cover.find('[data-short-label]').exists()).toBe(false)
  })

  it('trang chi tiết không ảnh vẫn có hero được dán nhãn và mô tả cho trình đọc màn hình', async () => {
    backend = (url) => {
      if (url.startsWith('/seo/jsonld/')) return null
      if (url === '/api/entities/dinh-long-thanh/gallery') return { images: [] }
      if (url.startsWith('/api/entities/dinh-long-thanh/relationships')) return { relationships: [], total: 0 }
      if (url === '/api/entities/dinh-long-thanh') {
        return {
          id: 'dinh-long-thanh',
          type: 'attraction',
          name: 'Đình Long Thanh',
          summary: 'Đình làng thời khẩn hoang bên rạch Long Hồ.',
          attributes: {},
          images: [],
        }
      }
      return {}
    }

    const wrapper = await mountPage(EntityDetailPage, '/dia-diem/dinh-long-thanh', detailStubs)

    const heroFigure = wrapper.get('[data-entity-hero]')
    expect(heroFigure.find('img').exists()).toBe(false)
    expect(heroFigure.attributes('role')).toBe('img')
    expect(heroFigure.attributes('aria-label')).toBe('Đình Long Thanh — chưa có ảnh riêng')
    // Hero rỗng vẫn được vẽ: motif loại + tấm placeholder có sắc vật liệu.
    expect(heroFigure.get('.dc-motif').find('svg').exists()).toBe(true)
    expect(heroFigure.get('.dc-placeholder').attributes('role')).toBe('img')
    expect(describedText(wrapper, heroFigure.attributes('aria-describedby')))
      .toBe(aiDisclosure.placeholder.full_disclosure)
    // Nhãn hiện thành chữ ngay trên hero, không phải chỉ ẩn cho screen reader.
    expect(heroFigure.text()).toContain(aiDisclosure.placeholder.full_disclosure)
    // Không có nút "Xem ảnh" khi chưa có ảnh nào.
    expect(heroFigure.find('.dc-photo-btn').exists()).toBe(false)
  })
})
