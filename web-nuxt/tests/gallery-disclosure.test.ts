import { mountSuspended } from '@nuxt/test-utils/runtime'
import { DOMWrapper } from '@vue/test-utils'
import { nextTick } from 'vue'
import { afterEach, describe, expect, it } from 'vitest'
import ImageLightbox from '../components/ImageLightbox.vue'
import PhotoGallery from '../components/PhotoGallery.vue'
import { aiDisclosure } from '../utils/aiDisclosure'
import type { ImageDescriptor } from '../types/image'

const aiDescriptor: ImageDescriptor = {
  url: '/img/entity.webp',
  alt: 'Chùa Vàm Ray — ảnh minh họa 1',
  source_class: 'ai-generated',
  source_kind: 'entity-editorial',
  disclosure_key: 'entity-ai',
  short_label: aiDisclosure.entity_ai.short_label,
  full_disclosure: aiDisclosure.entity_ai.full_disclosure,
  credit: null,
  width: null,
  height: null,
}

const reviewDescriptor: ImageDescriptor = {
  url: '/img/review.jpg',
  alt: 'Chùa Vàm Ray — ảnh đánh giá',
  source_class: 'user-uploaded',
  source_kind: 'review-ugc',
  disclosure_key: 'ugc-photo',
  short_label: aiDisclosure.ugc_photo.short_label,
  full_disclosure: aiDisclosure.ugc_photo.full_disclosure,
  credit: 'Lan',
  width: null,
  height: null,
}

const placeholderDescriptor: ImageDescriptor = {
  url: null,
  alt: 'Chùa Vàm Ray — chưa có ảnh riêng',
  source_class: 'placeholder',
  source_kind: 'generated-placeholder',
  disclosure_key: 'entity-placeholder',
  short_label: aiDisclosure.placeholder.short_label,
  full_disclosure: aiDisclosure.placeholder.full_disclosure,
  credit: null,
  width: null,
  height: null,
}

const mountedWrappers: Array<{ unmount: () => void }> = []

afterEach(() => {
  for (const wrapper of mountedWrappers.splice(0)) wrapper.unmount()
})

function activeCaption() {
  const dialog = new DOMWrapper(document.body).get('[role="dialog"]')
  const media = dialog.get('[data-active-media]')
  const captionId = media.attributes('aria-describedby')
  expect(captionId).toBeTruthy()
  const caption = dialog.get(`[data-full-disclosure][id="${captionId}"]`)
  return { dialog, media, caption }
}

describe('ImageLightbox disclosure navigation', () => {
  it('keeps the active descriptor caption through click, keyboard, swipe, and reopen', async () => {
    const wrapper = await mountSuspended(ImageLightbox, {
      props: { modelValue: true, images: [aiDescriptor, reviewDescriptor], startIndex: 0 },
    })
    mountedWrappers.push(wrapper)
    await nextTick()

    let state = activeCaption()
    expect(state.caption.text()).toContain(aiDescriptor.full_disclosure)
    expect(state.dialog.text()).not.toContain(reviewDescriptor.full_disclosure)

    await state.dialog.get('[data-next]').trigger('click')
    state = activeCaption()
    expect(state.media.attributes('src')).toBe(reviewDescriptor.url)
    expect(state.caption.text()).toContain(reviewDescriptor.full_disclosure)
    expect(state.caption.text()).toContain(reviewDescriptor.credit)
    expect(state.dialog.text()).not.toContain(aiDescriptor.short_label)
    expect(state.dialog.get('[data-counter]').text()).toBe('2 / 2')

    await state.dialog.get('[data-prev]').trigger('click')
    state = activeCaption()
    expect(state.media.attributes('src')).toBe(aiDescriptor.url)

    await state.dialog.trigger('keydown', { key: 'ArrowRight' })
    state = activeCaption()
    expect(state.media.attributes('src')).toBe(reviewDescriptor.url)

    await state.dialog.trigger('keydown', { key: 'ArrowLeft' })
    state = activeCaption()
    expect(state.media.attributes('src')).toBe(aiDescriptor.url)
    expect(state.caption.text()).toContain(aiDescriptor.full_disclosure)

    await state.dialog.trigger('touchstart', { touches: [{ clientX: 320 }] })
    await state.dialog.trigger('touchmove', { touches: [{ clientX: 120 }] })
    await new Promise(resolve => setTimeout(resolve, 0))
    await state.dialog.trigger('touchend')
    await nextTick()
    state = activeCaption()
    expect(state.media.attributes('src')).toBe(reviewDescriptor.url)

    await wrapper.setProps({ modelValue: false })
    await wrapper.setProps({ modelValue: true, startIndex: 0 })
    state = activeCaption()
    expect(state.media.attributes('src')).toBe(aiDescriptor.url)
    expect(state.caption.text()).toContain(aiDescriptor.full_disclosure)

    await new Promise(resolve => setTimeout(resolve, 0))
    expect(state.dialog.attributes('tabindex')).toBe('-1')
    expect(state.dialog.element.contains(document.activeElement)).toBe(true)
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    await nextTick()
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([false])
  })

  it('renders a placeholder media surface without an empty image and skips null prefetches', async () => {
    const wrapper = await mountSuspended(ImageLightbox, {
      props: {
        modelValue: true,
        images: [aiDescriptor, placeholderDescriptor, reviewDescriptor],
        startIndex: 1,
      },
    })
    mountedWrappers.push(wrapper)

    let state = activeCaption()
    expect(state.media.attributes('data-placeholder-media')).toBe('true')
    expect(state.media.element.tagName).not.toBe('IMG')
    expect(state.caption.text()).toContain(placeholderDescriptor.full_disclosure)
    expect(document.head.querySelectorAll('link[rel="prefetch"]').length).toBe(0)

    await state.dialog.get('[data-next]').trigger('click')
    state = activeCaption()
    expect(state.media.attributes('src')).toBe(reviewDescriptor.url)
    const prefetched = [...document.head.querySelectorAll('link[rel="prefetch"]')]
      .map(link => link.getAttribute('href'))
    expect(prefetched).toEqual([aiDescriptor.url])
    expect(prefetched).not.toContain(null)
    expect(prefetched).not.toContain('')
  })
})

describe('PhotoGallery descriptor boundary', () => {
  it('renders full disclosure and credit beside their original descriptor media', async () => {
    const wrapper = await mountSuspended(PhotoGallery, {
      props: { images: [aiDescriptor, reviewDescriptor], alt: 'Chùa Vàm Ray' },
    })
    mountedWrappers.push(wrapper)

    const mainMedia = wrapper.get('.pg-main [data-gallery-media]')
    const mainDescriptionId = mainMedia.attributes('aria-describedby')
    expect(wrapper.get(`#${mainDescriptionId}`).text()).toContain(aiDescriptor.full_disclosure)
    expect(mainMedia.attributes('src')).toBe(aiDescriptor.url)

    const reviewMedia = wrapper.get('.pg-thumb [data-gallery-media]')
    const reviewDescriptionId = reviewMedia.attributes('aria-describedby')
    const reviewCaption = wrapper.get(`#${reviewDescriptionId}`)
    expect(reviewCaption.text()).toContain(reviewDescriptor.full_disclosure)
    expect(reviewCaption.text()).toContain(reviewDescriptor.credit)
    expect(reviewMedia.attributes('src')).toBe(reviewDescriptor.url)
    expect(reviewCaption.text()).not.toContain(aiDescriptor.short_label)
  })

  it('keeps standalone open-lightbox indices aligned with descriptor order', async () => {
    const wrapper = await mountSuspended(PhotoGallery, {
      props: { images: [aiDescriptor, reviewDescriptor], alt: 'Chùa Vàm Ray', standalone: true },
    })
    mountedWrappers.push(wrapper)

    await wrapper.get('.pg-thumb').trigger('click')
    const dialog = new DOMWrapper(document.body).get('[role="dialog"]')
    expect(dialog.get('[data-active-media]').attributes('src')).toBe(reviewDescriptor.url)
    expect(dialog.get('[data-full-disclosure]').text()).toContain(reviewDescriptor.full_disclosure)
    expect(dialog.get('[data-full-disclosure]').text()).toContain(reviewDescriptor.credit)
  })

  it('does not render an empty image for a standalone placeholder', async () => {
    const wrapper = await mountSuspended(PhotoGallery, {
      props: { images: [placeholderDescriptor], alt: 'Chùa Vàm Ray', standalone: true },
    })
    mountedWrappers.push(wrapper)

    expect(wrapper.find('img').exists()).toBe(false)
    expect(wrapper.find('.pg-empty').exists()).toBe(true)
    expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
    const placeholder = wrapper.get('.pg-empty')
    const descriptionId = placeholder.attributes('aria-describedby')
    expect(descriptionId).toBeTruthy()
    expect(wrapper.get(`[data-full-disclosure][id="${descriptionId}"]`).text())
      .toBe(placeholderDescriptor.full_disclosure)
  })
})
