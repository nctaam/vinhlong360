<template>
  <button class="share-btn" @click="share" :title="copied ? 'Đã sao chép!' : 'Chia sẻ'">
    {{ copied ? '✓ Đã sao chép' : '🔗 Chia sẻ' }}
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
  padding: 8px 16px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: #fff;
  font-size: .85rem;
  font-weight: 600;
  color: var(--primary);
  cursor: pointer;
  transition: background .15s, border-color .15s;
}
.share-btn:hover { background: var(--bg-warm); border-color: var(--primary-light); }
</style>
