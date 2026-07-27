# Hệ thống thiết kế vinhlong360

> **Trạng thái:** `draft-for-review` - bản tổng hợp bespoke ngày 2026-07-27.
> **Phạm vi:** toàn bộ public, tài khoản riêng tư và AdminCP.
> **Quy tắc kế thừa:** khi thiết kế một trang, đọc file này trước rồi đọc `pages/<page>.md`. Quy tắc trong file trang chỉ được ghi đè khi có nêu rõ lý do.

## 1. Định hướng

**Tên hệ:** Mekong Signal Atlas - Civic Cartographic Modernism.

**Luận đề:** vinhlong360 không chỉ trưng bày miền Tây. Hệ thống giúp một người hiểu địa bàn của mình, nhận biết điều đáng chú ý và thực hiện hành động phù hợp trong thời gian ngắn nhất.

Ngôn ngữ thị giác gồm ba lớp có ranh giới rõ:

1. **Thông tin địa phương thích ứng:** cảnh báo, thời tiết, giao thông, sự kiện, dịch vụ và nội dung gần người dùng.
2. **Khám phá biên tập:** câu chuyện địa phương, điểm đến, ẩm thực, văn hóa và hành trình.
3. **Vận hành công ích:** danh bạ, nguồn dữ liệu, kiểm duyệt, AdminCP và các công việc mật độ cao.

Không dùng một preset chung cho cả ba lớp. Chúng dùng chung token, typography, icon và chữ ký bản đồ nhưng khác nhịp, mật độ và cấu trúc.

## 2. Chữ ký hệ thống: Dòng địa bàn

`Dòng địa bàn` là một đường bản đồ mảnh có nút dữ liệu. Nó phải biểu đạt thông tin thật, không phải đường trang trí:

- Trang chủ: khu vực hiện tại -> cảnh báo -> sự kiện -> dịch vụ gần đây.
- Catalog: khu vực -> loại trải nghiệm -> mùa/thời gian.
- Trang chi tiết: nguồn -> lần cập nhật -> vị trí -> hành động.
- Lịch trình: thứ tự điểm dừng và chặng di chuyển.
- AdminCP: hàng đợi -> trạng thái -> người phụ trách -> hành động tiếp theo.

Quy tắc:

- Dùng SVG stroke hoặc border/path, không dùng gradient cầu vồng.
- Một màn hình chỉ có một Dòng địa bàn chính.
- Nút đang hoạt động dùng màu đất nung; đường dùng màu sông; trạng thái phải có icon và chữ.
- Không chèn đường này vào card chỉ để tạo phong cách.

## 3. Kiến trúc token

```text
Primitive tokens
        -> Semantic tokens
        -> Component tokens
```

- Primitive chứa giá trị màu, kích thước, thời lượng và kiểu chữ.
- Semantic mô tả mục đích: canvas, surface, action, trust, status, text.
- Component chỉ tham chiếu semantic token; page không đặt màu/radius/shadow tùy ý.
- Trình duyệt cũ và webview Zalo dùng sRGB fallback ở `:root`; OKLCH chỉ ghi đè bên trong `@supports (color: oklch(0% 0 0))`.

## 4. Màu sắc

### 4.1 Primitive sáng

| Token | OKLCH | sRGB fallback | Vai trò |
|---|---|---|---|
| `--alluvial-paper` | `oklch(97.5% 0.008 90)` | `#F9F7F1` | Canvas hơi ấm, không vàng kem |
| `--surface-white` | `oklch(99% 0.004 90)` | `#FDFCF9` | Surface chính |
| `--mekong-ink` | `oklch(20% 0.025 180)` | `#081A16` | Chữ chính, không dùng đen tuyệt đối |
| `--mekong-muted` | `oklch(43% 0.025 180)` | `#415450` | Chữ phụ, đạt khoảng 7.5:1 trên canvas |
| `--river-600` | `oklch(43% 0.075 215)` | `#035A69` | Hành động chính, link, focus |
| `--river-700` | `oklch(35% 0.06 215)` | `#00434E` | Hover/active |
| `--mangthit-600` | `oklch(48% 0.12 35)` | `#95402B` | Brand, nút hiện tại, editorial accent |
| `--mangthit-700` | `oklch(39% 0.105 35)` | `#722B1A` | Brand đậm |
| `--orchard-600` | `oklch(43% 0.09 150)` | `#255D34` | Tín hiệu tích cực/đã xác minh |
| `--harvest-600` | `oklch(62% 0.12 75)` | `#B07A20` | Cảnh báo vừa, sự kiện sắp tới |
| `--coral-error` | `oklch(55% 0.16 25)` | `#BD413F` | Lỗi/nguy hiểm, không dùng đỏ gắt |
| `--alluvial-line` | `oklch(88% 0.015 90)` | `#DBD7CD` | Border/divider |

### 4.2 Primitive tối

| Token | OKLCH | sRGB fallback |
|---|---|---|
| `--night-canvas` | `oklch(17% 0.018 180)` | `#071210` |
| `--night-surface` | `oklch(22% 0.018 180)` | `#111D1B` |
| `--night-raised` | `oklch(27% 0.018 180)` | `#1D2927` |
| `--night-text` | `oklch(94% 0.008 90)` | `#EDEBE5` |
| `--night-muted` | `oklch(75% 0.015 180)` | `#A4B1AE` |
| `--night-river` | `oklch(72% 0.055 215)` | `#7DAEBA` |
| `--night-clay` | `oklch(68% 0.085 35)` | `#C78575` |
| `--night-leaf` | `oklch(68% 0.065 150)` | `#7CA483` |
| `--night-amber` | `oklch(75% 0.085 75)` | `#CEA770` |
| `--night-error` | `oklch(70% 0.12 25)` | `#DF7F78` |

Dark mode được thiết kế riêng, giảm chroma và tăng tương phản; không đảo màu light mode.

### 4.3 Semantic màu

```css
--color-canvas
--color-surface
--color-surface-subtle
--color-surface-raised
--color-text
--color-text-muted
--color-border
--color-action
--color-action-hover
--color-brand
--color-focus
--color-success
--color-warning
--color-error
--color-source-official
--color-source-verified
--color-source-community
```

Màu nguồn không đứng một mình:

- **Chính thức:** biểu tượng khiên + chữ `Chính thức` + màu sông.
- **Đã xác minh:** biểu tượng dấu xác nhận + chữ `Đã xác minh` + màu đất nung.
- **Cộng đồng:** biểu tượng người dùng + chữ `Cộng đồng` + neutral/leaf.

## 5. Typography

### 5.1 Họ chữ

- **UI/body:** `Be Vietnam Pro`, self-host, weight 400/500/600. Dùng cho navigation, form, card, bảng, body và AdminCP.
- **Editorial display:** giữ `Fraunces` nhưng giới hạn ở feature title, pull quote và tên địa danh có tính kể chuyện. Không dùng cho mọi H2.
- **Data/ID:** `ui-monospace` cho ID, log và mã; số liệu dùng `font-variant-numeric: tabular-nums` để tránh thêm font tải xuống.

Lý do giữ Fraunces: dự án đã có subset tiếng Việt và hình ảnh địa phương phù hợp. Để tránh công thức AI phổ biến “nền kem + serif + terracotta”, Fraunces không đi cùng nền kem/gradient mặc định và không chiếm UI chức năng.

### 5.2 Vai trò chữ

| Vai trò | Kích thước | Weight | Line-height | Họ chữ |
|---|---|---|---|---|
| Display editorial | `clamp(2.5rem, 5vw, 4.5rem)` | 600 | 1.12 trở lên | Fraunces |
| Page title | `clamp(2rem, 3vw, 3rem)` | 600 | 1.2 | Be Vietnam Pro |
| Section title | `clamp(1.375rem, 2vw, 2rem)` | 600 | 1.3 | Be Vietnam Pro |
| Card/item title | `1rem-1.25rem` | 600 | 1.35 | Be Vietnam Pro |
| Body | `1rem-1.125rem` | 400 | 1.6 | Be Vietnam Pro |
| Label | `0.8125rem-0.875rem` | 500 | 1.4 | Be Vietnam Pro |
| Data/metric | `1rem-2rem` | 600 | 1.2 | Be Vietnam Pro, tabular |

Phải test chuỗi `Ệ ộ Ẵ ữ Ề Ậ` ở 200% zoom. Không đặt line-height display dưới 1.1.

## 6. Grid, spacing và mật độ

- Spacing base 4px; nhịp dùng 8/12/16/24/32/48/64.
- Public canvas: 12 cột desktop, 8 cột tablet, 4 cột mobile.
- Gutter: 16px mobile, 24px tablet, 32px desktop, tối đa 40px ở màn hình lớn.
- Content max-width: 1280px cho canvas; 65ch cho nội dung dài.
- Component responsive bằng container query; breakpoint viewport chỉ dùng cho shell/page grid.
- Mật độ mặc định public: 6/10; personal workspace: 7/10; AdminCP: 8/10.

## 7. Radius, border và elevation

| Token | Giá trị | Dùng cho |
|---|---:|---|
| `--radius-control` | 8px | input, button, segmented control |
| `--radius-surface` | 12px | surface có ranh giới thật |
| `--radius-sheet` | 20px | sheet/dialog mobile |
| `--radius-pill` | 999px | filter chip, status; không dùng cho card |

- Content ưu tiên border/divider; card mặc định không có shadow.
- Shadow chỉ dùng cho dropdown, popover, sticky action dock, dialog và drag state.
- Không hover mọi card bằng `translateY`; item list chỉ đổi border/background.
- Glass chỉ dùng cho sticky header, mobile bottom bar, map controls, popover. Content surface luôn opaque.

## 8. Biểu tượng và hình ảnh

### 8.1 Biểu tượng

- Mở rộng `IconLine` thành một family đầy đủ, stroke 1.75, round cap/join.
- Size token: 16/20/24/32px; hit area tối thiểu 44x44px cho action chính.
- Không dùng emoji hoặc HTML numeric entity làm navigation, trạng thái, CTA, empty state hay AdminCP.
- Filled icon chỉ dùng cho trạng thái đang chọn; cùng một cấp không trộn filled và outline.

### 8.2 Nhiếp ảnh

Tỷ lệ định hướng:

- 60% ảnh tư liệu hữu ích: mặt tiền, biển hiệu, lối vào, không gian thật, dịch vụ và con người trong bối cảnh.
- 25% chân dung địa điểm: góc rộng, ánh sáng tự nhiên, màu trung thực.
- 15% ảnh editorial: bình minh/hoàng hôn hoặc khoảnh khắc đặc biệt.

Không để toàn hệ thống chỉ có ảnh vàng giờ hoàng kim. Ảnh AI tạo phải có disclosure, không đại diện cho cơ quan, cơ sở y tế, hành chính, giao thông hoặc tình trạng thực tế.

## 9. Motion

```text
instant feedback: 80-120ms
micro interaction: 150-220ms
panel/sheet: 220-320ms
ambient editorial: tối đa 600ms cho reveal; không chặn thao tác
```

- Chỉ animate transform/opacity.
- Một view tối đa 1-2 chuyển động nổi bật.
- Không dùng route-transition overlay toàn màn hình.
- Ken Burns chỉ được dùng cho một editorial feature có ảnh thật; không dùng làm nhịp mặc định.
- `prefers-reduced-motion` phải loại bỏ parallax, stagger và ambient motion.

## 10. Quy ước component

### 10.1 Đối tượng nội dung

Không mặc định mọi object là card. Chọn anatomy theo hành vi:

- `EntityRow`: quét nhanh, danh bạ, tìm kiếm, saved.
- `EntityTile`: object có ảnh và có thể mang đi qua catalog.
- `StoryFeature`: một nội dung editorial nổi bật, tối đa một lần trong một viewport.
- `SignalItem`: cảnh báo, thời tiết, sự kiện, traffic, nguồn rõ.
- `QueueRow`: công việc AdminCP với trạng thái, SLA, owner, next action.

### 10.2 Action

- Mỗi màn hình có một primary action rõ.
- Detail local service: ưu tiên `Chỉ đường` nếu có tọa độ, nếu không có thì `Gọi`; Zalo và lưu là secondary.
- Destructive action tách khỏi navigation/action thường và cần confirm/undo khi phù hợp.
- Button loading giữ nguyên chiều rộng và thông báo bằng `aria-busy`.

### 10.3 Trust

- `SourceMark`: Chính thức / Đã xác minh / Cộng đồng.
- `FreshnessLine`: cập nhật lúc nào, stale hay chưa.
- `WhyThis`: giải thích gợi ý và mở control khu vực/sở thích/vị trí.
- `DataCorrection`: báo sai/bổ sung nguồn, chỉ một affordance chính trên mỗi trang.

## 11. Shell thích ứng

### Desktop public

- Hàng 1: brand, universal search, context location, notification, user.
- Hàng 2 hoặc rail ngắn: Trang chủ, Khám phá, Gần bạn, Cộng đồng, Lịch trình.
- Nhóm danh mục sâu mở bằng mega panel có phân vùng, không tạo hàng nav dài.

### Mobile public

- Top: context location + search trigger + alert status.
- Bottom nav tối đa 5: Trang chủ, Khám phá, Gần bạn, Cộng đồng, Cá nhân.
- Search, filter và map list dùng full-screen sheet/bottom sheet; không nhét desktop dropdown vào mobile.

### AdminCP

- Sidebar theo scope và nhóm công việc, dùng icon SVG + label.
- Trang hiện tại, queue count và quyền bị giới hạn phải hiển thị rõ.
- Mobile AdminCP là task list/queue trước; bảng rộng dùng horizontal scroll có sticky cột chính hoặc chuyển thành row detail, không biến sidebar thành dải chip dài.

## 12. Quy tắc chống giao diện AI đại trà

1. Không dùng hero ảnh lớn cho mọi page.
2. Không dùng công thức `hero -> 3 cards -> stats -> CTA` nếu nội dung không có cấu trúc đó.
3. Không dùng emoji làm structural icon.
4. Không dùng gradient để tạo “cảm giác premium”; gradient chỉ dành cho scrim, bản đồ mật độ, dữ liệu liên tục và skeleton.
5. Không dùng glass trên content.
6. Không dùng card bo tròn cho nội dung có thể trình bày bằng row, list, table hoặc definition list.
7. Không tạo số liệu, lượt xem, review, scarcity hoặc social proof giả.
8. Không dùng cùng một motion reveal cho mọi section.
9. Không viết copy chung chung như “Khám phá điều tuyệt vời”; copy phải gọi đúng địa bàn, nguồn và hành động.
10. Mỗi layout family có một composition riêng nhưng dùng chung token và component contract.

## 13. Đặc tả bổ sung hiện có

- `pages/home.md`
- `pages/du-lich.md`
- `pages/entity-detail.md`
- `pages/admin-dashboard.md`

## 14. Cổng nghiệm thu

- Không còn raw color/radius/shadow trong component mới.
- Contrast body mục tiêu 7:1; UI tối thiểu 3:1; kiểm tra cả light/dark.
- Không emoji structural trong pilot.
- Tất cả action chính có hit area 44x44px, focus outline và disabled/loading state.
- 375px, 768px, 1024px, 1440px; text zoom 200%; landscape mobile.
- Forced colors, `prefers-contrast: more`, reduced motion và slow network có state riêng.
- Pilot không thay route, API, SEO policy, auth hoặc RBAC ngoài đặc tả đã duyệt.
