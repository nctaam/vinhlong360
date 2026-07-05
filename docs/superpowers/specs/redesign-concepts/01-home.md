# index.vue (Trang chủ) — "Sổ tay một chuyến đi chưa bắt đầu"

> Grade hiện tại: 8.5/10. Chẩn đoán: premium ở phần trên (hero, EntityFeature, StorySpread đã cinematic-editorial), nhưng từ giữa trang trở xuống rơi về "lưới catalog phẳng" — `cat-grid`, `dx-item` decision list, `scroll-row` các card giống hệt nhau lặp lại 6 lần liên tiếp không có nhịp điệu biên tập. Trang chủ hiện đọc như MỘT trang landing được lắp từ 12 block độc lập, không như MỘT câu chuyện có mở-thân-kết. Mục tiêu của bản concept này: biến index.vue thành **một đường kể chuyện liên tục từ hero tới footer**, nơi mỗi block là một "trang" trong cuốn sổ tay hành trình, không phải một "widget" trên dashboard.

---

## 1. STORY ANGLE

Trang chủ không phải là "danh mục các mục trên site" — nó là **lời mời của một buổi sáng ở Vĩnh Long mới**, kể theo đúng nhịp một ngày và một hành trình thật:

- **Bình minh** — bạn vừa mở mạng, chưa biết đi đâu (Hero: câu hỏi mở, không phải danh sách).
- **Quyết định đầu tiên** — "hôm nay có gì đang diễn ra" (sự kiện/mùa — thời gian tính bằng ngày/giờ, tạo cảm giác *bây giờ*, *ở đây*).
- **Bước chân đầu tiên xuống vườn** — trải nghiệm miệt vườn (EntityFeature #1) — cảm giác, không phải thông tin.
- **Điểm dừng ăn trưa** — quán ngon + đặc sản nổi bật (Nổi bật + Top dishes) — vị giác.
- **Khoảnh khắc sông nước** — StorySpread full-bleed — đây là "trang ảnh đôi" của cuốn sổ, không cần chữ nhiều.
- **Món quà mang về** — OCOP (EntityFeature #2) — cảm giác chạm tay vào sản vật.
- **Lên kế hoạch cho ngày mai** — lịch trình gợi ý — biến cảm xúc thành hành động cụ thể.
- **Nghe người đi trước kể** — cộng đồng — bằng chứng xã hội bằng giọng người thật.
- **Tối muộn, vẫn còn tò mò** — "Dành cho bạn" + hỏi trợ lý AI — cánh cửa mở tiếp, không phải điểm kết thúc cứng.

Framing then: đây không phải "trang chủ của một website thư mục", đây là **"một cuốn sổ tay hành trình đang được lật từng trang"** — ẩn dụ trực quan cho cấu trúc lại toàn trang (xem §3 & §10).

Nguyên tắc viết lại mọi microcopy: đổi từ **nhãn chức năng** ("Khám phá theo chủ đề", "Bài viết cộng đồng mới") sang **giọng mời gọi có ngữ cảnh thời gian/mùa/con người** ("Sáng nay ở Vĩnh Long", "Người vừa đi tuần trước kể lại").

---

## 2. CINEMATIC HERO / THESIS

Hero hiện tại đã tốt (Ken Burns, kicker mùa vụ, search, hero-feature card) — **giữ nguyên khung**, nhưng nâng 3 điểm:

1. **Tagline theo đồng hồ thực, không chỉ theo mùa.** `seasonalTagline` hiện chỉ đổi theo tháng. Thêm một lớp micro-thời-gian phía trên H1 — một dòng "sợi chỉ thời gian" nhỏ, ví dụ:
   - Sáng (5h–10h): "Sương còn trên mặt sông Cổ Chiên."
   - Trưa (10h–14h): "Nắng đứng bóng, ghe đã đầy chợ."
   - Chiều (14h–18h): "Nắng ngả vàng trên những vườn bưởi."
   - Tối (18h–5h): "Đèn ghe thương hồ đã lên."

   Đây KHÔNG phải nội dung SEO-critical (giữ `seasonalTagline` làm H1 chính, SSR-safe theo tháng) — dòng thời-gian-trong-ngày là một `<ClientOnly>` micro-string phía trên kicker, thuần trang trí/cảm xúc, không ảnh hưởng SSR/hydration vì tách khỏi luồng nội dung chính.

2. **"Cửa sổ đang mở" thay vì card tĩnh.** `hero-feature` hiện là 1 card cố định bên phải. Đổi thành khái niệm **"Ai đó đang ở đó" (Right now)** — vẫn cùng data (`heroFeature`), nhưng thêm một dòng ngữ cảnh sống động dựa trên field đã có (`days_until`, giờ mở cửa nếu có trong `attributes.hours`) — ví dụ thay vì luôn "Gợi ý nổi bật", khi có event gần: "Còn 3 ngày nữa". Card giữ nguyên cấu trúc DOM — chỉ đổi copy động, không thêm gọi API mới.

3. **Con trỏ cuộn có ý thức (scroll cue).** Thêm 1 chevron nhỏ cuối hero, animate nhẹ (translateY 2 nhịp, respect `prefers-reduced-motion`), label ẩn "Cuộn để xem hôm nay có gì" — thiết bị rẻ tiền nhưng hiệu quả cao để báo "trang còn nữa, còn chuyện để kể", đặc biệt quan trọng vì bên dưới hero sắp có nhịp biên tập mới lạ hơn thói quen người dùng.

---

## 3. LAYOUT + RHYTHM — "Sổ tay hành trình" (spine cấu trúc mới)

Vấn đề cốt lõi hiện nay: mọi section sau hero dùng chung một khuôn `section-head` (kicker nhỏ + H2 + "Xem tất cả →") + `scroll-row` ngang. Lặp lại 5-6 lần, mắt không phân biệt được "quan trọng" với "phụ". Cần **3 tầng nhịp editorial rõ rệt**, xen kẽ có chủ đích (không phải ngẫu nhiên):

| Tầng | Vai trò | Bố cục | Ví dụ áp dụng |
|---|---|---|---|
| **A — Full-bleed / cinematic** | "lật sang trang ảnh đôi" — nghỉ mắt, cảm xúc thuần | Ảnh tràn viewport, chữ nổi trên scrim | Hero, StorySpread (đã có) — **thêm 1 spread thứ 2** trước block cộng đồng |
| **B — Editorial 2-cột (photo+copy)** | "đọc một câu chuyện nhỏ" | EntityFeature-style, ảnh lớn 1 bên | Trải nghiệm miệt vườn, OCOP (đã có) — **áp dụng thêm cho Nổi bật (spotlight)** hiện đang là biến thể riêng (`.tinh-hoa`) |
| **C — Chuỗi ngang có nhịp số** | "lướt nhanh nhiều lựa chọn" | `scroll-row`, nhưng **luôn đặt ngay sau một khối A hoặc B**, không bao giờ 2 khối C liên tiếp | Sự kiện mini, quán ngon, lịch trình, cộng đồng |

**Quy tắc chống đơn điệu:** không cho phép 2 section liên tiếp cùng tầng. Thứ tự mới đề xuất:

```
Hero (A)
  ↓ scroll cue
Bắt đầu hành trình — decision index (redesign thành "3 câu hỏi", xem dưới) (B-lite)
  ↓
Đang diễn ra — sự kiện/mùa (C, nhưng dẫn bằng 1 khối tin tức lớn "hôm nay" không phải card nhỏ)
  ↓
[FULL-BLEED SPREAD #1 tuỳ chọn / hoặc đi thẳng]
Trải nghiệm miệt vườn (B) — EntityFeature #1
  ↓
Nổi bật + Quán ngon (B, chuyển .tinh-hoa sang khung EntityFeature-family để nhất quán — xem §11)
  ↓
[FULL-BLEED SPREAD — "Nơi vườn chạm sông"] (A) — đã có, giữ vị trí giữa trang, đúng vai trò "nghỉ mắt"
  ↓
Đặc sản OCOP (B) — EntityFeature #2
  ↓
Lịch trình gợi ý (C, nhưng mở đầu bằng 1 "Itinerary Feature" lớn — xem §11 Timeline Ribbon)
  ↓
[FULL-BLEED SPREAD #2 MỚI — "Tiếng gọi chợ nổi" hoặc "Đêm đờn ca"] (A) — ĐIỂM MỚI, xem §10 Signature Moment
  ↓
Từ cộng đồng (C, giọng người thật — ảnh tròn lớn hơn, trích dẫn kiểu editorial pull-quote)
  ↓
Dành cho bạn (C-nhẹ, cá nhân hoá)
  ↓
Hỏi trợ lý AI (kết — "cánh cửa mở tiếp")
```

Điểm mấu chốt: **thêm 1 full-bleed spread thứ hai** ở khoảng 65-70% chiều dài trang (trước cộng đồng) để phá vỡ chuỗi 4 block "C" liên tiếp (Nổi bật → Lịch trình → Cộng đồng → Dành cho bạn) hiện đang là đoạn "flat" nhất của trang — đúng vấn đề "flat lower third" mà brief nêu.

**Responsive posture:** tầng B (EntityFeature 2-cột) đã stack tốt trên mobile. Tầng A (spread) đã full-bleed đúng. Tầng C cần thêm **snap-scroll** (`scroll-snap-type: x mandatory` trên `.scroll-row`, `scroll-snap-align: start` trên card) — hiện chưa có, khiến vuốt ngang trên mobile bị "trôi tự do" thiếu cảm giác kiểm soát; snap tạo cảm giác "lật từng thẻ" chủ đích.

---

## 4. TYPOGRAPHY

Giữ nguyên cặp đã chốt: **Fraunces (`--font-editorial`)** cho mọi masthead/lede, **Inter (`--font-sans`)** cho UI/nhãn/eyebrow. Bổ sung cho trang chủ:

- **Cỡ chữ leo thang có chủ đích theo tầng.** Hero H1 lớn nhất trang (đã đúng). Nhưng hiện `dx-title` (decision index), `cat-tile` label, section H2 gần như cùng 1 cỡ thị giác — làm phẳng phân cấp. Đề xuất thang rõ:
  - Section H2 (đầu mỗi block chính): `clamp(1.75rem, 1.4rem+2.4vw, 2.75rem)` — như EntityFeature đã dùng — áp dụng ĐỒNG NHẤT cho mọi `<h2>` trang chủ (hiện `.h2-tight` ở Lịch trình/Dành cho bạn nhỏ hơn không lý do rõ — nên tăng lên cùng thang, chỉ giảm `margin`).
  - Decision index title (`dx-title`): giảm xuống 1 bậc dưới H2, dùng `--font-sans` weight 700 (đây là UI-điều-hướng, không phải "voice" biên tập — tách bạch rõ 2 giọng).
- **Pull-quote editorial cho mục Cộng đồng.** Thêm 1 trích dẫn lớn (Fraunces italic, 1.5rem+, dấu ngoặc kép kiểu in ấn " " lớn làm ornament ở góc) lấy từ nội dung bài viết nổi bật nhất trong `communityPosts` — biến bài đăng đầu tiên từ "1 card trong hàng ngang" thành "lời chứng thực nổi bật", giọng người thật thay vì giọng UI.
- **Số đếm ngược sự kiện = chữ hiển thị (display number).** `eh-day`/`eh-month` hiện đã lớn — giữ, nhưng đưa vào `--font-editorial` tabular-nums thay vì sans, để đồng bộ giọng "biên tập" toàn trang thay vì giọng "app lịch".

---

## 5. SENSORY + MOTION + CURIOSITY

Trang đã có: Ken Burns hero, parallax ảnh (EntityFeature, StorySpread), scroll-reveal, hover scale ảnh. Bổ sung có kiểm soát (KHÔNG thêm animation library, thuần CSS/composable sẵn có `useReveal`, `useParallax`):

1. **"Sợi chỉ phù sa" chạy dọc trang (signature thread).** Thay vì mỗi section tự đứng độc lập, thêm 1 **hairline dọc mảnh** (2px, gradient river→amber→clay lặp lại theo chu kỳ — cùng ngôn ngữ "phù-sa/sediment tick" đã có trên section heads) chạy DỌC THEO RÌA TRÁI của toàn bộ content column, từ ngay dưới hero tới trước block cộng đồng, **animate chiều dài theo scroll progress** (dùng `scroll-timeline`/`animation-timeline: view()` nếu hỗ trợ, fallback JS translateY tối giản qua IntersectionObserver đã có trong `useReveal`). Ẩn dụ: "dòng phù sa bồi dần" = hành trình đọc của bạn đang trôi qua. Đây chính là "discovery device" xuyên suốt biến 8 block rời rạc thành 1 dòng chảy liền mạch — **đây là ứng viên mạnh cho Signature Moment (§10)**.
2. **Đếm ngược sự kiện "sống".** `eh-countdown` với `ec-live-dot` đã có — mở rộng: nếu `days_until === 0`, thêm hiệu ứng pulse rất nhẹ trên chấm đỏ (đã có animation heart-pop pattern trong EntityCard — tái dùng cùng easing `--ease-spring-gentle`).
3. **Vi tương tác "chạm để nghe mùi vị" (hover reveal) trên top-dishes.** Khi hover `dish-item`, ngoài rating hiện có, số sao "nở" nhẹ (scale 1.15, 150ms) — nhỏ, rẻ, tăng cảm giác "món này ngon thật".
4. **Category tiles (`cat-grid`) — thêm độ trễ so le (staggered reveal).** Hiện 6 tile xuất hiện cùng lúc khi reveal. Stagger 40ms mỗi tile (CSS `animation-delay` biến số qua `nth-child`) — cảm giác "được bày ra" thay vì "bật đồng loạt", chi phí bằng 0.
5. **Giới hạn:** KHÔNG thêm parallax lớp thứ 3 trên cùng 1 khối, KHÔNG thêm particle/confetti, KHÔNG thêm auto-playing video — mọi thứ phải tắt sạch dưới `prefers-reduced-motion: reduce` (đã là pattern chuẩn trong `EntityFeature.vue`/`StorySpread.vue` — theo đúng khuôn đó).

---

## 6. UX FLOW

Information scent hiện tại khá tốt về mặt data (decision cards đã cá nhân hoá theo mùa/sự kiện) nhưng **thứ tự ưu tiên hành động chưa rõ**. Đề xuất luồng quyết định 3 bước, làm rõ ràng bằng nhãn:

1. **"Đi đâu?"** → category grid + decision index (giữ, nhưng gộp copy: decision index đổi tiêu đề từ "Hôm nay bạn muốn bắt đầu thế nào?" — hỏi hay nhưng hơi rộng — sang cụ thể hơn: **"3 câu hỏi, 3 câu trả lời nhanh"** framing rõ đây là shortcut không phải feed).
2. **"Ăn gì, xem gì?"** → sự kiện + trải nghiệm + ẩm thực + OCOP (thân bài, đã đúng thứ tự).
3. **"Đi khi nào, đi sao?"** → lịch trình → CTA "Tạo lịch trình riêng" (đã có, giữ, nhưng tăng độ nổi bật — hiện `.block-cta` là một nút outline nhỏ cuối block, nên nâng thành 1 dải ngang có nền `--bg-warm` riêng biệt, đặt xuyên suốt hết width, không chỉ dính cuối block).

**Giảm ma sát tới "khám phá / liên hệ / lưu":**
- Mọi entity card/feature đã có `SaveButton` — giữ. Đề xuất thêm: **hero-feature card** hiện thiếu nút lưu nhanh (`SaveButton`) — bổ sung (component đã tồn tại, chỉ cần chèn, không cần code mới).
- CTA cuối trang ("Hỏi ngay" chatbot) nên xuất hiện dạng "câu hỏi mở" thay vì nút đóng khung cứng — đổi copy nút từ "💬 Hỏi ngay" sang phản chiếu đúng câu hỏi mở đầu trang: **"Vẫn chưa biết đi đâu? Hỏi liền"** — tạo vòng lặp khép kín với hero (mở bằng câu hỏi, kết bằng lời mời trả lời câu hỏi đó).

---

## 7. PREMIUM CUES

- **Số liệu định lượng đặt đúng chỗ, không phô.** `community-stats-line` hiện đặt kiểu liệt kê 3 số cạnh nhau — đổi thành 1 dòng caption nhỏ dưới kicker, `font-variant-numeric: tabular-nums`, cùng nhịp với cách các tạp chí du lịch cao cấp chú thích ảnh (nhỏ, im lặng, đáng tin — không đóng khung to như "dashboard KPI").
- **Viền hairline nhất quán, không viền box đầy.** `dx-item`, `cat-tile` hiện dùng nền + shadow nhẹ khi hover — giữ, nhưng bỏ hẳn mọi `border` cứng còn sót (kiểm tra `.cat-tile`/`.dx-item` không có border-radius lệch tông) để mọi khối đều dùng "hairline + shadow" ngôn ngữ đã thiết lập ở EntityFeature.
- **Ảnh luôn có story caption ẩn, không chỉ alt rỗng.** Với ảnh AI-gen category-level dùng làm backdrop (spotlight, hero-feature), thêm 1 dòng caption nhỏ góc dưới ảnh khi có `region`/`area` (đã có `hf-region`, `spot-region` — style lại thành typographic caption kiểu "ảnh tạp chí" — chữ nhỏ, all-caps, tracking rộng, nằm đè mép dưới ảnh trong 1 dải scrim mảnh, không phải badge tròn nổi).
- **Không số 0 hiển thị trần trụi.** Nếu `communityStats.reviews === 0` hay tương tự → ẩn cả cụm thay vì hiện "0 đánh giá" (rà lại điều kiện `v-if` hiện tại đã khá tốt — giữ nguyên pattern, áp dụng nhất quán cho mọi số liệu mới thêm).

---

## 8. CULTURAL AUTHENTICITY

Bổ sung các "hạt cụ thể" (specificity hooks) mà bản hiện tại còn thiếu hoặc chỉ có ở copy tĩnh (`FEATURE_EXPERIENCE`, `STORIES`) chứ chưa lan ra motif thị giác:

- **"Sợi chỉ phù sa" (§5.1)** là hiện thân trực quan của chính ẩn dụ văn hoá cốt lõi — phù sa bồi đắp = default hành trình khám phá tích luỹ dần. Đây không phải trang trí ngẫu nhiên mà là ẩn dụ được thiết kế có chủ đích.
- **Đếm ngày sự kiện nên gắn âm lịch khi có** — `eh-lunar` đã tồn tại (🌙 lunar_date) — nâng cấp: khi lễ hội là Khmer (Ok Om Bok, Sene Dolta) hoặc gắn chùa Khmer, thêm 1 icon/motif khác biệt (không dùng 🎭 chung chung cho tất — phân biệt lễ hội Kinh/Khmer bằng 1 dấu hiệu nhỏ, ví dụ hoa văn góc thẻ sự kiện đổi theo `attributes.category`).
- **Full-bleed spread thứ 2 (điểm mới)** nên chọn 1 trong 2 chủ đề còn thiếu ở trang chủ hiện tại dù đã có trong nội dung site: **chợ nổi** (đã nhắc trong hero-sub "chợ nổi" nhưng chưa có hình ảnh riêng) hoặc **đờn ca tài tử ban đêm trên sông** — cả hai đều rất "miền Tây" và chưa được dùng ở đâu trên trang chủ hiện tại (StorySpread hiện tại "Nơi vườn chạm sông" đã dùng ảnh sông ban ngày).
- **Tránh cliché:** không dùng icon nón lá / cầu tre chung chung làm motif lặp lại (đã tránh — hero dùng ảnh thật/illustration theo category, giữ vậy). Không đặt caption kiểu "thiên đường miền Tây", "xứ sở diệu kỳ" — giữ giọng cụ thể, địa danh thật (Cầu Kè, Cổ Chiên, Mang Thít...) như copy hiện tại đã làm tốt (`FEATURE_OCOP.lede` là ví dụ chuẩn, giữ làm khuôn mẫu cho mọi lede mới).

---

## 9. COPY VOICE

Giọng: **thân tình, cụ thể, có nhịp câu ngắn-dài xen kẽ kiểu tản văn Nam Bộ**, không sến, không hô khẩu hiệu, không dùng superlative rỗng ("tuyệt vời nhất", "không thể bỏ lỡ"). Ví dụ áp dụng cho các điểm mới đề xuất:

- **Scroll cue cuối hero:** "Cuộn xuống — hôm nay ở Vĩnh Long còn nhiều chuyện hay."
- **Decision index kicker mới:** "3 câu hỏi, 3 câu trả lời nhanh" / dòng dẫn: "Bạn hỏi, tụi mình chỉ đường — dựa vào mùa này, sự kiện này, và những gì mọi người đang ghé."
- **Full-bleed spread mới (chợ nổi), nếu chọn hướng này:**
  - Kicker: "Trước khi trời sáng hẳn"
  - Title: "Chợ *nổi*, đời cũng nổi trôi mà vui"
  - Sub: "5 giờ sáng, ghe hàng đã neo san sát trên sông Cái Bè. Một tiếng rao, một nải chuối treo sào — đủ để biết bán gì."
- **Pull-quote cộng đồng (mẫu khung, sẽ thay bằng nội dung thật của bài đăng nổi bật):**
  - Format: dấu ngoặc kép lớn kiểu in ấn + trích 1 câu ngắn từ `p.content` + attribution "— {display_name}, vừa ghé {entity_name}".
- **CTA chatbot đổi lại (khép vòng với hero):** "Vẫn chưa biết đi đâu? Hỏi liền — tụi mình gợi ý theo đúng lúc bạn đang ở."

---

## 10. SIGNATURE MOMENT

**"Sợi chỉ phù sa" (Sediment Thread)** — một vệt gradient mảnh (river → amber → clay, lặp lại) chạy dọc suốt chiều dài trang, "chảy" theo tiến độ cuộn của người xem, nối liền mọi section từ hero tới cộng đồng thành MỘT dòng duy nhất thay vì 9 khối rời rạc. Đây là điều người dùng sẽ nhớ và là bằng chứng thị giác rõ nhất cho luận đề "trang chủ = một hành trình, không phải một danh mục". Nó cũng là phần mở rộng tự nhiên, rẻ tiền (thuần CSS + 1 progress hook) của "phù-sa/sediment tick" đã tồn tại trên section heads — nâng cấp 1 chi tiết trang trí nhỏ đã có thành motif cấu trúc toàn trang.

Ứng viên phụ (nếu muốn 1 signature moment "nội dung" thay vì "chuyển động"): **full-bleed spread chợ nổi 5 giờ sáng** — vì chưa từng xuất hiện ở đâu trên site, rất đặc trưng Mekong Delta, và tạo một "khoảnh khắc tĩnh lặng, cảm xúc" giữa nhịp catalog dày ở nửa dưới trang.

Khuyến nghị: làm **cả hai** — Sediment Thread là bộ khung chuyển động xuyên suốt (structural), spread chợ nổi là "đỉnh cảm xúc nội dung" đặt tại đúng điểm gãy nhịp (giữa Lịch trình và Cộng đồng).

---

## 11. COMPONENTS + FEASIBILITY

Tất cả đề xuất dùng token sẵn có (`--font-editorial`, `--space-*`, palette clay/leaf/river/amber trên sand), composable sẵn có (`useReveal`, `useParallax`), component sẵn có (`EntityFeature`, `StorySpread`, `EntityCard`, `SaveButton`). Không thêm thư viện animation, không thêm gọi API mới (mọi copy động dùng field đã có trong `/api/homepage` response).

**Mới, cần build:**
1. `SedimentThread.vue` (mới, reusable) — hairline dọc cố định bám theo cột content, chiều cao animate theo `scrollY / documentHeight` qua 1 composable nhỏ `useScrollProgress()`. CSS-only fallback (progress bằng scroll-linked `@supports (animation-timeline: view())`), JS fallback qua rAF cho trình duyệt cũ. Ẩn khi `prefers-reduced-motion: reduce` → thay bằng vệt tĩnh không animate (chỉ giữ vai trò trang trí, không mất thông tin).
   - **Tái dùng được:** có thể lắp cho mọi trang biên tập dài (kham-pha, du-lich) sau này — component độc lập, không phụ thuộc index.vue.
2. `EditorialSpread` biến thể thứ 2 của `StorySpread.vue` cho chợ nổi — thực chất chỉ là thêm 1 lần gọi `<StorySpread>` mới với ảnh/copy mới (`/img/spread/cho-noi.webp`, cần gen AI mới qua `scripts/gen_image.py`) — **0 code mới**, chỉ cần asset + copy.
3. `PullQuote.vue` (mới, nhỏ, reusable) — trích dẫn lớn Fraunces italic + ornament ngoặc kép SVG + attribution line. Dùng cho block Cộng đồng, tái dùng được cho trang `cong-dong.vue`, trang chi tiết review sau này.
4. Đưa `.tinh-hoa`/`.spotlight` (spotlight block hiện tại là CSS riêng trong index.vue) vào khuôn `EntityFeature` family — **giảm nợ CSS**: hiện `spotlight`/`spot-visual`/`spot-body` là 1 bộ style riêng gần như trùng lặp logic với `EntityFeature`. Refactor thành `<EntityFeature>` biến thể "compact + list phụ bên phải" (thêm slot `#aside` cho danh sách quán ngon) — vừa nhất quán thị giác vừa giảm CSS trùng lặp.

**CSS/motion cụ thể:**
- `.scroll-row { scroll-snap-type: x mandatory; }` + `.card, .event-mini, .cm-card { scroll-snap-align: start; }` — thêm vào mọi `scroll-row` hiện có.
- `.cat-tile { animation-delay: calc(var(--i) * 40ms); }` với `--i` set qua inline style `:style="{ '--i': idx }"` trong `v-for`.
- H2 chuẩn hoá 1 class dùng chung `.h2-editorial` áp `clamp(1.75rem, 1.4rem + 2.4vw, 2.75rem)` cho mọi `<h2>` trang chủ, xoá `.h2-tight` biến thể nhỏ hơn không lý do.
- `dish-item:hover .dish-score { transform: scale(1.15); transition: transform 150ms var(--ease-spring-gentle); }`.

**Dark-mode parity:** mọi màu mới (sediment gradient, pull-quote ornament) định nghĩa qua token hiện có (`--river-600`, `--amber-500`, `--clay-600` đã có biến thể `.dark` tương ứng trong `EntityFeature.vue` — theo đúng pattern `.dark .ef-ac-*` đã thiết lập).

**Reduced-motion:** Sediment Thread đổi từ animate sang static gradient; category tile stagger tắt (`animation: none`); dish-score hover scale tắt — theo đúng khối `@media (prefers-reduced-motion: reduce)` đã là chuẩn mực trong `EntityFeature.vue`/`StorySpread.vue`.

**Không đổi (giữ nguyên vì đã đúng):** Hero Ken Burns + grain, SearchAutocomplete, JourneyActionRail (ClientOnly), EmptyState/Skeleton fallback logic, toàn bộ SEO/schema.org block, decision-card personalization logic (`homeDecisionCards`, `homeJourneyActions`).
