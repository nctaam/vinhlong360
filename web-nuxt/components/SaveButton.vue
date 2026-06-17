<template>
  <button
    :class="['save-btn', { saved: saved, 'save-btn-sm': size === 'sm' }]"
    :title="saved ? 'Bỏ lưu' : 'Lưu yêu thích'"
    :aria-label="saved ? 'Bỏ lưu' : 'Lưu yêu thích'"
    :aria-pressed="saved"
    @click.prevent.stop="onToggle"
  >
    <svg class="save-icon" viewBox="0 0 24 24" aria-hidden="true">
      <path
        :d="heartPath"
        :fill="saved ? 'currentColor' : 'none'"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
      />
    </svg>
    <span v-if="showLabel" class="save-label">{{ saved ? 'Đã lưu' : 'Lưu' }}</span>
  </button>
</template>

<script setup lang="ts">
const props = defineProps<{
  entity: Record<string, any>
  size?: 'sm' | 'md'
  showLabel?: boolean
}>()

const { isSaved, toggle } = useFavorites()
const { show: showToast } = useToast()

const saved = computed(() => isSaved(props.entity.id))
const heartPath = 'M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z'

function onToggle() {
  const wasSaved = saved.value
  toggle(props.entity)
  showToast(wasSaved ? `Đã bỏ lưu "${props.entity.name}"` : `Đã lưu "${props.entity.name}" ❤️`, 'success', 2500)
}
</script>
