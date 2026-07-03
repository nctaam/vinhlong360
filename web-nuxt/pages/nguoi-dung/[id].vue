<template>
  <section class="page user-profile-page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Cộng đồng', to: '/cong-dong' }, { label: profile?.display_name || 'Người dùng' }]" />

    <div v-if="profile" class="user-profile reveal">
      <div class="profile-cover">
        <img v-if="profile.cover_url" :src="profile.cover_url" :alt="`Ảnh bìa ${profile.display_name}`" class="cover-img" loading="eager" fetchpriority="high" decoding="async" width="960" height="200" @error="(e: Event) => ((e.target as HTMLImageElement).style.opacity = '.15')" />
        <UserCoverPlaceholder v-else />
        <div class="cover-scrim" aria-hidden="true"></div>
        <div class="profile-avatar-wrap">
          <span v-if="profile.avatar" class="avatar avatar-xl">
            <img :src="profile.avatar" :alt="profile.display_name" loading="lazy" decoding="async" width="96" height="96" @error="(e: Event) => ((e.target as HTMLImageElement).style.display = 'none')" />
          </span>
          <span v-else class="avatar avatar-xl">{{ initial }}</span>
        </div>
      </div>

      <div class="profile-info">
        <div class="profile-name-row">
          <h1>{{ profile.display_name || profile.phone || 'Người dùng' }}</h1>
          <button type="button"
            v-if="isLoggedIn && !isSelf"
            :class="['btn btn-sm', isFollowing ? 'btn-ghost' : 'btn-primary']"
            :disabled="followLoading"
            :aria-busy="followLoading"
            @click="toggleFollow"
          >
            <span v-if="!followLoading">{{ isFollowing ? 'Đang theo dõi' : 'Theo dõi' }}</span>
            <span v-else class="spinner spinner-sm" aria-label="Đang xử lý"></span>
          </button>
          <div v-if="isLoggedIn && !isSelf" class="profile-more-wrap" @keydown.escape="showMoreMenu = false">
            <button type="button" class="btn btn-ghost btn-sm btn-icon" aria-label="Thêm" aria-haspopup="true" :aria-expanded="showMoreMenu" @click="showMoreMenu = !showMoreMenu">&#8226;&#8226;&#8226;</button>
            <div v-if="showMoreMenu" class="profile-more-menu" @click.self="showMoreMenu = false">
              <button type="button" class="pm-item" @click="toggleBlock">{{ isBlocked ? 'Bỏ chặn' : 'Chặn người này' }}</button>
              <button type="button" class="pm-item pm-danger" @click="reportUser">Báo cáo</button>
            </div>
          </div>
          <NuxtLink v-if="isSelf" to="/cai-dat" class="btn btn-ghost btn-sm">
            <svg class="icon-inline" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>Sửa hồ sơ
          </NuxtLink>
          <button type="button" class="btn btn-ghost btn-sm btn-icon" aria-label="Chia sẻ hồ sơ" @click="shareProfile">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"/><polyline points="16 6 12 2 8 6"/><line x1="12" y1="2" x2="12" y2="15"/></svg>
          </button>
        </div>
        <div class="profile-meta-row" aria-label="Thông tin nhanh">
          <span v-if="profileHandle" class="profile-handle">{{ profileHandle }}</span>
          <span :class="['profile-chip', profile.is_private ? 'is-private' : 'is-public']">
            {{ profile.is_private ? 'Hồ sơ riêng tư' : 'Hồ sơ công khai' }}
          </span>
          <span v-if="isSelf" class="profile-chip is-self">Hồ sơ của bạn</span>
          <span v-else-if="isFollowing" class="profile-chip is-following">Đang theo dõi</span>
        </div>
        <p v-if="profile.bio" class="profile-bio">{{ profile.bio }}</p>
        <div v-if="profile.reputation" class="profile-reputation">
          <NuxtLink to="/huong-dan-thanh-vien" class="rep-level" :data-level="profile.reputation.level" title="Xem hướng dẫn cấp bậc">
            {{ levelIcon(profile.reputation.level) }} {{ profile.reputation.level_label }}
          </NuxtLink>
          <span v-for="b in profile.reputation.badges" :key="b.id" class="rep-badge" :title="b.label">
            {{ b.icon }} {{ b.label }}
          </span>
        </div>
        <details v-if="isSelf && badgeProgress.length" class="badge-showcase" open>
          <summary class="bs-title">Thành tích ({{ earnedBadgeCount }}/{{ badgeProgress.length }})</summary>
          <div class="bs-grid">
            <div v-for="b in badgeProgress" :key="b.id" :class="['bs-card', { earned: b.earned }]">
              <span class="bs-icon" aria-hidden="true">{{ b.icon }}</span>
              <span class="bs-label">{{ b.label }}</span>
              <div v-if="!b.earned" class="bs-progress">
                <div class="bs-bar"><div class="bs-fill" :style="{ width: Math.min(100, (b.current / b.target) * 100) + '%' }"></div></div>
                <span class="bs-hint">{{ b.hint || `${b.current}/${b.target}` }}</span>
              </div>
              <span v-else class="bs-earned-label">Đã đạt</span>
            </div>
          </div>
        </details>
        <div class="profile-stats">
          <template v-if="!profile.is_private || isSelf">
            <div class="stat-item">
              <strong><CountUp :value="profile.post_count || 0" /></strong>
              <span>bài viết</span>
            </div>
            <div class="stat-item">
              <strong><CountUp :value="profile.review_count || 0" /></strong>
              <span>đánh giá</span>
            </div>
          </template>
          <button type="button" class="stat-item stat-clickable" @click="openFollowModal('followers')">
            <strong>{{ displayFollowerCount }}</strong>
            <span>người theo dõi</span>
          </button>
          <button type="button" class="stat-item stat-clickable" @click="openFollowModal('following')">
            <strong>{{ profile.following_count || 0 }}</strong>
            <span>đang theo dõi</span>
          </button>
          <div class="stat-item">
            <time v-if="profile.created_at" :datetime="profile.created_at"><strong>{{ joinDate }}</strong></time>
            <strong v-else>{{ joinDate }}</strong>
            <span>tham gia</span>
          </div>
        </div>
        <div class="profile-insight" aria-live="polite">
          <div class="profile-insight-copy">
            <span>Tổng quan</span>
            <strong>{{ activitySummary }}</strong>
          </div>
          <NuxtLink v-if="isSelf" to="/cai-dat" class="profile-insight-link">Cập nhật hồ sơ</NuxtLink>
          <NuxtLink v-else to="/cong-dong" class="profile-insight-link">Xem cộng đồng</NuxtLink>
        </div>
      </div>

      <div v-if="isSelf && profileCompletion < 100" class="profile-completion">
        <div class="pc-row">
          <span class="pc-label">Hồ sơ hoàn thiện {{ profileCompletion }}%</span>
          <NuxtLink to="/cai-dat" class="pc-link">Hoàn thiện</NuxtLink>
        </div>
        <div class="pc-bar"><div class="pc-fill" :style="{ width: profileCompletion + '%' }"></div></div>
        <div class="pc-hints">
          <span v-if="!profile.display_name" class="pc-hint">Thêm tên hiển thị</span>
          <span v-if="!profile.avatar" class="pc-hint">Thêm ảnh đại diện</span>
          <span v-if="!profile.cover_url" class="pc-hint">Thêm ảnh bìa</span>
          <span v-if="!profile.bio" class="pc-hint">Viết giới thiệu</span>
          <span v-if="(profile.post_count || 0) === 0" class="pc-hint">Đăng bài đầu tiên</span>
          <span v-if="(profile.review_count || 0) === 0" class="pc-hint">Viết đánh giá</span>
        </div>
      </div>

      <div v-if="isSelf && Object.keys(userStats).length" class="profile-analytics card reveal">
        <h3 class="pa-title">Tổng quan hoạt động</h3>
        <div class="pa-grid">
          <div class="pa-stat">
            <strong>{{ userStats.likes_received || 0 }}</strong>
            <span>lượt thích nhận</span>
          </div>
          <div class="pa-stat">
            <strong>{{ userStats.reactions_received || 0 }}</strong>
            <span>reactions nhận</span>
          </div>
          <div class="pa-stat">
            <strong>{{ userStats.entities_reviewed || 0 }}</strong>
            <span>nơi đã đánh giá</span>
          </div>
          <div class="pa-stat">
            <strong>{{ userStats.collections || 0 }}</strong>
            <span>danh sách</span>
          </div>
          <div v-if="profile.view_count_7d != null" class="pa-stat">
            <strong>{{ profile.view_count_7d }}</strong>
            <span>lượt xem tuần này</span>
          </div>
        </div>
      </div>

      <div v-if="profile.is_private" class="profile-private-notice">
        <p>🔒 Hồ sơ riêng tư — theo dõi để xem nội dung.</p>
      </div>

      <div v-else class="profile-tabs" role="tablist" aria-label="Nội dung người dùng" @keydown="onProfileTabKeydown">
        <button type="button" id="profile-tab-posts" role="tab" :class="['chip', { active: tab === 'posts' }]" :aria-selected="tab === 'posts'" aria-controls="profile-panel-posts" :tabindex="tab === 'posts' ? 0 : -1" @click="setProfileTab('posts')">Bài viết</button>
        <button type="button" id="profile-tab-reviews" role="tab" :class="['chip', { active: tab === 'reviews' }]" :aria-selected="tab === 'reviews'" aria-controls="profile-panel-reviews" :tabindex="tab === 'reviews' ? 0 : -1" @click="setProfileTab('reviews')">Đánh giá</button>
        <button type="button" id="profile-tab-timeline" role="tab" :class="['chip', { active: tab === 'timeline' }]" :aria-selected="tab === 'timeline'" aria-controls="profile-panel-timeline" :tabindex="tab === 'timeline' ? 0 : -1" @click="setProfileTab('timeline')">Hoạt động</button>
        <button type="button" id="profile-tab-saved" role="tab" v-if="isSelf" :class="['chip', { active: tab === 'saved' }]" :aria-selected="tab === 'saved'" aria-controls="profile-panel-saved" :tabindex="tab === 'saved' ? 0 : -1" @click="setProfileTab('saved')">
          Đã lưu<ClientOnly><span v-if="savedCount > 0" class="tab-count">{{ savedCount }}</span></ClientOnly>
        </button>
        <button type="button" id="profile-tab-collections" role="tab" v-if="isSelf" :class="['chip', { active: tab === 'collections' }]" :aria-selected="tab === 'collections'" aria-controls="profile-panel-collections" :tabindex="tab === 'collections' ? 0 : -1" @click="setProfileTab('collections')">
          Danh sách<ClientOnly><span v-if="collectionsCount > 0" class="tab-count">{{ collectionsCount }}</span></ClientOnly>
        </button>
      </div>

      <div v-if="!profile.is_private" class="feed-main reveal" role="tabpanel" :id="activePanelId" :aria-labelledby="activeTabId" tabindex="0">
        <!-- Đã lưu (self only, client-only — từ localStorage) -->
        <ClientOnly v-if="tab === 'saved' && isSelf">
          <div v-if="favorites.length" class="saved-grid">
            <NuxtLink v-for="fav in favorites" :key="fav.id" :to="savedItemPath(fav)" class="card saved-card">
              <div v-if="fav.image" class="cover cover-img">
                <img :src="fav.image" :alt="fav.name" loading="lazy" decoding="async" width="400" height="160" @error="(e: Event) => ((e.target as HTMLImageElement).style.opacity = '.15')" />
              </div>
              <div class="card-b">
                <span class="card-type">{{ getSavedTypeMeta(fav.type).label }}</span>
                <h3>{{ fav.name }}</h3>
                <p v-if="fav.place_name" class="place">{{ fav.place_name }}</p>
              </div>
            </NuxtLink>
          </div>
          <div v-if="favorites.length" class="saved-cta">
            <NuxtLink to="/tao-lich-trinh" no-prefetch class="btn btn-primary btn-sm">📋 Tạo lịch trình từ danh sách đã lưu</NuxtLink>
          </div>
          <EmptyState
            v-else
            icon="❤️"
            title="Chưa lưu địa điểm nào"
            message="Lưu địa điểm yêu thích để xem lại nhanh và ghép vào lịch trình."
            hint="Nhấn nút lưu ở bất kỳ địa điểm nào để bắt đầu."
          >
            <NuxtLink to="/du-lich" class="btn btn-primary btn-sm">Khám phá địa điểm</NuxtLink>
          </EmptyState>
        </ClientOnly>

        <!-- Danh sách (collections, self only, client-only — dữ liệu từ server) -->
        <ClientOnly v-else-if="tab === 'collections' && isSelf">
          <div v-if="collectionsLoading" class="collections-loading" role="status" aria-label="Đang tải"><div class="spinner spinner-sm"></div> Đang tải...</div>
          <template v-else>
            <div class="collections-header">
              <button type="button" class="btn btn-primary btn-sm" @click="showCreateCollection = true">+ Tạo danh sách</button>
            </div>
            <div v-if="userCollections.length" class="saved-grid">
              <div v-for="c in userCollections" :key="c.id" class="card saved-card">
                <div class="card-b">
                  <span class="card-type">{{ c.is_public ? 'Công khai' : 'Riêng tư' }}</span>
                  <h3>{{ c.name }}</h3>
                  <p v-if="c.description" class="place">{{ c.description }}</p>
                  <p class="place">{{ c.item_count || 0 }} bài viết</p>
                </div>
                <button type="button" class="btn btn-ghost btn-sm btn-danger-text" @click="handleDeleteCollection(c.id, c.name)">Xóa</button>
              </div>
            </div>
            <EmptyState
              v-else
              icon="🗂️"
              title="Chưa có danh sách nào"
              message="Tạo danh sách để sắp xếp bài viết yêu thích theo chủ đề."
              hint="Nhấn “+ Tạo danh sách” để bắt đầu."
            />
          </template>

          <!-- Tạo danh sách mới -->
          <Transition name="modal-fade">
            <div v-if="showCreateCollection" class="modal-overlay show" @click.self="closeCreateCollection">
              <div class="modal" role="dialog" aria-modal="true" aria-labelledby="create-collection-title" ref="createCollectionModalEl">
                <div class="modal-head">
                  <h2 id="create-collection-title">Tạo danh sách mới</h2>
                  <button type="button" class="modal-close" aria-label="Đóng" @click="closeCreateCollection">✕</button>
                </div>
                <div class="modal-body">
                  <form @submit.prevent="handleCreateCollection">
                    <label class="sf-field">
                      <span class="sf-label">Tên</span>
                      <input v-model="newCollectionName" type="text" class="sf-input" maxlength="100" required placeholder="VD: Quán ngon Vĩnh Long" />
                    </label>
                    <label class="sf-field">
                      <span class="sf-label">Mô tả (không bắt buộc)</span>
                      <textarea v-model="newCollectionDesc" class="sf-input" maxlength="300" rows="2"></textarea>
                    </label>
                    <div class="sf-actions">
                      <button type="button" class="btn btn-ghost" @click="closeCreateCollection">Hủy</button>
                      <button type="submit" class="btn btn-primary" :disabled="creatingCollection || !newCollectionName.trim()">{{ creatingCollection ? 'Đang tạo...' : 'Tạo' }}</button>
                    </div>
                  </form>
                </div>
              </div>
            </div>
          </Transition>
        </ClientOnly>

        <!-- Hoạt động (timeline — bài viết, đánh giá, theo dõi) -->
        <template v-else-if="tab === 'timeline'">
          <div v-if="timelineLoading && !timelineItems.length" class="profile-loading" role="status" aria-label="Đang tải">
            <div class="spinner"></div>
          </div>
          <div v-else-if="timelineItems.length" class="timeline-feed">
            <article v-for="item in timelineItems" :key="item.type + '-' + (item.data?.id || item.data?.target_id) + '-' + item.created_at" class="timeline-item">
              <span class="tl-icon" aria-hidden="true">{{ timelineIcon(item.type) }}</span>
              <div class="tl-body">
                <p class="tl-text">
                  <template v-if="item.type === 'post'">
                    Đã đăng bài{{ item.data.entity_name ? ` về ${item.data.entity_name}` : '' }}
                  </template>
                  <template v-else-if="item.type === 'review'">
                    Đã đánh giá <strong>{{ item.data.entity_name || 'địa điểm' }}</strong>
                    <span v-if="item.data.rating" class="tl-rating">{{ '⭐'.repeat(Math.min(item.data.rating, 5)) }}</span>
                  </template>
                  <template v-else-if="item.type === 'follow'">
                    Đã theo dõi <strong>{{ item.data.target_name }}</strong>
                  </template>
                </p>
                <p v-if="item.data?.content" class="tl-preview">{{ item.data.content }}</p>
                <time class="tl-time" :datetime="item.created_at">{{ timeAgo(item.created_at) }}</time>
              </div>
            </article>
          </div>
          <EmptyState v-else icon="📅" title="Chưa có hoạt động" message="Hoạt động sẽ hiện khi người dùng tương tác trên cộng đồng." />
          <div v-if="timelineLoading && timelineItems.length" class="profile-loading" role="status"><div class="spinner"></div></div>
          <div ref="timelineSentinel" style="height:1px" />
        </template>

        <template v-else>
          <TransitionGroup name="post-list" tag="div">
            <PostCard
              v-for="post in filteredPosts"
              :key="post.id"
              :post="post"
              @like="toggleLike"
              @comment="id => navigateTo(postPath(id))"
              @bookmark="toggleBookmark"
              @report="reportPost"
              @repost="repost"
              @quote="quote"
              @edit="(id) => navigateTo(`${postPath(id)}?edit=1`)"
              @delete="deletePost"
            />
          </TransitionGroup>
          <EmptyState
            v-if="postsFetchFailed && !filteredPosts.length && !loading"
            icon="⚠️" tone="error" title="Không thể tải bài viết" message="Lỗi kết nối. Vui lòng thử lại."
          >
            <button type="button" class="btn btn-outline btn-sm" @click="fetchPosts">Thử lại</button>
          </EmptyState>
          <Transition name="fade">
            <EmptyState
              v-if="!postsFetchFailed && !filteredPosts.length && !loading"
              :icon="tab === 'reviews' ? '⭐' : '✍️'"
              :title="tab === 'reviews' ? 'Chưa có đánh giá' : 'Chưa có bài viết'"
              :message="tab === 'reviews' ? 'Chưa có đánh giá nào.' : 'Chưa có bài viết nào.'"
              :hint="emptyHint"
            >
              <NuxtLink v-if="isSelf" to="/cong-dong" class="btn btn-primary btn-sm">
                {{ tab === 'reviews' ? 'Viết đánh giá đầu tiên' : 'Viết bài viết đầu tiên' }}
              </NuxtLink>
            </EmptyState>
          </Transition>
          <SkeletonList v-if="loading && !posts.length" :count="3" class="profile-skeleton" />
          <div v-else-if="loading" class="profile-loading" role="status" aria-label="Đang tải"><div class="spinner"></div></div>
        </template>
      </div>
    </div>

    <EmptyState v-else-if="profileFetchFailed" icon="⚠️" tone="error" title="Không thể tải trang" message="Lỗi kết nối. Vui lòng thử lại.">
      <button type="button" class="btn btn-outline btn-sm" @click="refreshProfile()">Thử lại</button>
    </EmptyState>
    <EmptyState v-else-if="profileNotFound" icon="👤" title="Không tìm thấy người dùng" message="Hồ sơ này không tồn tại hoặc đã được đổi tên." />
    <EmptyState v-else message="Không tìm thấy người dùng." />

    <!-- Modal danh sách theo dõi -->
    <Teleport to="body">
      <div v-if="followModalOpen" class="fm-overlay" @click.self="followModalOpen = false" @keydown.escape="followModalOpen = false">
        <div class="fm-dialog" role="dialog" aria-modal="true" aria-label="Danh sách theo dõi" tabindex="-1" ref="followDialogEl">
          <header class="fm-head">
            <div class="fm-tabs" role="tablist" aria-label="Danh sách theo dõi">
              <button type="button" role="tab" :class="['fm-tab', { active: followModalTab === 'followers' }]" :aria-selected="followModalTab === 'followers'" @click="followModalTab = 'followers'">Người theo dõi</button>
              <button type="button" role="tab" :class="['fm-tab', { active: followModalTab === 'following' }]" :aria-selected="followModalTab === 'following'" @click="followModalTab = 'following'">Đang theo dõi</button>
            </div>
            <button type="button" class="fm-close" aria-label="Đóng" @click="followModalOpen = false">&times;</button>
          </header>
          <div class="fm-body">
            <div v-if="followLoadingList" class="fm-loading" role="status" aria-label="Đang tải danh sách"><div class="spinner spinner-sm"></div></div>
            <template v-else>
              <ul v-if="followModalList.length" class="fm-list">
                <li v-for="u in followModalList" :key="u.id">
                  <NuxtLink :to="userPath(u.username || u.id)" class="fm-user" @click="followModalOpen = false">
                    <span class="avatar fm-avatar">{{ (u.display_name || '?').charAt(0).toUpperCase() }}</span>
                    <span class="fm-name">{{ u.display_name }}</span>
                  </NuxtLink>
                </li>
              </ul>
              <p v-else class="fm-empty">{{ followModalTab === 'followers' ? 'Chưa có người theo dõi.' : 'Chưa theo dõi ai.' }}</p>
            </template>
          </div>
        </div>
      </div>
    </Teleport>
  </section>
</template>

<script setup lang="ts">
import { TYPE_META } from '~/composables/useConstants'
type ProfileView = Record<string, any> & {
  id?: string
  username?: string
  display_name?: string
  phone?: string
  bio?: string
  avatar?: string | null
  avatar_url?: string | null
  cover_url?: string | null
  created_at?: string
  post_count?: number
  review_count?: number
  follower_count?: number
  following_count?: number
}
type ProfilePayload = {
  profile: ProfileView | null
  status: 'ok' | 'not-found' | 'error'
}
type ProfileTab = 'posts' | 'reviews' | 'timeline' | 'saved' | 'collections'
useReveal()
const route = useRoute()
const userId = computed(() => {
  const id = route.params.id
  return Array.isArray(id) ? String(id[0] || '') : String(id || '')
})
const { user: currentUser, isLoggedIn, authHeaders, handleSessionExpired } = useAuth()
const { show: showToast } = useToast()
const { reportPost, openReport } = useReport()
const { repost, quote } = useRepost()
const { filterCommunityPosts } = useCommunityPostFilters<any>()

const validProfileTabs = new Set<ProfileTab>(['posts', 'reviews', 'timeline', 'saved', 'collections'])
function normalizeProfileTab(value: unknown): ProfileTab {
  const raw = Array.isArray(value) ? value[0] : value
  return validProfileTabs.has(raw as ProfileTab) ? raw as ProfileTab : 'posts'
}
const tab = ref<ProfileTab>(normalizeProfileTab(route.query.tab))
const posts = ref<any[]>([])
const { favorites, count: savedCount } = useFavorites()
const loading = ref(true)
const isFollowing = ref(false)
const followLoading = ref(false)
const followerCount = ref<number | null>(null)

// ── Danh sách (collections) ──
const { collections: userCollections, loading: collectionsLoading, fetchCollections, createCollection, deleteCollection } = useCollections()
const collectionsCount = computed(() => userCollections.value.length)
const showCreateCollection = ref(false)
const newCollectionName = ref('')
const newCollectionDesc = ref('')
const creatingCollection = ref(false)
const createCollectionModalEl = ref<HTMLElement | null>(null)
useModalA11y(showCreateCollection, createCollectionModalEl, { onClose: () => { showCreateCollection.value = false } })

function closeCreateCollection() {
  showCreateCollection.value = false
}

async function handleCreateCollection() {
  if (!newCollectionName.value.trim() || creatingCollection.value) return
  creatingCollection.value = true
  try {
    await createCollection(newCollectionName.value.trim(), newCollectionDesc.value.trim())
    showCreateCollection.value = false
    newCollectionName.value = ''
    newCollectionDesc.value = ''
  } catch { /* toast đã hiển thị trong composable */ }
  creatingCollection.value = false
}

async function handleDeleteCollection(id: string, name: string) {
  const ok = await confirmDialog(`Xoá danh sách "${name}"? Hành động không thể hoàn tác.`, { title: 'Xoá danh sách?', confirmText: 'Xoá', danger: true })
  if (!ok) return
  try { await deleteCollection(id) } catch { /* toast đã hiển thị trong composable */ }
}

watch(tab, (t) => {
  if (t === 'collections' && isSelf.value && !userCollections.value.length) fetchCollections()
})

function mapProfileView(u: Record<string, any>): ProfileView {
  const stats = u.stats || {}
  return {
    ...u,
    avatar: u.avatar_url ?? u.avatar ?? null,
    post_count: stats.posts ?? u.post_count ?? 0,
    review_count: stats.reviews ?? u.review_count ?? 0,
    follower_count: stats.followers ?? u.follower_count ?? 0,
    following_count: stats.following ?? u.following_count ?? 0,
  }
}

const { data: profileState, refresh: refreshProfile } = await useAsyncData<ProfilePayload>(`public-user-${userId.value}`, async () => {
  const lookup = userId.value.trim()
  if (!lookup) return { profile: null, status: 'not-found' }
  try {
    const res = await apiFetch<Record<string, any>>(`/api/users/${encodeURIComponent(lookup)}`, { headers: authHeaders() })
    const u = (res?.user ?? res) as Record<string, any> | null
    if (!u || (!u.id && !u.username)) return { profile: null, status: 'not-found' }
    return { profile: mapProfileView(u), status: 'ok' }
  } catch (e: unknown) {
    return { profile: null, status: getStatusCode(e) === 404 ? 'not-found' : 'error' }
  }
}, {
  default: (): ProfilePayload => ({ profile: null, status: 'error' }),
})

const profilePayload = computed(() => profileState.value as ProfilePayload | null | undefined)
const profile = computed(() => profilePayload.value?.profile ?? null)
const profileLoadStatus = computed(() => profilePayload.value?.status ?? 'error')
const profileFetchFailed = computed(() => profileLoadStatus.value === 'error')
const profileNotFound = computed(() => profileLoadStatus.value === 'not-found')
if (import.meta.server && profileNotFound.value) setResponseStatus(404)

const profileSlug = computed(() => profile.value?.username || userId.value)
const publicProfilePath = computed(() => `/nguoi-dung/${encodeURIComponent(profileSlug.value)}`)

useHead({
  link: computed(() => [{ rel: 'canonical', href: canonicalUrl(publicProfilePath.value) }]),
  meta: [{ name: 'robots', content: 'noindex,follow' }],
})

const isSelf = computed(() => {
  const me = currentUser.value
  if (!me) return false
  const profileUsername = profile.value?.username
  return String(me.id) === profileId.value || (!!profileUsername && me.username === profileUsername) || me.username === userId.value
})
const profileId = computed(() => String(profile.value?.id || userId.value))
const encodedProfileId = computed(() => encodeURIComponent(profileId.value))
const displayFollowerCount = computed(() => followerCount.value ?? profile.value?.follower_count ?? 0)
const profileHandle = computed(() => profile.value?.username ? `@${profile.value.username}` : '')
const totalContributions = computed(() => (profile.value?.post_count || 0) + (profile.value?.review_count || 0))
const activitySummary = computed(() => {
  if (totalContributions.value === 0) {
    return isSelf.value ? 'Bắt đầu chia sẻ trải nghiệm đầu tiên' : 'Thành viên mới, chưa có đóng góp công khai'
  }
  return `${totalContributions.value} đóng góp công khai`
})
const visibleProfileTabs = computed<ProfileTab[]>(() => {
  const tabs: ProfileTab[] = ['posts', 'reviews', 'timeline']
  if (isSelf.value) tabs.push('saved', 'collections')
  return tabs
})
const activeTabId = computed(() => `profile-tab-${tab.value}`)
const activePanelId = computed(() => `profile-panel-${tab.value}`)

function normalizeVisibleProfileTab(value: unknown): ProfileTab {
  const next = normalizeProfileTab(value)
  return (next === 'saved' || next === 'collections') && !isSelf.value ? 'posts' : next
}

const initial = computed(() => {
  const name = profile.value?.display_name || profile.value?.phone || '?'
  return name.charAt(0).toUpperCase()
})

const joinDate = computed(() => formatDateVN(profile.value?.created_at))

const profileCompletion = computed(() => {
  if (!profile.value) return 0
  const p = profile.value
  const checks = [p.display_name, p.avatar, p.bio, p.cover_url, (p.post_count || 0) > 0, (p.review_count || 0) > 0]
  return Math.round((checks.filter(Boolean).length / checks.length) * 100)
})

const filteredPosts = computed(() => {
  if (tab.value === 'reviews') return posts.value.filter(p => p.post_type === 'review')
  return posts.value
})

const getSavedTypeMeta = getTypeMeta

const displayName = computed(() => profile.value?.display_name || profile.value?.phone || 'Người dùng')
const emptyHint = computed(() => {
  if (isSelf.value) return 'Chia sẻ trải nghiệm của bạn với cộng đồng.'
  return `Theo dõi ${displayName.value} để nhận cập nhật mới.`
})

// ── Hoạt động (timeline — bài viết, đánh giá, theo dõi) ──
const { timeAgo } = useTimeAgo()
const timelineItems = ref<Array<{ type: string; created_at: string; data: Record<string, any> }>>([])
const timelineLoading = ref(false)
const timelinePage = ref(1)
const timelineHasMore = ref(true)

function timelineIcon(type: string): string {
  switch (type) {
    case 'post': return '✍️'
    case 'review': return '⭐'
    case 'follow': return '👥'
    default: return '📌'
  }
}

async function loadTimeline() {
  if (timelineLoading.value || !timelineHasMore.value || !profile.value) return
  timelineLoading.value = true
  try {
    const res = await $fetch<{ items: typeof timelineItems.value; has_more: boolean }>(`/api/users/${encodedProfileId.value}/timeline`, {
      params: { page: timelinePage.value, limit: 20 },
      headers: authHeaders(),
    })
    timelineItems.value.push(...(res.items || []))
    timelineHasMore.value = res.has_more
    timelinePage.value++
  } catch {
    /* im lặng bỏ qua — timeline chỉ là bổ sung */
  } finally {
    timelineLoading.value = false
  }
}

const { sentinel: timelineSentinel } = useInfiniteScroll(loadTimeline, { enabled: computed(() => tab.value === 'timeline' && timelineHasMore.value) })

watch(tab, (t) => {
  if (t === 'timeline' && !timelineItems.value.length) loadTimeline()
})

const postsFetchFailed = ref(false)
async function fetchPosts() {
  if (!profile.value || profile.value.is_private) {
    posts.value = []
    loading.value = false
    return
  }
  loading.value = true
  postsFetchFailed.value = false
  try {
    const res = await $fetch<Record<string, unknown>>(`/api/users/${encodedProfileId.value}/posts?limit=50`, { headers: authHeaders() })
    const list = res?.posts
    posts.value = Array.isArray(list) ? filterCommunityPosts(list as any[]) : []
  } catch (e: unknown) {
    postsFetchFailed.value = true
    if (getStatusCode(e) === 401) { handleSessionExpired(); return }
    showToast('Không thể tải bài viết', 'error')
  } finally {
    loading.value = false
  }
}

const { toggleLike: _like, toggleBookmark: _bookmark, deletePost: _delete } = usePostActions()

function toggleLike(pid: string) {
  const p = posts.value.find(x => x.id === pid)
  if (p) _like(pid, p)
}
function toggleBookmark(pid: string) {
  const p = posts.value.find(x => x.id === pid)
  if (p) _bookmark(pid, p)
}
function deletePost(pid: string) {
  _delete(pid, () => { posts.value = posts.value.filter(x => x.id !== pid) })
}


// ── Modal danh sách follower/following ──
const followModalOpen = ref(false)
const followModalTab = ref<'followers' | 'following'>('followers')
const followLists = ref<{ followers: any[] | null; following: any[] | null }>({ followers: null, following: null })
const followLoadingList = ref(false)
const followModalList = computed(() => followLists.value[followModalTab.value] || [])
async function loadFollowList(which: 'followers' | 'following') {
  if (!profile.value) return
  if (followLists.value[which]) return  // đã tải (cache)
  followLoadingList.value = true
  try {
    const res = await $fetch<any>(`/api/users/${encodedProfileId.value}/${which}`, { headers: authHeaders() })
    followLists.value[which] = res.users || []
  } catch (e: unknown) {
    followLists.value[which] = []
    if (getStatusCode(e) === 401) { handleSessionExpired(); return }
    showToast('Không thể tải danh sách', 'error')
  } finally {
    followLoadingList.value = false
  }
}
const followDialogEl = ref<HTMLElement | null>(null)
function closeFollowModal() { followModalOpen.value = false }
useModalA11y(followModalOpen, followDialogEl, { onClose: closeFollowModal })
function openFollowModal(tab: 'followers' | 'following') {
  followModalTab.value = tab
  followModalOpen.value = true
  loadFollowList(tab)
}
watch(followModalTab, (t) => loadFollowList(t))

async function checkFollowing() {
  if (!isLoggedIn.value || !profile.value) return
  try {
    const res = await $fetch<{ following: boolean }>(`/api/follow/check/user/${encodedProfileId.value}`, { headers: authHeaders() })
    isFollowing.value = res.following
  } catch { /* non-critical */ }
}

// ── Thống kê hoạt động (chỉ hồ sơ của mình) ──
const userStats = ref<Record<string, number>>({})
const statsLoading = ref(false)
async function loadUserStats() {
  if (!isSelf.value) return
  statsLoading.value = true
  try {
    userStats.value = await $fetch<Record<string, number>>('/api/me/stats', { headers: authHeaders() })
  } catch { /* non-critical */ }
  statsLoading.value = false
}

// ── Huy hiệu + tiến độ (chỉ hồ sơ của mình) ──
type BadgeProgress = { id: string; label: string; icon: string; earned: boolean; current: number; target: number; hint?: string }
const badgeProgress = ref<BadgeProgress[]>([])
const earnedBadgeCount = computed(() => badgeProgress.value.filter(b => b.earned).length)

async function loadBadgeProgress() {
  if (!isSelf.value) return
  try {
    const res = await $fetch<{ badges: BadgeProgress[] }>('/api/me/badge-progress', { headers: authHeaders() })
    badgeProgress.value = res.badges || []
  } catch { /* non-critical */ }
}

function setProfileTab(next: ProfileTab) {
  tab.value = normalizeVisibleProfileTab(next)
}

function onProfileTabKeydown(event: KeyboardEvent) {
  const keys = ['ArrowLeft', 'ArrowRight', 'Home', 'End']
  if (!keys.includes(event.key)) return
  event.preventDefault()
  const tabs = visibleProfileTabs.value
  const current = Math.max(0, tabs.indexOf(tab.value))
  const firstTab = tabs[0] || 'posts'
  const lastTab = tabs[tabs.length - 1] || firstTab
  const next: ProfileTab = event.key === 'Home'
    ? firstTab
    : event.key === 'End'
      ? lastTab
      : event.key === 'ArrowRight'
        ? tabs[(current + 1) % tabs.length] || firstTab
        : tabs[(current - 1 + tabs.length) % tabs.length] || firstTab
  setProfileTab(next)
  nextTick(() => document.getElementById(`profile-tab-${next}`)?.focus())
}

watch(tab, (t) => {
  const query = { ...route.query }
  if (t === 'posts') delete query.tab
  else query.tab = t
  navigateTo({ path: route.path, query }, { replace: true })
})

watch(() => route.query.tab, (value) => {
  const next = normalizeVisibleProfileTab(value)
  if (next !== tab.value) setProfileTab(next)
})

watch([isSelf, tab], ([self, active]) => {
  if (!self && (active === 'saved' || active === 'collections')) tab.value = 'posts'
}, { immediate: true })

async function toggleFollow() {
  if (!isLoggedIn.value) { showToast('Đăng nhập để theo dõi', 'info'); return }
  if (!profile.value) return
  followLoading.value = true
  const was = isFollowing.value
  isFollowing.value = !was
  followerCount.value = Math.max(0, displayFollowerCount.value + (was ? -1 : 1))
  try {
    await $fetch(`/api/follow/user/${encodedProfileId.value}`, { method: 'POST', headers: authHeaders() })
    followLists.value = { followers: null, following: null }
  } catch (e: unknown) {
    isFollowing.value = was
    followerCount.value = Math.max(0, displayFollowerCount.value + (was ? 1 : -1))
    if (getStatusCode(e) === 401) { handleSessionExpired(); return }
    showToast('Không thể theo dõi', 'error')
  } finally {
    followLoading.value = false
  }
}

// ── Block / Report ──
const showMoreMenu = ref(false)
const isBlocked = ref(false)
const { confirmDialog } = useConfirm()

function syncViewerRelationship(p: ProfileView | null) {
  const relationship = p?.viewer_relationship || {}
  if (typeof relationship.is_following === 'boolean') isFollowing.value = relationship.is_following
  if (typeof relationship.is_blocked === 'boolean') isBlocked.value = relationship.is_blocked
  followerCount.value = null
}

watch(profile, syncViewerRelationship, { immediate: true })

function onClickOutsideMore(e: MouseEvent) {
  const wrap = (e.target as HTMLElement)?.closest('.profile-more-wrap')
  if (!wrap) showMoreMenu.value = false
}
watch(showMoreMenu, (v) => {
  if (import.meta.client) {
    if (v) setTimeout(() => document.addEventListener('click', onClickOutsideMore), 0)
    else document.removeEventListener('click', onClickOutsideMore)
  }
})
onUnmounted(() => document.removeEventListener('click', onClickOutsideMore))

async function checkBlocked() {
  if (!isLoggedIn.value || isSelf.value || !profile.value) return
  try {
    const res = await $fetch<{ blocked: any[] }>('/api/blocked-users', { headers: authHeaders() })
    isBlocked.value = (res.blocked || []).some(u => u.id === profileId.value)
  } catch { /* non-critical */ }
}

async function toggleBlock() {
  if (!profile.value) return
  if (isBlocked.value) {
    try {
      await $fetch(`/api/block/${encodedProfileId.value}`, { method: 'POST', headers: authHeaders() })
      isBlocked.value = false
      showToast('Đã bỏ chặn', 'success')
    } catch (e: unknown) {
      if (getStatusCode(e) === 401) { handleSessionExpired(); return }
      showToast('Không thể bỏ chặn', 'error')
    }
    return
  }
  const ok = await confirmDialog(
    'Họ sẽ không thấy bài viết, bình luận và hoạt động của bạn. Bạn cũng sẽ không thấy nội dung của họ.',
    {
      title: `Chặn ${profile.value?.display_name || 'người dùng này'}?`,
      confirmText: 'Chặn',
      danger: true,
    },
  )
  if (!ok) return
  try {
    await $fetch(`/api/block/${encodedProfileId.value}`, { method: 'POST', headers: authHeaders() })
    isBlocked.value = true
    if (isFollowing.value) { isFollowing.value = false; followerCount.value = Math.max(0, displayFollowerCount.value - 1) }
    showToast('Đã chặn người dùng', 'success')
  } catch (e: unknown) {
    if (getStatusCode(e) === 401) { handleSessionExpired(); return }
    showToast('Không thể chặn', 'error')
  }
}

function reportUser() {
  if (!profile.value) return
  showMoreMenu.value = false
  openReport('user', profileId.value)
}

async function shareProfile() {
  const url = `${window.location.origin}${publicProfilePath.value}`
  const name = profile.value?.display_name || 'Người dùng'
  if (navigator.share) {
    try { await navigator.share({ title: `${name} — vinhlong360`, url }) } catch {}
  } else {
    try {
      await navigator.clipboard.writeText(url)
      showToast('Đã sao chép liên kết hồ sơ', 'success')
    } catch { showToast('Không thể sao chép', 'error') }
  }
}

onMounted(() => {
  fetchPosts()
  checkFollowing()
  checkBlocked()
  if (isSelf.value) { loadUserStats(); loadBadgeProgress() }
  if (tab.value === 'collections' && isSelf.value) fetchCollections()
})

watch(userId, async () => {
  tab.value = 'posts'
  posts.value = []
  loading.value = true
  isFollowing.value = false
  isBlocked.value = false
  followerCount.value = null
  followLists.value = { followers: null, following: null }
  timelineItems.value = []
  timelinePage.value = 1
  timelineHasMore.value = true
  await refreshProfile()
  fetchPosts()
  checkFollowing()
  checkBlocked()
})

useSeoMeta({
  title: () => `${profile.value?.display_name || 'Người dùng'} — vinhlong360`,
  description: () => `Trang cá nhân của ${profile.value?.display_name || 'thành viên'} trên cộng đồng vinhlong360.`,
  ogTitle: () => `${profile.value?.display_name || 'Người dùng'} — vinhlong360`,
  ogDescription: () => `Trang cá nhân của ${profile.value?.display_name || 'thành viên'} trên cộng đồng vinhlong360.`,
  ogImage: () => entityOgImage([profile.value?.cover_url || profile.value?.avatar].filter(Boolean) as string[]),
  robots: 'noindex,follow',
})
</script>

<style scoped>
.profile-reputation { display: flex; flex-wrap: wrap; gap: .4rem; margin: .25rem 0 .75rem; }
.rep-level { font-weight: var(--weight-semibold); font-size: var(--text-sm); padding: .2rem .6rem; border-radius: 999px; background: color-mix(in srgb, var(--accent) 16%, var(--bg-alt)); color: var(--accent-text, var(--ink)); text-decoration: none; transition: filter .2s; }
.rep-level:hover { filter: brightness(1.1); }
.rep-level[data-level="4"] { background: color-mix(in srgb, gold 28%, var(--bg-alt)); }
.rep-badge { font-size: var(--text-xs); padding: .2rem .55rem; border-radius: 999px; background: var(--bg-alt); border: 1px solid var(--border); color: var(--ink-700); }
.profile-loading { text-align: center; padding: var(--space-5) 0; }
.profile-loading .spinner { margin: 0 auto; }

/* Huy hiệu + tiến độ (badge showcase, chỉ hồ sơ của mình) */
.badge-showcase { margin: var(--space-3) 0; }
.bs-title { font-weight: var(--weight-semibold); font-size: var(--text-sm); cursor: pointer; padding: var(--space-2) 0; color: var(--ink); }
.bs-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: var(--space-2); margin-top: var(--space-2); }
.bs-card { padding: var(--space-2); border-radius: var(--radius); border: 1px solid var(--line); text-align: center; background: var(--surface); }
.bs-card:not(.earned) { opacity: .6; }
.bs-card.earned { border-color: var(--primary); }
.bs-icon { font-size: 1.5rem; display: block; margin-bottom: var(--space-1); }
.bs-label { font-size: var(--text-sm); font-weight: var(--weight-medium); color: var(--ink); }
.bs-progress { margin-top: var(--space-1); }
.bs-bar { height: 4px; background: var(--line); border-radius: 2px; overflow: hidden; }
.bs-fill { height: 100%; background: var(--primary); border-radius: 2px; transition: width .3s ease; }
.bs-hint { font-size: var(--text-xs); color: var(--muted); }
.bs-earned-label { font-size: var(--text-xs); color: var(--success); font-weight: var(--weight-medium); }

.profile-cover { position: relative; border-radius: var(--radius-xl, 20px); overflow: hidden; margin-bottom: calc(-1 * var(--space-8)); box-shadow: var(--shadow-lg, var(--shadow-md)); }
.cover-img { width: 100%; height: 200px; object-fit: cover; display: block; background: linear-gradient(90deg, var(--bg-alt) 25%, var(--line) 37%, var(--bg-alt) 63%); background-size: 400% 100%; animation: coverShimmer 1.4s ease infinite; }
.cover-img[src] { animation: none; }
@keyframes coverShimmer { 0% { background-position: 100% 0; } 100% { background-position: -100% 0; } }
.profile-private-notice { text-align: center; padding: var(--space-8) var(--space-4); color: var(--ink-700); font-size: .95rem; }
.cover-scrim { position: absolute; inset: 0; pointer-events: none; background: linear-gradient(to bottom, transparent 40%, rgba(0,0,0,.18)); }
.dark .cover-scrim { background: linear-gradient(to bottom, transparent 30%, rgba(0,0,0,.45)); }
.profile-avatar-wrap { position: absolute; bottom: calc(-1 * var(--space-6)); left: var(--space-5); z-index: 1; }
.profile-avatar-wrap .avatar { border: 6px solid var(--card); box-shadow: 0 0 0 2px var(--line), 0 8px 28px rgba(0,0,0,.12); transition: transform .35s var(--ease-spring-gentle); }
.profile-avatar-wrap .avatar:hover { transform: scale(1.05); }
.profile-avatar-wrap .avatar:active { transform: scale(.98); transition-duration: .08s; }

.profile-info { padding-top: var(--space-10); }
.user-profile-page { max-width: 680px; margin: 0 auto; }
.profile-name-row { display: flex; align-items: center; gap: var(--space-3); flex-wrap: wrap; }
.profile-name-row h1 { flex: 1; min-width: 0; }
.profile-meta-row { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-2); margin-top: var(--space-2); }
.profile-handle { color: var(--muted); font-size: var(--text-sm); font-weight: var(--weight-semibold); overflow-wrap: anywhere; }
.profile-chip { display: inline-flex; align-items: center; min-height: 28px; padding: 0 var(--space-3); border-radius: var(--radius-full); border: 1px solid var(--line); background: var(--card); color: var(--ink-700); font-size: var(--text-xs); font-weight: var(--weight-semibold); }
.profile-chip.is-public { border-color: color-mix(in srgb, var(--success, #2e7d5b) 28%, var(--line)); color: var(--success, #2e7d5b); }
.profile-chip.is-private { border-color: color-mix(in srgb, var(--warning, #b7791f) 28%, var(--line)); color: var(--warning, #b7791f); }
.profile-chip.is-self,
.profile-chip.is-following { background: color-mix(in srgb, var(--primary) 10%, var(--card)); border-color: color-mix(in srgb, var(--primary) 30%, var(--line)); color: var(--primary); }
.profile-more-wrap { position: relative; }
.btn-icon { min-width: 44px; padding: .3rem .5rem; letter-spacing: 2px; font-weight: 700; }
.profile-more-menu { position: absolute; right: 0; top: 100%; margin-top: var(--space-1); background: var(--card); border: 1px solid var(--line); border-radius: var(--radius-md); box-shadow: var(--shadow-md); z-index: var(--z-dropdown); min-width: 160px; overflow: hidden; }
.pm-item { display: block; width: 100%; text-align: left; padding: .6rem 1rem; border: none; background: none; font: inherit; font-size: var(--text-sm); color: var(--ink); cursor: pointer; transition: background .15s; }
.pm-item:hover { background: var(--bg-alt); }
.pm-danger { color: var(--danger, #c0392b); }
.pm-danger:hover { background: rgba(192,57,43,.06); }
.profile-info h1 { font-size: clamp(1.25rem, 2.5vw, 1.75rem); font-weight: var(--weight-bold); letter-spacing: var(--tracking-tight); margin: 0; text-wrap: balance; overflow-wrap: break-word; }
.profile-bio { color: var(--ink-secondary); font-size: var(--text-sm); line-height: var(--leading-relaxed); margin-top: var(--space-2); max-width: 640px; overflow-wrap: break-word; word-break: break-word; }

.profile-stats { display: flex; gap: var(--space-6); margin-top: var(--space-4); }
.stat-item { display: flex; flex-direction: column; align-items: center; gap: var(--space-1); padding: var(--space-2) var(--space-3); background: var(--bg-warm); border: .5px solid var(--line); border-radius: var(--radius-md); transition: background .3s var(--ease-out), transform .35s var(--ease-spring-gentle), box-shadow .3s var(--ease-out), border-color .3s var(--ease-out); }
.stat-item:hover { background: var(--card); transform: translateY(-1px); box-shadow: var(--shadow-sm); border-color: var(--border, var(--line)); }
.stat-item:active { transform: scale(.95); transition-duration: .08s; }
.stat-item:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
.stat-item strong { font-size: var(--text-lg); font-weight: var(--weight-bold); user-select: all; }
.stat-item span { font-size: var(--text-xs); color: var(--muted); }
.stat-clickable { cursor: pointer; font: inherit; }
.profile-insight { display: flex; align-items: center; justify-content: space-between; gap: var(--space-3); margin-top: var(--space-4); padding: var(--space-3) var(--space-4); border: 1px solid var(--line); border-radius: var(--radius-md); background: color-mix(in srgb, var(--bg-warm) 82%, var(--card)); }
.profile-insight-copy { display: flex; flex-direction: column; min-width: 0; gap: 2px; }
.profile-insight-copy span { color: var(--muted); font-size: var(--text-xs); font-weight: var(--weight-semibold); text-transform: uppercase; letter-spacing: .04em; }
.profile-insight-copy strong { color: var(--ink); font-size: var(--text-sm); line-height: var(--leading-snug); overflow-wrap: anywhere; }
.profile-insight-link { flex: 0 0 auto; color: var(--primary); font-size: var(--text-sm); font-weight: var(--weight-semibold); text-decoration: none; }
.profile-insight-link:hover { text-decoration: underline; }

/* Modal follower/following */
.fm-overlay { position: fixed; inset: 0; z-index: var(--z-modal-high); background: rgba(0,0,0,.45); display: flex; align-items: center; justify-content: center; padding: var(--space-4); }
.fm-dialog { background: var(--card); border-radius: var(--radius-lg); width: 100%; max-width: 420px; max-height: 80vh; display: flex; flex-direction: column; box-shadow: var(--shadow-lg); overflow: hidden; }
.fm-head { display: flex; align-items: center; justify-content: space-between; border-bottom: .5px solid var(--line); padding-right: var(--space-2); }
.fm-tabs { display: flex; }
.fm-tab { flex: 1; padding: var(--space-3) var(--space-4); border: none; background: none; cursor: pointer; font-size: var(--text-sm); font-weight: var(--weight-semibold); color: var(--muted); border-bottom: 2px solid transparent; transition: color .2s var(--ease-out), border-bottom-color .25s var(--ease-out); }
.fm-tab:hover { color: var(--ink-secondary); }
.fm-tab.active { color: var(--ink); border-bottom-color: var(--primary); }
.fm-close { border: none; background: none; font-size: 1.5rem; line-height: 1; cursor: pointer; color: var(--muted); padding: var(--space-2); }
.fm-body { overflow-y: auto; padding: var(--space-2); }
.fm-loading { display: flex; justify-content: center; padding: var(--space-5); }
.fm-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; }
.fm-user { display: flex; align-items: center; gap: var(--space-3); padding: var(--space-2) var(--space-3); border-radius: var(--radius-md); text-decoration: none; color: var(--ink); }
.fm-user:hover { background: var(--bg-alt); }
.fm-avatar { width: 38px; height: 38px; display: inline-flex; align-items: center; justify-content: center; border-radius: 50%; background: var(--primary); color: var(--primary-fg, #fff); font-weight: var(--weight-semibold); flex-shrink: 0; }
.fm-name { font-size: var(--text-sm); font-weight: var(--weight-medium); }
.fm-empty { text-align: center; color: var(--muted); padding: var(--space-5); font-size: var(--text-sm); }

.profile-tabs { display: flex; gap: var(--space-2); margin: var(--space-5) 0 var(--space-4); border-bottom: .5px solid var(--line); padding-bottom: var(--space-3); }
.profile-tabs .chip { min-height: 44px; transition: transform .35s var(--ease-spring-gentle), background .3s var(--ease-out), color .3s var(--ease-out), border-color .3s var(--ease-out); }
.profile-tabs .chip:active { transform: scale(.95); transition-duration: .08s; }

/* Post list transitions */
.post-list-enter-active { transition: opacity .35s var(--ease-out), transform .4s var(--ease-spring-gentle); }
.post-list-leave-active { transition: opacity .2s var(--ease-out), transform .2s var(--ease-out); }
.post-list-enter-from { opacity: 0; transform: translateY(8px); }
.post-list-leave-to { opacity: 0; transform: translateY(-4px); }
.post-list-move { transition: transform .35s var(--ease-spring-gentle); }

/* Fade */
.fade-enter-active { transition: opacity .3s var(--ease-out); }
.fade-leave-active { transition: opacity .15s var(--ease-out); }
.fade-enter-from, .fade-leave-to { opacity: 0; }

/* Follow button spring */
.profile-name-row .btn { transition: transform .35s var(--ease-spring-gentle), background .3s var(--ease-out), color .3s var(--ease-out), border-color .3s var(--ease-out); }
.profile-name-row .btn:active { transform: scale(.92); transition-duration: .08s; }
.profile-name-row .btn[aria-busy="true"] { pointer-events: none; }
/* Spinner contrast inside filled primary follow button */
.profile-name-row .btn-primary .spinner-sm { border-color: rgba(var(--text-on-dark-rgb),.45); border-top-color: var(--text-on-dark); }

.profile-skeleton { margin-top: var(--space-2); }

/* Saved tab (self profile) */
.tab-count {
  margin-left: var(--space-2); padding: 0 var(--space-2);
  border-radius: var(--radius-full); background: rgba(var(--accent-rgb), .16);
  color: var(--accent-dark); font-size: var(--text-xs); font-weight: var(--weight-bold);
  font-variant-numeric: tabular-nums; line-height: 1.6;
}
.saved-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: var(--space-4); margin-top: var(--space-2); }
.saved-grid > * { animation: savedEnter .4s var(--ease-out) backwards; }
.saved-grid > *:nth-child(1) { animation-delay: 0s; }
.saved-grid > *:nth-child(2) { animation-delay: .06s; }
.saved-grid > *:nth-child(3) { animation-delay: .12s; }
.saved-grid > *:nth-child(4) { animation-delay: .18s; }
.saved-grid > *:nth-child(5) { animation-delay: .24s; }
.saved-grid > *:nth-child(6) { animation-delay: .3s; }
@keyframes savedEnter { from { opacity: 0; transform: translateY(8px); } }
.saved-cta { text-align: center; margin-top: var(--space-5); }
.saved-cta .btn:active { transform: scale(.97); transition-duration: .08s; }
.dark .tab-count { background: rgba(var(--accent-rgb),.2); color: var(--accent); }

/* Danh sách (collections) tab */
.collections-header { display: flex; justify-content: flex-end; margin-bottom: var(--space-4); }
.collections-loading { display: flex; align-items: center; gap: var(--space-2); justify-content: center; padding: var(--space-8) 0; color: var(--muted); font-size: var(--text-sm); }
.saved-card .card-b .place { overflow-wrap: break-word; word-break: break-word; }
.btn-danger-text { align-self: flex-start; margin: 0 var(--space-4) var(--space-4); color: var(--danger, #c0392b); }
.btn-danger-text:hover:not(:disabled) { background: rgba(192,57,43,.08); color: var(--danger, #c0392b); }

/* Create-collection modal form (mirrors .sf-* in cai-dat.vue / SettingsForm.vue — scoped styles don't leak across components) */
.sf-field { display: flex; flex-direction: column; gap: var(--space-2); margin-bottom: var(--space-4); }
.sf-label { font-weight: var(--weight-semibold); font-size: var(--text-sm); color: var(--ink); }
.sf-input {
  width: 100%; padding: var(--space-3); border: 1px solid var(--border-input, var(--line)); border-radius: var(--radius-md);
  background: var(--bg-alt); color: var(--ink); font: inherit; font-size: var(--text-sm); resize: vertical;
  transition: border-color .2s var(--ease-out), background .2s var(--ease-out);
}
.sf-input:focus-visible { outline: none; border-color: var(--primary); background: var(--card); box-shadow: 0 0 0 3px color-mix(in srgb, var(--primary) 15%, transparent); }
.sf-actions { display: flex; justify-content: flex-end; gap: var(--space-3); margin-top: var(--space-2); }

/* Dark mode */
.dark .profile-cover { border-color: var(--line); }
.dark .profile-avatar-wrap .avatar { border-color: var(--bg-warm); }
.dark .stat-item:hover { background: var(--card); box-shadow: var(--shadow-sm); }
.dark .profile-tabs { border-bottom-color: var(--line); }

/* Mobile: stack follow/edit button below name */
@media (max-width: 480px) {
  .profile-name-row { flex-direction: column; align-items: flex-start; }
  .profile-name-row .btn:not(.btn-icon) { width: 100%; justify-content: center; }
  .profile-stats { gap: var(--space-3); flex-wrap: wrap; overflow-x: auto; -webkit-overflow-scrolling: touch; }
  .profile-insight { align-items: flex-start; flex-direction: column; }
  .profile-insight-link { width: 100%; }
}

@media (prefers-reduced-motion: reduce) {
  .post-list-enter-active, .post-list-leave-active, .post-list-move { transition: none; }
  .profile-avatar-wrap .avatar:hover { transform: none; }
  .stat-item:hover { transform: none; }
  .profile-tabs .chip:active { transform: none; }
  .saved-cta .btn:active { transform: none; }
  .pc-fill { animation: none; }
  .saved-grid > * { animation: none; }
  .cover-img { animation: none; }
}
.profile-completion { padding: 0 var(--space-4); margin-bottom: var(--space-3); }
.pc-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-1); }
.pc-label { font-size: var(--text-sm); font-weight: 600; color: var(--muted); }
.pc-link { font-size: var(--text-sm); color: var(--primary); text-decoration: none; }
.pc-bar { height: 6px; background: var(--bg-alt); border-radius: var(--radius-full); overflow: hidden; }
.pc-fill { height: 100%; background: var(--accent); border-radius: var(--radius-full); transition: width .4s var(--ease-out); transform-origin: left; animation: pc-grow .6s var(--ease-out) .3s backwards; }
@keyframes pc-grow { from { transform: scaleX(0); } to { transform: scaleX(1); } }
.pc-hints { display: flex; flex-wrap: wrap; gap: var(--space-1); margin-top: var(--space-2); }
.pc-hint { font-size: .72rem; color: var(--muted); padding: 2px 8px; border: 1px solid var(--border-input); border-radius: var(--radius-full); }

.profile-analytics { padding: var(--space-4); margin-bottom: var(--space-4); }
.pa-title { font-size: .85rem; font-weight: 600; text-transform: uppercase; letter-spacing: .5px; color: var(--muted); margin-bottom: var(--space-3); }
.pa-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--space-3); text-align: center; }
.pa-stat strong { display: block; font-size: 1.25rem; color: var(--ink); }
.pa-stat span { font-size: .75rem; color: var(--muted); }
@media (max-width: 520px) { .pa-grid { grid-template-columns: repeat(2, 1fr); } }

/* Hoạt động (timeline) tab */
.timeline-feed { display: flex; flex-direction: column; gap: var(--space-2); }
.timeline-item { display: flex; gap: var(--space-3); padding: var(--space-3); border-radius: var(--radius); background: var(--surface); border: 1px solid var(--line); }
.tl-icon { font-size: 1.25rem; flex-shrink: 0; width: 2rem; text-align: center; }
.tl-body { flex: 1; min-width: 0; }
.tl-text { margin: 0; color: var(--ink); font-size: 0.9375rem; }
.tl-preview { margin: var(--space-1) 0 0; color: var(--muted); font-size: 0.875rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tl-time { font-size: 0.8125rem; color: var(--muted); }
.tl-rating { margin-left: var(--space-1); }
</style>
