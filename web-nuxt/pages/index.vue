<template>
  <div
    class="home"
    data-home-pilot="nocturne-b1"
    data-color-system="tri-region-v1"
    data-page-recipe="homepage"
    data-material-accent="clay"
  >
    <!-- 1. Hero — dynamic tagline + search + stats inline -->
    <section class="hero" aria-label="Giới thiệu" data-home-section="hero">
      <HeroIllustration />
      <div class="hero-scrim" aria-hidden="true"></div>
      <div class="hero-inner">
        <div class="hero-main hero-enter">
          <span class="hero-kicker" data-color-role="brand"><span class="hero-kicker-dot" aria-hidden="true"></span>{{ ss('homepage.hero_kicker', 'Du lịch & Đặc sản Vĩnh Long') }}</span>
          <h1>{{ seasonalTagline }}</h1>
          <p class="hero-sub">{{ ss('homepage.hero_subtitle', 'Tìm điểm đến, món ngon, lễ hội và lịch trình phù hợp cho chuyến đi Vĩnh Long hôm nay.') }}</p>
          <SearchAutocomplete
            class="hero-search hero-ac"
            data-color-role="action-primary"
            :placeholder="ss('homepage.search_placeholder', 'Tìm điểm đến, món ngon, lịch trình…')"
          />
          <NuxtLink to="/ban-do?near=1" class="hero-nearby"><IconLine name="pin" /> Tìm quanh tôi</NuxtLink>
        </div>
        <HomeFeatureDossier
          v-if="heroFeature"
          class="hero-feature"
          :eyebrow="heroFeatureReason"
          :title="heroFeature.name"
          :summary="heroFeature.summary"
          :region="hfRegion"
          :descriptor="heroFeatureDescriptor"
          :disclosure-id="heroFeatureDisclosureId"
          :detail-to="entityPath(heroFeature.id)"
          :planner-to="plannerAddPath(heroFeature.id)"
          :source-tier="resolveSourceTier(heroFeature?.quality?.source_tier)"
        />
      </div>
    </section>

    <!-- 1a-pre. Bản tin địa phương — lớp utility "giờ này đang thế nào", giữa hero (đây là
         đâu) và decision ledger (vậy làm gì). Tự ẩn khi chưa có dữ liệu đo. -->
    <HomeLocalBriefing data-home-section="briefing" />

    <!-- 1a. Bắt đầu hành trình — data-driven decision layer -->
    <HomeDecisionLedger :entries="homePresentation.decisionEntries" data-home-section="decisions" />

    <!-- ClientOnly: homeJourneyActions is personalized from client-only state (localStorage
         favorites/recently-viewed + isLoggedIn) → SSR (anon/empty) ≠ client → hydration
         mismatch that swapped nodes and broke the scroll-reveal observer. Client-only removes it. -->
    <ClientOnly>
      <JourneyActionRail
        v-if="!homePending && homeJourneyActions.length"
        :actions="homeJourneyActions"
        title="Tiếp tục hành trình của bạn"
        subtitle="Từ những gì bạn đã lưu và vừa xem."
        aria-label="Gợi ý hành trình trên trang chủ"
        compact
      />
    </ClientOnly>

    <!-- Degraded/empty fallback -->
    <section v-if="homeFailed" class="block reveal" data-home-section="recovery">
      <EmptyState :tone="homeError ? 'error' : 'empty'" title="Đang cập nhật nội dung" :message="homeError ? 'Mạng chậm một chút rồi. Bạn thử tải lại giúp tụi mình nhé!' : 'Tụi mình đang bổ sung điểm đến và đặc sản cho khu vực này. Quay lại sau nhé!'">
        <template #actions>
          <button v-if="homeError" type="button" class="btn btn-outline" @click="refreshHome()">Tải lại</button>
        </template>
      </EmptyState>
    </section>

    <!-- Skeleton -->
    <section v-if="homeLoadingSkeleton" class="block reveal" aria-hidden="true" data-home-section="recovery">
      <div class="section-head"><div class="sk-heading"></div></div>
      <SkeletonGrid :count="3" />
    </section>

    <!-- 1b. Khám phá nhanh — compact category grid (always visible for navigation) -->
    <HomeCategoryIndex
      v-if="!homePending"
      :groups="homePresentation.categoryGroups"
      data-home-section="categories"
    />

    <!-- 2. "Đang diễn ra" — upcoming events + seasonal -->
    <section v-if="upcomingEventList.length || seasonalList.length" class="block reveal" aria-label="Sự kiện và lễ hội" data-home-section="events-seasonal" data-material-accent="amber">
      <div class="section-head">
        <div class="sh-text">
          <h2>Đang <em class="ac-amber">diễn ra</em></h2>
          <p class="sh-sub">Sự kiện &amp; lễ hội sắp tới</p>
        </div>
        <NuxtLink class="see-all" to="/su-kien">Xem lịch →</NuxtLink>
      </div>

      <!-- declutter-3 T16 (B1-2): event-hero đã bỏ — event #1 sống ở decision card
           "Có lịch gần nhất"; 3 mini giữ nhịp lịch, không lặp -->
      <div v-if="upcomingEventList.length" class="happening-rest">
        <NuxtLink v-for="ev in upcomingEventList" :key="ev.id" :to="entityPath(ev.id)" class="event-mini">
          <div class="ec-date ec-date-sm" data-material-accent="amber">
            <span class="ec-day">{{ formatEventDay(ev) }}</span>
            <span class="ec-month">{{ formatEventMonth(ev) }}</span>
          </div>
          <div class="ec-info">
            <h3>{{ ev.name }}</h3>
            <span v-if="ev.days_until != null" class="ec-countdown" data-material-accent="amber" :class="{ 'ec-today': ev.days_until === 0 }">
              {{ ev.days_until === 0 ? 'Hôm nay!' : ev.days_until === 1 ? 'Ngày mai' : `Còn ${ev.days_until} ngày` }}
            </span>
          </div>
        </NuxtLink>
      </div>

      <div v-if="seasonalList.length" class="happening-section">
        <p class="happening-label" data-material-accent="amber"><IconLine name="flame" /> Đang vào mùa tháng {{ currentMonth }}</p>
        <div class="scroll-row" role="region" aria-label="Đặc sản theo mùa" tabindex="0">
          <EntityCard v-for="e in seasonalList" :key="e.id" :entity="e" :season-filter="String(currentMonth)" />
        </div>
      </div>
    </section>

    <!-- 2b. Feature — photo-led editorial block (Trải nghiệm miệt vườn) -->
    <section class="block reveal" aria-label="Trải nghiệm nổi bật" data-home-section="editorial-feature" data-material-accent="leaf">
      <EntityFeature
        :image="FEATURE_EXPERIENCE_IMAGE"
        v-bind="FEATURE_EXPERIENCE"
        accent="mở cửa"
        accent-tone="leaf"
        :thumbs="experienceThumbs"
        side="left"
        :priority="true"
      />
    </section>

    <!-- 3. Nổi bật — spotlight magazine + quán ngon rating -->
    <section v-if="spotlight || topDishes.length" class="block reveal band" aria-label="Nổi bật" data-home-section="spotlight-food">
      <div class="section-head">
        <div class="sh-text">
          <h2><em class="ac-river">Nổi bật</em></h2>
          <p class="sh-sub">Điểm đến &amp; quán ăn được cộng đồng yêu thích</p>
        </div>
      </div>

      <div class="home-spotlight-dossier">
        <div v-if="spotlight" class="spotlight">
          <NuxtLink
            :to="entityPath(spotlight.id)"
            class="spot-visual"
            :style="{ backgroundImage: spotBgCss }"
            :aria-label="`${spotlight.name} — ${spotDescriptor.alt}`"
            data-background-image
            :aria-describedby="spotDisclosureId"
          >
            <span v-if="spotRegion" class="spot-region">{{ spotRegion }}</span>
            <ImageDisclosure :id="spotDisclosureId" :descriptor="spotDescriptor" presentation="short" />
          </NuxtLink>
          <div class="spot-body">
            <span class="spot-kicker">{{ spotMeta?.label }} · Nổi bật</span>
            <h3 class="spot-name">{{ spotlight.name }}</h3>
            <p v-if="spotlight.summary" class="spot-sum">{{ spotlight.summary }}</p>
            <NuxtLink :to="entityPath(spotlight.id)" class="btn btn-primary spot-cta">Đọc câu chuyện {{ spotlight.name }} →</NuxtLink>
          </div>
        </div>

        <div v-if="topDishesList.length" class="home-food-ledger">
          <h3 class="dishes-heading">⭐ Quán ngon nổi bật</h3>
          <div class="dishes-list">
            <NuxtLink v-for="d in topDishesList" :key="d.id" :to="entityPath(d.id)" class="dish-item" data-material-accent="amber">
              <span v-if="Number(d.attributes?.rating) > 0" class="dish-rating-badge" data-material-accent="amber">
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
            <NuxtLink to="/kham-pha/am-thuc" class="btn btn-outline"><IconLine name="bowl" /> Còn nhiều quán ngon nữa</NuxtLink>
          </div>
        </div>
      </div>
    </section>

    <!-- 3a. Story spread — full-bleed signature moment -->
    <StorySpread
      data-home-section="story-spread"
      image="/img/spread/cu-lao-an-binh.webp"
      srcset="/img/spread/cu-lao-an-binh-640.webp 640w, /img/spread/cu-lao-an-binh-1024.webp 1024w, /img/spread/cu-lao-an-binh.webp 1536w"
      v-bind="SPREAD"
      image-alt="Cù lao An Bình giữa sông Cổ Chiên lúc hoàng hôn — vườn cây trái và dừa nước ven bờ, chiếc xuồng gỗ đậu sát mé sông."
    />

    <!-- declutter-3 T16 (B1-5): EntityFeature #2 OCOP đã bỏ — 1 feature-block/trang là đủ
         nhịp editorial; OCOP vẫn có trong chỉ mục địa phương. GIỮ feature #1
         (Trải nghiệm, LCP priority). -->

    <!-- declutter-3 T16 (B1-4): strip "Lịch trình gợi ý" đã bỏ — luồng lịch trình
         vẫn có trong chỉ mục tiện ích; itineraries GIỮ trong hasHomepageContent (degraded logic). -->

    <!-- 5. Từ cộng đồng — compact + trending tags; else always-populated editorial story.
         ClientOnly: communityData is lazy → renders null at prerender but resolves into the
         payload, so SSR (v-else story) ≠ client (v-if feed) = hydration mismatch. Rendering
         this volatile below-fold region client-only removes the mismatch at its source. -->
    <ClientOnly>
      <section
        v-if="communityPosts.length"
        class="block reveal"
        aria-label="Cộng đồng"
        data-image-surface="home-community"
        data-source-class="user-uploaded"
        data-entity-image-policy="no-image-invariant"
        data-home-section="community"
        data-material-accent="neutral"
      >
        <div class="section-head">
          <div class="sh-text">
            <h2>Từ <em class="ac-neutral">cộng đồng</em></h2>
            <p class="sh-sub">Trải nghiệm thật, mẹo hay từ người đi trước</p>
          </div>
          <NuxtLink class="see-all" to="/cong-dong">Đọc thêm chuyện người đi trước →</NuxtLink>
        </div>
        <template v-if="communityPosts.length">
          <p v-if="communityStats && (communityStats.posts || communityStats.reviews || communityStats.members)" class="community-stats-line">
            <strong>{{ communityStats.posts }}</strong> bài viết
            · <strong>{{ communityStats.reviews }}</strong> đánh giá
            · <strong>{{ communityStats.members }}</strong> thành viên
          </p>
          <div v-if="trendingTags.length" class="trending-tags">
            <span class="tt-label"><IconLine name="flame" /> Đang được nhắc:</span>
            <NuxtLink v-for="t in trendingTags" :key="t.tag" :to="`/cong-dong?tag=${encodeURIComponent(t.tag)}`" class="tt-chip">{{ t.tag }}</NuxtLink>
          </div>
          <!-- declutter-3 T16 (B1-6): dàn chip leaderboard → 1 link teaser (đích /bang-xep-hang) -->
          <p v-if="topMembers.length" class="home-leaders-teaser">
            <IconLine name="trophy" /> <NuxtLink to="/bang-xep-hang">Xem thành viên tích cực →</NuxtLink>
          </p>
          <div class="scroll-row" role="region" aria-label="Bài viết cộng đồng mới" tabindex="0">
            <NuxtLink v-for="p in communityPosts" :key="p.id" :to="postPath(p.id)" class="cm-card">
              <div class="cm-body">
                <div class="cm-author">
                  <span class="cm-avatar">{{ (p.display_name || '?').charAt(0).toUpperCase() }}</span>
                  <span class="cm-name">{{ p.display_name || 'Người dùng' }}</span>
                  <span v-if="p.post_type_label" class="cm-type">{{ p.post_type_label }}</span>
                </div>
                <p class="cm-content">{{ p.content }}</p>
                <div class="cm-meta">
                  <span v-if="p.likes"><IconLine name="heart" /> {{ p.likes }}</span>
                  <span v-if="p.comments_count || p.comment_count"><IconLine name="message" /> {{ p.comments_count || p.comment_count }}</span>
                  <span v-if="p.entity_name" class="cm-place">{{ p.entity_name }}</span>
                </div>
              </div>
            </NuxtLink>
          </div>
        </template>
        <div class="community-join">
          <span>Chia sẻ quán ngon, điểm đẹp, mẹo đi — góp một mảnh ghép cho bản đồ chung.</span>
          <NuxtLink to="/cong-dong" class="btn btn-outline"><IconLine name="message" /> Tham gia cộng đồng</NuxtLink>
        </div>
      </section>
      <section v-else class="block reveal" aria-label="Cộng đồng" data-home-section="community" data-material-accent="neutral">
        <EmptyState tone="empty" title="Cộng đồng đang khởi động"
          message="Chưa có bài viết nổi bật tuần này — bạn là người kể chuyện đầu tiên nhé!">
          <template #actions>
            <NuxtLink to="/cong-dong" class="btn btn-outline"><IconLine name="message" /> Tham gia cộng đồng</NuxtLink>
          </template>
        </EmptyState>
      </section>
    </ClientOnly>

    <!-- 6. Dành cho bạn — one merged, image-tolerant personalization strip (client-only) -->
    <ClientOnly>
      <!-- declutter-3 T16 (B1-7): chỉ hiện khi CÓ tín hiệu cá nhân thật (đã xem/đã lưu) —
           hết nhánh fallback "Gợi ý khám phá" đội lốt cá nhân hoá -->
      <section v-if="hasPersonalSignal && forYou.length" class="block block-compact reveal" aria-label="Dành cho bạn" data-home-section="for-you">
        <div class="section-head section-head-tight">
          <div class="sh-text">
            <h2 class="h2-tight">Dành cho <em class="ac-clay">bạn</em></h2>
            <p class="sh-sub">Nội dung bạn vừa xem, đã lưu và gợi ý theo bạn.</p>
          </div>
        </div>
        <div class="scroll-row for-you-row" role="region" aria-label="Dành cho bạn" tabindex="0">
          <NuxtLink v-for="item in forYou" :key="item.id" :to="item.to" class="fy-chip">
            <span class="fy-media">
              <span class="fy-thumb" :class="`cat-${getFavTypeMeta(item.type).cat}`">
                <NuxtImg v-if="item.imageDescriptor.url && isRemoteUrl(item.imageDescriptor.url)" :src="item.imageDescriptor.url" :alt="item.imageDescriptor.alt" :aria-describedby="item.disclosureId" loading="lazy" decoding="async" width="64" height="64" sizes="64px" @error="onImgError" />
                <img v-else-if="item.imageDescriptor.url" :src="item.imageDescriptor.url" :alt="item.imageDescriptor.alt" :aria-describedby="item.disclosureId" loading="lazy" decoding="async" width="64" height="64" @error="onImgError" />
                <span v-else class="fy-icon" v-html="genIcon(getFavTypeMeta(item.type).cat)" />
              </span>
              <ImageDisclosure class="fy-disclosure" :id="item.disclosureId" :descriptor="item.imageDescriptor" presentation="short" />
            </span>
            <span class="fy-body">
              <span class="fy-type">{{ getFavTypeMeta(item.type).label }}</span>
              <span class="fy-name">{{ item.name }}</span>
            </span>
          </NuxtLink>
        </div>
      </section>
    </ClientOnly>

  </div>
</template>

<script setup lang="ts">
import { TYPE_META, AREA_META } from '~/composables/useConstants'
import { generateCategoryIcon } from '~/composables/useCategoryPlaceholder'
import { useJourneyActions } from '~/composables/useJourneyActions'
import EntityFeature from '~/components/home/EntityFeature.vue'
import HomeCategoryIndex from '~/components/home/HomeCategoryIndex.vue'
import HomeDecisionLedger from '~/components/home/HomeDecisionLedger.vue'
import HomeFeatureDossier from '~/components/home/HomeFeatureDossier.vue'
import HomeLocalBriefing from '~/components/home/HomeLocalBriefing.vue'
import StorySpread from '~/components/home/StorySpread.vue'
import ImageDisclosure from '~/components/ImageDisclosure.vue'
import { describeEntityImages, describeEntityPlaceholder } from '~/utils/imageDescriptors'
import { createHomeNocturnePresentation } from '~/utils/homeNocturnePresentation'
import { resolveSourceTier } from '~/utils/regionalColor'
import { aiDisclosure } from '~/utils/aiDisclosure'
import type { ImageDescriptor } from '~/types/image'
import { useId } from 'vue'

useReveal()
const { get: ss } = useSiteSettings()

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
const FEATURE_EXPERIENCE_IMAGE = describeEntityImages({
  name: FEATURE_EXPERIENCE.title,
  image_descriptor: {
    url: '/img/features/trai-nghiem.webp',
    alt: 'Trải nghiệm miệt vườn — ảnh minh họa',
    source_class: 'ai-generated',
    source_kind: 'entity-editorial',
    disclosure_key: 'entity-ai',
    short_label: aiDisclosure.entity_ai.short_label,
    full_disclosure: aiDisclosure.entity_ai.full_disclosure,
    credit: null,
    width: null,
    height: null,
  } satisfies ImageDescriptor,
})[0]!

// Full-bleed signature moment (StorySpread). Discover-only CTA — never an order/price
// form, per project invariants.
const SPREAD = {
  kicker: 'Vĩnh Long',
  title: 'Nơi vườn chạm sông',
  subtitle: 'Nơi sông Cổ Chiên ôm 4 cù lao An Bình — gốm đỏ Mang Thít, bưởi Năm Roi, chợ nổi Trà Ôn họp lúc tinh mơ.',
  ctaText: 'Khám phá vùng đất',
  ctaTo: '/ban-do',
}

const { favorites } = useFavorites()

const { recentItems } = useRecentlyViewed()
const { enabled: ff } = useFeature()
const contextualRec = useContextualRecommendations({ context: 'home', limit: 8 })
// Only call the strip "Dành cho bạn" (For You) when there's a real personal signal; otherwise
// it's a popular fallback → relabel to "Gợi ý khám phá" so the heading doesn't over-promise.
const hasPersonalSignal = computed(() => recentItems.value.length > 0 || favorites.value.length > 0)
const forYou = computed(() => {
  const seen = new Set<string>()
  const out: { id: string; name: string; type: string; imageDescriptor: ImageDescriptor; disclosureId: string; to: string }[] = []
  const push = (source: any, type: any, to: string, allowLegacyImages: boolean) => {
    const id = source?.id
    const name = source?.name
    const key = String(id ?? '')
    if (!key || !name || seen.has(key)) return
    seen.add(key)
    const descriptor = (allowLegacyImages ? describeEntityImages(source)[0] : null)
      || (source?.image_descriptor ? describeEntityImages({ ...source, images: undefined, image: undefined })[0] : null)
      || describeEntityPlaceholder(source)
    const disclosureId = `for-you-${key.replace(/[^A-Za-z0-9_-]+/g, '-')}`
    out.push({ id: key, name, type: type || 'place', imageDescriptor: descriptor, disclosureId, to })
  }
  recentItems.value.forEach((rv: any) => push(rv, rv.type, entityPath(rv.id), false))
  favorites.value.forEach((fav: any) => push(fav, fav.type, savedItemPath(fav), false))
  if (ff('ai_recommendations')) contextualRec.items.value.forEach((e: any) => push(e, e.type, entityPath(e.id), true))
  return out.slice(0, 8)
})
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
    .filter((p: any) => (p.content || '').trim().length > 0)
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
// (declutter-1: computed `trending` đã bỏ — không section nào render nó; đếm nó trong
// hasHomepageContent chỉ làm trang "có nội dung" mà không hiển thị gì.)
const itineraries = computed(() => homeData.value?.itineraries || [])
const upcomingEvents = computed(() => homeData.value?.upcoming_events || [])
const seasonalTagline = computed(() => homeData.value?.seasonal_tagline || 'Khám phá Vĩnh Long theo cách của người bản địa')

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
const spotDescriptor = computed<ImageDescriptor>(() => {
  const entityDescriptor = spotlight.value ? describeEntityImages(spotlight.value)[0] : null
  if (entityDescriptor) return entityDescriptor
  const fallback = SPOT_CAT_PHOTO[spotMeta.value?.cat || ''] || '/img/cat-du-lich.webp'
  const fallbackDescriptor = describeEntityImages({
    id: `spotlight-${spotlight.value?.id || 'home'}`,
    name: spotlight.value?.name || 'Nổi bật',
    image_descriptor: {
      url: fallback,
      alt: `Ảnh minh họa danh mục ${spotMeta.value?.label || 'du lịch'} — ${spotlight.value?.name || 'Nổi bật'} chưa có ảnh riêng`,
      source_class: 'ai-generated',
      source_kind: 'entity-editorial',
      disclosure_key: 'entity-ai',
      short_label: aiDisclosure.entity_ai.short_label,
      full_disclosure: aiDisclosure.entity_ai.full_disclosure,
      credit: null,
      width: null,
      height: null,
    } satisfies ImageDescriptor,
  })[0]
  return fallbackDescriptor || describeEntityPlaceholder(spotlight.value || { name: 'Nổi bật' })
})
const spotPhoto = computed(() => spotDescriptor.value.url || '')
const spotBgCss = computed(() => spotlight.value
  ? `linear-gradient(to top, rgba(18,20,24,.55) 0%, rgba(18,20,24,.10) 45%, rgba(18,20,24,.32) 100%), url(${spotPhoto.value})`
  : '')
const spotDisclosureId = `home-spotlight-${useId().replace(/[^A-Za-z0-9_-]+/g, '-')}`
const spotRegion = computed(() => {
  const a = spotlight.value?.area || spotlight.value?.attributes?.area || spotlight.value?.attributes?.province
  if (!a) return ''
  const meta = (AREA_META as Record<string, { name: string }>)[String(a)]
  return meta ? meta.name : ''
})

const heroFeature = computed<any>(() => experiences.value.find((e: any) => e.id !== spotId.value) || spotlight.value || null)
const hfMeta = computed(() => heroFeature.value ? (TYPE_META[heroFeature.value.type] || { emoji: '📍', label: heroFeature.value.type, cat: 'place' }) : null)
const heroFeatureDescriptor = computed<ImageDescriptor>(() => {
  const descriptor = heroFeature.value ? describeEntityImages(heroFeature.value)[0] : null
  return descriptor || describeEntityPlaceholder(heroFeature.value || { name: 'Gợi ý nổi bật' })
})
const heroFeatureDisclosureId = `home-hero-feature-${useId().replace(/[^A-Za-z0-9_-]+/g, '-')}`
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

const areaCounts = computed<Record<string, number>>(() => homeData.value?.area_counts || {})

const experienceThumbs = computed(() =>
  experiences.value.filter((e: any) => e.id !== heroFeature.value?.id && e.id !== spotId.value).slice(0, 3))
const homePresentation = computed(() => createHomeNocturnePresentation({
  currentMonth: currentMonth.value,
  heroId: heroFeature.value?.id,
  spotlightId: spotlight.value?.id,
  upcomingEvents: upcomingEvents.value,
  seasonal: seasonal.value,
  topDishes: topDishes.value,
  itineraries: itineraries.value,
  categoryCounts: {
    experiences: experiences.value.length,
    dishes: topDishes.value.length,
    products: productsAll.value.length,
    events: upcomingEvents.value.length,
    areas: Object.keys(areaCounts.value).length,
  },
}))

const upcomingEventList = computed(() => homePresentation.value.upcomingEventEntries)
const seasonalList = computed(() => homePresentation.value.seasonalEntries)
const topDishesList = computed(() => homePresentation.value.dishEntries)

const homeJourneyActions = computed(() => homepageDecisionActions({
  isLoggedIn: isLoggedIn.value,
  savedCount: favorites.value.length,
  recentCount: recentItems.value.length,
  currentMonth: currentMonth.value,
}))

const hasHomepageContent = computed(() => !!(upcomingEvents.value.length || seasonal.value.length || itineraries.value.length || spotlight.value || topDishes.value.length))
const homeFailed = computed(() => !homePending.value && (!!homeError.value || (!!homeData.value && !hasHomepageContent.value)))
const homeLoadingSkeleton = computed(() => !hasHomepageContent.value && !homeFailed.value)
onMounted(() => { if (homeError.value || !hasHomepageContent.value) refreshHome() })

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

function formatRating(rating: number | string): string {
  const n = Number(rating)
  return n > 0 ? n.toFixed(1) : ''
}

function plannerAddPath(id: string | number) {
  return `/tao-lich-trinh?add=${encodeURIComponent(String(id))}`
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
html.js .home .hero-feature { opacity: 0; transform: translateY(16px); animation: hero-rise .7s var(--ease-out-expo) .5s forwards; }

.home .hero { background-image: none; }

/* Kicker */
/* Editorial dateline eyebrow — a hairline rule + wide-tracked caps, not a glass badge/pill */
.home .hero-kicker {
  display: inline-flex; align-items: center; gap: var(--space-3);
  margin-bottom: var(--space-5);
  color: rgba(var(--white-rgb),.88);
  font-family: var(--font-sans);
  font-size: var(--text-2xs); font-weight: 700;
  letter-spacing: .24em; text-transform: uppercase;
  text-shadow: 0 1px 3px rgba(var(--black-rgb),.45);
}
.home .hero-kicker::before {
  content: ""; flex: 0 0 auto;
  width: clamp(26px, 6vw, 54px); height: 1.5px;
  background: var(--color-brand);
}
.home .hero-kicker-dot { display: none; }
@keyframes hero-dot-pulse {
  0% { box-shadow: 0 0 0 0 rgba(var(--color-brand-rgb), .55); }
  70% { box-shadow: 0 0 0 7px rgba(var(--color-brand-rgb), 0); }
  100% { box-shadow: 0 0 0 0 rgba(var(--color-brand-rgb), 0); }
}

/* Display headline — editorial serif, cinematic scale */
/* Masthead headline — oversized editorial serif, tight measure so it wraps into a
   strong multi-line block (no decorative accent bar under it — that reads templated). */
.home .hero h1 {
  font-family: var(--font-editorial);
  font-weight: 600;
  /* Genuinely fluid: ~47px @375 (was ~66px — the old 2.6rem min never triggered because
     3.4rem+3.2vw stays ≥64px even at 320, so a 5-word tagline wrapped to 5 lines and pushed
     the search + feature card below the mobile fold). Now ~47px→86px, wraps to ~3 lines on
     phones, capped identically at 5.4rem on desktop. */
  font-size: clamp(2.75rem, 1.6rem + 5.6vw, 5.4rem);
  letter-spacing: -.02em; line-height: .98;
  text-shadow: 0 2px 28px rgba(var(--black-rgb),.42);
  max-width: 15ch;
  text-wrap: balance;
}
.home .hero-sub { font-family: var(--font-editorial); font-size: clamp(1.08rem, 1rem + .5vw, 1.3rem); line-height: 1.5; opacity: .95; max-width: 600px; margin: var(--space-4) 0 0; text-shadow: 0 1px 8px rgba(var(--black-rgb),.22); }
.dark .home .hero-sub { opacity: 1; font-weight: 400; }

/* Cinematic entrance */
html.js .home .hero-enter > * { opacity: 0; transform: translateY(16px); animation: hero-rise .7s var(--ease-out-expo) forwards; }
html.js .home .hero-enter > .hero-kicker { animation-delay: .05s; }
html.js .home .hero-enter > h1 { animation-delay: .14s; }
html.js .home .hero-enter > .hero-sub { animation-delay: .24s; }
html.js .home .hero-enter > .hero-search { animation-delay: .34s; }
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
  background: rgba(var(--white-rgb),.14);
  backdrop-filter: saturate(180%) blur(10px); -webkit-backdrop-filter: saturate(180%) blur(10px);
  border: .5px solid rgba(var(--white-rgb),.30);
  border-radius: calc(var(--radius-md) + var(--space-1));
  box-shadow: 0 8px 30px rgba(var(--black-rgb),.18), 0 2px 8px rgba(var(--black-rgb),.12);
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
  color: var(--color-action);
  opacity: .9;
  pointer-events: none;
  background: currentColor;
  -webkit-mask: url("data:image/svg+xml,%3Csvg viewBox='0 0 24 24' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath fill='none' stroke='black' stroke-width='2.35' stroke-linecap='round' stroke-linejoin='round' d='m21 21-4.34-4.34M10.8 18a7.2 7.2 0 1 1 0-14.4 7.2 7.2 0 0 1 0 14.4Z'/%3E%3C/svg%3E") center / contain no-repeat;
  mask: url("data:image/svg+xml,%3Csvg viewBox='0 0 24 24' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath fill='none' stroke='black' stroke-width='2.35' stroke-linecap='round' stroke-linejoin='round' d='m21 21-4.34-4.34M10.8 18a7.2 7.2 0 1 1 0-14.4 7.2 7.2 0 0 1 0 14.4Z'/%3E%3C/svg%3E") center / contain no-repeat;
}
.home .hero-search:focus-within {
  border-color: var(--color-focus);
  box-shadow: 0 12px 40px rgba(var(--black-rgb),.22), 0 0 0 4px color-mix(in srgb, var(--color-focus) 22%, transparent);
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
/* Single "near me" quick-entry under search (restores the intent lost when hero pills were cut). */
.home .hero-nearby {
  display: inline-flex; align-items: center; gap: .35em;
  margin-top: var(--space-3); min-height: 44px;
  color: rgba(var(--white-rgb),.92); font-size: var(--text-sm); font-weight: var(--weight-bold);
  text-decoration: none; text-shadow: 0 1px 6px rgba(var(--black-rgb),.35);
}
.home .hero-nearby:hover { text-decoration: underline; text-underline-offset: 3px; }
.home .hero-nearby:focus-visible { outline: 2px solid var(--color-focus); outline-offset: 3px; border-radius: 4px; }

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
  background: var(--color-brand);
}
/* Fraunces cất tiếng: chữ nghiêng trong tiêu đề dùng accent vật liệu theo ngữ cảnh,
   không gắn một theme riêng cho từng địa phương. */
.home .section-head h2 em, .home .spot-name em {
  font-family: var(--font-editorial); font-style: italic; font-weight: 600;
}
.home .ac-clay  { color: var(--color-material-clay); }
.home .ac-leaf  { color: var(--color-material-leaf); }
.home .ac-river { color: var(--color-material-river); }
.home .ac-amber { color: var(--color-material-amber); }
.home .ac-neutral { color: var(--color-material-neutral); }
.home .section-head .sh-text { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
.home .sh-sub { padding-left: var(--space-4); margin: 0; font-size: var(--text-sm); font-weight: var(--weight-normal); color: var(--muted); line-height: var(--leading-snug); max-width: 62ch; }
/* Tight variant — itineraries + personalization rows: smaller heading, less bottom margin,
   so these secondary sections read as a compact strip rather than a full-weight section. */
.home .section-head-tight { margin-bottom: var(--space-3); }
.home .section-head-tight h2.h2-tight { font-size: var(--text-lg); }

.home .block + .block { position: relative; }
.home .block + .block::before {
  content: ""; position: absolute; top: 0; left: 50%; transform: translateX(-50%);
  width: min(100%, var(--maxw)); height: 7px;
  background: linear-gradient(90deg, transparent, var(--color-material-clay) 26%, var(--color-material-clay) 74%, transparent) center/100% 1px no-repeat;
  opacity: .5;
}
.dark .home .block + .block::before { opacity: .62; }
/* Even vertical rhythm: every section shares the same symmetric padding as .block-compact
   (32/32) so the gap between ANY two sections is a uniform 64px — was 64px top / 32px bottom,
   giving 96px gaps between blocks vs 64px between compacts (the uneven, oversized whitespace). */
.home .block { padding-top: var(--space-8); padding-bottom: var(--space-8); content-visibility: auto; contain-intrinsic-size: auto 480px; }
.home .block-compact { padding-top: var(--space-8); padding-bottom: var(--space-8); }
.block-cta { text-align: center; margin-top: var(--space-4); }

/* ═══════════════════════════════════════════════════
   SCROLL ROW
   ═══════════════════════════════════════════════════ */
.home .scroll-row {
  display: grid; gap: var(--space-5);
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
}
@media (min-width: 769px) and (max-width: 1024px) { .home .scroll-row { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 768px) {
  .home .scroll-row {
    display: flex; gap: var(--space-3); overflow-x: auto;
    scroll-snap-type: x mandatory; overscroll-behavior-x: contain;
    -webkit-overflow-scrolling: touch; padding-bottom: var(--space-2);
    padding-inline: var(--space-4); margin-inline: calc(-1 * var(--space-4));
    scrollbar-width: none;
    mask-image: linear-gradient(to right, transparent, var(--color-mask-opaque) var(--space-4), var(--color-mask-opaque) 88%, transparent);
    -webkit-mask-image: linear-gradient(to right, transparent, var(--color-mask-opaque) var(--space-4), var(--color-mask-opaque) 88%, transparent);
  }
  .home .scroll-row::-webkit-scrollbar { display: none; }
  .home .scroll-row:focus-visible { outline: 2px solid var(--color-focus); outline-offset: 2px; border-radius: var(--radius-md); }
  .home .scroll-row:hover, .home .scroll-row:focus-within { mask-image: linear-gradient(to right, transparent, var(--color-mask-opaque) var(--space-4), var(--color-mask-opaque) 100%); -webkit-mask-image: linear-gradient(to right, transparent, var(--color-mask-opaque) var(--space-4), var(--color-mask-opaque) 100%); }
  .home .scroll-row > * { flex: 0 0 280px; scroll-snap-align: start; }
}

/* ═══════════════════════════════════════════════════
   "ĐANG DIỄN RA" — events + seasonal
   ═══════════════════════════════════════════════════ */
/* declutter-3 T16 (B1-2): event-hero + .eh-* đã xoá; minis đứng riêng thành hàng 3 cột */
.happening-rest { display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--space-2); }
@media (max-width: 760px) { .happening-rest { grid-template-columns: 1fr; } }
.event-mini { display: flex; align-items: center; gap: var(--space-3); padding: var(--space-2) var(--space-3); min-height: 48px; background: var(--card); border: .5px solid var(--line); border-radius: var(--radius); text-decoration: none; color: var(--ink); transition: border-color .25s var(--ease-out), transform .25s var(--ease-spring-gentle); }
.event-mini:hover { border-color: var(--color-action-border); transform: translateX(2px); }
.ec-date-sm { min-width: 46px; padding: var(--space-2); }
.ec-date { display: flex; flex-direction: column; align-items: center; justify-content: center; min-width: 52px; padding: var(--space-2); background: var(--home-color-amber-surface); border-radius: var(--radius-sm); color: var(--home-color-amber-text); }
.ec-day { font-size: var(--text-xl); font-weight: var(--weight-extrabold); line-height: 1; font-variant-numeric: tabular-nums; }
.ec-month { font-size: var(--text-xs); font-weight: var(--weight-semibold); opacity: 1; }
.ec-info { display: flex; flex-direction: column; gap: var(--space-1); min-width: 0; }
.ec-info h3 { margin: 0; font-size: var(--text-base); font-weight: var(--weight-semibold); letter-spacing: var(--tracking-tight); display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.event-mini .ec-info { gap: 2px; }
.event-mini h3 { margin: 0; font-size: var(--text-sm); font-weight: var(--weight-semibold); line-height: var(--leading-snug); display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.ec-countdown {
  display: inline-flex; align-items: center; gap: var(--space-1);
  font-size: var(--text-xs); font-weight: var(--weight-bold); color: var(--home-color-amber-text);
  background: var(--home-color-amber-surface); padding: var(--space-1) var(--space-2); border-radius: var(--radius-full);
}
.ec-today { color: var(--color-error); }
.happening-label { font-size: var(--text-sm); font-weight: var(--weight-semibold); color: var(--home-color-amber-text); margin: var(--space-4) 0 var(--space-2); }
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
  padding: var(--space-1) var(--space-3); background: rgba(var(--black-rgb),.5);
  color: var(--text-on-dark, var(--white)); border-radius: var(--radius-full);
  font-size: var(--text-xs); font-weight: var(--weight-semibold);
  backdrop-filter: blur(4px); -webkit-backdrop-filter: blur(4px);
}
.spot-body {
  padding: var(--space-8) var(--space-8) var(--space-8) 0;
  display: flex; flex-direction: column; justify-content: center; gap: var(--space-3); min-width: 0;
}
@media (max-width: 760px) { .spot-body { padding: var(--space-5); } }
.spot-kicker { font-size: var(--text-xs); font-weight: var(--weight-bold); text-transform: uppercase; letter-spacing: .05em; color: var(--color-brand); }
.spot-body .spot-name { margin: 0; font-size: clamp(1.5rem, 3.2vw, 2.1rem); line-height: var(--leading-snug); letter-spacing: -.01em; }
.spot-sum { margin: 0; color: var(--text-muted); line-height: var(--leading-relaxed); display: -webkit-box; -webkit-line-clamp: 4; -webkit-box-orient: vertical; overflow: hidden; }
.spot-cta { align-self: flex-start; margin-top: var(--space-2); }

/* Top dishes */
.dishes-heading { font-size: var(--text-lg); font-weight: var(--weight-bold); margin: 0 0 var(--space-3); }
/* Two columns from tablet up so the featured-eatery board fills the width instead of
   a lonely stack of full-width rows — matters most when the spotlight beside/above it is
   absent (no entity with a suitable image qualifies), which is the common live state. */
.dishes-list { display: grid; grid-template-columns: 1fr; gap: var(--space-2); }
@media (min-width: 640px) { .dishes-list { grid-template-columns: 1fr 1fr; } }
.dish-item {
  display: flex; align-items: center; gap: var(--space-3);
  padding: var(--space-3) var(--space-4); min-height: 48px;
  background: var(--card); border: .5px solid var(--line); border-radius: var(--radius);
  text-decoration: none; color: var(--ink);
  transition: border-color .25s var(--ease-out), transform .25s var(--ease-spring-gentle), box-shadow .25s var(--ease-out);
}
.dish-item:hover { border-color: var(--color-action-border); transform: translateX(4px); box-shadow: var(--shadow-sm); }
.dish-item:active { transform: translateX(1px) scale(.98); transition-duration: .1s; }
.dish-item:focus-visible { outline: 2px solid var(--color-focus); outline-offset: 2px; }
.dish-rating-badge {
  display: flex; align-items: center; gap: 3px; flex-shrink: 0;
  padding: var(--space-1) var(--space-2);
  background: color-mix(in srgb, var(--color-material-amber) 14%, transparent);
  border-radius: var(--radius-sm); font-weight: var(--weight-extrabold);
}
.dish-star { color: var(--color-material-amber); font-size: var(--text-sm); }
.dish-score { color: var(--color-text); font-size: var(--text-sm); font-variant-numeric: tabular-nums; }
.dish-info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 1px; }
.dish-name { font-size: var(--text-sm); font-weight: var(--weight-semibold); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.dish-reviews { font-size: var(--text-xs); color: var(--muted); }
.dish-arrow { color: var(--muted); font-size: var(--text-sm); flex-shrink: 0; transition: color .2s; }
.dish-item:hover .dish-arrow { color: var(--color-action); }
.dark .dish-item { background: var(--card); border-color: var(--line); }
.dark .dish-item:hover { border-color: rgba(var(--white-rgb),.1); }

/* ═══════════════════════════════════════════════════
   COMMUNITY — compact with trending tags
   ═══════════════════════════════════════════════════ */
.community-stats-line { font-size: var(--text-sm); color: var(--muted); margin: 0 0 var(--space-3); }
.community-stats-line strong { color: var(--color-source-community); font-weight: var(--weight-bold); }

.trending-tags { display: flex; align-items: center; flex-wrap: wrap; gap: var(--space-2); margin: 0 0 var(--space-3); }
.tt-label { font-size: var(--text-sm); font-weight: var(--weight-semibold); color: var(--ink); }
.tt-chip {
  display: inline-flex; align-items: center;
  padding: var(--space-2) var(--space-3);
  background: var(--bg-alt); border: .5px solid var(--line); border-radius: var(--radius-full);
  font-size: var(--text-xs); font-weight: var(--weight-semibold); color: var(--color-source-community);
  text-decoration: none; min-height: 44px;
  transition: background .2s var(--ease-out), border-color .2s var(--ease-out);
}
.tt-chip:hover { background: var(--bg-warm); border-color: var(--color-action-border); }
.dark .tt-chip { background: rgba(var(--white-rgb),.06); border-color: rgba(var(--white-rgb),.1); }
.dark .tt-chip:hover { background: rgba(var(--white-rgb),.1); }

/* declutter-3 T16 (B1-6): dàn chip leaderboard → 1 dòng teaser */
.home-leaders-teaser { display: flex; align-items: center; gap: var(--space-2); margin: 0 0 var(--space-4); font-size: var(--text-sm); font-weight: var(--weight-semibold); }
.home-leaders-teaser a { color: var(--color-action); text-decoration: none; }
.home-leaders-teaser a:hover { text-decoration: underline; }

.cm-card { display: flex; flex-direction: column; background: var(--card); border: .5px solid var(--line); border-radius: var(--radius); overflow: hidden; box-shadow: var(--shadow-xs); text-decoration: none; color: var(--ink); transition: transform .35s var(--ease-spring-gentle), box-shadow .35s var(--ease-out-expo), border-color .3s var(--ease-out); }
.cm-card:hover { transform: translateY(-3px); box-shadow: var(--shadow-md); border-color: var(--border); }
.cm-card:active { transform: scale(.98); transition-duration: .1s; }
.cm-card:focus-visible { outline: 2px solid var(--color-focus); outline-offset: 3px; }
.cm-body { display: flex; flex-direction: column; gap: var(--space-2); padding: var(--space-3) var(--space-4) var(--space-4); }
.cm-author { display: flex; align-items: center; gap: var(--space-2); min-width: 0; }
.cm-avatar { width: 26px; height: 26px; display: inline-flex; align-items: center; justify-content: center; border-radius: 50%; background: var(--color-source-community-surface); color: var(--color-source-community); font-size: var(--text-xs); font-weight: var(--weight-semibold); flex-shrink: 0; }
.cm-name { font-size: var(--text-sm); font-weight: var(--weight-semibold); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.cm-type { margin-left: auto; font-size: var(--text-xs); color: var(--muted); background: var(--bg-alt); padding: 1px 8px; border-radius: var(--radius-full); white-space: nowrap; flex-shrink: 0; }
.cm-content { margin: 0; font-size: var(--text-sm); color: var(--ink-700); line-height: var(--leading-snug); display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }
.cm-meta { display: flex; flex-wrap: wrap; gap: var(--space-3); font-size: var(--text-xs); color: var(--muted); }
.cm-place { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 60%; }
.dark .cm-card { background: var(--card); border-color: var(--line); }
.dark .cm-card:hover { border-color: rgba(var(--white-rgb),.1); }

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
   SKELETON + MISC
   ═══════════════════════════════════════════════════ */
.sk-heading { height: 1.4rem; width: 180px; border-radius: var(--radius-sm); background: linear-gradient(90deg, var(--bg-alt) 25%, var(--line) 37%, var(--bg-alt) 63%); background-size: 400% 100%; animation: skShimmer 1.4s var(--ease-out) infinite; }
@keyframes skShimmer { 0% { background-position: 100% 0; } 100% { background-position: -100% 0; } }
.home .grid .card, .home .scroll-row .card { transition: transform .18s var(--ease-out), box-shadow .25s var(--ease-out); }

/* ═══════════════════════════════════════════════════
   DARK MODE
   ═══════════════════════════════════════════════════ */
.dark .home .hero-scrim {
  background:
    radial-gradient(120% 95% at 88% 6%, color-mix(in srgb, var(--color-material-clay) 12%, transparent) 0%, color-mix(in srgb, var(--color-material-clay) 3%, transparent) 34%, transparent 60%),
    radial-gradient(90% 70% at 6% 100%, color-mix(in srgb, var(--color-material-clay) 12%, transparent) 0%, transparent 58%),
    linear-gradient(to top, rgba(var(--black-rgb),.30) 0%, rgba(var(--black-rgb),.04) 28%, transparent 50%);
}
.dark .home .hero-kicker { background: rgba(var(--white-rgb),.12); border-color: rgba(var(--white-rgb),.22); }
.dark .home .hero-search { background: rgba(var(--white-rgb),.22); border-color: rgba(var(--white-rgb),.38); }
.dark .home .hero-search input { background: var(--bg-warm); color: var(--ink); }
.dark .home .hero-search input::placeholder { color: rgba(var(--white-rgb),.50); }
.dark .home .hero-search:focus-within { border-color: var(--color-focus); }
.dark .home .section-head h2::before { background: var(--color-brand); }
.dark .home .block + .block::before { background: linear-gradient(90deg, transparent, var(--line) 22%, var(--line) 78%, transparent); opacity: .6; }
.dark .ec-today { color: var(--color-error); }

/* ═══════════════════════════════════════════════════
   REDUCED TRANSPARENCY / MOTION
   ═══════════════════════════════════════════════════ */
@media (prefers-reduced-transparency: reduce) {
  .home .hero-kicker { backdrop-filter: none; -webkit-backdrop-filter: none; background: rgba(var(--black-rgb),.4); }
  .home .hero-search { backdrop-filter: none; -webkit-backdrop-filter: none; background: rgba(var(--black-rgb),.35); }
}
@media (prefers-reduced-motion: reduce) {
  html.js .home .hero-enter > * { opacity: 1; transform: none; animation: none; }
  html.js .home .hero-enter h1::after { animation: none; transform: scaleX(1); opacity: 1; }
  .home .hero-kicker-dot { animation: none; }
  html.js .home .hero-feature { opacity: 1; transform: none; animation: none; }
  .event-mini:hover { transform: none; }
  .cm-card:hover, .cm-card:active { transform: none; }
  .sk-heading { animation: none; }
  .spotlight:hover .spot-visual { transform: none; }
  .dish-item:hover, .dish-item:active { transform: none; }
  .fy-chip:hover, .fy-chip:active { transform: none; }
}

/* ═══════════════════════════════════════════════════
   DÀNH CHO BẠN — merged personalization strip (chips)
   ═══════════════════════════════════════════════════ */
.for-you-row { align-items: stretch; }
.fy-chip {
  display: flex; align-items: center; gap: var(--space-3);
  flex: 0 0 auto; width: 15rem;
  padding: var(--space-3); min-height: 48px;
  background: var(--card); border: .5px solid var(--line); border-radius: var(--radius);
  text-decoration: none; color: var(--ink);
  transition: transform .25s var(--ease-spring-gentle), box-shadow .25s var(--ease-out), border-color .25s var(--ease-out);
}
.fy-chip:hover { transform: translateY(-3px); box-shadow: var(--shadow-sm); border-color: var(--border); }
.fy-chip:active { transform: translateY(-1px) scale(.98); transition-duration: .1s; }
.fy-chip:focus-visible { outline: 2px solid var(--color-focus); outline-offset: 2px; }
.fy-media { flex: 0 0 60px; width: 60px; display: flex; flex-direction: column; gap: 2px; align-self: stretch; }
.fy-thumb {
  flex: 0 0 60px; width: 60px; height: 60px;
  border-radius: var(--radius-sm); overflow: hidden;
  display: flex; align-items: center; justify-content: center;
  background: var(--bg-alt);
}
.fy-thumb img { width: 100%; height: 100%; object-fit: cover; }
.fy-disclosure { max-width: 60px; color: var(--muted); overflow-wrap: anywhere; }
.fy-disclosure :deep([data-short-label]) { font-size: .6rem; font-weight: var(--weight-semibold); line-height: 1.15; }
.fy-icon { width: 30px; height: 30px; opacity: .8; color: var(--muted); }
.fy-icon :deep(svg) { width: 100%; height: 100%; }
.fy-body { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.fy-type { font-size: var(--text-xs); font-weight: var(--weight-bold); text-transform: uppercase; letter-spacing: .04em; color: var(--color-material-clay); }
.fy-name { font-size: var(--text-sm); font-weight: var(--weight-bold); line-height: var(--leading-snug); color: var(--ink); display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.dark .fy-chip { background: var(--card); border-color: var(--line); }
.dark .fy-chip:hover { border-color: rgba(var(--white-rgb),.1); }
.dark .fy-thumb { background: rgba(var(--white-rgb),.06); }
</style>
<style src="~/assets/css/home-nocturne.css"></style>
