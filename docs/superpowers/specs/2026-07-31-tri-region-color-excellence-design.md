# Tri-Region Color Excellence System cho Plan B

> STATUS (2026-07-31): active — approved design, pending written-spec review.
> **Ngày chốt:** 2026-07-31
> **Phạm vi triển khai đầu tiên:** Homepage, Discovery/Search và Entity Detail
> **Hệ cha:** Adaptive Nocturne Heritage
> **Nguồn thị giác:** Existing Stitch Screen Evolution

## 1. Mục tiêu

Hoàn thiện hệ màu cho Vĩnh Long mới, bao gồm ba vùng cũ Vĩnh Long, Bến Tre và
Trà Vinh, theo hướng:

- giữ bản sắc địa phương dựa trên sông nước, phù sa, vật liệu, nghề thủ công và
  ánh sáng thật;
- bảo toàn tinh thần thị giác của các screen Stitch nhưng không sao chép raw
  hex hoặc tạo palette riêng theo từng trang;
- tách màu thương hiệu khỏi action, trust, status, severity, category, bản đồ
  và dữ liệu;
- duy trì một hệ semantic duy nhất cho Nocturne và Daylight Parchment;
- đạt accessibility, độ ổn định production và khả năng mở rộng toàn hệ thống.

Đặc tả này mở rộng, không thay thế, các quyết định trong:

- `docs/superpowers/specs/2026-07-31-nocturne-heritage-adaptive-public-design.md`;
- `design-system/vinhlong360/MASTER.md`;
- `design-system/vinhlong360/pages/home.md`;
- `design-system/vinhlong360/pages/du-lich.md`;
- `design-system/vinhlong360/pages/entity-detail.md`;
- `design-system/vinhlong360/concepts/hybrid-editorial/`.

Nếu có xung đột, đặc tả Adaptive Nocturne Heritage tiếp tục là authority cho
kiến trúc public tổng thể; file này là authority cho màu Plan B trên ba nhóm
trang trong phạm vi.

## 2. Bối cảnh và vấn đề cần giải quyết

Palette production cũ đã có nền tảng Tây Nam Bộ gồm clay, amber, leaf, river,
sand và ink. Nghiên cứu trước đây cũng đã gắn nhận diện với sông, bản đồ, gạch
Mang Thít, vườn cây và phù sa. Tuy nhiên:

- Vĩnh Long được biểu đạt rõ hơn Bến Tre và Trà Vinh;
- một số họ màu đang mang nhiều nghĩa nghiệp vụ;
- primary action cũ còn phụ thuộc Clay trong khi hệ mới đã chốt River cho
  interaction;
- raw hex, alias cũ và màu legacy vẫn tồn tại trong production;
- bản online chưa phản ánh đầy đủ token Nocturne Heritage mới nhất;
- ảnh, category, trust, warning và map chưa có ranh giới màu đủ chặt;
- việc thêm màu theo từng screen có nguy cơ tạo drift và cảm giác giao diện do
  AI tạo hàng loạt.

Đặc tả này giải quyết các khoảng trống đó mà không tạo ba theme tỉnh, không tạo
palette runtime và không tự đổi giao diện theo vị trí hoặc thời gian.

## 3. Quyết định tổng thể

Hướng được chọn là:

> **Tri-Region Color Excellence System**, theo mô hình **B+**: nền màu thống
> nhất cho toàn vùng, phổ vật liệu địa phương có kiểm soát và contextual accent
> chỉ được kích hoạt qua mapping đã duyệt.

Kiến trúc gồm năm tầng:

```text
Shared Mekong Foundation
        -> Local Material Spectrum
        -> Functional Semantic Colors
        -> Nocturne / Parchment Transformation
        -> Component and Page Recipes
```

Stitch cung cấp atmosphere, visual temperature, accent balance, image/surface
relationship và chromatic rhythm. Plan A cung cấp primitive, semantic meaning,
theme behavior, accessibility và production governance. Component chỉ dùng
semantic hoặc component token.

## 4. Visual Coherence Contract

Các bất biến:

- một hệ thống thị giác gốc;
- hai material mode, không phải hai website;
- một accent biểu cảm chính trong mỗi viewport;
- mỗi semantic token có một nhiệm vụ rõ;
- Parchment chỉ xuất hiện khi cải thiện việc đọc hoặc ra quyết định;
- serif chỉ xuất hiện ở điểm biên tập đã cho phép;
- hình ảnh không bị ép về cùng một thời điểm hoặc một lớp tint;
- các page family dùng chung DNA nhưng không dùng chung một template;
- màu không bao giờ là kênh duy nhất truyền trust, status hoặc severity;
- bản sắc vẫn phải nhận ra được khi chuyển sang grayscale.

Các ngôn ngữ thiết kế được xếp theo hierarchy:

```text
Adaptive Nocturne System
        -> Nocturne Heritage / Daylight Parchment
        -> Mekong Ink & Clay / Tri-Region Material Spectrum
        -> Framed Dossier / Dòng địa bàn
        -> Controlled Serif
        -> Grounded Local Light / Material Still Life / Campaign Capsule
```

Existing Stitch Screen Evolution là nguồn thị giác, không phải một ngôn ngữ
thiết kế đứng ngang hàng và không phải production token authority.

## 5. Regional Color Authority

### 5.1 Shared Mekong Foundation

Lớp nền chung của toàn Vĩnh Long mới:

| Family | Vai trò |
|---|---|
| Mekong Ink | Chữ, canvas Nocturne và chiều sâu |
| Alluvial Paper | Canvas sáng gần trung tính |
| Alluvial Parchment | Reading plate, evidence và dossier inset |
| River Teal | Kết nối địa bàn và action |
| Orchard Neutral | Hệ sinh thái và tín hiệu tích cực có kiểm soát |
| Aged Brass | Focus Nocturne, dateline và accent hiếm |

Ba vùng luôn chia sẻ foundation này. Không trang nào được trở thành một thương
hiệu tỉnh độc lập.

### 5.2 Local Material Spectrum

| Family | Nguồn cảm hứng | Trạng thái sử dụng |
|---|---|---|
| Mang Thít Clay | Gốm, gạch, lò nung, đất đỏ Vĩnh Long | Được phép dùng trong production |
| Coconut Leaf | Vườn dừa, sinh thái, nông nghiệp Bến Tre | Chỉ dùng qua Orchard hiện có cho đến khi evidence set được duyệt |
| Coir Umber | Xơ dừa, gỗ, đất và thủ công Bến Tre | Chưa tạo primitive production mới trong phạm vi Plan B |
| Khmer Ochre | Kiến trúc, thủ công và bề mặt địa phương Trà Vinh | Chưa tạo primitive production mới trong phạm vi Plan B |
| Aged Brass | Chi tiết kiến trúc, ánh sáng và chất liệu ấm toàn vùng | Dùng như shared accent, không gán độc quyền cho Trà Vinh |
| Harvest Amber | Mùa vụ, nông sản và ánh sáng | Dùng chung toàn vùng |

Các family chưa được phép tạo primitive mới phải được nghiên cứu bằng Regional
Color Evidence Book trước khi đưa vào production. Việc chưa tạo token là quyết
định phạm vi, không phải placeholder.

### 5.3 Không dùng mô hình một tỉnh một màu

Không quy định Vĩnh Long bằng đỏ, Bến Tre bằng xanh và Trà Vinh bằng vàng.
Accent được chọn theo vật liệu hoặc loại nội dung đã xác minh, không theo vị trí
người dùng và không theo tên tỉnh đơn thuần.

### 5.4 Quyền ưu tiên

```text
Accessibility
    > Danger / Warning
    > Interaction state
    > Trust / provenance
    > Category
    > Local material accent
    > Editorial decoration
```

Nếu không có mapping đủ tin cậy, component fallback về River, Ink hoặc neutral
surface. Không suy màu từ mô tả cộng đồng, IP, GPS hoặc ảnh.

## 6. Primitive và perceptual color

Các pigment anchor kế thừa từ Adaptive Nocturne Heritage:

| Anchor | Giá trị định hướng | Vai trò vật liệu |
|---|---:|---|
| Night Ink | `#07110F` | Canvas Nocturne |
| Raised Ink | `#10211E` | Surface Nocturne |
| River Teal | `#4C817D` | Sông sâu và context |
| Mang Thít Clay | `#A14D34` | Brand và editorial accent |
| Aged Brass | `#C79A57` | Focus và dateline |
| Alluvial Parchment | `#E4D7BD` | Reading material |
| Parchment Ink | `#14201D` | Chữ trên reading material |

Các giá trị trên là visual anchor, không phải quyền cho component hardcode.
Giá trị production cuối phải:

- được cân bằng bằng OKLCH;
- có khoảng sáu đến bảy cấp khi có use case thực;
- giảm chroma và điều chỉnh lightness riêng cho Nocturne;
- có sRGB fallback cho webview cũ;
- được kiểm tra theo foreground/background pair;
- không tạo thêm cấp màu chỉ để hoàn chỉnh thang lý thuyết.

## 7. Semantic Color Mapping

### 7.1 Foundation semantics

Foundation không mang ý nghĩa địa phương hoặc nghiệp vụ:

- `canvas`;
- `surface`;
- `surface-subtle`;
- `surface-raised`;
- `reading-plate`;
- `text`;
- `text-muted`;
- `border`.

### 7.2 Brand và editorial

| Role | Family |
|---|---|
| Brand primary | Mang Thít Clay |
| Brand support | Aged Brass |
| Regional accent | Material accent được mapping và duyệt |
| Current context | Clay marker hoặc Clay hairline |
| Editorial ornament | Clay hoặc Brass chroma thấp |

Clay không còn là màu mặc định của tất cả button. Clay nói về brand, chapter,
context đang xem hoặc editorial signature.

### 7.3 Action và interaction

| Role | Mapping |
|---|---|
| Primary action | River |
| Primary hover/pressed | River có lightness phù hợp với theme |
| Secondary action | Neutral surface với River text/border |
| Selected item | Clay marker cộng cấu trúc selected |
| Destructive action | Coral |
| Focus Nocturne | Aged Brass tương phản cao |
| Focus Parchment | River đậm hoặc Brass đã kiểm tra |

Quy tắc ngắn:

> River nói `có thể làm`; Clay nói `đây là bản sắc hoặc ngữ cảnh hiện tại`.

### 7.4 Trust và provenance

| Tier | Biểu đạt bắt buộc |
|---|---|
| Chính thức | Civic River + shield + chữ `Chính thức` |
| Đã xác minh | Orchard + check + chữ `Đã xác minh` |
| Cộng đồng | Neutral/Leaf-muted + user icon + chữ `Cộng đồng` |
| Nội dung AI | Neutral border + disclosure nhìn thấy được |
| Cũ/chưa cập nhật | Amber-muted + clock + thời điểm |
| Chưa rõ nguồn | Neutral-muted + nhãn giải thích |

Nội dung AI không dùng Brass hoặc Gold làm provenance color để tránh cảm giác
được chứng nhận. Trust tier mô tả nguồn, không mô tả severity.

### 7.5 Status và severity

| State | Family |
|---|---|
| Information | River semantic |
| Success | Orchard semantic |
| Warning | Harvest Amber semantic |
| Error | Coral semantic |
| Critical danger | Coral đậm hoặc danger surface riêng |
| Offline/unknown | Neutral |
| Pending | Amber-muted hoặc neutral progress |

Một cảnh báo chính thức phải tách SourceMark, severity panel và action. Không
nhồi source, severity và CTA vào cùng một badge màu.

### 7.6 Category và contextual data

| Context | Accent phụ trợ |
|---|---|
| Làng nghề, gốm, thủ công | Clay |
| Thiên nhiên, vườn, nông nghiệp | Leaf |
| Sông nước, di chuyển, lưu trú ven sông | River |
| Ẩm thực, mùa vụ, sự kiện | Amber |
| Hành chính, danh bạ, dữ liệu | Ink/River neutral |

Category color không thay đổi action, trust hoặc status của entity.

## 8. Bản đồ và dữ liệu

Map và data visualization dùng namespace riêng.

### 8.1 Bản đồ

- mặt nước dùng River low-chroma;
- route đang chọn dùng Clay hoặc Brass, không trùng mặt nước;
- ranh giới dùng Ink-muted;
- traffic dùng Green, Amber và Coral theo severity;
- cluster dùng neutral surface, số và category marker;
- vùng địa lý dùng color cộng pattern và label;
- vị trí hoặc tỉnh không bao giờ chỉ được phân biệt bằng màu.

### 8.2 Biểu đồ

Tách riêng:

- categorical palette;
- sequential palette;
- diverging palette;
- status palette.

Không lấy trực tiếp brand-primary hoặc warning để tạo series. Mọi legend phải
có label, và series phải giữ được phân biệt qua color-vision simulation.

## 9. Nocturne và Daylight Parchment

### 9.1 Bất biến theme

Khi đổi theme:

- Action vẫn là River;
- Brand vẫn là Clay;
- Verified vẫn là Orchard;
- Warning vẫn là Amber;
- Danger vẫn là Coral;
- trust tier giữ icon và label;
- layout, geometry, order và semantic meaning không đổi.

### 9.2 Transformation matrix

| Role | Nocturne | Daylight Parchment |
|---|---|---|
| Canvas | Night Ink | Alluvial Paper gần trung tính |
| Surface | Raised Ink | Surface White hơi ấm |
| Surface subtle | Ink sáng hơn canvas một cấp | Paper tối hơn canvas một cấp |
| Reading plate | Parchment có kiểm soát | Parchment nhạt hoặc Surface White |
| Text | Off-white | Mekong Ink |
| Muted text | Xám xanh sáng | Ink-muted |
| Action | Night River | River đậm |
| Brand | Night Clay giảm chroma | Mang Thít Clay |
| Focus | Aged Brass sáng | River đậm hoặc Brass đủ contrast |
| Border | Text pha trong suốt có kiểm soát | Alluvial Line |
| Danger | Night Coral | Coral đậm |

Dark mode được thiết kế riêng, không đảo light mode.

### 9.3 Parchment boundary

Parchment không đồng nghĩa phủ kem toàn trang. Trong Nocturne, Parchment chỉ
dùng ở reading, facts, evidence, form phức tạp hoặc decision panel. Trong
Daylight Parchment, canvas vẫn gần trung tính; màu parchment đậm hơn chỉ là
inset hoặc reading plate.

### 9.4 Preference

- Nocturne là mặc định;
- người dùng chủ động chọn `Nền sáng dễ đọc`;
- không tự đổi theo giờ, IP, GPS, mùa hoặc loại người dùng;
- guest vẫn được lưu lựa chọn;
- signed-in có thể đồng bộ preference nhưng không phụ thuộc location consent;
- theme được áp dụng trước render để tránh flash;
- chuyển theme không gây layout shift;
- transition phải tắt khi `prefers-reduced-motion`.

## 10. Contrast và accessibility

### 10.1 Contrast gates

| Nội dung | Cổng phát hành |
|---|---|
| Body text | Mục tiêu 7:1, không thấp hơn 4.5:1 |
| Small text hoặc metadata quan trọng | Tối thiểu 4.5:1 |
| Large display text | Tối thiểu 3:1, ưu tiên 4.5:1 |
| Icon và control | Tối thiểu 3:1 với nền |
| Border truyền cấu trúc | Tối thiểu 3:1 khi cần nhận biết |
| Focus indicator | Tối thiểu 3:1 với các màu liền kề |
| Text trên ảnh | Chỉ dùng khi scrim hoặc plate đạt contrast |
| Form placeholder | Phải đọc được, không dùng opacity quá thấp |

WCAG 2.2 AA là release gate. APCA chỉ là tín hiệu tham khảo bổ sung.

### 10.2 Test bắt buộc

- protanopia;
- deuteranopia;
- tritanopia;
- grayscale;
- forced colors;
- `prefers-contrast`;
- màn hình ngoài trời;
- OLED độ sáng thấp;
- thiết bị hoặc webview chỉ hỗ trợ sRGB;
- zoom 200%;
- chuỗi tiếng Việt nhiều dấu.

### 10.3 Release matrix

```text
Nocturne
x Parchment
x Desktop
x Mobile
x Normal contrast
x High contrast
x Default
x Hover
x Focus
x Selected
x Disabled
x Error
```

Homepage, Discovery và Detail phải có visual regression riêng cho hai theme.

## 11. Image Color Management

Ảnh không điều khiển semantic UI:

- không lấy dominant color từ ảnh để đổi nền, button hoặc navigation;
- không phủ tint Clay, River hoặc Amber lên toàn bộ ảnh;
- scrim chỉ dùng Ink hoặc black trung tính;
- giữ cân bằng trắng tự nhiên;
- text trên ảnh dùng scrim, plate hoặc chuyển ra ngoài media;
- frame, caption, credit và disclosure dùng semantic token cố định;
- ảnh cộng đồng và đối tác nằm trong neutral frame;
- ảnh AI luôn có disclosure và không dùng provenance color gợi chứng nhận;
- cùng một media phải hoạt động trong Nocturne và Parchment.

Grounded Local Light cho phép sáng sớm, trời nhiều mây, ánh sáng trong nhà,
chạng vạng và ánh sáng lao động thực tế. Không ép toàn bộ media về golden hour.

## 12. Chromatic Rhythm và page recipes

Tỷ lệ Nocturne/Parchment tiếp tục kế thừa tonal architecture của hệ cha và chỉ
là định hướng mật độ. Accent budget dưới đây là diện tích màu có chroma mạnh,
không phải tỷ lệ surface tối/sáng.

### 12.1 Homepage

- nơi biểu đạt Nocturne Heritage và material palette phong phú nhất;
- Search và action dùng River;
- mỗi viewport chỉ có một material accent nổi bật;
- Clay dành cho chapter hoặc editorial signature;
- Brass dành cho dateline, focus hoặc điểm nhấn hiếm;
- accent mạnh khoảng 8-10%.

### 12.2 Discovery/Search

- River dẫn interaction, filter và navigation;
- result chủ yếu dùng Ink, Parchment và border;
- category color chỉ ở hairline, icon, marker hoặc metadata;
- không tạo mỗi card một màu nền;
- accent mạnh khoảng 4-6%.

### 12.3 Entity Detail

- trust, freshness và action đứng trước decoration;
- River dẫn primary action;
- Clay có thể nhận diện câu chuyện hoặc vật liệu entity;
- Parchment dành cho facts, evidence và reading;
- Community dùng surface riêng, không mượn màu Official;
- accent mạnh khoảng 6-8%.

### 12.4 Accent debt

Muốn thêm một accent mới phải loại bỏ hoặc hạ cấp một accent hiện có. Không
dùng đồng thời Clay, River, Leaf và Amber với cường độ cao trong một viewport.

## 13. Regional Accent Resolver

```text
Verified content type or material
        -> Approved regional mapping
        -> Theme-compatible material token
        -> Contrast-safe component token
```

Resolver:

- không dùng IP, GPS hoặc profile location để đổi màu;
- không dùng mô tả tự do của cộng đồng;
- không lấy màu từ ảnh;
- không thay đổi action, trust hoặc severity;
- fallback về River hoặc Ink khi dữ liệu không đủ chắc chắn.

Plan B không cần runtime color engine. Mapping tĩnh, có type rõ và được kiểm
soát là đủ.

## 14. Campaign Capsule

Campaign đặc biệt được phép có màu phụ nếu:

- có namespace token riêng;
- có ngày bắt đầu và kết thúc;
- chỉ thêm tối đa một accent;
- không ghi đè status, trust, danger hoặc focus;
- không đưa màu campaign vào component dùng chung;
- trở về palette nền khi campaign kết thúc;
- Blue-hour Cinema có lý do biên tập rõ.

## 15. Color Governance

Nguồn thẩm quyền:

```text
Design specification
    -> MASTER design authority
    -> Primitive tokens
    -> Semantic tokens
    -> Component tokens
    -> Page recipes
```

Quy tắc:

- page và component không dùng raw hex;
- chỉ file primitive token được chứa sRGB fallback hoặc OKLCH value;
- không đọc primitive trực tiếp nếu đã có semantic token;
- màu mới phải có vai trò, theme pair và contrast evidence;
- token không dùng được deprecated trước khi xóa;
- map/chart library phải đi qua adapter token;
- không tạo JavaScript palette generator nếu CSS token đáp ứng được;
- mọi thay đổi palette phải có changelog và visual evidence.

## 16. Regional Color Evidence Book

Evidence Book là điều kiện để cấp quyền cho material family mới. Mỗi entry phải
có:

- nguồn ảnh hoặc quan sát hợp lệ;
- địa bàn và vật liệu cụ thể;
- điều kiện ánh sáng;
- màu đo hoặc swatch tham khảo;
- ý nghĩa sử dụng, không suy diễn văn hóa quá mức;
- use case được phép;
- use case bị cấm;
- reviewer xác nhận.

Evidence Book không dùng ảnh mạng không rõ nguồn và không biến màu biểu tượng
tôn giáo hoặc cộng đồng thành decoration tùy tiện.

## 17. Migration khỏi palette cũ

Thứ tự triển khai dự kiến:

1. kiểm kê raw hex, alias cũ và consumer;
2. lập mapping từ màu hiện tại sang semantic role mới;
3. giữ compatibility alias có thời hạn;
4. chuyển Homepage, Discovery và Detail;
5. kiểm tra Nocturne và Parchment;
6. chuyển map/chart adapter liên quan;
7. loại bỏ alias khi không còn consumer;
8. không thay toàn site trong một lần nếu chưa có visual regression.

Primary Clay cũ được chuyển về Brand. Primary action được chuyển sang River.
Migration không được làm thay đổi trust hoặc severity meaning.

## 18. Failure và fallback behavior

- browser không hỗ trợ OKLCH dùng sRGB fallback;
- accent mapping không tồn tại dùng River hoặc neutral;
- media quá phức tạp dùng text plate hoặc chuyển text ra ngoài;
- theme preference lỗi đọc dùng Nocturne mặc định;
- contrast pair không đạt dùng approved fallback pair, không giảm font hoặc thêm
  shadow để lách kiểm tra;
- map style không tải được vẫn giữ label và shape có thể hiểu;
- forced colors bỏ decoration nhưng giữ structure, label và action.

## 19. Quality gates

Mỗi thay đổi màu trong phạm vi Plan B phải qua:

- raw-hex scan;
- contrast audit;
- screenshot Nocturne và Parchment;
- desktop và mobile;
- default, hover, focus, selected, disabled và error;
- color-vision simulation;
- grayscale test;
- forced-colors smoke test;
- visual regression Homepage, Discovery và Detail;
- ảnh sáng nhất, tối nhất và ảnh nhiều chi tiết;
- kiểm tra không có status hoặc trust chỉ truyền bằng màu.

## 20. Success metrics

Hệ màu được đánh giá qua:

- thời gian tìm thấy primary action;
- tỷ lệ nhấn nhầm action;
- khả năng phân biệt Official, Verified và Community;
- khả năng hiểu đúng Warning và Danger;
- độ đọc ngoài trời và trên thiết bị phổ thông;
- visual fatigue trên trang dài;
- khả năng nhận diện thương hiệu trong grayscale;
- số raw hex và legacy alias giảm theo từng wave;
- không tăng layout shift hoặc runtime color cost.

Không dùng click rate đơn thuần làm bằng chứng màu tốt hơn.

## 21. Non-goals

Plan B không:

- tạo theme riêng cho Vĩnh Long, Bến Tre hoặc Trà Vinh;
- tự đổi theme theo vị trí, giờ, mùa hoặc hành vi;
- lấy dominant color từ ảnh hoặc nội dung AI;
- tạo palette runtime;
- thay đổi thiết kế AdminCP trong wave đầu;
- thay đổi typography, layout hoặc data contract ngoài phần cần thiết để áp màu;
- tạo token Coir Umber hoặc Khmer Ochre trước khi Evidence Book được duyệt;
- dùng color để thay icon, label hoặc source disclosure.

## 22. Acceptance criteria

Thiết kế được coi là triển khai đúng khi:

- Homepage, Discovery và Entity Detail cùng nhận ra là một Adaptive Nocturne
  System nhưng có chromatic rhythm khác nhau;
- Nocturne mặc định và Daylight Parchment giữ cùng semantic meaning;
- primary action dùng River, Brand dùng Clay;
- trust, status, severity và category không thể bị hiểu nhầm là cùng một lớp;
- mỗi viewport có tối đa một material accent nổi bật;
- image không điều khiển semantic UI;
- không có raw hex mới trong page/component thuộc phạm vi;
- các cổng WCAG 2.2 AA và test matrix đều đạt;
- bản sắc ba vùng hiện diện qua foundation và material evidence, không qua ba
  theme tỉnh;
- fallback vẫn rõ nghĩa khi mất màu, mất ảnh hoặc forced colors hoạt động.

## 23. Trình tự sau khi đặc tả được duyệt

Sau user review, bước tiếp theo là lập implementation plan riêng cho:

1. token inventory và migration map;
2. semantic/theme foundation;
3. Homepage recipe;
4. Discovery/Search recipe;
5. Entity Detail recipe;
6. map/data adapter trong phạm vi;
7. accessibility và visual regression gates;
8. legacy alias retirement.

Không triển khai code trước khi implementation plan được viết và duyệt theo
quy trình hiện tại.
