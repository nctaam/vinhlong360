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
  sun: W('<circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.9 4.9 1.4 1.4"/><path d="m17.7 17.7 1.4 1.4"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.3 17.7-1.4 1.4"/><path d="m19.1 4.9-1.4 1.4"/>'),
  star: W('<path d="m12 2.6 2.9 6 6.5.6-4.9 4.3 1.5 6.4L12 17.1 6 20.5l1.5-6.4L2.6 9.8l6.5-.6Z"/>'),
  bell: W('<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.9 1.9 0 0 0 3.4 0"/>'),
  x: W('<path d="M18 6 6 18"/><path d="m6 6 12 12"/>'),
  sparkles: W('<path d="M12 3l1.8 4.7L18.5 9l-4.7 1.8L12 15l-1.8-4.7L5.5 9l4.7-1.3Z"/><path d="M19 14.5l.8 2 2 .8-2 .8-.8 2-.8-2-2-.8 2-.8Z"/>'),
  user: W('<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>'),
  bookmark: W('<path d="M6 3h12a1 1 0 0 1 1 1v17l-7-4-7 4V4a1 1 0 0 1 1-1Z"/>'),
  sliders: W('<path d="M4 6h16"/><path d="M4 12h16"/><path d="M4 18h16"/><circle cx="8" cy="6" r="2"/><circle cx="16" cy="12" r="2"/><circle cx="9" cy="18" r="2"/>'),
  logout: W('<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="M16 17l5-5-5-5"/><path d="M21 12H9"/>'),
  clock: W('<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>'),
  tag: W('<path d="M3 11V4a1 1 0 0 1 1-1h7l9 9-8 8-9-9Z"/><circle cx="7.5" cy="7.5" r="1.3"/>'),
  phone: W('<path d="M5 3h3l2 5-2.5 1.5a12 12 0 0 0 5 5L15 12l5 2v3a1 1 0 0 1-1 1A16 16 0 0 1 4 4a1 1 0 0 1 1-1Z"/>'),
  globe: W('<circle cx="12" cy="12" r="9"/><path d="M3 12h18"/><path d="M12 3a14 14 0 0 1 0 18 14 14 0 0 1 0-18Z"/>'),
  compass: W('<circle cx="12" cy="12" r="9"/><path d="m15.5 8.5-2 5-5 2 2-5Z"/>'),
  camera: W('<path d="M4 8a2 2 0 0 1 2-2h1l1.4-2h7.2L17 6h1a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2Z"/><circle cx="12" cy="13" r="3.5"/>'),
  bulb: W('<path d="M9 18h6"/><path d="M10 21h4"/><path d="M12 3a6 6 0 0 0-4 10.5c.7.7 1 1.5 1 2.5h6c0-1 .3-1.8 1-2.5A6 6 0 0 0 12 3Z"/>'),
  coffee: W('<path d="M17 8h1a4 4 0 0 1 0 8h-1"/><path d="M3 8h14v8a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4Z"/><path d="M6 2v2"/><path d="M10 2v2"/><path d="M14 2v2"/>'),
  landmark: W('<path d="M3 22h18"/><path d="M6 18v-7"/><path d="M10 18v-7"/><path d="M14 18v-7"/><path d="M18 18v-7"/><path d="m12 2 9 6H3Z"/>'),
  building: W('<rect x="4" y="3" width="16" height="18" rx="1.5"/><path d="M9 7h1"/><path d="M14 7h1"/><path d="M9 11h1"/><path d="M14 11h1"/><path d="M10 21v-5h4v5"/>'),
  fruit: W('<circle cx="12" cy="14" r="7"/><path d="M12 7c0-2 1.4-3.6 3.2-3.8"/><path d="M12 7c-1-1.6-.6-3 0-3.7"/>'),
  cup: W('<path d="M5 5h14l-1.4 15a2 2 0 0 1-2 1.8H8.4a2 2 0 0 1-2-1.8Z"/><path d="M6 10h12"/>'),
  sprout: W('<path d="M7 20h10"/><path d="M12 20V9"/><path d="M12 12c-1-3-4-4-6-3 0 3 3 4 6 3Z"/><path d="M12 10c1-2.6 4-3.6 6-2.6 0 2.6-3 3.6-6 2.6Z"/>'),
  vase: W('<path d="M8 3h8"/><path d="M9.5 3c0 2.5-3 3.5-3 7a5.5 5.5 0 0 0 11 0c0-3.5-3-4.5-3-7"/>'),
  megaphone: W('<path d="M4 9v6h3l10 5V4L7 9Z"/><path d="M18.5 9a4 4 0 0 1 0 6"/>'),
  repeat: W('<path d="M17 2.5 21 6l-4 3.5"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><path d="M7 21.5 3 18l4-3.5"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/>'),
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
