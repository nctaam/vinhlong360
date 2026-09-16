<template>
  <section class="home-travel-companion block reveal" aria-label="Tiện Ích Du Khách Thực Địa Vĩnh Long" data-home-travel-companion>
    <div class="home-travel-companion__head section-head">
      <div class="sh-text">
        <span class="home-travel-companion__eyebrow" data-color-role="brand">
          <IconLine name="phone" />
          <span>Traveler Live Companion · Thực địa thông suốt</span>
        </span>
        <h2>Tiện Ích Du Khách <em class="editorial-italic-accent" aria-hidden="true">Thực Địa</em></h2>
        <p class="sh-sub">Cập nhật lịch vận hành bến phà, luồng tàu du lịch sông Cổ Chiên và danh bạ cứu hộ, hỗ trợ lữ khách 24/7.</p>
      </div>
    </div>

    <!-- Compact Frosted Glass Quick Utility Banner -->
    <div class="home-companion-quick-utility" role="region" aria-label="Thông báo khẩn và trạng thái luồng tuyến">
      <div class="home-companion-utility-pill">
        <span class="home-companion-utility-pill__pulse" aria-hidden="true" />
        <IconLine name="route" />
        <span class="home-companion-utility-pill__text">
          <strong>Phà Đình Khao:</strong> Hoạt động 24/24h (Long Hồ ↔ Chợ Lách) · <em>Bình thường</em>
        </span>
      </div>
      <div class="home-companion-quick-hotlines">
        <a
          href="tel:+842703822305"
          class="home-hotline-btn home-hotline-btn--quick"
          aria-label="Gọi hotline Cứu hộ đường thủy 24/7: (0270) 3822 305"
        >
          <div class="home-hotline-btn__call">
            <IconLine name="phone" />
            <span class="home-hotline-btn__num">(0270) 3822 305</span>
          </div>
        </a>
        <a
          href="tel:+842703822994"
          class="home-hotline-btn home-hotline-btn--quick"
          aria-label="Gọi hotline Hỗ trợ du khách 24/7: 0270 3822 994"
        >
          <div class="home-hotline-btn__call">
            <IconLine name="shield-check" />
            <span class="home-hotline-btn__num">0270 3822 994</span>
          </div>
        </a>
      </div>
    </div>

    <div class="home-travel-companion__grid">
      <!-- 1. Bến Phà Đình Khao -->
      <article class="home-companion-card" data-companion-ferry="dinh-khao">
        <div class="home-companion-card__header">
          <span class="home-companion-card__icon" aria-hidden="true">
            <IconLine name="route" />
          </span>
          <div>
            <span class="home-companion-card__badge home-companion-card__badge--active">Hoạt động 24/24h</span>
            <h3 class="home-companion-card__title">Bến Phà Đình Khao (QL57)</h3>
          </div>
        </div>
        <p class="home-companion-card__desc">
          Vượt sông Cổ Chiên (1.200m), nối TP Vĩnh Long & Chợ Lách. Phà 100–200 tấn vận hành liên tục cả ngày lẫn đêm.
        </p>
        <div class="home-companion-card__meta">
          <div class="home-companion-meta-row">
            <IconLine name="clock" />
            <span><strong>Ban ngày:</strong> 10–15 phút/chuyến</span>
          </div>
          <div class="home-companion-meta-row">
            <IconLine name="moon" />
            <span><strong>Đêm (22:00 – 04:00):</strong> 30–45 phút/chuyến</span>
          </div>
          <div class="home-companion-meta-row">
            <IconLine name="tag" />
            <span><strong>Giá vé:</strong> Xe máy 6.000đ · Ô tô từ 25.000đ</span>
          </div>
        </div>
        <NuxtLink to="/dia-diem/ben-pha-dinh-khao-vinh-long" class="home-companion-card__link">
          <span>Xem tọa độ & hướng dẫn lên phà</span>
          <IconLine name="arrow-right" aria-hidden="true" />
        </NuxtLink>
      </article>

      <!-- 2. Bến Phà An Bình & Bến Tàu Du Lịch -->
      <article class="home-companion-card" data-companion-ferry="an-binh">
        <div class="home-companion-card__header">
          <span class="home-companion-card__icon" aria-hidden="true">
            <IconLine name="map" />
          </span>
          <div>
            <span class="home-companion-card__badge home-companion-card__badge--scheduled">04:30 – 22:30 hàng ngày</span>
            <h3 class="home-companion-card__title">Bến Phà An Bình & Bến Tàu</h3>
          </div>
        </div>
        <p class="home-companion-card__desc">
          Bến thuyền Công viên Sông Tiền sang cù lao An Bình (600m). Đò máy, cano du lịch tham quan vườn cây rạch nhỏ.
        </p>
        <div class="home-companion-card__meta">
          <div class="home-companion-meta-row">
            <IconLine name="clock" />
            <span><strong>Tần suất:</strong> 10–15 phút/chuyến đò qua cù lao</span>
          </div>
          <div class="home-companion-meta-row">
            <IconLine name="route" />
            <span><strong>Tàu du lịch:</strong> Bến tàu đón cano đi rạch dừa nước</span>
          </div>
          <div class="home-companion-meta-row">
            <IconLine name="phone" />
            <span><strong>Điều phối phà:</strong> 0270 3822 514</span>
          </div>
        </div>
        <NuxtLink to="/dia-diem/ben-pha-an-binh-vinh-long" class="home-companion-card__link">
          <span>Xem lộ trình qua cù lao An Bình</span>
          <IconLine name="arrow-right" aria-hidden="true" />
        </NuxtLink>
      </article>

      <!-- 3. Thời Tiết & Luồng Tuyến Sông Nước -->
      <article class="home-companion-card" data-companion-navigation>
        <div class="home-companion-card__header">
          <span class="home-companion-card__icon" aria-hidden="true">
            <IconLine name="sun" />
          </span>
          <div>
            <span class="home-companion-card__badge home-companion-card__badge--info">Thời tiết & Thủy triều</span>
            <h3 class="home-companion-card__title">Thời Tiết & Lộ Trình Con Nước</h3>
          </div>
        </div>
        <p class="home-companion-card__desc">
          Lộ trình nhật triều: Nước lớn (08:30–13:30) đi rạch dừa Cù Lao; Nước ròng (15:00–18:00) khám phá vòm gốm Mang Thít.
        </p>
        <div class="home-companion-card__meta">
          <div class="home-companion-meta-row">
            <IconLine name="route" />
            <span><strong>Nước lớn (08:30–13:30):</strong> Rạch dừa nước Cù Lao An Bình & vườn trái cây</span>
          </div>
          <div class="home-companion-meta-row">
            <IconLine name="map" />
            <span><strong>Nước ròng (15:00–18:00):</strong> Vương quốc gốm Kênh Thầy Cai & chùa Khmer cổ</span>
          </div>
          <div class="home-companion-meta-row">
            <IconLine name="sun" />
            <span><strong>Thời tiết bến sông:</strong> 28°C – 32°C (Nắng dịu, gió thoảng)</span>
          </div>
        </div>
        <NuxtLink to="/theo-mua" class="home-companion-card__link">
          <span>Xem cẩm nang du lịch theo mùa vụ</span>
          <IconLine name="arrow-right" aria-hidden="true" />
        </NuxtLink>
      </article>

      <!-- 4. Danh Bạ Cứu Hộ & Hotline Du Khách 24/7 -->
      <article class="home-companion-card home-companion-card--hotlines" data-companion-hotlines>
        <div class="home-companion-card__header">
          <span class="home-companion-card__icon home-companion-card__icon--emergency" aria-hidden="true">
            <IconLine name="shield-check" />
          </span>
          <div>
            <span class="home-companion-card__badge home-companion-card__badge--alert">Hỗ trợ khẩn cấp 24/7</span>
            <h3 class="home-companion-card__title">Đường Dây Nóng Hỗ Trợ Du Khách</h3>
          </div>
        </div>
        <p class="home-companion-card__desc">
          Kết nối trực tiếp lực lượng cứu nạn đường thủy và trung tâm tư vấn du lịch Vĩnh Long khi cần trợ giúp thực địa.
        </p>

        <div class="home-companion-hotlines-list">
          <a
            v-for="hl in HOTLINES"
            :key="hl.phone"
            :href="hl.telUri"
            class="home-hotline-btn"
            :class="{ 'home-hotline-btn--priority': hl.priority }"
          >
            <div class="home-hotline-btn__text">
              <strong class="home-hotline-btn__name">{{ hl.name }}</strong>
              <span class="home-hotline-btn__scope">{{ hl.scope }}</span>
            </div>
            <div class="home-hotline-btn__call">
              <IconLine name="phone" />
              <span class="home-hotline-btn__num">{{ hl.phone }}</span>
            </div>
          </a>
        </div>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
import IconLine from '~/components/IconLine.vue'

interface EmergencyContact {
  readonly name: string
  readonly phone: string
  readonly telUri: string
  readonly scope: string
  readonly priority: boolean
}

const HOTLINES: readonly EmergencyContact[] = [
  {
    name: 'Cứu hộ Đường thủy CSGT (24/7)',
    phone: '(0270) 3822 305',
    telUri: 'tel:+842703822305',
    scope: 'Sự cố đò phà, tàu thuyền sông Tiền & Cổ Chiên',
    priority: true,
  },
  {
    name: 'Cứu hộ & Hỗ trợ Du khách Vĩnh Long',
    phone: '0270 3822 994',
    telUri: 'tel:+842703822994',
    scope: 'Cứu hộ du khách, hỗ trợ an toàn thực địa 24/7',
    priority: true,
  },
  {
    name: 'Tư vấn Du lịch Vĩnh Long 360',
    phone: '0270 3822 188',
    telUri: 'tel:+842703822188',
    scope: 'Tư vấn thực địa, phản ánh chất lượng dịch vụ',
    priority: false,
  },
  {
    name: 'Cấp cứu Y tế Toàn tỉnh',
    phone: '115',
    telUri: 'tel:115',
    scope: 'Cứu thương khẩn cấp, bệnh viện đa khoa tỉnh',
    priority: true,
  },
  {
    name: 'Công an Phản ứng nhanh',
    phone: '113',
    telUri: 'tel:113',
    scope: 'Bảo đảm an ninh trật tự và an toàn du khách',
    priority: false,
  },
]
</script>

<style scoped>
.home-travel-companion {
  max-width: var(--maxw);
  margin-inline: auto;
  padding-inline: var(--space-5);
  padding-block: var(--space-8);
}

.home-travel-companion__eyebrow {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--color-brand);
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  text-transform: uppercase;
  letter-spacing: var(--tracking-caps);
  margin-block-end: var(--space-2);
}

.home-travel-companion__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: var(--space-5);
  margin-block-start: var(--space-6);
}

@media (min-width: 1024px) {
  .home-travel-companion__grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

.home-companion-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  padding: var(--space-5);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-surface);
  box-shadow: 0 2px 8px rgba(var(--black-rgb), 0.04);
  transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.2s ease, box-shadow 0.25s ease;
}

.home-companion-card:hover {
  transform: translateY(-2px);
  border-color: color-mix(in srgb, var(--river-600) 45%, var(--color-border));
  box-shadow: 0 8px 20px rgba(var(--black-rgb), 0.08);
}

.home-companion-card:active {
  transform: scale(0.98);
}

.home-companion-card__header {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
}

.home-companion-card__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  flex-shrink: 0;
  border-radius: var(--radius-control);
  background: color-mix(in srgb, var(--river-600) 12%, transparent);
  color: var(--river-600);
  font-size: 1.25rem;
}

.home-companion-card__icon--emergency {
  background: color-mix(in srgb, var(--color-error) 12%, transparent);
  color: var(--color-error);
}

.home-companion-card__badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: var(--radius-pill, 9999px);
  font-size: 11px;
  font-weight: var(--weight-bold);
  margin-block-end: 4px;
}

.home-companion-card__badge--active {
  background: color-mix(in srgb, var(--orchard-600) 14%, transparent);
  color: var(--orchard-600);
}

.home-companion-card__badge--scheduled {
  background: color-mix(in srgb, var(--harvest-700) 14%, transparent);
  color: var(--harvest-700);
}

.home-companion-card__badge--info {
  background: color-mix(in srgb, var(--river-600) 14%, transparent);
  color: var(--river-600);
}

.home-companion-card__badge--alert {
  background: color-mix(in srgb, var(--color-error) 14%, transparent);
  color: var(--color-error);
}

.home-companion-card__title {
  margin: 0;
  font-family: var(--font-editorial-display);
  font-size: var(--text-base);
  color: var(--color-text);
  line-height: 1.3;
}

.home-companion-card__desc {
  margin: 0;
  font-size: var(--text-xs);
  color: var(--color-text);
  line-height: 1.55;
  opacity: 0.9;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.home-companion-card__meta {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-3);
  background: var(--color-canvas);
  border-radius: var(--radius-control);
}

.home-companion-meta-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-xs);
  color: var(--color-text);
}

.home-companion-meta-row .line-icon {
  color: var(--color-brand);
  flex-shrink: 0;
}

.home-companion-card__link {
  min-height: 44px;
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--color-action);
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  text-decoration: none;
  margin-top: auto;
  transition: transform 0.2s ease;
}

.home-companion-card__link:hover {
  text-decoration: underline;
  transform: translateX(2px);
}

/* Hotline buttons */
.home-companion-hotlines-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.home-hotline-btn {
  min-height: 48px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  background: var(--color-canvas);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  text-decoration: none;
  color: var(--color-text);
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.home-hotline-btn:hover {
  border-color: var(--color-brand);
  background: var(--color-surface);
  transform: translateY(-1px);
}

.home-hotline-btn:active {
  transform: scale(0.98);
}

.home-hotline-btn--priority {
  border-color: color-mix(in srgb, var(--color-error) 40%, var(--color-border));
}

.home-hotline-btn__text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.home-hotline-btn__name {
  font-size: var(--text-xs);
  color: var(--color-text);
  line-height: 1.2;
}

.home-hotline-btn__scope {
  font-size: 11px;
  color: var(--color-text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.home-hotline-btn__call {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background: color-mix(in srgb, var(--river-600) 12%, transparent);
  color: var(--river-600);
  border-radius: var(--radius-pill, 9999px);
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  font-family: var(--font-mono, monospace);
  flex-shrink: 0;
}

.home-hotline-btn--priority .home-hotline-btn__call {
  background: color-mix(in srgb, var(--color-error) 14%, transparent);
  color: var(--color-error);
}

/* Compact Frosted Glass Quick Utility Banner */
.home-companion-quick-utility {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  background: rgba(var(--white-rgb), 0.05);
  border: 1px solid var(--border-liquid-glass);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border-radius: var(--radius-surface);
  box-shadow: var(--shadow-card-ambient);
  margin-block-start: var(--space-4);
}

.home-companion-utility-pill {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-xs);
  color: var(--color-text);
}

.home-companion-utility-pill .line-icon {
  color: var(--color-brand);
}

.home-companion-utility-pill__pulse {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--orchard-600);
  box-shadow: 0 0 8px rgba(var(--white-rgb), 0.4);
  animation: companion-pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
  flex-shrink: 0;
}

@keyframes companion-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(0.9); }
}

.home-companion-utility-pill__text strong {
  color: var(--color-text);
  font-weight: var(--weight-bold);
}

.home-companion-utility-pill__text em {
  font-style: normal;
  color: var(--orchard-600);
  font-weight: var(--weight-semibold);
}

.home-companion-quick-hotlines {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
}

.home-hotline-btn--quick {
  min-height: 48px;
  padding: var(--space-2) var(--space-4);
  background: rgba(var(--black-rgb), 0.75);
  border: 1px solid var(--border-liquid-glass);
  border-radius: var(--radius-pill, 9999px);
  text-decoration: none;
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  color: var(--surface-white);
  transition: transform 0.2s ease, background-color 0.2s ease;
}

.home-hotline-btn--quick:hover {
  transform: translateY(-1px);
  background: rgba(var(--black-rgb), 0.85);
  border-color: var(--alluvial-gold);
}

.home-hotline-btn--quick .home-hotline-btn__call {
  background: transparent;
  color: var(--alluvial-gold);
  padding: 0;
}

.home-hotline-btn--quick .line-icon {
  color: var(--alluvial-gold);
}
</style>
