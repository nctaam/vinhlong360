<template>
  <div class="error-page" data-color-system="tri-region-v1">
    <div class="error-content" role="alert">
      <!-- Mekong Cultural Visual: Bến Đò Lỡ Chuyến -->
      <div class="error-illust" aria-hidden="true">
        <div class="illust-halo">
          <VernacularGlyph name="three-plank-sampan" :size="64" accent="clay" />
        </div>
      </div>

      <!-- Cultural Heritage Narrative -->
      <h1 class="error-heading">
        {{ is404 ? 'Bến Đò Lỡ Chuyến · Xin Quý Khách Thong Thả Đợi Chuyến Sau' : 'Con Nước Tạm Đứng · Xin Quý Khách Chờ Trong Giây Lát' }}
      </h1>

      <p class="error-msg">
        {{ is404 ? 'Dòng sông Cổ Chiên mênh mông nghìn năm con nước lớn ròng. Đôi khi lối rẽ bạn tìm tạm thời đổi bến hoặc con nước chưa kịp đưa thuyền cập bến. Xin mời thong thả quay về bến chính hoặc chọn một ngả đường sông nước thân quen dưới đây.' : message }}
      </p>

      <!-- 404: Tìm kiếm nhanh & Lối rẽ về bến an toàn -->
      <div v-if="is404" class="error-discovery">
        <div class="error-search" role="search">
          <input
            v-model="q"
            type="search"
            class="error-search-input"
            placeholder="Tìm di sản, món ngon, bến đò…"
            aria-label="Tìm kiếm trên vinhlong360"
            @keyup.enter="goSearch"
          />
          <button type="button" class="error-search-btn" @click="goSearch">
            <IconLine name="search" aria-hidden="true" />
            <span>Tìm</span>
          </button>
        </div>

        <p class="error-discovery-label">Hoặc chọn các ngả đường sông nước thân quen:</p>
        <nav class="error-links" aria-label="Liên kết phổ biến">
          <NuxtLink v-for="l in popularLinks" :key="l.to" :to="l.to" class="error-link-pill">
            <IconLine v-if="l.icon" :name="l.icon" class="error-link-pill__icon" />
            <span>{{ l.label }}</span>
          </NuxtLink>
        </nav>
      </div>

      <!-- 4 Safe Haven Waypoint Cards -->
      <div class="safe-haven-grid">
        <button type="button" class="safe-haven-card haven-primary" @click="handleError">
          <IconLine name="home" aria-hidden="true" />
          <div>
            <strong>Về Bến Chính</strong>
            <small>Trang chủ Di sản Vĩnh Long 360</small>
          </div>
        </button>

        <NuxtLink to="/ban-do" class="safe-haven-card">
          <IconLine name="map" aria-hidden="true" />
          <div>
            <strong>Bản Đồ Thủy Thổ</strong>
            <small>Tọa độ GPS &amp; Cẩm nang bến bãi</small>
          </div>
        </NuxtLink>

        <NuxtLink to="/am-thuc" class="safe-haven-card">
          <IconLine name="bowl" aria-hidden="true" />
          <div>
            <strong>Ký Sự Ẩm Thực</strong>
            <small>Hương vị miệt vườn phù sa</small>
          </div>
        </NuxtLink>

        <NuxtLink to="/danh-ba" class="safe-haven-card">
          <IconLine name="phone" aria-hidden="true" />
          <div>
            <strong>Danh Bạ Cứu Hộ</strong>
            <small>Số điện thoại bến phà &amp; y tế 24/7</small>
          </div>
        </NuxtLink>
      </div>

      <!-- Actions & Offline Rescue Trigger -->
      <div class="error-actions">
        <button type="button" class="btn btn-primary" @click="handleError">
          <IconLine name="home" aria-hidden="true" />
          <span>Về trang chủ</span>
        </button>
        <button type="button" v-if="!is404" class="btn btn-outline" @click="retry">
          <IconLine name="repeat" aria-hidden="true" />
          <span>Thử lại</span>
        </button>
        <button
          type="button"
          class="btn btn-offline-trigger"
          aria-label="Kích hoạt bảng cứu hộ ngoại tuyến"
          @click="showOfflinePanel = true"
        >
          <VernacularGlyph name="three-plank-sampan" :size="18" accent="silt" />
          <span>Chế độ Cứu hộ Ngoại tuyến</span>
        </button>
      </div>

      <!-- Offline Terroir Panel Modal Triggered when Requested -->
      <ClientOnly>
        <OfflineTerroirPanel
          v-model:open="showOfflinePanel"
          :is-offline="true"
          @close="showOfflinePanel = false"
        />
      </ClientOnly>

      <!-- Technical Status at Footer -->
      <footer class="error-technical-footer">
        <span class="error-code-badge">Mã trạng thái: {{ error?.statusCode || 500 }}</span>
      </footer>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { captureClientError, installGlobalErrorCapture } from '~/composables/useClientError'

const props = defineProps<{ error: { statusCode?: number; message?: string; url?: string } }>()

const is404 = computed(() => props.error?.statusCode === 404)
const showOfflinePanel = ref(false)
const q = ref('')

const popularLinks = [
  { label: 'Du lịch', to: '/du-lich', icon: 'compass' },
  { label: 'Ẩm thực', to: '/am-thuc', icon: 'bowl' },
  { label: 'Sự kiện', to: '/su-kien', icon: 'calendar' },
  { label: 'OCOP', to: '/ocop', icon: 'gift' },
]

function goSearch() {
  const term = q.value.trim()
  if (term) navigateTo(`/tim-kiem?q=${encodeURIComponent(term)}`)
}

onMounted(() => {
  try {
    installGlobalErrorCapture()
    const code = props.error?.statusCode
    if (code !== 404) {
      captureClientError(
        `error.vue: HTTP ${code}`,
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
  if (code === 404) return 'Trang bạn tìm kiếm hiện không còn ở địa chỉ này. Bạn thử tìm kiếm lại hoặc quay về trang chủ nhé!'
  if (code === 403) return 'Bạn chưa có quyền vào đây. Liên hệ hỗ trợ nếu cần nha.'
  return 'Có lỗi gì đó trên máy chủ. Chúng tôi đang sửa chữa, bạn thử lại trong giây lát nhé!'
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

useSeoMeta({
  title: `${props.error?.statusCode || 'Lỗi'} — vinhlong360`,
  robots: 'noindex, nofollow',
  ogTitle: `${props.error?.statusCode || 'Lỗi'} — vinhlong360`,
  twitterCard: 'summary_large_image',
})
</script>

<style scoped>
.error-page {
  min-height: 80vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-fib-5) var(--space-fib-3);
  background: var(--color-canvas);
  color: var(--color-text);
}

.error-content {
  width: 100%;
  max-width: 680px;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: var(--space-fib-3);
}

.error-illust {
  display: flex;
  align-items: center;
  justify-content: center;
}

.illust-halo {
  width: 110px;
  height: 110px;
  border-radius: var(--radius-full);
  background: color-mix(in srgb, var(--color-material-clay) 12%, var(--color-surface));
  border: 1.5px solid var(--alluvial-gold);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: var(--shadow-md);
}

.error-heading {
  margin: 0;
  font-family: var(--font-editorial, 'Lora', serif);
  font-size: var(--font-size-headline);
  font-weight: var(--weight-title);
  color: var(--color-text);
  line-height: 1.35;
}

.error-msg {
  margin: 0;
  font-size: var(--font-size-body);
  color: var(--color-text-muted);
  line-height: 1.65;
  max-width: 58ch;
}

.error-discovery {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: var(--space-fib-2);
}

.error-search {
  display: flex;
  gap: var(--space-fib-1);
  width: 100%;
  max-width: 480px;
  margin-inline: auto;
}

.error-search-input {
  flex: 1;
  min-height: 44px;
  padding: 0 var(--space-fib-3);
  font-family: var(--font-body, inherit);
  font-size: var(--font-size-body);
  color: var(--color-text);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  outline: none;
}

.error-search-input:focus {
  border-color: var(--alluvial-gold);
}

.error-search-btn {
  min-width: 44px;
  min-height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 0 var(--space-fib-3);
  background: var(--color-action);
  color: var(--sand-50);
  border: none;
  border-radius: var(--radius-control);
  font-weight: var(--weight-title-sm);
  cursor: pointer;
}

.error-discovery-label {
  margin: var(--space-fib-1) 0 0;
  font-size: var(--font-size-caption);
  color: var(--color-text-muted);
}

.error-links {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: var(--space-fib-1);
}

.error-link-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 44px;
  padding: 0 var(--space-fib-3);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-full);
  color: var(--color-text);
  text-decoration: none;
  font-size: var(--font-size-caption);
  transition: all 0.15s ease;
}

.error-link-pill:hover {
  background: var(--color-surface-raised);
  border-color: var(--alluvial-gold);
}

.safe-haven-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: var(--space-fib-2);
  width: 100%;
  margin: var(--space-fib-2) 0;
}

.safe-haven-card {
  display: flex;
  align-items: center;
  gap: var(--space-fib-2);
  min-height: 52px;
  padding: var(--space-fib-2) var(--space-fib-3);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-surface);
  color: var(--color-text);
  text-decoration: none;
  text-align: left;
  cursor: pointer;
  transition: all 0.15s ease;
}

.safe-haven-card:hover {
  background: var(--color-surface-raised);
  border-color: var(--alluvial-gold);
}

.safe-haven-card strong {
  display: block;
  font-size: var(--font-size-body);
}

.safe-haven-card small {
  display: block;
  font-size: var(--font-size-label);
  color: var(--color-text-muted);
}

.error-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: var(--space-fib-2);
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-fib-1);
  min-height: 44px;
  padding: 0 var(--space-fib-4);
  border-radius: var(--radius-control);
  font-size: var(--font-size-body);
  font-weight: var(--weight-title-sm);
  cursor: pointer;
  text-decoration: none;
  transition: all 0.15s ease;
}

.btn-primary {
  background: var(--color-action);
  color: var(--sand-50);
  border: none;
}

.btn-outline {
  background: var(--color-surface);
  color: var(--color-text);
  border: 1px solid var(--color-border);
}

.btn-offline-trigger {
  background: var(--color-surface);
  color: var(--color-material-clay);
  border: 1.5px solid var(--alluvial-gold);
}

.btn-offline-trigger:hover {
  background: var(--color-surface-raised);
}

.error-technical-footer {
  margin-top: var(--space-fib-3);
  font-size: var(--font-size-label);
  color: var(--color-text-muted);
}

.error-code-badge {
  font-family: monospace;
  padding: 2px 6px;
  background: var(--color-surface-subtle);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
}
</style>
