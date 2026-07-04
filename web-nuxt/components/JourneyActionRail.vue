<template>
  <section v-if="actions.length" class="journey-actions" :class="{ compact }" :aria-label="ariaLabel">
    <div v-if="title || subtitle" class="journey-actions-head">
      <h2 v-if="title">{{ title }}</h2>
      <p v-if="subtitle">{{ subtitle }}</p>
    </div>
    <div class="journey-actions-list">
      <NuxtLink
        v-for="action in actions"
        :key="action.id"
        :to="action.to"
        :class="['journey-action', `tone-${action.tone || 'neutral'}`]"
      >
        <span class="journey-action-icon" aria-hidden="true">{{ action.icon }}</span>
        <span class="journey-action-copy">
          <strong>{{ action.label }}</strong>
          <small v-if="action.text">{{ action.text }}</small>
        </span>
      </NuxtLink>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { JourneyAction } from '~/composables/useJourneyActions'

withDefaults(defineProps<{
  actions: JourneyAction[]
  title?: string
  subtitle?: string
  ariaLabel?: string
  compact?: boolean
}>(), {
  ariaLabel: 'Gợi ý bước tiếp theo',
})
</script>

<style scoped>
.journey-actions {
  margin: var(--space-5) 0;
}
.journey-actions.compact {
  margin: var(--space-3) 0 var(--space-4);
}
.journey-actions-head {
  margin-bottom: var(--space-3);
}
.journey-actions-head h2 {
  margin: 0;
  font-size: var(--text-lg);
}
.journey-actions-head p {
  margin: .2rem 0 0;
  color: var(--muted);
  font-size: var(--text-sm);
}
.journey-actions-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  gap: var(--space-3);
}
.journey-action {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  min-width: 0;
  min-height: 78px;
  padding: var(--space-3);
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  background: var(--card);
  color: var(--ink);
  text-decoration: none;
  transition: border-color .2s var(--ease-out), background .2s var(--ease-out), transform .25s var(--ease-spring-gentle), box-shadow .2s var(--ease-out);
}
.journey-action:hover {
  transform: translateY(-1px);
  border-color: rgba(var(--primary-rgb), .38);
  box-shadow: var(--shadow-xs);
}
.journey-action:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}
.journey-action-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  flex: 0 0 auto;
  border-radius: var(--radius-sm);
  background: var(--bg-warm);
}
.journey-action-copy {
  min-width: 0;
}
.journey-action-copy strong {
  display: block;
  font-size: var(--text-sm);
  line-height: 1.25;
}
.journey-action-copy small {
  display: block;
  margin-top: .25rem;
  color: var(--muted);
  font-size: var(--text-xs);
  line-height: 1.35;
}
.tone-primary .journey-action-icon { background: rgba(var(--primary-rgb), .1); }
.tone-map .journey-action-icon { background: rgba(var(--river-rgb, 14, 116, 144), .1); }
.tone-planner .journey-action-icon { background: rgba(var(--accent-rgb), .12); }
.tone-community .journey-action-icon { background: rgba(var(--secondary-rgb), .12); }
.tone-saved .journey-action-icon { background: rgba(220, 38, 38, .08); }
.tone-warning .journey-action-icon { background: rgba(var(--warning-rgb), .12); }
.tone-danger .journey-action-icon { background: rgba(var(--danger-rgb, 220, 38, 38), .1); }
.tone-admin .journey-action-icon { background: rgba(var(--blue-rgb, 52, 120, 246), .1); }
@media (max-width: 640px) {
  .journey-actions-list { grid-template-columns: 1fr; }
  .journey-action { min-height: 72px; }
}
@media (prefers-reduced-motion: reduce) {
  .journey-action { transition: none; }
  .journey-action:hover { transform: none; }
}
</style>
