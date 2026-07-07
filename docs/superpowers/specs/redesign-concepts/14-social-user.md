# Unit 14 — Profile · Leaderboard · Notifications · Saved

> **STATUS (2026-07-07): concept Ý TƯỞNG — KHÔNG thực thi nguyên văn.** Viết TRƯỚC declutter 3 đợt (ship 2026-07-07) và TRƯỚC chốt định vị 2026-07-06. Khi xung đột: code hiện tại + CLAUDE.md thắng. Trước khi thực thi bất kỳ mục nào: (1) dẹp mọi copy "miền Tây / ba tỉnh" — dùng khung tỉnh-Vĩnh-Long-mới; (2) KHÔNG dùng địa danh ngoài tỉnh (Cái Bè, Lai Vung… thuộc Đồng Tháp); (3) KHÔNG claim "đã xác minh"/quy mô đội ngũ; (4) re-ground line-number trên code hiện tại. Cảnh báo đầy đủ: 00-narrative-system.md. **LƯU Ý RIÊNG:** copy "miền Tây" (:10) CẤM dùng.

### `nguoi-dung/[id].vue` (7.5) · `bang-xep-hang.vue` (6.0) · `thong-bao.vue` (4.5) · `da-luu.vue` (5.5)

> Bốn trang này là **một hệ thống**, không phải bốn trang rời: hồ sơ là *danh tính*, bảng xếp hạng là *vị thế trong cộng đồng*, thông báo là *nhịp đập của mối quan hệ*, đã lưu là *bộ sưu tập hành trình của bạn*. Concept dưới đây thiết kế chúng như một dòng chảy — người dùng bước vào cộng đồng qua hồ sơ, được công nhận qua bảng xếp hạng, được nhắc nhở quay lại qua thông báo, và mang theo hành trình riêng của họ qua mục đã lưu.

---

## 1. STORY ANGLE

Mỗi trang xã hội hiện tại đang kể chuyện **hệ thống** ("đây là dữ liệu của bạn: điểm số, bài viết, thông báo") thay vì kể chuyện **con người** ("đây là hành trình của bạn ở miền Tây, đây là dấu chân bạn để lại, đây là vị trí của bạn trong một cộng đồng đang lớn lên").

- **Hồ sơ người dùng** không phải là "trang thông tin tài khoản" — nó là **cuốn sổ hành trình** (passport/travel journal) của một người đang khám phá Vĩnh Long. Cover photo là bến sông của riêng họ; huy hiệu là con dấu đóng ở mỗi cù lao họ đã ghé; heatmap là "mùa" hoạt động của họ (giống lịch nước lên nước ròng).
- **Bảng xếp hạng** không phải leaderboard game hoá vô hồn — nó là **"Sổ vàng cộng đồng"** (ĐCT xưa hay có sổ lưu niệm/sổ vàng ở đình, ở chùa) — ghi nhận ai đang "giữ lửa" cho cộng đồng bằng đóng góp thật (đánh giá, ảnh, bài viết), không phải điểm số trừu tượng.
- **Thông báo** là **nhịp sóng** — ai đó vừa "chèo" vào đời sống mạng của bạn: một lượt thích như con nước nhẹ, một bình luận như ai đó ghé bến đỗ lại nói chuyện, một người theo dõi mới như một người bạn đồng hành mới lên thuyền.
- **Đã lưu** là **giỏ đệm/khoang thuyền cá nhân** — nơi bạn cất giữ những gì định mang theo cho chuyến đi thật: địa điểm, bài viết truyền cảm hứng, lịch trình đang thai nghén. Không phải "bookmark list" khô khan mà là "hành trang đang xếp".

Chủ đề xuyên suốt: **"Dấu chân trên phù sa"** — mọi hoạt động của một thành viên (viết, đánh giá, lưu, theo dõi) đều là một dấu chân để lại trên lớp phù sa của cộng đồng; theo thời gian những dấu chân ấy bồi thành uy tín, thành vị trí, thành một câu chuyện cá nhân đáng tự hào.

---

## 2. CINEMATIC HERO / THESIS

### Hồ sơ người dùng (biggest opportunity — cover photo hiện là canvas 180px SVG trang trí, chưa kể chuyện gì)
Thay `UserCoverPlaceholder` giản lược (sóng + cây dừa lặp lại y hệt cho MỌI người dùng) bằng **cover sinh động theo cấp bậc + vùng hoạt động chủ đạo** của người dùng đó:
- Nếu user có `cover_url` thật → giữ nguyên, chỉ thêm **Ken Burns rất chậm** (dùng `.is-kb` sẵn có trong `editorial.css`) + scrim gradient dưới đáy để chữ nổi.
- Nếu KHÔNG có cover → SVG placeholder được **cá nhân hoá theo dữ liệu thật**, không còn là 1 SVG tĩnh giống hệt nhau:
  - Màu nền lấy theo **thể loại đóng góp nhiều nhất** của user (nếu chủ yếu review quán ăn → tông amber; nếu chủ yếu bài viết về địa điểm sông nước → tông river; OCOP/sản vật → tông leaf).
  - Vệt "phù sa" ngang cuối cover (dùng đúng gradient 3 hairline river→amber→clay đã có ở `index.vue`) chạy dọc theo **% hoàn thiện hồ sơ** — một thanh tiến trình được nguỵ trang thành đường bờ sông, không phải progress bar lộ liễu.
  - Một dải "waypoint dots" nhỏ tương ứng với `login_streak` — mỗi chấm sáng = 1 ngày liên tiếp, tối đa hiện 14 chấm gần nhất, giống các trạm dừng trên bản đồ sông.
- **Avatar** nổi trên đường viền cover với ring màu theo cấp bậc reputation (level 1 = ink nhạt, level 4 = amber ánh kim) thay vì viền trắng đồng nhất — cấp bậc phải NHÌN THẤY ngay ở avatar, không chỉ đọc chữ.

### Bảng xếp hạng
Header hiện là `<h1>Thành viên tích cực</h1>` + 1 dòng mô tả — không có hero. Nâng cấp: một **dải "bục vinh danh" (podium strip)** biên tập, không phải game leaderboard kiểu app điểm số:
- 3 người dẫn đầu hiện ở một hàng ngang phía trên danh sách, thẻ lớn hơn, có avatar + huy hiệu cấp bậc + **1 dòng trích dẫn tự động** rút từ đóng góp nổi bật nhất của họ (ví dụ: đánh giá được nhiều tim nhất) — biến con số thành câu chuyện.
- Đường viền "phù sa" (3-hairline) ngăn cách phần bục vinh danh với danh sách #4 trở đi.

### Thông báo
Không cần hero cinematic nặng (đây là trang tiện ích, tần suất ghé cao) — nhưng đổi **eyebrow + heading** sang giọng CE (dateline caps), và quan trọng nhất: **avatar người thực hiện hành động** phải xuất hiện (finding lớn nhất — hiện tại 100% icon emoji, không có avatar).

### Đã lưu
Đổi "Kho cá nhân" (kicker hiện có, đã đúng hướng) thành cinematic nhẹ: dải nền "waterline" mờ phía sau overview 3 số liệu — như thể các con số nổi trên mặt nước.

---

## 3. LAYOUT + RHYTHM

**Hồ sơ:**
```
[Cover cinematic 220px + avatar nổi + ring cấp bậc]
[Tên + hành động (theo dõi/sửa/chia sẻ)]
[Chip trạng thái + reputation + XP bar]
[Streak + Achievement showcase — giữ, nhưng gom vào "collapsed drawer" mặc định đóng cho profile người khác]
—— hairline phù-sa 3 màu ——
[Stats row → giờ là "sổ hành trình" ngang: bài viết · đánh giá · theo dõi · tham gia]
[Heatmap — đổi tên "Bản đồ con nước" / giữ nguyên cơ chế GitHub-heatmap nhưng palette theo river→amber→clay thay vì xanh lá generic]
—— tabs (posts/reviews/timeline/saved/collections) ——
[feed]
```
Nhịp: cover → định danh → bằng chứng số → bằng chứng chuyện (timeline) → nội dung. Đúng thứ tự "ai đó là ai" trước khi "họ đã làm gì".

**Bảng xếp hạng:**
```
[Eyebrow "SỔ VÀNG CỘNG ĐỒNG · Cập nhật {period}"]
[H1 + dek 1 câu]
[Bục vinh danh — top 3, thẻ lớn, ngang trên desktop / xếp dọc so le trên mobile]
—— phù-sa hairline ——
[Filter chips + search]
[Danh sách #4+ — giữ layout hiện có, chỉ tinh chỉnh token]
[Vị trí của bạn — sticky bottom bar nếu không nằm trong top 50 hiển thị, thay vì 1 dòng tình cờ ở giữa]
```

**Thông báo:**
Giữ layout list hiện tại (đã hợp lý cho use-case tần suất cao, không nên "cinematic hoá" quá đà — over-animation ở trang tiện ích = tính năng khó dùng). Chỉ nâng cấp: avatar actor bên trái thay icon emoji, nhóm theo ngày ("Hôm nay" / "Hôm qua" / "Tuần này") thay vì list phẳng.

**Đã lưu:**
Giữ cấu trúc tab hiện tại (đã tốt — entities/posts/itineraries), thêm 1 dải "Trạng thái hành trình" phía trên overview: nếu user có ≥3 địa điểm đã lưu cùng 1 khu vực → gợi ý nổi bật "Đủ để ghép thành 1 ngày ở {khu vực}" liên kết sang `/tao-lich-trinh`.

**Responsive chung:** cover 220px → 140px mobile; bục vinh danh top-3 chuyển từ hàng ngang sang thẻ dọc so le (huy chương giữa cao hơn 2 bên) → mobile xếp thành 1 cột với thứ tự 1-2-3 rõ ràng bằng số lớn.

---

## 4. TYPOGRAPHY

- **Tên người dùng trên hồ sơ (`<h1>`)**: chuyển sang `var(--font-editorial)` (Fraunces) thay vì font-sans mặc định hiện tại — tên riêng của một con người xứng đáng được "xưng danh" bằng serif, giống cách CE đã làm với tiêu đề địa điểm.
- **Bio**: giữ font-sans (đọc dài, không nên serif hoá).
- **Điểm/rank trên bảng xếp hạng**: số điểm lớn dùng `font-variant-numeric: tabular-nums` (đã có) nhưng đổi font thành editorial serif cho riêng con số của top-3 (biến điểm số thành thứ đáng chiêm ngưỡng, không phải liệt kê).
- **Trích dẫn tự động trong bục vinh danh**: dùng class `.pull-quote`-lite (serif, italic, cỡ nhỏ hơn bản gốc) đã có sẵn convention trong `editorial.css`.
- **Eyebrow/dateline** ở bảng xếp hạng + tiêu đề section trong hồ sơ: `var(--font-sans)`, `text-transform: uppercase`, `letter-spacing: var(--tracking-caps)`, `font-size: var(--text-2xs)` — tái dùng nguyên xi `.cine-kicker` pattern.

---

## 5. SENSORY + MOTION + CURIOSITY

- **Ken Burns cực chậm** trên cover hồ sơ nếu có ảnh thật (`--dur-kenburns`, đã có, chỉ cần gắn class `.is-kb`).
- **XP bar fill**: animate width lúc mount bằng CSS transition (0 → giá trị thật) thay vì hiện tĩnh — cảm giác "nước dâng" khi trang tải xong.
- **Heatmap "bản đồ con nước"**: hover 1 ô hiện tooltip đã có; thêm subtle scale(1.15) transition khi hover, gated bởi `prefers-reduced-motion`.
- **Streak chip 🔥**: khi số ngày là bội số của 7 (1 tuần) → thêm 1 hiệu ứng nhấp nháy nhẹ 1 lần duy nhất lúc mount (không loop — loop liên tục = AI-slop).
- **Bục vinh danh top-3**: khi trang tải, 3 thẻ reveal so le (stagger 80ms) từ hairline phù-sa — dùng `useReveal()` composable đã có.
- **Discovery device — "Vết tích gần đây"**: trên hồ sơ, thêm 1 dải nhỏ ngay dưới cover (chỉ hiện với profile người khác, chưa follow) — 1 dòng: "Vừa đánh giá {tên địa điểm} · {thời gian}" nếu có hoạt động timeline gần nhất, kèm link — biến "xem hồ sơ" thành "xem điều họ vừa khám phá", tăng tò mò bấm follow.
- **Notification actor avatar + micro-grouping**: khi nhiều người cùng thích 1 bài, hiện dải avatar chồng nhau (giống Facebook) thay vì chỉ số `+N` — cảm giác "có người thật" thay vì con số.
- **Sensory qua màu, không qua chuyển động thừa**: palette river cho hoạt động mạng xã hội (theo dõi/bình luận — chuyện chảy), amber cho thành tích/đặc sản (review/OCOP), clay cho bài viết gốc (đất, nền tảng) — mã hoá cảm xúc bằng màu tri-province có sẵn thay vì thêm icon mới.

**Giới hạn chống AI-slop**: KHÔNG particle effect, KHÔNG confetti khi lên cấp, KHÔNG shimmer loop trên badge, KHÔNG gradient text cầu vồng. Mọi motion đều single-shot hoặc rất chậm (Ken Burns), tất cả gated `prefers-reduced-motion`.

---

## 6. UX FLOW

**Hồ sơ (người khác xem):** Cover → tên + cấp bậc (0.5s để nhận diện "ai đây, đáng tin không") → "Vết tích gần đây" (tò mò) → nút Theo dõi (đã nổi bật, giữ) → lướt xuống thấy bằng chứng đóng góp thật (stats + timeline) → CTA phụ "Xem cộng đồng". Friction hiện tại thấp — giữ nguyên logic follow/block/report, chỉ nâng cấp visual.

**Hồ sơ (chính mình):** Cover → completion nudge (đã có, giữ vì hiệu quả) → achievement showcase (đã có nhưng cần **thu gọn mặc định** trên mobile, hiện `open` mặc định chiếm nhiều màn hình đầu) → tab Đã lưu/Danh sách dễ thấy vì đây là "workspace" hàng ngày.

**Bảng xếp hạng:** Vào trang → thấy ngay vị trí của mình nếu đã đăng nhập (hiện đã có `bxh-self` nhưng nằm giữa filter và list, dễ bị bỏ lỡ) → nâng cấp thành 1 **sticky insight bar** ngay dưới H1 khi có `selfEntry`, kèm CTA "Cách lên hạng?" dẫn tới hướng dẫn — biến trang từ "xem người khác" thành "biết mình đứng đâu, làm gì để lên".

**Thông báo:** Vào trang → nhóm theo ngày → click vào 1 thông báo dẫn thẳng tới ngữ cảnh (bài/comment) — đã đúng. Thêm: nút "Đọc tất cả" hiện luôn (không chỉ khi có unread) nhưng disabled khi không cần, giữ layout ổn định tránh nhảy nút.

**Đã lưu:** Vào trang → overview 3 số → tab → **gợi ý ghép lịch trình** khi đủ dữ kiện (đã note ở §3) là chỗ giảm friction lớn nhất: biến "danh sách tĩnh" thành "bước tiếp theo rõ ràng" mà không vi phạm CTA-contact-only (đây là điều hướng nội bộ, không phải booking).

---

## 7. PREMIUM CUES

- Avatar ring dùng `conic-gradient` mảnh theo cấp bậc thay vì border phẳng — chi tiết nhỏ, đắt tiền.
- Hairline phù-sa 3-màu dùng đúng công thức đã "chuẩn hoá" ở `index.vue` (river→amber→clay, thon 2 đầu) — nhất quán tuyệt đối, không tự chế thêm biến thể.
- Số liệu tabular-nums căn phải, không nhảy layout khi CountUp chạy (component đã có, đảm bảo dùng `font-variant-numeric: tabular-nums` ở mọi nơi hiển thị điểm).
- Bục vinh danh: khoảng cách, bóng đổ (`--shadow`) tinh tế, không viền màu sặc sỡ; chỉ số hạng #1 dùng màu `--rank-gold` đã định nghĩa (giữ, đã đúng chất "sang" thay vì rực rỡ).
- Trạng thái rỗng (`EmptyState`) mọi nơi đã nhất quán — giữ nguyên, đây là premium cue có sẵn (không phải icon lỗi xám xịt).
- Focus ring, WCAG contrast, dark-mode parity: audit lại tất cả màu mới thêm (ring cấp bậc, waterline gradient) qua `--dark` overrides tương ứng.

---

## 8. CULTURAL AUTHENTICITY

- "Bản đồ con nước" thay cho "activity heatmap" kiểu GitHub thuần code — vẫn cùng cơ chế 365 ô nhưng đặt tên và tooltip mang giọng miền Tây ("Ngày {date}: {count} đóng góp — như con nước lớn").
- Huy hiệu/thành tích: giữ nguyên hệ thống category (Nội dung/Khám phá/Cộng đồng/Kỳ cựu/Đặc biệt) đã có — đúng hướng, chỉ cần icon/label rà lại để không sa vào biểu tượng gaming chung chung (tránh 🏆⭐🎮 lặp lại vô hồn) mà dùng hình ảnh gắn với Vĩnh Long: 🛶 (xuồng) cho "khám phá", 🥥 (dừa) cho mốc đóng góp OCOP, 🌾 cho mốc bài viết đầu tiên.
- Streak = "chuỗi ngày ghé bến" thay vì "login streak" khô khan.
- KHÔNG dùng biểu tượng chợ nổi/áo bà ba làm hình trang trí sáo rỗng nếu không gắn với dữ liệu thật của user — tính xác thực đến từ VIỆC LÀM của người dùng (bài viết, đánh giá) được tôn vinh, không phải hoa văn trang trí chung chung dán lên.
- Bục vinh danh gọi là "Sổ vàng cộng đồng" — mượn hình ảnh có thật ở đình/chùa Nam Bộ (sổ vàng công đức), phù hợp tinh thần "được ghi nhận" chứ không phải "đấu game".

---

## 9. COPY VOICE

Giọng: ấm, gần gũi, tôn trọng — như người quen giới thiệu bạn với xóm giềng, không hô khẩu hiệu marketing.

Ví dụ cụ thể:

- **Hồ sơ (empty activity, người khác xem):** *"Thành viên mới, chưa để lại dấu chân nào trên phù sa Vĩnh Long — nhưng biết đâu chuyến đi đầu tiên của họ đang chờ bạn theo dõi."*
- **Hồ sơ (streak):** *"🔥 12 ngày liền ghé lại — coi bộ vùng đất này đang giữ chân bạn."*
- **Bảng xếp hạng (eyebrow):** *"SỔ VÀNG CỘNG ĐỒNG · Cập nhật tuần này"*
- **Bảng xếp hạng (self insight):** *"Bạn đang đứng hạng #34 — còn 18 điểm nữa để vượt qua {tên người #33}."*
- **Thông báo (nhóm actor):** *"Yến Nhi và 4 người khác vừa thích đánh giá của bạn về Cồn Chim."*
- **Đã lưu (gợi ý ghép lịch trình):** *"Bạn đã lưu 4 điểm quanh Cù lao An Bình — đủ để ghép thành 1 ngày rong ruổi. Gộp thành lịch trình?"*

---

## 10. SIGNATURE MOMENT

**Cover hồ sơ "sống theo dữ liệu thật của chính người đó"** — vệt phù sa chạy theo % hoàn thiện hồ sơ, màu nền đổi theo thể loại đóng góp mạnh nhất, ring avatar đổi theo cấp bậc, chấm waypoint đổi theo streak. Không một hồ sơ nào trông giống hồ sơ khác dù dùng cùng 1 hệ thống SVG placeholder — đây là điều **không tồn tại ở bất kỳ trang MXH template nào** (Facebook/Instagram cover đều tĩnh, không kể chuyện dữ liệu). Đây là khoảnh khắc biến "trang hồ sơ" thành "chân dung được vẽ bằng chính hành động của người dùng" — đúng tinh thần "dấu chân trên phù sa" xuyên suốt cả 4 trang.

Signature phụ (bảng xếp hạng): **"Sổ vàng cộng đồng"** — bục vinh danh với trích dẫn tự động rút từ đóng góp nổi bật nhất, biến 3 con số đầu bảng thành 3 câu chuyện ngắn.

---

## 11. COMPONENTS + FEASIBILITY

**Component mới (CSS-tokens only, không thư viện ngoài):**
1. `UserCoverPlaceholder.vue` — nâng cấp props: nhận `dominantCategory` ('river'|'amber'|'leaf'|'clay'), `completionPct`, `streakDays` (≤14 hiện waypoint dots) → render SVG động theo props thay vì tĩnh. Tính `dominantCategory` ở page bằng cách so `post_count` vs `review_count` vs stats theo category nếu backend có (nếu chưa có breakdown theo category, fallback: dùng review_count vs post_count, 2 nhóm là đủ cho v1 — KHÔNG cần thêm API mới).
2. `.rep-ring` CSS class — `avatar-xl` bọc thêm 1 lớp `conic-gradient` theo `data-level` (1-4), dùng `mask` để tạo viền mảnh 3px, tái dùng được ở `bang-xep-hang.vue` (avatar 44px) và notification actor avatar.
3. `PodiumStrip.vue` (mới, dùng riêng ở `bang-xep-hang.vue`) — nhận `top3` array, render 3 thẻ với trích dẫn tự động (lấy từ field có sẵn nếu backend trả về "đóng góp nổi bật" — nếu chưa có, v1 dùng câu tổng hợp từ số liệu: "{reviews} đánh giá · {posts} bài viết" bọc trong giọng editorial, KHÔNG cần gọi thêm API).
4. `.hairline-phusa` utility class — tách gradient 3-hairline hiện đang inline trong `index.vue` (`.home .block + .block::before`) thành 1 class dùng chung ở `assets/css/editorial.css`, áp dụng cho cả 4 trang này (giữa cover-và-info trong hồ sơ, giữa bục-vinh-danh-và-list trong bảng xếp hạng). **Đây là refactor tái sử dụng thấy rõ, không phải trùng lặp code.**
5. Notification actor avatar — `thong-bao.vue` cần backend trả `actor_avatar_url`/`actor_name` trong payload (kiểm tra `agent/social.py` xem đã có field này chưa; nếu chưa, đây là thay đổi backend nhỏ, additive, cần 1 test theo B4). Nếu backend chưa sẵn sàng, v1 front-end có thể fallback dùng chữ cái đầu tên actor (đã có pattern `.avatar` size nhỏ ở nhiều nơi) thay vì emoji icon.

**CSS/motion cụ thể:**
- Tái dùng `useReveal()` (đã có toàn site) cho stagger bục vinh danh + achievement cards.
- Tái dùng `.cine-kicker`, `--tracking-caps`, `--font-editorial` cho mọi eyebrow mới — không tạo token mới.
- Ken Burns: gắn class `.is-kb` có sẵn trong `editorial.css` lên `.cover-img` khi `profile.cover_url` tồn tại.
- XP-bar animate: `transition: width .6s var(--ease-out)` cộng `will-change: width`, trigger lúc mounted qua `nextTick`.
- Dark-mode: mọi màu mới (ring cấp bậc, waterline gradient) cần override tương ứng trong `dark-overrides.css`, theo đúng convention `.dark .xxx { }` đã thấy trong file.
- Reduced-motion: bọc mọi keyframe/stagger trong `@media (prefers-reduced-motion: reduce)` tắt animation, giữ trạng thái cuối (pattern đã chuẩn hoá toàn site).

**Reusable across pages:**
- `.hairline-phusa` (mục 4) → dùng được ở CẢ 4 trang trong unit này VÀ có thể lan sang các trang catalog/social khác chưa CE-hoá (ví dụ `cong-dong.vue`) — đúng tinh thần "EntityCard là keystone" nhưng ở tầng social, `.hairline-phusa` + `.rep-ring` là 2 keystone tương đương cho tầng người dùng.
- `PodiumStrip` là component riêng cho bảng xếp hạng, không tái dùng nơi khác nhưng pattern "trích dẫn tự động từ dữ liệu" có thể áp dụng lại cho trang "Thành viên nổi bật" nếu có trong tương lai.

**Feasibility check theo bất biến dự án:** không thêm dịch vụ trả phí, không cần LLM, không đổi CTA (vẫn contact-only ở các trang khác — 4 trang này vốn không có CTA booking), toàn bộ là CSS-tokens + component Vue nhỏ + (tuỳ chọn) 1 field backend nhỏ có test đi kèm theo B3/B4 của CLAUDE.md.
