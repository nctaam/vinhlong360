import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const readWebFile = (relPath: string) =>
  readFileSync(resolve(process.cwd(), relPath), 'utf8')

describe('Editorial Artistry & Anti-List-Monotony Architecture', () => {
  it('upgrades cards.css .grid--asymmetric with periodic horizontal magazine split-spreads and exhibition numbering', () => {
    const cardsCss = readWebFile('assets/css/cards.css')
    expect(cardsCss).toContain('.grid--asymmetric > .card:nth-child(7n + 1)')
    expect(cardsCss).toContain('grid-template-columns: minmax(0, 1.18fr) minmax(0, 1fr)')
    expect(cardsCss).toContain('counter-reset: editorial-plate')
    expect(cardsCss).toContain('counter(editorial-plate, decimal-leading-zero) " · "')
  })

  it('prevents /du-lich discovery grid view from collapsing into a 1-column text list while preserving list-view', () => {
    const catalogCss = readWebFile('assets/css/catalog.css')
    expect(catalogCss).toContain(
      '[data-page-recipe="discovery"] .catalog-result-surface.list-view > .catalog-result-item[data-entity-contract="entity-row"]'
    )
    expect(catalogCss).toContain('.catalog-result-item:nth-child(7n + 1)')
    expect(catalogCss).toContain('counter-reset: discovery-plate')
  })

  it('transforms CatalogAeoPlaque from a boxed SaaS card into an open architectural monograph spread', () => {
    const aeoPlaque = readWebFile('components/CatalogAeoPlaque.vue')
    expect(aeoPlaque).toContain('border-inline: 0;')
    expect(aeoPlaque).toContain('counter-reset: aeo-note;')
    expect(aeoPlaque).toContain('content: counter(aeo-note, decimal-leading-zero);')
  })

  it('elevates HomeCulinaryTrail with staggered gallery triptych rhythm and sculptural Fraunces italic rank numerals', () => {
    const culinary = readWebFile('components/home/HomeCulinaryTrail.vue')
    expect(culinary).toContain('.home-culinary-card:nth-child(2)')
    expect(culinary).toContain('transform: translateY(var(--space-6));')
    expect(culinary).toContain('font-family: var(--font-editorial-display);')
    expect(culinary).toContain('font-style: italic;')
  })

  it('transforms HomeRiversideStays and HomeIntentAnchors sub-items into open architectural hairline ledgers without nested boxes', () => {
    const stays = readWebFile('components/home/HomeRiversideStays.vue')
    const anchors = readWebFile('components/home/HomeIntentAnchors.vue')
    expect(stays).toContain('grid-template-columns: minmax(0, 1.38fr) minmax(0, 0.81fr) minmax(0, 0.81fr);')
    expect(stays).toContain('counter-reset: folk-exp;')
    expect(stays).toContain('content: counter(folk-exp, decimal-leading-zero);')
    expect(anchors).toContain('counter-reset: persona-spot;')
    expect(anchors).toContain('content: counter(persona-spot, decimal-leading-zero);')
  })

  it('extends .grid--asymmetric magazine split-spread rhythm to OCOP, seasonal, regional, and ward catalogs', () => {
    const ocop = readWebFile('pages/ocop.vue')
    const theoMua = readWebFile('pages/theo-mua.vue')
    const khuVuc = readWebFile('pages/khu-vuc/[area].vue')
    const xaPhuong = readWebFile('pages/xa-phuong/[id].vue')
    expect(ocop).toContain('grid grid--asymmetric')
    expect(theoMua).toContain('grid grid--asymmetric')
    expect(khuVuc).toContain('grid grid--asymmetric')
    expect(xaPhuong).toContain('wp-grid grid grid--asymmetric')
  })

  it('transforms am-thuc.vue .cuisine-triad, events.css ledgers, and danh-ba.vue gazetteer into numbered editorial layouts', () => {
    const amThuc = readWebFile('pages/am-thuc.vue')
    const eventsCss = readWebFile('assets/css/events.css')
    const danhBa = readWebFile('pages/danh-ba.vue')
    expect(amThuc).toContain('counter-reset: cuisine-triad;')
    expect(amThuc).toContain('content: counter(cuisine-triad, decimal-leading-zero);')
    expect(eventsCss).toContain('counter-reset: ceremonial-ledger;')
    expect(eventsCss).toContain('counter-reset: event-archive;')
    expect(eventsCss).toContain('.event-list > .event-row:first-child')
    expect(danhBa).toContain('counter-reset: gazetteer-entry;')
    expect(danhBa).toContain('counter(gazetteer-entry, decimal-leading-zero)')
  })

  it('elevates tuyen-duong.vue, bang-xep-hang.vue, gioi-thieu.vue, and lich-trinh/index.vue in Wave 3 without nested boxes', () => {
    const tuyenDuong = readWebFile('pages/tuyen-duong.vue')
    const bangXepHang = readWebFile('pages/bang-xep-hang.vue')
    const gioiThieu = readWebFile('pages/gioi-thieu.vue')
    const lichTrinh = readWebFile('pages/lich-trinh/index.vue')
    expect(tuyenDuong).toContain('counter-reset: route-dossier;')
    expect(tuyenDuong).toContain('content: "TUYẾN " counter(route-dossier, decimal-leading-zero);')
    expect(bangXepHang).toContain('counter-reset: honor-tier;')
    expect(bangXepHang).toContain('content: "BẬC " counter(honor-tier, decimal-leading-zero);')
    expect(gioiThieu).toContain('border-block-start: 1.5px solid var(--color-brand);')
    expect(lichTrinh).toContain('grid itin grid--asymmetric')
  })

  it('elevates luu-tru.vue, lich-trinh/[id].vue, huong-dan.vue, lien-he.vue, da-luu.vue, and tim-kiem.vue in Wave 4 into open architectural ledgers', () => {
    const luuTru = readWebFile('pages/luu-tru.vue')
    const lichTrinhDetail = readWebFile('pages/lich-trinh/[id].vue')
    const huongDan = readWebFile('pages/huong-dan.vue')
    const lienHe = readWebFile('pages/lien-he.vue')
    const daLuu = readWebFile('pages/da-luu.vue')
    const timKiem = readWebFile('pages/tim-kiem.vue')

    expect(luuTru).toContain('counter-reset: stay-triad;')
    expect(luuTru).toContain('content: counter(stay-triad, decimal-leading-zero);')
    expect(lichTrinhDetail).toContain('border-block-end: 1px solid var(--line);')
    expect(huongDan).toContain('/* Quickstart — open 5-chapter editorial ledger */')
    expect(lienHe).toContain('<style src="~/assets/css/legal.css"></style>')
    expect(lienHe).toContain('content: "KÊNH " counter(contact-channel, decimal-leading-zero);')
    expect(daLuu).toContain('counter-reset: saved-ledger;')
    expect(timKiem).not.toContain('transition: all .2s var(--ease-out);')
  })

  it('unboxes CatalogFaqAccordion, CatalogCrossLinks, JourneyActionRail, detail.css, and bai-viet/[id].vue in Wave 5 into open architectural ledgers', () => {
    const faq = readWebFile('components/CatalogFaqAccordion.vue')
    const catalogCss = readWebFile('assets/css/catalog.css')
    const journeyRail = readWebFile('components/JourneyActionRail.vue')
    const detailCss = readWebFile('assets/css/detail.css')
    const baiViet = readWebFile('pages/bai-viet/[id].vue')

    expect(faq).toContain('counter-reset: faq-entry;')
    expect(faq).toContain('content: counter(faq-entry, decimal-leading-zero);')
    expect(catalogCss).toContain('.cross-card:first-child { border-inline-start: 0; padding-inline-start: 0; }')
    expect(journeyRail).toContain('border-inline-start: 1px solid var(--line);')
    expect(detailCss).toContain('counter-reset: archival-fact;')
    expect(detailCss).toContain('content: counter(archival-fact, decimal-leading-zero);')
    expect(baiViet).toContain('/* ── Related posts — open editorial dispatch pair ── */')
  })

  it('elevates huong-dan-thanh-vien.vue, CommunitySidebar.vue, lich-trinh-chia-se/[id].vue, nguoi-dung/[id].vue, and thong-bao.vue in Wave 6 into open architectural ledgers', () => {
    const memberGuide = readWebFile('pages/huong-dan-thanh-vien.vue')
    const communitySidebar = readWebFile('components/community/CommunitySidebar.vue')
    const sharedItinerary = readWebFile('pages/lich-trinh-chia-se/[id].vue')
    const userProfile = readWebFile('pages/nguoi-dung/[id].vue')
    const notifications = readWebFile('pages/thong-bao.vue')

    expect(memberGuide).toContain('counter-reset: badge-ledger;')
    expect(memberGuide).toContain('content: counter(badge-ledger, decimal-leading-zero);')
    expect(communitySidebar).toContain('border-inline-start: 1px solid var(--line);')
    expect(sharedItinerary).toContain('border-inline-end: 1px solid var(--line);')
    expect(userProfile).toContain('/* Wave 6: Open Architectural 5-Metric Strip — unboxed from 5 rounded pill boxes */')
    expect(userProfile).toContain('/* Hoạt động (timeline) tab — Wave 6: Open Field Activity Ledger */')
    expect(notifications).toContain('/* Wave 6: Open Architectural Correspondence Ledger — unboxed from stacked cards */')
  })

  it('elevates dia-diem/index.vue, lich-van-nien.vue, tai-khoan.vue, cai-dat.vue, CaseStatusTimeline.vue, and DecisionPublicationState.vue in Wave 7 into open architectural ledgers', () => {
    const diaDiemIndex = readWebFile('pages/dia-diem/index.vue')
    const lichVanNien = readWebFile('pages/lich-van-nien.vue')
    const taiKhoan = readWebFile('pages/tai-khoan.vue')
    const caiDat = readWebFile('pages/cai-dat.vue')
    const caseTimeline = readWebFile('components/cases/CaseStatusTimeline.vue')
    const decisionState = readWebFile('components/cases/DecisionPublicationState.vue')

    expect(diaDiemIndex).toContain('counter-reset: type-filmstrip;')
    expect(diaDiemIndex).not.toContain('var(--radius-full)')
    expect(lichVanNien).toContain('counter-reset: lunar-hour;')
    expect(lichVanNien).toContain('counter-reset: solar-term;')
    expect(taiKhoan).toContain('/* Wave 7: Open Architectural Account & Activity Ledgers — unboxed from stacked pill rows */')
    expect(caiDat).toContain('/* Wave 7: Open Architectural Decree-13 Charter Strip — unboxed from 3 cards */')
    expect(caseTimeline).toContain('content: "BƯỚC " counter(case-step, decimal-leading-zero);')
    expect(decisionState).not.toContain('border-radius: 10px;')
  })

  it('completes Wave 8 cross-surface polish: zero card-in-card on .page-article, WardTerroirDigest, KnowBeforeYouGo, tao-lich-trinh, CaseReceiptCard, huong-dan, and Nocturne dark ledger parity', () => {
    const homeIntent = readWebFile('components/home/HomeIntentAnchors.vue')
    const catalogCss = readWebFile('assets/css/catalog.css')
    const wardDigest = readWebFile('components/ward/WardTerroirDigest.vue')
    const kbyg = readWebFile('components/KnowBeforeYouGo.vue')
    const taoLichTrinh = readWebFile('pages/tao-lich-trinh.vue')
    const caseReceipt = readWebFile('components/cases/CaseReceiptCard.vue')
    const taiKhoan = readWebFile('pages/tai-khoan.vue')
    const searchDrawer = readWebFile('components/SearchDrawer.vue')
    const terroirComposable = readWebFile('composables/useCognitiveTerroir.ts')

    expect(homeIntent).not.toContain('home-persona-capsule cinema-glass-plate')
    expect(catalogCss).toContain('/* ── Page Article (Open Magazine Essay Column — Wave 8 Zero Card-in-Card) ── */')
    expect(wardDigest).toContain('border-inline-start: 1px solid var(--color-border);')
    expect(kbyg).toContain('/* Practical facts — Open Specification Ledger */')
    expect(taoLichTrinh).toContain('border-block-end: 1px solid var(--line);')
    expect(caseReceipt).toContain('border-block-start: 2px solid var(--color-brand);')
    expect(taiKhoan).toContain('.dark .cp-action-item, .dark .cp-data-row, .dark .cp-activity-item { background: transparent; }')
    expect(searchDrawer).toContain('color: var(--color-on-action);')
    expect(terroirComposable).toContain('globalTerroirListenersCount')
  })

  it('completes Wave 9 open architectural ledgers across xa-phuong/[id].vue, tuyen-duong.vue, lich-trinh/[id].vue, bai-viet/[id].vue, lien-he.vue, and civic intake forms', () => {
    const xaPhuongDetail = readWebFile('pages/xa-phuong/[id].vue')
    const tuyenDuong = readWebFile('pages/tuyen-duong.vue')
    const lichTrinhDetail = readWebFile('pages/lich-trinh/[id].vue')
    const baiVietDetail = readWebFile('pages/bai-viet/[id].vue')
    const lienHe = readWebFile('pages/lien-he.vue')
    const intakeForm = readWebFile('components/cases/CorrectionIntakeForm.vue')

    expect(xaPhuongDetail).toContain('/* Sidebar specification ledger — Wave 9 Open Architectural Ledger */')
    expect(xaPhuongDetail).not.toContain('.dark .wp-card {')
    expect(tuyenDuong).toContain('/* Wave 9: Open Left-Rule Field Note — unboxed from nested card-in-card */')
    expect(tuyenDuong).not.toContain('.dark .route-tips')
    expect(lichTrinhDetail).toContain('/* Mode selector panel: Wave 9 Open Editorial Control Strip */')
    expect(lichTrinhDetail).not.toContain('.dark .transport-mode-spaced')
    expect(baiVietDetail).not.toContain('var(--radius-full)')
    expect(baiVietDetail).not.toContain('border-radius: 999px;')
    expect(lienHe).toContain('/* Wave 9: Open Architectural Contact Ledger — unboxed from 4-sided cards */')
    expect(lienHe).not.toContain('.dark .contact-card {')
    expect(intakeForm).toContain('border-inline-start: 2px solid var(--color-brand);')
  })

  it('completes Wave 10 global dark-overrides.css deduplication and unboxes EntityTrustPanel, ReviewCard, WhyThisDrawer, PocketPassModal, and components.css', () => {
    const darkOverrides = readWebFile('assets/css/dark-overrides.css')
    const entityTrust = readWebFile('components/EntityTrustPanel.vue')
    const reviewCard = readWebFile('components/ReviewCard.vue')
    const whyThis = readWebFile('components/WhyThisDrawer.vue')
    const pocketPass = readWebFile('components/PocketPassModal.vue')
    const componentsCss = readWebFile('assets/css/components.css')

    expect(darkOverrides).toContain('/* ── Ward hub (xa-phuong/[id]) — Wave 10 Open Architectural Nocturne Parity ── */')
    expect(darkOverrides).not.toContain('.dark .wp-card:hover { box-shadow: var(--shadow-lg); }')
    expect(darkOverrides).not.toContain('.dark .contact-card:hover { border-color: rgba(var(--white-rgb), .15); box-shadow: var(--shadow-lg); }')
    expect(entityTrust).toContain('/* Wave 10: Open Architectural Provenance Ledger — unboxed inside detail & ward sidebars */')
    expect(reviewCard).toContain('/* Wave 10: Open Left-Rule Editorial Testimony — unboxed from 4-sided amber box */')
    expect(whyThis).toContain('border-block-end: 1px solid var(--line);')
    expect(pocketPass).toContain('/* Wave 10: Open Architectural Emergency Hotline Ledger — unboxed from 5 nested cards */')
    expect(componentsCss).toContain('/* Wave 10: Open Architectural Page State Ledger */')
    expect(componentsCss).not.toContain('var(--radius-full)')
  })
})
