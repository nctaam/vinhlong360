<template>
  <section class="why-this-control" data-why-this-control>
    <button
      type="button"
      class="why-this-control__trigger"
      data-why-this-trigger
      :aria-expanded="expanded"
      :aria-controls="contentId"
      @click="expanded = !expanded"
    >
      <IconLine name="info" aria-hidden="true" />
      Vì sao tôi thấy mục này?
    </button>
    <div v-if="expanded" :id="contentId" class="why-this-control__content" role="status">
      <p class="why-this-control__reason">{{ normalizedReason }}</p>
      <ul v-if="normalizedSignals.length" class="why-this-control__signals" data-why-this-signals>
        <li v-for="signal in normalizedSignals" :key="signal">{{ signal }}</li>
      </ul>
      <button type="button" class="why-this-control__reset" data-why-this-reset @click="reset">
        Đặt lại đề xuất này
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
const props = withDefaults(defineProps<{
  reason: string
  signals?: string[]
  onReset?: () => void
}>(), {
  signals: () => [],
  onReset: undefined,
})

const emit = defineEmits<{ reset: [] }>()
const expanded = ref(false)
const contentId = useId()
const normalizedReason = computed(() => props.reason.trim() || 'Được cộng đồng quan tâm')
const normalizedSignals = computed(() => [...new Set(props.signals.map(signal => signal.trim()).filter(Boolean))])

function reset() {
  emit('reset')
}
</script>
