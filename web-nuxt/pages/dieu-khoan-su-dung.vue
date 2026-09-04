<template>
  <section class="legal-page about-page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Điều khoản sử dụng' }]" />
    <!-- Hero — brand-masthead dùng chung (declutter-3 T1: thống nhất với gioi-thieu,
         bỏ catalog-hero cat-org lai tạp trên trang pháp lý) -->
    <section class="brand-masthead about-masthead">
      <div class="bm-inner">
        <p class="bm-eyebrow"><span class="bm-tick" aria-hidden="true"></span>Hồ sơ pháp lý · Cập nhật {{ doc.updated_date }}</p>
        <h1>{{ doc.title }}</h1>
        <p class="bm-sub">{{ doc.seo_description }}</p>
      </div>
    </section>

    <aside class="legal-metadata" aria-label="Thông tin kiểm soát điều khoản">
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
    <nav class="legal-toc" aria-label="Mục lục điều khoản sử dụng">
      <a v-for="(s, i) in doc.sections" :key="i" :href="`#legal-section-${i + 1}`" class="legal-toc-link">
        {{ String(i + 1).padStart(2, '0') }}. {{ stripNum(s.heading) }}
      </a>
    </nav>

    <section class="legal-disclosure" aria-labelledby="cookie-inventory-title">
      <h2 id="cookie-inventory-title">Cookie và lịch sử chính sách</h2>
      <p>Danh mục dưới đây mô tả cookie hiện có và cách kiểm soát. Các mốc xử lý, nơi lưu trữ, bên xử lý và phạm vi lập chỉ mục công khai chỉ có hiệu lực sau khi được phê duyệt.</p>
      <div class="legal-table-wrap">
        <table class="legal-cookie-table">
          <thead><tr><th>Tên / vai trò runtime</th><th>Chủ quản & mục đích</th><th>Hạn / quyết định</th><th>Thuộc tính</th><th>Đồng ý / xoá</th><th>Lưu giữ / ngừng dùng</th></tr></thead>
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
import { LEGAL_TERMS, mergeLegalDoc } from '~/utils/legalContent'

useReveal()
const { get } = useSiteSettings()
const doc = computed(() => mergeLegalDoc(get('legal.terms', {}), LEGAL_TERMS))
const introHtml = computed(() => mdLite(doc.value.intro))

// Headings may carry their own "N. " prefix; the .about-section-num badge
// already shows the order, so strip the inline number to avoid duplicates.
const stripNum = (h: string) => (h || '').replace(/^\s*\d+\.\s*/, '')

useSeoMeta({
  title: () => doc.value.seo_title,
  description: () => doc.value.seo_description,
  ogTitle: () => doc.value.seo_title,
  ogDescription: () => doc.value.seo_description,
})
useHead({
  link: [{ rel: 'canonical', href: canonicalUrl('/dieu-khoan-su-dung') }],
  script: [{
    type: 'application/ld+json',
    innerHTML: JSON.stringify({
      '@context': 'https://schema.org',
      '@type': 'BreadcrumbList',
      itemListElement: [
        { '@type': 'ListItem', position: 1, name: 'Trang chủ', item: 'https://vinhlong360.vn/' },
        { '@type': 'ListItem', position: 2, name: 'Điều khoản sử dụng' },
      ],
    }),
  }],
})
</script>

<style src="~/assets/css/legal.css"></style>
