<template>
  <section
    class="map-list-fallback-state"
    data-map-fallback
    :data-map-state="state"
    :role="state === 'error' ? 'alert' : 'status'"
  >
    <IconLine :name="state === 'offline' ? 'globe' : state === 'loading' ? 'clock' : 'map-pin-off'" aria-hidden="true" />
    <div>
      <!-- h2: khối này là nội dung trực tiếp dưới h1 của trang (/ban-do có
           đúng hai tiêu đề: h1 "Bản đồ" rồi cái này), nên h3 làm cây tiêu đề
           nhảy mức. Component hiện chỉ có MỘT nơi gọi — MapListSurface.vue:73 —
           nên chốt cứng h2 là đúng; thêm nơi gọi ở ngữ cảnh khác thì đổi thành
           prop mức tiêu đề. -->
      <h2>{{ title }}</h2>
      <p>{{ message }}</p>
      <p class="map-list-fallback-state__continuity">
        Danh sách vẫn dùng được<span v-if="resultCount"> với {{ resultCount }} kết quả</span><span v-if="selectedAddress"> · {{ selectedAddress }}</span>.
      </p>
    </div>
    <button v-if="state === 'error'" type="button" class="btn btn-outline btn-sm" @click="$emit('retry')">Thử tải lại bản đồ</button>
  </section>
</template>

<script setup lang="ts">
const props = withDefaults(defineProps<{
  state: 'loading' | 'error' | 'offline' | 'empty' | 'partial' | 'stale'
  resultCount?: number
  selectedAddress?: string
}>(), {
  resultCount: 0,
  selectedAddress: '',
})

defineEmits<{ retry: [] }>()

const title = computed(() => ({
  loading: 'Đang chuẩn bị bản đồ',
  error: 'Bản đồ tạm thời không khả dụng',
  offline: 'Bản đồ không tải khi ngoại tuyến',
  empty: 'Chưa có vị trí để đặt trên bản đồ',
  partial: 'Bản đồ chỉ tải được một phần',
  stale: 'Nền bản đồ có thể đã cũ',
}[props.state]))

const message = computed(() => ({
  loading: 'Kết quả và địa chỉ đã sẵn sàng trong khi nền bản đồ tải.',
  error: 'Tile hoặc trình dựng bản đồ gặp sự cố; bộ lọc và lựa chọn không bị mất.',
  offline: 'Kết nối hiện không đủ để tải tile. Bạn vẫn có thể mở từng địa điểm.',
  empty: 'Các kết quả thiếu tọa độ vẫn được giữ trong danh sách.',
  partial: 'Một số tile chưa tải nhưng danh sách là nguồn đối chiếu chính.',
  stale: 'Hãy dùng địa chỉ trong danh sách để đối chiếu trước khi đi.',
}[props.state]))
</script>
