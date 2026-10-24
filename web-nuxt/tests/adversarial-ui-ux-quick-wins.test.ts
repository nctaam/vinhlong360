import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const webRoot = resolve(__dirname, '..')
const readWebFile = (relPath: string) => readFileSync(resolve(webRoot, relPath), 'utf8')

describe('Adversarial UI/UX & Frontend Quick Wins (QW-53 to QW-62)', () => {
  it('QW-53 & QW-57: index.vue serves responsive Hero srcset and marks sr-only link blocks as inert', () => {
    const indexVue = readWebFile('pages/index.vue')
    expect(indexVue).toContain('srcset="/img/spread/song-nuoc-640.webp 640w, /img/spread/song-nuoc-1024.webp 1024w, /img/spread/song-nuoc.webp 1920w"')
    expect(indexVue).toContain('sizes="100vw"')
    expect(indexVue).toContain('<HomeDecisionLedger :entries="homePresentation.decisionEntries" class="sr-only" inert />')
    expect(indexVue).toContain('<HomeLocalBriefing class="sr-only" inert />')
    expect(indexVue).not.toContain('import HomeAtmosphereControl from')
    expect(indexVue).not.toContain('COGNITIVE CONTEXTUAL BANNER (ASTRONOMICAL TIDE & SEASONS)')
  })

  it('QW-54: SearchAutocomplete uses unique instanceId for ARIA combobox/listbox and supports @click on recent searches', () => {
    const searchAutocomplete = readWebFile('components/SearchAutocomplete.vue')
    expect(searchAutocomplete).toContain('const instanceId = useId()')
    expect(searchAutocomplete).toContain(':aria-controls="`${instanceId}-listbox`"')
    expect(searchAutocomplete).toContain('@click="useRecent(term)"')
  })

  it('QW-55 & QW-56: variables.css defines --mekong-ink-rgb and tri-region-color.css preserves --focus-double-ring', () => {
    const variablesCss = readWebFile('assets/css/variables.css')
    const triRegionCss = readWebFile('assets/css/tri-region-color.css')
    const detailCss = readWebFile('assets/css/detail.css')
    const componentsCss = readWebFile('assets/css/components.css')

    expect(variablesCss).toContain('--mekong-ink-rgb: 8, 26, 22;')
    expect(triRegionCss).toContain('box-shadow: var(--focus-double-ring);')
    expect(detailCss).toContain('display: flow-root;')
    expect(componentsCss).toContain('@media (hover: none), (pointer: coarse)')
  })

  it('QW-59 & QW-60: shell.css eliminates transition: all and defines symmetric .closing animations; base.css syncs --header-h and preserves sk-shimmer pulse', () => {
    const shellCss = readWebFile('assets/css/shell.css')
    const baseCss = readWebFile('assets/css/base.css')

    expect(shellCss).not.toMatch(/transition:\s*all\b/)
    expect(shellCss).toContain('.public-shell-catalog.closing')
    expect(shellCss).toContain('@keyframes shell-panel-out')
    expect(shellCss).toContain('@keyframes shell-drawer-out')
    expect(baseCss).toContain('--header-h: var(--shell-public-header-height, 70px);')
    expect(baseCss).toContain('*:not(.sk-shimmer)::after')
  })

  it('QW-61 & QW-62: HomeRiversideStays removes nested card-in-card wrapper and sua-thong-tin.vue focuses receiptPanelRef on submit', () => {
    const riversideStays = readWebFile('components/home/HomeRiversideStays.vue')
    const suaThongTin = readWebFile('pages/yeu-cau/sua-thong-tin.vue')

    expect(riversideStays).toContain('border-top: 1px solid var(--border-liquid-glass, var(--color-border));')
    expect(suaThongTin).toContain('ref="receiptPanelRef"')
    expect(suaThongTin).toContain('tabindex="-1"')
    expect(suaThongTin).toContain('receiptPanelRef.value?.focus()')
  })

  it('QW-65, QW-66 & QW-67: Declutters AEO watermarks, redundant badge pills, and fake hardcoded weather pill', () => {
    const detailAeo = readWebFile('components/DetailAeoSummary.vue')
    const catalogAeo = readWebFile('components/CatalogAeoPlaque.vue')
    const indexVue = readWebFile('pages/index.vue')
    const detailVue = readWebFile('pages/dia-diem/[id].vue')

    expect(detailAeo).not.toContain('detail-aeo-summary__watermark')
    expect(detailAeo).toContain('detail-aeo-summary__stamp sr-only')
    expect(catalogAeo).toContain('catalog-aeo-plaque__stamp sr-only')
    expect(catalogAeo).toContain("kicker: 'Góc nhìn bản địa · Giải đáp nhanh',")
    expect(catalogAeo).not.toContain('Giải đáp nhanh AEO')
    expect(indexVue).not.toContain('hero-cognitive-chip--weather')
    expect(indexVue).not.toContain('28°C Nắng dịu')
    expect(detailVue).toContain('article-sourcemark-label sr-only')
  })

  it('QW-68 & QW-69: Standardizes pure Vietnamese copy and normalizes Title-Case Vietnamese headings', () => {
    const shareBtn = readWebFile('components/ShareButton.vue')
    const routeMap = readWebFile('components/planner/PlannerRouteMap.vue')
    const displaySettings = readWebFile('components/shell/DisplaySettingsPopover.vue')
    const riversideStays = readWebFile('components/home/HomeRiversideStays.vue')
    const communityFeed = readWebFile('components/home/HomeCommunityFeed.vue')
    const offlinePanel = readWebFile('components/OfflineTerroirPanel.vue')

    expect(shareBtn).toContain('Chia sẻ liên kết')
    expect(shareBtn).not.toContain('Chia sẻ link')
    expect(routeMap).toContain('Lịch trình vẫn giữ nguyên thứ tự')
    expect(displaySettings).toContain('Chữ lớn dễ đọc')
    expect(displaySettings).toContain('Phóng to cỡ chữ 125%')
    expect(displaySettings).toContain('Tiết kiệm dữ liệu')
    expect(displaySettings).not.toContain('Eco-Mode')
    expect(riversideStays).toContain('Homestay ven sông')
    expect(riversideStays).toContain('Trải nghiệm bản địa & di sản dân gian')
    expect(riversideStays).toContain('home-stay-card__perks sr-only')
    expect(communityFeed).toContain('Nhật ký lữ khách phương Nam')
    expect(offlinePanel).toContain('Lịch con nước thủy triều (tính toán ngoại tuyến)')
  })

  it('QW-71 & QW-72: Declutters seasonal duplicates, standardizes Vietnamese amenity/bookmark labels, and removes transition: all in map/routes/pocket-pass', () => {
    const entityCard = readWebFile('components/EntityCard.vue')
    const theoMua = readWebFile('pages/theo-mua.vue')
    const duLich = readWebFile('pages/du-lich.vue')
    const leHoi = readWebFile('pages/le-hoi.vue')
    const banDo = readWebFile('pages/ban-do.vue')
    const pocketPass = readWebFile('components/PocketPassModal.vue')
    const tuyenDuong = readWebFile('pages/tuyen-duong.vue')
    const plannerSteps = readWebFile('components/planner/PlannerSteps.vue')
    const daLuu = readWebFile('pages/da-luu.vue')

    expect(entityCard).toContain("kid_friendly: { icon: 'users', label: 'Phù hợp trẻ nhỏ' }")
    expect(entityCard).toContain("restroom: { icon: 'building', label: 'Nhà vệ sinh' }")
    expect(entityCard).not.toContain('Trẻ em OK')
    expect(theoMua).not.toContain('<small class="season-when">')
    expect(duLich).toContain("heading: 'Cù lao An Bình & nhịp sông Tiền'")
    expect(leHoi).toContain("heading: 'Lễ hội Kỳ Yên & đình miếu người Kinh'")
    expect(banDo).not.toMatch(/transition:\s*all\b/)
    expect(pocketPass).not.toMatch(/transition:\s*all\b/)
    expect(pocketPass).not.toContain('var(--radius-full)')
    expect(tuyenDuong).not.toMatch(/transition:\s*all\b/)
    expect(tuyenDuong).toContain('transform-box: fill-box;')
    expect(plannerSteps).toContain('@keydown.space.prevent')
    expect(plannerSteps).toContain('min-height: 44px;')
    expect(daLuu).toContain('Chưa thể tải bài viết đã lưu. Bạn có thể thử đồng bộ lại.')
    expect(daLuu).not.toContain('tải bookmark bài viết')
    expect(daLuu).not.toContain('Chưa bookmark bài viết nào.')
  })

  it('QW-73 & QW-74: Enforces WCAG 2.2 AAA focus-visible/live-regions and eliminates global CSS duplicates and transition: all', () => {
    const wardDigest = readWebFile('components/ward/WardTerroirDigest.vue')
    const detailCss = readWebFile('assets/css/detail.css')
    const danhBa = readWebFile('pages/danh-ba.vue')
    const detailVue = readWebFile('pages/dia-diem/[id].vue')
    const congDong = readWebFile('pages/cong-dong.vue')
    const offlinePanel = readWebFile('components/OfflineTerroirPanel.vue')
    const searchDrawer = readWebFile('components/SearchDrawer.vue')
    const defaultLayout = readWebFile('layouts/default.vue')

    expect(wardDigest).toContain('.ward-terroir-digest__call-btn:focus-visible')
    expect(detailCss).toContain('.fact-link:focus-visible')
    expect(detailCss).toContain('.claim-cta:focus-visible')
    expect(danhBa).not.toMatch(/transition:\s*all\b/)
    expect(danhBa).toContain('.gazetteer-tab:focus-visible')
    expect(detailVue).toContain('Đánh giá trung bình ${entity.attributes.rating} trên 5 sao')
    expect(congDong).toContain('role="alert" aria-live="assertive"')
    expect(offlinePanel).not.toMatch(/transition:\s*all\b/)
    expect(offlinePanel).toContain("name: 'Cứu hộ giao thông thủy Vĩnh Long'")
    expect(searchDrawer).not.toMatch(/transition:\s*all\b/)
    expect(defaultLayout).toContain("{ to: '/admin', label: 'Quản trị' }")
  })
})
