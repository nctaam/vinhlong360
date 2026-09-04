<template>
  <section
    ref="rootEl"
    class="planner-conflict-diff"
    data-planner-conflict-diff
    role="alert"
    aria-labelledby="planner-conflict-title"
    tabindex="-1"
  >
    <div class="planner-conflict-diff__head">
      <div>
        <span class="planner-conflict-diff__eyebrow">Cần bạn quyết định</span>
        <h2 id="planner-conflict-title">Lịch trình đã thay đổi trên thiết bị khác</h2>
      </div>
      <span class="planner-conflict-diff__revision">Bản máy chủ {{ conflict.revision }}</span>
    </div>
    <p id="planner-publish-conflict-reason" class="planner-conflict-diff__freshness">
      Cập nhật {{ formatDate(conflict.updatedAt) }}. Bản cục bộ vẫn được giữ nguyên để bạn đối chiếu. Hãy xử lý xung đột trước khi đổi trạng thái công khai.
    </p>
    <dl class="planner-conflict-diff__titles">
      <div>
        <dt>Bản cục bộ</dt>
        <dd>{{ planTitle.trim() || 'Lịch trình chưa đặt tên' }}</dd>
      </div>
      <div>
        <dt>Máy chủ</dt>
        <dd>{{ conflict.title }}</dd>
      </div>
    </dl>
    <div class="planner-conflict-diff__stops">
      <h3>Khác biệt theo điểm dừng</h3>
      <p v-if="!differences.length">Các điểm dừng giống nhau; chỉ tiêu đề hoặc thời điểm cập nhật khác.</p>
      <ul v-else>
        <li v-for="difference in differences" :key="difference.key">
          <strong>{{ difference.name }}</strong>
          <span>{{ difference.detail }}</span>
        </li>
      </ul>
    </div>
    <div class="planner-conflict-diff__actions" aria-label="Cách xử lý xung đột">
      <button type="button" class="btn btn-sm btn-outline" data-conflict-local :disabled="saving" @click="$emit('choose', 'local')">Giữ bản cục bộ</button>
      <button type="button" class="btn btn-sm btn-ghost" data-conflict-server :disabled="saving" @click="$emit('choose', 'server')">Dùng bản máy chủ</button>
      <button type="button" class="btn btn-sm btn-ghost" data-conflict-manual :disabled="saving" @click="$emit('choose', 'manual')">So sánh thủ công</button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { formatDateVN as formatDate } from '~/utils/safe'

interface PlannerConflictDifference {
  key: string
  name: string
  detail: string
}

interface ConflictSnapshot {
  revision: number
  updatedAt: string
  title: string
}

defineProps<{
  conflict: ConflictSnapshot
  planTitle: string
  differences: PlannerConflictDifference[]
  saving: boolean
}>()

defineEmits<{
  (e: 'choose', choice: 'local' | 'server' | 'manual'): void
}>()

const rootEl = ref<HTMLElement | null>(null)

defineExpose({
  focus: () => rootEl.value?.focus(),
  $el: rootEl,
})
</script>

<style scoped>
.planner-conflict-diff {
  margin: 0 0 var(--space-5);
  padding: var(--space-5);
  border: 1px solid var(--warning-border);
  border-radius: var(--radius-sheet);
  background:
    linear-gradient(135deg, rgba(var(--warning-rgb), .1), transparent 58%),
    var(--card);
  box-shadow: var(--shadow-sm);
}
.planner-conflict-diff:focus-visible { outline: 3px solid var(--primary); outline-offset: 3px; }
.planner-conflict-diff__head { display: flex; align-items: flex-start; justify-content: space-between; gap: var(--space-4); }
.planner-conflict-diff__eyebrow {
  display: block; margin-bottom: var(--space-1); color: var(--warning);
  font-size: var(--text-2xs); font-weight: var(--weight-bold); letter-spacing: var(--tracking-caps); text-transform: uppercase;
}
.planner-conflict-diff h2 { margin: 0; color: var(--ink); font-family: var(--font-editorial); font-size: var(--text-xl); line-height: 1.2; }
.planner-conflict-diff__revision {
  flex: 0 0 auto; padding: var(--space-2) var(--space-3); border: 1px solid var(--warning-border);
  border-radius: var(--radius-full); color: var(--ink); background: var(--bg-alt); font-size: var(--text-xs); font-weight: var(--weight-bold);
}
.planner-conflict-diff__freshness { margin: var(--space-3) 0; color: var(--muted); font-size: var(--text-sm); }
.planner-conflict-diff__titles { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--space-3); margin: 0; }
.planner-conflict-diff__titles > div { padding: var(--space-3); border: .5px solid var(--line); border-radius: var(--radius-surface); background: var(--bg-alt); }
.planner-conflict-diff__titles dt { color: var(--muted); font-size: var(--text-xs); font-weight: var(--weight-semibold); }
.planner-conflict-diff__titles dd { margin: var(--space-1) 0 0; color: var(--ink); font-weight: var(--weight-semibold); overflow-wrap: anywhere; }
.planner-conflict-diff__stops { margin-top: var(--space-4); }
.planner-conflict-diff__stops h3 { margin: 0 0 var(--space-2); color: var(--ink); font-size: var(--text-sm); }
.planner-conflict-diff__stops p { margin: 0; color: var(--muted); font-size: var(--text-sm); }
.planner-conflict-diff__stops ul { display: grid; gap: var(--space-2); margin: 0; padding: 0; list-style: none; }
.planner-conflict-diff__stops li { display: flex; justify-content: space-between; gap: var(--space-3); padding: var(--space-2) var(--space-3); border-inline-start: 3px solid var(--warning); background: var(--bg-alt); }
.planner-conflict-diff__stops li span { color: var(--muted); font-size: var(--text-sm); text-align: end; }
.planner-conflict-diff__actions { display: flex; flex-wrap: wrap; gap: var(--space-2); margin-top: var(--space-4); }

@media (max-width: 640px) {
  .planner-conflict-diff { padding: var(--space-4); }
  .planner-conflict-diff__head { flex-direction: column; }
  .planner-conflict-diff__titles { grid-template-columns: 1fr; }
  .planner-conflict-diff__stops li { flex-direction: column; gap: var(--space-1); }
  .planner-conflict-diff__stops li span { text-align: start; }
  .planner-conflict-diff__actions .btn { width: 100%; }
}
</style>
