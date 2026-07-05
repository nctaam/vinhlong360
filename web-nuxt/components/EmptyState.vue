<template>
  <div class="empty-state" :class="`is-${tone}`" :role="tone === 'error' ? 'alert' : 'status'">
    <span v-if="icon" class="empty-icon" aria-hidden="true">{{ icon }}</span>
    <svg v-else viewBox="0 0 200 160" xmlns="http://www.w3.org/2000/svg" aria-hidden="true" class="empty-illust">
      <defs>
        <linearGradient id="empty-sediment" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stop-color="var(--river-600)" />
          <stop offset="52%" stop-color="var(--amber-600)" />
          <stop offset="100%" stop-color="var(--clay-600)" />
        </linearGradient>
      </defs>
      <circle cx="100" cy="70" r="50" fill="var(--bg-warm)" />
      <rect class="empty-illust-grain" x="50" y="20" width="100" height="100" />
      <circle cx="100" cy="70" r="35" fill="var(--bg)" />
      <circle cx="90" cy="65" r="20" stroke="url(#empty-sediment)" stroke-width="3.5" fill="none" />
      <line x1="105" y1="80" x2="125" y2="100" stroke="var(--clay-600)" stroke-width="5" stroke-linecap="round" />
      <g fill="var(--amber-600)" opacity=".65">
        <path d="M140 35 l3 8 8 3 -8 3 -3 8 -3 -8 -8 -3 8 -3z" />
        <path d="M55 30 l2 6 6 2 -6 2 -2 6 -2 -6 -6 -2 6 -2z" />
        <path d="M150 75 l2 5 5 2 -5 2 -2 5 -2 -5 -5 -2 5 -2z" />
      </g>
    </svg>
    <span class="empty-rule" aria-hidden="true"></span>
    <component :is="headingTag" v-if="title" class="empty-title">{{ title }}</component>
    <p class="empty-text">{{ message }}</p>
    <p v-if="hint" class="empty-hint">{{ hint }}</p>
    <div v-if="$slots.actions" class="empty-actions" role="group" aria-label="Hành động">
      <slot name="actions" />
    </div>
    <slot />
  </div>
</template>

<script setup lang="ts">
const props = withDefaults(defineProps<{
  message?: string
  icon?: string
  title?: string
  hint?: string
  tone?: 'empty' | 'error'
  headingLevel?: 2 | 3 | 4
}>(), { headingLevel: 3, tone: 'empty' })

const headingTag = computed(() => `h${props.headingLevel}`)
</script>

<style scoped>
.empty-state { animation: emptyIn .5s var(--ease-spring-gentle); }
@keyframes emptyIn { from { opacity: 0; transform: translateY(12px) scale(.96); } }

/* Editorial title — a moment worth a serif line, not a form-validation label. */
.empty-title {
  font-family: var(--font-editorial);
  font-weight: 600;
  letter-spacing: -.01em;
}

/* Tri-province sediment rule (river → amber → clay) — same recipe as the Story
   Card's card-rule and the shared .sediment-head tick — ties this "nothing here
   yet" moment back to the site's one signature motif instead of a bare icon. */
.empty-rule {
  display: block;
  width: 30px; height: 2px; border-radius: 2px;
  margin: var(--space-4) auto var(--space-3);
  background: linear-gradient(90deg, var(--river-600) 0%, var(--amber-600) 52%, var(--clay-600) 100%);
}
.dark .empty-rule { background: linear-gradient(90deg, #74ABB5 0%, var(--amber-500) 52%, var(--clay-400) 100%); }

/* Grain tile behind the illustration's inner circle — turns the flat "no photo
   yet" placeholder into an intentional sediment-wash illustration instead of a
   bare flat-fill AI-gradient (anti-slop tell #1). Same --grain token as the
   Story Card's .cover-grain. */
.empty-illust-grain {
  clip-path: circle(50px at 100px 70px);
  fill: var(--grain);
  opacity: .05;
}
.dark .empty-illust-grain { opacity: .08; }

/* Optional contextual hint line below the message — used e.g. for region/star context on OCOP empty results. */
.empty-hint { font-size: var(--text-sm); color: var(--muted); margin: var(--space-3) 0 var(--space-4); }
.empty-icon { display: block; transition: transform .4s var(--ease-spring-gentle); }
.empty-state:hover .empty-icon { transform: scale(1.1) rotate(-4deg); }
.empty-illust { transition: transform .4s var(--ease-spring-gentle); }
.empty-state:hover .empty-illust { transform: scale(1.04); }

/* Error tone keeps the same editorial chrome but nudges the rule toward clay —
   a quieter cue than a red icon, consistent with "no hardcoded brand hex". */
.is-error .empty-rule { background: linear-gradient(90deg, var(--amber-600) 0%, var(--clay-600) 100%); }
.dark .is-error .empty-rule { background: linear-gradient(90deg, var(--amber-500) 0%, var(--clay-400) 100%); }

@media (prefers-reduced-motion: reduce) {
  .empty-state { animation: none; opacity: 1; transform: none; }
  .empty-icon, .empty-illust { transition: none; }
  .empty-state:hover .empty-icon { transform: none; }
  .empty-state:hover .empty-illust { transform: none; }
}
@media (forced-colors: active) {
  .empty-illust circle, .empty-illust line { stroke: CanvasText; }
  .empty-illust-grain { display: none; }
  .empty-rule { background: CanvasText; }
}
</style>
