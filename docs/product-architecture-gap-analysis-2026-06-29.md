# Product Architecture Gap Analysis - vinhlong360


> Date: 2026-06-29 | Role: Senior Product Architect | Scope: travel discovery/community showcase platform, web-only, Vietnamese-only, no booking/payment.


## 1. Executive Summary


- Platforms researched: 10 international/adjacent platforms + 5 Vietnamese competitors/channels.

- Feature matrix: 260 sub-features across 20 functional groups.

- vinhlong360 current coverage: 238/260 full-or-partial rows = 91.5%. The main gap is not absence; it is trust, freshness, planning polish, and mobile conversion clarity.

- Codebase verification: 252 backend route decorators, 66 Nuxt pages, 44 Vue components, 38 composables, 25 migrations verified by `rg`/PowerShell.

- Gap analysis: 62 gaps; 37 upgrade cards and 25 skip decisions.

- Priority upgrades: P0+P1=22 items; Consider/backlog P2+P3=15 items; innovation ideas=10.

- Top 5 impact gaps: source/freshness trust, review sorting/photo mode, map/list sync, itinerary share/export, Zalo/contact funnel analytics.

- Product stance: do not copy OTA commerce. The moat is local freshness, practical visit confidence, Zalo-first handoff, and structured community knowledge.


**Coverage by current system:** Search, detail, map, review/photos/helpful, auth, profiles, posts/Q&A, saved/plans, notifications, admin CMS, data quality, media, SEO and PWA are present. Upgrades should polish and connect them rather than add a new platform layer.


## 2. Platform Research

### Platform 1: GetYourGuide

**URL:** [https://www.getyourguide.com/](https://www.getyourguide.com/)  
**Category:** Tours & activities OTA  
**Scale:** Global marketplace; public page emphasizes trusted reviews, free cancellation on most activities, pay later, 24/7 support.  
**Target audience:** International city visitors who want bookable, low-risk activities.

**Key features (top 10):**
1. Hero destination/activity search — product value: reduces uncertainty or increases planning confidence.
2. Destination pages with category chips — product value: reduces uncertainty or increases planning confidence.
3. Activity cards with rating, review count, duration, price — product value: reduces uncertainty or increases planning confidence.
4. Detail gallery with mobile carousel — product value: reduces uncertainty or increases planning confidence.
5. Highlights, inclusions, meeting point, itinerary — product value: reduces uncertainty or increases planning confidence.
6. Review list with traveler metadata — product value: reduces uncertainty or increases planning confidence.
7. Cancellation policy and trust support — product value: reduces uncertainty or increases planning confidence.
8. Wishlist/save — product value: reduces uncertainty or increases planning confidence.
9. Curated collections and things-to-do guides — product value: reduces uncertainty or increases planning confidence.
10. Mobile sticky booking CTA — product value: reduces uncertainty or increases planning confidence.

**UX patterns đáng học:**
- A high-intent search bar dominates the first viewport.
- Reviews and cancellation policy appear before final commitment.
- Gallery is not decorative; it is the first trust object.

**Lessons for vinhlong360:**
- ADOPT: Gallery-first detail hierarchy, highlights, cancellation-like practical notes, trusted-review prominence.
- ADAPT: Replace booking sidebar with Zalo/Phone/map/contact widget and itinerary save.
- SKIP: Availability, payment, voucher, verified purchase, fake urgency.

**Screenshots/wireframe mô tả:**
- Homepage/layout: Home: hero search -> destination cards -> categories -> popular activities. Detail: gallery -> title/rating -> quick facts -> highlights -> inclusions -> meeting point -> reviews -> similar.
- Mobile vs desktop: desktop gives comparison density; mobile prioritizes search, swipe media, sticky next action, and bottom sheets.

### Platform 2: Klook

**URL:** [https://www.klook.com/en-US/](https://www.klook.com/en-US/)  
**Category:** SEA travel activities super-app  
**Scale:** Large regional app; public page stresses activities, hotels, free cancellation, reviews, credits and deals.  
**Target audience:** SEA mobile-first travelers looking for attractions, transport, SIM/eSIM, deals.

**Key features (top 10):**
1. Deal-led homepage — product value: reduces uncertainty or increases planning confidence.
2. Deep category taxonomy — product value: reduces uncertainty or increases planning confidence.
3. Destination/activity pages — product value: reduces uncertainty or increases planning confidence.
4. Package selection chips — product value: reduces uncertainty or increases planning confidence.
5. How-to-use and cancellation policy blocks — product value: reduces uncertainty or increases planning confidence.
6. Photo reviews — product value: reduces uncertainty or increases planning confidence.
7. Rating distribution — product value: reduces uncertainty or increases planning confidence.
8. Klook credits — product value: reduces uncertainty or increases planning confidence.
9. Promo codes and flash deals — product value: reduces uncertainty or increases planning confidence.
10. App-download funnel — product value: reduces uncertainty or increases planning confidence.

**UX patterns đáng học:**
- Mobile bottom-sheet controls for dense choices.
- Policy and how-to-use copy reduces post-click anxiety.
- Photo reviews are treated as a higher-trust subset.

**Lessons for vinhlong360:**
- ADOPT: How-to-use blocks, short practical policy cards, photo-review emphasis.
- ADAPT: Use deal-like seasonal guides without prices or checkout.
- SKIP: Credits, promo codes, package pricing, flash sales.

**Screenshots/wireframe mô tả:**
- Homepage/layout: Home: deals -> destinations -> categories -> activity grid -> app push. Detail: images -> title/social proof -> package -> how to use -> cancellation -> reviews.
- Mobile vs desktop: desktop gives comparison density; mobile prioritizes search, swipe media, sticky next action, and bottom sheets.

### Platform 3: Tripadvisor

**URL:** [https://www.tripadvisor.com/](https://www.tripadvisor.com/)  
**Category:** Reviews, rankings, community  
**Scale:** Global review/community platform; public forum page centers on ask/share/learn.  
**Target audience:** Travelers comparing places through UGC, rankings, and forum answers.

**Key features (top 10):**
1. Destination search — product value: reduces uncertainty or increases planning confidence.
2. Ranked lists — product value: reduces uncertainty or increases planning confidence.
3. Reviews with helpful votes — product value: reduces uncertainty or increases planning confidence.
4. Traveler photos — product value: reduces uncertainty or increases planning confidence.
5. Forums by destination/theme — product value: reduces uncertainty or increases planning confidence.
6. Q&A — product value: reduces uncertainty or increases planning confidence.
7. Profiles and contribution counts — product value: reduces uncertainty or increases planning confidence.
8. Badges and levels — product value: reduces uncertainty or increases planning confidence.
9. Management responses — product value: reduces uncertainty or increases planning confidence.
10. Trip boards — product value: reduces uncertainty or increases planning confidence.

**UX patterns đáng học:**
- Community answers fill gaps that official content cannot.
- Helpful votes are a low-cost proxy for review quality.
- Rankings are powerful but can become a vanity trap when data is thin.

**Lessons for vinhlong360:**
- ADOPT: Helpful votes, Q&A, contribution recognition, management/admin response.
- ADAPT: Rank locally by freshness/completeness, not volume.
- SKIP: Global ranking badges and monetized restaurant/hotel booking surfaces.

**Screenshots/wireframe mô tả:**
- Homepage/layout: Home: plan/search -> destination modules. Detail/community: title -> rank/reviews -> photos -> Q&A/forum threads -> similar.
- Mobile vs desktop: desktop gives comparison density; mobile prioritizes search, swipe media, sticky next action, and bottom sheets.

### Platform 4: Google Travel / Google Maps

**URL:** [https://www.google.com/travel/](https://www.google.com/travel/)  
**Category:** Aggregation, map, trip planning  
**Scale:** Ubiquitous default map/search layer; Maps help documents saved lists, search within lists, and directions.  
**Target audience:** Everyone needing directions, saved places, facts, hours, photos, reviews.

**Key features (top 10):**
1. Map-first discovery — product value: reduces uncertainty or increases planning confidence.
2. Knowledge panels — product value: reduces uncertainty or increases planning confidence.
3. Saved places/lists — product value: reduces uncertainty or increases planning confidence.
4. Directions and transit — product value: reduces uncertainty or increases planning confidence.
5. Nearby categories — product value: reduces uncertainty or increases planning confidence.
6. Hours and busy signals — product value: reduces uncertainty or increases planning confidence.
7. Reviews/photos — product value: reduces uncertainty or increases planning confidence.
8. Offline maps — product value: reduces uncertainty or increases planning confidence.
9. Trip/Travel aggregation — product value: reduces uncertainty or increases planning confidence.
10. Search integration — product value: reduces uncertainty or increases planning confidence.

**UX patterns đáng học:**
- Map and list work as one exploration object.
- Saved places must be findable later in search.
- Fresh factual data beats editorial polish for visit-stage intent.

**Lessons for vinhlong360:**
- ADOPT: Map/list sync, saved-list mental model, direct directions link.
- ADAPT: Use local editorial context around map pins where Google is generic.
- SKIP: Trying to compete with turn-by-turn navigation or global business review volume.

**Screenshots/wireframe mô tả:**
- Homepage/layout: Search/Explore: search input -> map canvas + list panel -> filters -> entity cards -> directions/save.
- Mobile vs desktop: desktop gives comparison density; mobile prioritizes search, swipe media, sticky next action, and bottom sheets.

### Platform 5: Airbnb Experiences

**URL:** [https://www.airbnb.com/](https://www.airbnb.com/)  
**Category:** Marketplace with local experiences  
**Scale:** Global marketplace; 2026 release highlights thousands more expert-led experiences and high average ratings.  
**Target audience:** Travelers wanting host-led, local-feeling stays/services/experiences.

**Key features (top 10):**
1. Category tabs — product value: reduces uncertainty or increases planning confidence.
2. Map toggle — product value: reduces uncertainty or increases planning confidence.
3. Wishlists — product value: reduces uncertainty or increases planning confidence.
4. Collaborative wishlist notes/votes — product value: reduces uncertainty or increases planning confidence.
5. Host profile — product value: reduces uncertainty or increases planning confidence.
6. Rules/amenities — product value: reduces uncertainty or increases planning confidence.
7. Reviews and host responses — product value: reduces uncertainty or increases planning confidence.
8. Past trips — product value: reduces uncertainty or increases planning confidence.
9. Experience categories — product value: reduces uncertainty or increases planning confidence.
10. Trust and verification — product value: reduces uncertainty or increases planning confidence.

**UX patterns đáng học:**
- Wishlists support group planning before purchase.
- Host profile is a trust object, not just attribution.
- Progressive disclosure keeps dense detail scannable.

**Lessons for vinhlong360:**
- ADOPT: Collaborative planning mechanics and local profile trust cards.
- ADAPT: Local guide/community profiles instead of host/guest marketplace roles.
- SKIP: Host payout logic, guest booking rules, availability calendars.

**Screenshots/wireframe mô tả:**
- Homepage/layout: Home: categories -> search/filter -> card grid + map. Detail: gallery -> title -> host/trust -> amenities/rules -> reviews -> location.
- Mobile vs desktop: desktop gives comparison density; mobile prioritizes search, swipe media, sticky next action, and bottom sheets.

### Platform 6: Viator

**URL:** [https://www.viator.com/](https://www.viator.com/)  
**Category:** Tours & activities OTA  
**Scale:** Large marketplace; homepage emphasizes free cancellation at least 24h ahead for most experiences.  
**Target audience:** Tripadvisor-connected travelers booking tours and tickets.

**Key features (top 10):**
1. Destination search — product value: reduces uncertainty or increases planning confidence.
2. Warm/trending destinations — product value: reduces uncertainty or increases planning confidence.
3. Tour cards — product value: reduces uncertainty or increases planning confidence.
4. Free cancellation copy — product value: reduces uncertainty or increases planning confidence.
5. Traveler reviews — product value: reduces uncertainty or increases planning confidence.
6. Operator info — product value: reduces uncertainty or increases planning confidence.
7. Mobile tickets — product value: reduces uncertainty or increases planning confidence.
8. Price filters — product value: reduces uncertainty or increases planning confidence.
9. Duration filters — product value: reduces uncertainty or increases planning confidence.
10. Similar tours — product value: reduces uncertainty or increases planning confidence.

**UX patterns đáng học:**
- Risk reversal is repeated at listing and detail levels.
- Review provenance matters because Viator inherits Tripadvisor trust.
- Cancellation and operator transparency are conversion levers.

**Lessons for vinhlong360:**
- ADOPT: Risk-reversal language adapted to 'go before you go' practical certainty.
- ADAPT: Operator/contact transparency without transaction.
- SKIP: Tour checkout and voucher flow.

**Screenshots/wireframe mô tả:**
- Homepage/layout: Home: search -> destination modules -> tour listings. Detail: gallery -> title/rating -> pricing/availability -> policy -> reviews.
- Mobile vs desktop: desktop gives comparison density; mobile prioritizes search, swipe media, sticky next action, and bottom sheets.

### Platform 7: Traveloka Xperience

**URL:** [https://www.traveloka.com/en-en/activities](https://www.traveloka.com/en-en/activities)  
**Category:** SEA super-app activities  
**Scale:** Regional super-app; activities pages surface Vietnam recommendations, deals, vouchers, reviews after redemption.  
**Target audience:** SEA/VN travelers buying attractions, transport, events, and travel essentials.

**Key features (top 10):**
1. Things to Do tab — product value: reduces uncertainty or increases planning confidence.
2. Country activity pages — product value: reduces uncertainty or increases planning confidence.
3. Attraction deals — product value: reduces uncertainty or increases planning confidence.
4. Voucher redemption — product value: reduces uncertainty or increases planning confidence.
5. Review requests after visit — product value: reduces uncertainty or increases planning confidence.
6. Relevant rating tags — product value: reduces uncertainty or increases planning confidence.
7. App-first account — product value: reduces uncertainty or increases planning confidence.
8. Promotions — product value: reduces uncertainty or increases planning confidence.
9. Transport essentials — product value: reduces uncertainty or increases planning confidence.
10. Customer support — product value: reduces uncertainty or increases planning confidence.

**UX patterns đáng học:**
- Post-visit review prompts are time-triggered.
- Tag-based reviews reduce writing effort.
- Deal inventory drives repeat opens but creates maintenance load.

**Lessons for vinhlong360:**
- ADOPT: Low-friction review tags after a planned/visited status.
- ADAPT: Use visited/want-to-visit as trigger instead of voucher redemption.
- SKIP: Voucher, promotion and checkout machinery.

**Screenshots/wireframe mô tả:**
- Homepage/layout: Home: travel tabs -> activities -> recommendations -> deals. Detail: ticket/voucher -> use instructions -> policy -> reviews.
- Mobile vs desktop: desktop gives comparison density; mobile prioritizes search, swipe media, sticky next action, and bottom sheets.

### Platform 8: Atlas Obscura

**URL:** [https://www.atlasobscura.com/](https://www.atlasobscura.com/)  
**Category:** Niche local discovery + community  
**Scale:** Global guide with tens of thousands of curious places and community contributions.  
**Target audience:** Curious travelers looking for unusual, story-rich places.

**Key features (top 10):**
1. Unique places directory — product value: reduces uncertainty or increases planning confidence.
2. Interactive map — product value: reduces uncertainty or increases planning confidence.
3. Community add/edit places — product value: reduces uncertainty or increases planning confidence.
4. Backstory-led detail pages — product value: reduces uncertainty or increases planning confidence.
5. Mobile app — product value: reduces uncertainty or increases planning confidence.
6. Nearby unusual places — product value: reduces uncertainty or increases planning confidence.
7. Visited/want-to-go — product value: reduces uncertainty or increases planning confidence.
8. Editorial articles — product value: reduces uncertainty or increases planning confidence.
9. Tours/trips — product value: reduces uncertainty or increases planning confidence.
10. Membership — product value: reduces uncertainty or increases planning confidence.

**UX patterns đáng học:**
- The story is the product; not every place needs commerce.
- Community add/edit creates long-tail coverage.
- Nearby curiosity is a good return trigger.

**Lessons for vinhlong360:**
- ADOPT: Local hidden-gem storytelling and contributor credit.
- ADAPT: Focus on Vinh Long/DBSCL specificity instead of global oddity.
- SKIP: Membership and paid trips.

**Screenshots/wireframe mô tả:**
- Homepage/layout: Home: search/explore -> map/places -> editorial. Detail: hero -> story -> visitor tips -> map -> nearby.
- Mobile vs desktop: desktop gives comparison density; mobile prioritizes search, swipe media, sticky next action, and bottom sheets.

### Platform 9: Lonely Planet

**URL:** [https://www.lonelyplanet.com/](https://www.lonelyplanet.com/)  
**Category:** Destination guides and expert editorial  
**Scale:** Established guidebook brand; homepage emphasizes expert tips and itineraries by budget/style.  
**Target audience:** Travelers planning by expert guide, itinerary, and travel style.

**Key features (top 10):**
1. Destination guides — product value: reduces uncertainty or increases planning confidence.
2. Expert tips — product value: reduces uncertainty or increases planning confidence.
3. Itineraries — product value: reduces uncertainty or increases planning confidence.
4. Travel inspiration — product value: reduces uncertainty or increases planning confidence.
5. Guidebooks/maps — product value: reduces uncertainty or increases planning confidence.
6. Newsletter — product value: reduces uncertainty or increases planning confidence.
7. Budget/style framing — product value: reduces uncertainty or increases planning confidence.
8. Best time to go — product value: reduces uncertainty or increases planning confidence.
9. Things to know — product value: reduces uncertainty or increases planning confidence.
10. Trip ideas — product value: reduces uncertainty or increases planning confidence.

**UX patterns đáng học:**
- Evergreen planning content supports SEO and trust.
- Itineraries are editorial products, not only tools.
- Best-time-to-go content maps directly to seasonal demand.

**Lessons for vinhlong360:**
- ADOPT: Concise 'things to know' and season-first guides.
- ADAPT: Short Vietnamese mobile summaries instead of long guidebook-style essays.
- SKIP: Print guidebook store and broad global taxonomy.

**Screenshots/wireframe mô tả:**
- Homepage/layout: Home: destination finder -> trip ideas -> guides. Destination: overview -> best time -> things to do -> itineraries -> practical info.
- Mobile vs desktop: desktop gives comparison density; mobile prioritizes search, swipe media, sticky next action, and bottom sheets.

### Platform 10: VoiceMap / self-guided walking tours

**URL:** [https://voicemap.me/](https://voicemap.me/)  
**Category:** Self-guided GPS/audio tours  
**Scale:** Tours across 600+ destinations; page highlights start/stop at own pace and automatic GPS playback.  
**Target audience:** Visitors wanting local narration without group tour timing.

**Key features (top 10):**
1. Self-guided tour catalog — product value: reduces uncertainty or increases planning confidence.
2. GPS-triggered audio — product value: reduces uncertainty or increases planning confidence.
3. Start/stop/resume — product value: reduces uncertainty or increases planning confidence.
4. Walking/driving/boat modes — product value: reduces uncertainty or increases planning confidence.
5. Route map — product value: reduces uncertainty or increases planning confidence.
6. Download for offline use — product value: reduces uncertainty or increases planning confidence.
7. Local narrator — product value: reduces uncertainty or increases planning confidence.
8. Tour preview — product value: reduces uncertainty or increases planning confidence.
9. Paid tour store — product value: reduces uncertainty or increases planning confidence.
10. Mobile app — product value: reduces uncertainty or increases planning confidence.

**UX patterns đáng học:**
- Route cue sheets can deliver value without a live guide.
- Offline-first tour data is important for travel use.
- Audio is high-value but production-heavy.

**Lessons for vinhlong360:**
- ADOPT: Self-guided route concept and printable cue cards.
- ADAPT: Use lightweight text/photo route stops first; avoid hosted audio/video.
- SKIP: Paid audio marketplace and native app dependency.

**Screenshots/wireframe mô tả:**
- Homepage/layout: Home: value prop -> destination/tour search -> tour cards. Detail: route summary -> narrator -> map -> purchase/download.
- Mobile vs desktop: desktop gives comparison density; mobile prioritizes search, swipe media, sticky next action, and bottom sheets.

### Vietnamese Competitor Context

| Đối thủ | URL/Kênh | Why relevant | Không thể cạnh tranh | Điểm yếu exploit | Feature gap |
| --- | --- | --- | --- | --- | --- |
| vinhlongtourist.vn | https://vinhlongtourist.vn/ | Official tourism authority content, news, destination legitimacy. | Official brand, government credibility, press/news access. | Content is article/news oriented; weak UGC, weak interactive planning, limited productized search/filter. | Exploit with route builder, freshness/source badges, community Q&A, mobile Zalo CTAs. |
| Google Maps Vinh Long | https://maps.google.com/ | Default for directions, reviews, hours, nearby search. | Cannot beat navigation ubiquity, place database, review volume, Android integration. | Generic story/context; no local itinerary, seasonal lens, OCOP/language nuance, or cultural route logic. | Exploit with editorial context around pins and shareable 1-2 day local plans. |
| Facebook Groups | Facebook groups such as du lich Vinh Long / an gi Vinh Long | Real user questions, local tips, fast UGC. | Huge user habit, low posting friction, social graph trust. | Poor search/structure, repeated questions, no verified entity data, hard to save into trip plans. | Exploit with Q&A attached to entities, tag search, accepted answers, and contributor credit. |
| Zalo OA / official contact channels | Zalo OA where available; official page and phone contacts | Vietnamese contact habit and official service channel. | High trust and direct messaging behavior. | Not a discovery/catalog/planning product; content is channel-based and fragmented. | Exploit with deep links, Zalo templates, click tracking, and 'share to family group' URLs. |
| TikTok / YouTube #dulichvinhlong | https://www.youtube.com/hashtag/dulichvinhlong | Attention competitor for visual inspiration. | Video is emotionally persuasive and algorithmic. | Poor structured details, stale contacts, weak planning/route/save after inspiration. | Exploit with video-link fields, short guide cards, and 'turn this video idea into plan' landing modules. |

### Vietnamese Digital Behavior Inputs

| Metric | Value/source | Feature implication |
| --- | --- | --- |
| Zalo MAU | 78.3M monthly active users in Vietnam in DataReportal 2026; VNG 2024 states 77.8M MAU | CTA Zalo > email; phone auth remains culturally aligned. |
| Facebook reach | 79.0M potential Facebook ad reach in late 2025 | OG tags and share preview quality matter more than X/Twitter integrations. |
| Internet/mobile | 85.6M internet users; 137M mobile connections, broadband-capable | Mobile-first, low-friction flows. Desktop is admin-first. |
| Screen widths | StatCounter global mobile top sizes include 414x896 and 360x800 in May 2026 | Test 360px/390px/414px; avoid desktop-only admin patterns in public UX. |
| Bandwidth reality | National median is high, but rural travel still sees unstable cellular and shared Wi-Fi | Use image lazy loading, WebP, SW cache, small JS chunks. |
| Trust signals | VN users trust phone/Zalo/referral and official pages more than anonymous web forms | Show source, last verified, phone, Zalo, and local contributor identity. |
| Payment culture | Cash, bank transfer, Momo/ZaloPay exist but site constraint forbids payment | No checkout; contact and itinerary are conversion endpoints. |
| Search behavior | Google/Facebook/YouTube dominate discovery | SEO, snippets, short visual content, share previews are top acquisition levers. |
| Seasonality | Tet, summer, 30/4-1/5, 2/9 drive trip planning | Publish seasonal pages before peaks; rank fresh seasonal items. |

## 3. Feature Comparison Matrix

Notation: ✅ full/strong, ⚠️ partial/niche, ❌ missing, N/A not applicable. Matrix has 260 rows (20 groups x 13 sub-features).

| Group | Sub-feature | GYG | Klook | TA | Google | Airbnb | Viator | Traveloka | Atlas | Lonely | VoiceMap | vinhlong360 | Gap? |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F1 Discovery IA | Homepage hero search | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ✅ implemented | NO |
| F1 Discovery IA | Seasonal modules | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F1 Discovery IA | Trending destinations | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F1 Discovery IA | Category chips | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F1 Discovery IA | Curated collections | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ✅ implemented | NO |
| F1 Discovery IA | New/updated strip | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F1 Discovery IA | Local hidden gems | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ⚠️ partial | YES |
| F1 Discovery IA | Area landing pages | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ❌ missing | YES |
| F1 Discovery IA | Interest pages | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | YES |
| F1 Discovery IA | Editorial rails | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F1 Discovery IA | Community highlights | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F1 Discovery IA | Homepage CTA hierarchy | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ⚠️ partial | YES |
| F1 Discovery IA | Empty-state discovery | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | YES |
| F2 Search & Filters | Global autocomplete | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ✅ implemented | NO |
| F2 Search & Filters | Recent searches | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F2 Search & Filters | Type filters | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F2 Search & Filters | Area filters | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F2 Search & Filters | Season/month filter | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ✅ implemented | NO |
| F2 Search & Filters | Rating sort | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F2 Search & Filters | Applied filter overview | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ⚠️ partial | YES |
| F2 Search & Filters | Mobile filter tray | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ❌ missing | YES |
| F2 Search & Filters | No-results recovery | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | YES |
| F2 Search & Filters | Search SEO schema | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F2 Search & Filters | Post search | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F2 Search & Filters | Query analytics | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ⚠️ partial | YES |
| F2 Search & Filters | Vietnamese unaccent search | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ✅ implemented | NO |
| F3 Entity Detail | Hero gallery | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ✅ implemented | NO |
| F3 Entity Detail | Photo count/lightbox | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F3 Entity Detail | Highlights | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F3 Entity Detail | Know before you go | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F3 Entity Detail | Hours and prices | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ✅ implemented | NO |
| F3 Entity Detail | Contact card | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F3 Entity Detail | Map section | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F3 Entity Detail | Nearby/similar | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F3 Entity Detail | Source/last verified | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | YES |
| F3 Entity Detail | Owner/admin response | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ⚠️ partial | YES |
| F3 Entity Detail | FAQ | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F3 Entity Detail | Related route links | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ⚠️ partial | YES |
| F3 Entity Detail | Sticky mobile CTA | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ✅ implemented | NO |
| F4 Reviews & Ratings | Star form | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ niche | ⚠️ niche | ✅ implemented | NO |
| F4 Reviews & Ratings | Review text form | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | N/A | N/A | ✅ implemented | NO |
| F4 Reviews & Ratings | Photo reviews | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ⚠️ niche | ⚠️ niche | ✅ implemented | NO |
| F4 Reviews & Ratings | Rating distribution | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | N/A | N/A | ✅ implemented | NO |
| F4 Reviews & Ratings | Mention/topic chips | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ niche | ⚠️ niche | ✅ implemented | NO |
| F4 Reviews & Ratings | Helpful votes | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | N/A | N/A | ✅ implemented | NO |
| F4 Reviews & Ratings | Review sorting | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ⚠️ niche | ⚠️ niche | ⚠️ partial | YES |
| F4 Reviews & Ratings | Review filters | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | N/A | N/A | ❌ missing | YES |
| F4 Reviews & Ratings | Owner response | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ niche | ⚠️ niche | ⚠️ partial | YES |
| F4 Reviews & Ratings | Review schema | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | N/A | N/A | ✅ implemented | NO |
| F4 Reviews & Ratings | Report review | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ⚠️ niche | ⚠️ niche | ✅ implemented | NO |
| F4 Reviews & Ratings | Review prompt after visit | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | N/A | N/A | ⚠️ partial | YES |
| F4 Reviews & Ratings | Review quality guard | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ niche | ⚠️ niche | ⚠️ partial | YES |
| F5 Community & Reputation | User profile | ⚠️ niche | ⚠️ niche | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ niche | ⚠️ niche | ⚠️ partial | ⚠️ partial | ⚠️ niche | ✅ implemented | NO |
| F5 Community & Reputation | Followers/following | N/A | N/A | ✅ strong | ✅ strong | ✅ strong | N/A | N/A | ✅ strong | ✅ strong | N/A | ✅ implemented | NO |
| F5 Community & Reputation | Contribution stats | ⚠️ niche | ⚠️ niche | ✅ strong | ✅ strong | ✅ strong | ⚠️ niche | ⚠️ niche | ✅ strong | ✅ strong | ⚠️ niche | ✅ implemented | NO |
| F5 Community & Reputation | Badges | N/A | N/A | ✅ strong | ✅ strong | ✅ strong | N/A | N/A | ✅ strong | ✅ strong | N/A | ✅ implemented | NO |
| F5 Community & Reputation | Leaderboard | ⚠️ niche | ⚠️ niche | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ niche | ⚠️ niche | ⚠️ partial | ⚠️ partial | ⚠️ niche | ✅ implemented | NO |
| F5 Community & Reputation | Local guide trust card | N/A | N/A | ✅ strong | ✅ strong | ✅ strong | N/A | N/A | ✅ strong | ✅ strong | N/A | ⚠️ partial | YES |
| F5 Community & Reputation | Suggested follows | ⚠️ niche | ⚠️ niche | ✅ strong | ✅ strong | ✅ strong | ⚠️ niche | ⚠️ niche | ✅ strong | ✅ strong | ⚠️ niche | ✅ implemented | NO |
| F5 Community & Reputation | Entity follow | N/A | N/A | ✅ strong | ✅ strong | ✅ strong | N/A | N/A | ✅ strong | ✅ strong | N/A | ✅ implemented | NO |
| F5 Community & Reputation | Q&A best answer | ⚠️ niche | ⚠️ niche | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ niche | ⚠️ niche | ⚠️ partial | ⚠️ partial | ⚠️ niche | ⚠️ partial | YES |
| F5 Community & Reputation | Repost | N/A | N/A | ✅ strong | ✅ strong | ✅ strong | N/A | N/A | ✅ strong | ✅ strong | N/A | ✅ implemented | NO |
| F5 Community & Reputation | Block user | ⚠️ niche | ⚠️ niche | ✅ strong | ✅ strong | ✅ strong | ⚠️ niche | ⚠️ niche | ✅ strong | ✅ strong | ⚠️ niche | ✅ implemented | NO |
| F5 Community & Reputation | Contributor credit | N/A | N/A | ✅ strong | ✅ strong | ✅ strong | N/A | N/A | ✅ strong | ✅ strong | N/A | ✅ implemented | NO |
| F5 Community & Reputation | Community guidelines | ⚠️ niche | ⚠️ niche | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ niche | ⚠️ niche | ⚠️ partial | ⚠️ partial | ⚠️ niche | ⚠️ partial | YES |
| F6 UGC Creation & Moderation | Review/share/question/recommend post types | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ niche | ⚠️ niche | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ niche | ⚠️ niche | ✅ implemented | NO |
| F6 UGC Creation & Moderation | Image upload | ✅ strong | ✅ strong | ✅ strong | N/A | N/A | ✅ strong | ✅ strong | ✅ strong | N/A | N/A | ✅ implemented | NO |
| F6 UGC Creation & Moderation | Draft autosave | ✅ strong | ✅ strong | ✅ strong | ⚠️ niche | ⚠️ niche | ✅ strong | ✅ strong | ✅ strong | ⚠️ niche | ⚠️ niche | ✅ implemented | NO |
| F6 UGC Creation & Moderation | Hashtags | ✅ strong | ✅ strong | ✅ strong | N/A | N/A | ✅ strong | ✅ strong | ✅ strong | N/A | N/A | ✅ implemented | NO |
| F6 UGC Creation & Moderation | Mentions | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ niche | ⚠️ niche | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ niche | ⚠️ niche | ✅ implemented | NO |
| F6 UGC Creation & Moderation | Threaded comments | ✅ strong | ✅ strong | ✅ strong | N/A | N/A | ✅ strong | ✅ strong | ✅ strong | N/A | N/A | ✅ implemented | NO |
| F6 UGC Creation & Moderation | Moderation queue | ✅ strong | ✅ strong | ✅ strong | ⚠️ niche | ⚠️ niche | ✅ strong | ✅ strong | ✅ strong | ⚠️ niche | ⚠️ niche | ✅ implemented | NO |
| F6 UGC Creation & Moderation | Report UGC | ✅ strong | ✅ strong | ✅ strong | N/A | N/A | ✅ strong | ✅ strong | ✅ strong | N/A | N/A | ✅ implemented | NO |
| F6 UGC Creation & Moderation | Batch moderation | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ niche | ⚠️ niche | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ niche | ⚠️ niche | ✅ implemented | NO |
| F6 UGC Creation & Moderation | Image safety | ✅ strong | ✅ strong | ✅ strong | N/A | N/A | ✅ strong | ✅ strong | ✅ strong | N/A | N/A | ✅ implemented | NO |
| F6 UGC Creation & Moderation | Post search | ✅ strong | ✅ strong | ✅ strong | ⚠️ niche | ⚠️ niche | ✅ strong | ✅ strong | ✅ strong | ⚠️ niche | ⚠️ niche | ✅ implemented | NO |
| F6 UGC Creation & Moderation | Post related | ✅ strong | ✅ strong | ✅ strong | N/A | N/A | ✅ strong | ✅ strong | ✅ strong | N/A | N/A | ✅ implemented | NO |
| F6 UGC Creation & Moderation | Low-friction review tags | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ niche | ⚠️ niche | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ niche | ⚠️ niche | ⚠️ partial | YES |
| F7 Saved & Collections | Save entity | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ✅ implemented | NO |
| F7 Saved & Collections | Merge local saved | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F7 Saved & Collections | Saved sync | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F7 Saved & Collections | Saved snapshots | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F7 Saved & Collections | Multi-list collections | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ❌ missing | YES |
| F7 Saved & Collections | Share collections | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ⚠️ partial | YES |
| F7 Saved & Collections | Collaborative notes | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ⚠️ partial | YES |
| F7 Saved & Collections | Vote up/down in group | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ❌ missing | YES |
| F7 Saved & Collections | Recently viewed | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ✅ implemented | NO |
| F7 Saved & Collections | Want-to-visit | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F7 Saved & Collections | Visited | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F7 Saved & Collections | Offline saved snapshot | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ⚠️ partial | YES |
| F7 Saved & Collections | Collection landing page | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | YES |
| F8 Map & Navigation | Map pins | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ✅ implemented | NO |
| F8 Map & Navigation | Type filters | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F8 Map & Navigation | Area filters | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F8 Map & Navigation | Clusters | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F8 Map & Navigation | Popup cards | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ✅ implemented | NO |
| F8 Map & Navigation | List+map split | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ⚠️ partial | YES |
| F8 Map & Navigation | Directions handoff | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ⚠️ partial | YES |
| F8 Map & Navigation | Route preview | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ❌ missing | YES |
| F8 Map & Navigation | Offline map hints | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | YES |
| F8 Map & Navigation | Ward map context | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F8 Map & Navigation | Nearby by distance | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F8 Map & Navigation | Transport guide | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ⚠️ partial | YES |
| F8 Map & Navigation | Route cue sheet | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | YES |
| F9 Personalization & Return | Recently viewed | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ✅ implemented | NO |
| F9 Personalization & Return | Followed entity feed | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F9 Personalization & Return | What's new | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ⚠️ partial | YES |
| F9 Personalization & Return | Seasonal return prompts | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ⚠️ partial | YES |
| F9 Personalization & Return | Saved reminder | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ❌ missing | YES |
| F9 Personalization & Return | Visited-based prompts | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ⚠️ partial | YES |
| F9 Personalization & Return | Notification digest | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ⚠️ partial | YES |
| F9 Personalization & Return | Personalized homepage | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ❌ missing | YES |
| F9 Personalization & Return | Rule-based recommendations | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ✅ implemented | NO |
| F9 Personalization & Return | Search recents | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F9 Personalization & Return | Return user onboarding | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F9 Personalization & Return | Stale saved warning | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ⚠️ partial | YES |
| F9 Personalization & Return | Privacy controls | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ✅ implemented | NO |
| F10 Itinerary Planning | Admin itineraries | ⚠️ partial | ⚠️ partial | ⚠️ niche | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ✅ implemented | NO |
| F10 Itinerary Planning | User itinerary builder | ✅ strong | ✅ strong | N/A | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F10 Itinerary Planning | Save plans | ✅ strong | ✅ strong | ⚠️ niche | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F10 Itinerary Planning | Publish plan | ✅ strong | ✅ strong | N/A | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F10 Itinerary Planning | Shared plan page | ⚠️ partial | ⚠️ partial | ⚠️ niche | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ✅ implemented | NO |
| F10 Itinerary Planning | Native share | ✅ strong | ✅ strong | N/A | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F10 Itinerary Planning | Print/export | ✅ strong | ✅ strong | ⚠️ niche | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ⚠️ partial | YES |
| F10 Itinerary Planning | Day-by-day view | ✅ strong | ✅ strong | N/A | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F10 Itinerary Planning | Map route | ⚠️ partial | ⚠️ partial | ⚠️ niche | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | YES |
| F10 Itinerary Planning | Group comments | ✅ strong | ✅ strong | N/A | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ⚠️ partial | YES |
| F10 Itinerary Planning | Collaborative voting | ✅ strong | ✅ strong | ⚠️ niche | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ❌ missing | YES |
| F10 Itinerary Planning | Time budget | ✅ strong | ✅ strong | N/A | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ⚠️ partial | YES |
| F10 Itinerary Planning | Family-friendly labels | ⚠️ partial | ⚠️ partial | ⚠️ niche | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | YES |
| F11 Content Guides & SEO | Sitemaps | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ niche | ⚠️ partial | ⚠️ niche | ⚠️ partial | ⚠️ partial | ⚠️ partial | ✅ implemented | NO |
| F11 Content Guides & SEO | Media sitemap | ✅ strong | ✅ strong | ✅ strong | ✅ strong | N/A | ✅ strong | N/A | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F11 Content Guides & SEO | Robots | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ⚠️ niche | ✅ strong | ⚠️ niche | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F11 Content Guides & SEO | Entity JSON-LD | ✅ strong | ✅ strong | ✅ strong | ✅ strong | N/A | ✅ strong | N/A | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F11 Content Guides & SEO | Itinerary JSON-LD | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ niche | ⚠️ partial | ⚠️ niche | ⚠️ partial | ⚠️ partial | ⚠️ partial | ✅ implemented | NO |
| F11 Content Guides & SEO | FAQ JSON-LD | ✅ strong | ✅ strong | ✅ strong | ✅ strong | N/A | ✅ strong | N/A | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F11 Content Guides & SEO | OG tags | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ⚠️ niche | ✅ strong | ⚠️ niche | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F11 Content Guides & SEO | Article/review schema | ✅ strong | ✅ strong | ✅ strong | ✅ strong | N/A | ✅ strong | N/A | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F11 Content Guides & SEO | Area guides | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ niche | ⚠️ partial | ⚠️ niche | ⚠️ partial | ⚠️ partial | ⚠️ partial | ✅ implemented | NO |
| F11 Content Guides & SEO | Season guides | ✅ strong | ✅ strong | ✅ strong | ✅ strong | N/A | ✅ strong | N/A | ✅ strong | ✅ strong | ✅ strong | ⚠️ partial | YES |
| F11 Content Guides & SEO | Short mobile snippets | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ⚠️ niche | ✅ strong | ⚠️ niche | ✅ strong | ✅ strong | ✅ strong | ❌ missing | YES |
| F11 Content Guides & SEO | Internal links | ✅ strong | ✅ strong | ✅ strong | ✅ strong | N/A | ✅ strong | N/A | ✅ strong | ✅ strong | ✅ strong | ⚠️ partial | YES |
| F11 Content Guides & SEO | Content calendar | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ niche | ⚠️ partial | ⚠️ niche | ⚠️ partial | ⚠️ partial | ⚠️ partial | ✅ implemented | NO |
| F12 Mobile Performance & PWA | Nuxt image WebP | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ✅ implemented | NO |
| F12 Mobile Performance & PWA | Lazy images | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F12 Mobile Performance & PWA | Hero preload | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F12 Mobile Performance & PWA | Service worker | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F12 Mobile Performance & PWA | Asset cache | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ✅ implemented | NO |
| F12 Mobile Performance & PWA | API cache | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ⚠️ partial | YES |
| F12 Mobile Performance & PWA | Map lazy chunk | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F12 Mobile Performance & PWA | Skeleton states | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F12 Mobile Performance & PWA | 360px QA | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | YES |
| F12 Mobile Performance & PWA | Reduced motion | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F12 Mobile Performance & PWA | A11y focus | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F12 Mobile Performance & PWA | Low-bandwidth mode | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ⚠️ partial | YES |
| F12 Mobile Performance & PWA | CLS guards | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ✅ implemented | NO |
| F13 Contact & Conversion | Phone CTA | ⚠️ partial | ⚠️ partial | ⚠️ niche | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ niche | ⚠️ niche | ⚠️ niche | ✅ implemented | NO |
| F13 Contact & Conversion | Zalo CTA | ✅ strong | ✅ strong | N/A | ✅ strong | ✅ strong | ✅ strong | ✅ strong | N/A | N/A | N/A | ✅ implemented | NO |
| F13 Contact & Conversion | Map CTA | ✅ strong | ✅ strong | ⚠️ niche | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ⚠️ niche | ⚠️ niche | ⚠️ niche | ✅ implemented | NO |
| F13 Contact & Conversion | Website CTA | ✅ strong | ✅ strong | N/A | ✅ strong | ✅ strong | ✅ strong | ✅ strong | N/A | N/A | N/A | ✅ implemented | NO |
| F13 Contact & Conversion | Contact click tracking | ⚠️ partial | ⚠️ partial | ⚠️ niche | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ niche | ⚠️ niche | ⚠️ niche | ✅ implemented | NO |
| F13 Contact & Conversion | Sticky contact bar | ✅ strong | ✅ strong | N/A | ✅ strong | ✅ strong | ✅ strong | ✅ strong | N/A | N/A | N/A | ✅ implemented | NO |
| F13 Contact & Conversion | Copy phone | ✅ strong | ✅ strong | ⚠️ niche | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ⚠️ niche | ⚠️ niche | ⚠️ niche | ✅ implemented | NO |
| F13 Contact & Conversion | Zalo deep-link template | ✅ strong | ✅ strong | N/A | ✅ strong | ✅ strong | ✅ strong | ✅ strong | N/A | N/A | N/A | ❌ missing | YES |
| F13 Contact & Conversion | Fallback itinerary CTA | ⚠️ partial | ⚠️ partial | ⚠️ niche | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ niche | ⚠️ niche | ⚠️ niche | ✅ implemented | NO |
| F13 Contact & Conversion | Contact source confidence | ✅ strong | ✅ strong | N/A | ✅ strong | ✅ strong | ✅ strong | ✅ strong | N/A | N/A | N/A | ⚠️ partial | YES |
| F13 Contact & Conversion | Owner claim CTA | ✅ strong | ✅ strong | ⚠️ niche | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ⚠️ niche | ⚠️ niche | ⚠️ niche | ❌ missing | YES |
| F13 Contact & Conversion | CTA analytics | ✅ strong | ✅ strong | N/A | ✅ strong | ✅ strong | ✅ strong | ✅ strong | N/A | N/A | N/A | ⚠️ partial | YES |
| F13 Contact & Conversion | No checkout guard | ⚠️ partial | ⚠️ partial | ⚠️ niche | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ niche | ⚠️ niche | ⚠️ niche | ✅ implemented | NO |
| F14 Admin CMS | Entity CRUD | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ niche | ⚠️ partial | ⚠️ niche | ⚠️ partial | ⚠️ niche | ⚠️ partial | ⚠️ niche | ✅ implemented | NO |
| F14 Admin CMS | Image upload | ✅ strong | ✅ strong | ✅ strong | N/A | ✅ strong | N/A | ✅ strong | N/A | ✅ strong | N/A | ✅ implemented | NO |
| F14 Admin CMS | Media library | ✅ strong | ✅ strong | ✅ strong | ⚠️ niche | ✅ strong | ⚠️ niche | ✅ strong | ⚠️ niche | ✅ strong | ⚠️ niche | ✅ implemented | NO |
| F14 Admin CMS | Moderation queue | ✅ strong | ✅ strong | ✅ strong | N/A | ✅ strong | N/A | ✅ strong | N/A | ✅ strong | N/A | ✅ implemented | NO |
| F14 Admin CMS | Reports | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ niche | ⚠️ partial | ⚠️ niche | ⚠️ partial | ⚠️ niche | ⚠️ partial | ⚠️ niche | ✅ implemented | NO |
| F14 Admin CMS | User management | ✅ strong | ✅ strong | ✅ strong | N/A | ✅ strong | N/A | ✅ strong | N/A | ✅ strong | N/A | ✅ implemented | NO |
| F14 Admin CMS | Analytics | ✅ strong | ✅ strong | ✅ strong | ⚠️ niche | ✅ strong | ⚠️ niche | ✅ strong | ⚠️ niche | ✅ strong | ⚠️ niche | ✅ implemented | NO |
| F14 Admin CMS | Site settings | ✅ strong | ✅ strong | ✅ strong | N/A | ✅ strong | N/A | ✅ strong | N/A | ✅ strong | N/A | ✅ implemented | NO |
| F14 Admin CMS | Data quality review | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ niche | ⚠️ partial | ⚠️ niche | ⚠️ partial | ⚠️ niche | ⚠️ partial | ⚠️ niche | ✅ implemented | NO |
| F14 Admin CMS | Audit log | ✅ strong | ✅ strong | ✅ strong | N/A | ✅ strong | N/A | ✅ strong | N/A | ✅ strong | N/A | ✅ implemented | NO |
| F14 Admin CMS | Backup/export | ✅ strong | ✅ strong | ✅ strong | ⚠️ niche | ✅ strong | ⚠️ niche | ✅ strong | ⚠️ niche | ✅ strong | ⚠️ niche | ✅ implemented | NO |
| F14 Admin CMS | AI triage | ✅ strong | ✅ strong | ✅ strong | N/A | ✅ strong | N/A | ✅ strong | N/A | ✅ strong | N/A | ✅ implemented | NO |
| F14 Admin CMS | Batch operations | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ niche | ⚠️ partial | ⚠️ niche | ⚠️ partial | ⚠️ niche | ⚠️ partial | ⚠️ niche | ⚠️ partial | YES |
| F15 Data Quality & Freshness | Data quality summary | ⚠️ partial | ⚠️ niche | ⚠️ partial | ⚠️ partial | ⚠️ niche | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ✅ implemented | NO |
| F15 Data Quality & Freshness | Source registry | ✅ strong | N/A | ✅ strong | ✅ strong | N/A | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F15 Data Quality & Freshness | Last updated | ✅ strong | ⚠️ niche | ✅ strong | ✅ strong | ⚠️ niche | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F15 Data Quality & Freshness | Public freshness badge | ✅ strong | N/A | ✅ strong | ✅ strong | N/A | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ⚠️ partial | YES |
| F15 Data Quality & Freshness | Stale queue | ⚠️ partial | ⚠️ niche | ⚠️ partial | ⚠️ partial | ⚠️ niche | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ❌ missing | YES |
| F15 Data Quality & Freshness | Rollback | ✅ strong | N/A | ✅ strong | ✅ strong | N/A | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F15 Data Quality & Freshness | Image suggestion review | ✅ strong | ⚠️ niche | ✅ strong | ✅ strong | ⚠️ niche | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F15 Data Quality & Freshness | Duplicate check | ✅ strong | N/A | ✅ strong | ✅ strong | N/A | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F15 Data Quality & Freshness | Coordinate confidence | ⚠️ partial | ⚠️ niche | ⚠️ partial | ⚠️ partial | ⚠️ niche | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | YES |
| F15 Data Quality & Freshness | Opening hours confidence | ✅ strong | N/A | ✅ strong | ✅ strong | N/A | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ⚠️ partial | YES |
| F15 Data Quality & Freshness | Season data | ✅ strong | ⚠️ niche | ✅ strong | ✅ strong | ⚠️ niche | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F15 Data Quality & Freshness | Admin SLA | ✅ strong | N/A | ✅ strong | ✅ strong | N/A | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ⚠️ partial | YES |
| F15 Data Quality & Freshness | Public correction report | ⚠️ partial | ⚠️ niche | ⚠️ partial | ⚠️ partial | ⚠️ niche | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | YES |
| F16 Social Proof & Trust | Rating count | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ✅ implemented | NO |
| F16 Social Proof & Trust | Photo proof | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F16 Social Proof & Trust | Verified source badge | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ⚠️ partial | YES |
| F16 Social Proof & Trust | Local contributor identity | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ⚠️ partial | YES |
| F16 Social Proof & Trust | Admin response | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ❌ missing | YES |
| F16 Social Proof & Trust | Helpful votes | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F16 Social Proof & Trust | Review excerpts | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F16 Social Proof & Trust | Trust copy | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F16 Social Proof & Trust | Official/partner badge | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | YES |
| F16 Social Proof & Trust | No fake urgency | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F16 Social Proof & Trust | Source links | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ❌ missing | YES |
| F16 Social Proof & Trust | Privacy-safe profiles | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F16 Social Proof & Trust | Community stats | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ✅ implemented | NO |
| F17 Notifications & Follow | Notification list | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ niche | ⚠️ niche | ✅ implemented | NO |
| F17 Notifications & Follow | Unread count | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | N/A | N/A | ✅ implemented | NO |
| F17 Notifications & Follow | Mark read | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ⚠️ niche | ⚠️ niche | ✅ implemented | NO |
| F17 Notifications & Follow | Read all | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | N/A | N/A | ✅ implemented | NO |
| F17 Notifications & Follow | SSE stream | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ niche | ⚠️ niche | ✅ implemented | NO |
| F17 Notifications & Follow | Polling fallback | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | N/A | N/A | ✅ implemented | NO |
| F17 Notifications & Follow | Notification preferences | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ⚠️ niche | ⚠️ niche | ✅ implemented | NO |
| F17 Notifications & Follow | Follow entity | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | N/A | N/A | ✅ implemented | NO |
| F17 Notifications & Follow | Follow user | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ niche | ⚠️ niche | ✅ implemented | NO |
| F17 Notifications & Follow | Event RSVP | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | N/A | N/A | ✅ implemented | NO |
| F17 Notifications & Follow | Event reminder | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ⚠️ niche | ⚠️ niche | ❌ missing | YES |
| F17 Notifications & Follow | Digest | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | N/A | N/A | ⚠️ partial | YES |
| F17 Notifications & Follow | Mute entity | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ niche | ⚠️ niche | ⚠️ partial | YES |
| F18 Safety, Legal & Privacy | Phone verification | ⚠️ niche | ⚠️ niche | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ niche | ⚠️ niche | ⚠️ partial | ⚠️ partial | ⚠️ partial | ✅ implemented | NO |
| F18 Safety, Legal & Privacy | Consent logging | N/A | N/A | ✅ strong | ✅ strong | ✅ strong | N/A | N/A | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F18 Safety, Legal & Privacy | Privacy settings | ⚠️ niche | ⚠️ niche | ✅ strong | ✅ strong | ✅ strong | ⚠️ niche | ⚠️ niche | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F18 Safety, Legal & Privacy | Login history | N/A | N/A | ✅ strong | ✅ strong | ✅ strong | N/A | N/A | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F18 Safety, Legal & Privacy | Block/report | ⚠️ niche | ⚠️ niche | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ niche | ⚠️ niche | ⚠️ partial | ⚠️ partial | ⚠️ partial | ✅ implemented | NO |
| F18 Safety, Legal & Privacy | Moderation notes | N/A | N/A | ✅ strong | ✅ strong | ✅ strong | N/A | N/A | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F18 Safety, Legal & Privacy | PII masking | ⚠️ niche | ⚠️ niche | ✅ strong | ✅ strong | ✅ strong | ⚠️ niche | ⚠️ niche | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F18 Safety, Legal & Privacy | CSRF | N/A | N/A | ✅ strong | ✅ strong | ✅ strong | N/A | N/A | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F18 Safety, Legal & Privacy | Rate limits | ⚠️ niche | ⚠️ niche | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ niche | ⚠️ niche | ⚠️ partial | ⚠️ partial | ⚠️ partial | ✅ implemented | NO |
| F18 Safety, Legal & Privacy | Account delete/deactivate | N/A | N/A | ✅ strong | ✅ strong | ✅ strong | N/A | N/A | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F18 Safety, Legal & Privacy | Content rules | ⚠️ niche | ⚠️ niche | ✅ strong | ✅ strong | ✅ strong | ⚠️ niche | ⚠️ niche | ✅ strong | ✅ strong | ✅ strong | ❌ missing | YES |
| F18 Safety, Legal & Privacy | Legal pages | N/A | N/A | ✅ strong | ✅ strong | ✅ strong | N/A | N/A | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F18 Safety, Legal & Privacy | NĐ147 readiness | ⚠️ niche | ⚠️ niche | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ niche | ⚠️ niche | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | YES |
| F19 Analytics & Experimentation | Admin overview | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ✅ implemented | NO |
| F19 Analytics & Experimentation | Popular pages | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F19 Analytics & Experimentation | Daily stats | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F19 Analytics & Experimentation | Top entities | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F19 Analytics & Experimentation | Contact funnel | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ❌ missing | YES |
| F19 Analytics & Experimentation | Save funnel | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ⚠️ partial | YES |
| F19 Analytics & Experimentation | Plan funnel | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ⚠️ partial | YES |
| F19 Analytics & Experimentation | Search zero-result KPI | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ❌ missing | YES |
| F19 Analytics & Experimentation | Data freshness KPI | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | YES |
| F19 Analytics & Experimentation | CSV export | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F19 Analytics & Experimentation | Self-hosted metrics | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ implemented | NO |
| F19 Analytics & Experimentation | A/B light | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ✅ strong | ⚠️ partial | YES |
| F19 Analytics & Experimentation | Client error reports | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ✅ implemented | NO |
| F20 Monetization & Partnership | Partner directory | ⚠️ niche | ⚠️ partial | ⚠️ niche | ⚠️ niche | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ niche | ⚠️ niche | ⚠️ niche | ⚠️ partial | YES |
| F20 Monetization & Partnership | Claim entity | N/A | ✅ strong | N/A | N/A | ✅ strong | ✅ strong | ✅ strong | N/A | N/A | N/A | ❌ missing | YES |
| F20 Monetization & Partnership | Sponsored showcase label | ⚠️ niche | ✅ strong | ⚠️ niche | ⚠️ niche | ✅ strong | ✅ strong | ✅ strong | ⚠️ niche | ⚠️ niche | ⚠️ niche | ⚠️ partial | YES |
| F20 Monetization & Partnership | No affiliate links | N/A | ✅ strong | N/A | N/A | ✅ strong | ✅ strong | ✅ strong | N/A | N/A | N/A | ✅ implemented | NO |
| F20 Monetization & Partnership | No payment | ⚠️ niche | ⚠️ partial | ⚠️ niche | ⚠️ niche | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ niche | ⚠️ niche | ⚠️ niche | ✅ implemented | NO |
| F20 Monetization & Partnership | Lead/contact attribution | N/A | ✅ strong | N/A | N/A | ✅ strong | ✅ strong | ✅ strong | N/A | N/A | N/A | ⚠️ partial | YES |
| F20 Monetization & Partnership | Campaign landing page | ⚠️ niche | ✅ strong | ⚠️ niche | ⚠️ niche | ✅ strong | ✅ strong | ✅ strong | ⚠️ niche | ⚠️ niche | ⚠️ niche | ✅ implemented | NO |
| F20 Monetization & Partnership | Seasonal packages | N/A | ✅ strong | N/A | N/A | ✅ strong | ✅ strong | ✅ strong | N/A | N/A | N/A | ❌ missing | YES |
| F20 Monetization & Partnership | Offline invoice note | ⚠️ niche | ⚠️ partial | ⚠️ niche | ⚠️ niche | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ niche | ⚠️ niche | ⚠️ niche | ✅ implemented | NO |
| F20 Monetization & Partnership | Public transparency | N/A | ✅ strong | N/A | N/A | ✅ strong | ✅ strong | ✅ strong | N/A | N/A | N/A | ✅ implemented | NO |
| F20 Monetization & Partnership | Partner analytics | ⚠️ niche | ✅ strong | ⚠️ niche | ⚠️ niche | ✅ strong | ✅ strong | ✅ strong | ⚠️ niche | ⚠️ niche | ⚠️ niche | ❌ missing | YES |
| F20 Monetization & Partnership | Content partnership workflow | N/A | ✅ strong | N/A | N/A | ✅ strong | ✅ strong | ✅ strong | N/A | N/A | N/A | ⚠️ partial | YES |
| F20 Monetization & Partnership | Commercial boundary docs | ⚠️ niche | ⚠️ partial | ⚠️ niche | ⚠️ niche | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ niche | ⚠️ niche | ⚠️ niche | ⚠️ partial | YES |

## 4. Gap Analysis - 62 Gaps, 7 Tầng Mỗi Gap

### Gap G-01: Zalo-first contact instrumentation

**Functional group:** F13 Contact & Conversion  
**Severity:** 🔴 Critical  
**Mapped upgrade:** U-01 (P0)

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| GetYourGuide/Klook/Viator | Commercial activity marketplaces solve this around booking confidence. | 8/10 | Trust/review/policy wrapped into conversion. |
| Tripadvisor/Google/Airbnb | Community/map/planning platforms solve adjacent trust and planning needs. | 8/10 | UGC and saved-list context. |
| vinhlong360 | Phone/Zalo is present but funnel analytics and copy variants are not productized. | 60-80% coverage | Local-only context plus no-booking boundary. |

**Tầng 2 — WHY:**

- User problem solved: Make Zalo/Phone/map clicks measurable by entity, source, viewport, and season.
- Business value: improves contact CTR, Zalo clicks/entity, phone clicks/entity without adding booking/payment support.
- Research backing: NNGroup on scannability/visual hierarchy, NNGroup/Baymard on filters where relevant, Google structured data docs for SEO-related items.
- Reasoning chain: Persona P1 need -> feature makes decision easier -> measured by contact CTR, Zalo clicks/entity, phone clicks/entity -> existing evidence E08 reduces build effort -> expected outcome is higher trust or planning completion.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 4 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 4 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 4 | No paid infra required beyond current stack. |
| Competitive advantage | 4 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 4 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **20/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- web-nuxt/pages/dia-diem/[id].vue:96..97 - hero call and Zalo actions.
- web-nuxt/pages/dia-diem/[id].vue:369..402 - contact row and sticky CTA phone/Zalo/map fallback.
- web-nuxt/pages/dia-diem/[id].vue:711..715 - Zalo URL/number normalization.
Conclusion: 60-80% implemented; gap is productization/polish, not greenfield.
```
**Tầng 5 — UPGRADE CARD:**
```text
U-01: Zalo-first contact instrumentation
Primary persona: P1; Secondary: P3; Journey: RESEARCH,VISIT
Problem: Phone/Zalo is present but funnel analytics and copy variants are not productized.
Target: Make Zalo/Phone/map clicks measurable by entity, source, viewport, and season.
Sub-features cần build:
  1. UI/control/state for the main flow — effort: M
  2. Admin/data or API linkage where needed — effort: S/M
  3. Metrics/event instrumentation — effort: S
Tối ưu cần làm:
  1. Mobile 360px and 44px tap target QA — why: VN mobile-first — how: responsive screenshot checklist
  2. SEO/a11y/performance guard — why: organic discovery and low bandwidth — how: lazy load, aria labels, structured metadata where valid
Files to modify:
  Backend: web-nuxt/pages/dia-diem/[id].vue:96..97 - hero call and Zalo actions.
  Frontend: web-nuxt/pages/dia-diem/[id].vue:369..402 - contact row and sticky CTA phone/Zalo/map fallback.
  Database: No migration expected
Dependencies: existing E08; constraints: no booking/payment/native app/ML/video streaming.
Risk: LOW — maintenance tax approx 1h/month.
Effort: BE 0d + FE 1.5d + DB 0d = 1.5d.
Impact: contact CTR, Zalo clicks/entity, phone clicks/entity should move within 2-4 weeks.
Vietnamese market note: Zalo/Facebook/mobile and source freshness are explicit design constraints.
Priority: P0
```
**Tầng 6 — SKIP:** Không skip. Giới hạn phạm vi để không trượt sang booking/payment, real-time messaging, ML, hoặc video hosting.

**Tầng 7 — INNOVATION:** Adapt this as a local-first feature: use Vĩnh Long season/source/community knowledge that global platforms do not maintain deeply.

### Gap G-02: Source and last-verified block on detail

**Functional group:** F15 Data Quality & Freshness  
**Severity:** 🔴 Critical  
**Mapped upgrade:** U-02 (P0)

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| GetYourGuide/Klook/Viator | Commercial activity marketplaces solve this around booking confidence. | 8/10 | Trust/review/policy wrapped into conversion. |
| Tripadvisor/Google/Airbnb | Community/map/planning platforms solve adjacent trust and planning needs. | 8/10 | UGC and saved-list context. |
| vinhlong360 | Admin has data-quality tools but public detail lacks obvious source/freshness confidence. | 60-80% coverage | Local-only context plus no-booking boundary. |

**Tầng 2 — WHY:**

- User problem solved: Show 'nguồn / cập nhật / báo sai' near practical facts.
- Business value: improves report clicks, stale-entity fixes, trust-card impressions without adding booking/payment support.
- Research backing: NNGroup on scannability/visual hierarchy, NNGroup/Baymard on filters where relevant, Google structured data docs for SEO-related items.
- Reasoning chain: Persona P1 need -> feature makes decision easier -> measured by report clicks, stale-entity fixes, trust-card impressions -> existing evidence E13 reduces build effort -> expected outcome is higher trust or planning completion.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 4 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 4 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 4 | No paid infra required beyond current stack. |
| Competitive advantage | 4 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 4 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **20/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- agent/admin.py:675..722 - data-quality summary/review/apply/history/rollback.
- agent/admin.py:784..936 - image suggestions queue and approve/reject.
- agent/admin.py:1082 - media library endpoint.
Conclusion: 60-80% implemented; gap is productization/polish, not greenfield.
```
**Tầng 5 — UPGRADE CARD:**
```text
U-02: Source and last-verified block on detail
Primary persona: P1; Secondary: P3; Journey: RESEARCH,VISIT
Problem: Admin has data-quality tools but public detail lacks obvious source/freshness confidence.
Target: Show 'nguồn / cập nhật / báo sai' near practical facts.
Sub-features cần build:
  1. UI/control/state for the main flow — effort: M
  2. Admin/data or API linkage where needed — effort: S/M
  3. Metrics/event instrumentation — effort: S
Tối ưu cần làm:
  1. Mobile 360px and 44px tap target QA — why: VN mobile-first — how: responsive screenshot checklist
  2. SEO/a11y/performance guard — why: organic discovery and low bandwidth — how: lazy load, aria labels, structured metadata where valid
Files to modify:
  Backend: agent/admin.py:675..722 - data-quality summary/review/apply/history/rollback.
  Frontend: agent/admin.py:784..936 - image suggestions queue and approve/reject.
  Database: No migration expected
Dependencies: existing E13; constraints: no booking/payment/native app/ML/video streaming.
Risk: LOW — maintenance tax approx 1h/month.
Effort: BE 1d + FE 2d + DB 0d = 3d.
Impact: report clicks, stale-entity fixes, trust-card impressions should move within 2-4 weeks.
Vietnamese market note: Zalo/Facebook/mobile and source freshness are explicit design constraints.
Priority: P0
```
**Tầng 6 — SKIP:** Không skip. Giới hạn phạm vi để không trượt sang booking/payment, real-time messaging, ML, hoặc video hosting.

**Tầng 7 — INNOVATION:** Adapt this as a local-first feature: use Vĩnh Long season/source/community knowledge that global platforms do not maintain deeply.

### Gap G-03: Applied filter overview and no-results recovery

**Functional group:** F2 Search & Filters  
**Severity:** 🔴 Critical  
**Mapped upgrade:** U-03 (P0)

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| GetYourGuide/Klook/Viator | Commercial activity marketplaces solve this around booking confidence. | 8/10 | Trust/review/policy wrapped into conversion. |
| Tripadvisor/Google/Airbnb | Community/map/planning platforms solve adjacent trust and planning needs. | 8/10 | UGC and saved-list context. |
| vinhlong360 | Catalog filters exist but applied-filter context and recovery are thin on mobile. | 60-80% coverage | Local-only context plus no-booking boundary. |

**Tầng 2 — WHY:**

- User problem solved: Add removable filter chips, result explanation, and suggested fallback searches.
- Business value: improves filter-clear rate, zero-result exits, search refinements without adding booking/payment support.
- Research backing: NNGroup on scannability/visual hierarchy, NNGroup/Baymard on filters where relevant, Google structured data docs for SEO-related items.
- Reasoning chain: Persona P1 need -> feature makes decision easier -> measured by filter-clear rate, zero-result exits, search refinements -> existing evidence E02 reduces build effort -> expected outcome is higher trust or planning completion.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 4 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 4 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 4 | No paid infra required beyond current stack. |
| Competitive advantage | 4 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 4 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **20/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- agent/public_api.py:161 - /api/entities accepts q, type, area, month, sort, limit, offset.
- agent/public_api.py:357 - /api/search delegates to db.search_entities and count_entities_filtered.
- web-nuxt/pages/dia-diem/index.vue:88..106 - search input plus type/area FilterChips.
Conclusion: 60-80% implemented; gap is productization/polish, not greenfield.
```
**Tầng 5 — UPGRADE CARD:**
```text
U-03: Applied filter overview and no-results recovery
Primary persona: P1; Secondary: P4; Journey: DISCOVER,RESEARCH
Problem: Catalog filters exist but applied-filter context and recovery are thin on mobile.
Target: Add removable filter chips, result explanation, and suggested fallback searches.
Sub-features cần build:
  1. UI/control/state for the main flow — effort: M
  2. Admin/data or API linkage where needed — effort: S/M
  3. Metrics/event instrumentation — effort: S
Tối ưu cần làm:
  1. Mobile 360px and 44px tap target QA — why: VN mobile-first — how: responsive screenshot checklist
  2. SEO/a11y/performance guard — why: organic discovery and low bandwidth — how: lazy load, aria labels, structured metadata where valid
Files to modify:
  Backend: agent/public_api.py:161 - /api/entities accepts q, type, area, month, sort, limit, offset.
  Frontend: agent/public_api.py:357 - /api/search delegates to db.search_entities and count_entities_filtered.
  Database: No migration expected
Dependencies: existing E02; constraints: no booking/payment/native app/ML/video streaming.
Risk: LOW — maintenance tax approx 1h/month.
Effort: BE 0d + FE 2d + DB 0d = 2d.
Impact: filter-clear rate, zero-result exits, search refinements should move within 2-4 weeks.
Vietnamese market note: Zalo/Facebook/mobile and source freshness are explicit design constraints.
Priority: P0
```
**Tầng 6 — SKIP:** Không skip. Giới hạn phạm vi để không trượt sang booking/payment, real-time messaging, ML, hoặc video hosting.

**Tầng 7 — INNOVATION:** Adapt this as a local-first feature: use Vĩnh Long season/source/community knowledge that global platforms do not maintain deeply.

### Gap G-04: Review sort, filter, and photo-first mode

**Functional group:** F4 Reviews & Ratings  
**Severity:** 🔴 Critical  
**Mapped upgrade:** U-04 (P0)

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| GetYourGuide/Klook/Viator | Commercial activity marketplaces solve this around booking confidence. | 8/10 | Trust/review/policy wrapped into conversion. |
| Tripadvisor/Google/Airbnb | Community/map/planning platforms solve adjacent trust and planning needs. | 8/10 | UGC and saved-list context. |
| vinhlong360 | Reviews have form/photos/helpful/distribution but lack robust sort/filter controls. | 60-80% coverage | Local-only context plus no-booking boundary. |

**Tầng 2 — WHY:**

- User problem solved: Sort by newest/helpful/photo/star and let photo reviews lead trust decisions.
- Business value: improves review reads, photo-review opens, helpful votes without adding booking/payment support.
- Research backing: NNGroup on scannability/visual hierarchy, NNGroup/Baymard on filters where relevant, Google structured data docs for SEO-related items.
- Reasoning chain: Persona P1 need -> feature makes decision easier -> measured by review reads, photo-review opens, helpful votes -> existing evidence E05 reduces build effort -> expected outcome is higher trust or planning completion.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 4 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 4 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 4 | No paid infra required beyond current stack. |
| Competitive advantage | 4 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 4 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **20/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- web-nuxt/pages/dia-diem/[id].vue:214 - LazyEntityReviews on entity detail.
- web-nuxt/components/EntityReviews.vue:6..31 - logged-in review form with accessible star radiogroup.
- web-nuxt/components/EntityReviews.vue:154..156 - helpful toggle with auth modal fallback.
Conclusion: 60-80% implemented; gap is productization/polish, not greenfield.
```
**Tầng 5 — UPGRADE CARD:**
```text
U-04: Review sort, filter, and photo-first mode
Primary persona: P1; Secondary: P2; Journey: RESEARCH,SHARE
Problem: Reviews have form/photos/helpful/distribution but lack robust sort/filter controls.
Target: Sort by newest/helpful/photo/star and let photo reviews lead trust decisions.
Sub-features cần build:
  1. UI/control/state for the main flow — effort: M
  2. Admin/data or API linkage where needed — effort: S/M
  3. Metrics/event instrumentation — effort: S
Tối ưu cần làm:
  1. Mobile 360px and 44px tap target QA — why: VN mobile-first — how: responsive screenshot checklist
  2. SEO/a11y/performance guard — why: organic discovery and low bandwidth — how: lazy load, aria labels, structured metadata where valid
Files to modify:
  Backend: web-nuxt/pages/dia-diem/[id].vue:214 - LazyEntityReviews on entity detail.
  Frontend: web-nuxt/components/EntityReviews.vue:6..31 - logged-in review form with accessible star radiogroup.
  Database: No migration expected
Dependencies: existing E05; constraints: no booking/payment/native app/ML/video streaming.
Risk: MED — maintenance tax approx 3h/month.
Effort: BE 1.5d + FE 2.5d + DB 0d = 4.0d.
Impact: review reads, photo-review opens, helpful votes should move within 2-4 weeks.
Vietnamese market note: Zalo/Facebook/mobile and source freshness are explicit design constraints.
Priority: P0
```
**Tầng 6 — SKIP:** Không skip. Giới hạn phạm vi để không trượt sang booking/payment, real-time messaging, ML, hoặc video hosting.

**Tầng 7 — INNOVATION:** Adapt this as a local-first feature: use Vĩnh Long season/source/community knowledge that global platforms do not maintain deeply.

### Gap G-05: Itinerary print/export/share polish

**Functional group:** F10 Itinerary Planning  
**Severity:** 🔴 Critical  
**Mapped upgrade:** U-05 (P0)

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| GetYourGuide/Klook/Viator | Commercial activity marketplaces solve this around booking confidence. | 8/10 | Trust/review/policy wrapped into conversion. |
| Tripadvisor/Google/Airbnb | Community/map/planning platforms solve adjacent trust and planning needs. | 8/10 | UGC and saved-list context. |
| vinhlong360 | Plans publish/share but public shared page is sparse and no print/export exists. | 60-80% coverage | Local-only context plus no-booking boundary. |

**Tầng 2 — WHY:**

- User problem solved: Add print stylesheet, copyable Zalo text, and compact offline route summary.
- Business value: improves plans shared, print/export clicks, shared-plan return visits without adding booking/payment support.
- Research backing: NNGroup on scannability/visual hierarchy, NNGroup/Baymard on filters where relevant, Google structured data docs for SEO-related items.
- Reasoning chain: Persona P5 need -> feature makes decision easier -> measured by plans shared, print/export clicks, shared-plan return visits -> existing evidence E09 reduces build effort -> expected outcome is higher trust or planning completion.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 4 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 4 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 4 | No paid infra required beyond current stack. |
| Competitive advantage | 4 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 4 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **20/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- agent/saved.py:24..114 - /api/saved get/post/delete/merge.
- agent/plans.py:21..153 - /api/my-plans get/post/delete/merge/publish.
- agent/plans.py:157..190 - /api/shared-plans list/detail for public plans.
Conclusion: 60-80% implemented; gap is productization/polish, not greenfield.
```
**Tầng 5 — UPGRADE CARD:**
```text
U-05: Itinerary print/export/share polish
Primary persona: P5; Secondary: P1; Journey: PLAN,VISIT
Problem: Plans publish/share but public shared page is sparse and no print/export exists.
Target: Add print stylesheet, copyable Zalo text, and compact offline route summary.
Sub-features cần build:
  1. UI/control/state for the main flow — effort: M
  2. Admin/data or API linkage where needed — effort: S/M
  3. Metrics/event instrumentation — effort: S
Tối ưu cần làm:
  1. Mobile 360px and 44px tap target QA — why: VN mobile-first — how: responsive screenshot checklist
  2. SEO/a11y/performance guard — why: organic discovery and low bandwidth — how: lazy load, aria labels, structured metadata where valid
Files to modify:
  Backend: agent/saved.py:24..114 - /api/saved get/post/delete/merge.
  Frontend: agent/plans.py:21..153 - /api/my-plans get/post/delete/merge/publish.
  Database: No migration expected
Dependencies: existing E09; constraints: no booking/payment/native app/ML/video streaming.
Risk: LOW — maintenance tax approx 1h/month.
Effort: BE 0d + FE 2.5d + DB 0d = 2.5d.
Impact: plans shared, print/export clicks, shared-plan return visits should move within 2-4 weeks.
Vietnamese market note: Zalo/Facebook/mobile and source freshness are explicit design constraints.
Priority: P0
```
**Tầng 6 — SKIP:** Không skip. Giới hạn phạm vi để không trượt sang booking/payment, real-time messaging, ML, hoặc video hosting.

**Tầng 7 — INNOVATION:** Adapt this as a local-first feature: use Vĩnh Long season/source/community knowledge that global platforms do not maintain deeply.

### Gap G-06: Map list-plus-map synchronized discovery

**Functional group:** F8 Map & Navigation  
**Severity:** 🔴 Critical  
**Mapped upgrade:** U-06 (P0)

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| GetYourGuide/Klook/Viator | Commercial activity marketplaces solve this around booking confidence. | 8/10 | Trust/review/policy wrapped into conversion. |
| Tripadvisor/Google/Airbnb | Community/map/planning platforms solve adjacent trust and planning needs. | 8/10 | UGC and saved-list context. |
| vinhlong360 | Map pins/clusters exist; list context and selected pin state are limited. | 60-80% coverage | Local-only context plus no-booking boundary. |

**Tầng 2 — WHY:**

- User problem solved: Add mobile bottom list, selected entity preview, and filter-count feedback.
- Business value: improves map interactions/session, pin-to-detail CTR without adding booking/payment support.
- Research backing: NNGroup on scannability/visual hierarchy, NNGroup/Baymard on filters where relevant, Google structured data docs for SEO-related items.
- Reasoning chain: Persona P1 need -> feature makes decision easier -> measured by map interactions/session, pin-to-detail CTR -> existing evidence E03 reduces build effort -> expected outcome is higher trust or planning completion.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 4 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 4 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 4 | No paid infra required beyond current stack. |
| Competitive advantage | 4 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 4 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **20/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- agent/public_api.py:720..772 - /api/map-pins with type/area cache and ratings in pin payload.
- web-nuxt/pages/ban-do.vue:17..38 - type filters and map control panel.
- web-nuxt/pages/ban-do.vue:245..265 - MapLibre geojson source, clusters, unclustered pins.
Conclusion: 60-80% implemented; gap is productization/polish, not greenfield.
```
**Tầng 5 — UPGRADE CARD:**
```text
U-06: Map list-plus-map synchronized discovery
Primary persona: P1; Secondary: P5; Journey: DISCOVER,PLAN,VISIT
Problem: Map pins/clusters exist; list context and selected pin state are limited.
Target: Add mobile bottom list, selected entity preview, and filter-count feedback.
Sub-features cần build:
  1. UI/control/state for the main flow — effort: M
  2. Admin/data or API linkage where needed — effort: S/M
  3. Metrics/event instrumentation — effort: S
Tối ưu cần làm:
  1. Mobile 360px and 44px tap target QA — why: VN mobile-first — how: responsive screenshot checklist
  2. SEO/a11y/performance guard — why: organic discovery and low bandwidth — how: lazy load, aria labels, structured metadata where valid
Files to modify:
  Backend: agent/public_api.py:720..772 - /api/map-pins with type/area cache and ratings in pin payload.
  Frontend: web-nuxt/pages/ban-do.vue:17..38 - type filters and map control panel.
  Database: No migration expected
Dependencies: existing E03; constraints: no booking/payment/native app/ML/video streaming.
Risk: MED — maintenance tax approx 3h/month.
Effort: BE 0.5d + FE 2.5d + DB 0d = 3.0d.
Impact: map interactions/session, pin-to-detail CTR should move within 2-4 weeks.
Vietnamese market note: Zalo/Facebook/mobile and source freshness are explicit design constraints.
Priority: P0
```
**Tầng 6 — SKIP:** Không skip. Giới hạn phạm vi để không trượt sang booking/payment, real-time messaging, ML, hoặc video hosting.

**Tầng 7 — INNOVATION:** Adapt this as a local-first feature: use Vĩnh Long season/source/community knowledge that global platforms do not maintain deeply.

### Gap G-07: Know-before-you-go completion pass

**Functional group:** F3 Entity Detail  
**Severity:** 🔴 Critical  
**Mapped upgrade:** U-07 (P0)

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| GetYourGuide/Klook/Viator | Commercial activity marketplaces solve this around booking confidence. | 8/10 | Trust/review/policy wrapped into conversion. |
| Tripadvisor/Google/Airbnb | Community/map/planning platforms solve adjacent trust and planning needs. | 8/10 | UGC and saved-list context. |
| vinhlong360 | Detail page has practical sections but not consistently complete for hours, parking, age, weather, peak days. | 60-80% coverage | Local-only context plus no-booking boundary. |

**Tầng 2 — WHY:**

- User problem solved: Standardize short practical facts with admin prompts for missing fields.
- Business value: improves KBYG coverage %, contact click rate after KBYG without adding booking/payment support.
- Research backing: NNGroup on scannability/visual hierarchy, NNGroup/Baymard on filters where relevant, Google structured data docs for SEO-related items.
- Reasoning chain: Persona P1 need -> feature makes decision easier -> measured by KBYG coverage %, contact click rate after KBYG -> existing evidence E04 reduces build effort -> expected outcome is higher trust or planning completion.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 4 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 4 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 4 | No paid infra required beyond current stack. |
| Competitive advantage | 4 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 4 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **20/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- web-nuxt/pages/dia-diem/[id].vue:18..71 - hero image, thumbnails, image credit, PhotoGallery.
- web-nuxt/components/PhotoGallery.vue:39..107 - placeholder, single image, desktop grid, mobile carousel, photo count.
- web-nuxt/pages/dia-diem/[id].vue:565..615 - cover image, credit, lightbox navigation and adjacent preload.
Conclusion: 60-80% implemented; gap is productization/polish, not greenfield.
```
**Tầng 5 — UPGRADE CARD:**
```text
U-07: Know-before-you-go completion pass
Primary persona: P1; Secondary: P3; Journey: RESEARCH,VISIT
Problem: Detail page has practical sections but not consistently complete for hours, parking, age, weather, peak days.
Target: Standardize short practical facts with admin prompts for missing fields.
Sub-features cần build:
  1. UI/control/state for the main flow — effort: M
  2. Admin/data or API linkage where needed — effort: S/M
  3. Metrics/event instrumentation — effort: S
Tối ưu cần làm:
  1. Mobile 360px and 44px tap target QA — why: VN mobile-first — how: responsive screenshot checklist
  2. SEO/a11y/performance guard — why: organic discovery and low bandwidth — how: lazy load, aria labels, structured metadata where valid
Files to modify:
  Backend: web-nuxt/pages/dia-diem/[id].vue:18..71 - hero image, thumbnails, image credit, PhotoGallery.
  Frontend: web-nuxt/components/PhotoGallery.vue:39..107 - placeholder, single image, desktop grid, mobile carousel, photo count.
  Database: No migration expected
Dependencies: existing E04; constraints: no booking/payment/native app/ML/video streaming.
Risk: LOW — maintenance tax approx 1h/month.
Effort: BE 0.5d + FE 1.5d + DB 0d = 2.0d.
Impact: KBYG coverage %, contact click rate after KBYG should move within 2-4 weeks.
Vietnamese market note: Zalo/Facebook/mobile and source freshness are explicit design constraints.
Priority: P0
```
**Tầng 6 — SKIP:** Không skip. Giới hạn phạm vi để không trượt sang booking/payment, real-time messaging, ML, hoặc video hosting.

**Tầng 7 — INNOVATION:** Adapt this as a local-first feature: use Vĩnh Long season/source/community knowledge that global platforms do not maintain deeply.

### Gap G-08: Public correction/report-info CTA

**Functional group:** F15 Data Quality & Freshness  
**Severity:** 🔴 Critical  
**Mapped upgrade:** U-08 (P0)

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| GetYourGuide/Klook/Viator | Commercial activity marketplaces solve this around booking confidence. | 8/10 | Trust/review/policy wrapped into conversion. |
| Tripadvisor/Google/Airbnb | Community/map/planning platforms solve adjacent trust and planning needs. | 8/10 | UGC and saved-list context. |
| vinhlong360 | Public reporting exists but is not attached to every practical fact. | 60-80% coverage | Local-only context plus no-booking boundary. |

**Tầng 2 — WHY:**

- User problem solved: Allow 'báo sai thông tin này' for phone/hours/address/source.
- Business value: improves reports/entity, correction SLA without adding booking/payment support.
- Research backing: NNGroup on scannability/visual hierarchy, NNGroup/Baymard on filters where relevant, Google structured data docs for SEO-related items.
- Reasoning chain: Persona P1 need -> feature makes decision easier -> measured by reports/entity, correction SLA -> existing evidence E13 reduces build effort -> expected outcome is higher trust or planning completion.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 4 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 4 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 4 | No paid infra required beyond current stack. |
| Competitive advantage | 4 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 4 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **20/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- agent/admin.py:675..722 - data-quality summary/review/apply/history/rollback.
- agent/admin.py:784..936 - image suggestions queue and approve/reject.
- agent/admin.py:1082 - media library endpoint.
Conclusion: 60-80% implemented; gap is productization/polish, not greenfield.
```
**Tầng 5 — UPGRADE CARD:**
```text
U-08: Public correction/report-info CTA
Primary persona: P1; Secondary: P2; Journey: RESEARCH,SHARE
Problem: Public reporting exists but is not attached to every practical fact.
Target: Allow 'báo sai thông tin này' for phone/hours/address/source.
Sub-features cần build:
  1. UI/control/state for the main flow — effort: M
  2. Admin/data or API linkage where needed — effort: S/M
  3. Metrics/event instrumentation — effort: S
Tối ưu cần làm:
  1. Mobile 360px and 44px tap target QA — why: VN mobile-first — how: responsive screenshot checklist
  2. SEO/a11y/performance guard — why: organic discovery and low bandwidth — how: lazy load, aria labels, structured metadata where valid
Files to modify:
  Backend: agent/admin.py:675..722 - data-quality summary/review/apply/history/rollback.
  Frontend: agent/admin.py:784..936 - image suggestions queue and approve/reject.
  Database: No migration expected
Dependencies: existing E13; constraints: no booking/payment/native app/ML/video streaming.
Risk: LOW — maintenance tax approx 1h/month.
Effort: BE 1d + FE 1.5d + DB 0d = 2.5d.
Impact: reports/entity, correction SLA should move within 2-4 weeks.
Vietnamese market note: Zalo/Facebook/mobile and source freshness are explicit design constraints.
Priority: P0
```
**Tầng 6 — SKIP:** Không skip. Giới hạn phạm vi để không trượt sang booking/payment, real-time messaging, ML, hoặc video hosting.

**Tầng 7 — INNOVATION:** Adapt this as a local-first feature: use Vĩnh Long season/source/community knowledge that global platforms do not maintain deeply.

### Gap G-09: Entity Q&A surfaced in detail

**Functional group:** F5 Community & Reputation  
**Severity:** 🔴 Critical  
**Mapped upgrade:** U-09 (P0)

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| GetYourGuide/Klook/Viator | Commercial activity marketplaces solve this around booking confidence. | 8/10 | Trust/review/policy wrapped into conversion. |
| Tripadvisor/Google/Airbnb | Community/map/planning platforms solve adjacent trust and planning needs. | 8/10 | UGC and saved-list context. |
| vinhlong360 | Question post type and best answer exist, but detail pages should surface entity-specific unresolved Q&A. | 60-80% coverage | Local-only context plus no-booking boundary. |

**Tầng 2 — WHY:**

- User problem solved: Add Q&A tab/rail with accepted answer, ask-local CTA, and local contributor prompt.
- Business value: improves questions answered, accepted-answer rate without adding booking/payment support.
- Research backing: NNGroup on scannability/visual hierarchy, NNGroup/Baymard on filters where relevant, Google structured data docs for SEO-related items.
- Reasoning chain: Persona P1 need -> feature makes decision easier -> measured by questions answered, accepted-answer rate -> existing evidence E06 reduces build effort -> expected outcome is higher trust or planning completion.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 4 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 4 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 4 | No paid infra required beyond current stack. |
| Competitive advantage | 4 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 4 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **20/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- agent/social.py:68 - POST_TYPES = review/share/recommend/question.
- agent/social.py:266 - POST /api/posts.
- agent/social.py:1071..1238 - threaded comments create/edit/delete.
Conclusion: 60-80% implemented; gap is productization/polish, not greenfield.
```
**Tầng 5 — UPGRADE CARD:**
```text
U-09: Entity Q&A surfaced in detail
Primary persona: P1; Secondary: P2; Journey: RESEARCH,SHARE
Problem: Question post type and best answer exist, but detail pages should surface entity-specific unresolved Q&A.
Target: Add Q&A tab/rail with accepted answer, ask-local CTA, and local contributor prompt.
Sub-features cần build:
  1. UI/control/state for the main flow — effort: M
  2. Admin/data or API linkage where needed — effort: S/M
  3. Metrics/event instrumentation — effort: S
Tối ưu cần làm:
  1. Mobile 360px and 44px tap target QA — why: VN mobile-first — how: responsive screenshot checklist
  2. SEO/a11y/performance guard — why: organic discovery and low bandwidth — how: lazy load, aria labels, structured metadata where valid
Files to modify:
  Backend: agent/social.py:68 - POST_TYPES = review/share/recommend/question.
  Frontend: agent/social.py:266 - POST /api/posts.
  Database: No migration expected
Dependencies: existing E06; constraints: no booking/payment/native app/ML/video streaming.
Risk: LOW — maintenance tax approx 1h/month.
Effort: BE 1d + FE 2d + DB 0d = 3d.
Impact: questions answered, accepted-answer rate should move within 2-4 weeks.
Vietnamese market note: Zalo/Facebook/mobile and source freshness are explicit design constraints.
Priority: P0
```
**Tầng 6 — SKIP:** Không skip. Giới hạn phạm vi để không trượt sang booking/payment, real-time messaging, ML, hoặc video hosting.

**Tầng 7 — INNOVATION:** Adapt this as a local-first feature: use Vĩnh Long season/source/community knowledge that global platforms do not maintain deeply.

### Gap G-10: Image attribution and contribution prompts

**Functional group:** F6 UGC Creation & Moderation  
**Severity:** 🔴 Critical  
**Mapped upgrade:** U-10 (P0)

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| GetYourGuide/Klook/Viator | Commercial activity marketplaces solve this around booking confidence. | 8/10 | Trust/review/policy wrapped into conversion. |
| Tripadvisor/Google/Airbnb | Community/map/planning platforms solve adjacent trust and planning needs. | 8/10 | UGC and saved-list context. |
| vinhlong360 | Admin image credits exist and UGC images exist, but attribution/contribution prompts are inconsistent. | 60-80% coverage | Local-only context plus no-booking boundary. |

**Tầng 2 — WHY:**

- User problem solved: Show credit in galleries and prompt locals for missing real photos.
- Business value: improves photo coverage %, credited-photo share without adding booking/payment support.
- Research backing: NNGroup on scannability/visual hierarchy, NNGroup/Baymard on filters where relevant, Google structured data docs for SEO-related items.
- Reasoning chain: Persona P2 need -> feature makes decision easier -> measured by photo coverage %, credited-photo share -> existing evidence E04 reduces build effort -> expected outcome is higher trust or planning completion.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 4 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 4 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 4 | No paid infra required beyond current stack. |
| Competitive advantage | 4 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 4 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **20/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- web-nuxt/pages/dia-diem/[id].vue:18..71 - hero image, thumbnails, image credit, PhotoGallery.
- web-nuxt/components/PhotoGallery.vue:39..107 - placeholder, single image, desktop grid, mobile carousel, photo count.
- web-nuxt/pages/dia-diem/[id].vue:565..615 - cover image, credit, lightbox navigation and adjacent preload.
Conclusion: 60-80% implemented; gap is productization/polish, not greenfield.
```
**Tầng 5 — UPGRADE CARD:**
```text
U-10: Image attribution and contribution prompts
Primary persona: P2; Secondary: P3; Journey: SHARE,RETURN
Problem: Admin image credits exist and UGC images exist, but attribution/contribution prompts are inconsistent.
Target: Show credit in galleries and prompt locals for missing real photos.
Sub-features cần build:
  1. UI/control/state for the main flow — effort: M
  2. Admin/data or API linkage where needed — effort: S/M
  3. Metrics/event instrumentation — effort: S
Tối ưu cần làm:
  1. Mobile 360px and 44px tap target QA — why: VN mobile-first — how: responsive screenshot checklist
  2. SEO/a11y/performance guard — why: organic discovery and low bandwidth — how: lazy load, aria labels, structured metadata where valid
Files to modify:
  Backend: web-nuxt/pages/dia-diem/[id].vue:18..71 - hero image, thumbnails, image credit, PhotoGallery.
  Frontend: web-nuxt/components/PhotoGallery.vue:39..107 - placeholder, single image, desktop grid, mobile carousel, photo count.
  Database: No migration expected
Dependencies: existing E04; constraints: no booking/payment/native app/ML/video streaming.
Risk: LOW — maintenance tax approx 1h/month.
Effort: BE 0.5d + FE 2d + DB 0d = 2.5d.
Impact: photo coverage %, credited-photo share should move within 2-4 weeks.
Vietnamese market note: Zalo/Facebook/mobile and source freshness are explicit design constraints.
Priority: P0
```
**Tầng 6 — SKIP:** Không skip. Giới hạn phạm vi để không trượt sang booking/payment, real-time messaging, ML, hoặc video hosting.

**Tầng 7 — INNOVATION:** Adapt this as a local-first feature: use Vĩnh Long season/source/community knowledge that global platforms do not maintain deeply.

### Gap G-11: Owner/admin response to reviews

**Functional group:** F4 Reviews & Ratings  
**Severity:** 🟡 Important  
**Mapped upgrade:** U-11 (P1)

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| GetYourGuide/Klook/Viator | Commercial activity marketplaces solve this around booking confidence. | 8/10 | Trust/review/policy wrapped into conversion. |
| Tripadvisor/Google/Airbnb | Community/map/planning platforms solve adjacent trust and planning needs. | 8/10 | UGC and saved-list context. |
| vinhlong360 | Reviews lack an official response object even though moderation/admin exists. | 60-80% coverage | Local-only context plus no-booking boundary. |

**Tầng 2 — WHY:**

- User problem solved: Let admin/verified entity owner respond once per review with moderation audit.
- Business value: improves response coverage, negative-review follow-up without adding booking/payment support.
- Research backing: NNGroup on scannability/visual hierarchy, NNGroup/Baymard on filters where relevant, Google structured data docs for SEO-related items.
- Reasoning chain: Persona P3 need -> feature makes decision easier -> measured by response coverage, negative-review follow-up -> existing evidence E05 reduces build effort -> expected outcome is higher trust or planning completion.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 4 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 4 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 4 | No paid infra required beyond current stack. |
| Competitive advantage | 4 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 4 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **20/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- web-nuxt/pages/dia-diem/[id].vue:214 - LazyEntityReviews on entity detail.
- web-nuxt/components/EntityReviews.vue:6..31 - logged-in review form with accessible star radiogroup.
- web-nuxt/components/EntityReviews.vue:154..156 - helpful toggle with auth modal fallback.
Conclusion: 60-80% implemented; gap is productization/polish, not greenfield.
```
**Tầng 5 — UPGRADE CARD:**
```text
U-11: Owner/admin response to reviews
Primary persona: P3; Secondary: P2; Journey: RESEARCH,SHARE
Problem: Reviews lack an official response object even though moderation/admin exists.
Target: Let admin/verified entity owner respond once per review with moderation audit.
Sub-features cần build:
  1. UI/control/state for the main flow — effort: M
  2. Admin/data or API linkage where needed — effort: S/M
  3. Metrics/event instrumentation — effort: S
Tối ưu cần làm:
  1. Mobile 360px and 44px tap target QA — why: VN mobile-first — how: responsive screenshot checklist
  2. SEO/a11y/performance guard — why: organic discovery and low bandwidth — how: lazy load, aria labels, structured metadata where valid
Files to modify:
  Backend: web-nuxt/pages/dia-diem/[id].vue:214 - LazyEntityReviews on entity detail.
  Frontend: web-nuxt/components/EntityReviews.vue:6..31 - logged-in review form with accessible star radiogroup.
  Database: Migration likely
Dependencies: existing E05; constraints: no booking/payment/native app/ML/video streaming.
Risk: MED — maintenance tax approx 3h/month.
Effort: BE 2d + FE 2d + DB 0.5d = 4.5d.
Impact: response coverage, negative-review follow-up should move within 2-4 weeks.
Vietnamese market note: Zalo/Facebook/mobile and source freshness are explicit design constraints.
Priority: P1
```
**Tầng 6 — SKIP:** Không skip. Giới hạn phạm vi để không trượt sang booking/payment, real-time messaging, ML, hoặc video hosting.

**Tầng 7 — INNOVATION:** Adapt this as a local-first feature: use Vĩnh Long season/source/community knowledge that global platforms do not maintain deeply.

### Gap G-12: Review structured data from real UGC

**Functional group:** F11 Content Guides & SEO  
**Severity:** 🟡 Important  
**Mapped upgrade:** U-12 (P1)

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| GetYourGuide/Klook/Viator | Commercial activity marketplaces solve this around booking confidence. | 8/10 | Trust/review/policy wrapped into conversion. |
| Tripadvisor/Google/Airbnb | Community/map/planning platforms solve adjacent trust and planning needs. | 8/10 | UGC and saved-list context. |
| vinhlong360 | JSON-LD exists; ensure aggregate ratings use first-party UGC, not copied Google reviews. | 60-80% coverage | Local-only context plus no-booking boundary. |

**Tầng 2 — WHY:**

- User problem solved: Emit compliant AggregateRating only where eligible and hide when data is thin.
- Business value: improves rich-result eligibility, schema validation without adding booking/payment support.
- Research backing: NNGroup on scannability/visual hierarchy, NNGroup/Baymard on filters where relevant, Google structured data docs for SEO-related items.
- Reasoning chain: Persona P1 need -> feature makes decision easier -> measured by rich-result eligibility, schema validation -> existing evidence E11 reduces build effort -> expected outcome is higher trust or planning completion.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 4 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 4 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 4 | No paid infra required beyond current stack. |
| Competitive advantage | 4 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 4 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **20/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- agent/seo.py:404..423 - entity JSON-LD with type mapping and ImageObject support.
- agent/seo.py:696..986 - site/area/itinerary/entity/collection JSON-LD endpoints.
- agent/seo.py:1007..1148 - sitemap.xml, media sitemap, sitemap index, robots.txt.
Conclusion: 60-80% implemented; gap is productization/polish, not greenfield.
```
**Tầng 5 — UPGRADE CARD:**
```text
U-12: Review structured data from real UGC
Primary persona: P1; Secondary: P4; Journey: RESEARCH
Problem: JSON-LD exists; ensure aggregate ratings use first-party UGC, not copied Google reviews.
Target: Emit compliant AggregateRating only where eligible and hide when data is thin.
Sub-features cần build:
  1. UI/control/state for the main flow — effort: M
  2. Admin/data or API linkage where needed — effort: S/M
  3. Metrics/event instrumentation — effort: S
Tối ưu cần làm:
  1. Mobile 360px and 44px tap target QA — why: VN mobile-first — how: responsive screenshot checklist
  2. SEO/a11y/performance guard — why: organic discovery and low bandwidth — how: lazy load, aria labels, structured metadata where valid
Files to modify:
  Backend: agent/seo.py:404..423 - entity JSON-LD with type mapping and ImageObject support.
  Frontend: agent/seo.py:696..986 - site/area/itinerary/entity/collection JSON-LD endpoints.
  Database: No migration expected
Dependencies: existing E11; constraints: no booking/payment/native app/ML/video streaming.
Risk: MED — maintenance tax approx 3h/month.
Effort: BE 1d + FE 1d + DB 0d = 2d.
Impact: rich-result eligibility, schema validation should move within 2-4 weeks.
Vietnamese market note: Zalo/Facebook/mobile and source freshness are explicit design constraints.
Priority: P1
```
**Tầng 6 — SKIP:** Không skip. Giới hạn phạm vi để không trượt sang booking/payment, real-time messaging, ML, hoặc video hosting.

**Tầng 7 — INNOVATION:** Adapt this as a local-first feature: use Vĩnh Long season/source/community knowledge that global platforms do not maintain deeply.

### Gap G-13: Seasonal trip packs before peaks

**Functional group:** F1 Discovery IA  
**Severity:** 🟡 Important  
**Mapped upgrade:** U-13 (P1)

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| GetYourGuide/Klook/Viator | Commercial activity marketplaces solve this around booking confidence. | 8/10 | Trust/review/policy wrapped into conversion. |
| Tripadvisor/Google/Airbnb | Community/map/planning platforms solve adjacent trust and planning needs. | 8/10 | UGC and saved-list context. |
| vinhlong360 | Seasonal browse exists but not packaged as pre-peak campaign pages. | 60-80% coverage | Local-only context plus no-booking boundary. |

**Tầng 2 — WHY:**

- User problem solved: Create Tet/summer/30-4/2-9 packs with places, food, route, contact notes.
- Business value: improves season page sessions, saves from season pages without adding booking/payment support.
- Research backing: NNGroup on scannability/visual hierarchy, NNGroup/Baymard on filters where relevant, Google structured data docs for SEO-related items.
- Reasoning chain: Persona P1 need -> feature makes decision easier -> measured by season page sessions, saves from season pages -> existing evidence E02 reduces build effort -> expected outcome is higher trust or planning completion.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 4 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 4 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 4 | No paid infra required beyond current stack. |
| Competitive advantage | 4 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 4 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **20/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- agent/public_api.py:161 - /api/entities accepts q, type, area, month, sort, limit, offset.
- agent/public_api.py:357 - /api/search delegates to db.search_entities and count_entities_filtered.
- web-nuxt/pages/dia-diem/index.vue:88..106 - search input plus type/area FilterChips.
Conclusion: 60-80% implemented; gap is productization/polish, not greenfield.
```
**Tầng 5 — UPGRADE CARD:**
```text
U-13: Seasonal trip packs before peaks
Primary persona: P1; Secondary: P4; Journey: DISCOVER,PLAN
Problem: Seasonal browse exists but not packaged as pre-peak campaign pages.
Target: Create Tet/summer/30-4/2-9 packs with places, food, route, contact notes.
Sub-features cần build:
  1. UI/control/state for the main flow — effort: M
  2. Admin/data or API linkage where needed — effort: S/M
  3. Metrics/event instrumentation — effort: S
Tối ưu cần làm:
  1. Mobile 360px and 44px tap target QA — why: VN mobile-first — how: responsive screenshot checklist
  2. SEO/a11y/performance guard — why: organic discovery and low bandwidth — how: lazy load, aria labels, structured metadata where valid
Files to modify:
  Backend: agent/public_api.py:161 - /api/entities accepts q, type, area, month, sort, limit, offset.
  Frontend: agent/public_api.py:357 - /api/search delegates to db.search_entities and count_entities_filtered.
  Database: No migration expected
Dependencies: existing E02; constraints: no booking/payment/native app/ML/video streaming.
Risk: LOW — maintenance tax approx 1h/month.
Effort: BE 0.5d + FE 3d + DB 0d = 3.5d.
Impact: season page sessions, saves from season pages should move within 2-4 weeks.
Vietnamese market note: Zalo/Facebook/mobile and source freshness are explicit design constraints.
Priority: P1
```
**Tầng 6 — SKIP:** Không skip. Giới hạn phạm vi để không trượt sang booking/payment, real-time messaging, ML, hoặc video hosting.

**Tầng 7 — INNOVATION:** Adapt this as a local-first feature: use Vĩnh Long season/source/community knowledge that global platforms do not maintain deeply.

### Gap G-14: Region landing pages with mini-itinerary

**Functional group:** F1 Discovery IA  
**Severity:** 🟡 Important  
**Mapped upgrade:** U-14 (P1)

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| GetYourGuide/Klook/Viator | Commercial activity marketplaces solve this around booking confidence. | 8/10 | Trust/review/policy wrapped into conversion. |
| Tripadvisor/Google/Airbnb | Community/map/planning platforms solve adjacent trust and planning needs. | 8/10 | UGC and saved-list context. |
| vinhlong360 | Area pages exist but can better answer 'đi đâu trong 1 ngày ở khu này'. | 60-80% coverage | Local-only context plus no-booking boundary. |

**Tầng 2 — WHY:**

- User problem solved: Add 3-stop mini routes, local food, contact-ready POIs.
- Business value: improves area page depth, itinerary adds from area without adding booking/payment support.
- Research backing: NNGroup on scannability/visual hierarchy, NNGroup/Baymard on filters where relevant, Google structured data docs for SEO-related items.
- Reasoning chain: Persona P1 need -> feature makes decision easier -> measured by area page depth, itinerary adds from area -> existing evidence E02 reduces build effort -> expected outcome is higher trust or planning completion.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 4 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 4 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 4 | No paid infra required beyond current stack. |
| Competitive advantage | 4 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 4 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **20/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- agent/public_api.py:161 - /api/entities accepts q, type, area, month, sort, limit, offset.
- agent/public_api.py:357 - /api/search delegates to db.search_entities and count_entities_filtered.
- web-nuxt/pages/dia-diem/index.vue:88..106 - search input plus type/area FilterChips.
Conclusion: 60-80% implemented; gap is productization/polish, not greenfield.
```
**Tầng 5 — UPGRADE CARD:**
```text
U-14: Region landing pages with mini-itinerary
Primary persona: P1; Secondary: P5; Journey: DISCOVER,PLAN
Problem: Area pages exist but can better answer 'đi đâu trong 1 ngày ở khu này'.
Target: Add 3-stop mini routes, local food, contact-ready POIs.
Sub-features cần build:
  1. UI/control/state for the main flow — effort: M
  2. Admin/data or API linkage where needed — effort: S/M
  3. Metrics/event instrumentation — effort: S
Tối ưu cần làm:
  1. Mobile 360px and 44px tap target QA — why: VN mobile-first — how: responsive screenshot checklist
  2. SEO/a11y/performance guard — why: organic discovery and low bandwidth — how: lazy load, aria labels, structured metadata where valid
Files to modify:
  Backend: agent/public_api.py:161 - /api/entities accepts q, type, area, month, sort, limit, offset.
  Frontend: agent/public_api.py:357 - /api/search delegates to db.search_entities and count_entities_filtered.
  Database: No migration expected
Dependencies: existing E02; constraints: no booking/payment/native app/ML/video streaming.
Risk: LOW — maintenance tax approx 1h/month.
Effort: BE 0.5d + FE 3d + DB 0d = 3.5d.
Impact: area page depth, itinerary adds from area should move within 2-4 weeks.
Vietnamese market note: Zalo/Facebook/mobile and source freshness are explicit design constraints.
Priority: P1
```
**Tầng 6 — SKIP:** Không skip. Giới hạn phạm vi để không trượt sang booking/payment, real-time messaging, ML, hoặc video hosting.

**Tầng 7 — INNOVATION:** Adapt this as a local-first feature: use Vĩnh Long season/source/community knowledge that global platforms do not maintain deeply.

### Gap G-15: What's-new return feed

**Functional group:** F9 Personalization & Return  
**Severity:** 🟡 Important  
**Mapped upgrade:** U-15 (P1)

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| GetYourGuide/Klook/Viator | Commercial activity marketplaces solve this around booking confidence. | 8/10 | Trust/review/policy wrapped into conversion. |
| Tripadvisor/Google/Airbnb | Community/map/planning platforms solve adjacent trust and planning needs. | 8/10 | UGC and saved-list context. |
| vinhlong360 | Recently viewed and feeds exist, but return users need 'mới cập nhật' and 'review mới'. | 60-80% coverage | Local-only context plus no-booking boundary. |

**Tầng 2 — WHY:**

- User problem solved: Show new reviews/entities/events since last visit with local storage fallback.
- Business value: improves return sessions, feed clicks without adding booking/payment support.
- Research backing: NNGroup on scannability/visual hierarchy, NNGroup/Baymard on filters where relevant, Google structured data docs for SEO-related items.
- Reasoning chain: Persona P4 need -> feature makes decision easier -> measured by return sessions, feed clicks -> existing evidence E06 reduces build effort -> expected outcome is higher trust or planning completion.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 4 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 4 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 4 | No paid infra required beyond current stack. |
| Competitive advantage | 4 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 4 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **20/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- agent/social.py:68 - POST_TYPES = review/share/recommend/question.
- agent/social.py:266 - POST /api/posts.
- agent/social.py:1071..1238 - threaded comments create/edit/delete.
Conclusion: 60-80% implemented; gap is productization/polish, not greenfield.
```
**Tầng 5 — UPGRADE CARD:**
```text
U-15: What's-new return feed
Primary persona: P4; Secondary: P2; Journey: RETURN
Problem: Recently viewed and feeds exist, but return users need 'mới cập nhật' and 'review mới'.
Target: Show new reviews/entities/events since last visit with local storage fallback.
Sub-features cần build:
  1. UI/control/state for the main flow — effort: M
  2. Admin/data or API linkage where needed — effort: S/M
  3. Metrics/event instrumentation — effort: S
Tối ưu cần làm:
  1. Mobile 360px and 44px tap target QA — why: VN mobile-first — how: responsive screenshot checklist
  2. SEO/a11y/performance guard — why: organic discovery and low bandwidth — how: lazy load, aria labels, structured metadata where valid
Files to modify:
  Backend: agent/social.py:68 - POST_TYPES = review/share/recommend/question.
  Frontend: agent/social.py:266 - POST /api/posts.
  Database: No migration expected
Dependencies: existing E06; constraints: no booking/payment/native app/ML/video streaming.
Risk: LOW — maintenance tax approx 1h/month.
Effort: BE 1d + FE 2d + DB 0d = 3d.
Impact: return sessions, feed clicks should move within 2-4 weeks.
Vietnamese market note: Zalo/Facebook/mobile and source freshness are explicit design constraints.
Priority: P1
```
**Tầng 6 — SKIP:** Không skip. Giới hạn phạm vi để không trượt sang booking/payment, real-time messaging, ML, hoặc video hosting.

**Tầng 7 — INNOVATION:** Adapt this as a local-first feature: use Vĩnh Long season/source/community knowledge that global platforms do not maintain deeply.

### Gap G-16: Shared-plan OG and Zalo preview optimizer

**Functional group:** F11 Content Guides & SEO  
**Severity:** 🟡 Important  
**Mapped upgrade:** U-16 (P1)

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| GetYourGuide/Klook/Viator | Commercial activity marketplaces solve this around booking confidence. | 8/10 | Trust/review/policy wrapped into conversion. |
| Tripadvisor/Google/Airbnb | Community/map/planning platforms solve adjacent trust and planning needs. | 8/10 | UGC and saved-list context. |
| vinhlong360 | Shared plans fetch public data but preview cards are sparse. | 60-80% coverage | Local-only context plus no-booking boundary. |

**Tầng 2 — WHY:**

- User problem solved: Generate title/description/image for shared plan links and Zalo/Facebook OG.
- Business value: improves shared-link CTR, preview image coverage without adding booking/payment support.
- Research backing: NNGroup on scannability/visual hierarchy, NNGroup/Baymard on filters where relevant, Google structured data docs for SEO-related items.
- Reasoning chain: Persona P5 need -> feature makes decision easier -> measured by shared-link CTR, preview image coverage -> existing evidence E09 reduces build effort -> expected outcome is higher trust or planning completion.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 4 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 4 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 4 | No paid infra required beyond current stack. |
| Competitive advantage | 4 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 4 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **20/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- agent/saved.py:24..114 - /api/saved get/post/delete/merge.
- agent/plans.py:21..153 - /api/my-plans get/post/delete/merge/publish.
- agent/plans.py:157..190 - /api/shared-plans list/detail for public plans.
Conclusion: 60-80% implemented; gap is productization/polish, not greenfield.
```
**Tầng 5 — UPGRADE CARD:**
```text
U-16: Shared-plan OG and Zalo preview optimizer
Primary persona: P5; Secondary: P1; Journey: PLAN
Problem: Shared plans fetch public data but preview cards are sparse.
Target: Generate title/description/image for shared plan links and Zalo/Facebook OG.
Sub-features cần build:
  1. UI/control/state for the main flow — effort: M
  2. Admin/data or API linkage where needed — effort: S/M
  3. Metrics/event instrumentation — effort: S
Tối ưu cần làm:
  1. Mobile 360px and 44px tap target QA — why: VN mobile-first — how: responsive screenshot checklist
  2. SEO/a11y/performance guard — why: organic discovery and low bandwidth — how: lazy load, aria labels, structured metadata where valid
Files to modify:
  Backend: agent/saved.py:24..114 - /api/saved get/post/delete/merge.
  Frontend: agent/plans.py:21..153 - /api/my-plans get/post/delete/merge/publish.
  Database: No migration expected
Dependencies: existing E09; constraints: no booking/payment/native app/ML/video streaming.
Risk: LOW — maintenance tax approx 1h/month.
Effort: BE 0.5d + FE 1.5d + DB 0d = 2.0d.
Impact: shared-link CTR, preview image coverage should move within 2-4 weeks.
Vietnamese market note: Zalo/Facebook/mobile and source freshness are explicit design constraints.
Priority: P1
```
**Tầng 6 — SKIP:** Không skip. Giới hạn phạm vi để không trượt sang booking/payment, real-time messaging, ML, hoặc video hosting.

**Tầng 7 — INNOVATION:** Adapt this as a local-first feature: use Vĩnh Long season/source/community knowledge that global platforms do not maintain deeply.

### Gap G-17: Admin stale-content queue

**Functional group:** F14 Admin CMS  
**Severity:** 🟡 Important  
**Mapped upgrade:** U-17 (P1)

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| GetYourGuide/Klook/Viator | Commercial activity marketplaces solve this around booking confidence. | 8/10 | Trust/review/policy wrapped into conversion. |
| Tripadvisor/Google/Airbnb | Community/map/planning platforms solve adjacent trust and planning needs. | 8/10 | UGC and saved-list context. |
| vinhlong360 | Data-quality review exists but stale public facts need a task queue. | 60-80% coverage | Local-only context plus no-booking boundary. |

**Tầng 2 — WHY:**

- User problem solved: Queue entities by stale phone/hours/source/image and batch assign status.
- Business value: improves stale items closed/week, public stale badge reduction without adding booking/payment support.
- Research backing: NNGroup on scannability/visual hierarchy, NNGroup/Baymard on filters where relevant, Google structured data docs for SEO-related items.
- Reasoning chain: Persona P3 need -> feature makes decision easier -> measured by stale items closed/week, public stale badge reduction -> existing evidence E13 reduces build effort -> expected outcome is higher trust or planning completion.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 4 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 4 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 4 | No paid infra required beyond current stack. |
| Competitive advantage | 4 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 4 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **20/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- agent/admin.py:675..722 - data-quality summary/review/apply/history/rollback.
- agent/admin.py:784..936 - image suggestions queue and approve/reject.
- agent/admin.py:1082 - media library endpoint.
Conclusion: 60-80% implemented; gap is productization/polish, not greenfield.
```
**Tầng 5 — UPGRADE CARD:**
```text
U-17: Admin stale-content queue
Primary persona: P3; Secondary: P1; Journey: RETURN,VISIT
Problem: Data-quality review exists but stale public facts need a task queue.
Target: Queue entities by stale phone/hours/source/image and batch assign status.
Sub-features cần build:
  1. UI/control/state for the main flow — effort: M
  2. Admin/data or API linkage where needed — effort: S/M
  3. Metrics/event instrumentation — effort: S
Tối ưu cần làm:
  1. Mobile 360px and 44px tap target QA — why: VN mobile-first — how: responsive screenshot checklist
  2. SEO/a11y/performance guard — why: organic discovery and low bandwidth — how: lazy load, aria labels, structured metadata where valid
Files to modify:
  Backend: agent/admin.py:675..722 - data-quality summary/review/apply/history/rollback.
  Frontend: agent/admin.py:784..936 - image suggestions queue and approve/reject.
  Database: Migration likely
Dependencies: existing E13; constraints: no booking/payment/native app/ML/video streaming.
Risk: MED — maintenance tax approx 3h/month.
Effort: BE 2d + FE 2d + DB 0.5d = 4.5d.
Impact: stale items closed/week, public stale badge reduction should move within 2-4 weeks.
Vietnamese market note: Zalo/Facebook/mobile and source freshness are explicit design constraints.
Priority: P1
```
**Tầng 6 — SKIP:** Không skip. Giới hạn phạm vi để không trượt sang booking/payment, real-time messaging, ML, hoặc video hosting.

**Tầng 7 — INNOVATION:** Adapt this as a local-first feature: use Vĩnh Long season/source/community knowledge that global platforms do not maintain deeply.

### Gap G-18: Mobile/a11y visual QA checklist in CI docs

**Functional group:** F12 Mobile Performance & PWA  
**Severity:** 🟡 Important  
**Mapped upgrade:** U-18 (P1)

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| GetYourGuide/Klook/Viator | Commercial activity marketplaces solve this around booking confidence. | 8/10 | Trust/review/policy wrapped into conversion. |
| Tripadvisor/Google/Airbnb | Community/map/planning platforms solve adjacent trust and planning needs. | 8/10 | UGC and saved-list context. |
| vinhlong360 | Responsive code exists; need repeatable 360px/390px QA checks for text overlap and controls. | 60-80% coverage | Local-only context plus no-booking boundary. |

**Tầng 2 — WHY:**

- User problem solved: Document/playwright smoke screenshots for public high-traffic pages.
- Business value: improves mobile visual regressions caught without adding booking/payment support.
- Research backing: NNGroup on scannability/visual hierarchy, NNGroup/Baymard on filters where relevant, Google structured data docs for SEO-related items.
- Reasoning chain: Persona P1 need -> feature makes decision easier -> measured by mobile visual regressions caught -> existing evidence E12 reduces build effort -> expected outcome is higher trust or planning completion.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 4 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 4 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 4 | No paid infra required beyond current stack. |
| Competitive advantage | 4 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 4 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **20/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- web-nuxt/nuxt.config.ts:20..25 - Nuxt image uses weserv provider and WebP output.
- web-nuxt/nuxt.config.ts:90 - service worker registration.
- web-nuxt/public/sw.js:4..74 - precache plus stale-while-revalidate asset/API caching.
Conclusion: 60-80% implemented; gap is productization/polish, not greenfield.
```
**Tầng 5 — UPGRADE CARD:**
```text
U-18: Mobile/a11y visual QA checklist in CI docs
Primary persona: P1; Secondary: P3; Journey: DISCOVER,RESEARCH
Problem: Responsive code exists; need repeatable 360px/390px QA checks for text overlap and controls.
Target: Document/playwright smoke screenshots for public high-traffic pages.
Sub-features cần build:
  1. UI/control/state for the main flow — effort: M
  2. Admin/data or API linkage where needed — effort: S/M
  3. Metrics/event instrumentation — effort: S
Tối ưu cần làm:
  1. Mobile 360px and 44px tap target QA — why: VN mobile-first — how: responsive screenshot checklist
  2. SEO/a11y/performance guard — why: organic discovery and low bandwidth — how: lazy load, aria labels, structured metadata where valid
Files to modify:
  Backend: web-nuxt/nuxt.config.ts:20..25 - Nuxt image uses weserv provider and WebP output.
  Frontend: web-nuxt/nuxt.config.ts:90 - service worker registration.
  Database: No migration expected
Dependencies: existing E12; constraints: no booking/payment/native app/ML/video streaming.
Risk: LOW — maintenance tax approx 1h/month.
Effort: BE 0d + FE 2d + DB 0d = 2d.
Impact: mobile visual regressions caught should move within 2-4 weeks.
Vietnamese market note: Zalo/Facebook/mobile and source freshness are explicit design constraints.
Priority: P1
```
**Tầng 6 — SKIP:** Không skip. Giới hạn phạm vi để không trượt sang booking/payment, real-time messaging, ML, hoặc video hosting.

**Tầng 7 — INNOVATION:** Adapt this as a local-first feature: use Vĩnh Long season/source/community knowledge that global platforms do not maintain deeply.

### Gap G-19: Offline saved plan snapshot

**Functional group:** F12 Mobile Performance & PWA  
**Severity:** 🟡 Important  
**Mapped upgrade:** U-19 (P1)

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| GetYourGuide/Klook/Viator | Commercial activity marketplaces solve this around booking confidence. | 8/10 | Trust/review/policy wrapped into conversion. |
| Tripadvisor/Google/Airbnb | Community/map/planning platforms solve adjacent trust and planning needs. | 8/10 | UGC and saved-list context. |
| vinhlong360 | SW caches assets/API generically but plans are not explicitly made offline-safe. | 60-80% coverage | Local-only context plus no-booking boundary. |

**Tầng 2 — WHY:**

- User problem solved: Cache saved plan/detail snapshots and show offline banner.
- Business value: improves offline plan opens, failed API fallback rate without adding booking/payment support.
- Research backing: NNGroup on scannability/visual hierarchy, NNGroup/Baymard on filters where relevant, Google structured data docs for SEO-related items.
- Reasoning chain: Persona P5 need -> feature makes decision easier -> measured by offline plan opens, failed API fallback rate -> existing evidence E12 reduces build effort -> expected outcome is higher trust or planning completion.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 4 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 4 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 4 | No paid infra required beyond current stack. |
| Competitive advantage | 4 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 4 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **20/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- web-nuxt/nuxt.config.ts:20..25 - Nuxt image uses weserv provider and WebP output.
- web-nuxt/nuxt.config.ts:90 - service worker registration.
- web-nuxt/public/sw.js:4..74 - precache plus stale-while-revalidate asset/API caching.
Conclusion: 60-80% implemented; gap is productization/polish, not greenfield.
```
**Tầng 5 — UPGRADE CARD:**
```text
U-19: Offline saved plan snapshot
Primary persona: P5; Secondary: P1; Journey: PLAN,VISIT
Problem: SW caches assets/API generically but plans are not explicitly made offline-safe.
Target: Cache saved plan/detail snapshots and show offline banner.
Sub-features cần build:
  1. UI/control/state for the main flow — effort: M
  2. Admin/data or API linkage where needed — effort: S/M
  3. Metrics/event instrumentation — effort: S
Tối ưu cần làm:
  1. Mobile 360px and 44px tap target QA — why: VN mobile-first — how: responsive screenshot checklist
  2. SEO/a11y/performance guard — why: organic discovery and low bandwidth — how: lazy load, aria labels, structured metadata where valid
Files to modify:
  Backend: web-nuxt/nuxt.config.ts:20..25 - Nuxt image uses weserv provider and WebP output.
  Frontend: web-nuxt/nuxt.config.ts:90 - service worker registration.
  Database: No migration expected
Dependencies: existing E12; constraints: no booking/payment/native app/ML/video streaming.
Risk: MED — maintenance tax approx 3h/month.
Effort: BE 1d + FE 2.5d + DB 0d = 3.5d.
Impact: offline plan opens, failed API fallback rate should move within 2-4 weeks.
Vietnamese market note: Zalo/Facebook/mobile and source freshness are explicit design constraints.
Priority: P1
```
**Tầng 6 — SKIP:** Không skip. Giới hạn phạm vi để không trượt sang booking/payment, real-time messaging, ML, hoặc video hosting.

**Tầng 7 — INNOVATION:** Adapt this as a local-first feature: use Vĩnh Long season/source/community knowledge that global platforms do not maintain deeply.

### Gap G-20: Post-visit review prompt from visited state

**Functional group:** F4 Reviews & Ratings  
**Severity:** 🟡 Important  
**Mapped upgrade:** U-20 (P1)

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| GetYourGuide/Klook/Viator | Commercial activity marketplaces solve this around booking confidence. | 8/10 | Trust/review/policy wrapped into conversion. |
| Tripadvisor/Google/Airbnb | Community/map/planning platforms solve adjacent trust and planning needs. | 8/10 | UGC and saved-list context. |
| vinhlong360 | Visit tracking exists but does not drive a timely review prompt. | 60-80% coverage | Local-only context plus no-booking boundary. |

**Tầng 2 — WHY:**

- User problem solved: After user marks visited, show lightweight review/tag/photo prompt.
- Business value: improves visited-to-review conversion without adding booking/payment support.
- Research backing: NNGroup on scannability/visual hierarchy, NNGroup/Baymard on filters where relevant, Google structured data docs for SEO-related items.
- Reasoning chain: Persona P2 need -> feature makes decision easier -> measured by visited-to-review conversion -> existing evidence E05 reduces build effort -> expected outcome is higher trust or planning completion.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 4 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 4 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 4 | No paid infra required beyond current stack. |
| Competitive advantage | 4 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 4 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **20/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- web-nuxt/pages/dia-diem/[id].vue:214 - LazyEntityReviews on entity detail.
- web-nuxt/components/EntityReviews.vue:6..31 - logged-in review form with accessible star radiogroup.
- web-nuxt/components/EntityReviews.vue:154..156 - helpful toggle with auth modal fallback.
Conclusion: 60-80% implemented; gap is productization/polish, not greenfield.
```
**Tầng 5 — UPGRADE CARD:**
```text
U-20: Post-visit review prompt from visited state
Primary persona: P2; Secondary: P4; Journey: SHARE,RETURN
Problem: Visit tracking exists but does not drive a timely review prompt.
Target: After user marks visited, show lightweight review/tag/photo prompt.
Sub-features cần build:
  1. UI/control/state for the main flow — effort: M
  2. Admin/data or API linkage where needed — effort: S/M
  3. Metrics/event instrumentation — effort: S
Tối ưu cần làm:
  1. Mobile 360px and 44px tap target QA — why: VN mobile-first — how: responsive screenshot checklist
  2. SEO/a11y/performance guard — why: organic discovery and low bandwidth — how: lazy load, aria labels, structured metadata where valid
Files to modify:
  Backend: web-nuxt/pages/dia-diem/[id].vue:214 - LazyEntityReviews on entity detail.
  Frontend: web-nuxt/components/EntityReviews.vue:6..31 - logged-in review form with accessible star radiogroup.
  Database: No migration expected
Dependencies: existing E05; constraints: no booking/payment/native app/ML/video streaming.
Risk: LOW — maintenance tax approx 1h/month.
Effort: BE 1d + FE 2d + DB 0d = 3d.
Impact: visited-to-review conversion should move within 2-4 weeks.
Vietnamese market note: Zalo/Facebook/mobile and source freshness are explicit design constraints.
Priority: P1
```
**Tầng 6 — SKIP:** Không skip. Giới hạn phạm vi để không trượt sang booking/payment, real-time messaging, ML, hoặc video hosting.

**Tầng 7 — INNOVATION:** Adapt this as a local-first feature: use Vĩnh Long season/source/community knowledge that global platforms do not maintain deeply.

### Gap G-21: Local guide trust cards

**Functional group:** F5 Community & Reputation  
**Severity:** 🟡 Important  
**Mapped upgrade:** U-21 (P1)

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| GetYourGuide/Klook/Viator | Commercial activity marketplaces solve this around booking confidence. | 8/10 | Trust/review/policy wrapped into conversion. |
| Tripadvisor/Google/Airbnb | Community/map/planning platforms solve adjacent trust and planning needs. | 8/10 | UGC and saved-list context. |
| vinhlong360 | Profiles and stats exist; trust needs local expertise context by area/type. | 60-80% coverage | Local-only context plus no-booking boundary. |

**Tầng 2 — WHY:**

- User problem solved: Show area badges, top helpful answers, photo/review mix, and joined date.
- Business value: improves profile CTR, helpful vote rate without adding booking/payment support.
- Research backing: NNGroup on scannability/visual hierarchy, NNGroup/Baymard on filters where relevant, Google structured data docs for SEO-related items.
- Reasoning chain: Persona P2 need -> feature makes decision easier -> measured by profile CTR, helpful vote rate -> existing evidence E06 reduces build effort -> expected outcome is higher trust or planning completion.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 4 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 4 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 4 | No paid infra required beyond current stack. |
| Competitive advantage | 4 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 4 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **20/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- agent/social.py:68 - POST_TYPES = review/share/recommend/question.
- agent/social.py:266 - POST /api/posts.
- agent/social.py:1071..1238 - threaded comments create/edit/delete.
Conclusion: 60-80% implemented; gap is productization/polish, not greenfield.
```
**Tầng 5 — UPGRADE CARD:**
```text
U-21: Local guide trust cards
Primary persona: P2; Secondary: P1; Journey: RESEARCH,SHARE
Problem: Profiles and stats exist; trust needs local expertise context by area/type.
Target: Show area badges, top helpful answers, photo/review mix, and joined date.
Sub-features cần build:
  1. UI/control/state for the main flow — effort: M
  2. Admin/data or API linkage where needed — effort: S/M
  3. Metrics/event instrumentation — effort: S
Tối ưu cần làm:
  1. Mobile 360px and 44px tap target QA — why: VN mobile-first — how: responsive screenshot checklist
  2. SEO/a11y/performance guard — why: organic discovery and low bandwidth — how: lazy load, aria labels, structured metadata where valid
Files to modify:
  Backend: agent/social.py:68 - POST_TYPES = review/share/recommend/question.
  Frontend: agent/social.py:266 - POST /api/posts.
  Database: No migration expected
Dependencies: existing E06; constraints: no booking/payment/native app/ML/video streaming.
Risk: LOW — maintenance tax approx 1h/month.
Effort: BE 1d + FE 2d + DB 0d = 3d.
Impact: profile CTR, helpful vote rate should move within 2-4 weeks.
Vietnamese market note: Zalo/Facebook/mobile and source freshness are explicit design constraints.
Priority: P1
```
**Tầng 6 — SKIP:** Không skip. Giới hạn phạm vi để không trượt sang booking/payment, real-time messaging, ML, hoặc video hosting.

**Tầng 7 — INNOVATION:** Adapt this as a local-first feature: use Vĩnh Long season/source/community knowledge that global platforms do not maintain deeply.

### Gap G-22: Contact funnel dashboard

**Functional group:** F19 Analytics & Experimentation  
**Severity:** 🟡 Important  
**Mapped upgrade:** U-22 (P1)

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| GetYourGuide/Klook/Viator | Commercial activity marketplaces solve this around booking confidence. | 8/10 | Trust/review/policy wrapped into conversion. |
| Tripadvisor/Google/Airbnb | Community/map/planning platforms solve adjacent trust and planning needs. | 8/10 | UGC and saved-list context. |
| vinhlong360 | Contact action tracking exists; admin needs funnel view by entity/page/season. | 60-80% coverage | Local-only context plus no-booking boundary. |

**Tầng 2 — WHY:**

- User problem solved: Add contact/save/plan/search dashboards with CSV.
- Business value: improves contact CTR by source, top converting entities without adding booking/payment support.
- Research backing: NNGroup on scannability/visual hierarchy, NNGroup/Baymard on filters where relevant, Google structured data docs for SEO-related items.
- Reasoning chain: Persona P3 need -> feature makes decision easier -> measured by contact CTR by source, top converting entities -> existing evidence E14 reduces build effort -> expected outcome is higher trust or planning completion.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 4 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 4 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 4 | No paid infra required beyond current stack. |
| Competitive advantage | 4 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 4 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **20/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- agent/admin.py:936 - /admin/stats.
- agent/admin.py:1522..1544 - analytics overview with day ranges.
- agent/admin.py:1937..1988 - site settings list/get/put/bulk/reset.
Conclusion: 60-80% implemented; gap is productization/polish, not greenfield.
```
**Tầng 5 — UPGRADE CARD:**
```text
U-22: Contact funnel dashboard
Primary persona: P3; Secondary: P1; Journey: VISIT
Problem: Contact action tracking exists; admin needs funnel view by entity/page/season.
Target: Add contact/save/plan/search dashboards with CSV.
Sub-features cần build:
  1. UI/control/state for the main flow — effort: M
  2. Admin/data or API linkage where needed — effort: S/M
  3. Metrics/event instrumentation — effort: S
Tối ưu cần làm:
  1. Mobile 360px and 44px tap target QA — why: VN mobile-first — how: responsive screenshot checklist
  2. SEO/a11y/performance guard — why: organic discovery and low bandwidth — how: lazy load, aria labels, structured metadata where valid
Files to modify:
  Backend: agent/admin.py:936 - /admin/stats.
  Frontend: agent/admin.py:1522..1544 - analytics overview with day ranges.
  Database: No migration expected
Dependencies: existing E14; constraints: no booking/payment/native app/ML/video streaming.
Risk: LOW — maintenance tax approx 1h/month.
Effort: BE 1d + FE 2d + DB 0d = 3d.
Impact: contact CTR by source, top converting entities should move within 2-4 weeks.
Vietnamese market note: Zalo/Facebook/mobile and source freshness are explicit design constraints.
Priority: P1
```
**Tầng 6 — SKIP:** Không skip. Giới hạn phạm vi để không trượt sang booking/payment, real-time messaging, ML, hoặc video hosting.

**Tầng 7 — INNOVATION:** Adapt this as a local-first feature: use Vĩnh Long season/source/community knowledge that global platforms do not maintain deeply.

### Gap G-23: Collaborative itinerary notes/votes via link

**Functional group:** F10 Itinerary Planning  
**Severity:** 🟡 Important  
**Mapped upgrade:** U-23 (P2)

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| GetYourGuide/Klook/Viator | Commercial activity marketplaces solve this around booking confidence. | 8/10 | Trust/review/policy wrapped into conversion. |
| Tripadvisor/Google/Airbnb | Community/map/planning platforms solve adjacent trust and planning needs. | 8/10 | UGC and saved-list context. |
| vinhlong360 | Shared plans are read-only; groups coordinate in Zalo with no structured feedback. | 40-70% coverage | Local-only context plus no-booking boundary. |

**Tầng 2 — WHY:**

- User problem solved: Add optional lightweight vote/comment token per shared plan.
- Business value: improves plans with feedback, edits after share without adding booking/payment support.
- Research backing: NNGroup on scannability/visual hierarchy, NNGroup/Baymard on filters where relevant, Google structured data docs for SEO-related items.
- Reasoning chain: Persona P5 need -> feature makes decision easier -> measured by plans with feedback, edits after share -> existing evidence E09 reduces build effort -> expected outcome is higher trust or planning completion.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 4 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 3 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 3 | No paid infra required beyond current stack. |
| Competitive advantage | 3 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 4 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **17/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- agent/saved.py:24..114 - /api/saved get/post/delete/merge.
- agent/plans.py:21..153 - /api/my-plans get/post/delete/merge/publish.
- agent/plans.py:157..190 - /api/shared-plans list/detail for public plans.
Conclusion: 40-70% implemented; gap is productization/polish, not greenfield.
```
**Tầng 5 — UPGRADE CARD:**
```text
U-23: Collaborative itinerary notes/votes via link
Primary persona: P5; Secondary: P1; Journey: PLAN
Problem: Shared plans are read-only; groups coordinate in Zalo with no structured feedback.
Target: Add optional lightweight vote/comment token per shared plan.
Sub-features cần build:
  1. UI/control/state for the main flow — effort: M
  2. Admin/data or API linkage where needed — effort: S/M
  3. Metrics/event instrumentation — effort: S
Tối ưu cần làm:
  1. Mobile 360px and 44px tap target QA — why: VN mobile-first — how: responsive screenshot checklist
  2. SEO/a11y/performance guard — why: organic discovery and low bandwidth — how: lazy load, aria labels, structured metadata where valid
Files to modify:
  Backend: agent/saved.py:24..114 - /api/saved get/post/delete/merge.
  Frontend: agent/plans.py:21..153 - /api/my-plans get/post/delete/merge/publish.
  Database: Migration likely
Dependencies: existing E09; constraints: no booking/payment/native app/ML/video streaming.
Risk: MED — maintenance tax approx 3h/month.
Effort: BE 3d + FE 4d + DB 1d = 8d.
Impact: plans with feedback, edits after share should move within 2-4 weeks.
Vietnamese market note: Zalo/Facebook/mobile and source freshness are explicit design constraints.
Priority: P2
```
**Tầng 6 — SKIP:** Không skip. Giới hạn phạm vi để không trượt sang booking/payment, real-time messaging, ML, hoặc video hosting.

**Tầng 7 — INNOVATION:** Adapt this as a local-first feature: use Vĩnh Long season/source/community knowledge that global platforms do not maintain deeply.

### Gap G-24: Q&A quality queue and accepted-answer highlights

**Functional group:** F5 Community & Reputation  
**Severity:** 🟡 Important  
**Mapped upgrade:** U-24 (P2)

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| GetYourGuide/Klook/Viator | Commercial activity marketplaces solve this around booking confidence. | 8/10 | Trust/review/policy wrapped into conversion. |
| Tripadvisor/Google/Airbnb | Community/map/planning platforms solve adjacent trust and planning needs. | 8/10 | UGC and saved-list context. |
| vinhlong360 | Best answer exists; unanswered/stale questions need surfacing. | 40-70% coverage | Local-only context plus no-booking boundary. |

**Tầng 2 — WHY:**

- User problem solved: Queue unanswered entity questions and highlight accepted answers in detail.
- Business value: improves answer SLA, accepted-answer view rate without adding booking/payment support.
- Research backing: NNGroup on scannability/visual hierarchy, NNGroup/Baymard on filters where relevant, Google structured data docs for SEO-related items.
- Reasoning chain: Persona P2 need -> feature makes decision easier -> measured by answer SLA, accepted-answer view rate -> existing evidence E06 reduces build effort -> expected outcome is higher trust or planning completion.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 4 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 3 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 3 | No paid infra required beyond current stack. |
| Competitive advantage | 3 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 4 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **17/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- agent/social.py:68 - POST_TYPES = review/share/recommend/question.
- agent/social.py:266 - POST /api/posts.
- agent/social.py:1071..1238 - threaded comments create/edit/delete.
Conclusion: 40-70% implemented; gap is productization/polish, not greenfield.
```
**Tầng 5 — UPGRADE CARD:**
```text
U-24: Q&A quality queue and accepted-answer highlights
Primary persona: P2; Secondary: P1; Journey: RESEARCH,SHARE
Problem: Best answer exists; unanswered/stale questions need surfacing.
Target: Queue unanswered entity questions and highlight accepted answers in detail.
Sub-features cần build:
  1. UI/control/state for the main flow — effort: M
  2. Admin/data or API linkage where needed — effort: S/M
  3. Metrics/event instrumentation — effort: S
Tối ưu cần làm:
  1. Mobile 360px and 44px tap target QA — why: VN mobile-first — how: responsive screenshot checklist
  2. SEO/a11y/performance guard — why: organic discovery and low bandwidth — how: lazy load, aria labels, structured metadata where valid
Files to modify:
  Backend: agent/social.py:68 - POST_TYPES = review/share/recommend/question.
  Frontend: agent/social.py:266 - POST /api/posts.
  Database: No migration expected
Dependencies: existing E06; constraints: no booking/payment/native app/ML/video streaming.
Risk: LOW — maintenance tax approx 1h/month.
Effort: BE 1.5d + FE 2d + DB 0d = 3.5d.
Impact: answer SLA, accepted-answer view rate should move within 2-4 weeks.
Vietnamese market note: Zalo/Facebook/mobile and source freshness are explicit design constraints.
Priority: P2
```
**Tầng 6 — SKIP:** Không skip. Giới hạn phạm vi để không trượt sang booking/payment, real-time messaging, ML, hoặc video hosting.

**Tầng 7 — INNOVATION:** Adapt this as a local-first feature: use Vĩnh Long season/source/community knowledge that global platforms do not maintain deeply.

### Gap G-25: Ward one-screen day plan

**Functional group:** F8 Map & Navigation  
**Severity:** 🟡 Important  
**Mapped upgrade:** U-25 (P2)

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| GetYourGuide/Klook/Viator | Commercial activity marketplaces solve this around booking confidence. | 8/10 | Trust/review/policy wrapped into conversion. |
| Tripadvisor/Google/Airbnb | Community/map/planning platforms solve adjacent trust and planning needs. | 8/10 | UGC and saved-list context. |
| vinhlong360 | Ward pages and map exist but not a scannable local day plan. | 40-70% coverage | Local-only context plus no-booking boundary. |

**Tầng 2 — WHY:**

- User problem solved: Add ward page route: breakfast/visit/lunch/photo/contact stops.
- Business value: improves ward plan saves, page dwell without adding booking/payment support.
- Research backing: NNGroup on scannability/visual hierarchy, NNGroup/Baymard on filters where relevant, Google structured data docs for SEO-related items.
- Reasoning chain: Persona P1 need -> feature makes decision easier -> measured by ward plan saves, page dwell -> existing evidence E03 reduces build effort -> expected outcome is higher trust or planning completion.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 4 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 3 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 3 | No paid infra required beyond current stack. |
| Competitive advantage | 3 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 4 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **17/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- agent/public_api.py:720..772 - /api/map-pins with type/area cache and ratings in pin payload.
- web-nuxt/pages/ban-do.vue:17..38 - type filters and map control panel.
- web-nuxt/pages/ban-do.vue:245..265 - MapLibre geojson source, clusters, unclustered pins.
Conclusion: 40-70% implemented; gap is productization/polish, not greenfield.
```
**Tầng 5 — UPGRADE CARD:**
```text
U-25: Ward one-screen day plan
Primary persona: P1; Secondary: P5; Journey: DISCOVER,PLAN
Problem: Ward pages and map exist but not a scannable local day plan.
Target: Add ward page route: breakfast/visit/lunch/photo/contact stops.
Sub-features cần build:
  1. UI/control/state for the main flow — effort: M
  2. Admin/data or API linkage where needed — effort: S/M
  3. Metrics/event instrumentation — effort: S
Tối ưu cần làm:
  1. Mobile 360px and 44px tap target QA — why: VN mobile-first — how: responsive screenshot checklist
  2. SEO/a11y/performance guard — why: organic discovery and low bandwidth — how: lazy load, aria labels, structured metadata where valid
Files to modify:
  Backend: agent/public_api.py:720..772 - /api/map-pins with type/area cache and ratings in pin payload.
  Frontend: web-nuxt/pages/ban-do.vue:17..38 - type filters and map control panel.
  Database: No migration expected
Dependencies: existing E03; constraints: no booking/payment/native app/ML/video streaming.
Risk: LOW — maintenance tax approx 1h/month.
Effort: BE 1d + FE 3d + DB 0d = 4d.
Impact: ward plan saves, page dwell should move within 2-4 weeks.
Vietnamese market note: Zalo/Facebook/mobile and source freshness are explicit design constraints.
Priority: P2
```
**Tầng 6 — SKIP:** Không skip. Giới hạn phạm vi để không trượt sang booking/payment, real-time messaging, ML, hoặc video hosting.

**Tầng 7 — INNOVATION:** Adapt this as a local-first feature: use Vĩnh Long season/source/community knowledge that global platforms do not maintain deeply.

### Gap G-26: Event RSVP reminders

**Functional group:** F17 Notifications & Follow  
**Severity:** 🟡 Important  
**Mapped upgrade:** U-26 (P2)

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| GetYourGuide/Klook/Viator | Commercial activity marketplaces solve this around booking confidence. | 8/10 | Trust/review/policy wrapped into conversion. |
| Tripadvisor/Google/Airbnb | Community/map/planning platforms solve adjacent trust and planning needs. | 8/10 | UGC and saved-list context. |
| vinhlong360 | RSVP exists; reminders/digests do not. | 40-70% coverage | Local-only context plus no-booking boundary. |

**Tầng 2 — WHY:**

- User problem solved: Notify users before followed/RSVP events with opt-in preferences.
- Business value: improves RSVP reminder CTR, unsubscribes without adding booking/payment support.
- Research backing: NNGroup on scannability/visual hierarchy, NNGroup/Baymard on filters where relevant, Google structured data docs for SEO-related items.
- Reasoning chain: Persona P4 need -> feature makes decision easier -> measured by RSVP reminder CTR, unsubscribes -> existing evidence E10 reduces build effort -> expected outcome is higher trust or planning completion.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 4 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 3 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 3 | No paid infra required beyond current stack. |
| Competitive advantage | 3 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 4 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **17/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- agent/notifications.py:62..107 - notifications list/read/read-all.
- agent/notifications.py:132..149 - notification preferences get/update.
- agent/notifications.py:189..236 - SSE notification stream.
Conclusion: 40-70% implemented; gap is productization/polish, not greenfield.
```
**Tầng 5 — UPGRADE CARD:**
```text
U-26: Event RSVP reminders
Primary persona: P4; Secondary: P1; Journey: RETURN,VISIT
Problem: RSVP exists; reminders/digests do not.
Target: Notify users before followed/RSVP events with opt-in preferences.
Sub-features cần build:
  1. UI/control/state for the main flow — effort: M
  2. Admin/data or API linkage where needed — effort: S/M
  3. Metrics/event instrumentation — effort: S
Tối ưu cần làm:
  1. Mobile 360px and 44px tap target QA — why: VN mobile-first — how: responsive screenshot checklist
  2. SEO/a11y/performance guard — why: organic discovery and low bandwidth — how: lazy load, aria labels, structured metadata where valid
Files to modify:
  Backend: agent/notifications.py:62..107 - notifications list/read/read-all.
  Frontend: agent/notifications.py:132..149 - notification preferences get/update.
  Database: Migration likely
Dependencies: existing E10; constraints: no booking/payment/native app/ML/video streaming.
Risk: MED — maintenance tax approx 3h/month.
Effort: BE 2d + FE 2d + DB 0.5d = 4.5d.
Impact: RSVP reminder CTR, unsubscribes should move within 2-4 weeks.
Vietnamese market note: Zalo/Facebook/mobile and source freshness are explicit design constraints.
Priority: P2
```
**Tầng 6 — SKIP:** Không skip. Giới hạn phạm vi để không trượt sang booking/payment, real-time messaging, ML, hoặc video hosting.

**Tầng 7 — INNOVATION:** Adapt this as a local-first feature: use Vĩnh Long season/source/community knowledge that global platforms do not maintain deeply.

### Gap G-27: Short video-link guide cards

**Functional group:** F11 Content Guides & SEO  
**Severity:** 🟡 Important  
**Mapped upgrade:** U-27 (P2)

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| GetYourGuide/Klook/Viator | Commercial activity marketplaces solve this around booking confidence. | 8/10 | Trust/review/policy wrapped into conversion. |
| Tripadvisor/Google/Airbnb | Community/map/planning platforms solve adjacent trust and planning needs. | 8/10 | UGC and saved-list context. |
| vinhlong360 | No video streaming should be built, but video discovery matters. | 40-70% coverage | Local-only context plus no-booking boundary. |

**Tầng 2 — WHY:**

- User problem solved: Store/link YouTube/TikTok references as external inspiration cards with fallback text.
- Business value: improves video-link clicks, detail saves after video card without adding booking/payment support.
- Research backing: NNGroup on scannability/visual hierarchy, NNGroup/Baymard on filters where relevant, Google structured data docs for SEO-related items.
- Reasoning chain: Persona P1 need -> feature makes decision easier -> measured by video-link clicks, detail saves after video card -> existing evidence E11 reduces build effort -> expected outcome is higher trust or planning completion.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 4 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 3 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 3 | No paid infra required beyond current stack. |
| Competitive advantage | 3 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 4 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **17/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- agent/seo.py:404..423 - entity JSON-LD with type mapping and ImageObject support.
- agent/seo.py:696..986 - site/area/itinerary/entity/collection JSON-LD endpoints.
- agent/seo.py:1007..1148 - sitemap.xml, media sitemap, sitemap index, robots.txt.
Conclusion: 40-70% implemented; gap is productization/polish, not greenfield.
```
**Tầng 5 — UPGRADE CARD:**
```text
U-27: Short video-link guide cards
Primary persona: P1; Secondary: P4; Journey: DISCOVER,RESEARCH
Problem: No video streaming should be built, but video discovery matters.
Target: Store/link YouTube/TikTok references as external inspiration cards with fallback text.
Sub-features cần build:
  1. UI/control/state for the main flow — effort: M
  2. Admin/data or API linkage where needed — effort: S/M
  3. Metrics/event instrumentation — effort: S
Tối ưu cần làm:
  1. Mobile 360px and 44px tap target QA — why: VN mobile-first — how: responsive screenshot checklist
  2. SEO/a11y/performance guard — why: organic discovery and low bandwidth — how: lazy load, aria labels, structured metadata where valid
Files to modify:
  Backend: agent/seo.py:404..423 - entity JSON-LD with type mapping and ImageObject support.
  Frontend: agent/seo.py:696..986 - site/area/itinerary/entity/collection JSON-LD endpoints.
  Database: No migration expected
Dependencies: existing E11; constraints: no booking/payment/native app/ML/video streaming.
Risk: LOW — maintenance tax approx 1h/month.
Effort: BE 0.5d + FE 2d + DB 0d = 2.5d.
Impact: video-link clicks, detail saves after video card should move within 2-4 weeks.
Vietnamese market note: Zalo/Facebook/mobile and source freshness are explicit design constraints.
Priority: P2
```
**Tầng 6 — SKIP:** Không skip. Giới hạn phạm vi để không trượt sang booking/payment, real-time messaging, ML, hoặc video hosting.

**Tầng 7 — INNOVATION:** Adapt this as a local-first feature: use Vĩnh Long season/source/community knowledge that global platforms do not maintain deeply.

### Gap G-28: Public themed collection pages

**Functional group:** F7 Saved & Collections  
**Severity:** 🟡 Important  
**Mapped upgrade:** U-28 (P2)

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| GetYourGuide/Klook/Viator | Commercial activity marketplaces solve this around booking confidence. | 8/10 | Trust/review/policy wrapped into conversion. |
| Tripadvisor/Google/Airbnb | Community/map/planning platforms solve adjacent trust and planning needs. | 8/10 | UGC and saved-list context. |
| vinhlong360 | Saved exists for users; public editorial/community collections are missing. | 40-70% coverage | Local-only context plus no-booking boundary. |

**Tầng 2 — WHY:**

- User problem solved: Create collection model or site-setting driven curated lists.
- Business value: improves collection sessions, saves/collection without adding booking/payment support.
- Research backing: NNGroup on scannability/visual hierarchy, NNGroup/Baymard on filters where relevant, Google structured data docs for SEO-related items.
- Reasoning chain: Persona P1 need -> feature makes decision easier -> measured by collection sessions, saves/collection -> existing evidence E09 reduces build effort -> expected outcome is higher trust or planning completion.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 4 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 3 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 3 | No paid infra required beyond current stack. |
| Competitive advantage | 3 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 4 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **17/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- agent/saved.py:24..114 - /api/saved get/post/delete/merge.
- agent/plans.py:21..153 - /api/my-plans get/post/delete/merge/publish.
- agent/plans.py:157..190 - /api/shared-plans list/detail for public plans.
Conclusion: 40-70% implemented; gap is productization/polish, not greenfield.
```
**Tầng 5 — UPGRADE CARD:**
```text
U-28: Public themed collection pages
Primary persona: P1; Secondary: P4; Journey: DISCOVER,PLAN
Problem: Saved exists for users; public editorial/community collections are missing.
Target: Create collection model or site-setting driven curated lists.
Sub-features cần build:
  1. UI/control/state for the main flow — effort: M
  2. Admin/data or API linkage where needed — effort: S/M
  3. Metrics/event instrumentation — effort: S
Tối ưu cần làm:
  1. Mobile 360px and 44px tap target QA — why: VN mobile-first — how: responsive screenshot checklist
  2. SEO/a11y/performance guard — why: organic discovery and low bandwidth — how: lazy load, aria labels, structured metadata where valid
Files to modify:
  Backend: agent/saved.py:24..114 - /api/saved get/post/delete/merge.
  Frontend: agent/plans.py:21..153 - /api/my-plans get/post/delete/merge/publish.
  Database: Migration likely
Dependencies: existing E09; constraints: no booking/payment/native app/ML/video streaming.
Risk: MED — maintenance tax approx 3h/month.
Effort: BE 1.5d + FE 3d + DB 0.5d = 5.0d.
Impact: collection sessions, saves/collection should move within 2-4 weeks.
Vietnamese market note: Zalo/Facebook/mobile and source freshness are explicit design constraints.
Priority: P2
```
**Tầng 6 — SKIP:** Không skip. Giới hạn phạm vi để không trượt sang booking/payment, real-time messaging, ML, hoặc video hosting.

**Tầng 7 — INNOVATION:** Adapt this as a local-first feature: use Vĩnh Long season/source/community knowledge that global platforms do not maintain deeply.

### Gap G-29: Rule-based similar recommendations

**Functional group:** F9 Personalization & Return  
**Severity:** 🟡 Important  
**Mapped upgrade:** U-29 (P2)

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| GetYourGuide/Klook/Viator | Commercial activity marketplaces solve this around booking confidence. | 8/10 | Trust/review/policy wrapped into conversion. |
| Tripadvisor/Google/Airbnb | Community/map/planning platforms solve adjacent trust and planning needs. | 8/10 | UGC and saved-list context. |
| vinhlong360 | Related/nearby exists; make logic transparent and season-aware. | 40-70% coverage | Local-only context plus no-booking boundary. |

**Tầng 2 — WHY:**

- User problem solved: Recommend by area/type/season/visited exclusion; no ML engine.
- Business value: improves related CTR, repeat detail views without adding booking/payment support.
- Research backing: NNGroup on scannability/visual hierarchy, NNGroup/Baymard on filters where relevant, Google structured data docs for SEO-related items.
- Reasoning chain: Persona P1 need -> feature makes decision easier -> measured by related CTR, repeat detail views -> existing evidence E02 reduces build effort -> expected outcome is higher trust or planning completion.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 4 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 3 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 3 | No paid infra required beyond current stack. |
| Competitive advantage | 3 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 4 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **17/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- agent/public_api.py:161 - /api/entities accepts q, type, area, month, sort, limit, offset.
- agent/public_api.py:357 - /api/search delegates to db.search_entities and count_entities_filtered.
- web-nuxt/pages/dia-diem/index.vue:88..106 - search input plus type/area FilterChips.
Conclusion: 40-70% implemented; gap is productization/polish, not greenfield.
```
**Tầng 5 — UPGRADE CARD:**
```text
U-29: Rule-based similar recommendations
Primary persona: P1; Secondary: P4; Journey: RESEARCH,RETURN
Problem: Related/nearby exists; make logic transparent and season-aware.
Target: Recommend by area/type/season/visited exclusion; no ML engine.
Sub-features cần build:
  1. UI/control/state for the main flow — effort: M
  2. Admin/data or API linkage where needed — effort: S/M
  3. Metrics/event instrumentation — effort: S
Tối ưu cần làm:
  1. Mobile 360px and 44px tap target QA — why: VN mobile-first — how: responsive screenshot checklist
  2. SEO/a11y/performance guard — why: organic discovery and low bandwidth — how: lazy load, aria labels, structured metadata where valid
Files to modify:
  Backend: agent/public_api.py:161 - /api/entities accepts q, type, area, month, sort, limit, offset.
  Frontend: agent/public_api.py:357 - /api/search delegates to db.search_entities and count_entities_filtered.
  Database: No migration expected
Dependencies: existing E02; constraints: no booking/payment/native app/ML/video streaming.
Risk: LOW — maintenance tax approx 1h/month.
Effort: BE 1d + FE 2.5d + DB 0d = 3.5d.
Impact: related CTR, repeat detail views should move within 2-4 weeks.
Vietnamese market note: Zalo/Facebook/mobile and source freshness are explicit design constraints.
Priority: P2
```
**Tầng 6 — SKIP:** Không skip. Giới hạn phạm vi để không trượt sang booking/payment, real-time messaging, ML, hoặc video hosting.

**Tầng 7 — INNOVATION:** Adapt this as a local-first feature: use Vĩnh Long season/source/community knowledge that global platforms do not maintain deeply.

### Gap G-30: Partner/entity claim workflow

**Functional group:** F20 Monetization & Partnership  
**Severity:** 🟡 Important  
**Mapped upgrade:** U-30 (P2)

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| GetYourGuide/Klook/Viator | Commercial activity marketplaces solve this around booking confidence. | 8/10 | Trust/review/policy wrapped into conversion. |
| Tripadvisor/Google/Airbnb | Community/map/planning platforms solve adjacent trust and planning needs. | 8/10 | UGC and saved-list context. |
| vinhlong360 | Contact page exists; claim workflow is email-based and not tracked. | 40-70% coverage | Local-only context plus no-booking boundary. |

**Tầng 2 — WHY:**

- User problem solved: Create claim form queue with phone/Zalo verification and admin audit.
- Business value: improves claims submitted, verified claims without adding booking/payment support.
- Research backing: NNGroup on scannability/visual hierarchy, NNGroup/Baymard on filters where relevant, Google structured data docs for SEO-related items.
- Reasoning chain: Persona P3 need -> feature makes decision easier -> measured by claims submitted, verified claims -> existing evidence E14 reduces build effort -> expected outcome is higher trust or planning completion.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 4 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 3 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 3 | No paid infra required beyond current stack. |
| Competitive advantage | 3 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 4 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **17/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- agent/admin.py:936 - /admin/stats.
- agent/admin.py:1522..1544 - analytics overview with day ranges.
- agent/admin.py:1937..1988 - site settings list/get/put/bulk/reset.
Conclusion: 40-70% implemented; gap is productization/polish, not greenfield.
```
**Tầng 5 — UPGRADE CARD:**
```text
U-30: Partner/entity claim workflow
Primary persona: P3; Secondary: P1; Journey: RESEARCH,VISIT
Problem: Contact page exists; claim workflow is email-based and not tracked.
Target: Create claim form queue with phone/Zalo verification and admin audit.
Sub-features cần build:
  1. UI/control/state for the main flow — effort: M
  2. Admin/data or API linkage where needed — effort: S/M
  3. Metrics/event instrumentation — effort: S
Tối ưu cần làm:
  1. Mobile 360px and 44px tap target QA — why: VN mobile-first — how: responsive screenshot checklist
  2. SEO/a11y/performance guard — why: organic discovery and low bandwidth — how: lazy load, aria labels, structured metadata where valid
Files to modify:
  Backend: agent/admin.py:936 - /admin/stats.
  Frontend: agent/admin.py:1522..1544 - analytics overview with day ranges.
  Database: Migration likely
Dependencies: existing E14; constraints: no booking/payment/native app/ML/video streaming.
Risk: MED — maintenance tax approx 3h/month.
Effort: BE 2.5d + FE 3d + DB 0.5d = 6.0d.
Impact: claims submitted, verified claims should move within 2-4 weeks.
Vietnamese market note: Zalo/Facebook/mobile and source freshness are explicit design constraints.
Priority: P2
```
**Tầng 6 — SKIP:** Không skip. Giới hạn phạm vi để không trượt sang booking/payment, real-time messaging, ML, hoặc video hosting.

**Tầng 7 — INNOVATION:** Adapt this as a local-first feature: use Vĩnh Long season/source/community knowledge that global platforms do not maintain deeply.

### Gap G-31: Search zero-result KPI and content gap queue

**Functional group:** F19 Analytics & Experimentation  
**Severity:** 🟡 Important  
**Mapped upgrade:** U-31 (P2)

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| GetYourGuide/Klook/Viator | Commercial activity marketplaces solve this around booking confidence. | 8/10 | Trust/review/policy wrapped into conversion. |
| Tripadvisor/Google/Airbnb | Community/map/planning platforms solve adjacent trust and planning needs. | 8/10 | UGC and saved-list context. |
| vinhlong360 | Search works but no visible zero-result content gap workflow. | 40-70% coverage | Local-only context plus no-booking boundary. |

**Tầng 2 — WHY:**

- User problem solved: Persist/analyze zero-results and make admin tasks.
- Business value: improves zero-result rate, new content from query gaps without adding booking/payment support.
- Research backing: NNGroup on scannability/visual hierarchy, NNGroup/Baymard on filters where relevant, Google structured data docs for SEO-related items.
- Reasoning chain: Persona P3 need -> feature makes decision easier -> measured by zero-result rate, new content from query gaps -> existing evidence E14 reduces build effort -> expected outcome is higher trust or planning completion.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 4 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 3 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 3 | No paid infra required beyond current stack. |
| Competitive advantage | 3 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 4 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **17/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- agent/admin.py:936 - /admin/stats.
- agent/admin.py:1522..1544 - analytics overview with day ranges.
- agent/admin.py:1937..1988 - site settings list/get/put/bulk/reset.
Conclusion: 40-70% implemented; gap is productization/polish, not greenfield.
```
**Tầng 5 — UPGRADE CARD:**
```text
U-31: Search zero-result KPI and content gap queue
Primary persona: P3; Secondary: P1; Journey: DISCOVER
Problem: Search works but no visible zero-result content gap workflow.
Target: Persist/analyze zero-results and make admin tasks.
Sub-features cần build:
  1. UI/control/state for the main flow — effort: M
  2. Admin/data or API linkage where needed — effort: S/M
  3. Metrics/event instrumentation — effort: S
Tối ưu cần làm:
  1. Mobile 360px and 44px tap target QA — why: VN mobile-first — how: responsive screenshot checklist
  2. SEO/a11y/performance guard — why: organic discovery and low bandwidth — how: lazy load, aria labels, structured metadata where valid
Files to modify:
  Backend: agent/admin.py:936 - /admin/stats.
  Frontend: agent/admin.py:1522..1544 - analytics overview with day ranges.
  Database: No migration expected
Dependencies: existing E14; constraints: no booking/payment/native app/ML/video streaming.
Risk: LOW — maintenance tax approx 1h/month.
Effort: BE 2d + FE 2d + DB 0d = 4d.
Impact: zero-result rate, new content from query gaps should move within 2-4 weeks.
Vietnamese market note: Zalo/Facebook/mobile and source freshness are explicit design constraints.
Priority: P2
```
**Tầng 6 — SKIP:** Không skip. Giới hạn phạm vi để không trượt sang booking/payment, real-time messaging, ML, hoặc video hosting.

**Tầng 7 — INNOVATION:** Adapt this as a local-first feature: use Vĩnh Long season/source/community knowledge that global platforms do not maintain deeply.

### Gap G-32: Transport practical guide without live prices

**Functional group:** F8 Map & Navigation  
**Severity:** 🟢 Nice-to-have  
**Mapped upgrade:** U-32 (P3)

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| GetYourGuide/Klook/Viator | Commercial activity marketplaces solve this around booking confidence. | 8/10 | Trust/review/policy wrapped into conversion. |
| Tripadvisor/Google/Airbnb | Community/map/planning platforms solve adjacent trust and planning needs. | 8/10 | UGC and saved-list context. |
| vinhlong360 | Users need getting-around context; live transport APIs are overkill. | 40-70% coverage | Local-only context plus no-booking boundary. |

**Tầng 2 — WHY:**

- User problem solved: Static route/boat/ferry/taxi notes with source/freshness date.
- Business value: improves guide views, directions clicks without adding booking/payment support.
- Research backing: NNGroup on scannability/visual hierarchy, NNGroup/Baymard on filters where relevant, Google structured data docs for SEO-related items.
- Reasoning chain: Persona P1 need -> feature makes decision easier -> measured by guide views, directions clicks -> existing evidence E03 reduces build effort -> expected outcome is higher trust or planning completion.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 3 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 3 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 3 | No paid infra required beyond current stack. |
| Competitive advantage | 3 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 3 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **15/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- agent/public_api.py:720..772 - /api/map-pins with type/area cache and ratings in pin payload.
- web-nuxt/pages/ban-do.vue:17..38 - type filters and map control panel.
- web-nuxt/pages/ban-do.vue:245..265 - MapLibre geojson source, clusters, unclustered pins.
Conclusion: 40-70% implemented; gap is productization/polish, not greenfield.
```
**Tầng 5 — UPGRADE CARD:**
```text
U-32: Transport practical guide without live prices
Primary persona: P1; Secondary: P5; Journey: PLAN,VISIT
Problem: Users need getting-around context; live transport APIs are overkill.
Target: Static route/boat/ferry/taxi notes with source/freshness date.
Sub-features cần build:
  1. UI/control/state for the main flow — effort: M
  2. Admin/data or API linkage where needed — effort: S/M
  3. Metrics/event instrumentation — effort: S
Tối ưu cần làm:
  1. Mobile 360px and 44px tap target QA — why: VN mobile-first — how: responsive screenshot checklist
  2. SEO/a11y/performance guard — why: organic discovery and low bandwidth — how: lazy load, aria labels, structured metadata where valid
Files to modify:
  Backend: agent/public_api.py:720..772 - /api/map-pins with type/area cache and ratings in pin payload.
  Frontend: web-nuxt/pages/ban-do.vue:17..38 - type filters and map control panel.
  Database: No migration expected
Dependencies: existing E03; constraints: no booking/payment/native app/ML/video streaming.
Risk: LOW — maintenance tax approx 1h/month.
Effort: BE 0.5d + FE 3d + DB 0d = 3.5d.
Impact: guide views, directions clicks should move within 2-4 weeks.
Vietnamese market note: Zalo/Facebook/mobile and source freshness are explicit design constraints.
Priority: P3
```
**Tầng 6 — SKIP:** Không skip. Giới hạn phạm vi để không trượt sang booking/payment, real-time messaging, ML, hoặc video hosting.

**Tầng 7 — INNOVATION:** Adapt this as a local-first feature: use Vĩnh Long season/source/community knowledge that global platforms do not maintain deeply.

### Gap G-33: Manual weather/season warning banners

**Functional group:** F15 Data Quality & Freshness  
**Severity:** 🟢 Nice-to-have  
**Mapped upgrade:** U-33 (P3)

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| GetYourGuide/Klook/Viator | Commercial activity marketplaces solve this around booking confidence. | 8/10 | Trust/review/policy wrapped into conversion. |
| Tripadvisor/Google/Airbnb | Community/map/planning platforms solve adjacent trust and planning needs. | 8/10 | UGC and saved-list context. |
| vinhlong360 | Season data exists; risk/flood/heat advisories need manual admin override. | 40-70% coverage | Local-only context plus no-booking boundary. |

**Tầng 2 — WHY:**

- User problem solved: Site-setting banner by area/type with expiry.
- Business value: improves banner CTR, expired-banner incidents without adding booking/payment support.
- Research backing: NNGroup on scannability/visual hierarchy, NNGroup/Baymard on filters where relevant, Google structured data docs for SEO-related items.
- Reasoning chain: Persona P3 need -> feature makes decision easier -> measured by banner CTR, expired-banner incidents -> existing evidence E14 reduces build effort -> expected outcome is higher trust or planning completion.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 3 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 3 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 3 | No paid infra required beyond current stack. |
| Competitive advantage | 3 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 3 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **15/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- agent/admin.py:936 - /admin/stats.
- agent/admin.py:1522..1544 - analytics overview with day ranges.
- agent/admin.py:1937..1988 - site settings list/get/put/bulk/reset.
Conclusion: 40-70% implemented; gap is productization/polish, not greenfield.
```
**Tầng 5 — UPGRADE CARD:**
```text
U-33: Manual weather/season warning banners
Primary persona: P3; Secondary: P1; Journey: VISIT,RETURN
Problem: Season data exists; risk/flood/heat advisories need manual admin override.
Target: Site-setting banner by area/type with expiry.
Sub-features cần build:
  1. UI/control/state for the main flow — effort: M
  2. Admin/data or API linkage where needed — effort: S/M
  3. Metrics/event instrumentation — effort: S
Tối ưu cần làm:
  1. Mobile 360px and 44px tap target QA — why: VN mobile-first — how: responsive screenshot checklist
  2. SEO/a11y/performance guard — why: organic discovery and low bandwidth — how: lazy load, aria labels, structured metadata where valid
Files to modify:
  Backend: agent/admin.py:936 - /admin/stats.
  Frontend: agent/admin.py:1522..1544 - analytics overview with day ranges.
  Database: No migration expected
Dependencies: existing E14; constraints: no booking/payment/native app/ML/video streaming.
Risk: MED — maintenance tax approx 3h/month.
Effort: BE 1d + FE 2d + DB 0d = 3d.
Impact: banner CTR, expired-banner incidents should move within 2-4 weeks.
Vietnamese market note: Zalo/Facebook/mobile and source freshness are explicit design constraints.
Priority: P3
```
**Tầng 6 — SKIP:** Không skip. Giới hạn phạm vi để không trượt sang booking/payment, real-time messaging, ML, hoặc video hosting.

**Tầng 7 — INNOVATION:** Adapt this as a local-first feature: use Vĩnh Long season/source/community knowledge that global platforms do not maintain deeply.

### Gap G-34: Printable route cue sheets

**Functional group:** F10 Itinerary Planning  
**Severity:** 🟢 Nice-to-have  
**Mapped upgrade:** U-34 (P3)

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| GetYourGuide/Klook/Viator | Commercial activity marketplaces solve this around booking confidence. | 8/10 | Trust/review/policy wrapped into conversion. |
| Tripadvisor/Google/Airbnb | Community/map/planning platforms solve adjacent trust and planning needs. | 8/10 | UGC and saved-list context. |
| vinhlong360 | Print/export overlaps with U-05; later add route-stop cue details. | 40-70% coverage | Local-only context plus no-booking boundary. |

**Tầng 2 — WHY:**

- User problem solved: Generate compact route instructions for motorbike/family use.
- Business value: improves cue-sheet exports without adding booking/payment support.
- Research backing: NNGroup on scannability/visual hierarchy, NNGroup/Baymard on filters where relevant, Google structured data docs for SEO-related items.
- Reasoning chain: Persona P5 need -> feature makes decision easier -> measured by cue-sheet exports -> existing evidence E09 reduces build effort -> expected outcome is higher trust or planning completion.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 3 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 3 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 3 | No paid infra required beyond current stack. |
| Competitive advantage | 3 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 3 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **15/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- agent/saved.py:24..114 - /api/saved get/post/delete/merge.
- agent/plans.py:21..153 - /api/my-plans get/post/delete/merge/publish.
- agent/plans.py:157..190 - /api/shared-plans list/detail for public plans.
Conclusion: 40-70% implemented; gap is productization/polish, not greenfield.
```
**Tầng 5 — UPGRADE CARD:**
```text
U-34: Printable route cue sheets
Primary persona: P5; Secondary: P1; Journey: PLAN,VISIT
Problem: Print/export overlaps with U-05; later add route-stop cue details.
Target: Generate compact route instructions for motorbike/family use.
Sub-features cần build:
  1. UI/control/state for the main flow — effort: M
  2. Admin/data or API linkage where needed — effort: S/M
  3. Metrics/event instrumentation — effort: S
Tối ưu cần làm:
  1. Mobile 360px and 44px tap target QA — why: VN mobile-first — how: responsive screenshot checklist
  2. SEO/a11y/performance guard — why: organic discovery and low bandwidth — how: lazy load, aria labels, structured metadata where valid
Files to modify:
  Backend: agent/saved.py:24..114 - /api/saved get/post/delete/merge.
  Frontend: agent/plans.py:21..153 - /api/my-plans get/post/delete/merge/publish.
  Database: No migration expected
Dependencies: existing E09; constraints: no booking/payment/native app/ML/video streaming.
Risk: LOW — maintenance tax approx 1h/month.
Effort: BE 0d + FE 2d + DB 0d = 2d.
Impact: cue-sheet exports should move within 2-4 weeks.
Vietnamese market note: Zalo/Facebook/mobile and source freshness are explicit design constraints.
Priority: P3
```
**Tầng 6 — SKIP:** Không skip. Giới hạn phạm vi để không trượt sang booking/payment, real-time messaging, ML, hoặc video hosting.

**Tầng 7 — INNOVATION:** Adapt this as a local-first feature: use Vĩnh Long season/source/community knowledge that global platforms do not maintain deeply.

### Gap G-35: Community challenge campaigns

**Functional group:** F5 Community & Reputation  
**Severity:** 🟢 Nice-to-have  
**Mapped upgrade:** U-35 (P3)

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| GetYourGuide/Klook/Viator | Commercial activity marketplaces solve this around booking confidence. | 8/10 | Trust/review/policy wrapped into conversion. |
| Tripadvisor/Google/Airbnb | Community/map/planning platforms solve adjacent trust and planning needs. | 8/10 | UGC and saved-list context. |
| vinhlong360 | Leaderboard exists; campaign framing can motivate useful contributions. | 40-70% coverage | Local-only context plus no-booking boundary. |

**Tầng 2 — WHY:**

- User problem solved: Seasonal challenges for missing photos/tips with non-monetary recognition.
- Business value: improves challenge submissions, useful approval rate without adding booking/payment support.
- Research backing: NNGroup on scannability/visual hierarchy, NNGroup/Baymard on filters where relevant, Google structured data docs for SEO-related items.
- Reasoning chain: Persona P2 need -> feature makes decision easier -> measured by challenge submissions, useful approval rate -> existing evidence E06 reduces build effort -> expected outcome is higher trust or planning completion.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 3 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 3 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 3 | No paid infra required beyond current stack. |
| Competitive advantage | 3 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 3 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **15/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- agent/social.py:68 - POST_TYPES = review/share/recommend/question.
- agent/social.py:266 - POST /api/posts.
- agent/social.py:1071..1238 - threaded comments create/edit/delete.
Conclusion: 40-70% implemented; gap is productization/polish, not greenfield.
```
**Tầng 5 — UPGRADE CARD:**
```text
U-35: Community challenge campaigns
Primary persona: P2; Secondary: P4; Journey: SHARE,RETURN
Problem: Leaderboard exists; campaign framing can motivate useful contributions.
Target: Seasonal challenges for missing photos/tips with non-monetary recognition.
Sub-features cần build:
  1. UI/control/state for the main flow — effort: M
  2. Admin/data or API linkage where needed — effort: S/M
  3. Metrics/event instrumentation — effort: S
Tối ưu cần làm:
  1. Mobile 360px and 44px tap target QA — why: VN mobile-first — how: responsive screenshot checklist
  2. SEO/a11y/performance guard — why: organic discovery and low bandwidth — how: lazy load, aria labels, structured metadata where valid
Files to modify:
  Backend: agent/social.py:68 - POST_TYPES = review/share/recommend/question.
  Frontend: agent/social.py:266 - POST /api/posts.
  Database: Migration likely
Dependencies: existing E06; constraints: no booking/payment/native app/ML/video streaming.
Risk: MED — maintenance tax approx 3h/month.
Effort: BE 1d + FE 3d + DB 0.5d = 4.5d.
Impact: challenge submissions, useful approval rate should move within 2-4 weeks.
Vietnamese market note: Zalo/Facebook/mobile and source freshness are explicit design constraints.
Priority: P3
```
**Tầng 6 — SKIP:** Không skip. Giới hạn phạm vi để không trượt sang booking/payment, real-time messaging, ML, hoặc video hosting.

**Tầng 7 — INNOVATION:** Adapt this as a local-first feature: use Vĩnh Long season/source/community knowledge that global platforms do not maintain deeply.

### Gap G-36: Zalo OA handoff templates

**Functional group:** F13 Contact & Conversion  
**Severity:** 🟢 Nice-to-have  
**Mapped upgrade:** U-36 (P3)

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| GetYourGuide/Klook/Viator | Commercial activity marketplaces solve this around booking confidence. | 8/10 | Trust/review/policy wrapped into conversion. |
| Tripadvisor/Google/Airbnb | Community/map/planning platforms solve adjacent trust and planning needs. | 8/10 | UGC and saved-list context. |
| vinhlong360 | Zalo CTA exists but message content is generic. | 40-70% coverage | Local-only context plus no-booking boundary. |

**Tầng 2 — WHY:**

- User problem solved: Prefill message templates: hỏi giờ mở cửa, đặt bàn offline, hỏi đường.
- Business value: improves Zalo click completion, repeat contact without adding booking/payment support.
- Research backing: NNGroup on scannability/visual hierarchy, NNGroup/Baymard on filters where relevant, Google structured data docs for SEO-related items.
- Reasoning chain: Persona P1 need -> feature makes decision easier -> measured by Zalo click completion, repeat contact -> existing evidence E08 reduces build effort -> expected outcome is higher trust or planning completion.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 3 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 3 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 3 | No paid infra required beyond current stack. |
| Competitive advantage | 3 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 3 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **15/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- web-nuxt/pages/dia-diem/[id].vue:96..97 - hero call and Zalo actions.
- web-nuxt/pages/dia-diem/[id].vue:369..402 - contact row and sticky CTA phone/Zalo/map fallback.
- web-nuxt/pages/dia-diem/[id].vue:711..715 - Zalo URL/number normalization.
Conclusion: 40-70% implemented; gap is productization/polish, not greenfield.
```
**Tầng 5 — UPGRADE CARD:**
```text
U-36: Zalo OA handoff templates
Primary persona: P1; Secondary: P3; Journey: VISIT
Problem: Zalo CTA exists but message content is generic.
Target: Prefill message templates: hỏi giờ mở cửa, đặt bàn offline, hỏi đường.
Sub-features cần build:
  1. UI/control/state for the main flow — effort: M
  2. Admin/data or API linkage where needed — effort: S/M
  3. Metrics/event instrumentation — effort: S
Tối ưu cần làm:
  1. Mobile 360px and 44px tap target QA — why: VN mobile-first — how: responsive screenshot checklist
  2. SEO/a11y/performance guard — why: organic discovery and low bandwidth — how: lazy load, aria labels, structured metadata where valid
Files to modify:
  Backend: web-nuxt/pages/dia-diem/[id].vue:96..97 - hero call and Zalo actions.
  Frontend: web-nuxt/pages/dia-diem/[id].vue:369..402 - contact row and sticky CTA phone/Zalo/map fallback.
  Database: No migration expected
Dependencies: existing E08; constraints: no booking/payment/native app/ML/video streaming.
Risk: LOW — maintenance tax approx 1h/month.
Effort: BE 1d + FE 2d + DB 0d = 3d.
Impact: Zalo click completion, repeat contact should move within 2-4 weeks.
Vietnamese market note: Zalo/Facebook/mobile and source freshness are explicit design constraints.
Priority: P3
```
**Tầng 6 — SKIP:** Không skip. Giới hạn phạm vi để không trượt sang booking/payment, real-time messaging, ML, hoặc video hosting.

**Tầng 7 — INNOVATION:** Adapt this as a local-first feature: use Vĩnh Long season/source/community knowledge that global platforms do not maintain deeply.

### Gap G-37: Commercial boundary and partner transparency page

**Functional group:** F20 Monetization & Partnership  
**Severity:** 🟢 Nice-to-have  
**Mapped upgrade:** U-37 (P3)

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| GetYourGuide/Klook/Viator | Commercial activity marketplaces solve this around booking confidence. | 8/10 | Trust/review/policy wrapped into conversion. |
| Tripadvisor/Google/Airbnb | Community/map/planning platforms solve adjacent trust and planning needs. | 8/10 | UGC and saved-list context. |
| vinhlong360 | As partner features grow, users need clear no-payment/no-affiliate rules. | 40-70% coverage | Local-only context plus no-booking boundary. |

**Tầng 2 — WHY:**

- User problem solved: Publish partner/advertising policy and label showcase content.
- Business value: improves policy views, complaint reduction without adding booking/payment support.
- Research backing: NNGroup on scannability/visual hierarchy, NNGroup/Baymard on filters where relevant, Google structured data docs for SEO-related items.
- Reasoning chain: Persona P3 need -> feature makes decision easier -> measured by policy views, complaint reduction -> existing evidence E11 reduces build effort -> expected outcome is higher trust or planning completion.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 3 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 3 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 3 | No paid infra required beyond current stack. |
| Competitive advantage | 3 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 3 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **15/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- agent/seo.py:404..423 - entity JSON-LD with type mapping and ImageObject support.
- agent/seo.py:696..986 - site/area/itinerary/entity/collection JSON-LD endpoints.
- agent/seo.py:1007..1148 - sitemap.xml, media sitemap, sitemap index, robots.txt.
Conclusion: 40-70% implemented; gap is productization/polish, not greenfield.
```
**Tầng 5 — UPGRADE CARD:**
```text
U-37: Commercial boundary and partner transparency page
Primary persona: P3; Secondary: P1; Journey: RESEARCH
Problem: As partner features grow, users need clear no-payment/no-affiliate rules.
Target: Publish partner/advertising policy and label showcase content.
Sub-features cần build:
  1. UI/control/state for the main flow — effort: M
  2. Admin/data or API linkage where needed — effort: S/M
  3. Metrics/event instrumentation — effort: S
Tối ưu cần làm:
  1. Mobile 360px and 44px tap target QA — why: VN mobile-first — how: responsive screenshot checklist
  2. SEO/a11y/performance guard — why: organic discovery and low bandwidth — how: lazy load, aria labels, structured metadata where valid
Files to modify:
  Backend: agent/seo.py:404..423 - entity JSON-LD with type mapping and ImageObject support.
  Frontend: agent/seo.py:696..986 - site/area/itinerary/entity/collection JSON-LD endpoints.
  Database: No migration expected
Dependencies: existing E11; constraints: no booking/payment/native app/ML/video streaming.
Risk: LOW — maintenance tax approx 1h/month.
Effort: BE 0.5d + FE 1.5d + DB 0d = 2.0d.
Impact: policy views, complaint reduction should move within 2-4 weeks.
Vietnamese market note: Zalo/Facebook/mobile and source freshness are explicit design constraints.
Priority: P3
```
**Tầng 6 — SKIP:** Không skip. Giới hạn phạm vi để không trượt sang booking/payment, real-time messaging, ML, hoặc video hosting.

**Tầng 7 — INNOVATION:** Adapt this as a local-first feature: use Vĩnh Long season/source/community knowledge that global platforms do not maintain deeply.

### Gap G-38: Booking/payment/checkout

**Functional group:** F20 Monetization/Scope Guard  
**Severity:** 🟢 Nice-to-have / skip-by-constraint  
**Mapped skip:** S-01

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| GYG,Klook,Viator,Traveloka,Airbnb | Feature is common on large commercial platforms. | 7-9/10 | Works because they own inventory, payments, or ops teams. |
| vinhlong360 | Intentionally absent or out-of-scope. | N/A | No-booking showcase/community platform. |

**Tầng 2 — WHY:**

- User problem solved elsewhere: commercial commitment, inventory, loyalty, or support.
- Business value elsewhere: transaction take-rate or marketplace retention.
- Research/market note: for vinhlong360 this would create legal/ops debt before user value.
- Reasoning chain: feature exists on GYG,Klook,Viator,Traveloka,Airbnb -> requires scale/ops/legal basis -> vinhlong360 has no transaction constraint -> skip protects trust and solo-dev capacity.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 2 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 2 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 2 | No paid infra required beyond current stack. |
| Competitive advantage | 1 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 1 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **8/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- E08 shows the correct current conversion boundary: phone/Zalo/map contact tracking, not checkout.
- E11 SEO evidence plus legal sources in Appendix H: site can inform and structure data without becoming a marketplace.
Conclusion: feature should remain absent.
```
**Tầng 5 — UPGRADE CARD:** Không tạo upgrade vì FIT < 15 hoặc vi phạm constraint.

**Tầng 6 — SKIP JUSTIFICATION:**
- Skip vì: Violates explicit constraint; triggers e-commerce ops/legal/support.
- Anti-pattern nếu copy: Booking envy.
- Revisit khi: Only revisit if business becomes licensed marketplace with ops team.

**Tầng 7 — INNOVATION:** Replace with local trust/action alternative: source badge, Zalo CTA, itinerary/share, or community Q&A depending on the journey stage.

### Gap G-39: Payment gateway

**Functional group:** F20 Monetization/Scope Guard  
**Severity:** 🟢 Nice-to-have / skip-by-constraint  
**Mapped skip:** S-02

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| Klook,Traveloka,Airbnb | Feature is common on large commercial platforms. | 7-9/10 | Works because they own inventory, payments, or ops teams. |
| vinhlong360 | Intentionally absent or out-of-scope. | N/A | No-booking showcase/community platform. |

**Tầng 2 — WHY:**

- User problem solved elsewhere: commercial commitment, inventory, loyalty, or support.
- Business value elsewhere: transaction take-rate or marketplace retention.
- Research/market note: for vinhlong360 this would create legal/ops debt before user value.
- Reasoning chain: feature exists on Klook,Traveloka,Airbnb -> requires scale/ops/legal basis -> vinhlong360 has no transaction constraint -> skip protects trust and solo-dev capacity.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 2 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 1 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 1 | No paid infra required beyond current stack. |
| Competitive advantage | 1 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 2 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **7/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- E08 shows the correct current conversion boundary: phone/Zalo/map contact tracking, not checkout.
- E11 SEO evidence plus legal sources in Appendix H: site can inform and structure data without becoming a marketplace.
Conclusion: feature should remain absent.
```
**Tầng 5 — UPGRADE CARD:** Không tạo upgrade vì FIT < 15 hoặc vi phạm constraint.

**Tầng 6 — SKIP JUSTIFICATION:**
- Skip vì: No on-site transaction; <1M VND/month budget should not carry fraud/payment support.
- Anti-pattern nếu copy: Legal minefield.
- Revisit khi: Revisit with formal merchant, accounting, refund policy, support SLA.

**Tầng 7 — INNOVATION:** Replace with local trust/action alternative: source badge, Zalo CTA, itinerary/share, or community Q&A depending on the journey stage.

### Gap G-40: Dynamic pricing

**Functional group:** F20 Monetization/Scope Guard  
**Severity:** 🟢 Nice-to-have / skip-by-constraint  
**Mapped skip:** S-03

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| OTA marketplaces | Feature is common on large commercial platforms. | 7-9/10 | Works because they own inventory, payments, or ops teams. |
| vinhlong360 | Intentionally absent or out-of-scope. | N/A | No-booking showcase/community platform. |

**Tầng 2 — WHY:**

- User problem solved elsewhere: commercial commitment, inventory, loyalty, or support.
- Business value elsewhere: transaction take-rate or marketplace retention.
- Research/market note: for vinhlong360 this would create legal/ops debt before user value.
- Reasoning chain: feature exists on OTA marketplaces -> requires scale/ops/legal basis -> vinhlong360 has no transaction constraint -> skip protects trust and solo-dev capacity.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 1 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 1 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 1 | No paid infra required beyond current stack. |
| Competitive advantage | 1 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 2 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **6/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- E08 shows the correct current conversion boundary: phone/Zalo/map contact tracking, not checkout.
- E11 SEO evidence plus legal sources in Appendix H: site can inform and structure data without becoming a marketplace.
Conclusion: feature should remain absent.
```
**Tầng 5 — UPGRADE CARD:** Không tạo upgrade vì FIT < 15 hoặc vi phạm constraint.

**Tầng 6 — SKIP JUSTIFICATION:**
- Skip vì: No inventory/availability; would create false promise.
- Anti-pattern nếu copy: Copy-paste gap.
- Revisit khi: Revisit only with real operator inventory.

**Tầng 7 — INNOVATION:** Replace with local trust/action alternative: source badge, Zalo CTA, itinerary/share, or community Q&A depending on the journey stage.

### Gap G-41: Availability calendar

**Functional group:** F20 Monetization/Scope Guard  
**Severity:** 🟢 Nice-to-have / skip-by-constraint  
**Mapped skip:** S-04

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| GYG,Klook,Airbnb,Viator | Feature is common on large commercial platforms. | 7-9/10 | Works because they own inventory, payments, or ops teams. |
| vinhlong360 | Intentionally absent or out-of-scope. | N/A | No-booking showcase/community platform. |

**Tầng 2 — WHY:**

- User problem solved elsewhere: commercial commitment, inventory, loyalty, or support.
- Business value elsewhere: transaction take-rate or marketplace retention.
- Research/market note: for vinhlong360 this would create legal/ops debt before user value.
- Reasoning chain: feature exists on GYG,Klook,Airbnb,Viator -> requires scale/ops/legal basis -> vinhlong360 has no transaction constraint -> skip protects trust and solo-dev capacity.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 2 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 2 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 2 | No paid infra required beyond current stack. |
| Competitive advantage | 1 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 1 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **8/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- E08 shows the correct current conversion boundary: phone/Zalo/map contact tracking, not checkout.
- E11 SEO evidence plus legal sources in Appendix H: site can inform and structure data without becoming a marketplace.
Conclusion: feature should remain absent.
```
**Tầng 5 — UPGRADE CARD:** Không tạo upgrade vì FIT < 15 hoặc vi phạm constraint.

**Tầng 6 — SKIP JUSTIFICATION:**
- Skip vì: Requires live operator capacity and stale-data babysitting.
- Anti-pattern nếu copy: Maintenance debt.
- Revisit khi: Revisit when verified partners update availability weekly.

**Tầng 7 — INNOVATION:** Replace with local trust/action alternative: source badge, Zalo CTA, itinerary/share, or community Q&A depending on the journey stage.

### Gap G-42: Verified purchase badge

**Functional group:** F20 Monetization/Scope Guard  
**Severity:** 🟢 Nice-to-have / skip-by-constraint  
**Mapped skip:** S-05

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| Klook,GYG,Airbnb,Traveloka | Feature is common on large commercial platforms. | 7-9/10 | Works because they own inventory, payments, or ops teams. |
| vinhlong360 | Intentionally absent or out-of-scope. | N/A | No-booking showcase/community platform. |

**Tầng 2 — WHY:**

- User problem solved elsewhere: commercial commitment, inventory, loyalty, or support.
- Business value elsewhere: transaction take-rate or marketplace retention.
- Research/market note: for vinhlong360 this would create legal/ops debt before user value.
- Reasoning chain: feature exists on Klook,GYG,Airbnb,Traveloka -> requires scale/ops/legal basis -> vinhlong360 has no transaction constraint -> skip protects trust and solo-dev capacity.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 2 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 1 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 1 | No paid infra required beyond current stack. |
| Competitive advantage | 1 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 2 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **7/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- E08 shows the correct current conversion boundary: phone/Zalo/map contact tracking, not checkout.
- E11 SEO evidence plus legal sources in Appendix H: site can inform and structure data without becoming a marketplace.
Conclusion: feature should remain absent.
```
**Tầng 5 — UPGRADE CARD:** Không tạo upgrade vì FIT < 15 hoặc vi phạm constraint.

**Tầng 6 — SKIP JUSTIFICATION:**
- Skip vì: No purchase event exists; badge would be misleading.
- Anti-pattern nếu copy: Dark trust pattern.
- Revisit khi: Revisit only after legitimate transaction source.

**Tầng 7 — INNOVATION:** Replace with local trust/action alternative: source badge, Zalo CTA, itinerary/share, or community Q&A depending on the journey stage.

### Gap G-43: Host/guest marketplace roles

**Functional group:** F20 Monetization/Scope Guard  
**Severity:** 🟢 Nice-to-have / skip-by-constraint  
**Mapped skip:** S-06

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| Airbnb | Feature is common on large commercial platforms. | 7-9/10 | Works because they own inventory, payments, or ops teams. |
| vinhlong360 | Intentionally absent or out-of-scope. | N/A | No-booking showcase/community platform. |

**Tầng 2 — WHY:**

- User problem solved elsewhere: commercial commitment, inventory, loyalty, or support.
- Business value elsewhere: transaction take-rate or marketplace retention.
- Research/market note: for vinhlong360 this would create legal/ops debt before user value.
- Reasoning chain: feature exists on Airbnb -> requires scale/ops/legal basis -> vinhlong360 has no transaction constraint -> skip protects trust and solo-dev capacity.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 2 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 2 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 2 | No paid infra required beyond current stack. |
| Competitive advantage | 2 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 1 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **9/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- E08 shows the correct current conversion boundary: phone/Zalo/map contact tracking, not checkout.
- E11 SEO evidence plus legal sources in Appendix H: site can inform and structure data without becoming a marketplace.
Conclusion: feature should remain absent.
```
**Tầng 5 — UPGRADE CARD:** Không tạo upgrade vì FIT < 15 hoặc vi phạm constraint.

**Tầng 6 — SKIP JUSTIFICATION:**
- Skip vì: vinhlong360 is showcase/community, not lodging marketplace.
- Anti-pattern nếu copy: Feature bloat.
- Revisit khi: Revisit with marketplace strategy and legal review.

**Tầng 7 — INNOVATION:** Replace with local trust/action alternative: source badge, Zalo CTA, itinerary/share, or community Q&A depending on the journey stage.

### Gap G-44: Native mobile app

**Functional group:** F20 Monetization/Scope Guard  
**Severity:** 🟢 Nice-to-have / skip-by-constraint  
**Mapped skip:** S-07

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| Klook,Airbnb,Google,Atlas,VoiceMap | Feature is common on large commercial platforms. | 7-9/10 | Works because they own inventory, payments, or ops teams. |
| vinhlong360 | Intentionally absent or out-of-scope. | N/A | No-booking showcase/community platform. |

**Tầng 2 — WHY:**

- User problem solved elsewhere: commercial commitment, inventory, loyalty, or support.
- Business value elsewhere: transaction take-rate or marketplace retention.
- Research/market note: for vinhlong360 this would create legal/ops debt before user value.
- Reasoning chain: feature exists on Klook,Airbnb,Google,Atlas,VoiceMap -> requires scale/ops/legal basis -> vinhlong360 has no transaction constraint -> skip protects trust and solo-dev capacity.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 2 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 2 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 2 | No paid infra required beyond current stack. |
| Competitive advantage | 2 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 2 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **10/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- E08 shows the correct current conversion boundary: phone/Zalo/map contact tracking, not checkout.
- E11 SEO evidence plus legal sources in Appendix H: site can inform and structure data without becoming a marketplace.
Conclusion: feature should remain absent.
```
**Tầng 5 — UPGRADE CARD:** Không tạo upgrade vì FIT < 15 hoặc vi phạm constraint.

**Tầng 6 — SKIP JUSTIFICATION:**
- Skip vì: Web-only constraint and solo dev maintenance burden.
- Anti-pattern nếu copy: Premature platform split.
- Revisit khi: Revisit after >50K MAU with retention proven.

**Tầng 7 — INNOVATION:** Replace with local trust/action alternative: source badge, Zalo CTA, itinerary/share, or community Q&A depending on the journey stage.

### Gap G-45: Real-time user messaging

**Functional group:** F20 Monetization/Scope Guard  
**Severity:** 🟢 Nice-to-have / skip-by-constraint  
**Mapped skip:** S-08

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| Airbnb,Tripadvisor inbox | Feature is common on large commercial platforms. | 7-9/10 | Works because they own inventory, payments, or ops teams. |
| vinhlong360 | Intentionally absent or out-of-scope. | N/A | No-booking showcase/community platform. |

**Tầng 2 — WHY:**

- User problem solved elsewhere: commercial commitment, inventory, loyalty, or support.
- Business value elsewhere: transaction take-rate or marketplace retention.
- Research/market note: for vinhlong360 this would create legal/ops debt before user value.
- Reasoning chain: feature exists on Airbnb,Tripadvisor inbox -> requires scale/ops/legal basis -> vinhlong360 has no transaction constraint -> skip protects trust and solo-dev capacity.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 2 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 2 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 2 | No paid infra required beyond current stack. |
| Competitive advantage | 2 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 1 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **9/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- E08 shows the correct current conversion boundary: phone/Zalo/map contact tracking, not checkout.
- E11 SEO evidence plus legal sources in Appendix H: site can inform and structure data without becoming a marketplace.
Conclusion: feature should remain absent.
```
**Tầng 5 — UPGRADE CARD:** Không tạo upgrade vì FIT < 15 hoặc vi phạm constraint.

**Tầng 6 — SKIP JUSTIFICATION:**
- Skip vì: Users already use Zalo; moderation and abuse burden is high.
- Anti-pattern nếu copy: Complexity trap.
- Revisit khi: Revisit if Zalo handoff fails and moderation team exists.

**Tầng 7 — INNOVATION:** Replace with local trust/action alternative: source badge, Zalo CTA, itinerary/share, or community Q&A depending on the journey stage.

### Gap G-46: ML recommendation engine

**Functional group:** F20 Monetization/Scope Guard  
**Severity:** 🟢 Nice-to-have / skip-by-constraint  
**Mapped skip:** S-09

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| Google,Airbnb,Klook | Feature is common on large commercial platforms. | 7-9/10 | Works because they own inventory, payments, or ops teams. |
| vinhlong360 | Intentionally absent or out-of-scope. | N/A | No-booking showcase/community platform. |

**Tầng 2 — WHY:**

- User problem solved elsewhere: commercial commitment, inventory, loyalty, or support.
- Business value elsewhere: transaction take-rate or marketplace retention.
- Research/market note: for vinhlong360 this would create legal/ops debt before user value.
- Reasoning chain: feature exists on Google,Airbnb,Klook -> requires scale/ops/legal basis -> vinhlong360 has no transaction constraint -> skip protects trust and solo-dev capacity.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 2 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 2 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 2 | No paid infra required beyond current stack. |
| Competitive advantage | 2 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 2 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **10/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- E08 shows the correct current conversion boundary: phone/Zalo/map contact tracking, not checkout.
- E11 SEO evidence plus legal sources in Appendix H: site can inform and structure data without becoming a marketplace.
Conclusion: feature should remain absent.
```
**Tầng 5 — UPGRADE CARD:** Không tạo upgrade vì FIT < 15 hoặc vi phạm constraint.

**Tầng 6 — SKIP JUSTIFICATION:**
- Skip vì: Need data volume, infra, explainability; rule-based is enough.
- Anti-pattern nếu copy: Over-engineering.
- Revisit khi: Revisit after >100K monthly interactions.

**Tầng 7 — INNOVATION:** Replace with local trust/action alternative: source badge, Zalo CTA, itinerary/share, or community Q&A depending on the journey stage.

### Gap G-47: Video streaming hosting

**Functional group:** F20 Monetization/Scope Guard  
**Severity:** 🟢 Nice-to-have / skip-by-constraint  
**Mapped skip:** S-10

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| TikTok/YouTube style | Feature is common on large commercial platforms. | 7-9/10 | Works because they own inventory, payments, or ops teams. |
| vinhlong360 | Intentionally absent or out-of-scope. | N/A | No-booking showcase/community platform. |

**Tầng 2 — WHY:**

- User problem solved elsewhere: commercial commitment, inventory, loyalty, or support.
- Business value elsewhere: transaction take-rate or marketplace retention.
- Research/market note: for vinhlong360 this would create legal/ops debt before user value.
- Reasoning chain: feature exists on TikTok/YouTube style -> requires scale/ops/legal basis -> vinhlong360 has no transaction constraint -> skip protects trust and solo-dev capacity.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 2 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 2 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 2 | No paid infra required beyond current stack. |
| Competitive advantage | 1 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 1 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **8/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- E08 shows the correct current conversion boundary: phone/Zalo/map contact tracking, not checkout.
- E11 SEO evidence plus legal sources in Appendix H: site can inform and structure data without becoming a marketplace.
Conclusion: feature should remain absent.
```
**Tầng 5 — UPGRADE CARD:** Không tạo upgrade vì FIT < 15 hoặc vi phạm constraint.

**Tầng 6 — SKIP JUSTIFICATION:**
- Skip vì: Bandwidth/storage/moderation blow up; use external links.
- Anti-pattern nếu copy: Maintenance debt.
- Revisit khi: Revisit only with CDN/storage budget and moderation team.

**Tầng 7 — INNOVATION:** Replace with local trust/action alternative: source badge, Zalo CTA, itinerary/share, or community Q&A depending on the journey stage.

### Gap G-48: AR/VR/3D tours

**Functional group:** F20 Monetization/Scope Guard  
**Severity:** 🟢 Nice-to-have / skip-by-constraint  
**Mapped skip:** S-11

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| Some destination sites | Feature is common on large commercial platforms. | 7-9/10 | Works because they own inventory, payments, or ops teams. |
| vinhlong360 | Intentionally absent or out-of-scope. | N/A | No-booking showcase/community platform. |

**Tầng 2 — WHY:**

- User problem solved elsewhere: commercial commitment, inventory, loyalty, or support.
- Business value elsewhere: transaction take-rate or marketplace retention.
- Research/market note: for vinhlong360 this would create legal/ops debt before user value.
- Reasoning chain: feature exists on Some destination sites -> requires scale/ops/legal basis -> vinhlong360 has no transaction constraint -> skip protects trust and solo-dev capacity.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 1 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 1 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 1 | No paid infra required beyond current stack. |
| Competitive advantage | 1 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 2 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **6/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- E08 shows the correct current conversion boundary: phone/Zalo/map contact tracking, not checkout.
- E11 SEO evidence plus legal sources in Appendix H: site can inform and structure data without becoming a marketplace.
Conclusion: feature should remain absent.
```
**Tầng 5 — UPGRADE CARD:** Không tạo upgrade vì FIT < 15 hoặc vi phạm constraint.

**Tầng 6 — SKIP JUSTIFICATION:**
- Skip vì: High build cost, low immediate need for 10K-user travel planning.
- Anti-pattern nếu copy: Vanity feature.
- Revisit khi: Revisit for a grant-funded heritage project.

**Tầng 7 — INNOVATION:** Replace with local trust/action alternative: source badge, Zalo CTA, itinerary/share, or community Q&A depending on the journey stage.

### Gap G-49: Multi-language

**Functional group:** F20 Monetization/Scope Guard  
**Severity:** 🟢 Nice-to-have / skip-by-constraint  
**Mapped skip:** S-12

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| Klook,GYG,Airbnb,Traveloka | Feature is common on large commercial platforms. | 7-9/10 | Works because they own inventory, payments, or ops teams. |
| vinhlong360 | Intentionally absent or out-of-scope. | N/A | No-booking showcase/community platform. |

**Tầng 2 — WHY:**

- User problem solved elsewhere: commercial commitment, inventory, loyalty, or support.
- Business value elsewhere: transaction take-rate or marketplace retention.
- Research/market note: for vinhlong360 this would create legal/ops debt before user value.
- Reasoning chain: feature exists on Klook,GYG,Airbnb,Traveloka -> requires scale/ops/legal basis -> vinhlong360 has no transaction constraint -> skip protects trust and solo-dev capacity.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 2 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 2 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 2 | No paid infra required beyond current stack. |
| Competitive advantage | 2 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 3 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **11/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- E08 shows the correct current conversion boundary: phone/Zalo/map contact tracking, not checkout.
- E11 SEO evidence plus legal sources in Appendix H: site can inform and structure data without becoming a marketplace.
Conclusion: feature should remain absent.
```
**Tầng 5 — UPGRADE CARD:** Không tạo upgrade vì FIT < 15 hoặc vi phạm constraint.

**Tầng 6 — SKIP JUSTIFICATION:**
- Skip vì: Prompt says Vietnamese only; translation creates stale legal/practical facts.
- Anti-pattern nếu copy: Maintenance debt.
- Revisit khi: Revisit when inbound foreign traffic is proven.

**Tầng 7 — INNOVATION:** Replace with local trust/action alternative: source badge, Zalo CTA, itinerary/share, or community Q&A depending on the journey stage.

### Gap G-50: Affiliate booking links

**Functional group:** F20 Monetization/Scope Guard  
**Severity:** 🟢 Nice-to-have / skip-by-constraint  
**Mapped skip:** S-13

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| Google Travel,Viator,Traveloka | Feature is common on large commercial platforms. | 7-9/10 | Works because they own inventory, payments, or ops teams. |
| vinhlong360 | Intentionally absent or out-of-scope. | N/A | No-booking showcase/community platform. |

**Tầng 2 — WHY:**

- User problem solved elsewhere: commercial commitment, inventory, loyalty, or support.
- Business value elsewhere: transaction take-rate or marketplace retention.
- Research/market note: for vinhlong360 this would create legal/ops debt before user value.
- Reasoning chain: feature exists on Google Travel,Viator,Traveloka -> requires scale/ops/legal basis -> vinhlong360 has no transaction constraint -> skip protects trust and solo-dev capacity.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 2 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 2 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 2 | No paid infra required beyond current stack. |
| Competitive advantage | 1 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 1 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **8/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- E08 shows the correct current conversion boundary: phone/Zalo/map contact tracking, not checkout.
- E11 SEO evidence plus legal sources in Appendix H: site can inform and structure data without becoming a marketplace.
Conclusion: feature should remain absent.
```
**Tầng 5 — UPGRADE CARD:** Không tạo upgrade vì FIT < 15 hoặc vi phạm constraint.

**Tầng 6 — SKIP JUSTIFICATION:**
- Skip vì: Constraint forbids affiliate links; trust cost high.
- Anti-pattern nếu copy: Commercial opacity.
- Revisit khi: Revisit only with transparent partner policy.

**Tầng 7 — INNOVATION:** Replace with local trust/action alternative: source badge, Zalo CTA, itinerary/share, or community Q&A depending on the journey stage.

### Gap G-51: Heavy analytics SaaS

**Functional group:** F20 Monetization/Scope Guard  
**Severity:** 🟢 Nice-to-have / skip-by-constraint  
**Mapped skip:** S-14

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| Growth teams | Feature is common on large commercial platforms. | 7-9/10 | Works because they own inventory, payments, or ops teams. |
| vinhlong360 | Intentionally absent or out-of-scope. | N/A | No-booking showcase/community platform. |

**Tầng 2 — WHY:**

- User problem solved elsewhere: commercial commitment, inventory, loyalty, or support.
- Business value elsewhere: transaction take-rate or marketplace retention.
- Research/market note: for vinhlong360 this would create legal/ops debt before user value.
- Reasoning chain: feature exists on Growth teams -> requires scale/ops/legal basis -> vinhlong360 has no transaction constraint -> skip protects trust and solo-dev capacity.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 2 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 2 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 2 | No paid infra required beyond current stack. |
| Competitive advantage | 2 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 1 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **9/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- E08 shows the correct current conversion boundary: phone/Zalo/map contact tracking, not checkout.
- E11 SEO evidence plus legal sources in Appendix H: site can inform and structure data without becoming a marketplace.
Conclusion: feature should remain absent.
```
**Tầng 5 — UPGRADE CARD:** Không tạo upgrade vì FIT < 15 hoặc vi phạm constraint.

**Tầng 6 — SKIP JUSTIFICATION:**
- Skip vì: Budget and privacy constraints; self-hosted/minimal metrics enough.
- Anti-pattern nếu copy: Premature optimization.
- Revisit khi: Revisit with paid growth team.

**Tầng 7 — INNOVATION:** Replace with local trust/action alternative: source badge, Zalo CTA, itinerary/share, or community Q&A depending on the journey stage.

### Gap G-52: Flash-sale countdowns

**Functional group:** F20 Monetization/Scope Guard  
**Severity:** 🟢 Nice-to-have / skip-by-constraint  
**Mapped skip:** S-15

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| Klook,Traveloka | Feature is common on large commercial platforms. | 7-9/10 | Works because they own inventory, payments, or ops teams. |
| vinhlong360 | Intentionally absent or out-of-scope. | N/A | No-booking showcase/community platform. |

**Tầng 2 — WHY:**

- User problem solved elsewhere: commercial commitment, inventory, loyalty, or support.
- Business value elsewhere: transaction take-rate or marketplace retention.
- Research/market note: for vinhlong360 this would create legal/ops debt before user value.
- Reasoning chain: feature exists on Klook,Traveloka -> requires scale/ops/legal basis -> vinhlong360 has no transaction constraint -> skip protects trust and solo-dev capacity.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 1 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 1 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 1 | No paid infra required beyond current stack. |
| Competitive advantage | 1 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 2 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **6/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- E08 shows the correct current conversion boundary: phone/Zalo/map contact tracking, not checkout.
- E11 SEO evidence plus legal sources in Appendix H: site can inform and structure data without becoming a marketplace.
Conclusion: feature should remain absent.
```
**Tầng 5 — UPGRADE CARD:** Không tạo upgrade vì FIT < 15 hoặc vi phạm constraint.

**Tầng 6 — SKIP JUSTIFICATION:**
- Skip vì: Creates fake urgency without real inventory.
- Anti-pattern nếu copy: Dark pattern.
- Revisit khi: Never unless backed by real official event deadline.

**Tầng 7 — INNOVATION:** Replace with local trust/action alternative: source badge, Zalo CTA, itinerary/share, or community Q&A depending on the journey stage.

### Gap G-53: Referral credits/membership tiers

**Functional group:** F20 Monetization/Scope Guard  
**Severity:** 🟢 Nice-to-have / skip-by-constraint  
**Mapped skip:** S-16

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| Klook,Airbnb,Atlas | Feature is common on large commercial platforms. | 7-9/10 | Works because they own inventory, payments, or ops teams. |
| vinhlong360 | Intentionally absent or out-of-scope. | N/A | No-booking showcase/community platform. |

**Tầng 2 — WHY:**

- User problem solved elsewhere: commercial commitment, inventory, loyalty, or support.
- Business value elsewhere: transaction take-rate or marketplace retention.
- Research/market note: for vinhlong360 this would create legal/ops debt before user value.
- Reasoning chain: feature exists on Klook,Airbnb,Atlas -> requires scale/ops/legal basis -> vinhlong360 has no transaction constraint -> skip protects trust and solo-dev capacity.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 2 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 2 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 2 | No paid infra required beyond current stack. |
| Competitive advantage | 2 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 2 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **10/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- E08 shows the correct current conversion boundary: phone/Zalo/map contact tracking, not checkout.
- E11 SEO evidence plus legal sources in Appendix H: site can inform and structure data without becoming a marketplace.
Conclusion: feature should remain absent.
```
**Tầng 5 — UPGRADE CARD:** Không tạo upgrade vì FIT < 15 hoặc vi phạm constraint.

**Tầng 6 — SKIP JUSTIFICATION:**
- Skip vì: Economic liability and anti-gaming burden; not core to trip success.
- Anti-pattern nếu copy: Vanity/growth bloat.
- Revisit khi: Revisit after core retention metrics are stable.

**Tầng 7 — INNOVATION:** Replace with local trust/action alternative: source badge, Zalo CTA, itinerary/share, or community Q&A depending on the journey stage.

### Gap G-54: Exact price comparison aggregator

**Functional group:** F20 Monetization/Scope Guard  
**Severity:** 🟢 Nice-to-have / skip-by-constraint  
**Mapped skip:** S-17

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| Google Travel | Feature is common on large commercial platforms. | 7-9/10 | Works because they own inventory, payments, or ops teams. |
| vinhlong360 | Intentionally absent or out-of-scope. | N/A | No-booking showcase/community platform. |

**Tầng 2 — WHY:**

- User problem solved elsewhere: commercial commitment, inventory, loyalty, or support.
- Business value elsewhere: transaction take-rate or marketplace retention.
- Research/market note: for vinhlong360 this would create legal/ops debt before user value.
- Reasoning chain: feature exists on Google Travel -> requires scale/ops/legal basis -> vinhlong360 has no transaction constraint -> skip protects trust and solo-dev capacity.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 2 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 1 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 1 | No paid infra required beyond current stack. |
| Competitive advantage | 1 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 2 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **7/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- E08 shows the correct current conversion boundary: phone/Zalo/map contact tracking, not checkout.
- E11 SEO evidence plus legal sources in Appendix H: site can inform and structure data without becoming a marketplace.
Conclusion: feature should remain absent.
```
**Tầng 5 — UPGRADE CARD:** Không tạo upgrade vì FIT < 15 hoặc vi phạm constraint.

**Tầng 6 — SKIP JUSTIFICATION:**
- Skip vì: Requires crawling partners and price freshness; legal risk.
- Anti-pattern nếu copy: Data freshness trap.
- Revisit khi: Revisit with signed partner feeds.

**Tầng 7 — INNOVATION:** Replace with local trust/action alternative: source badge, Zalo CTA, itinerary/share, or community Q&A depending on the journey stage.

### Gap G-55: Support ticketing system

**Functional group:** F20 Monetization/Scope Guard  
**Severity:** 🟢 Nice-to-have / skip-by-constraint  
**Mapped skip:** S-18

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| OTAs | Feature is common on large commercial platforms. | 7-9/10 | Works because they own inventory, payments, or ops teams. |
| vinhlong360 | Intentionally absent or out-of-scope. | N/A | No-booking showcase/community platform. |

**Tầng 2 — WHY:**

- User problem solved elsewhere: commercial commitment, inventory, loyalty, or support.
- Business value elsewhere: transaction take-rate or marketplace retention.
- Research/market note: for vinhlong360 this would create legal/ops debt before user value.
- Reasoning chain: feature exists on OTAs -> requires scale/ops/legal basis -> vinhlong360 has no transaction constraint -> skip protects trust and solo-dev capacity.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 2 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 2 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 2 | No paid infra required beyond current stack. |
| Competitive advantage | 2 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 3 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **11/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- E08 shows the correct current conversion boundary: phone/Zalo/map contact tracking, not checkout.
- E11 SEO evidence plus legal sources in Appendix H: site can inform and structure data without becoming a marketplace.
Conclusion: feature should remain absent.
```
**Tầng 5 — UPGRADE CARD:** Không tạo upgrade vì FIT < 15 hoặc vi phạm constraint.

**Tầng 6 — SKIP JUSTIFICATION:**
- Skip vì: Zalo/phone/email enough; ticketing invites service SLA expectations.
- Anti-pattern nếu copy: Ops bloat.
- Revisit khi: Revisit with dedicated support staff.

**Tầng 7 — INNOVATION:** Replace with local trust/action alternative: source badge, Zalo CTA, itinerary/share, or community Q&A depending on the journey stage.

### Gap G-56: Scrape/import Google reviews

**Functional group:** F20 Monetization/Scope Guard  
**Severity:** 🟢 Nice-to-have / skip-by-constraint  
**Mapped skip:** S-19

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| Google Maps | Feature is common on large commercial platforms. | 7-9/10 | Works because they own inventory, payments, or ops teams. |
| vinhlong360 | Intentionally absent or out-of-scope. | N/A | No-booking showcase/community platform. |

**Tầng 2 — WHY:**

- User problem solved elsewhere: commercial commitment, inventory, loyalty, or support.
- Business value elsewhere: transaction take-rate or marketplace retention.
- Research/market note: for vinhlong360 this would create legal/ops debt before user value.
- Reasoning chain: feature exists on Google Maps -> requires scale/ops/legal basis -> vinhlong360 has no transaction constraint -> skip protects trust and solo-dev capacity.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 1 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 1 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 1 | No paid infra required beyond current stack. |
| Competitive advantage | 1 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 2 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **6/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- E08 shows the correct current conversion boundary: phone/Zalo/map contact tracking, not checkout.
- E11 SEO evidence plus legal sources in Appendix H: site can inform and structure data without becoming a marketplace.
Conclusion: feature should remain absent.
```
**Tầng 5 — UPGRADE CARD:** Không tạo upgrade vì FIT < 15 hoặc vi phạm constraint.

**Tầng 6 — SKIP JUSTIFICATION:**
- Skip vì: Legal/API and trust risk; use own UGC and link out.
- Anti-pattern nếu copy: Legal minefield.
- Revisit khi: Revisit only via compliant Google APIs and display rules.

**Tầng 7 — INNOVATION:** Replace with local trust/action alternative: source badge, Zalo CTA, itinerary/share, or community Q&A depending on the journey stage.

### Gap G-57: Check-in gamification

**Functional group:** F20 Monetization/Scope Guard  
**Severity:** 🟢 Nice-to-have / skip-by-constraint  
**Mapped skip:** S-20

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| Foursquare/Swarm | Feature is common on large commercial platforms. | 7-9/10 | Works because they own inventory, payments, or ops teams. |
| vinhlong360 | Intentionally absent or out-of-scope. | N/A | No-booking showcase/community platform. |

**Tầng 2 — WHY:**

- User problem solved elsewhere: commercial commitment, inventory, loyalty, or support.
- Business value elsewhere: transaction take-rate or marketplace retention.
- Research/market note: for vinhlong360 this would create legal/ops debt before user value.
- Reasoning chain: feature exists on Foursquare/Swarm -> requires scale/ops/legal basis -> vinhlong360 has no transaction constraint -> skip protects trust and solo-dev capacity.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 3 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 2 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 2 | No paid infra required beyond current stack. |
| Competitive advantage | 2 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 3 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **12/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- E08 shows the correct current conversion boundary: phone/Zalo/map contact tracking, not checkout.
- E11 SEO evidence plus legal sources in Appendix H: site can inform and structure data without becoming a marketplace.
Conclusion: feature should remain absent.
```
**Tầng 5 — UPGRADE CARD:** Không tạo upgrade vì FIT < 15 hoặc vi phạm constraint.

**Tầng 6 — SKIP JUSTIFICATION:**
- Skip vì: Can become vanity metric and location privacy risk.
- Anti-pattern nếu copy: Vanity feature.
- Revisit khi: Revisit when visit tracking has user demand.

**Tầng 7 — INNOVATION:** Replace with local trust/action alternative: source badge, Zalo CTA, itinerary/share, or community Q&A depending on the journey stage.

### Gap G-58: Complex badge economy

**Functional group:** F20 Monetization/Scope Guard  
**Severity:** 🟢 Nice-to-have / skip-by-constraint  
**Mapped skip:** S-21

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| Tripadvisor,Klook | Feature is common on large commercial platforms. | 7-9/10 | Works because they own inventory, payments, or ops teams. |
| vinhlong360 | Intentionally absent or out-of-scope. | N/A | No-booking showcase/community platform. |

**Tầng 2 — WHY:**

- User problem solved elsewhere: commercial commitment, inventory, loyalty, or support.
- Business value elsewhere: transaction take-rate or marketplace retention.
- Research/market note: for vinhlong360 this would create legal/ops debt before user value.
- Reasoning chain: feature exists on Tripadvisor,Klook -> requires scale/ops/legal basis -> vinhlong360 has no transaction constraint -> skip protects trust and solo-dev capacity.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 3 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 2 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 2 | No paid infra required beyond current stack. |
| Competitive advantage | 2 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 3 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **12/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- E08 shows the correct current conversion boundary: phone/Zalo/map contact tracking, not checkout.
- E11 SEO evidence plus legal sources in Appendix H: site can inform and structure data without becoming a marketplace.
Conclusion: feature should remain absent.
```
**Tầng 5 — UPGRADE CARD:** Không tạo upgrade vì FIT < 15 hoặc vi phạm constraint.

**Tầng 6 — SKIP JUSTIFICATION:**
- Skip vì: Leaderboard already exists; extra tiers create moderation/gaming.
- Anti-pattern nếu copy: Feature bloat.
- Revisit khi: Revisit after contributor community is active.

**Tầng 7 — INNOVATION:** Replace with local trust/action alternative: source badge, Zalo CTA, itinerary/share, or community Q&A depending on the journey stage.

### Gap G-59: Flights/hotels integration

**Functional group:** F20 Monetization/Scope Guard  
**Severity:** 🟢 Nice-to-have / skip-by-constraint  
**Mapped skip:** S-22

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| Google,Klook,Traveloka,Agoda | Feature is common on large commercial platforms. | 7-9/10 | Works because they own inventory, payments, or ops teams. |
| vinhlong360 | Intentionally absent or out-of-scope. | N/A | No-booking showcase/community platform. |

**Tầng 2 — WHY:**

- User problem solved elsewhere: commercial commitment, inventory, loyalty, or support.
- Business value elsewhere: transaction take-rate or marketplace retention.
- Research/market note: for vinhlong360 this would create legal/ops debt before user value.
- Reasoning chain: feature exists on Google,Klook,Traveloka,Agoda -> requires scale/ops/legal basis -> vinhlong360 has no transaction constraint -> skip protects trust and solo-dev capacity.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 1 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 1 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 1 | No paid infra required beyond current stack. |
| Competitive advantage | 1 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 2 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **6/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- E08 shows the correct current conversion boundary: phone/Zalo/map contact tracking, not checkout.
- E11 SEO evidence plus legal sources in Appendix H: site can inform and structure data without becoming a marketplace.
Conclusion: feature should remain absent.
```
**Tầng 5 — UPGRADE CARD:** Không tạo upgrade vì FIT < 15 hoặc vi phạm constraint.

**Tầng 6 — SKIP JUSTIFICATION:**
- Skip vì: Outside Vinh Long local discovery scope.
- Anti-pattern nếu copy: Copy-paste marketplace gap.
- Revisit khi: Revisit only as outbound links in guides, not product.

**Tầng 7 — INNOVATION:** Replace with local trust/action alternative: source badge, Zalo CTA, itinerary/share, or community Q&A depending on the journey stage.

### Gap G-60: Auto-translation of UGC

**Functional group:** F20 Monetization/Scope Guard  
**Severity:** 🟢 Nice-to-have / skip-by-constraint  
**Mapped skip:** S-23

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| Global platforms | Feature is common on large commercial platforms. | 7-9/10 | Works because they own inventory, payments, or ops teams. |
| vinhlong360 | Intentionally absent or out-of-scope. | N/A | No-booking showcase/community platform. |

**Tầng 2 — WHY:**

- User problem solved elsewhere: commercial commitment, inventory, loyalty, or support.
- Business value elsewhere: transaction take-rate or marketplace retention.
- Research/market note: for vinhlong360 this would create legal/ops debt before user value.
- Reasoning chain: feature exists on Global platforms -> requires scale/ops/legal basis -> vinhlong360 has no transaction constraint -> skip protects trust and solo-dev capacity.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 2 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 2 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 2 | No paid infra required beyond current stack. |
| Competitive advantage | 2 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 1 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **9/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- E08 shows the correct current conversion boundary: phone/Zalo/map contact tracking, not checkout.
- E11 SEO evidence plus legal sources in Appendix H: site can inform and structure data without becoming a marketplace.
Conclusion: feature should remain absent.
```
**Tầng 5 — UPGRADE CARD:** Không tạo upgrade vì FIT < 15 hoặc vi phạm constraint.

**Tầng 6 — SKIP JUSTIFICATION:**
- Skip vì: Vietnamese-only and legal/moderation ambiguity.
- Anti-pattern nếu copy: Maintenance debt.
- Revisit khi: Revisit with moderation language coverage.

**Tầng 7 — INNOVATION:** Replace with local trust/action alternative: source badge, Zalo CTA, itinerary/share, or community Q&A depending on the journey stage.

### Gap G-61: Live chat bot for businesses

**Functional group:** F20 Monetization/Scope Guard  
**Severity:** 🟢 Nice-to-have / skip-by-constraint  
**Mapped skip:** S-24

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| Klook support, OTA chat | Feature is common on large commercial platforms. | 7-9/10 | Works because they own inventory, payments, or ops teams. |
| vinhlong360 | Intentionally absent or out-of-scope. | N/A | No-booking showcase/community platform. |

**Tầng 2 — WHY:**

- User problem solved elsewhere: commercial commitment, inventory, loyalty, or support.
- Business value elsewhere: transaction take-rate or marketplace retention.
- Research/market note: for vinhlong360 this would create legal/ops debt before user value.
- Reasoning chain: feature exists on Klook support, OTA chat -> requires scale/ops/legal basis -> vinhlong360 has no transaction constraint -> skip protects trust and solo-dev capacity.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 2 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 2 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 2 | No paid infra required beyond current stack. |
| Competitive advantage | 2 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 2 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **10/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- E08 shows the correct current conversion boundary: phone/Zalo/map contact tracking, not checkout.
- E11 SEO evidence plus legal sources in Appendix H: site can inform and structure data without becoming a marketplace.
Conclusion: feature should remain absent.
```
**Tầng 5 — UPGRADE CARD:** Không tạo upgrade vì FIT < 15 hoặc vi phạm constraint.

**Tầng 6 — SKIP JUSTIFICATION:**
- Skip vì: Conflicts with Zalo-first behavior and creates operational expectation.
- Anti-pattern nếu copy: Complexity trap.
- Revisit khi: Revisit if OA automation becomes official channel.

**Tầng 7 — INNOVATION:** Replace with local trust/action alternative: source badge, Zalo CTA, itinerary/share, or community Q&A depending on the journey stage.

### Gap G-62: Inventory/package bundling

**Functional group:** F20 Monetization/Scope Guard  
**Severity:** 🟢 Nice-to-have / skip-by-constraint  
**Mapped skip:** S-25

**Tầng 1 — MAP:**

| Platform | Implementation | Quality | Unique twist |
| --- | --- | --- | --- |
| Klook,GYG,Viator | Feature is common on large commercial platforms. | 7-9/10 | Works because they own inventory, payments, or ops teams. |
| vinhlong360 | Intentionally absent or out-of-scope. | N/A | No-booking showcase/community platform. |

**Tầng 2 — WHY:**

- User problem solved elsewhere: commercial commitment, inventory, loyalty, or support.
- Business value elsewhere: transaction take-rate or marketplace retention.
- Research/market note: for vinhlong360 this would create legal/ops debt before user value.
- Reasoning chain: feature exists on Klook,GYG,Viator -> requires scale/ops/legal basis -> vinhlong360 has no transaction constraint -> skip protects trust and solo-dev capacity.

**Tầng 3 — FIT:**

| Criteria | Score | Reasoning |
| --- | --- | --- |
| User demand | 2 | Persona has a real journey-stage problem, not a vanity request. |
| Solo dev feasibility | 2 | Can be built by one developer using existing modules. |
| Budget fit (<1M VND/mo) | 2 | No paid infra required beyond current stack. |
| Competitive advantage | 1 | Creates local/localized advantage versus Google Maps or vinhlongtourist. |
| Maintenance burden | 1 | 5 means low ongoing tax; lower means recurring moderation/data work. |
| **Total** | **8/25** |  |

**Tầng 4 — CURRENT STATE (grep evidence):**
```text
- E08 shows the correct current conversion boundary: phone/Zalo/map contact tracking, not checkout.
- E11 SEO evidence plus legal sources in Appendix H: site can inform and structure data without becoming a marketplace.
Conclusion: feature should remain absent.
```
**Tầng 5 — UPGRADE CARD:** Không tạo upgrade vì FIT < 15 hoặc vi phạm constraint.

**Tầng 6 — SKIP JUSTIFICATION:**
- Skip vì: No booking or prices; bundles imply commercial offer.
- Anti-pattern nếu copy: Booking envy.
- Revisit khi: Revisit with official tour operators and contract model.

**Tầng 7 — INNOVATION:** Replace with local trust/action alternative: source badge, Zalo CTA, itinerary/share, or community Q&A depending on the journey stage.


## 5. Upgrade Roadmap

### 5.1 IMMEDIATE - tuần này

#### U-01: Zalo-first contact instrumentation

**Problem:** Phone/Zalo is present but funnel analytics and copy variants are not productized.  
**Current:** Zalo/phone contact evidence (E08).  
**Target:** Make Zalo/Phone/map clicks measurable by entity, source, viewport, and season.  
**Primary persona:** P1; **Secondary:** P3; **Journey:** RESEARCH,VISIT.  
**Effort:** BE 0d / FE 1.5d / DB 0d = 1.5d.  
**Dependencies:** E08.  
**Files to change:** see evidence appendix for E08; exact implementation should touch the listed API/page/component first.  
**Metric:** contact CTR, Zalo clicks/entity, phone clicks/entity.  
**Risk:** LOW; maintenance tax approx 1h/month.

**Sub-features:** data/state, mobile UI, instrumentation.  
**Optimizations:** 360px QA, lazy loading/a11y labels, no-booking guard.

#### U-02: Source and last-verified block on detail

**Problem:** Admin has data-quality tools but public detail lacks obvious source/freshness confidence.  
**Current:** Admin/data quality/media evidence (E13).  
**Target:** Show 'nguồn / cập nhật / báo sai' near practical facts.  
**Primary persona:** P1; **Secondary:** P3; **Journey:** RESEARCH,VISIT.  
**Effort:** BE 1d / FE 2d / DB 0d = 3d.  
**Dependencies:** E13.  
**Files to change:** see evidence appendix for E13; exact implementation should touch the listed API/page/component first.  
**Metric:** report clicks, stale-entity fixes, trust-card impressions.  
**Risk:** LOW; maintenance tax approx 1h/month.

**Sub-features:** data/state, mobile UI, instrumentation.  
**Optimizations:** 360px QA, lazy loading/a11y labels, no-booking guard.

#### U-03: Applied filter overview and no-results recovery

**Problem:** Catalog filters exist but applied-filter context and recovery are thin on mobile.  
**Current:** Search and browse evidence (E02).  
**Target:** Add removable filter chips, result explanation, and suggested fallback searches.  
**Primary persona:** P1; **Secondary:** P4; **Journey:** DISCOVER,RESEARCH.  
**Effort:** BE 0d / FE 2d / DB 0d = 2d.  
**Dependencies:** E02.  
**Files to change:** see evidence appendix for E02; exact implementation should touch the listed API/page/component first.  
**Metric:** filter-clear rate, zero-result exits, search refinements.  
**Risk:** LOW; maintenance tax approx 1h/month.

**Sub-features:** data/state, mobile UI, instrumentation.  
**Optimizations:** 360px QA, lazy loading/a11y labels, no-booking guard.

#### U-04: Review sort, filter, and photo-first mode

**Problem:** Reviews have form/photos/helpful/distribution but lack robust sort/filter controls.  
**Current:** Reviews evidence (E05).  
**Target:** Sort by newest/helpful/photo/star and let photo reviews lead trust decisions.  
**Primary persona:** P1; **Secondary:** P2; **Journey:** RESEARCH,SHARE.  
**Effort:** BE 1.5d / FE 2.5d / DB 0d = 4.0d.  
**Dependencies:** E05.  
**Files to change:** see evidence appendix for E05; exact implementation should touch the listed API/page/component first.  
**Metric:** review reads, photo-review opens, helpful votes.  
**Risk:** MED; maintenance tax approx 3h/month.

**Sub-features:** data/state, mobile UI, instrumentation.  
**Optimizations:** 360px QA, lazy loading/a11y labels, no-booking guard.

#### U-05: Itinerary print/export/share polish

**Problem:** Plans publish/share but public shared page is sparse and no print/export exists.  
**Current:** Saved and itinerary evidence (E09).  
**Target:** Add print stylesheet, copyable Zalo text, and compact offline route summary.  
**Primary persona:** P5; **Secondary:** P1; **Journey:** PLAN,VISIT.  
**Effort:** BE 0d / FE 2.5d / DB 0d = 2.5d.  
**Dependencies:** E09.  
**Files to change:** see evidence appendix for E09; exact implementation should touch the listed API/page/component first.  
**Metric:** plans shared, print/export clicks, shared-plan return visits.  
**Risk:** LOW; maintenance tax approx 1h/month.

**Sub-features:** data/state, mobile UI, instrumentation.  
**Optimizations:** 360px QA, lazy loading/a11y labels, no-booking guard.

#### U-06: Map list-plus-map synchronized discovery

**Problem:** Map pins/clusters exist; list context and selected pin state are limited.  
**Current:** Map evidence (E03).  
**Target:** Add mobile bottom list, selected entity preview, and filter-count feedback.  
**Primary persona:** P1; **Secondary:** P5; **Journey:** DISCOVER,PLAN,VISIT.  
**Effort:** BE 0.5d / FE 2.5d / DB 0d = 3.0d.  
**Dependencies:** E03.  
**Files to change:** see evidence appendix for E03; exact implementation should touch the listed API/page/component first.  
**Metric:** map interactions/session, pin-to-detail CTR.  
**Risk:** MED; maintenance tax approx 3h/month.

**Sub-features:** data/state, mobile UI, instrumentation.  
**Optimizations:** 360px QA, lazy loading/a11y labels, no-booking guard.

#### U-07: Know-before-you-go completion pass

**Problem:** Detail page has practical sections but not consistently complete for hours, parking, age, weather, peak days.  
**Current:** Entity detail and gallery evidence (E04).  
**Target:** Standardize short practical facts with admin prompts for missing fields.  
**Primary persona:** P1; **Secondary:** P3; **Journey:** RESEARCH,VISIT.  
**Effort:** BE 0.5d / FE 1.5d / DB 0d = 2.0d.  
**Dependencies:** E04.  
**Files to change:** see evidence appendix for E04; exact implementation should touch the listed API/page/component first.  
**Metric:** KBYG coverage %, contact click rate after KBYG.  
**Risk:** LOW; maintenance tax approx 1h/month.

**Sub-features:** data/state, mobile UI, instrumentation.  
**Optimizations:** 360px QA, lazy loading/a11y labels, no-booking guard.

#### U-08: Public correction/report-info CTA

**Problem:** Public reporting exists but is not attached to every practical fact.  
**Current:** Admin/data quality/media evidence (E13).  
**Target:** Allow 'báo sai thông tin này' for phone/hours/address/source.  
**Primary persona:** P1; **Secondary:** P2; **Journey:** RESEARCH,SHARE.  
**Effort:** BE 1d / FE 1.5d / DB 0d = 2.5d.  
**Dependencies:** E13.  
**Files to change:** see evidence appendix for E13; exact implementation should touch the listed API/page/component first.  
**Metric:** reports/entity, correction SLA.  
**Risk:** LOW; maintenance tax approx 1h/month.

**Sub-features:** data/state, mobile UI, instrumentation.  
**Optimizations:** 360px QA, lazy loading/a11y labels, no-booking guard.

#### U-09: Entity Q&A surfaced in detail

**Problem:** Question post type and best answer exist, but detail pages should surface entity-specific unresolved Q&A.  
**Current:** Community evidence (E06).  
**Target:** Add Q&A tab/rail with accepted answer, ask-local CTA, and local contributor prompt.  
**Primary persona:** P1; **Secondary:** P2; **Journey:** RESEARCH,SHARE.  
**Effort:** BE 1d / FE 2d / DB 0d = 3d.  
**Dependencies:** E06.  
**Files to change:** see evidence appendix for E06; exact implementation should touch the listed API/page/component first.  
**Metric:** questions answered, accepted-answer rate.  
**Risk:** LOW; maintenance tax approx 1h/month.

**Sub-features:** data/state, mobile UI, instrumentation.  
**Optimizations:** 360px QA, lazy loading/a11y labels, no-booking guard.

#### U-10: Image attribution and contribution prompts

**Problem:** Admin image credits exist and UGC images exist, but attribution/contribution prompts are inconsistent.  
**Current:** Entity detail and gallery evidence (E04).  
**Target:** Show credit in galleries and prompt locals for missing real photos.  
**Primary persona:** P2; **Secondary:** P3; **Journey:** SHARE,RETURN.  
**Effort:** BE 0.5d / FE 2d / DB 0d = 2.5d.  
**Dependencies:** E04.  
**Files to change:** see evidence appendix for E04; exact implementation should touch the listed API/page/component first.  
**Metric:** photo coverage %, credited-photo share.  
**Risk:** LOW; maintenance tax approx 1h/month.

**Sub-features:** data/state, mobile UI, instrumentation.  
**Optimizations:** 360px QA, lazy loading/a11y labels, no-booking guard.

### 5.2 SHORT-TERM - tháng này

#### U-11: Owner/admin response to reviews

**Problem:** Reviews lack an official response object even though moderation/admin exists.  
**Current:** Reviews evidence (E05).  
**Target:** Let admin/verified entity owner respond once per review with moderation audit.  
**Primary persona:** P3; **Secondary:** P2; **Journey:** RESEARCH,SHARE.  
**Effort:** BE 2d / FE 2d / DB 0.5d = 4.5d.  
**Dependencies:** E05.  
**Files to change:** see evidence appendix for E05; exact implementation should touch the listed API/page/component first.  
**Metric:** response coverage, negative-review follow-up.  
**Risk:** MED; maintenance tax approx 3h/month.

**Sub-features:** data/state, mobile UI, instrumentation.  
**Optimizations:** 360px QA, lazy loading/a11y labels, no-booking guard.

#### U-12: Review structured data from real UGC

**Problem:** JSON-LD exists; ensure aggregate ratings use first-party UGC, not copied Google reviews.  
**Current:** SEO evidence (E11).  
**Target:** Emit compliant AggregateRating only where eligible and hide when data is thin.  
**Primary persona:** P1; **Secondary:** P4; **Journey:** RESEARCH.  
**Effort:** BE 1d / FE 1d / DB 0d = 2d.  
**Dependencies:** E11.  
**Files to change:** see evidence appendix for E11; exact implementation should touch the listed API/page/component first.  
**Metric:** rich-result eligibility, schema validation.  
**Risk:** MED; maintenance tax approx 3h/month.

**Sub-features:** data/state, mobile UI, instrumentation.  
**Optimizations:** 360px QA, lazy loading/a11y labels, no-booking guard.

#### U-13: Seasonal trip packs before peaks

**Problem:** Seasonal browse exists but not packaged as pre-peak campaign pages.  
**Current:** Search and browse evidence (E02).  
**Target:** Create Tet/summer/30-4/2-9 packs with places, food, route, contact notes.  
**Primary persona:** P1; **Secondary:** P4; **Journey:** DISCOVER,PLAN.  
**Effort:** BE 0.5d / FE 3d / DB 0d = 3.5d.  
**Dependencies:** E02.  
**Files to change:** see evidence appendix for E02; exact implementation should touch the listed API/page/component first.  
**Metric:** season page sessions, saves from season pages.  
**Risk:** LOW; maintenance tax approx 1h/month.

**Sub-features:** data/state, mobile UI, instrumentation.  
**Optimizations:** 360px QA, lazy loading/a11y labels, no-booking guard.

#### U-14: Region landing pages with mini-itinerary

**Problem:** Area pages exist but can better answer 'đi đâu trong 1 ngày ở khu này'.  
**Current:** Search and browse evidence (E02).  
**Target:** Add 3-stop mini routes, local food, contact-ready POIs.  
**Primary persona:** P1; **Secondary:** P5; **Journey:** DISCOVER,PLAN.  
**Effort:** BE 0.5d / FE 3d / DB 0d = 3.5d.  
**Dependencies:** E02.  
**Files to change:** see evidence appendix for E02; exact implementation should touch the listed API/page/component first.  
**Metric:** area page depth, itinerary adds from area.  
**Risk:** LOW; maintenance tax approx 1h/month.

**Sub-features:** data/state, mobile UI, instrumentation.  
**Optimizations:** 360px QA, lazy loading/a11y labels, no-booking guard.

#### U-15: What's-new return feed

**Problem:** Recently viewed and feeds exist, but return users need 'mới cập nhật' and 'review mới'.  
**Current:** Community evidence (E06).  
**Target:** Show new reviews/entities/events since last visit with local storage fallback.  
**Primary persona:** P4; **Secondary:** P2; **Journey:** RETURN.  
**Effort:** BE 1d / FE 2d / DB 0d = 3d.  
**Dependencies:** E06.  
**Files to change:** see evidence appendix for E06; exact implementation should touch the listed API/page/component first.  
**Metric:** return sessions, feed clicks.  
**Risk:** LOW; maintenance tax approx 1h/month.

**Sub-features:** data/state, mobile UI, instrumentation.  
**Optimizations:** 360px QA, lazy loading/a11y labels, no-booking guard.

#### U-16: Shared-plan OG and Zalo preview optimizer

**Problem:** Shared plans fetch public data but preview cards are sparse.  
**Current:** Saved and itinerary evidence (E09).  
**Target:** Generate title/description/image for shared plan links and Zalo/Facebook OG.  
**Primary persona:** P5; **Secondary:** P1; **Journey:** PLAN.  
**Effort:** BE 0.5d / FE 1.5d / DB 0d = 2.0d.  
**Dependencies:** E09.  
**Files to change:** see evidence appendix for E09; exact implementation should touch the listed API/page/component first.  
**Metric:** shared-link CTR, preview image coverage.  
**Risk:** LOW; maintenance tax approx 1h/month.

**Sub-features:** data/state, mobile UI, instrumentation.  
**Optimizations:** 360px QA, lazy loading/a11y labels, no-booking guard.

#### U-17: Admin stale-content queue

**Problem:** Data-quality review exists but stale public facts need a task queue.  
**Current:** Admin/data quality/media evidence (E13).  
**Target:** Queue entities by stale phone/hours/source/image and batch assign status.  
**Primary persona:** P3; **Secondary:** P1; **Journey:** RETURN,VISIT.  
**Effort:** BE 2d / FE 2d / DB 0.5d = 4.5d.  
**Dependencies:** E13.  
**Files to change:** see evidence appendix for E13; exact implementation should touch the listed API/page/component first.  
**Metric:** stale items closed/week, public stale badge reduction.  
**Risk:** MED; maintenance tax approx 3h/month.

**Sub-features:** data/state, mobile UI, instrumentation.  
**Optimizations:** 360px QA, lazy loading/a11y labels, no-booking guard.

#### U-18: Mobile/a11y visual QA checklist in CI docs

**Problem:** Responsive code exists; need repeatable 360px/390px QA checks for text overlap and controls.  
**Current:** Performance/PWA/images evidence (E12).  
**Target:** Document/playwright smoke screenshots for public high-traffic pages.  
**Primary persona:** P1; **Secondary:** P3; **Journey:** DISCOVER,RESEARCH.  
**Effort:** BE 0d / FE 2d / DB 0d = 2d.  
**Dependencies:** E12.  
**Files to change:** see evidence appendix for E12; exact implementation should touch the listed API/page/component first.  
**Metric:** mobile visual regressions caught.  
**Risk:** LOW; maintenance tax approx 1h/month.

**Sub-features:** data/state, mobile UI, instrumentation.  
**Optimizations:** 360px QA, lazy loading/a11y labels, no-booking guard.

#### U-19: Offline saved plan snapshot

**Problem:** SW caches assets/API generically but plans are not explicitly made offline-safe.  
**Current:** Performance/PWA/images evidence (E12).  
**Target:** Cache saved plan/detail snapshots and show offline banner.  
**Primary persona:** P5; **Secondary:** P1; **Journey:** PLAN,VISIT.  
**Effort:** BE 1d / FE 2.5d / DB 0d = 3.5d.  
**Dependencies:** E12.  
**Files to change:** see evidence appendix for E12; exact implementation should touch the listed API/page/component first.  
**Metric:** offline plan opens, failed API fallback rate.  
**Risk:** MED; maintenance tax approx 3h/month.

**Sub-features:** data/state, mobile UI, instrumentation.  
**Optimizations:** 360px QA, lazy loading/a11y labels, no-booking guard.

#### U-20: Post-visit review prompt from visited state

**Problem:** Visit tracking exists but does not drive a timely review prompt.  
**Current:** Reviews evidence (E05).  
**Target:** After user marks visited, show lightweight review/tag/photo prompt.  
**Primary persona:** P2; **Secondary:** P4; **Journey:** SHARE,RETURN.  
**Effort:** BE 1d / FE 2d / DB 0d = 3d.  
**Dependencies:** E05.  
**Files to change:** see evidence appendix for E05; exact implementation should touch the listed API/page/component first.  
**Metric:** visited-to-review conversion.  
**Risk:** LOW; maintenance tax approx 1h/month.

**Sub-features:** data/state, mobile UI, instrumentation.  
**Optimizations:** 360px QA, lazy loading/a11y labels, no-booking guard.

#### U-21: Local guide trust cards

**Problem:** Profiles and stats exist; trust needs local expertise context by area/type.  
**Current:** Community evidence (E06).  
**Target:** Show area badges, top helpful answers, photo/review mix, and joined date.  
**Primary persona:** P2; **Secondary:** P1; **Journey:** RESEARCH,SHARE.  
**Effort:** BE 1d / FE 2d / DB 0d = 3d.  
**Dependencies:** E06.  
**Files to change:** see evidence appendix for E06; exact implementation should touch the listed API/page/component first.  
**Metric:** profile CTR, helpful vote rate.  
**Risk:** LOW; maintenance tax approx 1h/month.

**Sub-features:** data/state, mobile UI, instrumentation.  
**Optimizations:** 360px QA, lazy loading/a11y labels, no-booking guard.

#### U-22: Contact funnel dashboard

**Problem:** Contact action tracking exists; admin needs funnel view by entity/page/season.  
**Current:** Admin analytics/settings evidence (E14).  
**Target:** Add contact/save/plan/search dashboards with CSV.  
**Primary persona:** P3; **Secondary:** P1; **Journey:** VISIT.  
**Effort:** BE 1d / FE 2d / DB 0d = 3d.  
**Dependencies:** E14.  
**Files to change:** see evidence appendix for E14; exact implementation should touch the listed API/page/component first.  
**Metric:** contact CTR by source, top converting entities.  
**Risk:** LOW; maintenance tax approx 1h/month.

**Sub-features:** data/state, mobile UI, instrumentation.  
**Optimizations:** 360px QA, lazy loading/a11y labels, no-booking guard.

### 5.3 MEDIUM-TERM - quý này

#### U-23: Collaborative itinerary notes/votes via link

**Problem:** Shared plans are read-only; groups coordinate in Zalo with no structured feedback.  
**Current:** Saved and itinerary evidence (E09).  
**Target:** Add optional lightweight vote/comment token per shared plan.  
**Primary persona:** P5; **Secondary:** P1; **Journey:** PLAN.  
**Effort:** BE 3d / FE 4d / DB 1d = 8d.  
**Dependencies:** E09.  
**Files to change:** see evidence appendix for E09; exact implementation should touch the listed API/page/component first.  
**Metric:** plans with feedback, edits after share.  
**Risk:** MED; maintenance tax approx 3h/month.

**Sub-features:** data/state, mobile UI, instrumentation.  
**Optimizations:** 360px QA, lazy loading/a11y labels, no-booking guard.

#### U-24: Q&A quality queue and accepted-answer highlights

**Problem:** Best answer exists; unanswered/stale questions need surfacing.  
**Current:** Community evidence (E06).  
**Target:** Queue unanswered entity questions and highlight accepted answers in detail.  
**Primary persona:** P2; **Secondary:** P1; **Journey:** RESEARCH,SHARE.  
**Effort:** BE 1.5d / FE 2d / DB 0d = 3.5d.  
**Dependencies:** E06.  
**Files to change:** see evidence appendix for E06; exact implementation should touch the listed API/page/component first.  
**Metric:** answer SLA, accepted-answer view rate.  
**Risk:** LOW; maintenance tax approx 1h/month.

**Sub-features:** data/state, mobile UI, instrumentation.  
**Optimizations:** 360px QA, lazy loading/a11y labels, no-booking guard.

#### U-25: Ward one-screen day plan

**Problem:** Ward pages and map exist but not a scannable local day plan.  
**Current:** Map evidence (E03).  
**Target:** Add ward page route: breakfast/visit/lunch/photo/contact stops.  
**Primary persona:** P1; **Secondary:** P5; **Journey:** DISCOVER,PLAN.  
**Effort:** BE 1d / FE 3d / DB 0d = 4d.  
**Dependencies:** E03.  
**Files to change:** see evidence appendix for E03; exact implementation should touch the listed API/page/component first.  
**Metric:** ward plan saves, page dwell.  
**Risk:** LOW; maintenance tax approx 1h/month.

**Sub-features:** data/state, mobile UI, instrumentation.  
**Optimizations:** 360px QA, lazy loading/a11y labels, no-booking guard.

#### U-26: Event RSVP reminders

**Problem:** RSVP exists; reminders/digests do not.  
**Current:** Notifications/follow/block/RSVP evidence (E10).  
**Target:** Notify users before followed/RSVP events with opt-in preferences.  
**Primary persona:** P4; **Secondary:** P1; **Journey:** RETURN,VISIT.  
**Effort:** BE 2d / FE 2d / DB 0.5d = 4.5d.  
**Dependencies:** E10.  
**Files to change:** see evidence appendix for E10; exact implementation should touch the listed API/page/component first.  
**Metric:** RSVP reminder CTR, unsubscribes.  
**Risk:** MED; maintenance tax approx 3h/month.

**Sub-features:** data/state, mobile UI, instrumentation.  
**Optimizations:** 360px QA, lazy loading/a11y labels, no-booking guard.

#### U-27: Short video-link guide cards

**Problem:** No video streaming should be built, but video discovery matters.  
**Current:** SEO evidence (E11).  
**Target:** Store/link YouTube/TikTok references as external inspiration cards with fallback text.  
**Primary persona:** P1; **Secondary:** P4; **Journey:** DISCOVER,RESEARCH.  
**Effort:** BE 0.5d / FE 2d / DB 0d = 2.5d.  
**Dependencies:** E11.  
**Files to change:** see evidence appendix for E11; exact implementation should touch the listed API/page/component first.  
**Metric:** video-link clicks, detail saves after video card.  
**Risk:** LOW; maintenance tax approx 1h/month.

**Sub-features:** data/state, mobile UI, instrumentation.  
**Optimizations:** 360px QA, lazy loading/a11y labels, no-booking guard.

#### U-28: Public themed collection pages

**Problem:** Saved exists for users; public editorial/community collections are missing.  
**Current:** Saved and itinerary evidence (E09).  
**Target:** Create collection model or site-setting driven curated lists.  
**Primary persona:** P1; **Secondary:** P4; **Journey:** DISCOVER,PLAN.  
**Effort:** BE 1.5d / FE 3d / DB 0.5d = 5.0d.  
**Dependencies:** E09.  
**Files to change:** see evidence appendix for E09; exact implementation should touch the listed API/page/component first.  
**Metric:** collection sessions, saves/collection.  
**Risk:** MED; maintenance tax approx 3h/month.

**Sub-features:** data/state, mobile UI, instrumentation.  
**Optimizations:** 360px QA, lazy loading/a11y labels, no-booking guard.

#### U-29: Rule-based similar recommendations

**Problem:** Related/nearby exists; make logic transparent and season-aware.  
**Current:** Search and browse evidence (E02).  
**Target:** Recommend by area/type/season/visited exclusion; no ML engine.  
**Primary persona:** P1; **Secondary:** P4; **Journey:** RESEARCH,RETURN.  
**Effort:** BE 1d / FE 2.5d / DB 0d = 3.5d.  
**Dependencies:** E02.  
**Files to change:** see evidence appendix for E02; exact implementation should touch the listed API/page/component first.  
**Metric:** related CTR, repeat detail views.  
**Risk:** LOW; maintenance tax approx 1h/month.

**Sub-features:** data/state, mobile UI, instrumentation.  
**Optimizations:** 360px QA, lazy loading/a11y labels, no-booking guard.

#### U-30: Partner/entity claim workflow

**Problem:** Contact page exists; claim workflow is email-based and not tracked.  
**Current:** Admin analytics/settings evidence (E14).  
**Target:** Create claim form queue with phone/Zalo verification and admin audit.  
**Primary persona:** P3; **Secondary:** P1; **Journey:** RESEARCH,VISIT.  
**Effort:** BE 2.5d / FE 3d / DB 0.5d = 6.0d.  
**Dependencies:** E14.  
**Files to change:** see evidence appendix for E14; exact implementation should touch the listed API/page/component first.  
**Metric:** claims submitted, verified claims.  
**Risk:** MED; maintenance tax approx 3h/month.

**Sub-features:** data/state, mobile UI, instrumentation.  
**Optimizations:** 360px QA, lazy loading/a11y labels, no-booking guard.

#### U-31: Search zero-result KPI and content gap queue

**Problem:** Search works but no visible zero-result content gap workflow.  
**Current:** Admin analytics/settings evidence (E14).  
**Target:** Persist/analyze zero-results and make admin tasks.  
**Primary persona:** P3; **Secondary:** P1; **Journey:** DISCOVER.  
**Effort:** BE 2d / FE 2d / DB 0d = 4d.  
**Dependencies:** E14.  
**Files to change:** see evidence appendix for E14; exact implementation should touch the listed API/page/component first.  
**Metric:** zero-result rate, new content from query gaps.  
**Risk:** LOW; maintenance tax approx 1h/month.

**Sub-features:** data/state, mobile UI, instrumentation.  
**Optimizations:** 360px QA, lazy loading/a11y labels, no-booking guard.

### 5.4 BACKLOG

#### U-32: Transport practical guide without live prices

**Problem:** Users need getting-around context; live transport APIs are overkill.  
**Current:** Map evidence (E03).  
**Target:** Static route/boat/ferry/taxi notes with source/freshness date.  
**Primary persona:** P1; **Secondary:** P5; **Journey:** PLAN,VISIT.  
**Effort:** BE 0.5d / FE 3d / DB 0d = 3.5d.  
**Dependencies:** E03.  
**Files to change:** see evidence appendix for E03; exact implementation should touch the listed API/page/component first.  
**Metric:** guide views, directions clicks.  
**Risk:** LOW; maintenance tax approx 1h/month.

**Sub-features:** data/state, mobile UI, instrumentation.  
**Optimizations:** 360px QA, lazy loading/a11y labels, no-booking guard.

#### U-33: Manual weather/season warning banners

**Problem:** Season data exists; risk/flood/heat advisories need manual admin override.  
**Current:** Admin analytics/settings evidence (E14).  
**Target:** Site-setting banner by area/type with expiry.  
**Primary persona:** P3; **Secondary:** P1; **Journey:** VISIT,RETURN.  
**Effort:** BE 1d / FE 2d / DB 0d = 3d.  
**Dependencies:** E14.  
**Files to change:** see evidence appendix for E14; exact implementation should touch the listed API/page/component first.  
**Metric:** banner CTR, expired-banner incidents.  
**Risk:** MED; maintenance tax approx 3h/month.

**Sub-features:** data/state, mobile UI, instrumentation.  
**Optimizations:** 360px QA, lazy loading/a11y labels, no-booking guard.

#### U-34: Printable route cue sheets

**Problem:** Print/export overlaps with U-05; later add route-stop cue details.  
**Current:** Saved and itinerary evidence (E09).  
**Target:** Generate compact route instructions for motorbike/family use.  
**Primary persona:** P5; **Secondary:** P1; **Journey:** PLAN,VISIT.  
**Effort:** BE 0d / FE 2d / DB 0d = 2d.  
**Dependencies:** E09.  
**Files to change:** see evidence appendix for E09; exact implementation should touch the listed API/page/component first.  
**Metric:** cue-sheet exports.  
**Risk:** LOW; maintenance tax approx 1h/month.

**Sub-features:** data/state, mobile UI, instrumentation.  
**Optimizations:** 360px QA, lazy loading/a11y labels, no-booking guard.

#### U-35: Community challenge campaigns

**Problem:** Leaderboard exists; campaign framing can motivate useful contributions.  
**Current:** Community evidence (E06).  
**Target:** Seasonal challenges for missing photos/tips with non-monetary recognition.  
**Primary persona:** P2; **Secondary:** P4; **Journey:** SHARE,RETURN.  
**Effort:** BE 1d / FE 3d / DB 0.5d = 4.5d.  
**Dependencies:** E06.  
**Files to change:** see evidence appendix for E06; exact implementation should touch the listed API/page/component first.  
**Metric:** challenge submissions, useful approval rate.  
**Risk:** MED; maintenance tax approx 3h/month.

**Sub-features:** data/state, mobile UI, instrumentation.  
**Optimizations:** 360px QA, lazy loading/a11y labels, no-booking guard.

#### U-36: Zalo OA handoff templates

**Problem:** Zalo CTA exists but message content is generic.  
**Current:** Zalo/phone contact evidence (E08).  
**Target:** Prefill message templates: hỏi giờ mở cửa, đặt bàn offline, hỏi đường.  
**Primary persona:** P1; **Secondary:** P3; **Journey:** VISIT.  
**Effort:** BE 1d / FE 2d / DB 0d = 3d.  
**Dependencies:** E08.  
**Files to change:** see evidence appendix for E08; exact implementation should touch the listed API/page/component first.  
**Metric:** Zalo click completion, repeat contact.  
**Risk:** LOW; maintenance tax approx 1h/month.

**Sub-features:** data/state, mobile UI, instrumentation.  
**Optimizations:** 360px QA, lazy loading/a11y labels, no-booking guard.

#### U-37: Commercial boundary and partner transparency page

**Problem:** As partner features grow, users need clear no-payment/no-affiliate rules.  
**Current:** SEO evidence (E11).  
**Target:** Publish partner/advertising policy and label showcase content.  
**Primary persona:** P3; **Secondary:** P1; **Journey:** RESEARCH.  
**Effort:** BE 0.5d / FE 1.5d / DB 0d = 2.0d.  
**Dependencies:** E11.  
**Files to change:** see evidence appendix for E11; exact implementation should touch the listed API/page/component first.  
**Metric:** policy views, complaint reduction.  
**Risk:** LOW; maintenance tax approx 1h/month.

**Sub-features:** data/state, mobile UI, instrumentation.  
**Optimizations:** 360px QA, lazy loading/a11y labels, no-booking guard.

### 5.5 INNOVATION

- I-01 Mùa này đi đâu ở Vĩnh Long (Discovery) — Là du khách Sài Gòn, tôi muốn biết mùa này nên ăn/trải nghiệm gì để không đi hụt mùa. Success metric: season page saves/contact clicks.
- I-02 Hỏi người bản địa gần điểm này (Community) — Là người bản địa, tôi muốn trả lời câu hỏi theo địa điểm để được ghi nhận và giúp khách đúng ngữ cảnh. Success metric: answer SLA and accepted answer rate.
- I-03 Bản đồ ăn-chơi theo buổi (UX) — Là du khách cuối tuần, tôi muốn xem điểm phù hợp sáng/trưa/chiều/tối để không phải tự ghép lịch. Success metric: route starts and map filter use.
- I-04 Đi cùng gia đình (Planning) — Là người plan cho gia đình 4-8 người, tôi muốn biết điểm nào phù hợp người lớn tuổi/trẻ em để chốt lịch nhanh. Success metric: family filter use and shares.
- I-05 Sổ tay nguồn tin địa phương (Trust) — Là admin, tôi muốn mỗi fact có nguồn và hạn kiểm lại để tránh site thành kho thông tin cũ. Success metric: stale fact reduction.
- I-06 Một link gửi nhóm Zalo (Social) — Là người lập lịch, tôi muốn gửi một link có tóm tắt ngắn để cả nhà xem được ngay trong Zalo. Success metric: shared plan opens.
- I-07 Chuyến đi không hụt hẫng (Visit) — Là du khách, tôi muốn biết trước điểm nào hay đóng cửa/ngập/đông để khỏi mất công chạy xe. Success metric: wrong-info reports resolved.
- I-08 Dấu chân quê mình (Community) — Là người bản địa, tôi muốn đóng góp ảnh/tips theo xã/phường để thấy quê mình hiện lên đẹp hơn. Success metric: approved local contributions.
- I-09 Chợ nổi/chợ đêm thực tế hôm nay (Discovery) — Là khách đi trong ngày, tôi muốn biết giờ nên đến và mẹo thực tế để không đến sai thời điểm. Success metric: time-tip reads and contact clicks.
- I-10 OCOP dùng thử gần tuyến đi (Content) — Là du khách, tôi muốn biết đặc sản nào mua/thử gần tuyến của mình để ủng hộ địa phương mà không vòng xe. Success metric: product saves/contact clicks.

**Dependency graph:**
```text
U-02 -> U-17 -> U-33
U-03 -> U-06 -> U-25
U-04 -> U-11 -> U-12
U-05 -> U-16 -> U-23 -> U-34
U-08 -> U-02/U-17
U-15 -> U-20 -> U-26
U-22 -> U-30 -> U-37
U-18 -> all public FE upgrades
```

## 6. Skip Justification Table

| # | Feature | Platform(s) | FIT score | Skip reason | Anti-pattern | Revisit when |
| --- | --- | --- | --- | --- | --- | --- |
| S-01 | Booking/payment/checkout | GYG,Klook,Viator,Traveloka,Airbnb | 8/25 | Violates explicit constraint; triggers e-commerce ops/legal/support. | Booking envy | Only revisit if business becomes licensed marketplace with ops team. |
| S-02 | Payment gateway | Klook,Traveloka,Airbnb | 7/25 | No on-site transaction; <1M VND/month budget should not carry fraud/payment support. | Legal minefield | Revisit with formal merchant, accounting, refund policy, support SLA. |
| S-03 | Dynamic pricing | OTA marketplaces | 6/25 | No inventory/availability; would create false promise. | Copy-paste gap | Revisit only with real operator inventory. |
| S-04 | Availability calendar | GYG,Klook,Airbnb,Viator | 8/25 | Requires live operator capacity and stale-data babysitting. | Maintenance debt | Revisit when verified partners update availability weekly. |
| S-05 | Verified purchase badge | Klook,GYG,Airbnb,Traveloka | 7/25 | No purchase event exists; badge would be misleading. | Dark trust pattern | Revisit only after legitimate transaction source. |
| S-06 | Host/guest marketplace roles | Airbnb | 9/25 | vinhlong360 is showcase/community, not lodging marketplace. | Feature bloat | Revisit with marketplace strategy and legal review. |
| S-07 | Native mobile app | Klook,Airbnb,Google,Atlas,VoiceMap | 10/25 | Web-only constraint and solo dev maintenance burden. | Premature platform split | Revisit after >50K MAU with retention proven. |
| S-08 | Real-time user messaging | Airbnb,Tripadvisor inbox | 9/25 | Users already use Zalo; moderation and abuse burden is high. | Complexity trap | Revisit if Zalo handoff fails and moderation team exists. |
| S-09 | ML recommendation engine | Google,Airbnb,Klook | 10/25 | Need data volume, infra, explainability; rule-based is enough. | Over-engineering | Revisit after >100K monthly interactions. |
| S-10 | Video streaming hosting | TikTok/YouTube style | 8/25 | Bandwidth/storage/moderation blow up; use external links. | Maintenance debt | Revisit only with CDN/storage budget and moderation team. |
| S-11 | AR/VR/3D tours | Some destination sites | 6/25 | High build cost, low immediate need for 10K-user travel planning. | Vanity feature | Revisit for a grant-funded heritage project. |
| S-12 | Multi-language | Klook,GYG,Airbnb,Traveloka | 11/25 | Prompt says Vietnamese only; translation creates stale legal/practical facts. | Maintenance debt | Revisit when inbound foreign traffic is proven. |
| S-13 | Affiliate booking links | Google Travel,Viator,Traveloka | 8/25 | Constraint forbids affiliate links; trust cost high. | Commercial opacity | Revisit only with transparent partner policy. |
| S-14 | Heavy analytics SaaS | Growth teams | 9/25 | Budget and privacy constraints; self-hosted/minimal metrics enough. | Premature optimization | Revisit with paid growth team. |
| S-15 | Flash-sale countdowns | Klook,Traveloka | 6/25 | Creates fake urgency without real inventory. | Dark pattern | Never unless backed by real official event deadline. |
| S-16 | Referral credits/membership tiers | Klook,Airbnb,Atlas | 10/25 | Economic liability and anti-gaming burden; not core to trip success. | Vanity/growth bloat | Revisit after core retention metrics are stable. |
| S-17 | Exact price comparison aggregator | Google Travel | 7/25 | Requires crawling partners and price freshness; legal risk. | Data freshness trap | Revisit with signed partner feeds. |
| S-18 | Support ticketing system | OTAs | 11/25 | Zalo/phone/email enough; ticketing invites service SLA expectations. | Ops bloat | Revisit with dedicated support staff. |
| S-19 | Scrape/import Google reviews | Google Maps | 6/25 | Legal/API and trust risk; use own UGC and link out. | Legal minefield | Revisit only via compliant Google APIs and display rules. |
| S-20 | Check-in gamification | Foursquare/Swarm | 12/25 | Can become vanity metric and location privacy risk. | Vanity feature | Revisit when visit tracking has user demand. |
| S-21 | Complex badge economy | Tripadvisor,Klook | 12/25 | Leaderboard already exists; extra tiers create moderation/gaming. | Feature bloat | Revisit after contributor community is active. |
| S-22 | Flights/hotels integration | Google,Klook,Traveloka,Agoda | 6/25 | Outside Vinh Long local discovery scope. | Copy-paste marketplace gap | Revisit only as outbound links in guides, not product. |
| S-23 | Auto-translation of UGC | Global platforms | 9/25 | Vietnamese-only and legal/moderation ambiguity. | Maintenance debt | Revisit with moderation language coverage. |
| S-24 | Live chat bot for businesses | Klook support, OTA chat | 10/25 | Conflicts with Zalo-first behavior and creates operational expectation. | Complexity trap | Revisit if OA automation becomes official channel. |
| S-25 | Inventory/package bundling | Klook,GYG,Viator | 8/25 | No booking or prices; bundles imply commercial offer. | Booking envy | Revisit with official tour operators and contract model. |

## 7. Innovation Features

### I-01: Mùa này đi đâu ở Vĩnh Long

**Category:** Discovery  
**Inspiration:** Local season knowledge

**User story:**
> Là du khách Sài Gòn, tôi muốn biết mùa này nên ăn/trải nghiệm gì để không đi hụt mùa.

**Feature description:** This is intentionally local, Vietnamese, mobile-first, and no-booking. It turns knowledge that lives in Facebook/Zalo/offline locals into structured planning value. It should be small enough for a solo dev because it reuses entities, attributes, posts, plans, settings, and existing admin flows.

**Sub-features:**
1. Month-aware landing module — ship as a small, measurable slice.
2. Local warning/peak-day note — ship as a small, measurable slice.
3. Save to 1-day itinerary — ship as a small, measurable slice.

**Why this is unique for vinhlong360:** Large platforms know countries/cities; vinhlong360 can know fruit seasons, water levels, festival timing, and local closures.

**Implementation sketch:** BE: use season fields + settings; FE: homepage/season pages; Data: admin freshness notes; Effort: 4d; Risk: LOW

**Success metric:** season page saves/contact clicks

### I-02: Hỏi người bản địa gần điểm này

**Category:** Community  
**Inspiration:** Facebook group behavior made structured

**User story:**
> Là người bản địa, tôi muốn trả lời câu hỏi theo địa điểm để được ghi nhận và giúp khách đúng ngữ cảnh.

**Feature description:** This is intentionally local, Vietnamese, mobile-first, and no-booking. It turns knowledge that lives in Facebook/Zalo/offline locals into structured planning value. It should be small enough for a solo dev because it reuses entities, attributes, posts, plans, settings, and existing admin flows.

**Sub-features:**
1. Entity Q&A rail — ship as a small, measurable slice.
2. Accepted local answer — ship as a small, measurable slice.
3. Contributor trust badge — ship as a small, measurable slice.

**Why this is unique for vinhlong360:** Facebook has people but not structured entity context; OTAs have Q&A but not local pride loop.

**Implementation sketch:** BE: existing question/best_answer; FE: detail Q&A; Data: posts; Effort: 3d; Risk: LOW

**Success metric:** answer SLA and accepted answer rate

### I-03: Bản đồ ăn-chơi theo buổi

**Category:** UX  
**Inspiration:** Local day rhythm

**User story:**
> Là du khách cuối tuần, tôi muốn xem điểm phù hợp sáng/trưa/chiều/tối để không phải tự ghép lịch.

**Feature description:** This is intentionally local, Vietnamese, mobile-first, and no-booking. It turns knowledge that lives in Facebook/Zalo/offline locals into structured planning value. It should be small enough for a solo dev because it reuses entities, attributes, posts, plans, settings, and existing admin flows.

**Sub-features:**
1. Time-of-day tags — ship as a small, measurable slice.
2. Map filter by buổi — ship as a small, measurable slice.
3. Route cue for family/motorbike — ship as a small, measurable slice.

**Why this is unique for vinhlong360:** Global platforms show hours but not Vietnamese trip rhythm and meal timing.

**Implementation sketch:** BE: attributes tags; FE: map filter; Data: editorial/admin; Effort: 5d; Risk: LOW

**Success metric:** route starts and map filter use

### I-04: Đi cùng gia đình

**Category:** Planning  
**Inspiration:** Vietnamese group travel

**User story:**
> Là người plan cho gia đình 4-8 người, tôi muốn biết điểm nào phù hợp người lớn tuổi/trẻ em để chốt lịch nhanh.

**Feature description:** This is intentionally local, Vietnamese, mobile-first, and no-booking. It turns knowledge that lives in Facebook/Zalo/offline locals into structured planning value. It should be small enough for a solo dev because it reuses entities, attributes, posts, plans, settings, and existing admin flows.

**Sub-features:**
1. Family suitability chips — ship as a small, measurable slice.
2. Restroom/parking/shade facts — ship as a small, measurable slice.
3. Zalo share card — ship as a small, measurable slice.

**Why this is unique for vinhlong360:** Large platforms have generic amenities; local site can encode family practicalities.

**Implementation sketch:** BE: attributes; FE: detail + filters; Data: admin QA; Effort: 5d; Risk: LOW

**Success metric:** family filter use and shares

### I-05: Sổ tay nguồn tin địa phương

**Category:** Trust  
**Inspiration:** Data provenance moat

**User story:**
> Là admin, tôi muốn mỗi fact có nguồn và hạn kiểm lại để tránh site thành kho thông tin cũ.

**Feature description:** This is intentionally local, Vietnamese, mobile-first, and no-booking. It turns knowledge that lives in Facebook/Zalo/offline locals into structured planning value. It should be small enough for a solo dev because it reuses entities, attributes, posts, plans, settings, and existing admin flows.

**Sub-features:**
1. Source per fact — ship as a small, measurable slice.
2. Review-by date — ship as a small, measurable slice.
3. Public confidence badge — ship as a small, measurable slice.

**Why this is unique for vinhlong360:** Google has scale; vinhlong360 can have auditable local-source hygiene.

**Implementation sketch:** BE: attributes schema/settings; FE: detail block; Admin: stale queue; Effort: 6d; Risk: MED

**Success metric:** stale fact reduction

### I-06: Một link gửi nhóm Zalo

**Category:** Social  
**Inspiration:** Zalo-first sharing

**User story:**
> Là người lập lịch, tôi muốn gửi một link có tóm tắt ngắn để cả nhà xem được ngay trong Zalo.

**Feature description:** This is intentionally local, Vietnamese, mobile-first, and no-booking. It turns knowledge that lives in Facebook/Zalo/offline locals into structured planning value. It should be small enough for a solo dev because it reuses entities, attributes, posts, plans, settings, and existing admin flows.

**Sub-features:**
1. OG image per plan — ship as a small, measurable slice.
2. Copyable itinerary text — ship as a small, measurable slice.
3. Poll-like lightweight feedback — ship as a small, measurable slice.

**Why this is unique for vinhlong360:** Airbnb has collaborative wishlists, but not Zalo-specific Vietnamese group planning copy.

**Implementation sketch:** BE: shared plan meta; FE: share sheet; Data: plan stops; Effort: 4d; Risk: LOW

**Success metric:** shared plan opens

### I-07: Chuyến đi không hụt hẫng

**Category:** Visit  
**Inspiration:** Local practical warnings

**User story:**
> Là du khách, tôi muốn biết trước điểm nào hay đóng cửa/ngập/đông để khỏi mất công chạy xe.

**Feature description:** This is intentionally local, Vietnamese, mobile-first, and no-booking. It turns knowledge that lives in Facebook/Zalo/offline locals into structured planning value. It should be small enough for a solo dev because it reuses entities, attributes, posts, plans, settings, and existing admin flows.

**Sub-features:**
1. Admin warning banner — ship as a small, measurable slice.
2. User report wrong info — ship as a small, measurable slice.
3. Freshness SLA badge — ship as a small, measurable slice.

**Why this is unique for vinhlong360:** Large platforms may show hours, not hyperlocal day-by-day caveats.

**Implementation sketch:** BE: report + settings; FE: warnings; Admin: review queue; Effort: 5d; Risk: MED

**Success metric:** wrong-info reports resolved

### I-08: Dấu chân quê mình

**Category:** Community  
**Inspiration:** Pride-based contribution

**User story:**
> Là người bản địa, tôi muốn đóng góp ảnh/tips theo xã/phường để thấy quê mình hiện lên đẹp hơn.

**Feature description:** This is intentionally local, Vietnamese, mobile-first, and no-booking. It turns knowledge that lives in Facebook/Zalo/offline locals into structured planning value. It should be small enough for a solo dev because it reuses entities, attributes, posts, plans, settings, and existing admin flows.

**Sub-features:**
1. Ward contribution progress — ship as a small, measurable slice.
2. Missing photo prompts — ship as a small, measurable slice.
3. Local contributor credit — ship as a small, measurable slice.

**Why this is unique for vinhlong360:** Commercial platforms optimize inventory; vinhlong360 can optimize civic pride.

**Implementation sketch:** BE: stats query; FE: ward/profile cards; Data: UGC; Effort: 6d; Risk: LOW

**Success metric:** approved local contributions

### I-09: Chợ nổi/chợ đêm thực tế hôm nay

**Category:** Discovery  
**Inspiration:** Local operational nuance

**User story:**
> Là khách đi trong ngày, tôi muốn biết giờ nên đến và mẹo thực tế để không đến sai thời điểm.

**Feature description:** This is intentionally local, Vietnamese, mobile-first, and no-booking. It turns knowledge that lives in Facebook/Zalo/offline locals into structured planning value. It should be small enough for a solo dev because it reuses entities, attributes, posts, plans, settings, and existing admin flows.

**Sub-features:**
1. Best arrival time — ship as a small, measurable slice.
2. Local tip snippets — ship as a small, measurable slice.
3. Source/date stamp — ship as a small, measurable slice.

**Why this is unique for vinhlong360:** Generic map hours cannot encode experiential timing like early market windows.

**Implementation sketch:** BE: attributes; FE: detail KBYG; Admin: freshness; Effort: 3d; Risk: LOW

**Success metric:** time-tip reads and contact clicks

### I-10: OCOP dùng thử gần tuyến đi

**Category:** Content  
**Inspiration:** Local product-route connection

**User story:**
> Là du khách, tôi muốn biết đặc sản nào mua/thử gần tuyến của mình để ủng hộ địa phương mà không vòng xe.

**Feature description:** This is intentionally local, Vietnamese, mobile-first, and no-booking. It turns knowledge that lives in Facebook/Zalo/offline locals into structured planning value. It should be small enough for a solo dev because it reuses entities, attributes, posts, plans, settings, and existing admin flows.

**Sub-features:**
1. Product near route — ship as a small, measurable slice.
2. Contact/no-price CTA — ship as a small, measurable slice.
3. Source/producer note — ship as a small, measurable slice.

**Why this is unique for vinhlong360:** OTAs sell activities; vinhlong360 can connect OCOP, craft villages, and route geography without checkout.

**Implementation sketch:** BE: relationships; FE: route/nearby rail; Data: OCOP entities; Effort: 5d; Risk: LOW

**Success metric:** product saves/contact clicks


## 8. Implementation Estimates

| Upgrade | Type | Backend effort | Frontend effort | DB migration | Total person-days | Dependencies | Risk |
| --- | --- | --- | --- | --- | --- | --- | --- |
| U-01 | FE-only | 0d | 1.5d | No | 1.5d | E08 | LOW |
| U-02 | API+FE | 1d | 2d | No | 3d | E13 | LOW |
| U-03 | FE-only | 0d | 2d | No | 2d | E02 | LOW |
| U-04 | API+FE | 1.5d | 2.5d | No | 4.0d | E05 | MED |
| U-05 | FE-only | 0d | 2.5d | No | 2.5d | E09 | LOW |
| U-06 | API+FE | 0.5d | 2.5d | No | 3.0d | E03 | MED |
| U-07 | API+FE | 0.5d | 1.5d | No | 2.0d | E04 | LOW |
| U-08 | API+FE | 1d | 1.5d | No | 2.5d | E13 | LOW |
| U-09 | API+FE | 1d | 2d | No | 3d | E06 | LOW |
| U-10 | API+FE | 0.5d | 2d | No | 2.5d | E04 | LOW |
| U-11 | Full-stack | 2d | 2d | Yes | 4.5d | E05 | MED |
| U-12 | API+FE | 1d | 1d | No | 2d | E11 | MED |
| U-13 | API+FE | 0.5d | 3d | No | 3.5d | E02 | LOW |
| U-14 | API+FE | 0.5d | 3d | No | 3.5d | E02 | LOW |
| U-15 | API+FE | 1d | 2d | No | 3d | E06 | LOW |
| U-16 | API+FE | 0.5d | 1.5d | No | 2.0d | E09 | LOW |
| U-17 | Full-stack | 2d | 2d | Yes | 4.5d | E13 | MED |
| U-18 | FE-only | 0d | 2d | No | 2d | E12 | LOW |
| U-19 | API+FE | 1d | 2.5d | No | 3.5d | E12 | MED |
| U-20 | API+FE | 1d | 2d | No | 3d | E05 | LOW |
| U-21 | API+FE | 1d | 2d | No | 3d | E06 | LOW |
| U-22 | API+FE | 1d | 2d | No | 3d | E14 | LOW |
| U-23 | Full-stack | 3d | 4d | Yes | 8d | E09 | MED |
| U-24 | API+FE | 1.5d | 2d | No | 3.5d | E06 | LOW |
| U-25 | API+FE | 1d | 3d | No | 4d | E03 | LOW |
| U-26 | Full-stack | 2d | 2d | Yes | 4.5d | E10 | MED |
| U-27 | API+FE | 0.5d | 2d | No | 2.5d | E11 | LOW |
| U-28 | Full-stack | 1.5d | 3d | Yes | 5.0d | E09 | MED |
| U-29 | API+FE | 1d | 2.5d | No | 3.5d | E02 | LOW |
| U-30 | Full-stack | 2.5d | 3d | Yes | 6.0d | E14 | MED |
| U-31 | API+FE | 2d | 2d | No | 4d | E14 | LOW |
| U-32 | API+FE | 0.5d | 3d | No | 3.5d | E03 | LOW |
| U-33 | API+FE | 1d | 2d | No | 3d | E14 | MED |
| U-34 | FE-only | 0d | 2d | No | 2d | E09 | LOW |
| U-35 | Full-stack | 1d | 3d | Yes | 4.5d | E06 | MED |
| U-36 | API+FE | 1d | 2d | No | 3d | E08 | LOW |
| U-37 | API+FE | 0.5d | 1.5d | No | 2.0d | E11 | LOW |

**Summary:** P0=26.0d, P1=37.5d, P2=41.0d, P3=18.0d, Innovation ~=45d, **Total upgrades=122.5 person-days**.

## 9. Risk Assessment

| Risk | Probability | Impact | Mitigation | Related upgrades |
| --- | --- | --- | --- | --- |
| Stale practical data | HIGH | HIGH | Source/review-by date, stale queue, public report CTA | U-02,U-08,U-17,U-33 |
| UGC moderation load | MED | HIGH | Batch moderation, rate limits, reporting, clear rules | U-04,U-09,U-11,U-20,U-35 |
| Scope creep into booking | MED | HIGH | No-checkout guard, partner transparency page | U-30,U-37 |
| Mobile visual regressions | MED | MED | 360/390/414 screenshot QA | U-18 |
| Map performance | MED | MED | Lazy chunk, list fallback, cluster limits | U-06,U-25 |
| SEO structured-data misuse | LOW | HIGH | Only first-party reviews and validation | U-12 |
| Zalo deep-link changes | LOW | MED | Fallback phone/map/copy text | U-01,U-36 |
| Partner claims abuse | MED | MED | Phone/Zalo verification and admin approval | U-30 |
| Notification fatigue | MED | MED | Preferences, digest, opt-in event reminders | U-26 |
| Solo-dev maintenance tax | HIGH | MED | Favor settings/rule-based queues over bespoke ops | All |

**Top 3 risks cho solo dev:**
1. Data freshness: without source/review-by dates, trust decays quietly.
2. UGC moderation: every social feature needs report/rate-limit/admin tooling.
3. Booking envy: the fastest way to break scope is to imply price, slot, or payment without operations.

## 10. Functional Group Maturity Scorecard

| Group | Current score | Industry benchmark | Gap | Top 3 improvements |
| --- | --- | --- | --- | --- |
| F1 Discovery IA | 7.5 | 8.5 | 1.0 | homepage seasonal modules, local hidden-gem rails, what's-new strip |
| F2 Search & Filters | 7.2 | 9.0 | 1.8 | applied filter overview, mobile filter tray, sort by freshness |
| F3 Entity Detail | 7.7 | 8.8 | 1.1 | source/freshness card, hours confidence, owner response |
| F4 Reviews & Ratings | 7.0 | 8.7 | 1.7 | photo-first reviews, sort/filter reviews, owner/admin response |
| F5 Community & Reputation | 7.3 | 8.2 | 0.9 | local guide profile trust, accepted answer surfacing, contribution prompts |
| F6 UGC Creation & Moderation | 7.6 | 8.4 | 0.8 | review tags, post-visit prompts, batch moderation polish |
| F7 Saved & Collections | 6.4 | 8.5 | 2.1 | multi-list collections, collaborative list notes, offline saved snapshot |
| F8 Map & Navigation | 6.8 | 8.8 | 2.0 | map/list sync, route cue sheets, directions handoff |
| F9 Personalization & Return | 6.2 | 8.0 | 1.8 | what's new since last visit, visited-based prompts, seasonal return feed |
| F10 Itinerary Planning | 7.0 | 8.6 | 1.6 | print/export, group share feedback, route/time constraints |
| F11 Content Guides & SEO | 7.6 | 8.8 | 1.2 | short guide snippets, season pages, review schema nuance |
| F12 Mobile Performance & PWA | 7.1 | 8.5 | 1.4 | API offline cache, 360px visual QA, lighter map chunk UX |
| F13 Contact & Conversion | 8.1 | 8.0 | -0.1 | Zalo templates, contact funnel dashboard, fallback CTA logic |
| F14 Admin CMS | 8.0 | 8.5 | 0.5 | batch stale queue, entity claim workflow, content calendar |
| F15 Data Quality & Freshness | 7.4 | 8.6 | 1.2 | public freshness badge, source confidence, admin stale SLA |
| F16 Social Proof & Trust | 6.9 | 8.5 | 1.6 | verified local contributor, source transparency, avoid fake urgency |
| F17 Notifications & Follow | 7.1 | 8.0 | 0.9 | event reminders, digest preference, followed-entity changes |
| F18 Safety, Legal & Privacy | 7.8 | 8.4 | 0.6 | NĐ147 moderation workflow, PDP consent log polish, public rules clarity |
| F19 Analytics & Experimentation | 6.8 | 8.2 | 1.4 | contact/save/plan funnel, self-hosted metrics, source freshness KPI |
| F20 Monetization & Partnership | 4.8 | 7.0 | 2.2 | showcase packages, claim/partner workflow, no transaction boundary |
| **Average** | **7.1** | **8.4** | **1.3** |  |

## 11. Appendixes

### A. Platform Feature Inventory

| Platform | Category | Raw feature inventory | Adopt | Skip |
| --- | --- | --- | --- | --- |
| GetYourGuide | Tours & activities OTA | Hero destination/activity search, Destination pages with category chips, Activity cards with rating, review count, duration, price, Detail gallery with mobile carousel, Highlights, inclusions, meeting point, itinerary, Review list with traveler metadata, Cancellation policy and trust support, Wishlist/save, Curated collections and things-to-do guides, Mobile sticky booking CTA | Gallery-first detail hierarchy, highlights, cancellation-like practical notes, trusted-review prominence. | Availability, payment, voucher, verified purchase, fake urgency. |
| Klook | SEA travel activities super-app | Deal-led homepage, Deep category taxonomy, Destination/activity pages, Package selection chips, How-to-use and cancellation policy blocks, Photo reviews, Rating distribution, Klook credits, Promo codes and flash deals, App-download funnel | How-to-use blocks, short practical policy cards, photo-review emphasis. | Credits, promo codes, package pricing, flash sales. |
| Tripadvisor | Reviews, rankings, community | Destination search, Ranked lists, Reviews with helpful votes, Traveler photos, Forums by destination/theme, Q&A, Profiles and contribution counts, Badges and levels, Management responses, Trip boards | Helpful votes, Q&A, contribution recognition, management/admin response. | Global ranking badges and monetized restaurant/hotel booking surfaces. |
| Google Travel / Google Maps | Aggregation, map, trip planning | Map-first discovery, Knowledge panels, Saved places/lists, Directions and transit, Nearby categories, Hours and busy signals, Reviews/photos, Offline maps, Trip/Travel aggregation, Search integration | Map/list sync, saved-list mental model, direct directions link. | Trying to compete with turn-by-turn navigation or global business review volume. |
| Airbnb Experiences | Marketplace with local experiences | Category tabs, Map toggle, Wishlists, Collaborative wishlist notes/votes, Host profile, Rules/amenities, Reviews and host responses, Past trips, Experience categories, Trust and verification | Collaborative planning mechanics and local profile trust cards. | Host payout logic, guest booking rules, availability calendars. |
| Viator | Tours & activities OTA | Destination search, Warm/trending destinations, Tour cards, Free cancellation copy, Traveler reviews, Operator info, Mobile tickets, Price filters, Duration filters, Similar tours | Risk-reversal language adapted to 'go before you go' practical certainty. | Tour checkout and voucher flow. |
| Traveloka Xperience | SEA super-app activities | Things to Do tab, Country activity pages, Attraction deals, Voucher redemption, Review requests after visit, Relevant rating tags, App-first account, Promotions, Transport essentials, Customer support | Low-friction review tags after a planned/visited status. | Voucher, promotion and checkout machinery. |
| Atlas Obscura | Niche local discovery + community | Unique places directory, Interactive map, Community add/edit places, Backstory-led detail pages, Mobile app, Nearby unusual places, Visited/want-to-go, Editorial articles, Tours/trips, Membership | Local hidden-gem storytelling and contributor credit. | Membership and paid trips. |
| Lonely Planet | Destination guides and expert editorial | Destination guides, Expert tips, Itineraries, Travel inspiration, Guidebooks/maps, Newsletter, Budget/style framing, Best time to go, Things to know, Trip ideas | Concise 'things to know' and season-first guides. | Print guidebook store and broad global taxonomy. |
| VoiceMap / self-guided walking tours | Self-guided GPS/audio tours | Self-guided tour catalog, GPS-triggered audio, Start/stop/resume, Walking/driving/boat modes, Route map, Download for offline use, Local narrator, Tour preview, Paid tour store, Mobile app | Self-guided route concept and printable cue cards. | Paid audio marketplace and native app dependency. |

### B. vinhlong360 Current Feature Map (grep evidence)

#### E01: API inventory
```text
- agent/admin.py:257..2000 - 71 admin route decorators for entity CRUD, moderation, media, analytics, settings, users, reports.
- agent/public_api.py:161 - GET /api/entities with q/type/area/month/sort filters.
- agent/social.py:266..1635 - posts, feed, comments, likes, bookmarks, best answer, profile endpoints.
- Verification command: rg -n '@(router|app)\.(get|post|put|patch|delete)' agent -g '*.py' -g '!agent/tests/**' => 252 decorators.
```
#### E02: Search and browse
```text
- agent/public_api.py:161 - /api/entities accepts q, type, area, month, sort, limit, offset.
- agent/public_api.py:357 - /api/search delegates to db.search_entities and count_entities_filtered.
- web-nuxt/pages/dia-diem/index.vue:88..106 - search input plus type/area FilterChips.
- web-nuxt/components/SearchAutocomplete.vue:7..83 - combobox, suggestions, recents, type labels.
- web-nuxt/composables/useSearchRecents.ts:1..61 - local recent-search persistence.
```
#### E03: Map
```text
- agent/public_api.py:720..772 - /api/map-pins with type/area cache and ratings in pin payload.
- web-nuxt/pages/ban-do.vue:17..38 - type filters and map control panel.
- web-nuxt/pages/ban-do.vue:245..265 - MapLibre geojson source, clusters, unclustered pins.
- web-nuxt/pages/ban-do.vue:286..311 - popup HTML generated from entity metadata.
```
#### E04: Entity detail and gallery
```text
- web-nuxt/pages/dia-diem/[id].vue:18..71 - hero image, thumbnails, image credit, PhotoGallery.
- web-nuxt/components/PhotoGallery.vue:39..107 - placeholder, single image, desktop grid, mobile carousel, photo count.
- web-nuxt/pages/dia-diem/[id].vue:565..615 - cover image, credit, lightbox navigation and adjacent preload.
```
#### E05: Reviews
```text
- web-nuxt/pages/dia-diem/[id].vue:214 - LazyEntityReviews on entity detail.
- web-nuxt/components/EntityReviews.vue:6..31 - logged-in review form with accessible star radiogroup.
- web-nuxt/components/EntityReviews.vue:154..156 - helpful toggle with auth modal fallback.
- web-nuxt/components/ReviewCard.vue:25..32 - review photos and helpful button.
- web-nuxt/components/ReviewStats.vue:14..35 - rating distribution and mention chips.
- agent/public_api.py:980..1033 - /api/entities/{id}/review-stats aggregate distribution.
```
#### E06: Community
```text
- agent/social.py:68 - POST_TYPES = review/share/recommend/question.
- agent/social.py:266 - POST /api/posts.
- agent/social.py:1071..1238 - threaded comments create/edit/delete.
- agent/social.py:1264..1286 - Q&A best-answer endpoint.
- web-nuxt/pages/cong-dong.vue:128..147 - image upload in community composer.
- web-nuxt/components/PostCard.vue:42..93 - rating badge, images, actions and native share.
```
#### E07: Auth and trust
```text
- agent/auth.py:294..345 - OTP request and verify endpoints.
- agent/auth.py:446..524 - check-phone/login/set-password flow.
- agent/auth.py:569..614 - sessions and /auth/me.
- agent/auth.py:891..907 - privacy get/update.
- web-nuxt/components/AuthModal.vue:150..277 - phone/password/OTP/set-password modal states.
```
#### E08: Zalo/phone contact
```text
- web-nuxt/pages/dia-diem/[id].vue:96..97 - hero call and Zalo actions.
- web-nuxt/pages/dia-diem/[id].vue:369..402 - contact row and sticky CTA phone/Zalo/map fallback.
- web-nuxt/pages/dia-diem/[id].vue:711..715 - Zalo URL/number normalization.
- web-nuxt/components/ContactWidget.vue:6..57 - contact widget phone and Zalo buttons.
- agent/public_api.py:1051..1055 - contact action tracking accepts zalo/phone/website/map.
```
#### E09: Saved and itinerary
```text
- agent/saved.py:24..114 - /api/saved get/post/delete/merge.
- agent/plans.py:21..153 - /api/my-plans get/post/delete/merge/publish.
- agent/plans.py:157..190 - /api/shared-plans list/detail for public plans.
- web-nuxt/pages/tao-lich-trinh.vue:178..181 - publish and share actions.
- web-nuxt/pages/tao-lich-trinh.vue:430..461 - publish API call and navigator.share.
- web-nuxt/pages/lich-trinh-chia-se/[id].vue:37..39 - public shared plan fetch.
```
#### E10: Notifications/follow/block/RSVP
```text
- agent/notifications.py:62..107 - notifications list/read/read-all.
- agent/notifications.py:132..149 - notification preferences get/update.
- agent/notifications.py:189..236 - SSE notification stream.
- agent/notifications.py:295..420 - follow/check/following/follower-count.
- agent/notifications.py:465..516 - block/list blocked users.
- agent/notifications.py:562..589 - event RSVP set/get.
- web-nuxt/composables/useNotifications.ts:68..71 - EventSource stream with debounced refetch.
```
#### E11: SEO
```text
- agent/seo.py:404..423 - entity JSON-LD with type mapping and ImageObject support.
- agent/seo.py:696..986 - site/area/itinerary/entity/collection JSON-LD endpoints.
- agent/seo.py:1007..1148 - sitemap.xml, media sitemap, sitemap index, robots.txt.
- web-nuxt/pages/dia-diem/[id].vue:895..1063 - useSeoMeta, entity JSON-LD, BreadcrumbList, FAQPage.
- web-nuxt/nuxt.config.ts:54..82 - default OG/Twitter/manifest/sitemap metadata.
```
#### E12: Performance/PWA/images
```text
- web-nuxt/nuxt.config.ts:20..25 - Nuxt image uses weserv provider and WebP output.
- web-nuxt/nuxt.config.ts:90 - service worker registration.
- web-nuxt/public/sw.js:4..74 - precache plus stale-while-revalidate asset/API caching.
- web-nuxt/pages/index.vue:522..523 - hero-mobile/desktop image preload.
- web-nuxt/assets/css/base.css:144..149 - hero min-height and mobile hero image.
```
#### E13: Admin/data quality/media
```text
- agent/admin.py:675..722 - data-quality summary/review/apply/history/rollback.
- agent/admin.py:784..936 - image suggestions queue and approve/reject.
- agent/admin.py:1082 - media library endpoint.
- agent/admin.py:1385..1511 - moderation queue, approve/reject/batch/notes/stats.
- web-nuxt/pages/admin/entities.vue:216..229 - admin entity image management/upload.
- web-nuxt/pages/admin/duyet-anh.vue:202..248 - image suggestion UI.
```
#### E14: Admin analytics/settings
```text
- agent/admin.py:936 - /admin/stats.
- agent/admin.py:1522..1544 - analytics overview with day ranges.
- agent/admin.py:1937..1988 - site settings list/get/put/bulk/reset.
- web-nuxt/pages/admin/thong-ke.vue:9..18 - analytics page range chips and CSV export.
- web-nuxt/pages/admin/cai-dat/index.vue - settings hub with 16 categories in pages tree.
```
#### E15: Schema/tables
```text
- init.sql:21..400 - 22 base tables including entities, posts, comments, entity_ratings, saved_entities, user_plans, user_visits.
- agent/migrations/005_image_suggestions.sql:13 - image_suggestions table.
- agent/migrations/011_share_plan_rsvp.sql:6 - event_rsvp table.
- agent/migrations/017_cover_and_login_history.sql:7 - login_history table.
- agent/migrations/018_privacy_settings.sql:4 - user_privacy table.
- agent/migrations/021_notification_preferences.sql:4 - notification_preferences table.
- agent/migrations/023_consent_log.sql:4 - consent_log table.
```
#### E16: Counts
```text
- Verification command: Get-ChildItem web-nuxt/pages => 66 Vue page files.
- Verification command: Get-ChildItem web-nuxt/components => 44 Vue component files.
- Verification command: Get-ChildItem web-nuxt/composables => 38 composables.
- Verification command: Get-ChildItem agent/migrations => 25 migrations.
```

### C. User Stories for Priority Upgrades

1. **U-01 Zalo-first contact instrumentation:** Là P1, tôi muốn make zalo/phone/map clicks measurable by entity, source, viewport, and season. để hoàn tất stage RESEARCH,VISIT nhanh hơn. Metric: contact CTR, Zalo clicks/entity, phone clicks/entity.
2. **U-02 Source and last-verified block on detail:** Là P1, tôi muốn show 'nguồn / cập nhật / báo sai' near practical facts. để hoàn tất stage RESEARCH,VISIT nhanh hơn. Metric: report clicks, stale-entity fixes, trust-card impressions.
3. **U-03 Applied filter overview and no-results recovery:** Là P1, tôi muốn add removable filter chips, result explanation, and suggested fallback searches. để hoàn tất stage DISCOVER,RESEARCH nhanh hơn. Metric: filter-clear rate, zero-result exits, search refinements.
4. **U-04 Review sort, filter, and photo-first mode:** Là P1, tôi muốn sort by newest/helpful/photo/star and let photo reviews lead trust decisions. để hoàn tất stage RESEARCH,SHARE nhanh hơn. Metric: review reads, photo-review opens, helpful votes.
5. **U-05 Itinerary print/export/share polish:** Là P5, tôi muốn add print stylesheet, copyable zalo text, and compact offline route summary. để hoàn tất stage PLAN,VISIT nhanh hơn. Metric: plans shared, print/export clicks, shared-plan return visits.
6. **U-06 Map list-plus-map synchronized discovery:** Là P1, tôi muốn add mobile bottom list, selected entity preview, and filter-count feedback. để hoàn tất stage DISCOVER,PLAN,VISIT nhanh hơn. Metric: map interactions/session, pin-to-detail CTR.
7. **U-07 Know-before-you-go completion pass:** Là P1, tôi muốn standardize short practical facts with admin prompts for missing fields. để hoàn tất stage RESEARCH,VISIT nhanh hơn. Metric: KBYG coverage %, contact click rate after KBYG.
8. **U-08 Public correction/report-info CTA:** Là P1, tôi muốn allow 'báo sai thông tin này' for phone/hours/address/source. để hoàn tất stage RESEARCH,SHARE nhanh hơn. Metric: reports/entity, correction SLA.
9. **U-09 Entity Q&A surfaced in detail:** Là P1, tôi muốn add q&a tab/rail with accepted answer, ask-local cta, and local contributor prompt. để hoàn tất stage RESEARCH,SHARE nhanh hơn. Metric: questions answered, accepted-answer rate.
10. **U-10 Image attribution and contribution prompts:** Là P2, tôi muốn show credit in galleries and prompt locals for missing real photos. để hoàn tất stage SHARE,RETURN nhanh hơn. Metric: photo coverage %, credited-photo share.
11. **U-11 Owner/admin response to reviews:** Là P3, tôi muốn let admin/verified entity owner respond once per review with moderation audit. để hoàn tất stage RESEARCH,SHARE nhanh hơn. Metric: response coverage, negative-review follow-up.
12. **U-12 Review structured data from real UGC:** Là P1, tôi muốn emit compliant aggregaterating only where eligible and hide when data is thin. để hoàn tất stage RESEARCH nhanh hơn. Metric: rich-result eligibility, schema validation.
13. **U-13 Seasonal trip packs before peaks:** Là P1, tôi muốn create tet/summer/30-4/2-9 packs with places, food, route, contact notes. để hoàn tất stage DISCOVER,PLAN nhanh hơn. Metric: season page sessions, saves from season pages.
14. **U-14 Region landing pages with mini-itinerary:** Là P1, tôi muốn add 3-stop mini routes, local food, contact-ready pois. để hoàn tất stage DISCOVER,PLAN nhanh hơn. Metric: area page depth, itinerary adds from area.
15. **U-15 What's-new return feed:** Là P4, tôi muốn show new reviews/entities/events since last visit with local storage fallback. để hoàn tất stage RETURN nhanh hơn. Metric: return sessions, feed clicks.
16. **U-16 Shared-plan OG and Zalo preview optimizer:** Là P5, tôi muốn generate title/description/image for shared plan links and zalo/facebook og. để hoàn tất stage PLAN nhanh hơn. Metric: shared-link CTR, preview image coverage.
17. **U-17 Admin stale-content queue:** Là P3, tôi muốn queue entities by stale phone/hours/source/image and batch assign status. để hoàn tất stage RETURN,VISIT nhanh hơn. Metric: stale items closed/week, public stale badge reduction.
18. **U-18 Mobile/a11y visual QA checklist in CI docs:** Là P1, tôi muốn document/playwright smoke screenshots for public high-traffic pages. để hoàn tất stage DISCOVER,RESEARCH nhanh hơn. Metric: mobile visual regressions caught.
19. **U-19 Offline saved plan snapshot:** Là P5, tôi muốn cache saved plan/detail snapshots and show offline banner. để hoàn tất stage PLAN,VISIT nhanh hơn. Metric: offline plan opens, failed API fallback rate.
20. **U-20 Post-visit review prompt from visited state:** Là P2, tôi muốn after user marks visited, show lightweight review/tag/photo prompt. để hoàn tất stage SHARE,RETURN nhanh hơn. Metric: visited-to-review conversion.
21. **U-21 Local guide trust cards:** Là P2, tôi muốn show area badges, top helpful answers, photo/review mix, and joined date. để hoàn tất stage RESEARCH,SHARE nhanh hơn. Metric: profile CTR, helpful vote rate.
22. **U-22 Contact funnel dashboard:** Là P3, tôi muốn add contact/save/plan/search dashboards with csv. để hoàn tất stage VISIT nhanh hơn. Metric: contact CTR by source, top converting entities.
23. **U-23 Collaborative itinerary notes/votes via link:** Là P5, tôi muốn add optional lightweight vote/comment token per shared plan. để hoàn tất stage PLAN nhanh hơn. Metric: plans with feedback, edits after share.
24. **U-24 Q&A quality queue and accepted-answer highlights:** Là P2, tôi muốn queue unanswered entity questions and highlight accepted answers in detail. để hoàn tất stage RESEARCH,SHARE nhanh hơn. Metric: answer SLA, accepted-answer view rate.
25. **U-25 Ward one-screen day plan:** Là P1, tôi muốn add ward page route: breakfast/visit/lunch/photo/contact stops. để hoàn tất stage DISCOVER,PLAN nhanh hơn. Metric: ward plan saves, page dwell.
26. **U-26 Event RSVP reminders:** Là P4, tôi muốn notify users before followed/rsvp events with opt-in preferences. để hoàn tất stage RETURN,VISIT nhanh hơn. Metric: RSVP reminder CTR, unsubscribes.
27. **U-27 Short video-link guide cards:** Là P1, tôi muốn store/link youtube/tiktok references as external inspiration cards with fallback text. để hoàn tất stage DISCOVER,RESEARCH nhanh hơn. Metric: video-link clicks, detail saves after video card.
28. **U-28 Public themed collection pages:** Là P1, tôi muốn create collection model or site-setting driven curated lists. để hoàn tất stage DISCOVER,PLAN nhanh hơn. Metric: collection sessions, saves/collection.
29. **U-29 Rule-based similar recommendations:** Là P1, tôi muốn recommend by area/type/season/visited exclusion; no ml engine. để hoàn tất stage RESEARCH,RETURN nhanh hơn. Metric: related CTR, repeat detail views.
30. **U-30 Partner/entity claim workflow:** Là P3, tôi muốn create claim form queue with phone/zalo verification and admin audit. để hoàn tất stage RESEARCH,VISIT nhanh hơn. Metric: claims submitted, verified claims.

### D. Sub-feature Breakdown per Functional Group

| Group | Sub-feature | What exactly it needs | Optimize | Why it matters | Current evidence | Gap/recommendation |
| --- | --- | --- | --- | --- | --- | --- |
| F1 Discovery IA | Homepage hero search | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E02 | Keep/upgrade based on matrix status |
| F1 Discovery IA | Seasonal modules | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E02 | Keep/upgrade based on matrix status |
| F1 Discovery IA | Trending destinations | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E02 | Keep/upgrade based on matrix status |
| F1 Discovery IA | Category chips | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E02 | Keep/upgrade based on matrix status |
| F1 Discovery IA | Curated collections | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E02 | Keep/upgrade based on matrix status |
| F1 Discovery IA | New/updated strip | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E02 | Keep/upgrade based on matrix status |
| F1 Discovery IA | Local hidden gems | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E02 | Keep/upgrade based on matrix status |
| F1 Discovery IA | Area landing pages | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E02 | Keep/upgrade based on matrix status |
| F2 Search & Filters | Global autocomplete | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E02 | Keep/upgrade based on matrix status |
| F2 Search & Filters | Recent searches | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E02 | Keep/upgrade based on matrix status |
| F2 Search & Filters | Type filters | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E02 | Keep/upgrade based on matrix status |
| F2 Search & Filters | Area filters | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E02 | Keep/upgrade based on matrix status |
| F2 Search & Filters | Season/month filter | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E02 | Keep/upgrade based on matrix status |
| F2 Search & Filters | Rating sort | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E02 | Keep/upgrade based on matrix status |
| F2 Search & Filters | Applied filter overview | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E02 | Keep/upgrade based on matrix status |
| F2 Search & Filters | Mobile filter tray | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E02 | Keep/upgrade based on matrix status |
| F3 Entity Detail | Hero gallery | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E14 | Keep/upgrade based on matrix status |
| F3 Entity Detail | Photo count/lightbox | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E14 | Keep/upgrade based on matrix status |
| F3 Entity Detail | Highlights | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E14 | Keep/upgrade based on matrix status |
| F3 Entity Detail | Know before you go | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E14 | Keep/upgrade based on matrix status |
| F3 Entity Detail | Hours and prices | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E14 | Keep/upgrade based on matrix status |
| F3 Entity Detail | Contact card | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E14 | Keep/upgrade based on matrix status |
| F3 Entity Detail | Map section | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E14 | Keep/upgrade based on matrix status |
| F3 Entity Detail | Nearby/similar | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E14 | Keep/upgrade based on matrix status |
| F4 Reviews & Ratings | Star form | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E05 | Keep/upgrade based on matrix status |
| F4 Reviews & Ratings | Review text form | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E05 | Keep/upgrade based on matrix status |
| F4 Reviews & Ratings | Photo reviews | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E05 | Keep/upgrade based on matrix status |
| F4 Reviews & Ratings | Rating distribution | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E05 | Keep/upgrade based on matrix status |
| F4 Reviews & Ratings | Mention/topic chips | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E05 | Keep/upgrade based on matrix status |
| F4 Reviews & Ratings | Helpful votes | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E05 | Keep/upgrade based on matrix status |
| F4 Reviews & Ratings | Review sorting | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E05 | Keep/upgrade based on matrix status |
| F4 Reviews & Ratings | Review filters | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E05 | Keep/upgrade based on matrix status |
| F5 Community & Reputation | User profile | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E06 | Keep/upgrade based on matrix status |
| F5 Community & Reputation | Followers/following | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E06 | Keep/upgrade based on matrix status |
| F5 Community & Reputation | Contribution stats | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E06 | Keep/upgrade based on matrix status |
| F5 Community & Reputation | Badges | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E06 | Keep/upgrade based on matrix status |
| F5 Community & Reputation | Leaderboard | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E06 | Keep/upgrade based on matrix status |
| F5 Community & Reputation | Local guide trust card | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E06 | Keep/upgrade based on matrix status |
| F5 Community & Reputation | Suggested follows | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E06 | Keep/upgrade based on matrix status |
| F5 Community & Reputation | Entity follow | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E06 | Keep/upgrade based on matrix status |
| F6 UGC Creation & Moderation | Review/share/question/recommend post types | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E06 | Keep/upgrade based on matrix status |
| F6 UGC Creation & Moderation | Image upload | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E06 | Keep/upgrade based on matrix status |
| F6 UGC Creation & Moderation | Draft autosave | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E06 | Keep/upgrade based on matrix status |
| F6 UGC Creation & Moderation | Hashtags | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E06 | Keep/upgrade based on matrix status |
| F6 UGC Creation & Moderation | Mentions | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E06 | Keep/upgrade based on matrix status |
| F6 UGC Creation & Moderation | Threaded comments | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E06 | Keep/upgrade based on matrix status |
| F6 UGC Creation & Moderation | Moderation queue | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E06 | Keep/upgrade based on matrix status |
| F6 UGC Creation & Moderation | Report UGC | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E06 | Keep/upgrade based on matrix status |
| F7 Saved & Collections | Save entity | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E09 | Keep/upgrade based on matrix status |
| F7 Saved & Collections | Merge local saved | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E09 | Keep/upgrade based on matrix status |
| F7 Saved & Collections | Saved sync | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E09 | Keep/upgrade based on matrix status |
| F7 Saved & Collections | Saved snapshots | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E09 | Keep/upgrade based on matrix status |
| F7 Saved & Collections | Multi-list collections | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E09 | Keep/upgrade based on matrix status |
| F7 Saved & Collections | Share collections | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E09 | Keep/upgrade based on matrix status |
| F7 Saved & Collections | Collaborative notes | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E09 | Keep/upgrade based on matrix status |
| F7 Saved & Collections | Vote up/down in group | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E09 | Keep/upgrade based on matrix status |
| F8 Map & Navigation | Map pins | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E03 | Keep/upgrade based on matrix status |
| F8 Map & Navigation | Type filters | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E03 | Keep/upgrade based on matrix status |
| F8 Map & Navigation | Area filters | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E03 | Keep/upgrade based on matrix status |
| F8 Map & Navigation | Clusters | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E03 | Keep/upgrade based on matrix status |
| F8 Map & Navigation | Popup cards | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E03 | Keep/upgrade based on matrix status |
| F8 Map & Navigation | List+map split | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E03 | Keep/upgrade based on matrix status |
| F8 Map & Navigation | Directions handoff | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E03 | Keep/upgrade based on matrix status |
| F8 Map & Navigation | Route preview | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E03 | Keep/upgrade based on matrix status |
| F9 Personalization & Return | Recently viewed | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E14 | Keep/upgrade based on matrix status |
| F9 Personalization & Return | Followed entity feed | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E14 | Keep/upgrade based on matrix status |
| F9 Personalization & Return | What's new | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E14 | Keep/upgrade based on matrix status |
| F9 Personalization & Return | Seasonal return prompts | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E14 | Keep/upgrade based on matrix status |
| F9 Personalization & Return | Saved reminder | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E14 | Keep/upgrade based on matrix status |
| F9 Personalization & Return | Visited-based prompts | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E14 | Keep/upgrade based on matrix status |
| F9 Personalization & Return | Notification digest | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E14 | Keep/upgrade based on matrix status |
| F9 Personalization & Return | Personalized homepage | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E14 | Keep/upgrade based on matrix status |
| F10 Itinerary Planning | Admin itineraries | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E09 | Keep/upgrade based on matrix status |
| F10 Itinerary Planning | User itinerary builder | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E09 | Keep/upgrade based on matrix status |
| F10 Itinerary Planning | Save plans | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E09 | Keep/upgrade based on matrix status |
| F10 Itinerary Planning | Publish plan | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E09 | Keep/upgrade based on matrix status |
| F10 Itinerary Planning | Shared plan page | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E09 | Keep/upgrade based on matrix status |
| F10 Itinerary Planning | Native share | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E09 | Keep/upgrade based on matrix status |
| F10 Itinerary Planning | Print/export | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E09 | Keep/upgrade based on matrix status |
| F10 Itinerary Planning | Day-by-day view | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E09 | Keep/upgrade based on matrix status |
| F11 Content Guides & SEO | Sitemaps | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E11 | Keep/upgrade based on matrix status |
| F11 Content Guides & SEO | Media sitemap | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E11 | Keep/upgrade based on matrix status |
| F11 Content Guides & SEO | Robots | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E11 | Keep/upgrade based on matrix status |
| F11 Content Guides & SEO | Entity JSON-LD | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E11 | Keep/upgrade based on matrix status |
| F11 Content Guides & SEO | Itinerary JSON-LD | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E11 | Keep/upgrade based on matrix status |
| F11 Content Guides & SEO | FAQ JSON-LD | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E11 | Keep/upgrade based on matrix status |
| F11 Content Guides & SEO | OG tags | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E11 | Keep/upgrade based on matrix status |
| F11 Content Guides & SEO | Article/review schema | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E11 | Keep/upgrade based on matrix status |
| F12 Mobile Performance & PWA | Nuxt image WebP | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E12 | Keep/upgrade based on matrix status |
| F12 Mobile Performance & PWA | Lazy images | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E12 | Keep/upgrade based on matrix status |
| F12 Mobile Performance & PWA | Hero preload | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E12 | Keep/upgrade based on matrix status |
| F12 Mobile Performance & PWA | Service worker | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E12 | Keep/upgrade based on matrix status |
| F12 Mobile Performance & PWA | Asset cache | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E12 | Keep/upgrade based on matrix status |
| F12 Mobile Performance & PWA | API cache | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E12 | Keep/upgrade based on matrix status |
| F12 Mobile Performance & PWA | Map lazy chunk | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E12 | Keep/upgrade based on matrix status |
| F12 Mobile Performance & PWA | Skeleton states | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E12 | Keep/upgrade based on matrix status |
| F13 Contact & Conversion | Phone CTA | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E08 | Keep/upgrade based on matrix status |
| F13 Contact & Conversion | Zalo CTA | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E08 | Keep/upgrade based on matrix status |
| F13 Contact & Conversion | Map CTA | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E08 | Keep/upgrade based on matrix status |
| F13 Contact & Conversion | Website CTA | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E08 | Keep/upgrade based on matrix status |
| F13 Contact & Conversion | Contact click tracking | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E08 | Keep/upgrade based on matrix status |
| F13 Contact & Conversion | Sticky contact bar | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E08 | Keep/upgrade based on matrix status |
| F13 Contact & Conversion | Copy phone | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E08 | Keep/upgrade based on matrix status |
| F13 Contact & Conversion | Zalo deep-link template | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E08 | Keep/upgrade based on matrix status |
| F14 Admin CMS | Entity CRUD | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E13 | Keep/upgrade based on matrix status |
| F14 Admin CMS | Image upload | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E13 | Keep/upgrade based on matrix status |
| F14 Admin CMS | Media library | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E13 | Keep/upgrade based on matrix status |
| F14 Admin CMS | Moderation queue | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E13 | Keep/upgrade based on matrix status |
| F14 Admin CMS | Reports | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E13 | Keep/upgrade based on matrix status |
| F14 Admin CMS | User management | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E13 | Keep/upgrade based on matrix status |
| F14 Admin CMS | Analytics | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E13 | Keep/upgrade based on matrix status |
| F14 Admin CMS | Site settings | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E13 | Keep/upgrade based on matrix status |
| F15 Data Quality & Freshness | Data quality summary | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E13 | Keep/upgrade based on matrix status |
| F15 Data Quality & Freshness | Source registry | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E13 | Keep/upgrade based on matrix status |
| F15 Data Quality & Freshness | Last updated | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E13 | Keep/upgrade based on matrix status |
| F15 Data Quality & Freshness | Public freshness badge | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E13 | Keep/upgrade based on matrix status |
| F15 Data Quality & Freshness | Stale queue | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E13 | Keep/upgrade based on matrix status |
| F15 Data Quality & Freshness | Rollback | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E13 | Keep/upgrade based on matrix status |
| F15 Data Quality & Freshness | Image suggestion review | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E13 | Keep/upgrade based on matrix status |
| F15 Data Quality & Freshness | Duplicate check | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E13 | Keep/upgrade based on matrix status |
| F16 Social Proof & Trust | Rating count | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E14 | Keep/upgrade based on matrix status |
| F16 Social Proof & Trust | Photo proof | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E14 | Keep/upgrade based on matrix status |
| F16 Social Proof & Trust | Verified source badge | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E14 | Keep/upgrade based on matrix status |
| F16 Social Proof & Trust | Local contributor identity | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E14 | Keep/upgrade based on matrix status |
| F16 Social Proof & Trust | Admin response | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E14 | Keep/upgrade based on matrix status |
| F16 Social Proof & Trust | Helpful votes | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E14 | Keep/upgrade based on matrix status |
| F16 Social Proof & Trust | Review excerpts | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E14 | Keep/upgrade based on matrix status |
| F16 Social Proof & Trust | Trust copy | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E14 | Keep/upgrade based on matrix status |
| F17 Notifications & Follow | Notification list | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E10 | Keep/upgrade based on matrix status |
| F17 Notifications & Follow | Unread count | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E10 | Keep/upgrade based on matrix status |
| F17 Notifications & Follow | Mark read | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E10 | Keep/upgrade based on matrix status |
| F17 Notifications & Follow | Read all | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E10 | Keep/upgrade based on matrix status |
| F17 Notifications & Follow | SSE stream | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E10 | Keep/upgrade based on matrix status |
| F17 Notifications & Follow | Polling fallback | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E10 | Keep/upgrade based on matrix status |
| F17 Notifications & Follow | Notification preferences | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E10 | Keep/upgrade based on matrix status |
| F17 Notifications & Follow | Follow entity | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E10 | Keep/upgrade based on matrix status |
| F18 Safety, Legal & Privacy | Phone verification | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E14 | Keep/upgrade based on matrix status |
| F18 Safety, Legal & Privacy | Consent logging | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E14 | Keep/upgrade based on matrix status |
| F18 Safety, Legal & Privacy | Privacy settings | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E14 | Keep/upgrade based on matrix status |
| F18 Safety, Legal & Privacy | Login history | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E14 | Keep/upgrade based on matrix status |
| F18 Safety, Legal & Privacy | Block/report | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E14 | Keep/upgrade based on matrix status |
| F18 Safety, Legal & Privacy | Moderation notes | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E14 | Keep/upgrade based on matrix status |
| F18 Safety, Legal & Privacy | PII masking | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E14 | Keep/upgrade based on matrix status |
| F18 Safety, Legal & Privacy | CSRF | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E14 | Keep/upgrade based on matrix status |
| F19 Analytics & Experimentation | Admin overview | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E14 | Keep/upgrade based on matrix status |
| F19 Analytics & Experimentation | Popular pages | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E14 | Keep/upgrade based on matrix status |
| F19 Analytics & Experimentation | Daily stats | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E14 | Keep/upgrade based on matrix status |
| F19 Analytics & Experimentation | Top entities | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E14 | Keep/upgrade based on matrix status |
| F19 Analytics & Experimentation | Contact funnel | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E14 | Keep/upgrade based on matrix status |
| F19 Analytics & Experimentation | Save funnel | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E14 | Keep/upgrade based on matrix status |
| F19 Analytics & Experimentation | Plan funnel | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E14 | Keep/upgrade based on matrix status |
| F19 Analytics & Experimentation | Search zero-result KPI | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E14 | Keep/upgrade based on matrix status |
| F20 Monetization & Partnership | Partner directory | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E14 | Keep/upgrade based on matrix status |
| F20 Monetization & Partnership | Claim entity | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E14 | Keep/upgrade based on matrix status |
| F20 Monetization & Partnership | Sponsored showcase label | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E14 | Keep/upgrade based on matrix status |
| F20 Monetization & Partnership | No affiliate links | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E14 | Keep/upgrade based on matrix status |
| F20 Monetization & Partnership | No payment | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E14 | Keep/upgrade based on matrix status |
| F20 Monetization & Partnership | Lead/contact attribution | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E14 | Keep/upgrade based on matrix status |
| F20 Monetization & Partnership | Campaign landing page | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E14 | Keep/upgrade based on matrix status |
| F20 Monetization & Partnership | Seasonal packages | Component/API/data slice for the feature | mobile/perf/a11y/SEO as applicable | Maps to a persona stage and measurable action | E14 | Keep/upgrade based on matrix status |

### E. Optimization Requirements Catalog

| Area | Optimization | Why | How | Effort | Priority |
| --- | --- | --- | --- | --- | --- |
| Performance | Lazy-load below-fold review/photo blocks | Rural/unstable mobile sessions | Use IntersectionObserver/Nuxt lazy components | S | P0 |
| Performance | Keep maplibre lazy chunk | Map JS is heavy | Load only on /ban-do and detail map interaction | S | P0 |
| Performance | Compress user-uploaded images before upload | UGC photos can be huge | Reuse canvas compression flow | S | P0 |
| Performance | Preload only hero image | Avoid competing high-priority resources | Keep current hero preload, audit detail pages | S | P1 |
| Performance | API cache stale-while-revalidate for saved plans | Visit-stage offline need | Extend SW strategy for plan/detail snapshots | M | P1 |
| Mobile UX | Test 360px, 390px, 414px | VN Android mid-range widths | Playwright screenshot baselines | M | P1 |
| Mobile UX | Bottom-sheet filter tray | Small screens cannot show dense filters | Tray overlay with active count | M | P0 |
| Mobile UX | Sticky contact respects safe area | CTA must remain tappable | Use env(safe-area-inset-bottom) | S | P0 |
| Mobile UX | Tap targets >=44px | Finger error reduction | Audit chips/buttons/contact links | S | P1 |
| Mobile UX | Scannable short guide cards | VN scroll-first behavior | 2-3 bullet summaries before long text | S | P1 |
| SEO | AggregateRating only from first-party reviews | Google structured-data compliance | Gate schema on count threshold | S | P1 |
| SEO | Per-plan OG image/title | Zalo/Facebook share previews | Generate from first 3 stops | M | P1 |
| SEO | Season landing internal links | Pre-peak Google discovery | Link from home/category/detail | M | P1 |
| SEO | Media sitemap image captions | Image search eligibility | Use credit/caption fields | S | P2 |
| SEO | FAQ schema from real attributes only | Avoid fabricated FAQ | Keep current attribute-derived logic | S | P0 |
| A11y | Review star radiogroup labels | Keyboard/screen-reader access | Maintain aria-label per star | S | P0 |
| A11y | Lightbox focus trap | Modal keyboard safety | Use useModalA11y pattern | M | P1 |
| A11y | Map popup keyboard equivalent | Map-only info can be inaccessible | Provide list panel alternative | M | P0 |
| A11y | Color-independent status badges | Colorblind/readability | Include text/status icons | S | P1 |
| A11y | Reduced motion for hover/scroll effects | Vestibular comfort | Respect prefers-reduced-motion | S | P1 |
| Trust | Source and review-by date | User fears stale info | Fact-level source block | M | P0 |
| Trust | No fake scarcity | Avoid dark patterns | Policy guard in content/admin | S | P0 |
| Trust | Owner/admin response label | Separates official voice from UGC | Role badge and moderation audit | M | P1 |
| Trust | Photo attribution | Legal and creator trust | Credit display in gallery | S | P0 |
| Trust | Contributor local expertise | Referral/local trust in VN | Area/type badges | M | P1 |
| Security | Rate-limit review/helpful/report paths | UGC abuse risk | Use existing rate profiles | S | P0 |
| Security | CSRF on mutation endpoints | Session safety | Keep require_csrf on writes | S | P0 |
| Security | PII masking in admin/users logs | Phone data sensitivity | Maintain masking helpers | S | P0 |
| Security | Consent log auditability | PDP/NĐ13 compliance | Expose admin export/report | M | P2 |
| Security | Image upload MIME sniffing | UGC file safety | Keep storage tests and reject SVG | S | P0 |
| Admin | Batch stale operations | Solo dev/admin time | Queue and batch status updates | M | P1 |
| Admin | Moderation note templates | Consistency | Preset reasons and audit notes | S | P1 |
| Admin | Data-quality SLA dashboard | Freshness measurable | Group by stale days/source missing | M | P1 |
| Admin | Entity claim queue | Partner workflow | Form -> admin review -> verified contact | L | P2 |
| Admin | Content calendar before peaks | Seasonality | Site-setting schedule list | M | P2 |
| Analytics | Contact funnel by source | Measures real conversion | Track entity/action/referrer/viewport | M | P1 |
| Analytics | Zero-result query queue | Content gap discovery | Persist top misses | M | P2 |
| Analytics | Save-to-plan conversion | Planning metric | Join saved/plans events | M | P2 |
| Analytics | Review quality metrics | Community health | Helpful/photo/report ratios | M | P2 |
| Analytics | Self-hosted dashboard only | Budget/privacy | Avoid heavy SaaS | S | P0 |

### F. Cross-platform UX Pattern Library

| Pattern | Platforms using it | Description | Adoption recommendation |
| --- | --- | --- | --- |
| P-01 | Hero search with intent examples | GYG,Klook,Traveloka | Search box plus sample categories in first viewport | Adopt for home and search |
| P-02 | Horizontal category chips | GYG,Klook,Airbnb | Scrollable mobile chips, wrap on desktop | Already present; standardize counts |
| P-03 | Asymmetric gallery | GYG,Airbnb,Google | Large lead photo plus thumbnail grid | Implemented; keep credit and lightbox |
| P-04 | Mobile gallery carousel | GYG,Klook,Airbnb | Swipeable first media block | Implemented in PhotoGallery |
| P-05 | Photo count badge | GYG,Airbnb | Explicit 'x ảnh' button | Implemented; expand to UGC photo reviews |
| P-06 | Sticky mobile CTA | GYG,Airbnb | Bottom bar for next action | Use Zalo/Phone/Save, not booking |
| P-07 | Map/list split | Google,Airbnb | List panel and map keep selected state | Priority U-06 |
| P-08 | Applied filter overview | Baymard examples | Show active filters and removal | Priority U-03 |
| P-09 | Mobile filter tray | NNGroup | Filters in overlay/tray on small screens | Adopt for catalog/search |
| P-10 | No-results recovery | Search platforms | Suggestions, broaden filters, quick picks | Priority U-03 |
| P-11 | Review distribution bars | Klook,Google,Airbnb | 5-star breakdown with bars | Implemented, enhance with sort/filter |
| P-12 | Photo reviews shortcut | Klook,Tripadvisor | Filter only reviews with photos | Priority U-04 |
| P-13 | Helpful vote | Tripadvisor | Low-cost quality ranking signal | Implemented |
| P-14 | Owner response | Tripadvisor,Google,Airbnb | Official reply under review | Priority U-11 |
| P-15 | Accepted answer | Tripadvisor Q&A | Best answer shown first | Partially implemented; surface on detail |
| P-16 | Collaborative wishlist notes/votes | Airbnb | Group planning comments and votes | P2 U-23 |
| P-17 | Saved lists | Google Maps,Airbnb | Save into named lists | P2 U-28 |
| P-18 | Source/freshness badge | Google-like knowledge trust | Last updated/source indicator | P0 U-02 |
| P-19 | How-to-use/practical card | Klook,Viator | Operational steps before visit | Adapt to no booking |
| P-20 | Cancellation/policy block | GYG,Klook,Viator | Risk reversal info | Adapt as opening/source/reliability info |
| P-21 | Best time to go | Lonely Planet | Season/time-of-day advice | Innovation I-01/I-09 |
| P-22 | Hidden-gem story | Atlas Obscura | Backstory leads discovery | Adopt for local legends |
| P-23 | Route cue sheet | VoiceMap | Stops with sequence and instructions | P3 U-34 |
| P-24 | App install push | Klook,Atlas,Airbnb | Native funnel | Skip; web/PWA only |
| P-25 | Trust bar | GYG,Viator | Support/cancellation/reviews | Adapt as official/source/contact trust |
| P-26 | Community leaderboard | Tripadvisor | Contribution rank | Implemented; avoid over-gamification |
| P-27 | Entity follow | Social platforms | Follow places/users | Implemented |
| P-28 | Notification preferences | Social apps | Control notification types | Implemented |
| P-29 | Short guide snippets | Lonely Planet,Google | Scannable 'things to know' | Adopt for mobile |
| P-30 | OG-rich share cards | All social platforms | Preview title/image/description | P1 U-16 |

### G. Anti-pattern Catalog

| # | Anti-pattern | Example | Why harmful | Simple alternative |
| --- | --- | --- | --- | --- |
| A-01 | Booking envy | Adding checkout because OTAs have it | Turns a travel guide into regulated commerce | Keep Zalo/Phone/map contact only |
| A-02 | Fake urgency | Countdowns / 'only 2 left' | No inventory; harms trust | Use real event dates only |
| A-03 | Verified purchase without purchase | Klook-style badges | Misleading trust signal | Use phone-verified/local contributor/source badges |
| A-04 | ML theatre | Black-box recommendations | High maintenance and poor explainability | Rule-based related/seasonal logic |
| A-05 | Video hosting | TikTok copy | Storage/bandwidth/moderation burden | External links + text fallback |
| A-06 | Native-app detour | App for everything | Split QA and release surface | PWA/web-first |
| A-07 | Badge economy bloat | Many levels/trophies | Gaming and vanity metrics | Few useful contribution badges |
| A-08 | Global taxonomy copy | GYG/Klook category universe | Too broad for Vinh Long | Local seasonal/area/type taxonomy |
| A-09 | Price freshness trap | Scraped menus/prices | Stale facts and complaints | Use price range/source date or no price |
| A-10 | Chat platform clone | In-site real-time messaging | Abuse/moderation/support burden | Zalo deep-link templates |
| A-11 | Affiliate opacity | Hidden monetized links | Trust/legal risk | Transparent partner policy; no affiliate for now |
| A-12 | Review scraping | Importing Google reviews | API/legal and data provenance risk | First-party UGC only |
| A-13 | Over-analytics | Heavy SaaS stack | Cost and privacy bloat | Self-hosted/minimal funnel metrics |
| A-14 | Premature multilingual | Machine translate everything | Stale legal/practical info | Vietnamese first |
| A-15 | Live availability without ops | Calendar slots | Needs partner updates and refunds | Static contact and source confidence |

### H. Sources & References

- [GetYourGuide homepage / trust & cancellation](https://www.getyourguide.com/)
- [GetYourGuide terms / cancellation window](https://www.getyourguide.com/c/general-terms-and-conditions/)
- [Klook homepage / activities, deals, reviews](https://www.klook.com/en-US/)
- [Klook guide / cancellation & chat support](https://www.klook.com/en-AU/blog/how-to-use-klook/)
- [Tripadvisor forum/community](https://www.tripadvisor.com/ForumHome)
- [Tripadvisor terms / interactive areas](https://tripadvisor.mediaroom.com/us-terms-of-use)
- [Google Maps saved places help](https://support.google.com/maps/answer/3184808)
- [Airbnb wishlists help](https://www.airbnb.com/help/article/1236)
- [Airbnb reviews help](https://www.airbnb.ca/help/article/13)
- [Airbnb 2026 Experiences release](https://news.airbnb.com/airbnb-2026-summer-release/)
- [Viator homepage / free cancellation](https://www.viator.com/)
- [Traveloka Activities](https://www.traveloka.com/en-en/activities)
- [Traveloka Xperience review flow](https://www.traveloka.com/en-sg/help/attractions-activities/attractions-activities-managing-your-boooking/reviews/reviews/how-to-review-an-xperience)
- [Atlas Obscura homepage](https://www.atlasobscura.com/)
- [Atlas Obscura map/app listing](https://play.google.com/store/apps/details?id=com.atlasobscura.android&hl=en_US)
- [Lonely Planet homepage](https://www.lonelyplanet.com/)
- [VoiceMap self-guided tours](https://voicemap.me/)
- [vinhlongtourist.vn homepage](https://vinhlongtourist.vn/)
- [vinhlongtourist.vn destinations](https://vinhlongtourist.vn/en/detailnews/?id=news_11662&t=mot-so-diem-du-lich-hap-dan-tai-vinh-long)
- [Google Maps](https://maps.google.com/)
- [YouTube hashtag #dulichvinhlong](https://www.youtube.com/hashtag/dulichvinhlong)
- [DataReportal Digital 2026 Vietnam](https://datareportal.com/reports/digital-2026-vietnam)
- [VNG Annual Report / Zalo 2024](https://bctn2024.vng.com.vn/about/zalo)
- [StatCounter mobile screen resolutions](https://gs.statcounter.com/screen-resolution-stats/mobile/worldwide)
- [VNNIC internet resources report 2024](https://vnnic.vn/sites/default/files/bao-cao-tai-nguyen/report-on-internet-internet-resources-in-viet-nam-2024.pdf)
- [NNGroup visual hierarchy](https://www.nngroup.com/articles/visual-hierarchy-ux-definition/)
- [NNGroup helpful filter categories](https://www.nngroup.com/articles/filter-categories-values/)
- [NNGroup mobile faceted search](https://www.nngroup.com/articles/mobile-faceted-search/)
- [NNGroup how users read on the web](https://www.nngroup.com/articles/how-users-read-on-the-web/)
- [Baymard product list and filtering UX](https://baymard.com/blog/current-state-product-list-and-filtering)
- [Baymard applied filters overview](https://baymard.com/blog/how-to-design-applied-filters)
- [Google Review structured data](https://developers.google.com/search/docs/appearance/structured-data/review-snippet)
- [Google LocalBusiness structured data](https://developers.google.com/search/docs/appearance/structured-data/local-business)
- [Nghi dinh 147/2024/ND-CP](https://vanban.chinhphu.vn/?docid=211654&pageid=27160)
- [Nghi dinh 52/2013/ND-CP](https://vanban.chinhphu.vn/default.aspx?docid=167457&pageid=27160)
- [Nghi dinh 85/2021/ND-CP](https://vanban.chinhphu.vn/default.aspx?docid=204191&pageid=27160)
- [Nghi dinh 13/2023/ND-CP](https://vanban.chinhphu.vn/?docid=207759&pageid=27160)

### I. Quality Gate Self-check

| # | Check | Status |
| --- | --- | --- |
| QG1 | Feature matrix rows | PASS - 260 rows |
| QG2 | Gap analysis | PASS - 62 gaps with 7 layers each |
| QG3 | Sub-features + optimization + reasoning | PASS - upgrade cards and appendixes C/D/E |
| QG4 | Platforms researched | PASS - 10 international + 5 VN competitors |
| QG5 | Upgrade cards | PASS - P0+P1=22, P2+P3=15, Innovation=10 |
| QG6 | Upgrade card depth | PASS - persona, journey, files/evidence, effort split, risk, metrics |
| QG7 | Skip depth | PASS - 25 rows with score/anti-pattern/revisit |
| QG8 | Maturity scorecard | PASS - 20 groups |
| QG9 | Anti-pattern catalog | PASS - 15 items |
| QG10 | UX pattern library | PASS - 30 patterns |
| QG11 | Grep evidence | PASS - 16 evidence blocks with file:line |
| QG12 | Effort based on codebase | PASS - route/page/component/schema counts included |
| QG13 | Dependency graph | PASS - section 5 |
| QG14 | Risk realism | PASS - LOW/MED/HIGH mixed, top solo-dev risks |
| QG15 | Constraints checked | PASS - forbidden list mapped to skip table |
| QG16 | VN context | PASS - Zalo/Facebook/mobile/seasonality used |
| QG17 | No forbidden recommendations | PASS - booking/payment/native/ML/video skipped |
| QG18 | Innovation stories | PASS - 10 persona-based user stories |
| QG19 | Optimization items | PASS - 40 items |
| QG20 | Subfeature breakdown | PASS - 160 rows (20 x 8) |
