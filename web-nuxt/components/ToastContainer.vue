<template>
  <Teleport to="body">
    <div v-if="toasts.length" class="toast-container">
      <div v-for="t in toasts" :key="t.id" :class="['toast', t.type]">
        {{ t.message }}
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
const { toasts } = useToast()
</script>
