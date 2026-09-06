<template>
  <div class="threads-compose-guest">
    <div class="guest-avatar">
      <span class="avatar thread-avatar guest">?</span>
    </div>
    <div class="guest-content">
      <p>Có trải nghiệm muốn chia sẻ?</p>
      <button type="button" class="btn btn-outline btn-sm" @click="$emit('login')">Đăng nhập</button>
    </div>
  </div>
</template>

<script setup lang="ts">
defineEmits<{
  (e: 'login'): void
}>()
</script>

<style scoped>
.threads-compose-guest {
  display: flex;
  gap: var(--space-3);
  padding: var(--space-4) 0;
  border-bottom: .5px solid var(--line);
  align-items: center;
  margin-bottom: var(--space-2);
}
.guest-avatar {
  width: 40px;
  flex-shrink: 0;
  display: flex;
  justify-content: center;
}
.guest-avatar .avatar.guest {
  opacity: .5;
}
.guest-content {
  flex: 1;
  display: flex;
  align-items: center;
  gap: var(--space-3);
}
.guest-content p {
  margin: 0;
  color: var(--muted);
  font-size: var(--text-sm);
  flex: 1;
}
</style>
