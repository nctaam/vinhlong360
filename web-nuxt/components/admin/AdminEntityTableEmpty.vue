<template>
  <tr v-if="!hasEntities">
    <td :colspan="colspan" class="admin-empty-row">
      <div class="ent-empty">
        <span class="ent-empty-icon">&#128269;</span>
        <template v-if="search">
          <span>Không có kết quả cho “{{ search }}”.</span>
          <button type="button" class="btn btn-outline btn-sm" @click="$emit('clear-search')">Xóa tìm kiếm</button>
        </template>
        <template v-else>
          <span>Chưa có entity nào.</span>
          <button type="button" class="btn btn-primary btn-sm" @click="$emit('open-create')">+ Tạo mới</button>
        </template>
      </div>
    </td>
  </tr>
</template>

<script setup lang="ts">
defineProps<{
  hasEntities: boolean
  colspan: number
  search: string
}>()

defineEmits<{
  (e: 'clear-search'): void
  (e: 'open-create'): void
}>()
</script>
