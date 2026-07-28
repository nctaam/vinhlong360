# Thiết kế NP-1: Identity, Location, Preferences và Trust

> **STATUS:** `draft-for-review` - 2026-07-28.
> **Phạm vi:** Wave NP-1 sau nền tảng RBAC/state; đặc tả dữ liệu, API, UI/state, trust, privacy và test. Chưa triển khai code trong tài liệu này.
> **Worktree:** `C:\Code\vl360-wt\non-public-wave0` trên nhánh `codex/non-public-wave0`.

## 1. Kết luận điều hành

Phương án được chọn là **Preference Contract + Existing Screens**.

Hệ thống giữ nguyên các màn hình và luồng đang có, sau đó bổ sung một hợp đồng preference thống nhất cho khu vực, sở thích, consent vị trí, cá nhân hóa và reset đề xuất. Saved items, visits, search context và first-party events tiếp tục làm tín hiệu phụ; chúng không được ghi đè lựa chọn chủ động của người dùng.

GPS và IP chỉ được xử lý tạm thời để suy ra khu vực gần đúng. Preference store không lưu tọa độ, IP hoặc lịch sử di chuyển. Server chỉ lưu khu vực chuẩn hóa, nguồn suy ra, mức chính xác, trạng thái consent, revision và thời điểm cập nhật.

UI dùng các screen hiện có trong project Stitch làm visual source-of-truth. Nuxt/API hiện tại vẫn là source-of-truth cho dữ liệu, nghiệp vụ, RBAC, accessibility và trạng thái lỗi. Không sao chép HTML Stitch nguyên trạng và không dùng bộ Hybrid Editorial P1.2 làm chuẩn chính.

## 2. Quyết định đã được duyệt

1. Không có chế độ riêng cho khách du lịch hoặc người địa phương.
2. Cá nhân hóa dựa trên khu vực, nhóm tuổi, sở thích, ngữ cảnh và hành vi.
3. Có `Vì sao bạn thấy nội dung này?`, chỉnh khu vực/sở thích, tắt vị trí và đặt lại đề xuất.
4. GPS/IP thô không được lưu trong hệ thống cá nhân hóa.
5. Lựa chọn thủ công luôn có ưu tiên cao hơn GPS, IP và suy luận hành vi.
6. Nội dung có ba tầng nguồn: `Chính thức`, `Đã xác minh`, `Cộng đồng`.
7. Không hiển thị `Đã xác minh` nếu thiếu `verified_at`.
8. Giữ gọi điện, Zalo, chỉ đường và liên hệ trực tiếp; NP-1 không mở marketplace, đặt chỗ hoặc thanh toán.
9. Nâng cấp các screen hiện có thay vì tạo một sản phẩm UI song song.

## 3. Hiện trạng và khoảng trống

### 3.1 Thành phần đã có

- `AuthModal.vue`: số điện thoại, đăng ký, mật khẩu, OTP, đặt mật khẩu và 2FA.
- `/cai-dat`: hồ sơ, bảo mật, phiên, thiết bị tin cậy, privacy, consent, export, deactivate và delete.
- `OnboardingSheet.vue`: welcome marketing có modal accessibility cơ bản.
- `useRegionPref.ts`: preference tỉnh lưu trong `localStorage`.
- `SmartRecommendations.vue`: recommendation và reason ngắn.
- `/dia-diem/[id]`: source/freshness và trust card cơ bản.
- `/api/me/insights` và `/api/me/recommendations/contextual`: profile suy luận từ events, saved items và visits.

### 3.2 Khoảng trống cần giải quyết

- Chưa có preference store phía server cho nơi sống, sở thích, location consent và personalization state.
- Recommendation hiện thiên về tín hiệu suy luận; lựa chọn chủ động chưa có quyền ưu tiên rõ ràng.
- `user_events.jsonl` chứa `user_id`, raw query và `ip_hash`, gây khó cho reset, TTL, export và xóa theo user.
- Consent timeline frontend đọc `consent_version/consent_at`, trong khi API trả `version/created_at`.
- UI xóa tài khoản mô tả xóa ngay, trong khi API lên lịch xóa có grace period và OTP login để hủy.
- Chưa có location permission flow, IP fallback có giải thích, tắt vị trí và reset recommendation.
- Chưa có source/trust drawer dùng chung cho các content family.

## 4. Nguồn thiết kế Stitch

Project Stitch `18117519291023488351` có 52 screen tại thời điểm audit. NP-1 lấy năm screen không thuộc Hybrid P1.2 làm reference chính:

| Vai trò | Screen Stitch | Screen ID | Cách dùng |
|---|---|---|---|
| Trust/detail | Chi tiết địa điểm - Cù lao An Bình (V2) | `6a86654f63f243679ebe997ea340172b` | Source hierarchy, detail rail, disclosure |
| Personal workspace | Lịch trình đã lưu - Vinh Long 360 | `db76e318f0354ee3b1b8e3a0860443a5` | Workspace density, card grouping, empty state |
| Community/source tier | Cộng đồng - Vinh Long 360 | `dc2a7a19958e442a990f548953a042e9` | Community identity, moderation context |
| Mobile interaction | Vinh Long 360 - Mobile Dark Mode Premium | `9dac45c42bd7470797ff912060690909` | Bottom sheet, mobile chrome, dark composition |
| Control density | Kết quả tìm kiếm - Vinh Long 360 | `41df1bef12c443fe8247a62b3f50f419` | Chips, filters, dense result controls |

Nguyên tắc sử dụng:

- Dùng screenshot và HTML reference để hiểu spacing, hierarchy, type role và component anatomy.
- Chuyển thiết kế về token/component hiện có của Nuxt; không dán generated HTML vào production.
- Hybrid P1.2 chỉ là tư liệu phụ, không quyết định anatomy NP-1.
- Screen private còn thiếu phải nối tiếp ngôn ngữ của năm screen reference, không tạo dashboard/card grid chung chung.

## 5. Mục tiêu và phi mục tiêu

### 5.1 Mục tiêu

- Một hợp đồng preference thống nhất cho frontend và recommendation engine.
- Người dùng biết hệ thống đang dùng khu vực nào, lấy từ đâu và có thể thay đổi ngay.
- Consent vị trí minh bạch, có thể thu hồi và không làm hỏng trải nghiệm khi bị từ chối.
- Recommendation giải thích được bằng các lý do thật, không phô bày điểm số nội bộ.
- Trust tier và freshness nhất quán trên detail, recommendation, event, service và notice.
- Reset, export và delete thực sự bao phủ dữ liệu cá nhân hóa.
- Desktop/mobile/light/dark/accessibility dùng cùng contract trạng thái.

### 5.2 Phi mục tiêu

- Không lưu lịch sử GPS/IP hoặc xây location timeline.
- Không suy luận chủng tộc, sức khỏe, tôn giáo, thu nhập hoặc thuộc tính nhạy cảm.
- Không tạo chế độ du lịch/người địa phương.
- Không triển khai transaction loop, booking, ordering hoặc payment.
- Không thiết kế lại homepage hoặc catalog public trong worktree này.
- Không thay toàn bộ visual system hiện có bằng Hybrid P1.2.

## 6. Kiến trúc tổng thể

```text
Manual area choice
        |
One-shot GPS with consent ---+
        |                     |
Coarse IP fallback ----------+--> normalized area resolver
        |                     |
System default --------------+
                              |
                              v
                      user_preferences
                              |
             +----------------+----------------+
             |                                 |
             v                                 v
  explicit preferences              saved/visits/events
             |                                 |
             +----------------+----------------+
                              |
                              v
                 recommendation composer
                              |
                              v
          explanation + source tier + freshness
```

### 6.1 Quy tắc ưu tiên

```text
manual > gps > ip > default
explicit interests > inferred interests
current consent > cached location hint
trust evidence > presentation ambition
```

- Nguồn chất lượng thấp không được ghi đè nguồn chất lượng cao hơn nếu không có thao tác rõ của người dùng.
- `location_enabled = false` vô hiệu hóa cả GPS và IP cho recommendation; khu vực chọn thủ công vẫn hoạt động.
- `personalization_enabled = false` trả recommendation theo khu vực thủ công và fallback công khai, không dùng hành vi.
- `recommendation_reset_at` loại mọi tín hiệu hành vi cũ hơn cutoff khỏi scoring, kể cả event, saved item và visit. Bản ghi saved/visit vẫn thuộc workspace của user và không bị xóa.

## 7. Mô hình dữ liệu

### 7.1 `user_preferences`

Một dòng hiện trạng cho mỗi user:

| Trường | Kiểu khái niệm | Quy tắc |
|---|---|---|
| `user_id` | UUID, PK/FK | Chủ sở hữu preference |
| `region_id` | nullable canonical place ID | Khu vực chuẩn hóa hiện tại |
| `region_label` | bounded text | Snapshot để hiển thị ổn định |
| `region_scope` | `ward/district/province/all/unknown` | Độ chi tiết địa bàn |
| `location_source` | `manual/gps/ip/default` | Nguồn tạo khu vực |
| `location_accuracy` | `ward/district/province/unknown` | Mức chính xác công bố cho UI |
| `location_consent_state` | `unknown/granted/denied/off/expired` | Trạng thái consent hiện tại |
| `location_enabled` | boolean | Cho phép GPS/IP personalization |
| `personalization_enabled` | boolean | Cho phép dùng hành vi |
| `explicit_interests` | JSON array bounded | Danh sách key chủ động, unique, tối đa 12 |
| `recommendation_reset_at` | timestamp nullable | Cutoff tín hiệu hành vi |
| `consent_version` | bounded text | Phiên bản location/personalization consent |
| `revision` | integer | Optimistic concurrency |
| `created_at/updated_at` | timestamp | Audit hiện trạng |

Không lưu latitude, longitude, raw IP, IP hash hoặc location history trong bảng này.

### 7.2 `user_personalization_events`

Kho first-party signal có TTL và xóa theo user:

| Trường | Mục đích |
|---|---|
| `id`, `user_id` | Ownership và delete/export |
| `event_type`, `context` | Loại hành vi và surface |
| `entity_id`, `entity_type`, `area_id` | Context nội dung đã chuẩn hóa |
| `interest_keys` | Intent key được suy ra tại thời điểm ghi |
| `occurred_at`, `expires_at` | Cutoff và retention |

Ràng buộc:

- Không lưu IP/IP hash, tọa độ hoặc raw search query.
- Raw query chỉ được dùng trong request hiện tại để tạo bounded `interest_keys`, sau đó bỏ.
- Retention mặc định 90 ngày; có job xóa theo `expires_at`.
- Mỗi user có giới hạn số event và rate limit ghi.

### 7.3 `user_preference_consents`

Consent location/personalization dùng append-only event riêng, không tái sử dụng `consent_log` điều khoản hiện có:

| Trường | Mục đích |
|---|---|
| `id`, `user_id` | Ownership và export/delete |
| `consent_type` | `location` hoặc `personalization` |
| `state` | `granted/denied/off/expired` |
| `version` | Phiên bản copy/policy đã chấp nhận |
| `created_at` | Thời điểm thay đổi |

Bảng này không lưu IP, tọa độ hoặc browser permission payload. `user_preferences` giữ current state; bảng consent giữ lịch sử quyết định.

### 7.4 Nhóm tuổi

- `date_of_birth` tiếp tục là field tài khoản hiện có.
- Recommendation chỉ nhận `derived_age_band`, ví dụ `under_18`, `18_24`, `25_34`, `35_49`, `50_plus`, `unknown`.
- Không trả exact age trong recommendation response hoặc drawer giải thích.
- Age band chỉ dùng cho tính phù hợp nội dung, không dùng để suy luận thuộc tính nhạy cảm.

## 8. API contract

Các endpoint mới đặt cạnh `/api/me/insights` và `/api/me/recommendations/contextual` để giữ cùng ownership boundary.

### 8.1 `GET /api/me/preferences`

Trả snapshot preference có `revision`, location display state, explicit interests, derived age band và control flags. Response `Cache-Control: no-store`.

### 8.2 `PATCH /api/me/preferences`

- Cập nhật từng phần cho manual region, interests, location/personalization flags và consent state.
- Bắt buộc login, CSRF và `revision` hiện tại.
- Revision sai trả `409` cùng snapshot mới để UI resolve conflict.
- Thu hồi consent phải có hiệu lực trong cùng transaction.

### 8.3 `POST /api/me/location/resolve`

Hai mode:

- `gps`: nhận latitude/longitude bounded trong request, chuẩn hóa sang khu vực rồi bỏ dữ liệu thô.
- `ip`: dùng IP request trong bộ nhớ, trả khu vực gần đúng rồi bỏ giá trị dùng cho lookup.

Response chỉ gồm `region_id`, `region_label`, `region_scope`, `location_source`, `location_accuracy` và thời điểm resolve. Endpoint không tự ghi preference; user phải xác nhận khu vực trước khi persist.

### 8.4 `POST /api/me/recommendations/reset`

- Idempotent.
- Ghi `recommendation_reset_at = now()`.
- Mọi personalization event, saved item và visit có timestamp trước cutoff không còn tham gia scoring.
- Không xóa saved items, visits, follows hoặc profile; background retention có thể xóa event cá nhân hóa cũ nhưng không xóa dữ liệu workspace.
- Trả cutoff và preference snapshot mới.

### 8.5 Mở rộng recommendation response

Mỗi item có explanation contract:

```json
{
  "primary_reason": "Cùng khu vực bạn đã chọn",
  "signals": ["explicit_region", "explicit_interest"],
  "location_context": {
    "label": "Vĩnh Long",
    "source": "manual",
    "accuracy": "province"
  },
  "source_tier": "official",
  "freshness_status": "fresh",
  "controls_url": "/cai-dat#khu-vuc-de-xuat"
}
```

Không trả exact score, feature weight hoặc thuộc tính nhạy cảm.

## 9. Location và consent flow

### 9.1 Nguyên tắc

- Không gọi `navigator.geolocation` khi page load.
- Chỉ yêu cầu GPS sau user gesture có copy nêu rõ lợi ích.
- Manual region không cần browser permission.
- IP luôn được mô tả là `khu vực gần đúng từ IP`.
- Từ chối GPS không làm hỏng app và không tạo vòng lặp prompt.
- Tắt vị trí không xóa manual region.

### 9.2 Trình tự first-time

1. Đăng nhập/đăng ký hoàn tất.
2. `OnboardingSheet` kiểm tra preference snapshot.
3. Nếu chưa có explicit preference, mở setup sheet không bắt buộc.
4. Chọn khu vực thủ công và tối đa ba sở thích ưu tiên.
5. Có thể chọn `Dùng vị trí gần đúng`; GPS chỉ chạy sau action này.
6. User xác nhận khu vực resolved trước khi lưu.
7. Có `Bỏ qua, thiết lập sau` ở mọi bước.

## 10. UI và state flow

### 10.1 `AuthModal`

- Giữ nhiệm vụ identity: phone, register, password, OTP, set-password, 2FA.
- Không nhét GPS/sở thích vào giữa authentication.
- Sau success chỉ phát tín hiệu để `OnboardingSheet` quyết định có mở setup hay không.

### 10.2 `OnboardingSheet`

- Chuyển từ welcome marketing thuần túy thành container state-aware.
- Desktop dùng modal/sheet gọn; mobile dùng bottom sheet theo screen Stitch mobile premium.
- Ba bước tối đa: khu vực, sở thích, location permission.
- Không khóa navigation và không dùng dark pattern để ép consent.

### 10.3 `/cai-dat#khu-vuc-de-xuat`

Thêm tab/card `Khu vực & đề xuất`:

- Khu vực ưu tiên, nguồn, độ chính xác và lần cập nhật.
- Đổi khu vực.
- Cho phép/tắt vị trí gần đúng.
- Cho phép/tắt cá nhân hóa hành vi.
- Sở thích chủ động.
- Nhóm tuổi dùng cho nội dung phù hợp.
- Đặt lại đề xuất.

Copy trạng thái phải phân biệt rõ manual, GPS, IP, off, denied, expired và unknown.

### 10.4 `SmartRecommendations`

- Giữ card/grid anatomy hiện có.
- Thay reason rời rạc bằng trigger `Vì sao bạn thấy nội dung này?`.
- Drawer nêu khu vực, explicit interests, bounded recent signals, context và source tier.
- Có shortcut chỉnh preference, tắt cá nhân hóa và reset.
- `AI gợi ý` không được dùng như nhãn nguồn nội dung.

### 10.5 Shared trust/source drawer

Component dùng chung cho detail, event, service, recommendation card và official notice:

- Source tier và organization identity.
- Source title/url.
- Published/updated/verified timestamps khi có.
- Freshness status.
- Báo sai hoặc bổ sung nguồn.
- Community moderation context.

Desktop dùng popover/side drawer; mobile dùng bottom sheet có sticky action.

## 11. Trust contract

Trust tier và freshness là hai trục độc lập.

### 11.1 `official`

Chỉ dùng khi publisher thuộc cơ quan/Admin và có metadata nguồn phát hành chính thức. Có thể được ưu tiên và push nhưng phải hiện organization identity.

### 11.2 `verified`

Chỉ dùng khi đối tác đã qua verification và có `verified_at`. Thiếu timestamp hoặc verification record thì hạ về tier phù hợp, không suy đoán.

### 11.3 `community`

UGC có moderation state, report và context người đăng. Moderation approval không biến community thành official hoặc verified partner.

### 11.4 Freshness

`fresh`, `aging`, `stale`, `unknown` chỉ nói về tuổi dữ liệu. Freshness không được tự nâng trust tier; official content cũ vẫn có thể là `stale`.

## 12. Error và recovery states

| Tình huống | Hành vi bắt buộc |
|---|---|
| GPS denied | Không prompt lại liên tục; đưa về manual choice |
| Resolve mơ hồ | Hiện khu vực gần đúng và yêu cầu xác nhận |
| Resolver/API lỗi | Giữ preference cuối đã xác nhận; không âm thầm chuyển sang IP |
| Consent expired | Dừng location signal và yêu cầu xác nhận lại |
| Preference conflict | Trả `409`, hiển thị snapshot mới, không ghi đè âm thầm |
| Offline | Cho xem state cache; khóa mutation và có retry |
| Reset lặp | Trả cùng semantics, không lỗi hoặc tạo nhiều side effect |
| Recommendation rỗng | Fallback public/region, không gọi là personalized |
| Trust metadata thiếu | Hạ nhãn, không đoán nguồn hoặc verification |

## 13. Privacy, security và retention

- Location resolve endpoint không log request body hoặc tọa độ trong exception telemetry.
- API gateway/access log không chứa query/body GPS. Request IP có thể tồn tại trong security/access control plane theo retention hiện hành nhưng không được sao chép sang preference, event, audit metadata hoặc recommendation telemetry.
- GPS/IP không đi vào personalization event, response cache hoặc analytics payload.
- Preference endpoints bắt buộc login, CSRF, rate limit, bounded input và ownership check.
- Consent versioned; revoke có hiệu lực ngay.
- Export dữ liệu gồm preference và personalization events.
- Khi schedule delete, preference/events được giữ trong grace period để OTP login có thể hủy. Final purge sau grace period phải xóa preference, consent history và personalization events cùng dữ liệu tài khoản khác.
- Deactivate chỉ dừng account/session; preference giữ để OTP reactivation khôi phục đúng state.
- Existing security/session/consent IP logs là control plane riêng, không được tái sử dụng cho personalization.

## 14. Legacy event cutover

1. Tạo bảng event mới và bật dual-read bằng feature flag.
2. Chuyển write path sang PostgreSQL; dừng ghi `user_events.jsonl`.
3. Không backfill raw query hoặc `ip_hash` từ JSONL vào bảng mới.
4. Trong 30 ngày chuyển tiếp, recommendation có thể đọc legacy event mới hơn `recommendation_reset_at`.
5. Export/delete trong giai đoạn chuyển tiếp phải lọc/purge legacy record theo user dưới file lock.
6. Hết cửa sổ chuyển tiếp, ngừng đọc và purge file theo retention policy.

## 15. Sửa sai lệch UI/API hiện có

- Consent timeline đọc `version` và `created_at`.
- Delete account copy nói rõ lên lịch xóa sau `grace_days` và OTP login có thể hủy.
- Toast delete dùng `message` do API trả về, không hard-code `Đã xóa tài khoản`.
- Recommendation explanation không dùng `AI` như source tier.
- `useRegionPref` trở thành adapter/cache frontend của preference API; `localStorage` không còn là source-of-truth cho user đã đăng nhập.

## 16. Accessibility và responsive contract

- Focus trap, focus restore, Escape close và route focus cho sheet/drawer.
- Touch target tối thiểu 44x44px; action spacing tối thiểu 8px.
- Không dùng màu là kênh duy nhất cho source, consent hoặc error state.
- Screen reader đọc source tier trước freshness và action.
- Reduced motion bỏ slide/scale, giữ transition tối thiểu.
- 200% text zoom không che action sticky.
- Desktop 1440/1024 và mobile 390 có baseline light/dark.
- Vietnamese diacritics giữ nguyên; không dùng uppercase dài ở control.

## 17. Test contract

### 17.1 Backend

- Preference precedence: `manual > gps > ip > default`.
- Explicit interests không bị inferred interests ghi đè.
- Tọa độ GPS không xuất hiện trong DB, JSONL, log fixture hoặc response cache; raw IP không xuất hiện trong personalization store/event/telemetry.
- Reset loại bỏ toàn bộ event trước cutoff.
- Saved items và visits trước cutoff không còn tham gia scoring nhưng vẫn còn trong workspace.
- Revoke consent dừng location signal trong request kế tiếp.
- Export/delete bao phủ preference và event mới/legacy trong cutover.
- `verified` không thể được trả nếu thiếu `verified_at`.
- Revision conflict trả `409` và không mất dữ liệu.
- Resolver input invalid/out-of-range bị từ chối trước side effect.

### 17.2 Frontend

- Không gọi geolocation trước user gesture.
- Ma trận state: unknown, manual, GPS, IP, off, denied, expired, offline và conflict.
- Consent timeline dùng đúng field API.
- Delete copy/toast khớp grace-period response.
- `WhyThis` và trust drawer hoạt động bằng bàn phím/screen reader.
- Fallback không bị gắn nhãn personalized.
- Visual regression đối chiếu năm screen Stitch reference.

### 17.3 E2E

- Register -> skip onboarding -> thiết lập sau.
- Register -> manual region/interests -> deny GPS.
- GPS resolve -> xác nhận region -> preference persist.
- Đổi region -> recommendation reason đổi đúng.
- Tắt location -> không gọi GPS/IP resolver.
- Reset -> event cũ không còn ảnh hưởng.
- Official/verified/community và fresh/stale không bị trộn semantic.
- Offline mutation giữ state cũ và retry không nhân đôi side effect.

## 18. Rollout và feature flags

1. `preference_profile_v1`: schema và API preference/consent phía server.
2. `personalization_events_pg`: dual-read legacy event, new-write PostgreSQL.
3. `preference_ui_v1`: `/cai-dat` và `OnboardingSheet` dùng preference API.
4. `location_resolver_v1`: resolver và consent controls.
5. `recommendation_explanations_v1`: explanation contract.
6. `trust_drawer_v1`: shared trust/source drawer.
7. Visual/a11y/E2E gates.
8. Tắt legacy read và purge JSONL sau cửa sổ chuyển tiếp.

Mỗi bước phải có flag/rollback độc lập; tắt personalization không được làm hỏng public fallback.

## 19. Acceptance criteria

- User có thể chọn khu vực/sở thích mà không bật GPS.
- User biết khu vực đến từ manual, GPS, IP hay default.
- Tắt vị trí làm GPS/IP ngừng ảnh hưởng recommendation ngay.
- Reset đề xuất có tác dụng đo được mà không xóa saved/visits.
- Không có tọa độ/IP thô trong personalization storage/logging.
- Recommendation có lý do thật và control liên quan.
- Không có `Đã xác minh` nếu thiếu `verified_at`.
- Consent timeline và account deletion copy khớp API.
- UI private mới nhìn cùng một hệ với các screen Stitch reference.
- Test backend, frontend, E2E, accessibility và visual regression đều qua trước rollout.

## 20. Self-review

- Không còn `TBD`, `TODO` hoặc endpoint chưa có ownership.
- Preference state, inferred profile và event retention có ranh giới rõ.
- Thiết kế không lưu GPS/IP thô và không tái sử dụng security IP cho personalization.
- Reset, export, delete và legacy cutover không mâu thuẫn nhau.
- UI dùng screen hiện có; không mở lại Hybrid P1.2 làm chuẩn.
- Scope dừng ở identity/location/trust; personal workspace, partner/moderation và AdminCP operations là các wave sau.

## 21. Decision gate

Sau khi người dùng duyệt tài liệu này, bước tiếp theo là dùng `superpowers:writing-plans` để lập implementation plan chi tiết cho NP-1. Chưa triển khai NP-2 personal workspace trước khi NP-1 qua verification và được commit riêng.
