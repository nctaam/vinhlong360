import { describe, it, expect } from 'vitest'

describe('Component smoke tests', () => {
  it('imports Breadcrumb component', async () => {
    const mod = await import('../components/Breadcrumb.vue')
    expect(mod.default).toBeTruthy()
  })

  it('imports ScrollToTop component', async () => {
    const mod = await import('../components/ScrollToTop.vue')
    expect(mod.default).toBeTruthy()
  })

  it('imports ToastContainer component', async () => {
    const mod = await import('../components/ToastContainer.vue')
    expect(mod.default).toBeTruthy()
  })

  it('imports ShareButton component', async () => {
    const mod = await import('../components/ShareButton.vue')
    expect(mod.default).toBeTruthy()
  })

  it('imports SaveButton component', async () => {
    const mod = await import('../components/SaveButton.vue')
    expect(mod.default).toBeTruthy()
  })

  it('imports ChatWidget component', async () => {
    const mod = await import('../components/ChatWidget.vue')
    expect(mod.default).toBeTruthy()
  })

  it('imports AuthModal component', async () => {
    const mod = await import('../components/AuthModal.vue')
    expect(mod.default).toBeTruthy()
  })

  it('imports OnboardingSheet component', async () => {
    const mod = await import('../components/OnboardingSheet.vue')
    expect(mod.default).toBeTruthy()
  })
})

describe('Page module imports', () => {
  it('imports index page', async () => {
    const mod = await import('../pages/index.vue')
    expect(mod.default).toBeTruthy()
  })

  it('imports du-lich page', async () => {
    const mod = await import('../pages/du-lich.vue')
    expect(mod.default).toBeTruthy()
  })

  it('imports san-pham page', async () => {
    const mod = await import('../pages/san-pham.vue')
    expect(mod.default).toBeTruthy()
  })

  it('imports tim-kiem page', async () => {
    const mod = await import('../pages/tim-kiem.vue')
    expect(mod.default).toBeTruthy()
  })

  it('imports cong-dong page', async () => {
    const mod = await import('../pages/cong-dong.vue')
    expect(mod.default).toBeTruthy()
  })

  it('imports settings page', async () => {
    const mod = await import('../pages/cai-dat.vue')
    expect(mod.default).toBeTruthy()
  })

  it('imports account page', async () => {
    const mod = await import('../pages/tai-khoan.vue')
    expect(mod.default).toBeTruthy()
  })

  it('imports user profile page', async () => {
    const mod = await import('../pages/nguoi-dung/[id].vue')
    expect(mod.default).toBeTruthy()
  })

  it('imports map page', async () => {
    const mod = await import('../pages/ban-do.vue')
    expect(mod.default).toBeTruthy()
  })

  it('imports lien-he page', async () => {
    const mod = await import('../pages/lien-he.vue')
    expect(mod.default).toBeTruthy()
  })
})
