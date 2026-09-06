<template>
  <div class="threads-filter-wrapper">
    <!-- Main tabs -->
    <div class="threads-filter-bar">
      <div class="threads-filter" role="tablist" aria-label="Bộ lọc bảng tin" @keydown="$emit('tab-keydown', $event)">
        <button
          v-for="tab in visibleFeedTabs"
          :key="tab.key"
          type="button"
          role="tab"
          :class="['threads-tab', { active: activeTab === tab.key }]"
          :aria-selected="activeTab === tab.key"
          :tabindex="activeTab === tab.key ? 0 : -1"
          :data-tab="tab.key"
          @click="$emit('select-tab', tab.key)"
        >
          <svg v-if="tab.key === 'bookmarks'" class="icon-inline" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/></svg>{{ tab.label }}
        </button>
      </div>
      <button type="button" class="threads-refresh" :disabled="loading" aria-label="Tải lại bảng tin" @click="$emit('refresh')">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" :class="{ spinning: loading }"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
      </button>
    </div>

    <slot name="discovery" />

    <!-- Đang lọc theo hashtag -->
    <div v-if="activeTag" class="tag-banner" role="status">
      <span>Đang xem <strong>#{{ activeTag }}</strong></span>
      <button type="button" class="tag-clear" @click="$emit('clear-tag')"><IconLine name="x" /> Bỏ lọc</button>
    </div>

    <!-- Post type filter (only for feed tabs, not bookmarks) -->
    <div v-if="activeTab !== 'bookmarks'" class="type-filter-row" role="tablist" aria-label="Lọc loại bài viết" @keydown="$emit('type-keydown', $event)">
      <button
        v-for="pt in filterTypeOptions"
        :key="pt.value || 'all'"
        type="button"
        role="tab"
        :class="['chip chip-filter', { active: filterType === pt.value }]"
        :aria-selected="filterType === pt.value"
        :tabindex="filterType === pt.value ? 0 : -1"
        :data-type="pt.value || 'all'"
        @click="$emit('select-type', pt.value)"
      ><IconLine v-if="pt.icon" :name="pt.icon" aria-hidden="true" /> <span>{{ pt.label }}</span></button>
    </div>
  </div>
</template>

<script setup lang="ts">
export type FeedTab = 'latest' | 'trending' | 'following' | 'bookmarks'
export type PostTypeValue = '' | 'share' | 'review' | 'question' | 'recommend'

export interface FeedTabItem {
  key: FeedTab
  label: string
  requiresAuth?: boolean
}

export interface FilterTypeOption {
  value: PostTypeValue
  label: string
  icon?: string
}

defineProps<{
  visibleFeedTabs: FeedTabItem[]
  activeTab: FeedTab
  loading: boolean
  activeTag: string
  filterType: PostTypeValue
  filterTypeOptions: FilterTypeOption[]
}>()

defineEmits<{
  (e: 'select-tab', tab: FeedTab): void
  (e: 'refresh'): void
  (e: 'clear-tag'): void
  (e: 'select-type', type: PostTypeValue): void
  (e: 'tab-keydown', event: KeyboardEvent): void
  (e: 'type-keydown', event: KeyboardEvent): void
}>()
</script>

<style scoped>
.threads-filter-bar {
  display: flex;
  align-items: stretch;
  border-bottom: .5px solid var(--line);
  margin-top: var(--space-5);
  margin-bottom: var(--space-2);
  position: sticky;
  top: 78px;
  z-index: 20;
  background: var(--surface-translucent, var(--bg));
  backdrop-filter: var(--glass);
  -webkit-backdrop-filter: var(--glass);
}
.threads-filter {
  display: flex;
  flex: 1;
  min-width: 0;
}
.threads-tab {
  flex: 1;
  text-align: center;
  padding: var(--space-3) var(--space-4);
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  color: var(--muted);
  cursor: pointer;
  min-height: 44px;
  transition: color .25s var(--ease-out);
  position: relative;
}
.threads-tab::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 20%;
  right: 20%;
  height: 2px;
  background: var(--ink);
  border-radius: 1px;
  transform: scaleX(0);
  transition: transform .25s var(--ease-out-expo);
}
.threads-tab:hover {
  color: var(--ink);
}
.threads-tab:hover::after {
  transform: scaleX(.5);
}
.threads-tab:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 2px;
}
.threads-tab.active {
  color: var(--ink);
  border-bottom-color: transparent;
}
.threads-tab.active::after {
  transform: scaleX(1);
}
.dark .threads-tab.active {
  color: var(--ink);
}
.threads-refresh {
  flex-shrink: 0;
  width: 44px;
  min-height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: .5rem;
  background: none;
  border: none;
  color: var(--muted);
  cursor: pointer;
  transition: color .25s var(--ease-out), background .25s var(--ease-out);
}
.threads-refresh:hover {
  color: var(--ink);
  background: var(--overlay-subtle);
}
.threads-refresh:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 2px;
}
.threads-refresh svg {
  display: block;
}
.threads-refresh .spinning {
  animation: spin .8s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* ── Type filter ── */
.type-filter-row {
  display: flex;
  gap: var(--space-2);
  padding: var(--space-3) 0;
  margin-top: var(--space-2);
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
}
.type-filter-row::-webkit-scrollbar {
  display: none;
}
.chip-filter {
  font-size: var(--text-xs);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-full);
  border: .5px solid var(--line);
  background: var(--card);
  color: var(--muted);
  cursor: pointer;
  white-space: nowrap;
  min-height: 44px;
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  transition: background .2s, color .2s, border-color .2s, transform .25s var(--ease-out-expo);
}
.chip-filter:hover {
  border-color: var(--ink);
  color: var(--ink);
}
.chip-filter:active {
  transform: scale(.95);
  transition-duration: .08s;
}
.chip-filter:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 2px;
}
.chip-filter.active {
  background: var(--ink);
  color: var(--bg);
  border-color: var(--ink);
  font-weight: var(--weight-semibold);
}

/* ── Tag banner ── */
.tag-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  background: var(--bg-alt);
  border: .5px solid var(--line);
  border-radius: var(--radius-control);
  margin-top: var(--space-2);
  font-size: var(--text-xs);
  color: var(--ink);
}
.tag-clear {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--muted);
  font-size: var(--text-xs);
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  min-height: 32px;
  padding: 0 var(--space-2);
  border-radius: var(--radius-control);
  transition: color .2s, background .2s;
}
.tag-clear:hover {
  color: var(--ink);
  background: var(--overlay-subtle);
}

.dark .chip-filter {
  background: var(--bg-alt);
  border-color: var(--line);
}
.dark .chip-filter.active {
  background: var(--ink);
  color: var(--bg);
  border-color: var(--ink);
}
.dark .threads-filter-bar {
  background: var(--surface-translucent, rgba(var(--black-rgb), .72));
}

@media (prefers-reduced-motion: reduce) {
  .threads-tab::after {
    transition: none;
  }
  .chip-filter:active {
    transform: none;
  }
  .threads-refresh .spinning {
    animation: none;
  }
}
</style>
