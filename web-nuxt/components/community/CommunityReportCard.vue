<template>
  <div v-if="reportEntityId" class="report-entity-card">
    <div>
      <p class="report-kicker">Báo sai dữ liệu</p>
      <h2>{{ reportEntity?.name || reportEntityId }}</h2>
      <p>{{ isLoggedIn ? 'Mô tả ngắn điểm sai để admin kiểm tra.' : 'Đăng nhập để gửi báo cáo.' }}</p>
    </div>
    <div v-if="isLoggedIn" class="report-form-inline">
      <div class="report-reasons">
        <button
          v-for="reason in reportReasons"
          :key="reason"
          type="button"
          :class="['chip', { active: reportReason === reason }]"
          :aria-pressed="reportReason === reason"
          @click="reportReason = reason"
        >{{ reason }}</button>
      </div>
      <textarea
        v-model="reportReason"
        class="textarea"
        rows="3"
        placeholder="Ví dụ: địa chỉ sai, thiếu nguồn, tọa độ không đúng…"
        aria-label="Mô tả báo cáo"
      ></textarea>
      <button
        type="button"
        class="btn btn-primary"
        :disabled="reportSubmitting || reportReason.trim().length < 5"
        @click="submitEntityReport"
      >
        {{ reportSubmitting ? 'Đang gửi…' : 'Gửi báo cáo' }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { Entity } from '~/types'
import { getStatusCode, extractErrorMessage } from '~/composables/useFetchError'

function firstQueryValue(value: unknown) {
  return Array.isArray(value) ? String(value[0] || '') : String(value || '')
}

type ReportEntity = Entity & { quality?: Entity['quality'] & { has_source?: boolean } }

const route = useRoute()
const router = useRouter()
const { isLoggedIn, authHeaders, handleSessionExpired } = useAuth()
const { show: showToast } = useToast()

const reportEntityId = computed(() => firstQueryValue(route.query.report).trim())
const reportEntity = ref<ReportEntity | null>(null)
const reportReasons = ['Sai thông tin', 'Địa điểm đã đóng cửa', 'Ảnh không đúng', 'Nội dung phản cảm', 'Trùng lặp']
const reportReason = ref('')
const reportSubmitting = ref(false)

async function fetchReportEntity() {
  reportEntity.value = null
  if (!reportEntityId.value) return
  try {
    reportEntity.value = await $fetch<Entity>(`/api/entities/${encodeURIComponent(reportEntityId.value)}`)
    if (!reportReason.value) {
      reportReason.value = reportEntity.value?.quality?.has_source ? 'Nội dung cần cập nhật' : 'Thiếu nguồn xác minh'
    }
  } catch {
    reportEntity.value = { id: reportEntityId.value, type: 'unknown', name: reportEntityId.value } as ReportEntity
  }
}

async function submitEntityReport() {
  if (!isLoggedIn.value || !reportEntityId.value || reportReason.value.trim().length < 5) return
  reportSubmitting.value = true
  try {
    await $fetch('/api/report', {
      method: 'POST',
      headers: authHeaders(),
      body: {
        target_type: 'entity',
        target_id: reportEntityId.value,
        reason: reportReason.value.trim(),
      },
    })
    showToast('Đã gửi báo cáo. Cảm ơn bạn!', 'success')
    reportReason.value = ''
    const nextQuery = { ...route.query }
    delete nextQuery.report
    router.replace({ query: nextQuery })
  } catch (e: unknown) {
    if (getStatusCode(e) === 401) { handleSessionExpired(); return }
    showToast(extractErrorMessage(e, 'Không thể gửi báo cáo'), 'error')
  } finally {
    reportSubmitting.value = false
  }
}

watch(reportEntityId, () => fetchReportEntity())

onMounted(() => {
  if (reportEntityId.value) {
    fetchReportEntity()
  }
})
</script>

<style scoped>
.report-entity-card {
  display: flex; flex-direction: column; gap: var(--space-3);
  padding: var(--space-4); margin-bottom: var(--space-4);
  background: var(--bg-alt); border: 1.5px solid var(--accent);
  border-radius: var(--radius-sheet);
  animation: slide-up .3s var(--ease-out);
}
.report-entity-card:focus-within { border-color: var(--accent-dark); box-shadow: 0 0 0 4px rgba(var(--accent-rgb),.15); }
.report-entity-card:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
.report-kicker { margin: 0; font-size: var(--text-2xs); font-weight: var(--weight-bold); text-transform: uppercase; letter-spacing: var(--tracking-caps); color: var(--accent); }
.report-entity-card h2 { margin: 2px 0 var(--space-1); font-size: var(--text-base); font-weight: var(--weight-semibold); color: var(--ink); }
.report-entity-card p { margin: 0; color: var(--muted); font-size: var(--text-sm); }
.report-form-inline { display: flex; flex-direction: column; gap: var(--space-2); margin-top: var(--space-2); }
.report-reasons { display: flex; flex-wrap: wrap; gap: var(--space-1); }
.dark .report-entity-card { background: rgba(var(--accent-rgb),.08); border-color: rgba(var(--accent-rgb),.3); }

@media (prefers-reduced-motion: reduce) {
  .report-entity-card { animation: none; }
}
</style>
