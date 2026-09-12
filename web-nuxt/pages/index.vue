<template>
  <div
    class="home"
    data-home-pilot="nocturne-b1"
    data-color-system="tri-region-v1"
    data-page-recipe="homepage"
    data-material-accent="clay"
  >
    <!-- One editorial thesis: useful action first, one disclosed media dossier second. -->
    <div class="sr-only" data-home-section="context" aria-label="Ngữ cảnh khám phá">Khu vực khám phá: Vĩnh Long</div>
    <section class="hero" aria-label="Giới thiệu" data-home-section="editorial-lead">
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
          <div class="hero-terroir-chips" role="region" aria-label="Gợi ý thực địa Vĩnh Long">
            <span class="hero-terroir-chips__label">Khám phá nhanh:</span>
            <NuxtLink
              v-for="chip in HERO_TERROIR_CHIPS"
              :key="chip.label"
              :to="`/kham-pha?q=${encodeURIComponent(chip.q)}`"
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
          :source-tier="resolveSourceTier(heroFeature?.quality?.source_tier)"
        />
      </div>
    </section>

    <div class="home-river-divider" aria-hidden="true" />

    <div class="home-quick-decisions" data-home-section="quick-decisions">
      <HomeDecisionLedger :entries="homePresentation.decisionEntries" />
      <HomeCategoryIndex
        v-if="!homePending"
        :groups="homePresentation.categoryGroups"
      />
    </div>

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

    <HomeProductLead
      v-if="showProductLead"
      :scale-line="productLeadScale"
      scale-note="Con số lấy từ dữ liệu, cập nhật theo kho"
      eyebrow="Đề cử của ban biên tập"
      :title="productLead.name"
      :summary="productLead.summary"
      :region="productLeadRegion"
      :descriptor="productLeadDescriptor"
      :disclosure-id="productLeadDisclosureId"
      :detail-to="`/dia-diem/${productLead.id}`"
    />

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

    <div class="home-signals" data-home-section="signals">
      <HomeLocalBriefing />

      <section v-if="upcomingEventList.length || seasonalList.length" class="block reveal" aria-label="Tín hiệu địa phương" data-material-accent="amber">
        <div class="section-head">
          <div class="sh-text">
            <h2>Tín hiệu địa phương</h2>
            <p class="sh-sub">Lịch đang tới và mùa vụ đang có dữ liệu.</p>
          </div>
          <NuxtLink class="see-all" to="/su-kien">Xem lịch</NuxtLink>
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
            <p class="happening-label" data-material-accent="amber"><IconLine name="calendar" /> Đang vào mùa tháng {{ currentMonth }}</p>
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
                <span class="home-season-row__action">Xem theo mùa</span>
              </NuxtLink>
              </li>
            </ul>
          </div>
        </div>
      </section>
    </div>

    <!-- 4b. Sổ vàng OCOP — Điểm dừng thị giác 3, trạng thái E-lite -->
    <HomeOcopLedger />

    <!-- 5. Từ cộng đồng — ClientOnly tránh hydration mismatch -->
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
          <NuxtLink class="see-all" to="/cong-dong">Đọc thêm chuyện người đi trước <IconLine name="arrow-right" class="inline-arrow" aria-hidden="true" /></NuxtLink>
        </div>
        <HomeCommunityFeed
          :posts="communityPosts"
          :stats="communityStats"
          :trending-tags="trendingTags"
          :top-members="topMembers"
        />
      </section>
      <section v-else class="block reveal" aria-label="Cộng đồng" data-home-section="community" data-material-accent="neutral">
        <EmptyState tone="empty" title="Cộng đồng đang khởi động"
          message="Chưa có bài viết nổi bật tuần này — bạn là người kể chuyện đầu tiên nhé!">
          <template #actions>
            <NuxtLink to="/cong-dong" class="btn btn-outline"><IconLine name="message" /> Tham gia cộng đồng</NuxtLink>
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
        <section class="block reveal" aria-hidden="true" data-home-section="community" style="min-height: 240px;">
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
import HomeProductLead from '~/components/home/HomeProductLead.vue'
import HomeOcopLedger from '~/components/home/HomeOcopLedger.vue'
import HomeCommunityFeed from '~/components/home/HomeCommunityFeed.vue'
import HomeContinuation from '~/components/home/HomeContinuation.vue'
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
import { useId } from 'vue'

useReveal()
const { get: ss } = useSiteSettings()

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

const heroFeature = computed<any>(() => experiences.value.find((e: any) => e.id !== spotId.value) || spotlight.value || null)
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

// ── Tin chính đặc sản (điểm dừng thị giác 2) ────────────────────────────
// Cờ home_product_lead mặc định TẮT: mục mới phải bật tay từ AdminCP, và tắt
// lại trong 10 giây nếu hỏng — máy chủ KHÔNG giữ bản N-1 nên đây là đường lùi
// duy nhất không cần deploy.
const productLead = computed<any>(() => homeData.value?.product_lead || null)
const productsTotal = computed<number | null>(() => homeData.value?.products_total ?? null)

// Descriptor tính Ở ĐÂY rồi truyền xuống component qua prop. Cổng R20.10 chỉ
// đỏ khi mã tự đọc trường ảnh thô của entity; uỷ quyền cho describeEntityImages
// thì sạch (đã kiểm bằng thực nghiệm: đọc thô = 2 finding, uỷ quyền = 0).
// LƯU Ý cho người sửa sau: checker là bộ SO CHUỖI, nó bắt cả câu bình luận —
// đừng viết tên trường đó ra đây, kể cả để giải thích cách tránh nó (§5c).
const productLeadDescriptor = computed<ImageDescriptor>(() => {
  const e = productLead.value
  if (!e) return describeEntityPlaceholder({ name: 'Đặc sản' })
  return describeEntityImages(e)[0] || describeEntityPlaceholder(e)
})
const productLeadDisclosureId = `home-product-lead-${useId().replace(/[^A-Za-z0-9_-]+/g, '-')}`
const productLeadRegion = computed(() => {
  const e = productLead.value
  const a = e?.place?.name || e?.attributes?.ward || e?.attributes?.place_name
  return a ? String(a) : ''
})
// Con số render TỪ PAYLOAD, không viết cứng — số xã/phường lấy từ chính
// area_counts nếu có, không bịa hằng số.
const productLeadScale = computed(() => {
  const n = productsTotal.value
  return n ? `${n} đặc sản Vĩnh Long` : 'Đặc sản Vĩnh Long'
})
// Mục chỉ hiện khi CÓ CỜ và CÓ DỮ LIỆU — thiếu một trong hai thì khuyết êm,
// không để lại khung rỗng hay nhãn treo.
const showProductLead = computed(() => ff('home_product_lead') && !!productLead.value)

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
.home .hero h1 {
  font-family: var(--font-editorial);
  font-weight: 600;
  font-size: clamp(2.75rem, 1.6rem + 5.6vw, 5.4rem);
  letter-spacing: -.02em;
  text-shadow: 0 2px 28px rgba(var(--black-rgb),.42);
  max-width: 15ch;
  text-wrap: balance;
}
.home .hero-sub { font-family: var(--font-editorial); font-size: clamp(1.08rem, 1rem + .5vw, 1.3rem); line-height: 1.5; opacity: .95; max-width: 600px; margin: var(--space-4) 0 0; text-shadow: 0 1px 8px rgba(var(--black-rgb),.22); }
.dark .home .hero-sub { opacity: 1; font-weight: 400; }

/* Premium search capsule */
.home .hero-search {
  padding: var(--space-1);
  background: rgba(var(--white-rgb),.14);
  backdrop-filter: saturate(180%) blur(10px); -webkit-backdrop-filter: saturate(180%) blur(10px);
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
  .home .hero-search { backdrop-filter: none; -webkit-backdrop-filter: none; background: rgba(var(--black-rgb),.35); }
}

/* ═══════════════════════════════════════════════════
   DÀNH CHO BẠN & DISCLOSURE MICRO-TYPOGRAPHY
   ═══════════════════════════════════════════════════ */
.for-you-row { align-items: stretch; }
.fy-disclosure { max-width: 60px; color: var(--muted); overflow-wrap: anywhere; }
.fy-disclosure :deep([data-short-label]) { font-size: var(--text-2xs); font-weight: var(--weight-semibold); line-height: 1.15; }
</style>
<style src="~/assets/css/home-nocturne.css"></style>
