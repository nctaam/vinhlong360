<template>
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
</template>

<script setup lang="ts">
import { userPath } from '~/utils/routePaths'

interface TopMember {
  id: string
  username?: string
  display_name?: string
}

interface TrendingTag {
  tag: string
  count?: number
}

defineProps<{
  topMembers: TopMember[]
  trendingTags: TrendingTag[]
  searchMode: boolean
}>()
</script>

<style scoped>
.mobile-discovery { display: none; margin-top: var(--space-2); }

@media (max-width: 820px) {
  .mobile-discovery { display: flex; flex-direction: column; gap: var(--space-2); padding: var(--space-2) var(--space-3); }
  .md-section { display: flex; align-items: center; gap: var(--space-2); }
  .md-label { font-size: .7rem; font-weight: 600; text-transform: uppercase; letter-spacing: .04em; color: var(--muted); white-space: nowrap; min-width: 52px; }
  .md-scroll { display: flex; gap: var(--space-2); overflow-x: auto; -webkit-overflow-scrolling: touch; scrollbar-width: none; padding-block: 2px; }
  .md-scroll::-webkit-scrollbar { display: none; }
  .md-tag { font-size: .8rem; padding: var(--space-1) 10px; border-radius: var(--radius-full); background: var(--surface-2); color: var(--accent); white-space: nowrap; text-decoration: none; font-weight: 500; }
  .md-tag:hover { background: var(--accent); color: var(--text-on-dark, var(--white)); }
  .md-member { display: flex; align-items: center; gap: var(--space-1); padding: var(--space-1) var(--space-2); border-radius: var(--radius-full); background: var(--surface-2); text-decoration: none; white-space: nowrap; }
  .md-name { font-size: .78rem; color: var(--ink-800); }
  .dark .md-tag { background: var(--surface-3); }
  .dark .md-member { background: var(--surface-3); }
}
</style>
