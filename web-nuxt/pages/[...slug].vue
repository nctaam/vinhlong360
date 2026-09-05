<template>
  <section class="not-found">
    <div class="nf-inner">
      <span class="nf-emoji" aria-hidden="true"><IconLine name="map" /></span>
      <h1 class="nf-code">404</h1>
      <p class="nf-msg">Trang bạn tìm không tồn tại hoặc đã bị xóa.</p>
      <form class="nf-search" @submit.prevent="onSearch">
        <input v-model="q" type="search" enterkeyhint="search" placeholder="Tìm đặc sản, trải nghiệm…" aria-label="Tìm kiếm" autocomplete="off" />
        <button type="submit">Tìm</button>
      </form>
      <div class="nf-actions">
        <NuxtLink to="/" class="nf-btn nf-btn-primary">Về trang chủ</NuxtLink>
        <button type="button" class="nf-btn nf-btn-outline" @click="$router.back()">Quay lại</button>
      </div>

      <nav class="nf-suggestions" aria-label="Gợi ý khám phá">
        <p class="nf-suggestions__title">Hoặc bắt đầu hành trình từ:</p>
        <div class="nf-suggestions__list">
          <NuxtLink v-for="item in discoveryLinks" :key="item.to" :to="item.to" class="nf-pill">
            <IconLine :name="item.icon" class="nf-pill__icon" />
            <span>{{ item.label }}</span>
          </NuxtLink>
        </div>
      </nav>
    </div>
  </section>
</template>

<script setup lang="ts">
if (import.meta.server) {
  const event = useRequestEvent()
  if (event) setResponseStatus(event, 404)
}

useSeoMeta({
  title: '404 — Không tìm thấy trang | vinhlong360',
  description: 'Trang bạn tìm kiếm không tồn tại hoặc đã được di chuyển trên Cổng thông tin Vĩnh Long 360.',
  robots: 'noindex, nofollow',
  ogTitle: '404 — Không tìm thấy trang | vinhlong360',
  twitterCard: 'summary_large_image',
})

const q = ref('')
function onSearch() {
  if (q.value.trim()) navigateTo(`/tim-kiem?q=${encodeURIComponent(q.value.trim())}`)
}

const discoveryLinks = [
  { label: 'Điểm đến', to: '/dia-diem', icon: 'compass' },
  { label: 'Ẩm thực', to: '/san-pham', icon: 'bowl' },
  { label: 'Sự kiện', to: '/su-kien', icon: 'calendar' },
  { label: 'OCOP', to: '/ocop', icon: 'gift' },
]
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
  border: .5px solid var(--line);
  border-radius: var(--radius-full);
  background: var(--card);
  font-size: 1rem;
  min-height: 44px;
  transition: border-color .3s var(--ease-out), box-shadow .35s var(--ease-out-expo);
}

.nf-search input:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 1px;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(var(--primary-rgb), .1);
}

.nf-search button {
  padding: var(--space-3) var(--space-5);
  background: var(--accent);
  color: var(--text-on-dark, var(--white));
  border: none;
  border-radius: var(--radius-full);
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  cursor: pointer;
  min-height: 44px;
  transition: background .3s var(--ease-out), transform .35s var(--ease-out-expo), box-shadow .3s var(--ease-out);
}

.nf-search button:hover { background: var(--accent-dark); }
.nf-search button:active { transform: scale(.95); transition-duration: .08s; }
.nf-search button:focus-visible { outline: 2px solid var(--color-focus); outline-offset: 2px; }

.nf-actions {
  display: flex;
  gap: var(--space-3);
  justify-content: center;
}

.nf-btn {
  display: inline-flex;
  align-items: center;
  padding: var(--space-3) var(--space-5);
  border-radius: var(--radius-full);
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  text-decoration: none;
  cursor: pointer;
  min-height: 44px;
  transition: background .3s var(--ease-out), transform .35s var(--ease-out-expo), box-shadow .35s var(--ease-out-expo);
}

.nf-btn:active { transform: scale(.97); }
.nf-btn:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }

.nf-btn-primary {
  background: var(--accent);
  color: var(--text-on-dark, var(--white));
  border: none;
}

.nf-btn-primary:hover { background: var(--accent-dark); }

.nf-btn-outline {
  background: transparent;
  color: var(--accent);
  border: 1.5px solid var(--accent);
}

.nf-btn-outline:hover { background: var(--accent); color: var(--text-on-dark, var(--white)); }

.nf-inner { animation: nfIn .5s var(--ease-out-expo); }
@keyframes nfIn { from { opacity: 0; transform: translateY(16px) scale(.96); } to { opacity: 1; transform: translateY(0) scale(1); } }
.nf-emoji { transition: transform .35s var(--ease-out-expo); }
.nf-inner:hover .nf-emoji { transform: scale(1.1) rotate(-5deg); }
.nf-btn:hover { transform: translateY(-1px); box-shadow: var(--shadow-md); }
.nf-search button:active { transform: scale(.95); transition-duration: .08s; }
.nf-suggestions {
  margin-top: var(--space-8);
  padding-top: var(--space-6);
  border-top: 1px dashed var(--line);
}

.nf-suggestions__title {
  font-size: var(--text-xs);
  font-weight: var(--weight-medium);
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wider, 0.05em);
  margin-bottom: var(--space-3);
}

.nf-suggestions__list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  justify-content: center;
}

.nf-pill {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  min-height: 40px;
  padding: var(--space-2) var(--space-4);
  border: 1px solid var(--line);
  border-radius: var(--radius-full);
  background: var(--card);
  color: var(--ink);
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
  text-decoration: none;
  transition: transform .3s var(--ease-out-expo), border-color .25s var(--ease-out), color .25s var(--ease-out), box-shadow .25s var(--ease-out);
}

.nf-pill__icon {
  font-size: 1.05em;
  color: var(--accent);
}

.nf-pill:hover {
  transform: translateY(-1px);
  border-color: var(--accent);
  color: var(--accent);
  box-shadow: var(--shadow-sm);
}

.nf-pill:active {
  transform: scale(0.96);
}

.nf-pill:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

@media (prefers-reduced-motion: reduce) {
  .nf-inner { animation: none; }
  .nf-emoji { transition: none; }
  .nf-pill { transition: none; }
}
</style>
