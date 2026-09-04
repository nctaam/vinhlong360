<template>
  <aside class="threads-sidebar">
    <div class="sidebar-card sidebar-about reveal">
      <p class="sidebar-kicker">Đôi lời</p>
      <h2 class="sediment-head">Cộng đồng vinhlong360</h2>
      <p>Nơi chia sẻ trải nghiệm du lịch, đánh giá đặc sản và kết nối với cộng đồng yêu Vĩnh Long.</p>
      <div class="sidebar-stats">
        <div class="sidebar-stat">
          <span class="stat-num">{{ feedStats.postCount }}</span>
          <span class="stat-label">bài viết</span>
        </div>
        <div class="sidebar-stat">
          <span class="stat-num">{{ feedStats.reviewCount }}</span>
          <span class="stat-label">đánh giá</span>
        </div>
      </div>
      <NuxtLink to="/huong-dan-thanh-vien" class="sidebar-more">Xem quy tắc cộng đồng <IconLine name="arrow-right" class="sidebar-more-arrow" /></NuxtLink>
    </div>

    <div v-if="recentMentions.length" class="sidebar-card reveal">
      <p class="sidebar-kicker">Đang được nhắc tới</p>
      <h2 class="sediment-head">Nhắc tới gần đây</h2>
      <ul class="mention-list">
        <li v-for="m in recentMentions" :key="m.entity_id">
          <NuxtLink :to="entityPath(m.entity_id)" class="mention-link">
            {{ m.entity_name }}<span class="mention-count">{{ m.count }} lượt kể</span>
          </NuxtLink>
        </li>
      </ul>
    </div>

    <div v-if="topMembers.length" class="sidebar-card reveal">
      <p class="sidebar-kicker">Bảng xếp hạng</p>
      <h2 class="sediment-head">Thành viên tích cực</h2>
      <ol class="leaderboard-list">
        <li v-for="(m, i) in topMembers" :key="m.id">
          <NuxtLink :to="userPath(m.username || m.id)" class="lb-row">
            <span class="lb-rank" :class="`lb-rank-${i + 1}`">{{ i + 1 }}</span>
            <span class="avatar lb-avatar">{{ (m.display_name || '?').charAt(0).toUpperCase() }}</span>
            <span class="lb-name">{{ m.display_name }}</span>
            <span class="lb-points">{{ m.points }}đ</span>
          </NuxtLink>
        </li>
      </ol>
      <NuxtLink to="/bang-xep-hang" class="sidebar-more">Xem bảng xếp hạng <IconLine name="arrow-right" class="sidebar-more-arrow" /></NuxtLink>
    </div>

    <div v-if="isLoggedIn && suggestedUsers.length" class="sidebar-card reveal">
      <p class="sidebar-kicker">Gợi ý kết bạn</p>
      <h2 class="sediment-head">Có thể bạn quan tâm</h2>
      <ul class="suggest-list">
        <li v-for="s in suggestedUsers" :key="s.id" class="suggest-row">
          <NuxtLink :to="userPath(s.username || s.id)" class="suggest-user">
            <span class="avatar suggest-avatar">{{ (s.display_name || '?').charAt(0).toUpperCase() }}</span>
            <span class="suggest-name">{{ s.display_name }}</span>
          </NuxtLink>
          <button type="button" class="btn btn-outline btn-sm suggest-follow" :disabled="s._following" @click="$emit('follow', s)">
            {{ s._following ? 'Đã theo dõi' : 'Theo dõi' }}
          </button>
        </li>
      </ul>
    </div>

    <div v-if="trendingTags.length" class="sidebar-card reveal">
      <p class="sidebar-kicker">Chủ đề đang bàn</p>
      <h2 class="sediment-head">Hashtag thịnh hành</h2>
      <div class="trending-tags">
        <NuxtLink
          v-for="t in trendingTags"
          :key="t.tag"
          :to="{ path: '/cong-dong', query: { tag: t.tag } }"
          class="trending-tag"
        >#{{ t.tag }}<span class="tt-count">{{ t.count }}</span></NuxtLink>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { entityPath, userPath } from '~/utils/routePaths'

defineProps<{
  feedStats: { postCount: string | number; reviewCount: string | number }
  recentMentions: Array<{ entity_id: string; entity_name: string; count: number }>
  topMembers: Array<{ id: string; display_name: string; points: number; username?: string }>
  suggestedUsers: any[]
  trendingTags: Array<{ tag: string; count: number }>
  isLoggedIn?: boolean | any
}>()

defineEmits<{
  (e: 'follow', user: any): void
}>()
</script>

<style scoped>
.threads-sidebar { position: sticky; top: 78px; display: flex; flex-direction: column; gap: var(--space-4); }
.sidebar-card {
  background: var(--card); border: .5px solid var(--line);
  border-radius: var(--radius-sheet); padding: var(--space-4);
  box-shadow: var(--shadow-xs);
  transition: transform .35s var(--ease-out-expo), box-shadow .35s var(--ease-out-expo), border-color .3s var(--ease-out);
}
.sidebar-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-md); border-color: var(--border, var(--ink)); }
.sidebar-card:focus-within { border-color: var(--border, var(--ink)); }
.sidebar-card h2 { margin: 0 0 var(--space-3); font-size: var(--text-sm); font-weight: var(--weight-bold); }
.sidebar-card p { margin: 0; font-size: var(--text-sm); color: var(--muted); line-height: var(--leading-relaxed); }
.sidebar-card p.sidebar-kicker {
  margin: 0 0 var(--space-1); font-family: var(--font-editorial); font-style: italic;
  font-weight: 600; font-size: var(--text-2xs); letter-spacing: var(--tracking-caps);
  text-transform: uppercase; color: var(--muted);
}

.sidebar-stats { display: flex; gap: var(--space-4); margin-top: var(--space-3); padding-top: var(--space-3); border-top: .5px solid var(--line); }
.sidebar-stat { display: flex; flex-direction: column; gap: 2px; padding: var(--space-2) var(--space-3); border-radius: var(--radius-control); transition: background .3s var(--ease-out); cursor: default; }
.sidebar-stat:hover { background: var(--overlay-subtle); }
.stat-num { font-size: var(--text-lg); font-weight: var(--weight-bold); color: var(--ink); font-variant-numeric: tabular-nums; transition: color .3s var(--ease-out); }
.sidebar-stat:hover .stat-num { color: var(--primary-fg); }
.stat-label { font-size: var(--text-xs); color: var(--muted); }

.sidebar-more { display: inline-flex; align-items: center; gap: var(--space-1); font-size: var(--text-sm); color: var(--primary-fg); text-decoration: none; }
.sidebar-more:hover { text-decoration: underline; }
.sidebar-more-arrow { display: inline-flex; transition: transform .3s var(--ease-out-expo); }
.sidebar-more:hover .sidebar-more-arrow { transform: translateX(3px); }

.mention-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: var(--space-1); }
.mention-link {
  display: flex; align-items: baseline; justify-content: space-between; gap: var(--space-2);
  padding: var(--space-1) var(--space-2); border-radius: var(--radius-surface);
  text-decoration: none; color: var(--ink); font-size: var(--text-sm); font-weight: 500;
  transition: background .2s var(--ease-out);
}
.mention-link:hover { background: var(--bg-alt); }
.mention-count { flex-shrink: 0; font-size: var(--text-2xs); color: var(--muted); white-space: nowrap; }
.dark .mention-link:hover { background: rgba(var(--white-rgb),.04); }

.leaderboard-list { list-style: none; padding: 0; margin: 0 0 var(--space-2); display: flex; flex-direction: column; gap: var(--space-1); }
.lb-row { display: flex; align-items: center; gap: var(--space-2); padding: var(--space-1) var(--space-2); border-radius: var(--radius-surface); text-decoration: none; color: var(--ink); transition: background .2s var(--ease-out); }
.lb-row:hover { background: var(--bg-alt); }
.lb-rank { flex-shrink: 0; width: 18px; text-align: center; font-size: var(--text-xs); font-weight: var(--weight-bold); color: var(--muted); }
.lb-rank-1, .lb-rank-2, .lb-rank-3 {
  display: inline-flex; align-items: center; justify-content: center;
  width: 20px; height: 20px; border-radius: 50%;
  font-size: var(--text-2xs); color: var(--medal-ink);
}
.lb-rank-1 { background: var(--medal-gold); }
.lb-rank-2 { background: var(--medal-silver); }
.lb-rank-3 { background: var(--medal-bronze); }
.lb-avatar { width: 26px; height: 26px; display: inline-flex; align-items: center; justify-content: center; border-radius: 50%; background: var(--primary); color: var(--primary-fg, var(--white)); font-size: var(--text-2xs); font-weight: var(--weight-semibold); flex-shrink: 0; }
.lb-name { flex: 1; min-width: 0; font-size: var(--text-sm); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.lb-points { flex-shrink: 0; font-size: var(--text-xs); font-weight: var(--weight-semibold); color: var(--primary-fg); }

.suggest-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: var(--space-2); }
.suggest-row { display: flex; align-items: center; gap: var(--space-2); }
.suggest-user { display: flex; align-items: center; gap: var(--space-2); flex: 1; min-width: 0; text-decoration: none; color: var(--ink); }
.suggest-avatar { width: 30px; height: 30px; display: inline-flex; align-items: center; justify-content: center; border-radius: 50%; background: var(--primary); color: var(--primary-fg, var(--white)); font-size: var(--text-xs); font-weight: var(--weight-semibold); flex-shrink: 0; }
.suggest-name { font-size: var(--text-sm); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.suggest-follow { flex-shrink: 0; padding: .2rem .6rem; }

.trending-tags { display: flex; flex-wrap: wrap; gap: var(--space-2); }
.trending-tag { display: inline-flex; align-items: center; gap: .35rem; padding: .25rem .6rem; background: var(--bg-alt); border: .5px solid var(--line); border-radius: var(--radius-full); font-size: var(--text-sm); color: var(--primary-fg); text-decoration: none; transition: border-color .25s var(--ease-out), background .25s var(--ease-out); }
.trending-tag:hover { border-color: var(--primary-fg); background: rgba(var(--primary-rgb), .06); }
.tt-count { font-size: var(--text-xs); color: var(--muted); }
</style>
