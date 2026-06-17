<template>
  <div class="error-page">
    <div class="error-content">
      <h1 class="error-code">{{ error?.statusCode || 500 }}</h1>
      <p class="error-msg">{{ message }}</p>
      <div class="error-actions">
        <button class="btn btn-primary" @click="handleError">Về trang chủ</button>
        <button class="btn btn-outline" @click="retry">Thử lại</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{ error: any }>()

const message = computed(() => {
  const code = props.error?.statusCode
  if (code === 404) return 'Trang bạn tìm không tồn tại hoặc đã bị xóa.'
  if (code === 403) return 'Bạn không có quyền truy cập trang này.'
  return 'Đã xảy ra lỗi. Vui lòng thử lại sau.'
})

function handleError() {
  clearError({ redirect: '/' })
}

function retry() {
  clearError()
  window.location.reload()
}

useSeoMeta({ title: `${props.error?.statusCode || 'Lỗi'} — vinhlong360` })
</script>

<style scoped>
.error-page {
  min-height: 80vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-10) var(--space-5);
}
.error-content { text-align: center; max-width: 400px; }
.error-code {
  font-size: 5rem;
  margin: 0;
  color: var(--primary);
  line-height: 1;
  font-weight: var(--weight-extrabold);
  letter-spacing: var(--tracking-tighter);
}
.error-msg {
  font-size: var(--text-lg);
  color: var(--muted);
  margin: var(--space-3) 0 0;
  line-height: var(--leading-relaxed);
}
.error-actions {
  display: flex;
  gap: var(--space-3);
  justify-content: center;
  margin-top: var(--space-6);
}
.error-content { animation: errorIn .5s var(--ease-spring); }
@keyframes errorIn { from { opacity: 0; transform: translateY(16px) scale(.97); } to { opacity: 1; transform: translateY(0) scale(1); } }
.error-code { background: linear-gradient(135deg, var(--primary) 0%, var(--accent) 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
.error-actions .btn { transition: all var(--duration-fast) var(--ease-out); }
.error-actions .btn:hover { transform: translateY(-1px); box-shadow: var(--shadow-md); }
.error-actions .btn:active { transform: scale(.95); transition-duration: .08s; }
</style>
