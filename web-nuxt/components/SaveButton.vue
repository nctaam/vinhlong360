<template>
  <button
    :class="['save-btn', { saved: saved, 'save-btn-sm': size === 'sm' }]"
    :title="saved ? 'Bỏ lưu' : 'Lưu yêu thích'"
    @click.prevent.stop="onToggle"
  >
    <span class="save-icon">{{ saved ? '❤️' : '🤍' }}</span>
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

function onToggle() {
  const wasSaved = saved.value
  toggle(props.entity)
  showToast(wasSaved ? `Đã bỏ lưu "${props.entity.name}"` : `Đã lưu "${props.entity.name}" ❤️`, 'success', 2500)
}
</script>
