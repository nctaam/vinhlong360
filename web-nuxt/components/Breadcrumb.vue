<template>
  <nav class="breadcrumb" aria-label="Breadcrumb">
    <ol>
      <li v-for="(item, i) in items" :key="i">
        <NuxtLink v-if="item.to" :to="item.to">{{ item.label }}</NuxtLink>
        <span v-else aria-current="page" :title="item.label">{{ item.label }}</span>
      </li>
    </ol>
  </nav>
</template>

<script setup lang="ts">
// P1-8: opt-in BreadcrumbList JSON-LD tập trung (bật :json-ld trên trang chưa tự-chế schema,
// vd su-kien/luu-tru) — tránh trùng với trang đã hand-roll.
const props = defineProps<{
  items: Array<{ label: string; to?: string }>
  jsonLd?: boolean
}>()

if (props.jsonLd) {
  useHead(() => ({
    script: [{
      type: 'application/ld+json',
      innerHTML: JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'BreadcrumbList',
        itemListElement: props.items.map((it, i) => ({
          '@type': 'ListItem',
          position: i + 1,
          name: it.label,
          ...(it.to ? { item: canonicalUrl(it.to) } : {}),
        })),
      }),
    }],
  }))
}
</script>

<style scoped>
.breadcrumb { animation: bcIn .4s var(--ease-out-expo) both; }
@keyframes bcIn { from { opacity: 0; transform: translateX(-6px); } }
.breadcrumb ol { display: flex; flex-wrap: wrap; gap: 0; list-style: none; margin: 0 0 var(--space-3); padding: 0; font-size: var(--text-sm); }
.breadcrumb li { display: inline-flex; align-items: center; }
.breadcrumb li + li::before { content: "›"; margin: 0 var(--space-2); color: var(--muted); opacity: .6; font-size: .8em; }
.breadcrumb a { color: var(--primary-fg); text-decoration: none; transition: color .3s var(--ease-out), background .3s var(--ease-out); padding: var(--space-2) 6px; margin: calc(-1 * var(--space-2)) -6px; border-radius: var(--radius-sm); min-height: 44px; display: inline-flex; align-items: center; }
.breadcrumb a:hover { color: var(--primary-fg-strong, var(--primary-fg)); background: rgba(var(--primary-rgb), .06); }
.breadcrumb a:active { transform: scale(.95); transition-duration: .08s; }
.breadcrumb a:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
.breadcrumb span { color: var(--muted); max-width: 200px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
@media (prefers-reduced-motion: reduce) { .breadcrumb { animation: none; } }
@media (forced-colors: active) {
  .breadcrumb a { color: LinkText; }
  .breadcrumb li + li::before { color: GrayText; }
}
</style>
