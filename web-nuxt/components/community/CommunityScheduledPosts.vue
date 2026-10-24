<template>
  <details v-if="posts.length" class="scheduled-section">
    <summary class="scheduled-summary"><IconLine name="calendar" /> Bài đã lên lịch ({{ posts.length }})</summary>
    <div class="scheduled-list">
      <div v-for="sp in posts" :key="sp.id" class="scheduled-item">
        <p>{{ sp.content?.slice(0, 100) }}{{ (sp.content?.length || 0) > 100 ? '...' : '' }}</p>
        <div class="scheduled-meta">
          <time :datetime="sp.scheduled_at">{{ new Date(sp.scheduled_at).toLocaleString('vi-VN') }}</time>
          <button type="button" class="btn btn-ghost btn-sm scheduled-cancel" @click="$emit('cancel', sp.id)">Hủy</button>
        </div>
      </div>
    </div>
  </details>
</template>

<script setup lang="ts">
defineProps<{
  posts: Array<{ id: string; content?: string; scheduled_at: string }>
}>()

defineEmits<{
  (e: 'cancel', id: string): void
}>()
</script>

<style scoped>
.scheduled-section { margin-bottom: var(--space-4); }
.scheduled-summary { cursor: pointer; font-weight: var(--weight-semibold); color: var(--color-action); padding: var(--space-2) 0; min-height: 44px; display: inline-flex; align-items: center; gap: var(--space-1); }
.scheduled-summary::-webkit-details-marker { display: none; }
.scheduled-summary:focus-visible { outline: 2px solid var(--color-focus); outline-offset: 2px; border-radius: var(--radius-control); }
.scheduled-list { display: flex; flex-direction: column; gap: 0; margin-top: var(--space-1); border-block-start: 1px solid var(--line); }
.scheduled-item { padding: var(--space-3) 0; background: transparent; border: 0; border-block-end: 1px solid var(--line); border-radius: 0; }
.scheduled-item p { margin: 0; font-size: var(--text-sm); line-height: var(--leading-relaxed); overflow-wrap: anywhere; }
.scheduled-meta { display: flex; justify-content: space-between; align-items: center; margin-top: var(--space-1); font-size: var(--text-xs); color: var(--muted); font-variant-numeric: tabular-nums; }
.scheduled-cancel { color: var(--error); padding: 0 var(--space-3); min-height: 44px; min-width: 44px; display: inline-flex; align-items: center; justify-content: center; }
.scheduled-cancel:hover { background: rgba(var(--color-error-rgb), .08); }
</style>
