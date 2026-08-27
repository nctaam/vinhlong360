<template>
  <!-- KHÔNG mang data-media-led-feature: thuộc tính đó là NGÂN SÁCH THỊ GIÁC
       "mỗi trang chỉ một đầu tàu ảnh", không phải nhãn mô tả. HomeFeatureDossier
       giữ vai đó ở hero; mục này là điểm dừng thứ hai với ngôn ngữ riêng.
       data-home-section="product-lead" nằm NGOÀI allowlist 5 tên mà hai test
       thứ tự mục lọc theo, nên chèn vào khe giữa không phải sửa test nào. -->
  <section
    class="home-product-lead"
    data-home-section="product-lead"
    data-home-product-lead
    aria-labelledby="home-product-lead-title"
  >
    <header class="home-product-lead__header">
      <p class="home-product-lead__dept">Đặc sản Vĩnh Long — tin chính</p>
      <h2 id="home-product-lead-title" class="home-product-lead__scale">
        {{ scaleLine }}
      </h2>
      <p v-if="scaleNote" class="home-product-lead__note">{{ scaleNote }}</p>
    </header>

    <div class="home-product-lead__body">
      <figure class="home-product-lead__matte">
        <NuxtLink
          v-if="descriptor.url"
          :to="detailTo"
          class="home-product-lead__media"
          :aria-label="`Xem ${title}`"
        >
          <NuxtImg
            v-if="isRemote(descriptor.url)"
            :src="descriptor.url"
            :alt="descriptor.alt"
            :aria-describedby="disclosureId"
            width="960"
            height="540"
            sizes="375px sm:540px md:640px"
            loading="lazy"
            decoding="async"
          />
          <img
            v-else
            :src="descriptor.url"
            :alt="descriptor.alt"
            :aria-describedby="disclosureId"
            width="960"
            height="540"
            loading="lazy"
            decoding="async"
          >
        </NuxtLink>
        <div v-else class="home-product-lead__media home-product-lead__media--empty">
          <IconLine name="pin" aria-hidden="true" />
        </div>
        <figcaption class="home-product-lead__caption">
          <ImageDisclosure :id="disclosureId" :descriptor="descriptor" presentation="short" />
        </figcaption>
      </figure>

      <div class="home-product-lead__text">
        <p class="home-product-lead__eyebrow">{{ eyebrow }}</p>
        <h3 class="home-product-lead__name">{{ title }}</h3>
        <span class="home-product-lead__rule" aria-hidden="true"></span>
        <p v-if="summary" class="home-product-lead__summary">{{ summary }}</p>
        <p v-if="region" class="home-product-lead__region">{{ region }}</p>
        <NuxtLink :to="detailTo" class="home-product-lead__cta" data-home-product-lead-cta>
          Đọc câu chuyện <span class="home-product-lead__arrow" aria-hidden="true">→</span>
        </NuxtLink>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { ImageDescriptor } from '~/types/image'

const isRemote = isRemoteUrl

// `descriptor` được TRUYỀN VÀO; component không bao giờ tự đọc trường ảnh thô
// của entity. Đây là điều kiện để R20.10 không đòi hàng registry: cổng chỉ đỏ
// khi mã tự đọc trường đó, còn uỷ quyền cho describeEntityImages ở trang gọi
// thì sạch (đã kiểm bằng thực nghiệm: đọc thô = 2 finding, uỷ quyền = 0).
// Checker là bộ SO CHUỖI — đừng viết tên trường ra đây, kể cả trong bình luận.
withDefaults(defineProps<{
  scaleLine: string
  scaleNote?: string | null
  eyebrow: string
  title: string
  summary?: string | null
  region?: string | null
  descriptor: ImageDescriptor
  disclosureId: string
  detailTo: string
}>(), {
  scaleNote: undefined,
  summary: undefined,
  region: undefined,
})
</script>
