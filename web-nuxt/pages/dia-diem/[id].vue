<template>
  <section v-if="entity" class="page entity-detail entity-detail-page" data-color-system="tri-region-v1" data-page-recipe="detail" :data-material-accent="detailMaterialAccent">
    <div class="scroll-progress" :style="{ transform: `scaleX(${progress})` }" aria-hidden="true" />
    <PageState
      v-if="!detailOnline"
      class="detail-offline-state"
      :state="{ kind: 'offline', cached: entity }"
    >
      <p>Hồ sơ địa điểm đã tải vẫn có thể đọc và dùng để tiếp tục hành trình.</p>
    </PageState>
    <!-- Breadcrumb -->
    <nav class="breadcrumb" aria-label="Breadcrumb">
      <button type="button" class="bc-back" aria-label="Quay lại" @click="goBack">
        <IconLine name="arrow-left" aria-hidden="true" />
      </button>
      <ol>
        <li><NuxtLink to="/">Trang chủ</NuxtLink></li>
        <li><NuxtLink :to="typeBreadcrumbUrl">{{ typeMeta.label }}</NuxtLink></li>
        <!-- Đơn vị hành chính cấp xã/phường -->
        <li v-if="adminUnitBreadcrumb">
          <NuxtLink v-if="adminUnitBreadcrumb.to" :to="adminUnitBreadcrumb.to">{{ adminUnitBreadcrumb.label }}</NuxtLink>
          <template v-else>{{ adminUnitBreadcrumb.label }}</template>
        </li>
        <li aria-current="page">{{ entity.name }}</li>
      </ol>
    </nav>

    <!-- Cover + Hero Image. The descriptor remains authoritative through gallery navigation. -->
    <div
      data-entity-hero
      data-detail-region="identity"
      :class="['detail-cover', `cat-${typeMeta.cat}`, { 'has-cover-img': hasEntityImages }]"
      :style="!hasEntityImages ? { backgroundImage: heroPlaceholderBg } : undefined"
      :aria-describedby="heroDisclosureId"
    >
      <!-- KHÔNG đặt role="img" lên chính .detail-cover: khối này bọc cả
           .dc-place-link lẫn các nút hành động, mà role="img" tuyên bố cả vùng
           là một hình ảnh — axe bắt `nested-interactive` (serious, 2026-08-06),
           cùng dạng lỗi với .season-timeline ở theo-mua.vue. Nhãn ảnh minh hoạ
           nay do chính EntityHeroPlaceholder mang (nó đã có role="img" +
           aria-label từ descriptor), nên bỏ luôn aria-hidden của nó. -->
      <NuxtImg v-if="hasEntityImages && heroDescriptor.url && isRemoteUrl(heroDescriptor.url)" :key="heroImageIdentity" ref="heroImage" :src="heroDescriptor.url" :alt="heroDescriptor.alt" :class="['dc-bg', { loaded: heroLoaded }]" :style="heroLoaded ? undefined : { opacity: 0, transition: 'none' }" loading="eager" fetchpriority="high" width="1200" height="600" sizes="sm:100vw md:100vw lg:960px xl:1200px" role="button" tabindex="0" :aria-describedby="heroDisclosureId" :aria-label="`Xem ảnh ${entity.name}`" @load="revealHeroImage" @click="openCoverLightbox(0)" @keydown.enter="openCoverLightbox(0)" @keydown.space.prevent="openCoverLightbox(0)" />
      <img v-else-if="hasEntityImages && heroDescriptor.url" :key="heroImageIdentity" ref="heroImage" :src="heroDescriptor.url" :alt="heroDescriptor.alt" :class="['dc-bg', { loaded: heroLoaded }]" :style="heroLoaded ? undefined : { opacity: 0, transition: 'none' }" loading="eager" fetchpriority="high" width="1200" height="600" role="button" tabindex="0" :aria-describedby="heroDisclosureId" :aria-label="`Xem ảnh ${entity.name}`" @load="revealHeroImage" @click="openCoverLightbox(0)" @keydown.enter="openCoverLightbox(0)" @keydown.space.prevent="openCoverLightbox(0)" />
      <EntityHeroPlaceholder v-else :id="entity.id" :cat="typeMeta.cat" :label="typeMeta.label" :descriptor="heroDescriptor" :material-accent="detailMaterialAccent" class="dc-placeholder" />
      <div v-if="coverImage" class="dc-overlay"></div>
      <div v-if="coverImage" class="dc-vignette" aria-hidden="true"></div>
      <span v-if="!hasEntityImages" class="dc-motif" aria-hidden="true" v-html="heroMotifSvg"></span>
      <div class="dc-inner">
        <span class="dc-type-row">
          <span class="dc-type-chip"><IconLine :name="typeMeta.icon" class="dc-emoji" />{{ typeMeta.label }}</span>
          <span v-if="ocopBadge" class="dc-ocop-chip" :aria-label="`Sản phẩm ${ocopBadge}`">
            <IconLine name="star" /> {{ ocopBadge }}
          </span>
        </span>
        <span v-if="heroDateline" class="dc-eyebrow">{{ heroDateline }}</span>
        <h1>{{ entity.name }}</h1>
        <p v-if="heroHook" class="dc-hook">{{ heroHook }}</p>
        <p v-if="entity.place_name" class="dc-place"><NuxtLink v-if="entity.placeId" :to="`/xa-phuong/${entity.placeId}`" class="dc-place-link">{{ entity.place_name }}</NuxtLink><template v-else>{{ entity.place_name }}</template></p>
        <!-- Hero action suite -->
        <DetailActionSuite :entity-id="entity.id" :entity-type="entity.type" />
      </div>
      <DetailCoverLightbox
        ref="coverLightboxRef"
        :entity-name="entity.name"
        :entity-id="entity.id"
        :entity-image-descriptors="entityImageDescriptors"
        :has-entity-images="hasEntityImages"
      />
      <ImageDisclosure :id="heroDisclosureId" :descriptor="heroDescriptor" presentation="short" class="dc-disclosure" />
    </div>

    <!-- Photo Gallery (asymmetric grid for 2+ images) -->
    <div
      v-if="hasEntityGallery"
      class="detail-gallery"
      data-image-surface="mixed-gallery"
      data-source-class="user-uploaded"
      data-entity-image-policy="no-image-invariant"
    >
      <LazyPhotoGallery
        :images="entityImageDescriptors"
        :alt="entity.name"
        @open-lightbox="openCoverLightbox"
      />
    </div>

    <PageState
      v-if="galleryPartial"
      class="detail-partial-state"
      :state="{ kind: 'partial', data: entity, failedPanels: ['media'] }"
      :retry="refreshGallery"
    >
      <p>Thông tin địa điểm vẫn dùng được trong khi hình ảnh được tải lại.</p>
    </PageState>

    <!-- Body -->
    <div class="detail-body">
      <!-- Sidebar -->
      <aside class="detail-aside" aria-label="Thông tin bổ sung">
        <div class="detail-trust-region" data-detail-region="trust">
          <p class="entity-byline"><IconLine name="user" /> {{ bylineText }} · <strong>Ban biên tập vinhlong360</strong> · <NuxtLink to="/gioi-thieu#ban-bien-tap">phương pháp biên tập</NuxtLink></p>

          <EntityTrustPanel
            v-if="!trustVisible"
            class="trust-card"
            :tier="trustTier"
            :source-title="trustSourceTitle"
            :source-url="trustSourceUrl || undefined"
            :freshness-status="trustFreshnessStatus"
            :updated-label="trustUpdatedLabel"
            :note="trustNote"
            :report-to="reportUrl"
            :conflicts="trustConflicts"
          />

          <section v-if="trustVisible" class="trust-card" aria-labelledby="trust-card-title">
            <div class="trust-card-head">
              <h2 id="trust-card-title" class="sediment-head">Độ tin cậy dữ liệu</h2>
              <span :class="['trust-status', trustStatusTone]">{{ trustStatusLabel }}</span>
            </div>
            <p class="trust-source"><IconLine :name="trustSourceTier === 'community' ? 'users' : 'shield-check'" aria-hidden="true" /> {{ trustSourceTitle }}</p>
            <button
              type="button"
              class="trust-open"
              data-action="open-source-trust"
              aria-haspopup="dialog"
              :aria-expanded="trustDrawerOpen"
              @click="trustDrawerOpen = true"
            >
              Xem nguồn và cách đánh giá
              <IconLine name="panel-left-open" aria-hidden="true" />
            </button>
          </section>

          <SourceTrustDrawer
            :open="trustDrawerOpen"
            :source-tier="trustSourceTier"
            :source-title="trustSourceTitle"
            :source-url="trustSourceUrl"
            :verified-at="trustVerifiedAt"
            :updated-at="trustUpdatedAt"
            :freshness-status="trustStatus"
            :community-context="trustCommunityContext"
            :conflicts="trustConflicts"
            @close="trustDrawerOpen = false"
            @report="reportTrustIssue"
          />
        </div>

        <ActionDock class="detail-action-dock" data-detail-region="action" data-detail-action-safe-area>
          <template #primary>
            <a
              v-if="detailPrimaryAction.id === 'call'"
              class="detail-primary-action"
              data-color-role="action-primary"
              data-contact-action="phone"
              :href="detailPrimaryAction.href"
              @click="trackContact('phone')"
            >{{ detailPrimaryAction.label }}</a>
            <NuxtLink
              v-else
              class="detail-primary-action"
              data-color-role="action-primary"
              :data-contact-action="detailPrimaryAction.id === 'directions' ? 'map' : undefined"
              :to="detailPrimaryAction.href"
              no-prefetch
              @click="detailPrimaryAction.id === 'directions' && trackContact('map')"
            >{{ detailPrimaryAction.label }}</NuxtLink>
          </template>
          <ClientOnly>
            <SaveButton :entity="entity" :show-label="true" />
            <ShareButton :title="entity.name" :text="entity.summary" :descriptor="heroDescriptor" />
          </ClientOnly>
        </ActionDock>

        <!-- OCOP highlight -->
        <div v-if="ocopBadge" class="ocop-highlight">
          <div class="ocop-stars">
            <IconLine v-for="s in ocopStars" :key="s" class="ocop-star" name="star" aria-hidden="true" />
          </div>
          <!-- Nối hạng sao vào tiền tố CMS -->
          <strong>{{ ss('labels.detail.ocop_product_prefix', 'Sản phẩm OCOP') }}<span v-if="ocopStars"> {{ ocopStars }} sao</span></strong>
          <small>{{ ss('labels.detail.ocop_program', 'Chương trình Mỗi xã Một sản phẩm') }}</small>
        </div>

        <!-- Rating -->
        <div v-if="entity.attributes?.rating" class="rating-display">
          <div class="rd-stars">
            <IconLine v-for="s in 5" :key="s" :class="['rd-star', { filled: s <= Math.round(Number(entity.attributes.rating)) }]" name="star" aria-hidden="true" />
          </div>
          <span class="rd-score">{{ entity.attributes.rating }}</span>
          <span v-if="entity.attributes?.review_count" class="rd-count">({{ entity.attributes.review_count }} đánh giá)</span>
        </div>

        <div data-detail-region="facts">
          <h2 class="facts-heading sediment-head"><IconLine class="facts-heading-icon" name="clipboard-list" aria-hidden="true" />{{ ss('labels.detail.info_heading', 'Thông tin') }}</h2>
          <div class="facts-card">
            <section class="fact-group">
              <h3 class="fg-label">Tổng quan</h3>
              <dl>
                <div class="fact">
                  <dt class="k"><IconLine :name="typeMeta.icon" class="fact-ic" /><span>{{ ss('labels.detail.fact_type', 'Loại') }}</span></dt>
                  <dd class="v">{{ typeMeta.label }}</dd>
                </div>
                <div v-if="entity.place_name" class="fact">
                  <dt class="k"><IconLine class="fact-ic" name="pin" aria-hidden="true" /><span>{{ ss('labels.detail.fact_place', 'Địa điểm') }}</span></dt>
                  <dd class="v">
                    <NuxtLink v-if="entity.placeId" :to="`/xa-phuong/${entity.placeId}`" class="fact-link">{{ entity.place_name }}</NuxtLink>
                    <template v-else>{{ entity.place_name }}</template>
                  </dd>
                </div>
                <div v-if="entity.place_area" class="fact">
                  <dt class="k"><IconLine class="fact-ic" name="map" aria-hidden="true" /><span>{{ ss('labels.detail.fact_area', 'Khu vực') }}</span></dt>
                  <dd class="v"><NuxtLink :to="`/khu-vuc/${entity.place_area}`" class="fact-link">{{ areaName }}</NuxtLink></dd>
                </div>
                <div v-if="entity.season" class="fact">
                  <dt class="k"><IconLine class="fact-ic" name="sun" aria-hidden="true" /><span>{{ ss('labels.detail.fact_season', 'Mùa') }}</span></dt>
                  <dd class="v">{{ seasonLabel }}</dd>
                </div>
              </dl>
            </section>

            <section v-if="hasVisitFacts" class="fact-group">
              <h3 class="fg-label">Tham quan</h3>
              <div class="fact-evidence">
                <SourceMark :tier="trustTier" compact />
                <FreshnessLine :status="trustFreshnessStatus" :updated-label="trustUpdatedLabel" />
              </div>
              <dl>
                <div v-if="entity.attributes?.hours" class="fact">
                  <dt class="k"><IconLine class="fact-ic" name="clock" aria-hidden="true" /><span>{{ ss('labels.detail.fact_hours', 'Giờ mở cửa') }}</span></dt>
                  <dd class="v">{{ entity.attributes.hours }}</dd>
                </div>
                <div v-if="entity.attributes?.price" class="fact">
                  <dt class="k"><IconLine class="fact-ic" name="tag" aria-hidden="true" /><span>{{ ss('labels.detail.fact_price', 'Giá tham khảo') }}</span></dt>
                  <dd class="v">{{ entity.attributes.price }}</dd>
                </div>
                <div v-if="entity.attributes?.fee" class="fact">
                  <dt class="k"><IconLine class="fact-ic" name="tag" aria-hidden="true" /><span>{{ ss('labels.detail.fact_fee', 'Phí vào cửa') }}</span></dt>
                  <dd class="v">{{ entity.attributes.fee }}</dd>
                </div>
                <div v-if="entity.attributes?.suggested_duration" class="fact">
                  <dt class="k"><IconLine class="fact-ic" name="clock" aria-hidden="true" /><span>Thời gian tham quan</span></dt>
                  <dd class="v">{{ entity.attributes.suggested_duration }}</dd>
                </div>
                <div v-if="entity.attributes?.transport" class="fact">
                  <dt class="k"><IconLine class="fact-ic" name="car" aria-hidden="true" /><span>{{ ss('labels.detail.fact_transport', 'Di chuyển') }}</span></dt>
                  <dd class="v">{{ entity.attributes.transport }}</dd>
                </div>
                <div v-if="entity.attributes?.vehicle_access" class="fact">
                  <dt class="k"><IconLine class="fact-ic" name="car" aria-hidden="true" /><span>Tiếp cận xe</span></dt>
                  <dd class="v">{{ entity.attributes.vehicle_access }}</dd>
                </div>
                <div v-if="entity.attributes?.parking" class="fact">
                  <dt class="k"><IconLine class="fact-ic" name="car" aria-hidden="true" /><span>Bãi đỗ xe</span></dt>
                  <dd class="v">{{ entity.attributes.parking }}</dd>
                </div>
              </dl>
            </section>

            <section v-if="hasContactFacts" class="fact-group">
              <h3 class="fg-label">Liên hệ</h3>
              <dl>
                <div v-if="entity.attributes?.phone" class="fact">
                  <dt class="k"><IconLine class="fact-ic" name="phone" aria-hidden="true" /><span>{{ ss('labels.detail.fact_phone', 'Liên hệ') }}</span></dt>
                  <dd class="v"><a :href="telHref(entity.attributes.phone)" class="fact-link" data-contact-action="phone" @click="trackContact('phone')">{{ entity.attributes.phone }}</a><button type="button" class="fact-copy" @click="copyText(entity.attributes.phone!, 'số điện thoại')" aria-label="Sao chép số điện thoại" title="Sao chép"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg></button></dd>
                </div>
                <div v-if="entity.attributes?.address" class="fact">
                  <dt class="k"><IconLine class="fact-ic" name="home" aria-hidden="true" /><span>{{ ss('labels.detail.fact_address', 'Địa chỉ') }}</span></dt>
                  <dd class="v">{{ entity.attributes.address }}<button type="button" class="fact-copy" @click="copyText(entity.attributes.address!, 'địa chỉ')" aria-label="Sao chép địa chỉ" title="Sao chép"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg></button></dd>
                </div>
                <div v-if="entity.attributes?.coords_approximate && hasCoords" class="fact fact-approx">
                  <dt class="k"><IconLine class="fact-ic" name="pin" aria-hidden="true" /><span>{{ ss('labels.detail.fact_location', 'Vị trí') }}</span></dt>
                  <dd class="v">{{ ss('labels.detail.coords_approximate', 'Gần đúng (trung tâm xã/phường) — chưa có toạ độ chính xác') }}</dd>
                </div>
                <div v-if="entity.attributes?.website" class="fact">
                  <dt class="k"><IconLine class="fact-ic" name="globe" aria-hidden="true" /><span>{{ ss('labels.detail.fact_website', 'Website') }}</span></dt>
                  <dd class="v"><a :href="safeUrl(entity.attributes.website)" target="_blank" rel="noopener nofollow" class="fact-link website-link" data-contact-action="website" @click="trackContact('website')">{{ entity.attributes?.website?.replace(/^https?:\/\//, '') }}</a></dd>
                </div>
              </dl>
            </section>

            <section v-if="hasFeatureFacts" class="fact-group">
              <h3 class="fg-label">Đặc điểm</h3>
              <dl>
                <div v-if="entity.attributes?.amenities" class="fact">
                  <dt class="k"><IconLine class="fact-ic" name="check" aria-hidden="true" /><span>{{ ss('labels.detail.fact_amenities', 'Tiện ích') }}</span></dt>
                  <dd class="v">{{ Array.isArray(entity.attributes.amenities) ? entity.attributes.amenities.join(', ') : entity.attributes.amenities }}</dd>
                </div>
                <div v-if="entity.attributes?.price_range" class="fact">
                  <dt class="k"><IconLine class="fact-ic" name="tag" aria-hidden="true" /><span>Mức giá</span></dt>
                  <dd class="v">{{ entity.attributes.price_range }}</dd>
                </div>
              </dl>
            </section>
          </div>
        </div>

        <NuxtErrorBoundary>
          <ClientOnly>
            <LazyAIBestTime v-if="ff('ai_best_time')" :entity-id="id" :entity-name="entity.name" />
          </ClientOnly>
        </NuxtErrorBoundary>

        <!-- Contextual next steps -->
        <div class="next-steps">
          <h2 class="ns-title sediment-head">{{ ss('labels.detail.next_steps_title', 'Bước tiếp theo') }}</h2>
          <!-- Active planning CTA -->
        <NuxtLink :to="planAddUrl" no-prefetch class="ns-action"><IconLine name="clipboard-list" aria-hidden="true" /> {{ ss('labels.detail.next_add_itinerary', 'Thêm vào lịch trình') }}</NuxtLink>
          <!-- Kênh mua trực tiếp -->
          <a v-if="buyContactUrl" :href="buyContactUrl" target="_blank" rel="nofollow noopener" class="ns-action" data-contact-action="website" :aria-label="`Hỏi mua ${entity.name}`" @click="trackContact('website')"><IconLine name="gift" aria-hidden="true" /> {{ ss('labels.detail.cta_buy_contact', 'Hỏi mua trực tiếp') }}</a>
          <NuxtLink v-if="entity.type !== 'accommodation'" to="/luu-tru" class="ns-action"><IconLine name="home" aria-hidden="true" /> {{ ss('labels.detail.next_find_stay', 'Tìm chỗ ở gần đây') }}</NuxtLink>
        <NuxtLink :to="mapUrl" no-prefetch class="ns-action"><IconLine name="map" aria-hidden="true" /> {{ ss('labels.detail.next_view_map', 'Xem trên bản đồ') }}</NuxtLink>
          <NuxtLink to="/tuyen-duong" class="ns-action"><IconLine name="route" aria-hidden="true" /> {{ ss('labels.detail.next_route', 'Tuyến đường gợi ý') }}</NuxtLink>
          <!-- declutter-3 T17 (B5e): claim-cta DỜI vào next-steps (di chuyển, không bỏ) -->
          <NuxtLink :to="claimUrl" class="ns-action claim-cta"><IconLine name="tag" aria-hidden="true" /> {{ ss('labels.detail.cta_claim', 'Đây là cơ sở của tôi — đăng ký quản lý') }}</NuxtLink>
        </div>
      </aside>

      <article class="detail-main" data-detail-region="narrative" aria-label="Thông tin chi tiết">
        <!-- Highlights quét nhanh (Baymard: 78% site thiếu; chống info bị chôn dưới fold) -->
        <div v-if="hasHighlights" class="highlights">
          <a v-if="zaloLink" class="hl hl-action" data-color-role="action-secondary" data-contact-action="zalo" :href="zaloLink" target="_blank" rel="nofollow noopener" :aria-label="`Nhắn Zalo ${entity.name}`" @click="trackContact('zalo')"><IconLine name="message" aria-hidden="true" /> Zalo</a>
          <a v-if="entity.attributes?.phone" class="hl hl-action" data-color-role="action-secondary" data-contact-action="phone" :href="telHref(entity.attributes.phone)" :aria-label="`Gọi ${entity.name}`" @click="trackContact('phone')"><IconLine name="phone" aria-hidden="true" /> Gọi</a>
          <NuxtLink v-if="hasCoords" class="hl hl-action" data-color-role="action-secondary" data-contact-action="map" :to="mapUrl" :aria-label="`Xem ${entity.name} trên bản đồ`" @click="trackContact('map')"><IconLine name="map" aria-hidden="true" /> Bản đồ</NuxtLink>
          <span v-if="entity.attributes?.hours" class="hl"><IconLine name="clock" aria-hidden="true" /> {{ entity.attributes.hours }}</span>
          <span v-if="addressText" class="hl"><IconLine name="pin" aria-hidden="true" /> {{ addressText }}</span>
        </div>
        <p class="lead">{{ entity.summary }}</p>

        <!-- Highlight tagline -->
        <blockquote v-if="entity.attributes?.highlight" class="entity-highlight">
          <p>{{ entity.attributes.highlight }}</p>
        </blockquote>

        <!-- Hộp Tóm tắt Thực địa 30s & AEO -->
        <DetailAeoSummary :entity="entity" :accent="detailMaterialAccent" />

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
            <h2 class="section-subtitle"><IconLine :name="sec.icon" aria-hidden="true" /> {{ sec.title }}</h2>
            <p>{{ sec.text }}</p>
          </div>
        </div>

        <!-- Know Before You Go -->
        <KnowBeforeYouGo
          v-if="entity.attributes"
          :attributes="entity.attributes"
          :entity-type="entity.type"
          :source-tier="trustTier"
          :freshness-status="trustFreshnessStatus"
          :updated-label="trustUpdatedLabel"
        />

        <!-- Food specialties (dish/product only) -->
        <DetailFoodSpecialties :entity="entity" />

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
          <p v-if="entity.attributes?.peak_event" class="season-note peak-event"><IconLine name="calendar" aria-hidden="true" /> {{ entity.attributes.peak_event }}</p>
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

        <!-- Relationships belong after the full narrative and recommendation flow. -->
        <DetailRelationships
          data-detail-region="related"
          :entity-id="id"
          :initial-relationships="entity?.relationships"
          :initial-total="entity?.relationship_total"
        />
      </article>

    </div>

    <!-- Mobile Sticky CTA Bar — thumb-zone reachability on mobile -->
    <nav class="sticky-cta-bar" aria-label="Thao tác nhanh địa điểm">
      <a
        v-if="entity.attributes?.phone"
        :href="telHref(entity.attributes.phone)"
        class="scta-phone"
        data-color-role="action-primary"
        data-contact-action="phone"
        :aria-label="`Gọi ${entity.name}`"
        @click="trackContact('phone')"
      >
        <IconLine name="phone" aria-hidden="true" /> Gọi điện
      </a>
      <a
        v-if="zaloLink"
        :href="zaloLink"
        target="_blank"
        rel="noopener noreferrer nofollow"
        class="scta-zalo"
        data-contact-action="zalo"
        :aria-label="`Nhắn Zalo ${entity.name}`"
        @click="trackContact('zalo')"
      >
        <IconLine name="message" aria-hidden="true" /> Zalo
      </a>
      <NuxtLink
        v-if="hasCoords"
        :to="mapUrl"
        class="scta-map"
        data-contact-action="map"
        :aria-label="`Chỉ đường tới ${entity.name}`"
        @click="trackContact('map')"
      >
        <IconLine name="map" aria-hidden="true" /> Chỉ đường
      </NuxtLink>
      <NuxtLink
        v-if="!entity.attributes?.phone && !zaloLink && !hasCoords"
        :to="planAddUrl"
        class="scta-plan"
        data-color-role="action-primary"
        :aria-label="`Thêm ${entity.name} vào lịch trình`"
      >
        <IconLine name="clipboard-list" aria-hidden="true" /> Thêm lịch trình
      </NuxtLink>
    </nav>

  </section>
  <section v-else-if="detailFetchResolution?.kind === 'not_found'" class="page">
    <EmptyState title="Không tìm thấy địa điểm này" message="Có thể nội dung đã được di chuyển hoặc đường dẫn chưa đúng. Bạn thử khám phá các điểm đến khác nhé.">
      <template #actions>
        <NuxtLink to="/du-lich" class="btn btn-primary">Khám phá điểm đến</NuxtLink>
        <button type="button" class="btn btn-ghost" @click="goBack">Quay lại</button>
      </template>
    </EmptyState>
  </section>
  <section v-else-if="detailFetchResolution?.kind === 'hidden'" class="page">
    <EmptyState title="Nội dung chưa công khai" message="Nội dung này hiện không có trên bề mặt công khai. Bạn có thể quay lại kết quả trước đó hoặc khám phá nội dung khác.">
      <template #actions>
        <button type="button" class="btn btn-primary" @click="goBack">Quay lại</button>
        <NuxtLink to="/du-lich" class="btn btn-ghost">Khám phá điểm đến</NuxtLink>
      </template>
    </EmptyState>
  </section>
  <section v-else class="page detail-recovery-page">
    <PageState
      :state="entityStatus === 'idle' || entityStatus === 'pending'
        ? { kind: 'loading' }
        : { kind: 'error', retry: { label: 'Thử lại' } }"
      title="Không thể tải dữ liệu"
      :retry="entityStatus === 'idle' || entityStatus === 'pending' ? undefined : refreshEntity"
    />
    <nav class="detail-recovery-links" aria-label="Điều hướng khôi phục">
      <button type="button" class="btn btn-ghost" @click="goBack">Quay lại kết quả trước</button>
      <NuxtLink to="/du-lich" class="btn btn-outline">Khám phá điểm đến</NuxtLink>
    </nav>
  </section>
</template>

<script setup lang="ts">
import { ocopBadgeLabel, ocopStars as ocopStarsOf } from '~/utils/ocop'
import type { Entity } from '~/types'
import type { ImageDescriptor } from '~/types/image'
import { TYPE_META, AREA_META } from '~/composables/useConstants'
import { seasonText } from '~/composables/useSeason'
import { generateCategoryPlaceholder, generateCategoryIcon } from '~/composables/useCategoryPlaceholder'
import { entityStoryTeaser } from '~/composables/useEntityStory'
import { trackContactView, type ContactAction } from '~/composables/useContactBeacon'
import { adminUnitCrumb, withAdminUnitBreadcrumb } from '~/utils/adminUnit'
import { aiDisclosure } from '~/utils/aiDisclosure'
import { currentGalleryDescriptors, type GalleryDescriptorCarrier } from '~/utils/entityGallery'
import { describeEntityImages, parseGalleryDescriptor } from '~/utils/imageDescriptors'
import { resolveDetailAction, resolveDetailFetchError, parseDescriptionSections, type DetailFetchResolution, type DescSection } from '~/utils/detailExperience'
import { resolveFreshnessStatus, resolveRegionalAccent, resolveSourceTier } from '~/utils/regionalColor'
import ActionDock from '~/components/public/ActionDock.vue'
import PageState from '~/components/public/PageState.vue'
import SourceTrustDrawer from '~/components/SourceTrustDrawer.vue'

interface LaunchEntityCarrier extends Entity {
  readonly __launchGeneration: number
  readonly __launchRequestId: string
}

interface GalleryResponse {
  readonly images: unknown[]
}

interface DetailGalleryCarrier extends GalleryDescriptorCarrier {
  readonly failed: boolean
}

useReveal()
const { progress } = useScrollProgress()
const { enabled: ff } = useFeature()
const { get: ss } = useSiteSettings()

const route = useRoute()
const router = useRouter()
const id = computed(() => normalizeRouteParam(route.params.id))
const encodedId = computed(() => encodePathId(id.value))
const heroLoaded = ref(false)
const detailOnline = ref(true)
const launchSafety = useLaunchSafety()
const entityLaunchGeneration = createLaunchGenerationGuard(() => launchSafety.resetForNavigation())
entityLaunchGeneration.initialize()

// Client-side route reuse must not carry a previous entity's launch evidence
// into the next request before its own carrier has been checked. Watch the raw
// target as well as the id so query, slash, and encoding aliases cannot reuse
// a positive decision (including an A -> B -> A route sequence).
watch(() => route.fullPath, (next, previous) => {
  if (previous !== undefined && next !== previous) entityLaunchGeneration.begin()
}, { flush: 'sync' })

type HeroNavigationAttempt = {
  readonly fromFullPath: string
  readonly toFullPath: string
}

let pendingHeroNavigation: HeroNavigationAttempt | null = null

function changesHeroRouteIdentity(to: typeof route, from: typeof route): boolean {
  return to.name !== from.name || normalizeRouteParam(to.params.id) !== normalizeRouteParam(from.params.id)
}

const removeHeroNavigationGuard = router.beforeEach((to, from) => {
  if (!changesHeroRouteIdentity(to, from)) return
  pendingHeroNavigation = { fromFullPath: from.fullPath, toFullPath: to.fullPath }
  heroLoaded.value = false
})

const removeHeroNavigationCompletionHook = router.afterEach((to, from, failure) => {
  const pending = pendingHeroNavigation
  if (!pending) return
  const completesPendingNavigation = (
    pending.fromFullPath === from.fullPath && pending.toFullPath === to.fullPath
  ) || to.redirectedFrom?.fullPath === pending.toFullPath
  if (!completesPendingNavigation) return
  pendingHeroNavigation = null
  if (failure || !changesHeroRouteIdentity(to, from)) void revealHeroImageAfterUpdate()
})

onUnmounted(() => {
  removeHeroNavigationGuard()
  removeHeroNavigationCompletionHook()
  window.removeEventListener('online', updateDetailConnectivity)
  window.removeEventListener('offline', updateDetailConnectivity)
})

const { user, isLoggedIn } = useAuth()
const journeyThread = useJourneyThread({
  ownerScope: () => isLoggedIn.value ? String(user.value?.id || 'authenticated') : 'guest',
})
const journeyOwner = computed(() => isLoggedIn.value ? String(user.value?.id || 'authenticated') : 'guest')
const { show: _showToast } = useToast()

async function copyText(text: string, label: string) {
  try {
    await navigator.clipboard.writeText(text)
    _showToast(`Đã sao chép ${label}`, 'success')
  } catch {
    _showToast('Không thể sao chép', 'error')
  }
}

type HeroImageRef = HTMLImageElement | { $el?: unknown } | null
const heroImage = ref<HeroImageRef>(null)

function revealHeroImage(event?: Event) {
  const eventTarget = event?.currentTarget
  const refTarget = heroImage.value
  const image = eventTarget instanceof HTMLImageElement
    ? eventTarget
    : refTarget instanceof HTMLImageElement
      ? refTarget
      : refTarget?.$el instanceof HTMLImageElement
        ? refTarget.$el
        : null
  if (!image?.complete || image.naturalWidth <= 0) return
  heroLoaded.value = true
}

async function revealHeroImageAfterUpdate() {
  await nextTick()
  revealHeroImage()
}

const { track: trackRecent } = useRecentlyViewed()
const { trackEntityView } = useUserEvents()

function trackCurrentEntity() {
  if (!entity.value) return
  trackRecent(entity.value)
  trackEntityView(entity.value, 'entity')
}

function advanceDetailJourney() {
  const restored = journeyThread.restore()
  journeyThread.pushIntent('explore', { currentPath: route.fullPath, returnPath: restored?.returnPath || '/du-lich' })
}

function updateDetailConnectivity() {
  if (!import.meta.client) return
  detailOnline.value = navigator.onLine
}

watch(journeyOwner, advanceDetailJourney)

onMounted(async () => {
  updateDetailConnectivity()
  window.addEventListener('online', updateDetailConnectivity)
  window.addEventListener('offline', updateDetailConnectivity)
  advanceDetailJourney()
  await revealHeroImageAfterUpdate()
  trackCurrentEntity()
})

const RELATIONSHIP_BATCH_SIZE = 24

const goBack = () => goBackOr(journeyThread.returnPath.value || '/du-lich')

const { data: entity, error: fetchError, status: entityStatus, refresh: refreshEntityData } = await useAsyncData(
  computed(() => `entity-${id.value}`),
  async () => {
    const generation = entityLaunchGeneration.current()
    const requestId = id.value
    const carrier = await apiFetch<Entity>(`/api/entities/${encodedId.value}`)
    return { ...carrier, __launchGeneration: generation, __launchRequestId: requestId } satisfies LaunchEntityCarrier
  },
  { watch: [id, () => route.fullPath], deep: false }
)

const { data: galleryCarrier, refresh: refreshGalleryData } = await useAsyncData(
  computed(() => `entity-gallery-${id.value}`),
  async (): Promise<DetailGalleryCarrier> => {
    const requestId = id.value
    try {
      const response = await apiFetch<GalleryResponse>(`/api/entities/${encodedId.value}/gallery`)
      if (!response || !Array.isArray(response.images)) return { requestId, descriptors: [], failed: true }
      const descriptors = response.images.flatMap((raw) => {
        const descriptor = parseGalleryDescriptor(raw)
        return descriptor && descriptor.source_class !== 'user-uploaded' ? [descriptor] : []
      })
      return { requestId, descriptors, failed: false }
    } catch { return { requestId, descriptors: [], failed: true } }
  },
  { watch: [id], deep: false },
)

const galleryDescriptors = computed(() => currentGalleryDescriptors(galleryCarrier.value, id.value))
const galleryPartial = computed(() => galleryCarrier.value?.requestId === id.value && galleryCarrier.value.failed)

async function refreshGallery() {
  await refreshGalleryData()
}

async function refreshEntity() {
  entityLaunchGeneration.begin()
  await refreshEntityData()
}

async function refineCurrentEntityLaunchDecision() {
  if (entityStatus.value === 'idle' || entityStatus.value === 'pending') return
  if (entity.value && !entityLaunchGeneration.isCurrent(entity.value.__launchGeneration)) {
    launchSafety.resetForNavigation()
    return
  }
  if (entity.value && entity.value.__launchRequestId !== id.value) {
    launchSafety.resetForNavigation()
    return
  }
  if (entity.value && entity.value.id !== id.value) {
    await launchSafety.refineEntityPolicy({ carrier: null, expectedKind: 'entity', canonicalPath: '' })
    return
  }
  await launchSafety.refineEntityPolicy({
    carrier: entityStatus.value === 'error' || fetchError.value ? null : entity.value,
    expectedKind: 'entity',
    canonicalPath: entity.value ? entityPath(entity.value.id) : '',
  })
}

await refineCurrentEntityLaunchDecision()
watch(
  [entity, entityStatus, fetchError],
  () => { void refineCurrentEntityLaunchDecision() },
  { flush: 'post' },
)

type JsonLdPayload = Record<string, unknown> | Record<string, unknown>[]

const { data: backendJsonLd } = await useAsyncData(
  computed(() => `entity-jsonld-${id.value}`),
  () => apiFetch<JsonLdPayload>(`/seo/jsonld/${encodedId.value}`).catch(() => null),
  { watch: [id], deep: false }
)

// SSR: throw 404 so the server responds with proper status code.
// Client-side: show error state in-page (fetchError ref drives the template).
const detailFetchResolution = computed<DetailFetchResolution | null>(() => (
  fetchError.value ? resolveDetailFetchError(fetchError.value) : null
))

if (import.meta.server && detailFetchResolution.value?.kind === 'not_found') {
  throw createError({ statusCode: 404, statusMessage: 'Không tìm thấy nội dung' })
}

watch(() => entity.value?.id, () => trackCurrentEntity())

const typeMeta = computed(() => {
  if (!entity.value) return { emoji: '•', icon: 'pin', label: '', cat: 'place' }
  return TYPE_META[entity.value.type] || { emoji: '•', icon: 'pin', label: entity.value.type, cat: 'place' }
})

const detailMaterialAccent = computed(() => resolveRegionalAccent(entity.value?.type))

const areaName = computed(() => {
  const area = entity.value ? getEntityArea(entity.value) : ''
  return AREA_META[area]?.name || area || ''
})

const entityImageDescriptors = computed<ImageDescriptor[]>(() => {
  if (galleryDescriptors.value?.length) return [...galleryDescriptors.value]
  const descriptors = describeEntityImages(entity.value || {})
  return descriptors.length ? descriptors : [createPlaceholderDescriptor()]
})

function createPlaceholderDescriptor(): Readonly<ImageDescriptor> {
  const name = entity.value?.name || 'Địa điểm'
  return Object.freeze({
    url: null,
    alt: `${name} — chưa có ảnh riêng`,
    source_class: 'placeholder',
    source_kind: 'generated-placeholder',
    disclosure_key: 'entity-placeholder',
    short_label: aiDisclosure.placeholder.short_label,
    full_disclosure: aiDisclosure.placeholder.full_disclosure,
    credit: null,
    width: null,
    height: null,
  })
}

const heroDescriptor = computed(() => entityImageDescriptors.value[0] || createPlaceholderDescriptor())
const heroImageIdentity = computed(() => `${id.value}:${heroDescriptor.value.url || 'placeholder'}`)
const hasEntityImages = computed(() => (
  entityImageDescriptors.value.some(descriptor => descriptor.url !== null)
))
const hasEntityGallery = computed(() => (
  hasEntityImages.value && entityImageDescriptors.value.length !== 1
))

const coverImage = computed(() => heroDescriptor.value.url || '')

// Reset stale route state before Vue reuses the hero, then inspect the committed replacement ref.
watch(heroImageIdentity, () => {
  heroLoaded.value = false
}, { flush: 'sync' })

watch(heroImageIdentity, () => {
  void revealHeroImageAfterUpdate()
}, { flush: 'post' })

function sanitizeDisclosureIdToken(value: unknown): string {
  const raw = String(value ?? '').trim()
  if (!raw) return 'entity'
  return encodeURIComponent(raw).replace(/%/g, '_').replace(/[^A-Za-z0-9_-]+/g, '-') || 'entity'
}

const disclosureEntityId = computed(() => sanitizeDisclosureIdToken(entity.value?.id || id.value))
const heroDisclosureId = computed(() => `entity-image-disclosure-${disclosureEntityId.value}-hero`)
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
const coverLightboxRef = ref<{ open: (idx?: number) => void } | null>(null)
function openCoverLightbox(idx = 0) {
  coverLightboxRef.value?.open(idx)
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

// §1.6: breadcrumb đi qua xã/phường (đơn vị hành chính thật) chứ không qua `area`.
// Thiếu placeId, hoặc placeId trỏ tới id không tồn tại (backend không gắn được
// place_name) → null = bỏ hẳn mắt xích, không bịa địa bàn.
const adminUnitBreadcrumb = computed(() => adminUnitCrumb(entity.value))

const seasonLabel = computed(() => seasonText(entity.value?.season))

// P0-3: bỏ paragraph description đầu nếu chỉ lặp lại summary (đã render làm lead
const descriptionSections = computed<DescSection[]>(() =>
  parseDescriptionSections(entity.value?.description, entity.value?.summary))
const hasRichDescription = computed(() => descriptionSections.value.some(s => s.level > 0))
const totalDescParagraphs = computed(() => descriptionSections.value.reduce((n, s) => n + s.paragraphs.length + (s.heading ? 1 : 0), 0))

const descExpanded = ref(false)

const extraContentSections = computed(() => {
  const a = entity.value?.attributes
  if (!a) return []
  const sections: { icon: string; title: string; text: string }[] = []
  if (a.significance && typeof a.significance === 'string')
    sections.push({ icon: 'landmark', title: 'Ý nghĩa', text: a.significance })
  if (a.atmosphere && typeof a.atmosphere === 'string')
    sections.push({ icon: 'leaf', title: 'Không gian', text: a.atmosphere })
  if (a.famous_for && typeof a.famous_for === 'string')
    sections.push({ icon: 'star', title: 'Nổi tiếng với', text: a.famous_for })
  if (a.travel_tips && typeof a.travel_tips === 'string')
    sections.push({ icon: 'bulb', title: 'Mẹo du lịch', text: a.travel_tips })
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
const detailPrimaryAction = computed(() => resolveDetailAction({
  coords: normalizeCoords(entity.value?.coordinates),
  phone: entity.value?.attributes?.phone,
}, { family: 'entity', id: id.value }))

// Đo lượt bấm CTA liên hệ (contact-funnel). Fire-and-forget, KHÔNG await:
// `tel:` rời trang ngay nên beacon dùng keepalive; endpoint chết thì nút vẫn chạy.
function trackContact(action: ContactAction) {
  trackContactView(id.value, action)
}
const hasHighlights = computed(() => !!(entity.value?.attributes?.phone || zaloLink.value || entity.value?.attributes?.hours || priceText.value || addressText.value || hasCoords.value))
const hasVisitFacts = computed(() => { const a = entity.value?.attributes; return !!(a?.hours || a?.price || a?.fee || a?.suggested_duration || a?.transport || a?.vehicle_access || a?.parking) })
const hasContactFacts = computed(() => { const a = entity.value?.attributes; return !!(a?.phone || a?.address || (a?.coords_approximate && hasCoords.value) || a?.website) })
const hasFeatureFacts = computed(() => { const a = entity.value?.attributes; return !!(a?.amenities || a?.price_range || a?.atmosphere || a?.famous_for || a?.significance) })

// The trust CTA files a correction against this entry. It used to drop the
// reader into a community search, which records nothing and promises less.
const reportUrl = computed(() => correctionIntakeLink(id.value, { source: 'dia-diem' }))

const sourceFreshness = computed(() => entity.value?.source_freshness)
const trustTier = computed(() => resolveSourceTier(sourceFreshness.value?.source_tier || entity.value?.quality?.source_tier))
const trustSourceUrl = computed(() => sourceFreshness.value?.source_url || entity.value?.quality?.source_url || '')
const trustSourceTitle = computed(() => sourceFreshness.value?.source_title || entity.value?.quality?.source_title || (trustSourceUrl.value ? 'Nguồn tham khảo' : 'Chưa có nguồn công khai'))
// Bản main gộp `verified_at` vào `trustUpdatedAt`; bản NP-1 tách ra. Lấy bản TÁCH:
// §1.7 phân biệt rõ "cập nhật lúc nào" với "đã kiểm chứng thực địa" — gộp hai thứ đó
// làm một là để ngày sửa nội dung trông như bằng chứng kiểm chứng.
const trustUpdatedAt = computed(() => sourceFreshness.value?.updated_at || entity.value?.updatedAt || '')
const trustVerifiedAt = computed(() => sourceFreshness.value?.verified_at || entity.value?.quality?.verified_at || '')
const trustUpdatedLabel = computed(() => trustUpdatedAt.value ? formatDateVN(trustUpdatedAt.value) : 'Chưa rõ')
const trustFreshnessStatus = computed(() => resolveFreshnessStatus(sourceFreshness.value?.freshness_status))
const trustSourceTier = computed(() => trustTier.value)
const trustStatus = computed(() => trustFreshnessStatus.value)
// Retained as a text contract for integrations; FreshnessLine owns its visible status label.
const trustStatusLabel = computed(() => {
  if (trustFreshnessStatus.value === 'fresh') return 'Mới cập nhật'
  if (trustFreshnessStatus.value === 'aging') return 'Cần kiểm tra định kỳ'
  if (trustFreshnessStatus.value === 'stale') return 'Có thể đã cũ'
  if (trustFreshnessStatus.value === 'conflict') return 'Thông tin có mâu thuẫn'
  return 'Chưa rõ'
})
const trustNote = computed(() => {
  if (trustFreshnessStatus.value === 'fresh') return 'Thông tin này có tín hiệu cập nhật gần đây.'
  if (trustFreshnessStatus.value === 'aging') return 'Thông tin vẫn dùng được nhưng nên kiểm tra lại nếu bạn sắp đi.'
  if (trustFreshnessStatus.value === 'stale') return 'Thông tin có thể đã cũ; hãy báo sai nếu bạn thấy khác thực tế.'
  if (trustFreshnessStatus.value === 'conflict') return 'Các nguồn đang ghi khác nhau; xem từng giá trị và thời điểm trước khi quyết định.'
  return 'Hệ thống chưa có đủ tín hiệu nguồn/ngày cập nhật cho mục này.'
})
const trustStatusTone = computed(() => {
  if (trustStatus.value === 'fresh') return 'fresh'
  if (trustStatus.value === 'aging') return 'aging'
  if (trustStatus.value === 'stale') return 'stale'
  if (trustStatus.value === 'conflict') return 'conflict'
  return 'unknown'
})
const trustConflicts = computed(() => {
  const raw = entity.value?.attributes?.source_conflicts
  if (!Array.isArray(raw)) return []
  return raw.flatMap((item): Array<{ label: string; value: string; sourceTitle?: string; updatedLabel?: string }> => {
    if (!item || typeof item !== 'object' || Array.isArray(item)) return []
    const conflict = item as Record<string, unknown>
    const label = typeof conflict.label === 'string' ? conflict.label.trim() : ''
    const value = typeof conflict.value === 'string' ? conflict.value.trim() : ''
    if (!label || !value) return []
    return [{
      label,
      value,
      ...(typeof conflict.source_title === 'string' && conflict.source_title.trim() ? { sourceTitle: conflict.source_title.trim() } : {}),
      ...(typeof conflict.updated_at === 'string' && conflict.updated_at.trim() ? { updatedLabel: formatDateVN(conflict.updated_at) } : {}),
    }]
  })
})
const trustCommunityContext = computed(() => trustSourceTier.value === 'community'
  ? 'Nguồn cộng đồng đã qua bước kiểm duyệt nội dung; không phải thông tin chính thức.'
  : false)
// P0-7: chỉ hiện trust-card khi CÓ nguồn công khai thật (đừng quảng cáo "chưa có nguồn").
const trustVisible = computed(() => ff('trust_drawer_v1') && !!trustSourceUrl.value)
const trustDrawerOpen = ref(false)

async function reportTrustIssue() {
  trustDrawerOpen.value = false
  await navigateTo(reportUrl.value)
}

// P0-5: byline biên tập (Who) — LUÔN hiện, mọi trang. Trung thực theo
// attributes.verifiedAt (người đặt tay); hiện chưa entity nào có → mặc định
// "chưa kiểm chứng thực địa".
const entityVerifiedAt = computed(() => sourceFreshness.value?.verified_at || '')
const bylineText = computed(() => entityVerifiedAt.value
  ? `Biên tập & kiểm chứng thực địa · ${formatDateVN(entityVerifiedAt.value)}`
  : 'Tổng hợp & biên tập từ nguồn công khai — chưa kiểm chứng thực địa')

// GĐ10.4: normalizeCoords gom vào composables/useCoords.ts (Nuxt auto-import).

// Xem ~/utils/ocop.ts: `attributes.ocop` là văn xuôi, và bản parseInt cũ vừa
// trả 0 cho gần như mọi sản phẩm vừa để chuỗi thô lọt lên giao diện.
const ocopStars = computed(() => Math.min(ocopStarsOf(entity.value as any), 5))
const ocopBadge = computed(() => ocopBadgeLabel(entity.value as any))

// ── Reactive SEO meta: updates when entity changes (client-side navigation) ──
const seoDesc = computed(() => {
  const e = entity.value
  if (!e) return ''
  const raw = e.description ? e.description.split(/\n\s*\n/)[0]?.trim() || e.summary || '' : e.summary || ''
  if (raw.length <= 160) return raw
  return raw.slice(0, 157).replace(/\s+\S*$/, '') + '…'
})

const heroImageMeta = computed(() => buildImageMeta(heroDescriptor.value))

useSeoMeta({
  ogType: 'article',
  title: () => entity.value ? `${entity.value.name} — ${typeMeta.value.label} — vinhlong360` : 'Địa điểm — vinhlong360',
  description: () => seoDesc.value,
  ogTitle: () => entity.value ? `${entity.value.name} — vinhlong360` : 'Địa điểm — vinhlong360',
  ogDescription: () => seoDesc.value,
  ogUrl: () => entity.value ? entityDetailUrl(entity.value.id) : canonicalUrl('/dia-diem'),
  twitterCard: 'summary_large_image',
  ogImage: () => heroImageMeta.value.ogImage,
  ogImageAlt: () => heroImageMeta.value.ogImageAlt,
  twitterImage: () => heroImageMeta.value.twitterImage,
  twitterImageAlt: () => heroImageMeta.value.twitterImageAlt,
})

// JSON-LD + canonical: rebuilt reactively via computed
const fallbackJsonLdScripts = computed(() => {
  const e = entity.value
  if (!e) return []

  const graph = buildEntityDetailSchemaGraph({
    entity: e,
    typeLabel: typeMeta.value.label,
    areaName: areaName.value,
    adminUnitBreadcrumb: adminUnitBreadcrumb.value,
    heroDescriptor: heroDescriptor.value,
    typeBreadcrumbUrl: typeBreadcrumbUrl.value,
  })

  return graph ? [{ type: 'application/ld+json', innerHTML: safeJsonLd(graph) }] : []
})

function normalizeJsonLdPayload(payload: JsonLdPayload | null | undefined) {
  if (!payload) return []
  return (Array.isArray(payload) ? payload : [payload]).filter(Boolean)
}

// Backend /seo/jsonld/{id} (agent/seo.py:519 `_build_breadcrumb`) vẫn phát mắt xích
// `area` cũ (/khu-vuc/...) và payload backend được ưu tiên hơn fallback dưới đây —
// chuẩn hoá tại chỗ để structured-data không lệch breadcrumb hiển thị.
const backendJsonLdScripts = computed(() => normalizeJsonLdPayload(backendJsonLd.value).map(item => ({
  type: 'application/ld+json',
  innerHTML: safeJsonLd(withAdminUnitBreadcrumb(item, adminUnitBreadcrumb.value)),
})))

// P1-3: nếu backend /seo/jsonld fail/rỗng → dùng fallback (BreadcrumbList + entity schema + FAQ)
const jsonLdScripts = computed(() =>
  backendJsonLdScripts.value.length ? backendJsonLdScripts.value : fallbackJsonLdScripts.value)

useHead({
  link: [{ rel: 'canonical', href: () => entity.value ? entityDetailUrl(entity.value.id) : canonicalUrl('/dia-diem') }],
  script: jsonLdScripts,
})
</script>

<!-- detail.css nạp theo route (bỏ khỏi global entry.css; phần dùng-chung ở detail-shared.css) -->
<style src="~/assets/css/detail.css"></style>
