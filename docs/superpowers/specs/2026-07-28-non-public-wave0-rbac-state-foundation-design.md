# Non-public Wave NP-0: RBAC và State Foundation

> STATUS: active - được chủ dự án duyệt triển khai theo thứ tự `RBAC/state foundation -> identity/location/trust -> personal workspace -> partner/moderation -> AdminCP operations` ngày 2026-07-28.

## 1. Mục tiêu

Tạo nền quyền truy cập và trạng thái dùng chung để các screen private/AdminCP tiếp theo không tự suy diễn role, không lặp permission logic và không biến lỗi quyền thành lỗi mạng.

Kết quả của Wave NP-0:

1. `/auth/me` trả danh sách `admin_scopes` đã chuẩn hóa từ backend.
2. Moderator hợp lệ vào được moderation surface.
3. Middleware, sidebar, dashboard entry và action dùng cùng một access resolver.
4. Route thiếu quyền đi tới `/403` có giải thích và đường quay lại an toàn.
5. Có component state dùng chung cho `permission-denied`, `session-expired`, `partial`, `conflict`, `rate-limited`, `offline` và `read-only`.

## 2. Phương án được chọn

### Vertical slice theo contract backend

- Tách mapping role -> scope ra module backend độc lập để `admin.py` và `auth.py` dùng chung.
- Giữ các symbol cũ được import/re-export trong `admin.py` để không phá test và caller hiện có.
- Thêm `admin_scopes` vào safe user response; user thường nhận mảng rỗng, superadmin nhận `['*']`.
- Frontend có utility thuần TypeScript để resolve scope, kiểm tra path, lọc navigation và tìm landing route đầu tiên.
- Middleware không hardcode `admin/superadmin`; nó kiểm tra entry scope và scope của route đích.
- Moderator truy cập `/admin` được chuyển tới `/admin/kiem-duyet`; role có nhiều scope giữ `/admin` làm bàn điều phối.

Không chọn frontend-only vì backend đã là nguồn sự thật RBAC. Không chọn big-bang vì các wave sau cần một nền có test và rollback độc lập.

## 3. Kiến trúc

```text
users.role + optional custom scopes
             |
             v
agent/admin_permissions.py
             |
       +-----+------------------+
       |                        |
agent/admin.py              agent/auth.py
require_admin + API         /auth/me.admin_scopes
                                  |
                                  v
web-nuxt/useAuth -> adminAccess.ts
                         |
             +-----------+-----------+
             |           |           |
         middleware    sidebar      actions/pages
             |
             v
          /403 + SystemStatePanel
```

## 4. Contract scope

Scope chuẩn:

- `content.editor`
- `moderation.manager`
- `ops.deploy`
- `settings.admin`
- `security.admin`
- `*`

Role mặc định:

| Role | Scope |
|---|---|
| `user` | không có |
| `moderator` | `moderation.manager` |
| `admin` | năm scope quản trị |
| `superadmin` | `*` |

Custom scope trong các field `admin_scopes`, `scopes`, `permissions` được hợp nhất ở backend. Frontend chỉ tiêu thụ kết quả đã chuẩn hóa, nhưng có fallback role mapping để không khóa toàn bộ AdminCP trong thời gian rollout nếu client nhận response cũ.

## 5. Route và navigation policy

- `/admin` yêu cầu có ít nhất một admin entry scope.
- `/admin/kiem-duyet`, `/admin/bao-cao` yêu cầu `moderation.manager`.
- Content/data routes yêu cầu `content.editor`.
- `/admin/thong-ke`, `/admin/ai` yêu cầu `ops.deploy`.
- `/admin/users`, `/admin/nhat-ky` yêu cầu `security.admin`.
- `/admin/cai-dat/**` yêu cầu `settings.admin`.
- Route chưa có rule riêng fail closed nếu nằm dưới `/admin/**`, ngoại trừ `/admin` entry.

Sidebar loại bỏ item không đủ scope. Badge API chỉ được tải khi actor có ít nhất một queue tương ứng; failure của badge không chặn navigation.

## 6. State foundation

`SystemStatePanel` là component trình bày trạng thái, không tự fetch dữ liệu và không tự điều hướng. Props tối thiểu:

- `kind`: `permission-denied | session-expired | partial | conflict | rate-limited | offline | read-only | error`;
- `title`, `description`;
- `primaryLabel`, `secondaryLabel` tùy chọn;
- `details` và `retryAfter` tùy chọn.

Component emit `primary` và `secondary`; caller quyết định retry, login hoặc navigate. Mọi variant dùng cùng semantic tokens, icon SVG qua `IconLine`, focus-visible và không dùng emoji.

## 7. Error và recovery

- Guest vào AdminCP: chuyển tới `/?login=admin`, giữ `redirect` nội bộ đã encode.
- Có admin entry scope nhưng thiếu scope route: chuyển `/403?from=<path>&required=<scope>`.
- `/403` không tin query để redirect ra domain ngoài; chỉ cho quay lại route nội bộ hợp lệ hoặc landing scope đầu tiên.
- Response `/auth/me` cũ không có `admin_scopes`: fallback theo role.
- Response scope không hợp lệ: bỏ qua giá trị lạ; không cấp quyền từ chuỗi rỗng hoặc object.
- Permission error và network error dùng copy/state khác nhau.

## 8. Phạm vi file

Backend:

- Tạo `agent/admin_permissions.py`.
- Sửa `agent/admin.py` để dùng module quyền chung.
- Sửa `agent/auth.py` để trả `admin_scopes`.
- Thêm test contract scope và `/auth/me` safe user.

Frontend:

- Tạo `web-nuxt/utils/adminAccess.ts`.
- Sửa `web-nuxt/types/index.ts`.
- Sửa `web-nuxt/middleware/admin.ts`.
- Sửa `web-nuxt/utils/adminNavigation.ts`.
- Sửa `web-nuxt/layouts/admin.vue` để dùng nav đã lọc.
- Tạo `web-nuxt/components/system/SystemStatePanel.vue`.
- Tạo `web-nuxt/pages/403.vue`.
- Thêm Vitest cho resolver, navigation và state panel.

Không sửa homepage, public catalog, entity detail, database schema, production data hoặc endpoint mutation.

## 9. Kiểm thử

TDD bắt buộc:

1. Backend test fail trước khi tạo module scope và trước khi `/auth/me` có `admin_scopes`.
2. Frontend test fail trước khi có resolver/filter/navigation.
3. Component test fail trước khi có `SystemStatePanel` và `/403` integration.
4. Chạy focused tests sau từng chu kỳ.
5. Cuối wave chạy backend suite liên quan, frontend Vitest, typecheck và build.

## 10. Tiêu chí hoàn tất

- Moderator mở được `/admin/kiem-duyet` và `/admin/bao-cao`.
- Moderator không thấy hoặc mở được content, users, ops, settings.
- Admin/superadmin giữ quyền hiện tại.
- Sidebar và middleware dùng cùng resolver; không có route visible nhưng bị middleware chặn do mapping lệch.
- `/403` phân biệt rõ thiếu quyền với lỗi mạng.
- Không có structural emoji mới, raw secret, open redirect hoặc thay đổi dữ liệu.
- Mỗi thay đổi có test đỏ -> xanh và toàn bộ verify cuối không có fail mới.

## 11. Phần chuyển sang Wave NP-1

Wave identity/location/trust chỉ bắt đầu sau khi NP-0 đạt toàn bộ tiêu chí trên. Nó sẽ tái sử dụng `SystemStatePanel` và access/state contracts thay vì tạo error component riêng cho từng page.
