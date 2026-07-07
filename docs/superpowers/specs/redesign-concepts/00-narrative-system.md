# 00 — Hệ thống Tường thuật & Cảm quan hợp nhất

> **STATUS (2026-07-07): active — đã truth-sync.** Creative-direction (luận đề, giọng, thiết bị tò mò) còn hiệu lực làm hướng tư duy; các mệnh đề "giữ/kept" về cấu trúc trang bị OVERRIDE bởi declutter — xem khối cảnh báo grounding ngay dưới.

> ⚠️ **CẢNH BÁO GROUNDING (2026-07-07) — đọc trước khi thực thi bất kỳ concept nào (00–16).**
> Toàn bộ concept trong thư mục này là tài liệu **Ý TƯỞNG**, viết 2026-07-05 — TRƯỚC 3 đợt declutter đã được chủ dự án duyệt và ship (đợt 1: `docs/superpowers/plans/2026-07-06-declutter-dot1-trim.md`; đợt 2: `.../2026-07-07-declutter-dot2-shared.md`; đợt 3 ship 2026-07-07: `.../2026-07-07-declutter-dot3-structural.md`). **Khi xung đột, declutter THẮNG concept.** Các khối concept ghi "giữ/kept" nhưng THỰC TẾ ĐÃ GỠ khỏi code:
>
> - **Home (`index.vue`):** section "Trợ lý AI" CTA cuối trang (B1-1, trùng ChatWidget FAB — bỏ từ đợt 1, commit `691e694`); event-hero lớn (B1-2); EntityFeature #2 OCOP (B1-5); strip "Lịch trình gợi ý" (B1-4); dàn chip leaderboard → 1 link teaser (B1-6) — xem các comment `declutter-3 T16` trong `web-nuxt/pages/index.vue`.
> - **san-pham/ocop:** `CatalogSpotlight` đã bỏ ở CẢ HAI trang (T10/T9 — `san-pham.vue:33`, `ocop.vue:38`); region quick-picks đã bỏ ở ocop (đợt 2 A5 — `ocop.vue:95`).
> - **kham-pha/[interest]:** int-intro đã xoá, 2 hàng filter rời → 1 panel hợp nhất (T12/B9).
>
> Hệ quả cho §6 Wave Sequencing bên dưới: Sóng 2 mục 6 ("Home spine" theo 01-home) và các spine trang khác mô tả cấu trúc TIỀN-declutter — mọi sóng thực thi sau này phải **re-ground trên code hiện tại** (đọc `index.vue`/`san-pham.vue`/`ocop.vue` + comment declutter) trước khi làm, và KHÔNG khôi phục khối đã cắt có chủ đích.

*Creative-direction layer trên 16 concept trang lẻ (01–16). Đây là "hiến pháp kể chuyện" — nơi mọi trang lấy chung một luận đề, một giọng, một bộ thiết bị tò mò, một ngôn ngữ điện ảnh, để cả site đọc như MỘT ấn phẩm chứ không phải 52 template rời.*

---

## 0. LUẬN ĐỀ TRUNG TÂM (enforce ở mọi nơi)

> **Mỗi địa điểm, món ăn, sản phẩm, điểm đến, chỗ ở, lễ hội, làng nghề, cù lao — là một CÂU CHUYỆN**, kể sao cho người đọc *tò mò muốn đi Vĩnh Long NGAY BÂY GIỜ.*

Ba hệ quả bắt buộc từ luận đề này:

1. **Không có "listing", chỉ có "story-hook".** Mọi đơn vị lặp lại (card, row, tile) phải mở bằng một lý-do-để-tò-mò, không phải một nhãn phân loại. Giá là chú thích cuối; provenance/mùa/khoảnh-khắc là tít.
2. **Không có "trang tĩnh", chỉ có "ấn phẩm đang sống".** Mọi trang phải mang một tín hiệu *bây giờ* (mùa này, âm lịch hôm nay, còn N ngày, vừa có bài mới, đang chính vụ) — cảm giác trang được "phát hành hôm nay".
3. **Ẩn dụ nền tảng = phù sa.** Hành trình khám phá bồi đắp dần như phù sa. Ngôn ngữ thị giác cốt lõi (sediment-tick, phù-sa hero, sediment thread, river→amber→clay) là hiện thân của ẩn dụ này — KHÔNG phải trang trí ngẫu nhiên.

Khung ngôn từ chung cho mọi trang (đã hội tụ tự nhiên qua 16 concept): **"sổ tay / cuốn sổ / niên giám / sổ vàng"** — trang chủ = *sổ tay hành trình*; danh bạ = *niên giám bến đò*; OCOP = *sổ vàng*; cộng đồng = *sổ tay truyền miệng của cả vùng*; tài khoản = *sổ tay hành trình cá nhân (hộ chiếu)*. Giữ nguyên họ ẩn dụ này khi viết mọi masthead mới.

Bốn bất biến kế thừa từ CLAUDE.md §1 mà creative KHÔNG được phá:
- **Contact-only** (Zalo/điện thoại/hỏi-giá) — không cart, không booking, không form chốt đơn. Mọi CTA "story continues" phải đổ về khám phá/liên hệ/lưu, không đổ về giao dịch.
- **Chỉ ảnh AI-gen sạch bản quyền** (cx/gpt-5.5-image) — không stock, không Wikimedia, không re-host báo. 96% entity KHÔNG có ảnh thật → *phù-sa hero placeholder* là giải pháp mặc định, không phải fallback thất bại.
- **CSS thuần + tokens** (KHÔNG Tailwind); mọi màu qua token; mọi chuyển động thuần CSS/composable sẵn có (`useReveal`, `useParallax`).
- **Dark-mode parity + reduced-motion off** cho mọi visual mới, không ngoại lệ.

---

## 1. STORY TEMPLATES THEO LOẠI ENTITY

Mỗi loại có một **khung tường thuật cố định 3 nhịp: HOOK MỞ → THÂN (chuỗi beat) → LỜI MỜI**. Khung này *tái sắp xếp attribute đã có trong DB* thành một chuỗi kể chuyện — **không cần field backend mới cho v1**. Chuỗi fallback cho câu hook khi thiếu field chuyên biệt (dùng thống nhất mọi trang):

> `attributes.hook` → `attributes.highlight` → `famous_for` / `signature_dish` → câu đầu tiên của `description`.

Nhịp LỜI MỜI luôn kết bằng một trong: (a) tín hiệu *bây giờ* (mùa/âm lịch/đếm ngược), (b) một nút liên hệ contact-only, hoặc (c) một "story continues" link sang entity/khu-vực kế cận — không bao giờ kết bằng nút chatbot chung chung vô danh.

### Bảng khung tường thuật

| Loại | HOOK MỞ (1 câu vì-sao) | THÂN — chuỗi beat (theo thứ tự kể) | LỜI MỜI (kết + tín hiệu *bây giờ*) |
|---|---|---|---|
| **Điểm đến / Attraction / Experience** | Khoảnh khắc điện ảnh nhất (bình minh trên sông, mùa nước nổi, đờn ca tài tử đêm) | ai kể tại chỗ (người địa phương) → làm gì ở đó theo giờ trong ngày → cảm giác giác quan (gió, nắng ngả, tiếng ghe) | "đi lúc này vì…" (mùa/best_time) → nearby entities → save/liên hệ |
| **Món ăn / Dish** | Nghi thức ăn nó: khi nào, ăn với ai, ăn kèm gì | ai nấu ngon nhất gần đây → mùa đỉnh → người-mới phải gọi món gì → tín hiệu giác quan (mùi mắm, độ giòn/béo) | "đang rộ mùa — còn ~N tuần" → quán gần → Zalo hỏi |
| **Sản phẩm · OCOP** | *Ai làm ra nó? Ở đâu?* (provenance-first, TRƯỚC giá) | hộ dân/HTX đằng sau → quy trình (thủ công vs máy) → khác gì cùng loại nơi khác → cách xác minh đúng hàng OCOP có sao | "★N — đã qua N vòng kiểm định" → xem sổ vàng / liên hệ hộ làm |
| **Chỗ ở / Lodging** | Buổi sáng bạn sẽ thức dậy trong đó (view + tiếng chim, KHÔNG floor-plan) | thức dậy thấy gì/nghe gì sáng đầu tiên → nhịp một ngày ở đây → ai đón bạn | "thức dậy giữa vườn" → giá (surfaced) → Zalo hỏi phòng |
| **Lễ hội / Festival** | Cộng đồng đằng sau (đình / chùa Khmer / HTX) | nghi thức cụ thể (rước, thả đèn, đua ghe ngo) → vì sao *năm nay / ngày này* quan trọng → 3 dân tộc Kinh–Khmer–Hoa giữ lịch riêng | âm-lịch-first + "còn N ngày" → thêm vào lịch (.ics) |
| **Làng nghề / Craft village** | Sợi chỉ mấy đời làm nghề | tiếng/mùi của làng lúc đang làm → giờ nào trong ngày xem nghề diễn ra (không chỉ giờ mở cửa shop) → sản vật ra đời thế nào | "sáng ra bến sông nghe tiếng khung dệt" → sản phẩm của làng → liên hệ |
| **Cù lao / Thiên nhiên** | Miếng đất giữa dòng — sông bồi nên nó | hình dáng đất (outline riêng) → hệ sinh thái/miệt vườn → cách tới (bến đò gần nhất) | mùa trái/mùa nước → "đi tiếp" cù lao/xã kế → save |
| **Xã/Phường (portrait)** | Tên cũ trước sáp nhập 2025 (dấu ấn đời sống thật) | outline địa giới tự-vẽ riêng từng xã → thuộc về khu vực nào (AREA_META blurb) → mùa thật từ entity trong xã | "Trong vùng" — dải xã lân cận (biến 124 trang cô lập thành mạng đi bộ được) |
| **Tổ chức / Place (directory)** | Lift tường thuật thấp nhất — giữ gần factual | thông tin liên hệ + vai trò | vẫn nhận masthead + sediment-tick để đồng bộ ấn phẩm |

**Nguyên tắc chọn beat:** mỗi section nên *kết thúc bằng một câu gợi câu hỏi kế tiếp* (mùa → "đỉnh mùa chính xác khi nào?" → month-strip) hoặc một related-entity link — để tò mò tích lũy dồn (compounding curiosity), không phẳng.

---

## 2. KEYSTONE — "STORY CARD" (redesign EntityCard)

> **Đây là thay đổi đòn bẩy cao nhất toàn site.** EntityCard lặp trên ~15 lưới (index, dia-diem, kham-pha, du-lich, san-pham, ocop, su-kien, tim-kiem, saved, nearby…). Sửa 1 component = nâng cấp cảm giác của MỌI lưới cùng lúc. Nó phải đọc như một **mẩu tít story-hook**, không phải một ô e-commerce (ảnh · pill · tên · giá).

### Giải phẫu card mới (từ trên xuống)

1. **Cover — phù-sa placeholder (mặc định cho ~97% card không ảnh):**
   - Gradient hash-seeded theo `entity.id` (id → luôn một look) + glyph category lệch tâm (bleed off mép, không icon-giữa-ô).
   - **Overlay grain SVG ~4% opacity** trên gradient → biến "flat gradient" thành "minh hoạ có chủ đích" (anti-AI-slop tell #1: flat gradient = rẻ; grain = cố ý).
   - Có ảnh thật → dùng ảnh, giữ Ken-Burns nhẹ khi ở hero; ở card giữ tĩnh + crossfade 150ms khi đổi ảnh carousel (không jump-cut).
2. **Dateline eyebrow** (thay cover-tag pill đặc): small-caps wide-tracked, **hairline top border màu accent category** (KHÔNG nền đặc) → đọc như nhãn bảo tàng/spec-tag, không như app badge. Nội dung: `{LOẠI} · {KHU VỰC}` (+ `· ĐANG RỘ MÙA` khi peak).
3. **Tên = serif** (`--font-editorial`, weight 600, `--text-base/lg`). *Chỉ một dòng CSS đổi cho EntityCard nhưng nâng cảm giác premium mọi card toàn site.*
4. **Rule tri-tỉnh** — hairline river→amber→clay mảnh (phiên bản card của sediment-tick) ngăn tên và teaser, như tick section-head thu nhỏ.
5. **Story teaser 1 dòng** — câu hook rút từ chuỗi fallback §1 (KHÔNG phải summary cắt cụt). Với product: **maker/place TRƯỚC giá** ("— Cô Ba, Vườn bưởi Bình Minh"), fallback về place, ẩn hẳn nếu không có (additive, không schema mới). Provenance là tít, giá là footnote.
6. **Curiosity affordance (đúng 1, không nhồi):** một trong —
   - badge mùa "Đang mùa" foil-gradient (peak = premium moment),
   - "còn N ngày" cho event,
   - "vừa thêm" pulse-ring **một nhịp trên mount** (không loop),
   - glow nhẹ cho rating 5.0 (phân biệt điểm tuyệt đối với 4.2).
7. **Save/Share** ghost pill, im lặng — không cạnh tranh với hook.

### Kỷ luật keystone
- OCOP star = *hạng chất lượng nhà nước*, **không** trộn glyph với review-rating stars — hai ngôn ngữ khác nhau, giữ tách bạch.
- Không bao giờ hiện "0 đánh giá / 0đ" trần trụi — ẩn cả cụm nếu rỗng.
- Mọi thiết bị trên: có `.dark` variant (grain giảm opacity, shadow mềm), tắt sạch dưới reduced-motion.
- Ship như một thay đổi *riêng, test-visual-diff* qua index/dia-diem/san-pham/ocop/du-lich trước khi merge (rủi ro cao vì reuse rộng).

---

## 3. THƯ VIỆN THIẾT BỊ TÒ MÒ & KHÁM PHÁ (site-wide)

Bộ pattern dùng chung khiến người ta *muốn click/cuộn/lật tiếp*. Mỗi cái map tới ẩn dụ phù sa và tái dùng được nhiều trang.

| Thiết bị | Làm gì | Áp ở đâu (ví dụ) | Chi phí |
|---|---|---|---|
| **Sediment Thread** (signature toàn trang) | hairline dọc river→amber→clay chạy dọc content column, animate theo scroll-progress — nối các block rời thành *một dòng chảy* | index (keystone), mọi trang biên tập dài | `SedimentThread.vue` + `useScrollProgress`; RM→vệt tĩnh |
| **Sediment-tick section-head** | tick dọc river→amber→clay trước mọi `<h2>` — mọi section "cùng một ấn phẩm" | MỌI trang (promote vào partial dùng chung) | CSS-only, đã có |
| **Phù-sa hero placeholder** | biến 96% "không ảnh" thành masthead hash-unique có grain + sediment wash + microcopy thật thà | detail, ward, social cover, itinerary cover | `EntityHeroPlaceholder.vue` |
| **Living calendar / month-strip** | peak-month glow + ring "bạn đang ở đây" (tháng thực) — trả lời *"nên đi bây giờ không?"* không cần đọc | detail, theo-mua, san-pham | CSS + `new Date()`, RM→pause glow |
| **Season-ring instrument** | vòng mùa *là* month-picker, scrub → hero đổi tông + đổi câu verdict | theo-mua (keystone) → extract `SeasonRing.vue` cho detail | composable sẵn |
| **Lunar ribbon** | dải trăng âm-lịch-first, ghim lễ hội theo vị trí trăng — chứng minh "lịch chạy bằng trăng" | su-kien/le-hoi | CSS/SVG crescent |
| **"Đang diễn ra" / đếm ngược sống** | banner thay stat-chip khi có event ≤3 ngày; live-dot pulse khi `days_until===0` | index hero, events | dữ liệu `days_until` sẵn |
| **Story teaser trên "Xem thêm"** | thay đếm trần bằng teaser món kế tiếp thật ("còn 41 nơi, kể cả làng gốm Mang Thít →") | mọi load-more/empty-state | dữ liệu client sẵn |
| **Province stamp** | 3 thẻ tem bưu-chính (mép răng cưa, tên serif, blurb AREA_META làm caption) thay quick-pick phẳng | dia-diem (keystone) → footer/map/home | CSS clip-path, blurb đã viết |
| **Peek / hover reveal** | hover lộ gloss thơ ("từ chợ nổi đến chùa cổ"), sao "nở" nhẹ, filmstrip underline draw | dia-diem stats, top-dishes | CSS, no layout shift |
| **Proximity / "Trong vùng"** | dải entity/xã lân cận biến trang cô lập thành mạng đi-bộ-được | ward, detail nearby, area region-hop | data nearby sẵn |
| **Grid divider biên tập** | mỗi 8–10 card chèn một interruption typographic (place-name serif / fact) phá lưới vô tận | mọi lưới dài | CSS `grid-column:1/-1` |
| **Rotating hero ticker** | placeholder/subhead xoay câu-hỏi-đang-được-hỏi thật ("bún nước lèo", "bưởi Năm Roi") | search (keystone), home hero | mảng câu hỏi thật |
| **Zero-result recovery** | 2–3 near-match card ("Có phải bạn muốn tìm…") trước khi về CTA chung | search, mọi empty grid | reuse EntityCard |

**Quy tắc vàng:** tối đa **một phần tử "sống" (breathing/animate lặp) trong viewport tại một thời điểm**. Nếu month-strip đang glow thì why-now chip đứng yên; hai nhịp thở khác nhau để không đua nhau. Nhồi nhiều thiết bị tò mò cùng lúc = AI-slop.

---

## 4. NGÔN NGỮ ĐIỆN ẢNH & CẢM QUAN MỞ RỘNG

### 4.1 Ngân sách chuyển động (motion budget — kỷ luật cứng)
- **Reveal:** `useReveal()` (opacity + 4px rise, ~400ms) là mặc định site-wide. Pull-quote chậm hơn (~600ms) để "thành một nhịp". Stagger cho phép **≤40ms/item**, tối đa một hàng.
- **Parallax:** `useParallax()` chỉ trên hero/EntityFeature/StorySpread. **KHÔNG** parallax lớp thứ 3 trên cùng khối; **KHÔNG** parallax trên lưới dày (motion-sick).
- **Ken Burns:** chỉ hero có ảnh thật, `--dur-kenburns: 20s`, scale 1.0→1.06, subtle.
- **Ambient "sống":** đúng một per viewport (§3 quy tắc vàng). Pulse-ring "vừa thêm" = **một nhịp trên mount**, không loop. Wax-seal/stamp = một lần settle 400ms, không loop.
- **CẤM:** auto-play video, particle/confetti, cursor-follow, looping shimmer/glow-mãi-mãi, stagger-animate-mọi-card.

### 4.2 Gợi giác quan sông nước Vĩnh Long qua thiết kế (không dùng media thật)
Site không có audio; gợi giác quan bằng **motif + màu + chữ**, không bằng GIF/SFX:
- **Sông nước:** sediment wash (river→amber→clay blur ngang), ripple `box-shadow` như giọt nước trên card (transition, không transform khi RM), hairline "dòng chảy" dọc.
- **Phù sa / đất:** grain SVG overlay (giấy in), palette clay/leaf/river/amber trên nền sand — không bao giờ nền trắng thuần.
- **Mùa/thời gian:** đồng hồ trong-ngày (sương sáng / nắng đứng bóng / nắng ngả vàng / đèn ghe), âm-lịch-first cho lễ hội, month-strip sống.
- **Kết cấu văn hoá cụ thể:** woven `cần xé`/`thúng` basket (chợ phiên, san-pham), guilloché (sổ vàng OCOP), carved temple-stone numerals (date badge lễ hội), ghe/xuồng + cầu khỉ + lá dừa line-motif (thay clip-art nón-lá/cầu-tre chung chung).

### 4.3 Dark-mode & reduced-motion (bắt buộc mọi visual mới)
- **Dark:** mọi màu qua token có `.dark` override sẵn (`--river-600`/`--amber-500`/`--clay-600`…). Grain giảm opacity; shadow mềm; tick màu chuyển sang biến dark. **Không** hex off-brand hardcode (`#c0392b`, `#dc2626`, `#f5f5f5` → resolve về token).
- **Reduced-motion:** Ken Burns/parallax/glow-pulse/tick-grow/thread-animate/stamp **tắt sạch** → thay bằng trạng thái tĩnh tương đương (thread thành vệt tĩnh, glow thành ring tĩnh) — không mất thông tin, chỉ mất chuyển động.

### 4.4 Anti-AI-slop guardrails (checklist trước khi ship)
- ❌ Flat gradient trần → ✅ luôn có grain/texture overlay.
- ❌ Bố cục đối xứng-hoàn-hảo, icon-giữa-ô → ✅ motif lệch tâm, bleed mép, editorial asymmetry.
- ❌ Emoji trần cạnh chữ serif → ✅ emoji-trong-chip-thiết-kế hoặc glyph SVG line-icon (`generateCategoryIcon`).
- ❌ Border box đặc + shadow nặng → ✅ hairline + shadow nhẹ (ngôn ngữ EntityFeature).
- ❌ Superlative rỗng ("thiên đường", "tuyệt vời nhất", "hidden gem", "must-see") → ✅ danh từ cụ thể + địa danh thật.
- ❌ Mọi thứ breathing-mãi-mãi → ✅ một ambient/viewport, phần lớn "settle rồi đứng yên".
- ❌ Clip-art du lịch chung (beach/palm/passport-stamp) → ✅ motif Delta thật (ghe, cầu khỉ, lá dừa, mái chùa Khmer).

---

## 5. HƯỚNG DẪN GIỌNG VĂN (Copy Voice)

**Giọng:** thân tình như người địa phương khoe quê mình — cụ thể, có nhịp câu ngắn-dài xen kẽ kiểu tản văn Nam Bộ. Tự tin đến từ *chi tiết*, không từ tính từ. Sensory trước superlative. Second-person tuỳ chọn, không hô khẩu hiệu.

**NÊN:**
- Dẫn bằng người / nơi / mùa cụ thể (Cầu Kè, Cổ Chiên, Mang Thít, bến đò, cù lao, đờn ca tài tử).
- Câu ngắn được phép đứng một mình để tạo nhịp.
- Số liệu như một lời khoe khiêm tốn ("không sót nơi nào"), tabular-nums, im lặng — không như KPI dashboard.
- Thành thật về giới hạn ("chưa có ảnh thật cho nơi này") → đáng tin hơn là giả vờ.
- Âm-lịch-first cho lễ hội; phân biệt Kinh/Khmer/Hoa rõ khi liên quan.

**KHÔNG:**
- Superlative rỗng: "thiên đường miền Tây", "tuyệt vời nhất", "không thể bỏ lỡ", "hidden gem", "must-see", "off the beaten path".
- Ngôn ngữ giao dịch: "mua ngay", "đặt hàng", "giao hàng tận nơi", "thêm vào giỏ" (site contact-only).
- Nhãn chức năng khô ("Khám phá theo chủ đề", "Bài viết mới") thay cho lời mời có ngữ cảnh.
- Hiện số 0 trần; tô vẽ/đánh bóng nội dung UGC của người thật.

**6 dòng mẫu (model the voice):**
1. *Hook món ăn:* "Nước lèo phải nấu từ mắm bò hóc để dậy mùi — không phải tô bún nào cũng làm được vậy."
2. *Subhead danh bạ:* "1.532 điểm đến được ban biên tập tổng hợp, từ cù lao giữa sông đến quầy hàng trong hẻm nhỏ — Vĩnh Long, Bến Tre, Trà Vinh, không sót nơi nào." *(CẤM chữ "đã xác minh" — verifiedAt ~0, CLAUDE.md §1.7)*
3. *Why-now chip (mùa):* "🌾 Đang rộ mùa — chôm chôm ngọt nhất tháng này, còn khoảng 3 tuần."
4. *Load-more teaser:* "Xem thêm — 41 nơi nữa, kể cả làng nghề gốm Mang Thít →"
5. *Masthead cộng đồng (động):* "Hôm nay, ai đó vừa kể chuyện về một buổi sáng ở chợ nổi Trà Ôn." *(Cái Bè NGOÀI tỉnh — Đồng Tháp; chợ nổi của tỉnh là Trà Ôn)*
6. *Microcopy thật thà no-photo:* "Ảnh minh hoạ theo tông màu đặc trưng — vinhlong360 chưa có ảnh thật cho nơi này."

---

## 6. ƯU TIÊN LIÊN TRANG & TRÌNH TỰ SÓNG (Wave Sequencing)

Xếp theo đòn bẩy (reuse × tần suất hiển thị) giảm dần. Ship theo sóng: mỗi sóng để lại hệ thống chạy được (CLAUDE.md §B5), commit nhỏ.

### 🌊 Sóng 1 — Keystone tái dùng rộng nhất (nâng cả site cùng lúc)
1. **EntityCard → Story Card (§2).** Đòn bẩy #1 tuyệt đối: ~15 lưới nâng cấp bằng một component. Serif title + dateline eyebrow + tri-province rule + story teaser + provenance-first + grain placeholder. Ship riêng, test-visual-diff.
2. **Promote sediment-tick section-head + phù-sa hero placeholder vào partial dùng chung** (`EntityHeroPlaceholder.vue`, `.section-head-sediment`). Gỡ nợ CSS trùng lặp trên 4+ trang; mở khoá "CE không dừng ở hero".
3. **Chuẩn hoá dateline-eyebrow + chuỗi hook-fallback (§1)** thành pattern/composable dùng chung — mọi trang gọi cùng logic, không tái phát minh.

### 🌊 Sóng 2 — Flagship & browse (nơi lưu lượng dồn)
4. **Detail page `dia-diem/[id]` (§1 spine + phù-sa hero + living calendar).** Trang đòn bẩy cao nhất theo lượt xem; mọi entity đổ về đây.
5. **Discovery (dia-diem/index + kham-pha): province stamp + refine-bar hợp nhất + grid divider.** Gỡ filter trùng ba lớp; biến database-screen thành shelf-of-stories.
6. **Home spine (§index): Sediment Thread + nhịp 3-tầng A/B/C + StorySpread #2 + PullQuote.** Biến trang chủ thành một dòng kể liên tục.

### 🌊 Sóng 3 — Type-specific narrative & tiện ích
7. **Products/OCOP split (market vs sổ vàng), Events merge (lunar-first), Community masthead + serif-read-mode, Season-ring instrument** — mỗi trang lấy narrative-skin riêng nhưng dùng chung keystone của Sóng 1–2.

**Nguyên tắc thứ tự:** Sóng 1 trước — vì mọi trang ở Sóng 2–3 *tiêu thụ* keystone của Sóng 1 (Story Card, sediment-tick partial, hook-fallback). Làm ngược lại sẽ phải sửa hai lần.

---

*Mọi concept trang lẻ (01–16) từ nay đọc như hiện thực-hoá cục bộ của hệ thống này. Xung đột giữa concept trang và file này → file này thắng.*
