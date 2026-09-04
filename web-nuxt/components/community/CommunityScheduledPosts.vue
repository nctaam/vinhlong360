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
.scheduled-summary { cursor: pointer; font-weight: var(--weight-semibold); color: var(--primary-fg); padding: var(--space-2) 0; }
.scheduled-summary::-webkit-details-marker { display: none; }
.scheduled-summary:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; border-radius: var(--radius-control); }
.scheduled-list { display: flex; flex-direction: column; gap: var(--space-2); padding-top: var(--space-2); }
.scheduled-item { padding: var(--space-3); background: var(--card); border: .5px solid var(--line); border-radius: var(--radius-surface); }
.scheduled-item p { margin: 0; font-size: var(--text-sm); line-height: var(--leading-relaxed); overflow-wrap: anywhere; }
.scheduled-meta { display: flex; justify-content: space-between; align-items: center; margin-top: var(--space-2); font-size: var(--text-xs); color: var(--muted); }
.scheduled-cancel { color: var(--error); padding: var(--space-1) var(--space-2); min-height: 32px; }
.scheduled-cancel:hover { background: rgba(var(--color-error-rgb), .08); }
</style>
