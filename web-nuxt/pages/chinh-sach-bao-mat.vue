<template>
  <section class="legal-page about-page" data-color-system="tri-region-v1">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Chính sách bảo mật' }]" :json-ld="true" />
    <!-- Hero — brand-masthead dùng chung (declutter-3 T1: thống nhất với gioi-thieu,
         bỏ catalog-hero cat-org lai tạp trên trang pháp lý) -->
    <section class="brand-masthead about-masthead">
      <div class="bm-inner">
        <p class="bm-eyebrow"><span class="bm-tick" aria-hidden="true"></span>Hồ sơ pháp lý · Cập nhật {{ doc.updated_date }}</p>
        <h1>{{ doc.title }}</h1>
        <p class="bm-sub">{{ doc.seo_description }}</p>
      </div>
    </section>

    <aside class="legal-metadata" aria-label="Thông tin kiểm soát chính sách">
      <dl>
        <div><dt>Phiên bản</dt><dd>{{ doc.policyVersion }}</dd></div>
        <div><dt>Cập nhật</dt><dd>{{ doc.updatedDate }}</dd></div>
        <div><dt>Đầu mối</dt><dd>{{ doc.owner }}</dd></div>
        <div><dt>Liên hệ</dt><dd>{{ doc.contact }}</dd></div>
      </dl>
    </aside>

    <div class="legal-body editorial-body drop-cap" v-html="introHtml"></div>

    <!-- Jump-link TOC — 6 sections cross-link each other elsewhere on the site;
         without anchors a cross-link only ever lands on the page top. -->
    <nav class="legal-toc" aria-label="Mục lục chính sách bảo mật">
      <a v-for="(s, i) in doc.sections" :key="i" :href="`#legal-section-${i + 1}`" class="legal-toc-link">
        {{ String(i + 1).padStart(2, '0') }}. {{ stripNum(s.heading) }}
      </a>
    </nav>

    <section class="legal-disclosure" aria-labelledby="cookie-inventory-title">
      <h2 id="cookie-inventory-title">Cookie và kiểm soát</h2>
      <p>Cookie cần thiết giúp đăng nhập và bảo vệ biểu mẫu. Cookie tuỳ chọn chỉ lưu khi bạn chọn và có thể xoá trong cài đặt.</p>
      <div class="legal-table-wrap" role="region" tabindex="0" aria-label="Bảng danh mục cookie và kiểm soát">
        <table class="legal-cookie-table" aria-label="Danh mục cookie và kiểm soát">
          <thead><tr><th scope="col">Tên / vai trò runtime</th><th scope="col">Chủ quản & mục đích</th><th scope="col">Hạn / quyết định</th><th scope="col">Thuộc tính</th><th scope="col">Đồng ý / xoá</th><th scope="col">Lưu giữ / ngừng dùng</th></tr></thead>
          <tbody>
            <tr v-for="cookie in doc.cookieInventory" :key="cookie.name">
              <th scope="row">{{ cookie.name }}<br><small>{{ cookie.runtimeRole }}</small></th>
              <td><strong>{{ cookie.owner }}</strong><br>{{ cookie.purpose }}</td>
              <td>{{ cookie.expiry }}<br><small>{{ cookie.expiryDecision || 'Theo cấu hình runtime hiện hành.' }}</small></td>
              <td>{{ cookie.sameSite }} · {{ cookie.secure === 'production-only' ? 'Secure production-only' : cookie.secure ? 'Secure' : 'Không Secure' }} · {{ cookie.httpOnly ? 'HttpOnly' : 'Không HttpOnly (trình duyệt có thể đọc)' }}</td>
              <td>{{ cookie.consentControl }}<br><small>Xoá: {{ cookie.deletion.mechanism || `delete_cookie path=${cookie.deletion.path}` }}</small></td>
              <td>{{ cookie.retention }}<br><small>{{ cookie.deprecation || 'Không có lịch ngừng dùng riêng.' }}</small></td>
            </tr>
          </tbody>
        </table>
      </div>
      <h3>Lịch sử thay đổi</h3>
      <ol class="legal-history">
        <li v-for="change in doc.changeHistory" :key="`${change.version}-${change.date}`"><strong>{{ change.version }} · {{ change.date }}</strong> — {{ change.summary }}</li>
      </ol>
    </section>

    <section
      v-for="(s, i) in doc.sections"
      :key="i"
      :id="`legal-section-${i + 1}`"
      class="legal-section reveal sediment-head"
    >
      <span class="about-section-num" aria-hidden="true">{{ String(i + 1).padStart(2, '0') }}</span>
      <div class="about-section-content">
        <h2>{{ stripNum(s.heading) }}</h2>
        <div class="legal-body editorial-body" v-html="mdLite(s.body)"></div>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { mdLite } from '~/utils/mdLite'
import { LEGAL_PRIVACY, mergeLegalDoc } from '~/utils/legalContent'

useReveal()
const { get } = useSiteSettings()
const doc = computed(() => mergeLegalDoc(get('legal.privacy', {}), LEGAL_PRIVACY))
const introHtml = computed(() => mdLite(doc.value.intro))

// Headings may carry their own "N. " prefix; the .about-section-num badge
// already shows the order, so strip the inline number to avoid duplicates.
const stripNum = (h: string) => (h || '').replace(/^\s*\d+\.\s*/, '')

const privacySchema = computed(() => ({
  '@context': 'https://schema.org',
  '@type': 'WebPage',
  name: doc.value.title || 'Chính sách bảo mật — vinhlong360',
  description: doc.value.seo_description || 'Chính sách bảo mật và quyền riêng tư dữ liệu trên vinhlong360.',
  url: canonicalUrl('/chinh-sach-bao-mat'),
  inLanguage: 'vi',
}))

useSeoMeta({
  title: () => doc.value.seo_title,
  description: () => doc.value.seo_description,
  ogTitle: () => doc.value.seo_title,
  ogDescription: () => doc.value.seo_description,
  ogUrl: () => canonicalUrl('/chinh-sach-bao-mat'),
  twitterCard: 'summary_large_image',
})

useHead(() => ({
  link: [{ rel: 'canonical', href: canonicalUrl('/chinh-sach-bao-mat') }],
  script: [
    { type: 'application/ld+json', innerHTML: safeJsonLd(privacySchema.value) },
  ],
}))
</script>

<style src="~/assets/css/legal.css"></style>
