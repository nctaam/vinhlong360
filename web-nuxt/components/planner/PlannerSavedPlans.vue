<template>
  <div v-if="savedPlans.length" class="saved-plans">
    <h2 class="sediment-head">Lịch trình đã lưu</h2>
    <div v-for="(plan, pi) in savedPlans" :key="pi" class="saved-plan-item">
      <button type="button" class="saved-plan-info saved-plan-btn" :disabled="saving" @click="$emit('load', pi)">
        <strong>{{ plan.title || 'Lịch trình chưa đặt tên' }}</strong>
        <small>{{ plan.stops.length }} điểm · Lưu {{ formatDate(plan.savedAt) }}</small>
      </button>
      <div class="saved-plan-actions">
        <button
          v-if="plan.id"
          type="button"
          :class="['btn btn-sm', plan.is_public ? 'btn-outline' : 'btn-ghost']"
          :disabled="saving || planBusy === pi || publishBlockedByConflict(plan)"
          :aria-describedby="publishBlockedByConflict(plan) ? 'planner-publish-conflict-reason' : undefined"
          @click="$emit('publish', pi)"
        >
          {{ planBusy === pi ? 'Đang cập nhật' : plan.is_public ? 'Công khai' : 'Riêng tư' }}
        </button>
        <button type="button" class="btn btn-sm btn-ghost" :disabled="planBusy === pi" @click="$emit('share', pi)">Chia sẻ</button>
        <button type="button" class="btn btn-sm btn-ghost danger" :disabled="saving || planBusy === pi" @click="$emit('delete', pi)">Xóa</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { SavedPlan } from '~/utils/plannerSnapshots'
import { formatDateVN as formatDate } from '~/utils/safe'

defineProps<{
  savedPlans: SavedPlan[]
  saving: boolean
  planBusy: number
  publishBlockedByConflict: (plan: SavedPlan) => boolean
}>()

defineEmits<{
  (e: 'load', index: number): void
  (e: 'publish', index: number): void
  (e: 'share', index: number): void
  (e: 'delete', index: number): void
}>()
</script>

<style scoped>
.dark .saved-plan-item { background: var(--bg-alt); border-color: var(--line); }
.dark .saved-plan-item:hover { border-color: rgba(var(--white-rgb),.1); }
</style>
