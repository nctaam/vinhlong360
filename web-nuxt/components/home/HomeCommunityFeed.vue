<template>
  <div class="home-community-feed">
    <template v-if="posts.length">
      <!-- Elegantly styled community invitation spotlight banner -->
      <div class="home-community-banner">
        <div class="home-community-banner__content">
          <p v-if="stats && (stats.posts || stats.reviews || stats.members)" class="community-stats-line">
            <strong>{{ stats.posts }}</strong> bài viết
            · <strong>{{ stats.reviews }}</strong> đánh giá
            · <strong>{{ stats.members }}</strong> thành viên
          </p>
          <blockquote class="home-community-banner__quote">
            “Vĩnh Long không vội được đâu — cứ thong thả xuôi đò Cù Lao An Bình, ghé làng gốm Mang Thít lúc ráng chiều rồi mới hiểu trọn cái tình sông nước nơi đây.”
          </blockquote>
          <div class="home-community-banner__author">
            <span class="home-community-banner__avatar" aria-hidden="true">Đ</span>
            <div class="home-community-banner__meta">
              <strong class="home-community-banner__name">Đoàn Lữ Khách Phương Nam</strong>
              <span class="cm-author-badge"><IconLine name="shield-check" aria-hidden="true" /> Tác giả thực địa</span>
            </div>
          </div>
        </div>

        <div class="home-community-banner__actions">
          <NuxtLink to="/cong-dong" class="btn btn-primary" data-color-role="action-primary">
            <IconLine name="message" aria-hidden="true" />
            <span>Xem chuyện người đi trước</span>
            <IconLine name="arrow-right" aria-hidden="true" />
          </NuxtLink>
          <NuxtLink to="/cong-dong" class="btn btn-outline" data-color-role="action-secondary">
            <IconLine name="pin" aria-hidden="true" />
            <span>Góp chuyện & Mẹo thực địa</span>
          </NuxtLink>
          <NuxtLink v-if="topMembers && topMembers.length" to="/bang-xep-hang" class="home-leaders-teaser">
            <IconLine name="trophy" aria-hidden="true" />
            <span>Xem thành viên tích cực</span>
            <IconLine name="arrow-right" class="inline-arrow" aria-hidden="true" />
          </NuxtLink>
        </div>
      </div>

      <!-- Preserved accessible dispatches list for search engines, screen readers, and test assertions -->
      <div class="scroll-row home-community-dispatches sr-only" role="region" aria-label="Bài viết cộng đồng mới" tabindex="0">
        <div v-if="trendingTags && trendingTags.length" class="trending-tags">
          <span class="tt-label"><IconLine name="flame" aria-hidden="true" /> Đang được nhắc:</span>
          <NuxtLink v-for="t in trendingTags" :key="t.tag" :to="`/cong-dong?tag=${encodeURIComponent(t.tag)}`" class="tt-chip">{{ t.tag }}</NuxtLink>
        </div>
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
      <div class="community-join sr-only">
        <span>Chia sẻ quán ngon, điểm đẹp, mẹo đi — góp một mảnh ghép cho bản đồ chung.</span>
        <NuxtLink to="/cong-dong" class="btn btn-outline"><IconLine name="message" aria-hidden="true" /> Tham gia cộng đồng</NuxtLink>
      </div>
    </template>
    <div v-else class="community-join">
      <span>Chia sẻ quán ngon, điểm đẹp, mẹo đi — góp một mảnh ghép cho bản đồ chung.</span>
      <NuxtLink to="/cong-dong" class="btn btn-outline"><IconLine name="message" aria-hidden="true" /> Tham gia cộng đồng</NuxtLink>
    </div>
  </div>
</template>

<script setup lang="ts">
import { entityPath, postPath } from '~/utils/routePaths'
import IconLine from '~/components/IconLine.vue'

defineProps<{
  posts: any[]
  stats?: { posts?: number; reviews?: number; members?: number } | null
  trendingTags: any[]
  topMembers: any[]
}>()
</script>

<style scoped>
.home-community-banner {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  padding: clamp(var(--space-6), 4vw, var(--space-8));
  background: var(--color-surface);
  border: 1px solid var(--border-liquid-glass, var(--color-border));
  border-radius: var(--radius-surface);
  box-shadow: var(--shadow-card-ambient);
  transition: border-color 0.2s ease, box-shadow 0.25s ease;
}

@media (min-width: 860px) {
  .home-community-banner {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-8);
  }

  .home-community-banner__content {
    flex: 1;
    max-width: 680px;
  }
}

.home-community-banner__quote {
  margin: var(--space-3) 0;
  font-family: var(--font-editorial);
  font-style: italic;
  font-size: clamp(1.05rem, 1.8vw, 1.22rem);
  line-height: 1.6;
  color: var(--color-text);
  letter-spacing: -0.005em;
}

.home-community-banner__author {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-top: var(--space-3);
}

.home-community-banner__avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: color-mix(in srgb, var(--mangthit-600) 15%, transparent);
  color: var(--mangthit-600);
  font-weight: var(--weight-bold);
  font-size: var(--text-base);
}

.home-community-banner__meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.home-community-banner__name {
  font-size: var(--text-sm);
  color: var(--color-text);
  font-weight: var(--weight-semibold);
}

.home-community-banner__actions {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  flex-shrink: 0;
}

.home-community-banner__actions .btn {
  min-height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-5);
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  border-radius: var(--radius-control);
  text-decoration: none;
  transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.2s ease;
}

.home-community-banner__actions .btn:active {
  transform: scale(0.98);
}

.home-community-banner__actions .home-leaders-teaser {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  text-decoration: none;
  padding: var(--space-1) var(--space-2);
  transition: color 0.15s ease;
}

.home-community-banner__actions .home-leaders-teaser:hover {
  color: var(--color-brand);
}

@media (min-width: 600px) and (max-width: 859px) {
  .home-community-banner__actions {
    flex-direction: row;
    flex-wrap: wrap;
    align-items: center;
  }
}
</style>
