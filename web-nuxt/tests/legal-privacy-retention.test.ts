import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { describe, expect, it } from 'vitest'

import privacyPolicy from '#privacy-policy'
import ContactPage from '../pages/lien-he.vue'
import { LEGAL_PRIVACY } from '../utils/legalContent'

mockNuxtImport('useReveal', () => () => undefined)
mockNuxtImport('useRoute', () => () => ({ query: {} }))
mockNuxtImport('useSiteSettings', () => () => ({
  get: (_key: string, fallback: unknown) => fallback,
}))
mockNuxtImport('usePageContent', () => () => ({
  f: (key: string) => key,
}))

describe('privacy retention authority', () => {
  it('renders the committed account-erasure deadline', () => {
    expect(privacyPolicy.accountErasureDeadlineDays).toBe(30)
    const rights = LEGAL_PRIVACY.sections.find(section => section.heading.startsWith('4.'))
    expect(rights?.body).toContain('30 ngày kể từ khi yêu cầu xoá tài khoản')
    expect(rights?.body).not.toContain('20 ngày')
  })

  it('renders the same deadline on the contact page', async () => {
    const wrapper = await mountSuspended(ContactPage, {
      global: {
        stubs: {
          Breadcrumb: true,
          NuxtLink: false,
        },
      },
    })

    try {
      expect(wrapper.text()).toContain('xoá dữ liệu (30 ngày)')
      expect(wrapper.text()).not.toContain('xoá dữ liệu (20 ngày)')
    } finally {
      wrapper.unmount()
    }
  })
})
