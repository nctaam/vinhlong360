import { describe, expect, it } from 'vitest'
import { mountSuspended } from '@nuxt/test-utils/runtime'
import FramedDossier from '../components/FramedDossier.vue'
import DossierLineItem from '../components/DossierLineItem.vue'

describe('Framed Dossier foundation', () => {
  it('renders only supplied anatomy and exposes one primary action slot', async () => {
    const wrapper = await mountSuspended(FramedDossier, {
      props: { eyebrow: 'MANG THÍT', title: 'Một buổi bên lò gốm' },
      slots: {
        summary: '<p>Thông tin có nguồn.</p>',
        action: '<button>Chỉ đường</button>',
      },
    })
    expect(wrapper.find('[data-dossier-eyebrow]').text()).toBe('MANG THÍT')
    expect(wrapper.find('[data-dossier-title]').text()).toContain('Một buổi bên lò gốm')
    expect(wrapper.findAll('button')).toHaveLength(1)
    expect(wrapper.find('[data-dossier-media]').exists()).toBe(false)
  })

  it('keeps line items readable as a list and preserves keyboard focus', async () => {
    const wrapper = await mountSuspended(DossierLineItem, {
      props: { label: 'Cập nhật', value: '31/07/2026', href: '/dia-diem/1' },
      global: { stubs: { NuxtLink: { template: '<a :href="to"><slot /></a>', props: ['to'] } } },
    })
    const link = wrapper.get('a')
    expect(link.text()).toContain('31/07/2026')
    expect(link.attributes('href')).toBe('/dia-diem/1')
    expect(link.attributes('data-dossier-line')).toBe('true')
  })
})
