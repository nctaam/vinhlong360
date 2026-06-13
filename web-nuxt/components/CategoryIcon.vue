<template>
  <!-- Experience: lúa/lá -->
  <svg v-if="cat === 'experience'" viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg" class="cat-icon" aria-hidden="true">
    <path d="M24 42 Q24 28 18 18 Q14 12 10 10" stroke="#fff" stroke-width="2.5" fill="none" stroke-linecap="round"/>
    <path d="M24 42 Q24 26 30 16 Q34 10 38 8" stroke="#fff" stroke-width="2.5" fill="none" stroke-linecap="round"/>
    <path d="M18 18 Q14 16 8 18" stroke="#fff" stroke-width="2" fill="none" stroke-linecap="round"/>
    <path d="M20 24 Q16 22 10 24" stroke="#fff" stroke-width="2" fill="none" stroke-linecap="round"/>
    <path d="M30 16 Q34 14 40 16" stroke="#fff" stroke-width="2" fill="none" stroke-linecap="round"/>
    <path d="M28 22 Q32 20 38 22" stroke="#fff" stroke-width="2" fill="none" stroke-linecap="round"/>
  </svg>

  <!-- Product: trái cây -->
  <svg v-else-if="cat === 'product'" viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg" class="cat-icon" aria-hidden="true">
    <circle cx="24" cy="26" r="14" fill="rgba(255,255,255,.3)"/>
    <circle cx="24" cy="26" r="10" fill="rgba(255,255,255,.2)"/>
    <path d="M24 12 Q26 6 30 8" stroke="#fff" stroke-width="2" fill="none" stroke-linecap="round"/>
    <path d="M24 12 Q22 7 18 9" stroke="#fff" stroke-width="2" fill="none" stroke-linecap="round"/>
    <ellipse cx="20" cy="24" rx="3" ry="4" fill="rgba(255,255,255,.15)" transform="rotate(-15 20 24)"/>
  </svg>

  <!-- Attraction: chùa/mái -->
  <svg v-else-if="cat === 'attraction'" viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg" class="cat-icon" aria-hidden="true">
    <rect x="14" y="24" width="20" height="18" rx="2" fill="rgba(255,255,255,.25)"/>
    <path d="M10 24 L24 10 L38 24Z" fill="rgba(255,255,255,.3)"/>
    <path d="M16 24 L24 14 L32 24Z" fill="rgba(255,255,255,.15)"/>
    <rect x="21" y="30" width="6" height="12" rx="3" fill="rgba(255,255,255,.2)"/>
    <circle cx="24" cy="18" r="2.5" fill="rgba(255,255,255,.5)"/>
  </svg>

  <!-- Craft: gốm/bình -->
  <svg v-else-if="cat === 'craft'" viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg" class="cat-icon" aria-hidden="true">
    <path d="M18 38 Q16 30 17 24 Q18 18 22 16 Q24 15 26 16 Q30 18 31 24 Q32 30 30 38Z" fill="rgba(255,255,255,.3)"/>
    <path d="M20 16 Q22 12 24 12 Q26 12 28 16" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round"/>
    <line x1="20" y1="26" x2="28" y2="26" stroke="rgba(255,255,255,.3)" stroke-width="1.5"/>
    <line x1="19" y1="30" x2="29" y2="30" stroke="rgba(255,255,255,.3)" stroke-width="1.5"/>
    <line x1="18" y1="34" x2="30" y2="34" stroke="rgba(255,255,255,.3)" stroke-width="1.5"/>
  </svg>

  <!-- Accommodation: nhà -->
  <svg v-else-if="cat === 'accommodation'" viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg" class="cat-icon" aria-hidden="true">
    <rect x="12" y="22" width="24" height="18" rx="2" fill="rgba(255,255,255,.25)"/>
    <path d="M8 22 L24 10 L40 22" fill="none" stroke="#fff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
    <rect x="20" y="30" width="8" height="10" rx="1" fill="rgba(255,255,255,.2)"/>
    <rect x="15" y="26" width="5" height="5" rx=".5" fill="rgba(255,255,255,.15)"/>
    <rect x="28" y="26" width="5" height="5" rx=".5" fill="rgba(255,255,255,.15)"/>
  </svg>

  <!-- Dish: bát -->
  <svg v-else-if="cat === 'dish'" viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg" class="cat-icon" aria-hidden="true">
    <ellipse cx="24" cy="30" rx="16" ry="6" fill="rgba(255,255,255,.25)"/>
    <path d="M8 28 Q8 20 24 20 Q40 20 40 28" fill="rgba(255,255,255,.15)"/>
    <path d="M16 18 Q18 12 20 14" stroke="#fff" stroke-width="1.5" fill="none" stroke-linecap="round"/>
    <path d="M24 16 Q26 10 28 12" stroke="#fff" stroke-width="1.5" fill="none" stroke-linecap="round"/>
    <path d="M32 18 Q34 12 36 14" stroke="#fff" stroke-width="1.5" fill="none" stroke-linecap="round"/>
    <line x1="8" y1="36" x2="40" y2="36" stroke="rgba(255,255,255,.2)" stroke-width="2"/>
  </svg>

  <!-- Itinerary: bản đồ -->
  <svg v-else-if="cat === 'itinerary'" viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg" class="cat-icon" aria-hidden="true">
    <path d="M12 10 L20 14 L28 10 L36 14 L36 38 L28 34 L20 38 L12 34Z" fill="rgba(255,255,255,.2)" stroke="#fff" stroke-width="2"/>
    <line x1="20" y1="14" x2="20" y2="38" stroke="rgba(255,255,255,.2)" stroke-width="1.5"/>
    <line x1="28" y1="10" x2="28" y2="34" stroke="rgba(255,255,255,.2)" stroke-width="1.5"/>
    <circle cx="24" cy="22" r="3" fill="rgba(255,255,255,.4)"/>
  </svg>

  <!-- Fallback -->
  <svg v-else viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg" class="cat-icon" aria-hidden="true">
    <circle cx="24" cy="24" r="12" fill="rgba(255,255,255,.2)"/>
    <circle cx="24" cy="24" r="4" fill="rgba(255,255,255,.3)"/>
  </svg>
</template>

<script setup lang="ts">
defineProps<{ cat: string }>()
</script>

<style scoped>
.cat-icon { width: 48px; height: 48px; }
</style>
