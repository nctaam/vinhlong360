# Kế hoạch Redesign Cinematic + Premium — Toàn bộ trang Public

> **STATUS (2026-07-07): superseded một phần bởi declutter 3 đợt.** Section chatbot-CTA homepage (dòng ~86) đã bị XOÁ (declutter B1-1) — đừng dựng lại. Trang liên hệ: KHÔNG claim "Con người thật/SLA X giờ" (không kiểm chứng được, solo dev, byline cấp tổ chức). Concepts con: xem cảnh báo trong redesign-concepts/00-narrative-system.md.


> **Nguồn:** Audit 36 trang public (5 agent song song, 2026-07-05) + bối cảnh hệ thống thiết kế đã triển khai (CE1–CE3). Thực thi qua skill **frontend-design**, verify bằng preview-probe, deploy theo đợt.
> **Mục tiêu:** Nâng TẤT CẢ trang public lên một giọng **cinematic-editorial** nhất quán, premium — không phá vỡ tính năng, không thêm chi phí, ảnh chỉ AI-gen.

---

## 0. Tóm tắt điều hành

Website hiện **vững về kỹ thuật** (điểm trung bình ~6.4/10) nhưng **phân mảnh về thị giác thành 3 tầng**. Ngôn ngữ "cinematic-editorial" (serif masthead Fraunces, eyebrow dateline, màu 3 tỉnh clay/leaf/river/amber, dấu ấn "phù-sa/trầm-tích", hero ảnh thật, motion tinh tế) **chỉ chạm tới hero** của 4 trang tier-1, rồi dừng lại.

**Phát hiện keystone:** đơn vị hình ảnh lặp nhiều nhất — **`EntityCard`** — chưa hề được "CE hoá". Nên dù hero của trang có premium đến đâu, mọi lưới thẻ bên dưới đều tụt về vẻ "generic travel-listing". **Một pass CE cho `EntityCard` nâng cấp gần như MỌI trang cùng lúc** — đây là đòn bẩy #1.

### Ba tầng hiện trạng

| Tầng | Đặc điểm | Trang | Điểm TB |
|---|---|---|---|
| **1 — Cinematic** | CE đầy đủ tới hero + section head | home · khu-vực · xã-phường · chi-tiết | ~7.5 |
| **2 — Catalog** | `catalog-hero` chung (emoji + serif h1), body generic | index-địa-điểm · khám-phá · sản-phẩm · OCOP · sự-kiện · lễ-hội · du-lịch · lưu-trú · theo-mùa · tuyến-đường · danh-bạ · lịch-trình×3 · tạo-lịch-trình · bản-đồ · tìm-kiếm | ~6.5 |
| **3 — Social / Account / Static** | **KHÔNG có CE** (grep: 0 `--font-editorial`, 0 token 3 tỉnh, 0 sediment tick) | cộng-đồng · bài-viết · xếp-hạng · hồ-sơ · thông-báo · đã-lưu · cài-đặt · tài-khoản · giới-thiệu · liên-hệ · hướng-dẫn×2 · bảo-mật · điều-khoản · 404 | ~5.6 |

### Bảng điểm hiện trạng (36 trang)

| Điểm | Trang |
|---|---|
| **8.5** | `index` (home) · `theo-mua` |
| **7.5** | `khu-vuc/[area]` · `ocop` · `du-lich` · `nguoi-dung/[id]` |
| **7** | `dia-diem/[id]` · `xa-phuong/[id]` · `lich-trinh/[id]` · `le-hoi` · `luu-tru` · `tuyen-duong` · `danh-ba` · `bai-viet/[id]` · `lien-he` |
| **6.5** | `kham-pha/[interest]` · `su-kien` · `cong-dong` · `huong-dan` |
| **6** | `dia-diem/index` · `lich-trinh/index` · `tao-lich-trinh` · `ban-do` · `bang-xep-hang` · `huong-dan-thanh-vien` · `tim-kiem` |
| **5.5** | `da-luu` · `gioi-thieu` · `chinh-sach-bao-mat` · `dieu-khoan-su-dung` |
| **5** | `cai-dat` · `tai-khoan` · `[...slug]` (404) |
| **4.5** | `thong-bao` |
| **3** | `lich-trinh-chia-se/[id]` |

---

## 1. Đòn bẩy keystone (Wave 0 — Foundation, ROI cao nhất)

Làm những thứ này TRƯỚC — mỗi cái nâng cấp NHIỀU trang cùng lúc, chi phí thấp.

### K1 — `EntityCard` CE pass **(đòn bẩy #1)**
Thẻ entity là đơn vị lặp trên ~15 trang. Cấp cho nó ngôn ngữ CE:
- Tiêu đề thẻ dùng `var(--font-editorial)` (serif) thay sans.
- **Eyebrow dateline** nhỏ (loại · khu-vực) chữ hoa giãn rộng thay `cover-tag` pill phẳng.
- **Đường kẻ accent 3 tỉnh** (clay/leaf/river theo khu-vực hoặc màu theo loại) thay hairline xám.
- Placeholder SVG giữ nguyên (đã tốt) nhưng thêm **grain overlay** nhẹ để bớt "phẳng".
- Hover: nâng + scale ảnh tinh tế (đã có, giữ).
→ **Một lần sửa `components/EntityCard.vue` → mọi lưới trên toàn site lên hạng.**

### K2 — Cover no-photo cho trang chi tiết
Trang chi tiết (`dia-diem/[id]`) khi entity KHÔNG có ảnh (~96% lượt) rơi về gradient `--cat-*` **phẳng, không motif**. Trong khi homepage đã chứng minh placeholder SVG (`generateCategoryPlaceholder` + motif glyph + grain) đọc rất tốt.
→ **Áp placeholder SVG vào cover no-photo** (sửa `detail.css` + component cover). Đây là fix đơn lẻ tác động mạnh nhất — trang flagship đang yếu nhất ở trạng thái phổ biến nhất.

### K3 — Trích xuất `season-ring` thành hero-variant dùng chung
`theo-mua` có **`season-ring`** (conic-gradient mã hoá tín hiệu 3 tỉnh green→amber→river thành vòng mùa) — **ý tưởng thị giác mạnh nhất toàn site**, đang bị cô lập một trang.
→ Trích thành **biến thể hero opt-in** cho `<CatalogPage>` (K5) để các trang danh mục khác dùng lại.

### K4 — Token-parity + dọn token-drift
`cai-dat` + `tai-khoan` dùng **giá trị hardcode** (`.85rem`, `1.2rem`, `#c0392b`) thay token, `var(--ink-700)` thay token semantic → "off-brand" rõ. `tai-khoan` còn tham chiếu `--danger:#c0392b` KHÔNG khớp `--error:#D94F3D` thật.
→ **Sweep hardcode → `--text-*`/`--space-*`/`--muted`/`--error`.** Rẻ, xoá "tell" lớn nhất.

### K5 — Trích `<CatalogPage>` layout + `useCatalogFilters()`
7 trang danh mục (`san-pham`, `ocop`, `du-lich`, `luu-tru`, `su-kien`, `le-hoi`, `theo-mua`) dùng **cùng bộ khung** (hero → spotlight → scroll-rows → interstitial → essay → divider → lưới lọc → cross-links) nhưng **copy-paste ~30 dòng** logic `activeFilterCount`/`clearFilters`/pagination/`sortByRegion` + phím tắt "/" ở mỗi file.
→ **Trích `<CatalogPage>` (slots cho hero-icon/stats/sections) + `useCatalogFilters()` composable.** Sửa 1 chỗ → áp mọi trang; K1/K3 gắn vào đây.

### K6 — CE phải "chạm tới thân trang", không dừng ở hero
Sediment tick + serif + eyebrow hiện chỉ ở hero/section-head. Cần lan vào **sidebar (facts/trust card), thân bài, thẻ**. (Nhiều mục per-page dưới đây là instance của nguyên tắc này.)

### K7 — Track ảnh thật (song song, là trần thị giác)
Chỉ 60/1730 entity có ảnh → mọi lưới đầy thẻ placeholder. Chạy các **đợt AI-gen ~30 ảnh** cho điểm-đến/OCOP ưu tiên (pipeline đã chuẩn hoá). Không chặn Wave 0–4 nhưng là thứ nâng "trần" cao nhất về lâu dài.

---

## 2. Redesign chi tiết theo trang

Mỗi trang: **điểm hiện tại → hiện trạng 1 dòng → nước đi redesign cụ thể** (thẩm mỹ · bố cục · giác quan · UX · cinematic).

### TẦNG 1 — Cinematic (tinh chỉnh + đẩy sâu)

#### `index.vue` — Home / cover story — **8.5/10**
Flagship mạnh nhất; premium ở 2/3 trên, **phẳng dần ở 1/3 dưới** (community cards, "dành cho bạn" chips, chatbot CTA là hộp viền trơn).
- **CE cho 1/3 dưới:** community card + for-you chip + chatbot CTA lên serif/eyebrow/accent thay hộp trơn.
- **Bỏ `event-sheen`** (light-sweep xiên — trope promo cũ, không cinematic).
- **Thêm 1 full-bleed break** (kiểu `StorySpread`) ở nửa dưới để trang không "thu nhỏ dần" thành strip.
- Chatbot CTA (cửa ngõ trợ lý AI — điểm khác biệt thật) → khung editorial (serif prompt line + accent phù-sa) thay gradient box + emoji.

#### `dia-diem/[id].vue` — Chi tiết entity (flagship) — **7/10**
Cover premium KHI có ảnh; **fallback no-photo phẳng, không motif** (→ **K2**). Sidebar sans-serif "hệ cũ" bolt lên hero CE.
- **K2** (cover placeholder SVG) — ưu tiên số 1 của trang.
- Đưa sediment tick + serif sub-head vào **sidebar** (`facts-heading`, `trust-card h2`) để không lệch "hệ".
- Phân cấp typography cho 17+ hàng icon+label+value (serif cho giá trị dạng tên vs sans cho metadata) — chống đơn điệu.
- Thêm 1 full-bleed editorial break giữa trang dài để reset nhịp trước lưới AI-recs.

#### `khu-vuc/[area].vue` — Guide khu vực — **7.5/10** *(CE2 đã làm hero)*
Hero premium; **thân trang là "cùng một lưới thẻ lặp 6 lần"** (nhiều carousel EntityCard chồng nhau).
- Spotlight cần **grammar thị giác riêng** (motif full-bleed khác scale / mảnh bản-đồ vẽ tay / pull-quote serif) để không chỉ là "thẻ to nhất".
- Ward chips hiện trơ tên → thêm **count badge / cluster theo huyện**.
- **Per-row stagger** + parallax/scale nhẹ ảnh hero khi scroll (hiện `background-size:cover` tĩnh).
- Interstitial fact chung chung → **đặc thù khu vực** (vd Trà Vinh 140+ chùa Khmer) khớp giọng essay.

#### `xa-phuong/[id].vue` — Hồ sơ xã/phường — **7/10** *(CE3 đã làm)*
CE có mặt tới hero + section-head; **dừng ở đó**; sidebar 320px thường mỏng/lệch; `wp-summary` clamp 4 dòng **không expand**.
- Kéo motif phù-sa vào **thân** (kẻ gradient 3 màu mép trái cột chính / sediment vào `wp-divider` đang là hairline gạch đứt).
- **Trạng thái "ward ít ảnh"** (đây là ca chủ đạo ở granularity 124 phường, không phải edge case) — caption/định khung placeholder là "đang cập nhật có chủ đích".
- Cân lại sidebar (facility count badge, gấp map-link vào) để aside không "trống do lỗi".
- Dùng lại `desc-toggle` (đã có ở entity page) cho `wp-summary` thay clamp câm.

### TẦNG 2 — Catalog (nâng lên bán-cinematic)

#### `dia-diem/index.vue` — Danh bạ toàn bộ ~1730 entity — **6/10**
Lọc **lặp 3 lần** (type ×3, area ×2) trước một lưới `auto-fill` phẳng; dưới spotlight là template chung.
- **Gộp lọc lặp** thành 1 **filter rail editorial sticky** (sediment tick đánh dấu facet đang chọn).
- **K1** (EntityCard CE) — trang này hưởng lợi nhiều nhất.
- Chèn ô "featured" rộng (span 2 cột, kiểu spotlight) mỗi ~12 thẻ, phá đơn điệu lưới.
- Hero có identity riêng cho "danh bạ" (sediment tick lớn sau H1) thay wash chung.

#### `kham-pha/[interest].vue` — Catalog theo sở thích — **6.5/10**
Engineering/IA tốt (lọc 2 tầng, `collectionNarrative` từ số thật) nhưng **pre-CE**: không masthead/eyebrow/tick, hero là hộp emoji.
- **Masthead CE + eyebrow dateline** ("KHÁM PHÁ · ẨM THỰC") thay emoji-trong-halo.
- Sediment tick ở 3 ranh giới section (intro/filter/cross-links) — gần 0 chi phí.
- Cross-link "band" phẳng → **story-block** dùng motif SVG category phóng to làm "media panel".
- `collectionNarrative` → **dek line kiểu CE** dưới masthead (đang là caption nhỏ).

#### `san-pham.vue` — Catalog sản phẩm/OCOP — **7/10**
Trùng khung + gần trùng thị giác với `du-lich`/`ocop`; motif citrus **dùng chung 1:1 với `ocop`**.
- **Motif riêng** (giỏ chợ / quầy hàng line-art) thay citrus dùng chung.
- **Hạ "Sản phẩm OCOP" scroll-row** xuống 1 teaser cross-link (essay OCOP đang trùng `ocop.vue`).
- Framing "quầy sản vật": strip timeline chợ-nổi tháng→trái→tên thay month-chip trơn.

#### `ocop.vue` — Sản phẩm OCOP (cert) — **7.5/10**
Khác biệt tốt nhất họ sản-phẩm (`hero-creds` + honor-roll) nhưng **vẫn twin thị giác với `san-pham`** (chung SVG); nội dung OCOP trùng ~70%.
- **Motif con-dấu/chứng-nhận** (hình dấu tròn) thay citrus — hiện thực hoá lời hứa "official seal".
- **Certificate card** cho 5★ (nền tone giấy, dấu sáp góc).
- **Star ladder** (3★→4★→5★ dạng bậc thang có count) thay quick-pick phẳng.
- Dedupe: giữ `ocop` là trang explainer chuẩn, `san-pham` chỉ teaser.

#### `su-kien.vue` — Sự kiện — **6.5/10**  ·  #### `le-hoi.vue` — Lễ hội — **7/10**
**Ứng viên gộp mạnh nhất:** cùng endpoint `/api/events`, ~90% trùng markup + `events.css`, cross-link lẫn nhau. Lịch âm + iCal + calendar-view là điểm mạnh thật. `le-hoi` có **essay văn hoá hay nhất site** (Kinh–Khmer–Hoa, Ok Om Bok).
- **Gộp thành 1 trang** + segmented tab ("Tất cả · Lễ hội · Sự kiện khác"), tách phần calendar/list thành 1 component. (Nếu giữ 2 URL vì SEO → tối thiểu tách component chung + dừng trùng essay.)
- Nếu giữ riêng: **register thị giác khác nhau** — sự-kiện = ticket-stub + sans đậm (hiện đại); lễ-hội = tone đỏ-sơn-mài + gold + vignette lồng đèn (nghi lễ). Promote essay `le-hoi` **lên trên** hero.
- Animate chuyển tháng calendar (slide theo hướng nav); countdown chip "còn N ngày".

#### `du-lich.vue` — Du lịch (umbrella hub) — **7.5/10**
**Nhịp editorial tốt nhất họ catalog** (5 section xen kẽ = cảm giác lật tạp chí) nhưng hero rơi về **motif fallback generic**.
- **Motif hero riêng** (xuồng/dòng-kênh / cù-lao line-art) — trang hub cần chữ ký nhất.
- Mỗi trong 5 section một micro-accent riêng (làng nghề = hairline đỏ-lò; món ăn = wisp khói) → cảm giác "từng chương".
- Tuyên bố vai trò umbrella: nav strip "Xem theo: Trải nghiệm · Ăn ở · Đặc sản · Sự kiện" (hiện 6 trang là siblings không thấy quan hệ cha-con).
- `featured` = 1 item/loại (đảm bảo breadth) thay "6 cái đầu có ảnh".

#### `luu-tru.vue` — Lưu trú — **7/10**
Cặp motif/màu (palm + river) **khác biệt tốt nhất họ**; nhưng lưới chính **phẳng/thiếu animation** + **thiếu sort control** (peer pages có).
- Thêm **sort (giá thấp→cao)** + list/grid toggle → parity.
- `catalog-type-breakdown` pill → mở rộng thành quick-pick "theo loại" (Homestay/Resort/Khách sạn) cạnh region.
- Chuẩn hoá root `<div class="page">` (đang `<section>`).

#### `theo-mua.vue` — Theo mùa — **8.5/10 (STANDOUT)**
`season-ring` là **ý tưởng thị giác mạnh nhất site** → **K3** (trích dùng chung).
- Grid chọn tháng đang phẳng vs ring tinh tế → **timeline/arc** khớp motif ring.
- Audit "animation-fatigue" (bob + spark + pulse + stagger đồng thời) — stagger start-delay để không chọi nhau.

#### `tuyen-duong.vue` — Tuyến đường — **7/10**
Micro-interaction thẻ tốt; nhưng **thiếu spotlight/scroll-row**, và **hệ màu vùng không khớp** `--AREA-rgb` (mượn token category).
- **Sửa hệ màu vùng** → dùng `--AREA-rgb` như `ocop`/`danh-ba`.
- **Route-overview SVG** (line-path nối stop-dot) trong header thẻ — hiện chỉ list số.
- Map-thumbnail/distance-timeline strip mỗi thẻ ("3h · 65km" thành tỉ lệ thị giác).

#### `danh-ba.vue` — Danh bạ hành chính — **7/10**
Trust/verify UX xuất sắc (`.gov.vn` regex badge, "báo sai"); nhưng **undersell tầm quan trọng chiến lược** (ngách trống mạnh nhất) + `<select>` generic.
- Promote essay/intro **lên trên** quick-picks, masthead civic-editorial → là "flagship utility" không phải trang phụ.
- **Combobox typeahead** (gõ "Vĩnh Long" lọc live) thay `<select>` 124 ward.
- Row "gần tôi" (geolocation) / "ward vừa xem" trên picker.

#### `tim-kiem.vue` — Tìm kiếm — **6/10**
Engineering tương tác tốt; **0 identity CE**; zero-query = 3 lưới quick-pick "link soup".
- Zero-query → **rail "featured tuần này"** ảnh + Ken Burns + eyebrow thay 3 lưới phẳng.
- Result-type chip + list → **màu 3 tỉnh** (clay=du-lịch, leaf=OCOP, river=lưu-trú).
- **Skeleton** (không spinner) cho autocomplete; animate zero-result → recovery.
- **Sediment divider** giữa các nhóm result (entity/người/bài).

#### `ban-do.vue` — Bản đồ — **6/10**
Accessible/robust, 1 hover shadow đẹp; nhưng **popup MapLibre generic** (inline `#666`/`6px` hardcode), filter snap không motion.
- **Restyle popup** thành card token-driven (radius/shadow/typography như entity-card).
- **Animate filter transition** (cross-fade/scale-in marker mới) thay `setData` snap.
- **Slide-in detail panel** (desktop drawer / mobile bottom-sheet) ảnh+summary+CTA thay chỉ popup.
- Hero map-flavored (map-tile mờ sau hero text).

#### `lich-trinh/index.vue` — List lịch trình — **6/10**
Filter vùng **lặp 2 lần** (quick-picks + chip-row); thẻ itinerary chưa nói "hành trình".
- **Gộp filter lặp** → nhường chỗ cho strip editorial 3-4 itinerary flagship ảnh route full-bleed.
- `ItineraryCard`: **motif tuyến** (đường chấm + stop-dot đánh số ở mép ảnh) — thẻ tự đọc là "journey".
- Hero → `.cine-hero` full-bleed (dùng `/img/area-*.webp` xoay vòng) thay emoji+gradient.

#### `lich-trinh/[id].vue` — Chi tiết lịch trình — **7/10 (mạnh nhất tier-2)**
Timeline spine + route-leg là **"khoảnh khắc journey" tốt nhất site**; nhưng hero generic + **map chôn dưới cùng** (visual weight ngược).
- **Route hero full-bleed**: ảnh area + SVG silhouette tuyến ở đáy hero (xem "hình dạng chuyến đi" trước khi scroll).
- **Map sticky 2 cột** (map phải sticky / timeline trái scroll) — click marker ↔ highlight step đồng bộ.
- **Reveal timeline theo scroll** (stop hiện dần) thay reveal cả block.

#### `lich-trinh-chia-se/[id].vue` — Lịch trình chia sẻ — **3/10 (YẾU NHẤT)**
Trang "chưa mặc quần áo": không CE, **không dark-mode**, không motion, **không map dù data giống hệt** `lich-trinh/[id]`. Đây là trang người-lạ-lần-đầu-thấy sản phẩm.
- **Nâng ngang `lich-trinh/[id]`**: hero + dark-mode + render map route (component đã có, chỉ chưa wire).
- Dùng lại `.timeline`/`.step` (spine đánh số) thay `.sp-stop` trơ.
- **CTA "Nhân bản lịch trình này"** (clone → pre-fill `tao-lich-trinh`) — hạ ma sát viewer→creator.

#### `tao-lich-trinh.vue` — Trình tạo lịch trình — **6/10**
Sophisticated nhất về engineering; nhưng **reorder = 2 nút mũi tên** (kém tactile nhất) — undercut lời hứa "Sắp xếp".
- **Drag-and-drop thật** (pointer-based, giữ ↑/↓ làm fallback a11y) — plumbing re-render map/route đã có.
- Builder side: mỗi stop như **thẻ trên bảng itinerary** (drag handle, xoay/shadow khi kéo, spring snap).
- Map **persistent** (mini-map cột phải từ click đầu) thay chỉ hiện sau ≥2 stop.
- "Bay" ghost-card từ picker→builder khi add (bán "đang thêm vào chuyến đi" cinematically).

### TẦNG 3 — Social / Account / Static (đưa vào vũ trụ CE)

#### `nguoi-dung/[id].vue` — Hồ sơ người dùng — **7.5/10**
Sâu nhất về nội dung/gamification; **cover photo = canvas cinematic lớn nhất chưa dùng** toàn site.
- **THE page để đưa CE cover**: Ken Burns cover, scrim accent 3 tỉnh, tên serif `--font-editorial`.
- **Hợp nhất** achievement grid + heatmap + XP bar (3 hệ thị giác rời) dưới 1 idiom "progress" chung (cùng accent gradient + iconography phù-sa).
- Badge cấp độ → **màu 3 tỉnh** (clay→leaf→river→amber) — lên cấp có payoff màu.
- Reveal cho **header** (hiện pop không transition).

#### `bai-viet/[id].vue` — Chi tiết bài viết — **7/10**
Content-complete nhất (Q&A, edit, threading, schema); dùng chung skin social generic.
- **Áp editorial typography Ở ĐÂY trước** (trang "article" của cộng đồng, nhiều reading real-estate nhất): serif pull-quote cho post gốc, display `--font-editorial` cho post "featured".
- Badge "✓ Câu trả lời hay" → nền leaf-green wash nổi bật.
- Related-posts grid → thẻ ảnh lớn hơn (hiện thumbnail 100px).

#### `cong-dong.vue` — Feed cộng đồng — **6.5/10**
Interaction-rich (like-pop, glass filter bar) nhưng **skin "Threads clone"**, hero emoji 💬.
- **Masthead serif + strip ảnh** (banner mỏng ảnh post gần đây) thay emoji-icon hero — mở trang bằng register editorial.
- Card "Cách tham gia"/"Quy tắc" → sediment tick + hairline như section-head area/ward.
- Avatar → **ring accent 3 tỉnh** theo vùng/level thay circle-initial phẳng.
- **Banner "cộng đồng mới bắt đầu"** (reframe ít bài = "thành viên sáng lập" thay "feed hỏng").

#### `bang-xep-hang.vue` — Xếp hạng — **6/10**
Sạch; gold/silver/bronze **vay mượn** (không phải chữ ký vinhlong360); avatar 100% initials.
- **Podium #1** thật (avatar lớn, crown micro-icon, accent amber) — hiện number-tint mờ.
- **Avatar ảnh** (dùng `AvatarPlaceholder` — trang này về "gặp gỡ top contributor" mà toàn circle).
- Entrance stagger cho list (đang tĩnh).
- Masthead editorial "Thành viên tích cực" + sediment tick — khoảnh khắc "hall of fame".

#### `thong-bao.vue` — Thông báo — **4.5/10**
Plainest; **chỉ emoji làm identity**; **0 avatar actor** (không thấy AI liked/commented) — lạnh, bất thường cho tính năng social.
- **Avatar actor mỗi dòng** (`AvatarPlaceholder`) — fix giá trị cao nhất; trang đang 0 khuôn mặt người.
- **Group theo recency** ("Hôm nay/7 ngày/Cũ hơn") thay list phẳng.
- Icon-badge màu theo loại (đỏ=like, xanh=comment) thay emoji-as-UI.
- "Đọc tất cả" có micro-animation (chấm mờ dần theo chuỗi).

#### `da-luu.vue` — Đã lưu — **5.5/10**
IA/product thông minh (workspace framing, JourneyActionRail, degraded-sync states) nhưng **motion phẳng nhất**.
- **Thẻ entity image-forward** (hiện thumbnail 80×56 cạnh text) — là place-card, xứng ảnh lớn overlay text.
- Hover-lift + entrance stagger (pattern `.saved-grid > *` đã có ở `nguoi-dung` — gần như copy-paste).
- Overview stat strip → CountUp treatment 3 tỉnh như `cong-dong`.

#### `cai-dat.vue` — Cài đặt — **5/10**
Sâu nhất về a11y/chức năng (2FA/trusted-device/consent/export); nhưng **0 CE, hardcode value, 9 tab phẳng** → như admin tool.
- **K4** token-parity (fix hardcode → token scale).
- **Nhóm 9 tab thành 2-3 cụm** (Hồ sơ/Giao diện | Bảo mật/Riêng tư/Chặn | Dữ liệu/Nguy hiểm) + crossfade/slide khi chuyển tab.
- Security tab → **scorecard thật** (progress ring/segment) thay dòng "Đã có mật khẩu".
- `--font-editorial` cho H1/overview strip (nhẹ, không đụng form).

#### `tai-khoan.vue` — Dashboard tài khoản — **5/10**
Giàu data nhất, **phẳng nhất**, "reward surface" mà **không celebrate gì**.
- **Animate `cp-score` ring** (SVG conic/stroke-dashoffset 0→score% + accent 3 tỉnh + spring pop khi vượt ngưỡng level) — fix premium giá trị nhất (là tâm điểm thị giác).
- `useReveal()` + stagger cho 7 section (hiện load 1 block tĩnh).
- **K4** fix token-drift (`#c0392b`→`--error`, `.85rem`→`--text-sm`).
- Activity feed: item slide/fade in + icon nền màu 3 tỉnh.

#### `gioi-thieu.vue` — Giới thiệu — **5.5/10**
Trust-heavy tốt nhưng **không phải "brand moment"** (như policy doc icon thân thiện).
- **Cover essay full-bleed**: ảnh AI-gen Mekong + masthead serif overlay + eyebrow ("Vĩnh Long, Bến Tre, Trà Vinh — 2026").
- Số section 01/02/03 → màu 3 tỉnh; mission/non-commercial dùng nền accent-tint (không chỉ left-border).
- **Pull-quote serif lớn** (founder note "vì sao có trang này") phá tường body text.
- Strip timeline sáp-nhập 3 tỉnh (minh hoạ nhẹ).

#### `lien-he.vue` — Liên hệ — **7/10**
Interaction layer tốt nhất batch tĩnh; chỉ visual identity giữ lại.
- **Strip ảnh/motif Mekong** trên card grid + subhead serif ("Con người thật, trả lời thật — không chatbot").
- **Màu-code 5 card theo chức năng** (claim=amber, privacy=river, report=clay) thay card trắng đồng loạt.
- Line-art icon phù-sa thay emoji-in-circle.
- Live-status "Thường phản hồi trong X giờ" (SLA thật).

#### `huong-dan.vue` — Hướng dẫn — **6.5/10**
IA/content tốt nhất site (docs-grade) nhưng **under-designed** so với 84KB nội dung.
- **Recolor 6 topic section** theo màu 3 tỉnh/category (search=river, itinerary=clay, community=leaf) — TOC scan bằng màu.
- **Animate `<details>` open/close** (max-height/opacity) thay snap native — fix tương tác chủ đạo.
- Callout tip/warn/dyk → sediment tick + hairline như editorial thay pastel box.
- Intro serif 1 câu "welcome" trước quickstart.

#### `huong-dan-thanh-vien.vue` — Hướng dẫn thành viên — **6/10**
Transparency công thức điểm xuất sắc; presentation generic + **rời khỏi tiến trình thực của user**.
- **Personalize**: nếu logged-in, show cấp/điểm/badge THẬT + progress bar tới cấp sau (đang bảng trừu tượng).
- Retint 4 level card → token 3 tỉnh+amber (đang hex ad-hoc green/blue/orange/gold).
- Count-up number cho bảng điểm + worked example khi scroll.
- Badge earned → micro foil/shine (là "huy hiệu").

#### `chinh-sach-bao-mat.vue` + `dieu-khoan-su-dung.vue` — Pháp lý — **5.5/10**
Cùng template `.legal-page`; restraint đúng thể loại nhưng "generic legal boilerplate" là trần.
- **Sticky mini-TOC** (jump-link section) — usability gap thật cho doc dài.
- Badge số → tint river (privacy) / clay (terms) — wayfinding khi nhảy giữa 2 trang.
- **TL;DR strip/section** ("Tóm tắt: chúng tôi không bán dữ liệu") kiểu Apple/Basecamp.
- **Terms:** surface disclaimer "chỉ giới thiệu — không đặt hàng/booking" thành **highlight callout** (dùng `.highlight-badge` của About) — câu quan trọng nhất chiến lược, đang chôn trong prose.
- Print/PDF + version-diff.

#### `[...slug].vue` — 404 — **5/10**
"Recovery moment" mà **ít vinhlong360 nhất site**.
- **Illustration on-brand** (motif "xuồng lạc/rẽ nhầm" reuse `.catalog-hero::before` wave/palm/lotus) thay emoji-on-white.
- **3-4 quick-link** điểm-đến/category dưới search (reuse `.quick-pick`) — recovery thật.
- `--font-editorial` cho "404" + eyebrow dateline.
- Fuzzy-match: "Có phải bạn muốn tìm: [gần nhất]?" ngay trên 404 (dùng unaccented-search đã có).

---

## 3. Gộp / dọn trùng lặp (làm cùng Wave 1)

1. **`su-kien` + `le-hoi` → gộp** (cùng `/api/events`, 90% trùng). 1 trang + segmented tab, hoặc tối thiểu tách component chung + dừng trùng essay.
2. **`san-pham` / `ocop` → giữ 2 (SEO/trust) nhưng dedupe essay OCOP** + tách motif dùng-chung.
3. **`du-lich` = umbrella** → tuyên bố quan hệ hub-spoke rõ (nav strip), tránh 6 trang là siblings mờ quan hệ.
4. **`ocop.vue` vs `san-pham.vue?ocop=1`** — cân nhắc `ocop` là landing chuyên biệt, `san-pham` là superset.

---

## 4. Lộ trình theo đợt

| Đợt | Nội dung | Nâng bao nhiêu trang | Rủi ro |
|---|---|---|---|
| **W0 — Foundation** | K1 EntityCard CE · K2 detail cover · K3 season-ring extract · K4 token-parity · K5 `<CatalogPage>`+composable · K6 nguyên tắc | ~all (K1 chạm ~15 lưới) | Trung bình (component chung → test kỹ) |
| **W1 — Tier-2 catalog + gộp** | Masthead/eyebrow/tick cho mọi catalog-hero · gộp su-kien/le-hoi · dedupe san-pham/ocop · motif riêng · sort/toggle parity · filter-rail | 14 trang | Trung bình |
| **W2 — Tier-3 social/account** | nguoi-dung cover CE · cong-dong masthead · bai-viet editorial · thong-bao actor avatar · bang-xep-hang podium · da-luu image-forward · tai-khoan score-ring · cai-dat token+cụm-tab | 8 trang | Thấp-TB |
| **W3 — Static/brand moments** | gioi-thieu cover essay · lien-he strip · huong-dan color+details-anim · huong-dan-tv personalize · legal TOC+callout · 404 brand | 8 trang | Thấp |
| **W4 — Cinematic depth tier-1/tools** | detail sidebar CE + full-bleed break · itinerary route-hero + sticky map · planner drag-drop · ban-do popup+panel · lich-trinh-chia-se nâng cấp | 8 trang | Cao (tương tác) |
| **W-img (song song)** | Đợt ảnh AI-gen ~30/lần cho điểm-đến/OCOP ưu tiên | trần thị giác toàn site | Thấp (đã có pipeline) |

**Thứ tự đề xuất:** W0 → W-img(đợt1) → W1 → W2 → W3 → W4, xen kẽ W-img. W0 trước vì đòn bẩy lan toả; W4 sau cùng (rủi ro tương tác cao).

---

## 5. Cách thực thi (per wave/page)

1. **frontend-design** làm lăng kính: mỗi trang/đợt — token plan (màu/type/layout/signature) trong đầu, review chống-generic, rồi code.
2. **Scoped, không rò:** mỗi trang/nhóm có class scope (`.ce-*`) như CE2/CE3; component chung (EntityCard/CatalogPage) test toàn site.
3. **Verify preview-probe** (screenshot hỏng phiên này → dùng DOM probe + `preview_inspect`). **Nhớ clear service-worker** sau rebuild (đã dính bug cache phiên này).
4. **§B1 backup** trước mọi thao tác data; ảnh AI-gen chỉ cx/gpt-5.5-image; CTA contact-only; deploy §4 owner-gated.
5. **1 đợt = 1 nhóm commit + 1 build + 1 deploy + verify live**, giữ site luôn chạy (§B5).

---

## 6. Nguyên tắc thẩm mỹ chung (áp mọi trang)

- **Cinematic:** hero là "luận đề" — mở bằng thứ đặc trưng nhất (ảnh thật/masthead serif/motif), không phải hộp emoji.
- **Premium qua restraint:** một signature nổi bật/trang (§Chanel "bỏ bớt 1 món"), quanh nó giữ kỷ luật; cắt trang trí không phục vụ.
- **Giác quan có chủ đích:** motion phục vụ nội dung (reveal, parallax, micro-interaction), tôn trọng reduced-motion; **tránh over-animation = tell AI-slop**.
- **Giọng biên tập:** eyebrow dateline + serif + màu 3 tỉnh + dấu phù-sa = "một giọng" xuyên suốt; **không emoji-as-UI**.
- **Nội dung là chất liệu:** copy chủ động, cụ thể hơn "clever"; empty/error/cold-start là khoảnh khắc dẫn dắt, không phải fallback trơ.
- **Ảnh là trần:** nơi chưa có ảnh thật, placeholder SVG có chủ đích (gradient + motif + grain), không hộp xám.
