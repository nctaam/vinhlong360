<template>
  <section class="not-found">
    <div class="nf-inner">
      <span class="nf-emoji">🗺️</span>
      <h1 class="nf-code">404</h1>
      <p class="nf-msg">Trang bạn tìm không tồn tại hoặc đã bị xóa.</p>
      <form class="nf-search" @submit.prevent="onSearch">
        <input v-model="q" type="search" placeholder="Tìm đặc sản, trải nghiệm…" />
        <button type="submit">Tìm</button>
      </form>
      <div class="nf-actions">
        <NuxtLink to="/" class="nf-btn nf-btn-primary">Về trang chủ</NuxtLink>
        <button class="nf-btn nf-btn-outline" @click="$router.back()">Quay lại</button>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
if (import.meta.server) {
  const event = useRequestEvent()
  if (event) setResponseStatus(event, 404)
}

useSeoMeta({ title: '404 — vinhlong360', robots: 'noindex, nofollow' })

const q = ref('')
function onSearch() {
  if (q.value.trim()) navigateTo(`/tim-kiem?q=${encodeURIComponent(q.value.trim())}`)
}
</script>

<style scoped>
.not-found {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 70vh;
  padding: var(--space-8) var(--space-5);
  text-align: center;
}

.nf-inner {
  max-width: 420px;
}

.nf-emoji {
  font-size: 3rem;
  display: block;
  margin-bottom: var(--space-3);
}

.nf-code {
  font-size: clamp(3rem, 10vw, 5rem);
  font-weight: var(--weight-bold);
  color: var(--accent);
  letter-spacing: var(--tracking-tight);
  line-height: 1;
  margin: 0 0 var(--space-3);
}

.nf-msg {
  font-size: var(--text-base);
  color: var(--muted);
  margin-bottom: var(--space-6);
  line-height: var(--leading-relaxed);
}

.nf-search {
  display: flex;
  gap: var(--space-2);
  margin-bottom: var(--space-5);
}

.nf-search input {
  flex: 1;
  padding: var(--space-3) var(--space-4);
  border: 1.5px solid var(--line);
  border-radius: var(--radius-full, 100px);
  background: var(--card);
  font-size: var(--text-sm);
  min-height: 44px;
  transition: border-color var(--ease-out, .2s);
}

.nf-search input:focus {
  outline: none;
  border-color: var(--accent);
}

.nf-search button {
  padding: var(--space-3) var(--space-5);
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: var(--radius-full, 100px);
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  cursor: pointer;
  min-height: 44px;
  transition: background var(--ease-out, .2s);
}

.nf-search button:hover { background: var(--accent-dark); }

.nf-actions {
  display: flex;
  gap: var(--space-3);
  justify-content: center;
}

.nf-btn {
  display: inline-flex;
  align-items: center;
  padding: var(--space-3) var(--space-5);
  border-radius: var(--radius-full, 100px);
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  text-decoration: none;
  cursor: pointer;
  min-height: 44px;
  transition: background var(--ease-out, .2s), transform var(--ease-out, .15s);
}

.nf-btn:active { transform: scale(.97); }

.nf-btn-primary {
  background: var(--accent);
  color: #fff;
  border: none;
}

.nf-btn-primary:hover { background: var(--accent-dark); }

.nf-btn-outline {
  background: transparent;
  color: var(--accent);
  border: 1.5px solid var(--accent);
}

.nf-btn-outline:hover { background: var(--accent); color: #fff; }

.nf-inner { animation: nfIn .5s var(--ease-spring); }
@keyframes nfIn { from { opacity: 0; transform: translateY(16px) scale(.97); } to { opacity: 1; transform: translateY(0) scale(1); } }
.nf-emoji { transition: transform var(--duration-normal) var(--ease-spring); }
.nf-inner:hover .nf-emoji { transform: scale(1.1) rotate(-5deg); }
.nf-btn:hover { transform: translateY(-1px); box-shadow: var(--shadow-md); }
.nf-search button:active { transform: scale(.95); transition-duration: .08s; }

</style>
