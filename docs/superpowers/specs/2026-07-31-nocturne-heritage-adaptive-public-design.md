# Adaptive Nocturne Heritage cho hệ thống public vinhlong360

> STATUS: draft-for-owner-review - các quyết định thị giác và kiến trúc trải nghiệm đã được chủ dự án duyệt trong phiên 2026-07-30/31; chưa cho phép triển khai code.

## 1. Mục tiêu

Biến **Nocturne Heritage** thành visual direction chính cho toàn bộ hệ thống
public của vinhlong360, đồng thời giữ khả năng đọc, khả năng vận hành và tính
minh bạch cần thiết cho một local super app.

Hệ thống phải đạt đồng thời các mục tiêu sau:

1. Có bản sắc Vĩnh Long rõ, cao cấp và không giống giao diện AI sản xuất hàng
   loạt.
2. Dùng được cho toàn bộ public surface: homepage, discovery, catalog, search,
   detail, community, map, planner, directory, static/legal và shared public
   itinerary.
3. Giữ skeleton và navigation ổn định; cá nhân hóa không làm giao diện nhảy hoặc
   đổi cấu trúc khó đoán.
4. Cho phép người dùng hiểu và kiểm soát khu vực, vị trí, sở thích và lý do đề
   xuất.
5. Không thay đổi mô hình sản phẩm hiện tại: giới thiệu và liên hệ trực tiếp qua
   gọi điện, Zalo, chỉ đường, lưu và theo dõi; không booking, ordering hoặc thanh
   toán on-site.

## 2. Phạm vi và nguồn thẩm quyền

### 2.1 Phạm vi

Đặc tả áp dụng cho toàn bộ page family public/hybrid trong Nuxt, gồm phần public
của các route có action yêu cầu đăng nhập. AdminCP không dùng Nocturne làm
composition chính; AdminCP tiếp tục là workbench mật độ cao nhưng có thể dùng
cùng semantic trust, typography sans và một số token thương hiệu.

Đặc tả không thêm bảng hoặc storage cho one-time token/nonce. Nếu một flow cần
chống replay hoặc xác nhận revision, implementation phải tái sử dụng contract
hiện có hoặc dùng cơ chế stateless/bounded đã được review riêng.

### 2.2 Nguồn thị giác

Quyết định sau cùng là **Existing Stitch Screen Evolution**:

- giữ khoảng 70% bố cục, nhịp ảnh và cảm xúc của các screen Stitch hiện hữu;
- chuẩn hóa khoảng 20% bằng token, typography, navigation, spacing, responsive
  và accessibility của dự án;
- bổ sung khoảng 10% lớp super app cho location, trust, personalization,
  journey continuity và community.

Hybrid Editorial Homepage P1.2 chỉ còn là tài liệu tham khảo về anatomy, copy và
media disclosure. Nó không còn là visual source of truth bắt buộc và không được
dùng để thay thế screen hiện hữu một cách máy móc.

Không tuyên bố có generated Stitch HTML hoặc live Stitch response nếu công cụ
Stitch không truy xuất được trong phiên triển khai.

## 3. Quyết định tổng thể

Kiến trúc được chọn là:

> **Adaptive Nocturne System**, dùng **Nocturne + Parchment** như một material
> mode bên trong cùng hệ thống.

Nocturne là DNA chung, không phải quy định mọi pixel đều tối. Parchment là bề
mặt đọc, bằng chứng và thao tác cần độ rõ; nó không phải một theme thứ hai ghép
vào Nocturne.

## 4. Tonal architecture

Tỷ lệ dưới đây là định hướng mật độ, không phải yêu cầu chia màn hình thành các
khối màu theo phần trăm cứng.

| Layout family | Nocturne / Ink | Parchment / Reading | Vai trò |
|---|---:|---:|---|
| Gateway / Editorial | 88% | 12% | Homepage, event feature, seasonal story, campaign |
| Discovery / Search | 62% | 38% | Catalog, search, area, ward, filter và result state |
| Dossier / Detail | 56% | 44% | Entity, article, itinerary detail và source evidence |
| Community / Social | 70% | 30% | Feed, post detail, composer context và moderation state |
| Map / Planner | 90% | 10% | Map canvas, route workspace và itinerary builder |
| Directory / Legal | 35% | 65% | Directory, policy, help và nội dung đọc dài |

Nocturne có thể tồn tại qua shell, typography, border, media crop, khoảng âm và
grain tĩnh. Parchment chỉ xuất hiện khi cải thiện việc đọc hoặc ra quyết định.

## 5. Color và material: Mekong Ink & Clay

### 5.1 Primitive định hướng

| Vai trò | Giá trị khởi điểm | Ý nghĩa vật liệu |
|---|---|---|
| Night ink | `#07110F` | Đen xanh hữu cơ, nền Nocturne chính |
| Raised ink | `#10211E` | Surface tối cấp hai |
| River teal | `#4C817D` | Sông sâu, action phụ và focus context |
| Mang Thit clay | `#A14D34` | Brand action và editorial accent |
| Aged brass | `#C79A57` | Focus, dateline và accent có kiểm soát |
| Alluvial parchment | `#E4D7BD` | Bề mặt đọc ấm |
| Parchment ink | `#14201D` | Chữ trên parchment |

Giá trị production cuối cùng phải được kiểm tra contrast và chuyển thành token
semantic. Page component không được dùng trực tiếp primitive.

### 5.2 Semantic boundary

Màu địa phương không thay thế trạng thái nghiệp vụ:

- clay không mặc định có nghĩa cảnh báo;
- river teal không tự động có nghĩa chính thức;
- brass không thay thế warning;
- official, verified, community, stale, warning và error có semantic token riêng.

Mọi status cần icon, nhãn và màu; màu không bao giờ là kênh duy nhất.

### 5.3 Material

- Grain chỉ là texture tĩnh, opacity thấp và không làm giảm độ đọc.
- Parchment không dùng texture ảnh nặng hoặc noise động.
- Border hairline tạo cấu trúc chính; shadow chỉ dành cho overlay nổi thật.
- Không dùng glassmorphism, glowing gradient, blur diện rộng hoặc surface trong
  suốt lồng nhau.

## 6. Typography: Controlled Serif

Dự án tiếp tục dùng font self-host hiện có:

- `Fraunces` cho `editorial-display`;
- `Be Vietnam Pro` cho `interface-heading`, `body`, `label`, `data`, form và
  navigation.

### 6.1 Fraunces được phép

- hero H1;
- một editorial feature title;
- tên địa danh hoặc tên chương trong Dossier;
- pull quote và narrative highlight có chủ đích.

### 6.2 Fraunces không được phép

- toàn bộ H2/H3 mặc định;
- card title chức năng;
- form, table, metadata, navigation, notification hoặc error;
- map control, planner control và community action.

### 6.3 Contract

- `editorial-display`: Fraunces, weight 500/600, tracking âm nhẹ;
- `interface-heading`: Be Vietnam Pro 600;
- `body`: Be Vietnam Pro 400/500, tối thiểu 16px;
- `label`: Be Vietnam Pro 600/700, không uppercase quá rộng trên chuỗi dài;
- `data`: Be Vietnam Pro với numeral rõ, không dùng serif.

Test chuỗi `Ệ ộ Ẵ ữ Ề Ậ` ở 200% zoom để ngăn dấu tiếng Việt chạm dòng trên.

## 7. Shape language: Framed Dossier

Framed Dossier là composition mặc định cho public surface:

- radius 0-8px;
- hairline border và divider thay cho card shadow;
- layout bất đối xứng có kiểm soát;
- row, dossier, split view và list thay cho uniform card grid;
- một viewport chỉ có tối đa một media-led feature;
- status chip chỉ dùng cho status thực, không dùng pill làm container nội dung;
- hover đổi border, action hoặc underline; không hover-lift đồng loạt.

### 7.1 Anatomy

Một dossier object có thể gồm:

1. dateline hoặc context label;
2. title;
3. narrative summary;
4. primary action;
5. source/trust/freshness row;
6. secondary metadata dạng line item;
7. optional media có disclosure.

Không bắt buộc mọi object có đủ bảy phần. Thiếu dữ liệu thì ẩn phần đó, không
tạo placeholder claim hoặc metric giả.

## 8. Image art direction

### 8.1 Mặc định: Grounded Local Light

- Ưu tiên dusk, chạng vạng, đèn sinh hoạt, ánh lò và ánh sáng địa phương hợp lý.
- Màu trung tính, giữ texture thật và chi tiết gắn với Vĩnh Long.
- Không teal-orange mạnh, lens flare, glow hoặc golden-hour cho mọi ảnh.
- Prompt phải gọi đúng vật liệu, địa bàn, hoạt động và thời điểm.

### 8.2 Lớp phụ: Material Still Life

Dùng cho gốm, sản phẩm, nghề thủ công, nguyên liệu và editorial inset. Ưu tiên
crop gần vật liệu, đồ vật và thao tác; hạn chế khuôn mặt giả lập.

### 8.3 Ngoại lệ: Blue-hour Cinema

Chỉ dùng cho campaign hoặc một hero đặc biệt có lý do biên tập. Không dùng làm
mặc định cho entity, catalog hoặc community.

### 8.4 Disclosure và truth boundary

- Ảnh AI luôn có disclosure nhìn thấy được.
- Không dùng ảnh AI để đại diện tình trạng thực tế của cơ quan, y tế, giao
  thông, cảnh báo hoặc trạng thái đang mở.
- Không OCR screenshot Stitch hoặc concept raster rồi hardcode claim.
- Media có `width`, `height` hoặc `aspect-ratio`; dưới fold lazy-load.

## 9. Theme behavior

### 9.1 Nocturne mặc định

Lần truy cập đầu tiên dùng Nocturne cho toàn bộ public surface.

### 9.2 Daylight Parchment

Giữ tùy chọn người dùng có nhãn dự kiến `Nền sáng dễ đọc`:

- truy cập từ header và settings;
- dùng được cho cả guest và signed-in, không yêu cầu auth hoặc location;
- lưu lựa chọn bền vững;
- không tự đổi theo giờ trong khi người dùng đang sử dụng;
- giữ nguyên layout, component, trust và semantic meaning;
- chỉ thay hệ surface, foreground, border và media scrim cần thiết.

Không gọi Daylight Parchment là một visual direction khác. Nó là accessibility
variant của cùng Adaptive Nocturne System.

## 10. Kiến trúc trải nghiệm thông minh

Kiến trúc được chọn là:

> **Local Life Graph Orchestration** kết nối toàn hệ thống; **Adaptive Task
> Continuity** quản lý hành trình; **Ambient Intelligence** cung cấp ngữ cảnh;
> agentic assistance chỉ tạo bản nháp/giải thích và **Predictive Orchestration**
> chỉ dùng giới hạn cho cảnh báo chính thức hoặc đề xuất confidence cao.

```text
Nocturne Heritage
    -> Context Envelope
    -> Local Life Graph Projection
    -> Intent Resolver
    -> Journey Thread
    -> Adaptive Priority Composer
    -> Next Best Action
    -> Explainability + Recovery
```

Local Life Graph là projection logic từ dữ liệu/API hiện có, không mặc định yêu
cầu graph database, service hoặc dependency mới. Implementation chỉ được thêm
persistence/infra mới khi một plan riêng chứng minh nhu cầu, chi phí và rollback.

### 10.1 Context Envelope

Context chuẩn hóa có thể gồm:

- khu vực thủ công;
- region suy ra tạm thời từ GPS/IP theo consent;
- thời gian, ngày trong tuần;
- thời tiết, sự kiện, mùa vụ và cảnh báo;
- sở thích, lịch sử xem/lưu và hành động gần đây;
- consent, freshness và confidence.

Authority location giữ nguyên:

`manual > GPS > IP > default`

GPS/IP thô chỉ xử lý tạm thời để suy ra khu vực rồi bỏ. Không log, cache hoặc
lưu raw GPS/IP. Server chỉ lưu khu vực chuẩn hóa, nguồn suy ra, độ chính xác,
consent state và thời điểm cập nhật theo contract đã duyệt.

### 10.2 Intent Resolver

Intent là trạng thái tạm thời, không phải mode người dùng cố định. Các intent
hợp lệ ở lớp presentation gồm:

- explore;
- plan;
- contact;
- contribute;
- verify/trust.

Không có tourist mode hoặc local mode. Không suy đoán thuộc tính nhạy cảm và
không lưu nhãn intent dài hạn nếu không cần cho chức năng rõ ràng.

### 10.3 Journey Thread

Journey Thread là row nhỏ giúp tiếp tục tác vụ:

- tiếp tục lịch trình;
- quay lại tập địa điểm vừa so sánh;
- tiếp tục bài viết nháp;
- theo dõi báo sai hoặc claim;
- hoàn tất xác nhận khu vực;
- xem thay đổi của item đã lưu.

Nó không phải dashboard lớn và không được cạnh tranh với primary action của
page.

### 10.4 Adaptive Priority Composer

Giữ skeleton page ổn định và xếp hạng item trong module theo thứ tự:

1. cảnh báo chính thức đang hiệu lực;
2. tác vụ dang dở của chính người dùng;
3. khu vực và khoảng cách;
4. thời gian, mùa vụ và trạng thái có nguồn;
5. sở thích và lịch sử hành động;
6. freshness và trust;
7. ranking mặc định.

Không đảo section sau hydration. Không đổi navigation hoặc layout family theo
personalization.

### 10.5 Next Best Action

Mỗi object chỉ có một primary action phù hợp nhất. Ví dụ:

- `Thêm vào lịch trình`;
- `Chỉ đường`;
- `Gọi` hoặc `Zalo`;
- `Lưu lịch`;
- `Tiếp tục chỉnh sửa`;
- `Xem nguồn` hoặc `Báo thông tin chưa đúng`.

Action phụ đi vào secondary treatment hoặc menu. Không tạo CTA giao dịch mà hệ
thống không thực hiện.

### 10.6 Confidence-aware UI

- confidence cao: gợi ý trực tiếp;
- confidence trung bình: dùng ngôn ngữ `Có thể phù hợp với bạn`;
- confidence thấp: hiển thị ranking mặc định, không gọi là cá nhân hóa;
- stale: nêu thời điểm cập nhật và nguồn;
- conflict: mở source comparison thay vì tự chọn claim.

### 10.7 Explainability

`Vì sao bạn thấy nội dung này?` chỉ hiển thị các tín hiệu broad và allowlisted:

- gần khu vực đã chọn;
- phù hợp sở thích;
- đang đúng mùa;
- liên quan item vừa lưu;
- được ưu tiên vì cảnh báo chính thức;
- ranking mặc định.

Controls bắt buộc:

`Đổi khu vực` · `Chỉnh sở thích` · `Tắt vị trí` · `Đặt lại đề xuất`

### 10.8 Local Life Graph Projection

Graph kết nối các node broad sau:

- user context và journey hiện tại;
- khu vực;
- thời gian và mùa vụ;
- thời tiết, giao thông, sự kiện và cảnh báo;
- địa điểm, dịch vụ, sản phẩm và nội dung cộng đồng;
- source, freshness và trust tier;
- action `directions`, `call`, `zalo`, `save`, `follow`, `plan`, `report`,
  `claim`.

Các edge presentation hợp lệ gồm:

- `nearby`;
- `in_area`;
- `happening_at`;
- `relevant_to_interest`;
- `fits_time_window`;
- `part_of_journey`;
- `saved_or_followed`;
- `has_contact_path`;
- `has_source`;
- `affected_by_official_notice`;
- `needs_recovery`.

Graph projection không đưa raw GPS/IP, private draft content, secret, internal
score hoặc quan hệ của user khác vào client. Edge không đủ dữ liệu phải vắng
mặt, không được suy diễn bằng copy hoặc metric giả.

### 10.9 Situational Brief

Mỗi lần mở hệ thống, có thể hiển thị một brief cực ngắn gồm tối đa:

1. một official signal đang hiệu lực;
2. một thay đổi ảnh hưởng Journey Thread;
3. một task đang dang dở;
4. một gợi ý phù hợp nhất lúc này.

Brief chỉ hiển thị 2-3 dòng và một primary action. Không biến homepage thành
dashboard, không dùng modal và không lấp viewport đầu khi không có tín hiệu đủ
mạnh.

### 10.10 Action Chain

Hệ thống hiểu chuỗi hành động thay vì từng CTA độc lập:

```text
discover
  -> compare
  -> add_to_plan
  -> directions/contact
  -> visited
  -> review/report/correct
```

Mỗi screen chỉ hiển thị bước hiện tại và bước hợp lý kế tiếp. Chuỗi không tự
thực hiện mutation. Mọi bước gửi bài, report, claim, contact hoặc thay đổi lịch
đã xác nhận đều cần hành động rõ của người dùng.

### 10.11 Contextual Continuity Rail

Rail thu gọn có thể chứa:

- địa điểm đang so sánh;
- lịch trình đang chỉnh;
- bài viết nháp;
- claim/report đang xử lý;
- sự kiện vừa lưu;
- location confirmation còn dang dở.

Desktop dùng rail thu gọn; mobile dùng bottom sheet. Rail không mở mặc định khi
không có journey thật, không trở thành navigation thứ hai và không hiển thị task
của user khác sau logout/login hoặc account switch.

### 10.12 Predictive Friction Detection

UI được phép phát hiện trước các lỗi có thể chứng minh từ dữ liệu:

- entity thiếu tọa độ trước khi thêm vào planner;
- time window hoặc travel time không khả thi;
- sự kiện đã hết hạn;
- giờ mở cửa hoặc contact data stale;
- browser đã chặn location/push;
- route service degraded;
- claim thiếu evidence;
- draft có revision conflict.

Mỗi friction notice cần một recovery action. Không dự báo rủi ro bằng LLM nếu
không có dữ liệu xác nhận và không tạo urgency giả.

### 10.13 Trust-weighted Decision Support

Priority logic ở lớp presentation sử dụng thứ tự lexicographic/guarded thay vì
một điểm số bí ẩn:

1. safety/official policy;
2. task feasibility;
3. temporal fit;
4. locality;
5. journey continuity;
6. relevance;
7. freshness;
8. trust;
9. uncertainty và operational risk.

Khi người dùng so sánh, UI chỉ dùng field có dữ liệu thật như khoảng cách, time
fit, khu vực, freshness, source và contact availability. Hiển thị 2-4 lý do
chính; không hiển thị một AI score tổng hợp không giải thích được.

### 10.14 Progressive Complexity

Không tạo beginner/expert mode. Độ chi tiết tăng qua progressive disclosure:

- primary action và thông tin thiết yếu luôn nhìn thấy;
- chi tiết route constraint, source evidence hoặc moderation history mở theo
  nhu cầu;
- preference hiển thị có thể được ghi nhớ nếu không chứa dữ liệu nhạy cảm;
- không ẩn chức năng quan trọng vì hệ thống suy đoán người dùng là “người mới”.

### 10.15 Smart Search và Planner Orchestration

Search là entry point thống nhất cho entity, service, event, community và
official information. Query intent broad như `đi đâu tối nay`, `gần tôi`,
`đang mở` hoặc `phù hợp trẻ em` chỉ được giải bằng dữ liệu hiện có và policy
allowlist; AI không tạo result không tồn tại.

Planner dùng cùng graph/action contract để:

- phát hiện ngày quá tải;
- đề xuất đổi thứ tự hoặc chuyển stop sang ngày khác;
- giữ required stop và preference;
- giải thích stop bị loại;
- giữ lịch khi route service degraded;
- đưa ra bản sửa để người dùng xác nhận, không tự ghi đè.

### 10.16 Adaptive Latency

- Prefetch detail có giới hạn cho item đang focus/hover hoặc next likely route.
- Render shell và cached/stale-safe data trước, cập nhật từng panel.
- Optimistic UI chỉ dùng khi mutation idempotent hoặc có undo rõ.
- Không optimistic approve, report, claim, role change hoặc mutation nhạy cảm.
- Background work bị timeout không được tiếp tục side effect ngoài ownership
  boundary đã duyệt.

### 10.17 Attention Budget

- Tối đa một proactive suggestion nổi bật trong một viewport.
- Không lặp location prompt sau khi người dùng từ chối.
- Suggestion bị dismiss phải giảm ưu tiên trong phạm vi phù hợp.
- Push chỉ dành cho official notice hoặc nội dung user đã chủ động theo dõi.
- Gợi ý thông thường không dùng modal, badge đỏ hoặc countdown.
- Không dùng scarcity, urgency hoặc social proof giả để tăng tương tác.

### 10.18 Agentic Assistance Boundary

AI được phép:

- tóm tắt lựa chọn có dữ liệu;
- tạo draft lịch trình;
- giải thích recommendation hoặc conflict;
- đề xuất bản sửa planner;
- tạo draft bài viết hoặc báo sai để người dùng review.

AI không được tự động:

- gửi bài, report hoặc claim;
- gọi điện, gửi Zalo hoặc liên hệ đối tác;
- thay đổi lịch trình đã xác nhận;
- bật location/push;
- trình bày generated content như official notice;
- tạo entity, rating, giờ mở cửa hoặc event không tồn tại.

Mọi AI output phải có provenance của input, confidence phù hợp và đường quay về
dữ liệu gốc.

### 10.19 Experience Quality Loop

Đo chất lượng bằng kết quả thay vì page view đơn thuần:

- time to first meaningful action;
- task completion rate;
- recovery success;
- planner completion;
- directions/call/Zalo handoff;
- recommendation dismiss/reset;
- `why_recommendation_open`;
- stale/report/correction resolution;
- Journey Thread resume success.

Analytics không thu raw location, private draft content, source evidence nhạy
cảm hoặc dữ liệu không cần thiết cho metric.

## 11. Motion và interaction

- Page entry: fade/reveal 180-260ms, không stagger mọi card.
- Drawer/bottom sheet: transform + opacity tối đa 220ms.
- Không autoplay video, parallax, Ken Burns, particle, WebGL hoặc ambient glow.
- Không dùng animation để thể hiện trust hoặc severity.
- `prefers-reduced-motion` loại bỏ toàn bộ chuyển động không thiết yếu.
- Touch target tối thiểu 44x44px.
- Focus ring dùng outline tương phản; không chỉ đổi màu.

## 12. State và recovery contract

Mỗi layout family phải thiết kế và kiểm thử:

- `loading`;
- `partial`;
- `stale`;
- `empty`;
- `offline`;
- `timeout`;
- `rate-limited`;
- `permission-denied`;
- `conflict`;
- `read-only`;
- `session-expired` khi có action riêng tư.

Quy tắc:

- lỗi một panel không làm trắng toàn page;
- skeleton giữ đúng hình học Framed Dossier và media;
- map lỗi chuyển sang list và giữ filter;
- route service lỗi giữ stop và chỉ downgrade chất lượng tuyến;
- hết phiên giữ intent/draft để đăng nhập lại;
- upload lỗi giữ file hợp lệ;
- offline dùng dữ liệu gần nhất và nêu rõ timestamp;
- zero result nới một điều kiện cụ thể, không reset mọi filter.

## 13. Trust và source hierarchy

Ba tầng nguồn phải tách biệt:

1. `Chính thức`: cơ quan/Admin, có thể ưu tiên và gửi push theo policy.
2. `Đã xác minh`: đối tác/tổ chức có verification record và `verifiedAt` hợp lệ.
3. `Cộng đồng`: UGC đã qua moderation cần thiết, không trình bày như thông báo
   chính thức.

Source presentation gồm icon, label, updated time, freshness và optional source
drawer. Không cấp nhãn `Đã xác minh` chỉ từ boolean hoặc claim thiếu
`verifiedAt`.

## 14. Smart density theo nhiệm vụ

- Reading: giảm action, tăng measure và khoảng thở.
- Search/catalog: tăng mật độ quét, giữ filter và result count thật.
- Map/planner: ưu tiên canvas và sticky task rail, giảm trang trí.
- Community: giữ composer/thread context và moderation status.
- Official notice: ưu tiên nguồn, phạm vi, hiệu lực và recovery action.

Responsive không chỉ co kích thước. Mobile phải tái cấu trúc touch-first; không
thu nhỏ desktop.

## 15. Component contract dự kiến

Foundation dùng chung:

- `NocturneShell`;
- `ThemeModeControl`;
- `FramedDossier`;
- `DossierLineItem`;
- `SourceMark`;
- `FreshnessLine`;
- `WhyThisControl`;
- `SituationalBrief`;
- `JourneyThread`;
- `ContinuityRail`;
- `ActionChain`;
- `NextBestAction`;
- `FrictionNotice`;
- `DecisionSupport`;
- `OfficialNotice`;
- `SystemStatePanel`;
- `GeneratedMediaDisclosure`.

Layout family component không được biến foundation thành một mega-component.
Mỗi component cần một mục đích rõ, API hẹp và có thể mount/test độc lập.

## 16. Data flow và privacy boundary

```text
API/state inputs
  -> allowlisted context projection
  -> local-life graph projection
  -> transient intent resolution
  -> module-local ranking
  -> action-chain / friction projection
  -> confidence + reasons projection
  -> stable page render
  -> user control / reset / recovery
```

Không truyền raw GPS/IP, secret, private history hoặc internal scoring vào DOM,
analytics, source drawer hoặc `Vì sao bạn thấy`.

Analytics chỉ ghi action cần thiết như:

- `call`;
- `zalo`;
- `directions`;
- `save`;
- `follow`;
- `rsvp`;
- `share`;
- `report`;
- `claim`;
- `why_recommendation_open`;
- `location_permission_result`;
- `recommendation_reset`;
- `official_notice_open`.

Không ghi nội dung riêng tư hoặc raw location vào event payload.

## 17. Accessibility và performance gates

### 17.1 Accessibility

- body/input tối thiểu 16px;
- touch target tối thiểu 44x44px;
- body text trên parchment hướng tới 7:1;
- UI boundary và icon tối thiểu 3:1;
- keyboard, focus trap, return focus và back-stack đúng;
- forced colors, `prefers-contrast: more`, reduced motion;
- text zoom 200%;
- mobile landscape;
- color không là kênh duy nhất.

### 17.2 Performance

- font self-host;
- không runtime icon/font CDN;
- media có kích thước ổn định và lazy-load dưới fold;
- không blur diện rộng hoặc backdrop filter lồng nhau;
- không WebGL/particle/ambient animation;
- personalization không gây CLS;
- module lỗi hoặc chậm không chặn first meaningful content của page.

## 18. Cổng chống giao diện AI hàng loạt

Một screen không đạt nếu có một trong các dấu hiệu sau mà không có lý do nghiệp
vụ:

- hero -> stats -> ba card -> CTA cuối trang;
- bento grid dùng cho mọi family;
- pill cloud hoặc glass content;
- gradient thương hiệu phủ mọi ảnh;
- mọi H2/card title đều serif;
- mọi card hover-lift;
- nhiều carousel ngang liên tiếp;
- ảnh blue-hour/golden-hour đồng dạng;
- copy generic `miền Tây`, `sông nước hữu tình`, `khám phá điều tuyệt vời`;
- fake rating, fake urgency, fake OCOP hoặc social proof không có dữ liệu;
- các trang khác nhau chỉ đổi nội dung nhưng giữ nguyên một anatomy card.

## 19. QA matrix

### 19.1 Viewport và mode

- 375px;
- 390px;
- 768px;
- 1024px;
- 1440px;
- portrait/landscape;
- Nocturne;
- Daylight Parchment;
- forced colors;
- reduced motion;
- 200% text zoom.

### 19.2 Behavior-level tests

Ưu tiên mount component/page, gọi feature flag/API fixture và kiểm kết quả người
dùng thực sự thấy. Không chỉ kiểm source string hoặc private implementation.

Tối thiểu phải chứng minh:

- theme selection được lưu và không đổi layout;
- location off ngăn GPS/IP call;
- manual region thắng GPS/IP;
- recommendation explanation chỉ chứa signal allowlist;
- reset idempotent;
- partial API failure giữ panel còn dữ liệu;
- stale/source/trust tách biệt;
- Journey Thread phục hồi đúng task và không lộ task của user khác;
- Continuity Rail được xóa/cách ly đúng khi logout hoặc account switch;
- Situational Brief tôn trọng attention budget và không hiện khi confidence thấp;
- friction notice chỉ dùng dữ liệu có thể chứng minh và luôn có recovery;
- Action Chain không tự thực hiện mutation hoặc contact;
- next best action có fallback an toàn;
- decision support không tạo AI score không giải thích được;
- hydration không reorder section;
- reduced motion và 200% zoom không che control.

### 19.3 Visual review

Mỗi layout family cần screenshot baseline cho desktop/mobile và hai theme. Review
phải kiểm tra composition, Vietnamese typography, disclosure, focus, contrast,
overflow và layout shift; không chỉ so pixel tuyệt đối với Stitch.

## 20. Thứ tự triển khai đề xuất

1. Truth-sync design authority: đánh dấu Hybrid P1.2 là reference và cập nhật
   design-system master.
2. Token + theme foundation: Mekong Ink & Clay, Nocturne/Daylight Parchment,
   Controlled Serif và Framed Dossier.
3. Existing Screen Evolution pilots: homepage, discovery và entity detail.
4. Context/trust primitives: SourceMark, FreshnessLine, WhyThis, OfficialNotice.
5. Local Life Graph projection thuần từ API/state hiện có; không thêm graph DB.
6. Adaptive Task Continuity primitives: Situational Brief, Journey Thread,
   Continuity Rail, Action Chain, Friction Notice, Next Best Action và
   module-local composer.
7. Smart search/planner orchestration và agentic draft/explanation boundary.
8. Map/planner, community, directory/legal và remaining public families.
9. Cross-family state catalog, behavior tests, quality-loop metrics và
   screenshot baselines.

Việc triển khai phải giữ thứ tự privacy/RBAC đã duyệt cho các action private.
Không mở rộng scope sang AdminCP operations, payment, booking hoặc production
deployment trong cùng implementation plan.

## 21. Tiêu chí hoàn tất thiết kế

- Nocturne là nhận diện chính trên mọi public family.
- Daylight Parchment là accessibility variant, không phải site thứ hai.
- Existing Stitch screens được tiến hóa thay vì thay bằng một homepage concept
  độc lập.
- Mỗi family có composition phù hợp nhiệm vụ và không nhân bản card-grid.
- Location, trust và personalization minh bạch, có control và recovery.
- Giao diện thông minh nhưng skeleton/navigation ổn định.
- Local Life Graph kết nối nội dung và hành động mà không cần graph database mặc
  định hoặc tự động thực hiện mutation.
- Situational Brief, Continuity Rail và proactive suggestion tuân thủ attention
  budget.
- Agent chỉ tạo draft/giải thích; mọi action bên ngoài hoặc mutation cần xác
  nhận của người dùng.
- Không lưu hoặc lộ raw GPS/IP.
- Không tạo claim, rating, urgency hoặc verification không có dữ liệu thật.
- Đặc tả đủ rõ để viết implementation plan theo task nhỏ và behavior-level test.
