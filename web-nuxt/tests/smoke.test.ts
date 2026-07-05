import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { entityPath, normalizeRouteParam, notificationTargetPath, postPath, savedItemPath, userPath } from '../utils/routePaths'

describe('Component smoke tests', () => {
  it('imports Breadcrumb component', async () => {
    const mod = await import('../components/Breadcrumb.vue')
    expect(mod.default).toBeTruthy()
  })

  it('imports ScrollToTop component', async () => {
    const mod = await import('../components/ScrollToTop.vue')
    expect(mod.default).toBeTruthy()
  })

  it('imports ToastContainer component', async () => {
    const mod = await import('../components/ToastContainer.vue')
    expect(mod.default).toBeTruthy()
  })

  it('imports ShareButton component', async () => {
    const mod = await import('../components/ShareButton.vue')
    expect(mod.default).toBeTruthy()
  })

  it('imports SaveButton component', async () => {
    const mod = await import('../components/SaveButton.vue')
    expect(mod.default).toBeTruthy()
  })

  it('imports ChatWidget component', async () => {
    const mod = await import('../components/ChatWidget.vue')
    expect(mod.default).toBeTruthy()
  })

  it('imports AuthModal component', async () => {
    const mod = await import('../components/AuthModal.vue')
    expect(mod.default).toBeTruthy()
  })

  it('imports OnboardingSheet component', async () => {
    const mod = await import('../components/OnboardingSheet.vue')
    expect(mod.default).toBeTruthy()
  })

  it('imports SmartRecommendations component', async () => {
    const mod = await import('../components/SmartRecommendations.vue')
    expect(mod.default).toBeTruthy()
  })

  it('imports JourneyActionRail component', async () => {
    const mod = await import('../components/JourneyActionRail.vue')
    expect(mod.default).toBeTruthy()
  })
})

describe('UserCP regressions', () => {
  const src = (file: string) => readFileSync(resolve(process.cwd(), file), 'utf8').replaceAll('\r\n', '\n')

  it('route path helpers encode user-facing dynamic ids', () => {
    expect(normalizeRouteParam(['post/1', 'ignored'])).toBe('post/1')
    expect(entityPath('place/a b')).toBe('/dia-diem/place%2Fa%20b')
    expect(postPath('post/a?b')).toBe('/bai-viet/post%2Fa%3Fb')
    expect(userPath('user/name')).toBe('/nguoi-dung/user%2Fname')
    expect(savedItemPath({ id: 'itinerary-mekong-weekend', type: 'itinerary' })).toBe('/lich-trinh/mekong-weekend')
    expect(savedItemPath({ id: 'place/1', kind: 'entity' })).toBe('/dia-diem/place%2F1')
    expect(notificationTargetPath({ ref_type: 'entity', ref_id: 'place/1' })).toBe('/dia-diem/place%2F1')
    expect(notificationTargetPath({ ref_type: 'post', ref_id: 'post/1' })).toBe('/bai-viet/post%2F1')
    expect(notificationTargetPath({ ref_type: 'itinerary', ref_id: 'plan/1' })).toBe('/lich-trinh/plan%2F1')
    expect(notificationTargetPath({ ref_type: 'user', ref_id: 'user/1' })).toBe('/nguoi-dung/user%2F1')
  })

  it('account dashboard exposes readiness and next actions', () => {
    const page = src('pages/tai-khoan.vue')
    expect(page).toContain('accountScore')
    expect(page).toContain('profileData')
    expect(page).toContain('cp-alert')
    expect(page).toContain('profileCompletion')
    expect(page).toContain('nextActions')
    expect(page).toContain('userCpJourneyActions')
    expect(page).toContain('JourneyActionRail')
    expect(page).toContain('cp-summary-grid')
    expect(page).toContain('resetAccountData')
    expect(page).toContain('handleSessionExpired')
    expect(page).toContain('Bảo vệ tài khoản bằng mật khẩu')
    expect(page).not.toContain("{ key: 'username'")
  })

  it('settings tabs support keyboard navigation and hide inactive profile panel', () => {
    const page = src('pages/cai-dat.vue')
    expect(page).toContain('onTabKeydown')
    expect(page).toContain('Rời tab Hồ sơ?')
    expect(page).toContain('settings-hash-anchors')
    expect(page).toContain("window.addEventListener('hashchange', onPopState)")
    expect(page).toContain('syncHashTabSoon')
    expect(page).toContain("const activeTab = ref<TabKey>('ho-so')")
    expect(page).toContain(':hidden="activeTab !== \'ho-so\'"')
    expect(page).toContain('hiddenSystemSessions')
    expect(page).toContain("user?.username || user?.id || '—'")
  })

  it('saved workspace supports filtering, syncing and place links', () => {
    const page = src('pages/da-luu.vue')
    expect(page).toContain('savedQuery')
    expect(page).toContain('savedJourneyActions')
    expect(page).toContain('JourneyActionRail')
    expect(page).toContain('refreshCurrentTab')
    expect(page).toContain('filteredEntities')
    expect(page).toContain('savedItemPath(item)')
    expect(page).toContain('encodePathId')
    expect(page).toContain('URLSearchParams')
    expect(page).toContain('handleSessionExpired')
    expect(page).toContain('resetSavedRemoteData')
    expect(page).toContain('LazySmartRecommendations context="saved"')
    expect(page).toContain('normalizeSavedTab(route.query.tab)')
    expect(page).toContain('savedMapLink')
    expect(page).toContain('syncSavedRoute')
    expect(src('composables/useJourneyActions.ts')).toContain('/tao-lich-trinh?source=saved')
  })

  it('planner, map and festival journeys use the upgraded contracts', () => {
    const planner = src('pages/tao-lich-trinh.vue')
    expect(planner).toContain('pendingAddId')
    expect(planner).toContain('route.query.add')
    expect(planner).toContain('route.query.source')
    expect(planner).toContain('autoAddedFromQuery')
    expect(planner).toContain('clearPlannerAddQuery')
    expect(planner).toContain('stops.value.some(s => s.id === entity.id)')
    expect(planner).toContain('usePublicApi')
    expect(planner).toContain('listEntities')
    expect(planner).toContain('getEntity')
    expect(planner).not.toContain('/api/entities?limit=700')
    expect(planner).not.toContain('role="button"')

    const map = src('pages/ban-do.vue')
    const ndaMap = src('composables/useNDAMap.ts')
    expect(map).toContain('mapPinApiPath')
    expect(map).toContain("params.set('type', type)")
    expect(map).toContain('mapSearchQuery')
    expect(map).toContain('syncMapRoute')
    expect(map).toContain('visibleListPins')
    expect(map).not.toContain('/api/entities?limit=700')
    expect(ndaMap).toContain('getFallbackStyle')
    expect(ndaMap).toContain("map.on('error'")
    expect(ndaMap).toContain('isRecoverableMapResourceError')

    const festivals = src('pages/le-hoi.vue')
    expect(festivals).toContain('categoryTokens')
    expect(festivals).toContain("includes('le-hoi')")
    expect(festivals).toContain('eventStart(e)')
    const season = src('pages/theo-mua.vue')
    expect(season).toContain('monthFromQuery(route.query.mua)')
    expect(season).toContain("router.replace({ query: { ...route.query, mua: String(m) } })")
  })

  it('homepage hero uses intent-led copy and safer visual affordances', () => {
    const page = src('pages/index.vue')
    expect(page).toContain('Tìm điểm đến, món ngon, lễ hội và lịch trình phù hợp')
    expect(page).toContain('Tìm điểm đến, món ngon, lịch trình…')
    expect(page).toContain("label: 'Gần tôi'")
    expect(page).toContain("label: 'Ăn gì hôm nay'")
    expect(page).toContain("to: '/ban-do?near=1'")
    expect(page).toContain('.home .hero .hero-ac::before')
    expect(page).toContain('homeDecisionCards')
    expect(page).toContain('homeJourneyActions')
    expect(page).toContain('homepageDecisionActions')
    expect(page).toContain('JourneyActionRail')
    expect(page).toContain('Hôm nay bạn muốn bắt đầu thế nào?')
    expect(page).toContain('plannerAddPath(heroFeature.id)')
    expect(page).toContain('to: `/theo-mua?mua=${encodeURIComponent(String(currentMonth.value))}`')
    expect(page).toContain('dx-item')
    expect(page).toContain('cat-hint')
    expect(page).toContain('letter-spacing: -.02em; line-height: .98;')
    expect(page).not.toContain('letter-spacing: -1.4px')
  })

  it('default layout mounts client widgets after hydration', () => {
    const layout = src('layouts/default.vue')
    const baseCss = src('assets/css/base.css')
    const componentsCss = src('assets/css/components.css')
    const heroIllustration = src('components/HeroIllustration.vue')
    expect(layout).toContain('const clientReady = ref(false)')
    expect(layout).toContain('<template v-if="clientReady">')
    expect(layout).toContain('<LazyChatWidget />')
    expect(layout).toContain('<SearchAutocomplete class="topbar-search" />')
    expect(layout).toContain('<template v-else>\n            <button type="button" class="theme-toggle"')
    expect(layout).toContain('auth-user-snapshot')
    expect(layout).toContain('const { isLoggedIn, user } = useAuth()')
    expect(layout).not.toContain('Boolean(token.value)')
    expect(layout).toContain('hasAuthSession')
    expect(layout).not.toContain('<LazySearchAutocomplete class="topbar-search" />')
    expect(layout).toContain('<LazyAuthModal :visible="showAuth"')
    expect(layout).toContain('<LazyConfirmDialog />')
    expect(layout).toContain("to: '/da-luu'")
    expect(layout).toContain('<noscript class="noscript-banner">')
    expect(layout).not.toContain('<noscript>\n      <div')
    expect(baseCss).toContain('@media (max-width: 640px)')
    expect(baseCss).toContain('.topbar-search { display: none; }')
    expect(componentsCss).toContain('.topbar-search.search-ac { display: none !important; }')
    expect(heroIllustration).toContain('overflow: hidden;')
    expect(heroIllustration).toContain('contain: paint;')
  })

  it('does not register the service worker on local dev hosts', () => {
    const config = src('nuxt.config.ts')
    expect(config).toContain("location.protocol==='https:'")
    expect(config).toContain("'127.0.0.1'")
  })

  it('keeps auth-aware community UI hydration-safe', () => {
    const config = src('nuxt.config.ts')
    const prerenderStart = config.indexOf('prerender:')
    const prerenderBlock = config.slice(prerenderStart, config.indexOf('routeRules:', prerenderStart))
    expect(prerenderBlock).not.toContain("'/cong-dong'")

    const timeAgo = src('composables/useTimeAgo.ts')
    expect(timeAgo).toContain('relative-time-hydrated')
    expect(timeAgo).toContain("timeZone: 'Asia/Ho_Chi_Minh'")
    expect(timeAgo).toContain('if (!hydrated.value) return formatAbsoluteDate(date)')
  })

  it('login buttons call openAuth without passing click events', () => {
    const auth = src('composables/useAuth.ts')
    expect(auth).toContain('shouldUseSecureAuthCookie')
    expect(auth).toContain("window.location.protocol === 'https:'")
    expect(auth).toContain('secure: shouldUseSecureAuthCookie()')
    expect(auth).not.toContain('secure: true')
    for (const file of ['pages/tai-khoan.vue', 'pages/cai-dat.vue', 'pages/da-luu.vue', 'pages/thong-bao.vue']) {
      const page = src(file)
      expect(page).toContain('@click="openAuth()"')
      expect(page).not.toContain('@click="() => openAuth()"')
      expect(page).not.toMatch(/@click="openAuth"(?!\()/)
    }
  })

  it('notifications page avoids nested interactive buttons', () => {
    const page = src('pages/thong-bao.vue')
    expect(page).toContain('role="button"')
    expect(page).toContain('@keydown.enter.prevent="open(n)"')
    expect(page).not.toContain('<button type="button" :class="[\'tb-item\'')
  })

  it('shared apiFetch honors runtime API_BASE during SSR', () => {
    const util = src('utils/apiFetch.ts')
    expect(util).toContain('useRuntimeConfig().public.apiBase')
    expect(util).toContain('FALLBACK_SSR_ORIGIN')
    expect(util).toContain('baseURL')
  })

  it('public user profile handles username routes and accessible tabs', () => {
    const page = src('pages/nguoi-dung/[id].vue')
    expect(page).toContain('ProfilePayload')
    expect(page).toContain('public-user-${userId.value}')
    expect(page).toContain('encodeURIComponent(lookup)')
    expect(page).toContain('profileLoadStatus')
    expect(page).toContain('profileNotFound')
    expect(page).toContain('setResponseStatus(404)')
    expect(page).toContain('setProfileTab')
    expect(page).toContain('onProfileTabKeydown')
    expect(page).toContain('role="tabpanel"')
    expect(page).toContain('profile-insight')
    expect(page).toContain('useCommunityPostFilters')
    expect(page).toContain('normalizeVisibleProfileTab')
    expect(page).toContain("tab === 'saved' && isSelf")
    expect(page).not.toContain('Chọn tên người dùng')
  })

  it('community feed normalizes tabs and filters production test posts', () => {
    const page = src('pages/cong-dong.vue')
    const filter = src('composables/useCommunityPostFilters.ts')
    const actions = src('composables/usePostActions.ts')
    expect(page).toContain('visibleFeedTabs')
    expect(page).toContain('normalizeCommunityRouteState')
    expect(page).toContain('onFeedTabKeydown')
    expect(page).toContain('onTypeFilterKeydown')
    expect(page).toContain('filterCommunityPosts')
    expect(page).toContain('useCommunityPostFilters')
    expect(filter).toContain('isProductionTestPost')
    expect(filter).toContain('isExplicitSeedFlag')
    expect(filter).toContain('truthySeedMarkers')
    expect(filter).toContain('communityPostSearchText')
    expect(filter).toContain('repost_snapshot')
    expect(filter).toContain('test admin')
    expect(page).toContain('firstQueryValue')
    expect(page).toContain('normalizeTagQuery')
    expect(page).toContain('syncCommunitySearchQuery')
    expect(page).toContain('encodeURIComponent(reportEntityId.value)')
    expect(page).toContain('refreshFeed()')
    expect(page).toContain("if (isPrivateFeedTab(activeTab.value)) setTab('latest')")
    expect(page).toContain(':data-tab="tab.key"')
    expect(actions).toContain('Math.max(0')
    expect(actions).toContain('previous.forEach')
    expect(actions).toContain('encodedPostId = encodePathId(postId)')
    const topbar = src('components/SearchAutocomplete.vue')
    expect(topbar).toContain('class="ac-recent-row"')
    expect(topbar).toContain('class="ac-item ac-recent"')
  })

  it('community navigation uses shared encoded route helpers', () => {
    expect(src('components/PostCard.vue')).toContain('postPath(props.post.id)')
    expect(src('components/PostCard.vue')).toContain('entityPath(post.entity_id)')
    expect(src('components/PostCard.vue')).toContain('userPath(post.username || post.user_id)')
    const entityCard = src('components/EntityCard.vue')
    expect(entityCard).toContain('const cardPath = computed(() => entityPath(props.entity.id))')
    expect(entityCard).toContain('<article :class="[\'card\'')
    expect(entityCard).toContain('class="card-cover-link"')
    expect(entityCard).not.toContain('<NuxtLink :to="entityPath(entity.id)" :class="[\'card\'')
    expect(src('components/NotificationBell.vue')).toContain('notificationTargetPath(n)')
    expect(src('pages/thong-bao.vue')).toContain('notificationTargetPath(n)')
    expect(src('pages/thong-bao.vue')).toContain('encodePathId(n.id)')
    expect(src('composables/useNotifications.ts')).toContain('encodePathId(id)')
    expect(src('components/EntityReviews.vue')).toContain('helpfulPending')
    expect(src('components/EntityReviews.vue')).toContain('Math.max(0')
    expect(src('components/EntityReviews.vue')).toContain('encodedEntityId')
    const detail = src('pages/bai-viet/[id].vue')
    expect(detail).toContain('normalizeRouteParam(route.params.id)')
    expect(detail).toContain('encodedPostId')
    expect(detail).toContain('await refreshPost()')
    expect(detail).toContain('postPath(postId.value)')
    expect(detail).toContain('userPath(c.author?.username || c.author?.id)')
  })

  it('entity detail exposes a user-facing trust layer', () => {
    const detail = src('pages/dia-diem/[id].vue')
    const types = src('types/index.ts')
    expect(types).toContain('EntitySourceFreshness')
    expect(types).toContain('source_freshness')
    expect(detail).toContain('trust-card')
    expect(detail).toContain('source_freshness')
    expect(detail).toContain('trustStatusLabel')
    expect(detail).toContain('Báo sai hoặc bổ sung nguồn')
  })

  it('entity detail renders backend JSON-LD as the schema source of truth', () => {
    const detail = src('pages/dia-diem/[id].vue')
    expect(detail).toContain('/seo/jsonld/${encodedId.value}')
    expect(detail).toContain('backendJsonLdScripts')
    expect(detail).toContain('return backendJsonLdScripts.value')
    expect(detail).not.toContain('backendJsonLdScripts.value.length ? backendJsonLdScripts.value : fallbackJsonLdScripts.value')
  })

  it('notification SSE uses cookie credentials without leaking bearer token in the URL', () => {
    const notifications = src('composables/useNotifications.ts')
    expect(notifications).toContain("new EventSource('/api/notifications/stream', { withCredentials: true })")
    expect(notifications).not.toContain('/api/notifications/stream?token=')
    expect(notifications).not.toContain('encodeURIComponent(token)')
    expect(notifications).toContain('activeSubscribers')
    expect(notifications).toContain('sseRetryDelay')
    expect(notifications).toContain('_scheduleReconnect')
    expect(notifications).toContain('_isDocumentHidden()')
    expect(notifications).toContain('visibilityListenerAttached')
  })

  it('personalized recommendation foundation tracks events and surfaces contextual blocks', () => {
    const api = src('../agent/public_api.py')
    expect(api).toContain('USER_EVENTS_FILE')
    expect(api).toContain('@router.post("/me/events"')
    expect(api).toContain('@router.get("/me/insights"')
    expect(api).toContain('@router.get("/me/recommendations/contextual"')
    expect(api).toContain('_build_user_interest_profile')
    expect(api).toContain('saved_entities')
    expect(api).toContain('user_visits')

    const events = src('composables/useUserEvents.ts')
    expect(events).toContain("trackEvent('search'")
    expect(events).toContain('trackEntityView')
    expect(events).toContain('trackSave')
    expect(events).toContain('/api/me/events')
    expect(events).toContain('fetchCsrf')

    const recs = src('composables/useContextualRecommendations.ts')
    expect(src('types/api.ts')).toContain('RecommendationResponse')
    expect(src('types/api.ts')).toContain('reason_vi')
    expect(recs).toContain('/api/me/recommendations/contextual')
    expect(recs).toContain('/api/entities/popular')
    expect(recs).toContain('/similar?limit=')
    expect(recs).toContain('reasonMapFromItems')

    const smart = src('components/SmartRecommendations.vue')
    expect(smart).toContain('useContextualRecommendations')
    expect(smart).toContain('smart-rec-reason')
    expect(smart).toContain('reasonFor')

    expect(src('pages/index.vue')).toContain('LazySmartRecommendations context="home"')
    expect(src('pages/tai-khoan.vue')).toContain('LazySmartRecommendations context="home"')
    expect(src('pages/dia-diem/[id].vue')).toContain('trackEntityView')
    expect(src('pages/dia-diem/[id].vue')).toContain('LazySmartRecommendations context="entity"')
    expect(src('pages/tim-kiem.vue')).toContain('trackSearch')
    expect(src('pages/tim-kiem.vue')).toContain('LazySmartRecommendations context="search"')
    expect(src('pages/cong-dong.vue')).toContain("trackEvent('community_view'")
    expect(src('pages/bai-viet/[id].vue')).toContain("trackEvent('post_view'")
  })

  it('unified search and ops cockpit contracts are wired in the frontend', () => {
    const unified = src('composables/useUnifiedSearch.ts')
    const apiTypes = src('types/api.ts')
    const publicApi = src('composables/usePublicApi.ts')
    const searchPage = src('pages/tim-kiem.vue')
    const topbar = src('components/SearchAutocomplete.vue')
    const admin = src('pages/admin/index.vue')
    const dataQuality = src('pages/admin/data-quality.vue')
    const journeyActions = src('composables/useJourneyActions.ts')

    expect(apiTypes).toContain('UnifiedSearchPayload')
    expect(apiTypes).toContain('EntityListQuery')
    expect(publicApi).toContain('/api/search')
    expect(publicApi).toContain('/api/entities')
    expect(publicApi).toContain('apiFetch<EntityListResponse>')
    expect(unified).toContain('publicApi.search')
    expect(unified).toContain('fetchEntitySuggestions')
    expect(unified).toContain('normalizedEntities')
    expect(searchPage).toContain('searchAll(q.value, 100)')
    expect(searchPage).toContain('useJourneyActions')
    expect(searchPage).toContain('searchRecoveryActions')
    expect(searchPage).toContain('searchSuccessActions')
    expect(searchPage).toContain('JourneyActionRail')
    expect(searchPage).toContain('zero_result')
    expect(searchPage).not.toContain('/api/search/posts')
    expect(searchPage).not.toContain('/api/search/users')
    expect(topbar).toContain('fetchEntitySuggestions')
    expect(topbar).not.toContain('/api/entities?q=')
    expect(admin).toContain('/admin-api/ops-summary')
    expect(admin).toContain('dash-ops')
    expect(admin).toContain('opsQueueTotal')
    expect(admin).toContain('schema_ok')
    expect(admin).toContain('shared_controls')
    expect(admin).toContain('adminOpsActions')
    expect(admin).toContain('JourneyActionRail')
    expect(dataQuality).toContain('dataQualityQueueActions')
    expect(dataQuality).toContain('applyFilters')
    expect(dataQuality).toContain('normalizeBucketQuery(route.query.bucket')
    expect(dataQuality).toContain('JourneyActionRail')
    expect(journeyActions).toContain('homepageDecisionActions')
    expect(journeyActions).toContain('userCpJourneyActions')
    expect(journeyActions).toContain('adminOpsActions')
    expect(journeyActions).toContain('dataQualityQueueActions')
  })

  it('release gate covers the QA plan before deploy', () => {
    const gate = src('../scripts/release_gate.ps1')
    expect(gate).toContain('dev_auth_check.ps1')
    expect(gate).toContain('sensitive_route_guard_matrix.py')
    expect(gate).toContain('test_qa_fixes.py')
    expect(gate).toContain('admin cockpit regressions')
    expect(gate).toContain('test_admin_p1_p2_regressions.py')
    expect(gate).toContain('check_migration_gate.py')
    expect(gate).toContain('quality_budget.py')
    expect(gate).toContain('TestSystemEndpointGate')
    expect(gate).toContain('TestEndpointAuthGuards')
    expect(gate).toContain('validate_data.py')
    expect(gate).toContain('vitest')
    expect(gate).toContain('vue-tsc')
    expect(gate).toContain('smoke_e2e_chrome.mjs')
    expect(gate).toContain('RequireE2E')
  })

  it('data validation report exposes text quality counters', () => {
    const validator = src('../scripts/validate_data.py')
    const audit = src('../scripts/deep_audit.py')
    const reportStart = validator.indexOf('print("\\nData quality:")')
    const reportBlock = validator.slice(reportStart, validator.indexOf('ss_examples', reportStart))
    expect(validator).toContain('has_bad_sentence_join')
    expect(validator).toContain('SAFE_DOT_TOKEN')
    expect(validator).toContain('is_external_gateway')
    expect(validator).toContain('has_approximate_coordinates')
    expect(validator).toContain('itinerary_declared_areas')
    expect(validator).toContain('itinerary_stop_ref')
    expect(reportBlock).toContain('"near_one_way_edges"')
    expect(reportBlock).toContain('"coordinate_clusters_precise"')
    expect(reportBlock).toContain('"text_repeated_sentence"')
    expect(reportBlock).toContain('"text_bad_sentence_join"')
    expect(reportBlock).toContain('"text_excessive_length"')
    expect(audit).toContain('VALID_TYPES = set(VALID_ENTITY_TYPES)')
    expect(audit).toContain('has_approximate_coordinates')
    expect(audit).toContain('Duplicate directed edges')
    expect(audit).toContain('Reciprocal near pairs')
    expect(audit).toContain('itinerary_stop_ref(stop)')
  })

  it('itinerary UI supports cross-region coverage metadata', () => {
    const constants = src('composables/useConstants.ts')
    const card = src('components/ItineraryCard.vue')
    const page = src('pages/lich-trinh/index.vue')
    const admin = src('pages/admin/lich-trinh.vue')
    expect(constants).toContain("'lien-vung'")
    expect(card).toContain('itineraryAreas')
    expect(card).toContain("'lien-vung': 'itinerary'")
    expect(page).toContain('itineraryMatchesArea')
    expect(page).toContain('areas.includes(key)')
    expect(admin).toContain('form.areas')
    expect(admin).toContain('coverageAreaOptions')
    expect(admin).toContain("'entity_id'")
    expect(admin).toContain('title: form.value.name.trim()')
    expect(admin).toContain('summary,')
    expect(src('types/index.ts')).toContain('entityId?: string')
    const detail = src('pages/lich-trinh/[id].vue')
    expect(detail).toContain('function stopIdentity')
    expect(detail).toContain('stop?.id || stop?.entityId || stop?.entity_id')
    expect(detail).toContain('canonicalUrl(entityPath(stopId))')
  })
})

describe('AdminCP P0 regressions', () => {
  const src = (file: string) => readFileSync(resolve(process.cwd(), file), 'utf8').replaceAll('\r\n', '\n')

  it('sidebar badges use the admin-api proxy', () => {
    const layout = src('layouts/admin.vue')
    expect(layout).toContain("'/admin-api/badge-counts'")
    expect(layout).not.toContain("'/admin/badge-counts'")
  })

  it('users page uses server-side search role filtering and total pagination', () => {
    const page = src('pages/admin/users.vue')
    expect(page).toContain("page: String(page.value)")
    expect(page).toContain("params.set('search', search.value)")
    expect(page).toContain("params.set('role_filter', roleFilter.value)")
    expect(page).toContain('totalUsers')
    expect(page).toContain('hasNextPage')
    expect(page).not.toContain("params.set('q', search.value)")
    expect(page).not.toContain("offset: String((page.value - 1) * limit)")
  })

  it('reports page loads all report statuses for history filters', () => {
    const page = src('pages/admin/bao-cao.vue')
    expect(page).toContain('/admin-api/reports?status=all&limit=200')
  })

  it('data quality confirmation reflects DB rollback support', () => {
    const page = src('pages/admin/data-quality.vue')
    expect(page).toContain('snapshot theo batch')
    expect(page).not.toContain('web/data.json')
    expect(page).not.toContain('KHÔNG thể hoàn tác tự động')
  })
})

describe('AdminCP P1/P2 regressions', () => {
  const src = (file: string) => readFileSync(resolve(process.cwd(), file), 'utf8').replaceAll('\r\n', '\n')

  it('data quality page supports reviewed decisions and decision history', () => {
    const page = src('pages/admin/data-quality.vue')
    expect(page).toContain('/admin-api/data-quality/decision')
    expect(page).toContain('decisionBusy')
    expect(page).toContain('dq-decision-badge')
    expect(page).toContain('decisionHistory')
    expect(page).toContain('dq-decision-history')
    expect(page).toContain('applied_count')
  })

  it('unclassified page uses the bulk place endpoint', () => {
    const page = src('pages/admin/chua-phan-loai.vue')
    expect(page).toContain('/admin-api/entities/bulk-place')
    expect(page).toContain('assigned_ids')
    expect(page).toContain('res.errors')
    expect(page).not.toContain('for (const id of ids) {\\n      await $fetch(`/admin-api/entities/${id}/place`')
  })

  it('moderation batch reject requires and sends a reason', () => {
    const page = src('pages/admin/kiem-duyet.vue')
    expect(page).toContain('batchRejectReason')
    expect(page).toContain('Nhập lý do từ chối hàng loạt')
    expect(page).toContain('body: { post_ids: [...batchSelected.value], action, reason }')
    expect(page).toContain('mod-batch-reason')
  })

  it('settings form exposes site settings history and rollback', () => {
    const form = src('components/admin/SettingsForm.vue')
    expect(form).toContain('/admin-api/site-settings-history')
    expect(form).toContain('rollbackHistory')
    expect(form).toContain('sf-history')
    expect(form).toContain('historyActionLabel')
    expect(form).toContain('await loadHistory()')
  })
})

describe('Page module imports', () => {
  it('imports index page', async () => {
    const mod = await import('../pages/index.vue')
    expect(mod.default).toBeTruthy()
  })

  it('imports du-lich page', async () => {
    const mod = await import('../pages/du-lich.vue')
    expect(mod.default).toBeTruthy()
  })

  it('imports san-pham page', async () => {
    const mod = await import('../pages/san-pham.vue')
    expect(mod.default).toBeTruthy()
  })

  it('imports tim-kiem page', async () => {
    const mod = await import('../pages/tim-kiem.vue')
    expect(mod.default).toBeTruthy()
  })

  it('imports cong-dong page', async () => {
    const mod = await import('../pages/cong-dong.vue')
    expect(mod.default).toBeTruthy()
  })

  it('imports settings page', async () => {
    const mod = await import('../pages/cai-dat.vue')
    expect(mod.default).toBeTruthy()
  })

  it('imports account page', async () => {
    const mod = await import('../pages/tai-khoan.vue')
    expect(mod.default).toBeTruthy()
  })

  it('imports user profile page', async () => {
    const mod = await import('../pages/nguoi-dung/[id].vue')
    expect(mod.default).toBeTruthy()
  })

  it('imports map page', async () => {
    const mod = await import('../pages/ban-do.vue')
    expect(mod.default).toBeTruthy()
  })

  it('imports lien-he page', async () => {
    const mod = await import('../pages/lien-he.vue')
    expect(mod.default).toBeTruthy()
  })
})

describe('Admin page smoke imports', () => {
  const pages: [string, () => Promise<any>][] = [
    ['admin/index', () => import('../pages/admin/index.vue')],
    ['admin/entities', () => import('../pages/admin/entities.vue')],
    ['admin/thong-ke', () => import('../pages/admin/thong-ke.vue')],
    ['admin/kiem-duyet', () => import('../pages/admin/kiem-duyet.vue')],
    ['admin/duyet-anh', () => import('../pages/admin/duyet-anh.vue')],
    ['admin/duyet-tu-hoc', () => import('../pages/admin/duyet-tu-hoc.vue')],
    ['admin/users', () => import('../pages/admin/users.vue')],
    ['admin/bao-cao', () => import('../pages/admin/bao-cao.vue')],
    ['admin/data-quality', () => import('../pages/admin/data-quality.vue')],
    ['admin/media', () => import('../pages/admin/media.vue')],
    ['admin/ai', () => import('../pages/admin/ai.vue')],
    ['admin/nhat-ky', () => import('../pages/admin/nhat-ky.vue')],
    ['admin/lich-trinh', () => import('../pages/admin/lich-trinh.vue')],
    ['admin/danh-ba', () => import('../pages/admin/danh-ba.vue')],
    ['admin/chua-phan-loai', () => import('../pages/admin/chua-phan-loai.vue')],
    ['admin/cai-dat/index', () => import('../pages/admin/cai-dat/index.vue')],
    ['admin/cai-dat/chao-mung', () => import('../pages/admin/cai-dat/chao-mung.vue')],
    ['admin/cai-dat/chat-ai', () => import('../pages/admin/cai-dat/chat-ai.vue')],
    ['admin/cai-dat/danh-muc', () => import('../pages/admin/cai-dat/danh-muc.vue')],
    ['admin/cai-dat/dieu-huong', () => import('../pages/admin/cai-dat/dieu-huong.vue')],
    ['admin/cai-dat/footer', () => import('../pages/admin/cai-dat/footer.vue')],
    ['admin/cai-dat/giao-dien', () => import('../pages/admin/cai-dat/giao-dien.vue')],
    ['admin/cai-dat/lien-he', () => import('../pages/admin/cai-dat/lien-he.vue')],
    ['admin/cai-dat/phap-ly', () => import('../pages/admin/cai-dat/phap-ly.vue')],
    ['admin/cai-dat/seo', () => import('../pages/admin/cai-dat/seo.vue')],
    ['admin/cai-dat/thong-bao', () => import('../pages/admin/cai-dat/thong-bao.vue')],
    ['admin/cai-dat/thuong-hieu', () => import('../pages/admin/cai-dat/thuong-hieu.vue')],
    ['admin/cai-dat/tinh-nang', () => import('../pages/admin/cai-dat/tinh-nang.vue')],
    ['admin/cai-dat/trang-chu', () => import('../pages/admin/cai-dat/trang-chu.vue')],
    ['admin/cai-dat/trang/index', () => import('../pages/admin/cai-dat/trang/index.vue')],
    ['admin/cai-dat/trang/[slug]', () => import('../pages/admin/cai-dat/trang/[slug].vue')],
    ['admin/cai-dat/tuyen-duong', () => import('../pages/admin/cai-dat/tuyen-duong.vue')],
  ]

  for (const [name, loader] of pages) {
    it(`imports ${name}`, async () => {
      const mod = await loader()
      expect(mod.default).toBeTruthy()
    })
  }

  it('imports admin layout', async () => {
    const mod = await import('../layouts/admin.vue')
    expect(mod.default).toBeTruthy()
  })
})
