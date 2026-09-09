<template>
  <details class="ent-kbyg-details">
    <summary class="admin-label ent-kbyg-summary">
      <IconLine name="calendar" /> Mùa / thời điểm ({{ seasonMonths.length }} tháng<span v-if="seasonPeak.length">, {{ seasonPeak.length }} cao điểm</span>)
    </summary>
    <div class="ent-kbyg-fields">
      <p class="sf-help ent-season-hint">Bấm mỗi tháng để chuyển: không → có mùa → cao điểm → tắt.</p>
      <div class="ent-season-grid" role="group" aria-label="Chọn tháng theo mùa">
        <button v-for="(lbl, i) in monthLabels" :key="i" type="button"
          :class="['ent-season-cell', `ent-season-${monthState(i + 1)}`]"
          :aria-label="`Tháng ${lbl}: ${monthState(i + 1) === 'peak' ? 'cao điểm' : monthState(i + 1) === 'in' ? 'có mùa' : 'không'}`"
          @click="cycleMonth(i + 1)">T{{ lbl }}</button>
      </div>
      <div class="ent-season-legend">
        <span><i class="ent-season-swatch ent-season-in"></i> Có mùa</span>
        <span><i class="ent-season-swatch ent-season-peak"></i> Cao điểm</span>
      </div>
    </div>
  </details>
</template>

<script setup lang="ts">
defineProps<{
  seasonMonths: number[]
  seasonPeak: number[]
  monthLabels: string[]
  monthState: (month: number) => 'peak' | 'in' | 'none' | 'off'
  cycleMonth: (month: number) => void
}>()
</script>
