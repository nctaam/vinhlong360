<template>
  <div class="home-community-feed">
    <template v-if="posts.length">
      <p v-if="stats && (stats.posts || stats.reviews || stats.members)" class="community-stats-line">
        <strong>{{ stats.posts }}</strong> bài viết
        · <strong>{{ stats.reviews }}</strong> đánh giá
        · <strong>{{ stats.members }}</strong> thành viên
      </p>
      <div v-if="trendingTags.length" class="trending-tags">
        <span class="tt-label"><IconLine name="flame" /> Đang được nhắc:</span>
        <NuxtLink v-for="t in trendingTags" :key="t.tag" :to="`/cong-dong?tag=${encodeURIComponent(t.tag)}`" class="tt-chip">{{ t.tag }}</NuxtLink>
      </div>
      <!-- declutter-3 T16 (B1-6): dàn chip leaderboard → 1 link teaser (đích /bang-xep-hang) -->
      <p v-if="topMembers.length" class="home-leaders-teaser">
        <IconLine name="trophy" /> <NuxtLink to="/bang-xep-hang">Xem thành viên tích cực <IconLine name="arrow-right" class="inline-arrow" aria-hidden="true" /></NuxtLink>
      </p>
      <div class="scroll-row home-community-dispatches" role="region" aria-label="Bài viết cộng đồng mới" tabindex="0">
        <NuxtLink v-for="p in posts" :key="p.id" :to="postPath(p.id)" class="cm-card">
          <div class="cm-body">
            <div class="cm-author">
              <span class="cm-avatar">{{ (p.display_name || '?').charAt(0).toUpperCase() }}</span>
              <span class="cm-name">{{ p.display_name || 'Người dùng' }}</span>
              <span v-if="p.post_type_label" class="cm-type">{{ p.post_type_label }}</span>
            </div>
            <p class="cm-content">{{ p.content }}</p>
            <div class="cm-meta">
              <span v-if="p.likes"><IconLine name="heart" /> {{ p.likes }}</span>
              <span v-if="p.comments_count || p.comment_count"><IconLine name="message" /> {{ p.comments_count || p.comment_count }}</span>
              <span v-if="p.entity_name" class="cm-place">{{ p.entity_name }}</span>
            </div>
          </div>
        </NuxtLink>
      </div>
    </template>
    <div class="community-join">
      <span>Chia sẻ quán ngon, điểm đẹp, mẹo đi — góp một mảnh ghép cho bản đồ chung.</span>
      <NuxtLink to="/cong-dong" class="btn btn-outline"><IconLine name="message" /> Tham gia cộng đồng</NuxtLink>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  posts: any[]
  stats?: { posts?: number; reviews?: number; members?: number } | null
  trendingTags: any[]
  topMembers: any[]
}>()
</script>
