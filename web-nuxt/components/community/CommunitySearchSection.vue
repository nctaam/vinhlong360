<template>
  <div class="community-search-section">
    <!-- Tìm bài viết -->
    <div v-if="!ugcUnavailable" class="community-search" role="search">
      <svg class="cs-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg>
      <input
        :value="modelValue"
        class="cs-input"
        type="search"
        enterkeyhint="search"
        maxlength="100"
        placeholder="Tìm bài viết trong cộng đồng…"
        aria-label="Tìm bài viết trong cộng đồng"
        @input="$emit('update:modelValue', ($event.target as HTMLInputElement).value)"
        @keyup.enter="$emit('search')"
      />
      <button v-if="searchMode" type="button" class="cs-clear" aria-label="Xoá tìm kiếm" @click="$emit('clear')"><IconLine name="x" /></button>
      <button type="button" class="btn btn-primary btn-sm cs-go" @click="$emit('search')">Tìm</button>
    </div>

    <!-- Đang xem kết quả tìm -->
    <div v-if="searchMode" class="tag-banner" role="status">
      <span><strong>{{ displayPostsCount }}</strong> kết quả cho <strong>&ldquo;{{ searchQuery }}&rdquo;</strong></span>
      <button type="button" class="tag-clear" @click="$emit('clear')"><IconLine name="x" /> Bỏ tìm</button>
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
  </div>
</template>

<script setup lang="ts">
import { userPath } from '~/utils/routePaths'

interface SearchUser {
  id: string
  username?: string
  display_name?: string
  avatar_url?: string
  post_count?: number
}

defineProps<{
  modelValue: string
  searchMode: boolean
  searchQuery: string
  displayPostsCount: number
  searchUsers: SearchUser[]
  ugcUnavailable: boolean
}>()

defineEmits<{
  (e: 'update:modelValue', val: string): void
  (e: 'search'): void
  (e: 'clear'): void
}>()
</script>

<style scoped>
.community-search { display: flex; align-items: center; gap: var(--space-2); margin-bottom: var(--space-3); padding: .35rem .5rem .35rem .75rem; background: var(--card); border: 1px solid var(--border); border-radius: var(--radius-full); }
.community-search:focus-within { border-color: var(--primary); }
.cs-icon { color: var(--muted); flex-shrink: 0; }
.cs-input { flex: 1; min-width: 0; border: none; background: none; outline: none; color: var(--ink); font-size: var(--text-sm); padding: .35rem 0; }
.cs-input:focus-visible { outline: 2px solid var(--color-focus); outline-offset: 2px; }
.cs-input::placeholder { color: var(--muted); }
.cs-clear { border: none; background: none; color: var(--muted); font-size: 1.3rem; line-height: 1; cursor: pointer; padding: 0 .25rem; min-width: 44px; display: inline-flex; align-items: center; justify-content: center; }
.cs-clear:hover { color: var(--ink); }
.cs-go { flex-shrink: 0; }

.tag-banner { display: flex; align-items: center; justify-content: space-between; gap: .5rem; padding: .5rem .75rem; margin-bottom: var(--space-3); background: color-mix(in srgb, var(--accent) 10%, var(--bg-alt)); border-radius: var(--radius-surface); font-size: var(--text-sm); }
.tag-clear { border: none; background: none; color: var(--primary-fg); cursor: pointer; font-size: var(--text-sm); }

.search-users-section { margin-bottom: var(--space-4); }
.search-users-grid { display: flex; gap: var(--space-2); overflow-x: auto; padding-bottom: var(--space-1); }
.search-user-card { display: flex; align-items: center; gap: var(--space-2); padding: var(--space-2) var(--space-3); min-width: 180px; flex-shrink: 0; text-decoration: none; }
.suc-info { min-width: 0; }
.suc-info strong { display: block; font-size: 0.875rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: var(--ink); }
.suc-meta { font-size: 0.75rem; color: var(--muted); }
.section-label { font-size: var(--text-sm); font-weight: var(--weight-semibold); color: var(--muted); margin: 0 0 var(--space-2); text-transform: uppercase; letter-spacing: 0.04em; }

@media (max-width: 820px) {
  .cs-input { font-size: 16px; }
}
</style>
