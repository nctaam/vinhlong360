<template>
  <span class="line-icon" :class="`li-${name}`" v-html="svg" />
</template>

<script setup lang="ts">
// Inline line-icon set (stroke, currentColor, 1em) — replaces functional emoji
// with a coherent editorial icon language. Full <svg> string per name so the
// HTML parser keeps the SVG namespace (v-html of partial svg children would not).
const props = defineProps<{ name: string }>()

const W = (inner: string) =>
  `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${inner}</svg>`

const ICONS: Record<string, string> = {
  pin: W('<path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/>'),
  map: W('<path d="m9 3-6 3v15l6-3 6 3 6-3V3l-6 3Z"/><path d="M9 3v15"/><path d="M15 6v15"/>'),
  list: W('<path d="M11 6h9"/><path d="M11 12h9"/><path d="M11 18h9"/><path d="m3.5 6 1 1 2-2"/><path d="m3.5 12 1 1 2-2"/><path d="m3.5 18 1 1 2-2"/>'),
  home: W('<path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V21h14V9.5"/><path d="M9.5 21v-6h5v6"/>'),
  bowl: W('<path d="M4 11h16a8 8 0 0 1-16 0Z"/><path d="M9 4c-.7.8-.7 1.7 0 2.5"/><path d="M13 4c-.7.8-.7 1.7 0 2.5"/>'),
  lantern: W('<path d="M12 2v2.5"/><path d="M12 19.5V22"/><path d="M7.5 5.2h9"/><path d="M7.5 18.8h9"/><path d="M6.5 12c0-3 2.5-7 5.5-7s5.5 4 5.5 7-2.5 7-5.5 7-5.5-4-5.5-7Z"/>'),
  gift: W('<path d="M20 12v9H4v-9"/><path d="M2.5 8h19v4h-19Z"/><path d="M12 8v13"/><path d="M12 8S11 3 8.5 3a2.5 2.5 0 0 0 0 5Z"/><path d="M12 8s1-5 3.5-5a2.5 2.5 0 0 1 0 5Z"/>'),
  leaf: W('<path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.5 19 2c1 2 2 4.2 2 8 0 5.5-4.8 10-10 10Z"/><path d="M2 21c0-3 1.85-5.36 5.08-6"/>'),
  calendar: W('<rect x="3" y="4.5" width="18" height="17" rx="2"/><path d="M8 2.5v4"/><path d="M16 2.5v4"/><path d="M3 10h18"/>'),
  moon: W('<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z"/>'),
  flame: W('<path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.07-2.14-.22-4.05 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.15.43-2.29 1-3a2.5 2.5 0 0 0 2.5 2.5Z"/>'),
  heart: W('<path d="M20.8 5.6a5.5 5.5 0 0 0-7.7-.2L12 6.5l-1.1-1.1a5.5 5.5 0 1 0-7.7 7.8l1 1L12 21l7.8-6.7 1-1a5.5 5.5 0 0 0 0-7.5Z"/>'),
  message: W('<path d="M21 11.5a8.5 8.5 0 0 1-8.5 8.5 8.4 8.4 0 0 1-3.8-.9L3 21l1.9-5.7A8.4 8.4 0 0 1 4 11.5 8.5 8.5 0 0 1 12.5 3 8.5 8.5 0 0 1 21 11.5Z"/>'),
  trophy: W('<path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/><path d="M4 22h16"/><path d="M10 14.6V17a2 2 0 0 1-1 1.7L8 22"/><path d="M14 14.6V17a2 2 0 0 0 1 1.7L16 22"/><path d="M6 2h12v7a6 6 0 0 1-12 0Z"/>'),
}

const svg = computed(() => ICONS[props.name] || '')
</script>

<style scoped>
.line-icon {
  display: inline-flex;
  width: 1em;
  height: 1em;
  vertical-align: -0.135em;
  flex: 0 0 auto;
}
.line-icon :deep(svg) { width: 100%; height: 100%; display: block; }
</style>
