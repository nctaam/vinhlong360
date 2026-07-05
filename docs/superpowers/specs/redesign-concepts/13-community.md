# Community feed + post — `cong-dong.vue` (6.5) + `bai-viet/[id].vue` (7.0)

> Đơn vị: **Cộng đồng** — bảng tin xã hội (Threads-clone hiện tại) + trang bài viết đơn (không gian đọc tốt nhất trong toàn site cho editorial type).
> Bối cảnh: UGC còn non (ít bài, ít ảnh thật), nhưng đây là nơi NGƯỜI THẬT nói bằng giọng THẬT về miền Tây — thứ mà nội dung biên tập không thể giả được. Đây phải là nơi cảm thấy sống động và đáng tin nhất site, không phải bản sao Threads.

---

## 1. STORY ANGLE

`cong-dong.vue` hiện đang kể sai câu chuyện: nó nói "đây là một mạng xã hội" (feed, like, bookmark, follow) — nhưng thực ra nó nên nói **"đây là cuốn sổ tay truyền miệng của cả vùng"**: những gì người thật vừa ăn, vừa đi, vừa hỏi, vừa khen hôm nay ở Vĩnh Long – Bến Tre – Trà Vinh. Câu chuyện không phải "mạng xã hội có bao nhiêu bài" mà là **"vùng đất này đang được kể lại, ngay lúc này, bởi chính người đang sống trong nó."**

Với `bai-viet/[id].vue`: một bài đánh giá quán bún nước lèo không phải "1 review 3 sao" — nó là một lát cắt trải nghiệm có tên, có thời điểm, có địa danh, có thể nối tiếp thành đối thoại (bình luận) và thành khám phá (bài liên quan, địa điểm được nhắc tới). Trang bài viết phải đọc như một **tản văn ngắn có bình luận**, không phải một "post detail view".

Nguyên tắc kể chuyện xuyên suốt: **Chuyện thật > chuyện hay**. Không tô vẽ bài viết của user (không thêm ảnh AI-gen giả làm nền cho content của họ, không đánh bóng giọng văn) — nhưng khung chứa (frame) xung quanh phải được nâng tầm lên mức editorial, giống cách một tờ báo in làm đẹp phần "Ý kiến bạn đọc" mà không sửa lời bạn đọc.

## 2. CINEMATIC HERO / THESIS

**Bỏ hoàn toàn `catalog-hero` hiện tại** (emoji-icon-trong-vòng-tròn + card thống kê rời rạc — đây chính là kiểu "tầng catalog" mà audit đã chỉ ra).

Thay bằng một **"Sổ tay hôm nay" (Today's Almanac) masthead** — cinematic nhưng KHÔNG dùng ảnh hero lớn (vì UGC không có ảnh hero đại diện đáng tin cậy):

- Editorial dateline eyebrow chuẩn CE: hairline + wide-tracked caps — `CỘNG ĐỒNG · SỔ TAY MIỀN TÂY HÔM NAY` — với ngày thực (`{{ new Date().toLocaleDateString('vi-VN', {weekday:'long', day:'numeric', month:'long'}) }}`), tạo cảm giác ấn phẩm ra hằng ngày, không phải trang tĩnh.
- H1 bằng `--font-editorial` (Fraunces), cỡ `--text-3xl`, không phải "Cộng đồng" khô khan mà một dòng sống động, đổi theo dữ liệu thật (ví dụ nếu hôm nay có bài mới về món ăn: *"Hôm nay, ai đó vừa kể về một bữa cơm ở Cù Lao Dài."* — fallback tĩnh khi không có tín hiệu: *"Chuyện kể mỗi ngày của người miền sông nước."*)
- Ba con số thống kê (bài viết / đánh giá / thành viên) KHÔNG còn là card rời rạc kiểu dashboard — trình bày như một **dòng "phát hành" của tờ báo**: `1.204 CHUYỆN ĐÃ KỂ  ·  312 ĐÁNH GIÁ THẬT  ·  890 NGƯỜI MIỀN TÂY` — serif numerals, hairline phân cách dấu `·`, không box/pill/card.
- Signature phù-sa tick (river→amber→clay 3-hairline, dùng đúng CSS pattern đã có ở `index.vue` `.block + .block::before`) đặt NGAY DƯỚI masthead, đánh dấu ranh giới "phần biên tập" (masthead) và "phần cộng đồng sống" (feed) bên dưới — ẩn dụ: phù sa là nơi báo chí biên tập và tiếng nói người dân giao thoa.
- KHÔNG Ken Burns/parallax ở đây (không có ảnh hero để làm) — chuyển động duy nhất: con số thống kê vẫn dùng `CountUp` (giữ), nhưng thêm micro-signal "có bài mới" bằng một dot nhỏ hoạt hình nhẹ (không phải banner) cạnh dateline khi feed có bài trong 10 phút gần nhất.

## 3. LAYOUT + RHYTHM

**cong-dong.vue:**
- Giữ layout 2 cột (feed + sidebar) — đây là mẫu hình đúng cho social feed, không cần phá.
- Nhưng chuyển compose box, filter tabs, feed thành các "khối có nhịp" thay vì xếp chồng phẳng: thêm khoảng thở `--space-6` giữa compose/search/tabs và feed thay vì tất cả dính liền.
- Sidebar: nâng cấp mỗi `sidebar-card` từ card trắng phẳng thành card có **kicker chữ nhỏ serif-italic** phía trên h2 (giống cách CE dùng dateline cho section) — vd phía trên "Thành viên tích cực" thêm kicker `Bảng xếp hạng` bằng `--font-editorial italic`, `--text-2xs`, tracked caps màu `--muted`.
- Responsive: mobile giữ single-column, nhưng "mobile-discovery" strip (trending tags + top members) chuyển từ scroll ngang thô sang một dải có label kicker đồng bộ.

**bai-viet/[id].vue:**
- Đây là trang có "reading real-estate" tốt nhất — tận dụng triệt để. Mở rộng max-width đọc content chính lên `72ch` (thay vì bó trong `680px` container cứng của PostCard) khi hiển thị nội dung dài, tương tự cách trang báo web hiện đại cho phần thân bài rộng hơn khung UI xung quanh.
- Thêm **"article rail"** nhẹ bên phải (chỉ desktop ≥1200px, ẩn hẳn dưới đó — không rebuild layout) hiển thị: tên địa điểm được nhắc (nếu có `entity_id`), 2-3 bài liên quan dạng text-only (không thumbnail card), và nút "Xem trên bản đồ" nếu có toạ độ. Đây là nơi biến 1 bài UGC thành 1 điểm nút trong mạng lưới khám phá — tăng "khát vọng khám phá tiếp theo".
- Comment thread giữ nguyên cấu trúc threading (đã tốt) nhưng đổi rhythm: thêm khoảng cách lớn hơn (`--space-8` thay vì `--space-6`) trước khi vào phần bình luận, với một dòng chuyển tiếp mảnh: hairline + label serif-italic nhỏ `"Người ta nói gì"` thay cho icon-label thô hiện tại.
- Related posts grid ở cuối: đổi từ 2-cột card-ảnh nhỏ sang dải ngang kiểu "đọc tiếp" biên tập (giống "More from this section" của báo), có kicker `TIẾP TỤC ĐỌC`.

## 4. TYPOGRAPHY

- Masthead H1: `--font-editorial`, `--text-3xl`, `--weight-semibold` (không bold nặng — editorial thường medium/semibold cho display, không black).
- Dateline eyebrow + kicker sidebar: `--font-sans`, `--text-2xs`, `letter-spacing: .12em`, `text-transform: uppercase`, màu `--muted`.
- **Nội dung bài viết trên `bai-viet/[id].vue` (nơi khác biệt lớn nhất với feed card)**: đổi `.thread-content` trên trang detail sang `--font-editorial` cho phần thân — đây LÀ signature move của trang, biến một dòng status thành một đoạn văn được đọc như tản văn. Cỡ `--text-base` → tăng nhẹ lên giữa `--text-base` và `--text-lg` (`clamp(1.0625rem, 1rem + .3vw, 1.1875rem)`), `line-height: 1.7`.
- Feed card (PostCard trong list) GIỮ NGUYÊN `--font-sans` — vì feed cần quét nhanh (scannability), chỉ trang detail mới "chậm lại" bằng serif. Đây là phân tầng có chủ đích: lướt = sans, đọc sâu = serif.
- Tên tác giả (`thread-author`): giữ sans nhưng tăng `--weight-semibold` → dùng màu `--ink` đậm hơn `--ink-secondary` hiện tại một chút để tác giả nổi bật như "byline".
- Số liệu (bài viết/đánh giá/thành viên trong masthead): serif oldstyle numerals nếu font hỗ trợ (Fraunces có), tạo cảm giác ấn bản in.

## 5. SENSORY + MOTION + CURIOSITY

- **Discovery device #1 — "Vệt phù sa mới"**: một chỉ báo cực nhẹ (không banner, không badge to) ở đầu feed: hairline ngang mảnh có gradient river→amber chạy nhẹ (giữ nguyên phong cách phù-sa) xuất hiện phía trên bài mới nhất khi có bài đăng trong phiên hiện tại — click để "cuộn lên xem". Tạo cảm giác "đang sống" mà không ồn ào.
- **Discovery device #2 — "Nhắc tới gần đây"**: trong sidebar, thay "Hashtag thịnh hành" tĩnh bằng góc nhìn địa danh — hiển thị 3-4 địa điểm được nhắc tới nhiều nhất trong bài đăng 7 ngày qua (dùng data `entity_id`/mentions đã có), dẫn thẳng ra trang địa điểm. Đây là cầu nối UGC → catalog, tăng giá trị SEO nội bộ và cảm giác "cộng đồng đang thực sự bàn về nơi có thật".
- Scroll-reveal: áp `useReveal()` (đã có) đồng bộ cho sidebar cards với stagger nhẹ 60ms/card — hiện tại chỉ 1 sidebar-card có class `reveal`, cần áp đều.
- Micro-interaction giữ nguyên (like-pop, hover border trên related-card) — đủ tốt, KHÔNG thêm animation mới ở feed card (tránh over-animation/AI-slop — feed card phải giữ tốc độ, cảm giác "nhanh, gọn, thật" của Threads-style, không biến thành cinematic nặng nề).
- Vị giác/giác quan miền Tây: khi post có `post_type === 'review'` và rating, hiển thị rating bằng 5 chấm nhỏ dạng "hạt lúa" thay vì sao Unicode thô — một chi tiết nhỏ CSS-only (5 hình elip nghiêng nhẹ, fill theo rating) gợi hình ảnh miệt vườn mà vẫn đọc được như rating chuẩn (giữ `role="img" aria-label`).
- Reduced-motion: tất cả transition/animation trên (dot pulse, stagger reveal) phải có `@media (prefers-reduced-motion: reduce)` tắt hẳn animation, giữ trạng thái cuối.

## 6. UX FLOW

- Luồng chính không đổi (đúng là feed cần giữ tốc độ thao tác: đăng, thích, bình luận, lưu) — nhưng **entry point cảm xúc** đổi: thay vì mở trang thấy ngay "hero card + compose box" khô, giờ mở trang thấy "masthead sống động hôm nay" trước, rồi mới đến compose — điều hướng mắt: đọc trước, viết sau (giống cách người ta đọc báo trước khi viết thư độc giả).
- Giảm ma sát "khám phá tiếp theo": mọi `entity_name` trong PostCard đã là link — giữ, nhưng thêm **preview-on-hover nhẹ** (desktop only, CSS `:hover` + tooltip nhỏ hiện category-icon + 1 dòng mô tả ngắn nếu có sẵn trong props, không gọi thêm API) để giảm rủi ro "click ra khỏi feed rồi không quay lại".
- `bai-viet/[id].vue`: luồng đọc → bình luận → khám phá tiếp. "Article rail" bên phải + "TIẾP TỤC ĐỌC" ở cuối là 2 cửa thoát có chủ đích để giữ session (thay vì hết bài là hết trang).
- CTA liên hệ: khi bài viết có `entity_id` với `contact_zalo`/`contact_phone` (dữ liệu entity), thêm 1 dòng nhỏ cuối bài (trước phần bình luận) dạng text-link tinh tế: `"Muốn hỏi thêm về {{entity_name}}? Liên hệ qua Zalo"` — reuse pattern CTA contact-only đã có ở trang entity, KHÔNG tạo CTA mới, chỉ surface lại đúng nơi.

## 7. PREMIUM CUES

- Hairline dividers thay border rõ nét ở mọi nơi có thể (`.5px solid var(--line)` — đã dùng, giữ và mở rộng ra sidebar cards, hiện sidebar-card đang dùng border khác cần đồng bộ).
- Serif italic kicker nhỏ phía trên mỗi sidebar block — chi tiết rẻ tiền để làm nhưng tạo cảm giác "được biên tập", không phải component tự sinh.
- Đồng nhất khoảng trắng: mọi khối cách nhau đúng bội số `--space-*`, không có margin tuỳ tiện (hiện tại nhiều `margin-bottom` rời rạc trong file).
- Loading state: `SkeletonGrid`/`SkeletonList` đã dùng đúng — giữ, đây là premium cue tốt (không giật layout).
- Empty state hiện đã có icon + message + hint tốt — nâng cấp thêm 1 chi tiết: icon emoji đổi thành SVG line-icon nhất quán bộ icon đang dùng trong PostCard (hiện emoji 💬/🔖/👥 lẫn với SVG stroke icon khác — thiếu nhất quán, đây là 1 "AI-slop tell" nhỏ cần dọn: chọn MỘT hệ — khuyến nghị SVG line-icon để khớp phong cách premium editorial, bỏ emoji-as-icon).
- Số liệu dùng oldstyle serif numerals trong masthead — chi tiết typographic nhỏ nhưng rất "premium print".

## 8. CULTURAL AUTHENTICITY

- Ngôn ngữ dateline/masthead dùng đúng địa danh cụ thể khi có dữ liệu (Cù Lao Dài, Cồn Phụng, chợ nổi Cái Bè…) thay vì generic "miền Tây" lặp lại — kéo dữ liệu thật từ `entity_name` được nhắc đến nhiều nhất hôm đó.
- Rating "hạt lúa" (mục 5) là 1 chi tiết văn hoá nhỏ, cụ thể cho vùng lúa gạo/miệt vườn — tránh sao ⭐ generic toàn cầu.
- Post-type labels giữ tiếng Việt tự nhiên đã có (Chia sẻ/Đánh giá/Hỏi đáp/Gợi ý) — đúng giọng, không đổi.
- Tránh: không thêm hoạ tiết "làng quê" sáo rỗng (nón lá, cầu khỉ minh hoạ) làm nền trang trí — vì đây là trang UGC, hoạ tiết trang trí giả sẽ mâu thuẫn với tính "thật" của nội dung người dùng viết. Văn hoá thể hiện qua NGÔN NGỮ và DỮ LIỆU THẬT (địa danh, món ăn được nhắc tới), không qua icon trang trí.

## 9. COPY VOICE

Giọng: thân mật, ấm, như người hàng xóm kể chuyện — không hô hào ("Tham gia ngay!"), không marketing-speak.

Ví dụ dateline/masthead:
> **CỘNG ĐỒNG · SỔ TAY MIỀN TÂY HÔM NAY**
> # Hôm nay, ai đó vừa kể chuyện về một buổi sáng ở chợ nổi Cái Bè.
> *1.204 chuyện đã kể · 312 lời khen thật · 890 người miền sông nước*

Ví dụ empty-state (thay cho câu hiện tại):
> Chưa ai kể chuyện hôm nay. Bạn vừa đi đâu, ăn gì ngon — kể cho tụi này nghe với.

Ví dụ CTA cuối bài (liên kết entity):
> Muốn hỏi thêm về Cồn Phụng? Nhắn Zalo cho người rành ở đây.

## 10. SIGNATURE MOMENT

**"Sổ tay hôm nay"** — dòng H1 động đổi theo bài viết mới nhất thực tế trong ngày (không phải placeholder tĩnh), kết hợp với vệt phù-sa hairline "bài mới" phía trên feed. Đây là khoảnh khắc khiến người dùng cảm thấy trang cộng đồng KHÔNG PHẢI một database bài viết tĩnh, mà là một tờ báo tường sống động đang được viết ngay lúc họ ghé qua — thứ mà không nền tảng OCOP/tourism đối thủ nào ở khu vực có.

## 11. COMPONENTS + FEASIBILITY

**Components mới (CSS-tokens only, không thư viện ngoài):**
- `CommunityMasthead` (thay `.catalog-hero.cat-community`): serif H1 động, dateline eyebrow, dòng số liệu serif, phù-sa tick dưới cùng. Props: `latestPostEntityName?`, `stats`. Fallback copy tĩnh khi không có tín hiệu bài mới.
- `.sidebar-kicker` class util: serif-italic, `--text-2xs`, tracked caps, màu `--muted` — dùng lặp lại cho mọi `sidebar-card h2`.
- `.new-post-thread-hint`: hairline gradient river→amber, click-to-scroll, session-only state (không cần API mới, dùng timestamp bài đầu feed đã có).
- `.rating-grains`: 5 SVG elip nhỏ thay `.thread-rating .star`, giữ đúng `role="img" aria-label`.
- `ArticleRail` (chỉ `bai-viet/[id].vue`, ẩn <1200px): tái dùng data đã fetch (`post.entity_id`, `relatedPosts`) — KHÔNG gọi API mới, chỉ bố trí lại.

**CSS/motion cụ thể:**
- Reuse chính xác phù-sa gradient 3-hairline từ `web-nuxt/pages/index.vue` (`.home .block + .block::before`) — tách thành class dùng chung nếu chưa có (khuyến nghị thêm `.sediment-divider` vào file CSS chung, ví dụ `assets/css/utilities.css`, để 13 (community) và các trang khác không copy-paste).
- `useReveal()` áp đều lên sidebar cards với `data-reveal-delay` stagger — composable đã tồn tại, chỉ cần thêm class.
- Font đổi sang `--font-editorial` cho `.thread-detail-page :deep(.thread-content)` — 1 dòng CSS, đã có selector sẵn ở file hiện tại (dòng 620-624 của `bai-viet/[id].vue`), chỉ cần thêm `font-family`.
- Dark-mode: mọi màu mới (hairline gradient, kicker màu muted) đã dùng token nên tự động parity; verify riêng độ tương phản `--muted` trên `.dark` cho kicker italic nhỏ (test WCAG AA cho `--text-2xs`).
- `prefers-reduced-motion`: tắt animation dot-pulse, stagger reveal, giữ CountUp instant-set (đã có pattern reduced-motion trong codebase, tái dùng).

**Reusable cross-page:**
- `.sediment-divider` (phù-sa 3-hairline) → dùng được cho mọi trang có "block-to-block" transition, không chỉ homepage.
- `.sidebar-kicker` → dùng được cho mọi sidebar-card trên site (nếu có trang khác dùng sidebar pattern tương tự).
- `ArticleRail` pattern (nội dung chính rộng + rail phụ ẩn <1200px) → khả năng tái dùng cho các trang single-content-detail khác nếu cần nâng cấp sau (không phải scope hiện tại).

**Không đổi / rủi ro thấp:**
- Compose box, mention autocomplete, comment threading, moderation flow, report flow — giữ nguyên 100% logic, chỉ chỉnh CSS bao quanh.
- Không thêm ảnh AI-gen giả cho bài UGC (vi phạm tính "thật" — CTA/hero chỉ dùng ảnh do chính user upload, không fake).
