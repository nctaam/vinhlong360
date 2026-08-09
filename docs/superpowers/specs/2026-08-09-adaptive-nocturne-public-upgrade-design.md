# Adaptive Nocturne Public Upgrade

> STATUS: proposed - implementation-focused extension, waiting for user review
> **Ngày:** 2026-08-09
> **Phạm vi:** implementation-focused extension cho public Wave 0-7

## 1. Mục đích

Đặc tả này chuyển các quyết định trong `2026-07-31-nocturne-heritage-adaptive-public-design.md` thành một chương trình nâng cấp UI/UX có thể triển khai và kiểm chứng theo từng lát dọc. Mục tiêu không phải làm lại một homepage riêng lẻ, mà xây một public experience thống nhất:

- có bản sắc Adaptive Nocturne Heritage;
- giúp người dùng tìm, hiểu, quyết định và lập lịch trình nhanh;
- thích ứng theo context nhưng không làm thay đổi skeleton khó đoán;
- minh bạch về nguồn, độ mới, vị trí và lý do gợi ý;
- tiếp tục dùng được khi API, map, media, intelligence hoặc mạng gặp lỗi.

Đặc tả này không thay thế design authority hiện có. Khi có khác biệt, `2026-07-31-nocturne-heritage-adaptive-public-design.md` và `design-system/vinhlong360/MASTER.md` là nguồn thẩm quyền.

## 2. Phạm vi

### 2.1 Public vertical slice ưu tiên

1. shared shell và navigation;
2. homepage;
3. catalog/discovery;
4. search và map;
5. entity detail dossier;
6. itinerary/planner;
7. context, trust, freshness, continuity và intelligence primitives dùng chung.

Community, directory/legal, AdminCP và các public family còn lại sẽ kế thừa foundation nhưng không nằm trong lát triển khai đầu tiên.

### 2.2 Không thuộc phạm vi

- booking, ordering, thanh toán hoặc transaction mới;
- thay đổi route, API, auth, RBAC, SEO hoặc data ownership contract nếu không có đặc tả riêng;
- graph database mới, raw GPS/IP storage, one-time token hoặc nonce storage;
- tự động gọi điện, nhắn Zalo, lưu, chia sẻ, mutate lịch trình hay thay đổi dữ liệu bên ngoài xác nhận của người dùng;
- redesign AdminCP thành public Nocturne surface.

## 3. Nguyên tắc bất biến

- **Existing Screen Evolution:** tiến hóa màn hình hiện hữu; không thay bằng công thức hero → stats → card grid.
- **Adaptive Nocturne System:** Nocturne là DNA chung; Daylight Parchment là accessibility/material variant.
- **Mekong Ink & Clay:** component chỉ dùng semantic tokens, không dùng raw color/radius/shadow.
- **Framed Dossier:** ưu tiên row, split view, definition list, hairline border và bất đối xứng có kiểm soát.
- **Fast action + editorial identity:** mỗi màn hình có một primary action; mỗi viewport tối đa một media-led feature.
- **Trust first:** SourceMark, FreshnessLine, stale/conflict và WhyThis là UI primitives, không phải copy trang trí.
- **Stable adaptation:** context thay đổi density, ordering, CTA và continuation; không thay shell, route hoặc ý nghĩa semantic.
- **Graceful degradation:** lỗi một panel không làm hỏng toàn trang; intelligence tắt thì deterministic UI vẫn dùng được.

## 4. Foundation và shared contracts

### 4.1 Shell

Desktop gồm brand, universal search, khu vực, notification, account; nav thứ hai gồm Trang chủ, Khám phá, Gần bạn, Cộng đồng và Lịch trình. Mobile gồm context/location, search trigger, alert status và bottom nav tối đa năm mục.

Component contracts:

`NocturneShell`, `ContextShell`, `DesktopHeader`, `MobileHeader`, `PrimaryNav`, `ContextLine`, `UniversalSearch`, `ThemeModeControl`, `MobileBottomNav`, `ActionDock`.

Mobile phải recompose theo task; không thu nhỏ desktop header hoặc biến mega panel thành một dải chip.

### 4.2 Content primitives

`EntityRow` phục vụ quét nhanh; `EntityTile` cho object có media; `StoryFeature` cho một feature editorial; `SignalItem` cho cảnh báo/sự kiện/thời tiết; `FilterBar` cho quyết định; `MapListSurface` cho list-map; `SourceMark`, `FreshnessLine`, `WhyThis`, `DataCorrection`, `PageState` và `JourneyTimeline` dùng xuyên family.

Mỗi primitive phải có loading, ready, partial, stale, empty, error và offline behavior. Không tạo page-specific spinner/error/recovery nếu contract chung đã đủ.

### 4.3 Surface state

```ts
type SurfaceState<T> =
  | { kind: 'loading' }
  | { kind: 'ready'; data: T; freshness?: FreshnessMeta }
  | { kind: 'partial'; data: T; failedPanels: string[] }
  | { kind: 'stale'; data: T; updatedAt: string }
  | { kind: 'empty'; recovery: RecoveryAction }
  | { kind: 'error'; retry: RetryAction; fallback?: T }
  | { kind: 'offline'; cached?: T; cachedAt?: string }
```

SSR và client phải dùng cùng state semantics; hydration không được reorder section. Retry có giới hạn và backoff. Fallback phải hữu ích, không chỉ là thông báo lỗi.

### 4.4 Context Envelope

```ts
type ContextEnvelope = {
  area?: AreaRef
  location: {
    mode: 'exact' | 'approximate' | 'selected' | 'unavailable'
    confidence: 'high' | 'medium' | 'low'
  }
  intent?: IntentState
  time: { localDate: string; localTime: string; season?: string }
  freshness: FreshnessSummary
  accessibility: AccessibilityProfile
  network: 'online' | 'degraded' | 'offline'
}
```

Envelope có version, source và TTL. UI phải giải thích được tín hiệu nào đã ảnh hưởng đến ordering hoặc CTA. Không lưu raw GPS/IP trong UI state hay analytics.

### 4.5 Token và responsive

- Primitive → semantic → component; page không đặt token trực tiếp.
- 12 cột desktop, 8 tablet, 4 mobile; gutter 16/24/32px; max-width 1280px.
- Responsive component ưu tiên container query; viewport breakpoint chỉ giữ cho shell/page grid.
- Content surface opaque; shadow chỉ cho overlay, dock, dialog, popover và drag state.
- Action chính có hit area tối thiểu 44×44px.
- Nocturne mặc định; Parchment giữ nguyên layout và semantic meaning.

## 5. Page families Wave 1-2

### 5.1 Homepage

Composition: `context → editorial lead → quick decisions → signals → journey continuation`.

Homepage không được dùng số liệu giả, card lặp hoặc hero lớn mặc định. Quick decisions phải dẫn trực tiếp đến search/catalog/nearby/planner. Signal có source và freshness. Mobile ưu tiên action và context trước media.

### 5.2 Catalog

Composition: `editorial orientation → filter/decision → result surface → evidence → continuation`.

Filter phải phản ánh quyết định thật: khu vực, loại, thời gian, đang mở, accessibility, source. Kết quả dùng row/tile theo hành vi, không ép mọi object vào cùng một card grid.

## 6. Wave 3 — Search và Map

### 6.1 SearchViewState

```ts
type SearchViewState = {
  query: string
  intent: 'place' | 'service' | 'event' | 'story' | 'all'
  filters: FilterSet
  area?: AreaRef
  viewport?: MapViewport
  selectedId?: string
  panel: 'list' | 'map'
}
```

`query`, `intent`, `filters`, `area` và `viewport` có thể serialize vào URL. `selectedId`, panel và scroll position dùng session state để URL vẫn gọn. Back-stack khôi phục toàn bộ context.

### 6.2 Desktop và mobile

Desktop dùng list/map 5/7 cột, list rộng ổn định khoảng 400-440px; map có một control layer. Mobile dùng list trước và map bottom sheet 30-92% chiều cao. Chọn row sẽ pan marker; chọn marker sẽ mở đúng row và giữ scroll continuity.

### 6.3 Recovery và fallback

Zero-result recovery theo thứ tự: bỏ filter ít quan trọng, mở rộng khu vực, sửa chính tả/từ đồng nghĩa, đổi intent sang `all`, xem saved/recent. Không tự đổi query.

Nếu map SDK/tile/network lỗi, list vẫn usable và hiển thị địa chỉ, khu vực, link chỉ đường ngoài hệ thống nếu có. Chỉ dùng toàn trang error khi query và fallback list cùng thất bại. Map lazy-load sau first useful result.

### 6.4 Location

Location state phải phân biệt exact, approximate, selected và unavailable; người dùng luôn sửa được khu vực và tắt personalization. Không hiển thị khoảng cách nếu không có dữ liệu đủ tin cậy.

## 7. Wave 4 — Detail Dossier

### 7.1 Anatomy

Desktop: cột chính 8/12 cho identity, facts, narrative, evidence; rail 4/12 cho action dock, source/freshness, location snapshot và related journey. Hero media chỉ xuất hiện khi ảnh có nguồn, kích thước/aspect ratio và disclosure hợp lệ.

Mobile: `identity → trust/freshness → primary action → facts → narrative → related`. Action dock có safe-area padding và không che nội dung cuối trang.

### 7.2 CTA resolution

- tọa độ hợp lệ: `Chỉ đường`;
- thiếu tọa độ nhưng có liên hệ tin cậy: `Gọi`;
- có Zalo đã xác nhận: `Mở Zalo`;
- có thể lập lịch: `Lưu` hoặc `Thêm vào lịch trình`;
- thiếu dữ liệu: CTA đọc/xem nguồn, không tạo nút giả hoặc disabled không giải thích.

Chỉ một primary CTA; action phụ đi qua action sheet trên mobile.

### 7.3 Trust và dữ liệu lỗi

`SourceMark` và `FreshnessLine` luôn đi cùng facts nhạy cảm theo thời gian. Partial state cho phép facts hoạt động khi media/narrative lỗi. Stale state vẫn cho thao tác an toàn nhưng claim thời gian nhạy cảm phải được đánh dấu. Conflict hiển thị các giá trị, nguồn và thời điểm; không tự chọn im lặng.

Detail chỉ trả 404 khi backend xác nhận `not_found`. Timeout, 5xx, parse failure hoặc offline phải giữ route và cung cấp retry, cache gần nhất nếu có và link quay lại kết quả. Đây là yêu cầu bắt buộc để loại bỏ false-404.

## 8. Wave 5 — Planner

### 8.1 Bố cục

Desktop: timeline 5/12, map 4/12, summary rail 3/12. Ở 1024px chuyển thành split 6/6 và summary drawer. Mobile: time budget → friction notices → timeline → map sheet → action dock.

### 8.2 Timeline và friction

Mỗi stop là row có thời lượng, source, drag handle, note và CTA chỉnh sửa. Friction detection gồm giờ mở cửa xung đột, travel time vượt budget, stale data, thiếu tọa độ/địa chỉ, route unavailable, stop trùng và accessibility mismatch. Mỗi cảnh báo có severity, nguyên nhân và một recovery action; màu không phải kênh duy nhất.

### 8.3 Optimizer

`Tối ưu lịch trình` luôn tạo preview trước/sau, giải thích trade-off và điểm bị ảnh hưởng. Người dùng xác nhận mới áp dụng. Không thể tối ưu an toàn thì giữ lịch trình và đề xuất chỉnh sửa thủ công.

### 8.4 Offline và conflict

Draft có revision, timestamp và source. Offline vẫn cho phép sắp xếp/ghi chú trên cache. Khi online, diff theo từng stop; người dùng chọn local, server hoặc merge thủ công. Share link chỉ đọc khi draft chưa đồng bộ.

## 9. Cross-page continuity

`Journey Thread` mang theo mục tiêu, query, khu vực, filter, item gần đây và planner đang mở. `ContextLine` là surface có thể kiểm tra; `WhyThis` luôn có control. Detail → planner giữ source/freshness và back về đúng vị trí. Auth return path bảo toàn intent thay vì đưa về homepage mặc định. Recent/saved có TTL, nút xóa và không lưu raw location.

## 10. Wave 6 — Adaptive intelligence

### 10.1 Pipeline

```text
signals → Context Envelope → Intent Resolver
       → Adaptive Priority Composer
       → UI/CTA → WhyThis + controls
       → outcome/harm → Learning Ledger
```

Intent confidence `high` mới được đổi primary CTA; `medium` chỉ đổi ordering/metadata; `low` giữ default. Adaptation chỉ được đổi ordering, density, CTA và continuation; không đổi shell, route, grid hoặc semantic colors. Không reorder khi người dùng đang nhập, kéo thả hoặc đọc; context mới áp dụng sau action hiện tại.

### 10.2 Attention và reversibility

Mỗi viewport tối đa một primary action và hai suggestion phụ. Không tự mở popup cho thay đổi context thông thường. Suggestion có `WhyThis`, dismiss và `Hiển thị gọn hơn`. Mọi adaptation quan trọng có before/after, undo, lý do và đường về default.

### 10.3 Degradation

Feature flags độc lập cho personalization, recommendation, search expansion, optimizer và proactive notices. Khi lỗi hoặc bị tắt, deterministic UI vẫn hiển thị content và action cơ bản.

## 11. Wave 7 — Accessibility, reliability và quality

### 11.1 Accessibility profile

Profile dùng chung cho theme, text scale 1/1.25/1.5/2, reduced motion, high contrast, compact density và keyboard-first. Không tự đổi theme theo giờ. Forced colors, 200% zoom, mobile landscape, screen reader và safe-area đều là release gates.

### 11.2 Reliability mesh

Mọi surface dùng `loading → ready/partial/stale/offline/empty/error`, timeout theo shell/content/map/intelligence, retry backoff hữu hạn, stale-while-revalidate và fallback hữu ích. Error không lộ stack trace. SSR/client phải cùng semantics để tránh hydration mismatch.

### 11.3 Quality scorecard

Success metrics: time-to-first-useful-result, search recovery, detail CTA completion, planner completion, save/share/direction success.

Harm metrics: false-404, conflict overwrite, stale-data action, location exposure, repeated dismissed suggestion, accessibility failure và abandon sau error/permission.

Coverage phải được kiểm tra theo khu vực trung tâm/ngoại vi, nguồn dữ liệu, thiết bị thấp cấp, mạng chậm, location disabled và tiếng Việt có dấu. Không rollout khi success tăng nhưng harm hoặc coverage xấu đi.

## 12. Testing và acceptance gates

### 12.1 Viewports và modes

Baseline: 375, 390, 768, 1024, 1440px; Nocturne/Parchment; 200% zoom; reduced motion; forced colors; keyboard; mobile landscape; slow network.

### 12.2 Behavior matrix

Mỗi page family phải test loading, ready, partial, stale, offline, empty, error, retry, auth return, context change, map unavailable, revision conflict và kill switch.

### 12.3 Quality gates

- không overflow hoặc action bị che;
- không hydration reorder hoặc layout shift ngoài ngưỡng;
- body contrast mục tiêu 7:1, UI tối thiểu 3:1;
- primary action có hit area/focus/loading/disabled state;
- không claim, rating, distance, urgency hoặc freshness giả;
- map lỗi không làm mất list; media lỗi không làm mất facts; intelligence lỗi không làm mất task;
- false-404 chỉ xảy ra với not-found có xác nhận;
- visual review theo hierarchy, trust, readability, disclosure và task completion.

## 13. Performance và observability

Theo dõi LCP, CLS, INP, TTFB, payload JS/CSS/SSR, API p95, error rate, time-to-first-useful-result, time-to-primary-action, map tile cost và media decode cost. Shell và first useful result tải trước map/media/intelligence. RUM phải tách theo viewport, network, theme, area và accessibility profile mà không lộ raw location.

## 14. Rollout và rollback

Thứ tự: token/theme → shell → homepage/catalog → search/map → detail → planner → adaptive intelligence. Mỗi bước có feature flag, cohort nhỏ hoặc khu vực giới hạn, baseline, success/harm dashboard, kill switch và rollback về deterministic composition. Rollback không xóa draft planner hoặc dữ liệu người dùng.

## 15. Trình tự implementation plans

1. Foundation tokens, theme, typography và component contracts.
2. Shell/navigation và shared state primitives.
3. Homepage/catalog vertical slice.
4. Search/map vertical slice.
5. Detail dossier và false-404 UX correction.
6. Planner timeline/map/summary và conflict handling.
7. Context envelope, trust/freshness/WhyThis và adaptive composer.
8. Accessibility profile, reliability mesh, RUM và quality gates.
9. Canary, kill switch, rollback và cross-family regression.

Mỗi plan phải có behavior-level tests, visual baseline, performance gate, rollback path và không làm thay đổi route/API/auth/RBAC ngoài scope đã duyệt.

## 16. Tiêu chí hoàn tất design

- public foundation và năm page family có component/state contract rõ;
- search, detail và planner liên tục qua Journey Thread;
- adaptation có confidence, explanation, controls và undo;
- stale/partial/offline/conflict/false-404 có behavior xác định;
- accessibility, performance, trust, privacy, fairness và harm metrics là release gates;
- intelligence có degradation và kill switch;
- spec đủ rõ để tách thành các implementation plans độc lập, không tạo một branch lớn khó rollback.
