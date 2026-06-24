<template>
  <div class="home">
    <!-- 1. Hero — dynamic tagline + search + quick-pick pills -->
    <section class="hero">
      <div class="hero-kenburns" aria-hidden="true"></div>
      <HeroIllustration />
      <div class="hero-scrim" aria-hidden="true"></div>
      <div class="hero-inner">
        <div class="hero-main hero-enter">
          <span class="hero-kicker"><span class="hero-kicker-dot" aria-hidden="true"></span>Vĩnh Long · Bến Tre · Trà Vinh</span>
          <h1>{{ seasonalTagline }}</h1>
          <p class="hero-sub">{{ ss('homepage.hero_subtitle', 'Trải nghiệm miệt vườn, đặc sản theo mùa, lễ hội truyền thống — tất cả trong một bản đồ.') }}</p>
          <SearchAutocomplete class="hero-search hero-ac" :placeholder="ss('homepage.search_placeholder', 'Tìm: chôm chôm, kẹo dừa, cù lao An Bình…')" />
          <div class="hero-pills">
            <NuxtLink v-for="pill in heroPills" :key="pill.to" :to="pill.to" class="hero-pill">{{ pill.emoji }} {{ pill.label }}</NuxtLink>
          </div>
        </div>
        <aside v-if="heroFeature" class="hero-feature" aria-label="Gợi ý nổi bật">
          <NuxtLink :to="`/dia-diem/${heroFeature.id}`" class="hf-card">
            <span class="hf-thumb" :class="`cat-${hfMeta?.cat}`" :style="{ backgroundImage: hfBg }" aria-hidden="true">
              <span class="hf-thumb-icon" v-html="hfIcon" />
            </span>
            <span class="hf-body">
              <span class="hf-tag">✦ Gợi ý nổi bật</span>
              <span class="hf-title">{{ heroFeature.name }}</span>
              <span v-if="hfRegion" class="hf-region">📍 {{ hfRegion }}</span>
              <span class="hf-cta">Khám phá →</span>
            </span>
          </NuxtLink>
        </aside>
      </div>
    </section>

    <!-- Region selector — first visit prompt -->
    <ClientOnly>
      <section v-if="!hasChosen && !regionSkipped" class="region-picker reveal">
        <p class="rp-question">Bạn muốn khám phá vùng nào?</p>
        <div class="rp-options">
          <button type="button" v-for="slug in Object.keys(AREA_META)" :key="slug" class="rp-btn" :class="`rp-${slug}`" @click="setRegion(slug as keyof typeof AREA_META)">
            <span class="rp-emoji">{{ AREA_META[slug].emoji }}</span>
            <span class="rp-name">{{ AREA_META[slug].name }}</span>
          </button>
          <button type="button" class="rp-btn rp-all" @click="setRegion('all')">
            <span class="rp-emoji">🌏</span>
            <span class="rp-name">Cả 3 vùng</span>
          </button>
        </div>
        <button type="button" class="rp-skip" @click="regionSkipped = true">Bỏ qua, xem tất cả</button>
      </section>
      <div v-else-if="isReturning && hasChosen && region && region !== 'all'" class="welcome-back reveal">
        <span class="wb-text">Chào mừng trở lại! Đang ưu tiên <strong>{{ AREA_META[region!]?.name || 'khu vực' }}</strong> cho bạn.</span>
        <button type="button" class="wb-change" @click="setRegion('all')">Xem tất cả</button>
      </div>
    </ClientOnly>

    <!-- Stats bar — trust signal -->
    <section v-if="stats" class="stats-bar reveal">
      <div class="stat-item" v-for="s in statsItems" :key="s.label">
        <span class="stat-num"><CountUp :value="s.value" /></span>
        <span class="stat-label">{{ s.label }}</span>
      </div>
    </section>

    <!-- Degraded/empty fallback — chỉ hiện khi client đã fetch xong mà lỗi/rỗng (không nhấp-nháy) -->
    <section v-if="homeFailed" class="block reveal">
      <EmptyState icon="🌾" :tone="homeError ? 'error' : 'empty'" title="Đang cập nhật nội dung" :message="homeError ? 'Mạng chậm một chút rồi. Bạn thử tải lại giúp tụi mình nhé!' : 'Tụi mình đang bổ sung điểm đến và đặc sản cho khu vực này. Quay lại sau nhé!'">
        <template #actions>
          <button v-if="homeError" type="button" class="btn btn-outline" @click="refreshHome()">Tải lại</button>
        </template>
      </EmptyState>
    </section>

    <!-- Skeleton khi đang nạp data (SSR-fail rồi client refetch, hoặc mạng chậm) -->
    <section v-if="homeLoadingSkeleton" class="block reveal" aria-hidden="true">
      <div class="section-head"><div class="sk-heading"></div></div>
      <SkeletonGrid :count="3" />
    </section>

    <!-- 2. "Đang diễn ra" — upcoming events + seasonal merged -->
    <section v-if="upcomingEvents.length || seasonal.length" class="block reveal">
      <div class="section-head">
        <div class="sh-text">
          <h2>Đang diễn ra</h2>
          <p class="sh-sub">Sự kiện &amp; lễ hội sắp tới khắp ba vùng</p>
        </div>
        <NuxtLink class="see-all" to="/su-kien">Xem lịch →</NuxtLink>
      </div>

      <!-- Sự kiện: cái gần nhất nổi-bật (hero), còn lại danh-sách gọn → bất-đối-xứng -->
      <div v-if="upcomingEvents.length" class="happening-feature">
        <NuxtLink :to="`/dia-diem/${upcomingEvents[0].id}`" class="event-hero">
          <div class="eh-date">
            <span class="eh-day">{{ formatEventDay(upcomingEvents[0]) }}</span>
            <span class="eh-month">{{ formatEventMonth(upcomingEvents[0]) }}</span>
          </div>
          <div class="eh-body">
            <span class="eh-cat">{{ upcomingEvents[0].attributes?.category === 'le-hoi' ? '🎭 Lễ hội' : '📅 Sự kiện' }}</span>
            <h3>{{ upcomingEvents[0].name }}</h3>
            <span v-if="upcomingEvents[0].attributes?.lunar_date" class="eh-lunar">🌙 {{ upcomingEvents[0].attributes.lunar_date }}</span>
            <span v-if="upcomingEvents[0].days_until != null" class="eh-countdown" :class="{ 'eh-today': upcomingEvents[0].days_until === 0 }">
              <span v-if="upcomingEvents[0].days_until === 0" class="ec-live-dot" aria-hidden="true"></span>
              {{ upcomingEvents[0].days_until === 0 ? 'Hôm nay!' : upcomingEvents[0].days_until === 1 ? 'Ngày mai' : `Còn ${upcomingEvents[0].days_until} ngày` }}
            </span>
          </div>
        </NuxtLink>
        <div v-if="upcomingEvents.length > 1" class="happening-rest">
          <NuxtLink v-for="ev in upcomingEvents.slice(1, 4)" :key="ev.id" :to="`/dia-diem/${ev.id}`" class="event-mini">
            <div class="ec-date ec-date-sm">
              <span class="ec-day">{{ formatEventDay(ev) }}</span>
              <span class="ec-month">{{ formatEventMonth(ev) }}</span>
            </div>
            <div class="ec-info">
              <h3>{{ ev.name }}</h3>
              <span v-if="ev.days_until != null" class="ec-countdown" :class="{ 'ec-today': ev.days_until === 0 }">
                {{ ev.days_until === 0 ? 'Hôm nay!' : ev.days_until === 1 ? 'Ngày mai' : `Còn ${ev.days_until} ngày` }}
              </span>
            </div>
          </NuxtLink>
        </div>
      </div>

      <!-- Seasonal products/experiences -->
      <div v-if="seasonal.length" class="happening-section">
        <p class="happening-label">🔥 Đang vào mùa tháng {{ currentMonth }}</p>
        <div class="scroll-row" role="region" aria-label="Đặc sản theo mùa">
          <EntityCard v-for="e in seasonal" :key="e.id" :entity="e" :season-filter="String(currentMonth)" />
        </div>
      </div>
    </section>

    <!-- 3. Lịch trình gợi ý (đẩy lên sớm — 25% user là Planner) -->
    <section v-if="itineraries.length" class="block reveal band">
      <div class="section-head">
        <div class="sh-text">
          <h2>Lịch trình gợi ý</h2>
          <p class="sh-sub">Hành trình 1–2 ngày, đi là có ngay</p>
        </div>
        <NuxtLink class="see-all" to="/lich-trinh">Xem tất cả →</NuxtLink>
      </div>
      <div class="scroll-row" role="region" aria-label="Lịch trình gợi ý">
        <ItineraryCard v-for="it in itineraries" :key="it.id" :itinerary="it" />
      </div>
      <div class="block-cta">
        <NuxtLink to="/tao-lich-trinh" no-prefetch class="btn btn-outline">📋 Tạo lịch trình riêng</NuxtLink>
      </div>
    </section>

    <!-- 4. 3 Vùng -->
    <section class="block reveal">
      <div class="section-head">
        <div class="sh-text">
          <h2>Khám phá 3 vùng</h2>
          <p class="sh-sub">Vĩnh Long • Bến Tre • Trà Vinh — mỗi nơi một sắc</p>
        </div>
        <NuxtLink class="see-all" to="/ban-do" no-prefetch>Xem bản đồ →</NuxtLink>
      </div>
      <div class="regions">
        <NuxtLink
          v-for="slug in areaKeys"
          :key="slug"
          :to="`/khu-vuc/${slug}`"
          class="region-tile"
          :class="[`region-${slug}`, { 'region-active': region === slug }]"
          :style="{ backgroundImage: `url(/img/cat/${REGION_IMG[slug] || 'place'}.jpg)` }"
        >
          <div class="region-tile-in">
            <span class="region-emoji">{{ AREA_META[slug].emoji }}</span>
            <h3>{{ AREA_META[slug].name }}</h3>
            <p>{{ AREA_META[slug].blurb }}</p>
            <div class="region-footer">
              <span class="region-count">{{ areaCounts[slug] || 0 }} điểm</span>
              <span class="region-cta">Khám phá →</span>
            </div>
          </div>
        </NuxtLink>
      </div>
    </section>

    <!-- 4.5 Khám phá theo sở thích — card lớn có ảnh -->
    <section class="block reveal">
      <div class="section-head">
        <div class="sh-text">
          <h2>Khám phá theo sở thích</h2>
          <p class="sh-sub">Chọn điều bạn mê, để miền Tây dẫn lối</p>
        </div>
      </div>
      <div class="interest-grid">
        <NuxtLink
          v-for="it in interestCards"
          :key="it.key"
          :to="`/kham-pha/${it.key}`"
          class="interest-card"
          :style="{ backgroundImage: `url(/img/cat/${it.img}.jpg)` }"
        >
          <div class="interest-in">
            <span class="interest-emoji">{{ it.emoji }}</span>
            <h3>{{ it.label }}</h3>
            <p>{{ it.description }}</p>
            <span class="interest-cta">Khám phá →</span>
          </div>
        </NuxtLink>
      </div>
    </section>

    <!-- 4.7 Spotlight — 1 điểm nổi bật cỡ lớn (magazine split, panel thiết-kế) -->
    <section v-if="spotlight" class="block reveal">
      <div class="spotlight">
        <NuxtLink
          :to="`/dia-diem/${spotlight.id}`"
          class="spot-visual"
          :class="`cat-${spotMeta?.cat}`"
          :style="{ backgroundImage: spotBg }"
          :aria-label="spotlight.name"
        >
          <span v-if="spotRegion" class="spot-region">📍 {{ spotRegion }}</span>
          <span class="spot-icon" v-html="spotIcon" />
        </NuxtLink>
        <div class="spot-body">
          <span class="spot-kicker">{{ spotMeta?.emoji }} {{ spotMeta?.label }} · Nổi bật</span>
          <h2>{{ spotlight.name }}</h2>
          <p v-if="spotlight.summary" class="spot-sum">{{ spotlight.summary }}</p>
          <NuxtLink :to="`/dia-diem/${spotlight.id}`" class="btn btn-primary spot-cta">Khám phá ngay →</NuxtLink>
        </div>
      </div>
    </section>

    <!-- 4.8 Interstitial cinematic — "act-break" nghệ-thuật, khí-quyển trôi + đại-tự -->
    <section class="block-cine reveal" aria-label="Vĩnh Long · Bến Tre · Trà Vinh">
      <div class="cine">
        <div class="cine-bg" aria-hidden="true"></div>
        <div class="cine-grain" aria-hidden="true"></div>
        <div class="cine-inner">
          <p class="cine-kicker">Vĩnh Long · Bến Tre · Trà Vinh</p>
          <h2 class="cine-title">Ba dòng sông,<br>một miền phù sa</h2>
          <p class="cine-sub">Miệt vườn trĩu quả, xứ dừa bạt ngàn, văn hoá Khmer ngàn năm — ba bản sắc hợp lưu thành một vùng đất.</p>
        </div>
      </div>
    </section>

    <!-- 5. Trải nghiệm nổi bật -->
    <section v-if="topExperiences.length" class="block reveal band">
      <div class="section-head">
        <div class="sh-text">
          <h2>Trải nghiệm nổi bật</h2>
          <p class="sh-sub">Miệt vườn, sông nước, làng nghề được yêu thích</p>
        </div>
        <NuxtLink class="see-all" to="/du-lich">Xem tất cả →</NuxtLink>
      </div>
      <div class="scroll-row" role="region" aria-label="Trải nghiệm nổi bật">
        <EntityCard v-for="e in topExperiences" :key="e.id" :entity="e" />
      </div>
    </section>

    <!-- 6. Đặc sản & Quà OCOP — always visible -->
    <section v-if="products.length" class="block reveal">
      <div class="section-head">
        <div class="sh-text">
          <h2>Đặc sản &amp; Quà OCOP</h2>
          <p class="sh-sub">Mang hương vị miền Tây về làm quà</p>
        </div>
        <NuxtLink class="see-all" to="/san-pham">Xem tất cả →</NuxtLink>
      </div>
      <div class="scroll-row" role="region" aria-label="Đặc sản và quà OCOP">
        <EntityCard v-for="e in products" :key="e.id" :entity="e" />
      </div>
    </section>

    <!-- 6.4 Interstitial #2 — lời mời tham-gia cộng-đồng (cinematic, ấm) -->
    <section class="block-cine reveal" aria-label="Tham gia cộng đồng vinhlong360">
      <div class="cine cine--invite">
        <div class="cine-bg" aria-hidden="true"></div>
        <div class="cine-grain" aria-hidden="true"></div>
        <div class="cine-inner">
          <p class="cine-kicker">Cộng đồng vinhlong360</p>
          <h2 class="cine-title">Kể câu chuyện<br>miền Tây của bạn</h2>
          <p class="cine-sub">Chia sẻ quán ngon, điểm đẹp, mẹo đi — góp một mảnh ghép cho bản đồ chung của ba vùng đất.</p>
          <NuxtLink to="/cong-dong" class="btn btn-primary cine-cta">Tham gia ngay →</NuxtLink>
        </div>
      </div>
    </section>

    <!-- 6.5 Từ cộng đồng — social proof, luôn tươi (client-only, không kẹt cache SWR) -->
    <ClientOnly>
      <section v-if="communityPosts.length" class="block reveal band">
        <div class="section-head">
          <div class="sh-text">
            <h2>Từ cộng đồng</h2>
            <p class="sh-sub">Trải nghiệm thật, mẹo hay từ người đi trước</p>
          </div>
          <NuxtLink class="see-all" to="/cong-dong">Xem tất cả →</NuxtLink>
        </div>
        <p v-if="communityStats" class="community-stats-line">
          <strong>{{ communityStats.posts }}</strong> bài viết
          · <strong>{{ communityStats.reviews }}</strong> đánh giá
          · <strong>{{ communityStats.members }}</strong> thành viên
        </p>
        <div v-if="topMembers.length" class="home-leaders">
          <span class="hl-label">🏆 Tích cực nhất:</span>
          <NuxtLink v-for="(m, i) in topMembers" :key="m.id" :to="`/nguoi-dung/${m.id}`" class="hl-chip">
            <span class="hl-rank" :class="`hl-rank-${i + 1}`">{{ i + 1 }}</span>
            <span class="hl-avatar">{{ (m.display_name || '?').charAt(0).toUpperCase() }}</span>
            <span class="hl-name">{{ m.display_name }}</span>
          </NuxtLink>
          <NuxtLink to="/bang-xep-hang" class="hl-more">Bảng xếp hạng →</NuxtLink>
        </div>
        <div class="scroll-row" role="region" aria-label="Bài viết cộng đồng mới">
          <NuxtLink v-for="p in communityPosts" :key="p.id" :to="`/bai-viet/${p.id}`" class="cm-card">
            <div v-if="p.images && p.images.length" class="cm-img">
              <img :src="p.images[0]" alt="" loading="lazy" decoding="async" width="280" height="150" />
            </div>
            <div class="cm-body">
              <div class="cm-author">
                <span class="cm-avatar">{{ (p.display_name || '?').charAt(0).toUpperCase() }}</span>
                <span class="cm-name">{{ p.display_name || 'Người dùng' }}</span>
                <span v-if="p.post_type_label" class="cm-type">{{ p.post_type_label }}</span>
              </div>
              <p class="cm-content">{{ p.content }}</p>
              <div class="cm-meta">
                <span v-if="p.likes">❤️ {{ p.likes }}</span>
                <span v-if="p.comments_count || p.comment_count">💬 {{ p.comments_count || p.comment_count }}</span>
                <span v-if="p.entity_name" class="cm-place">📍 {{ p.entity_name }}</span>
              </div>
            </div>
          </NuxtLink>
        </div>
        <div class="block-cta">
          <NuxtLink to="/cong-dong" class="btn btn-outline">💬 Tham gia cộng đồng</NuxtLink>
        </div>
      </section>
    </ClientOnly>

    <!-- 7. Cá nhân hóa — client-only (saved + AI recommendations) -->
    <ClientOnly>
      <section v-if="recentSaved.length" class="block">
        <div class="section-head">
          <h2>Đã lưu gần đây</h2>
          <NuxtLink class="see-all" to="/lich-trinh">Xem tất cả →</NuxtLink>
        </div>
        <div class="scroll-row" role="region" aria-label="Đã lưu gần đây">
          <NuxtLink v-for="fav in recentSaved" :key="fav.id" :to="`/dia-diem/${fav.id}`" class="card">
            <div v-if="fav.image" class="cover cover-img">
              <img :src="fav.image" :alt="fav.name" loading="lazy" decoding="async" width="480" height="192" />
            </div>
            <div class="card-b">
              <span class="card-type">{{ getFavTypeMeta(fav.type).label }}</span>
              <h3>{{ fav.name }}</h3>
              <p v-if="fav.place_name" class="place">{{ fav.place_name }}</p>
            </div>
          </NuxtLink>
        </div>
        <div class="block-cta">
          <NuxtLink to="/tao-lich-trinh" no-prefetch class="btn btn-outline">Tạo lịch trình từ danh sách đã lưu</NuxtLink>
        </div>
      </section>
      <NuxtErrorBoundary>
        <AIRecommendations title="Có thể bạn quan tâm" :limit="4" />
      </NuxtErrorBoundary>
    </ClientOnly>

    <!-- Region mini-switcher — sticky, visible after first choice (or skip) -->
    <ClientOnly>
      <div v-if="hasChosen || regionSkipped" class="region-mini-bar">
        <button type="button"
          v-for="slug in Object.keys(AREA_META)"
          :key="slug"
          class="rmb-btn"
          :class="{ active: region === slug }"
          @click="setRegion(slug as keyof typeof AREA_META)"
        >{{ AREA_META[slug].emoji }} {{ AREA_META[slug].name }}</button>
        <button type="button" class="rmb-btn" :class="{ active: region === 'all' }" @click="setRegion('all')">🌏 Tất cả</button>
      </div>
    </ClientOnly>

    <!-- 8. Quick links + Chatbot CTA -->
    <section class="block block-compact reveal">
      <div class="section-head">
        <div class="sh-text">
          <h2>Khám phá thêm</h2>
          <p class="sh-sub">Lối tắt tới mọi ngóc ngách ba vùng đất</p>
        </div>
      </div>
      <div class="quick-grid">
        <NuxtLink v-for="ql in quickLinks" :key="ql.to" :to="ql.to" class="quick-link"><span class="ql-icon">{{ ql.emoji }}</span><span class="ql-text">{{ ql.label }}</span></NuxtLink>
      </div>

      <!-- Chatbot CTA -->
      <div class="chatbot-cta">
        <div class="chatbot-cta-inner">
          <p class="chatbot-cta-text">{{ ss('homepage.chatbot_cta_title', 'Chưa biết đi đâu?') }}</p>
          <p class="chatbot-cta-sub">{{ ss('homepage.chatbot_cta_text', 'Trợ lý AI sẵn sàng gợi ý lịch trình, món ăn, điểm đến phù hợp với bạn.') }}</p>
        </div>
        <button type="button" class="chatbot-cta-btn" @click="openChat">💬 Hỏi ngay</button>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import type { Itinerary, Entity} from '~/types'
import { TYPE_META, AREA_META, INTEREST_META } from '~/composables/useConstants'
import { generateCategoryPlaceholder, generateCategoryIcon } from '~/composables/useCategoryPlaceholder'

useReveal()
const { get: ss } = useSiteSettings()

const DEFAULT_HERO_PILLS = [
  { emoji: '🗓️', label: 'Cuối tuần 2N1Đ', to: '/lich-trinh' },
  { emoji: '🍲', label: 'Ẩm thực', to: '/kham-pha/am-thuc' },
  { emoji: '🎁', label: 'Quà OCOP', to: '/ocop' },
  { emoji: '🌿', label: 'Miệt vườn', to: '/du-lich' },
  { emoji: '🎭', label: 'Lễ hội', to: '/le-hoi' },
  { emoji: '🗺️', label: 'Bản đồ', to: '/ban-do' },
]
const heroPills = computed(() => ss('homepage.hero_pills', DEFAULT_HERO_PILLS) as typeof DEFAULT_HERO_PILLS)

const DEFAULT_QUICK_LINKS = [
  { emoji: '🍲', label: 'Ẩm thực', to: '/kham-pha/am-thuc' },
  { emoji: '🌿', label: 'Thiên nhiên', to: '/kham-pha/thien-nhien' },
  { emoji: '🛕', label: 'Văn hóa', to: '/kham-pha/van-hoa' },
  { emoji: '🏺', label: 'Làng nghề', to: '/kham-pha/lang-nghe' },
  { emoji: '🛍️', label: 'Mua sắm', to: '/kham-pha/mua-sam' },
  { emoji: '🍊', label: 'Vòng trái cây VL', to: '/tuyen-duong?vung=vinh-long' },
  { emoji: '🥥', label: 'Vòng dừa BT', to: '/tuyen-duong?vung=ben-tre' },
  { emoji: '🛕', label: 'Chùa Khmer TV', to: '/tuyen-duong?vung=tra-vinh' },
]
const quickLinks = computed(() => ss('homepage.quick_links', DEFAULT_QUICK_LINKS) as typeof DEFAULT_QUICK_LINKS)

const { region, isReturning, hasChosen, setRegion, sortByRegion, orderedAreaKeys } = useRegionPref()
// First-visit escape hatch: dismiss the region picker without committing a
// region. `region` stays null so sortByRegion()/orderedAreaKeys() return all
// content unsorted; the mini-switcher remains for optional later refinement.
const regionSkipped = ref(false)
const { favorites } = useFavorites()
const recentSaved = computed(() => favorites.value.slice(0, 4))

// Post-login welcome signal — warm re-entry cue for returning users. Fires once
// on a guest→logged-in transition (additive; does not touch the region-recall
// welcome-back banner). Toast only, client-side.
const { isLoggedIn } = useAuth()
const { show: showToast } = useToast()
if (import.meta.client) {
  let greeted = false
  watch(isLoggedIn, (now, prev) => {
    if (now && !prev && !greeted) {
      greeted = true
      const n = favorites.value.length
      showToast(n ? `Chào mừng trở lại! Bạn có ${n} mục đã lưu.` : 'Chào mừng trở lại!', 'info')
    }
  })
}
function getFavTypeMeta(type: string) {
  return TYPE_META[type] || { emoji: '📍', label: type, cat: 'place' }
}

// SSR fetch qua ORIGIN CÔNG-KHAI (đường nginx→backend ổn định 200) — KHÔNG dùng
// internal $fetch (proxy nội-bộ Nitro 502 trong ngữ-cảnh render '/'). Có data trong
// HTML-SSR → tốt cho SEO (JSON-LD Event/ItemList + thẻ điểm-đến crawl được).
// Client fetch tương-đối. Nếu SSR vẫn lỗi → onMounted tự refetch (an toàn).
const ssrBase = import.meta.server ? 'https://vinhlong360.vn' : ''
const { data: homeData, error: homeError, pending: homePending, refresh: refreshHome } = await useAsyncData('homepage',
  () => $fetch<Record<string, unknown>>('/api/homepage', ssrBase ? { baseURL: ssrBase } : {}))

// Từ cộng đồng — fetch client-side (luôn tươi, không kẹt cache SWR của trang chủ)
const { data: communityData } = await useAsyncData('home-community', async () => {
  const [feed, cstats, lb] = await Promise.all([
    $fetch<any>('/api/feed?limit=10').catch(() => ({ posts: [] })),
    $fetch<any>('/api/community/stats').catch(() => null),
    $fetch<any>('/api/community/leaderboard?limit=3').catch(() => ({ leaders: [] })),
  ])
  const posts = (feed.posts || [])
    .filter((p: any) => ((p.content || '').trim().length > 0) || (p.images && p.images.length))
    .slice(0, 6)
  return { posts, stats: cstats, leaders: lb.leaders || [] }
}, { server: false, lazy: true })
const communityPosts = computed(() => communityData.value?.posts || [])
const communityStats = computed(() => communityData.value?.stats || null)
const topMembers = computed(() => communityData.value?.leaders || [])

const currentMonth = computed(() => homeData.value?.month || (new Date().getMonth() + 1))
// Tất cả content section ưu tiên theo vùng đã chọn (sortByRegion ổn định: vùng khác vẫn giữ).
const seasonal = computed(() => sortByRegion(homeData.value?.seasonal || []))
const experiences = computed(() => sortByRegion(homeData.value?.experiences || []))
const productsAll = computed(() => sortByRegion(homeData.value?.products || []))
// Spotlight — 1 điểm nổi bật cỡ lớn (magazine split): chọn entity có summary GIÀU
// nhất từ trải-nghiệm/đặc-sản → panel editorial "có chất", phá nhịp lưới card.
// Loại khỏi rail bên dưới để khỏi trùng. Deterministic (SSR-safe, không theo giờ).
const spotlight = computed<any>(() => {
  const pool = [...experiences.value.slice(0, 8), ...productsAll.value.slice(0, 8)]
  if (!pool.length) return null
  return pool.slice().sort((a: any, b: any) => (b?.summary || '').length - (a?.summary || '').length)[0] || null
})
const spotId = computed(() => spotlight.value?.id)
const spotMeta = computed(() => spotlight.value ? (TYPE_META[spotlight.value.type] || { emoji: '📍', label: spotlight.value.type, cat: 'place' }) : null)
const spotBg = computed(() => spotlight.value && spotMeta.value ? generateCategoryPlaceholder(spotlight.value.id, spotMeta.value.cat) : '')
const spotIcon = computed(() => spotMeta.value ? generateCategoryIcon(spotMeta.value.cat) : '')
const spotRegion = computed(() => {
  const a = spotlight.value?.area || spotlight.value?.attributes?.area || spotlight.value?.attributes?.province
  if (!a) return ''
  const meta = (AREA_META as Record<string, { name: string }>)[String(a)]
  return meta ? meta.name : String(a)
})
// Hero feature (cột phải hero bất-đối-xứng) — điểm trải-nghiệm nổi nhất, KHÁC spotlight;
// loại khỏi rail bên dưới để không trùng. Ẩn trên mobile (CSS) → hero mobile vẫn gọn.
const heroFeature = computed<any>(() => experiences.value.find((e: any) => e.id !== spotId.value) || spotlight.value || null)
const hfId = computed(() => heroFeature.value?.id)
const hfMeta = computed(() => heroFeature.value ? (TYPE_META[heroFeature.value.type] || { emoji: '📍', label: heroFeature.value.type, cat: 'place' }) : null)
const hfBg = computed(() => heroFeature.value && hfMeta.value ? generateCategoryPlaceholder(heroFeature.value.id, hfMeta.value.cat) : '')
const hfIcon = computed(() => hfMeta.value ? generateCategoryIcon(hfMeta.value.cat) : '')
const hfRegion = computed(() => {
  const a = heroFeature.value?.area || heroFeature.value?.attributes?.area || heroFeature.value?.attributes?.province
  if (!a) return ''
  const meta = (AREA_META as Record<string, { name: string }>)[String(a)]
  return meta ? meta.name : String(a)
})
const topExperiences = computed(() => experiences.value.filter((e: any) => e.id !== spotId.value && e.id !== hfId.value).slice(0, 6))
const products = computed(() => productsAll.value.filter((e: any) => e.id !== spotId.value).slice(0, 6))
const itineraries = computed(() => sortByRegion(homeData.value?.itineraries || []))
const upcomingEvents = computed(() => sortByRegion(homeData.value?.upcoming_events || []))
const seasonalTagline = computed(() => homeData.value?.seasonal_tagline || 'Khám phá Vĩnh Long theo cách của người bản địa')
const hasHomeContent = computed(() => !!(upcomingEvents.value.length || seasonal.value.length || itineraries.value.length || topExperiences.value.length || products.value.length || spotlight.value))

// Chỉ coi là "lỗi/rỗng" sau khi đã fetch xong (tránh nhấp-nháy fallback lúc đang tải).
const homeFailed = computed(() => !homePending.value && (!!homeError.value || (!!homeData.value && !hasHomeContent.value)))
// #3 skeleton: đang nạp mà chưa có nội dung (SSR-fail rồi client đang refetch, hoặc mạng chậm).
const homeLoadingSkeleton = computed(() => !hasHomeContent.value && !homeFailed.value)
// An toàn: nếu SSR fetch lỗi (hiếm), client tự refetch 1 lần — khách không thấy fallback kẹt.
onMounted(() => { if (homeError.value || !hasHomeContent.value) refreshHome() })

const areaKeys = computed(() => orderedAreaKeys(Object.keys(AREA_META)))
const REGION_IMG: Record<string, string> = { 'vinh-long': 'attraction', 'ben-tre': 'nature', 'tra-vinh': 'history' }

// Khám phá theo sở thích — card lớn từ INTEREST_META + ảnh category
const INTEREST_IMG: Record<string, string> = { 'am-thuc': 'dish', 'thien-nhien': 'nature', 'van-hoa': 'history', 'lang-nghe': 'craft', 'mua-sam': 'product' }
const interestCards = Object.entries(INTEREST_META).map(([key, m]: [string, any]) => ({
  key, emoji: m.emoji, label: m.label, description: m.description, img: INTEREST_IMG[key] || 'place',
}))

const areaCounts = computed(() => homeData.value?.area_counts || {})
const stats = computed(() => homeData.value?.stats || null)
const statsItems = computed(() => {
  const s = stats.value
  if (!s) return []
  const items = []
  if (s.entities) items.push({ value: s.entities + '+', label: 'Điểm đến & Đặc sản' })
  if (s.places) items.push({ value: s.places, label: 'Xã phường' })
  if (s.itineraries) items.push({ value: s.itineraries, label: 'Lịch trình' })
  const totalAreas = Object.values(areaCounts.value).reduce((a: number, b: unknown) => a + (Number(b) || 0), 0)
  if (totalAreas) items.push({ value: '3', label: 'Vùng đất' })
  return items
})

function formatEventDay(ev: any) {
  const ds = ev.attributes?.date_start
  if (!ds) return '?'
  return ds.split('-')[2]?.replace(/^0/, '') || '?'
}
function formatEventMonth(ev: any) {
  const ds = ev.attributes?.date_start
  if (!ds) return ''
  const m = parseInt(ds.split('-')[1], 10)
  return `Th${m}`
}

function openChat() {
  if (import.meta.client) {
    const fab = document.querySelector('.chat-fab') as HTMLElement
    if (fab) fab.click()
  }
}

useSeoMeta({
  title: ss('seo.default_title', 'vinhlong360 — Du lịch & Sản phẩm địa phương'),
  description: ss('seo.default_description', 'Cổng du lịch và sản phẩm địa phương Vĩnh Long: trải nghiệm miệt vườn, đặc sản theo mùa, OCOP, làng nghề và lịch trình gợi ý.'),
  ogTitle: ss('seo.default_title', 'vinhlong360 — Du lịch & Sản phẩm địa phương'),
  ogDescription: ss('branding.tagline', 'Khám phá Vĩnh Long theo cách của người bản địa.'),
  ogImage: ss('branding.og_image', 'https://vinhlong360.vn/img/og-default.jpg'),
})
const itemListSchema = computed(() => {
  const items = topExperiences.value.map((e: any, i: number) => ({
    '@type': 'ListItem',
    position: i + 1,
    url: `https://vinhlong360.vn/dia-diem/${e.id}`,
    name: e.name,
  }))
  return items.length ? JSON.stringify({
    '@context': 'https://schema.org',
    '@type': 'ItemList',
    name: 'Trải nghiệm nổi bật tại Vĩnh Long',
    numberOfItems: items.length,
    itemListElement: items,
  }) : ''
})

const eventListSchema = computed(() => {
  const events = upcomingEvents.value.map((ev: { features?: { properties: Record<string, unknown> }[] }) => ({
    '@type': 'Event',
    name: ev.name,
    startDate: ev.attributes?.date_start,
    endDate: ev.attributes?.date_end || ev.attributes?.date_start,
    url: `https://vinhlong360.vn/dia-diem/${ev.id}`,
    eventStatus: 'https://schema.org/EventScheduled',
    eventAttendanceMode: 'https://schema.org/OfflineEventAttendanceMode',
    location: { '@type': 'Place', name: ev.place_name || 'Vĩnh Long', address: { '@type': 'PostalAddress', addressRegion: ev.place_area || 'Vĩnh Long', addressCountry: 'VN' } },
  }))
  return events.length ? JSON.stringify(events) : ''
})

useHead({
  link: [
    { rel: 'canonical', href: canonicalUrl('/') },
    { rel: 'preload', as: 'image', href: '/img/hero-mobile.webp', fetchpriority: 'high', media: '(max-width: 640px)', imagesrcset: '/img/hero-mobile.webp', imagesizes: '100vw' },
    { rel: 'preload', as: 'image', href: '/img/hero.webp', fetchpriority: 'high', media: '(min-width: 641px)', imagesrcset: '/img/hero.webp', imagesizes: '100vw' },
  ],
  script: [
    {
      type: 'application/ld+json',
      innerHTML: JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'WebSite',
        name: 'vinhlong360',
        url: 'https://vinhlong360.vn',
        description: 'Cổng du lịch và sản phẩm địa phương Vĩnh Long, Bến Tre, Trà Vinh.',
        inLanguage: 'vi-VN',
        potentialAction: {
          '@type': 'SearchAction',
          target: 'https://vinhlong360.vn/tim-kiem?q={search_term_string}',
          'query-input': 'required name=search_term_string',
        },
      }),
    },
    {
      type: 'application/ld+json',
      innerHTML: JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'Organization',
        name: 'vinhlong360',
        url: 'https://vinhlong360.vn',
        logo: 'https://vinhlong360.vn/icons/icon-512.png',
        description: 'Cổng du lịch và sản phẩm địa phương Vĩnh Long, Bến Tre, Trà Vinh.',
        inLanguage: 'vi-VN',
        areaServed: [
          { '@type': 'AdministrativeArea', name: 'Vĩnh Long' },
          { '@type': 'AdministrativeArea', name: 'Bến Tre' },
          { '@type': 'AdministrativeArea', name: 'Trà Vinh' },
        ],
        sameAs: [],
      }),
    },
    ...(itemListSchema.value ? [{ type: 'application/ld+json', innerHTML: itemListSchema.value }] : []),
    ...(eventListSchema.value ? [{ type: 'application/ld+json', innerHTML: eventListSchema.value }] : []),
  ],
})
</script>

<style>
/* ── Homepage-specific overrides (scoped by .home) ── */

/* ════════════════════════════════════════════════════════════════
   SIGNATURE: Flagship hero — layered depth, display type, cinematic
   entrance. All additive on top of base.css `.hero`; degrades cleanly.
   ════════════════════════════════════════════════════════════════ */

/* 1 — Layered depth scrim. Sits above the bg image, below content.
   A warm radial glow (top-right, echoing the SVG sun) + a soft bottom
   vignette give the flat photo real dimension and keep text legible. */
.home .hero { isolation: isolate; }
.home .hero-scrim {
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  background:
    radial-gradient(120% 95% at 88% 6%, rgba(232,163,61,.30) 0%, rgba(232,163,61,.07) 34%, transparent 60%),
    radial-gradient(90% 70% at 6% 100%, rgba(var(--primary-rgb),.32) 0%, transparent 58%),
    linear-gradient(to top, rgba(var(--ink-rgb),.55) 0%, rgba(var(--ink-rgb),.06) 32%, transparent 55%);
}
.home .hero-inner { z-index: 1; }

/* Hero BẤT-ĐỐI-XỨNG: ≥920px chia 2 cột (chữ trái + thẻ featured phải) — magazine,
   đưa nội-dung lên màn đầu. Mobile: thẻ ẩn (giữ hero gọn). */
@media (min-width: 920px) {
  .home .hero-inner { display: grid; grid-template-columns: minmax(0, 1.32fr) minmax(280px, 0.8fr); gap: var(--space-10); align-items: center; }
}
@media (max-width: 919px) { .hero-feature { display: none; } }
.hf-card {
  display: flex; gap: var(--space-4); align-items: center;
  padding: var(--space-4);
  background: rgba(255,255,255,.12);
  backdrop-filter: saturate(180%) blur(14px); -webkit-backdrop-filter: saturate(180%) blur(14px);
  border: .5px solid rgba(255,255,255,.28);
  border-radius: var(--radius-lg);
  color: var(--text-on-dark, #fff); text-decoration: none;
  box-shadow: var(--shadow-md);
  transition: transform .4s var(--ease-spring-gentle), box-shadow .4s var(--ease-out-expo), background .3s var(--ease-out);
}
.hf-card:hover { transform: translateY(-4px); background: rgba(255,255,255,.18); box-shadow: var(--shadow-xl); }
.hf-card:active { transform: scale(.99); transition-duration: .1s; }
.hf-card:focus-visible { outline: 2px solid var(--text-on-dark, #fff); outline-offset: 3px; }
.hf-thumb {
  flex: 0 0 86px; height: 86px; border-radius: var(--radius-md);
  background-size: cover; background-position: center;
  position: relative; overflow: hidden;
  display: flex; align-items: center; justify-content: center;
}
.hf-thumb-icon { width: 46px; height: 46px; opacity: .85; filter: drop-shadow(0 2px 6px rgba(0,0,0,.22)); }
.hf-thumb-icon :deep(svg), .hf-thumb-icon svg { width: 100%; height: 100%; display: block; }
.hf-body { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
.hf-tag { font-size: var(--text-xs); font-weight: var(--weight-bold); text-transform: uppercase; letter-spacing: .04em; color: var(--accent); }
.hf-title { font-size: var(--text-lg); font-weight: var(--weight-bold); line-height: var(--leading-snug); display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.hf-region { font-size: var(--text-xs); opacity: .88; }
.hf-cta { font-size: var(--text-sm); font-weight: var(--weight-semibold); margin-top: var(--space-1); }
/* Entrance: thẻ featured xuất-hiện sau chữ (cinematic) — JS-gated, reduced-motion tắt. */
html.js .home .hero-feature { opacity: 0; transform: translateY(16px); animation: hero-rise .7s var(--ease-out-expo) .5s forwards; }

/* 1b — Ken-Burns: ảnh hero "sống" bằng zoom + pan rất chậm (transform thuần,
   composited; reduced-motion tắt). Layer riêng nằm DƯỚI illustration + scrim
   nên không ảnh hưởng legibility chữ. Ảnh chuyển từ .hero sang đây để pan được. */
.home .hero { background-image: none; }
.home .hero-kenburns {
  position: absolute;
  inset: 0;
  z-index: 0;
  background-image:
    linear-gradient(105deg, rgba(var(--ink-rgb),.86) 0%, rgba(var(--ink-rgb),.52) 46%, rgba(var(--ink-rgb),.12) 100%),
    url('/img/hero.webp');
  background-size: cover;
  background-position: center;
  transform: scale(1.06);
  animation: hero-kenburns 34s ease-in-out infinite alternate;
}
@media (max-width: 640px) {
  .home .hero-kenburns {
    background-image:
      linear-gradient(105deg, rgba(var(--ink-rgb),.86) 0%, rgba(var(--ink-rgb),.52) 46%, rgba(var(--ink-rgb),.12) 100%),
      url('/img/hero-mobile.webp');
  }
}
@keyframes hero-kenburns {
  0%   { transform: scale(1.06) translate3d(0, 0, 0); }
  100% { transform: scale(1.16) translate3d(-2.2%, -1.6%, 0); }
}

/* 2 — Kicker (eyebrow) above the headline: quiet authority + place IA */
.home .hero-kicker {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-1) var(--space-3) var(--space-1) var(--space-2);
  margin-bottom: var(--space-4);
  background: rgba(255,255,255,.12);
  backdrop-filter: saturate(180%) blur(8px);
  -webkit-backdrop-filter: saturate(180%) blur(8px);
  border: .5px solid rgba(255,255,255,.28);
  border-radius: var(--radius-full);
  color: var(--text-on-dark, #fff);
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  letter-spacing: .04em;
  text-transform: uppercase;
  text-shadow: 0 1px 2px rgba(0,0,0,.25);
}
.home .hero-kicker-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--accent);
  box-shadow: 0 0 0 0 rgba(var(--accent-rgb), .55);
  animation: hero-dot-pulse 2.4s var(--ease-out) infinite;
}
@keyframes hero-dot-pulse {
  0% { box-shadow: 0 0 0 0 rgba(var(--accent-rgb), .55); }
  70% { box-shadow: 0 0 0 7px rgba(var(--accent-rgb), 0); }
  100% { box-shadow: 0 0 0 0 rgba(var(--accent-rgb), 0); }
}

/* 3 — Display headline. Bigger, tighter, with a warm gradient accent
   rule beneath it (a "signature stroke" the owner will feel at a glance). */
.home .hero h1 {
  font-size: clamp(2.15rem, 6.2vw, 3.6rem);
  letter-spacing: -1.4px;
  line-height: 1.05;
  /* LCP element: smaller blur radius = cheaper paint, same legibility over the
     hero photo (tighter shadow + slightly higher opacity preserves contrast). */
  text-shadow: 0 1px 6px rgba(0,0,0,.34);
  position: relative;
  display: inline-block;
}
.home .hero h1::after {
  content: "";
  display: block;
  width: clamp(56px, 14vw, 112px);
  height: 4px;
  margin-top: var(--space-4);
  border-radius: var(--radius-full);
  background: linear-gradient(90deg, var(--accent) 0%, var(--primary-light) 100%);
  box-shadow: 0 2px 10px rgba(var(--accent-rgb), .45);
  transform-origin: left center;
}
.home .hero-sub { font-size: var(--text-lg); opacity: .95; max-width: 640px; margin: var(--space-4) 0 0; text-shadow: 0 1px 8px rgba(0,0,0,.22); }
.dark .home .hero-sub { opacity: 1; font-weight: 400; }

/* 4 — Cinematic staggered entrance. JS-gated (html.js) so SSR/no-JS
   renders fully visible. Calm spring rise, one beat per element. */
html.js .home .hero-enter > * {
  opacity: 0;
  transform: translateY(16px);
  animation: hero-rise .7s var(--ease-out-expo) forwards;
}
html.js .home .hero-enter > .hero-kicker { animation-delay: .05s; }
html.js .home .hero-enter > h1 { animation-delay: .14s; }
html.js .home .hero-enter > .hero-sub { animation-delay: .24s; }
html.js .home .hero-enter > .hero-search { animation-delay: .34s; }
html.js .home .hero-enter > .hero-pills { animation-delay: .44s; }
@keyframes hero-rise {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}
/* underline draw — separate so it can run slightly behind the h1 */
html.js .home .hero-enter h1::after {
  animation: hero-underline-draw .8s var(--ease-out-expo) .5s both;
}
@keyframes hero-underline-draw {
  from { transform: scaleX(0); opacity: 0; }
  to { transform: scaleX(1); opacity: 1; }
}

/* 5 — Premium search capsule. Floats the field in a soft glass shell
   with real elevation; focus blooms a warm ring. Layers on base.css. */
.home .hero-search {
  padding: var(--space-1);
  background: rgba(255,255,255,.10);
  backdrop-filter: saturate(180%) blur(10px);
  -webkit-backdrop-filter: saturate(180%) blur(10px);
  border: .5px solid rgba(255,255,255,.22);
  border-radius: calc(var(--radius-md) + var(--space-1));
  box-shadow: 0 8px 30px rgba(0,0,0,.18), 0 2px 8px rgba(0,0,0,.12);
  transition: box-shadow .35s var(--ease-out-expo), border-color .3s var(--ease-out), transform .35s var(--ease-spring-gentle);
}
.home .hero-search:focus-within {
  border-color: rgba(var(--accent-rgb), .6);
  box-shadow: 0 12px 40px rgba(0,0,0,.22), 0 0 0 4px rgba(var(--accent-rgb), .22);
  transform: translateY(-1px);
}
.home .hero-search input { border-color: transparent; background: var(--card); }
.home .hero-search input:focus { border-color: transparent; box-shadow: none; }

/* Hero autocomplete — tái dùng glass capsule (.hero-search) cho SearchAutocomplete.
   Không còn icon dẫn-đầu/nút Tìm: input lấp đầy, chừa chỗ phải cho nút xoá (X). */
.home .hero .hero-ac { align-items: center; }
.home .hero .hero-ac input {
  flex: 1; width: 100%;
  padding: var(--space-4) 42px var(--space-4) var(--space-5);
  border-color: transparent; background: var(--card);
}
.home .hero .hero-ac .ac-dropdown { text-align: left; }

/* ════════════════════════════════════════════════════════════════
   SIGNATURE: Section rhythm — each heading gets a warm accent tick +
   refined kicker weight, so the page reads as a designed flagship.
   ════════════════════════════════════════════════════════════════ */

/* Section headings — Apple HIG: xl semibold (not 2xl extrabold) */
.home .section-head h2 {
  font-size: var(--text-xl);
  font-weight: var(--weight-bold);
  letter-spacing: -.015em;
  line-height: var(--leading-snug);
  position: relative;
  padding-left: var(--space-4);
}
/* Vertical accent tick — a small warm gradient bar anchoring each section */
.home .section-head h2::before {
  content: "";
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 4px;
  height: 1.05em;
  border-radius: var(--radius-full);
  background: linear-gradient(180deg, var(--accent) 0%, var(--primary) 100%);
}
/* Phụ-đề editorial dưới heading (warmth + ngữ-cảnh, phá thế "heading trơ + list") */
.home .section-head .sh-text { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
.home .sh-sub { padding-left: var(--space-4); margin: 0; font-size: var(--text-sm); font-weight: var(--weight-normal); color: var(--muted); line-height: var(--leading-snug); max-width: 62ch; }

/* Bento "3 vùng": vùng đầu (ưu-tiên theo region) lớn bên trái, 2 vùng còn lại xếp phải */
@media (min-width: 721px) {
  .home .regions { grid-template-columns: 1.6fr 1fr; grid-template-rows: 1fr 1fr; }
  .home .region-tile:first-child { grid-row: 1 / span 2; }
  .home .region-tile:first-child .region-tile-in h3 { font-size: var(--text-2xl); }
  .home .region-tile:first-child .region-emoji { font-size: var(--text-3xl); }
  .home .region-tile:first-child .region-tile-in p { font-size: var(--text-base); }
}

/* Subtle hairline divider above each block — calm section separation */
.home .block + .block {
  position: relative;
}
.home .block + .block::before {
  content: "";
  position: absolute;
  top: 0;
  left: 50%;
  transform: translateX(-50%);
  width: min(100%, var(--maxw));
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--line) 22%, var(--line) 78%, transparent);
  opacity: .7;
}

/* Breathing room between sections */
.home .block { padding-top: var(--space-16); padding-bottom: var(--space-8); }
/* content-visibility: bỏ qua render layout/paint các section NGOÀI màn hình (trang chủ
   rất dài ~10000px) → giảm chi-phí paint ban-đầu. 'auto' nhớ kích-thước thật sau lần
   render đầu (tránh nhảy scroll); 480px là ước-lượng ban đầu. Section trong tầm vẫn render
   bình thường nên không hại LCP/above-the-fold. */
.home .block { content-visibility: auto; contain-intrinsic-size: auto 480px; }
.home .block-compact { padding-top: var(--space-8); padding-bottom: var(--space-8); }

/* ── Stats bar ── */
.stats-bar {
  display: flex;
  justify-content: center;
  gap: var(--space-8);
  padding: var(--space-5) var(--space-4);
  margin: calc(-1 * var(--space-4)) auto var(--space-4);
  max-width: var(--maxw);
  background: var(--bg-alt);
  border-radius: var(--radius-md);
}
.stats-bar .stat-item {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  transition: background .3s var(--ease-out), transform .35s var(--ease-spring-gentle);
  cursor: default;
}
.stats-bar .stat-item:hover {
  background: var(--overlay-subtle);
  transform: translateY(-1px);
}
/* Đường phân-cách mảnh giữa các chỉ-số → cảm-giác "stat strip" gọn (desktop). */
.stats-bar .stat-item + .stat-item::before {
  content: ""; position: absolute; left: calc(-1 * var(--space-4)); top: 50%;
  transform: translateY(-50%); width: 1px; height: 26px; background: var(--line);
}
@media (max-width: 480px) { .stats-bar .stat-item + .stat-item::before { display: none; } }
.stats-bar .stat-num {
  font-size: var(--text-xl);
  font-weight: var(--weight-extrabold);
  color: var(--primary-fg);
  letter-spacing: var(--tracking-tight);
}
.stats-bar .stat-label {
  font-size: var(--text-xs);
  color: var(--muted);
  font-weight: var(--weight-medium);
  text-transform: uppercase;
  letter-spacing: .03em;
}
@media (max-width: 480px) {
  .stats-bar { gap: var(--space-5); }
  .stats-bar .stat-num { font-size: var(--text-lg); }
  .stats-bar .stat-label { font-size: .65rem; }
}

/* ── Hero quick-pick pills ── */
.hero-pills {
  display: flex;
  gap: var(--space-2);
  margin-top: var(--space-5);
  flex-wrap: wrap;
}
.hero-pill {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-5);
  background: var(--overlay-light);
  backdrop-filter: saturate(180%) blur(12px);
  -webkit-backdrop-filter: saturate(180%) blur(12px);
  border: .5px solid rgba(255,255,255,.3);
  border-radius: var(--radius-full);
  color: var(--text-on-dark, #fff);
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  transition: background .3s var(--ease-out), transform .35s var(--ease-spring-gentle), box-shadow .3s var(--ease-out);
  min-height: 44px;
}
.hero-pill:hover {
  background: rgba(255,255,255,.3);
  transform: translateY(-2px);
}
.hero-pill:active {
  transform: scale(.95);
  transition-duration: .1s;
}
.hero-pill:focus-visible {
  outline: 2px solid var(--text-on-dark, #fff);
  outline-offset: 2px;
}
/* Mobile: nén pill (padding ngang nhỏ hơn) để 6 pill bớt tràn 3 hàng — giữ
   min-height 44px cho touch + font-size không đổi (đọc tốt). */
@media (max-width: 480px) {
  .hero-pills { gap: var(--space-2); margin-top: var(--space-4); }
  .hero-pill { padding-left: var(--space-3); padding-right: var(--space-3); }
}

/* ── Horizontal scroll row (mobile → scroll, tablet → 2col, desktop → grid) ── */
.scroll-row {
  display: grid;
  gap: var(--space-5);
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
}
@media (min-width: 769px) and (max-width: 1024px) {
  .scroll-row {
    grid-template-columns: repeat(2, 1fr);
  }
}
@media (max-width: 768px) {
  .scroll-row {
    display: flex;
    gap: var(--space-3);
    overflow-x: auto;
    scroll-snap-type: x mandatory;
    overscroll-behavior-x: contain;
    -webkit-overflow-scrolling: touch;
    padding-bottom: var(--space-2);
    padding-inline: var(--space-4);
    margin-inline: calc(-1 * var(--space-4));
    scrollbar-width: none;
    mask-image: linear-gradient(to right, transparent, #000 var(--space-4), #000 88%, transparent);
    -webkit-mask-image: linear-gradient(to right, transparent, #000 var(--space-4), #000 88%, transparent);
  }
  .scroll-row::-webkit-scrollbar { display: none; }
  .scroll-row:hover, .scroll-row:focus-within { mask-image: linear-gradient(to right, transparent, #000 var(--space-4), #000 100%); -webkit-mask-image: linear-gradient(to right, transparent, #000 var(--space-4), #000 100%); }
  .scroll-row > * {
    flex: 0 0 280px;
    scroll-snap-align: start;
  }
}

/* ── "Đang diễn ra" section ── */
.happening-scroll {
  display: flex;
  gap: var(--space-3);
  overflow-x: auto;
  scroll-snap-type: x mandatory;
  -webkit-overflow-scrolling: touch;
  overscroll-behavior-x: contain;
  padding-bottom: var(--space-2);
  scrollbar-width: none;
  mask-image: linear-gradient(to right, #000 0%, #000 calc(100% - 40px), transparent 100%);
  -webkit-mask-image: linear-gradient(to right, #000 0%, #000 calc(100% - 40px), transparent 100%);
}
.happening-scroll::-webkit-scrollbar { display: none; }
.happening-scroll:hover, .happening-scroll:focus-within { mask-image: none; -webkit-mask-image: none; }

.event-card {
  flex: 0 0 300px;
  scroll-snap-align: start;
  display: flex;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  background: var(--card);
  border: .5px solid var(--line);
  border-radius: var(--radius);
  box-shadow: var(--shadow-xs);
  transition: transform .35s var(--ease-spring-gentle), box-shadow .35s var(--ease-out-expo), border-color .3s var(--ease-out);
}
.event-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-md);
  border-color: var(--border);
}
.event-card:active {
  transform: scale(.97);
  transition-duration: .1s;
}
.event-card:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 3px;
}
.ec-date {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-width: 52px;
  padding: var(--space-2);
  background: var(--primary);
  border-radius: var(--radius-sm);
  color: var(--text-on-dark, #fff);
}
.ec-day { font-size: var(--text-xl); font-weight: var(--weight-extrabold); line-height: 1; font-variant-numeric: tabular-nums; }
.ec-month { font-size: var(--text-xs); font-weight: var(--weight-semibold); opacity: .9; }
.ec-info { display: flex; flex-direction: column; gap: var(--space-1); min-width: 0; }
.ec-cat { font-size: var(--text-xs); font-weight: var(--weight-bold); text-transform: uppercase; letter-spacing: .04em; color: var(--primary-fg); }
.ec-info h3 { margin: 0; font-size: var(--text-base); font-weight: var(--weight-semibold); letter-spacing: var(--tracking-tight); display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.ec-lunar { font-size: var(--text-xs); color: var(--muted); }
.ec-countdown {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  color: var(--amber-700); /* A11Y-01: qua token thay vì hex cứng */
  background: rgba(154, 109, 30, .08);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-full);
}
.ec-today {
  color: #b93a2a;
}
.ec-live-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--error);
  animation: pulse-dot 1.5s ease-in-out infinite;
}
@keyframes pulse-dot {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: .4; transform: scale(.7); }
}

/* ── "Đang diễn ra" — featured event (hero) + danh-sách gọn ── */
.happening-feature { display: grid; grid-template-columns: 1.5fr 1fr; gap: var(--space-4); align-items: stretch; }
@media (max-width: 760px) { .happening-feature { grid-template-columns: 1fr; } }
.event-hero {
  display: flex; align-items: center; gap: var(--space-5);
  padding: var(--space-6);
  border-radius: var(--radius-lg);
  background: linear-gradient(135deg, rgba(var(--primary-rgb), .96) 0%, rgba(var(--accent-rgb), .88) 100%);
  color: #fff; text-decoration: none;
  box-shadow: var(--shadow-md);
  transition: transform .35s var(--ease-spring-gentle), box-shadow .35s var(--ease-out-expo);
  position: relative;
  overflow: hidden;
  isolation: isolate;
}
/* "Đang diễn ra" — vệt sáng quét chậm: cảm-giác live/premium. Transform thuần,
   composited; reduced-motion tắt (xem khối @media cuối). */
.event-hero::before {
  content: "";
  position: absolute;
  top: 0; bottom: 0;
  left: -60%;
  width: 45%;
  z-index: -1;
  background: linear-gradient(105deg, transparent 0%, rgba(255,255,255,.16) 50%, transparent 100%);
  transform: translateX(0) skewX(-14deg);
  animation: event-sheen 6.5s ease-in-out 1.2s infinite;
}
@keyframes event-sheen {
  0%   { transform: translateX(0) skewX(-14deg); }
  55%  { transform: translateX(420%) skewX(-14deg); }
  100% { transform: translateX(420%) skewX(-14deg); }
}
.event-hero:hover { transform: translateY(-3px); box-shadow: var(--shadow-lg); }
.event-hero:active { transform: scale(.99); transition-duration: .1s; }
.event-hero:focus-visible { outline: 2px solid #fff; outline-offset: 3px; }
.eh-date { display: flex; flex-direction: column; align-items: center; justify-content: center; min-width: 88px; padding: var(--space-4); background: rgba(255,255,255,.2); border-radius: var(--radius-md); flex-shrink: 0; }
.eh-day { font-size: var(--text-4xl); font-weight: var(--weight-extrabold); line-height: 1; font-variant-numeric: tabular-nums; }
.eh-month { font-size: var(--text-sm); font-weight: var(--weight-semibold); opacity: .92; }
.eh-body { min-width: 0; display: flex; flex-direction: column; gap: var(--space-1); }
.eh-cat { font-size: var(--text-xs); font-weight: var(--weight-bold); text-transform: uppercase; letter-spacing: .04em; opacity: .9; }
.eh-body h3 { margin: var(--space-1) 0; font-size: var(--text-2xl); font-weight: var(--weight-bold); letter-spacing: -.01em; line-height: var(--leading-snug); display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.eh-lunar { font-size: var(--text-sm); opacity: .9; }
.eh-countdown { align-self: flex-start; display: inline-flex; align-items: center; gap: 5px; margin-top: var(--space-1); padding: var(--space-1) var(--space-3); background: rgba(255,255,255,.22); border-radius: var(--radius-full); font-size: var(--text-sm); font-weight: var(--weight-bold); }
.eh-today { background: rgba(255,255,255,.32); }
.happening-rest { display: flex; flex-direction: column; gap: var(--space-2); justify-content: center; }
.event-mini { display: flex; align-items: center; gap: var(--space-3); padding: var(--space-2) var(--space-3); background: var(--card); border: .5px solid var(--line); border-radius: var(--radius); text-decoration: none; color: var(--ink); transition: border-color .25s var(--ease-out), transform .25s var(--ease-spring-gentle); }
.event-mini:hover { border-color: var(--primary-fg); transform: translateX(2px); }
.ec-date-sm { min-width: 46px; padding: var(--space-2); }
.event-mini .ec-info { gap: 2px; }
.event-mini h3 { margin: 0; font-size: var(--text-sm); font-weight: var(--weight-semibold); line-height: var(--leading-snug); display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
@media (prefers-reduced-motion: reduce) { .event-hero:hover, .event-mini:hover { transform: none; } }

/* ── #1 Nhịp section: panel nền-ấm bo-góc xen-kẽ → tách section, phá nền cream phẳng.
   Dùng panel (contained) thay full-bleed box-shadow vì content-visibility:auto sẽ cắt paint. ── */
.home .block.band { background: var(--bg-warm); border-radius: var(--radius-xl); padding-inline: var(--space-6); }
.home .block.band + .block::before,
.home .block + .block.band::before { display: none; }
.dark .home .block.band { background: var(--bg-alt); }

.happening-label {
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  color: var(--primary-fg);
  margin: var(--space-4) 0 var(--space-2);
}
.dark .happening-label { color: var(--primary-fg-strong); }
.happening-section { margin-top: var(--space-1); }

/* ── Skeleton heading (khi đang nạp data trang chủ) ── */
.sk-heading { height: 1.4rem; width: 180px; border-radius: var(--radius-sm); background: linear-gradient(90deg, var(--bg-alt) 25%, var(--line) 37%, var(--bg-alt) 63%); background-size: 400% 100%; animation: skShimmer 1.4s ease infinite; }
@keyframes skShimmer { 0% { background-position: 100% 0; } 100% { background-position: -100% 0; } }
@media (prefers-reduced-motion: reduce) { .sk-heading { animation: none; } }

/* ── Block CTA ── */
.block-cta { text-align: center; margin-top: var(--space-4); }

/* ── Từ cộng đồng ── */
.community-stats-line { font-size: var(--text-sm); color: var(--muted); margin: 0 0 var(--space-3); }
.community-stats-line strong { color: var(--primary-fg); font-weight: var(--weight-bold); }
.home-leaders { display: flex; align-items: center; flex-wrap: wrap; gap: var(--space-2); margin: 0 0 var(--space-4); }
.hl-label { font-size: var(--text-sm); font-weight: var(--weight-semibold); color: var(--ink); }
.hl-chip { display: inline-flex; align-items: center; gap: var(--space-1); padding: .2rem .6rem .2rem .2rem; background: var(--bg-alt); border: .5px solid var(--line); border-radius: var(--radius-full); text-decoration: none; color: var(--ink); transition: border-color .25s var(--ease-out); }
.hl-chip:hover { border-color: var(--primary-fg); }
.hl-rank { width: 18px; height: 18px; display: inline-flex; align-items: center; justify-content: center; font-size: var(--text-xs); font-weight: var(--weight-bold); color: var(--muted); }
.hl-rank-1 { color: #d4a017; } .hl-rank-2 { color: #8a8d91; } .hl-rank-3 { color: #b07b4f; }
.hl-avatar { width: 24px; height: 24px; display: inline-flex; align-items: center; justify-content: center; border-radius: 50%; background: var(--primary); color: var(--text-on-dark, #fff); font-size: 11px; font-weight: var(--weight-semibold); }
.hl-name { font-size: var(--text-sm); font-weight: var(--weight-medium); }
.hl-more { font-size: var(--text-sm); color: var(--primary-fg); text-decoration: none; font-weight: var(--weight-semibold); }
.hl-more:hover { text-decoration: underline; }
.cm-card { display: flex; flex-direction: column; background: var(--card); border: .5px solid var(--line); border-radius: var(--radius); overflow: hidden; box-shadow: var(--shadow-xs); text-decoration: none; color: var(--ink); transition: transform .35s var(--ease-spring-gentle), box-shadow .35s var(--ease-out-expo), border-color .3s var(--ease-out); }
.cm-card:hover { transform: translateY(-3px); box-shadow: var(--shadow-md); border-color: var(--border); }
.cm-card:active { transform: scale(.98); transition-duration: .1s; }
.cm-card:focus-visible { outline: 2px solid var(--primary); outline-offset: 3px; }
.cm-img { aspect-ratio: 16 / 9; overflow: hidden; background: var(--bg-alt); }
.cm-img img { width: 100%; height: 100%; object-fit: cover; }
.cm-body { display: flex; flex-direction: column; gap: var(--space-2); padding: var(--space-3) var(--space-4) var(--space-4); }
.cm-author { display: flex; align-items: center; gap: var(--space-2); min-width: 0; }
.cm-avatar { width: 26px; height: 26px; display: inline-flex; align-items: center; justify-content: center; border-radius: 50%; background: var(--primary); color: var(--text-on-dark, #fff); font-size: var(--text-xs); font-weight: var(--weight-semibold); flex-shrink: 0; }
.cm-name { font-size: var(--text-sm); font-weight: var(--weight-semibold); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.cm-type { margin-left: auto; font-size: var(--text-xs); color: var(--muted); background: var(--bg-alt); padding: 1px 8px; border-radius: var(--radius-full); white-space: nowrap; flex-shrink: 0; }
.cm-content { margin: 0; font-size: var(--text-sm); color: var(--ink-700); line-height: var(--leading-snug); display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }
.cm-meta { display: flex; flex-wrap: wrap; gap: var(--space-3); font-size: var(--text-xs); color: var(--muted); }
.cm-place { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 60%; }
.dark .cm-card { background: var(--card); border-color: var(--line); }
.dark .cm-card:hover { border-color: rgba(255,255,255,.1); }

/* ── Card grid choreography ── */
.home .grid .card,
.home .scroll-row .card {
  transition:
    transform .18s var(--ease-out),
    box-shadow .25s var(--ease-out);
}

/* ── Region tiles — enhanced ── */
.home .region-tile {
  transition:
    transform .18s var(--ease-out),
    box-shadow .25s var(--ease-out);
}
.region-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: var(--space-2);
}
.region-count {
  font-size: var(--text-sm);
  font-weight: var(--weight-extrabold);
  opacity: .95;
}
.region-cta {
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  opacity: .85;
  transition: opacity .3s;
}
.region-tile:hover .region-cta { opacity: 1; }
/* Per-region tint overlays */
.region-vinh-long .region-tile-in { background: linear-gradient(135deg, rgba(var(--primary-rgb),.82) 0%, rgba(var(--primary-rgb),.55) 100%); }
.region-ben-tre .region-tile-in { background: linear-gradient(135deg, rgba(var(--secondary-rgb),.82) 0%, rgba(var(--secondary-rgb),.55) 100%); }
.region-tra-vinh .region-tile-in { background: linear-gradient(135deg, rgba(var(--river-rgb),.82) 0%, rgba(var(--river-rgb),.55) 100%); }

/* ── Khám phá theo sở thích — card lớn có ảnh ── */
/* Bento bất-đối-xứng: ô đầu (Ẩm thực) lớn 2×2, 4 ô còn lại nhỏ → phá thế lưới đều */
.interest-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  grid-auto-rows: minmax(132px, 1fr);
  gap: var(--space-4);
}
.interest-card:first-child {
  grid-column: span 2;
  grid-row: span 2;
}
.interest-card:first-child .interest-emoji { font-size: 2.6rem; }
.interest-card:first-child .interest-in h3 { font-size: var(--text-2xl); }
.interest-card:first-child .interest-in p { -webkit-line-clamp: 3; font-size: var(--text-sm); }
@media (max-width: 720px) {
  .interest-grid { grid-template-columns: repeat(2, 1fr); }
  .interest-card:first-child { grid-column: span 2; grid-row: span 1; min-height: 200px; }
}
/* Giữ bento 2-cột tới máy rất nhỏ (gọn + đỡ đơn-điệu hơn 5 thẻ full-width xếp dọc);
   chỉ về 1-cột khi ≤360px (thẻ 2-cột sẽ quá hẹp). */
@media (max-width: 360px) {
  .interest-grid { grid-template-columns: 1fr; }
  .interest-card:first-child { grid-column: span 1; }
}
.interest-card {
  position: relative;
  display: block;
  min-height: 0;  /* để grid-auto-rows điều-khiển (bento): ô nhỏ thấp, ô đầu cao 2 hàng */
  border-radius: var(--radius);
  overflow: hidden;
  background-size: cover;
  background-position: center;
  text-decoration: none;
  box-shadow: var(--shadow-sm);
  transition: transform .18s var(--ease-out), box-shadow .25s var(--ease-out);
}
.interest-card:hover { transform: translateY(-3px); box-shadow: var(--shadow-lg); }
.interest-card:active { transform: scale(.98); transition-duration: .1s; }
.interest-card:focus-visible { outline: 2px solid var(--primary); outline-offset: 3px; }
.interest-in {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  gap: var(--space-1);
  padding: var(--space-4);
  background: linear-gradient(to top, rgba(var(--ink-rgb), .86) 0%, rgba(var(--ink-rgb), .35) 48%, rgba(var(--ink-rgb), .04) 100%);
  color: #fff;
}
.interest-emoji { font-size: 1.7rem; line-height: 1; }
.interest-in h3 { margin: var(--space-1) 0 0; font-size: var(--text-lg); font-weight: var(--weight-bold); letter-spacing: -.01em; }
.interest-in p { margin: 0; font-size: var(--text-xs); opacity: .92; line-height: var(--leading-snug); display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.interest-cta { margin-top: var(--space-2); font-size: var(--text-sm); font-weight: var(--weight-semibold); opacity: .9; transition: opacity .3s; }
.interest-card:hover .interest-cta { opacity: 1; }
@media (prefers-reduced-motion: reduce) {
  .interest-card:hover { transform: none; }
  .interest-card:active { transform: none; }
}

/* ── Spotlight — magazine split: 1 điểm nổi bật cỡ lớn, panel thiết-kế (KHÔNG
   ô-ảnh-trống), phá nhịp lưới card. Đảo-chiều stack trên mobile. ── */
.spotlight {
  display: grid;
  grid-template-columns: 1.05fr 1fr;
  gap: var(--space-6);
  align-items: stretch;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius-xl);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
}
@media (max-width: 760px) { .spotlight { grid-template-columns: 1fr; } }
.spot-visual {
  position: relative;
  min-height: 300px;
  background-size: cover;
  background-position: center;
  display: flex; align-items: center; justify-content: center;
  overflow: hidden;
  text-decoration: none;
  isolation: isolate;
}
/* Panel "thở": quầng sáng khí-quyển trôi chậm sau motif (composited, reduced-motion off).
   Layer riêng → KHÔNG đụng transform hover của .spot-icon. */
.spot-visual::before {
  content: ""; position: absolute; inset: -18%; z-index: 0;
  background: radial-gradient(46% 46% at 34% 30%, rgba(255,255,255,.24) 0%, transparent 68%);
  animation: spot-glow 13s ease-in-out infinite alternate;
  pointer-events: none;
}
.spot-region, .spot-icon { position: relative; z-index: 1; }
@keyframes spot-glow {
  0%   { transform: translate3d(0, 0, 0) scale(1); opacity: .9; }
  100% { transform: translate3d(7%, 5%, 0) scale(1.12); opacity: 1; }
}
@media (max-width: 760px) { .spot-visual { min-height: 180px; } }
.spot-icon {
  width: 150px; height: 150px;
  opacity: .88;
  color: var(--text-on-dark, #fff);
  filter: drop-shadow(0 4px 16px rgba(0,0,0,.28));
  transition: transform .6s var(--ease-out-expo);
  pointer-events: none;
}
.spot-icon :deep(svg), .spot-icon svg { width: 100%; height: 100%; display: block; }
.spot-visual:hover .spot-icon { transform: scale(1.07) rotate(-2deg); }
/* Mobile icon nhỏ hơn — ĐẶT SAU base .spot-icon để override đúng (cùng specificity). */
@media (max-width: 760px) { .spot-icon { width: 96px; height: 96px; } }
.spot-region {
  position: absolute; top: var(--space-4); left: var(--space-4);
  padding: var(--space-1) var(--space-3);
  background: rgba(0,0,0,.36);
  color: #fff; border-radius: var(--radius-full);
  font-size: var(--text-xs); font-weight: var(--weight-semibold);
  backdrop-filter: blur(4px); -webkit-backdrop-filter: blur(4px);
}
.spot-body {
  padding: var(--space-8) var(--space-8) var(--space-8) 0;
  display: flex; flex-direction: column; justify-content: center;
  gap: var(--space-3); min-width: 0;
}
@media (max-width: 760px) { .spot-body { padding: var(--space-5); } }
.spot-kicker {
  font-size: var(--text-xs); font-weight: var(--weight-bold);
  text-transform: uppercase; letter-spacing: .05em;
  color: var(--primary-fg-strong);
}
.spot-body h2 {
  margin: 0;
  font-size: clamp(1.5rem, 3.2vw, 2.1rem);
  line-height: var(--leading-snug); letter-spacing: -.01em;
}
.spot-sum {
  margin: 0; color: var(--text-muted); line-height: var(--leading-relaxed);
  display: -webkit-box; -webkit-line-clamp: 4; -webkit-box-orient: vertical; overflow: hidden;
}
.spot-cta { align-self: flex-start; margin-top: var(--space-2); }
@media (prefers-reduced-motion: reduce) {
  .spot-visual:hover .spot-icon { transform: none; }
  .spot-visual::before { animation: none; }
}

/* ── Interstitial cinematic ("act-break") — dải tối điện-ảnh: khí-quyển 3-màu-vùng
   trôi chậm + film-grain + đại-tự thơ. Contained (KHÔNG full-bleed → tránh cv-clip).
   Mọi animation composited + reduced-motion tắt. ── */
.block-cine { padding: var(--space-8) var(--space-5); max-width: var(--maxw); margin: 0 auto; }
.cine {
  position: relative; isolation: isolate; overflow: hidden;
  border-radius: var(--radius-xl);
  /* Hairline rim → định-hình cạnh dải tối khi nằm trên nền-tối (dark mode), tinh-tế ở light. */
  border: 1px solid rgba(255,255,255,.08);
  padding: clamp(var(--space-12), 9vw, var(--space-16)) var(--space-6);
  text-align: center; color: #fff;
  background: linear-gradient(135deg, #14241f 0%, #1a1f24 48%, #241a16 100%);
  box-shadow: var(--shadow-lg);
}
/* Dark: viền rõ hơn chút + glow màu-vùng đậm hơn để dải nổi trên nền tối. */
.dark .cine { border-color: rgba(255,255,255,.1); }
.dark .cine-bg { filter: blur(10px) saturate(1.15) brightness(1.12); }
.cine-bg {
  position: absolute; inset: -25%; z-index: -2;
  background:
    radial-gradient(40% 50% at 22% 28%, rgba(46,160,120,.40) 0%, transparent 60%),
    radial-gradient(42% 52% at 80% 72%, rgba(232,163,61,.32) 0%, transparent 62%),
    radial-gradient(50% 60% at 60% 16%, rgba(58,140,170,.28) 0%, transparent 60%);
  filter: blur(10px);
  animation: cine-drift 20s ease-in-out infinite alternate;
}
@keyframes cine-drift {
  0%   { transform: translate3d(0, 0, 0) scale(1); }
  100% { transform: translate3d(2.6%, -2.2%, 0) scale(1.1); }
}
.cine-grain {
  position: absolute; inset: 0; z-index: -1; opacity: .14; pointer-events: none;
  mix-blend-mode: overlay;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='140' height='140'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
}
.cine-inner { position: relative; }
.cine-kicker {
  margin: 0 0 var(--space-3); font-size: var(--text-xs); font-weight: var(--weight-bold);
  letter-spacing: .22em; text-transform: uppercase; color: rgba(255,255,255,.78);
}
.cine-title {
  margin: 0; font-weight: var(--weight-extrabold);
  font-size: clamp(2rem, 6.2vw, 3.7rem); line-height: 1.06; letter-spacing: -.02em;
  text-shadow: 0 2px 28px rgba(0,0,0,.4);
}
.cine-sub {
  margin: var(--space-5) auto 0; max-width: 560px;
  font-size: var(--text-lg); line-height: var(--leading-relaxed); color: rgba(255,255,255,.84);
}
@media (max-width: 640px) {
  .cine { padding: var(--space-12) var(--space-5); }
  .cine-sub { font-size: var(--text-base); }
}
/* Interstitial #2 (mời cộng-đồng): gradient ấm hơn + CTA */
.cine--invite { background: linear-gradient(135deg, #241a16 0%, #20191f 46%, #142420 100%); }
.cine-cta { margin-top: var(--space-6); display: inline-flex; }

/* Parallax-lite: nội-dung interstitial trôi nhẹ theo cuộn (depth điện-ảnh).
   Scroll-driven (compositor, 0 JS); @supports + reduced-motion → Firefox/giảm-motion
   tự fallback TĨNH, không vỡ. Chỉ ±24px nên an-toàn trong khung overflow-hidden. */
@media (prefers-reduced-motion: no-preference) {
  @supports (animation-timeline: view()) {
    .cine-inner {
      animation: cine-parallax linear both;
      animation-timeline: view();
      animation-range: entry 8% exit 92%;
      will-change: transform;
    }
  }
}
@keyframes cine-parallax {
  from { transform: translateY(26px); }
  to   { transform: translateY(-26px); }
}
@media (prefers-reduced-motion: reduce) {
  .cine-bg { animation: none; }
  .cine-inner { animation: none; transform: none; }
}

/* ── Quick links — grid layout ── */
.quick-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-3);
}
@media (max-width: 640px) {
  .quick-grid { grid-template-columns: repeat(2, 1fr); }
}
.quick-link {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-4) var(--space-3);
  background: var(--card);
  border: .5px solid var(--line);
  border-radius: var(--radius);
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  color: var(--ink);
  min-height: 44px;
  text-align: center;
  transition:
    transform .35s var(--ease-spring-gentle),
    box-shadow .35s var(--ease-out-expo),
    border-color .3s var(--ease-out);
}
.quick-link:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-md);
  border-color: var(--primary-fg);
  color: var(--primary-fg);
}
.quick-link:active {
  transform: scale(.95);
  transition-duration: .1s;
}
.quick-link:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
  box-shadow: inset 0 0 0 2px var(--card);
}
.ql-icon { font-size: 1.6rem; line-height: 1; display: flex; align-items: center; justify-content: center; height: 1.8rem; }
.ql-text { font-size: var(--text-xs); }

/* ── Chatbot CTA — enhanced ── */
.chatbot-cta {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  margin-top: var(--space-6);
  padding: var(--space-5) var(--space-6);
  background: linear-gradient(135deg, var(--bg-alt) 0%, var(--bg-warm) 100%);
  border: .5px solid var(--line);
  border-radius: var(--radius);
  transition: border-color .3s var(--ease-out), box-shadow .35s var(--ease-out-expo), transform .35s var(--ease-spring-gentle);
}
.chatbot-cta:hover {
  border-color: var(--border);
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}
.chatbot-cta-inner { flex: 1; }
.chatbot-cta-text {
  margin: 0;
  font-size: var(--text-base);
  font-weight: var(--weight-semibold);
  color: var(--ink);
}
.chatbot-cta-sub {
  margin: var(--space-1) 0 0;
  font-size: var(--text-sm);
  color: var(--muted);
  line-height: var(--leading-relaxed);
}
.chatbot-cta-btn {
  padding: var(--space-3) var(--space-6);
  background: var(--primary);
  color: var(--text-on-dark, #fff);
  border: none;
  border-radius: var(--radius-full);
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  cursor: pointer;
  min-height: 44px;
  white-space: nowrap;
  transition: background .3s var(--ease-out), transform .35s var(--ease-spring-gentle), box-shadow .3s var(--ease-out);
}
.chatbot-cta-btn:hover {
  background: var(--primary-dark, var(--primary));
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}
.chatbot-cta-btn:active {
  transform: scale(.95);
  transition-duration: .1s;
}
.chatbot-cta-btn:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 3px;
}
@media (max-width: 480px) {
  .chatbot-cta { flex-direction: column; text-align: center; gap: var(--space-3); }
  .chatbot-cta-btn { width: 100%; }
}

/* ── Region picker (first visit) ── */
.region-picker {
  text-align: center;
  padding: var(--space-5) var(--space-5);
  margin: 0 auto var(--space-4);
  max-width: var(--maxw);
}
.rp-question {
  font-size: var(--text-base);
  font-weight: var(--weight-semibold);
  color: var(--ink);
  margin: 0 0 var(--space-3);
}
.rp-options {
  display: flex;
  gap: var(--space-2);
  justify-content: center;
  flex-wrap: wrap;
}
.rp-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-5);
  background: var(--card);
  border: 1.5px solid var(--line);
  border-radius: var(--radius-full);
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  color: var(--ink);
  cursor: pointer;
  min-height: 44px;
  transition: transform .35s var(--ease-spring-gentle), box-shadow .3s var(--ease-out), border-color .3s var(--ease-out), background .3s var(--ease-out);
}
.rp-btn:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-sm);
  border-color: var(--primary-fg);
  color: var(--primary-fg);
}
.rp-btn:active {
  transform: scale(.95);
  transition-duration: .08s;
}
.rp-btn:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 3px;
}
.rp-emoji { font-size: 1.2rem; }

/* Skip / escape hatch — quiet secondary action so first-time users can start
   browsing immediately without committing a region. */
.rp-skip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-top: var(--space-3);
  padding: var(--space-2) var(--space-3);
  background: none;
  border: none;
  border-radius: var(--radius-full);
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
  color: var(--muted);
  cursor: pointer;
  min-height: 44px;
  text-decoration: underline;
  text-underline-offset: 3px;
  transition: color .3s var(--ease-out);
}
.rp-skip:hover { color: var(--primary-fg); }
.rp-skip:active { transform: scale(.96); transition-duration: .08s; }
.rp-skip:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }

/* ── Welcome back banner ── */
.welcome-back {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  padding: var(--space-4) var(--space-5);
  max-width: var(--maxw);
  margin: 0 auto var(--space-4);
  font-size: var(--text-sm);
  color: var(--muted);
}
.wb-text strong { color: var(--primary-fg); font-weight: var(--weight-semibold); }
.wb-change {
  background: none;
  border: 1px solid var(--line);
  border-radius: var(--radius-full);
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  color: var(--muted);
  cursor: pointer;
  white-space: nowrap;
  min-height: 44px;
  display: inline-flex;
  align-items: center;
  transition: border-color .3s var(--ease-out), color .3s var(--ease-out);
}
.wb-change:hover { border-color: var(--primary-fg); color: var(--primary-fg); }
.wb-change:active { transform: scale(.95); transition-duration: .08s; }
.wb-change:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
@media (max-width: 480px) {
  .welcome-back { flex-direction: column; text-align: center; }
}

/* ── Region active highlight ── */
.region-active {
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg);
}
.region-active .region-tile-in {
  box-shadow: inset 0 0 0 2px rgba(255,255,255,.5);
}

/* ── Region mini-switcher bar ── */
.region-mini-bar {
  display: flex;
  justify-content: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  max-width: var(--maxw);
  margin: 0 auto var(--space-4);
  flex-wrap: wrap;
}
.rmb-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-2) var(--space-3);
  background: var(--bg-alt);
  border: 1px solid var(--line);
  border-radius: var(--radius-full);
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  color: var(--muted);
  cursor: pointer;
  min-height: 44px;
  transition: background .3s var(--ease-out), border-color .3s var(--ease-out), color .3s var(--ease-out), transform .35s var(--ease-spring-gentle);
}
.rmb-btn:hover {
  border-color: var(--primary-fg);
  color: var(--primary-fg);
  transform: translateY(-1px);
}
.rmb-btn:active {
  transform: scale(.95);
  transition-duration: .08s;
}
.rmb-btn.active {
  background: var(--primary);
  border-color: var(--primary);
  color: var(--text-on-dark, #fff);
}

/* Dark mode: hero gradient — đặt trên LAYER kenburns (khớp Ken-Burns), không
   re-add lên .hero (tránh nhị ảnh + gradient sáng sai do --ink-rgb đảo ở dark).
   PERF: dùng hero.webp (cùng ảnh jpg, đã verify diff 0.48/255) — webp đã PRELOAD
   → dark LCP nhanh + bỏ jpg 217KB/78KB. */
.dark .home .hero-kenburns {
  background-image:
    linear-gradient(105deg, rgba(26,26,26,.82) 0%, rgba(26,26,26,.48) 46%, rgba(26,26,26,.08) 100%),
    url('/img/hero.webp');
}
@media (max-width: 640px) {
  .dark .home .hero-kenburns {
    background-image:
      linear-gradient(105deg, rgba(26,26,26,.82) 0%, rgba(26,26,26,.48) 46%, rgba(26,26,26,.08) 100%),
      url('/img/hero-mobile.webp');
  }
}

/* Dark mode — flagship hero pieces */
.dark .home .hero-scrim {
  background:
    radial-gradient(120% 95% at 88% 6%, rgba(232,163,61,.22) 0%, rgba(232,163,61,.05) 34%, transparent 60%),
    radial-gradient(90% 70% at 6% 100%, rgba(var(--primary-rgb),.28) 0%, transparent 58%),
    linear-gradient(to top, rgba(0,0,0,.62) 0%, rgba(0,0,0,.10) 34%, transparent 58%);
}
.dark .home .hero-kicker { background: rgba(255,255,255,.08); border-color: rgba(255,255,255,.16); }
.dark .home .hero-search { background: rgba(28,28,30,.5); border-color: rgba(255,255,255,.12); }
.dark .home .hero-search input { background: var(--bg-alt); }
.dark .home .hero-search:focus-within { border-color: rgba(var(--accent-rgb), .55); }
.dark .home .section-head h2::before { background: linear-gradient(180deg, var(--accent) 0%, var(--primary-fg) 100%); }
.dark .home .block + .block::before { background: linear-gradient(90deg, transparent, var(--line) 22%, var(--line) 78%, transparent); opacity: .6; }

/* Dark mode */
.dark .event-card { background: var(--card); border-color: var(--line); }
.dark .ec-countdown { color: #e0b366; }
.dark .ec-today { color: #f0846f; }
.dark .event-card:hover { border-color: rgba(255,255,255,.1); }
.dark .chatbot-cta { background: linear-gradient(135deg, var(--card) 0%, rgba(255,255,255,.03) 100%); border-color: var(--line); }
.dark .chatbot-cta:hover { border-color: rgba(255,255,255,.1); }
.dark .stats-bar .stat-item:hover { background: rgba(255,255,255,.03); }
.dark .hero-pill { background: var(--glass-medium); border-color: var(--border); }
.dark .quick-link { background: var(--card); }
.dark .stat-num { color: var(--primary-fg-strong); }
.dark .rp-btn { background: var(--bg-alt); border-color: var(--border); }
.dark .rp-btn:hover { background: var(--card); }
.dark .rmb-btn { background: rgba(255,255,255,.06); border-color: rgba(255,255,255,.12); }
.dark .rmb-btn:hover:not(.active) { background: rgba(255,255,255,.08); border-color: rgba(255,255,255,.15); }
.dark .rmb-btn.active { background: var(--primary); border-color: var(--primary); color: #fff; }
.dark .wb-change { border-color: var(--border); }

/* Reduce transparency */
@media (prefers-reduced-transparency: reduce) {
  .quick-link { backdrop-filter: none; }
  .hero-pill { backdrop-filter: none; background: rgba(255,255,255,.3); }
}

/* Reduce transparency — flagship hero glass falls back to solid scrims */
@media (prefers-reduced-transparency: reduce) {
  .home .hero-kicker { backdrop-filter: none; -webkit-backdrop-filter: none; background: rgba(0,0,0,.4); }
  .home .hero-search { backdrop-filter: none; -webkit-backdrop-filter: none; background: rgba(0,0,0,.35); }
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  /* Flagship hero: no entrance, no pulse, no underline draw — show final state */
  html.js .home .hero-enter > * { opacity: 1; transform: none; animation: none; }
  html.js .home .hero-enter h1::after { animation: none; transform: scaleX(1); opacity: 1; }
  .home .hero-kicker-dot { animation: none; }
  .home .hero-kenburns { animation: none; transform: none; }
  html.js .home .hero-feature { opacity: 1; transform: none; animation: none; }
  .hf-card:hover { transform: none; }
  .event-hero::before { animation: none; opacity: 0; }
  .hero-pill:hover { transform: none; }
  .hero-pill:active { transform: none; }
  .event-card:hover { transform: none; }
  .event-card:active { transform: none; }
  .quick-link:hover { transform: none; }
  .quick-link:active { transform: none; }
  .chatbot-cta:hover { transform: none; }
  .chatbot-cta-btn:hover { transform: none; }
  .chatbot-cta-btn:active { transform: none; }
  .home .region-tile:hover { transform: none; }
  .home .region-tile:active { transform: none; }
  .ec-live-dot { animation: none; }
  .rp-btn:hover { transform: none; }
  .rp-btn:active { transform: none; }
  .rp-skip:active { transform: none; }
  .rmb-btn:hover { transform: none; }
  .rmb-btn:active { transform: none; }
  .stats-bar .stat-item:hover { transform: none; }
}
</style>
