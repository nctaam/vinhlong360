<template>
  <!-- Vĩnh Long: cam sành, sông nước, gốm -->
  <svg v-if="area === 'vinh-long'" class="area-illust" viewBox="0 0 280 140" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
    <defs><linearGradient id="vl-bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#9C3D22"/><stop offset="100%" stop-color="#C4694E"/></linearGradient></defs>
    <rect width="280" height="140" rx="12" fill="url(#vl-bg)"/>
    <path d="M0 100 Q70 85 140 100 Q210 115 280 95 L280 140 L0 140Z" fill="rgba(255,255,255,.1)"/>
    <circle cx="60" cy="50" r="18" fill="#E8A33D" opacity=".7"/>
    <circle cx="85" cy="42" r="14" fill="#E8A33D" opacity=".6"/>
    <circle cx="70" cy="68" r="15" fill="#E8A33D" opacity=".65"/>
    <path d="M68 28 Q72 18 80 22" stroke="#4BA97D" stroke-width="2" fill="none" opacity=".7"/>
    <path d="M62 30 Q58 20 52 24" stroke="#4BA97D" stroke-width="2" fill="none" opacity=".7"/>
    <g opacity=".3" transform="translate(180,30)">
      <rect x="0" y="20" width="30" height="50" rx="4" fill="#fff"/>
      <rect x="40" y="10" width="25" height="60" rx="4" fill="#fff"/>
      <path d="M5 20 L15 5 L25 20" fill="rgba(255,255,255,.5)"/>
      <path d="M44 10 L52.5 -2 L61 10" fill="rgba(255,255,255,.5)"/>
    </g>
  </svg>

  <!-- Bến Tre: dừa, kẹo dừa, rẫy -->
  <svg v-else-if="area === 'ben-tre'" class="area-illust" viewBox="0 0 280 140" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
    <defs><linearGradient id="bt-bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#2E7D5B"/><stop offset="100%" stop-color="#4BA97D"/></linearGradient></defs>
    <rect width="280" height="140" rx="12" fill="url(#bt-bg)"/>
    <path d="M0 110 Q90 95 180 108 Q240 116 280 100 L280 140 L0 140Z" fill="rgba(255,255,255,.1)"/>
    <g opacity=".5" transform="translate(50,10)">
      <line x1="25" y1="110" x2="25" y2="40" stroke="#fff" stroke-width="3.5"/>
      <path d="M25 40 Q5 25 -10 35" stroke="#fff" stroke-width="2.5" fill="none"/>
      <path d="M25 40 Q45 22 60 30" stroke="#fff" stroke-width="2.5" fill="none"/>
      <path d="M25 40 Q18 18 8 14" stroke="#fff" stroke-width="2.5" fill="none"/>
      <path d="M25 40 Q35 16 48 10" stroke="#fff" stroke-width="2.5" fill="none"/>
      <ellipse cx="22" cy="55" rx="7" ry="9" fill="rgba(255,255,255,.4)"/>
      <ellipse cx="32" cy="52" rx="6" ry="8" fill="rgba(255,255,255,.35)"/>
    </g>
    <g opacity=".35" transform="translate(170,20)">
      <line x1="25" y1="100" x2="25" y2="45" stroke="#fff" stroke-width="3"/>
      <path d="M25 45 Q8 32 -5 40" stroke="#fff" stroke-width="2" fill="none"/>
      <path d="M25 45 Q42 30 55 36" stroke="#fff" stroke-width="2" fill="none"/>
      <path d="M25 45 Q19 25 10 20" stroke="#fff" stroke-width="2" fill="none"/>
      <path d="M25 45 Q33 22 44 16" stroke="#fff" stroke-width="2" fill="none"/>
    </g>
  </svg>

  <!-- Trà Vinh: chùa Khmer, ao Bà Om -->
  <svg v-else-if="area === 'tra-vinh'" class="area-illust" viewBox="0 0 280 140" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
    <defs><linearGradient id="tv-bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#33646E"/><stop offset="100%" stop-color="#4E8A96"/></linearGradient></defs>
    <rect width="280" height="140" rx="12" fill="url(#tv-bg)"/>
    <path d="M0 105 Q70 115 140 105 Q210 95 280 108 L280 140 L0 140Z" fill="rgba(255,255,255,.08)"/>
    <g opacity=".4" transform="translate(80,15)">
      <rect x="25" y="50" width="70" height="55" rx="3" fill="#fff"/>
      <path d="M20 50 L60 15 L100 50Z" fill="rgba(255,255,255,.7)"/>
      <path d="M40 50 L60 30 L80 50Z" fill="rgba(255,255,255,.5)"/>
      <rect x="50" y="70" width="18" height="35" rx="8" fill="rgba(51,100,110,.3)"/>
      <circle cx="60" cy="28" r="4" fill="#E8A33D" opacity=".8"/>
    </g>
    <ellipse cx="210" cy="100" rx="40" ry="18" fill="rgba(255,255,255,.12)"/>
    <ellipse cx="210" cy="100" rx="32" ry="14" fill="rgba(255,255,255,.08)"/>
  </svg>

  <!-- Fallback -->
  <svg v-else class="area-illust" viewBox="0 0 280 140" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
    <rect width="280" height="140" rx="12" fill="#6B7B73"/>
    <circle cx="140" cy="70" r="30" fill="rgba(255,255,255,.1)"/>
  </svg>
</template>

<script setup lang="ts">
defineProps<{ area: string }>()
</script>

<style scoped>
.area-illust { width: 100%; height: auto; display: block; border-radius: var(--radius-md); }
</style>
