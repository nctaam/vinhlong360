<template>
  <EmptyState
    v-if="activeTab === 'bookmarks' && !bookmarksLength && !bookmarksLoading"
    icon-name="bookmark"
    title="Chưa lưu bài viết nào"
    message="Nhấn biểu tượng bookmark trên bài viết để lưu lại và xem sau."
  />

  <EmptyState
    v-else-if="activeTab === 'following' && !postsLength && !loading && !feedError"
    icon-name="users"
    title="Chưa có bài từ người bạn theo dõi"
    message="Theo dõi người dùng và địa điểm để xem bài viết của họ ở đây."
    hint="Mở hồ sơ người dùng hoặc trang địa điểm rồi nhấn “Theo dõi”."
  >
    <template #actions>
      <NuxtLink to="/tim-kiem" class="btn btn-outline btn-sm">Tìm người để theo dõi</NuxtLink>
    </template>
  </EmptyState>

  <EmptyState
    v-else-if="activeTab !== 'bookmarks' && activeTab !== 'following' && !postsLength && !loading && !feedError"
    icon-name="message"
    title="Cộng đồng đang chờ bạn"
    message="Chưa có bài viết nào. Hãy là người đầu tiên chia sẻ!"
    hint="Chia sẻ ảnh chuyến đi, đặt câu hỏi, hay để lại đánh giá của bạn."
  >
    <template v-if="loggedIn" #actions>
      <button type="button" class="btn btn-primary btn-sm" @click="$emit('focus-composer')">Viết bài đầu tiên</button>
    </template>
    <template v-else #actions>
      <button type="button" class="btn btn-primary btn-sm" @click="$emit('login')">Đăng nhập để chia sẻ</button>
    </template>
  </EmptyState>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  activeTab: string
  bookmarksLength: number
  bookmarksLoading: boolean
  postsLength: number
  loading: boolean
  feedError: boolean
  isLoggedIn?: boolean | any
}>()

const loggedIn = computed(() => Boolean(props.isLoggedIn?.value ?? props.isLoggedIn))

defineEmits<{
  (e: 'focus-composer'): void
  (e: 'login'): void
}>()
</script>
