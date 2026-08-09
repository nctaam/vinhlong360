<template>
  <section class="planner-optimization-preview" data-optimization-preview aria-labelledby="planner-preview-title">
    <div class="planner-optimization-preview__head">
      <div>
        <span class="planner-optimization-preview__eyebrow">Bản xem trước</span>
        <h2 id="planner-preview-title">Đề xuất thứ tự mới</h2>
      </div>
      <span class="planner-optimization-preview__count">{{ changes.length }} thay đổi</span>
    </div>

    <div class="planner-optimization-preview__columns">
      <div>
        <h3>Hiện tại</h3>
        <ol data-preview-before>
          <li v-for="(stop, index) in before" :key="`before-${stopKey(stop, index)}`">
            <span>{{ index + 1 }}</span> {{ stopName(stop, index) }}
          </li>
        </ol>
      </div>
      <div>
        <h3>Đề xuất</h3>
        <ol data-preview-after>
          <li v-for="(stop, index) in after" :key="`after-${stopKey(stop, index)}`">
            <span>{{ index + 1 }}</span> {{ stopName(stop, index) }}
          </li>
        </ol>
      </div>
    </div>

    <ul v-if="tradeoffs.length" class="planner-optimization-preview__tradeoffs" data-preview-tradeoffs>
      <li v-for="tradeoff in tradeoffs" :key="tradeoff">{{ tradeoff }}</li>
    </ul>

    <div class="planner-optimization-preview__actions">
      <button type="button" class="btn btn-primary" data-preview-confirm @click="$emit('confirm')">Áp dụng đề xuất</button>
      <button type="button" class="btn btn-ghost" data-preview-cancel @click="$emit('cancel')">Giữ thứ tự hiện tại</button>
    </div>
  </section>
</template>

<script setup lang="ts">
interface PreviewStop {
  id?: string
  name?: string
}

const props = withDefaults(defineProps<{
  before: PreviewStop[]
  after: PreviewStop[]
  changes: Array<{ id: string; from: number; to: number; stop?: PreviewStop }>
  tradeoffs: string[]
}>(), {
  tradeoffs: () => [],
})

defineEmits<{ confirm: []; cancel: [] }>()

function stopKey(stop: PreviewStop, index: number): string {
  return stop.id || String(index)
}

function stopName(stop: PreviewStop, index: number): string {
  return stop.name || stop.id || `Điểm dừng ${index + 1}`
}

void props
</script>
