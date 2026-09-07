<template>
  <section
    class="ward-terroir-digest"
    data-ward-terroir-digest
    :data-material-accent="accent"
    :aria-labelledby="headingId"
  >
    <header class="ward-terroir-digest__header">
      <div class="ward-terroir-digest__badge">
        <IconLine name="sparkles" aria-hidden="true" />
        <span>Hồ sơ Thực địa Bản xứ · Địa hạt {{ placeName }}</span>
      </div>
      <h2 :id="headingId" class="ward-terroir-digest__title">
        Đặc trưng thổ nhưỡng &amp; Lưu ý hành trình
      </h2>
      <p class="ward-terroir-digest__dek">
        Chỉ dẫn đặc sản OCOP chủ lực, nhịp điệu đò giang sông Cổ Chiên &amp; liên lạc cứu hộ tại địa bàn.
      </p>
    </header>

    <div class="ward-terroir-digest__grid">
      <!-- Cột 1: OCOP & Thổ nhưỡng -->
      <article class="ward-terroir-digest__card ward-terroir-digest__card--ocop">
        <div class="ward-terroir-digest__card-head">
          <span class="ward-terroir-digest__card-icon" aria-hidden="true">
            <IconLine name="award" />
          </span>
          <div class="ward-terroir-digest__head-text">
            <span class="ward-terroir-digest__kicker">Nông sản &amp; Thủ công</span>
            <h3 class="ward-terroir-digest__card-title">Đặc sản &amp; OCOP chủ lực</h3>
          </div>
        </div>

        <ul class="ward-terroir-digest__spec-list">
          <li v-for="(spec, idx) in terroirSpecs" :key="idx" class="ward-terroir-digest__spec-item">
            <div class="ward-terroir-digest__spec-top">
              <strong class="ward-terroir-digest__spec-name">{{ spec.title }}</strong>
              <span v-if="spec.badge" class="ward-terroir-digest__tag">{{ spec.badge }}</span>
            </div>
            <p class="ward-terroir-digest__spec-desc">{{ spec.desc }}</p>
          </li>
        </ul>
      </article>

      <!-- Cột 2: Di chuyển & Đò giang -->
      <article class="ward-terroir-digest__card ward-terroir-digest__card--transit">
        <div class="ward-terroir-digest__card-head">
          <span class="ward-terroir-digest__card-icon" aria-hidden="true">
            <IconLine name="route" />
          </span>
          <div class="ward-terroir-digest__head-text">
            <span class="ward-terroir-digest__kicker">{{ transitGuide.kicker }}</span>
            <h3 class="ward-terroir-digest__card-title">Lưu ý đò giang &amp; lộ trình</h3>
          </div>
        </div>

        <div class="ward-terroir-digest__transit-body">
          <p class="ward-terroir-digest__transit-text">{{ transitGuide.detail }}</p>

          <div class="ward-terroir-digest__transit-pills">
            <span class="ward-terroir-digest__pill">
              <IconLine name="bike" aria-hidden="true" />
              <span>{{ transitGuide.vehicle }}</span>
            </span>
            <span class="ward-terroir-digest__pill">
              <IconLine name="droplet" aria-hidden="true" />
              <span>{{ transitGuide.tide }}</span>
            </span>
          </div>
        </div>
      </article>

      <!-- Cột 3: Hỗ trợ khẩn cấp & Hotline -->
      <article class="ward-terroir-digest__card ward-terroir-digest__card--rescue">
        <div class="ward-terroir-digest__card-head">
          <span class="ward-terroir-digest__card-icon" aria-hidden="true">
            <IconLine name="shield" />
          </span>
          <div class="ward-terroir-digest__head-text">
            <span class="ward-terroir-digest__kicker">Trực ban địa phương</span>
            <h3 class="ward-terroir-digest__card-title">Đường dây nóng 24/7</h3>
          </div>
        </div>

        <div class="ward-terroir-digest__contacts">
          <div class="ward-terroir-digest__contact-row">
            <div class="ward-terroir-digest__contact-meta">
              <span class="ward-terroir-digest__contact-label">Công an địa bàn</span>
              <span class="ward-terroir-digest__contact-sub">Trực ban an ninh trật tự</span>
            </div>
            <a
              :href="telHref(policePhone)"
              class="ward-terroir-digest__call-btn"
              data-contact-action="phone"
              data-contact-surface="ward-terroir-digest"
              :data-contact-entity-id="place.id"
              :aria-label="`Gọi công an ${placeName}: ${policePhone}`"
              @click="trackContactView(place.id, 'phone')"
            >
              <IconLine name="phone" aria-hidden="true" />
              <span>{{ policePhone }}</span>
            </a>
          </div>

          <div class="ward-terroir-digest__contact-row">
            <div class="ward-terroir-digest__contact-meta">
              <span class="ward-terroir-digest__contact-label">Cứu hộ Du lịch Vĩnh Long 360</span>
              <span class="ward-terroir-digest__contact-sub">Hỗ trợ thông tin &amp; Sự cố</span>
            </div>
            <a
              :href="telHref('02703822188')"
              class="ward-terroir-digest__call-btn"
              data-contact-action="phone"
              data-contact-surface="ward-terroir-digest"
              data-contact-entity-id="vl360-helpline"
              aria-label="Gọi Cứu hộ Du lịch Vĩnh Long 360: 0270 3822 188"
              @click="trackContactView('vl360-helpline', 'phone')"
            >
              <IconLine name="phone" aria-hidden="true" />
              <span>0270 3822 188</span>
            </a>
          </div>

          <div class="ward-terroir-digest__contact-row">
            <div class="ward-terroir-digest__contact-meta">
              <span class="ward-terroir-digest__contact-label">Cấp cứu Y tế &amp; Cứu nạn</span>
              <span class="ward-terroir-digest__contact-sub">Điều phối 115 / BV Đa khoa</span>
            </div>
            <a
              :href="telHref('115')"
              class="ward-terroir-digest__call-btn ward-terroir-digest__call-btn--urgent"
              data-contact-action="phone"
              data-contact-surface="ward-terroir-digest"
              data-contact-entity-id="medical-115"
              aria-label="Gọi Cấp cứu Y tế 115"
              @click="trackContactView('medical-115', 'phone')"
            >
              <IconLine name="phone" aria-hidden="true" />
              <span>115</span>
            </a>
          </div>
        </div>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, useId } from 'vue'
import { trackContactView } from '~/composables/useContactBeacon'
import { telHref } from '~/utils/safe'

interface PlaceInput {
  id: string
  name: string
  area?: string
  level?: string
  attributes?: Record<string, any>
}

const props = defineProps<{
  place: PlaceInput
}>()

const instanceId = useId().replace(/[^A-Za-z0-9_-]+/g, '-')
const headingId = `ward-terroir-heading-${instanceId}`

const placeName = computed(() => props.place?.name || 'Xã/Phường')
const areaKey = computed(() => props.place?.area || '')
const attrs = computed(() => (props.place?.attributes || {}) as Record<string, any>)

const policePhone = computed(() => {
  return attrs.value.police_phone || '0270 3822 224'
})

const accent = computed<'leaf' | 'clay' | 'amber' | 'river' | 'neutral'>(() => {
  const area = areaKey.value
  if (area === 'long-ho') return 'leaf'
  if (area === 'mang-thit' || area === 'vung-liem') return 'clay'
  if (area === 'binh-minh' || area === 'binh-tan') return 'amber'
  if (area === 'tra-on' || area === 'vinh-long') return 'river'
  return 'leaf'
})

interface TerroirSpec {
  title: string
  desc: string
  badge?: string
}

const terroirSpecs = computed<TerroirSpec[]>(() => {
  const name = props.place?.name || ''
  const area = areaKey.value

  if (name.includes('Lục Sĩ Thành') || name.includes('Phú Thành') || area === 'tra-on') {
    return [
      {
        title: 'Bánh tráng nem Cù lao Mây',
        desc: 'Bánh tráng ngọt bùi, bánh tráng nem và bánh tráng ớt cay nồng tráng thủ công nức tiếng cù lao ven sông Hậu.',
        badge: 'OCOP 4 sao',
      },
      {
        title: 'Cam sành Trà Ôn đất phù sa',
        desc: 'Cam sành trồng trên dải đất phù sa cổ ven sông Măng Thít, tép mọng nước đậm đà vị ngọt thanh.',
        badge: 'OCOP',
      },
      {
        title: 'Dưa lưới & Chuối xiêm hữu cơ',
        desc: 'Sản vật vườn cồn ngập nắng phù sa ngọt mát quanh năm.',
        badge: 'Đặc sản',
      },
    ]
  }

  if (name.includes('Mỹ Hòa') || area === 'binh-minh') {
    return [
      {
        title: 'Bưởi Năm Roi Hoàng Gia',
        desc: 'Tép vàng óng, ráo nước không hạt, chua ngọt thanh mát trứ danh vùng chuyên canh sông Hậu.',
        badge: 'Chỉ dẫn PGI',
      },
      {
        title: 'Tàu hũ ky làng nghề Mỹ Hòa',
        desc: 'Làng nghề hàng trăm năm lửa đỏ, làm từ hạt đậu nành nguyên chất thơm bùi giòn rụm.',
        badge: 'Di sản Quốc gia',
      },
      {
        title: 'Rau xà lách xoong Thuận An',
        desc: 'Rau ngập dòng nước ngọt mát tự nhiên, lá dày xanh mướt giòn ngọt đặc trưng.',
        badge: 'OCOP',
      },
    ]
  }

  if (
    name.includes('An Bình') ||
    name.includes('Bình Hòa Phước') ||
    name.includes('Đồng Phú') ||
    name.includes('Hòa Ninh') ||
    area === 'long-ho'
  ) {
    return [
      {
        title: 'Chôm chôm Bình Hòa Phước',
        desc: 'Chôm chôm nhãn giòn ráo tróc cơm, chôm chôm Java chín đỏ rực vườn cây miệt cù lao An Bình.',
        badge: 'OCOP 4 sao',
      },
      {
        title: 'Nhãn xuồng cơm vàng Cù lao',
        desc: 'Cơm dày khô ráo, vị ngọt thanh sâu, ngát hương hoa nhãn phù sa sông Cổ Chiên.',
        badge: 'Đặc sản',
      },
      {
        title: 'Sầu riêng Ri6 & Mật ong hoa nhãn',
        desc: 'Thương hiệu sầu riêng Vĩnh Long cùng mật ong hoa nhãn nguyên chất tại các vườn homestay.',
        badge: 'OCOP',
      },
    ]
  }

  if (area === 'mang-thit') {
    return [
      {
        title: 'Gốm đỏ Di sản Đương đại',
        desc: 'Đất sét đỏ trầm tích nung lò truyền thống rực lửa trăm năm dọc dải kênh Thầy Cai cổ kính.',
        badge: 'Di sản',
      },
      {
        title: 'Bưởi da xanh đất sét phù sa',
        desc: 'Trái da xanh ruột hồng mọng nước, vị ngọt thanh mát đạt tiêu chuẩn nông nghiệp sạch.',
        badge: 'OCOP',
      },
      {
        title: 'Nấm rơm & Nông sản hữu cơ',
        desc: 'Mô hình ủ rơm truyền thống miệt đồng đem lại sản vật sạch tinh khiết cho bếp ăn gia đình.',
        badge: 'OCOP',
      },
    ]
  }

  if (area === 'binh-tan') {
    return [
      {
        title: 'Khoai lang tím Nhật Bình Tân',
        desc: 'Củ khoai ruột tím thẫm đậm đà tinh bột, xuất khẩu toàn cầu và được bảo hộ chỉ dẫn địa lý.',
        badge: 'Chỉ dẫn PGI',
      },
      {
        title: 'Hành lá & Rau màu chuyên canh',
        desc: 'Vựa rau màu lớn nhất tỉnh cung ứng hành lá, ớt, đậu tươi mới mỗi sớm mai cho cả vùng.',
        badge: 'OCOP',
      },
      {
        title: 'Dưa hấu Ba Bầu ngọt giòn',
        desc: 'Dưa hấu vỏ mỏng ruột đỏ au mọng nước, giải nhiệt ngày hè miệt sông Hậu.',
        badge: 'Đặc sản',
      },
    ]
  }

  if (area === 'tam-binh') {
    return [
      {
        title: 'Cam sành Tam Bình ruột vàng',
        desc: 'Trái to vỏ sần mọng nước, tép cam vàng óng đậm đà nức tiếng khắp các tỉnh phía Nam.',
        badge: 'OCOP 4 sao',
      },
      {
        title: 'Lúa thảo dược tím Ba Loan',
        desc: 'Hạt gạo giàu vi lượng dinh dưỡng canh tác tự nhiên trên đồng đất phù sa trù phú.',
        badge: 'OCOP',
      },
      {
        title: 'Nấm mối thiên nhiên đầu mùa',
        desc: 'Sản vật trời ban chỉ rộ vào đầu mùa mưa tại các líp vườn cam cổ thụ đất cát mịn.',
        badge: 'Đặc sản quý',
      },
    ]
  }

  if (area === 'vung-liem') {
    return [
      {
        title: 'Xoài cát núm Trung Thành',
        desc: 'Thịt chắc mịn thơm lừng, vị ngọt đậm quyến rũ đạt chứng nhận OCOP tiêu biểu của huyện.',
        badge: 'OCOP',
      },
      {
        title: 'Bánh tráng dừa nướng Trung Ngãi',
        desc: 'Bánh tráng béo ngậy nước cốt dừa nướng trên bếp than hồng giòn rụm thơm lừng.',
        badge: 'Đặc sản',
      },
      {
        title: 'Chiếu lác Tân Duyệt Vũng Liêm',
        desc: 'Làng nghề dệt chiếu cói dẻo dai in hoa rực rỡ mang đậm phong vị thủ công Nam Bộ.',
        badge: 'Làng nghề',
      },
    ]
  }

  return [
    {
      title: 'Bánh tét 3 màu nghệ nhân',
      desc: 'Nếp dẻo thơm quyện lá cẩm tím, lá dứa xanh biếc và nhân đậu xanh thịt mỡ đậm đà.',
      badge: 'OCOP',
    },
    {
      title: 'Kẹo thèo lèo truyền thống',
      desc: 'Kẹo đậu phộng giòn tan bọc mè rang bùi béo, món quà quê ký ức phố thị Vĩnh Long.',
      badge: 'Đặc sản',
    },
    {
      title: 'Cá tai tượng chiên xù miệt vườn',
      desc: 'Vảy cá giòn rụm cuốn bánh tráng rau rừng chấm nước mắm me sông nước trứ danh.',
      badge: 'Ẩm thực',
    },
  ]
})

interface TransitGuide {
  kicker: string
  detail: string
  vehicle: string
  tide: string
}

const transitGuide = computed<TransitGuide>(() => {
  const name = props.place?.name || ''
  const area = areaKey.value

  const isIsland =
    name.includes('An Bình') ||
    name.includes('Bình Hòa Phước') ||
    name.includes('Đồng Phú') ||
    name.includes('Hòa Ninh') ||
    name.includes('Lục Sĩ Thành') ||
    name.includes('Phú Thành') ||
    name.includes('Quới Thiện') ||
    name.includes('Thanh Bình')

  if (isIsland) {
    return {
      kicker: 'Sông nước & Cù lao',
      detail:
        'Khu vực cù lao sông Cổ Chiên và sông Hậu: Cần qua phà An Bình (hoạt động 24/7), đò khách ven bến hoặc phà Đình Khao. Đường đan nông thôn 1.5–2.5m mát rượi rợp bóng cây; lý tưởng nhất cho xe máy và xe đạp dạo vườn trái cây.',
      vehicle: 'Xe máy · Xe đạp · Đò máy',
      tide: 'Phà 24/7 · Nước lớn rằm',
    }
  }

  if (area === 'mang-thit') {
    return {
      kicker: 'Dọc Kênh Thầy Cai',
      detail:
        'Tuyến ĐT 902 chạy dọc bờ kênh Thầy Cai ngắm nhìn hàng ngàn lò gạch gốm đỏ cổ kính. Đường nhựa thông thoáng thuận tiện cho ô tô 4–16 chỗ và xe máy. Có thể thuê tàu du lịch từ bến sông để chiêm ngưỡng vương quốc gốm từ mặt nước.',
      vehicle: 'Ô tô · Xe máy · Thuyền vỏ lãi',
      tide: 'ĐT 902 cao ráo quanh năm',
    }
  }

  if (area === 'binh-minh' || area === 'binh-tan') {
    return {
      kicker: 'Cửa ngõ Cầu Cần Thơ & QL1A',
      detail:
        'Kết nối nhanh qua Quốc lộ 1A, Quốc lộ 54 và cầu Cần Thơ. Tuyến giao thông huyết mạch phẳng phiu, xe du lịch từ 4 đến 45 chỗ lưu thông thuận lợi đến tận các vùng trồng chuyên canh bưởi Năm Roi, khoai tím và làng nghề.',
      vehicle: 'Ô tô 4–45 chỗ · Xe máy đường dài',
      tide: 'Lưu thông thông suốt ngày đêm',
    }
  }

  if (area === 'tam-binh' || area === 'tra-on') {
    return {
      kicker: 'Vành đai Sông Măng Thít',
      detail:
        'Trục ĐT 904 và ĐT 905 kết nối các vựa cam sành và miệt vườn trù phú. Đường nông thôn mới rộng rãi, ô tô dưới 16 chỗ tiếp cận dễ dàng. Vào dịp triều cường ngày rằm và mùng một âm lịch, du khách nên chú ý quan sát mé đường ven rạch.',
      vehicle: 'Ô tô dưới 16 chỗ · Xe máy',
      tide: 'Triều cường nhẹ mé rạch ngày rằm',
    }
  }

  return {
    kicker: 'Trung tâm Đô thị & Kết nối',
    detail:
      'Hạ tầng đô thị hoàn chỉnh, đường nhựa rộng thoáng kết nối thẳng tới các điểm di tích, bến tàu du lịch và chợ trung tâm. Dễ dàng gọi taxi hoặc thuê xe máy tự lái để bắt đầu chuyến du ngoạn miệt vườn ven sông.',
    vehicle: 'Taxi · Xe máy · Xe buýt nội tỉnh',
    tide: 'Đường phố thông thoáng quanh năm',
  }
})
</script>

<style scoped>
.ward-terroir-digest {
  margin-block: var(--space-6);
  padding: var(--space-6);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sheet);
  box-shadow: var(--shadow-sm);
  transition: border-color 0.2s ease;
}

.ward-terroir-digest:hover {
  border-color: var(--color-action-border);
}

.ward-terroir-digest__header {
  margin-block-end: var(--space-5);
}

.ward-terroir-digest__badge {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-1) var(--space-3);
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--color-action);
  background: var(--color-action-surface);
  border-radius: var(--radius-pill);
  margin-block-end: var(--space-2);
}

.ward-terroir-digest__title {
  font-size: 1.35rem;
  font-weight: 700;
  color: var(--color-text);
  line-height: 1.3;
  margin-block-end: var(--space-1);
}

.ward-terroir-digest__dek {
  font-size: 0.9375rem;
  color: var(--color-text-muted);
  line-height: 1.5;
  margin: 0;
}

.ward-terroir-digest__grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--space-4);
}

@media (min-width: 840px) {
  .ward-terroir-digest__grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

.ward-terroir-digest__card {
  display: flex;
  flex-direction: column;
  padding: var(--space-4);
  background: var(--color-canvas);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sheet);
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.ward-terroir-digest__card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-sm);
}

.ward-terroir-digest__card-head {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  margin-block-end: var(--space-3);
  padding-block-end: var(--space-2);
  border-bottom: 1px solid var(--color-border);
}

.ward-terroir-digest__card-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  inline-size: 2.25rem;
  block-size: 2.25rem;
  border-radius: var(--radius-control);
  background: var(--color-action-surface);
  color: var(--color-action);
  flex-shrink: 0;
  font-size: 1.125rem;
}

.ward-terroir-digest__head-text {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.ward-terroir-digest__kicker {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-text-muted);
}

.ward-terroir-digest__card-title {
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--color-text);
  line-height: 1.3;
  margin: 0;
}

/* OCOP Spec List */
.ward-terroir-digest__spec-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  flex-grow: 1;
}

.ward-terroir-digest__spec-item {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.ward-terroir-digest__spec-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.ward-terroir-digest__spec-name {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-text);
}

.ward-terroir-digest__tag {
  display: inline-flex;
  align-items: center;
  font-size: 0.6875rem;
  font-weight: 600;
  padding: 0.125rem var(--space-2);
  border-radius: var(--radius-pill);
  background: var(--color-action-surface);
  color: var(--color-action);
  white-space: nowrap;
}

.ward-terroir-digest__spec-desc {
  font-size: 0.8125rem;
  color: var(--color-text-muted);
  line-height: 1.45;
  margin: 0;
}

/* Transit */
.ward-terroir-digest__transit-body {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  flex-grow: 1;
  justify-content: space-between;
}

.ward-terroir-digest__transit-text {
  font-size: 0.875rem;
  color: var(--color-text);
  line-height: 1.5;
  margin: 0;
}

.ward-terroir-digest__transit-pills {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.ward-terroir-digest__pill {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  font-size: 0.78125rem;
  font-weight: 500;
  color: var(--color-text-muted);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-control);
}

/* Contacts */
.ward-terroir-digest__contacts {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  flex-grow: 1;
  justify-content: space-between;
}

.ward-terroir-digest__contact-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  padding-block: var(--space-1);
}

.ward-terroir-digest__contact-meta {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.ward-terroir-digest__contact-label {
  font-size: 0.84375rem;
  font-weight: 600;
  color: var(--color-text);
}

.ward-terroir-digest__contact-sub {
  font-size: 0.71875rem;
  color: var(--color-text-muted);
}

.ward-terroir-digest__call-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  font-size: 0.8125rem;
  font-weight: 600;
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-pill);
  background: var(--color-action-surface);
  color: var(--color-action);
  border: 1px solid var(--color-action-border);
  text-decoration: none;
  white-space: nowrap;
  transition: background-color 0.15s ease, color 0.15s ease;
}

.ward-terroir-digest__call-btn:hover {
  background: var(--color-action);
  color: var(--color-on-action);
}

.ward-terroir-digest__call-btn--urgent {
  background: var(--color-error);
  color: var(--color-on-action);
  border-color: var(--color-error);
}

.ward-terroir-digest__call-btn--urgent:hover {
  opacity: 0.9;
}
</style>
