<template>
  <section class="page threads-page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Cộng đồng' }]" />

    <!-- Social proof hero -->
    <section class="catalog-hero cat-community" aria-label="Cộng đồng vinhlong360">
      <div class="catalog-hero-inner">
        <span class="catalog-hero-icon" aria-hidden="true">💬</span>
        <div>
          <h1>{{ pc('hero_title') }}</h1>
          <p>Chia sẻ trải nghiệm, đánh giá đặc sản và kết nối với cộng đồng yêu miền Tây.</p>
        </div>
      </div>
      <div v-if="communityStats" class="catalog-stats">
        <div class="stat-item">
          <CountUp :value="communityStats.posts" class="stat-num" />
          <span class="stat-label">bài viết</span>
        </div>
        <div class="stat-item">
          <CountUp :value="communityStats.reviews" class="stat-num" />
          <span class="stat-label">đánh giá</span>
        </div>
        <div class="stat-item">
          <CountUp :value="communityStats.members" class="stat-num" />
          <span class="stat-label">thành viên</span>
        </div>
      </div>
    </section>

    <div class="threads-layout">
      <div class="threads-feed">

        <!-- Report entity (if from ?report=id) -->
        <div v-if="reportEntityId" class="report-entity-card">
          <div>
            <p class="report-kicker">Báo sai dữ liệu</p>
            <h2>{{ reportEntity?.name || reportEntityId }}</h2>
            <p>{{ isLoggedIn ? 'Mô tả ngắn điểm sai để admin kiểm tra.' : 'Đăng nhập để gửi báo cáo.' }}</p>
          </div>
          <div v-if="isLoggedIn" class="report-form-inline">
            <div class="report-reasons">
              <button type="button"
                v-for="reason in reportReasons"
                :key="reason"
                :class="['chip', { active: reportReason === reason }]"
                :aria-pressed="reportReason === reason"
                @click="reportReason = reason"
              >{{ reason }}</button>
            </div>
            <textarea
              v-model="reportReason"
              class="textarea"
              rows="3"
              placeholder="Ví dụ: địa chỉ sai, thiếu nguồn, tọa độ không đúng…"
              aria-label="Mô tả báo cáo"
            ></textarea>
            <button type="button" class="btn btn-primary" :disabled="reportSubmitting || reportReason.trim().length < 5" @click="submitEntityReport">
              {{ reportSubmitting ? 'Đang gửi…' : 'Gửi báo cáo' }}
            </button>
          </div>
        </div>

        <!-- Create post (Threads style) -->
        <div v-if="isLoggedIn && !ugcUnavailable" id="compose" ref="composeEl" class="threads-compose" role="form" aria-label="Viết bài mới">
          <div class="compose-left">
            <span class="avatar thread-avatar">{{ userInitial }}</span>
          </div>
          <div class="compose-right">
            <div class="post-type-selector">
              <button type="button"
                v-for="pt in postTypes"
                :key="pt.value"
                :class="['chip chip-sm', { active: newType === pt.value }]"
                :aria-pressed="newType === pt.value"
                @click="newType = pt.value"
              >{{ pt.label }}</button>
            </div>

            <div v-if="quotingPost" class="quote-preview">
              <div class="quote-preview-body">
                <span class="qp-head">✍️ Trích dẫn <strong>{{ quotingPost.author || quotingPost.display_name || 'Người dùng' }}</strong></span>
                <span class="qp-content">{{ quotingPost.content || '(bài viết)' }}</span>
              </div>
              <button type="button" class="qp-remove" aria-label="Bỏ trích dẫn" @click="cancelQuote">&times;</button>
            </div>

            <div class="compose-mention-wrap">
              <textarea
                ref="composeInputEl"
                v-model="newContent"
                class="compose-input"
                :placeholder="typePlaceholder"
                :maxlength="MAX_CHARS"
                rows="2"
                aria-label="Nội dung bài viết (gõ @ để nhắc người dùng hoặc địa điểm)"
                @input="onComposerInput"
                @keydown="onComposerKeydown"
              ></textarea>
              <ul v-if="mentionOpen && mentionResults.length" class="mention-menu" role="listbox" aria-label="Gợi ý @nhắc">
                <li
                  v-for="(m, mi) in mentionResults"
                  :key="m.type + m.id"
                  :class="['mention-item', { active: mi === mentionActive }]"
                  role="option"
                  :aria-selected="mi === mentionActive"
                  @mousedown.prevent="pickMention(m)"
                >
                  <span class="mention-ic" aria-hidden="true">{{ m.type === 'user' ? '👤' : '📍' }}</span>
                  <span class="mention-label">{{ m.label }}</span>
                  <span class="mention-sub">{{ m.sub }}</span>
                </li>
              </ul>
            </div>

            <div v-if="previewImages.length" class="img-preview-row">
              <div v-for="(src, i) in previewImages" :key="i" class="img-preview-item">
                <img :src="src" :alt="`Ảnh đính kèm ${i + 1}`" width="120" height="120" loading="lazy" decoding="async" @error="(e: Event) => ((e.target as HTMLImageElement).style.opacity = '.15')" />
                <button type="button" class="remove" aria-label="Xóa ảnh" @click="removeImage(i)">&times;</button>
              </div>
            </div>

            <div v-if="!quotingPost" class="schedule-option">
              <label class="schedule-toggle">
                <input type="checkbox" v-model="schedulePost" class="cd-toggle" />
                <span>Lên lịch đăng bài</span>
              </label>
              <div v-if="schedulePost" class="schedule-picker">
                <input type="datetime-local" v-model="scheduledAt" class="cd-input" :min="minScheduleDate" required aria-label="Thời gian đăng bài" />
                <span class="cd-hint">Bài sẽ tự động đăng vào thời gian này.</span>
              </div>
            </div>

            <div class="compose-footer">
              <div class="compose-footer-left">
                <label class="compose-attach" title="Thêm ảnh">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="m21 15-5-5L5 21"/></svg>
                  <input
                    type="file"
                    accept="image/*"
                    multiple
                    class="sr-only"
                    aria-label="Thêm ảnh"
                    @change="onFileSelect"
                  />
                </label>
                <span v-if="newContent.length > 0" :class="['char-count', { warn: charRatio > .8, full: charRatio >= 1 }]">
                  {{ newContent.length }}/{{ MAX_CHARS }}
                </span>
              </div>
              <button type="button" class="btn btn-primary btn-sm" :disabled="!canSubmit || posting || (schedulePost && !scheduledAt)" @click="submitPost">
                {{ posting ? (schedulePost ? 'Đang lên lịch…' : 'Đang đăng…') : (schedulePost ? 'Lên lịch' : 'Đăng') }}
              </button>
            </div>
          </div>
        </div>

        <div v-else-if="!ugcUnavailable" class="threads-compose-guest">
          <div class="guest-avatar">
            <span class="avatar thread-avatar guest">?</span>
          </div>
          <div class="guest-content">
            <p>Có trải nghiệm muốn chia sẻ?</p>
            <button type="button" class="btn btn-outline btn-sm" @click="openAuth()">Đăng nhập</button>
          </div>
        </div>

        <!-- Bài đã lên lịch -->
        <details v-if="isLoggedIn && scheduledPosts.length" class="scheduled-section">
          <summary class="scheduled-summary">📅 Bài đã lên lịch ({{ scheduledPosts.length }})</summary>
          <div class="scheduled-list">
            <div v-for="sp in scheduledPosts" :key="sp.id" class="scheduled-item">
              <p>{{ sp.content?.slice(0, 100) }}{{ (sp.content?.length || 0) > 100 ? '...' : '' }}</p>
              <div class="scheduled-meta">
                <time :datetime="sp.scheduled_at">{{ new Date(sp.scheduled_at).toLocaleString('vi-VN') }}</time>
                <button type="button" class="btn btn-ghost btn-sm scheduled-cancel" @click="cancelScheduled(sp.id)">Hủy</button>
              </div>
            </div>
          </div>
        </details>

        <!-- Tìm bài viết -->
        <div v-if="!ugcUnavailable" class="community-search" role="search">
          <svg class="cs-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg>
          <input
            v-model="searchInput"
            class="cs-input"
            type="search"
            enterkeyhint="search"
            maxlength="100"
            placeholder="Tìm bài viết trong cộng đồng…"
            aria-label="Tìm bài viết trong cộng đồng"
            @keyup.enter="runSearch"
          />
          <button v-if="searchMode" type="button" class="cs-clear" aria-label="Xoá tìm kiếm" @click="clearSearch">&times;</button>
          <button type="button" class="btn btn-primary btn-sm cs-go" @click="runSearch">Tìm</button>
        </div>

        <!-- Đang xem kết quả tìm -->
        <div v-if="searchMode" class="tag-banner" role="status">
          <span><strong>{{ displayPosts.length }}</strong> kết quả cho <strong>&ldquo;{{ searchQuery }}&rdquo;</strong></span>
          <button type="button" class="tag-clear" @click="clearSearch">✕ Bỏ tìm</button>
        </div>

        <!-- Người dùng tìm thấy -->
        <div v-if="searchUsers.length && searchQuery" class="search-users-section">
          <h3 class="section-label">Người dùng</h3>
          <div class="search-users-grid">
            <NuxtLink v-for="u in searchUsers" :key="u.id" :to="userPath(u.username || u.id)" class="search-user-card card">
              <AvatarPlaceholder :initial="(u.display_name || '?').charAt(0)" :src="u.avatar_url" :size="40" />
              <div class="suc-info">
                <strong>{{ u.display_name }}</strong>
                <span class="suc-meta">{{ u.post_count }} bài viết</span>
              </div>
            </NuxtLink>
          </div>
        </div>

        <!-- Main tabs -->
        <div v-if="!searchMode && !ugcUnavailable" class="threads-filter-bar">
          <div class="threads-filter" role="tablist" aria-label="Bộ lọc bảng tin" @keydown="onFeedTabKeydown">
            <button
              v-for="tab in visibleFeedTabs"
              :key="tab.key"
              type="button"
              role="tab"
              :class="['threads-tab', { active: activeTab === tab.key }]"
              :aria-selected="activeTab === tab.key"
              :tabindex="activeTab === tab.key ? 0 : -1"
              :data-tab="tab.key"
              @click="setTab(tab.key)"
            >
              <svg v-if="tab.key === 'bookmarks'" class="icon-inline" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/></svg>{{ tab.label }}
            </button>
          </div>
          <button type="button" class="threads-refresh" :disabled="loading" aria-label="Tải lại bảng tin" @click="refreshFeed">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" :class="{ spinning: loading }"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
          </button>
        </div>

        <!-- Mobile discovery strip (sidebar content for small screens) -->
        <div v-if="(topMembers.length || trendingTags.length) && !searchMode" class="mobile-discovery">
          <div v-if="trendingTags.length" class="md-section">
            <span class="md-label">Thịnh hành</span>
            <div class="md-scroll">
              <NuxtLink
                v-for="t in trendingTags.slice(0, 6)"
                :key="t.tag"
                :to="{ path: '/cong-dong', query: { tag: t.tag } }"
                class="md-tag"
              >#{{ t.tag }}</NuxtLink>
            </div>
          </div>
          <div v-if="topMembers.length" class="md-section">
            <span class="md-label">Top</span>
            <div class="md-scroll">
              <NuxtLink
                v-for="m in topMembers.slice(0, 5)"
                :key="m.id"
                :to="userPath(m.username || m.id)"
                class="md-member"
              >
                <span class="avatar avatar-xs">{{ (m.display_name || '?').charAt(0).toUpperCase() }}</span>
                <span class="md-name">{{ m.display_name }}</span>
              </NuxtLink>
            </div>
          </div>
        </div>

        <!-- Đang lọc theo hashtag -->
        <div v-if="activeTag" class="tag-banner" role="status">
          <span>Đang xem <strong>#{{ activeTag }}</strong></span>
          <button type="button" class="tag-clear" @click="clearTag">✕ Bỏ lọc</button>
        </div>

        <!-- Post type filter (only for feed tabs, not bookmarks/search) -->
        <div v-if="activeTab !== 'bookmarks' && !searchMode" class="type-filter-row" role="tablist" aria-label="Lọc loại bài viết" @keydown="onTypeFilterKeydown">
          <button
            v-for="pt in filterTypeOptions"
            :key="pt.value || 'all'"
            type="button"
            role="tab"
            :class="['chip chip-filter', { active: filterType === pt.value }]"
            :aria-selected="filterType === pt.value"
            :tabindex="filterType === pt.value ? 0 : -1"
            :data-type="pt.value || 'all'"
            @click="setFilterType(pt.value)"
          >{{ pt.label }}</button>
        </div>

        <!-- Posts -->
        <SkeletonGrid v-if="(loading || bookmarksLoading || searchLoading) && !displayPosts.length" :count="3" />

        <TransitionGroup name="post-list" tag="div" class="post-list-container">
          <PostCard
            v-for="post in displayPosts"
            :key="post.id"
            :post="post"
            :has-replies="(post.comments_count || 0) > 0"
            @like="toggleLike"
            @comment="goToPost"
            @bookmark="toggleBookmark"
            @report="reportPost"
            @repost="repostPost"
            @quote="startQuote"
            @edit="(id) => navigateTo(`${postPath(id)}?edit=1`)"
            @delete="deletePost"
          />
        </TransitionGroup>

        <EmptyState
          v-if="searchMode && !searchResults.length && !searchLoading"
          icon="🔍" title="Không tìm thấy bài viết"
          :message="`Không có bài viết nào khớp “${searchQuery}”.`"
        />

        <EmptyState
          v-else-if="ugcUnavailable"
          icon="🚧" title="Cộng đồng sắp mở"
          message="Tính năng cộng đồng đang được hoàn thiện. Bạn sẽ sớm có thể chia sẻ trải nghiệm, đánh giá địa điểm và kết nối với những người yêu miền Tây."
        />

        <div v-else-if="feedError && !displayPosts.length" class="feed-error">
          <p>Không thể tải bảng tin.</p>
          <button type="button" class="btn btn-outline btn-sm" @click="fetchFeed(true)">Thử lại</button>
        </div>

        <EmptyState
          v-else-if="activeTab === 'bookmarks' && !bookmarks.length && !bookmarksLoading"
          icon="🔖" title="Chưa lưu bài viết nào"
          message="Nhấn biểu tượng bookmark trên bài viết để lưu lại và xem sau."
        />

        <EmptyState
          v-else-if="activeTab === 'following' && !posts.length && !loading && !feedError"
          icon="👥" title="Chưa có bài từ người bạn theo dõi"
          message="Theo dõi người dùng và địa điểm để xem bài viết của họ ở đây."
          hint="Mở hồ sơ người dùng hoặc trang địa điểm rồi nhấn “Theo dõi”."
        >
          <template #actions>
            <div v-if="suggestedUsers.length" class="onboard-follows">
              <p class="onboard-title">Gợi ý theo dõi</p>
              <div class="onboard-list">
                <div v-for="s in suggestedUsers.slice(0, 5)" :key="s.id" class="onboard-user">
                  <NuxtLink :to="userPath(s.username || s.id)" class="onboard-info">
                    <span class="avatar avatar-sm">{{ (s.display_name || '?').charAt(0).toUpperCase() }}</span>
                    <span class="onboard-name">{{ s.display_name }}</span>
                  </NuxtLink>
                  <button type="button" class="btn btn-primary btn-xs" :disabled="s._following" @click="followSuggested(s)">
                    {{ s._following ? 'Đã theo dõi' : 'Theo dõi' }}
                  </button>
                </div>
              </div>
            </div>
            <NuxtLink to="/tim-kiem" class="btn btn-outline btn-sm">Tìm người để theo dõi</NuxtLink>
          </template>
        </EmptyState>

        <EmptyState
          v-else-if="activeTab !== 'bookmarks' && activeTab !== 'following' && !posts.length && !loading && !feedError"
          icon="💬" title="Cộng đồng đang chờ bạn"
          message="Chưa có bài viết nào. Hãy là người đầu tiên chia sẻ!"
          hint="Chia sẻ ảnh chuyến đi, đặt câu hỏi, hay để lại đánh giá của bạn."
        >
          <template v-if="isLoggedIn" #actions>
            <button type="button" class="btn btn-primary btn-sm" @click="focusComposer">Viết bài đầu tiên</button>
          </template>
          <template v-else #actions>
            <button type="button" class="btn btn-primary btn-sm" @click="openAuth()">Đăng nhập để chia sẻ</button>
          </template>
        </EmptyState>

        <!-- Cuộn vô hạn: observer tự nạp khi sentinel vào tầm; nút là fallback (no-JS/observer fail) -->
        <div ref="loadSentinel" class="load-sentinel" aria-hidden="true"></div>
        <button type="button" v-if="canLoadMore" class="btn btn-ghost threads-load-more" @click="loadMore">
          Xem thêm
        </button>
        <div v-if="(loading && posts.length) || bookmarksLoading || (searchLoading && searchResults.length)" class="feed-loading" role="status" aria-live="polite" aria-label="Đang tải bài viết"><div class="spinner"></div></div>
      </div>

      <aside class="threads-sidebar">
        <div class="sidebar-card sidebar-about">
          <h2>Cộng đồng vinhlong360</h2>
          <p>Nơi chia sẻ trải nghiệm du lịch, đánh giá đặc sản và kết nối với cộng đồng yêu miền Tây.</p>
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
        </div>

        <div v-if="topMembers.length" class="sidebar-card">
          <h2>Thành viên tích cực</h2>
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
          <NuxtLink to="/bang-xep-hang" class="sidebar-more">Xem bảng xếp hạng →</NuxtLink>
        </div>

        <div v-if="isLoggedIn && suggestedUsers.length" class="sidebar-card">
          <h2>Có thể bạn quan tâm</h2>
          <ul class="suggest-list">
            <li v-for="s in suggestedUsers" :key="s.id" class="suggest-row">
              <NuxtLink :to="userPath(s.username || s.id)" class="suggest-user">
                <span class="avatar suggest-avatar">{{ (s.display_name || '?').charAt(0).toUpperCase() }}</span>
                <span class="suggest-name">{{ s.display_name }}</span>
              </NuxtLink>
              <button type="button" class="btn btn-outline btn-sm suggest-follow" :disabled="s._following" @click="followSuggested(s)">
                {{ s._following ? 'Đã theo dõi' : 'Theo dõi' }}
              </button>
            </li>
          </ul>
        </div>

        <div v-if="trendingTags.length" class="sidebar-card">
          <h2>Hashtag thịnh hành</h2>
          <div class="trending-tags">
            <NuxtLink
              v-for="t in trendingTags"
              :key="t.tag"
              :to="{ path: '/cong-dong', query: { tag: t.tag } }"
              class="trending-tag"
            >#{{ t.tag }}<span class="tt-count">{{ t.count }}</span></NuxtLink>
          </div>
        </div>

        <div class="sidebar-card reveal">
          <h2>Cách tham gia</h2>
          <ul class="sidebar-list">
            <li>
              <span class="sl-icon">📸</span>
              <div><strong>Chia sẻ</strong><br><span class="sl-desc">Kể lại chuyến đi, khám phá của bạn</span></div>
            </li>
            <li>
              <span class="sl-icon">⭐</span>
              <div><strong>Đánh giá</strong><br><span class="sl-desc">Chấm điểm địa điểm, dịch vụ đã trải nghiệm</span></div>
            </li>
            <li>
              <span class="sl-icon">❓</span>
              <div><strong>Hỏi đáp</strong><br><span class="sl-desc">Đặt câu hỏi về 3 tỉnh VL–BT–TV</span></div>
            </li>
            <li>
              <span class="sl-icon">👍</span>
              <div><strong>Gợi ý</strong><br><span class="sl-desc">Giới thiệu nơi hay, món ngon cho mọi người</span></div>
            </li>
          </ul>
        </div>

        <div class="sidebar-card sidebar-rules">
          <h2>Quy tắc cộng đồng</h2>
          <ol class="sidebar-rules-list">
            <li>Tôn trọng lẫn nhau</li>
            <li>Chia sẻ thông tin chính xác</li>
            <li>Không quảng cáo, spam</li>
            <li>Bảo vệ quyền riêng tư</li>
          </ol>
        </div>
      </aside>
    </div>

    <!-- Save momentum cue — keeps bookmarking from dead-ending -->
    <Transition name="momentum-fade">
      <div v-if="showBookmarkMomentum" class="bookmark-momentum" role="status">
        <span class="bm-icon" aria-hidden="true">🔖</span>
        <button type="button" class="bm-link" @click="setTab('bookmarks'); bookmarkBannerDismissed = true">Xem mục đã lưu</button>
        <button type="button" class="bm-dismiss" aria-label="Đóng" @click="bookmarkBannerDismissed = true">&times;</button>
      </div>
    </Transition>

    <!-- Scroll to top — uses global ScrollToTop from layout -->
  </section>
</template>

<script setup lang="ts">
import type { Post, Entity } from '~/types'
useReveal()
const { f: pc } = usePageContent('cong_dong')

const MAX_CHARS = 500

const { isLoggedIn, authHeaders, user, handleSessionExpired } = useAuth()
const { openAuth } = useAuthModal()
const { repost } = useRepost()
function repostPost(postId: string) {
  repost(postId, () => { activeTab.value = 'latest'; fetchFeed(true) })
}
const route = useRoute()
const router = useRouter()

const { show: showToast } = useToast()
const { trackEvent } = useUserEvents()
const postTypes = [
  { value: 'share', label: '📸 Chia sẻ' },
  { value: 'review', label: '⭐ Đánh giá' },
  { value: 'question', label: '❓ Hỏi đáp' },
  { value: 'recommend', label: '👍 Gợi ý' },
]
type FeedTab = 'latest' | 'trending' | 'following' | 'bookmarks'
type PostTypeValue = '' | 'share' | 'review' | 'question' | 'recommend'

const feedTabs: Array<{ key: FeedTab; label: string; requiresAuth?: boolean }> = [
  { key: 'latest', label: 'Mới nhất' },
  { key: 'trending', label: 'Nổi bật' },
  { key: 'following', label: 'Đang theo dõi', requiresAuth: true },
  { key: 'bookmarks', label: 'Đã lưu', requiresAuth: true },
]
const privateFeedTabs = new Set<FeedTab>(['following', 'bookmarks'])
const postTypeValues = new Set(postTypes.map(pt => pt.value))

function firstQueryValue(value: unknown) {
  return Array.isArray(value) ? String(value[0] || '') : String(value || '')
}

function normalizeTagQuery(value: unknown) {
  return firstQueryValue(value).trim().replace(/^#/, '').toLowerCase()
}

const userInitial = computed(() => {
  const name = user.value?.display_name || user.value?.phone || '?'
  return name.charAt(0).toUpperCase()
})

// ── Tabs & filtering ──
const activeTab = ref<FeedTab>('latest')
const sort = computed(() => activeTab.value === 'trending' ? 'trending' : 'latest')
const filterType = ref<PostTypeValue>('')
const activeTag = ref(normalizeTagQuery(route.query.tag))
const visibleFeedTabs = computed(() => feedTabs.filter(tab => !tab.requiresAuth || isLoggedIn.value))
const filterTypeOptions = computed<Array<{ value: PostTypeValue; label: string }>>(() => [
  { value: '', label: 'Tất cả' },
  ...postTypes.map(pt => ({ value: pt.value as PostTypeValue, label: pt.label })),
])
const { syncToUrl: syncFeedFiltersToUrl } = useFilterUrl({ tab: activeTab, type: filterType }, { tab: 'latest', type: '' })

function isFeedTab(value: unknown): value is FeedTab {
  return typeof value === 'string' && feedTabs.some(tab => tab.key === value)
}
function isPrivateFeedTab(value: unknown) {
  return isFeedTab(value) && privateFeedTabs.has(value)
}
function normalizeFeedTab(value: unknown): FeedTab {
  if (!isFeedTab(value)) return 'latest'
  if (privateFeedTabs.has(value) && !isLoggedIn.value) return 'latest'
  return value
}
function normalizeFilterType(value: unknown): PostTypeValue {
  const next = typeof value === 'string' ? value : ''
  return (next === '' || postTypeValues.has(next)) ? next as PostTypeValue : ''
}
function normalizeCommunityRouteState() {
  const nextTab = normalizeFeedTab(activeTab.value)
  const nextType = activeTab.value === 'bookmarks' ? '' : normalizeFilterType(filterType.value)
  let changed = false
  if (nextTab !== activeTab.value) { activeTab.value = nextTab; changed = true }
  if (nextType !== filterType.value) { filterType.value = nextType; changed = true }
  if (changed) syncFeedFiltersToUrl()
}
normalizeCommunityRouteState()

watch(() => route.query.tag, (t) => {
  const newTag = normalizeTagQuery(t)
  if (newTag !== activeTag.value) { activeTag.value = newTag; fetchFeed(true) }
})
watch(() => route.query.q, () => applyRouteSearchQuery())
watch(() => route.query.compose, () => focusComposerFromRoute())
function clearTag() {
  activeTag.value = ''
  const { tag: _, ...rest } = route.query
  router.replace({ query: rest })
  fetchFeed(true)
}
const page = ref(1)
const posts = ref<Post[]>([])
const hasMore = ref(false)
const loading = ref(false)
const feedError = ref(false)
const ugcUnavailable = ref(false)
let feedAbort: AbortController | null = null
// ── Tìm bài viết cộng đồng ──
const searchInput = ref('')
const searchQuery = ref('')          // truy vấn đang áp dụng (rỗng = không ở chế-độ tìm)
const searchResults = ref<Post[]>([])
const searchPage = ref(1)
const searchHasMore = ref(false)
const searchLoading = ref(false)
const searchMode = computed(() => !!searchQuery.value)
const { saveDraft, loadDraft, clearDraft } = useDrafts()
const newContent = ref('')
const newType = ref('share')
const posting = ref(false)
const imageFiles = ref<File[]>([])
const previewImages = ref<string[]>([])
const charRatio = computed(() => newContent.value.length / MAX_CHARS)
const quotingPost = ref<Record<string, any> | null>(null)

// ── Lên lịch đăng bài ──
const schedulePost = ref(false)
const scheduledAt = ref('')
const minScheduleDate = computed(() => {
  const d = new Date()
  d.setMinutes(d.getMinutes() + 10)
  return d.toISOString().slice(0, 16)
})
const scheduledPosts = ref<any[]>([])

async function loadScheduledPosts() {
  if (!isLoggedIn.value) return
  try {
    const res = await $fetch<{ scheduled: any[] }>('/api/scheduled', { headers: authHeaders() })
    scheduledPosts.value = res.scheduled || []
  } catch { /* im lặng — mục lên lịch không quan trọng bằng bảng tin chính */ }
}

async function cancelScheduled(id: string) {
  try {
    await $fetch(`/api/scheduled/${encodePathId(id)}`, { method: 'DELETE', headers: authHeaders() })
    scheduledPosts.value = scheduledPosts.value.filter(s => s.id !== id)
    showToast('Đã hủy lịch đăng', 'success')
  } catch (e: unknown) {
    if (getStatusCode(e) === 401) { handleSessionExpired(); return }
    showToast('Không thể hủy lịch đăng', 'error')
  }
}

// ── Bookmarks ──
const bookmarks = ref<Post[]>([])
const bookmarksLoading = ref(false)
const bookmarksPage = ref(1)
const bookmarksHasMore = ref(false)
// Session momentum: after first save this session, surface a "view saved" cue
// so bookmarking has a next action instead of dead-ending.
const sessionBookmarked = ref(false)
const bookmarkBannerDismissed = ref(false)
const showBookmarkMomentum = computed(() =>
  sessionBookmarked.value && !bookmarkBannerDismissed.value && activeTab.value !== 'bookmarks'
)

type PostListResponse = {
  posts?: Post[]
  bookmarks?: Post[]
  has_more?: boolean
}
const { filterCommunityPosts, mergeCommunityPosts } = useCommunityPostFilters<Post>()

function extractPostArray(res: unknown, preferredKey: 'posts' | 'bookmarks' = 'posts') {
  const payload = res as PostListResponse | Post[] | null | undefined
  if (Array.isArray(payload)) return payload
  if (Array.isArray(payload?.[preferredKey])) return payload[preferredKey] || []
  if (Array.isArray((payload as PostListResponse | undefined)?.posts)) return (payload as PostListResponse).posts || []
  return []
}

function responseHasMore(res: unknown, rawPosts: Post[]) {
  const hasMoreValue = (res as PostListResponse | undefined)?.has_more
  return typeof hasMoreValue === 'boolean' ? hasMoreValue : rawPosts.length === 20
}

// ── Feed stats: số THẬT từ server (không phải đếm 20 bài đã tải) ──
const communityStats = ref<{ posts: number; reviews: number; members: number } | null>(null)
const feedStats = computed(() => ({
  postCount: communityStats.value?.posts ?? '—',
  reviewCount: communityStats.value?.reviews ?? '—',
}))
async function loadCommunityStats() {
  try { communityStats.value = await $fetch<{ posts: number; reviews: number; members: number }>('/api/community/stats' as string) } catch { /* giữ '—' */ }
}

// ── Hashtag thịnh hành (sidebar khám phá) ──
const trendingTags = ref<{ tag: string; count: number }[]>([])
async function loadTrendingTags() {
  try {
    const res = await $fetch<{ tags: { tag: string; count: number }[] }>('/api/community/trending-tags')
    trendingTags.value = res.tags || []
  } catch { /* ẩn card nếu lỗi */ }
}

// ── Bảng xếp hạng đóng góp (sidebar top 5) ──
const topMembers = ref<{ id: string; display_name: string; points: number; username?: string }[]>([])
async function loadLeaderboard() {
  try {
    const res = await $fetch<{ leaders: any[] }>('/api/community/leaderboard?limit=5')
    topMembers.value = res.leaders || []
  } catch { /* ẩn card nếu lỗi */ }
}

// ── Gợi ý người để theo dõi (logged-in) ──
const suggestedUsers = ref<any[]>([])
function normalizeSuggestedUsers(users: any[]) {
  const seen = new Set<string>()
  const selfId = String(user.value?.id || '')
  return users.filter((item) => {
    const id = String(item?.id || '')
    if (!id || id === selfId || seen.has(id) || item.is_following || item._following) return false
    seen.add(id)
    return true
  })
}
async function loadSuggested() {
  if (!isLoggedIn.value) { suggestedUsers.value = []; return }
  try {
    const res = await $fetch<{ users: any[] }>('/api/community/suggested-follows?limit=5', { headers: authHeaders() })
    suggestedUsers.value = normalizeSuggestedUsers(res.users || [])
  } catch (e: unknown) {
    if (getStatusCode(e) === 401) handleSessionExpired()
  }
}
async function followSuggested(s: any) {
  if (!isLoggedIn.value) { openAuth(); return }
  if (s._following) return
  s._following = true
  try {
    await $fetch(`/api/follow/user/${s.id}`, { method: 'POST', headers: authHeaders() })
    suggestedUsers.value = suggestedUsers.value.filter(item => item.id !== s.id)
    showToast(`Đã theo dõi ${s.display_name}`, 'success')
  } catch (e: unknown) {
    s._following = false
    if (getStatusCode(e) === 401) { handleSessionExpired(); return }
    showToast('Không thể theo dõi', 'error')
  }
}

// ── Display posts (with type filter) ──
const displayPosts = computed(() => {
  if (searchMode.value) return searchResults.value
  if (activeTab.value === 'bookmarks') return bookmarks.value
  if (!filterType.value) return posts.value
  return posts.value.filter(p => p.post_type === filterType.value)
})

const canLoadMore = computed(() => {
  if (searchMode.value) return searchHasMore.value && !searchLoading.value
  if (activeTab.value === 'bookmarks') return bookmarksHasMore.value && !bookmarksLoading.value
  return hasMore.value && !loading.value
})

// ── Report entity ──
const reportEntityId = computed(() => firstQueryValue(route.query.report).trim())
type ReportEntity = Entity & { quality?: Entity['quality'] & { has_source?: boolean } }
const reportEntity = ref<ReportEntity | null>(null)
const reportReason = ref('')
const reportSubmitting = ref(false)
const reportReasons = ['Thiếu nguồn xác minh', 'Tọa độ chưa đúng', 'Sai địa chỉ/khu vực', 'Nội dung cần cập nhật']

const typePlaceholder = computed(() => {
  const map: Record<string, string> = {
    share: 'Kể về trải nghiệm du lịch của bạn…',
    review: 'Đánh giá một địa điểm, sản phẩm…',
    question: 'Bạn muốn hỏi gì về miền Tây?',
    recommend: 'Gợi ý một địa điểm, món ăn…',
  }
  return map[newType.value] || map.share
})

const canSubmit = computed(() => {
  if (newContent.value.length > MAX_CHARS) return false
  if (quotingPost.value) return true   // rỗng = đăng lại, có chữ = trích dẫn
  return newContent.value.trim().length > 0
})

const loadSentinel = ref<HTMLElement | null>(null)
let loadObserver: IntersectionObserver | null = null
let suppressFilterFetch = false

// ── Composer focus (from empty-state CTA) ──
const composeEl = ref<HTMLElement | null>(null)
const composeInputEl = ref<HTMLTextAreaElement | null>(null)
function focusComposer() {
  const prefersReduced = typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  composeEl.value?.scrollIntoView({ behavior: prefersReduced ? 'auto' : 'smooth', block: 'center' })
  nextTick(() => composeInputEl.value?.focus())
}

// ── Trích dẫn (quote) ──
async function startQuote(postId: string) {
  if (!isLoggedIn.value) { openAuth(() => startQuote(postId)); return }
  let p: any = posts.value.find((x: any) => x.id === postId)
  if (!p) {
    try { const r = await $fetch<any>(`/api/posts/${encodePathId(postId)}`, { headers: authHeaders() }); p = r?.post } catch { /* post may be deleted */ }
  }
  quotingPost.value = p || { id: postId, content: '(Bài viết không khả dụng)' }
  schedulePost.value = false
  scheduledAt.value = ''
  activeTab.value = 'latest'
  focusComposer()
}
function cancelQuote() { quotingPost.value = null }

function autoGrow(e: Event) {
  const el = e.target as HTMLTextAreaElement
  el.style.height = 'auto'
  el.style.height = el.scrollHeight + 'px'
}

// ── @-mention: gõ @ để nhắc người dùng / địa điểm (composable chung) ──
const {
  mentionResults, mentionOpen, mentionActive,
  onInput: onMentionInput, pick: pickMention,
  onKeydown: onMentionKeydownComposer, closeMention, reset: resetMention, activeMentions,
} = useMentionAutocomplete(newContent, composeInputEl)

function onComposerKeydown(e: KeyboardEvent) {
  if (onMentionKeydownComposer(e)) return
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') { e.preventDefault(); submitPost() }
}

function onComposerInput(e: Event) {
  autoGrow(e)
  onMentionInput(e)
}

// Thu nhỏ ảnh trước khi gửi (max 1280px, JPEG q0.82) — base64 nhẹ đi nhiều lần (trước đây
// gửi full-size → payload có thể tới hàng chục MB).
function downscaleImage(file: File, maxDim = 1280, quality = 0.82): Promise<string> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file)
    const img = new Image()
    img.onload = () => {
      URL.revokeObjectURL(url)
      let { width, height } = img
      if (Math.max(width, height) > maxDim) {
        const s = maxDim / Math.max(width, height)
        width = Math.round(width * s); height = Math.round(height * s)
      }
      const canvas = document.createElement('canvas')
      canvas.width = width; canvas.height = height
      const ctx = canvas.getContext('2d')
      if (!ctx) return reject(new Error('no-ctx'))
      ctx.drawImage(img, 0, 0, width, height)
      const result = canvas.toDataURL('image/jpeg', quality)
      canvas.width = 0; canvas.height = 0
      resolve(result)
    }
    img.onerror = () => { URL.revokeObjectURL(url); reject(new Error('img-load')) }
    img.src = url
  })
}

async function onFileSelect(e: Event) {
  const input = e.target as HTMLInputElement
  if (!input.files) return
  const newFiles = Array.from(input.files).slice(0, 5 - imageFiles.value.length)
  for (const file of newFiles) {
    if (!file.type.startsWith('image/') || file.type === 'image/svg+xml') { showToast(`${file.name} không phải ảnh hợp lệ`, 'warning'); continue }
    if (file.size > 10 * 1024 * 1024) { showToast('Ảnh quá lớn (tối đa 10MB)', 'warning'); continue }
    try {
      const dataUrl = await downscaleImage(file)
      imageFiles.value.push(file)
      previewImages.value.push(dataUrl)
    } catch {
      showToast('Không thể đọc ảnh', 'error')
    }
  }
  input.value = ''
}

function removeImage(idx: number) {
  imageFiles.value.splice(idx, 1)
  previewImages.value.splice(idx, 1)
}

function focusFeedTab(tab: FeedTab) {
  if (typeof document === 'undefined') return
  nextTick(() => document.querySelector<HTMLElement>(`.threads-filter [data-tab="${tab}"]`)?.focus())
}

function focusTypeFilter(value: PostTypeValue) {
  if (typeof document === 'undefined') return
  const key = value || 'all'
  nextTick(() => document.querySelector<HTMLElement>(`.type-filter-row [data-type="${key}"]`)?.focus())
}

function nextIndex(current: number, total: number, key: string) {
  if (key === 'Home') return 0
  if (key === 'End') return total - 1
  if (key === 'ArrowRight' || key === 'ArrowDown') return (current + 1) % total
  if (key === 'ArrowLeft' || key === 'ArrowUp') return (current - 1 + total) % total
  return current
}

function onFeedTabKeydown(e: KeyboardEvent) {
  if (!['ArrowRight', 'ArrowLeft', 'ArrowDown', 'ArrowUp', 'Home', 'End'].includes(e.key)) return
  const tabs = visibleFeedTabs.value.map(tab => tab.key)
  if (!tabs.length) return
  e.preventDefault()
  const current = Math.max(0, tabs.indexOf(normalizeFeedTab(activeTab.value)))
  const tab = tabs[nextIndex(current, tabs.length, e.key)] || 'latest'
  setTab(tab)
  focusFeedTab(tab)
}

function onTypeFilterKeydown(e: KeyboardEvent) {
  if (!['ArrowRight', 'ArrowLeft', 'ArrowDown', 'ArrowUp', 'Home', 'End'].includes(e.key)) return
  const options = filterTypeOptions.value.map(option => option.value)
  e.preventDefault()
  const current = Math.max(0, options.indexOf(normalizeFilterType(filterType.value)))
  const value = options[nextIndex(current, options.length, e.key)] || ''
  setFilterType(value)
  focusTypeFilter(value)
}

function setFilterType(value: PostTypeValue) {
  filterType.value = normalizeFilterType(value)
}

function setTab(tab: FeedTab) {
  if (isPrivateFeedTab(tab) && !isLoggedIn.value) {
    activeTab.value = 'latest'
    openAuth()
    return
  }
  const nextTab = normalizeFeedTab(tab)
  if (searchMode.value) clearSearch()
  if (activeTab.value === nextTab) return
  feedAbort?.abort()
  activeTab.value = nextTab
  suppressFilterFetch = true
  filterType.value = ''
  nextTick(() => { suppressFilterFetch = false })
  if (nextTab === 'bookmarks') {
    if (!bookmarks.value.length) fetchBookmarks(true)
  } else {
    fetchFeed(true)
  }
  nextTick(() => {
    if (typeof window !== 'undefined') window.scrollTo({ top: 0, behavior: 'smooth' })
  })
}

async function fetchFeed(reset = false) {
  normalizeCommunityRouteState()
  if (activeTab.value === 'bookmarks') { await fetchBookmarks(reset); return }
  if (reset) { page.value = 1; posts.value = []; feedError.value = false }
  feedAbort?.abort()
  feedAbort = new AbortController()
  loading.value = true
  try {
    const url = activeTab.value === 'following'
      ? `/api/feed/following?page=${page.value}&limit=20`
      : (() => {
          const params = new URLSearchParams({ page: String(page.value), limit: '20', sort: sort.value })
          if (filterType.value) params.set('post_type', filterType.value)
          if (activeTag.value) params.set('tag', activeTag.value)
          return `/api/feed?${params}`
        })()
    const res = await $fetch<PostListResponse>(url, {
      headers: authHeaders(),
      signal: feedAbort.signal,
    })
    const rawPosts = extractPostArray(res)
    const newPosts = filterCommunityPosts(rawPosts)
    posts.value = reset ? newPosts : mergeCommunityPosts(posts.value, newPosts)
    hasMore.value = responseHasMore(res, rawPosts)
  } catch (e: unknown) {
    if (e instanceof DOMException && e.name === 'AbortError') return
    const status = (e as any)?.response?.status || (e as any)?.status || (e as any)?.statusCode
    if (status === 503) {
      ugcUnavailable.value = true
      return
    }
    if (reset && !posts.value.length) feedError.value = true
    showToast(reset ? 'Không thể tải bảng tin' : 'Không thể tải thêm', 'error')
  } finally {
    loading.value = false
  }
}

async function fetchBookmarks(reset = false) {
  if (reset) { bookmarksPage.value = 1; bookmarks.value = [] }
  bookmarksLoading.value = true
  try {
    const res = await $fetch<PostListResponse>(`/api/me/bookmarks?page=${bookmarksPage.value}&limit=20`, {
      headers: authHeaders(),
    })
    const rawPosts = extractPostArray(res, 'bookmarks')
    const newPosts = filterCommunityPosts(rawPosts)
    bookmarks.value = reset ? newPosts : mergeCommunityPosts(bookmarks.value, newPosts)
    bookmarksHasMore.value = responseHasMore(res, rawPosts)
  } catch (e: unknown) {
    if (getStatusCode(e) === 401) { handleSessionExpired(); return }
    showToast('Không thể tải bài viết đã lưu', 'error')
  } finally {
    bookmarksLoading.value = false
  }
}

function refreshFeed() {
  if (searchMode.value) { fetchSearch(true); return }
  if (activeTab.value === 'bookmarks') { fetchBookmarks(true); return }
  fetchFeed(true)
}

function loadMore() {
  if (loading.value || searchLoading.value || bookmarksLoading.value) return
  if (searchMode.value) {
    searchPage.value++
    fetchSearch()
  } else if (activeTab.value === 'bookmarks') {
    bookmarksPage.value++
    fetchBookmarks()
  } else {
    page.value++
    fetchFeed()
  }
}

// ── Tìm bài viết ──
const searchUsers = ref<Array<{ id: string; display_name: string; avatar_url: string; username: string; post_count: number }>>([])

async function fetchSearchUsers(query: string) {
  if (!query || query.length < 2) { searchUsers.value = []; return }
  try {
    const res = await $fetch<{ users: typeof searchUsers.value }>('/api/search/users', {
      params: { q: query, page: 1 },
      headers: authHeaders(),
    })
    searchUsers.value = (res.users || []).slice(0, 5)
  } catch {
    searchUsers.value = []
  }
}

async function fetchSearch(reset = false) {
  if (reset) { searchPage.value = 1; searchResults.value = [] }
  searchLoading.value = true
  try {
    const res = await $fetch<PostListResponse>(
      `/api/search/posts?q=${encodeURIComponent(searchQuery.value)}&page=${searchPage.value}`,
      { headers: authHeaders() },
    )
    const rawPosts = extractPostArray(res)
    const newPosts = filterCommunityPosts(rawPosts)
    searchResults.value = reset ? newPosts : mergeCommunityPosts(searchResults.value, newPosts)
    searchHasMore.value = responseHasMore(res, rawPosts)
  } catch (e: unknown) {
    if (getStatusCode(e) === 401) { handleSessionExpired(); return }
    showToast('Không thể tìm bài viết', 'error')
  } finally {
    searchLoading.value = false
  }
}

function runSearch() {
  const q = searchInput.value.trim()
  if (q.length < 2) { showToast('Nhập ít nhất 2 ký tự để tìm kiếm', 'info'); return }
  searchQuery.value = q
  syncCommunitySearchQuery(q)
  fetchSearchUsers(q)
  fetchSearch(true)
}

function clearSearch() {
  searchInput.value = ''
  searchQuery.value = ''
  searchResults.value = []
  searchUsers.value = []
  syncCommunitySearchQuery('')
}

function syncCommunitySearchQuery(q: string) {
  if (!import.meta.client) return
  const query = { ...route.query }
  const term = q.trim()
  if (term) query.q = term
  else delete query.q
  if (firstQueryValue(route.query.q) === firstQueryValue(query.q)) return
  router.replace({ query }).catch(() => {})
}

function applyRouteSearchQuery() {
  const q = firstQueryValue(route.query.q).trim()
  if (q.length < 2) {
    if (searchQuery.value) {
      searchInput.value = ''
      searchQuery.value = ''
      searchResults.value = []
    }
    return
  }
  if (q === searchQuery.value) return
  searchInput.value = q
  searchQuery.value = q
  fetchSearch(true)
}

function focusComposerFromRoute() {
  const composeIntent = firstQueryValue(route.query.compose).trim().toLowerCase()
  if (composeIntent !== 'draft' && route.hash !== '#compose') return
  nextTick(() => {
    composeEl.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    composeInputEl.value?.focus()
  })
}

watch(activeTab, (tab) => {
  const normalized = normalizeFeedTab(tab)
  if (normalized !== tab) { activeTab.value = normalized; return }
  if (normalized === 'bookmarks' && filterType.value) setFilterType('')
})

watch(isLoggedIn, (loggedIn) => {
  if (loggedIn) {
    loadSuggested()
    loadScheduledPosts()
    return
  }
  suggestedUsers.value = []
  scheduledPosts.value = []
  if (isPrivateFeedTab(activeTab.value)) setTab('latest')
})

watch(filterType, (value) => {
  const normalized = normalizeFilterType(value)
  if (normalized !== value) { filterType.value = normalized; return }
  if (suppressFilterFetch || searchMode.value || activeTab.value === 'bookmarks') return
  fetchFeed(true)
})

if (import.meta.client) {
  watch([activeTab, filterType, activeTag], ([tab, type, tag]) => {
    trackEvent('community_view', {
      context: 'community',
      metadata: { tab, type, tag },
    }, { dedupeMs: 30_000 })
  })
}

function resetComposer() {
  newContent.value = ''
  newType.value = 'share'
  imageFiles.value = []
  previewImages.value = []
  clearDraft()
  resetMention()
  quotingPost.value = null
  schedulePost.value = false
  scheduledAt.value = ''
}

async function submitScheduledPost() {
  const draftBody: Record<string, any> = {
    content: newContent.value.trim(),
    post_type: newType.value,
  }
  if (previewImages.value.length) draftBody.images = previewImages.value
  const { draft } = await $fetch<{ draft: { id: string } }>('/api/drafts', {
    method: 'POST',
    headers: authHeaders(),
    body: draftBody,
  })
  const isoScheduledAt = new Date(scheduledAt.value).toISOString()
  await $fetch(`/api/drafts/${encodePathId(draft.id)}/schedule?scheduled_at=${encodeURIComponent(isoScheduledAt)}`, {
    method: 'POST',
    headers: authHeaders(),
  })
  resetComposer()
  showToast('Đã lên lịch đăng bài', 'success')
  await loadScheduledPosts()
}

async function submitPost() {
  if (!canSubmit.value) return
  if (schedulePost.value && !scheduledAt.value) return
  if (draftTimer) { clearTimeout(draftTimer); draftTimer = null }
  posting.value = true
  try {
    if (schedulePost.value) {
      await submitScheduledPost()
      return
    }
    const body: Record<string, any> = {
      content: newContent.value.trim(),
      post_type: newType.value,
    }
    if (quotingPost.value) body.repost_of = quotingPost.value.id
    if (previewImages.value.length) {
      body.images = previewImages.value
    }
    // chỉ gửi mention còn xuất hiện trong nội dung (user có thể đã xoá)
    const mentions = activeMentions()
    if (mentions.length) body.mentions = mentions
    await $fetch('/api/posts', {
      method: 'POST',
      headers: authHeaders(),
      body,
    })
    const wasQuote = !!quotingPost.value
    resetComposer()
    showToast(wasQuote ? 'Đã đăng trích dẫn 🔁' : 'Đã đăng bài viết', 'success')
    activeTab.value = 'latest'
    await fetchFeed(true)
  } catch (e: unknown) {
    if (getStatusCode(e) === 401) handleSessionExpired()
    else showToast(extractErrorMessage(e, schedulePost.value ? 'Không thể lên lịch — vui lòng thử lại' : 'Gửi bài thất bại — vui lòng thử lại'), 'error')
  } finally {
    posting.value = false
  }
}

async function fetchReportEntity() {
  reportEntity.value = null
  if (!reportEntityId.value) return
  try {
    reportEntity.value = await $fetch<Entity>(`/api/entities/${encodeURIComponent(reportEntityId.value)}`)
    if (!reportReason.value) {
      reportReason.value = reportEntity.value?.quality?.has_source ? 'Nội dung cần cập nhật' : 'Thiếu nguồn xác minh'
    }
  } catch {
    reportEntity.value = { id: reportEntityId.value, type: 'unknown', name: reportEntityId.value } as ReportEntity
  }
}

async function submitEntityReport() {
  if (!isLoggedIn.value || !reportEntityId.value || reportReason.value.trim().length < 5) return
  reportSubmitting.value = true
  try {
    await $fetch('/api/report', {
      method: 'POST',
      headers: authHeaders(),
      body: {
        target_type: 'entity',
        target_id: reportEntityId.value,
        reason: reportReason.value.trim(),
      },
    })
    showToast('Đã gửi báo cáo. Cảm ơn bạn!', 'success')
    reportReason.value = ''
    const nextQuery = { ...route.query }
    delete nextQuery.report
    router.replace({ query: nextQuery })
  } catch (e: unknown) {
    if (getStatusCode(e) === 401) { handleSessionExpired(); return }
    showToast(extractErrorMessage(e, 'Không thể gửi báo cáo'), 'error')
  }
  reportSubmitting.value = false
}

const { reportPost } = useReport()

// cùng 1 post có thể nằm ở CẢ feed + tab bookmark → cập-nhật MỌI bản để không lệch.
function _copies(postId: string) {
  return [...posts.value, ...bookmarks.value, ...searchResults.value].filter(p => p.id === postId)
}

const { toggleLike: _like, toggleBookmark: _bookmark, deletePost: _delete } = usePostActions()

function toggleLike(postId: string) {
  _like(postId, _copies(postId))
}
function toggleBookmark(postId: string) {
  _bookmark(postId, _copies(postId), () => {
    if (!sessionBookmarked.value) sessionBookmarked.value = true
  })
}
function deletePost(postId: string) {
  _delete(postId, () => {
    posts.value = posts.value.filter(p => p.id !== postId)
    bookmarks.value = bookmarks.value.filter(p => p.id !== postId)
    searchResults.value = searchResults.value.filter(p => p.id !== postId)
  })
}

function goToPost(postId: string) {
  navigateTo(postPath(postId))
}

watch(reportEntityId, () => fetchReportEntity())

let draftTimer: ReturnType<typeof setTimeout> | null = null
watch(newContent, (v) => {
  if (draftTimer) clearTimeout(draftTimer)
  draftTimer = setTimeout(() => {
    try {
      saveDraft(v, newType.value)
    } catch {
      showToast('Không thể lưu bản nháp', 'warning')
    }
  }, 3000)
})

function onClickOutsideMention(e: MouseEvent) {
  if (mentionOpen.value && !(e.target as HTMLElement)?.closest('.compose-mention-wrap')) {
    closeMention()
  }
}

onMounted(() => {
  document.addEventListener('click', onClickOutsideMention)
  trackEvent('community_view', {
    context: 'community',
    metadata: { tab: activeTab.value, type: filterType.value, tag: activeTag.value },
  })
  const draft = loadDraft()
  if (draft && draft.content) { newContent.value = draft.content; newType.value = draft.postType }
  applyRouteSearchQuery()
  focusComposerFromRoute()
  fetchReportEntity()
  normalizeCommunityRouteState()
  refreshFeed()
  loadCommunityStats()
  loadTrendingTags()
  loadLeaderboard()
  loadSuggested()
  loadScheduledPosts()
  // Trích dẫn từ trang khác điều hướng tới: ?quote=<post_id>
  const q = firstQueryValue(route.query.quote).trim()
  if (q) {
    startQuote(q)
    const { quote, ...rest } = route.query
    router.replace({ query: rest })
  }
  // Cuộn vô hạn: tự nạp trang kế khi sentinel gần vào tầm nhìn
  if (typeof IntersectionObserver !== 'undefined' && loadSentinel.value) {
    loadObserver = new IntersectionObserver((entries) => {
      if (entries[0]?.isIntersecting && canLoadMore.value) loadMore()
    }, { rootMargin: '500px' })
    loadObserver.observe(loadSentinel.value)
  }
})

onUnmounted(() => {
  if (draftTimer) { clearTimeout(draftTimer); draftTimer = null }
  feedAbort?.abort()
  loadObserver?.disconnect()
  document.removeEventListener('click', onClickOutsideMention)
})

useSeoMeta({
  title: () => pc('seo_title'),
  description: () => pc('seo_description'),
  ogTitle: () => pc('og_title'),
  ogDescription: () => pc('og_description'),
})

useHead({
  link: [{ rel: 'canonical', href: canonicalUrl('/cong-dong') }],
  script: [{
    type: 'application/ld+json',
    innerHTML: JSON.stringify({
      '@context': 'https://schema.org',
      '@type': 'CollectionPage',
      name: 'Cộng đồng vinhlong360',
      description: 'Bảng tin cộng đồng chia sẻ trải nghiệm du lịch, đánh giá và báo cáo dữ liệu cho Vĩnh Long, Bến Tre, Trà Vinh.',
      url: canonicalUrl('/cong-dong'),
    }),
  }],
})
</script>

<style scoped>
/* @-mention dropdown: styles dùng chung đã chuyển sang assets/css/components.css */
.community-search { display: flex; align-items: center; gap: var(--space-2); margin-bottom: var(--space-3); padding: .35rem .5rem .35rem .75rem; background: var(--card); border: 1px solid var(--border); border-radius: var(--radius-full); }
.community-search:focus-within { border-color: var(--primary); }
.cs-icon { color: var(--muted); flex-shrink: 0; }
.cs-input { flex: 1; min-width: 0; border: none; background: none; outline: none; color: var(--ink); font-size: var(--text-sm); padding: .35rem 0; }
.cs-input:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
.cs-input::placeholder { color: var(--muted); }
.cs-clear { border: none; background: none; color: var(--muted); font-size: 1.3rem; line-height: 1; cursor: pointer; padding: 0 .25rem; }
.cs-clear:hover { color: var(--ink); }
.cs-go { flex-shrink: 0; }
.leaderboard-list { list-style: none; padding: 0; margin: 0 0 var(--space-2); display: flex; flex-direction: column; gap: var(--space-1); }
.lb-row { display: flex; align-items: center; gap: var(--space-2); padding: var(--space-1) var(--space-2); border-radius: var(--radius-md); text-decoration: none; color: var(--ink); transition: background .2s var(--ease-out); }
.lb-row:hover { background: var(--bg-alt); }
.lb-rank { flex-shrink: 0; width: 18px; text-align: center; font-size: var(--text-xs); font-weight: var(--weight-bold); color: var(--muted); }
.lb-rank-1 { color: var(--lb-gold, #d4a017); } .lb-rank-2 { color: var(--lb-silver, #8a8d91); } .lb-rank-3 { color: var(--lb-bronze, #b07b4f); }
.lb-avatar { width: 26px; height: 26px; display: inline-flex; align-items: center; justify-content: center; border-radius: 50%; background: var(--primary); color: var(--primary-fg, #fff); font-size: var(--text-2xs); font-weight: var(--weight-semibold); flex-shrink: 0; }
.lb-name { flex: 1; min-width: 0; font-size: var(--text-sm); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.lb-points { flex-shrink: 0; font-size: var(--text-xs); font-weight: var(--weight-semibold); color: var(--primary-fg); }
.sidebar-more { display: inline-block; font-size: var(--text-sm); color: var(--primary-fg); text-decoration: none; }
.sidebar-more:hover { text-decoration: underline; }
.suggest-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: var(--space-2); }
.suggest-row { display: flex; align-items: center; gap: var(--space-2); }
.suggest-user { display: flex; align-items: center; gap: var(--space-2); flex: 1; min-width: 0; text-decoration: none; color: var(--ink); }
.suggest-avatar { width: 30px; height: 30px; display: inline-flex; align-items: center; justify-content: center; border-radius: 50%; background: var(--primary); color: var(--primary-fg, #fff); font-size: var(--text-xs); font-weight: var(--weight-semibold); flex-shrink: 0; }
.suggest-name { font-size: var(--text-sm); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.suggest-follow { flex-shrink: 0; padding: .2rem .6rem; }
.trending-tags { display: flex; flex-wrap: wrap; gap: var(--space-2); }
.trending-tag { display: inline-flex; align-items: center; gap: .35rem; padding: .25rem .6rem; background: var(--bg-alt); border: .5px solid var(--line); border-radius: var(--radius-full); font-size: var(--text-sm); color: var(--primary-fg); text-decoration: none; transition: border-color .25s var(--ease-out), background .25s var(--ease-out); }
.trending-tag:hover { border-color: var(--primary-fg); background: rgba(var(--primary-rgb), .06); }
.tt-count { font-size: var(--text-xs); color: var(--muted); }
.tag-banner { display: flex; align-items: center; justify-content: space-between; gap: .5rem; padding: .5rem .75rem; margin-bottom: var(--space-3); background: color-mix(in srgb, var(--accent) 10%, var(--bg-alt)); border-radius: var(--radius-md); font-size: var(--text-sm); }
.tag-clear { border: none; background: none; color: var(--primary-fg); cursor: pointer; font-size: var(--text-sm); }
.threads-page { max-width: 960px; margin: 0 auto; }
.threads-layout { display: grid; grid-template-columns: 1fr 280px; gap: var(--space-6); align-items: start; }
.threads-feed { display: flex; flex-direction: column; }

/* ── Compose (Threads style) ── */
.threads-compose { display: flex; gap: var(--space-3); padding: var(--space-4) 0; border-bottom: .5px solid var(--line); }
.compose-left { width: 40px; flex-shrink: 0; display: flex; justify-content: center; }
.compose-right { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: var(--space-2); }
.compose-input {
  width: 100%; border: none; background: transparent; color: var(--ink);
  font-size: var(--text-base); line-height: var(--leading-relaxed);
  resize: none; outline: none; font-family: inherit;
  min-height: 44px; padding: 0;
}
.compose-input:focus-visible { outline: 2px solid var(--primary); outline-offset: -2px; }
.compose-input::placeholder { color: var(--muted); }
.threads-compose {
  transition: background .3s var(--ease-out), border-color .3s var(--ease-out), border-radius .3s var(--ease-out), box-shadow .3s var(--ease-out-expo);
  border-radius: var(--radius-md); margin: 0 calc(var(--space-2) * -1);
  padding: var(--space-5) var(--space-3) var(--space-4);
  background: rgba(var(--accent-rgb), .04);
  border-bottom: none; box-shadow: var(--shadow-xs);
}
.threads-compose:focus-within { background: rgba(var(--accent-rgb), .07); border-radius: var(--radius-lg); box-shadow: var(--shadow-sm); }
/* Composer post-type chips — micro feedback on selection (signature) */
.post-type-selector { display: flex; flex-wrap: wrap; gap: var(--space-2); }
.post-type-selector .chip-sm { transition: background .2s, color .2s, border-color .2s, transform .3s var(--ease-spring-gentle); }
.post-type-selector .chip-sm.active { transform: scale(1.04) rotate(-1deg); }
.post-type-selector .chip-sm:active { transform: scale(.95); transition-duration: .08s; }
.compose-footer { display: flex; justify-content: space-between; align-items: center; gap: var(--space-3); padding-top: var(--space-1); }
.compose-footer-left { display: flex; align-items: center; gap: var(--space-3); }
.compose-attach {
  display: inline-flex; align-items: center; justify-content: center;
  width: 44px; height: 44px; min-width: 44px; min-height: 44px; border-radius: var(--radius-full);
  cursor: pointer; color: var(--muted); transition: background .3s var(--ease-out), color .3s var(--ease-out), transform .35s var(--ease-spring-gentle);
}
.compose-attach:hover { background: var(--bg-alt); color: var(--ink); transform: scale(1.08); }
.compose-attach:active { transform: scale(.88); transition-duration: .08s; }
.compose-attach:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
.char-count { font-size: var(--text-xs); color: var(--muted); font-variant-numeric: tabular-nums; transition: color .2s; }
.char-count.warn { color: var(--accent-dark); }
.char-count.full { color: var(--error); font-weight: var(--weight-semibold); }
.chip-sm { font-size: var(--text-xs); padding: var(--space-2) 10px; min-height: 44px; display: inline-flex; align-items: center; }

.threads-compose-guest {
  display: flex; gap: var(--space-3); padding: var(--space-4) 0;
  border-bottom: .5px solid var(--line); align-items: center;
}
.guest-avatar { width: 40px; flex-shrink: 0; display: flex; justify-content: center; }
.guest-avatar .avatar.guest { opacity: .5; }
.guest-content { flex: 1; display: flex; align-items: center; gap: var(--space-3); }
.guest-content p { margin: 0; color: var(--muted); font-size: var(--text-sm); flex: 1; }

/* ── Filter tabs ── */
.threads-filter-bar {
  display: flex; align-items: stretch;
  border-bottom: .5px solid var(--line);
  margin-top: var(--space-5);
  position: sticky; top: 78px; z-index: 20;
  background: var(--surface-translucent, var(--bg));
  backdrop-filter: var(--glass, saturate(160%) blur(12px));
  -webkit-backdrop-filter: var(--glass, saturate(160%) blur(12px));
}
.threads-filter { display: flex; flex: 1; min-width: 0; }
.threads-tab {
  flex: 1; text-align: center; padding: var(--space-3) var(--space-4);
  background: none; border: none; border-bottom: 2px solid transparent;
  font-size: var(--text-sm); font-weight: var(--weight-semibold);
  color: var(--muted); cursor: pointer; min-height: 44px;
  transition: color .25s var(--ease-out);
  position: relative;
}
.threads-tab::after {
  content: ''; position: absolute; bottom: -1px; left: 20%; right: 20%;
  height: 2px; background: var(--ink); border-radius: 1px;
  transform: scaleX(0); transition: transform .3s var(--ease-spring-gentle);
}
.threads-tab:hover { color: var(--ink); }
.threads-tab:hover::after { transform: scaleX(.5); }
.threads-tab:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
.threads-tab.active { color: var(--ink); border-bottom-color: transparent; }
.threads-tab.active::after { transform: scaleX(1); }
.dark .threads-tab.active { color: var(--ink); }
.threads-refresh {
  flex-shrink: 0; width: 44px; min-height: 44px;
  display: inline-flex; align-items: center; justify-content: center;
  padding: .5rem; background: none; border: none;
  color: var(--muted); cursor: pointer;
  transition: color .25s var(--ease-out), background .25s var(--ease-out);
}
.threads-refresh:hover { color: var(--ink); background: var(--overlay-subtle); }
.threads-refresh:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
.threads-refresh svg { display: block; }
.threads-refresh .spinning { animation: spin .8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* ── Type filter ── */
.type-filter-row {
  display: flex; gap: var(--space-2); padding: var(--space-3) 0;
  overflow-x: auto; -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
}
.type-filter-row::-webkit-scrollbar { display: none; }
.chip-filter {
  font-size: var(--text-xs); padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-full); border: .5px solid var(--line);
  background: var(--card); color: var(--muted); cursor: pointer;
  white-space: nowrap; min-height: 44px; display: inline-flex; align-items: center;
  transition: background .2s, color .2s, border-color .2s, transform .25s var(--ease-spring-gentle);
}
.chip-filter:hover { border-color: var(--ink); color: var(--ink); }
.chip-filter:active { transform: scale(.95); transition-duration: .08s; }
.chip-filter:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
.chip-filter.active { background: var(--ink); color: var(--bg); border-color: var(--ink); font-weight: var(--weight-semibold); }

/* ── Post list transitions ── */
.post-list-container { display: flex; flex-direction: column; }
.post-list-enter-active { transition: opacity .3s var(--ease-out), transform .3s var(--ease-spring-gentle); }
.post-list-leave-active { transition: opacity .2s var(--ease-out); }
.post-list-enter-from { opacity: 0; transform: translateY(8px); }
.post-list-leave-to { opacity: 0; }
.post-list-move { transition: transform .3s var(--ease-spring-gentle); }

/* ── Load more ── */
.threads-load-more {
  width: 100%; margin-top: var(--space-3); min-height: 44px;
  font-weight: var(--weight-semibold);
  transition: background .25s var(--ease-out), transform .25s var(--ease-spring-gentle), box-shadow .25s var(--ease-out);
}
.threads-load-more:hover { transform: translateY(-1px); box-shadow: var(--shadow-xs); }
.threads-load-more:active { transform: scale(.98); transition-duration: .08s; }
.threads-load-more:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
/* Section rhythm — quiet divider between compose and feed */
.type-filter-row + .post-list-container { margin-top: var(--space-1); }

/* ── Sidebar ── */
.threads-sidebar { position: sticky; top: 78px; display: flex; flex-direction: column; gap: var(--space-4); }
.sidebar-card {
  background: var(--card); border: .5px solid var(--line);
  border-radius: var(--radius-lg); padding: var(--space-4);
  box-shadow: var(--shadow-xs);
  transition: transform .35s var(--ease-spring-gentle), box-shadow .35s var(--ease-out-expo), border-color .3s var(--ease-out);
}
.sidebar-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-md); border-color: var(--border, var(--ink)); }
.sidebar-card:focus-within { border-color: var(--border, var(--ink)); }
.sidebar-card h2 { margin: 0 0 var(--space-3); font-size: var(--text-sm); font-weight: var(--weight-bold); }
.sidebar-card p { margin: 0; font-size: var(--text-sm); color: var(--muted); line-height: var(--leading-relaxed); }

.sidebar-stats { display: flex; gap: var(--space-4); margin-top: var(--space-3); padding-top: var(--space-3); border-top: .5px solid var(--line); }
.sidebar-stat { display: flex; flex-direction: column; gap: 2px; padding: var(--space-2) var(--space-3); border-radius: var(--radius-sm); transition: background .3s var(--ease-out); cursor: default; }
.sidebar-stat:hover { background: var(--overlay-subtle); }
.stat-num { font-size: var(--text-lg); font-weight: var(--weight-bold); color: var(--ink); font-variant-numeric: tabular-nums; transition: color .3s var(--ease-out); }
.sidebar-stat:hover .stat-num { color: var(--primary-fg); }
.stat-label { font-size: var(--text-xs); color: var(--muted); }

.sidebar-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: var(--space-2); }
.sidebar-list li { display: flex; gap: var(--space-3); align-items: flex-start; font-size: var(--text-sm); line-height: var(--leading-snug); padding: var(--space-2); border-radius: var(--radius-sm); transition: background .3s var(--ease-out), transform .35s var(--ease-spring-gentle); }
.sidebar-list li:hover { background: var(--overlay-subtle); transform: translateX(2px); }
.sl-icon { font-size: var(--text-lg); flex-shrink: 0; width: 24px; text-align: center; transition: transform .3s var(--ease-spring-gentle); }
.sidebar-list li:hover .sl-icon { transform: scale(1.15); }
.sl-desc { font-size: var(--text-xs); color: var(--muted); }
.sidebar-list strong { font-weight: var(--weight-semibold); }

.sidebar-rules-list {
  padding: 0; margin: 0; list-style: none;
  counter-reset: rule-counter;
  font-size: var(--text-sm); color: var(--ink-secondary);
  display: flex; flex-direction: column; gap: var(--space-2);
  line-height: var(--leading-relaxed);
}
.sidebar-rules-list li {
  counter-increment: rule-counter;
  display: flex; align-items: flex-start; gap: var(--space-2);
}
.sidebar-rules-list li::before {
  content: counter(rule-counter);
  flex-shrink: 0;
  width: 20px; height: 20px; border-radius: var(--radius-full);
  display: inline-flex; align-items: center; justify-content: center;
  font-size: var(--text-xs); font-weight: var(--weight-bold);
  background: rgba(var(--accent-rgb), .14); color: var(--accent-dark);
  margin-top: 1px;
}

/* ── Report card ── */
.report-entity-card {
  display: grid; gap: var(--space-3); margin-bottom: 0;
  padding: var(--space-5) var(--space-4) var(--space-4);
  border: .5px solid rgba(var(--accent-rgb), .2); border-radius: var(--radius-lg);
  background: rgba(var(--accent-rgb), .06); box-shadow: var(--shadow-xs);
  animation: slideDown .35s var(--ease-spring-gentle);
  transition: border-color .3s var(--ease-out), box-shadow .35s var(--ease-out-expo);
}
.report-entity-card:focus-within { border-color: var(--accent-dark); box-shadow: 0 0 0 4px rgba(var(--accent-rgb), .1), var(--shadow-sm); }
.report-entity-card:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
@keyframes slideDown { from { opacity: 0; transform: translateY(-8px) scale(.99); } }
.report-entity-card h2 { margin: 2px 0 var(--space-1); font-size: var(--text-base); font-weight: var(--weight-semibold); }
.report-entity-card p { margin: 0; color: var(--muted); font-size: var(--text-sm); }
.report-kicker { font-size: var(--text-xs); text-transform: uppercase; letter-spacing: .04em; font-weight: var(--weight-extrabold); color: var(--accent-dark); }
.report-form-inline { display: grid; gap: var(--space-3); }
.report-reasons { display: flex; flex-wrap: wrap; gap: var(--space-2); }
.report-form-inline .btn { justify-self: start; }

.img-preview-row { display: flex; gap: var(--space-2); flex-wrap: wrap; animation: fadeIn .25s var(--ease-out); }
.img-preview-item { position: relative; width: 64px; height: 64px; border-radius: var(--radius-sm); overflow: hidden; transition: transform .35s var(--ease-spring-gentle), box-shadow .3s var(--ease-out); }
.img-preview-item:hover { transform: scale(1.08); box-shadow: var(--shadow-sm); }
.img-preview-item img { width: 100%; height: 100%; object-fit: cover; }
.img-preview-item .remove { position: absolute; top: -4px; right: -4px; width: 28px; height: 28px; border-radius: 50%; background: var(--overlay-dark); color: var(--text-on-dark, #fff); border: none; cursor: pointer; font-size: .7rem; display: flex; align-items: center; justify-content: center; padding: var(--space-2); box-sizing: content-box; transition: background .2s, transform .25s var(--ease-spring-gentle); }
.img-preview-item .remove:hover { background: var(--error); transform: scale(1.1); }
.img-preview-item .remove:focus-visible { outline: 2px solid var(--text-on-dark, #fff); outline-offset: 1px; }
@keyframes fadeIn { from { opacity: 0; } }

.feed-error { text-align: center; padding: var(--space-5); color: var(--error); }
.feed-error p { margin: 0 0 var(--space-3); }
.feed-loading { text-align: center; padding: var(--space-5); }
.feed-loading .spinner { margin: 0 auto; }


/* ── Bookmark momentum cue (bottom-center, clears the right-side FAB) ── */
.bookmark-momentum {
  position: fixed; z-index: var(--z-dropdown);
  bottom: calc(var(--space-6) + env(safe-area-inset-bottom));
  left: 50%; transform: translateX(-50%);
  display: flex; align-items: center; gap: var(--space-2);
  padding: var(--space-2) var(--space-2) var(--space-2) var(--space-4);
  background: var(--card); border: .5px solid var(--line);
  border-radius: var(--radius-full); box-shadow: var(--shadow-lg);
  max-width: calc(100vw - var(--space-6) * 2);
}
.bm-icon { font-size: 1.05rem; flex-shrink: 0; }
.bm-link {
  background: none; border: none; cursor: pointer; padding: 0;
  color: var(--primary-fg); font-size: var(--text-sm); font-weight: var(--weight-semibold);
  min-height: 44px; display: inline-flex; align-items: center;
  transition: color .2s var(--ease-out);
}
.bm-link:hover { color: var(--ink); text-decoration: underline; }
.bm-link:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; border-radius: var(--radius-sm); }
.bm-dismiss {
  flex-shrink: 0; width: 44px; height: 44px; min-width: 44px; border-radius: var(--radius-full);
  background: none; border: none; cursor: pointer; color: var(--muted);
  font-size: 1.25rem; line-height: 1; display: inline-flex; align-items: center; justify-content: center;
  transition: background .2s var(--ease-out), color .2s var(--ease-out), transform .25s var(--ease-spring-gentle);
}
.bm-dismiss:hover { background: var(--bg-alt); color: var(--ink); }
.bm-dismiss:active { transform: scale(.9); transition-duration: .08s; }
.bm-dismiss:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
.momentum-fade-enter-active { transition: opacity .25s var(--ease-out), transform .3s var(--ease-spring-gentle); }
.momentum-fade-leave-active { transition: opacity .15s var(--ease-out), transform .15s var(--ease-out); }
.momentum-fade-enter-from { opacity: 0; transform: translate(-50%, 16px); }
.momentum-fade-leave-to { opacity: 0; transform: translate(-50%, 8px); }

/* ── Dark mode ── */
.dark .sidebar-card { background: var(--card); border-color: var(--line); }
.dark .sidebar-card:hover { box-shadow: var(--shadow-sm); border-color: rgba(255,255,255,.14); }
.dark .chip-filter { background: var(--bg-alt); border-color: var(--line); }
.dark .chip-filter.active { background: var(--ink); color: var(--bg); border-color: var(--ink); }
.dark .bookmark-momentum { background: var(--card); border-color: rgba(255,255,255,.1); box-shadow: 0 8px 32px rgba(0,0,0,.5); }
.dark .bm-dismiss:hover { background: rgba(255,255,255,.08); }
.dark .sidebar-stat:hover { background: rgba(255,255,255,.03); }
.dark .sidebar-list li:hover { background: rgba(255,255,255,.03); }
.dark .report-entity-card { background: rgba(var(--accent-rgb),.08); border-color: rgba(var(--accent-rgb),.22); }
.dark .compose-attach:hover { background: rgba(255,255,255,.08); }
.dark .threads-compose { background: rgba(var(--accent-rgb),.06); }
.dark .threads-compose:focus-within { background: rgba(var(--accent-rgb),.1); }
.dark .threads-filter-bar { background: var(--surface-translucent, rgba(0,0,0,.72)); }
.dark .sidebar-rules-list li::before { background: rgba(var(--accent-rgb),.2); color: var(--accent); }
.dark .lb-rank-1 { --lb-gold: #f0c040; } .dark .lb-rank-2 { --lb-silver: #b0b3b8; } .dark .lb-rank-3 { --lb-bronze: #d4975a; }

.mobile-discovery { display: none; }

/* ── User search results ── */
.search-users-section { margin-bottom: var(--space-4); }
.search-users-grid { display: flex; gap: var(--space-2); overflow-x: auto; padding-bottom: var(--space-1); }
.search-user-card { display: flex; align-items: center; gap: var(--space-2); padding: var(--space-2) var(--space-3); min-width: 180px; flex-shrink: 0; text-decoration: none; }
.suc-info { min-width: 0; }
.suc-info strong { display: block; font-size: 0.875rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: var(--ink); }
.suc-meta { font-size: 0.75rem; color: var(--muted); }
.section-label { font-size: var(--text-sm); font-weight: var(--weight-semibold); color: var(--muted); margin: 0 0 var(--space-2); text-transform: uppercase; letter-spacing: 0.04em; }

@media (max-width: 820px) {
  .threads-layout { grid-template-columns: 1fr; }
  .threads-sidebar { display: none; }
  .threads-page { max-width: 100%; }
  .threads-feed { padding-inline: var(--space-1); }
  .threads-compose { padding-inline: var(--space-3); }
  .compose-input { min-height: 48px; font-size: var(--text-base); }
  .mobile-discovery { display: flex; flex-direction: column; gap: var(--space-2); padding: var(--space-2) var(--space-3); }
  .md-section { display: flex; align-items: center; gap: var(--space-2); }
  .md-label { font-size: .7rem; font-weight: 600; text-transform: uppercase; letter-spacing: .04em; color: var(--ink-500); white-space: nowrap; min-width: 52px; }
  .md-scroll { display: flex; gap: var(--space-2); overflow-x: auto; -webkit-overflow-scrolling: touch; scrollbar-width: none; padding-block: 2px; }
  .md-scroll::-webkit-scrollbar { display: none; }
  .md-tag { font-size: .8rem; padding: var(--space-1) 10px; border-radius: var(--radius-full); background: var(--surface-2); color: var(--accent); white-space: nowrap; text-decoration: none; font-weight: 500; }
  .md-tag:hover { background: var(--accent); color: var(--text-on-dark, #fff); }
  .md-member { display: flex; align-items: center; gap: var(--space-1); padding: var(--space-1) var(--space-2); border-radius: var(--radius-full); background: var(--surface-2); text-decoration: none; white-space: nowrap; }
  .md-name { font-size: .78rem; color: var(--ink-800); }
  .dark .md-tag { background: var(--surface-3); }
  .dark .md-member { background: var(--surface-3); }
  .dark .md-name { color: var(--ink-200); }
}

@media (prefers-reduced-motion: reduce) {
  .report-entity-card { animation: none; }
  .img-preview-row { animation: none; }
  .post-list-enter-active,
  .post-list-leave-active,
  .post-list-move,
  .fab-fade-enter-active,
  .fab-fade-leave-active { transition: none; }
  .sidebar-card { transition: none; }
  .sidebar-card:hover { transform: none; }
  .sidebar-list li:hover { transform: none; }
  .sidebar-list li:hover .sl-icon { transform: none; }
  .img-preview-item:hover { transform: none; }
  .compose-attach:hover { transform: none; }
  .compose-attach:active { transform: none; }
  .threads-tab::after { transition: none; }
  .post-type-selector .chip-sm.active { transform: none; }
  .post-type-selector .chip-sm:active { transform: none; }
  .chip-filter:active { transform: none; }
  .threads-load-more:hover { transform: none; }
  .threads-load-more:active { transform: none; }
  .momentum-fade-enter-active,
  .momentum-fade-leave-active { transition: none; }
  .bm-dismiss:active { transform: none; }
  .threads-refresh .spinning { animation: none; }
}
.onboard-follows { width: 100%; margin-bottom: var(--space-3); text-align: left; }
.onboard-title { font-size: var(--text-sm); font-weight: 600; margin-bottom: var(--space-2); color: var(--muted); }
.onboard-list { display: flex; flex-direction: column; gap: var(--space-2); }
.onboard-user { display: flex; align-items: center; justify-content: space-between; gap: var(--space-3); padding: var(--space-2) var(--space-3); border-radius: var(--radius-md); background: var(--bg-alt); }
.onboard-info { display: flex; align-items: center; gap: var(--space-2); text-decoration: none; color: inherit; font-weight: 500; }
.onboard-name { font-size: var(--text-sm); }
.btn-xs { padding: var(--space-1) 10px; font-size: .72rem; border-radius: var(--radius-sm); }

/* ── Lên lịch đăng bài ── */
.schedule-option { margin-top: var(--space-1); }
.schedule-toggle { display: flex; align-items: center; gap: var(--space-2); cursor: pointer; font-size: var(--text-sm); color: var(--ink); width: fit-content; }
.schedule-picker { margin-top: var(--space-2); display: flex; flex-direction: column; gap: var(--space-1); align-items: flex-start; }
.cd-toggle { appearance: none; width: 40px; height: 22px; background: var(--muted); border-radius: 11px; position: relative; cursor: pointer; transition: background .25s var(--ease-out); flex-shrink: 0; min-height: 44px; padding: 11px 0; box-sizing: content-box; margin: 0; }
.cd-toggle::after { content: ''; position: absolute; top: 2px; left: 2px; width: 18px; height: 18px; background: var(--white, #fff); border-radius: 50%; transition: transform .3s var(--ease-spring-gentle); box-shadow: 0 1px 3px rgba(0,0,0,.15); }
.cd-toggle:checked { background: var(--accent, var(--primary)); }
.cd-toggle:checked::after { transform: translateX(18px); }
.cd-toggle:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
.cd-input {
  padding: var(--space-2) var(--space-3); border: 1px solid var(--line); border-radius: var(--radius-md);
  background: var(--bg-alt); color: var(--ink); font-size: var(--text-sm); font-family: inherit; min-height: 44px;
}
.cd-input:focus-visible { outline: none; border-color: var(--accent, var(--primary)); box-shadow: 0 0 0 3px rgba(var(--accent-rgb, 33,150,83), .15); }
.cd-hint { font-size: var(--text-xs); color: var(--muted); }

.scheduled-section { margin-bottom: var(--space-4); }
.scheduled-summary { cursor: pointer; font-weight: var(--weight-semibold); color: var(--primary-fg); padding: var(--space-2) 0; list-style: none; }
.scheduled-summary::-webkit-details-marker { display: none; }
.scheduled-summary:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; border-radius: var(--radius-sm); }
.scheduled-list { display: flex; flex-direction: column; gap: var(--space-2); padding-top: var(--space-2); }
.scheduled-item { padding: var(--space-3); background: var(--card); border: .5px solid var(--line); border-radius: var(--radius-md); }
.scheduled-item p { margin: 0; font-size: var(--text-sm); line-height: var(--leading-relaxed); overflow-wrap: anywhere; }
.scheduled-meta { display: flex; justify-content: space-between; align-items: center; margin-top: var(--space-2); font-size: var(--text-xs); color: var(--muted); }
.scheduled-cancel { color: var(--error); padding: var(--space-1) var(--space-2); min-height: 32px; }
.scheduled-cancel:hover { background: rgba(var(--error-rgb, 220,38,38), .08); }

@media (prefers-reduced-motion: reduce) {
  .cd-toggle, .cd-toggle::after { transition: none; }
}
</style>
