<template>
  <svg class="hero-illustration" viewBox="0 0 600 400" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
    <!-- River -->
    <path d="M0 280 Q150 260 300 280 Q450 300 600 270 L600 400 L0 400Z" fill="rgba(255,255,255,.08)" />
    <path d="M0 300 Q120 285 280 300 Q440 315 600 290 L600 400 L0 400Z" fill="rgba(255,255,255,.05)" />
    <!-- Palm trees -->
    <g opacity=".15">
      <line x1="520" y1="280" x2="520" y2="160" stroke="#fff" stroke-width="4" />
      <path d="M520 160 Q490 140 460 155" stroke="#fff" stroke-width="3" fill="none" />
      <path d="M520 160 Q550 135 580 145" stroke="#fff" stroke-width="3" fill="none" />
      <path d="M520 160 Q510 130 495 125" stroke="#fff" stroke-width="3" fill="none" />
      <path d="M520 160 Q535 128 555 120" stroke="#fff" stroke-width="3" fill="none" />
      <path d="M520 165 Q485 155 470 170" stroke="#fff" stroke-width="2.5" fill="none" />
      <path d="M520 165 Q555 150 575 160" stroke="#fff" stroke-width="2.5" fill="none" />
    </g>
    <g opacity=".1" transform="translate(-80, 20)">
      <line x1="520" y1="280" x2="520" y2="180" stroke="#fff" stroke-width="3.5" />
      <path d="M520 180 Q495 162 468 175" stroke="#fff" stroke-width="2.5" fill="none" />
      <path d="M520 180 Q545 158 572 165" stroke="#fff" stroke-width="2.5" fill="none" />
      <path d="M520 180 Q512 152 498 148" stroke="#fff" stroke-width="2.5" fill="none" />
      <path d="M520 180 Q532 150 550 144" stroke="#fff" stroke-width="2.5" fill="none" />
    </g>
    <!-- Boat -->
    <g opacity=".12" transform="translate(80, 240)">
      <path d="M0 20 Q20 30 60 30 Q80 30 90 20 Q70 35 20 35Z" fill="#fff" />
      <line x1="40" y1="20" x2="40" y2="-5" stroke="#fff" stroke-width="2" />
      <path d="M42 -5 Q55 5 42 15" fill="rgba(255,255,255,.6)" />
    </g>
    <!-- Fruits cluster -->
    <g opacity=".1" transform="translate(480, 60)">
      <circle cx="0" cy="0" r="12" fill="#E8A33D" />
      <circle cx="22" cy="5" r="10" fill="#E8A33D" />
      <circle cx="8" cy="20" r="11" fill="#E8A33D" />
      <path d="M5 -14 Q8 -22 15 -18" stroke="#4BA97D" stroke-width="2" fill="none" />
    </g>
    <!-- Sun/moon -->
    <circle cx="530" cy="60" r="30" fill="rgba(232,163,61,.12)" />
    <circle cx="530" cy="60" r="22" fill="rgba(232,163,61,.08)" />
    <!-- Small waves -->
    <path d="M50 310 Q70 305 90 310 Q110 315 130 310" stroke="rgba(255,255,255,.08)" stroke-width="2" fill="none" />
    <path d="M200 320 Q220 315 240 320 Q260 325 280 320" stroke="rgba(255,255,255,.06)" stroke-width="2" fill="none" />
    <path d="M350 305 Q370 300 390 305 Q410 310 430 305" stroke="rgba(255,255,255,.07)" stroke-width="2" fill="none" />
  </svg>
</template>

<style scoped>
.hero-illustration {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}
</style>
