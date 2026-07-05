<template>
  <div class="home">
    <!-- 1. Hero — dynamic tagline + search + quick-pick pills + stats inline -->
    <section class="hero" aria-label="Giới thiệu">
      <div class="hero-kenburns" aria-hidden="true"></div>
      <HeroIllustration />
      <div class="hero-scrim" aria-hidden="true"></div>
      <div class="hero-inner">
        <div class="hero-main hero-enter">
          <span class="hero-kicker"><span class="hero-kicker-dot" aria-hidden="true"></span>{{ ss('homepage.hero_kicker', 'Du lịch & Đặc sản Vĩnh Long') }}</span>
          <h1>{{ seasonalTagline }}</h1>
          <p class="hero-sub">{{ ss('homepage.hero_subtitle', 'Tìm điểm đến, món ngon, lễ hội và lịch trình phù hợp cho chuyến đi Vĩnh Long hôm nay.') }}</p>
          <SearchAutocomplete class="hero-search hero-ac" :placeholder="ss('homepage.search_placeholder', 'Tìm điểm đến, món ngon, lịch trình…')" />
          <div class="hero-pills">
            <NuxtLink v-for="pill in heroPills" :key="pill.to" :to="pill.to" class="hero-pill">{{ pill.label }}</NuxtLink>
          </div>
        </div>
        <aside v-if="heroFeature" class="hero-feature" aria-label="Gợi ý nổi bật">
          <div class="hf-card">
            <NuxtLink :to="entityPath(heroFeature.id)" class="hf-thumb" :class="`cat-${hfMeta?.cat}`" :style="{ backgroundImage: hfBg }" :aria-label="`Xem ${heroFeature.name}`">
              <span v-if="!heroFeature?.images?.length" class="hf-thumb-icon" v-html="hfIcon" />
            </NuxtLink>
            <span class="hf-body">
              <span class="hf-tag">{{ heroFeatureReason }}</span>
              <NuxtLink :to="entityPath(heroFeature.id)" class="hf-title">{{ heroFeature.name }}</NuxtLink>
              <span v-if="hfRegion" class="hf-region">{{ hfRegion }}</span>
              <span v-if="heroFeature.summary" class="hf-summary">{{ heroFeature.summary }}</span>
              <span class="hf-actions">
                <NuxtLink :to="entityPath(heroFeature.id)" class="hf-action hf-action-primary">Khám phá</NuxtLink>
                <NuxtLink :to="plannerAddPath(heroFeature.id)" no-prefetch class="hf-action">Thêm vào lịch trình</NuxtLink>
              </span>
            </span>
          </div>
        </aside>
      </div>
      <div v-if="statsItems.length" class="hero-stats" role="group" aria-label="Thống kê nổi bật">
        <div class="hero-stat" v-for="s in statsItems" :key="s.label">
          <span class="hero-stat-num"><CountUp :value="s.value" /></span>
          <span class="hero-stat-label">{{ s.label }}</span>
        </div>
      </div>
    </section>

    <!-- 1a. Bắt đầu hành trình — data-driven decision layer -->
    <section v-if="homeDecisionCards.length" class="block block-compact reveal home-decision" aria-label="Bắt đầu hành trình">
      <div class="decision-shell">
        <div class="decision-copy">
          <span class="decision-kicker">Gợi ý nhanh</span>
          <h2>Hôm nay bạn muốn bắt đầu thế nào?</h2>
          <p>Dựa trên mùa, sự kiện và nội dung đang nổi bật để đưa bạn tới đúng luồng tiếp theo.</p>
        </div>
        <ol class="decision-index">
          <li v-for="(card, i) in homeDecisionCards" :key="card.to" class="dx-row">
            <NuxtLink :to="card.to" class="dx-item" :class="`dx-${card.tone}`">
              <span class="dx-num" aria-hidden="true">{{ String(i + 1).padStart(2, '0') }}</span>
              <span class="dx-main">
                <span class="dx-eyebrow">{{ card.eyebrow }}</span>
                <span class="dx-title">{{ card.title }}</span>
                <span class="dx-text">{{ card.text }}</span>
              </span>
              <span class="dx-go" aria-hidden="true">→</span>
            </NuxtLink>
          </li>
        </ol>
      </div>
    </section>

    <JourneyActionRail
      v-if="!homePending && homeJourneyActions.length"
      :actions="homeJourneyActions"
      title="Bước tiếp theo phù hợp"
      subtitle="Decision engine ưu tiên theo mục đã lưu, nội dung vừa xem, lịch gần nhất và tín hiệu cộng đồng."
      aria-label="Gợi ý hành trình trên trang chủ"
      compact
    />

    <!-- Degraded/empty fallback -->
    <section v-if="homeFailed" class="block reveal">
      <EmptyState icon="🌾" :tone="homeError ? 'error' : 'empty'" title="Đang cập nhật nội dung" :message="homeError ? 'Mạng chậm một chút rồi. Bạn thử tải lại giúp tụi mình nhé!' : 'Tụi mình đang bổ sung điểm đến và đặc sản cho khu vực này. Quay lại sau nhé!'">
        <template #actions>
          <button v-if="homeError" type="button" class="btn btn-outline" @click="refreshHome()">Tải lại</button>
        </template>
      </EmptyState>
    </section>

    <!-- Skeleton -->
    <section v-if="homeLoadingSkeleton" class="block reveal" aria-hidden="true">
      <div class="section-head"><div class="sk-heading"></div></div>
      <SkeletonGrid :count="3" />
    </section>

    <!-- 1b. Khám phá nhanh — compact category grid (always visible for navigation) -->
    <section v-if="!homePending" class="block block-compact reveal">
      <nav class="cat-grid" aria-label="Khám phá theo chủ đề">
        <NuxtLink v-for="cat in categoryLinks" :key="cat.to" :to="cat.to" class="cat-tile" :class="[`cat-tile-${cat.accent}`, `ct-${cat.key}`]">
          <span class="cat-emoji" aria-hidden="true">{{ cat.emoji }}</span>
          <span class="cat-label">{{ cat.label }}</span>
          <span class="cat-hint">{{ cat.hint }}</span>
          <span class="cat-count" v-if="cat.countLabel">{{ cat.countLabel }}</span>
        </NuxtLink>
      </nav>
    </section>

    <!-- 2. "Đang diễn ra" — upcoming events + seasonal -->
    <section v-if="upcomingEvents.length || seasonal.length" class="block reveal" aria-label="Sự kiện và lễ hội">
      <div class="section-head">
        <div class="sh-text">
          <h2>Đang diễn ra</h2>
          <p class="sh-sub">Sự kiện &amp; lễ hội sắp tới</p>
        </div>
        <NuxtLink class="see-all" to="/su-kien">Xem lịch →</NuxtLink>
      </div>

      <div v-if="upcomingEvents.length" class="happening-feature">
        <NuxtLink :to="entityPath(upcomingEvents[0].id)" class="event-hero">
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
          <NuxtLink v-for="ev in upcomingEvents.slice(1, 4)" :key="ev.id" :to="entityPath(ev.id)" class="event-mini">
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

      <div v-if="seasonal.length" class="happening-section">
        <p class="happening-label">🔥 Đang vào mùa tháng {{ currentMonth }}</p>
        <div class="scroll-row" role="region" aria-label="Đặc sản theo mùa" tabindex="0">
          <EntityCard v-for="e in seasonal" :key="e.id" :entity="e" :season-filter="String(currentMonth)" />
        </div>
      </div>
    </section>

    <!-- 2b. Feature — photo-led editorial block (Trải nghiệm miệt vườn) -->
    <section class="block reveal" aria-label="Trải nghiệm nổi bật">
      <EntityFeature
        image="/img/features/trai-nghiem.webp"
        v-bind="FEATURE_EXPERIENCE"
        :thumbs="experiences.slice(0, 3)"
        side="left"
        :priority="true"
      />
    </section>

    <!-- 3. Nổi bật — spotlight magazine + quán ngon rating -->
    <section v-if="spotlight || topDishes.length" class="block reveal band" aria-label="Nổi bật">
      <div class="section-head">
        <div class="sh-text">
          <h2>Nổi bật</h2>
          <p class="sh-sub">Điểm đến &amp; quán ăn được cộng đồng yêu thích</p>
        </div>
      </div>

      <div class="tinh-hoa">
        <div v-if="spotlight" class="spotlight">
          <NuxtLink
            :to="entityPath(spotlight.id)"
            class="spot-visual"
            :style="{ backgroundImage: spotBgCss }"
            :aria-label="spotlight.name"
          >
            <span v-if="spotRegion" class="spot-region">{{ spotRegion }}</span>
          </NuxtLink>
          <div class="spot-body">
            <span class="spot-kicker">{{ spotMeta?.label }} · Nổi bật</span>
            <h3 class="spot-name">{{ spotlight.name }}</h3>
            <p v-if="spotlight.summary" class="spot-sum">{{ spotlight.summary }}</p>
            <NuxtLink :to="entityPath(spotlight.id)" class="btn btn-primary spot-cta">Khám phá ngay →</NuxtLink>
          </div>
        </div>

        <div v-if="topDishes.length" class="top-dishes">
          <h3 class="dishes-heading">⭐ Quán ngon nổi bật</h3>
          <div class="dishes-list">
            <NuxtLink v-for="d in topDishes" :key="d.id" :to="entityPath(d.id)" class="dish-item">
              <span class="dish-rating-badge">
                <span class="dish-star">★</span>
                <span class="dish-score">{{ formatRating(d.attributes?.rating || 0) }}</span>
              </span>
              <span class="dish-info">
                <span class="dish-name">{{ d.name }}</span>
                <span v-if="d.attributes?.review_count" class="dish-reviews">{{ d.attributes.review_count }} đánh giá</span>
              </span>
              <span class="dish-arrow">→</span>
            </NuxtLink>
          </div>
          <div class="block-cta">
            <NuxtLink to="/kham-pha/am-thuc" class="btn btn-outline">🍲 Xem tất cả quán ăn</NuxtLink>
          </div>
        </div>
      </div>
    </section>

    <!-- 3a. Story spread — full-bleed signature moment -->
    <StorySpread
      image="/img/spread/song-nuoc.webp"
      srcset="/img/spread/song-nuoc-640.webp 640w, /img/spread/song-nuoc-1024.webp 1024w, /img/spread/song-nuoc.webp 1536w"
      v-bind="SPREAD"
    />

    <!-- 3a2. Feature — photo-led editorial block (Đặc sản OCOP), mirrored -->
    <section class="block reveal" aria-label="Đặc sản nổi bật">
      <EntityFeature
        image="/img/features/ocop.webp"
        v-bind="FEATURE_OCOP"
        :thumbs="productsAll.slice(0, 3)"
        side="right"
      />
    </section>

    <!-- 3b. Đang được quan tâm — trending entities -->
    <section v-if="trending.length" class="block reveal" aria-label="Đang được quan tâm">
      <div class="section-head">
        <div class="sh-text">
          <h2>🔥 Đang được quan tâm</h2>
          <p class="sh-sub">Điểm đến nhiều người tìm kiếm nhất tuần qua</p>
        </div>
      </div>
      <div class="scroll-row" role="region" aria-label="Điểm đến đang hot" tabindex="0">
        <EntityCard v-for="e in trending" :key="e.id" :entity="e" />
      </div>
    </section>

    <!-- 4. Lịch trình gợi ý -->
    <section v-if="itineraries.length" class="block reveal band" aria-label="Lịch trình gợi ý">
      <div class="section-head">
        <div class="sh-text">
          <h2>Lịch trình gợi ý</h2>
          <p class="sh-sub">Hành trình 1–2 ngày, đi là có ngay</p>
        </div>
        <NuxtLink class="see-all" to="/lich-trinh">Xem tất cả →</NuxtLink>
      </div>
      <div class="scroll-row" role="region" aria-label="Lịch trình gợi ý" tabindex="0">
        <ItineraryCard v-for="it in itineraries" :key="it.id" :itinerary="it" />
      </div>
      <div class="block-cta">
        <NuxtLink to="/tao-lich-trinh" no-prefetch class="btn btn-outline">📋 Tạo lịch trình riêng</NuxtLink>
      </div>
    </section>

    <!-- 5. Từ cộng đồng — compact + trending tags -->
      <section v-if="communityPosts.length || communityStats" class="block reveal" aria-label="Cộng đồng">
        <div class="section-head">
          <div class="sh-text">
            <h2>Từ cộng đồng</h2>
            <p class="sh-sub">Trải nghiệm thật, mẹo hay từ người đi trước</p>
          </div>
          <NuxtLink class="see-all" to="/cong-dong">Xem tất cả →</NuxtLink>
        </div>
        <template v-if="communityPosts.length">
          <p v-if="communityStats && (communityStats.posts || communityStats.reviews || communityStats.members)" class="community-stats-line">
            <strong>{{ communityStats.posts }}</strong> bài viết
            · <strong>{{ communityStats.reviews }}</strong> đánh giá
            · <strong>{{ communityStats.members }}</strong> thành viên
          </p>
          <div v-if="trendingTags.length" class="trending-tags">
            <span class="tt-label">🔥 Trending:</span>
            <NuxtLink v-for="t in trendingTags" :key="t.tag" :to="`/cong-dong?tag=${encodeURIComponent(t.tag)}`" class="tt-chip">{{ t.tag }}</NuxtLink>
          </div>
          <div v-if="topMembers.length" class="home-leaders">
            <span class="hl-label">🏆 Tích cực nhất:</span>
            <NuxtLink v-for="(m, i) in topMembers" :key="m.id" :to="userPath(m.username || m.id)" class="hl-chip">
              <span class="hl-rank" :class="`hl-rank-${Number(i) + 1}`">{{ Number(i) + 1 }}</span>
              <span class="hl-avatar">{{ (m.display_name || '?').charAt(0).toUpperCase() }}</span>
              <span class="hl-name">{{ m.display_name }}</span>
            </NuxtLink>
            <NuxtLink to="/bang-xep-hang" class="hl-more">Bảng xếp hạng →</NuxtLink>
          </div>
          <div class="scroll-row" role="region" aria-label="Bài viết cộng đồng mới" tabindex="0">
            <NuxtLink v-for="p in communityPosts" :key="p.id" :to="postPath(p.id)" class="cm-card">
              <div v-if="p.images && p.images.length && p.images[0]" class="cm-img">
                <NuxtImg v-if="isRemoteUrl(p.images[0])" :src="p.images[0]" :alt="p.display_name || 'Bài viết'" loading="lazy" decoding="async" width="280" height="150" sizes="sm:280px" @error="onImgError" />
                <img v-else :src="p.images[0]" :alt="p.display_name || 'Bài viết'" loading="lazy" decoding="async" width="280" height="150" @error="onImgError" />
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
                  <span v-if="p.entity_name" class="cm-place">{{ p.entity_name }}</span>
                </div>
              </div>
            </NuxtLink>
          </div>
        </template>
        <div class="community-join">
          <span>Chia sẻ quán ngon, điểm đẹp, mẹo đi — góp một mảnh ghép cho bản đồ chung.</span>
          <NuxtLink to="/cong-dong" class="btn btn-outline">💬 Tham gia cộng đồng</NuxtLink>
        </div>
      </section>

    <!-- 6. Cá nhân hóa — client-only (recently viewed + saved + AI recommendations) -->
    <ClientOnly>
      <section v-if="recentlyViewed.length" class="block reveal">
        <div class="section-head">
          <h2>Xem gần đây</h2>
        </div>
        <div class="scroll-row" role="region" aria-label="Xem gần đây" tabindex="0">
          <NuxtLink v-for="rv in recentlyViewed" :key="rv.id" :to="entityPath(rv.id)" class="card card-mini">
            <div v-if="rv.image" class="cover cover-img">
              <NuxtImg v-if="isRemoteUrl(rv.image)" :src="rv.image" :alt="rv.name" loading="lazy" decoding="async" width="320" height="180" sizes="sm:50vw md:33vw lg:320px" @error="onImgError" />
              <img v-else :src="rv.image" :alt="rv.name" loading="lazy" decoding="async" width="320" height="180" @error="onImgError" />
            </div>
            <div v-else class="cover cover-img cover-generated" :class="`cat-${getFavTypeMeta(rv.type).cat}`" :style="{ backgroundImage: genPlaceholder(rv.id, getFavTypeMeta(rv.type).cat) }">
              <span class="cover-svg-icon" v-html="genIcon(getFavTypeMeta(rv.type).cat)" />
            </div>
            <div class="card-b">
              <span class="card-type">{{ getFavTypeMeta(rv.type).label }}</span>
              <h3>{{ rv.name }}</h3>
            </div>
          </NuxtLink>
        </div>
      </section>
      <section v-if="recentSaved.length" class="block reveal">
        <div class="section-head">
          <h2>Đã lưu gần đây</h2>
          <NuxtLink class="see-all" to="/da-luu">Xem tất cả →</NuxtLink>
        </div>
        <div class="scroll-row" role="region" aria-label="Đã lưu gần đây" tabindex="0">
          <NuxtLink v-for="fav in recentSaved" :key="fav.id" :to="savedItemPath(fav)" class="card">
            <div v-if="fav.image" class="cover cover-img">
              <NuxtImg v-if="isRemoteUrl(fav.image)" :src="fav.image" :alt="fav.name" loading="lazy" decoding="async" width="480" height="192" sizes="sm:100vw md:50vw lg:480px" @error="onImgError" />
              <img v-else :src="fav.image" :alt="fav.name" loading="lazy" decoding="async" width="480" height="192" @error="onImgError" />
            </div>
            <div class="card-b">
              <span class="card-type">{{ getFavTypeMeta(fav.type).label }}</span>
              <h3>{{ fav.name }}</h3>
              <p v-if="fav.place_name" class="place">{{ fav.place_name }}</p>
            </div>
          </NuxtLink>
        </div>
      </section>
      <NuxtErrorBoundary>
        <LazySmartRecommendations context="home" title="Có thể bạn quan tâm" :limit="4" />
      </NuxtErrorBoundary>
    </ClientOnly>

    <!-- 7. Chatbot CTA -->
    <section class="block block-compact reveal" aria-label="Trợ lý AI">
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
import type { Entity } from '~/types'
import { TYPE_META, AREA_META } from '~/composables/useConstants'
import { generateCategoryPlaceholder, generateCategoryIcon } from '~/composables/useCategoryPlaceholder'
import { useJourneyActions } from '~/composables/useJourneyActions'
import EntityFeature from '~/components/home/EntityFeature.vue'
import StorySpread from '~/components/home/StorySpread.vue'

useReveal()
const { get: ss } = useSiteSettings()

const DEFAULT_HERO_PILLS = [
  { emoji: '📍', label: 'Gần tôi', to: '/ban-do?near=1' },
  { emoji: '🍲', label: 'Ăn gì hôm nay', to: '/kham-pha/am-thuc' },
  { emoji: '🗓️', label: 'Đi 2N1Đ', to: '/lich-trinh' },
  { emoji: '🌿', label: 'Miệt vườn', to: '/du-lich' },
  { emoji: '🗺️', label: 'Bản đồ', to: '/ban-do' },
  { emoji: '🎁', label: 'Đặc sản làm quà', to: '/ocop' },
]
const heroPills = computed(() => ss('homepage.hero_pills', DEFAULT_HERO_PILLS) as typeof DEFAULT_HERO_PILLS)
const { homepageDecisionActions } = useJourneyActions()

// Editorial photo-led feature copy (EntityFeature block). Contact/discover CTA only —
// never an order/price form, per project invariants.
const FEATURE_EXPERIENCE = {
  kicker: 'Trải nghiệm',
  title: 'Miệt vườn mở cửa đón bạn',
  lede: 'Chèo xuồng qua rạch dừa, hái trái tại vườn, nghe đờn ca giữa cù lao — những ngày chậm rãi rất Nam Bộ.',
  ctaText: 'Khám phá trải nghiệm',
  ctaTo: '/du-lich',
}

const FEATURE_OCOP = {
  kicker: 'Đặc sản OCOP',
  title: 'Mang cả miền Tây về làm quà',
  lede: 'Dừa sáp Cầu Kè, kẹo dừa, mật ong rừng bần, gạo thơm — sản vật đạt sao OCOP, gói ghém vị quê.',
  ctaText: 'Xem đặc sản OCOP',
  ctaTo: '/ocop',
}

// Full-bleed signature moment (StorySpread). Discover-only CTA — never an order/price
// form, per project invariants.
const SPREAD = {
  kicker: 'Vĩnh Long',
  title: 'Nơi vườn chạm sông',
  subtitle: 'Ba vùng đất — Vĩnh Long, Bến Tre, Trà Vinh — một miền phù sa, trái ngọt và những phiên chợ nổi.',
  ctaText: 'Khám phá vùng đất',
  ctaTo: '/ban-do',
}

type HomeDecisionCard = {
  icon: string
  eyebrow: string
  title: string
  text: string
  to: string
  cta: string
  tone: 'event' | 'season' | 'planner' | 'food' | 'map'
}

const { favorites } = useFavorites()
const recentSaved = computed(() => favorites.value.slice(0, 4))

const { recentItems } = useRecentlyViewed()
const recentlyViewed = computed(() => recentItems.value.slice(0, 6))
const genPlaceholder = generateCategoryPlaceholder
const genIcon = generateCategoryIcon

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
const getFavTypeMeta = getTypeMeta

const { data: homeData, error: homeError, pending: homePending, refresh: refreshHome } = await useAsyncData('homepage',
  () => apiFetch<any>('/api/homepage'))

const { data: communityData } = await useAsyncData('home-community', async () => {
  const [feed, cstats, lb, tags] = await Promise.all([
    apiFetch<any>('/api/feed?limit=10').catch(() => ({ posts: [] })),
    apiFetch<any>('/api/community/stats').catch(() => null),
    apiFetch<any>('/api/community/leaderboard?limit=3').catch(() => ({ leaders: [] })),
    apiFetch<any>('/api/community/trending-tags?limit=8').catch(() => ({ tags: [] })),
  ])
  const posts = (feed.posts || [])
    .filter((p: any) => ((p.content || '').trim().length > 0) || (p.images && p.images.length))
    .slice(0, 6)
  return { posts, stats: cstats, leaders: lb.leaders || [], tags: tags.tags || [] }
}, { lazy: true })
const communityPosts = computed(() => communityData.value?.posts || [])
const communityStats = computed(() => communityData.value?.stats || null)
const topMembers = computed(() => communityData.value?.leaders || [])
const trendingTags = computed(() => communityData.value?.tags || [])

const currentMonth = computed(() => homeData.value?.month || (new Date().getMonth() + 1))
const seasonal = computed(() => homeData.value?.seasonal || [])
const experiences = computed(() => homeData.value?.experiences || [])
const productsAll = computed(() => homeData.value?.products || [])
const topDishes = computed(() => homeData.value?.top_dishes || [])
const trending = computed(() => homeData.value?.trending || [])
const itineraries = computed(() => homeData.value?.itineraries || [])
const upcomingEvents = computed(() => homeData.value?.upcoming_events || [])
const seasonalTagline = computed(() => homeData.value?.seasonal_tagline || 'Khám phá Vĩnh Long theo cách của người bản địa')

const CATEGORY_LINKS = [
  { emoji: '🌿', label: 'Du lịch', hint: 'vườn, sông, làng nghề', to: '/du-lich', accent: 'leaf', countKey: 'experiences', key: 'du-lich' },
  { emoji: '🍲', label: 'Ẩm thực', hint: 'quán ngon, món bản địa', to: '/kham-pha/am-thuc', accent: 'amber', countKey: 'dishes', key: 'am-thuc' },
  { emoji: '🎁', label: 'OCOP', hint: 'đặc sản làm quà', to: '/ocop', accent: 'clay', countKey: 'products', key: 'ocop' },
  { emoji: '🎭', label: 'Lễ hội', hint: 'lịch gần nhất', to: '/le-hoi', accent: 'river', countKey: 'events', key: 'le-hoi' },
  { emoji: '🏡', label: 'Lưu trú', hint: 'nghỉ lại theo khu vực', to: '/luu-tru', accent: 'leaf', countKey: '', key: 'luu-tru' },
  { emoji: '🗺️', label: 'Bản đồ', hint: 'lọc theo vùng', to: '/ban-do', accent: 'river', countKey: 'areas', key: 'ban-do' },
]
const categoryLinks = computed(() => {
  return CATEGORY_LINKS.map(c => ({
    ...c,
    countLabel: categoryMetric(c.countKey),
  }))
})

const SPOTLIGHT_TYPE_WEIGHT: Record<string, number> = { experience: 3, place: 2, dish: 1, product: 0 }
const spotlight = computed<any>(() => {
  const pool = [...experiences.value.slice(0, 8), ...productsAll.value.slice(0, 8)]
  if (!pool.length) return null
  return pool.reduce((best: any, cur: any) => {
    const wc = SPOTLIGHT_TYPE_WEIGHT[cur?.type] ?? 1
    const wb = SPOTLIGHT_TYPE_WEIGHT[best?.type] ?? 1
    if (wc !== wb) return wc > wb ? cur : best
    return (cur?.summary || '').length > (best?.summary || '').length ? cur : best
  })
})
const spotId = computed(() => spotlight.value?.id)
const spotMeta = computed(() => spotlight.value ? (TYPE_META[spotlight.value.type] || { emoji: '📍', label: spotlight.value.type, cat: 'place' }) : null)
// Real AI-photo backdrop keyed off the spotlight's category — robust to spotlight
// rotation (no per-entity generation). Replaces the flat gradient + centered leaf icon.
const SPOT_CAT_PHOTO: Record<string, string> = {
  place: '/img/cat-du-lich.webp', experience: '/img/cat-du-lich.webp',
  product: '/img/cat-ocop.webp', dish: '/img/cat-am-thuc.webp',
  event: '/img/cat-le-hoi.webp', stay: '/img/cat-luu-tru.webp',
}
const spotPhoto = computed(() => spotlight.value?.images?.[0] || SPOT_CAT_PHOTO[spotMeta.value?.cat || ''] || '/img/cat-du-lich.webp')
const spotBgCss = computed(() => spotlight.value
  ? `linear-gradient(to top, rgba(18,20,24,.55) 0%, rgba(18,20,24,.10) 45%, rgba(18,20,24,.32) 100%), url(${spotPhoto.value})`
  : '')
const spotRegion = computed(() => {
  const a = spotlight.value?.area || spotlight.value?.attributes?.area || spotlight.value?.attributes?.province
  if (!a) return ''
  const meta = (AREA_META as Record<string, { name: string }>)[String(a)]
  return meta ? meta.name : ''
})

const heroFeature = computed<any>(() => experiences.value.find((e: any) => e.id !== spotId.value) || spotlight.value || null)
const hfMeta = computed(() => heroFeature.value ? (TYPE_META[heroFeature.value.type] || { emoji: '📍', label: heroFeature.value.type, cat: 'place' }) : null)
const hfBg = computed(() => {
  const img = heroFeature.value?.images?.[0]
  if (img) return `linear-gradient(to top, rgba(18,20,24,.42) 0%, rgba(18,20,24,.06) 45%, rgba(18,20,24,.22) 100%), url(${img})`
  return heroFeature.value && hfMeta.value ? generateCategoryPlaceholder(heroFeature.value.id, hfMeta.value.cat) : ''
})
const hfIcon = computed(() => hfMeta.value ? generateCategoryIcon(hfMeta.value.cat) : '')
const hfRegion = computed(() => {
  const a = heroFeature.value?.area || heroFeature.value?.attributes?.area || heroFeature.value?.attributes?.province
  if (!a) return ''
  const meta = (AREA_META as Record<string, { name: string }>)[String(a)]
  return meta ? meta.name : ''
})
const heroFeatureReason = computed(() => {
  if (!heroFeature.value) return 'Gợi ý nổi bật'
  const label = hfMeta.value?.label || 'Điểm đến'
  return hfRegion.value ? `${label} tại ${hfRegion.value}` : `${label} nổi bật`
})

const stats = computed(() => homeData.value?.stats || null)
const areaCounts = computed<Record<string, number>>(() => homeData.value?.area_counts || {})
const statsItems = computed(() => {
  const s = stats.value
  if (!s) return []
  const items: { value: string | number; label: string }[] = []
  if (s.entities) items.push({ value: s.entities + '+', label: 'Điểm đến & Đặc sản' })
  if (s.places) items.push({ value: s.places, label: 'Xã phường' })
  if (s.itineraries) items.push({ value: s.itineraries, label: 'Lịch trình' })
  return items
})

const firstUpcomingEvent = computed<any>(() => upcomingEvents.value[0] || null)
const firstSeasonal = computed<any>(() => seasonal.value[0] || null)
const firstDish = computed<any>(() => topDishes.value[0] || null)
const homeDecisionCards = computed<HomeDecisionCard[]>(() => {
  const cards: HomeDecisionCard[] = []
  const ev = firstUpcomingEvent.value
  if (ev) {
    cards.push({
      icon: '🎭',
      eyebrow: eventCountdownLabel(ev),
      title: 'Có lịch gần nhất',
      text: ev.name,
      to: entityPath(ev.id),
      cta: 'Xem sự kiện',
      tone: 'event',
    })
  }

  const seasonalPick = firstSeasonal.value
  if (seasonalPick) {
    cards.push({
      icon: '🌿',
      eyebrow: `Tháng ${currentMonth.value}`,
      title: 'Đang vào mùa',
      text: seasonalPick.name,
      to: `/theo-mua?mua=${encodeURIComponent(String(currentMonth.value))}`,
      cta: 'Xem theo mùa',
      tone: 'season',
    })
  }

  if (heroFeature.value) {
    cards.push({
      icon: '🧭',
      eyebrow: heroFeatureReason.value,
      title: 'Bắt đầu lịch trình',
      text: heroFeature.value.name,
      to: plannerAddPath(heroFeature.value.id),
      cta: 'Thêm điểm này',
      tone: 'planner',
    })
  }

  const dish = firstDish.value
  if (dish) {
    cards.push({
      icon: '🍲',
      eyebrow: dish.attributes?.rating ? `${formatRating(dish.attributes.rating)} điểm` : 'Ẩm thực',
      title: 'Ăn gì hôm nay',
      text: dish.name,
      to: '/kham-pha/am-thuc?sort=rating',
      cta: 'Xem quán ngon',
      tone: 'food',
    })
  }

  if (cards.length < 4) {
    cards.push({
      icon: '🗺️',
      eyebrow: `${Object.keys(areaCounts.value).length || 3} khu vực`,
      title: 'Mở bản đồ khám phá',
      text: 'Lọc điểm đến theo vùng, loại hình và vị trí gần bạn.',
      to: '/ban-do',
      cta: 'Mở bản đồ',
      tone: 'map',
    })
  }

  return cards.slice(0, 4)
})

const homeJourneyActions = computed(() => {
  const ev = firstUpcomingEvent.value
  return homepageDecisionActions({
    isLoggedIn: isLoggedIn.value,
    savedCount: favorites.value.length,
    recentCount: recentItems.value.length,
    currentMonth: currentMonth.value,
    heroFeatureName: heroFeature.value?.name,
    heroFeaturePlannerPath: heroFeature.value ? plannerAddPath(heroFeature.value.id) : '',
    upcomingEventName: ev?.name,
    upcomingEventPath: ev?.id ? entityPath(ev.id) : '',
    communityPostCount: communityPosts.value.length,
  })
})

const hasHomeContent = computed(() => !!(upcomingEvents.value.length || seasonal.value.length || itineraries.value.length || spotlight.value || topDishes.value.length || trending.value.length || communityPosts.value.length))
const homeFailed = computed(() => !homePending.value && (!!homeError.value || (!!homeData.value && !hasHomeContent.value)))
const homeLoadingSkeleton = computed(() => !hasHomeContent.value && !homeFailed.value)
onMounted(() => { if (homeError.value || !hasHomeContent.value) refreshHome() })

function formatEventDay(ev: any) {
  const ds = ev.attributes?.date_start
  if (!ds) return '?'
  return ds.split('-')[2]?.replace(/^0/, '') || '?'
}
function formatEventMonth(ev: any) {
  const ds = ev.attributes?.date_start
  if (!ds) return ''
  const m = parseInt(ds.split('-')[1] || '0', 10)
  return isNaN(m) || m === 0 ? '' : `Th${m}`
}

function eventCountdownLabel(ev: any) {
  if (ev?.days_until === 0) return 'Hôm nay'
  if (ev?.days_until === 1) return 'Ngày mai'
  if (typeof ev?.days_until === 'number') return `Còn ${ev.days_until} ngày`
  return 'Sắp diễn ra'
}

function formatRating(rating: number | string): string {
  const n = Number(rating)
  return n > 0 ? n.toFixed(1) : 'Mới'
}

function plannerAddPath(id: string | number) {
  return `/tao-lich-trinh?add=${encodeURIComponent(String(id))}`
}

function categoryMetric(key: string) {
  if (!key) return ''
  if (key === 'experiences') return experiences.value.length ? `${experiences.value.length} gợi ý` : ''
  if (key === 'dishes') return topDishes.value.length ? `${topDishes.value.length} nổi bật` : ''
  if (key === 'products') return productsAll.value.length ? `${productsAll.value.length} gợi ý` : ''
  if (key === 'events') return upcomingEvents.value.length ? `${upcomingEvents.value.length} sắp tới` : ''
  if (key === 'areas') {
    const count = Object.keys(areaCounts.value).length
    return count ? `${count} vùng` : ''
  }
  return ''
}

function onImgError(e: Event | string) {
  if (typeof e === 'string') return
  const img = e.target as HTMLImageElement
  img.style.display = 'none'
}

function areaName(slug: string | undefined): string {
  if (!slug) return ''
  const meta = (AREA_META as Record<string, { name: string }>)[slug]
  return meta ? meta.name : ''
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
  ogDescription: ss('seo.default_description', 'Cổng du lịch và sản phẩm địa phương Vĩnh Long: trải nghiệm miệt vườn, đặc sản theo mùa, OCOP, làng nghề và lịch trình gợi ý.'),
  ogImage: ss('branding.og_image', 'https://vinhlong360.vn/img/og-default.jpg'),
})

const eventListSchema = computed(() => {
  const events = upcomingEvents.value.map((ev: any, i: number) => ({
    '@type': 'ListItem',
    position: i + 1,
    item: {
      '@type': 'Event',
      name: ev.name,
      startDate: ev.attributes?.date_start,
      endDate: ev.attributes?.date_end || ev.attributes?.date_start,
      url: `https://vinhlong360.vn${entityPath(ev.id)}`,
      eventStatus: 'https://schema.org/EventScheduled',
      eventAttendanceMode: 'https://schema.org/OfflineEventAttendanceMode',
      location: { '@type': 'Place', name: ev.place_name || 'Vĩnh Long', address: { '@type': 'PostalAddress', addressRegion: areaName(ev.area || ev.place_area) || 'Vĩnh Long', addressCountry: 'VN' } },
    },
  }))
  if (!events.length) return ''
  return JSON.stringify({
    '@context': 'https://schema.org',
    '@type': 'ItemList',
    name: 'Sự kiện sắp tới tại Vĩnh Long',
    itemListElement: events,
  })
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
        description: 'Cổng du lịch và sản phẩm địa phương Vĩnh Long.',
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
        description: 'Cổng du lịch và sản phẩm địa phương Vĩnh Long.',
        inLanguage: 'vi-VN',
        areaServed: { '@type': 'AdministrativeArea', name: 'Vĩnh Long, Bến Tre, Trà Vinh' },
      }),
    },
    ...(eventListSchema.value ? [{ type: 'application/ld+json', innerHTML: eventListSchema.value }] : []),
  ],
})
</script>

<style>
/* ═══════════════════════════════════════════════════
   HERO — layered depth, Ken Burns, cinematic entrance
   ═══════════════════════════════════════════════════ */
.home .hero {
  isolation: isolate;
  min-height: 62vh;
  min-height: clamp(24rem, 62svh, 40rem);
  display: flex; flex-direction: column; justify-content: flex-end;
  padding-bottom: max(var(--space-6), env(safe-area-inset-bottom));
}
/* Cinematic scrim — a clean bottom-up wash (no coloured "glow" radials, which read AI-ish),
   anchoring an editorial masthead composition to the lower-left. */
.home .hero-scrim {
  position: absolute; inset: 0; z-index: 0; pointer-events: none;
  background:
    linear-gradient(to top, rgba(8,9,12,.80) 0%, rgba(8,9,12,.38) 24%, rgba(8,9,12,.06) 52%, transparent 74%),
    linear-gradient(103deg, rgba(8,9,12,.48) 0%, rgba(8,9,12,.10) 46%, transparent 70%);
}
/* Tactile grain over the image — the antidote to the flat "AI-gradient" look.
   Small tiled SVG the browser rasterises once; subtle overlay. */
.home .hero::after {
  content: ""; position: absolute; inset: 0; z-index: 0; pointer-events: none;
  background-image: var(--grain); background-size: 120px 120px;
  opacity: .05;
}
.home .hero-inner {
  position: relative; z-index: 1;
  width: min(100% - 2 * var(--space-5), 1180px); margin-inline: auto;
}

/* Hero asymmetric layout: ≥920px two columns */
@media (min-width: 920px) {
  .home .hero-inner { display: grid; grid-template-columns: minmax(0, 1.32fr) minmax(280px, 0.8fr); gap: var(--space-10); align-items: center; }
  .home .hero-feature { align-self: end; padding-bottom: var(--space-2); }
}
/* Mobile: hero feature as compact inline card (NOT hidden) */
@media (max-width: 919px) {
  .hero-feature { margin-top: var(--space-4); }
  .hf-card { padding: var(--space-3); gap: var(--space-3); }
  .hf-thumb { flex: 0 0 56px; height: 56px; }
  .hf-title { font-size: var(--text-base); }
}
.hf-card {
  display: flex; gap: var(--space-4); align-items: center;
  padding: var(--space-4);
  background: rgba(255,255,255,.07);
  backdrop-filter: saturate(160%) blur(6px); -webkit-backdrop-filter: saturate(160%) blur(6px);
  border: .5px solid rgba(255,255,255,.14);
  border-radius: var(--radius-md);
  color: var(--text-on-dark, #fff); text-decoration: none;
  box-shadow: 0 4px 18px rgba(0,0,0,.14);
  opacity: 1;
  transition: transform .4s var(--ease-spring-gentle), box-shadow .4s var(--ease-out-expo), background .3s var(--ease-out);
}
.hf-card:hover { transform: translateY(-4px); background: rgba(255,255,255,.16); box-shadow: var(--shadow-lg); opacity: 1; }
.hf-card:active { transform: scale(.99); transition-duration: .1s; }
.hf-thumb {
  flex: 0 0 76px; height: 76px; border-radius: var(--radius-md);
  background-size: cover; background-position: center;
  position: relative; overflow: hidden;
  display: flex; align-items: center; justify-content: center;
  color: var(--text-on-dark, #fff);
  text-decoration: none;
}
.hf-thumb:focus-visible, .hf-title:focus-visible, .hf-action:focus-visible { outline: 2px solid var(--text-on-dark, #fff); outline-offset: 3px; }
.hf-thumb-icon { width: 46px; height: 46px; opacity: .85; filter: drop-shadow(0 2px 6px rgba(0,0,0,.22)); }
.hf-thumb-icon :deep(svg), .hf-thumb-icon svg { width: 100%; height: 100%; display: block; }
.hf-body { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
.hf-tag { font-size: var(--text-xs); font-weight: var(--weight-bold); text-transform: uppercase; letter-spacing: .04em; color: var(--accent); }
.hf-title { color: inherit; text-decoration: none; font-size: var(--text-lg); font-weight: var(--weight-bold); line-height: var(--leading-snug); display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.hf-title:hover { text-decoration: underline; text-underline-offset: 3px; }
.hf-region { font-size: var(--text-xs); opacity: .88; }
.hf-summary { color: rgba(255,255,255,.78); font-size: var(--text-xs); line-height: var(--leading-snug); display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.hf-actions { display: flex; flex-wrap: wrap; gap: var(--space-2); margin-top: var(--space-2); }
.hf-action {
  display: inline-flex; align-items: center; justify-content: center;
  min-height: 38px; padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-full);
  background: rgba(255,255,255,.14); border: .5px solid rgba(255,255,255,.24);
  color: var(--text-on-dark, #fff); text-decoration: none;
  font-size: var(--text-xs); font-weight: var(--weight-bold);
}
.hf-action:hover { background: rgba(255,255,255,.22); }
.hf-action-primary { background: rgba(var(--accent-rgb), .28); border-color: rgba(var(--accent-rgb), .48); color: var(--text-on-dark, #fff); }
html.js .home .hero-feature { opacity: 0; transform: translateY(16px); animation: hero-rise .7s var(--ease-out-expo) .5s forwards; }

/* Ken Burns */
.home .hero { background-image: none; }
.home .hero-kenburns {
  position: absolute; inset: 0; z-index: 0;
  background-image:
    linear-gradient(105deg, rgba(var(--ink-rgb),.80) 0%, rgba(var(--ink-rgb),.42) 46%, rgba(var(--ink-rgb),.08) 100%),
    url('/img/hero.webp');
  background-size: cover; background-position: center;
  transform: scale(1.06);
  animation: hero-kenburns 34s var(--ease-in-out) infinite alternate;
  will-change: transform;
}
@media (max-width: 640px) {
  .home .hero-kenburns {
    background-image:
      linear-gradient(105deg, rgba(var(--ink-rgb),.82) 0%, rgba(var(--ink-rgb),.48) 46%, rgba(var(--ink-rgb),.12) 100%),
      url('/img/hero-mobile.webp');
  }
}
@keyframes hero-kenburns {
  0%   { transform: scale(1.06) translate3d(0, 0, 0); }
  100% { transform: scale(1.16) translate3d(-2.2%, -1.6%, 0); }
}

/* Kicker */
/* Editorial dateline eyebrow — a hairline rule + wide-tracked caps, not a glass badge/pill */
.home .hero-kicker {
  display: inline-flex; align-items: center; gap: var(--space-3);
  margin-bottom: var(--space-5);
  color: rgba(255,255,255,.88);
  font-family: var(--font-sans);
  font-size: var(--text-2xs); font-weight: 700;
  letter-spacing: .24em; text-transform: uppercase;
  text-shadow: 0 1px 3px rgba(0,0,0,.45);
}
.home .hero-kicker::before {
  content: ""; flex: 0 0 auto;
  width: clamp(26px, 6vw, 54px); height: 1.5px;
  background: var(--accent);
}
.home .hero-kicker-dot { display: none; }
@keyframes hero-dot-pulse {
  0% { box-shadow: 0 0 0 0 rgba(var(--accent-rgb), .55); }
  70% { box-shadow: 0 0 0 7px rgba(var(--accent-rgb), 0); }
  100% { box-shadow: 0 0 0 0 rgba(var(--accent-rgb), 0); }
}

/* Display headline — editorial serif, cinematic scale */
/* Masthead headline — oversized editorial serif, tight measure so it wraps into a
   strong multi-line block (no decorative accent bar under it — that reads templated). */
.home .hero h1 {
  font-family: var(--font-editorial);
  font-weight: 600;
  font-size: clamp(2.6rem, 3.4rem + 3.2vw, 5.4rem);
  letter-spacing: -.02em; line-height: .98;
  text-shadow: 0 2px 28px rgba(0,0,0,.42);
  max-width: 15ch;
  text-wrap: balance;
}
.home .hero-sub { font-family: var(--font-editorial); font-size: clamp(1.08rem, 1rem + .5vw, 1.3rem); line-height: 1.5; opacity: .95; max-width: 600px; margin: var(--space-4) 0 0; text-shadow: 0 1px 8px rgba(0,0,0,.22); }
.dark .home .hero-sub { opacity: 1; font-weight: 400; }

/* Cinematic entrance */
html.js .home .hero-enter > * { opacity: 0; transform: translateY(16px); animation: hero-rise .7s var(--ease-out-expo) forwards; }
html.js .home .hero-enter > .hero-kicker { animation-delay: .05s; }
html.js .home .hero-enter > h1 { animation-delay: .14s; }
html.js .home .hero-enter > .hero-sub { animation-delay: .24s; }
html.js .home .hero-enter > .hero-search { animation-delay: .34s; }
html.js .home .hero-enter > .hero-pills { animation-delay: .44s; }
@keyframes hero-rise {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}
html.js .home .hero-enter h1::after { animation: hero-underline-draw .8s var(--ease-out-expo) .5s both; }
@keyframes hero-underline-draw {
  from { transform: scaleX(0); opacity: 0; }
  to { transform: scaleX(1); opacity: 1; }
}

/* Premium search capsule */
.home .hero-search {
  padding: var(--space-1);
  background: rgba(255,255,255,.14);
  backdrop-filter: saturate(180%) blur(10px); -webkit-backdrop-filter: saturate(180%) blur(10px);
  border: .5px solid rgba(255,255,255,.30);
  border-radius: calc(var(--radius-md) + var(--space-1));
  box-shadow: 0 8px 30px rgba(0,0,0,.18), 0 2px 8px rgba(0,0,0,.12);
  transition: box-shadow .35s var(--ease-out-expo), border-color .3s var(--ease-out), transform .35s var(--ease-spring-gentle);
}
.home .hero .hero-ac::before {
  content: "";
  position: absolute;
  left: 20px;
  top: 50%;
  z-index: 2;
  width: 20px;
  height: 20px;
  transform: translateY(-50%);
  color: var(--primary-fg);
  opacity: .9;
  pointer-events: none;
  background: currentColor;
  -webkit-mask: url("data:image/svg+xml,%3Csvg viewBox='0 0 24 24' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath fill='none' stroke='black' stroke-width='2.35' stroke-linecap='round' stroke-linejoin='round' d='m21 21-4.34-4.34M10.8 18a7.2 7.2 0 1 1 0-14.4 7.2 7.2 0 0 1 0 14.4Z'/%3E%3C/svg%3E") center / contain no-repeat;
  mask: url("data:image/svg+xml,%3Csvg viewBox='0 0 24 24' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath fill='none' stroke='black' stroke-width='2.35' stroke-linecap='round' stroke-linejoin='round' d='m21 21-4.34-4.34M10.8 18a7.2 7.2 0 1 1 0-14.4 7.2 7.2 0 0 1 0 14.4Z'/%3E%3C/svg%3E") center / contain no-repeat;
}
.home .hero-search:focus-within {
  border-color: rgba(var(--accent-rgb), .72);
  box-shadow: 0 12px 40px rgba(0,0,0,.22), 0 0 0 4px rgba(var(--accent-rgb), .22);
  transform: translateY(-1px);
}
.home .hero-search input { border-color: transparent; background: var(--card); }
.home .hero-search input:focus { border-color: transparent; box-shadow: none; }
.home .hero .hero-ac { align-items: center; }
.home .hero .hero-ac input {
  flex: 1; width: 100%;
  padding: var(--space-4) 48px var(--space-4) 54px;
  border-color: transparent; background: var(--card);
}
.home .hero .hero-ac .ac-dropdown { text-align: left; }

/* Hero pills */
/* Editorial "quick index" — tracked text links with a hairline underline, not glass chips */
.hero-pills { display: flex; align-items: center; gap: var(--space-3) var(--space-5); margin-top: var(--space-6); flex-wrap: wrap; }
.hero-pill {
  display: inline-flex; align-items: center;
  color: rgba(255,255,255,.9); text-decoration: none;
  font-family: var(--font-sans); font-size: var(--text-sm); font-weight: 600;
  letter-spacing: .01em;
  min-height: 40px; padding: var(--space-1) 0;
  border-bottom: 1.5px solid rgba(255,255,255,.32);
  text-shadow: 0 1px 3px rgba(0,0,0,.4);
  transition: color .3s var(--ease-out), border-color .3s var(--ease-out);
}
.hero-pill:hover { color: #fff; border-color: var(--accent); }
.hero-pill:active { color: rgba(255,255,255,.7); }
.hero-pill:focus-visible { outline: 2px solid var(--text-on-dark, #fff); outline-offset: 3px; }
@media (max-width: 480px) {
  .hero-pills { gap: var(--space-2) var(--space-4); margin-top: var(--space-5); }
}

/* ═══════════════════════════════════════════════════
   HERO STATS — inline strip at bottom of hero
   ═══════════════════════════════════════════════════ */
/* Editorial "contents" strip — hairline-ruled meta line, left-aligned: serif numerals +
   tracked-caps labels. Replaces the centred glass stat-banner (a documented AI tell). */
.hero-stats {
  position: relative; z-index: 1;
  display: flex; flex-wrap: wrap; align-items: baseline;
  gap: var(--space-2) var(--space-5);
  margin: var(--space-6) 0 0;
  padding: var(--space-4) 0 0;
  border-top: 1px solid rgba(255,255,255,.20);
  max-width: 640px;
}
.hero-stat { display: inline-flex; align-items: baseline; gap: var(--space-2); }
.hero-stat-num {
  font-family: var(--font-editorial);
  font-size: var(--text-xl); font-weight: 600;
  color: #fff; letter-spacing: -.01em;
  text-shadow: 0 1px 8px rgba(0,0,0,.4);
}
.hero-stat-label {
  font-family: var(--font-sans);
  font-size: var(--text-2xs); color: rgba(255,255,255,.72);
  font-weight: 700; text-transform: uppercase; letter-spacing: .16em;
}
@media (max-width: 480px) {
  .hero-stats { gap: var(--space-2) var(--space-4); }
  .hero-stat-num { font-size: var(--text-lg); }
}

/* Decision layer */
.home-decision { padding-top: var(--space-8); }
.decision-shell {
  display: grid; grid-template-columns: minmax(220px, .48fr) minmax(0, 1fr);
  gap: var(--space-5); align-items: stretch;
}
.decision-copy {
  display: flex; flex-direction: column; justify-content: center;
  min-width: 0; padding: var(--space-1) 0;
}
.decision-kicker {
  width: fit-content; padding: 3px var(--space-2);
  border-radius: var(--radius-full);
  background: rgba(var(--primary-rgb), .08); color: var(--primary-fg);
  font-size: var(--text-xs); font-weight: var(--weight-bold); text-transform: uppercase; letter-spacing: .04em;
}
.decision-copy h2 {
  margin: var(--space-2) 0 0;
  font-size: clamp(1.15rem, 2vw, 1.55rem);
  line-height: var(--leading-snug); letter-spacing: 0;
}
.decision-copy p {
  margin: var(--space-2) 0 0; color: var(--muted);
  font-size: var(--text-sm); line-height: var(--leading-relaxed);
}
/* Editorial numbered index — the old uniform card-grid read as generic/AI-slop.
   This is conceptually a table-of-contents for the page: big serif numerals,
   hairline rules, no boxes, no emoji-in-box. */
.decision-index {
  display: grid; grid-template-columns: repeat(2, minmax(0, 1fr));
  column-gap: var(--space-8); row-gap: 0;
  margin: 0; padding: 0; list-style: none;
  border-top: 1px solid var(--line);
}
.dx-row { margin: 0; }
.dx-item {
  display: grid; grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center; gap: var(--space-4);
  padding: var(--space-4) var(--space-1);
  border-bottom: 1px solid var(--line);
  color: var(--ink); text-decoration: none;
  transition: background .3s var(--ease-out);
}
.dx-item:hover { background: var(--bg-warm); }
.dx-item:active { background: var(--bg-alt); }
.dx-item:focus-visible { outline: 2px solid var(--primary); outline-offset: -2px; }
.dx-num {
  font-family: var(--font-editorial);
  font-size: clamp(2rem, 1.3rem + 2.2vw, 2.9rem); line-height: 1;
  font-weight: 500; letter-spacing: -.02em; font-variant-numeric: tabular-nums;
  color: var(--tone, var(--muted)); opacity: .4;
  transition: opacity .3s var(--ease-out);
}
.dx-item:hover .dx-num { opacity: 1; }
.dx-main { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.dx-eyebrow {
  font-size: .68rem; font-weight: var(--weight-bold);
  text-transform: uppercase; letter-spacing: .09em; color: var(--tone, var(--accent-text));
}
.dx-title { font-size: var(--text-base); font-weight: var(--weight-bold); line-height: var(--leading-snug); }
.dx-text {
  color: var(--muted); font-size: var(--text-sm); line-height: var(--leading-snug);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.dx-go {
  color: var(--tone, var(--primary-fg)); font-size: 1.1rem; font-weight: var(--weight-bold);
  transform: translateX(-3px); opacity: .5;
  transition: transform .3s var(--ease-spring-gentle), opacity .3s var(--ease-out);
}
.dx-item:hover .dx-go { transform: translateX(2px); opacity: 1; }
.dx-event   { --tone: #d1503f; }
.dx-season  { --tone: var(--primary-fg); }
.dx-planner { --tone: #3f7fb4; }
.dx-food    { --tone: var(--accent-text, #c0872e); }
.dx-map     { --tone: #4a78aa; }
@media (max-width: 860px) {
  .decision-shell { grid-template-columns: 1fr; }
  .decision-copy { max-width: 680px; }
}
@media (max-width: 560px) {
  .decision-index { grid-template-columns: 1fr; column-gap: 0; }
}

/* ═══════════════════════════════════════════════════
   CATEGORY QUICK-NAV GRID
   ═══════════════════════════════════════════════════ */
.cat-grid {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--space-3);
}
@media (min-width: 769px) { .cat-grid { grid-template-columns: repeat(6, 1fr); } }
/* ── Klook/GYG-style image tiles: each category shows its own logical photo,
   editorial label bottom-left over a scrim; small corner emoji as a wayfinding accent. ── */
.cat-tile {
  display: flex; flex-direction: column; justify-content: flex-end; align-items: flex-start; gap: 1px;
  min-height: clamp(8.5rem, 7.5rem + 7vw, 12rem);
  padding: var(--space-3);
  color: #fff; text-decoration: none;
  background-color: var(--card);
  background-image: linear-gradient(to top, rgba(8,9,12,.86) 0%, rgba(8,9,12,.34) 46%, rgba(8,9,12,.05) 100%), var(--tile-img);
  background-size: cover; background-position: center;
  border-radius: var(--radius);
  position: relative; overflow: hidden;
  transition: transform .35s var(--ease-spring-gentle), box-shadow .3s var(--ease-out);
}
.cat-tile:hover { transform: translateY(-3px); box-shadow: var(--shadow-md); }
.cat-tile:active { transform: scale(.97); transition-duration: .1s; }
.cat-tile:focus-visible { outline: 2px solid var(--text-on-dark, #fff); outline-offset: 3px; }
.cat-emoji { position: absolute; top: var(--space-2); left: var(--space-3); font-size: 1.2rem; line-height: 1; filter: drop-shadow(0 1px 4px rgba(0,0,0,.65)); }
.cat-label { color: #fff; font-size: var(--text-base); font-weight: 700; text-align: left; text-shadow: 0 1px 8px rgba(0,0,0,.7); }
.cat-hint {
  min-height: 0; color: rgba(255,255,255,.82); font-size: var(--text-xs); line-height: var(--leading-snug);
  text-align: left; text-shadow: 0 1px 5px rgba(0,0,0,.65);
  display: -webkit-box; -webkit-line-clamp: 1; -webkit-box-orient: vertical; overflow: hidden;
}
.cat-count { font-size: var(--text-xs); color: rgba(255,255,255,.8); text-shadow: 0 1px 4px rgba(0,0,0,.6); font-variant-numeric: tabular-nums; margin-top: 1px; }
.dark .cat-tile { background-color: var(--card); }
/* Per-category tile image via static class (NOT inline :style — that custom-prop caused an
   SSR hydration mismatch that broke the scroll-reveal observer). */
.ct-du-lich { --tile-img: url(/img/cat-du-lich.webp); }
.ct-am-thuc { --tile-img: url(/img/cat-am-thuc.webp); }
.ct-ocop    { --tile-img: url(/img/cat-ocop.webp); }
.ct-le-hoi  { --tile-img: url(/img/cat-le-hoi.webp); }
.ct-luu-tru { --tile-img: url(/img/cat-luu-tru.webp); }
.ct-ban-do  { --tile-img: url(/img/cat-ban-do.webp); }

/* ═══════════════════════════════════════════════════
   SECTION RHYTHM
   ═══════════════════════════════════════════════════ */
.home .section-head h2 {
  font-family: var(--font-editorial);
  font-size: var(--text-2xl); font-weight: 600;
  letter-spacing: -.01em; line-height: var(--leading-tight);
  position: relative; padding-left: var(--space-4);
}
.home .section-head h2::before {
  content: ""; position: absolute; left: 0; top: 50%; transform: translateY(-50%);
  width: 4px; height: 1.05em; border-radius: var(--radius-full);
  background: linear-gradient(180deg, var(--accent) 0%, var(--primary) 100%);
}
.home .section-head .sh-text { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
.home .sh-sub { padding-left: var(--space-4); margin: 0; font-size: var(--text-sm); font-weight: var(--weight-normal); color: var(--muted); line-height: var(--leading-snug); max-width: 62ch; }

.home .block + .block { position: relative; }
.home .block + .block::before {
  content: ""; position: absolute; top: 0; left: 50%; transform: translateX(-50%);
  width: min(100%, var(--maxw)); height: 1px;
  background: linear-gradient(90deg, transparent, var(--line) 22%, var(--line) 78%, transparent); opacity: .7;
}
.home .block { padding-top: var(--space-16); padding-bottom: var(--space-8); content-visibility: auto; contain-intrinsic-size: auto 480px; }
.home .block-compact { padding-top: var(--space-8); padding-bottom: var(--space-8); }
.home .block.band { background: var(--bg-warm); background-image: var(--season-hero-gradient); border-radius: var(--radius-xl); padding-inline: var(--space-6); }
.home .block.band + .block::before, .home .block + .block.band::before { display: none; }
.dark .home .block.band { background-color: var(--bg-alt); }
.block-cta { text-align: center; margin-top: var(--space-4); }

/* ═══════════════════════════════════════════════════
   SCROLL ROW
   ═══════════════════════════════════════════════════ */
.scroll-row {
  display: grid; gap: var(--space-5);
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
}
@media (min-width: 769px) and (max-width: 1024px) { .scroll-row { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 768px) {
  .scroll-row {
    display: flex; gap: var(--space-3); overflow-x: auto;
    scroll-snap-type: x mandatory; overscroll-behavior-x: contain;
    -webkit-overflow-scrolling: touch; padding-bottom: var(--space-2);
    padding-inline: var(--space-4); margin-inline: calc(-1 * var(--space-4));
    scrollbar-width: none;
    mask-image: linear-gradient(to right, transparent, #000 var(--space-4), #000 88%, transparent);
    -webkit-mask-image: linear-gradient(to right, transparent, #000 var(--space-4), #000 88%, transparent);
  }
  .scroll-row::-webkit-scrollbar { display: none; }
  .scroll-row:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; border-radius: var(--radius-md); }
  .scroll-row:hover, .scroll-row:focus-within { mask-image: linear-gradient(to right, transparent, #000 var(--space-4), #000 100%); -webkit-mask-image: linear-gradient(to right, transparent, #000 var(--space-4), #000 100%); }
  .scroll-row > * { flex: 0 0 280px; scroll-snap-align: start; }
}

/* ═══════════════════════════════════════════════════
   "ĐANG DIỄN RA" — events + seasonal
   ═══════════════════════════════════════════════════ */
.happening-feature { display: grid; grid-template-columns: 1.5fr 1fr; gap: var(--space-4); align-items: stretch; }
@media (max-width: 760px) { .happening-feature { grid-template-columns: 1fr; } }
.event-hero {
  display: flex; align-items: center; gap: var(--space-5);
  padding: var(--space-6); border-radius: var(--radius-lg);
  background: linear-gradient(135deg, rgba(var(--primary-rgb), .96) 0%, rgba(var(--accent-rgb), .88) 100%);
  color: var(--text-on-dark, #fff); text-decoration: none; box-shadow: var(--shadow-md);
  transition: transform .35s var(--ease-spring-gentle), box-shadow .35s var(--ease-out-expo);
  position: relative; overflow: hidden; isolation: isolate;
}
.event-hero::before {
  content: ""; position: absolute; top: 0; bottom: 0; left: -60%; width: 45%; z-index: -1;
  background: linear-gradient(105deg, transparent 0%, rgba(255,255,255,.16) 50%, transparent 100%);
  transform: translateX(0) skewX(-14deg);
  animation: event-sheen 6.5s var(--ease-in-out) 1.2s infinite;
  will-change: transform;
}
@keyframes event-sheen {
  0%   { transform: translateX(0) skewX(-14deg); }
  55%  { transform: translateX(420%) skewX(-14deg); }
  100% { transform: translateX(420%) skewX(-14deg); }
}
.event-hero:hover { transform: translateY(-3px); box-shadow: var(--shadow-lg); }
.event-hero:active { transform: scale(.99); transition-duration: .1s; }
.event-hero:focus-visible { outline: 2px solid var(--text-on-dark, #fff); outline-offset: 3px; }
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
.event-mini { display: flex; align-items: center; gap: var(--space-3); padding: var(--space-2) var(--space-3); min-height: 48px; background: var(--card); border: .5px solid var(--line); border-radius: var(--radius); text-decoration: none; color: var(--ink); transition: border-color .25s var(--ease-out), transform .25s var(--ease-spring-gentle); }
.event-mini:hover { border-color: var(--primary-fg); transform: translateX(2px); }
.ec-date-sm { min-width: 46px; padding: var(--space-2); }
.ec-date { display: flex; flex-direction: column; align-items: center; justify-content: center; min-width: 52px; padding: var(--space-2); background: var(--primary); border-radius: var(--radius-sm); color: var(--text-on-dark, #fff); }
.ec-day { font-size: var(--text-xl); font-weight: var(--weight-extrabold); line-height: 1; font-variant-numeric: tabular-nums; }
.ec-month { font-size: var(--text-xs); font-weight: var(--weight-semibold); opacity: .9; }
.ec-info { display: flex; flex-direction: column; gap: var(--space-1); min-width: 0; }
.ec-info h3 { margin: 0; font-size: var(--text-base); font-weight: var(--weight-semibold); letter-spacing: var(--tracking-tight); display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.event-mini .ec-info { gap: 2px; }
.event-mini h3 { margin: 0; font-size: var(--text-sm); font-weight: var(--weight-semibold); line-height: var(--leading-snug); display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.ec-countdown {
  display: inline-flex; align-items: center; gap: var(--space-1);
  font-size: var(--text-xs); font-weight: var(--weight-bold); color: var(--amber-700);
  background: rgba(154, 109, 30, .08); padding: var(--space-1) var(--space-2); border-radius: var(--radius-full);
}
.ec-today { color: var(--error); }
.ec-live-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--error); animation: pulse-dot 1.5s var(--ease-in-out) infinite; }
@keyframes pulse-dot { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: .4; transform: scale(.7); } }
.happening-label { font-size: var(--text-sm); font-weight: var(--weight-semibold); color: var(--primary-fg); margin: var(--space-4) 0 var(--space-2); }
.dark .happening-label { color: var(--primary-fg-strong); }
.happening-section { margin-top: var(--space-1); }

/* ═══════════════════════════════════════════════════
   TINH HOA — spotlight magazine + quán ngon rating
   ═══════════════════════════════════════════════════ */
.tinh-hoa { display: flex; flex-direction: column; gap: var(--space-8); }

/* Spotlight */
.spotlight {
  display: grid; grid-template-columns: 1.05fr 1fr; gap: var(--space-6); align-items: stretch;
  background: var(--card); border: 1px solid var(--border); border-radius: var(--radius-xl);
  overflow: hidden; box-shadow: var(--shadow-sm); contain: layout style paint;
}
@media (max-width: 760px) { .spotlight { grid-template-columns: 1fr; } }
.spot-visual {
  position: relative; min-height: 300px;
  background-size: cover; background-position: center;
  display: block; overflow: hidden; text-decoration: none; isolation: isolate;
  transition: transform .6s var(--ease-out-expo);
}
.spotlight:hover .spot-visual { transform: scale(1.03); }
@media (max-width: 760px) { .spot-visual { min-height: 200px; } }
.spot-region {
  position: absolute; top: var(--space-4); left: var(--space-4);
  padding: var(--space-1) var(--space-3); background: rgba(0,0,0,.5);
  color: var(--text-on-dark, #fff); border-radius: var(--radius-full);
  font-size: var(--text-xs); font-weight: var(--weight-semibold);
  backdrop-filter: blur(4px); -webkit-backdrop-filter: blur(4px);
}
.spot-body {
  padding: var(--space-8) var(--space-8) var(--space-8) 0;
  display: flex; flex-direction: column; justify-content: center; gap: var(--space-3); min-width: 0;
}
@media (max-width: 760px) { .spot-body { padding: var(--space-5); } }
.spot-kicker { font-size: var(--text-xs); font-weight: var(--weight-bold); text-transform: uppercase; letter-spacing: .05em; color: var(--primary-fg-strong); }
.spot-body .spot-name { margin: 0; font-size: clamp(1.5rem, 3.2vw, 2.1rem); line-height: var(--leading-snug); letter-spacing: -.01em; }
.spot-sum { margin: 0; color: var(--text-muted); line-height: var(--leading-relaxed); display: -webkit-box; -webkit-line-clamp: 4; -webkit-box-orient: vertical; overflow: hidden; }
.spot-cta { align-self: flex-start; margin-top: var(--space-2); }

/* Top dishes */
.dishes-heading { font-size: var(--text-lg); font-weight: var(--weight-bold); margin: 0 0 var(--space-3); }
.dishes-list { display: flex; flex-direction: column; gap: var(--space-2); }
.dish-item {
  display: flex; align-items: center; gap: var(--space-3);
  padding: var(--space-3) var(--space-4); min-height: 48px;
  background: var(--card); border: .5px solid var(--line); border-radius: var(--radius);
  text-decoration: none; color: var(--ink);
  transition: border-color .25s var(--ease-out), transform .25s var(--ease-spring-gentle), box-shadow .25s var(--ease-out);
}
.dish-item:hover { border-color: var(--primary-fg); transform: translateX(4px); box-shadow: var(--shadow-sm); }
.dish-item:active { transform: translateX(1px) scale(.98); transition-duration: .1s; }
.dish-item:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
.dish-rating-badge {
  display: flex; align-items: center; gap: 3px; flex-shrink: 0;
  padding: var(--space-1) var(--space-2);
  background: var(--accent-container);
  border-radius: var(--radius-sm); font-weight: var(--weight-extrabold);
}
.dish-star { color: var(--accent); font-size: var(--text-sm); }
.dish-score { color: var(--on-accent-container); font-size: var(--text-sm); font-variant-numeric: tabular-nums; }
.dish-info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 1px; }
.dish-name { font-size: var(--text-sm); font-weight: var(--weight-semibold); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.dish-reviews { font-size: var(--text-xs); color: var(--muted); }
.dish-arrow { color: var(--muted); font-size: var(--text-sm); flex-shrink: 0; transition: color .2s; }
.dish-item:hover .dish-arrow { color: var(--primary-fg); }
.dark .dish-item { background: var(--card); border-color: var(--line); }
.dark .dish-item:hover { border-color: rgba(255,255,255,.1); }

/* ═══════════════════════════════════════════════════
   COMMUNITY — compact with trending tags
   ═══════════════════════════════════════════════════ */
.community-stats-line { font-size: var(--text-sm); color: var(--muted); margin: 0 0 var(--space-3); }
.community-stats-line strong { color: var(--primary-fg); font-weight: var(--weight-bold); }

.trending-tags { display: flex; align-items: center; flex-wrap: wrap; gap: var(--space-2); margin: 0 0 var(--space-3); }
.tt-label { font-size: var(--text-sm); font-weight: var(--weight-semibold); color: var(--ink); }
.tt-chip {
  display: inline-flex; align-items: center;
  padding: var(--space-2) var(--space-3);
  background: var(--bg-alt); border: .5px solid var(--line); border-radius: var(--radius-full);
  font-size: var(--text-xs); font-weight: var(--weight-semibold); color: var(--primary-fg);
  text-decoration: none; min-height: 44px;
  transition: background .2s var(--ease-out), border-color .2s var(--ease-out);
}
.tt-chip:hover { background: var(--bg-warm); border-color: var(--primary-fg); }
.dark .tt-chip { background: rgba(255,255,255,.06); border-color: rgba(255,255,255,.1); }
.dark .tt-chip:hover { background: rgba(255,255,255,.1); }

.home-leaders { display: flex; align-items: center; flex-wrap: wrap; gap: var(--space-2); margin: 0 0 var(--space-4); }
.hl-label { font-size: var(--text-sm); font-weight: var(--weight-semibold); color: var(--ink); }
.hl-chip { display: inline-flex; align-items: center; gap: var(--space-1); padding: var(--space-1) var(--space-3) var(--space-1) var(--space-1); min-height: 44px; background: var(--bg-alt); border: .5px solid var(--line); border-radius: var(--radius-full); text-decoration: none; color: var(--ink); transition: border-color .25s var(--ease-out); }
.hl-chip:hover { border-color: var(--primary-fg); }
.hl-rank { width: 18px; height: 18px; display: inline-flex; align-items: center; justify-content: center; font-size: var(--text-xs); font-weight: var(--weight-bold); color: var(--muted); }
.hl-rank-1 { --rank-color: #d4a017; color: var(--rank-color); } .hl-rank-2 { --rank-color: #8a8d91; color: var(--rank-color); } .hl-rank-3 { --rank-color: #b07b4f; color: var(--rank-color); }
.dark .hl-rank-1 { --rank-color: #ffd54f; } .dark .hl-rank-2 { --rank-color: #b0b3b8; } .dark .hl-rank-3 { --rank-color: #d4a574; }
.hl-avatar { width: 24px; height: 24px; display: inline-flex; align-items: center; justify-content: center; border-radius: 50%; background: var(--primary); color: var(--text-on-dark, #fff); font-size: var(--text-2xs); font-weight: var(--weight-semibold); }
.hl-name { font-size: var(--text-sm); font-weight: var(--weight-medium); }
.hl-more { font-size: var(--text-sm); color: var(--primary-fg); text-decoration: none; font-weight: var(--weight-semibold); }
.hl-more:hover { text-decoration: underline; }

.cm-card { display: flex; flex-direction: column; background: var(--card); border: .5px solid var(--line); border-radius: var(--radius); overflow: hidden; box-shadow: var(--shadow-xs); text-decoration: none; color: var(--ink); transition: transform .35s var(--ease-spring-gentle), box-shadow .35s var(--ease-out-expo), border-color .3s var(--ease-out); }
.cm-card:hover { transform: translateY(-3px); box-shadow: var(--shadow-md); border-color: var(--border); }
.cm-card:active { transform: scale(.98); transition-duration: .1s; }
.cm-card:focus-visible { outline: 2px solid var(--primary); outline-offset: 3px; }
.cm-img { aspect-ratio: 16 / 9; overflow: hidden; background: var(--bg-alt); }
.cm-img img { width: 100%; height: 100%; object-fit: cover; transition: transform .4s var(--ease-out); }
.cm-card:hover .cm-img img { transform: scale(var(--img-hover-scale)); }
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

.community-join {
  display: flex; align-items: center; gap: var(--space-4);
  margin-top: var(--space-4); padding: var(--space-4) var(--space-5);
  background: var(--bg-warm); border-radius: var(--radius);
  font-size: var(--text-sm); color: var(--muted);
}
.community-join .btn { flex-shrink: 0; }
@media (max-width: 480px) { .community-join { flex-direction: column; text-align: center; gap: var(--space-3); } }
.dark .community-join { background: var(--bg-alt); }

/* ═══════════════════════════════════════════════════
   CHATBOT CTA
   ═══════════════════════════════════════════════════ */
.chatbot-cta {
  display: flex; align-items: center; gap: var(--space-4);
  padding: var(--space-5) var(--space-6);
  background: linear-gradient(135deg, var(--bg-alt) 0%, var(--bg-warm) 100%);
  border: .5px solid var(--line); border-radius: var(--radius);
  transition: border-color .3s var(--ease-out), box-shadow .35s var(--ease-out-expo), transform .35s var(--ease-spring-gentle);
}
.chatbot-cta:hover { border-color: var(--border); box-shadow: var(--shadow-md); transform: translateY(-2px); }
.chatbot-cta-inner { flex: 1; }
.chatbot-cta-text { margin: 0; font-size: var(--text-base); font-weight: var(--weight-semibold); color: var(--ink); }
.chatbot-cta-sub { margin: var(--space-1) 0 0; font-size: var(--text-sm); color: var(--muted); line-height: var(--leading-relaxed); }
.chatbot-cta-btn {
  padding: var(--space-3) var(--space-6); background: var(--primary);
  color: var(--text-on-dark, #fff); border: none; border-radius: var(--radius-full);
  font-size: var(--text-sm); font-weight: var(--weight-semibold); cursor: pointer;
  min-height: 44px; white-space: nowrap;
  transition: background .3s var(--ease-out), transform .35s var(--ease-spring-gentle), box-shadow .3s var(--ease-out);
}
.chatbot-cta-btn:hover { background: var(--primary-dark, var(--primary)); transform: translateY(-1px); box-shadow: var(--shadow-sm); }
.chatbot-cta-btn:active { transform: scale(.95); transition-duration: .1s; }
.chatbot-cta-btn:focus-visible { outline: 2px solid var(--primary); outline-offset: 3px; }
@media (max-width: 480px) {
  .chatbot-cta { flex-direction: column; text-align: center; gap: var(--space-3); }
  .chatbot-cta-btn { width: 100%; }
}

/* ═══════════════════════════════════════════════════
   SKELETON + MISC
   ═══════════════════════════════════════════════════ */
.sk-heading { height: 1.4rem; width: 180px; border-radius: var(--radius-sm); background: linear-gradient(90deg, var(--bg-alt) 25%, var(--line) 37%, var(--bg-alt) 63%); background-size: 400% 100%; animation: skShimmer 1.4s var(--ease-out) infinite; }
@keyframes skShimmer { 0% { background-position: 100% 0; } 100% { background-position: -100% 0; } }
.home .grid .card, .home .scroll-row .card { transition: transform .18s var(--ease-out), box-shadow .25s var(--ease-out); }

/* ═══════════════════════════════════════════════════
   DARK MODE
   ═══════════════════════════════════════════════════ */
.dark .home .hero-kenburns {
  background-image:
    linear-gradient(105deg, rgba(26,26,26,.60) 0%, rgba(26,26,26,.30) 46%, rgba(26,26,26,.05) 100%),
    url('/img/hero.webp');
}
@media (max-width: 640px) {
  .dark .home .hero-kenburns {
    background-image:
      linear-gradient(105deg, rgba(26,26,26,.60) 0%, rgba(26,26,26,.30) 46%, rgba(26,26,26,.05) 100%),
      url('/img/hero-mobile.webp');
  }
}
.dark .home .hero-scrim {
  background:
    radial-gradient(120% 95% at 88% 6%, rgba(var(--accent-rgb),.12) 0%, rgba(var(--accent-rgb),.03) 34%, transparent 60%),
    radial-gradient(90% 70% at 6% 100%, rgba(var(--primary-rgb),.12) 0%, transparent 58%),
    linear-gradient(to top, rgba(0,0,0,.30) 0%, rgba(0,0,0,.04) 28%, transparent 50%);
}
.dark .home .hero-kicker { background: rgba(255,255,255,.12); border-color: rgba(255,255,255,.22); }
.dark .home .hero-search { background: rgba(255,255,255,.22); border-color: rgba(255,255,255,.38); }
.dark .home .hero-search input { background: var(--bg-warm); color: var(--ink); }
.dark .home .hero-search input::placeholder { color: rgba(255,255,255,.50); }
.dark .home .hero-search:focus-within { border-color: rgba(var(--accent-rgb), .7); }
.dark .home .section-head h2::before { background: linear-gradient(180deg, var(--accent) 0%, var(--primary-fg) 100%); }
.dark .home .block + .block::before { background: linear-gradient(90deg, transparent, var(--line) 22%, var(--line) 78%, transparent); opacity: .6; }
.dark .event-card { background: var(--surface-container); border-color: rgba(255,255,255,.12); }
.dark .ec-countdown { color: var(--accent-text, #e0b366); }
.dark .ec-today { color: var(--secondary-fg, #f0846f); }
.dark .event-card:hover { border-color: rgba(255,255,255,.2); }
.dark .chatbot-cta { background: linear-gradient(135deg, var(--surface-container) 0%, rgba(255,255,255,.06) 100%); border-color: rgba(255,255,255,.12); }
.dark .chatbot-cta:hover { border-color: rgba(255,255,255,.2); }
.dark .hero-pill { background: rgba(255,255,255,.24); border-color: rgba(255,255,255,.40); }
.dark .hero-stat-num { color: var(--ink); }
.dark .spot-visual::before { background: radial-gradient(46% 46% at 34% 30%, rgba(255,255,255,.14) 0%, transparent 68%); }

/* ═══════════════════════════════════════════════════
   REDUCED TRANSPARENCY / MOTION
   ═══════════════════════════════════════════════════ */
@media (prefers-reduced-transparency: reduce) {
  .hero-pill { backdrop-filter: none; background: rgba(255,255,255,.3); }
  .home .hero-kicker { backdrop-filter: none; -webkit-backdrop-filter: none; background: rgba(0,0,0,.4); }
  .home .hero-search { backdrop-filter: none; -webkit-backdrop-filter: none; background: rgba(0,0,0,.35); }
}
@media (prefers-reduced-motion: reduce) {
  html.js .home .hero-enter > * { opacity: 1; transform: none; animation: none; }
  html.js .home .hero-enter h1::after { animation: none; transform: scaleX(1); opacity: 1; }
  .home .hero-kicker-dot { animation: none; }
  .home .hero-kenburns { animation: none; transform: none; }
  html.js .home .hero-feature { opacity: 1; transform: none; animation: none; }
  .hf-card:hover { transform: none; }
  .event-hero::before { animation: none; opacity: 0; }
  .hero-pill:hover, .hero-pill:active { transform: none; }
  .event-hero:hover, .event-mini:hover { transform: none; }
  .cm-card:hover, .cm-card:active { transform: none; }
  .cm-card:hover .cm-img img { transform: none; }
  .chatbot-cta:hover { transform: none; }
  .chatbot-cta-btn:hover, .chatbot-cta-btn:active { transform: none; }
  .ec-live-dot { animation: none; }
  .sk-heading { animation: none; }
  .spotlight:hover .spot-visual { transform: none; }
  .dish-item:hover, .dish-item:active { transform: none; }
  .cat-tile:hover, .cat-tile:active { transform: none; }
}

/* Recently viewed cards — compact */
.card.card-mini { min-width: 160px; max-width: 200px; }
.card.card-mini .cover { aspect-ratio: 16/10; }
.card.card-mini h3 { font-size: .85rem; }
</style>
