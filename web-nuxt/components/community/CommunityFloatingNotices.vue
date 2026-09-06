<template>
  <!-- Save momentum cue — keeps bookmarking from dead-ending -->
  <Transition name="momentum-fade">
    <div v-if="showBookmarkMomentum && !hiddenNotice" class="bookmark-momentum" role="status">
      <span class="bm-icon" aria-hidden="true"><IconLine name="bookmark" /></span>
      <button type="button" class="bm-link" @click="$emit('view-bookmarks')">Xem mục đã lưu</button>
      <button type="button" class="bm-dismiss" aria-label="Đóng" @click="$emit('dismiss-bookmark')"><IconLine name="x" /></button>
    </div>
  </Transition>

  <!-- Ẩn bài: lối hoàn tác NGAY tại chỗ -->
  <Transition name="momentum-fade">
    <div v-if="hiddenNotice" class="bookmark-momentum hide-undo" role="status" data-testid="hide-undo">
      <span class="bm-icon" aria-hidden="true"><IconLine name="eye-off" /></span>
      <span class="hu-text">Đã ẩn bài này khỏi bảng tin của bạn.</span>
      <button type="button" class="bm-link" data-post-action="undo-hide" :disabled="undoingHide" @click="$emit('undo-hide')">Hoàn tác</button>
      <button type="button" class="bm-dismiss" aria-label="Đóng" @click="$emit('dismiss-hide')"><IconLine name="x" /></button>
    </div>
  </Transition>
</template>

<script setup lang="ts">
defineProps<{
  showBookmarkMomentum: boolean
  hiddenNotice: { id: string } | null
  undoingHide: boolean
}>()

defineEmits<{
  (e: 'view-bookmarks'): void
  (e: 'dismiss-bookmark'): void
  (e: 'undo-hide'): void
  (e: 'dismiss-hide'): void
}>()
</script>

<style scoped>
.bookmark-momentum {
  position: fixed;
  z-index: var(--z-dropdown);
  bottom: calc(var(--space-6) + env(safe-area-inset-bottom));
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-2) var(--space-2) var(--space-4);
  background: var(--card);
  border: .5px solid var(--line);
  border-radius: var(--radius-full);
  box-shadow: var(--shadow-lg);
  max-width: calc(100vw - var(--space-6) * 2);
}
.bm-icon {
  font-size: 1.05rem;
  flex-shrink: 0;
}
.bm-link {
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
  color: var(--color-action);
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  min-height: 44px;
  display: inline-flex;
  align-items: center;
  transition: color .2s var(--ease-out);
}
.bm-link:hover {
  color: var(--ink);
  text-decoration: underline;
}
.bm-link:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 2px;
  border-radius: var(--radius-control);
}
.bm-dismiss {
  flex-shrink: 0;
  width: 44px;
  height: 44px;
  min-width: 44px;
  border-radius: var(--radius-full);
  background: none;
  border: none;
  cursor: pointer;
  color: var(--muted);
  font-size: 1.25rem;
  line-height: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: background .2s var(--ease-out), color .2s var(--ease-out), transform .2s var(--ease-out-expo);
}
.bm-dismiss:hover {
  background: var(--bg-alt);
  color: var(--ink);
}
.bm-dismiss:active {
  transform: scale(.9);
  transition-duration: .08s;
}
.bm-dismiss:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 2px;
}
.hide-undo {
  padding-left: var(--space-3);
}
.hu-text {
  font-size: var(--text-sm);
  color: var(--ink);
}
.bm-link:disabled {
  opacity: .55;
  cursor: progress;
}
.momentum-fade-enter-active {
  transition: opacity .25s var(--ease-out), transform .25s var(--ease-out-expo);
}
.momentum-fade-leave-active {
  transition: opacity .15s var(--ease-out), transform .15s var(--ease-out);
}
.momentum-fade-enter-from {
  opacity: 0;
  transform: translate(-50%, 16px);
}
.momentum-fade-leave-to {
  opacity: 0;
  transform: translate(-50%, 8px);
}

.dark .bookmark-momentum {
  background: var(--card);
  border-color: rgba(var(--white-rgb), .1);
  box-shadow: 0 8px 32px rgba(var(--black-rgb), .5);
}
.dark .bm-dismiss:hover {
  background: rgba(var(--white-rgb), .08);
}

@media (prefers-reduced-motion: reduce) {
  .momentum-fade-enter-active,
  .momentum-fade-leave-active {
    transition: none;
  }
  .bm-dismiss:active {
    transform: none;
  }
}
</style>
