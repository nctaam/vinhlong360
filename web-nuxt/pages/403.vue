<template>
  <main class="access-denied-page">
    <SystemSystemStatePanel
      kind="permission-denied"
      title="Bạn chưa có quyền truy cập"
      :description="description"
      :details="requiredDetail"
      :primary-label="primaryLabel"
      secondary-label="Về trang chủ"
      @primary="openAllowedArea"
      @secondary="navigateTo('/')"
    />
  </main>
</template>

<script setup lang="ts">
import { firstAdminRoute, resolveAdminScopes } from '~/utils/adminAccess'

const route = useRoute()
const { user } = useAuth()

useHead({
  title: 'Không đủ quyền truy cập',
})

const scopes = computed(() => resolveAdminScopes(user.value))
const landing = computed(() => firstAdminRoute(scopes.value))
const requestedPath = computed(() => {
  const value = Array.isArray(route.query.from) ? route.query.from[0] : route.query.from
  return typeof value === 'string' && value.startsWith('/admin') ? value : ''
})
const requiredScope = computed(() => {
  const value = Array.isArray(route.query.required) ? route.query.required[0] : route.query.required
  return typeof value === 'string' ? value : ''
})

const description = computed(() => requestedPath.value
  ? `Tài khoản hiện tại không được phép mở ${requestedPath.value}. Bạn vẫn có thể tiếp tục trong khu vực quản trị đã được cấp.`
  : 'Tài khoản hiện tại không có phạm vi cần thiết để mở màn hình này.')
const requiredDetail = computed(() => requiredScope.value ? `Quyền cần có: ${requiredScope.value}` : undefined)
const primaryLabel = computed(() => landing.value === '/' ? 'Về trang chủ' : 'Mở khu vực được phép')

function openAllowedArea() {
  return navigateTo(landing.value)
}
</script>

<style scoped>
.access-denied-page {
  display: grid;
  min-height: min(72vh, 760px);
  padding: clamp(var(--space-8), 8vw, var(--space-16)) var(--page-gutter, var(--space-4));
  place-items: center;
  background:
    linear-gradient(var(--line) 1px, transparent 1px),
    linear-gradient(90deg, var(--line) 1px, transparent 1px),
    var(--bg);
  background-size: 48px 48px;
}
</style>
