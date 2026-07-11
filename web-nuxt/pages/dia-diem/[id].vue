<template>
  <section v-if="entity" class="entity-detail-page">
    <div class="scroll-progress" :style="{ transform: `scaleX(${progress})` }" aria-hidden="true" />
    <!-- Breadcrumb -->
    <nav class="breadcrumb" aria-label="Breadcrumb">
      <button type="button" class="bc-back" aria-label="Quay lại" @click="goBack">
        <span aria-hidden="true">←</span>
      </button>
      <ol>
        <li><NuxtLink to="/">Trang chủ</NuxtLink></li>
        <li><NuxtLink :to="typeBreadcrumbUrl">{{ typeMeta.label }}</NuxtLink></li>
        <li v-if="entity.place_area"><NuxtLink :to="`/khu-vuc/${entity.place_area}`">{{ areaName }}</NuxtLink></li>
        <li aria-current="page">{{ entity.name }}</li>
      </ol>
    </nav>

    <!-- Cover + Hero Image -->
    <div
      :class="['detail-cover', `cat-${typeMeta.cat}`, { 'has-cover-img': hasEntityImages }]"
      :style="!hasEntityImages ? { backgroundImage: heroPlaceholderBg } : undefined"
      :role="!hasEntityImages ? 'img' : undefined"
      :aria-label="!hasEntityImages ? 'Ảnh minh hoạ theo tông màu ' + typeMeta.label : undefined"
    >
      <NuxtImg v-if="hasEntityImages && isRemoteUrl(coverImage)" :src="coverImage" :alt="entity.name" class="dc-bg" loading="eager" fetchpriority="high" width="1200" height="600" sizes="sm:100vw md:100vw lg:960px xl:1200px" :role="hasEntityImages ? 'button' : undefined" :tabindex="hasEntityImages ? 0 : undefined" :aria-label="hasEntityImages ? `Xem ảnh ${entity.name}` : undefined" @load="($event.target as HTMLElement)?.classList.add('loaded')" @click="hasEntityImages && openCoverLightbox(0)" @keydown.enter="hasEntityImages && openCoverLightbox(0)" @keydown.space.prevent="hasEntityImages && openCoverLightbox(0)" />
      <img v-else-if="hasEntityImages" :src="coverImage" :alt="entity.name" class="dc-bg" loading="eager" fetchpriority="high" width="1200" height="600" :role="hasEntityImages ? 'button' : undefined" :tabindex="hasEntityImages ? 0 : undefined" :aria-label="hasEntityImages ? `Xem ảnh ${entity.name}` : undefined" @load="($event.target as HTMLElement)?.classList.add('loaded')" @click="hasEntityImages && openCoverLightbox(0)" @keydown.enter="hasEntityImages && openCoverLightbox(0)" @keydown.space.prevent="hasEntityImages && openCoverLightbox(0)" />
      <div v-if="coverImage" class="dc-overlay"></div>
      <div v-if="coverImage" class="dc-vignette" aria-hidden="true"></div>
      <span v-if="!hasEntityImages" class="dc-motif" aria-hidden="true" v-html="heroMotifSvg"></span>
      <div class="dc-inner">
        <span class="dc-type-row">
          <span class="dc-type-chip"><IconLine :name="typeMeta.icon" class="dc-emoji" />{{ typeMeta.label }}</span>
          <span v-if="entity.attributes?.ocop" class="dc-ocop-chip" :aria-label="`Sản phẩm OCOP ${entity.attributes.ocop}`">
            <IconLine name="star" /> OCOP {{ entity.attributes.ocop }}
          </span>
        </span>
        <span v-if="heroDateline" class="dc-eyebrow">{{ heroDateline }}</span>
        <h1>{{ entity.name }}</h1>
        <p v-if="heroHook" class="dc-hook">{{ heroHook }}</p>
        <p v-if="entity.place_name" class="dc-place"><NuxtLink v-if="entity.placeId" :to="`/xa-phuong/${entity.placeId}`" class="dc-place-link">{{ entity.place_name }}</NuxtLink><template v-else>{{ entity.place_name }}</template></p>
        <!-- declutter-3 T17 (B5d): Save/Share dời về sidebar .aside-actions (additive-first,
             verify xong mới xoá ở đây) — hero còn tối đa 3 nút hành-vi-chuyến-đi -->
        <div class="dc-actions">
          <ClientOnly>
            <div class="dc-trip">
              <button v-if="entity.type === 'event'" type="button" :class="['trip-btn', { active: rsvpGoing }]" :aria-pressed="rsvpGoing" :disabled="actionPending" @click="toggleRsvp">
                {{ rsvpGoing ? '✓ Sẽ đi' : '🎉 Tôi sẽ đi' }}<span v-if="rsvpCount" class="trip-count">{{ rsvpCount }}</span>
              </button>
              <template v-else>
                <button type="button" :class="['trip-btn', { active: visitStatus === 'visited' }]" :aria-pressed="visitStatus === 'visited'" :disabled="actionPending" @click="setVisit('visited')">✓ Đã đến</button>
                <button type="button" :class="['trip-btn', { active: visitStatus === 'want' }]" :aria-pressed="visitStatus === 'want'" :disabled="actionPending" @click="setVisit('want')">♡ Muốn đến</button>
              </template>
              <button type="button" :class="['trip-btn', { active: isFollowingPlace }]" :aria-pressed="isFollowingPlace" :disabled="actionPending" @click="toggleFollowPlace">{{ isFollowingPlace ? '🔔 Đang theo dõi' : '🔔 Theo dõi' }}</button>
            </div>
          </ClientOnly>
        </div>
      </div>
      <button type="button" v-if="hasEntityImages" class="dc-photo-btn" :aria-label="entityImages.length === 1 ? 'Xem ảnh' : `Xem ${entityImages.length} ảnh`" @click="openCoverLightbox()">
        <span class="dc-photo-icon" aria-hidden="true">&#128247;</span>
        {{ entityImages.length === 1 ? 'Xem ảnh' : `${entityImages.length} ảnh` }}
      </button>
      <div v-if="hasEntityImages && entityImages.length > 1" class="dc-thumbs">
        <template v-for="(src, i) in entityImages.slice(0, 4)" :key="src">
          <button type="button" class="dc-thumb-btn" :class="{ active: i === 0 }" :aria-label="`Xem ảnh ${i + 1} của ${entity.name}`" @click="openCoverLightbox(i)">
            <NuxtImg v-if="isRemoteUrl(src)" :src="src" :alt="`${entity.name} - ${i + 1}`" class="dc-thumb" loading="lazy" width="56" height="40" sizes="56px" decoding="async" @error="hideImage" />
            <img v-else :src="src" :alt="`${entity.name} - ${i + 1}`" class="dc-thumb" loading="lazy" width="56" height="40" decoding="async" @error="hideImage" />
          </button>
        </template>
        <button type="button" v-if="entityImages.length > 4" class="dc-thumb-more" :aria-label="`Xem thêm ${entityImages.length - 4} ảnh`" @click="openCoverLightbox(4)">
          +{{ entityImages.length - 4 }}
        </button>
      </div>
      <small v-if="imageCredit" class="dc-credit">{{ imageCredit }}</small>
      <small v-else-if="!hasEntityImages" class="dc-nophoto-note">Ảnh minh hoạ theo tông màu đặc trưng — chưa có ảnh thật cho địa điểm này.</small>
    </div>

    <!-- Photo Gallery (asymmetric grid for 2+ images) -->
    <LazyPhotoGallery
      v-if="hasEntityImages && entityImages.length >= 2"
      :images="entityImages"
      :alt="entity.name"
      class="detail-gallery"
      @open-lightbox="openCoverLightbox"
    />

    <LazyImageLightbox v-if="entityImages.length" v-model="lightboxOpen" :images="entityImages" :start-index="lbIndex" />

    <!-- Body -->
    <div class="detail-body">
      <article class="detail-main" aria-label="Thông tin chi tiết">
        <!-- Highlights quét nhanh (Baymard: 78% site thiếu; chống info bị chôn dưới fold) -->
        <div v-if="hasHighlights" class="highlights">
          <a v-if="entity.attributes?.phone" class="hl hl-action" :href="telHref(entity.attributes.phone)" :aria-label="`Gọi ${entity.name}`">📞 Gọi</a>
          <a v-if="zaloLink" class="hl hl-action" :href="zaloLink" target="_blank" rel="nofollow noopener" :aria-label="`Nhắn Zalo ${entity.name}`">💬 Zalo</a>
          <NuxtLink v-if="hasCoords" class="hl hl-action" :to="mapUrl" :aria-label="`Xem ${entity.name} trên bản đồ`">🗺️ Bản đồ</NuxtLink>
          <span v-if="entity.attributes?.hours" class="hl"><span aria-hidden="true">🕒</span> {{ entity.attributes.hours }}</span>
          <span v-if="addressText" class="hl"><span aria-hidden="true">📍</span> {{ addressText }}</span>
        </div>
        <p class="lead">{{ entity.summary }}</p>

        <!-- Highlight tagline -->
        <blockquote v-if="entity.attributes?.highlight" class="entity-highlight">
          <p>{{ entity.attributes.highlight }}</p>
        </blockquote>

        <!-- Mô tả chi tiết -->
        <div v-if="descriptionSections.length" class="entity-description" :class="{ 'rich-desc': hasRichDescription }">
          <div id="desc-content" class="desc-content" :class="{ expanded: descExpanded || totalDescParagraphs <= 5 }">
            <template v-for="(section, si) in descriptionSections" :key="si">
              <h2 v-if="section.level === 2" class="desc-heading">{{ section.heading }}</h2>
              <h3 v-else-if="section.level === 3" class="desc-subheading">{{ section.heading }}</h3>
              <p v-for="(para, pi) in section.paragraphs" :key="`${si}-${pi}`">{{ para }}</p>
            </template>
          </div>
          <button type="button" v-if="totalDescParagraphs > 5" class="desc-toggle" :aria-expanded="descExpanded" aria-controls="desc-content" @click="descExpanded = !descExpanded">
            <span class="desc-toggle-icon" :class="{ rotated: descExpanded }">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true"><polyline points="6 9 12 15 18 9"/></svg>
            </span>
            {{ descExpanded ? ss('labels.detail.desc_collapse', 'Thu gọn') : ss('labels.detail.desc_expand', 'Đọc thêm') }}
          </button>
        </div>

        <!-- Extra content sections from attributes -->
        <div v-if="extraContentSections.length" class="extra-content">
          <div v-for="sec in extraContentSections" :key="sec.title" class="extra-section">
            <h2 class="section-subtitle"><span aria-hidden="true">{{ sec.icon }}</span> {{ sec.title }}</h2>
            <p>{{ sec.text }}</p>
          </div>
        </div>

        <!-- Lưu ý thực tế — Scenarios 2,3,6,9: practical tips for food/family/OCOP/delegation -->
        <div v-if="practicalTips.length" class="practical-tips reveal">
          <h2 class="section-subtitle sediment-head">📋 {{ ss('labels.detail.practical_tips_heading', 'Lưu ý thực tế') }}</h2>
          <ul class="pt-list">
            <li v-for="tip in practicalTips" :key="tip.icon" class="pt-item">
              <span class="pt-icon">{{ tip.icon }}</span>
              <div class="pt-content">
                <strong>{{ tip.label }}</strong>
                <span>{{ tip.value }}</span>
              </div>
            </li>
          </ul>
        </div>

        <!-- Best time callout -->
        <!-- declutter-1 T6: best_time chỉ render 1 chỗ (callout này); đã bỏ khỏi practicalTips
             nên guard chống-trùng cũ không cần nữa. -->
        <div v-if="bestTimeText" class="best-time-callout reveal">
          <span class="btc-icon" aria-hidden="true">🕐</span>
          <div class="btc-body">
            <strong>Thời điểm lý tưởng</strong>
            <span>{{ bestTimeText }}</span>
          </div>
        </div>

        <!-- Know Before You Go -->
        <KnowBeforeYouGo v-if="entity.attributes" :attributes="entity.attributes" :entity-type="entity.type" />

        <!-- Food specialties (dish/product only) -->
        <div v-if="foodSpecialties.length" class="food-specialties reveal">
          <h2 class="section-subtitle sediment-head">🍽️ Nên thử</h2>
          <ul class="fs-list">
            <li v-for="item in foodSpecialties" :key="item.label" class="fs-item">
              <span class="fs-icon" aria-hidden="true">{{ item.icon }}</span>
              <div class="fs-content">
                <strong>{{ item.label }}</strong>
                <span>{{ item.value }}</span>
              </div>
            </li>
          </ul>
        </div>

        <!-- Month strip -->
        <div v-if="entity.season?.months" class="season-block reveal">
          <h2 class="section-subtitle sediment-head">{{ ss('labels.detail.season_heading', 'Mùa vụ') }}</h2>
          <div class="month-strip" role="group" aria-label="Lịch mùa vụ theo tháng">
            <span
              v-for="m in 12"
              :key="m"
              :class="['ms-cell', { on: entity.season?.months?.includes(m), peak: entity.season?.peak?.includes(m) }]"
              :aria-label="`Tháng ${m}${entity.season?.peak?.includes(m) ? ' — rộ nhất' : entity.season?.months?.includes(m) ? ' — có mùa' : ''}`"
            >T{{ m }}</span>
          </div>
          <div class="ms-legend">
            <span class="ms-cell on ms-legend-swatch"></span> {{ ss('labels.detail.season_legend_in', 'Có mùa') }}
            <span class="ms-cell on peak ms-legend-swatch"></span> {{ ss('labels.detail.season_legend_peak', 'Rộ nhất') }}
          </div>
          <p v-if="entity.attributes?.season_note" class="season-note">{{ entity.attributes.season_note }}</p>
          <p v-if="entity.attributes?.peak_event" class="season-note peak-event">🎉 {{ entity.attributes.peak_event }}</p>
        </div>

        <!-- Relationships -->
        <div v-if="relationships.length" class="rel-block reveal">
          <h2 class="sediment-head">{{ ss('labels.detail.relationships_heading', 'Liên kết') }}</h2>
          <ul class="rel-list">
            <li v-for="rel in relationships" :key="`${rel.target_id}-${rel.rel_type}`">
              <span class="rel-label">{{ rel.label }}</span>
              <span class="rel-main">
                <NuxtLink :to="entityPath(rel.target_id)">{{ rel.target_name }}</NuxtLink>
                <small v-if="rel.distance_km" class="rel-distance">{{ rel.distance_km }} km</small>
              </span>
            </li>
          </ul>
          <button
            v-if="hasMoreRelationships"
            class="rel-more"
            type="button"
            :disabled="loadingRelationships"
            @click="loadMoreRelationships"
          >
            {{ loadingRelationships ? ss('labels.detail.relationships_loading', 'Đang tải...') : `${ss('labels.detail.relationships_more', 'Xem thêm')} ${remainingRelationshipCount}` }}
          </button>
          <p v-if="relError" class="empty" role="alert">{{ relError }}</p>
        </div>

        <!-- Nearby entities (same area, different type) -->
        <NuxtErrorBoundary>
          <NearbyEntities v-if="entity.place_area && ff('nearby')" :entity-id="id" :entity-type="entity.type" :area="entity.place_area" />
        </NuxtErrorBoundary>

        <!-- Community Reviews -->
        <NuxtErrorBoundary>
          <ClientOnly>
            <LazyEntityReviews v-if="ff('reviews')" :entity-id="id" :entity-name="entity.name" />
            <template #fallback><div class="detail-skeleton"><div class="sk-title"></div><div class="sk-line w80"></div><div class="sk-line w60"></div></div></template>
          </ClientOnly>
        </NuxtErrorBoundary>

        <!-- Community Feed -->
        <NuxtErrorBoundary>
          <ClientOnly>
            <LazyEntityFeed :entity-id="id" :entity-name="entity.name" />
            <template #fallback><div class="detail-skeleton"><div class="sk-title"></div><div class="sk-line w90"></div><div class="sk-line w70"></div></div></template>
          </ClientOnly>
        </NuxtErrorBoundary>

        <!-- AI Travel Tips -->
        <NuxtErrorBoundary>
          <ClientOnly>
            <LazyAITravelTips v-if="entity && ff('ai_tips')" :entity-id="id" :entity-name="entity.name" />
            <template #fallback><div class="detail-skeleton"><div class="sk-title"></div><div class="sk-line w80"></div></div></template>
          </ClientOnly>
        </NuxtErrorBoundary>

        <!-- AI Recommendations -->
        <NuxtErrorBoundary>
          <ClientOnly>
            <LazySmartRecommendations context="entity" :entity-id="id" :title="ss('labels.detail.recommendations_title', 'Bạn cũng có thể thích')" :limit="4" />
            <template #fallback><div class="detail-skeleton"><div class="sk-grid"><div class="sk-card"></div><div class="sk-card"></div><div class="sk-card"></div><div class="sk-card"></div></div></div></template>
          </ClientOnly>
        </NuxtErrorBoundary>
      </article>

      <!-- Sidebar -->
      <aside class="detail-aside" aria-label="Thông tin bổ sung">
        <!-- Contact Widget (sticky, replaces old contact-row on desktop) -->
        <LazyContactWidget :entity="entity" class="detail-contact-widget" />

        <!-- declutter-3 T17 (B5d): Save/Share dời từ hero về sidebar (desktop) —
             state sync qua useFavorites, cùng composable với JourneyBar -->
        <ClientOnly>
          <div class="aside-actions">
            <SaveButton :entity="entity" :show-label="true" />
            <ShareButton :title="entity.name" :text="entity.summary" />
          </div>
        </ClientOnly>

        <!-- OCOP highlight -->
        <div v-if="entity.attributes?.ocop" class="ocop-highlight">
          <div class="ocop-stars">
            <span v-for="s in ocopStars" :key="s" class="ocop-star">⭐</span>
          </div>
          <strong>{{ ss('labels.detail.ocop_product_prefix', 'Sản phẩm OCOP') }} {{ entity.attributes.ocop }}</strong>
          <small>{{ ss('labels.detail.ocop_program', 'Chương trình Mỗi xã Một sản phẩm') }}</small>
        </div>

        <!-- Rating -->
        <div v-if="entity.attributes?.rating" class="rating-display">
          <div class="rd-stars">
            <span v-for="s in 5" :key="s" :class="['rd-star', { filled: s <= Math.round(Number(entity.attributes.rating)) }]">★</span>
          </div>
          <span class="rd-score">{{ entity.attributes.rating }}</span>
          <span v-if="entity.attributes?.review_count" class="rd-count">({{ entity.attributes.review_count }} đánh giá)</span>
        </div>

        <h2 class="facts-heading sediment-head"><span class="facts-heading-icon" aria-hidden="true">📑</span>{{ ss('labels.detail.info_heading', 'Thông tin') }}</h2>
        <div class="facts-card">
          <div class="fact-group">
            <h3 class="fg-label">Tổng quan</h3>
            <div class="fact">
              <IconLine :name="typeMeta.icon" class="fact-ic" />
              <span class="k">{{ ss('labels.detail.fact_type', 'Loại') }}</span>
              <span class="v">{{ typeMeta.label }}</span>
            </div>
            <div v-if="entity.place_name" class="fact">
              <span class="fact-ic" aria-hidden="true">📍</span>
              <span class="k">{{ ss('labels.detail.fact_place', 'Địa điểm') }}</span>
              <span class="v">
                <NuxtLink v-if="entity.placeId" :to="`/xa-phuong/${entity.placeId}`" class="fact-link">{{ entity.place_name }}</NuxtLink>
                <template v-else>{{ entity.place_name }}</template>
              </span>
            </div>
            <div v-if="entity.place_area" class="fact">
              <span class="fact-ic" aria-hidden="true">🗺️</span>
              <span class="k">{{ ss('labels.detail.fact_area', 'Khu vực') }}</span>
              <span class="v">
                <NuxtLink :to="`/khu-vuc/${entity.place_area}`" class="fact-link">{{ areaName }}</NuxtLink>
              </span>
            </div>
            <div v-if="entity.season" class="fact">
              <span class="fact-ic" aria-hidden="true">🌤️</span>
              <span class="k">{{ ss('labels.detail.fact_season', 'Mùa') }}</span>
              <span class="v">{{ seasonLabel }}</span>
            </div>
          </div>

          <div v-if="hasVisitFacts" class="fact-group">
            <h3 class="fg-label">Tham quan</h3>
            <div v-if="entity.attributes?.hours" class="fact">
              <span class="fact-ic" aria-hidden="true">🕒</span>
              <span class="k">{{ ss('labels.detail.fact_hours', 'Giờ mở cửa') }}</span>
              <span class="v">{{ entity.attributes.hours }}</span>
            </div>
            <div v-if="entity.attributes?.price" class="fact">
              <span class="fact-ic" aria-hidden="true">💰</span>
              <span class="k">{{ ss('labels.detail.fact_price', 'Giá tham khảo') }}</span>
              <span class="v">{{ entity.attributes.price }}</span>
            </div>
            <div v-if="entity.attributes?.fee" class="fact">
              <span class="fact-ic" aria-hidden="true">🎫</span>
              <span class="k">{{ ss('labels.detail.fact_fee', 'Phí vào cửa') }}</span>
              <span class="v">{{ entity.attributes.fee }}</span>
            </div>
            <div v-if="entity.attributes?.suggested_duration" class="fact">
              <span class="fact-ic" aria-hidden="true">⏱️</span>
              <span class="k">Thời gian tham quan</span>
              <span class="v">{{ entity.attributes.suggested_duration }}</span>
            </div>
            <div v-if="entity.attributes?.transport" class="fact">
              <span class="fact-ic" aria-hidden="true">🚗</span>
              <span class="k">{{ ss('labels.detail.fact_transport', 'Di chuyển') }}</span>
              <span class="v">{{ entity.attributes.transport }}</span>
            </div>
          </div>

          <div v-if="hasContactFacts" class="fact-group">
            <h3 class="fg-label">Liên hệ</h3>
            <div v-if="entity.attributes?.phone" class="fact">
              <span class="fact-ic" aria-hidden="true">📞</span>
              <span class="k">{{ ss('labels.detail.fact_phone', 'Liên hệ') }}</span>
              <span class="v"><a :href="telHref(entity.attributes.phone)" class="fact-link">{{ entity.attributes.phone }}</a><button type="button" class="fact-copy" @click="copyText(entity.attributes.phone!, 'số điện thoại')" aria-label="Sao chép số điện thoại" title="Sao chép"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg></button></span>
            </div>
            <div v-if="entity.attributes?.address" class="fact">
              <span class="fact-ic" aria-hidden="true">🏠</span>
              <span class="k">{{ ss('labels.detail.fact_address', 'Địa chỉ') }}</span>
              <span class="v">{{ entity.attributes.address }}<button type="button" class="fact-copy" @click="copyText(entity.attributes.address!, 'địa chỉ')" aria-label="Sao chép địa chỉ" title="Sao chép"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg></button></span>
            </div>
            <div v-if="entity.attributes?.coords_approximate && hasCoords" class="fact fact-approx">
              <span class="fact-ic" aria-hidden="true">📍</span>
              <span class="k">{{ ss('labels.detail.fact_location', 'Vị trí') }}</span>
              <span class="v">{{ ss('labels.detail.coords_approximate', 'Gần đúng (trung tâm xã/phường) — chưa có toạ độ chính xác') }}</span>
            </div>
            <div v-if="entity.attributes?.website" class="fact">
              <span class="fact-ic" aria-hidden="true">🔗</span>
              <span class="k">{{ ss('labels.detail.fact_website', 'Website') }}</span>
              <span class="v"><a :href="safeUrl(entity.attributes.website)" target="_blank" rel="noopener nofollow" class="fact-link website-link">{{ entity.attributes?.website?.replace(/^https?:\/\//, '') }}</a></span>
            </div>
          </div>

          <div v-if="hasFeatureFacts" class="fact-group">
            <h3 class="fg-label">Đặc điểm</h3>
            <div v-if="entity.attributes?.amenities" class="fact">
              <span class="fact-ic" aria-hidden="true">✅</span>
              <span class="k">{{ ss('labels.detail.fact_amenities', 'Tiện ích') }}</span>
              <span class="v">{{ Array.isArray(entity.attributes.amenities) ? entity.attributes.amenities.join(', ') : entity.attributes.amenities }}</span>
            </div>
            <div v-if="entity.attributes?.price_range" class="fact">
              <span class="fact-ic" aria-hidden="true">💵</span>
              <span class="k">Mức giá</span>
              <span class="v">{{ entity.attributes.price_range }}</span>
            </div>
          </div>
        </div>

        <!-- P0-5: byline biên tập (Who) — always-on, ngoài trust-card -->
        <p class="entity-byline"><IconLine name="user" /> {{ bylineText }} · <strong>Ban biên tập vinhlong360</strong> · <NuxtLink to="/gioi-thieu#ban-bien-tap">phương pháp biên tập</NuxtLink></p>

        <!-- Liên hệ trực tiếp (showcase — KHÔNG đặt hàng/giỏ hàng/thanh toán on-site) -->
        <section v-if="trustVisible" class="trust-card" aria-labelledby="trust-card-title">
          <div class="trust-card-head">
            <h2 id="trust-card-title" class="sediment-head">Độ tin cậy dữ liệu</h2>
            <span :class="['trust-status', trustStatusTone]">{{ trustStatusLabel }}</span>
          </div>
          <dl class="trust-list">
            <div>
              <dt>Nguồn</dt>
              <dd>
                <a v-if="trustSourceUrl" :href="safeUrl(trustSourceUrl)" target="_blank" rel="noopener nofollow">{{ trustSourceTitle }}</a>
                <span v-else>{{ trustSourceTitle }}</span>
              </dd>
            </div>
            <div>
              <dt>Cập nhật</dt>
              <dd>{{ trustUpdatedLabel }}</dd>
            </div>
          </dl>
          <p class="trust-note">{{ trustNote }}</p>
          <NuxtLink class="trust-report" :to="reportUrl">Báo sai hoặc bổ sung nguồn</NuxtLink>
        </section>

        <!-- declutter-3 T17 (B5c/D12): đúng 1 kênh Báo sai mỗi trang — trust-card ưu tiên;
             fallback này chỉ hiện khi entity KHÔNG có nguồn (trust-card ẩn) -->
        <NuxtLink v-if="!trustVisible" class="quality-report" :to="reportUrl">{{ ss('labels.detail.cta_report', 'Báo sai dữ liệu') }}</NuxtLink>

        <NuxtErrorBoundary>
          <ClientOnly>
            <LazyAIBestTime v-if="ff('ai_best_time')" :entity-id="id" :entity-name="entity.name" />
          </ClientOnly>
        </NuxtErrorBoundary>

        <!-- Contextual next steps -->
        <div class="next-steps">
          <h2 class="ns-title sediment-head">{{ ss('labels.detail.next_steps_title', 'Bước tiếp theo') }}</h2>
          <!-- Save affordance lives in the hero (SaveButton) — avoid a second, divergent toggle here.
               Next step is the active-planning CTA, labeled to distinguish it from "save for later". -->
        <NuxtLink :to="planAddUrl" no-prefetch class="ns-action">📋 {{ ss('labels.detail.next_add_itinerary', 'Thêm vào lịch trình') }}</NuxtLink>
          <!-- declutter-1 T5: buy-contact dời từ contact-row (đã bỏ — desktop bị CSS ẩn,
               mobile ContactWidget che); ContactWidget không có kênh hỏi-mua nên giữ ở đây. -->
          <a v-if="buyContactUrl" :href="buyContactUrl" target="_blank" rel="nofollow noopener" class="ns-action" :aria-label="`Hỏi mua ${entity.name}`">🛒 {{ ss('labels.detail.cta_buy_contact', 'Hỏi mua trực tiếp') }}</a>
          <NuxtLink v-if="entity.type !== 'accommodation'" to="/luu-tru" class="ns-action">🏡 {{ ss('labels.detail.next_find_stay', 'Tìm chỗ ở gần đây') }}</NuxtLink>
        <NuxtLink :to="mapUrl" no-prefetch class="ns-action">🗺️ {{ ss('labels.detail.next_view_map', 'Xem trên bản đồ') }}</NuxtLink>
          <NuxtLink to="/tuyen-duong" class="ns-action">🛤️ {{ ss('labels.detail.next_route', 'Tuyến đường gợi ý') }}</NuxtLink>
          <!-- declutter-3 T17 (B5e): claim-cta DỜI vào next-steps (di chuyển, không bỏ) -->
          <NuxtLink :to="claimUrl" class="ns-action claim-cta">🏷️ {{ ss('labels.detail.cta_claim', 'Đây là cơ sở của tôi — đăng ký quản lý') }}</NuxtLink>
        </div>
      </aside>
    </div>

    <!-- Sticky mobile CTA bar (always visible, thumb zone).
         Always renders so mobile users never hit a "CTA void"; when there's no
         phone/Zalo/map, fall back to the guaranteed next action (add to itinerary). -->
    <div class="sticky-cta-bar">
      <a v-if="entity.attributes?.phone" class="scta-phone" :href="telHref(entity.attributes.phone)" aria-label="Gọi điện thoại">📞 Gọi</a>
      <a v-if="zaloLink" class="scta-zalo" :href="zaloLink" target="_blank" rel="nofollow noopener" aria-label="Nhắn Zalo">💬 Zalo</a>
      <NuxtLink v-if="hasCoords" class="scta-map" :to="mapUrl" aria-label="Xem trên bản đồ">🗺️ Bản đồ</NuxtLink>
      <NuxtLink v-if="!hasStickyContact" :to="planAddUrl" no-prefetch class="scta-plan" aria-label="Thêm vào lịch trình">📋 {{ ss('labels.detail.next_add_itinerary', 'Thêm vào lịch trình') }}</NuxtLink>
    </div>
  </section>
  <section v-else-if="fetchError" class="page">
    <EmptyState
      :icon="fetchError.statusCode === 404 ? '🔍' : '⚠️'"
      :title="fetchError.statusCode === 404 ? 'Không tìm thấy địa điểm này' : 'Không thể tải dữ liệu'"
      :message="fetchError.statusCode === 404
        ? 'Có thể nội dung đã được di chuyển hoặc đường dẫn chưa đúng. Bạn thử khám phá các điểm đến khác nhé.'
        : 'Đã có lỗi khi tải dữ liệu. Vui lòng thử lại sau.'"
      :tone="fetchError.statusCode === 404 ? undefined : 'error'"
    >
      <template #actions>
        <button v-if="fetchError.statusCode !== 404" type="button" class="btn btn-primary" @click="refreshEntity()">Thử lại</button>
        <NuxtLink to="/du-lich" class="btn btn-primary">Khám phá điểm đến</NuxtLink>
        <NuxtLink to="/" class="btn btn-ghost">Về trang chủ</NuxtLink>
      </template>
    </EmptyState>
  </section>
  <section v-else class="page">
    <EmptyState icon="🔍" title="Không tìm thấy địa điểm này" message="Có thể nội dung đã được di chuyển hoặc đường dẫn chưa đúng. Bạn thử khám phá các điểm đến khác nhé.">
      <template #actions>
        <NuxtLink to="/du-lich" class="btn btn-primary">Khám phá điểm đến</NuxtLink>
        <NuxtLink to="/" class="btn btn-ghost">Về trang chủ</NuxtLink>
      </template>
    </EmptyState>
  </section>
</template>

<script setup lang="ts">
import type { Entity } from '~/types'
import { TYPE_META, AREA_META, REL_FWD, REL_BWD } from '~/composables/useConstants'
import { seasonText } from '~/composables/useSeason'
import { generateCategoryPlaceholder, generateCategoryIcon } from '~/composables/useCategoryPlaceholder'
import { entityStoryTeaser } from '~/composables/useEntityStory'

useReveal()
const { progress } = useScrollProgress()
const { enabled: ff } = useFeature()
const { get: ss } = useSiteSettings()

const route = useRoute()
const router = useRouter()
const id = computed(() => normalizeRouteParam(route.params.id))
const encodedId = computed(() => encodePathId(id.value))

// ── Đã-đi/Muốn-đi + theo-dõi địa-điểm (Tier-1 MXH) ──
const { isLoggedIn, authHeaders } = useAuth()
const { openAuth } = useAuthModal()
const { show: _showToast } = useToast()

async function copyText(text: string, label: string) {
  try {
    await navigator.clipboard.writeText(text)
    _showToast(`Đã sao chép ${label}`, 'success')
  } catch {
    _showToast('Không thể sao chép', 'error')
  }
}

const visitStatus = ref<string | null>(null)
const isFollowingPlace = ref(false)
const rsvpGoing = ref(false)
const rsvpCount = ref(0)
const actionPending = ref(false)

async function toggleRsvp() {
  if (!isLoggedIn.value) { openAuth(() => toggleRsvp()); return }
  if (actionPending.value) return
  actionPending.value = true
  const prevGoing = rsvpGoing.value
  const prevCount = rsvpCount.value
  rsvpGoing.value = !prevGoing
  rsvpCount.value += prevGoing ? -1 : 1
  try {
    const r = await $fetch<{ going: boolean; count: number }>(`/api/events/${encodeURIComponent(id.value)}/rsvp`, { method: 'POST', headers: authHeaders() })
    rsvpGoing.value = r.going
    rsvpCount.value = r.count
    if (r.going) _showToast('Đã đăng ký đi sự kiện này 🎉', 'success')
  } catch { rsvpGoing.value = prevGoing; rsvpCount.value = prevCount; _showToast('Không thể đăng ký, thử lại', 'error') }
  finally { actionPending.value = false }
}

async function setVisit(status: 'visited' | 'want') {
  if (!isLoggedIn.value) { openAuth(() => setVisit(status)); return }
  if (actionPending.value) return
  actionPending.value = true
  const prev = visitStatus.value
  try {
    if (visitStatus.value === status) {
      visitStatus.value = null
      await $fetch(`/api/me/visits/${encodeURIComponent(id.value)}`, { method: 'DELETE', headers: authHeaders() })
    } else {
      visitStatus.value = status
      await $fetch('/api/me/visits', { method: 'POST', headers: authHeaders(), body: { entity_id: id.value, status } })
      _showToast(status === 'visited' ? 'Đã đánh dấu Đã đến' : 'Đã thêm vào Muốn đến', 'success')
    }
  } catch { visitStatus.value = prev; _showToast('Không thể lưu, thử lại', 'error') }
  finally { actionPending.value = false }
}

async function toggleFollowPlace() {
  if (!isLoggedIn.value) { openAuth(() => toggleFollowPlace()); return }
  if (actionPending.value) return
  actionPending.value = true
  const prev = isFollowingPlace.value
  isFollowingPlace.value = !prev
  try {
    await $fetch(`/api/follow/entity/${encodeURIComponent(id.value)}`, { method: 'POST', headers: authHeaders() })
    if (!prev) _showToast('Đang theo dõi — sẽ báo khi có bài mới', 'success')
  } catch { isFollowingPlace.value = prev; _showToast('Không thể theo dõi, thử lại', 'error') }
  finally { actionPending.value = false }
}

const { track: trackRecent } = useRecentlyViewed()
const { trackEntityView } = useUserEvents()

function trackCurrentEntity() {
  if (!entity.value) return
  trackRecent(entity.value)
  trackEntityView(entity.value, 'entity')
}

onMounted(async () => {
  trackCurrentEntity()
  if (!isLoggedIn.value) return
  const tasks: Promise<void>[] = [
    $fetch<{ status: string | null }>(`/api/me/visits/check/${encodeURIComponent(id.value)}`, { headers: authHeaders() })
      .then(v => { visitStatus.value = v?.status ?? null }).catch(() => {}),
    $fetch<{ following: { target_id: string }[] }>('/api/following', { headers: authHeaders() })
      .then(f => { isFollowingPlace.value = (f?.following || []).some(x => String(x.target_id) === id.value) }).catch(() => {}),
  ]
  if (entity.value?.type === 'event') {
    tasks.push(
      $fetch<{ count: number; going: boolean }>(`/api/events/${encodeURIComponent(id.value)}/rsvp`, { headers: authHeaders() })
        .then(r => { rsvpGoing.value = r.going; rsvpCount.value = r.count }).catch(() => {}),
    )
  }
  await Promise.all(tasks)
})

const RELATIONSHIP_BATCH_SIZE = 24

const goBack = () => goBackOr('/du-lich')

const { data: entity, error: fetchError, refresh: refreshEntity } = await useAsyncData(
  computed(() => `entity-${id.value}`),
  () => apiFetch<Entity>(`/api/entities/${encodedId.value}`),
  { watch: [id], deep: false }
)

type JsonLdPayload = Record<string, unknown> | Record<string, unknown>[]

const { data: backendJsonLd } = await useAsyncData(
  computed(() => `entity-jsonld-${id.value}`),
  () => apiFetch<JsonLdPayload>(`/seo/jsonld/${encodedId.value}`).catch(() => null),
  { watch: [id], deep: false }
)

// SSR: throw 404 so the server responds with proper status code.
// Client-side: show error state in-page (fetchError ref drives the template).
if (import.meta.server && fetchError.value) {
  throw createError({ statusCode: 404, statusMessage: 'Không tìm thấy nội dung' })
}

watch(() => entity.value?.id, () => trackCurrentEntity())

const typeMeta = computed(() => {
  if (!entity.value) return { emoji: '•', icon: 'pin', label: '', cat: 'place' }
  return TYPE_META[entity.value.type] || { emoji: '•', icon: 'pin', label: entity.value.type, cat: 'place' }
})

const areaName = computed(() => {
  const area = entity.value ? getEntityArea(entity.value) : ''
  return AREA_META[area]?.name || area || ''
})

const entityImages = computed(() => {
  const imgs = entity.value?.images
  return Array.isArray(imgs) ? imgs.filter(Boolean) : []
})
const hasEntityImages = computed(() => entityImages.value.length > 0)

const coverImage = computed(() => {
  const first = entityImages.value[0]
  if (first) return first
  return `/img/cat/${typeMeta.value.cat}.jpg`
})

// No-photo "phù sa" hero: per-entity hash-seeded gradient (same system as EntityCard),
// promoted to full-bleed hero scale. Replaces the flat shared /img/cat/*.jpg fallback.
const heroPlaceholderBg = computed(() =>
  entity.value ? generateCategoryPlaceholder(entity.value.id, typeMeta.value.cat) : '')
// Oversized off-centre category motif glyph (same watermark system as EntityHeroPlaceholder)
// so the no-photo hero reads as an intentional editorial cover, not a bare gradient.
const heroMotifSvg = computed(() => generateCategoryIcon(typeMeta.value.cat))
// Editorial dateline eyebrow: "{TYPE} · {AREA}" (area from the page's own resolver).
const heroDateline = computed(() =>
  areaName.value ? `${typeMeta.value.label} · ${areaName.value}` : typeMeta.value.label)
// Cover-story hook (one line): highlight → famous_for → first sentence of description.
const heroHook = computed(() => {
  if (!entity.value) return ''
  const t = entityStoryTeaser(entity.value)
  return t && t !== entity.value.name ? t : ''
})


const imageCredit = computed(() => {
  const credits = entity.value?.image_credits
  if (!Array.isArray(credits) || !credits.length) return ''
  const c = credits[0]
  if (!c) return ''
  return c.author ? `${c.author} · ${c.license || 'CC'}` : ''
})

const lightboxOpen = ref(false)
const lbIndex = ref(0)
function openCoverLightbox(idx = 0) {
  if (!entityImages.value.length) return
  lbIndex.value = typeof idx === 'number' ? idx : 0
  lightboxOpen.value = true
}

function hideImage(payload: Event | string) {
  if (typeof payload === 'string') return
  const img = payload.target
  if (img instanceof HTMLImageElement) img.style.display = 'none'
}

const TYPE_BREADCRUMB: Record<string, string> = {
  product: '/san-pham', experience: '/du-lich', attraction: '/du-lich',
  dish: '/du-lich', craft_village: '/du-lich', accommodation: '/luu-tru',
  organization: '/danh-ba', place: '/xa-phuong',
}
const typeBreadcrumbUrl = computed(() => {
  const type = entity.value?.type
  return type ? (TYPE_BREADCRUMB[type] || '/du-lich') : '/du-lich'
})

const seasonLabel = computed(() => seasonText(entity.value?.season))

// P0-3: bỏ paragraph description đầu nếu chỉ lặp lại summary (đã render làm lead
// phía trên) — giết double-print verbatim (description==summary / body in lại lead).
const _normText = (s: unknown) => String(s ?? '').replace(/\s+/g, ' ').trim().toLowerCase()
const descriptionBlocks = computed<string[]>(() => {
  const desc = entity.value?.description
  if (!desc || typeof desc !== 'string') return []
  let blocks = desc.split(/\n\s*\n/).map(b => b.trim()).filter(b => b.length > 0)
  const summary = entity.value?.summary
  if (summary && blocks.length && _normText(blocks[0]) === _normText(summary)) {
    blocks = blocks.slice(1)
  }
  return blocks
})

const descriptionParagraphs = computed(() => descriptionBlocks.value)

interface DescSection { level: 0 | 2 | 3; heading: string; paragraphs: string[] }
const descriptionSections = computed<DescSection[]>(() => {
  const blocks = descriptionBlocks.value
  if (!blocks.length) return []
  const sections: DescSection[] = []
  let current: DescSection = { level: 0, heading: '', paragraphs: [] }
  for (const block of blocks) {
    const h2 = block.match(/^##\s+(.+)$/)
    const h3 = block.match(/^###\s+(.+)$/)
    if (h3) {
      if (current.paragraphs.length || current.heading) sections.push(current)
      current = { level: 3, heading: h3[1] ?? '', paragraphs: [] }
    } else if (h2) {
      if (current.paragraphs.length || current.heading) sections.push(current)
      current = { level: 2, heading: h2[1] ?? '', paragraphs: [] }
    } else {
      current.paragraphs.push(block)
    }
  }
  if (current.paragraphs.length || current.heading) sections.push(current)
  return sections
})
const hasRichDescription = computed(() => descriptionSections.value.some(s => s.level > 0))
const totalDescParagraphs = computed(() => descriptionSections.value.reduce((n, s) => n + s.paragraphs.length + (s.heading ? 1 : 0), 0))

const descExpanded = ref(false)

const extraContentSections = computed(() => {
  const a = entity.value?.attributes
  if (!a) return []
  const sections: { icon: string; title: string; text: string }[] = []
  if (a.significance && typeof a.significance === 'string')
    sections.push({ icon: '🏛️', title: 'Ý nghĩa', text: a.significance })
  if (a.atmosphere && typeof a.atmosphere === 'string')
    sections.push({ icon: '🌿', title: 'Không gian', text: a.atmosphere })
  if (a.famous_for && typeof a.famous_for === 'string')
    sections.push({ icon: '⭐', title: 'Nổi tiếng với', text: a.famous_for })
  if (a.travel_tips && typeof a.travel_tips === 'string')
    sections.push({ icon: '💡', title: 'Mẹo du lịch', text: a.travel_tips })
  return sections
})

// GĐ13.2: link Zalo từ attributes.zalo (số hoặc URL). KHÔNG đặt hàng — chỉ liên hệ.
const zaloLink = computed(() => {
  const z = entity.value?.attributes?.zalo
  if (!z) return ''
  return String(z).startsWith('http') ? safeUrl(z) : `https://zalo.me/${String(z).replace(/\D/g, '')}`
})
// GĐ13.1 (MVP): chủ cơ sở "nhận listing" -> trang liên hệ kèm ngữ cảnh (luồng owner-edit đầy đủ = sau).
const claimUrl = computed(() => `/lien-he?ref=claim&entity=${encodeURIComponent(entity.value?.name || id.value)}`)

// D2 (2026-06-13): với sản phẩm OCOP, đưa website RIÊNG của chủ thể thành CTA "hỏi mua trực tiếp"
// — dẫn khách về kênh bán/đặt riêng của họ. KHÔNG link sàn TMĐT, KHÔNG giỏ hàng/thanh toán on-site
// (giữ showcase-only §1.4). Chỉ áp cho product để khỏi trùng link website ở phần "facts".
const buyContactUrl = computed(() => {
  if (entity.value?.type !== 'product') return ''
  const w = entity.value?.attributes?.website
  return w && String(w).startsWith('http') ? safeUrl(w) : ''
})

// Highlights (quét nhanh đầu trang)
const priceText = computed(() => entity.value?.attributes?.price || entity.value?.attributes?.fee || '')
const addressText = computed(() => entity.value?.attributes?.address || entity.value?.place_name || '')
const hasCoords = computed(() => !!normalizeCoords(entity.value?.coordinates))
// Link bản đồ FOCUS đúng điểm này (truyền id + toạ độ) — không ra bản đồ chung
const mapUrl = computed(() => {
  const c = normalizeCoords(entity.value?.coordinates)
  const base = `/ban-do?id=${encodeURIComponent(id.value)}`
  return c ? `${base}&lat=${c[0]}&lng=${c[1]}` : base
})
const planAddUrl = computed(() => `/tao-lich-trinh?add=${encodeURIComponent(id.value)}`)
const hasHighlights = computed(() => !!(entity.value?.attributes?.phone || zaloLink.value || entity.value?.attributes?.hours || priceText.value || addressText.value || hasCoords.value))
const hasVisitFacts = computed(() => { const a = entity.value?.attributes; return !!(a?.hours || a?.price || a?.fee || a?.suggested_duration || a?.transport) })
const hasContactFacts = computed(() => { const a = entity.value?.attributes; return !!(a?.phone || a?.address || (a?.coords_approximate && hasCoords.value) || a?.website) })
const hasFeatureFacts = computed(() => { const a = entity.value?.attributes; return !!(a?.amenities || a?.price_range || a?.atmosphere || a?.famous_for || a?.significance) })
// Sticky bar always renders; this tells the template whether any "contact" CTA
// (phone/Zalo/map) is present. If not, the bar shows the itinerary fallback CTA.
const hasStickyContact = computed(() => !!(entity.value?.attributes?.phone || zaloLink.value || hasCoords.value))

const practicalTips = computed(() => {
  const a = entity.value?.attributes
  if (!a) return []
  const tips: { icon: string; label: string; value: string }[] = []
  if (a.highlight) tips.push({ icon: '✨', label: 'Điểm nhấn', value: a.highlight })
  if (a.booking_note) tips.push({ icon: '📝', label: 'Đặt trước', value: a.booking_note })
  if (a.transport) tips.push({ icon: '🚗', label: 'Di chuyển', value: a.transport })
  if (a.fee) tips.push({ icon: '🎫', label: 'Phí vào cửa', value: a.fee })
  // declutter-3 T17 (A8 thu-scope D5): amenities 1 nguồn duy nhất = facts-card "Tiện ích"
  // (bảng tham chiếu) — bỏ dòng lặp trong practical-tips.
  if (a.family_friendly || a.suitable_for?.includes('family'))
    tips.push({ icon: '👨‍👩‍👧‍👦', label: 'Gia đình', value: 'Phù hợp cho gia đình có trẻ em' })
  if (a.parking) tips.push({ icon: '🅿️', label: 'Đậu xe', value: a.parking })
  if (Array.isArray(a.travel_tips)) {
    for (const t of a.travel_tips.slice(0, 3)) {
      if (t) tips.push({ icon: '💡', label: 'Mẹo', value: t })
    }
  }
  return tips
})

const bestTimeText = computed(() => entity.value?.attributes?.best_time || '')

const foodSpecialties = computed(() => {
  const a = entity.value?.attributes
  const t = entity.value?.type
  if (!a || (t !== 'dish' && t !== 'product' && t !== 'craft_village')) return []
  const items: { icon: string; label: string; value: string }[] = []
  if (a.must_order) items.push({ icon: '⭐', label: 'Phải thử', value: Array.isArray(a.must_order) ? a.must_order.join(', ') : a.must_order })
  if (a.signature_dish) items.push({ icon: '👨‍🍳', label: 'Món đặc trưng', value: a.signature_dish })
  if (a.best_dish) items.push({ icon: '🥇', label: 'Món hay gọi nhất', value: a.best_dish })
  if (a.specialty) items.push({ icon: '🎯', label: 'Đặc sản', value: Array.isArray(a.specialty) ? a.specialty.join(', ') : a.specialty })
  if (a.ingredients) items.push({ icon: '🧄', label: 'Nguyên liệu', value: Array.isArray(a.ingredients) ? a.ingredients.join(', ') : a.ingredients })
  if (a.what_to_buy) items.push({ icon: '🛍️', label: 'Nên mua', value: Array.isArray(a.what_to_buy) ? a.what_to_buy.join(', ') : a.what_to_buy })
  return items
})

const reportUrl = computed(() => `/cong-dong?report=${encodeURIComponent(id.value)}`)

const sourceFreshness = computed(() => entity.value?.source_freshness)
const trustSourceUrl = computed(() => sourceFreshness.value?.source_url || entity.value?.quality?.source_url || '')
const trustSourceTitle = computed(() => sourceFreshness.value?.source_title || entity.value?.quality?.source_title || (trustSourceUrl.value ? 'Nguồn tham khảo' : 'Chưa có nguồn công khai'))
const trustUpdatedAt = computed(() => sourceFreshness.value?.updated_at || entity.value?.quality?.verified_at || entity.value?.updatedAt || '')
const trustUpdatedLabel = computed(() => trustUpdatedAt.value ? formatDateVN(trustUpdatedAt.value) : 'Chưa rõ')
const trustStatus = computed(() => sourceFreshness.value?.freshness_status || 'unknown')
const trustStatusLabel = computed(() => {
  if (trustStatus.value === 'fresh') return 'Mới cập nhật'
  if (trustStatus.value === 'aging') return 'Cần kiểm tra định kỳ'
  if (trustStatus.value === 'stale') return 'Có thể đã cũ'
  return 'Chưa rõ'
})
const trustStatusTone = computed(() => {
  if (trustStatus.value === 'fresh') return 'fresh'
  if (trustStatus.value === 'aging') return 'aging'
  if (trustStatus.value === 'stale') return 'stale'
  return 'unknown'
})
const trustNote = computed(() => {
  if (trustStatus.value === 'fresh') return 'Thông tin này có tín hiệu cập nhật gần đây.'
  if (trustStatus.value === 'aging') return 'Thông tin vẫn dùng được nhưng nên kiểm tra lại nếu bạn sắp đi.'
  if (trustStatus.value === 'stale') return 'Thông tin có thể đã cũ; hãy báo sai nếu bạn thấy khác thực tế.'
  return 'Hệ thống chưa có đủ tín hiệu nguồn/ngày cập nhật cho mục này.'
})
// P0-7: chỉ hiện trust-card khi CÓ nguồn công khai thật (đừng quảng cáo "chưa có nguồn").
const trustVisible = computed(() => !!trustSourceUrl.value)

// P0-5: byline biên tập (Who) — LUÔN hiện, mọi trang. Trung thực theo verifiedAt thật
// (người đặt tay); hiện chưa entity nào có → mặc định "chưa kiểm chứng thực địa".
const entityVerifiedAt = computed(() => entity.value?.verifiedAt || '')
const bylineText = computed(() => entityVerifiedAt.value
  ? `Biên tập & kiểm chứng thực địa · ${formatDateVN(entityVerifiedAt.value)}`
  : 'Tổng hợp & biên tập từ nguồn công khai — chưa kiểm chứng thực địa')

// GĐ10.4: normalizeCoords gom vào composables/useCoords.ts (Nuxt auto-import).

const ocopStars = computed(() => {
  const ocop = entity.value?.attributes?.ocop || ''
  const num = parseInt(String(ocop), 10) || 0
  return Math.min(num, 5)
})

const relationshipRows = ref<Record<string, any>[]>([])
const relationshipTotal = ref(0)
const loadingRelationships = ref(false)

watch(entity, (next) => {
  relationshipRows.value = Array.isArray(next?.relationships) ? next.relationships.map(rel => ({ ...rel })) : []
  relationshipTotal.value = Number(next?.relationship_total ?? relationshipRows.value.length) || relationshipRows.value.length
}, { immediate: true })

function rawRelationshipKey(r: Record<string, any>) {
  return `${r.source_id || ''}|${r.target_id || ''}|${r.rel_type || ''}`
}

function normalizeRelationship(r: Record<string, any>) {
  const sourceId = r.source_id
  const targetId = r.target_id
  const relType = r.rel_type
  if (!sourceId || !targetId || !relType) return null
  const isNear = relType === 'near'
  const distance = typeof r.distance_km === 'number' ? r.distance_km : null
  if (isNear && (distance === null || distance > 50)) return null
  const isFwd = sourceId === id.value
  const otherId = r.other_id ?? (isFwd ? targetId : sourceId)
  const otherName = r.other_name ?? (isFwd ? (r.target_name ?? r.name) : (r.source_name ?? r.name))
  const otherType = r.other_type ?? ''
  let label = isFwd ? (REL_FWD[relType] || relType) : (REL_BWD[relType] || relType)
  if ((relType === 'related_to' || relType === 'associated_with') && otherType) {
    const meta = TYPE_META[otherType]
    if (meta) label = meta.emoji + ' ' + meta.label
  }
  return {
    target_id: otherId,
    target_name: otherName || otherId,
    rel_type: relType,
    distance_km: distance,
    label,
  }
}

const relationships = computed(() => {
  return relationshipRows.value
    .map(normalizeRelationship)
    .filter((rel): rel is NonNullable<ReturnType<typeof normalizeRelationship>> => Boolean(rel))
})

const remainingRelationshipCount = computed(() => Math.max(relationshipTotal.value - relationshipRows.value.length, 0))
const hasMoreRelationships = computed(() => remainingRelationshipCount.value > 0)

const relError = ref('')
async function loadMoreRelationships() {
  if (loadingRelationships.value || !hasMoreRelationships.value) return
  const currentId = id.value
  loadingRelationships.value = true
  relError.value = ''
  try {
    const response = await $fetch<{ total?: number; relationships?: Record<string, any>[] }>(`/api/entities/${encodePathId(currentId)}/relationships`, {
      query: {
        limit: RELATIONSHIP_BATCH_SIZE,
        offset: relationshipRows.value.length,
      },
    })
    if (currentId !== id.value) return
    relationshipTotal.value = Number(response?.total ?? relationshipTotal.value) || relationshipTotal.value
    const seen = new Set(relationshipRows.value.map(rawRelationshipKey))
    for (const rel of response?.relationships || []) {
      const key = rawRelationshipKey(rel)
      if (!seen.has(key)) {
        relationshipRows.value.push(rel)
        seen.add(key)
      }
    }
  } catch {
    relError.value = ss('labels.detail.relationships_error', 'Không tải thêm được, thử lại sau.')
  } finally {
    loadingRelationships.value = false
  }
}

// ── Reactive SEO meta: updates when entity changes (client-side navigation) ──
const absUrl = (u: string) => (u.startsWith('http') ? u : `${SITE_URL}${u}`)

const TYPE_TO_SCHEMA: Record<string, string> = {
  product: 'Product',
  accommodation: 'LodgingBusiness',
  dish: 'FoodEstablishment',
  craft_village: 'LocalBusiness',
  organization: 'LocalBusiness',
  attraction: 'TouristAttraction',
  experience: 'TouristAttraction',
  event: 'Event',
  place: 'Place',
}

const seoDesc = computed(() => {
  const e = entity.value
  if (!e) return ''
  const raw = e.description ? e.description.split(/\n\s*\n/)[0]?.trim() || e.summary || '' : e.summary || ''
  if (raw.length <= 160) return raw
  return raw.slice(0, 157).replace(/\s+\S*$/, '') + '…'
})

useSeoMeta({
  ogType: 'article',
  title: () => entity.value ? `${entity.value.name} — ${typeMeta.value.label} — vinhlong360` : 'Địa điểm — vinhlong360',
  description: () => seoDesc.value,
  ogTitle: () => entity.value ? `${entity.value.name} — vinhlong360` : 'Địa điểm — vinhlong360',
  ogDescription: () => seoDesc.value,
  ogImage: () => entityOgImage(entity.value?.images),
})

// JSON-LD + canonical: rebuilt reactively via computed
const fallbackJsonLdScripts = computed(() => {
  const e = entity.value
  if (!e) return []

  const ldType = TYPE_TO_SCHEMA[e.type] || 'TouristAttraction'
  const hasRealPhoto = Array.isArray(e.images) && e.images.length > 0

  const entityUrl = `${SITE_URL}${entityPath(e.id)}`
  const ld: Record<string, any> = {
    '@context': 'https://schema.org',
    '@type': ldType,
    '@id': entityUrl,
    name: e.name,
    description: e.description || e.summary,
    inLanguage: 'vi-VN',
    url: entityUrl,
    address: {
      '@type': 'PostalAddress',
      addressLocality: e.place_name || '',
      addressRegion: areaName.value,
      addressCountry: 'VN',
    },
  }
  if (hasRealPhoto) ld.image = e.images!.map(absUrl)
  if (e.attributes?.phone) ld.telephone = e.attributes.phone
  const sameAs = [e.attributes?.website, e.quality?.source_url].filter(Boolean)
  if (sameAs.length) ld.sameAs = sameAs.length === 1 ? sameAs[0] : sameAs
  if (e.quality?.source_url) {
    ld.citation = {
      '@type': 'CreativeWork',
      name: e.quality?.source_title || e.quality.source_url,
      url: e.quality.source_url,
    }
  }
  if (e.attributes?.address) ld.address.streetAddress = e.attributes.address
  const geoCoords = normalizeCoords(e.coordinates)
  if (geoCoords) {
    ld.geo = { '@type': 'GeoCoordinates', latitude: geoCoords[0], longitude: geoCoords[1] }
  }
  if (e.attributes?.hours) ld.openingHours = e.attributes.hours

  // isAccessibleForFree
  const fee = e.attributes?.fee || e.attributes?.price_range || ''
  const isFree = /miễn phí|free|không mất phí|0\s*đ/i.test(fee)
    || (e.attributes?.amenities && Array.isArray(e.attributes.amenities) && e.attributes.amenities.includes('free_entry'))
  if (isFree) ld.isAccessibleForFree = true

  // LocalBusiness/LodgingBusiness/FoodEstablishment enrichment
  if (['LocalBusiness', 'LodgingBusiness', 'FoodEstablishment'].includes(ldType)) {
    if (e.attributes?.price_range) ld.priceRange = e.attributes.price_range
  }
  if (ldType === 'LodgingBusiness') {
    if (e.attributes?.checkin) ld.checkinTime = e.attributes.checkin
    if (e.attributes?.checkout) ld.checkoutTime = e.attributes.checkout
  }

  if (ldType === 'Event') {
    if (e.attributes?.date_start) ld.startDate = e.attributes.date_start
    if (e.attributes?.date_end) ld.endDate = e.attributes.date_end
    if (e.place_name || areaName.value) {
      ld.location = {
        '@type': 'Place',
        name: e.place_name || areaName.value,
        address: { '@type': 'PostalAddress', addressRegion: areaName.value, addressCountry: 'VN' },
      }
      if (geoCoords) {
        ld.location.geo = { '@type': 'GeoCoordinates', latitude: geoCoords[0], longitude: geoCoords[1] }
      }
    }
    ld.eventStatus = 'https://schema.org/EventScheduled'
    ld.eventAttendanceMode = 'https://schema.org/OfflineEventAttendanceMode'
    if (isFree) {
      ld.offers = { '@type': 'Offer', price: '0', priceCurrency: 'VND', availability: 'https://schema.org/InStock' }
    }
  }
  if (e.attributes?.rating) {
    ld.aggregateRating = {
      '@type': 'AggregateRating',
      ratingValue: e.attributes.rating,
      bestRating: '5',
      ...(e.attributes.review_count ? { reviewCount: String(e.attributes.review_count) } : { ratingCount: '1' }),
    }
  }
  if (ldType === 'Product') {
    if (e.attributes?.price) {
      ld.offers = {
        '@type': 'Offer',
        price: String(e.attributes.price).replace(/[^\d]/g, '') || '0',
        priceCurrency: 'VND',
        availability: 'https://schema.org/InStock',
        url: entityUrl,
      }
    }
    if (e.attributes?.ocop) {
      ld.brand = { '@type': 'Brand', name: `OCOP ${e.attributes.ocop}` }
    }
  }

  // Geographic containment (all entity types)
  if (e.place_name) {
    ld.containedInPlace = {
      '@type': 'AdministrativeArea',
      name: e.place_name,
      ...(areaName.value ? { containedInPlace: { '@type': 'AdministrativeArea', name: areaName.value } } : {}),
    }
  }

  const bcItems: any[] = [
    { '@type': 'ListItem', position: 1, name: 'Trang chủ', item: `${SITE_URL}/` },
    { '@type': 'ListItem', position: 2, name: typeMeta.value.label, item: `${SITE_URL}${typeBreadcrumbUrl.value}` },
  ]
  if (e.place_area) {
    bcItems.push({ '@type': 'ListItem', position: 3, name: areaName.value, item: `${SITE_URL}/khu-vuc/${e.place_area}` })
  }
  bcItems.push({ '@type': 'ListItem', position: bcItems.length + 1, name: e.name, item: entityUrl })
  const breadcrumb = {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: bcItems,
  }

  // FAQPage from entity attributes
  const faqItems: { q: string; a: string }[] = []
  if (e.attributes?.hours)
    faqItems.push({ q: `${e.name} mở cửa lúc mấy giờ?`, a: `Giờ mở cửa: ${e.attributes.hours}` })
  if (e.attributes?.fee)
    faqItems.push({ q: `Phí vào ${e.name} bao nhiêu?`, a: e.attributes.fee })
  if (e.attributes?.transport)
    faqItems.push({ q: `Đi đến ${e.name} bằng cách nào?`, a: e.attributes.transport })
  if (e.attributes?.parking)
    faqItems.push({ q: `${e.name} có chỗ đậu xe không?`, a: e.attributes.parking })
  if (e.attributes?.best_time)
    faqItems.push({ q: `Thời điểm nào đẹp nhất để đến ${e.name}?`, a: e.attributes.best_time })

  const scripts: any[] = [
    { type: 'application/ld+json', innerHTML: safeJsonLd(ld) },
    { type: 'application/ld+json', innerHTML: safeJsonLd(breadcrumb) },
  ]

  if (faqItems.length >= 2) {
    scripts.push({
      type: 'application/ld+json',
      innerHTML: safeJsonLd({
        '@context': 'https://schema.org',
        '@type': 'FAQPage',
        mainEntity: faqItems.map(f => ({
          '@type': 'Question',
          name: f.q,
          acceptedAnswer: { '@type': 'Answer', text: f.a },
        })),
      }),
    })
  }

  return scripts
})

function normalizeJsonLdPayload(payload: JsonLdPayload | null | undefined) {
  if (!payload) return []
  return (Array.isArray(payload) ? payload : [payload]).filter(Boolean)
}

const backendJsonLdScripts = computed(() => normalizeJsonLdPayload(backendJsonLd.value).map(item => ({
  type: 'application/ld+json',
  innerHTML: safeJsonLd(item),
})))

const jsonLdScripts = computed(() => {
  // P1-3: nếu backend /seo/jsonld fail/rỗng → dùng fallback (BreadcrumbList + entity
  // schema + FAQ) thay vì mất hết rich-result, chỉ còn WebSite toàn cục.
  return backendJsonLdScripts.value.length ? backendJsonLdScripts.value : fallbackJsonLdScripts.value
})

useHead({
  link: [{ rel: 'canonical', href: () => entity.value ? entityDetailUrl(entity.value.id) : canonicalUrl('/dia-diem') }],
  script: jsonLdScripts,
})
</script>

<!-- detail.css nạp theo route (bỏ khỏi global entry.css; phần dùng-chung ở detail-shared.css) -->
<style src="~/assets/css/detail.css"></style>

<style scoped>
/* PhotoGallery placement below hero */
.detail-gallery {
  max-width: var(--maxw, 1200px);
  margin: var(--space-4) auto;
  padding: 0 var(--space-5);
}

/* ContactWidget: let the component handle its own sticky/positioning,
   but override width inside the sidebar context */
.detail-contact-widget {
  width: 100%;
  position: static;
  margin-bottom: var(--space-5);
}

.fact-copy {
  display: inline-flex; align-items: center; justify-content: center;
  width: 28px; height: 28px; margin-left: var(--space-1); vertical-align: middle;
  border: none; border-radius: var(--radius-sm); background: transparent;
  color: var(--muted); cursor: pointer; transition: color .2s, background .2s;
}
.fact-copy:hover { color: var(--primary-fg); background: rgba(var(--primary-rgb), .08); }
.fact-copy:focus-visible { outline: 2px solid var(--primary); outline-offset: 1px; }

/* P0-5: editorial byline — subtle, honest "Who" line above the trust card. */
.entity-byline {
  display: flex;
  align-items: center;
  gap: .5em;
  margin: var(--space-4) 0 var(--space-2);
  font-size: var(--text-xs);
  line-height: var(--leading-snug);
  color: var(--muted);
}
.entity-byline .line-icon { font-size: 1.1em; color: var(--muted); flex: 0 0 auto; }
.entity-byline strong { font-weight: var(--weight-semibold); color: var(--ink); }
.entity-byline a { color: var(--primary-fg); text-decoration: underline; text-underline-offset: 2px; }

.trust-card {
  margin: var(--space-4) 0;
  padding: var(--space-4);
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  background: var(--surface);
}
.trust-card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: var(--space-3);
}
.trust-card h2 {
  margin: 0;
  font-size: var(--text-base);
}
.trust-status {
  flex: 0 0 auto;
  padding: 3px 8px;
  border-radius: 999px;
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  border: 1px solid var(--line);
}
.trust-status.fresh { color: var(--success); background: var(--success-bg); border-color: var(--success-border); }
.trust-status.aging { color: var(--warning); background: var(--warning-bg); border-color: var(--warning-border); }
.trust-status.stale { color: var(--error); background: var(--error-bg); border-color: var(--error-border); }
.trust-status.unknown { color: var(--muted); background: var(--bg-warm); }
.trust-list {
  display: grid;
  gap: var(--space-2);
  margin: 0;
}
.trust-list > div {
  display: grid;
  grid-template-columns: 88px minmax(0, 1fr);
  gap: var(--space-2);
}
.trust-list dt {
  color: var(--muted);
  font-size: var(--text-sm);
}
.trust-list dd {
  margin: 0;
  min-width: 0;
  font-size: var(--text-sm);
  overflow-wrap: anywhere;
}
.trust-note {
  margin: var(--space-3) 0 0;
  color: var(--muted);
  font-size: var(--text-sm);
  line-height: 1.5;
}
.trust-report {
  display: inline-flex;
  margin-top: var(--space-3);
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
}

/* declutter-3 T17 (B5d): Save/Share dời từ hero về sidebar — 2 nút chia đều hàng.
   Sidebar stack dưới article trên mobile nên mọi viewport đều với tới. */
.aside-actions { display: flex; gap: var(--space-2); margin: var(--space-3) 0 var(--space-4); }
.aside-actions > * { flex: 1; }


/* On mobile, hide the desktop ContactWidget (it renders its own fixed bottom bar) */
@media (max-width: 767px) {
  /* Hide existing sticky-cta-bar since ContactWidget provides mobile bottom bar */
  .sticky-cta-bar { display: none; }
}

/* ── Cover-story hero layer (Wave 2): dateline eyebrow + hook + phù-sa no-photo hero ── */
.detail-cover .dc-eyebrow {
  display: inline-block; margin-bottom: var(--space-2);
  font-family: var(--font-sans); font-size: var(--text-2xs); font-weight: 700;
  letter-spacing: .12em; text-transform: uppercase;
  color: rgba(var(--white-rgb), .92); padding-bottom: 4px;
  border-bottom: 1px solid rgba(var(--white-rgb), .38);
}
.detail-cover .dc-hook {
  margin: var(--space-2) 0 var(--space-1); max-width: 42ch;
  font-family: var(--font-editorial); font-style: italic; font-weight: 500;
  font-size: var(--text-lg); line-height: 1.4; color: rgba(var(--white-rgb), .95);
  text-shadow: 0 1px 10px rgba(var(--black-rgb), .38);
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
/* No-photo entities: the per-entity gradient (inline bg) fills the hero; grain adds print texture */
.detail-cover:not(.has-cover-img) { background-size: cover; background-position: center; }
.detail-cover:not(.has-cover-img)::after {
  content: ""; position: absolute; inset: 0; z-index: 0; pointer-events: none;
  background-image: var(--grain); background-size: 168px 168px; opacity: .09;
}
.detail-cover:not(.has-cover-img) .dc-inner { position: relative; z-index: 2; }
.dc-nophoto-note {
  position: absolute; right: var(--space-4); bottom: var(--space-3); z-index: 2;
  font-size: var(--text-2xs); color: rgba(var(--white-rgb), .82);
  text-shadow: 0 1px 3px rgba(var(--black-rgb), .5); max-width: 58%; text-align: right; line-height: 1.3;
}
/* Oversized off-centre category motif watermark (no-photo hero only) — same visual
   language as EntityHeroPlaceholder.vue's .ehp-motif. Sits behind .dc-inner (z-index 2)
   and the existing .dc-overlay/.dc-vignette scrim, so hero text stays fully legible. */
.dc-motif {
  position: absolute; right: -4%; bottom: -10%; z-index: 1; pointer-events: none;
  width: 42%; max-width: 300px; color: rgba(var(--white-rgb), .5); opacity: .45;
}
.dc-motif :deep(svg) { width: 100%; height: auto; display: block; }
@media (max-width: 640px) {
  .detail-cover .dc-hook { font-size: var(--text-base); max-width: 100%; }
  .dc-nophoto-note { max-width: 72%; }
  .dc-motif { width: 56%; opacity: .3; }
}
</style>
