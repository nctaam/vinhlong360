<template>
  <div class="error-page">
    <div class="error-content">
      <div class="error-illust" aria-hidden="true">
        <svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
          <circle cx="100" cy="100" r="80" fill="var(--bg-warm)" />
          <circle cx="100" cy="100" r="55" fill="var(--bg)" />
          <g v-if="is404">
            <circle cx="80" cy="85" r="6" fill="var(--muted)" />
            <circle cx="120" cy="85" r="6" fill="var(--muted)" />
            <path d="M75 120 Q100 108 125 120" stroke="var(--muted)" stroke-width="3" fill="none" stroke-linecap="round" />
          </g>
          <g v-else>
            <line x1="72" y1="78" x2="88" y2="92" stroke="var(--muted)" stroke-width="3" stroke-linecap="round" />
            <line x1="88" y1="78" x2="72" y2="92" stroke="var(--muted)" stroke-width="3" stroke-linecap="round" />
            <line x1="112" y1="78" x2="128" y2="92" stroke="var(--muted)" stroke-width="3" stroke-linecap="round" />
            <line x1="128" y1="78" x2="112" y2="92" stroke="var(--muted)" stroke-width="3" stroke-linecap="round" />
            <circle cx="100" cy="118" r="10" fill="none" stroke="var(--muted)" stroke-width="3" />
          </g>
          <g fill="var(--accent)" opacity=".4">
            <path d="M155 45 l3 8 8 3 -8 3 -3 8 -3 -8 -8 -3 8 -3z" />
            <path d="M40 55 l2 6 6 2 -6 2 -2 6 -2 -6 -6 -2 6 -2z" />
            <path d="M160 140 l2 5 5 2 -5 2 -2 5 -2 -5 -5 -2 5 -2z" />
          </g>
        </svg>
      </div>
      <h1 class="error-code">{{ error?.statusCode || 500 }}</h1>
      <p class="error-msg">{{ message }}</p>
      <div class="error-actions">
        <button type="button" class="btn btn-primary" @click="handleError">Về trang chủ</button>
        <button type="button" v-if="!is404" class="btn btn-outline" @click="retry">Thử lại</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{ error: any }>()

const is404 = computed(() => props.error?.statusCode === 404)

const message = computed(() => {
  const code = props.error?.statusCode
  if (code === 404) return 'Trang bạn tìm không có hoặc đã chuyển đi. Thử quay về trang chủ nhé!'
  if (code === 403) return 'Bạn không có quyền truy cập trang này.'
  return 'Có lỗi xảy ra khi tải trang. Bạn có thể thử lại hoặc quay về trang chủ.'
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
.error-content { text-align: center; max-width: 420px; animation: errorIn .5s var(--ease-spring-gentle); }
@keyframes errorIn { from { opacity: 0; transform: translateY(16px) scale(.96); } to { opacity: 1; transform: translateY(0) scale(1); } }
.error-illust { width: 160px; margin: 0 auto var(--space-4); }
.error-illust svg { width: 100%; height: auto; }
.error-code {
  font-size: 4rem;
  margin: 0;
  line-height: 1;
  font-weight: var(--weight-extrabold);
  letter-spacing: var(--tracking-tighter);
  background: linear-gradient(135deg, var(--primary) 0%, var(--accent) 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
}
.error-msg {
  font-size: var(--text-base);
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
.error-actions .btn { transition: transform .35s var(--ease-spring-gentle), box-shadow .35s var(--ease-out-expo); }
.error-actions .btn:hover { transform: translateY(-1px); box-shadow: var(--shadow-md); }
.error-actions .btn:active { transform: scale(.95); transition-duration: .08s; }
@media (prefers-reduced-motion: reduce) {
  .error-content { animation: none; }
  .error-actions .btn { transition: none; }
}
</style>
