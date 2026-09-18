<template>
  <div class="home-community-feed">
    <template v-if="posts.length">
      <p v-if="stats && (stats.posts || stats.reviews || stats.members)" class="community-stats-line">
        <strong>{{ stats.posts }}</strong> bài viết
        · <strong>{{ stats.reviews }}</strong> đánh giá
        · <strong>{{ stats.members }}</strong> thành viên
      </p>
      <div v-if="trendingTags.length" class="trending-tags">
        <span class="tt-label"><IconLine name="flame" aria-hidden="true" /> Đang được nhắc:</span>
        <NuxtLink v-for="t in trendingTags" :key="t.tag" :to="`/cong-dong?tag=${encodeURIComponent(t.tag)}`" class="tt-chip">{{ t.tag }}</NuxtLink>
      </div>
      <!-- declutter-3 T16 (B1-6): dàn chip leaderboard → 1 link teaser (đích /bang-xep-hang) -->
      <p v-if="topMembers.length" class="home-leaders-teaser">
        <IconLine name="trophy" aria-hidden="true" /> <NuxtLink to="/bang-xep-hang">Xem thành viên tích cực <IconLine name="arrow-right" class="inline-arrow" aria-hidden="true" /></NuxtLink>
      </p>
      <div class="scroll-row home-community-dispatches" role="region" aria-label="Bài viết cộng đồng mới" tabindex="0">
        <article v-for="p in posts" :key="p.id" class="cm-card">
          <div class="cm-body">
            <div class="cm-author">
              <span class="cm-avatar" aria-hidden="true">{{ (p.display_name || '?').charAt(0).toUpperCase() }}</span>
              <span class="cm-name">{{ p.display_name || 'Người dùng' }}</span>
              <span v-if="p.post_type_label" class="cm-type">{{ p.post_type_label }}</span>
              <span class="cm-author-badge"><IconLine name="shield-check" aria-hidden="true" /> Tác giả thực địa</span>
            </div>
            <NuxtLink :to="postPath(p.id)" class="cm-content-link" :aria-label="`Đọc bài viết của ${p.display_name || 'Người dùng'}: ${p.content}`">
              <p class="cm-content">{{ p.content }}</p>
            </NuxtLink>
            <div class="cm-meta">
              <span v-if="p.likes" :aria-label="`${p.likes} lượt thích`"><IconLine name="heart" aria-hidden="true" /> {{ p.likes }}</span>
              <span v-if="p.comments_count || p.comment_count" :aria-label="`${p.comments_count || p.comment_count} bình luận`"><IconLine name="message" aria-hidden="true" /> {{ p.comments_count || p.comment_count }}</span>
              <NuxtLink v-if="p.entity_name" :to="p.entity_id ? entityPath(p.entity_id) : '/du-lich'" class="cm-place" :aria-label="`Địa điểm: ${p.entity_name}`">
                <IconLine name="pin" aria-hidden="true" /> {{ p.entity_name }}
              </NuxtLink>
            </div>
          </div>
        </article>
      </div>
    </template>
    <div class="community-join">
      <span>Chia sẻ quán ngon, điểm đẹp, mẹo đi — góp một mảnh ghép cho bản đồ chung.</span>
      <NuxtLink to="/cong-dong" class="btn btn-outline"><IconLine name="message" aria-hidden="true" /> Tham gia cộng đồng</NuxtLink>
    </div>
  </div>
</template>

<script setup lang="ts">
import { entityPath, postPath } from '~/utils/routePaths'

defineProps<{
  posts: any[]
  stats?: { posts?: number; reviews?: number; members?: number } | null
  trendingTags: any[]
  topMembers: any[]
}>()
</script>
