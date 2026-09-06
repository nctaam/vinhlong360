<template>
  <div v-if="post" class="quote-preview">
    <div class="quote-preview-body">
      <span class="qp-head"><IconLine name="file-text" /> Trích dẫn <strong>{{ post.author || post.display_name || 'Người dùng' }}</strong></span>
      <span class="qp-content">{{ post.content || '(bài viết)' }}</span>
    </div>
    <button type="button" class="qp-remove" aria-label="Bỏ trích dẫn" @click="$emit('cancel')"><IconLine name="x" /></button>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  post: Record<string, any> | null
}>()

defineEmits<{
  (e: 'cancel'): void
}>()
</script>
