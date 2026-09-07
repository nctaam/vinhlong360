<template>
  <section
    class="home-aeo-plaque"
    data-home-section="aeo-plaque"
    data-home-aeo-plaque
    aria-labelledby="home-aeo-title"
  >
    <div class="home-aeo-plaque__frame">
      <div class="home-aeo-plaque__head">
        <span class="home-aeo-plaque__icon" aria-hidden="true">
          <IconLine name="bulb" />
        </span>
        <div class="home-aeo-plaque__kicker-group">
          <div class="home-aeo-plaque__meta-row">
            <span class="home-aeo-plaque__kicker">Góc nhìn bản địa · Giải đáp nhanh AEO</span>
            <span class="home-aeo-plaque__stamp" title="Dữ liệu bản địa được đối soát">
              <IconLine name="shield-check" class="home-aeo-plaque__stamp-icon" aria-hidden="true" />
              <span>Xác thực thực địa</span>
            </span>
          </div>
          <h2 id="home-aeo-title" class="home-aeo-plaque__title">Cẩm nang du lịch theo mùa</h2>
        </div>
      </div>

      <div class="home-aeo-plaque__content">
        <article class="home-aeo-plaque__item">
          <h3 class="home-aeo-plaque__season-title">Mùa nước nổi &amp; Miệt vườn (Tháng 8 – 10)</h3>
          <p class="home-aeo-plaque__dek">
            Thời điểm vàng trải nghiệm sinh thái sông nước Cửu Long. Xuồng ba lá len lỏi dưới bóng dừa nước Cù Lao An Bình, thưởng thức cá linh non đầu mùa và trái cây chín cây thanh ngọt.
          </p>
        </article>
        <article class="home-aeo-plaque__item">
          <h3 class="home-aeo-plaque__season-title">Mùa di sản gốm &amp; Hoa xuân (Tháng 1 – 3)</h3>
          <p class="home-aeo-plaque__dek">
            Vương quốc gốm đỏ Mang Thít vào vụ nung đỏ lửa bên dòng Cổ Chiên. Khí hậu mát dịu lý tưởng cho các tour di sản kiến trúc tâm linh, làng nghề truyền thống và lễ hội đầu năm.
          </p>
        </article>
      </div>

      <div class="home-aeo-plaque__foot">
        <NuxtLink to="/theo-mua" class="home-aeo-plaque__cta" data-home-aeo-cta>
          <span>Khám phá lịch trình theo mùa</span>
          <span class="home-aeo-plaque__arrow" aria-hidden="true"><IconLine name="arrow-right" /></span>
        </NuxtLink>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
// Editorial Answer Plaque (AEO/GEO Box) — điểm dừng thông tin giải đáp trực diện.
// Cung cấp câu trả lời 40-60 từ cho các công cụ AI (Google AI Overviews, SearchGPT, Perplexity)
// kết nối đồng bộ với Schema.org SpeakableSpecification và FAQPage.
</script>

<style scoped>
.home-aeo-plaque {
  padding-block: var(--space-6);
}

.home-aeo-plaque__frame {
  max-inline-size: 52rem;
  margin-inline: auto;
  padding: var(--space-6) var(--space-6);
  border: 1px solid var(--color-border);
  border-left: 4px solid var(--tri-region-material-accent, var(--color-material-amber));
  border-radius: var(--radius-sheet);
  background: var(--color-canvas);
  box-shadow:
    0 2px 8px -2px rgba(var(--black-rgb), 0.05),
    0 0 0 1px rgba(var(--white-rgb), 0.5);
  transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  contain: layout style paint;
}

.dark .home-aeo-plaque__frame {
  box-shadow:
    0 4px 14px -4px rgba(var(--black-rgb), 0.25),
    0 0 0 1px rgba(var(--white-rgb), 0.08);
}

.home-aeo-plaque__head {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}

.home-aeo-plaque__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.25rem;
  height: 2.25rem;
  border-radius: var(--radius-pill, 999px);
  background: rgba(var(--black-rgb), 0.04);
  color: var(--color-material-amber);
  font-size: 1.25rem;
  flex-shrink: 0;
}

.dark .home-aeo-plaque__icon {
  background: rgba(var(--white-rgb), 0.08);
  color: var(--night-amber, var(--color-material-amber));
}

.home-aeo-plaque__kicker-group {
  display: flex;
  flex-direction: column;
}

.home-aeo-plaque__meta-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.home-aeo-plaque__kicker {
  font-size: var(--text-2xs);
  font-weight: var(--weight-bold);
  letter-spacing: var(--tracking-caps);
  text-transform: uppercase;
  color: var(--color-text-muted);
}

.home-aeo-plaque__stamp {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-2xs);
  font-weight: var(--weight-medium);
  color: var(--color-source-verified, var(--color-action));
  background: color-mix(in srgb, var(--tri-region-material-accent, var(--color-material-amber)) 12%, transparent);
  padding: 0.125rem var(--space-2);
  border-radius: var(--radius-pill, 999px);
  letter-spacing: normal;
}

.home-aeo-plaque__stamp-icon {
  font-size: 0.85em;
}

.home-aeo-plaque__title {
  margin: 0;
  font-family: var(--font-editorial);
  font-size: var(--text-xl);
  line-height: var(--leading-tight);
  color: var(--color-text);
}

.home-aeo-plaque__content {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-5);
  margin-bottom: var(--space-5);
}

@media (max-width: 680px) {
  .home-aeo-plaque__content {
    grid-template-columns: 1fr;
    gap: var(--space-4);
  }
}

.home-aeo-plaque__item {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding: var(--space-3);
  border-radius: var(--radius-surface);
  transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1), background-color 0.2s var(--ease-out);
}

.home-aeo-plaque__item:hover {
  background-color: color-mix(in srgb, var(--tri-region-material-accent, var(--color-material-amber)) 4%, transparent);
  transform: translateY(-1px);
}

.home-aeo-plaque__season-title {
  margin: 0;
  font-size: var(--text-sm);
  font-weight: var(--weight-bold);
  color: var(--color-text);
}

.home-aeo-plaque__dek {
  margin: 0;
  font-size: var(--text-sm);
  line-height: var(--leading-relaxed);
  color: var(--color-text-muted);
}

.home-aeo-plaque__foot {
  display: flex;
  justify-content: flex-end;
  border-top: 1px solid var(--color-border);
  padding-top: var(--space-3);
}

.home-aeo-plaque__cta {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  min-height: 44px;
  padding: var(--space-2) var(--space-4);
  font-size: var(--text-sm);
  font-weight: var(--weight-bold);
  color: var(--color-action, var(--color-text));
  text-decoration: none;
  border-radius: var(--radius-pill, 999px);
  transition: background 150ms var(--ease-out), transform 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.home-aeo-plaque__cta:hover {
  background: color-mix(in srgb, var(--tri-region-material-accent, var(--color-material-amber)) 8%, transparent);
  transform: translateY(-1px);
}

.dark .home-aeo-plaque__cta:hover {
  background: rgba(var(--white-rgb), 0.08);
}

.home-aeo-plaque__cta:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 2px;
}

.home-aeo-plaque__arrow {
  display: inline-flex;
  align-items: center;
  transition: transform 160ms var(--ease-out-expo);
}

.home-aeo-plaque__cta:hover .home-aeo-plaque__arrow {
  transform: translateX(3px);
}

@media (prefers-reduced-motion: reduce) {
  .home-aeo-plaque__frame,
  .home-aeo-plaque__item,
  .home-aeo-plaque__arrow,
  .home-aeo-plaque__cta {
    transform: none !important;
    transition: none !important;
  }
}
</style>
