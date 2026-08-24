<script setup lang="ts">
// Before and after, legible without colour.
//
// Each side is named in text and prefixed like a patch, so a monochrome print
// or a colour-blind reader loses nothing. The diff never invents content: it
// shows exactly the two values the change set recorded.
defineProps<{
  fieldPath: string
  before: string
  after: string
}>()
</script>

<template>
  <div class="changeset-diff">
    <p class="diff-field">{{ fieldPath }}</p>
    <dl class="diff-sides">
      <div class="diff-side diff-before">
        <dt>Trước (−)</dt>
        <dd data-role="diff-before"><span aria-hidden="true">− </span>{{ before }}</dd>
      </div>
      <div class="diff-side diff-after">
        <dt>Sau (+)</dt>
        <dd data-role="diff-after"><span aria-hidden="true">+ </span>{{ after }}</dd>
      </div>
    </dl>
  </div>
</template>

<style scoped>
.changeset-diff {
  display: grid;
  gap: 0.4rem;
}
.diff-field {
  margin: 0;
  font-family: var(--font-mono);
  font-size: 0.85rem;
}
.diff-sides {
  margin: 0;
  display: grid;
  gap: 0.3rem;
}
.diff-side dt {
  font-size: 0.75rem;
  color: var(--muted);
}
.diff-side dd {
  margin: 0;
  padding: 0.35rem 0.55rem;
  border-radius: 6px;
  overflow-wrap: anywhere;
}
.diff-before dd {
  background: color-mix(in srgb, var(--color-error) 12%, var(--bg));
}
.diff-after dd {
  background: color-mix(in srgb, var(--color-success) 12%, var(--bg));
}
</style>
