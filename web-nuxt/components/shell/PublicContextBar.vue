<template>
  <div class="public-context-bar" role="region" aria-label="Ngữ cảnh khu vực">
    <div class="public-context-inner">
      <div class="public-context-copy">
        <IconLine name="locate" aria-hidden="true" />
        <span class="public-context-label">Khu vực đang ưu tiên</span>
        <strong class="public-context-current">{{ currentRegionLabel }}</strong>
      </div>

      <label class="public-context-control">
        <IconLine class="public-context-mobile-icon" name="locate" aria-hidden="true" />
        <span class="sr-only">Đổi khu vực ưu tiên</span>
        <select v-model="selectedRegion" aria-label="Đổi khu vực ưu tiên">
          <option v-for="option in regionOptions" :key="option.value" :value="option.value">
            {{ option.label }}
          </option>
        </select>
        <IconLine class="public-context-chevron" name="chevron-down" aria-hidden="true" />
      </label>
    </div>
  </div>
</template>

<script setup lang="ts">
import { AREA_META } from '~/composables/useConstants'
import type { RegionSlug } from '~/composables/useRegionPref'

const { region, setRegion } = useRegionPref()
const allRegionsSummary = 'Vĩnh Long · Bến Tre · Trà Vinh'

const regionOptions = computed<Array<{ value: RegionSlug; label: string; summary: string }>>(() => [
  { value: 'all', label: 'Tất cả khu vực', summary: allRegionsSummary },
  { value: 'vinh-long', label: AREA_META['vinh-long']?.name || 'Vĩnh Long', summary: AREA_META['vinh-long']?.name || 'Vĩnh Long' },
  { value: 'ben-tre', label: AREA_META['ben-tre']?.name || 'Bến Tre', summary: AREA_META['ben-tre']?.name || 'Bến Tre' },
  { value: 'tra-vinh', label: AREA_META['tra-vinh']?.name || 'Trà Vinh', summary: AREA_META['tra-vinh']?.name || 'Trà Vinh' },
])

const selectedRegion = computed<RegionSlug>({
  get: () => region.value || 'all',
  set: value => setRegion(value),
})

const currentRegionLabel = computed(() =>
  regionOptions.value.find(option => option.value === selectedRegion.value)?.summary || allRegionsSummary,
)
</script>
