<template>
  <section class="home-travel-planner block reveal" aria-label="Gợi Ý Lịch Trình Tinh Tuyển Vĩnh Long" data-home-travel-planner>
    <div class="home-travel-planner__head section-head">
      <div class="sh-text">
        <span class="home-travel-planner__eyebrow" data-color-role="brand">
          <IconLine name="route" />
          <span>Smart Travel Planner · Tối ưu thời gian</span>
        </span>
        <h2>Gợi Ý Lịch Trình <em class="editorial-italic-accent" aria-hidden="true">Tinh Tuyển</em></h2>
        <p class="sh-sub">3 phương án lộ trình được thiết kế chuẩn xác từ kinh nghiệm thực địa, giúp bạn khám phá trọn vẹn tinh hoa Vĩnh Long theo quỹ thời gian cá nhân.</p>
      </div>
      <NuxtLink to="/lich-trinh" class="see-all">
        <span>Xem toàn bộ 16 lịch trình</span>
        <IconLine name="arrow-right" class="inline-arrow" aria-hidden="true" />
      </NuxtLink>
    </div>

    <!-- Interactive Planner Tabs -->
    <div class="home-travel-planner__tabs-nav" role="tablist" aria-label="Chọn thời lượng chuyến đi">
      <button
        v-for="it in ITINERARIES"
        :key="it.id"
        type="button"
        role="tab"
        class="home-planner-tab-btn"
        :class="{ 'is-active': activeTabId === it.id }"
        :aria-selected="activeTabId === it.id"
        @click="activeTabId = it.id"
      >
        <span class="home-planner-tab-btn__badge">{{ it.durationBadge }}</span>
        <span class="home-planner-tab-btn__title">{{ it.shortTitle }}</span>
        <span class="home-planner-tab-btn__terroir">{{ it.terroir }}</span>
      </button>
    </div>

    <!-- Active Itinerary Content Card -->
    <div v-if="activeItinerary" class="home-planner-card" data-active-itinerary>
      <div class="home-planner-card__header">
        <div class="home-planner-card__title-group">
          <div class="home-planner-card__meta-badges">
            <span class="home-planner-card__badge">
              <IconLine name="calendar" />
              <span>{{ activeItinerary.durationLabel }}</span>
            </span>
            <span class="home-planner-card__terroir-badge">
              <IconLine name="map" />
              <span>{{ activeItinerary.terroir }}</span>
            </span>
            <!-- Fieldwork Certification Seal -->
            <span class="home-planner-card__seal" title="Đã đối soát thực địa">
              <IconLine name="shield-check" />
              <span>Bảo chứng thực địa</span>
            </span>
          </div>

          <div class="home-planner-card__trust">
            <SourceMark tier="official" source-title="Ban biên tập Vĩnh Long 360" compact />
            <FreshnessLine status="fresh" updated-label="Thực địa 2026" />
          </div>

          <h3 class="home-planner-card__title">{{ activeItinerary.title }}</h3>
          <p class="home-planner-card__theme">{{ activeItinerary.theme }}</p>
        </div>
        <div class="home-planner-card__actions">
          <NuxtLink :to="activeItinerary.to" class="btn btn-primary" data-color-role="action-primary">
            <span>Xem chi tiết lộ trình</span>
            <IconLine name="arrow-right" aria-hidden="true" />
          </NuxtLink>
          <NuxtLink to="/tao-lich-trinh" class="btn btn-outline" data-color-role="action-secondary">
            <IconLine name="pencil" />
            <span>Tùy chỉnh lịch trình riêng</span>
          </NuxtLink>
        </div>
      </div>

      <div class="home-planner-card__stops">
        <h4 class="home-planner-card__stops-heading">Các chặng dừng chân nổi bật:</h4>
        <div class="home-planner-card__timeline">
          <div
            v-for="(stop, idx) in activeItinerary.stops"
            :key="stop.name"
            class="home-planner-stop"
          >
            <div class="home-planner-stop__marker">
              <span class="home-planner-stop__number">{{ idx + 1 }}</span>
            </div>
            <div class="home-planner-stop__info">
              <span class="home-planner-stop__time">{{ stop.time }}</span>
              <strong class="home-planner-stop__name">{{ stop.name }}</strong>
              <span class="home-planner-stop__desc">{{ stop.desc }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import IconLine from '~/components/IconLine.vue'
import SourceMark from '~/components/SourceMark.vue'
import FreshnessLine from '~/components/FreshnessLine.vue'

interface ItineraryStop {
  readonly time: string
  readonly name: string
  readonly desc: string
}

interface CuratedItinerary {
  readonly id: string
  readonly durationBadge: string
  readonly shortTitle: string
  readonly terroir: string
  readonly durationLabel: string
  readonly title: string
  readonly theme: string
  readonly stops: readonly ItineraryStop[]
  readonly to: string
}

const ITINERARIES: readonly CuratedItinerary[] = [
  {
    id: 'mot-ngay-cu-lao-an-binh',
    durationBadge: '1 Ngày',
    shortTitle: 'Nông Dân Cù Lao',
    terroir: 'Xanh Cù Lao',
    durationLabel: '07:30 – 17:00 (1 Ngày)',
    title: 'Một Ngày Làm Nông Dân Cù Lao & Hái Trái Cây Sông Cổ Chiên',
    theme: 'Trải nghiệm sông nước miệt vườn thanh bình, thưởng ngoạn vườn chôm chôm chín cây và ẩm thực cá tai tượng chiên xù.',
    stops: [
      { time: '07:30 - 09:00', name: 'Bến tàu Du lịch Vĩnh Long → Cù lao An Bình', desc: 'Xuồng máy vượt sông Cổ Chiên lộng gió, đón bình minh trên sông.' },
      { time: '09:00 - 11:30', name: 'Vườn chôm chôm & Sầu riêng Bình Hòa Phước', desc: 'Tự tay hái và thưởng thức quả chín cây, chèo xuồng rạch dừa nước.' },
      { time: '11:30 - 13:30', name: 'Bữa trưa miệt vườn tại Homestay Út Trinh', desc: 'Thưởng thức Cá tai tượng chiên xù, canh chua cá linh bông điên điển.' },
      { time: '13:30 - 16:30', name: 'Khu du lịch sinh thái Vinh Sang', desc: 'Mặc áo bà ba tát mương bắt cá đồng, trò chơi dân gian và nghe tài tử.' },
    ],
    to: '/lich-trinh/mot-ngay-cu-lao-an-binh',
  },
  {
    id: 'di-san-mang-thit-tra-vinh',
    durationBadge: '2N1Đ',
    shortTitle: 'Gốm Đỏ Mang Thít',
    terroir: 'Đất nung Mang Thít',
    durationLabel: '2 Ngày 1 Đêm',
    title: 'Về Miền Di Sản Gốm Đỏ Mang Thít & Đêm Đờn Ca Tài Tử Cù Lao',
    theme: 'Chiêm ngưỡng kỳ quan Vương quốc Đỏ trăm năm tuổi, tự tay nặn gốm nung thủ công và lắng đọng cùng khúc ca tài tử bên sông.',
    stops: [
      { time: 'Ngày 1 (Sáng)', name: 'Quần thể Lò gạch gốm Mang Thít ven kênh Thầy Cai', desc: 'Check-in những "kim tự tháp đỏ", trải nghiệm nặn gốm xưởng Thầy Kay.' },
      { time: 'Ngày 1 (Trưa)', name: 'Thưởng thức Bánh xèo hến Cổ Chiên & Nhà Gốm Tư Buôi', desc: 'Ẩm thực độc bản hến bãi cồn và chiêm ngưỡng kiến trúc gốm đỏ 300m².' },
      { time: 'Ngày 1 (Tối)', name: 'Nghỉ đêm Homestay Út Trinh / Ba Linh & Nghe Đờn ca tài tử', desc: 'Mâm cơm gia đình bến sông, hòa tấu đàn kìm réo rắt đêm trăng thanh.' },
      { time: 'Ngày 2', name: 'Đạp xe đường làng An Bình & Mua sắm đặc sản OCOP', desc: 'Thăm làng kẹo chuối, mua khoai lang Bình Tân và bưởi năm roi làm quà.' },
    ],
    to: '/lich-trinh/di-san-mang-thit-tra-vinh',
  },
  {
    id: 'mien-tay-3-ngay',
    durationBadge: '3N2Đ',
    shortTitle: 'Toàn Cảnh Đất Phương Nam',
    terroir: 'Phù Sa Cổ Chiên',
    durationLabel: '3 Ngày 2 Đêm',
    title: 'Toàn Cảnh Đất Phương Nam: Sinh Thái, Làng Nghề & Văn Hóa Tâm Linh',
    theme: 'Đại hành trình liên kết tam giác văn hóa Vĩnh Long – Trà Vinh – Bến Tre từ sông ra biển lớn.',
    stops: [
      { time: 'Ngày 1', name: 'Trọn vẹn Cù Lao An Bình & KDL Sinh thái Vinh Sang', desc: 'Vườn cây ăn trái nhiệt đới, dỡ chà bắt cá, nghỉ đêm nhà vườn sinh thái.' },
      { time: 'Ngày 2', name: 'Vương quốc Đỏ Mang Thít → Quần thể Chùa Khmer Trà Vinh', desc: 'Viếng Chùa cổ Khmer Hạnh Phúc Tăng, Ao Bà Om, thưởng thức Bún nước lèo.' },
      { time: 'Ngày 3', name: 'Thủy lộ Cồn Phụng sông Tiền & Xứ Dừa Bến Tre', desc: 'Đi thuyền khám phá sinh thái cồn bãi sông Tiền, kết thúc chuyến đi.' },
    ],
    to: '/lich-trinh/mien-tay-3-ngay',
  },
]

const activeTabId = ref<string>('mot-ngay-cu-lao-an-binh')

const activeItinerary = computed(() => {
  return ITINERARIES.find(it => it.id === activeTabId.value) || ITINERARIES[0]
})
</script>

<style scoped>
.home-travel-planner {
  max-width: var(--maxw);
  margin-inline: auto;
  padding-inline: var(--space-5);
  padding-block: clamp(var(--space-fib-4), 6vw, var(--space-fib-5));
}

.home-travel-planner__eyebrow {
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

.home-travel-planner__tabs-nav {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  margin-block: var(--space-fib-4) var(--space-fib-3);
}

.home-planner-tab-btn {
  min-height: 48px;
  display: inline-flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-5);
  background: var(--color-surface);
  border: 1px solid var(--border-liquid-glass, var(--color-border));
  border-radius: var(--radius-pill, 9999px);
  color: var(--color-text);
  font-family: inherit;
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  cursor: pointer;
  box-shadow: 0 1px 3px rgba(var(--black-rgb), 0.04);
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.home-planner-tab-btn:hover {
  border-color: color-mix(in srgb, var(--mangthit-600) 45%, var(--color-border));
  transform: translateY(-2px);
}

.home-planner-tab-btn:active {
  transform: scale(0.98);
}

.home-planner-tab-btn.is-active {
  background: var(--color-brand);
  color: var(--surface-white);
  border-color: var(--color-brand);
  box-shadow: 0 4px 14px color-mix(in srgb, var(--mangthit-600) 35%, transparent);
}

.home-planner-tab-btn__badge {
  padding: 2px 8px;
  background: var(--color-canvas);
  color: var(--color-text);
  border-radius: var(--radius-pill, 9999px);
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
}

.home-planner-tab-btn__terroir {
  font-size: 11px;
  color: var(--alluvial-gold);
  font-weight: var(--weight-bold);
  padding: 1px 6px;
  border-radius: var(--radius-pill, 9999px);
  background: rgba(var(--black-rgb), 0.08);
}

.home-planner-tab-btn.is-active .home-planner-tab-btn__terroir {
  color: var(--surface-white);
  background: rgba(var(--white-rgb), 0.22);
}

.home-planner-tab-btn.is-active .home-planner-tab-btn__badge {
  background: rgba(var(--white-rgb), 0.22);
  color: var(--surface-white);
}

/* Planner Card */
.home-planner-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  padding: clamp(var(--space-5), 4vw, var(--space-8));
  background: var(--color-surface);
  border: 1px solid var(--border-liquid-glass, var(--color-border));
  border-radius: var(--radius-surface);
  box-shadow: var(--shadow-card-ambient);
}

.home-planner-card__header {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  border-bottom: 1px solid var(--color-border);
  padding-bottom: var(--space-5);
}

@media (min-width: 840px) {
  .home-planner-card__header {
    flex-direction: row;
    align-items: flex-start;
    justify-content: space-between;
  }
}

.home-planner-card__title-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  flex: 1;
}

.home-planner-card__meta-badges {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
}

.home-planner-card__terroir-badge {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1h);
  padding: 3px 10px;
  background: color-mix(in srgb, var(--mangthit-600) 12%, transparent);
  color: var(--mangthit-600);
  border-radius: var(--radius-pill, 9999px);
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
}

.home-planner-card__seal {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: 3px 10px;
  background: color-mix(in srgb, var(--orchard-600) 12%, transparent);
  color: var(--orchard-600);
  border-radius: var(--radius-pill, 9999px);
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  border: 1px solid color-mix(in srgb, var(--orchard-600) 30%, transparent);
}

.home-planner-card__trust {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  margin-block-start: var(--space-1);
}

.home-planner-card__badge {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  width: fit-content;
  padding: 3px 10px;
  background: color-mix(in srgb, var(--river-600) 12%, transparent);
  color: var(--river-600);
  border-radius: var(--radius-pill, 9999px);
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
}

.home-planner-card__title {
  margin: 0;
  font-family: var(--font-editorial-display);
  font-size: clamp(var(--text-xl), 3vw, var(--text-2xl));
  color: var(--color-text);
  line-height: 1.25;
}

.home-planner-card__theme {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  line-height: 1.5;
}

.home-planner-card__actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  flex-shrink: 0;
}

.home-planner-card__actions .btn {
  min-height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  border-radius: var(--radius-control);
  text-decoration: none;
  transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.home-planner-card__actions .btn:active {
  transform: scale(0.98);
}

/* Timeline */
.home-planner-card__stops {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.home-planner-card__stops-heading {
  margin: 0;
  font-size: var(--text-sm);
  font-weight: var(--weight-bold);
  text-transform: uppercase;
  letter-spacing: var(--tracking-caps);
  color: var(--color-text-muted);
}

.home-planner-card__timeline {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--space-4);
}

.home-planner-stop {
  display: flex;
  gap: var(--space-3);
  padding: var(--space-4);
  background: var(--color-canvas);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-surface);
}

.home-planner-stop__marker {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  flex-shrink: 0;
  background: var(--color-brand);
  color: var(--surface-white);
  border-radius: var(--radius-pill, 9999px);
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
}

.home-planner-stop__info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.home-planner-stop__time {
  font-size: 11px;
  color: var(--color-brand);
  font-weight: var(--weight-bold);
}

.home-planner-stop__name {
  font-size: var(--text-sm);
  color: var(--color-text);
  line-height: 1.35;
}

.home-planner-stop__desc {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  line-height: 1.4;
  margin-top: 2px;
}
</style>
