# Nghiên cứu và thiết kế hệ thống UI chuyên nghiệp cho vinhlong360

> **STATUS:** `draft-for-review` - snapshot 2026-07-27.
> **Vai trò:** tài liệu này mở rộng và cụ thể hóa phần visual foundation, shell và bốn pilot trong `2026-07-27-vinhlong360-ui-first-super-app-design.md`.
> **Phạm vi:** thiết kế bằng văn bản; chưa chỉnh code UI, route, API, dữ liệu hoặc quyền truy cập.

## 1. Kết luận điều hành

Định hướng khuyến nghị là **Mekong Signal Atlas - Civic Cartographic Modernism**.

Đây không phải một lần “làm đẹp” theo preset. Nó chuyển vinhlong360 từ giao diện travel/editorial đang chiếm ưu thế thành một Local Intelligence Platform có ba lớp rõ ràng:

1. **Thông tin địa phương thích ứng:** thông tin cần biết ngay, gần người dùng và có nguồn.
2. **Khám phá biên tập:** khám phá địa phương bằng ảnh, câu chuyện và hành trình có chọn lọc.
3. **Vận hành công ích:** danh bạ, độ tin cậy, kiểm duyệt, dữ liệu và AdminCP có mật độ cao.

Quyết định quan trọng nhất: **trang chủ không tiếp tục mở bằng hero du lịch toàn màn hình**. Vùng nhìn đầu trở thành **Bảng tin địa phương thích ứng** gồm ngữ cảnh khu vực, tìm kiếm, tín hiệu chính thức và các việc có thể làm ngay. Chất biên tập được đưa xuống sau lớp tiện ích, nơi nó tạo cảm xúc đúng lúc mà không làm sai định vị super app.

Thiết kế dùng một chữ ký chung là **Dòng địa bàn**: đường bản đồ có nút dữ liệu, mang nghĩa khu vực, nguồn, hành trình hoặc workstream. Đây là rủi ro thẩm mỹ có chủ đích và là yếu tố giúp hệ thống không giống template AI.

## 2. Phạm vi đã kiểm tra

- 68 page template: 36 ngoài AdminCP, 32 AdminCP.
- 12 layout family.
- 138 file Vue; 32 file dài hơn 500 dòng và 7 file dài hơn 1.000 dòng.
- Bốn pilot: `/`, `/du-lich`, `/dia-diem/[id]`, `/admin`.
- Foundation: `variables.css`, 9 file CSS global, font, icon, dark mode, accessibility state.
- Shell: `layouts/default.vue`, `layouts/admin.vue`.
- Các đặc tả cinematic/editorial, homepage refinement, declutter và UX audit trước đây.
- Hệ thống skill: `frontend-design`, `designing-ui-foundations`, `design-system`, `ui-ux-pro-max`, `brand`, `superpowers:brainstorming`.

## 3. Kết quả từ skill và cách sử dụng

### 3.1 `ui-ux-pro-max`

Kết quả tự động cho public nghiêng về Swiss Modernism, Be Vietnam Pro/Noto Sans và cặp cam/xanh bản đồ. Admin nghiêng về dashboard mật độ dữ liệu cao. Các nguyên tắc được giữ:

- Lưới rõ, responsive và mật độ theo bối cảnh.
- Public có accessibility cao; Admin mật độ cao nhưng ưu tiên công việc.
- Không dùng emoji làm thành phần cấu trúc.
- Motion 150-300ms, reduced motion, touch target 44px.
- SSR, lazy hydration và state giữ ổn định trong Nuxt.

Không áp dụng nguyên xi:

- Landing cộng đồng/diễn đàn không đại diện cho toàn super app.
- Bảng màu cam/xanh theo preset không đủ bản sắc.
- EB Garamond/Lato cho AdminCP tạo cảm giác legal, không phù hợp màn hình vận hành.
- Lưới thẻ KPI và spinner trung tâm không phải mặc định cho dashboard vận hành.

### 3.2 `frontend-design`

Các ràng buộc được đưa thành quyết định thiết kế:

- Hero phải là luận đề của sản phẩm, không phải công thức marketing.
- Typography có vai trò; không dùng display serif ở mọi nơi.
- Mỗi family có một signature có nghĩa.
- Chỉ tiêu độ táo bạo ở một nơi, phần còn lại kỷ luật.
- Copy gọi đúng việc người dùng kiểm soát và hành động xảy ra.

### 3.3 `designing-ui-foundations` và `design-system`

- Token ba lớp primitive -> semantic -> component.
- Màu primitive OKLCH, có sRGB fallback đúng cho webview cũ.
- Body contrast mục tiêu 7:1, UI 3:1, kiểm tra độc lập light/dark.
- Glass chỉ ở chrome, không ở content.
- Dark mode được thiết kế lại chroma/lightness, không đảo màu.
- Container query cho component, viewport breakpoint cho shell.
- Forced colors, contrast preference, font budget và Vietnamese glyph là acceptance gate.

### 3.4 `brand`

Visual identity được gắn với chất liệu thật của hệ thống:

- Sông, địa bàn, bản đồ, gạch Mang Thít, vườn và nhịp địa phương.
- Không biến chúng thành họa tiết dân gian dán lên card.
- Hình ảnh chuyển từ “cinematic vàng” sang ảnh tư liệu hữu ích và có nguồn gốc rõ.
- Giọng thương hiệu: gần gũi, rõ nguồn, hiểu địa bàn, không phô trương công nghệ.

### 3.5 Hạn chế nghiên cứu web

Skill `9router-web-search` đã được kiểm tra nhưng workspace chưa có `NINEROUTER_URL`/`NINEROUTER_KEY`. Không cài hoặc thay đổi cấu hình máy. Vì vậy, vòng này dùng code thật, tài liệu dự án và cơ sở dữ liệu skill cục bộ làm nguồn chính.

## 4. Audit hiện trạng: bằng chứng và rủi ro

Các số sau là số lần xuất hiện trong file `.css`, `.vue`, `.ts`, không phải số component độc lập:

| Tín hiệu | Số lần | Phạm vi file | Rủi ro |
|---|---:|---:|---|
| `linear-gradient` | 332 | 69 file | Gradient trở thành phản xạ mặc định |
| `radial-gradient` | 36 | 15 file | Nhiều motif nền cạnh tranh nhau |
| `backdrop-filter` | 82 | 17 file | Glass có nguy cơ rò vào content |
| `box-shadow` | 610 | 71 file | Elevation thiếu semantic discipline |
| `border-radius` | 897 | 114 file | Card/pill hóa quá nhiều surface |
| Raw hex | 532 | 79 file | Token drift và dark parity khó kiểm soát |
| `rgb/rgba` | 1.859 | 98 file | Nhiều màu/effect đặt trực tiếp |
| Primitive `oklch(...)` | 0 | 0 file | Có `color-mix(in oklch)` nhưng chưa có thang OKLCH thật |
| Unicode emoji structural | hiện diện | 54 file | Không đồng nhất platform/theme |
| HTML numeric icon | hiện diện | 21 file | Đặc biệt nhiều trong AdminCP |

Nền tảng hiện tại cũng có điểm mạnh:

- 273 `focus-visible` rule.
- 144 reduced-motion rule.
- Có touch token, icon scale, skeleton, dark mode, source disclosure và semantic alias bước đầu.
- Fraunces đã self-host subset tiếng Việt.
- `IconLine` đã chứng minh hướng icon line có thể mở rộng.

### 4.1 Style stack đang chồng lớp

Hiện có Apple HIG, M3, cinematic editorial, travel platform, seasonal theme, glass và category gradient trong cùng foundation. Mỗi lớp riêng lẻ có lý, nhưng tổng hợp tạo ra ba vấn đề:

1. Nhiều token cùng nói về một khái niệm: surface, elevation, duration, radius.
2. Page tự đặt style để “khác biệt”, làm component chung mất vai trò source of truth.
3. Một thay đổi UI toàn dự án khó dự đoán vì cascade qua khoảng 316 KiB CSS global và 123 style block Vue.

### 4.2 Định vị ưu tiên du lịch không còn khớp sản phẩm

Homepage hiện mở bằng ảnh du lịch điện ảnh, seasonal tagline và recommendation card. Cấu trúc này phù hợp site destination nhưng không đại diện cho super app có cảnh báo, thời tiết, giao thông, danh bạ, cộng đồng và dịch vụ thiết yếu.

Hậu quả:

- Thông tin chính thức/tiện ích địa phương bị đẩy xuống dưới cảm xúc du lịch.
- Người địa phương có thể không nhận ra giá trị truy cập hằng ngày.
- Personalization khó giải thích vì top zone đã được cố định theo travel narrative.

### 4.3 Hero, thẻ và gradient trở thành công thức

Nhiều catalog dùng biến thể `catalog-hero`, emoji/motif, stats, filter, nhiều shelf rồi mới tới results. Dù đã declutter, cấu trúc vẫn có nguy cơ “mỗi trang một hero nhưng thân trang giống nhau”.

Card hiện là container mặc định cho entity, contact, settings, stats, dashboard và cross-link. Đây là dấu hiệu giao diện template: nội dung khác vai trò nhưng được bọc cùng anatomy.

### 4.4 Typography chưa có ranh giới chức năng

- Fraunces có character và hỗ trợ tiếng Việt, nhưng nếu dùng rộng với nền ấm/đất nung sẽ rơi vào cụm thẩm mỹ AI phổ biến.
- UI body vẫn dùng system stack chứa Inter/Roboto/Arial fallback, chưa tạo bản sắc Việt rõ.
- Admin và public chưa có type role tách biệt đủ rõ cho data, narrative và control.

### 4.5 Iconography bị chia đôi

- Public đã có `IconLine` 1.75 stroke.
- Nhiều page vẫn dùng emoji trong hero, badge, facts, CTA và empty state.
- Admin sidebar/dashboard dùng HTML numeric emoji/entity.

Kết quả là hệ thống nhìn như hai sản phẩm và thay đổi theo OS.

### 4.6 Photography có nguy cơ “AI cinematic đồng loạt”

Các ảnh hero/spread hiện xem được đều nghiêng về ánh sáng vàng, sông-vườn, bố cục điện ảnh. Chúng đẹp riêng lẻ nhưng quá đồng nhất, làm giảm tính tư liệu và tạo cảm giác ảnh tạo sinh.

Thiếu các loại ảnh cần cho Local Intelligence:

- Mặt tiền và biển hiệu thực.
- Lối vào, bãi xe, accessibility, giờ hoạt động.
- Cơ sở y tế/giáo dục/hành chính với provenance.
- Con người, hoạt động và hạ tầng trong ánh sáng thường ngày.

### 4.7 Page và component quá lớn

Các page lớn nhất: `cong-dong.vue` 1.909 dòng, `admin/entities.vue` 1.585, detail 1.446, home 1.410. File lớn chứa template, data orchestration và scoped style khiến:

- Khó giữ anatomy đồng nhất.
- Dễ tạo thêm class/radius/shadow cục bộ.
- QA visual theo family khó hơn QA theo page.

Redesign phải trích theo boundary sản phẩm, không chỉ cắt file cơ học.

### 4.8 AdminCP là dashboard trang trí nhiều hơn workbench

- Sidebar dày, không scope-aware hoàn toàn, dùng emoji/entity.
- Dashboard mở bằng KPI card grid, nhiều chart và quick action; priority work không đứng đầu tuyệt đối.
- Mobile biến sidebar thành dải nav ngang dài, không phù hợp 32 page.
- Spinner trung tâm và full loading làm mất dữ liệu cũ trong lúc refresh.

## 5. Ba phương án đã so sánh

### A. Cinematic Editorial 2.0

Giữ hero/ảnh/Fraunces hiện tại, token hóa và thay emoji.

- Ưu: ít thay đổi, tận dụng code/ảnh đã có, nhanh.
- Nhược: vẫn ưu tiên du lịch; dễ tiếp tục giống site du lịch do AI tạo; AdminCP khó chung hệ.
- Phù hợp nếu mục tiêu chỉ là nâng site tourism, không phù hợp super app đã chốt.

### B. Mekong Signal Atlas - khuyến nghị

Bảng tin địa phương ưu tiên công việc ở trên; biên tập theo ngữ cảnh; mật độ công ích/dữ liệu cho danh bạ và AdminCP. Dòng địa bàn là chữ ký có nghĩa.

- Ưu: khớp Unified Local Life Graph; khác biệt nhưng không phô trương; mở rộng tốt cho weather/traffic/alerts/services/community.
- Nhược: cần tái cấu trúc shell/home và component anatomy, không chỉ đổi CSS.
- Rủi ro: nếu Dòng địa bàn bị lạm dụng sẽ thành motif trang trí; master rules đã giới hạn một line chính/view.

### C. Tiện ích mềm theo kiểu ứng dụng

Mobile-first, bottom nav, surface mềm, card module và interaction kiểu super app phổ biến.

- Ưu: nhanh học, hiệu quả touch, dễ triển khai.
- Nhược: dễ giống hàng loạt ứng dụng tiêu dùng; làm yếu bản sắc địa phương; thẻ/glass/pill càng tăng.

**Chọn B.** A và C chỉ được dùng như nguồn kỹ thuật cục bộ, không làm visual direction.

## 6. Brand và ngôn ngữ thị giác cuối cùng

### 6.1 Subject, audience, job

- **Subject:** địa bàn và đời sống địa phương Vĩnh Long mở rộng.
- **Audience:** người dân, khách đến khu vực, cơ quan, đối tác và đội vận hành.
- **Nhiệm vụ duy nhất của shell:** luôn cho biết người dùng đang ở ngữ cảnh nào, có gì đáng chú ý và hành động tiếp theo là gì.

### 6.2 Tính cách

- Hiểu địa bàn, không khoe dữ liệu.
- Gần gũi, không xuề xòa.
- Chính xác, không lạnh lùng.
- Có chiều sâu biên tập, không văn hoa ở control.
- Hiện đại, không chạy theo hiệu ứng.

### 6.3 Voice chart

| Trait | Làm | Không làm |
|---|---|---|
| Rõ địa bàn | `Cách bạn 2,4 km tại phường...` | `Khám phá quanh bạn` mơ hồ |
| Rõ nguồn | `Thông báo từ UBND...` | `Tin nóng` không nguồn |
| Rõ hành động | `Mở chỉ đường` | `Tìm hiểu thêm` khi thực chất mở bản đồ |
| Bình tĩnh | `Chưa tải được dữ liệu. Thử lại.` | Xin lỗi dài hoặc đổ lỗi |
| Trung thực | `Khu vực ước tính từ IP` | Ngụ ý có GPS khi chưa consent |

## 7. Foundation cuối cùng

Chi tiết token được ghi tại `design-system/vinhlong360/MASTER.md`.

Các quyết định cốt lõi:

- Primary action chuyển sang river teal; clay là brand/signature, không nhuộm toàn UI.
- Canvas dùng alluvial paper gần neutral, tránh “warm cream luxury template”.
- Be Vietnam Pro cho UI/body/Admin; Fraunces chỉ cho editorial feature.
- Radius 8/12/20, pill chỉ cho filter/status.
- Content mặc định flat/border; shadow chỉ ở overlay/chrome.
- Glass chỉ ở sticky chrome/map control.
- Dòng địa bàn thay thế phần lớn gradient signature.

## 8. Shell trải nghiệm thích ứng

### 8.1 Desktop public

Hàng đầu ưu tiên universal search và context location. Navigation chính giữ năm destination: Trang chủ, Khám phá, Gần bạn, Cộng đồng, Lịch trình. Các catalog sâu vào mega panel/contextual navigation.

Context control luôn nói rõ:

- Khu vực đang dùng.
- Nguồn context: người dùng chọn / GPS / IP ước tính.
- Trạng thái vị trí.
- Link chỉnh khu vực/sở thích/reset.

### 8.2 Mobile public

Top chrome có context, search trigger và alert state. Bottom nav năm mục. Search/filter/map dùng sheet phù hợp task; không mang desktop dropdown xuống mobile.

### 8.3 AdminCP

Navigation theo scope và workstream. Mobile dùng drawer/task switcher. Dashboard là triage desk; page con table/queue dùng bulk action, detail sheet và state riêng.

## 9. Mười hai layout family

| Family | Composition riêng | Signature | Không được làm |
|---|---|---|---|
| Trang chủ/bản tin địa phương | ngữ cảnh -> tín hiệu chính thức -> bản tin -> khám phá | Dòng địa bàn tín hiệu | hero du lịch cỡ lớn |
| Catalog | tuyên bố atlas -> bộ lọc -> nội dung tuyển -> kết quả | mục lục atlas | nhiều kệ nội dung trước kết quả |
| Bản đồ/danh bạ | tìm/lọc -> bản đồ/danh sách -> nguồn/độ mới | đường/ghim đang chọn | lưới thẻ chật cạnh bản đồ |
| Chi tiết | nguồn/tiêu đề/ảnh -> hành động -> câu chuyện/sự kiện -> liên quan | đường từ nguồn tới hành động | 17 dòng emoji và CTA |
| Khu vực/sở thích | tuyên bố địa bàn -> mục lục vùng -> nổi bật -> xã/phường | ranh giới/mục lục địa bàn | đổi gradient tùy ý theo vùng |
| Lập lịch trình | điểm dừng -> bản đồ -> thời gian/phương tiện -> lưu/chia sẻ | tuyến đường thật | wizard trang trí không có trạng thái |
| Cộng đồng | soạn bài/feed -> nguồn/kiểm duyệt -> khám phá | đường hội thoại/nguồn | sao chép Threads và feed thẻ chung chung |
| Không gian cá nhân | mức sẵn sàng/công việc -> đã lưu/hoạt động -> cài đặt | đường tiến triển cá nhân | lưới thẻ dashboard lặp |
| Nội dung dài/tin cậy | masthead gọn -> nội dung đọc -> nguồn/liên hệ | đường kẻ biên tập | hero cinematic trên pháp lý/trợ giúp |
| Dashboard Admin | hàng đợi ưu tiên -> sổ sức khỏe -> ngoại lệ | đường workstream | tường thẻ KPI |
| Hàng đợi/bảng Admin | thanh công cụ -> chọn -> bảng -> chi tiết/hành động | đường trạng thái/SLA | hành động từng dòng, thiếu xử lý hàng loạt |
| CMS Admin | ngữ cảnh -> nhóm biểu mẫu -> xem trước/lịch sử | đường trạng thái xuất bản | biểu mẫu một cột dài không tiến trình |

## 10. Bốn pilot

### 10.1 `/` - Bảng tin địa phương thích ứng

- Thay hero full-screen bằng context + search + official signal + briefing.
- Editorial image nằm sau lớp utility.
- Mọi personalization có `Vì sao bạn thấy nội dung này`.
- Module không có dữ liệu thì ẩn; không gọi feed mặc định là `Dành cho bạn`.
- Chi tiết tại `design-system/vinhlong360/pages/home.md`.

### 10.2 `/du-lich` - Atlas Catalog

- Atlas statement và index thay emoji mode pills/stats hero.
- Một curated feature trước results, không 5-7 shelf.
- EntityTile khi ảnh thật đủ tốt; EntityRow khi thiếu ảnh.
- Filter state có URL và giữ khi quay lại.
- Chi tiết tại `design-system/vinhlong360/pages/du-lich.md`.

### 10.3 `/dia-diem/[id]` - Local Dossier

- Source/freshness nằm trên title/media.
- Một primary action theo dữ liệu; mobile tối đa ba action trực tiếp.
- Official facts tách khỏi community/AI.
- Honest placeholder, không AI facade giả ảnh thật.
- Chi tiết tại `design-system/vinhlong360/pages/entity-detail.md`.

### 10.4 `/admin` - Bàn điều phối vận hành

- Priority work đứng đầu.
- Sổ sức khỏe hệ thống thay lưới thẻ KPI.
- Navigation scope-aware, icon SVG.
- Partial failure giữ dữ liệu cũ và timestamp.
- Chi tiết tại `design-system/vinhlong360/pages/admin-dashboard.md`.

## 11. Chiến lược component

### 11.1 Component foundation

- Button, icon button, input, select, textarea, checkbox, radio, switch.
- SourceMark, StatusMark, FreshnessLine, WhyThis, DataCorrection.
- EntityRow, EntityTile, SignalItem, QueueRow, DefinitionList.
- ActionDock, BulkActionBar, FilterLedger, ContextControl.
- Sheet, dialog, popover, toast, skeleton, empty/error/stale/forbidden.

### 11.2 Ranh giới cần trích khi triển khai

- `index.vue`: bản tin địa phương, tín hiệu chính thức, gần bạn, nội dung biên tập, tóm tắt cộng đồng.
- Detail: EntityHeader, EntityActionDock, EntityFacts, TrustRail, CommunityEvidence.
- Admin: AdminNavigation, PriorityQueue, HealthLedger, ExceptionPanel.
- Catalog: AtlasHeader, FilterLedger, ResultCollection.

Mục tiêu không phải giảm dòng bằng mọi giá; mỗi component phải có một nhiệm vụ, contract rõ và state test được.

## 12. UX nâng cao bắt buộc dù UI-first

### 12.1 Personalization transparency

`WhyThis` phải nêu một hoặc nhiều lý do thật:

- Khu vực bạn đã chọn.
- Vị trí gần đúng/chính xác với consent.
- Sở thích đã chọn.
- Nội dung vừa xem/đã lưu.
- Độ phổ biến trong khu vực.

Control liên quan mở trực tiếp từ disclosure. Reset chỉ xóa tín hiệu recommendation, không xóa tài khoản hoặc saved data.

### 12.2 Location

- Không tự yêu cầu GPS khi page load.
- IP chỉ hiển thị như ước tính.
- Tắt location không làm hỏng app; fallback về khu vực profile/manual.
- Location permission copy nói lợi ích cụ thể và có `Để sau`.

### 12.3 Three-tier source

- Official có priority và push capability nhưng UI không làm community giống official.
- Verified partner có organization identity và verification details.
- Community có moderation state, report và context; không dùng seal official.

### 12.4 State integrity

- Preserve filter, scroll, draft, selection và input khi quay lại hoặc lỗi.
- Skeleton phản chiếu geometry, không spinner toàn trang mặc định.
- Partial failure theo module.
- Empty state hướng dẫn một hành động có thật.

## 13. Accessibility, performance và compatibility

- WCAG 2.2 AA bắt buộc, AAA cho body token khi khả thi.
- Focus bằng outline, hoạt động trong forced colors.
- Color không là kênh duy nhất.
- 200% text zoom, Vietnamese uppercase, screen-reader order và route focus.
- Touch 44x44px cho action chính, gap tối thiểu 8px.
- Font self-host, tối đa ba weight cần thiết; body `font-display: optional` nếu metric fallback đạt yêu cầu.
- Sáng/tối/high-contrast kiểm tra riêng.
- LCP media có kích thước; below-fold lazy; tránh hydration mismatch làm nhảy layout.
- Zalo/Facebook in-app webview dùng sRGB fallback an toàn.

## 14. Anti-AI-slop gates có thể đo

### Trong pilot mới

- 0 emoji structural.
- 0 raw hex/rgb trong component/page; chỉ token file có primitive fallback.
- 0 glass content card.
- Tối đa một editorial signature lớn trong một viewport.
- Không có page dùng công thức giống pilot khác ở top zone.
- Mỗi source-bearing item có SourceMark hoặc context nguồn tương đương.
- Ảnh AI/không xác minh có disclosure; không giả ảnh thực địa.

### Khi migrate toàn hệ thống

- Giảm gradient về các use case được cho phép: scrim, map/data continuum, skeleton.
- Giảm shadow content về zero/subtle border-first.
- Mọi icon navigation/action về một vector family.
- Raw CSS value được theo dõi bằng token validator.
- Mỗi layout family có screenshot baseline 390/1024/1440 light/dark.

## 15. Thứ tự UI-first sau khi duyệt

1. Chốt MASTER token và visual gates.
2. Foundation code: font, primitive/semantic/component token, icon family, surface/elevation.
3. Public shell và Admin shell.
4. Pilot `/` và `/admin` để xác minh hai cực utility/density.
5. Pilot `/du-lich` và detail để xác minh editorial/catalog/trust.
6. Visual QA, accessibility và state matrix.
7. Mở rộng theo 12 layout family, không theo thứ tự file route ngẫu nhiên.

## 16. Self-review

- Không còn mục bỏ trống trong phạm vi quyết định thị giác.
- Không thêm marketplace, booking, payment hoặc tính năng backend giả.
- Không thay route/API/SEO/RBAC hiện tại.
- Bốn pilot có primary goal/action, mobile composition, source/state và anti-pattern rõ.
- MASTER dùng OKLCH nhưng có sRGB fallback đúng cho old webview.
- Cinematic/editorial không bị xóa; nó được giới hạn vào discovery nơi có giá trị.

## 17. Decision gate

Cần duyệt ba quyết định trước implementation plan:

1. Chấp nhận **Mekong Signal Atlas** là visual direction cuối.
2. Chấp nhận homepage **Bảng tin địa phương thích ứng**, không tiếp tục hero du lịch cỡ lớn ở vùng nhìn đầu.
3. Chấp nhận thay dashboard thẻ KPI của Admin bằng **Bàn điều phối vận hành** ưu tiên công việc.

Sau khi duyệt, bước tiếp theo là lập implementation plan chi tiết theo P0 Foundation/Shell và P1 bốn pilot; chưa mở rộng 68 page ngay.
