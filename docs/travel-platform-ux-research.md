# Nghien cuu UX 5 nen tang du lich hang dau
> Ngay: 2026-06-27 | Phuong phap: 5 agent doc lap browse + phan tich 10 chieu | Ap dung cho: vinhlong360 (showcase-only, KHONG booking)

---

## Muc luc
- [1. Tong quan & phuong phap](#1-tong-quan)
- [2. GetYourGuide](#2-getyourguide)
- [3. Klook](#3-klook)
- [4. Google Travel](#4-google-travel)
- [5. TripAdvisor](#5-tripadvisor)
- [6. Airbnb](#6-airbnb)
- [7. So sanh cheo 10 chieu](#7-so-sanh-cheo)
- [8. Pattern Library cho vinhlong360](#8-pattern-library)
- [9. Khuyen nghi cu the: CSS + Component](#9-khuyen-nghi)

---

## 1. Tong quan & phuong phap {#1-tong-quan}

### Muc tieu
Phan tich sau bo cuc, chuc nang, va UX pattern cua 5 nen tang du lich lon nhat the gioi de rut ra nhung pattern co the ap dung cho vinhlong360 — mot trang gioi thieu du lich/OCOP/cong dong (showcase-only, KHONG booking/thanh toan).

### 5 nen tang
| # | Platform | Mo hinh | Diem manh |
|---|----------|---------|-----------|
| 1 | GetYourGuide | OTA tour/activity | Gallery, AI review, filter UX |
| 2 | Klook | OTA SEA-focused | SEA localization, card design |
| 3 | Google Travel | Aggregator/planner | Map+list, minimal design, type restraint |
| 4 | TripAdvisor | Review/community | Bubble rating, AI chat, community |
| 5 | Airbnb | Marketplace | Content-first, progressive disclosure, micro-interactions |

### 10 chieu phan tich
1. Information Architecture (IA)
2. Category Navigation
3. Card Patterns
4. Photo Gallery / Media
5. Search + Map View
6. Filter System
7. Detail Page Layout
8. Review / Rating Display
9. Responsive Design
10. Micro-interactions

---

## 2. GetYourGuide {#2-getyourguide}

### 2.1 Information Architecture
- **Homepage flow**: Hero search → destination cards → activity categories → popular activities → trust bar → footer
- **Destination page**: Hero image + breadcrumb → filter bar → activity card grid → "Things to do" editorial → FAQ accordion
- **Detail page**: Gallery → title+rating → description → highlights → inclusions → meeting point map → reviews → similar activities

### 2.2 Category Navigation
- **Destination-specific filter chips**: Khong phai filter chung — moi destination co chip rieng (VD: "Mekong Delta", "Cu Chi Tunnels" cho Ho Chi Minh City)
- **Horizontal scroll** tren mobile, wrap tren desktop
- **Active state**: Filled background (brand blue)

### 2.3 Card Patterns
- **Activity card anatomy**: 3:2 image ratio → badge overlay (top-left: "Bestseller", "Likely to sell out") → title (2 lines max, truncate) → meta line (duration + type) → star rating + review count → price (right-aligned, bold)
- **Card dimensions**: ~280px width trong 4-col grid, 16px gap
- **Hover**: Subtle shadow elevation + image slight zoom
- **Heart/save**: Top-right corner cua image

### 2.4 Photo Gallery
- **Asymmetric grid**: 1 anh lon (trai, ~60% width) + 4 anh nho (phai, 2x2 grid)
- **Overlap badges**: Photo count ("12 photos") bottom-right cua grid
- **Click → fullscreen carousel** voi thumbnail strip phia duoi
- **Video support**: First slot co the la video voi play button overlay

### 2.5 Search
- **Compact search trong header**: Input + destination autocomplete dropdown
- **Autocomplete**: Phan loai theo Destinations, Activities, Attractions voi icons rieng
- **No map view** tren trang ket qua chinh (chi co map embed trong detail page)

### 2.6 Filter System
- **Filter bar**: Horizontal chip row, sticky khi scroll
- **Chips**: Date, Language, Duration, Price range, Time of day, Category
- **Active filters**: Badge count tren "Filters" button
- **Sort**: Recommended / Price / Rating dropdown

### 2.7 Detail Page
- **Section order**: Gallery → Title+rating+category → Quick facts (duration/language/mobile ticket) → Description (truncated + "Read more") → Highlights (checkmark list) → What's included/excluded → Meeting point (Google Map embed) → Reviews → Similar activities
- **Sticky booking sidebar** (desktop): Price + date picker + "Check availability" CTA
- **AI-summarized reviews**: Tong hop tu dong tu nhieu review thanh 2-3 bullet points

### 2.8 Review Display
- **Star rating**: 5 sao vang, hien 1 decimal (VD: 4.7)
- **Review count**: "(2,847 reviews)" — social proof manh
- **AI summary**: Tren cac review ca nhan, hien tom tat tu dong
- **Individual review**: Avatar circle + name + country flag + date + star rating + text
- **Filter reviews by**: Star level, language

### 2.9 Responsive
- 4-col → 3-col → 2-col → 1-col activity grid
- Gallery: Desktop asymmetric → mobile horizontal swipe carousel
- Booking sidebar → bottom sticky bar (mobile)

### 2.10 Micro-interactions
- Image hover zoom (scale 1.05, transition 300ms)
- Filter chip toggle animation
- Review "Read more" expand (height transition)
- Itinerary timeline voi map markers connected by dotted line

---

## 3. Klook {#3-klook}

### 3.1 Information Architecture
- **Homepage**: Top deals banner → destination cards carousel → "Things to do" category grid → trending activities → editorial content → app download CTA → footer
- **Destination page**: Hero voi search → chip navigation (Tours, Tickets, Transport, etc.) → activity grid → editorial guides
- **Strong SEA focus**: Content toi uu cho thi truong Dong Nam A (36+ ngon ngu, noi dung rieng cho VN)

### 3.2 Category Navigation
- **Chip-based categories** tren destination page: Tours & Sightseeing, Tickets & Attractions, Transport, Food & Drink, etc.
- **Icon + text** cho moi category chip
- **Bottom-sheet hamburger menu** (mobile): Slide-up panel thay vi sidebar

### 3.3 Card Patterns
- **Destination cards**: 3:4 portrait ratio, text overlay gradient (ten destination + "X activities"), border-radius 16px
- **Activity cards**: 3-col grid, 16px radius, image top → title → location → rating → price (orange accent color)
- **Orange accent** (#FF5722 hoac tuong tu) xuyen suot — CTA, price, badges
- **Card gap**: 16px giua cards

### 3.4 Photo Gallery
- **Activity detail**: Main image carousel (16:9) voi dot navigation
- **Thumbnail strip** phia duoi main image
- **User-submitted photos** trong review section

### 3.5 Search
- **Rotating search placeholder**: Text animation xoay vong ("Search for activities", "Search for food tours", "Search Ho Chi Minh")
- **Autocomplete**: Group theo category (Destinations / Activities / Deals)
- **Recent searches** hien thi khi focus

### 3.6 Filter System
- **Chip-based package selection**: Trong detail page, chon package bang chips (khong dropdown)
- **Filter categories**: Price range, Duration, Rating, Category, Language
- **Sticky tab navigation**: Khi scroll qua hero, tab bar sticky voi category names

### 3.7 Detail Page
- **Section order**: Image carousel → Title + rating + booking count → Package selection (chips) → Description → Highlights → How to use → Cancellation policy → Reviews → Similar
- **Booking count social proof**: "1,234 booked today" — so lieu thuc
- **Package chips**: Thay vi dropdown, moi package la mot chip co ten + gia, click de chon

### 3.8 Review Display
- **Star rating**: 5 sao, 1 decimal
- **"Verified purchase" badge** tren reviews
- **Photo reviews** duoc uu tien hien thi
- **Review filters**: Rating, Has photos, Language
- **Review summary**: Bar chart phan bo rating (5★ = 80%, 4★ = 15%, etc.)

### 3.9 Responsive / SEA Market
- **36+ languages** voi content localized (khong chi dich)
- **Vietnam-specific content**: Noi dung viet rieng cho thi truong VN
- **Mobile-first**: Bottom-sheet patterns, swipe carousels
- **Price display**: Local currency auto-detect

### 3.10 Micro-interactions
- **Package chip selection**: Smooth highlight transition
- **Price update animation**: Khi chon package khac, gia update voi fade transition
- **Carousel snap**: Swipe voi snap-to-card physics
- **Bottom-sheet**: Spring animation khi mo/dong

---

## 4. Google Travel {#4-google-travel}

### 4.1 Information Architecture
- **Cuc ky toi gian**: Khong hero, khong banner, khong marketing
- **Explore page**: Search bar → map (chiem 60%+ viewport) + list panel (400px) → filter chips
- **Hotel detail**: Image grid → title + rating → prices table → amenities → reviews → location map
- **Trip planner**: Saved places + itinerary builder

### 4.2 Category Navigation
- **Minimal tabs**: Hotels / Vacation Rentals / Flights — chi 3 tab chinh
- **No icon, no emoji** — chi text
- **Active tab**: Bold text + underline, khong background change

### 4.3 Card Patterns
- **Flat cards**: KHONG shadow, KHONG border, KHONG decoration
- **Card anatomy**: Image (16:9) → name → rating (stars + count) → price → 1-line description
- **Separation**: Chi bang whitespace (24-32px)
- **Image**: Rounded corners 8px
- **"Extreme type restraint"**: Chi 3 kich co font + 2 weights xuyen suot

### 4.4 Photo Gallery
- **Grid layout**: Tuong tu Airbnb — 1 lon + 4 nho
- **Click → fullscreen** voi swipe navigation
- **Google Street View integration**: Panorama embed cho location

### 4.5 Search + Map View (DI DANG)
- **Split-panel layout**: List panel 400px (trai) + map 60% (phai)
- **Map la thanh phan CHINH**, khong phai phu — chiem phan lon viewport
- **Progressive disclosure**: Click item trong list → detail replaces list TRONG CUNG panel (khong mo trang moi)
- **Map pins**: Gia hien thi tren pin (tuong tu Airbnb nhung don gian hon)
- **Pan/zoom map → list update** tu dong

### 4.6 Filter System
- **Filter chips**: Nho (32-36px height), border-radius 4px (khong tron hoan toan nhu Airbnb)
- **Chip style**: Outlined default, filled khi active
- **Filters**: Price, Rating, Amenities, Hotel class, Brand
- **"When prices change, we tell you"** — transparent pricing communication

### 4.7 Detail Page
- **In-panel detail** (khong navigate sang trang moi):
  - Image grid (compact)
  - Name + star rating
  - Price comparison table (from multiple OTAs)
  - Icon-grid amenities (icons + label, 3-col grid)
  - Brief description
  - Reviews snippet
  - Location section
- **CTA**: "View deal" buttons (link to OTA) — Google khong ban truc tiep

### 4.8 Review Display
- **Google Reviews integration**: Star rating (5 sao) + review count
- **Review highlights**: AI-extracted "mentioned in reviews" phrases
- **Category breakdown**: Cleanliness, Service, Location — horizontal bar charts
- **Mix sources**: Google Reviews + OTA reviews

### 4.9 Responsive
- **Map collapse**: Tren mobile, map chuyen thanh toggle button phia tren list
- **Panel → full-width**: List panel chiem 100% width tren mobile
- **Breakpoints**: ~600px (mobile), ~900px (tablet), ~1200px (desktop)

### 4.10 Micro-interactions
- **Map pin hover**: Enlarge + show preview card
- **Panel transition**: Slide animation khi detail replaces list
- **Filter chip toggle**: Instant, khong animation (on-brand voi Google Material)
- **Pricing highlight**: Green text cho "great deal" prices

---

## 5. TripAdvisor {#5-tripadvisor}

### 5.1 Information Architecture
- **Destination page IA**:
  1. Hero image + destination name
  2. AI chat widget ("Ask AI about [destination]")
  3. Category chips (Hotels, Things to Do, Restaurants, Flights, Vacation Rentals, Cruises)
  4. 3-col grid grouped by type (Hotels, Things to Do, Restaurants — moi nhom la 1 section)
  5. Travel guides / editorial
  6. Forum/community section
  7. Footer
- **Entity page**: Gallery → title + rating + ranking → AI summary → review highlights → details → map → similar

### 5.2 Category Navigation
- **Category chips** ngang: Hotels / Things to Do / Restaurants / Flights / Vacation Rentals / Cruises
- **Each chip**: Icon + text, rounded pill shape
- **Click → filter page content** (khong navigate sang trang moi)

### 5.3 Card Patterns
- **Entity cards**: 4:3 image ratio + carousel dots (nhieu anh) + bubble rating + category tag + title + "from $XX" price
- **3-col grid layout** cho destination pages
- **Card shadow**: Subtle shadow (0 2px 8px rgba(0,0,0,0.1))
- **Photo count social proof**: "595,000+ photos" hien thi tren destination hero

### 5.4 Photo Gallery
- **Photo count prominence**: So luong anh la social proof (VD: "595,000+ traveler photos")
- **Gallery grid**: Masonry-style hoac uniform grid
- **User-submitted dominant**: Phan lon la anh tu travelers, khong phai anh marketing
- **Filter photos by**: Category (Hotel, Restaurant, Attraction), recency

### 5.5 Search
- **Search bar**: "Where to?" placeholder
- **Autocomplete**: Group theo entity type (Hotels, Restaurants, Things to Do, Forums)
- **AI search**: "Plan with AI" button ben canh search bar

### 5.6 Filter System
- **Filter panel** (trai): Vertical sidebar voi checkboxes + sliders
- **Filters**: Price range (slider), Rating (bubble), Cuisine type, Meal type, Dietary, Features
- **"Popular mention" chips**: Trong review section — click de filter reviews theo keyword

### 5.7 Detail Page
- **Entity (Restaurant/Attraction) detail**:
  1. Gallery (carousel + "See all X photos")
  2. Title + bubble rating (#X of Y [type] in [city]) — ranking la diem noi bat
  3. Quick info: Address, hours, phone, website
  4. AI-generated summary (moi)
  5. "Popular mentions" chips (tu review analysis)
  6. Reviews (sorted by recency default)
  7. Details & location (map)
  8. Similar nearby
- **KHONG co booking widget** cho restaurants — CTA la "Reserve" link den OpenTable/external

### 5.8 Review Display (DAC BIET)
- **Bubble rating** (KHONG phai stars): 5 hinh tron mau xanh la (green circles), fill theo muc do
  - 5 bubbles = Excellent, 4 = Very good, 3 = Average, 2 = Poor, 1 = Terrible
  - Day la thuong hieu dac trung cua TripAdvisor
- **Review section anatomy**:
  - Overall bubble rating + review count
  - Rating distribution bar chart
  - "Popular mentions" chips (extracted keywords: "great view", "delicious food", "friendly staff")
  - Search reviews input
  - Sort: Most recent / Detailed / Rating
  - Individual review: Avatar + name + location + contributions count + bubble rating + title + date + text + helpful votes

### 5.9 AI Integration (MOI)
- **"Plan with AI"**: Tren destination page — AI trip planner
- **"Ask AI"**: Chat widget tren entity pages
- **AI review summaries**: Tom tat tu dong tu nhieu reviews
- **AI-generated destination guides**: Noi dung editorial tu AI

### 5.10 Community / Forum
- **Q&A format**: Hoi-dap ve destination
- **"Destination experts"**: Badge cho nguoi dong gop nhieu
- **Forum threads**: Sorted by recency, voi reply count
- **Traveler photos**: Gallery rieng cho UGC photos
- **Contribution system**: Count so reviews + photos + helpful votes → level/badge

---

## 6. Airbnb {#6-airbnb}

### 6.1 Information Architecture
- **Content-first homepage**: KHONG hero image, KHONG banner, KHONG marketing block
- **Homepage flow**: Sticky header (80px) → Search bar (pill-shaped, 3 segments: Where|When|Who) → Personalized carousel sections → "Inspiration for future getaways" tab bar → Footer
- **Category tabs** (header): All (globe) / Homes (house) / Experiences (pin) / Services (bell) — emoji icons, khong SVG
- **Section titles personalized**: "Popular homes in [City]", "Great hotels for your next trip"

### 6.2 Category Navigation
- **Top tabs**: Icon+label pairs, emoji illustrations, underline active indicator
- **Tab widths**: All=66px, Homes=104px, Experiences=125px, Services=106px
- **Tab switch = doi toan bo noi dung trang** — top-level navigation, khong phai filter

### 6.3 Card Patterns
- **Homepage carousel cards**: 191px width, 5 per row, 12px gap
  - Image: ~1:1 (square), border-radius 12px
  - Line 1: Property type + location
  - Line 2: Price + star rating
  - Heart/save: 32x32px top-right, white heart tren semi-transparent dark bg
  - Badges: "Guest favorite" (top-left, 11px font, 600 weight), "Superhost" (black pill)

- **Search result cards**: 440px full-width (left column)
  - Image: ~250px height (landscape), carousel voi 5 dots
  - Content: Type+location | rating (right-aligned) → name → specs → dates → **price (bold/underlined)** → tags
  - **KHONG border, KHONG shadow** — separation bang whitespace

### 6.4 Photo Gallery
- **Grid**: 1 large (493x493, 1:1) + 4 small (238x238-246, ~1:1) — 2x2 grid
- **Gap**: ~8px
- **Total width**: ~985px
- **Rounded corners**: Top-left tren large, top-right+bottom-right tren right column
- **"Show all photos" button**: Bottom-right, white pill voi grid icon
- **Click → fullscreen gallery modal**

### 6.5 Search + Map View
- **Split layout**: 440px list (45%) + ~530px map (55%)
- **Map sticky** khi scroll list
- **Map pins**: White rounded-rectangle pills voi price text (VD: "d3,252,354")
  - Hover: Invert to black bg/white text + highlight tuong ung card trong list
  - Click: Mini card popup phia tren pin
- **Map controls**: Zoom +/-, fullscreen toggle

### 6.6 Filter System
- **Filter bar** (duoi header): Horizontal chip row
- **"Filters" button** (co settings icon) → full modal voi tat ca categories
- **Quick filter chips**: Amenity toggles — Wifi, Washer, Kitchen, Free cancellation, Air conditioning, etc.
- **Chip style**: Pill (24px radius), 1px border #DDD, white bg, 34px height
- **Active**: Black bg, white text

### 6.7 Detail Page (DAY DU)
Section order (20+ sections voi HR dividers):
1. Title (H1, 26px, weight 500) + Share/Save buttons
2. Photo grid (1+4)
3. Property type + location
4. Specs: "2 guests . 1 bedroom . 1 bed . 1 bath"
5. Rating + reviews link
6. Host info: Avatar (48px circle) + name + badge
7. Highlights: Icon (40x40) + title + description (2-3 items)
8. Description (truncated + "Show more" pill button)
9. "Where you'll sleep" room cards
10. "What this place offers" amenities: Icon (24px) + label list + "Show all X amenities"
11. Calendar widget (month view, 7-col grid)
12. Reviews section
13. "Where you'll be" Google Map (~400px tall) + location privacy note
14. "Meet your host" card (avatar, stats, verified badge, response rate/time, "Message host")
15. "Things to know" 3-col grid (Cancellation/House rules/Safety)

**Booking widget** (RIGHT COLUMN, sticky):
- 277px wide, sticky position
- Date picker (CHECK-IN/CHECKOUT split input)
- Guests dropdown
- CTA: "Check availability" — full-width, radius 999px, pink gradient (#FF385C), 48px height, 16px font

**Sticky section nav**: "Photos | Amenities | Reviews | Location" — xuat hien KHI scroll qua gallery

**Condensed header booking bar**: Khi booking widget scroll ra khoi view → header hien price + CTA

### 6.8 Review Display
- **Star rating**: 5 black stars (KHONG mau)
- **6 category breakdown**: Cleanliness, Accuracy, Check-in, Communication, Location, Value — horizontal bar graph
- **"Guest favorite" badge** khi ratings outstanding
- **Review card**: Avatar (48px) + name + tenure ("7 years on Airbnb") + 5 stars + "4 days ago" + text (truncated + "Show more")
- **"How reviews work"** link — transparency

### 6.9 Responsive Design
- **Homepage**: 5-col → responsive breakdowns
- **Search**: 2-col split (list+map)
- **Detail**: Content (~490px) + sidebar (~277px)
- **Page padding**: 32-40px
- **Breakpoints** (standard Airbnb):
  - 744px: Tablet (2-col cards, map toggleable)
  - 950px: Desktop (map appears alongside)
  - 1128px: Wide desktop (4-col without map)
  - 1440px+: Max content width

### 6.10 Micro-interactions (XUAT SAC)
- **Image carousel**: Dots phia duoi, arrows xuat hien on hover, slide animation
- **Heart/save**: Click → fill red + "pop" scale animation
- **Carousel navigation**: 28x28px arrow circles, snap-to-card, dot pagination
- **Sticky header transition**: Header height giam, search bar collapse tu 3-field pill → compact "Anywhere | Anytime | Add guests" — SIGNATURE INTERACTION
- **Map pin hover**: Cross-highlight (pin ↔ card) dong thoi
- **Font**: "Airbnb Cereal VF" (variable font) — 1 file cho moi weight

---

## 7. So sanh cheo 10 chieu {#7-so-sanh-cheo}

### 7.1 Information Architecture

| Platform | Homepage Approach | Detail Page Length | Progressive Disclosure |
|----------|-------------------|-------------------|----------------------|
| GetYourGuide | Hero search + card grid | Trung binh (~8 sections) | "Read more" truncation |
| Klook | Deal banners + carousels | Trung binh (~8 sections) | Package chips thay dropdown |
| Google Travel | KHONG hero, map-first | Ngan (in-panel, ~5 sections) | Detail replaces list in-panel |
| TripAdvisor | Hero + AI chat + grid | Dai (~10 sections) | "Popular mentions" chip filter |
| Airbnb | KHONG hero, content-first | Rat dai (~15+ sections, HR dividers) | Truncate everywhere + "Show more" |

**Insight cho vinhlong360**: Homepage content-first (theo Airbnb/Google) — KHONG hero banner to. Detail page do dai trung binh voi progressive disclosure.

### 7.2 Card Patterns

| Platform | Image Ratio | Border/Shadow | Badge Position | Price Display |
|----------|-------------|---------------|----------------|---------------|
| GetYourGuide | 3:2 | Subtle shadow | Top-left overlay | Right-aligned, bold |
| Klook | 3:4 (portrait) | 16px radius, no shadow | Top-left | Orange accent |
| Google Travel | 16:9 | KHONG shadow, KHONG border | Khong co | Inline |
| TripAdvisor | 4:3 | Subtle shadow | Top-left | "from $XX" |
| Airbnb | 1:1 (square) | KHONG shadow, KHONG border | Top-left + Top-right | Bottom, bold/underlined |

**Insight cho vinhlong360**: Dung 3:2 hoac 4:3 (landscape/standard) — 1:1 chi hop voi property listings. KHONG can shadow neu whitespace du. Badge top-left.

### 7.3 Photo Gallery

| Platform | Layout | Image Count Shown | Fullscreen |
|----------|--------|-------------------|------------|
| GetYourGuide | 1 large + 4 small (asymmetric) | 5 | Yes, carousel + thumbnails |
| Klook | Carousel (16:9) | 1 + dots | Yes |
| Google Travel | 1 large + 4 small | 5 | Yes |
| TripAdvisor | Carousel + count ("595K photos") | 1-5 | Yes, masonry |
| Airbnb | 1 large (1:1) + 4 small (2x2) | 5 | Yes, modal |

**Insight cho vinhlong360**: Asymmetric grid (1+4) la pattern chung GetYourGuide/Google/Airbnb. Ap dung voi 3:2 ratio cho anh chinh, 1:1 cho anh phu.

### 7.4 Search + Map

| Platform | Map Presence | Split Ratio | Map Pins | Map Interactive |
|----------|--------------|-------------|----------|-----------------|
| GetYourGuide | Chi trong detail | N/A | N/A | Embed only |
| Klook | Khong co | N/A | N/A | N/A |
| Google Travel | MAP-FIRST (60%) | 40:60 (list:map) | Price pills | Pan→update list |
| TripAdvisor | Optional | Toggle | Dot markers | Limited |
| Airbnb | Split view | 45:55 | Price pills | Hover cross-highlight |

**Insight cho vinhlong360**: Map+list split view (theo Google/Airbnb) cuc ky phu hop cho directory du lich. Pin hien ten/category (khong gia). Map nhu secondary — list la primary (60:40 hoac toggle tren mobile).

### 7.5 Filter System

| Platform | Filter Style | Position | Active State | Quick Filters |
|----------|-------------|----------|--------------|---------------|
| GetYourGuide | Horizontal chips | Sticky below header | Filled bg | Yes (destination-specific) |
| Klook | Chips + sidebar | Top + left panel | Filled bg | Yes (category-based) |
| Google Travel | Small chips (4px radius) | Below header | Outlined→filled | Minimal |
| TripAdvisor | Sidebar checkboxes | Left panel | Checked | "Popular mentions" |
| Airbnb | Pill chips (24px radius) | Below header | Black bg/white text | Amenity toggles |

**Insight cho vinhlong360**: Horizontal chip row (sticky) la consensus. Chips: Loai hinh (Am thuc, Di tich, OCOP, Homestay), Khu vuc (huyen/xa), Rating. Style: Outlined default, filled active.

### 7.6 Review / Rating System

| Platform | Rating Style | AI Summary | Category Breakdown | Social Proof |
|----------|-------------|------------|-------------------|--------------|
| GetYourGuide | Stars (5, yellow) | Yes (bullet summary) | No | Review count |
| Klook | Stars (5) | No | Bar chart distribution | "X booked today" |
| Google Travel | Stars (5) | Review highlights | Yes (3 categories) | Review count |
| TripAdvisor | **Bubbles (5, green)** | Yes (AI destination guide) | Yes (sub-ratings) | Photo count (595K+) |
| Airbnb | Stars (5, black) | No | Yes (6 categories) | Host tenure |

**Insight cho vinhlong360**: Stars (5, semantic color) la chuan. Them category breakdown (Khong khi, Chat luong, Gia tri, Phuc vu — 4 categories). "Popular mentions" chips tu TripAdvisor cuc hay cho a11y.

### 7.7 Detail Page Structure (consensus)

Tat ca 5 nen tang co chung pattern nay cho detail page:
```
1. Media (gallery/carousel)          — LUON dau tien
2. Title + rating + metadata         — ngay sau media
3. Quick facts / highlights          — scannable info
4. Description (truncated)           — progressive disclosure
5. Amenities / features              — icon grid
6. Location (map)                    — embed map
7. Reviews                           — social proof
8. Similar / related                 — discovery
9. CTA (sticky)                      — luon hien thi
```

### 7.8 Responsive Patterns

| Breakpoint | Cards/row | Map | Sidebar | Navigation |
|------------|-----------|-----|---------|------------|
| <600px | 1 | Hidden/toggle | Bottom sheet | Bottom tabs / hamburger |
| 600-900px | 2 | Toggle button | Overlay | Top tabs |
| 900-1200px | 3 | Split view | Sticky right | Top tabs + search |
| >1200px | 4-5 | Split view | Sticky right | Full nav |

### 7.9 Micro-interactions (consensus)

| Pattern | Dung boi | Recommend cho vinhlong360 |
|---------|----------|--------------------------|
| Image hover zoom (1.03-1.05) | GYG, Klook, Airbnb | **CO** — don gian, hieu qua |
| Card shadow elevation on hover | GYG, Klook | **CO** — neu card co shadow |
| Heart/save button on image | GYG, Airbnb | **CO** — da co trong favorites |
| Carousel dot navigation | Klook, TripAdvisor, Airbnb | **CO** — cho multi-image cards |
| Filter chip toggle animation | Tat ca | **CO** — CSS transition du |
| Sticky header transition | Airbnb | **KHONG** — phuc tap, it value |
| Map pin cross-highlight | Google, Airbnb | **CO** — neu co map view |
| "Show more" expand | GYG, Airbnb | **CO** — progressive disclosure |
| Snap-to-card carousel | Klook, Airbnb | **CO** — CSS scroll-snap |

### 7.10 Typography & Color

| Platform | Font | Heading Weight | Body Size | Accent Color |
|----------|------|---------------|-----------|--------------|
| GetYourGuide | System stack | 700 | 14-16px | Blue (#0050FF) |
| Klook | Custom | 700 | 14px | Orange (#FF5722) |
| Google Travel | Google Sans / Roboto | 400-500 | 14px | Blue (#1A73E8) |
| TripAdvisor | Trip Sans | 700 | 14-16px | Green (#00AA6C) |
| Airbnb | Cereal VF | 500-600 | 14-16px | Pink (#FF385C) |

**Insight**: Weight 500-700 cho headings (KHONG 800-900). Body 14-16px. Accent color la 1 mau duy nhat, bao hoa cao.

---

## 8. Pattern Library cho vinhlong360 {#8-pattern-library}

### 8.1 ADOPT (ap dung truc tiep)

#### A1. Content-first Homepage
- KHONG hero banner lon — di thang vao noi dung
- Search bar noi bat (pill-shaped hoac rounded input)
- Carousel sections voi heading + "Xem tat ca" link
- **Ly do**: Airbnb + Google chung minh content-first giam bounce rate

#### A2. Card Anatomy chuan
```
┌─────────────────────────┐
│  [Image 3:2]            │
│  ┌─badge─┐    ♡ save    │
│  │OCOP 5★│              │
│  └───────┘              │
├─────────────────────────┤
│  Title (2 lines max)    │
│  Location • Category    │
│  ★ 4.5 (23 danh gia)   │
│  Lien he: Zalo │ Goi    │ ← thay vi gia/booking
└─────────────────────────┘
```
- Image ratio: **3:2** (landscape, tot cho phong canh)
- Border-radius: 12-16px
- Badge: Top-left overlay (OCOP rating, "Noi bat", "Moi")
- Save/heart: Top-right
- **CTA**: "Lien he" (Zalo icon + Phone icon) thay vi "Book now"

#### A3. Asymmetric Photo Gallery
```
┌──────────────┬─────┬─────┐
│              │     │     │
│  Main (3:2)  │ sm1 │ sm2 │
│              │     │     │
│              ├─────┼─────┤
│              │ sm3 │ sm4 │
│              └─────┴─────┘
│  "Xem X anh" button      │
└───────────────────────────┘
```
- Main: 60% width, 3:2 ratio
- 4 anh phu: 40% width, 2x2 grid, 1:1 ratio
- Gap: 4-8px
- Click → fullscreen carousel

#### A4. Horizontal Filter Chips
- Sticky below header khi scroll
- Chips: Am thuc | Di tich | OCOP | Homestay | Le hoi | Cho | [Huyen/xa dropdown]
- Style: Outlined default (1px border), filled active (primary color bg)
- Height: 36px, border-radius: 18px (pill)
- Horizontal scroll tren mobile

#### A5. Progressive Disclosure
- Truncate descriptions > 3 lines + "Xem them" link
- Amenities: Show 6, "Xem tat ca X tien ich" button
- Reviews: Show 3, "Xem tat ca X danh gia" link
- **Pattern tu Airbnb**: Moi section ket thuc bang "Show more" action

#### A6. Detail Page Section Order
1. Gallery (asymmetric grid)
2. Title + rating + category + location
3. Quick facts (gio mo cua, dia chi, SDT, Zalo)
4. Description (truncated)
5. Features/amenities (icon + label grid)
6. Location map (embed)
7. Reviews
8. Related/similar
9. **Sticky CTA bar** (mobile): "Goi dien" | "Nhan tin Zalo"

#### A7. Review Section
- 5-star rating (semantic gold color)
- Rating distribution bar chart (5★ → 1★)
- "Noi bat" mention chips (extracted keywords)
- Individual review: Avatar + ten + ngay + stars + text
- Sort: Moi nhat | Cao nhat | Chi tiet nhat

### 8.2 ADAPT (dieu chinh roi ap dung)

#### B1. Map + List View
- **Original**: 45:55 list:map (Airbnb), 40:60 (Google)
- **Adapt cho vinhlong360**: 60:40 list:map (list uu tien — khong co gia de hien tren pin)
- Map pins: Category icon (fork=am thuc, temple=di tich, star=OCOP) thay vi gia
- Mobile: Map la toggle button, khong split
- **Leaflet/OpenStreetMap** (free) thay vi Google Maps (tra phi)

#### B2. Booking Widget → Contact Widget
- **Original**: Date picker + guests + "Reserve" (Airbnb)
- **Adapt**: Sticky sidebar (desktop) / bottom bar (mobile)
  ```
  ┌─────────────────────┐
  │  ★ 4.5 (23 reviews) │
  │  📍 Vinh Long city   │
  │  🕐 7:00 - 21:00     │
  │                      │
  │  [📱 Zalo] [📞 Goi]  │  ← 2 CTA buttons
  │  [🔗 Website]        │  ← optional
  └─────────────────────┘
  ```
- CTA style: Primary color, full-width, 48px height, pill radius

#### B3. Trust Signals → Community Signals
- **Original**: "Guest favorite", "Superhost", "Verified" (Airbnb)
- **Adapt cho vinhlong360**:
  - "OCOP 4 sao" / "OCOP 5 sao" — badge chinh thuc
  - "Top danh gia" — khi rating > 4.5 va > 10 reviews
  - "Dia diem xac thuc" — admin verified
  - "Cong dong goi y" — khi duoc nhieu user save

#### B4. AI Features → Knowledge Agent
- **Original**: AI review summary (GYG), AI trip planner (TripAdvisor), AI chat (TripAdvisor)
- **Adapt**: Knowledge Agent da co (chatbot ve Vinh Long)
  - Them "Hoi ve [ten dia diem]" button tren detail page
  - Agent tra loi dua tren entity data trong DB
  - KHONG them tinh nang AI moi — dung infrastructure hien co

#### B5. "Popular Mentions" → Tag Cloud
- **Original**: TripAdvisor extract keywords tu reviews
- **Adapt**: Dung tags/categories da co trong DB
  - Hien thi nhu clickable chips tren review section
  - Click → filter reviews chua keyword do

### 8.3 SKIP (khong ap dung)

| Pattern | Ly do |
|---------|-------|
| Date picker / availability calendar | Khong co booking |
| Price comparison table (Google) | Khong co gia |
| Package selection chips (Klook) | Khong co packages |
| "X booked today" counter (Klook) | Khong co booking metrics |
| Rotating search placeholder (Klook) | Khong can — search don gian |
| "Plan with AI" trip builder (TripAdvisor) | Qua phuc tap cho solo dev |
| Variable font (Airbnb Cereal) | Da co font system tot |
| Two-state collapsing search (Airbnb) | Phuc tap, it value |
| Real-time price pins on map (Airbnb/Google) | Khong co gia |
| Guest/host messaging (Airbnb) | Users dung Zalo |
| Verified purchase badge (Klook) | Khong co purchase flow |

---

## 9. Khuyen nghi cu the: CSS + Component {#9-khuyen-nghi}

### 9.1 CSS Variables can them/update

```css
/* Card patterns (tu cross-platform consensus) */
--card-image-ratio: 3 / 2;         /* landscape, tot cho phong canh */
--card-radius: var(--radius-3);     /* 12px — consensus GYG/Airbnb */
--card-gap: var(--space-4);         /* 16px */
--card-badge-font: var(--text-xs);  /* 11-12px, weight 600 */
--card-badge-radius: var(--radius-2); /* 8px pill */

/* Filter chips */
--chip-height: 36px;
--chip-radius: 18px;                /* full pill */
--chip-border: 1px solid var(--border-default);
--chip-active-bg: var(--surface-inverse);
--chip-active-text: var(--text-on-inverse);
--chip-gap: var(--space-2);         /* 8px between chips */

/* Gallery grid */
--gallery-gap: var(--space-1);      /* 4px — tight, nhu Airbnb */
--gallery-main-ratio: 3 / 2;
--gallery-thumb-ratio: 1 / 1;
--gallery-main-width: 60%;

/* Map split */
--split-list-width: 60%;
--split-map-width: 40%;
--map-pin-radius: var(--radius-2);
--map-pin-bg: var(--surface-elevated);
--map-pin-shadow: var(--shadow-2);

/* Contact widget (thay booking) */
--contact-widget-width: 320px;
--contact-cta-height: 48px;
--contact-cta-radius: var(--radius-pill);  /* 999px */
--contact-cta-bg: var(--primary);

/* Detail page */
--detail-content-max: 680px;
--detail-sidebar-width: 320px;
--detail-section-gap: var(--space-8);  /* 32px between sections */
--detail-divider: 1px solid var(--border-subtle);

/* Trust badges */
--badge-verified-bg: var(--success-surface);
--badge-verified-text: var(--success);
--badge-featured-bg: var(--warning-surface);
--badge-featured-text: var(--warning);
--badge-ocop-bg: var(--primary-surface);
--badge-ocop-text: var(--primary);
```

### 9.2 Component Specs

#### EntityCard.vue
```
Props: entity, variant ('grid' | 'list' | 'carousel')
Slots: badge, actions
Layout:
  - Image container: aspect-ratio var(--card-image-ratio), overflow hidden, radius var(--card-radius)
  - Badge overlay: position absolute, top 8px left 8px, z-index 1
  - Save button: position absolute, top 8px right 8px
  - Content: padding 12px 0
  - Title: --text-base, weight 600, 2-line clamp
  - Meta: --text-sm, color --text-secondary, "location • category"
  - Rating: star icon + number + count
  - CTA: 2 inline buttons (Zalo, Phone) hoac 1 "Chi tiet" link
Hover: image scale(1.03) transition 300ms, optional shadow elevation
```

#### PhotoGallery.vue
```
Props: images (array), layout ('asymmetric' | 'carousel' | 'single')
Layout (asymmetric):
  - CSS Grid: grid-template-columns: 3fr 2fr, grid-template-rows: 1fr 1fr
  - Main image: grid-row: 1 / -1 (span 2 rows)
  - 4 thumbnails: 2x2 trong right column
  - Gap: 4px
  - "Xem X anh" button: position absolute, bottom 12px right 12px
  - Border-radius: outer corners only (top-left main, top-right+bottom-right right col)
Click: open fullscreen modal voi carousel + close button
Mobile: single carousel voi dots + swipe
```

#### FilterChips.vue
```
Props: filters (array of {key, label, icon?}), modelValue (selected keys)
Layout:
  - Horizontal flex, gap 8px
  - overflow-x: auto, scroll-snap-type: x mandatory
  - -webkit-overflow-scrolling: touch
  - Hide scrollbar: scrollbar-width: none
Chip:
  - height 36px, padding 0 16px
  - border-radius 18px (pill)
  - border: 1px solid var(--border-default)
  - font-size var(--text-sm), weight 500
  - Transition: background-color 150ms, color 150ms, border-color 150ms
Active:
  - background: var(--surface-inverse)
  - color: var(--text-on-inverse)
  - border-color: transparent
```

#### ContactWidget.vue (thay BookingWidget)
```
Props: entity (name, phone, zalo, website, hours, rating, reviewCount)
Layout (desktop sidebar):
  - width var(--contact-widget-width)
  - position: sticky, top: calc(var(--header-height) + 16px)
  - background: var(--surface-elevated)
  - border-radius: var(--radius-3)
  - box-shadow: var(--shadow-3)
  - padding: 24px
Content:
  - Rating: star + number + "(X danh gia)"
  - Location: pin icon + address
  - Hours: clock icon + gio mo cua
  - Divider: 1px solid var(--border-subtle), margin 16px 0
  - CTA group: 2 buttons (Zalo primary, Phone secondary), full-width, 48px height
  - Website link: text link below CTAs
Mobile: fixed bottom bar, 2 buttons side-by-side, 56px height, safe-area padding
```

#### MapListView.vue
```
Props: entities (array), center (lat/lng), zoom
Layout (desktop):
  - CSS Grid: grid-template-columns: var(--split-list-width) var(--split-map-width)
  - List: overflow-y: auto, max-height: calc(100vh - header)
  - Map: position: sticky, top: var(--header-height), height: calc(100vh - header)
Map pins:
  - Category icon markers (thay vi gia)
  - Hover: enlarge + show entity name tooltip
  - Click: scroll-to-card trong list + highlight card
Mobile (<768px):
  - Full-width list
  - "Ban do" toggle FAB button (bottom-right)
  - Toggle: Map overlay full viewport voi "Danh sach" button de quay lai
```

#### ReviewSection.vue
```
Props: reviews, rating, reviewCount, categories
Layout:
  - Header: "Danh gia" H2 + overall rating (large) + count
  - Distribution: 5 horizontal bars (5★→1★), width proportional
  - Category ratings: 4-col grid (Khong khi, Chat luong, Gia tri, Phuc vu)
  - Mention chips: horizontal scroll, extracted from review text
  - Sort: dropdown (Moi nhat, Cao nhat, Chi tiet nhat)
  - Review list: avatar + name + date + stars + text (truncated)
  - "Xem tat ca X danh gia" button
```

### 9.3 Layout Breakpoints (cross-platform consensus)

```css
/* Mobile first */
--bp-sm: 600px;    /* 1-col → 2-col cards */
--bp-md: 768px;    /* Map toggle appears */
--bp-lg: 1024px;   /* Split view (list+map), sidebar appears */
--bp-xl: 1280px;   /* 4-col cards, wider content */
--bp-2xl: 1440px;  /* Max content width */
```

### 9.4 Animation/Motion (cross-platform consensus)

```css
/* Image hover zoom */
.card-image:hover img {
  transform: scale(1.03);
  transition: transform 300ms var(--ease-standard);
}

/* Heart/save button "pop" */
@keyframes heart-pop {
  0% { transform: scale(1); }
  50% { transform: scale(1.3); }
  100% { transform: scale(1); }
}
.save-btn.active {
  animation: heart-pop 300ms var(--ease-emphasized);
  color: var(--error); /* red heart */
}

/* Filter chip toggle */
.chip {
  transition: background-color 150ms, color 150ms, border-color 150ms;
}

/* Progressive disclosure expand */
.expandable-content {
  display: grid;
  grid-template-rows: 0fr;
  transition: grid-template-rows 300ms var(--ease-standard);
}
.expandable-content.open {
  grid-template-rows: 1fr;
}

/* Card carousel snap */
.carousel {
  scroll-snap-type: x mandatory;
  scroll-behavior: smooth;
  -webkit-overflow-scrolling: touch;
}
.carousel-item {
  scroll-snap-align: start;
}
```

---

## Ghi chu phap ly

Tai lieu nay la **phan tich pattern thiet ke** (UI patterns, layout structures, interaction behaviors) — KHONG sao chep code, hinh anh, noi dung, hay thuong hieu cua bat ky nen tang nao. Cac pattern duoc mo ta la kien thuc thiet ke chung (design knowledge), tuong tu viec phan tich xu huong thiet ke trong sach/bao/conference.

Moi khuyen nghi cho vinhlong360 deu duoc thiet ke rieng, phu hop voi mo hinh "chi gioi thieu" (§1.4 CLAUDE.md) va KHONG sao chep truc tiep bat ky yeu to nao co ban quyen.
