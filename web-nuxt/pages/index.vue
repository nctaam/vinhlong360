<template>
  <div
    class="home"
    data-home-pilot="nocturne-b1"
    data-color-system="tri-region-v1"
    data-page-recipe="homepage"
    data-material-accent="clay"
    :data-atmosphere="atmosphereMode"
  >
    <!-- One editorial thesis: useful action first, one disclosed media dossier second. -->
    <div class="sr-only" data-home-section="context" aria-label="Ngữ cảnh khám phá">Khu vực khám phá: Vĩnh Long</div>
    <section class="hero" aria-label="Giới thiệu" data-home-section="editorial-lead">
      <div class="hero-cinematic" aria-hidden="true">
        <img
          class="hero-cinematic__img"
          src="/img/spread/song-nuoc.webp"
          alt=""
          width="1920"
          height="1080"
          loading="eager"
          decoding="async"
          @error="onHeroImgError"
        >
        <span class="hero-cinematic__scrim" />
      </div>
      <div class="hero-inner">
        <div class="hero-main hero-enter">
          <span class="hero-kicker" data-color-role="brand"><span class="hero-kicker-dot" aria-hidden="true"></span>{{ ss('homepage.hero_kicker', 'Xứ sở Cù lao · Đất lành phù sa Vĩnh Long') }}</span>
          <h1>{{ seasonalTagline }}</h1>
          <p class="hero-sub">{{ ss('homepage.hero_subtitle', 'Hành trình di sản cù lao, làng gốm trăm năm và vị ngọt cây trái giữa đôi bờ Cổ Chiên.') }}</p>
          <div class="hero-cognitive-banner" role="region" aria-label="Khuyến nghị thời vụ lữ hành">
            <div class="hero-cognitive-chip hero-cognitive-chip--weather">
              <IconLine name="sun" class="hero-cognitive-chip__icon" aria-hidden="true" />
              <strong class="hero-cognitive-chip__title">Trời êm gió mát</strong>
              <span class="hero-cognitive-chip__sep" aria-hidden="true">·</span>
              <span class="hero-cognitive-chip__desc">28°C Nắng dịu, thuận đường sông nước</span>
            </div>
            <div class="hero-cognitive-chip hero-cognitive-chip--fruit">
              <IconLine name="leaf" class="hero-cognitive-chip__icon" aria-hidden="true" />
              <span class="hero-cognitive-chip__fruit-text">{{ seasonalFruitHighlight }}</span>
            </div>
          </div>
          <div class="hero-search-island" role="search" aria-label="Tìm kiếm lữ hành">
            <SearchAutocomplete
              class="hero-search hero-ac"
              data-color-role="action-primary"
              :placeholder="ss('homepage.search_placeholder', 'Tìm điểm đến, món ngon, lịch trình…')"
            />
            <div class="hero-search-island__footer">
              <NuxtLink to="/ban-do?near=1" class="hero-nearby"><IconLine name="pin" aria-hidden="true" /> Tìm quanh tôi</NuxtLink>
              <span class="hero-search-island__hint">
                <IconLine name="compass" class="hero-search-island__hint-icon" aria-hidden="true" />
                <span>Tìm cù lao, lò gạch cổ, quán ăn hay thức quà miệt vườn</span>
              </span>
            </div>
          </div>
          <div class="hero-terroir-chips" role="region" aria-label="Gợi ý thực địa Vĩnh Long">
            <span class="hero-terroir-chips__label">Rẽ lối lẹ:</span>
            <NuxtLink
              v-for="chip in HERO_TERROIR_CHIPS"
              :key="chip.label"
              :to="`/tim-kiem?q=${encodeURIComponent(chip.q)}`"
              class="hero-terroir-chip"
            >
              {{ chip.label }}
            </NuxtLink>
          </div>
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
          :source-tier="eventSourceTier(heroFeature)"
          :source-title="eventSourceTitle(heroFeature)"
          :source-url="eventSourceUrl(heroFeature)"
          :verified-at="eventVerifiedAt(heroFeature)"
          :coordinates="hfCoordinates"
          :map-to="hfMapTo"
        />
      </div>
    </section>

    <div class="home-river-divider" aria-hidden="true" />

    <HomeCuratedShowcase v-if="!homeFailed" />

    <div class="home-river-divider" aria-hidden="true" />

    <HomeCulinaryTrail v-if="!homeFailed" />

    <div class="home-river-divider" aria-hidden="true" />

    <HomeRiversideStays v-if="!homeFailed" />
    <HomeTravelPlanner v-if="!homeFailed" class="sr-only" />

    <div class="home-river-divider" aria-hidden="true" />

    <CatalogAeoPlaque
      data-home-section="aeo-plaque"
      data-home-aeo-plaque
      title="Cẩm nang du lịch theo mùa"
      kicker="Góc nhìn bản địa · Giải đáp nhanh AEO"
      accent="amber"
      icon="bulb"
      :entries="homeAeoEntries"
      cta-to="/theo-mua"
      cta-label="Khám phá lịch trình theo mùa"
    />
    <HomeFieldworkFaq class="sr-only" />

    <div class="home-quick-decisions sr-only" data-home-section="quick-decisions">
      <HomeDecisionLedger :entries="homePresentation.decisionEntries" class="sr-only" />
      <HomeCategoryIndex
        v-if="!homePending"
        :groups="homePresentation.categoryGroups"
        class="sr-only"
      />
    </div>

    <!-- Degraded/empty fallback -->
    <section v-if="homeFailed" class="block reveal" data-home-section="recovery">
      <EmptyState :tone="homeError ? 'error' : 'empty'" title="Bến đò chờ con nước · Đang cập nhật nội dung" :message="homeError ? 'Mạng chậm một chút rồi. Bạn thử tải lại giúp tụi mình nhé!' : 'Tụi mình đang bổ sung điểm đến và đặc sản cho khu vực này. Quay lại sau nhé!'">
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

    <div class="home-signals" data-home-section="signals">
      <HomeLocalBriefing class="sr-only" />

      <section v-if="upcomingEventList.length || seasonalList.length" class="block reveal sr-only" aria-label="Tín hiệu địa phương" data-material-accent="amber">
        <div class="section-head">
          <div class="sh-text">
            <h2>Tín hiệu địa phương <em class="editorial-italic-accent" aria-hidden="true">theo mùa</em></h2>
            <p class="sh-sub">Lịch hội hè sắp tới và mùa vụ cây trái đương rộ trên bến dưới thuyền.</p>
          </div>
          <NuxtLink class="see-all" to="/su-kien">Xem trọn lịch hội</NuxtLink>
        </div>

        <div class="home-signals__grid">
          <div v-if="upcomingEventList.length" class="happening-rest">
            <NuxtLink
              v-for="ev in upcomingEventList"
              :key="ev.id"
              :to="entityPath(ev.id)"
              class="event-mini"
              :class="{ 'is-signal-lead': ev.id === signalLeadId }"
              data-home-signal
            >
              <div class="ec-date ec-date-sm" data-material-accent="amber">
                <span class="ec-day">{{ formatEventDay(ev) }}</span>
                <span class="ec-month">{{ formatEventMonth(ev) }}</span>
              </div>
              <div class="ec-info">
                <h3>{{ ev.name }}</h3>
                <!-- Cố ý không in ngày âm cho từng sự kiện để tránh xung đột lịch trình (xem docs) -->
                <span v-if="ev.days_until != null" class="ec-countdown" data-material-accent="amber" :class="{ 'ec-today': ev.days_until === 0 }">
                  {{ ev.days_until === 0 ? 'Hôm nay!' : ev.days_until === 1 ? 'Ngày mai' : `Còn ${ev.days_until} ngày` }}
                </span>
                <span class="home-signal-evidence">
                  <SourceMark
                    :tier="eventSourceTier(ev)"
                    :source-title="eventSourceTitle(ev)"
                    :source-url="eventSourceUrl(ev)"
                    :verified-at="eventVerifiedAt(ev)"
                    compact
                    data-signal-source
                  />
                  <FreshnessLine
                    :status="eventFreshnessStatus(ev)"
                    :updated-label="eventFreshnessLabel(ev)"
                  />
                </span>
              </div>
              <span v-if="ev.id === signalLeadId && signalLeadDescriptor?.url" class="signal-lead-figure">
                <img
                  class="signal-lead-media"
                  :src="signalLeadDescriptor.url"
                  :alt="signalLeadDescriptor.alt"
                  :aria-describedby="signalLeadDisclosureId"
                  width="800"
                  height="600"
                  loading="lazy"
                  decoding="async"
                >
                <ImageDisclosure
                  :id="signalLeadDisclosureId"
                  :descriptor="signalLeadDescriptor"
                  presentation="short"
                  class="signal-lead-disclosure"
                />
              </span>
            </NuxtLink>
          </div>

          <div v-if="seasonalList.length" class="happening-section">
            <p class="happening-label" data-material-accent="amber"><IconLine name="calendar" aria-hidden="true" /> Đang vào mùa tháng {{ currentMonth }}</p>
            <!-- ul/li: role="listitem" trên NuxtLink ghi đè vai trò link của thẻ <a>
                 và xoá luôn tên khả truy cập (listitem là name-from-author). -->
            <ul class="home-season-ledger" aria-label="Đặc sản theo mùa">
              <li v-for="e in seasonalList" :key="e.id" class="home-season-item">
              <NuxtLink
                :to="entityPath(e.id)"
                class="home-season-row"
                :class="{ 'is-signal-lead': e.id === signalLeadId }"
                data-home-signal
                data-home-seasonal-signal
              >
                <span class="home-season-row__body">
                  <strong>{{ e.name }}</strong>
                  <span class="home-signal-evidence">
                    <SourceMark
                      :tier="eventSourceTier(e)"
                      :source-title="eventSourceTitle(e)"
                      :source-url="eventSourceUrl(e)"
                      :verified-at="eventVerifiedAt(e)"
                      compact
                      data-signal-source
                    />
                    <FreshnessLine
                      :status="eventFreshnessStatus(e)"
                      :updated-label="eventFreshnessLabel(e)"
                    />
                  </span>
                </span>
                <span v-if="e.id === signalLeadId && signalLeadDescriptor?.url" class="signal-lead-figure">
                  <img
                    class="signal-lead-media"
                    :src="signalLeadDescriptor.url"
                    :alt="signalLeadDescriptor.alt"
                    :aria-describedby="signalLeadDisclosureId"
                    width="800"
                    height="600"
                    loading="lazy"
                    decoding="async"
                  >
                  <ImageDisclosure
                    :id="signalLeadDisclosureId"
                    :descriptor="signalLeadDescriptor"
                    presentation="short"
                    class="signal-lead-disclosure"
                  />
                </span>
                <span class="home-season-row__action">Xem mùa vụ</span>
              </NuxtLink>
              </li>
            </ul>
          </div>
        </div>
      </section>
    </div>

    <!-- 5. Từ cộng đồng — ClientOnly tránh hydration mismatch -->
    <ClientOnly>
      <section
        v-if="communityPosts.length"
        class="block reveal sr-only"
        aria-label="Cộng đồng"
        data-image-surface="home-community"
        data-source-class="user-uploaded"
        data-entity-image-policy="no-image-invariant"
        data-home-section="community"
        data-material-accent="neutral"
      >
        <div class="section-head">
          <div class="sh-text">
            <h2 aria-label="Từ cộng đồng">Từ <em class="editorial-italic-accent" aria-hidden="true">cộng đồng</em></h2>
            <p class="sh-sub">Trải nghiệm thật, mẹo hay từ người đi trước</p>
          </div>
          <NuxtLink class="see-all" to="/cong-dong">Đọc thêm chuyện người đi trước <IconLine name="arrow-right" class="inline-arrow" aria-hidden="true" /></NuxtLink>
        </div>
        <HomeCommunityFeed
          :posts="communityPosts"
          :stats="communityStats"
          :trending-tags="trendingTags"
          :top-members="topMembers"
        />
      </section>
      <section v-else class="block reveal sr-only" aria-label="Cộng đồng" data-home-section="community" data-material-accent="neutral">
        <EmptyState tone="empty" title="Cộng đồng đang khởi động"
          message="Chưa có bài viết nổi bật tuần này — bạn là người kể chuyện đầu tiên nhé!">
          <template #actions>
            <NuxtLink to="/cong-dong" class="btn btn-outline"><IconLine name="message" aria-hidden="true" /> Tham gia cộng đồng</NuxtLink>
          </template>
          <div class="community-seed-prompts" aria-label="Gợi ý chủ đề chia sẻ">
            <p class="community-seed-label">Gợi ý chủ đề người Vĩnh Long đang quan tâm:</p>
            <div class="community-seed-grid">
              <NuxtLink to="/cong-dong" class="community-seed-card">
                <strong>Chèo SUP ngắm bình minh</strong>
                <span>Khúc sông Cổ Chiên buổi sáng sớm</span>
              </NuxtLink>
              <NuxtLink to="/cong-dong" class="community-seed-card">
                <strong>Sầu riêng chín cây An Bình</strong>
                <span>Nhận biết sầu riêng rụng không nhúng thuốc</span>
              </NuxtLink>
              <NuxtLink to="/cong-dong" class="community-seed-card">
                <strong>Lò gạch Thầy Kay hoàng hôn</strong>
                <span>Góc chụp ánh sáng xuyên vòm gốm đỏ</span>
              </NuxtLink>
            </div>
          </div>
        </EmptyState>
      </section>
      <template #fallback>
        <section class="block reveal sr-only" aria-hidden="true" data-home-section="community" style="min-height: 240px;">
          <div class="section-head">
            <div class="sh-text">
              <h2>Từ <em class="ac-neutral">cộng đồng</em></h2>
              <p class="sh-sub">Trải nghiệm thật, mẹo hay từ người đi trước</p>
            </div>
          </div>
          <SkeletonGrid :count="2" />
        </section>
      </template>
    </ClientOnly>

    <!-- 6. Dành cho bạn — one merged, image-tolerant personalization strip (client-only) -->
    <ClientOnly>
      <!-- Chỉ hiện khi có tín hiệu cá nhân thật (đã xem/đã lưu) -->
      <section v-if="hasPersonalSignal && forYou.length" class="block block-compact reveal" aria-label="Dành cho bạn" data-home-section="for-you">
        <div class="section-head section-head-tight">
          <div class="sh-text">
            <h2 class="h2-tight">Dành cho <em class="ac-clay">bạn</em></h2>
            <p class="sh-sub">Nội dung bạn vừa xem, đã lưu và gợi ý theo bạn.</p>
          </div>
        </div>
        <!-- Tên khác section cha tránh trùng lặp landmark axe -->
        <div class="scroll-row for-you-row" role="region" aria-label="Danh sách nội dung gợi ý" tabindex="0">
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

    <div class="home-river-divider" aria-hidden="true" />

    <!-- Continuation with JourneyActionRail -->
    <HomeContinuation :actions="homeJourneyActions" :pending="homePending" />

  </div>
</template>

<script setup lang="ts">
import { TYPE_META, AREA_META } from '~/composables/useConstants'
import { generateCategoryIcon } from '~/composables/useCategoryPlaceholder'
import { useJourneyActions } from '~/composables/useJourneyActions'
import HomeCategoryIndex from '~/components/home/HomeCategoryIndex.vue'
import HomeDecisionLedger from '~/components/home/HomeDecisionLedger.vue'
import HomeFeatureDossier from '~/components/home/HomeFeatureDossier.vue'
import HomeLocalBriefing from '~/components/home/HomeLocalBriefing.vue'
import HomeCommunityFeed from '~/components/home/HomeCommunityFeed.vue'
import HomeContinuation from '~/components/home/HomeContinuation.vue'
import HomeFieldworkFaq from '~/components/home/HomeFieldworkFaq.vue'
import HomeCuratedShowcase from '~/components/home/HomeCuratedShowcase.vue'
import HomeCulinaryTrail from '~/components/home/HomeCulinaryTrail.vue'
import HomeRiversideStays from '~/components/home/HomeRiversideStays.vue'
import HomeTravelPlanner from '~/components/home/HomeTravelPlanner.vue'
import HomeAtmosphereControl from '~/components/home/HomeAtmosphereControl.vue'
import type { AtmosphereMode } from '~/components/home/HomeAtmosphereControl.vue'
import ImageDisclosure from '~/components/ImageDisclosure.vue'
import { describeEntityImages, describeEntityPlaceholder } from '~/utils/imageDescriptors'
import { createHomeNocturnePresentation } from '~/utils/homeNocturnePresentation'
import type { HomePresentationEntity } from '~/utils/homeNocturnePresentation'
import { resolveFreshnessStatus, resolveSourceTier } from '~/utils/regionalColor'

const HERO_TERROIR_CHIPS = [
  { label: 'Cù lao An Bình', q: 'Cù lao An Bình' },
  { label: 'Lò gạch Mang Thít', q: 'Lò gạch Mang Thít' },
  { label: 'Chợ nổi Trà Ôn', q: 'Chợ nổi Trà Ôn' },
  { label: 'Sầu riêng Ri6', q: 'Sầu riêng Ri6' },
  { label: 'Chùa Phật Ngọc', q: 'Chùa Phật Ngọc Xá Lợi' },
] as const

const homeAeoEntries = [
  {
    heading: 'Mùa nước nổi & Miệt vườn (Tháng 8 – 10)',
    text: 'Thời điểm vàng trải nghiệm sinh thái sông nước Cửu Long. Xuồng ba lá len lỏi dưới bóng dừa nước Cù Lao An Bình, thưởng thức cá linh non đầu mùa và trái cây chín cây thanh ngọt.',
  },
  {
    heading: 'Mùa di sản gốm & Hoa xuân (Tháng 1 – 3)',
    text: 'Vương quốc gốm đỏ Mang Thít vào vụ nung đỏ lửa bên dòng Cổ Chiên. Khí hậu mát dịu lý tưởng cho các tour di sản kiến trúc tâm linh, làng nghề truyền thống và lễ hội đầu năm.',
  },
  {
    heading: 'Mùa trái cây rộ hè (Tháng 5 – 7)',
    text: 'Mùa sầu riêng Ri6, chôm chôm Bình Hòa Phước và bưởi Năm Roi Bình Minh vào vụ thu hoạch rộ. Lữ khách tự tay hái trái chín tại vườn ven sông và thưởng thức bánh xèo hến cù lao.',
  },
]
import {
  formatFreshnessLabel,
  eventMetadata,
  eventSourceTier,
  eventSourceTitle,
  eventSourceUrl,
  eventVerifiedAt,
  eventFreshnessStatus,
  eventFreshnessLabel,
} from '~/utils/homeSignalFormatters'
import { aiDisclosure } from '~/utils/aiDisclosure'
import type { ImageDescriptor } from '~/types/image'
import { useId, ref, computed } from 'vue'

useReveal()
const { get: ss } = useSiteSettings()
const atmosphereMode = ref<AtmosphereMode>('noon')

// Contextual Seasonal Highlight

const seasonalFruitHighlight = computed(() => {
  const month = new Date().getMonth() + 1
  if (month >= 5 && month <= 8) {
    return 'Mùa chôm chôm chín đỏ & sầu riêng Ri6 An Bình'
  } else if (month >= 9 && month <= 11) {
    return 'Mùa bưởi Năm Roi Bình Minh & cá linh non mùa nước nổi'
  }
  return 'Mùa cam sành ngọt Tam Bình & sắc hoa gốm đỏ Mang Thít'
})

const { homepageDecisionActions } = useJourneyActions()

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

const homeAsyncData = useAsyncData('homepage',
  () => apiFetch<any>('/api/homepage'))
const { data: homeData, error: homeError, pending: homePending, refresh: refreshHome } = homeAsyncData

const communityAsyncData = useAsyncData('home-community', async () => {
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
const { data: communityData } = communityAsyncData
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

const HERO_ELIGIBLE_TYPES = new Set(['attraction', 'experience', 'nature', 'craft_village', 'history', 'place'])

const HERO_ICONIC_IDS = new Set([
  'de-an-di-san-duong-dai-mang-thit',
  'lo-gach-mang-thit',
  'lang-nghe-gach-gom-mang-thit-vuong-quoc-do',
  'lang-gach-gom-mang-thit',
  'lang-nghe-gom-do-mang-thit',
  'cu-lao-an-binh',
  'dap-xe-miet-vuon',
  'cheo-xuong-rach-an-binh',
  'cho-noi-tra-on',
  'chua-tien-chau-tien-chau-tu',
  'nha-gom-do-tu-buoi',
  'nha-gom-tu-buoi',
  'chua-ong-that-phu-mieu',
  'khu-du-lich-vinh-sang',
])

function getHeroPriorityScore(entity: any): number {
  if (!entity || !entity.id) return -100
  const type = String(entity.type || '').toLowerCase()
  if (!HERO_ELIGIBLE_TYPES.has(type)) return -100

  let score = 10
  const id = String(entity.id).toLowerCase()
  const name = String(entity.name || entity.title || '').toLowerCase()
  const area = String(entity.area || entity.place_area || entity.attributes?.area || entity.attributes?.province || '').toLowerCase()

  if (HERO_ICONIC_IDS.has(id)) {
    score += 30
  } else if (
    id.includes('mang-thit') ||
    id.includes('an-binh') ||
    id.includes('tra-on') ||
    id.includes('tien-chau') ||
    id.includes('tu-buoi') ||
    name.includes('mang thít') ||
    name.includes('an bình') ||
    name.includes('trà ôn') ||
    name.includes('tiên châu') ||
    name.includes('tư buôi')
  ) {
    score += 25
  }

  if (area === 'vinh-long' || area === 'vinh_long') {
    score += 15
  }

  if (type === 'attraction' || type === 'craft_village') score += 5
  else if (type === 'experience' || type === 'nature') score += 4

  if (entity.images?.length || entity.image || entity.image_descriptor || entity.attributes?.is_verified_photo) {
    score += 5
  }

  if ((entity.summary || '').length > 60) score += 2

  return score
}

const SPOTLIGHT_TYPE_WEIGHT: Record<string, number> = { experience: 3, attraction: 2, nature: 2, craft_village: 2, place: 2, dish: 1, product: 0 }
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

const heroFeature = computed<any>(() => {
  const pool = [...experiences.value, ...(homeData.value?.experiences || [])]
  const valid = pool.filter((e: any) => e && HERO_ELIGIBLE_TYPES.has(String(e.type || '').toLowerCase()))
  if (!valid.length) {
    const fallbackPool = [...(homeData.value?.upcoming_events || []), ...(homeData.value?.seasonal || [])]
      .filter((e: any) => e && HERO_ELIGIBLE_TYPES.has(String(e.type || '').toLowerCase()))
    if (fallbackPool.length) {
      return fallbackPool.reduce((best, cur) => (getHeroPriorityScore(cur) > getHeroPriorityScore(best) ? cur : best))
    }
    return null
  }
  return valid.reduce((best, cur) => (getHeroPriorityScore(cur) > getHeroPriorityScore(best) ? cur : best))
})
const hfMeta = computed(() => heroFeature.value ? (TYPE_META[heroFeature.value.type] || { icon: 'pin', label: heroFeature.value.type, cat: 'place' }) : null)
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
const hfCoordinates = computed<string>(() => {
  const e = heroFeature.value
  if (!e) return '10.254° N, 105.972° E'
  const lat = Number(e.lat ?? e.latitude ?? e.attributes?.lat ?? e.attributes?.latitude)
  const lng = Number(e.lng ?? e.longitude ?? e.attributes?.lng ?? e.attributes?.longitude)
  if (Number.isFinite(lat) && Number.isFinite(lng) && lat !== 0 && lng !== 0) {
    return `${lat.toFixed(3)}° N, ${lng.toFixed(3)}° E`
  }
  return '10.254° N, 105.972° E'
})
const hfMapTo = computed<string>(() => {
  if (!heroFeature.value?.id) return '/ban-do'
  return `/ban-do?selected=${encodeURIComponent(heroFeature.value.id)}`
})

// Măng-sét ngày âm–dương — ĐỌC TỪ PAYLOAD, không tính ở trình duyệt.
// Oracle âm lịch là Python (agent/lunar_calendar.py); tính tại nguồn thì không
// có rủi ro lệch bản port, trang chủ khỏi nạp ~7kB gz bản port JS chỉ để in một
// dòng chữ (bundle đang vượt trần), và hết hẳn rủi ro SSR bất đồng client.
// Backend cũng đã lấy ngày theo giờ VN nên không còn lệch 7 tiếng.
const masthead = computed(() => homeData.value?.masthead || null)
const mastheadSolar = computed(() => masthead.value?.solar_label || '')
const mastheadLunar = computed(() => masthead.value?.lunar_label || '')

// ── Tin dẫn tín hiệu: luật 3 bậc (sự kiện -> hàng mùa -> không ai) ───────
const signalLead = computed<any>(() =>
  upcomingEventList.value.find((x: any) => x?.signal_lead_ok)
  || seasonalList.value.find((x: any) => x?.signal_lead_ok)
  || null)
const signalLeadId = computed(() => signalLead.value?.id || null)
const signalLeadDescriptor = computed<ImageDescriptor | null>(() => {
  const e = signalLead.value
  return e ? (describeEntityImages(e)[0] || null) : null
})
const signalLeadDisclosureId = `home-signal-lead-${useId().replace(/[^A-Za-z0-9_-]+/g, '-')}`

const areaCounts = computed<Record<string, number>>(() => homeData.value?.area_counts || {})

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
await homeAsyncData
function plannerAddPath(id: string | number) {
  return `/tao-lich-trinh?add=${encodeURIComponent(String(id))}`
}

function onImgError(e: Event | string) {
  if (typeof e === 'string') return
  const img = e.target as HTMLImageElement
  img.style.display = 'none'
}

useSeoMeta({
  title: ss('seo.default_title', 'vinhlong360 — Du lịch & Sản phẩm địa phương'),
  description: ss('seo.default_description', 'Cổng du lịch và sản phẩm địa phương Vĩnh Long: trải nghiệm miệt vườn, đặc sản theo mùa, OCOP, làng nghề và lịch trình gợi ý.'),
  ogTitle: ss('seo.default_title', 'vinhlong360 — Du lịch & Sản phẩm địa phương'),
  ogDescription: ss('seo.default_description', 'Cổng du lịch và sản phẩm địa phương Vĩnh Long: trải nghiệm miệt vườn, đặc sản theo mùa, OCOP, làng nghề và lịch trình gợi ý.'),
  ogImage: ss('branding.og_image', 'https://vinhlong360.vn/img/og-default.jpg'),
  ogType: 'website',
  ogUrl: 'https://vinhlong360.vn/',
  twitterCard: 'summary_large_image',
})

// Schema.org unified @graph: buildHomeSchemaGraph (@type': 'EntryPoint', urlTemplate: 'https://vinhlong360.vn/tim-kiem?q={search_term_string}')
// §1.6: areaServed: 'Vĩnh Long'
const homeSchema = computed(() => buildHomeSchemaGraph({
  upcomingEvents: upcomingEvents.value,
}))

function onHeroImgError(e: Event) {
  const img = e.target as HTMLImageElement
  if (img && !img.dataset.fallbackApplied) {
    img.dataset.fallbackApplied = 'true'
    img.src = '/img/spread/song-nuoc.webp'
  }
}

useHead({
  link: [
    { rel: 'canonical', href: canonicalUrl('/') },
  ],
  script: computed(() => [
    {
      type: 'application/ld+json',
      innerHTML: safeJsonLd({
        ...homeSchema.value,
      }),
    },
  ]),
})
</script>

<style>
/* ═══════════════════════════════════════════════════
   HERO DISPLAY & PROTECTED CONSUMER CONTRACT
   ═══════════════════════════════════════════════════ */
.home .hero-main h1 { letter-spacing: -.02em; }

/* Premium search capsule */
.home .hero-search {
  padding: var(--space-1);
  background: rgba(var(--white-rgb),.14);
  backdrop-filter: saturate(180%) blur(10px);
  border: .5px solid rgba(var(--white-rgb),.30);
  border-radius: calc(var(--radius-surface) + var(--space-1));
  box-shadow: 0 8px 30px rgba(var(--black-rgb),.18), 0 2px 8px rgba(var(--black-rgb),.12);
  transition: box-shadow .35s var(--ease-out-expo), border-color .3s var(--ease-out), transform .35s var(--ease-out-expo);
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
  padding: var(--space-4) var(--space-12) var(--space-4) calc(var(--space-12) + var(--space-1h));
  border-color: transparent; background: var(--card);
}
.home .hero .hero-ac .ac-dropdown { text-align: left; }
.home .hero-nearby {
  display: inline-flex; align-items: center; gap: .35em;
  margin-top: var(--space-3); min-height: 44px;
  color: rgba(var(--white-rgb),.92); font-size: var(--text-sm); font-weight: var(--weight-bold);
  text-decoration: none; text-shadow: 0 1px 6px rgba(var(--black-rgb),.35);
}
.home .hero-nearby:hover { text-decoration: underline; text-underline-offset: 3px; }
.home .hero-nearby:focus-visible { outline: 2px solid var(--color-focus); outline-offset: 3px; border-radius: 4px; }

/* ═══════════════════════════════════════════════════
   "ĐANG DIỄN RA" — protected date & countdown consumers
   ═══════════════════════════════════════════════════ */
.ec-date { display: flex; flex-direction: column; align-items: center; justify-content: center; min-width: 52px; padding: var(--space-2); background: var(--home-color-amber-surface); border-radius: var(--radius-control); color: var(--home-color-amber-text); }
.ec-countdown {
  display: inline-flex; align-items: center; gap: var(--space-1);
  font-size: var(--text-xs); font-weight: var(--weight-bold); color: var(--home-color-amber-text);
  background: var(--home-color-amber-surface); padding: var(--space-1) var(--space-2); border-radius: var(--radius-full);
}
.ec-today { color: var(--color-error); }

/* ═══════════════════════════════════════════════════
   DARK MODE & REDUCED TRANSPARENCY PROTECTED CONSUMERS
   ═══════════════════════════════════════════════════ */
.dark .home .hero-search { background: rgba(var(--white-rgb),.22); border-color: rgba(var(--white-rgb),.38); }
.dark .home .hero-search input { background: var(--bg-warm); color: var(--ink); }
.dark .home .hero-search input::placeholder { color: rgba(var(--white-rgb),.50); }
.dark .home .hero-search:focus-within { border-color: var(--color-focus); }
.dark .ec-today { color: var(--color-error); }

@media (prefers-reduced-transparency: reduce) {
  .home .hero-search { backdrop-filter: none; background: rgba(var(--black-rgb),.35); }
}

/* ═══════════════════════════════════════════════════
   DÀNH CHO BẠN & DISCLOSURE MICRO-TYPOGRAPHY
   ═══════════════════════════════════════════════════ */
.for-you-row { align-items: stretch; }
.fy-disclosure { max-width: 60px; color: var(--muted); overflow-wrap: anywhere; }
.fy-disclosure :deep([data-short-label]) { font-size: var(--text-2xs); font-weight: var(--weight-semibold); line-height: 1.15; }

/* ═══════════════════════════════════════════════════
   COGNITIVE CONTEXTUAL BANNER (ASTRONOMICAL TIDE & SEASONS)
   ═══════════════════════════════════════════════════ */
.hero-cognitive-banner {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  padding: 6px 14px;
  border-radius: var(--radius-pill, 9999px);
  background: rgba(var(--white-rgb), 0.08);
  border: 1px solid var(--border-liquid-glass);
  backdrop-filter: blur(16px);
  margin-bottom: var(--space-4);
  width: fit-content;
}

.hero-cognitive-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: var(--text-xs);
  color: var(--surface-white);
}

.hero-cognitive-chip--weather {
  color: var(--surface-white);
}

.hero-cognitive-chip--weather .line-icon {
  color: var(--alluvial-gold);
}

.hero-cognitive-chip__title {
  font-weight: var(--weight-bold);
  color: var(--surface-white);
}

.hero-cognitive-chip__sep {
  opacity: 0.6;
}

.hero-cognitive-chip__desc {
  opacity: 0.9;
}

.hero-cognitive-chip--fruit {
  padding-left: var(--space-2);
  border-left: 1px solid var(--border-liquid-glass);
  color: var(--alluvial-gold);
  font-weight: var(--weight-medium);
}
</style>
<style src="~/assets/css/home-nocturne.css"></style>
