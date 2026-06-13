<template>
  <div class="error-page">
    <div class="error-content">
      <h1 class="error-code">{{ error?.statusCode || 500 }}</h1>
      <p class="error-msg">{{ message }}</p>
      <div style="display: flex; gap: 10px; justify-content: center; margin-top: 24px">
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
.error-page { min-height: 80vh; display: flex; align-items: center; justify-content: center; padding: 40px 20px; }
.error-content { text-align: center; max-width: 400px; }
.error-code { font-size: 5rem; margin: 0; color: var(--primary); line-height: 1; }
.error-msg { font-size: 1.1rem; color: var(--muted); margin: 12px 0 0; }
</style>
