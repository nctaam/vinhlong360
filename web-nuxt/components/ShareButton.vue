<template>
  <button class="share-btn" @click="share" :title="copied ? 'Đã sao chép!' : 'Chia sẻ'" :aria-label="copied ? 'Đã sao chép link' : 'Chia sẻ link'">
    <svg v-if="!copied" class="share-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      <circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/>
      <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>
    </svg>
    <svg v-else class="share-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      <polyline points="20 6 9 17 4 12"/>
    </svg>
    {{ copied ? 'Đã sao chép' : 'Chia sẻ' }}
  </button>
</template>

<script setup lang="ts">
const props = defineProps<{ title?: string; text?: string }>()
const copied = ref(false)

async function share() {
  if (!import.meta.client) return
  const url = window.location.href
  if (navigator.share) {
    try {
      await navigator.share({ title: props.title, text: props.text, url })
      return
    } catch { /* cancelled or unsupported */ }
  }
  try {
    await navigator.clipboard.writeText(url)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
  } catch { /* clipboard not available */ }
}
</script>

<style scoped>
.share-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  border: 1px solid var(--line);
  border-radius: var(--radius-full);
  background: var(--card);
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  color: var(--primary);
  cursor: pointer;
  min-height: 44px;
  transition: background var(--duration-fast) var(--ease-out), border-color var(--duration-fast), transform var(--duration-fast) var(--ease-spring);
}
.share-btn:hover { background: var(--bg-warm); border-color: var(--primary-light); }
.share-btn:active { transform: scale(.92); transition-duration: .08s; }
.share-btn:focus-visible { outline: 2px solid var(--primary); outline-offset: 3px; }
.share-icon { flex-shrink: 0; transition: transform var(--duration-fast) var(--ease-spring); }
.share-btn:hover .share-icon { transform: scale(1.08); }
</style>
