<template>
  <ol class="planner-steps" aria-label="Các bước tạo lịch trình">
    <li :class="['planner-step', { active: !stopCount, done: stopCount > 0 }]">
      <span class="step-dot">1</span><span class="step-label">Chọn điểm</span>
    </li>
    <li class="planner-step-sep" aria-hidden="true"></li>
    <li :class="['planner-step', { active: stopCount > 0 && stopCount < 2, done: stopCount >= 2 }]">
      <span class="step-dot">2</span><span class="step-label">Sắp xếp</span>
    </li>
    <li class="planner-step-sep" aria-hidden="true"></li>
    <li :class="['planner-step', { active: stopCount >= 2 }]">
      <span class="step-dot">3</span><span class="step-label">Xem & lưu</span>
    </li>
  </ol>
</template>

<script setup lang="ts">
defineProps<{
  stopCount: number
}>()
</script>

<style scoped>
.planner-steps {
  list-style: none; margin: 0 0 var(--space-5); padding: 0;
  display: flex; align-items: center; gap: var(--space-2);
  flex-wrap: wrap;
}
.planner-step { display: inline-flex; align-items: center; gap: var(--space-2); color: var(--muted); font-size: var(--text-sm); transition: color .3s var(--ease-out); }
.planner-step .step-dot {
  width: 26px; height: 26px; border-radius: 50%;
  display: inline-flex; align-items: center; justify-content: center;
  font-size: var(--text-xs); font-weight: var(--weight-bold);
  background: var(--bg-alt); color: var(--muted);
  border: .5px solid var(--line);
  transition: background .3s var(--ease-out), color .3s var(--ease-out), border-color .3s var(--ease-out), box-shadow .3s var(--ease-out-expo), transform .35s var(--ease-out-expo);
}
.planner-step.active { color: var(--ink); font-weight: var(--weight-semibold); }
.planner-step.active .step-dot { background: var(--color-action); color: var(--color-on-action); border-color: var(--color-action); box-shadow: 0 0 0 4px rgba(var(--color-action-rgb), .18); transform: scale(1.05); }
.planner-step.done .step-dot { background: rgba(var(--secondary-rgb), .14); color: var(--secondary-fg); border-color: rgba(var(--secondary-rgb), .3); }
.planner-step.done .step-label { color: var(--ink); }
.planner-step-sep { flex: 1 1 18px; min-width: 18px; max-width: 48px; height: 2px; border-radius: 1px; background: var(--line); }
.dark .planner-step .step-dot { background: var(--bg-alt); border-color: var(--line); }

@media (prefers-reduced-motion: reduce) {
  .planner-step.active .step-dot { transform: none; }
}
</style>
