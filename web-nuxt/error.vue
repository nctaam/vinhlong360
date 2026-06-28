<template>
  <div class="error-page">
    <div class="error-content" role="alert">
      <div class="error-illust" aria-hidden="true">
        <svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
          <!-- warm clay halo + nested calm circle -->
          <circle cx="100" cy="100" r="80" fill="var(--bg-warm)" class="illust-halo" />
          <circle cx="100" cy="100" r="55" fill="var(--bg)" />
          <g v-if="is404" class="illust-face">
            <!-- 404: nhân vật mơ màng / ngủ — nét mềm, thân thiện -->
            <path d="M72 86 q8 -8 16 0" stroke="var(--clay-400)" stroke-width="3.5" fill="none" stroke-linecap="round" />
            <path d="M112 86 q8 -8 16 0" stroke="var(--clay-400)" stroke-width="3.5" fill="none" stroke-linecap="round" />
            <path d="M78 120 Q100 110 122 120" stroke="var(--clay-400)" stroke-width="3" fill="none" stroke-linecap="round" />
          </g>
          <g v-else class="illust-face">
            <!-- 500/khác: nhân vật trầm tư — mắt nhắm nhẹ + miệng đăm chiêu -->
            <line x1="74" y1="86" x2="90" y2="86" stroke="var(--clay-400)" stroke-width="3.5" stroke-linecap="round" />
            <line x1="110" y1="86" x2="126" y2="86" stroke="var(--clay-400)" stroke-width="3.5" stroke-linecap="round" />
            <path d="M80 122 Q100 116 120 122" stroke="var(--clay-400)" stroke-width="3" fill="none" stroke-linecap="round" />
          </g>
          <!-- decorative sparkles (như EmptyState) -->
          <g fill="var(--accent)" class="illust-sparkles">
            <path class="spark spark-1" d="M155 45 l3 8 8 3 -8 3 -3 8 -3 -8 -8 -3 8 -3z" />
            <path class="spark spark-2" d="M40 55 l2 6 6 2 -6 2 -2 6 -2 -6 -6 -2 6 -2z" />
            <path class="spark spark-3" d="M160 140 l2 5 5 2 -5 2 -2 5 -2 -5 -5 -2 5 -2z" />
            <path class="spark spark-4" d="M44 142 l2 5 5 2 -5 2 -2 5 -2 -5 -5 -2 5 -2z" />
          </g>
        </svg>
      </div>
      <h1 class="error-code" :aria-label="`Lỗi ${error?.statusCode || 500}`">{{ error?.statusCode || 500 }}</h1>
      <p class="error-msg">{{ message }}</p>

      <!-- 404: gợi ý khám phá nhanh (discovery links — không phải form chốt đơn) -->
      <div v-if="is404" class="error-discovery">
        <p class="error-discovery-label">Có thể bạn muốn:</p>
        <div class="error-search" role="search">
          <input
            v-model="q"
            type="search"
            class="error-search-input"
            placeholder="Tìm điều bạn cần"
            aria-label="Tìm kiếm trên vinhlong360"
            @keyup.enter="goSearch"
          />
          <button type="button" class="btn btn-primary error-search-btn" @click="goSearch">Tìm</button>
        </div>
        <nav class="error-links" aria-label="Liên kết phổ biến">
          <NuxtLink v-for="l in popularLinks" :key="l.to" :to="l.to" class="error-link-pill">{{ l.label }}</NuxtLink>
        </nav>
      </div>

      <div class="error-actions">
        <button type="button" class="btn btn-primary" @click="handleError">Về trang chủ</button>
        <button type="button" v-if="!is404" class="btn btn-outline" @click="retry">Thử lại</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { captureClientError, installGlobalErrorCapture } from '~/composables/useClientError'
const props = defineProps<{ error: { statusCode?: number; message?: string; url?: string } }>()

const is404 = computed(() => props.error?.statusCode === 404)

const q = ref('')
const popularLinks = [
  { label: 'Du lịch', to: '/du-lich' },
  { label: 'Ẩm thực', to: '/san-pham' },
  { label: 'Sự kiện', to: '/su-kien' },
  { label: 'OCOP', to: '/ocop' },
]

function goSearch() {
  const term = q.value.trim()
  if (term) navigateTo(`/tim-kiem?q=${encodeURIComponent(term)}`)
}

// P3: báo lỗi fatal về backend (best-effort). Bỏ qua 404 (định tuyến bình thường,
// tránh spam). Chỉ chạy client-side; composable đã tự guard SSR + opt-out.
onMounted(() => {
  try {
    installGlobalErrorCapture()
    const code = props.error?.statusCode
    if (code !== 404) {
      captureClientError(
        `error.vue: HTTP ${code ?? 'unknown'}`,
        props.error?.message || `status ${code}`,
        { statusCode: code, url: props.error?.url },
      )
    }
  } catch {
    /* capture không bao giờ làm vỡ trang lỗi */
  }
})

const message = computed(() => {
  const code = props.error?.statusCode
  if (code === 404) return 'Hmm, trang này có vẻ đã chuyển đi rồi. 🌿 Bạn thử tìm lại hoặc quay về trang chủ nhé!'
  if (code === 403) return 'Bạn chưa có quyền vào đây. Liên hệ hỗ trợ nếu cần nha.'
  return 'Có lỗi gì đó trên máy chủ. Chúng tôi đang sửa chữa, bạn thử lại trong tý nhé!'
})

function handleError() {
  clearError({ redirect: '/' })
}

function retry() {
  const raw = props.error?.url || window.location.pathname
  const url = raw.startsWith('/') && !raw.startsWith('//') ? raw : '/'
  clearError()
  navigateTo(url, { replace: true })
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
.error-content { text-align: center; max-width: 460px; animation: errorIn .6s var(--ease-spring-gentle) both; }
@keyframes errorIn { from { opacity: 0; transform: translateY(16px) scale(.96); } to { opacity: 1; transform: translateY(0) scale(1); } }
@keyframes errorPartIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
@keyframes sparkTwinkle { 0%, 100% { opacity: .25; transform: scale(.9); } 50% { opacity: .7; transform: scale(1.05); } }

.error-illust { width: 160px; margin: 0 auto var(--space-4); }
.error-illust svg { width: 100%; height: auto; }
.illust-halo { transition: opacity .3s var(--ease-out); }
.illust-sparkles .spark { transform-box: fill-box; transform-origin: center; animation: sparkTwinkle 3.2s var(--ease-in-out, ease-in-out) infinite; }
.illust-sparkles .spark-2 { animation-delay: .8s; }
.illust-sparkles .spark-3 { animation-delay: 1.6s; }
.illust-sparkles .spark-4 { animation-delay: 2.4s; }

.error-code {
  font-size: clamp(3rem, 12vw, 5rem);
  margin: 0;
  line-height: 1;
  font-weight: var(--weight-extrabold);
  letter-spacing: var(--tracking-tighter);
  background: linear-gradient(135deg, var(--primary) 0%, var(--accent) 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
  animation: errorPartIn .5s var(--ease-out-expo) .1s both;
}
.error-msg {
  font-size: var(--text-base);
  color: var(--muted);
  margin: var(--space-3) 0 0;
  line-height: var(--leading-relaxed);
  animation: errorPartIn .5s var(--ease-out-expo) .2s both;
}

/* 404 discovery block */
.error-discovery { margin-top: var(--space-5); animation: errorPartIn .5s var(--ease-out-expo) .3s both; }
.error-discovery-label { font-size: var(--text-sm); color: var(--ink-tertiary); margin: 0 0 var(--space-2); }
.error-search { display: flex; gap: var(--space-2); justify-content: center; flex-wrap: wrap; margin-bottom: var(--space-3); }
.error-search-input {
  flex: 1 1 200px;
  min-width: 0;
  max-width: 280px;
  padding: 10px 16px;
  min-height: 44px;
  border: .5px solid var(--border-input, var(--border));
  border-radius: var(--radius-full);
  background: var(--card, var(--bg));
  color: var(--ink);
  font-size: .9rem;
  transition: border-color .25s var(--ease-out), box-shadow .3s var(--ease-out-expo);
}
.error-search-input:focus { outline: none; border-color: var(--accent); box-shadow: 0 0 0 3px rgba(var(--accent-rgb), .25); }
.error-search-btn { flex: 0 0 auto; padding: 0 var(--space-5); min-height: 44px; }
.error-links { display: flex; flex-wrap: wrap; gap: var(--space-2); justify-content: center; }
.error-link-pill {
  display: inline-flex;
  align-items: center;
  min-height: 44px;
  padding: var(--space-2) var(--space-4);
  border: .5px solid var(--line);
  border-radius: var(--radius-full);
  background: var(--bg-warm);
  color: var(--ink);
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  text-decoration: none;
  transition: transform .35s var(--ease-spring-gentle), border-color .3s var(--ease-out), background .3s var(--ease-out), box-shadow .3s var(--ease-out);
}
.error-link-pill:hover { transform: translateY(-1px); border-color: var(--primary); box-shadow: var(--shadow-sm); }
.error-link-pill:active { transform: scale(.96); }
.error-link-pill:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }

.error-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  justify-content: center;
  margin-top: var(--space-6);
  animation: errorPartIn .5s var(--ease-out-expo) .4s both;
}
.error-actions .btn { transition: transform .35s var(--ease-spring-gentle), box-shadow .35s var(--ease-out-expo); }
.error-actions .btn:hover { transform: translateY(-1px); box-shadow: var(--shadow-md); }
.error-actions .btn:active { transform: scale(.95); transition-duration: .08s; }

/* Dark mode: gradient text + SVG legibility */
.dark .error-code { background: linear-gradient(135deg, var(--primary-light) 0%, var(--accent) 100%); -webkit-background-clip: text; background-clip: text; }
.dark .illust-halo { opacity: .9; }
.dark .illust-face { stroke-opacity: 1; }
.dark .error-link-pill { background: var(--bg-alt, var(--bg-warm)); border-color: var(--border); }
.dark .error-link-pill:hover { border-color: var(--primary-fg); }
.dark .error-search-input { background: var(--card, var(--bg-alt)); border-color: var(--border); }
.dark .error-search-input:focus { border-color: var(--primary-fg); box-shadow: 0 0 0 3px rgba(var(--primary-rgb), .25); }

/* Mobile: stack actions + search vertically, generous touch targets */
@media (max-width: 520px) {
  .error-page { min-height: 60vh; padding: var(--space-8) var(--space-4); }
  .error-actions { flex-direction: column; align-items: stretch; }
  .error-actions .btn { width: 100%; min-width: 140px; }
  .error-search { flex-direction: column; align-items: stretch; }
  .error-search-input { max-width: none; }
  .error-search-btn { width: 100%; }
}

@media (prefers-reduced-motion: reduce) {
  .error-content,
  .error-code,
  .error-msg,
  .error-discovery,
  .error-actions { animation: none; }
  .illust-sparkles .spark { animation: none; }
  .error-actions .btn,
  .error-link-pill,
  .error-search-input { transition: none; }
}
@media (forced-colors: active) {
  .error-code { -webkit-text-fill-color: Highlight; background: none; }
  .error-illust circle, .error-illust line, .error-illust path { stroke: CanvasText; }
  .illust-halo { fill: Canvas; }
  .error-search-input { border: 1px solid ButtonBorder; }
  .error-link-pill { border: 1px solid ButtonText; }
  .error-actions .btn { border: 1px solid ButtonText; }
}
</style>
