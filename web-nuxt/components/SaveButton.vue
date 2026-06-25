<template>
  <button type="button"
    :class="['save-btn', { saved: saved, 'save-btn-sm': size === 'sm', 'save-pop': popping }]"
    :title="actionLabel"
    :aria-label="actionLabel"
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
const actionLabel = computed(() => saved.value ? `Bỏ lưu ${props.entity.name}` : `Lưu ${props.entity.name}`)
const heartPath = 'M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z'

const popping = ref(false)

function onToggle() {
  const wasSaved = saved.value
  toggle(props.entity)
  if (!wasSaved) {
    popping.value = true
    setTimeout(() => { popping.value = false }, 500)
  }
  showToast(wasSaved ? `Đã bỏ lưu "${props.entity.name}"` : `Đã lưu "${props.entity.name}"`, 'success', 2500)
}
</script>

<style scoped>
.save-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border: .5px solid var(--line);
  border-radius: var(--radius-full);
  background: var(--card);
  color: var(--muted);
  cursor: pointer;
  min-height: 44px;
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  transition: background .3s var(--ease-out), color .3s var(--ease-out),
              border-color .3s var(--ease-out), transform .35s var(--ease-spring-gentle),
              box-shadow .3s var(--ease-out);
}
.save-btn:hover {
  background: var(--bg-warm);
  border-color: var(--save-red, #e74c3c);
  color: var(--save-red, #e74c3c);
  transform: translateY(-1px);
  box-shadow: var(--shadow-xs);
}
.save-btn:active { transform: scale(.92); transition-duration: .08s; }
.save-btn:focus-visible { outline: 2px solid var(--primary); outline-offset: 3px; }

.save-btn.saved {
  color: var(--save-red, #e74c3c);
  border-color: color-mix(in srgb, var(--save-red, #e74c3c) 30%, var(--line));
  background: color-mix(in srgb, var(--save-red, #e74c3c) 6%, var(--card));
}

.save-btn-sm { padding: var(--space-1) var(--space-2); min-height: 36px; font-size: var(--text-xs); }

.save-icon {
  width: 18px; height: 18px; flex-shrink: 0;
  transition: transform .35s var(--ease-spring-gentle);
}
.save-btn:hover .save-icon { transform: scale(1.12); }

.save-pop .save-icon { animation: heartPop .5s var(--ease-spring-gentle); }

@keyframes heartPop {
  0% { transform: scale(1); }
  30% { transform: scale(1.35); }
  60% { transform: scale(.9); }
  100% { transform: scale(1); }
}

@media (prefers-reduced-motion: reduce) {
  .save-btn, .save-icon { transition: none; }
  .save-pop .save-icon { animation: none; }
  .save-btn:hover { transform: none; }
  .save-btn:active { transform: none; }
}
</style>
