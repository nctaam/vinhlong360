<template>
  <svg viewBox="0 0 800 200" xmlns="http://www.w3.org/2000/svg" class="user-cover-svg" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
    <defs>
      <linearGradient id="ucg1" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stop-color="#9C3D22" stop-opacity=".85" />
        <stop offset="50%" stop-color="#E8A33D" stop-opacity=".6" />
        <stop offset="100%" stop-color="#2E7D5B" stop-opacity=".75" />
      </linearGradient>
    </defs>
    <rect width="800" height="200" fill="url(#ucg1)" />
    <!-- river -->
    <path d="M0 140 Q200 120 400 145 Q600 170 800 130" fill="none" stroke="rgba(255,255,255,.15)" stroke-width="40" />
    <path d="M0 160 Q200 140 400 165 Q600 190 800 150" fill="none" stroke="rgba(255,255,255,.08)" stroke-width="30" />
    <!-- palm tree left -->
    <line x1="120" y1="200" x2="130" y2="80" stroke="rgba(255,255,255,.15)" stroke-width="4" />
    <path d="M130 80 Q110 50 80 60" stroke="rgba(255,255,255,.12)" stroke-width="3" fill="none" />
    <path d="M130 80 Q150 45 175 55" stroke="rgba(255,255,255,.12)" stroke-width="3" fill="none" />
    <path d="M130 80 Q125 42 110 40" stroke="rgba(255,255,255,.12)" stroke-width="3" fill="none" />
    <!-- palm tree right -->
    <line x1="680" y1="200" x2="670" y2="90" stroke="rgba(255,255,255,.12)" stroke-width="3.5" />
    <path d="M670 90 Q650 60 625 70" stroke="rgba(255,255,255,.1)" stroke-width="2.5" fill="none" />
    <path d="M670 90 Q695 55 720 65" stroke="rgba(255,255,255,.1)" stroke-width="2.5" fill="none" />
    <!-- sun -->
    <circle cx="650" cy="40" r="20" fill="rgba(255,255,255,.1)" />
    <circle cx="650" cy="40" r="12" fill="rgba(255,255,255,.08)" />
    <!-- dots decoration -->
    <circle cx="300" cy="50" r="2" fill="rgba(255,255,255,.1)" />
    <circle cx="320" cy="35" r="1.5" fill="rgba(255,255,255,.08)" />
    <circle cx="340" cy="55" r="2.5" fill="rgba(255,255,255,.06)" />
    <circle cx="450" cy="40" r="2" fill="rgba(255,255,255,.1)" />
    <circle cx="480" cy="55" r="1.5" fill="rgba(255,255,255,.07)" />
  </svg>
</template>

<style scoped>
.user-cover-svg { width: 100%; height: 180px; display: block; }
</style>
