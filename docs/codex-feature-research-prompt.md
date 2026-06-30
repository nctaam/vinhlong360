# Codex Feature Research Prompt — Deep Functional Audit

> Copy TOÀN BỘ nội dung bên dưới vào Codex task.
> **Input:** 6 URLs + toàn bộ codebase trên GitHub
> **Output:** 1 file `docs/feature-audit-report.md` — báo cáo nghiên cứu chức năng so sánh + đề xuất nâng cấp

---

## PROMPT BẮT ĐẦU TỪ ĐÂY

---

# PERSONA

Bạn là **Senior Product Architect** — 15 năm kinh nghiệm xây dựng travel platforms, từng là Product Lead tại 2 OTA lớn (quy mô 10M+ MAU). Bạn không chỉ liệt kê features — bạn **hiểu TẠI SAO** mỗi feature tồn tại, **ai cần nó**, **khi nào nó tạo giá trị**, và **khi nào nó là waste cho team nhỏ**.

**Triết lý:**
> "Feature không có user story thật = waste. Feature copy từ platform 100M users mà áp cho 10K users = self-destruction. Tôi chỉ đề xuất feature mà solo dev có thể build trong 1-2 tuần VÀ tạo giá trị đo được cho user thật."

**Hai lăng kính phân tích:**
1. **Lăng kính Product:** Feature này giải quyết problem gì? Cho ai? Đo bằng metric nào?
2. **Lăng kính Engineering:** Solo dev build được không? Maintain được không? Phá gì không?

---

# NHIỆM VỤ

## Bước 1: Nghiên cứu SÂU 6 platforms

Truy cập, dùng thử, và phân tích TOÀN BỘ chức năng của 6 platforms:

### Platform 1: GetYourGuide (https://www.getyourguide.com/)
**Focus:** Tours & activities marketplace
- Trang chủ: hero search, destination cards, category pills, curated collections
- Discovery: browse by city, browse by category, "things to do in X"
- Detail page: gallery, highlights, itinerary, meeting point, reviews, similar, CTA flow
- Search & filter: location search, date picker, price range, duration, language, rating
- Reviews: verified purchase, photo reviews, response from provider, sorting
- User account: wishlist, bookings, reviews given, notifications
- Collections: curated lists, themed collections
- Content: blog/magazine, travel guides, "X things to do"

### Platform 2: Klook (https://www.klook.com/)
**Focus:** SEA travel activities + deals
- Trang chủ: trending destinations, flash deals, category tabs, app download push
- Discovery: categories deep (food tours, day trips, transport, wifi/sim, attractions)
- Detail page: what's included, how to use, cancellation policy, combo deals
- Reviews: photo reviews, rating breakdown by category, "most helpful"
- User: Klook credits, referral program, membership tiers
- Deals: flash sales, bundle pricing, promo codes
- Blog: destination guides, tips & tricks

### Platform 3: TripAdvisor (https://www.tripadvisor.com/)
**Focus:** Reviews + community + travel planning
- Trang chủ: "Plan your next trip", destination search, trending
- Community: forums, Q&A, travel articles by travelers
- Reviews: detailed review form, photo uploads, helpful votes, management responses
- Rankings: "Top 10", "Travelers' Choice", "#1 of 50 things to do"
- User profiles: contributions, badges, level system, helpful votes received
- Travel planning: trip boards, save & organize, share with friends
- Restaurant/hotel integration: menu, photos, prices, availability (skip for vinhlong360)

### Platform 4: Google Travel (https://www.google.com/travel)
**Focus:** Trip planning + aggregation
- Explore: map-based discovery, "things to do", price insights
- Saved places: from Google Maps, organized in lists
- Travel planning: create trip, add activities, day-by-day view
- Knowledge graph: entity cards, facts, hours, photos, reviews from web
- Integration: Maps, Search, Reviews, Flights, Hotels
- "Things to do": curated from web, user reviews, booking links

### Platform 5: Airbnb (https://www.airbnb.com/)
**Focus:** Accommodation + Experiences marketplace
- Trang chủ: category tabs (icons), map toggle, date/guest filter
- Discovery: "Experiences" category (most relevant for vinhlong360)
- Detail page: host info, reviews, amenities grid, map, house rules, availability
- Reviews: host response rate, superhost badge, photo reviews
- Wishlists: create lists, share, collaborate
- User profiles: verifications, reviews, hosting history
- Community: host forums, local guides, "things to do nearby"

### Platform 6+: TỰ TÌM THÊM tối thiểu 3 platforms tương tự

**Gợi ý (KHÔNG giới hạn):**

| Platform | URL | Tại sao relevant |
|----------|-----|-----------------|
| **Viator** | viator.com | Owned by TripAdvisor, tours & activities focus |
| **Culture Trip** | theculturetrip.com | Editorial + community travel content |
| **Lonely Planet** | lonelyplanet.com | Destination guides + community |
| **Rome2Rio** | rome2rio.com | Multi-modal transport planning |
| **Traveloka** | traveloka.com/vi | SEA travel super-app, Vietnamese market |
| **Agoda** | agoda.com | Strong in SEA, review system |
| **iDiscover** | idiscover.co | Local discovery + walking tours |
| **Atlas Obscura** | atlasobscura.com | Unique/niche attractions, community |
| **Yelp** | yelp.com | Local business reviews & community |
| **Foursquare/Swarm** | foursquare.com | Check-ins, tips, venue discovery |

**Cho MỖI platform thêm:** ghi URL, feature nổi bật, và 1 insight cho vinhlong360.

### Bước 1b: Phân tích đối thủ Việt Nam

Ngoài 9+ platforms quốc tế, BẮT BUỘC phân tích:

| Đối thủ | URL / Kênh | Tại sao relevant |
|---------|------------|-----------------|
| **vinhlongtourist.vn** | vinhlongtourist.vn | Đối thủ trực tiếp — website Sở Du lịch Vĩnh Long |
| **Google Maps khu vực VL** | maps.google.com (search "Vĩnh Long") | User VN dùng Google Maps nhiều nhất cho tìm đường + reviews |
| **Facebook Groups du lịch** | Groups "Du lịch Vĩnh Long", "Ăn gì Vĩnh Long" | Nơi user thật sự trao đổi — competitor trực tiếp cho UGC |
| **Zalo OA** | Zalo OA du lịch Vĩnh Long (nếu có) | Kênh liên hệ phổ biến nhất tại VN |
| **TikTok / YouTube** | Hashtag #dulịchvĩnhlong | Content video du lịch — competitor attention |

Cho MỖI đối thủ VN:
- Điểm mạnh mà vinhlong360 KHÔNG THỂ cạnh tranh (vd: Google Maps ubiquity)
- Điểm yếu mà vinhlong360 CÓ THỂ exploit (vd: Facebook groups không có search, Google Maps không có itinerary builder)
- Feature gap = cơ hội cho vinhlong360

---

### Bước 1c: Vietnamese Digital Behavior Context

**BẮT BUỘC dùng context này khi đánh giá FIT cho mỗi feature:**

| Metric | Giá trị | Source | Ảnh hưởng đến feature decision |
|--------|---------|--------|-------------------------------|
| Zalo MAU | ~75M | Zalo 2024 | CTA Zalo > email. Chat > form. Deep link quan trọng |
| Facebook MAU VN | ~70M | Meta 2024 | Share to Facebook > Twitter/X. OG tags critical |
| Mobile internet | 95% under-30, 85% overall | VNNIC 2024 | Mobile-first bắt buộc. Desktop là secondary |
| Avg bandwidth rural ĐBSCL | 5-15 Mbps 4G, unstable | Viettel/VNPT 2024 | Image optimization critical. Offline cache helpful |
| Screen size phổ biến | 360-414px width (Android mid-range) | StatCounter VN | Test tối thiểu 360px. Không giả sử iPhone |
| Payment culture | Cash + bank transfer + Momo/ZaloPay | — | KHÔNG payment gateway trên site. Invoice offline |
| Content consumption | Scroll-first, video-heavy, ngắn | — | Short content > long articles. Visual > text |
| Trust signals VN | Phone verify > email. Zalo > website. Referral > review | — | OTP phone auth đúng hướng. Zalo CTA quan trọng |
| Search behavior VN | Google VN 95%+. YouTube = search engine #2 | — | SEO Google VN critical. YouTube/TikTok cho discovery |
| Seasonality | Tết + hè (6-8) + lễ 30/4-1/5 + 2/9 | — | Seasonal content/guide cần ready TRƯỚC mùa cao điểm |

---

## Bước 2: Đọc TOÀN BỘ codebase vinhlong360 trên GitHub

**BẮT BUỘC đọc trước khi phân tích:**

### Hệ thống hiện có — INVENTORY ĐẦY ĐỦ

#### A. Backend API (175+ endpoints)

| Nhóm | Endpoints | Mô tả |
|------|-----------|-------|
| **Entity** | 18 | CRUD, search, detail, gallery, relationships, nearby, related |
| **Auth** | 17 | OTP login, sessions, profile, avatar, cover, privacy, deactivate, login history |
| **Social** | 29 | Posts (4 types: review/share/recommend/question), comments, likes, bookmarks, feeds, leaderboard, trending tags, suggested follows, repost, Q&A best-answer |
| **Notifications** | 13 | Fetch, mark read, SSE stream, follow/unfollow, block, preferences |
| **Saved** | 4 | Favorites CRUD, merge duplicates |
| **Itinerary** | 5 | User plans CRUD, publish to shared |
| **Visits** | 4 | Track visited/want-to-visit entities |
| **Admin** | 68 | Entity CRUD, data quality, images, moderation, analytics, user mgmt, site settings (16 categories), audit log, reports, AI triage, media library, backup |
| **SEO** | 9 | Sitemaps, JSON-LD, OG tags, robots.txt |
| **Chat/AI** | 8 | Multi-turn chat, tool use, streaming, feedback |

#### B. Frontend Pages (70 pages)

**Public (37 pages):**
- Homepage (bento layout, hero search, trending, spotlight, community)
- Entity browsing: catalog `/dia-diem`, detail `/dia-diem/[id]`, ward `/xa-phuong/[id]`
- Category pages: `/ocop`, `/san-pham`, `/luu-tru`, `/su-kien`, `/le-hoi`, `/tuyen-duong`
- Discovery: `/kham-pha/[interest]`, `/khu-vuc/[area]`, `/theo-mua`, `/ban-do`, `/tim-kiem`
- Itinerary: catalog, detail, builder, shared view
- Community: `/cong-dong`, `/bai-viet/[id]`, `/nguoi-dung/[id]`, `/bang-xep-hang`, `/danh-ba`
- User: settings, notifications, policy pages

**Admin (33 pages):**
- Dashboard + entity CRUD + moderation + analytics + user mgmt + 16 settings pages + media + reports + audit log + AI management

#### C. Database (25 tables)

| Nhóm | Tables |
|------|--------|
| Knowledge | entities, relationships, itineraries, feedback, query_log |
| Auth | users, otp_sessions, user_sessions |
| UGC | posts (4 types), comments, likes, bookmarks, entity_ratings |
| Community | follows, notifications, reports, blocks, moderation_log |
| Personal | saved_entities, user_plans, user_visits |
| Config | site_settings |

#### D. Composables (38)
`useAuth`, `useNotifications`, `useFavorites`, `useRecentlyViewed`, `useDrafts`, `useAdminPrefs`, `useToast`, `useConfirm`, `useAuthModal`, `useReport`, `useModalA11y`, `useReveal`, `useScrollFade`, `useRouting`, `useFilterUrl`, `usePagination`, `useInfiniteScroll`, `useFetchError`, `useSearchRecents`, `useMentionAutocomplete`, `useRepost`, `usePageContent`, `useSeoHelpers`, `useCoords`, `useNDAMap`, `useRegionPref`, `useSeason`, `useSeasonTheme`, `useTimeAgo`, `useConstants`, `useLunar`, `useCategoryPlaceholder`, `useFeature`, `useClientError`, `useErrorDetail`, `useDebounce`, `useAI`

#### E. Key Features ALREADY Implemented

| Feature | Status | Chi tiết |
|---------|--------|----------|
| **Entity catalog + search** | ✅ Full | Hybrid search (keyword+semantic), filters (type/area/season/rating/OCOP), faceted browse, map view |
| **Entity detail** | ✅ Full | Gallery, attributes, reviews, relationships, nearby, JSON-LD, OG tags |
| **OTP auth** | ✅ Full | Phone-based, session management, login history, multi-device |
| **User profiles** | ✅ Full | Avatar, cover, bio, activity, followers/following, contribution stats |
| **Posts (4 types)** | ✅ Full | Review (1-5 star), share, recommend, question (Q&A + best-answer) |
| **Comments** | ✅ Full | Threaded, @mentions, edit/delete |
| **Likes + Bookmarks** | ✅ Full | Like posts, bookmark posts |
| **Following** | ✅ Full | Follow users + entities, feed, suggested follows |
| **Notifications** | ✅ Full | SSE real-time, preferences, grouping, types: like/comment/mention/follow |
| **Leaderboard** | ✅ Full | Rank by contributions, badges, reputation |
| **Hashtags** | ✅ Full | Auto-extract, trending, search by tag |
| **Repost** | ✅ Full | Share with attribution |
| **Block** | ✅ Full | User blocking, enforcement |
| **Favorites** | ✅ Full | Save entities, sync across devices, snapshots |
| **Itineraries** | ✅ Full | Admin-created + user builder + public sharing |
| **Visit tracking** | ✅ Full | Visited / want-to-visit per entity |
| **Map** | ✅ Full | Leaflet/OSM, pins by type, clustering, filter |
| **Reviews/Ratings** | ✅ Full | 1-5 star, aggregate, per-entity |
| **Chat/AI** | ✅ Full | Multi-turn, tool use, streaming, feedback, rate limiting |
| **Admin CMS** | ✅ Full | Entity CRUD, moderation, analytics, 16 settings categories, data quality, media library, audit log, reports |
| **SEO** | ✅ Full | Sitemaps, JSON-LD (6 types), OG tags, robots.txt, meta per page |
| **Seasonal browse** | ✅ Full | Browse by month, seasonal badges |
| **Recently viewed** | ✅ Full | Local history |
| **Drafts** | ✅ Full | Auto-save posts locally |
| **RSVP** | ✅ Full | Event attendance |
| **Search** | ✅ Full | Global search, autocomplete, recent searches, trending |

---

## Bước 3: SO SÁNH & PHÂN TÍCH

Cho MỖI nhóm chức năng, viết phân tích theo format 7 tầng:

### Tầng 1: FEATURE MAP — Các platform có gì?

Bảng so sánh chi tiết:

```markdown
| Feature | GYG | Klook | TA | Google | Airbnb | vinhlong360 | Gap? |
|---------|-----|-------|----|--------|--------|-------------|------|
| Photo reviews | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | YES |
| ... | ... | ... | ... | ... | ... | ... | ... |
```

### Tầng 2: WHY — Tại sao feature này tồn tại?

- **User problem:** Feature này giải quyết vấn đề gì của người dùng?
- **Business value:** Feature này tạo giá trị kinh doanh gì?
- **Metric:** Đo bằng gì? (engagement, retention, conversion, SEO, trust)
- **Research:** Có nghiên cứu UX/product nào chứng minh? (NNGroup, Baymard, academic)

### Tầng 3: FIT — vinhlong360 CÓ CẦN feature này không?

Đánh giá qua 5 tiêu chí:

| Tiêu chí | Câu hỏi | Scoring |
|----------|---------|---------|
| **User need** | User 10K du lịch Vĩnh Long có cần? | 1-5 |
| **Solo dev feasibility** | 1 người build + maintain được? | 1-5 |
| **Budget fit** | Chạy được với <1tr/tháng? | 1-5 |
| **Legal fit** | Không vi phạm NĐ147, NĐ52/85? Không cần giấy phép? | 1-5 |
| **Existing coverage** | Hệ thống hiện có cover bao nhiêu %? | 0-100% |

**Tổng score < 12** → SKIP (giải thích tại sao)
**Tổng score 12-18** → CONSIDER (ghi điều kiện)
**Tổng score > 18 + coverage < 70%** → PRIORITY (ghi action plan)

### Tầng 4: CURRENT STATE — Hệ thống đang có gì?

- File/module nào implement?
- Bao nhiêu % complete so với "world-class"?
- Có bug/limitation nào?
- UX hiện tại tốt chưa?

**BẮT BUỘC grep codebase** để verify — KHÔNG đoán. Ví dụ:
```
grep -rn "photo.*review\|review.*photo\|image.*review" agent/ web-nuxt/ --include="*.py" --include="*.vue" --include="*.ts"
```

### Tầng 5: UPGRADE — Cần nâng cấp gì?

Cho mỗi feature được đánh giá PRIORITY hoặc CONSIDER:

```markdown
#### Upgrade U-XX: [Tên upgrade]

**Problem:** [User problem cụ thể]
**Current:** [Trạng thái hiện tại]
**Target:** [Trạng thái mong muốn]
**Effort:** S (< 1 ngày) / M (1-3 ngày) / L (1-2 tuần) / XL (> 2 tuần → CẨN THẬN)
**Dependencies:** [Cần gì trước?]
**Files to change:** [file:function cụ thể]
**Metric:** [Đo thành công bằng gì?]
**Risk:** [Có phá gì không? Migration? Data loss?]
```

### Tầng 6: SKIP — Tại sao KHÔNG làm?

Cho mỗi feature bị SKIP, giải thích RÕ:
- **Platform X có nhưng vinhlong360 KHÔNG CẦN vì:** [lý do cụ thể]
- **Anti-pattern nếu copy:** [chuyện gì xảy ra nếu cố làm]

### Tầng 7: INNOVATION — Feature mà KHÔNG platform nào có?

Suy nghĩ feature ĐỘC ĐÁO cho vinhlong360 mà các platform lớn KHÔNG làm (vì họ phục vụ toàn cầu, không phải 1 vùng cụ thể):
- **Local knowledge advantage:** Thông tin chỉ người địa phương biết
- **Cultural specificity:** Feature cho văn hóa Việt Nam / ĐBSCL
- **Community-first:** Feature mà platform thương mại bỏ qua
- **Budget advantage:** Feature mà platform lớn quá phức tạp để làm nhưng solo dev lại đơn giản

---

# USER PERSONAS — Đánh giá FIT cho mỗi persona

Khi đánh giá FIT score cho feature, BẮT BUỘC xét qua 5 personas:

### P1. Du khách từ Sài Gòn (70% traffic dự kiến)
- **Profile:** 25-40 tuổi, smartphone Android mid-range, 4G, weekend trip 1-2 ngày
- **Goal:** Tìm nhanh "đi đâu, ăn gì" → lập kế hoạch → liên hệ trực tiếp
- **Behavior:** Google search → vào site → scan nhanh → save hoặc gọi → đi
- **Pain points:** Thông tin cũ/sai, không biết mùa nào đẹp, không biết đường đi
- **Key features:** Search, Detail page, Map, CTA (Zalo/Phone), Itinerary, Seasonal

### P2. Người bản địa Vĩnh Long / Bến Tre / Trà Vinh
- **Profile:** 20-50 tuổi, biết rõ khu vực, muốn CHIA SẺ hiểu biết + tự hào quê
- **Goal:** Viết review, chia sẻ tips, giúp du khách, được công nhận
- **Behavior:** Đăng ký → viết review → follow entities → trả lời Q&A
- **Pain points:** Thiếu nơi chia sẻ (chỉ có Facebook groups), contribution không được ghi nhận
- **Key features:** Community, Reviews, Reputation/Badges, Profile, Q&A

### P3. Admin / Content Manager (Sở Du lịch hoặc đối tác)
- **Profile:** 30-50 tuổi, desktop, quản lý nội dung, cần dashboard
- **Goal:** Cập nhật entities, xem analytics, kiểm duyệt UGC, xuất báo cáo
- **Behavior:** Đăng nhập admin → check dashboard → xử lý queue → cập nhật content
- **Pain points:** Workflow chậm, thiếu batch operations, khó biết content nào cần update
- **Key features:** Admin CMS, Analytics, Moderation, Data quality, Reports

### P4. Du khách quay lại (retention target)
- **Profile:** Đã visit 1+ lần, đã save entities, muốn khám phá thêm
- **Goal:** Tìm cái MỚI (chưa đi), xem reviews mới, lập trip tiếp
- **Behavior:** Quay lại → check saved → xem "có gì mới" → lập trip mới
- **Pain points:** Không biết có gì mới, content cũ vẫn hiện đầu, trùng lặp
- **Key features:** Personalization, Notifications, Collections, "What's new", Seasonal

### P5. Du khách nhóm / gia đình (trip planner)
- **Profile:** 1 người plan cho 4-8 người, cần chia sẻ lịch trình, coordinate
- **Goal:** Tạo lịch trình 2-3 ngày → share qua Zalo → điều chỉnh cùng nhau
- **Behavior:** Browse → save nhiều → tạo itinerary → share link → in/export
- **Pain points:** Nhiều người cùng góp ý nhưng không có nơi tập trung
- **Key features:** Itinerary builder, Share, Print/Export, Collections, Map route

**Yêu cầu cho Codex:** Mỗi upgrade card U-XX phải ghi "Primary persona: P[X]" + "Secondary: P[Y]". Feature không phục vụ persona nào cụ thể = RED FLAG.

---

# USER JOURNEY MAP — Đánh giá feature theo journey stage

Mỗi feature phải map vào 1+ stage trong journey:

```
[DISCOVER] → [RESEARCH] → [PLAN] → [VISIT] → [SHARE] → [RETURN]
  F1,F2        F3,F4         F7       F8,F12     F6,F4      F9,F15
  F11,F15      F16           F10                  F5         F10
```

| Stage | User doing | Key features | Success metric |
|-------|-----------|--------------|----------------|
| DISCOVER | Google search, browse homepage, explore map | F1, F2, F8, F11, F15 | Pages/session, bounce rate |
| RESEARCH | Read detail page, check reviews, compare | F3, F4, F16, F17 | Time on detail page, review reads |
| PLAN | Save entities, build itinerary, share | F7, F10, F12 | Itineraries created, saves |
| VISIT | Navigate to location, check hours, call | F8, F12, F18 | CTA clicks, directions opened |
| SHARE | Write review, post photos, recommend | F4, F6, F5 | Reviews written, posts created |
| RETURN | Check notifications, see what's new | F9, F15, F10 | D30 retention, return visits |

**Yêu cầu cho Codex:** Ghi mỗi feature thuộc journey stage nào. Identify stage nào hiện YẾEST (= priority upgrade area).

---

# FEATURE INTERACTION MAP

Features không độc lập — chúng tạo feedback loops. BẮT BUỘC phân tích các mối liên kết:

```
F4 Reviews ──→ F16 Social Proof ──→ F1 Discovery (entities có review xếp cao hơn)
    ↑                                        ↓
F5 Reputation ←── F6 Community ←── F14 Onboarding (user mới → post đầu tiên)
    ↓
F9 Notifications ──→ F15 Personalization ──→ F7 Itinerary (gợi ý dựa trên behavior)
    ↑
F10 Save ──→ F12 CTA (saved entities → smart re-engagement)
```

**Yêu cầu cho Codex:**
1. Vẽ dependency graph đầy đủ giữa 20 F-groups
2. Identify "keystone features" — feature nào nếu yếu sẽ làm yếu nhiều feature khác?
3. Identify "force multipliers" — upgrade 1 feature nào sẽ improve 3+ features khác?
4. Xếp priority upgrades theo force-multiplier effect, KHÔNG chỉ theo standalone value

---

# PHASED ROLLOUT STRATEGY

Upgrades phải phù hợp với SCALE hiện tại. Codex BẮT BUỘC chia recommendations theo milestones:

| Phase | User count | Focus | Feature priorities |
|-------|-----------|-------|-------------------|
| **NOW** (0-100 users) | Seeding | Content quality, SEO, cold-start | F11 Content, F1 Discovery, F3 Detail, F2 Search, F14 Onboarding cold-start |
| **GROW** (100-1K users) | Engagement | Community participation, reviews | F4 Reviews, F6 Community, F5 Reputation, F9 Notifications, F12 CTA tracking |
| **SCALE** (1K-10K users) | Retention | Personalization, collections, depth | F15 Personalization, F10 Collections, F7 Itinerary, F16 Social Proof |
| **SUSTAIN** (10K+ users) | Revenue | Monetization, advanced analytics | F20 Monetization, F19 Analytics advanced, F13 Admin advanced |

**Yêu cầu cho Codex:** Mỗi upgrade card phải ghi "Phase: NOW/GROW/SCALE/SUSTAIN". Feature thuộc SUSTAIN nhưng recommend cho NOW = anti-pattern.

---

# MOBILE-FIRST AUDIT REQUIREMENT

85% users sẽ dùng mobile. Cho MỖI feature trong F1-F20, Codex BẮT BUỘC phân tích:

| Aspect | Mobile consideration | Desktop consideration |
|--------|---------------------|---------------------|
| **Layout** | Single column, bottom-heavy CTA | Multi-column, sidebar |
| **Navigation** | Bottom tabs, hamburger, back gesture | Top nav, breadcrumb, sidebar |
| **Touch targets** | ≥ 44×44px (Apple HIG), ≥ 48×48dp (M3) | Click targets smaller OK |
| **Scrolling** | Infinite scroll, pull-to-refresh | Pagination OK, no pull-to-refresh |
| **Input** | Bottom sheet > modal, native pickers, OTP auto-read | Modal OK, datepicker |
| **Media** | Carousel swipe, vertical video, compressed images | Grid gallery, lightbox |
| **Performance** | < 3s LCP on 4G, skeleton loading mandatory | < 2s LCP |
| **Offline** | Service Worker cache essential pages | Nice-to-have |

**Yêu cầu cho Codex:** Mỗi F-group phải có "📱 Mobile audit" sub-section ghi: (a) mobile-specific UX, (b) mobile-specific optimization, (c) mobile-specific limitation. Feature chỉ tốt trên desktop = low priority.

---

# 20 NHÓM CHỨC NĂNG CẦN PHÂN TÍCH

Phân tích TỪNG nhóm theo format 7 tầng ở trên:

## F1. DISCOVERY & BROWSING

### Sub-features cần phân tích chi tiết:

**F1.1 Homepage experience**
- Hero section: search bar trung tâm (Google Travel) vs content-first grid (Airbnb) vs destination cards (GYG)?
- Tại sao quan trọng: homepage = 60-70% first impression. Bounce rate tăng 32% nếu user không thấy value trong 3 giây (NNGroup)
- Cần có gì: (a) search bar prominent, (b) seasonal/trending content, (c) popular destinations, (d) community highlights, (e) CTA rõ ràng
- Tối ưu gì: load time < 2s (LCP), above-fold content không cần scroll để thấy value, mobile-first layout
- Phân tích: vinhlong360 hiện có bento layout — so sánh hiệu quả vs các mô hình khác. GYG dùng hero search, Airbnb dùng category tabs, TripAdvisor dùng destination search. Mô hình nào phù hợp cho 10K users du lịch vùng cụ thể?

**F1.2 Category navigation**
- Horizontal pills (Airbnb/Klook) vs tabs (GYG) vs sidebar (TripAdvisor) vs mega-menu?
- Cần có gì: (a) visual icons per category, (b) scroll horizontal on mobile, (c) active state rõ, (d) count per category, (e) sticky on scroll
- Tối ưu gì: max 7-9 categories visible (Miller's Law), icon+text (không chỉ text), smooth scroll snap
- vinhlong360 có 8+ entity types — đang hiển thị thế nào? Có filter chips? Có icon per type?

**F1.3 Destination browsing**
- By region: GYG "Things to do in Paris" / Google Travel explore map / TripAdvisor destination page
- By interest: "Food tours", "Nature", "Heritage" — Klook category deep dive
- By season: "Best in December" — seasonal discovery
- By occasion: "Gia đình", "Cặp đôi", "Nhóm bạn" — trip type filter
- Cần có gì: (a) area overview pages, (b) interest-based landing pages, (c) seasonal landing pages, (d) combination filters
- Tối ưu gì: SEO cho long-tail "du lịch Vĩnh Long tháng 3", internal linking hub-spoke
- vinhlong360 có `/khu-vuc/[area]`, `/kham-pha/[interest]`, `/theo-mua` — đã cover bao nhiêu %? Chất lượng content mỗi trang?

**F1.4 Curated collections**
- GYG: "Top 10 things to do", "Hidden gems", "Family activities"
- TripAdvisor: "Travelers' Choice", "Top-rated near you"
- Airbnb: "Unique stays", "Trending experiences"
- Cần có gì: (a) admin-curated lists, (b) auto-generated "top rated", (c) seasonal "best right now", (d) user-curated lists
- Tối ưu gì: không chỉ static list — dynamic dựa trên rating/season/trending
- Tại sao cần: collections tăng time-on-site 40%+ (GYG internal data), giúp user không bị overwhelmed

**F1.5 "Near me" & location-based**
- Google Travel: map-first, auto-detect location
- Airbnb: "Explore nearby"
- Cần có gì: (a) geolocation permission request UX, (b) distance display on cards, (c) sort by distance, (d) "popular near you" section
- Tối ưu gì: privacy-first (ask permission politely), fallback khi user từ chối location, hiển thị khoảng cách bằng "X km" hoặc "X phút lái xe"

**F1.6 Cross-entity discovery**
- "People also viewed" (Amazon-style collaborative filtering)
- "Related entities" (graph-based: same area, same type, same itinerary)
- "After visiting X, try Y" (sequential recommendation)
- Cần có gì: (a) relationship-based suggestions, (b) co-visitation data, (c) editorial "pairs well with"
- Tối ưu gì: KHÔNG dùng ML phức tạp — dùng relationship graph đã có + visit co-occurrence đơn giản
- vinhlong360 có `relationships` table — đang dùng cho suggestions chưa? Hiệu quả thế nào?

**Yêu cầu phân tích cho Codex:**
> Cho F1, nghiên cứu chi tiết homepage flow của MỖI platform. Screenshot hoặc mô tả pixel-level layout. So sánh conversion path: user đến homepage → tìm được entity quan tâm mất bao nhiêu click? vinhlong360 hiện mất bao nhiêu click? Đề xuất giảm friction cụ thể.

---

## F2. SEARCH & FILTER

### Sub-features cần phân tích chi tiết:

**F2.1 Search bar UX**
- GYG: "Where to?" + destination autocomplete + activity autocomplete
- Klook: category tabs above search + trending searches below
- Google: instant results as you type, rich previews
- TripAdvisor: separate search for hotels/restaurants/activities
- Cần có gì: (a) single search bar, (b) autocomplete với entity names + areas + categories, (c) recent searches, (d) trending searches, (e) typo correction (đã có), (f) rich preview in dropdown
- Tối ưu gì:
  - Debounce: 200-300ms (quá nhanh = quá nhiều requests, quá chậm = user thấy lag)
  - Max 8 suggestions (Miller's Law)
  - Highlight matching text in suggestions
  - Category icon next to each suggestion
  - "Tìm kiếm phổ biến" khi search bar empty (zero-state)
  - Keyboard navigation (arrow keys + enter)
- Tại sao: 30% users dùng search là primary navigation (Baymard). Search UX kém = user bỏ site
- vinhlong360 có hybrid search + autocomplete — UX hiện tại đủ tốt chưa? So sánh vs GYG/Google

**F2.2 Filter system**
- Chips (Airbnb): horizontal scroll, multi-select, clear all
- Panel (TripAdvisor): sidebar with checkboxes, ranges
- Bottom sheet (Klook mobile): full-screen filter on mobile
- Cần có gì:
  - Type filter: chips với icon per type
  - Area filter: dropdown hoặc chips per huyện/xã
  - Rating filter: "4+ sao" threshold buttons
  - Season filter: "Tốt nhất tháng này" toggle
  - OCOP filter: certified-only toggle
  - Active filter count badge: "3 bộ lọc đang áp dụng"
  - Clear all: reset một chạm
  - URL sync: filters reflect in URL (shareable, SEO)
- Tối ưu gì:
  - Mobile: bottom sheet full-screen (Klook pattern) — KHÔNG sidebar
  - Desktop: horizontal chips + collapsible panel
  - Instant results (không cần nhấn "Áp dụng" — filter ngay khi chọn)
  - Show result count per filter option: "Di tích (23)", "Ẩm thực (45)"
  - Preserve filters across navigation (back button keeps filters)
- Tại sao: users rời site nếu phải scroll qua 100+ results không filter (Baymard: 76% users dùng filter trên e-commerce)
- vinhlong360 có `/dia-diem?type=X&area=Y` — filter UX hiện tại cần cải thiện gì cụ thể?

**F2.3 Sort options**
- Cần có gì: Relevance (default), Rating (cao→thấp), Popularity (views/saves), Distance (nếu có location), Newest, Alphabetical
- Tối ưu gì: dropdown hoặc chips, nhớ sort preference per session
- Tại sao: sort khác nhau phục vụ intent khác nhau ("best" vs "newest" vs "nearest")

**F2.4 Map search**
- Google Travel: pan map → results update
- Airbnb: split screen list + map, pins update khi filter
- Cần có gì: (a) map view toggle, (b) search within map bounds, (c) cluster pins → expand on zoom, (d) pin click → preview card, (e) list ↔ map sync (hover list = highlight pin)
- Tối ưu gì: lazy load pins (không load 1000+ pins lúc đầu), debounce map move → search
- vinhlong360 có `/ban-do` — map search có update results khi pan không? Có sync với list view không?

**F2.5 Zero-results experience**
- Cần có gì: (a) friendly message, (b) spelling suggestions, (c) broader search suggestions, (d) popular entities, (e) clear filter CTA
- Tối ưu gì: KHÔNG bao giờ dead-end. Luôn có next action cho user
- Tại sao: zero-result page = 100% bounce nếu không có recovery path

**F2.6 Search analytics (admin)**
- Cần có gì: (a) popular queries dashboard, (b) zero-result queries list, (c) query → click-through entity mapping, (d) search conversion rate
- Tại sao: zero-result queries = content gaps → guide content creation priorities

**Yêu cầu phân tích cho Codex:**
> Thử search trên mỗi platform: "vườn trái cây", "ăn gì", "homestay" — so sánh UX flow, số bước, chất lượng suggestions. Đề xuất search UX lý tưởng cho vinhlong360 với wireframe mô tả.

---

## F3. ENTITY DETAIL PAGE

### Sub-features cần phân tích chi tiết:

**F3.1 Photo gallery**
- GYG: 1 hero + thumbnail strip, lightbox with counter
- Airbnb: asymmetric grid (1 large + 4 small), "Show all photos" button
- TripAdvisor: hero carousel + "See all X photos" + user-submitted tab
- Cần có gì: (a) hero image prominent, (b) multiple images visible, (c) lightbox with swipe, (d) image counter "X/Y", (e) download/share per image, (f) lazy load below-fold images
- Tối ưu gì:
  - Mobile: horizontal swipe carousel + dot indicators
  - Desktop: grid (1 large + 2-4 small) + "Xem tất cả" overlay
  - `aspect-ratio: 3/2` consistent
  - WebP/AVIF with JPEG fallback
  - Skeleton placeholder with matching aspect ratio (CLS prevention)
  - `fetchpriority="high"` on hero image
- Tại sao: ảnh = yếu tố #1 quyết định user click vào entity (Airbnb: listings with 20+ photos get 2x more engagement)
- vinhlong360 dùng AI-generated images — gallery experience hiện tại thế nào? Có lightbox? Có counter?

**F3.2 Key facts panel (structured info)**
- GYG: duration, language, group size, highlights
- Google Travel: hours, address, phone, rating, busy times
- TripAdvisor: price range, cuisine, hours, address
- Airbnb: beds, baths, guests, amenities icons
- Cần có gì cho vinhlong360:
  - 🕐 Giờ mở cửa (với "Đang mở" / "Đã đóng" realtime badge)
  - 📍 Địa chỉ (link Google Maps)
  - 📞 Điện thoại (click-to-call)
  - 🌤️ Mùa tốt nhất (tháng X-Y)
  - ⭐ Rating trung bình + số reviews
  - 🏷️ Loại hình (di tích, ẩm thực, OCOP...)
  - 🎫 Phí vào cổng / Miễn phí (text, KHÔNG giá chính xác)
  - ♿ Accessibility info (xe lăn, người cao tuổi)
- Tối ưu gì: hiển thị above-fold, icon + label + value format, responsive grid 2 cột mobile / 3 cột desktop
- Tại sao: structured info = scan nhanh → quyết định nhanh → engagement cao hơn. Users đọc facts trước description (NNGroup eye-tracking)

**F3.3 Description & content structure**
- Cần có gì: (a) short summary (2-3 câu, SEO meta description), (b) full description expandable, (c) highlights/tips bullet list, (d) "Điểm nổi bật" section, (e) history/culture context
- Tối ưu gì: truncate description > 3 dòng trên mobile, "Xem thêm" expand, inverted pyramid (quan trọng trước)
- Tại sao: 79% users scan không đọc hết (NNGroup). Structured > wall-of-text

**F3.4 Amenities / features grid**
- Airbnb: icon grid với labels, "Show all X amenities" expand
- GYG: "What's included" checklist, "What's not included"
- Cần có gì: icon + label grid (2-3 cột), top 6 shown + "Xem thêm", negative info ("Không có WiFi")
- Tối ưu gì: consistent icon set (Tabler icons đã dùng), max 2 rows visible on mobile

**F3.5 Related entities section**
- Cần có gì: (a) "Gần đây" — same area, sorted by distance, (b) "Cùng loại" — same type, sorted by rating, (c) "Cùng lộ trình" — entities in same itinerary, (d) "Người dùng cũng xem" — co-visitation
- Tối ưu gì: horizontal scroll cards (không pagination), lazy load, max 8 per row
- Tại sao: related entities tăng pages/session 30%+ (internal link juice cho SEO)
- vinhlong360 có `relationships` table + `/api/entities/[id]/related` — đang hiển thị thế nào? Có đủ 4 loại related?

**F3.6 Contact/CTA section**
- Cần có gì: (a) Zalo chat button (deep link), (b) Phone call button (tel: link), (c) Chỉ đường (Google Maps deep link), (d) Lưu (favorite), (e) Chia sẻ (Web Share API)
- Tối ưu gì:
  - Mobile: sticky bottom bar 56px với 2-3 CTA (Zalo + Phone + Save)
  - Desktop: sidebar card sticky với full CTA list
  - CTA analytics: track which button clicked, for which entity
  - Zalo deep link format: `https://zalo.me/[phone]`
  - Safe area padding: `env(safe-area-inset-bottom)` cho iPhone
- Tại sao: CTA = conversion point duy nhất (vì KHÔNG có booking). Nếu CTA khó tìm/khó bấm = user bỏ đi

**F3.7 Section order (page anatomy)**
- Nghiên cứu section order từ 5 platforms:
  - GYG: Gallery → Title+Facts → Highlights → Description → Itinerary → Meeting Point → Reviews → Similar → Sticky CTA
  - TripAdvisor: Gallery → Title+Rating → Facts → Description → Reviews → Nearby → Map
  - Google: Gallery → Title+Rating+Facts → Description → Reviews → Hours/Map → Related
- Đề xuất section order tối ưu cho vinhlong360, giải thích TẠI SAO mỗi section ở vị trí đó

**Yêu cầu phân tích cho Codex:**
> Mở entity detail page trên mỗi platform, liệt kê TỪNG section theo thứ tự từ trên xuống. Vẽ wireframe mô tả layout lý tưởng cho vinhlong360. Ghi rõ: section nào above-fold, section nào lazy load, section nào expandable.

---

## F4. REVIEWS & RATINGS

### Sub-features cần phân tích chi tiết:

**F4.1 Rating system design**
- Star rating (GYG, TripAdvisor, Google): 1-5 sao, half-star, average display
- Bubble rating (TripAdvisor cũ): 1-5 circles — phân biệt thương hiệu
- Thumbs (YouTube): like/dislike — quá đơn giản cho travel
- Multi-criteria (TripAdvisor restaurants): Food, Service, Value, Atmosphere — riêng
- Cần có gì cho vinhlong360:
  - ⭐ Overall rating: 1-5 sao (standard)
  - 📊 Rating breakdown: 4 criteria cho points-of-interest:
    - Không khí / Cảnh quan (Atmosphere/Scenery)
    - Chất lượng / Trải nghiệm (Quality/Experience)
    - Giá trị (Value — dù miễn phí vẫn có "đáng đi không?")
    - Tiện nghi / Dịch vụ (Amenities/Service)
  - 📈 Distribution chart: horizontal bars (5★ = 60%, 4★ = 25%, ...)
- Tối ưu gì: half-star input (drag hoặc tap), animated star fill, clear label cho mỗi mức (1=Kém, 2=Trung bình, 3=Khá, 4=Tốt, 5=Xuất sắc)
- Tại sao multi-criteria: overall rating che giấu trade-offs. "4 sao" có thể là "cảnh đẹp nhưng dịch vụ kém" hoặc "cảnh bình thường nhưng đồ ăn tuyệt" → user cần chi tiết hơn

**F4.2 Review form UX**
- Cần có gì:
  - Star selector (tap each criteria)
  - Text review: min 50 chars, max 2000 chars, character counter
  - Photo upload: max 5 photos, preview grid, remove per photo
  - Visit date: month/year picker (không cần exact date)
  - Trip type: "Một mình", "Cặp đôi", "Gia đình", "Nhóm bạn", "Công tác"
  - Tips: toggle "Có tips cho người đến sau không?" + text input
  - Preview before submit: full review preview
- Tối ưu gì:
  - Progressive: star first → text → photos → metadata (KHÔNG form dài 1 lần)
  - Auto-save draft: nếu user rời giữa chừng, quay lại vẫn còn
  - Mobile-optimized: large touch targets, native photo picker
  - Encouraging copy: "Chia sẻ trải nghiệm để giúp người khác" thay "Viết đánh giá"
- Tại sao: review form phức tạp = ít review hơn. Mỗi bước thêm = 20% drop-off (Baymard funnel research). Progressive approach giữ completion rate cao

**F4.3 Review display & interaction**
- Cần có gì:
  - Sort: Mới nhất, Hữu ích nhất, Rating cao nhất, Rating thấp nhất, Có ảnh
  - Filter: By star rating, by trip type, by date range
  - Helpful votes: "Hữu ích?" button + count
  - Photo reviews: image inline, tap to lightbox
  - Response from owner: indented reply với verified badge
  - Review highlights: AI-extracted "Nhiều người khen: view đẹp, đồ ăn ngon, nhân viên thân thiện"
  - Review summary: AI-generated 2-3 câu tổng hợp (NẾU có đủ reviews)
  - Pagination: "Xem thêm đánh giá" (lazy load 10 per batch)
- Tối ưu gì:
  - Show 3 reviews above-fold (đủ social proof mà không overwhelm)
  - Star distribution chart compact (inline, không full-width)
  - Helpful vote cần login (tránh spam)
  - Date display: relative ("2 tháng trước") cho < 1 năm, absolute cho > 1 năm
- Tại sao: 93% consumers nói reviews ảnh hưởng purchase decision (BrightLocal 2024). Photo reviews trusted 3x more than text-only

**F4.4 Review moderation**
- Cần có gì: (a) auto-flag profanity/spam, (b) admin review queue, (c) reject with reason, (d) edit grace period (24h), (e) report button on each review
- Tối ưu gì: auto-approve for trusted users (>5 reviews), manual queue for new users
- Tại sao: spam reviews destroy trust. Nhưng over-moderation kills community. Balance = auto-flag + manual review

**F4.5 Verified visit badge**
- TripAdvisor: "Verified review" (booked through platform)
- Google: review from Google account
- Cần có gì cho vinhlong360: "Đã ghé thăm" badge khi user có `user_visits` record cho entity đó
- Tối ưu gì: badge subtle (không phải big banner), tooltip "Người dùng này đã đánh dấu đã ghé thăm"
- Tại sao: verified reviews trusted 72% more (BrightLocal). vinhlong360 đã có visit tracking → leverage!

**Yêu cầu phân tích cho Codex:**
> So sánh review form flow trên 5 platforms: bao nhiêu bước, bao nhiêu fields, completion rate ước tính. Đề xuất review flow tối ưu cho vinhlong360 (progressive 3-step). Grep codebase xem review hiện tại implement ở đâu, có photo upload chưa, có multi-criteria chưa.

---

## F5. USER PROFILES & REPUTATION

### Sub-features cần phân tích chi tiết:

**F5.1 Profile page anatomy**
- TripAdvisor: avatar, badges, contribution count, reviews tab, photos tab, forums tab
- Airbnb: bio, verifications, reviews given/received, wishlist sharing
- Cần có gì:
  - Header: avatar + cover photo + name + bio (max 200 chars)
  - Stats bar: X reviews, Y posts, Z photos, W followers, V following
  - Badges section: earned badges grid
  - Tabs: Hoạt động (feed), Đánh giá, Đã lưu (nếu public), Theo dõi
  - Edit button (self-profile only)
  - Follow/Block buttons (other profiles)
  - Join date + verified phone badge
- Tối ưu gì: profile load < 1s, tabs lazy load content, avatar fallback (initials)
- vinhlong360 có `/nguoi-dung/[id]` — đang hiển thị gì? Thiếu gì so với TripAdvisor?

**F5.2 Reputation & gamification system**
- TripAdvisor levels: Contributor → Senior → Top Contributor → Top 10%
- GYG: verification badges only
- Cần có gì:
  - Points system: review=10pts, photo=5pts, answer=8pts, best-answer=15pts, helpful-vote-received=2pts
  - Levels: Khách mới (0-50) → Thành viên (50-200) → Cộng tác viên (200-500) → Chuyên gia (500-1000) → Đại sứ (1000+)
  - Badges: "Người đầu tiên đánh giá" (first review on entity), "Nhà thám hiểm" (visited 10+ entities), "Sành ăn" (reviewed 10+ cuisine), "Hướng dẫn viên" (5+ best answers), "Nhiếp ảnh gia" (20+ photos uploaded), "Người địa phương" (reviewed in 3+ areas)
  - Level benefits: higher level = review auto-approved, profile badge, priority in leaderboard
- Tối ưu gì: KHÔNG gamification quá nặng (badges phải EARN, không phải spam). Quality > quantity
- Tại sao: TripAdvisor said badges increase review contribution by 31%. Levels create aspiration loop.
- vinhlong360 có leaderboard + basic reputation — cần thêm gì cụ thể? Badges system hiện có bao nhiêu badges?

**F5.3 Profile completion flow**
- Cần có gì: progress bar (%), prompt cards ("Thêm ảnh đại diện +20%"), reward per step
- Tối ưu gì: 5 steps: name (20%) → avatar (20%) → bio (20%) → first post (20%) → first review (20%)
- Tại sao: LinkedIn: complete profiles are 40x more likely to receive opportunities. Profile completion = commitment = retention

**Yêu cầu phân tích cho Codex:**
> Nghiên cứu badge system của TripAdvisor và Airbnb chi tiết. Đề xuất badge list đầy đủ cho vinhlong360 (15-20 badges), phân loại: contribution badges, expertise badges, milestone badges. Ghi rõ criteria earn mỗi badge, icon suggestion, thứ tự hiển thị.

---

## F6. COMMUNITY & UGC

### Sub-features cần phân tích chi tiết:

**F6.1 Post types & content diversity**
- TripAdvisor forums: questions, discussions, reviews, tips
- Google Maps: reviews, photos, Q&A, local guides
- Cần có gì (mở rộng từ 4 types hiện có):
  - Review (đã có): 1-5 star + text + photos cho entity
  - Share (đã có): trip story, free-form text + photos
  - Question (đã có): Q&A + best answer marking
  - Recommend (đã có): endorse entity + reason
  - **THÊM — Tips:** short tips (< 280 chars), quick advice, "Nên biết trước khi đi"
  - **THÊM — Photo story:** 5-10 photos + captions, visual travel diary
  - **THÊM — Checklist/Guide:** user-created "10 điều phải thử ở Vĩnh Long", structured list
- Tối ưu gì: mỗi post type có form riêng (không chung 1 form), icon phân biệt in feed, filter by type
- Tại sao đa dạng: different user mindsets → different content types. "Tip" user khác "review" user. More types = lower barrier to contribute

**F6.2 Feed algorithm**
- Cần có gì: (a) Following feed (posts từ users/entities đang follow), (b) Trending feed (hot posts), (c) Latest feed (chronological), (d) For You feed (personalized — SIMPLE, rule-based)
- Tối ưu gì:
  - "For You" KHÔNG cần ML: score = recency × (likes + comments) × same_area_as_visited × is_following_author
  - Infinite scroll with skeleton loading
  - "New posts available" toast (not auto-refresh — annoying)
  - Feed diversity: không hiển thị 5 posts liên tiếp cùng 1 author
- vinhlong360 có feed — algorithm hiện tại thế nào? Có personalization không?

**F6.3 Content quality signals**
- TripAdvisor: helpful votes, management responses, "Travelers' Choice"
- Cần có gì:
  - Helpful votes ("Hữu ích" button + count)
  - Featured posts (admin picks, auto + manual)
  - Quality score (internal): length + photos + helpful_votes → boost in feed
  - "Top post tuần này" highlight
  - Low-quality auto-flag: < 20 chars, duplicate content, spam patterns
- Tối ưu gì: quality signals VISIBLE to user (encourage better content), low-quality HIDDEN (not deleted, just deprioritized)

**F6.4 User-generated guides**
- Lonely Planet: "Things to do", structured destination guides
- TripAdvisor: "Top 10" lists by users
- Cần có gì: template cho user tạo guide (tiêu đề + 5-15 items + mô tả mỗi item + entity link)
- Tối ưu gì: guide = enhanced checklist/post type, link to entities → internal SEO
- Tại sao: user guides = UGC content gold. SEO value cao, authentic, tăng engagement

**Yêu cầu phân tích cho Codex:**
> So sánh community features: TripAdvisor forums vs Google Maps Local Guides vs Airbnb Experiences community. Feature nào tạo NHIỀU content nhất? Feature nào tạo content CHẤT LƯỢNG nhất? Đề xuất chiến lược cold-start cho vinhlong360 (< 100 active users).

---

## F7. ITINERARY & TRIP PLANNING

### Sub-features cần phân tích chi tiết:

**F7.1 Builder UX**
- Google Travel: day-by-day, drag reorder, auto-suggest, map view
- TripAdvisor: trip boards, save & organize, share
- Cần có gì:
  - Day tabs: "Ngày 1", "Ngày 2", ... + add/remove days
  - Stop cards: entity card mini + notes + duration estimate + reorder drag
  - Map view: route visualization, distance/time between stops
  - Add entity: search + browse inline, "Thêm điểm dừng" button
  - Auto-suggest: "Gần [stop cuối], có [entity type]: [suggestions]"
  - Time budget: tổng thời gian per day, warning nếu quá 10h
  - Save: to profile, public/private toggle
- Tối ưu gì:
  - Drag & drop: `SortableJS` hoặc HTML5 drag (touchscreen support!)
  - Offline draft: localStorage backup
  - One-tap add: từ entity detail page → "Thêm vào lịch trình" → chọn trip + day
  - Print-friendly: CSS print styles cho export
- Tại sao: trip planning = highest-intent user action. User lập lịch trình = CHẮC CHẮN sẽ đi. Retention goldmine.
- vinhlong360 có `/tao-lich-trinh` + `user_plans` — builder hiện tại có drag? Có map? Có auto-suggest?

**F7.2 Sharing & collaboration**
- Cần có gì: (a) public URL, (b) social share (Zalo, Facebook), (c) QR code, (d) copy link, (e) Web Share API
- Tối ưu gì: shared itinerary = SEO landing page (structured data `TravelAction` hoặc `Trip`)
- Tại sao: shared itineraries = organic marketing. "Bạn tui share lịch trình → tui cũng plan"

**F7.3 Smart suggestions**
- Cần có gì:
  - "Gần [stop X]": entities within 5km of current last stop
  - "Cùng loại với [stop X]": if user added 2 restaurants, suggest more
  - "Đừng bỏ lỡ": top-rated entities in same area not yet in trip
  - "Thời gian phù hợp": suggest morning/afternoon based on entity type
- Tối ưu gì: rule-based (KHÔNG ML), dùng relationship graph + location proximity + rating
- Tại sao: empty planner = high abandonment. Suggestions reduce friction

**Yêu cầu phân tích cho Codex:**
> Thử tạo 1 trip 3 ngày trên Google Travel, TripAdvisor Trips, và Wanderlog. So sánh UX flow. Đề xuất builder flow tối ưu cho vinhlong360 với wireframe mô tả mobile + desktop.

---

## F8. MAPS & GEOLOCATION

### Sub-features cần phân tích chi tiết:

**F8.1 Interactive map**
- Cần có gì: (a) pins colored by entity type, (b) cluster at low zoom → expand at high zoom, (c) click pin → preview card popup, (d) filter overlay (same filters as catalog), (e) "Tìm trong khu vực này" button after pan, (f) list ↔ map sync
- Tối ưu gì:
  - Max 200 visible pins (performance)
  - Pin icons: 24x24, different color per type, selected pin larger/different
  - Popup card: image + name + rating + type + distance + CTA
  - Mobile: full-screen map with floating filter chips + back-to-list FAB
  - Desktop: split view 60% list / 40% map (Airbnb pattern)
- Tại sao: map = spatial discovery, fundamentally different from list. Some users are map-first (30%+ on travel sites per Google research)
- vinhlong360 có Leaflet/OSM map — đang có pin popup? Có filter overlay? Có list-map sync?

**F8.2 Directions deep links**
- Cần có gì: (a) Google Maps direction link, (b) Apple Maps fallback (iOS), (c) Zalo Map (VN-specific), (d) grab/uber link (nếu applicable)
- Format: `https://www.google.com/maps/dir/?api=1&destination={lat},{lng}&destination_place_id={placeId}`
- Tối ưu gì: detect platform → show relevant map app option

**F8.3 Area boundaries & context**
- Cần có gì: (a) huyện/xã boundary polygon overlay, (b) area label on map, (c) entity count per area
- Tại sao: user cần context "Tôi đang xem khu vực nào?" — boundary giúp orientation

**Yêu cầu phân tích cho Codex:**
> So sánh map experience: Airbnb (split view), Google Travel (explore map), TripAdvisor (map pins). Đề xuất map UX tối ưu cho vinhlong360. Ghi cụ thể pin design, popup content, filter integration, mobile vs desktop layout.

---

## F9. NOTIFICATIONS & ENGAGEMENT

### Sub-features cần phân tích chi tiết:

**F9.1 Notification types**
- Cần có gì (phân loại):
  - **Social:** like, comment, @mention, follow, repost, best-answer
  - **Content:** new entity in followed area, new review on saved entity, new itinerary for followed interest
  - **Achievement:** "Bạn đạt level Cộng tác viên!", "Badge mới: Sành ăn"
  - **Smart (rule-based):** "Mùa tốt nhất để đi [entity you saved] bắt đầu tháng tới"
  - **System:** maintenance, feature update, welcome after join
- Tối ưu gì:
  - Group notifications: "A, B và 3 người khác thích bài viết" (đã có — verify)
  - Priority ordering: social > achievement > content > system
  - Smart timing: không gửi notification lúc 2h sáng (timezone VN)
  - Unsubscribe per type: settings page cho mỗi loại
- Tại sao: notifications = retention tool #1. Nhưng spam notifications = uninstall trigger #1. Quality > quantity

**F9.2 Smart re-engagement notifications**
- Cần có gì:
  - "Đã lâu bạn chưa ghé thăm" (inactive 30+ days)
  - "Mùa [entity type] bắt đầu" (seasonal trigger)
  - "5 địa điểm mới ở khu vực bạn quan tâm" (content digest)
  - "Bạn đã ghé [entity A], thử [entity B] gần đó?" (journey continuation)
- Tối ưu gì: max 2 smart notifications/tuần, opt-out easy, KHÔNG fake urgency
- Tại sao: re-engagement notifications tăng D30 retention 15-25% (mobile app industry benchmark, áp dụng cho web in-app notifications)
- vinhlong360 có SSE real-time notifications — có smart notifications không? Có re-engagement logic không?

**Yêu cầu phân tích cho Codex:**
> Liệt kê TẤT CẢ notification types trên TripAdvisor (social + content + marketing). So sánh với vinhlong360 hiện tại. Đề xuất notification strategy đầy đủ với priority, frequency cap, smart triggers.

---

## F10. SAVE & ORGANIZE

### Sub-features cần phân tích chi tiết:

**F10.1 Collections/Wishlists**
- Airbnb: named lists ("Europe 2025"), share, collaborate
- Google Maps: saved lists ("Want to go", "Favorites", custom)
- TripAdvisor: "Save" to trip, organize by destination
- Cần có gì:
  - Default collections: "Muốn đi", "Đã đi", "Yêu thích"
  - Custom collections: user tạo tên + mô tả + cover image
  - Add to collection: entity detail page → "Lưu" → chọn collection
  - Collection page: grid of saved entities, sort, filter
  - Share collection: public URL, social share
  - Collection stats: X entities, Y areas, Z types
- Tối ưu gì:
  - Quick save: 1-tap heart → add to "Yêu thích" (default)
  - Long-press hoặc dropdown: choose specific collection
  - Offline access: save snapshot for offline viewing (localStorage)
  - Sync: cloud-backed, cross-device
- Tại sao: collections = commitment signal. Users who save 3+ entities are 4x more likely to return (travel app industry data). Shared collections = organic growth
- vinhlong360 có `saved_entities` + `user_visits` — có collections feature chưa? User chỉ save flat list hay có organize?

**F10.2 Recently viewed**
- Cần có gì: (a) browsing history, (b) "Xem gần đây" section on homepage/profile, (c) clear history, (d) max 50 items
- Tối ưu gì: localStorage (không cần auth), dedup, remove deleted entities
- vinhlong360 có `useRecentlyViewed` composable — hiển thị ở đâu? Trên homepage?

**Yêu cầu phân tích cho Codex:**
> So sánh save & organize flow: Airbnb wishlists vs Google Maps saved lists vs TripAdvisor trips. Đề xuất collections system cho vinhlong360 (DB schema, API endpoints, FE components). Ghi rõ effort estimate.

---

## F11. CONTENT STRATEGY

### Sub-features cần phân tích chi tiết:

**F11.1 Editorial content types**
- Lonely Planet: destination guides, "best of" lists, practical info
- Culture Trip: storytelling, cultural explainers, local perspectives
- Cần có gì:
  - Destination guide: "Du lịch [huyện] — Hướng dẫn đầy đủ" (auto-generated from entities + reviews)
  - Food guide: "Ăn gì ở [khu vực]?" (top-rated cuisine entities + tips)
  - Cultural explainer: "Lịch sử [di tích]" (knowledge base content)
  - Seasonal guide: "Vĩnh Long tháng [X]" (what's best, weather, events, festivals)
  - "X điều phải thử": curated top-N lists per category/area
  - FAQ: "Đi Vĩnh Long cần bao nhiêu ngày?" (SEO + GEO)
- Tối ưu gì: hybrid editorial+auto — admin writes skeleton, AI enriches, community adds reviews/tips
- Tại sao: editorial content = SEO backbone + topical authority. Google AI Overview cites structured guides

**F11.2 Content freshness & lifecycle**
- Cần có gì:
  - Freshness indicator: "Cập nhật tháng 6/2026"
  - Staleness detection: entity không có review mới > 6 tháng → flag
  - Seasonal auto-update: banner "Đang vào mùa" / "Hết mùa" based on month
  - Community-contributed updates: "Thông tin này còn đúng không?" prompt
- Tối ưu gì: last_updated timestamp visible, auto-archive outdated events
- Tại sao: stale content = trust killer. "Giờ mở cửa: 8-17h" nhưng thực tế đã đổi → negative experience

**F11.3 AI-assisted content**
- Cần có gì:
  - Auto-summary: generate 2-3 câu summary từ description dài (cho meta + cards)
  - Auto-FAQ: generate Q&A từ entity attributes + reviews
  - Auto-guide: generate seasonal guide từ entity data + season attributes
  - Translation summary: English summary cho international tourists (FUTURE, not now)
- Tối ưu gì: AI-generated marked as "[AI tổng hợp]", editable by admin, opt-in per entity
- vinhlong360 có AI chat — đang dùng AI cho content generation không? Cần thêm gì?

**Yêu cầu phân tích cho Codex:**
> Nghiên cứu content strategy của Lonely Planet và Culture Trip. Loại content nào tạo nhiều organic traffic nhất? Đề xuất content calendar cho vinhlong360 (monthly, 5-10 pieces). Ghi rõ loại content, SEO target keyword, effort.

---

## F12. CONTACT & CONVERSION (CHỈ GIỚI THIỆU)

### Sub-features cần phân tích chi tiết:

**F12.1 CTA optimization**
- Cần có gì: Zalo chat, Phone call, Chỉ đường, Lưu, Chia sẻ
- Tối ưu gì:
  - **CTA copy A/B testing:** "Gọi ngay" vs "Liên hệ" vs "Hỏi giá" — cái nào fit "chỉ giới thiệu"?
  - **CTA placement heat analysis:** Where do users look? (F-pattern: CTA at end of F)
  - **Mobile sticky bar:** 2-3 buttons, always visible, safe-area padding
  - **Desktop sidebar:** sticky card, scrolls with content
  - **Color hierarchy:** primary CTA (Zalo/Phone) = accent color, secondary (Save/Share) = outlined
  - **Time-aware:** "Đang mở cửa — Gọi ngay" vs "Đã đóng cửa — Lưu để gọi sau"
- Tại sao: CTA = ONLY conversion point. Friction ở CTA = mất user. vinhlong360 KHÔNG có booking → CTA phải rõ ràng "liên hệ trực tiếp"

**F12.2 Contact tracking analytics**
- Cần có gì:
  - Event tracking: mỗi CTA click → log (entity_id, cta_type, user_id, timestamp)
  - Dashboard: top entities by contact clicks, CTA type distribution, trend
  - Conversion funnel: page view → CTA visible → CTA click → (external: Zalo/Phone)
  - Heatmap: which CTA clicked most per entity type
- Tối ưu gì: privacy-compliant (không track phone content, chỉ click event)
- Tại sao: data cho business model (premium listing → "entity X nhận 50 clicks/tháng")

**F12.3 Operating hours intelligence**
- Cần có gì:
  - "Đang mở cửa" / "Đã đóng cửa" / "Sắp đóng (còn 30 phút)" badge
  - Opening hours structured display (daily schedule)
  - Holiday hours override
  - "Giờ đông khách" / "Giờ vắng" (nếu có data — Google Popular Times equivalent)
- Tối ưu gì: timezone-aware (UTC+7), auto-compute from structured hours data
- Tại sao: users muốn biết "đi giờ này có mở không?" — giảm wasted trip

**Yêu cầu phân tích cho Codex:**
> Nghiên cứu CTA patterns trên Google Maps (khi không có booking — business listings) và Yelp. Copy, placement, color, size, behavior. Đề xuất CTA system đầy đủ cho vinhlong360 (mobile + desktop) với wireframe.

---

## F13. ADMIN & CONTENT MANAGEMENT

### Sub-features cần phân tích chi tiết:

**F13.1 Entity management workflow**
- Cần có gì:
  - Create wizard: step-by-step (name → type → area → description → images → attributes → relationships)
  - Bulk import: CSV/JSON upload cho nhiều entities cùng lúc
  - Bulk edit: select multiple → batch update type/area/status
  - Export: CSV/JSON download (filtered)
  - Version history: track changes per entity, rollback
  - Completeness score: % fields filled, visual indicator on list
  - Duplicate detection: warn before create if similar name exists (đã có)
- Tối ưu gì: keyboard shortcuts (Ctrl+N new, Ctrl+S save), inline edit on table (đã có partially)
- vinhlong360 có 68 admin endpoints — admin UX đã tốt chưa? Workflow mượt chưa? Bottleneck ở đâu?

**F13.2 Content moderation workflow**
- Cần có gì:
  - Queue sorted by: newest, reported, auto-flagged
  - Preview: full content without leaving queue page
  - Actions: approve, reject (with reason), edit, escalate, ban user
  - Batch moderation: select multiple → bulk action (đã có)
  - Auto-flag rules: profanity, links, duplicate text, new user first post
  - Stats: pending count, avg review time, rejection rate, top reporters
- Tối ưu gì: keyboard shortcuts (đã có j/k/a/r), preview modal (đã có)
- Tại sao: moderation speed = community health. Queue > 50 unreviewed → trust erosion

**F13.3 Analytics dashboard**
- Cần có gì:
  - Overview: users, posts, entities, pageviews (delta vs last period)
  - Trending: most viewed entities, most saved, most reviewed this week
  - Community health: new users/day, active users/day, post frequency, review frequency
  - Search analytics: top queries, zero-result queries, conversion rate
  - CTA analytics: clicks per entity, per CTA type, trend
  - Content gaps: areas with few entities, entity types with few items
  - Export: CSV for all data sets
- Tối ưu gì: date range filter (đã có), sparkline trends (đã có), alert khi metric unusual
- vinhlong360 có analytics dashboard — đang cover bao nhiêu % so với ideal?

**Yêu cầu phân tích cho Codex:**
> Nghiên cứu admin panels: WordPress admin, Strapi CMS, Sanity Studio. Best practices cho admin UX. Đề xuất admin workflow improvements top 5 cho vinhlong360.

---

## F14. ONBOARDING & FIRST-TIME UX

### Sub-features cần phân tích chi tiết:

**F14.1 Guest experience (chưa đăng ký)**
- Cần có gì: (a) full browsing without login, (b) gentle nudges to register (not blocking), (c) save → prompt login, (d) review → prompt login, (e) chat → allow without login (limited)
- Tối ưu gì: KHÔNG gate content behind login wall. Chỉ gate actions (save, review, follow)
- Tại sao: gate content = bounce. 70% users leave if asked to register before seeing value (UX research)

**F14.2 Registration optimization**
- Cần có gì: (a) phone OTP (fast, VN-standard), (b) 2-step: phone → name (minimal friction), (c) skip avatar/bio (optional later), (d) redirect to action that prompted registration
- Tối ưu gì: form completion < 30 seconds, OTP auto-read (if mobile), remember "what user was doing" → redirect back
- Tại sao: every extra field = 10% more drop-off. Phone + name = minimum viable profile

**F14.3 First-visit homepage optimization**
- Cần có gì: (a) clear value prop (2 giây hiểu "đây là gì"), (b) trending content (social proof), (c) seasonal/relevant content, (d) search bar prominent, (e) NOT a tutorial wall
- Tối ưu gì: first-time vs returning user homepage có thể khác (first-time: more explanatory, returning: more personalized)
- vinhlong360 homepage hiện tại cho first-time visitor — truyền tải value prop trong bao nhiêu giây?

**F14.4 Cold-start strategy (< 100 active users)**
- Cần có gì:
  - Seed content: admin reviews, admin itineraries, AI-generated descriptions
  - Invite friends: share profile/collection to Zalo
  - Gamification early: "5 người đầu tiên đánh giá [entity] nhận badge"
  - Community manager presence: admin posts, replies to reviews, creates content
- Tại sao: empty platform = no one stays. Cold-start is the #1 challenge for community platforms

**Yêu cầu phân tích cho Codex:**
> Nghiên cứu onboarding flows: TripAdvisor first visit, Google Maps first review, Airbnb first save. Đề xuất onboarding flow cho vinhlong360 (first visit → first save → first review → first post). Wireframe mô tả.

---

## F15. PERSONALIZATION & RECOMMENDATIONS

### Sub-features cần phân tích chi tiết:

**F15.1 Rule-based recommendations (KHÔNG ML)**
- Cần có gì:
  - "Dựa trên lịch sử": entities cùng type/area với recently viewed
  - "Gần nơi bạn đã ghé": entities within 10km of visited entities
  - "Phổ biến khu vực bạn quan tâm": top-rated in followed areas
  - "Theo mùa": best-season entities matching current month
  - "Người dùng tương tự cũng thích": co-visitation simple (users who saved X also saved Y)
- Tối ưu gì:
  - KHÔNG dùng ML library (quá phức tạp cho solo dev)
  - SQL query đơn giản: `SELECT e.* FROM entities e JOIN user_visits uv ON e.area = (SELECT area FROM user_visits WHERE user_id = ?) WHERE e.id NOT IN (SELECT entity_id FROM user_visits WHERE user_id = ?) ORDER BY e.rating DESC LIMIT 10`
  - Cache recommendations per user (invalidate on new visit/save)
  - Fallback: if no user data → trending/popular/seasonal
- Tại sao: personalization tăng engagement 20-30% (McKinsey). Simple rules cover 80% of value, ML adds 20% but costs 10x effort
- vinhlong360 có recommender module — đang dùng logic gì? Rule-based hay ML? Output quality?

**Yêu cầu phân tích cho Codex:**
> Nghiên cứu recommendation systems: Netflix (collaborative filtering), Amazon ("customers also bought"), Spotify (Discover Weekly). Đề xuất 5 recommendation rules đơn giản cho vinhlong360, mỗi rule = 1 SQL query, giải thích logic + expected output.

---

## F16. SOCIAL PROOF & TRUST

### Sub-features cần phân tích chi tiết:

**F16.1 Trust signals on entity**
- Cần có gì:
  - ⭐ Rating + review count (prominent, above-fold)
  - 👥 "X người đã ghé thăm" (from `user_visits` — real data)
  - 📸 "Y ảnh từ cộng đồng" (photo reviews count)
  - 🏅 OCOP badge (certified products)
  - ✅ "Thông tin được cập nhật [date]" (freshness signal)
  - 🗣️ Review snippet: 1-2 sentence highlight from best review
  - 📍 "Nằm trên lộ trình [itinerary name]" (itinerary inclusion)
- Tối ưu gì: compact display, KHÔNG fake numbers, only show metrics with real data (0 reviews → don't show "0 đánh giá", show "Chưa có đánh giá — Hãy là người đầu tiên!")
- Tại sao: trust = #1 barrier for travel decisions. BrightLocal: 98% consumers read reviews, 73% only use businesses with 4+ stars. Social proof > marketing copy

**F16.2 Community trust signals**
- Cần có gì: (a) contributor level badges on reviews, (b) "Đã xác minh SĐT" badge, (c) "Thành viên từ [date]" on profile, (d) contribution count visible
- Tại sao: anonymous reviews trusted less. Showing contributor history → trust reviewer → trust content

**Yêu cầu phân tích cho Codex:**
> Nghiên cứu social proof patterns: TripAdvisor ("Travelers' Choice"), Google Maps (contribution badges), Airbnb (Superhost). Đề xuất social proof system cho vinhlong360 — display rules, placement, data sources.

---

## F17. ACCESSIBILITY & INCLUSIVITY

(Đã cover chi tiết trong `codex-design-research-prompt.md` R10 — ở đây focus vào FEATURE-level a11y)

**F17.1 Functional accessibility features**
- Cần có gì:
  - Skip navigation link
  - High contrast mode toggle
  - Text size adjustment (A / A+ / A++)
  - Reduced motion toggle
  - Keyboard-only navigation (full site usable without mouse)
  - Screen reader landmarks & announcements
  - Focus management in modals/dialogs
- vinhlong360 implement bao nhiêu % accessibility features? Grep `aria-` usage, `role=` usage, skip-link, focus trap

**Yêu cầu phân tích cho Codex:**
> Chạy Lighthouse Accessibility audit (mental simulation) trên vinhlong360 entity detail page. Liệt kê potential failures. Đề xuất fix priority.

---

## F18. PERFORMANCE & OFFLINE

(Đã cover chi tiết trong `codex-design-research-prompt.md` R12 — ở đây focus vào FEATURE-level performance)

**F18.1 Perceived performance features**
- Cần có gì:
  - Skeleton loading cho mọi content page
  - Optimistic UI: like/save instant, sync background
  - Prefetch: hover link → prefetch page data
  - Image progressive loading: blur-up → full resolution
  - Infinite scroll with scroll position preservation
- vinhlong360 có skeleton loading? Có optimistic UI cho like/save? Có prefetch?

**F18.2 Offline & low-bandwidth**
- Cần có gì:
  - Service Worker: cache homepage, recently viewed entities
  - Save-Data mode: smaller images, no animations
  - Offline indicator: "Bạn đang offline — hiển thị dữ liệu đã lưu"
  - Retry logic: auto-retry failed requests when back online
- Tại sao: du lịch = outdoor = network issues. User xem entity detail trước → offline khi tại điểm đến → cần access saved info

**Yêu cầu phân tích cho Codex:**
> Nghiên cứu offline strategy: Google Maps offline areas, TripAdvisor offline guides. Đề xuất offline strategy phù hợp cho vinhlong360 (light — Service Worker cache, KHÔNG full offline app).

---

## F19. ANALYTICS & INSIGHTS (admin)

### Sub-features cần phân tích chi tiết:

**F19.1 Dashboard KPIs**
- Cần có gì:
  - **Growth:** new users/week, total users, growth rate
  - **Engagement:** DAU/MAU ratio, avg session duration, pages/session
  - **Content:** new reviews/week, new posts/week, photo uploads
  - **Discovery:** top search queries, zero-result queries, search → click rate
  - **Conversion:** CTA clicks, CTA → external (Zalo open, phone dial)
  - **SEO:** top landing pages, organic traffic %, bounce rate
  - **Health:** entities with 0 reviews, entities not updated > 6 months
- Tối ưu gì: self-hosted analytics (privacy, cost), NOT Google Analytics if possible
- vinhlong360 có analytics — bao nhiêu KPIs hiện track được? Gaps?

**Yêu cầu phân tích cho Codex:**
> Nghiên cứu analytics dashboards: Plausible Analytics (self-hosted), Umami (open source), PostHog (product analytics). Đề xuất analytics strategy cho vinhlong360 — self-hosted, privacy-first, free-tier.

---

## F20. MONETIZATION & SUSTAINABILITY

### Sub-features cần phân tích chi tiết:

**F20.1 Revenue streams (legal cho "chỉ giới thiệu")**
- Cần có gì:
  - **Premium listing:** entity owners pay to highlight (badge, boost in search, featured section)
  - **Featured content:** sponsored guides/collections (labeled "Tài trợ")
  - **B2G contracts:** tourism board pays for platform operation + data insights
  - **Data insights:** anonymized reports (popular areas, trending queries, visitor demographics) cho Sở Du lịch
  - **Display ads:** tasteful, limited (max 1 per page, clearly labeled)
- KHÔNG làm: booking commission, subscription paywall, affiliate links
- Tối ưu gì: premium listing = admin toggle per entity, no payment integration on site (invoice offline)
- Tại sao: sustainability = survival. Free platform without revenue = dead platform after 1 year

**Yêu cầu phân tích cho Codex:**
> Nghiên cứu monetization models: Yelp (premium listings), TripAdvisor (sponsored placements), Lonely Planet (advertising). Đề xuất revenue strategy cho vinhlong360 phù hợp constraint "chỉ giới thiệu". Ghi expected revenue range.

---

# RÀng BUỘC DỰ ÁN — BẮT BUỘC TUÂN THỦ

Mọi đề xuất PHẢI tuân theo ràng buộc sau (vi phạm = đề xuất KHÔNG HỢP LỆ):

| # | Ràng buộc | Chi tiết |
|---|-----------|----------|
| C1 | **Solo developer** | 1 người duy nhất code + maintain + deploy + support |
| C2 | **Budget < 1 triệu VNĐ/tháng** | ~$40 USD. Hosting + domain + API calls. KHÔNG dịch vụ trả phí thêm |
| C3 | **CHỈ giới thiệu** | KHÔNG booking, KHÔNG thanh toán, KHÔNG sàn TMĐT. CTA chỉ Zalo/Phone/Chỉ đường |
| C4 | **Web-only** | KHÔNG native app (iOS/Android). PWA OK nếu nhẹ |
| C5 | **Ảnh CHỈ AI-generated** | KHÔNG stock (Pexels/Unsplash), KHÔNG UGC photos (trừ review photos từ users), KHÔNG Wikimedia |
| C6 | **CSS thuần** | KHÔNG Tailwind, KHÔNG UI library. Design tokens + custom properties |
| C7 | **Pháp lý Việt Nam** | NĐ147 (MXH < 10K user chưa cần đăng ký trang TTĐT tổng hợp nhưng cần chuẩn bị). KHÔNG crawler nguyên văn báo |
| C8 | **Stack cố định** | Nuxt 4 SSR + FastAPI + PostgreSQL + SQLite. KHÔNG thêm framework |
| C9 | **No heavy features** | KHÔNG AR, audio guide, 3D, video streaming, native push, real-time messaging |
| C10 | **Database-as-SoT** | Entity/relationship = SQLite. UGC/auth = PostgreSQL. KHÔNG port UGC sang SQLite |

---

# OUTPUT: `docs/feature-audit-report.md`

## CẤU TRÚC FILE BẮT BUỘC

```markdown
# Feature Audit Report — vinhlong360

> Nghiên cứu so sánh chức năng với 9+ travel platforms hàng đầu thế giới.
> Mục đích: xác định GAP, ưu tiên UPGRADE, và giải thích SKIP.
> Cập nhật: [ngày]

---

## MỤC LỤC
1. Executive Summary
2. Platform Research (9+ platforms)
3. Feature Comparison Matrix (20 nhóm × 9+ platforms × vinhlong360)
4. Gap Analysis & Prioritization
5. Upgrade Roadmap (Priority → Consider → Innovation)
6. Skip Justification
7. Innovation Features
8. Implementation Estimates
9. Risk Assessment
10. Appendixes

---

## 1. EXECUTIVE SUMMARY (1-2 trang)
- Tổng features khảo sát: [số] across [số] platforms
- vinhlong360 coverage: [X/Y features = Z%]
- Maturity score per functional group: F1=X/10, F2=Y/10, ... F20=Z/10
- Top 5 gaps theo impact
- Priority upgrades: [số] items (estimated [X] person-days)
- Consider upgrades: [số] items
- Skip: [số] items
- Innovation features: [số] ideas
- Estimated total effort: [tổng person-days]
- Risk summary: [top 3 risks]

## 2. PLATFORM RESEARCH (chi tiết mỗi platform)

Cho MỖI platform (9+), viết:
### Platform [N]: [Name]
**URL:** [url]
**Category:** [OTA / Meta-search / Map / Community / Government]
**Scale:** [MAU nếu biết]
**Target audience:** [tourist type]

**Key features (top 10):**
1. [Feature] — [1-line description] — [unique twist]
...

**UX patterns đáng học:**
- [Pattern 1]: mô tả cụ thể (vd: "horizontal filter chips with count badge, sticky on scroll, chip style border-radius 18px")
- [Pattern 2]: ...

**Lessons for vinhlong360:**
- ADOPT: [gì nên copy nguyên]
- ADAPT: [gì nên chỉnh cho phù hợp]
- SKIP: [gì KHÔNG nên copy, vì sao]

**Screenshots/wireframe mô tả:**
- Homepage layout: [mô tả chi tiết bố cục]
- Detail page sections (top→bottom): [liệt kê từng section]
- Mobile vs Desktop differences: [gì thay đổi]

## 3. FEATURE COMPARISON MATRIX

**Format:** Bảng khổng lồ, mỗi ô = status + quality note

| Functional Group | Sub-feature | GYG | Klook | TripAdvisor | Google | Airbnb | [+3] | vinhlong360 | Gap? |
|---|---|---|---|---|---|---|---|---|---|
| F1 Discovery | F1.1 Homepage hero | ✅ Search | ✅ Deals | ✅ Destination | ✅ Search+Map | ✅ Categories | ... | ⚠️ Bento | Y |
| F1 Discovery | F1.2 Category nav | ✅ Pills | ✅ Tabs+Pills | ✅ Tabs | ✅ Chips | ✅ Icon pills | ... | ✅ Chips | N |
| ... | ... | ... | ... | ... | ... | ... | ... | ... | ... |

**Yêu cầu:** ≥ 200 rows (mỗi F-group ≥ 10 sub-features)

Ô notation:
- ✅ = Fully implemented, good quality
- ⚠️ = Partially implemented, needs improvement (ghi note)
- ❌ = Not implemented
- N/A = Not applicable for platform type
- 🔒 = Behind paywall / premium

## 4. GAP ANALYSIS (phân tích sâu)

Cho MỖI feature gap (≥ 50 gaps), phân tích 7 tầng:

### Gap G-[XX]: [Feature name]
**Functional group:** F[X]
**Severity:** 🔴 Critical / 🟡 Important / 🟢 Nice-to-have

**Tầng 1 — MAP:** Platforms nào có feature này?
| Platform | Implementation | Quality (1-10) | Unique twist |
|---|---|---|---|
| GYG | [mô tả] | [X] | [gì đặc biệt] |
| Klook | ... | ... | ... |
| ... | ... | ... | ... |

**Tầng 2 — WHY:** Tại sao platforms này cần feature đó?
- User problem solved: [vấn đề gì]
- Business value: [giá trị gì]
- Research backing: [study/metric nào]

**Tầng 3 — FIT:** vinhlong360 có cần feature này không?
| Criteria | Score (1-5) | Reasoning |
|---|---|---|
| User demand | [X] | [giải thích] |
| Solo dev feasibility | [X] | [giải thích] |
| Budget fit (< 1M VND/mo) | [X] | [giải thích] |
| Competitive advantage | [X] | [giải thích] |
| Maintenance burden | [X] | [giải thích: 5=low burden] |
| **Total** | **[sum/25]** | |

**Tầng 4 — CURRENT STATE:** vinhlong360 hiện có gì?
```
grep/find results:
- [file:line] — [gì implement]
- [file:line] — [gì implement]
Conclusion: [X% implemented / not implemented / partially]
```

**Tầng 5 — UPGRADE CARD (nếu FIT score ≥ 15):**
```
U-[XX]: [Feature name]
───────────────────────────
Sub-features cần build:
  1. [sub-feature 1] — [mô tả] — effort: [S/M/L]
  2. [sub-feature 2] — [mô tả] — effort: [S/M/L]
  3. ...

Tối ưu cần làm:
  1. [optimization 1] — tại sao: [reason] — cách: [how]
  2. [optimization 2] — tại sao: [reason] — cách: [how]
  3. ...

Files to modify:
  Backend: [list files + what changes]
  Frontend: [list files + what changes]
  Database: [migration nếu cần]

Dependencies: [list]
Risk: LOW/MEDIUM/HIGH — [explanation]
Effort: [X person-days total]
Impact: [mô tả user benefit, metric kỳ vọng]
Vietnamese market note: [VN-specific consideration]

Priority: P0 (ngay) / P1 (tuần sau) / P2 (tháng sau) / P3 (backlog)
```

**Tầng 6 — SKIP JUSTIFICATION (nếu FIT score < 15):**
- Skip vì: [lý do cụ thể]
- Anti-pattern nếu copy: [hậu quả]
- Revisit khi: [điều kiện thay đổi — vd "khi MAU > 50K"]

**Tầng 7 — INNOVATION:** Có cách tiếp cận sáng tạo hơn platforms lớn không?
- Idea: [mô tả]
- User story: "Là [persona], tôi muốn [action] để [benefit]"
- Why better for vinhlong360: [giải thích]

## 5. UPGRADE ROADMAP

### 5.1 IMMEDIATE (P0 — tuần này, effort < 3 days each)
[Cards U-XX]

### 5.2 SHORT-TERM (P1 — tháng này, effort 3-7 days each)
[Cards U-XX]

### 5.3 MEDIUM-TERM (P2 — quý này, effort 1-2 weeks each)
[Cards U-XX]

### 5.4 BACKLOG (P3 — khi có thêm resources)
[Cards U-XX]

### 5.5 INNOVATION (P-I — unique opportunities)
[Innovation cards I-XX]

**Dependency graph:**
```
U-01 ──→ U-05 ──→ U-12
U-02 ──→ U-06
U-03 (independent)
...
```

## 6. SKIP JUSTIFICATION TABLE

| # | Feature | Platform(s) | FIT score | Skip reason | Anti-pattern | Revisit when |
|---|---------|-------------|-----------|-------------|--------------|--------------|
| S-01 | [feature] | GYG, Klook | [X/25] | [reason] | [anti-pattern] | [condition] |
| S-02 | ... | ... | ... | ... | ... | ... |
| ... ≥ 20 rows

## 7. INNOVATION FEATURES

Cho MỖI innovation idea (≥ 8):

### I-[XX]: [Feature name]
**Category:** [Discovery / Community / Content / Local-advantage / UX]
**Inspiration:** [nguồn cảm hứng — KHÔNG copy, SÁNG TẠO]

**User story:**
> Là [persona cụ thể: du khách Sài Gòn, người bản địa Vĩnh Long, admin Sở Du lịch], tôi muốn [action] để [benefit].

**Feature description (chi tiết):**
[3-5 câu mô tả chức năng]

**Sub-features:**
1. [sub-feature] — [mô tả]
2. [sub-feature] — [mô tả]

**Why this is unique for vinhlong360:**
[Tại sao platform lớn KHÔNG có feature này — vì quy mô lớn quá, vì context khác, vì data khác]

**Implementation sketch:**
- Backend: [endpoint(s), data model]
- Frontend: [component(s), page(s)]
- Data source: [where the data comes from]
- Effort: [X person-days]
- Risk: LOW/MEDIUM/HIGH

**Success metric:** [cách đo hiệu quả]

## 8. IMPLEMENTATION ESTIMATES

| Upgrade | Type | Backend effort | Frontend effort | DB migration | Total person-days | Dependencies | Risk |
|---------|------|----------------|-----------------|--------------|-------------------|--------------|------|
| U-01 | FE-only | 0 | 2d | No | 2 | None | LOW |
| U-02 | Full-stack | 3d | 2d | Yes | 5 | U-01 | MED |
| ... | ... | ... | ... | ... | ... | ... | ... |

**Summary:** P0=[X]d, P1=[X]d, P2=[X]d, P3=[X]d, Innovation=[X]d, **Total=[X] person-days**

## 9. RISK ASSESSMENT

| Risk | Probability | Impact | Mitigation | Related upgrades |
|------|-------------|--------|------------|-----------------|
| [risk 1] | HIGH/MED/LOW | HIGH/MED/LOW | [mitigation strategy] | U-XX, U-YY |
| [risk 2] | ... | ... | ... | ... |

**Top 3 risks cho solo dev:**
1. [risk + mitigation]
2. [risk + mitigation]
3. [risk + mitigation]

## 10. FUNCTIONAL GROUP MATURITY SCORECARD

| Group | Current score (1-10) | Industry benchmark | Gap | Top 3 improvements |
|-------|---------------------|-------------------|-----|---------------------|
| F1 Discovery | [X] | 8 | [Y] | [list] |
| F2 Search | [X] | 9 | [Y] | [list] |
| ... | ... | ... | ... | ... |
| F20 Monetization | [X] | 7 | [Y] | [list] |
| **Average** | **[X]** | **[Y]** | **[Z]** | |

## 11. APPENDIXES

### A. Platform Feature Inventory (raw data)
[Bảng đầy đủ TỪNG feature phát hiện trên MỖI platform, không tóm tắt]

### B. vinhlong360 Current Feature Map (from codebase analysis)
[Bảng: feature → file(s) → status → quality note]
[Grep/find evidence cho TỪNG feature claim]

### C. User Stories for ALL Priority Upgrades
[User story format cho MỖI upgrade card P0-P2]

### D. Sub-feature Breakdown per Functional Group
[Chi tiết MỌI sub-feature cần có cho mỗi F-group, với:]
- What exactly it needs (components, endpoints, data)
- What to optimize (performance, UX, a11y)
- Why it matters (research, metric, user benefit)
- Current state in vinhlong360 (grep evidence)
- Gap and recommendation

### E. Optimization Requirements Catalog
[Bảng: area → optimization → why → how → effort → priority]
[Bao gồm: performance, SEO, a11y, mobile UX, offline, security]

### F. Cross-platform UX Pattern Library
[Pattern → platforms using it → description → wireframe description → adoption recommendation]
[Ít nhất 30 patterns across F1-F20]

### G. Sources & References
[Tất cả sources: research papers, industry reports, platform documentation, UX studies]
```

---

# YÊU CẦU CHẤT LƯỢNG

## Depth requirements

1. **Không liệt kê suông** — mỗi feature phải có WHY (tại sao platform X làm feature này) + FIT (vinhlong360 có cần không) + EVIDENCE (metric/research/data backing)
2. **Grep trước khi đánh giá** — verify codebase thật sự có/không có feature đó. KHÔNG đoán. Ghi rõ file:line
3. **Effort estimates thực tế** — dựa trên codebase hiện có (175+ endpoints, 70 pages, 38 composables, 25 DB tables). Nếu endpoint đã có → FE-only upgrade = S (1-2 days). Nếu cần new table + API + FE = L (5-10 days). Phân rõ: backend effort, frontend effort, migration effort
4. **Solo dev perspective** — feature nào build 1 tuần nhưng maintain 1 năm = RED FLAG. Ghi "maintenance tax" estimate
5. **Vietnamese market context** — user behavior VN (85% mobile, Zalo-first, data-conscious, low bandwidth rural areas, dùng Facebook/Zalo nhiều hơn web). Ghi cụ thể: "user VN sẽ [action] vì [reason]"
6. **Competitive advantage** — feature nào giúp vinhlong360 khác biệt vs vinhlongtourist.vn / Google Maps? Ghi "competitive moat" score: 1=easy to copy, 5=hard to replicate
7. **Sub-feature completeness** — mỗi feature gap phải liệt kê TẤT CẢ sub-features cần có (không chỉ high-level). Ví dụ: "Review system" phải breakdown thành: form UX, star selector, photo upload, moderation, display, sorting, filtering, helpful votes, response from owner, summary, verified badge — mỗi sub-feature có WHY + effort riêng
8. **Optimization requirements** — mỗi feature phải ghi TỐI ƯU CẦN LÀM gì (performance, UX, a11y, SEO, mobile). Ví dụ: "Review display cần optimize: lazy load reviews (performance), aria-labels (a11y), structured data Review schema (SEO), responsive layout (mobile)"
9. **Reasoning chain** — mỗi đề xuất phải có chuỗi lý luận: [User need] → [Feature solves it because] → [Evidence/metric] → [vinhlong360 context] → [Implementation approach] → [Expected outcome]
10. **Cross-reference** — link related features across groups. Ví dụ: F4 Reviews ↔ F16 Social Proof ↔ F5 Reputation. Ghi rõ dependencies

## Anti-patterns to flag

Ghi vào mục riêng "ANTI-PATTERN CATALOG" nếu phát hiện:
1. **Feature bloat:** Feature có ở platform 100M users mà áp cho 10K users = waste. [Ghi: feature gì, platform nào, tại sao waste cho vinhlong360]
2. **Booking envy:** Cố gắng thêm booking/payment khi constraint nói KHÔNG. [Ghi: feature gì ngụy trang booking]
3. **Complexity trap:** Feature đơn giản ở frontend nhưng nightmare ở backend (real-time sync, recommendation ML, search ranking). [Ghi: frontend effort vs backend effort vs maintenance]
4. **Maintenance debt:** Feature build 3 ngày nhưng cần babysitting hàng tuần (content moderation, data freshness, external API dependency). [Ghi: build effort vs monthly maintenance hours]
5. **Legal minefield:** Feature cần đăng ký TMĐT, giấy phép, GDPR-equivalent. [Ghi: luật nào, NĐ nào, rủi ro gì]
6. **Dark patterns:** Feature tạo fake urgency/scarcity/social proof ("Chỉ còn 2 chỗ!", "X người đang xem", fake countdown). [Ghi: pattern gì, platform nào dùng, tại sao vinhlong360 KHÔNG nên]
7. **Over-engineering:** Feature dùng tech stack quá phức tạp cho vấn đề đơn giản (WebSocket khi polling đủ, Redis khi in-memory đủ, Elasticsearch khi SQLite FTS đủ). [Ghi: simple alternative]
8. **Copy-paste gap:** Copy feature từ marketplace (GYG/Klook) sang content platform (vinhlong360) — logic khác hoàn toàn. [Ghi: tại sao context khác]
9. **Premature optimization:** Build feature cho 100K users khi mới có 100 users (sharding, CDN multi-region, microservices). [Ghi: threshold khi nào cần]
10. **Vanity feature:** Feature tạo số metric đẹp nhưng không giúp user (badge system phức tạp, leaderboard meaningless). [Ghi: feature gì, metric nào vanity, metric nào thật]

## Minimum deliverables (TĂNG so với v1)

- **Feature comparison matrix:** ≥ 250 rows (20 nhóm × ≥ 12 sub-features mỗi nhóm)
- **Gap analysis:** ≥ 60 feature gaps analyzed (7 tầng mỗi gap, đầy đủ sub-features + optimizations + reasoning)
- **Priority upgrades (P0+P1):** ≥ 20 upgrade cards (full format U-XX, mỗi card ≥ 3 sub-features + ≥ 2 optimizations)
- **Consider upgrades (P2+P3):** ≥ 15 upgrade cards
- **Skip justifications:** ≥ 25 features explained (với anti-pattern + revisit condition)
- **Innovation ideas:** ≥ 10 unique features (mỗi idea ≥ 3 sub-features + user story + implementation sketch)
- **Total platforms researched:** ≥ 9 (6 chính + 3 tự tìm)
- **Maturity scorecard:** 20 F-groups scored 1-10 with benchmark comparison
- **Anti-pattern catalog:** ≥ 15 anti-patterns identified across platforms
- **Cross-platform UX pattern library:** ≥ 30 patterns documented
- **Sub-feature breakdown:** MỖI F-group phải có ≥ 8 sub-features chi tiết (what/optimize/why/current/gap)
- **Optimization requirements:** ≥ 40 optimization items across all features (performance/UX/a11y/SEO/mobile)
- **User stories:** ≥ 30 user stories cho priority upgrades

---

# ANALYSIS METHODOLOGY

## Nghiên cứu mỗi platform (bắt buộc)

1. **Mở trang chủ** — mô tả layout, section order, above-fold content, CTA placement
2. **Tìm kiếm** — thử search "food tour", "temple", "local guide". Ghi: UX flow, suggestions, filter options
3. **Xem detail page** — mô tả TỪNG section từ trên xuống dưới, ghi thứ tự, kích thước, behavior
4. **Thử review flow** — nếu có account: bao nhiêu bước, bao nhiêu fields, UX quality
5. **Xem profile** — cấu trúc profile, reputation system, contribution display
6. **Xem community** — forums, Q&A, tips, user guides
7. **Xem mobile** — responsive hay native? Sự khác biệt vs desktop?
8. **Check performance** — page load, image optimization, skeleton loading
9. **Check a11y** — keyboard nav, screen reader, contrast
10. **Check SEO** — structured data, meta tags, URL structure, sitemap

## So sánh methodology

Cho MỖI feature:
1. Liệt kê PLATFORMS NÀO CÓ (và implementation quality 1-10)
2. Liệt kê PLATFORMS NÀO KHÔNG CÓ (và tại sao — market segment khác? Không cần?)
3. Tìm CONSENSUS PATTERN — feature implement giống nhau ở ≥ 3 platforms = industry standard
4. Tìm UNIQUE PATTERNS — feature chỉ 1 platform có = innovation hoặc niche
5. Đánh giá RELEVANCE cho vinhlong360 (5 criteria scoring)

## Codebase verification methodology

1. **Grep feature keywords:** `grep -r "review" --include="*.py" --include="*.vue" --include="*.ts"`
2. **Check API endpoints:** `grep -r "@app\.\(get\|post\|put\|delete\)" agent/*.py`
3. **Check DB tables:** `grep -r "CREATE TABLE" agent/*.py`
4. **Check Vue components:** `ls web-nuxt/components/` + `ls web-nuxt/pages/`
5. **Check composables:** `ls web-nuxt/composables/`
6. **Cross-reference:** endpoint exists? → composable calls it? → component renders it? → page shows it?
7. **Quality check:** feature exists but is it GOOD? Check: error handling, loading states, empty states, mobile responsive, a11y

---

# QUALITY GATE — TỰ KIỂM TRA (NÂNG CẤP)

Trước khi nộp, check TẤT CẢ 20 items:

## Gate A: Completeness
| # | Check | Pass? |
|---|-------|-------|
| QG1 | Feature matrix có ≥ 250 rows (20 groups × ≥ 12 sub-features)? | |
| QG2 | Gap analysis có ≥ 60 feature gaps, MỖI gap đủ 7 tầng? | |
| QG3 | Mỗi gap có đầy đủ: sub-features list + optimizations + reasoning chain? | |
| QG4 | Tổng platforms ≥ 9 với research chi tiết mỗi platform? | |
| QG5 | Upgrade cards P0+P1 ≥ 20, P2+P3 ≥ 15, Innovation ≥ 10? | |

## Gate B: Depth
| # | Check | Pass? |
|---|-------|-------|
| QG6 | Mỗi upgrade card có: ≥ 3 sub-features + ≥ 2 optimizations + effort split (BE/FE/DB) + risk + files? | |
| QG7 | Mỗi SKIP có: FIT score + anti-pattern + revisit condition? | |
| QG8 | Maturity scorecard 20 groups scored với benchmark comparison? | |
| QG9 | Anti-pattern catalog ≥ 15 items với ví dụ cụ thể? | |
| QG10 | Cross-platform UX pattern library ≥ 30 patterns? | |

## Gate C: Verification
| # | Check | Pass? |
|---|-------|-------|
| QG11 | TỪNG feature claim có grep evidence (file:line)? KHÔNG đoán? | |
| QG12 | Effort estimates dựa trên codebase thật (endpoints/tables/components count)? | |
| QG13 | Dependencies giữa upgrades được graph hoá? | |
| QG14 | Risk assessment realistic (không tất cả "LOW")? | |

## Gate D: Context
| # | Check | Pass? |
|---|-------|-------|
| QG15 | Mọi constraint C1-C10 checked cho MỖI đề xuất? | |
| QG16 | Vietnamese market context cụ thể cho MỖI đề xuất (không generic "VN users")? | |
| QG17 | Không recommend feature nào vi phạm constraint? | |
| QG18 | Innovation features có user story THẬT (persona + action + benefit)? | |

## Gate E: Quality
| # | Check | Pass? |
|---|-------|-------|
| QG19 | Optimization requirements ≥ 40 items (performance/UX/a11y/SEO/mobile)? | |
| QG20 | Sub-feature breakdown mỗi F-group ≥ 8 items chi tiết (what/optimize/why/current/gap)? | |

**20/20 PASS mới nộp. Thiếu 1 item = quay lại bổ sung.**

---

# FORBIDDEN — KHÔNG ĐƯỢC ĐỀ XUẤT

1. **Booking/payment/checkout** — CTA chỉ Zalo/Phone (constraint C3)
2. **Native app** — web-only (constraint C4)
3. **Real-time messaging** — users dùng Zalo (constraint C9)
4. **ML recommendation engine** — quá phức tạp cho solo dev, dùng rule-based
5. **Video streaming** — bandwidth + storage (constraint C9)
6. **AR/VR/3D** — (constraint C9)
7. **Multi-language** — chỉ tiếng Việt
8. **Dynamic pricing** — KHÔNG có giá, KHÔNG có booking
9. **Host/Guest system** — KHÔNG marketplace
10. **Verified purchase badges** — KHÔNG purchase
11. **Calendar availability** — KHÔNG booking
12. **Payment gateway integration** — (constraint C3)
13. **Affiliate links** — (constraint C7)
14. **Heavy analytics SaaS** — free-tier or self-hosted only (constraint C2)

---

## KẾT THÚC PROMPT
