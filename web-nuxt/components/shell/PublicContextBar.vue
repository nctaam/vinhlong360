<template>
  <div
    class="public-context-bar"
    data-public-context-line
    :data-location-mode="envelope.location.mode"
    role="region"
    aria-label="Ngữ cảnh khu vực"
  >
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
const { envelope } = usePublicContextEnvelope()
const allRegionsSummary = 'Vĩnh Long · Bến Tre · Trà Vinh'

// Tiền tố "Vùng" tách PHẦN khỏi TOÀN THỂ. Trước đây chuỗi "Vĩnh Long" vừa mở đầu
// tóm tắt của phạm vi TOÀN BỘ ("Vĩnh Long · Bến Tre · Trà Vinh") vừa là nhãn của
// MỘT trong ba vùng, nên trạng thái mặc định và trạng thái đã thu hẹp đọc lên
// gần như giống nhau — người dùng không biết mình đang ở phạm vi nào, và không
// đoán được lựa chọn đó làm gì. Chỉ đổi chữ hiển thị: slug không đổi nên dữ
// liệu, đường dẫn và lựa chọn đã lưu đều giữ nguyên.
const zoneLabel = (slug: RegionSlug, fallback: string) =>
  `Vùng ${AREA_META[slug]?.name || fallback}`

const regionOptions = computed<Array<{ value: RegionSlug; label: string; summary: string }>>(() => [
  { value: 'all', label: 'Tất cả khu vực', summary: allRegionsSummary },
  { value: 'vinh-long', label: zoneLabel('vinh-long', 'Vĩnh Long'), summary: zoneLabel('vinh-long', 'Vĩnh Long') },
  { value: 'ben-tre', label: zoneLabel('ben-tre', 'Bến Tre'), summary: zoneLabel('ben-tre', 'Bến Tre') },
  { value: 'tra-vinh', label: zoneLabel('tra-vinh', 'Trà Vinh'), summary: zoneLabel('tra-vinh', 'Trà Vinh') },
])

const selectedRegion = computed<RegionSlug>({
  get: () => region.value || 'all',
  set: value => setRegion(value),
})

const currentRegionLabel = computed(() =>
  regionOptions.value.find(option => option.value === selectedRegion.value)?.summary || allRegionsSummary,
)
</script>
