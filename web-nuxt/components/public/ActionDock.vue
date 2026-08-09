<script setup lang="ts">
import { Comment, Fragment, Text, type VNode } from 'vue'

const slots = useSlots()

function firstRenderable(nodes: VNode[]): VNode | undefined {
  for (const node of nodes) {
    if (node.type === Comment) continue
    if (node.type === Text && typeof node.children === 'string' && !node.children.trim()) continue
    if (node.type === Fragment && Array.isArray(node.children)) {
      const child = firstRenderable(node.children as VNode[])
      if (child) return child
      continue
    }
    return node
  }
}

const primaryAction = computed(() => firstRenderable(slots.primary?.() ?? []))
</script>

<template>
  <aside class="action-dock" data-action-dock aria-label="Hành động chính">
    <div v-if="primaryAction" class="action-dock__primary" data-action-dock-primary>
      <component :is="{ render: () => primaryAction }" />
    </div>
    <div v-if="$slots.default" class="action-dock__secondary" data-action-dock-secondary>
      <slot />
    </div>
  </aside>
</template>
