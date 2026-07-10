# User System Deep Upgrade — Design Spec
> STATUS (2026-07-10): done — design/audit đã hiện thực & ship.


**Date:** 2026-07-03
**Branch:** feat/entity-content-model
**Scope:** User system toàn diện — FE gap closure, dark mode, activity timeline, achievements, 2FA
**Constraints:** Solo dev, free-tier only, web-only, no paid services, <10k users

---

## Context

User system backend đã rất đầy đủ: avatar/cover upload, sessions, password management, deactivation, notification preferences, block/mute enforcement, SSE real-time, drafts, scheduled posts, reactions (5 emoji), comment editing (24h), collections (20 max), privacy settings, login history, reputation/badges, Q&A/best-answer, repost, pinning. Tổng cộng 54 items trong plan trước đã 100% implemented.

"Sâu hơn" = **3 trục**: (1) FE gap closure + UX micro-interactions, (2) Social depth + engagement, (3) Security hardening. Triển khai theo 4 waves, mỗi wave self-contained.

---

## Wave 1: FE Gap Closure + Dark Mode + Polish

Mục tiêu: đảm bảo mọi backend feature có FE implementation đầy đủ. Thêm dark mode cho public pages.

### W1.1: Dark Mode cho Public Pages (M)

**What:** Toggle dark/light mode trong header cho toàn site. Admin đã có dark mode toggle — extend sang public pages.

**How:**
- Thêm dark mode toggle button vào `layouts/default.vue` header (cạnh notification bell)
- Persist lựa chọn vào `localStorage('theme')` + cookie cho SSR
- Respect `prefers-color-scheme` media query làm default
- Dùng CSS variables đã có trong `variables.css` + `dark-overrides.css`
- Toggle class `dark-mode` trên `<html>` element (pattern đã dùng ở admin layout)

**Files:** `layouts/default.vue`, `composables/useTheme.ts` (new), `plugins/theme.client.ts` (new)

### W1.2: Login History UI (S)

**What:** Security tab trong `/cai-dat` hiển thị 10 lần đăng nhập gần nhất.

**How:**
- `GET /auth/login-history` endpoint (nếu chưa có — check, table đã có)
- Render table trong security tab: device icon, IP, thời gian, status (success/fail)
- "Phiên hiện tại" badge cho session trùng

**Files:** `auth.py` (nếu cần endpoint), `cai-dat.vue`

### W1.3: Password Strength Meter (S)

**What:** Visual indicator khi user set/change password.

**How:**
- Pure scoring: length (<8 weak, <12 medium, <16 strong, >=16 very strong) + char class diversity (lower/upper/digit/special)
- Common password blacklist (top 100)
- CSS bar animation (red→orange→green→blue), label text
- Không thêm dependency, inline scoring function

**Files:** `cai-dat.vue` (FE only)

### W1.4: AvatarPlaceholder Consistency (S)

**What:** Replace tất cả inline avatar fallback bằng `<AvatarPlaceholder>` component.

**How:**
- Audit tất cả component render avatar: PostCard, ReviewCard, comment sections, notification items
- Replace inline `<span class="avatar">{{ initial }}</span>` patterns với `<AvatarPlaceholder :initial="..." :src="..." />`
- Đảm bảo component handle cả img error gracefully

**Files:** `PostCard.vue`, `ReviewCard.vue`, + bất kỳ file nào render avatar inline

### W1.5: Blocked/Muted Users in Settings (S)

**What:** Privacy tab hiển thị danh sách người đã chặn/tắt tiếng + nút bỏ chặn/bỏ tắt.

**How:**
- `GET /api/blocked-users` đã có — fetch và render
- `GET /api/muted-users` — kiểm tra, thêm nếu chưa có
- Render dưới dạng list: avatar + tên + nút action
- Optimistic UI khi unblock/unmute

**Files:** `cai-dat.vue`, `social.py` (nếu cần endpoint muted)

### W1.6: Collection Management FE (S-M)

**What:** Ensure FE fully covers collection backend. Backend CRUD đầy đủ (create/list/delete collections, add/remove items, max 20 collections).

**How:**
- Audit FE: tìm tất cả references đến `/me/collections` — xác định đã có gì
- Required UI: (a) "Save to collection" dropdown trên PostCard bookmark button, (b) collection grid trên profile tab, (c) create/rename/delete collection modal, (d) collection detail page showing items
- Nếu item nào thiếu → implement. Nếu đã đủ → polish (loading states, empty states, error handling)

**Files:** `cong-dong.vue`, `PostCard.vue`, `nguoi-dung/[id].vue`

### W1.7: Scheduled Posts UI (S)

**What:** Ensure post scheduling UI đầy đủ. Backend hỗ trợ create/list/cancel scheduled posts.

**How:**
- Audit FE: tìm references đến `scheduled` trong cong-dong.vue — xác định đã có gì
- Required UI: (a) date/time picker trong post creation form, (b) "Bài đã lên lịch" tab/section, (c) cancel scheduled button, (d) "Sẽ đăng lúc..." indicator
- Nếu item nào thiếu → implement. Nếu đã đủ → polish UX

**Files:** `cong-dong.vue`

### W1.8: Content Analytics Card (S)

**What:** Self-profile hiển thị analytics card (views, likes, reactions, reach).

**How:**
- `/me/stats` endpoint đã trả reactions_received, collections, etc.
- Render card mới trên self-profile: "📊 Tổng quan" section
- Stats: tổng view, tổng reaction, top entity reviewed, post count by type

**Files:** `nguoi-dung/[id].vue`

### W1.9: Save/Reaction Micro-animations (S)

**What:** CSS keyframe animation khi save/unsave và khi react.

**How:**
- Heart bounce animation khi toggle favorite (scale 1→1.3→1 + color transition)
- Reaction emoji pop animation (scale 0→1.2→1 + opacity)
- Bookmark slide animation
- Dùng CSS `@keyframes`, no JS library. `prefers-reduced-motion` guard

**Files:** `components.css` hoặc component scoped styles

### W1.10: Settings Overview Enrichment (S)

**What:** Thêm thông tin vào overview cards trên settings page.

**How:**
- Card "Thông báo": tóm tắt notification prefs (bao nhiêu loại bật/tắt)
- Card "Quyền riêng tư": profile visibility status + blocked/muted count
- Card "Danh sách": số collections
- Fetch data từ existing endpoints

**Files:** `cai-dat.vue`

---

## Wave 2: Activity Timeline + Profile Depth

### W2.1: Activity Timeline Tab (M)

**What:** Tab mới trên profile: "Hoạt động" — dòng thời gian tất cả actions.

**Backend:**
- `GET /api/users/{id}/timeline?page=1&limit=20` — union query:
  - Posts (post_type, created_at)
  - Reviews (entity_name, rating, created_at)
  - Follows (followed_user display_name, created_at)
  - Achievements (achievement_name, unlocked_at) — khi Wave 3 done
- Sort by created_at DESC, paginated
- Respect privacy settings (private profile → only self)

**Frontend:**
- New tab "Hoạt động" trên profile (cạnh Bài viết / Đánh giá / Đã lưu)
- Timeline items with type icon, content preview, timestamp
- Infinite scroll

**Files:** `social.py`, `nguoi-dung/[id].vue`

### W2.2: Enhanced User Discovery (S)

**What:** Tìm kiếm người dùng theo tên trong community.

**How:**
- Backend: `/api/community/search-users?q=xxx` (kiểm tra đã có chưa)
- FE: search input trong community page, render user cards
- Filter: theo hoạt động (active/all), sort: reputation/recent

**Files:** `cong-dong.vue`, `social.py` (nếu cần)

### W2.3: Profile Visit Counter (S)

**What:** "X người đã xem hồ sơ tuần này" trên self-profile.

**Backend:**
- Migration: `profile_views` table (viewer_id, viewed_id, created_at) hoặc simple counter
- `GET /api/users/{id}/profile` trả `view_count_7d` cho self
- Log view khi không phải self (dedupe per viewer/day)

**Frontend:**
- Stat card trên self-profile: "👁 X lượt xem tuần này"

**Files:** `social.py`, migration, `nguoi-dung/[id].vue`

### W2.4: Following Feed Enhancement (M)

**What:** Following feed hiển thị entity feed + friend activity, không chỉ posts.

**How:**
- Thêm "Bạn bè đã đánh giá" section (reviews từ followed users)
- Thêm "Được lưu bởi bạn bè" section (entities saved by followed users)
- Tab trong community: "Tất cả" / "Bạn bè" / "Khám phá"

**Files:** `cong-dong.vue`, `social.py`

### W2.5: Profile Badges Showcase (S)

**What:** Section dedicated cho badges với progress bars.

**How:**
- Hiển thị tất cả badges (earned + locked) với progress bar
- Earned: icon + label + date earned
- Locked: greyed icon + "Còn X reviews nữa để đạt Review Master"
- `/me/badge-progress` endpoint trả progress cho mỗi badge

**Files:** `nguoi-dung/[id].vue`, `social.py`

### W2.6: Weekly Activity Digest (M)

**What:** Notification in-app tóm tắt hoạt động tuần.

**Backend:**
- Scheduler job (weekly, Sunday 8am): cho mỗi active user
- Tóm tắt: new followers, total reactions, post performance, suggested actions
- Dùng existing notification system (type = 'digest')
- Chỉ in-app, KHÔNG email (không có email service)

**Files:** `notifications.py`, scheduler

---

## Wave 3: Achievement System + Engagement

### W3.1: Achievement System Backend (M)

**Migration:**
```sql
CREATE TABLE achievements (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    icon TEXT,
    category TEXT,  -- social, content, explorer, veteran
    requirement_type TEXT,  -- count, streak, threshold
    requirement_value INT
);

CREATE TABLE user_achievements (
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    achievement_id TEXT REFERENCES achievements(id),
    unlocked_at TIMESTAMPTZ DEFAULT NOW(),
    progress INT DEFAULT 0,
    PRIMARY KEY (user_id, achievement_id)
);
```

**~15 achievements:**
| ID | Name | Category | Requirement |
|----|------|----------|-------------|
| first_post | Bài viết đầu tiên | content | 1 post |
| writer_10 | Nhà văn | content | 10 posts |
| reviewer_5 | Nhà phê bình | content | 5 reviews |
| review_master | Bậc thầy đánh giá | content | 25 reviews |
| photographer | Nhiếp ảnh gia | content | 10 posts with images |
| explorer_5 | Nhà thám hiểm | explorer | 5 entities visited |
| explorer_20 | Lữ khách | explorer | 20 entities visited |
| local_3 | Người địa phương | explorer | 3 areas explored |
| social_10 | Kết nối | social | 10 followers |
| social_50 | Ảnh hưởng | social | 50 followers |
| helpful_5 | Hữu ích | social | 5 best answers |
| streak_7 | Chăm chỉ | veteran | 7-day login streak |
| streak_30 | Kiên trì | veteran | 30-day login streak |
| veteran_6m | Lão làng | veteran | 6 months membership |
| allrounder | Đa tài | special | 1 of each category |

**Backend logic:**
- `check_achievements(user_id)` — run after key actions (post, review, follow, login)
- Compute progress, award if threshold met
- Create notification on unlock
- `GET /api/me/achievements` — list all with progress

### W3.2: Achievement Showcase FE (M)

**Frontend:**
- Profile section "Thành tích" — grid of achievement cards
- Earned: colored icon + name + date
- Locked: grey + progress bar + "Còn X để đạt"
- Unlock animation: confetti-lite CSS effect (scale + glow)
- Toast notification on achievement unlock

### W3.3: Login Streak Tracking (S)

**Backend:**
- Track daily login in `user_stats` or dedicated column
- Increment streak on login if last login = yesterday
- Reset if gap > 1 day
- Notify milestones (7, 30, 100 days)

### W3.4: Level Progression Enhancement (S)

**Frontend:**
- XP bar below level label on profile
- Show "X XP to next level"
- Level-up toast with CSS animation
- Micro-progress animation on XP gain

### W3.5: Contribution Heatmap (S)

**Frontend:**
- GitHub-style 52-week activity grid on profile
- CSS grid, no library, green shading by activity count
- Tooltip on hover showing date + count
- `GET /api/users/{id}/activity-heatmap` — daily counts for 365 days

### W3.6: Leaderboard Improvements (M)

**Frontend + Backend:**
- Time filter: tuần này / tháng này / tất cả
- Category filter: bài viết / đánh giá / ảnh / tổng hợp
- User search within leaderboard
- Self-highlight row

---

## Wave 4: 2FA + Security Hardening

### W4.1: 2FA TOTP Setup (M)

**Migration:**
```sql
CREATE TABLE user_2fa (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    secret TEXT NOT NULL,
    recovery_codes JSONB DEFAULT '[]',
    enabled BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Backend:**
- `POST /auth/2fa/setup` — generate TOTP secret + QR data URI (otpauth:// URL)
- `POST /auth/2fa/verify-setup` — verify first code to enable
- `POST /auth/2fa/disable` — require current TOTP code to disable
- Library: `pyotp` (pure Python, no external dependency)
- QR generation: `qrcode` library (or inline SVG generation)

**Frontend:**
- Setup wizard in security tab:
  1. Click "Bật xác thực 2 bước"
  2. Show QR code + manual key
  3. Enter verification code
  4. Show recovery codes (copy/download)
  5. Done

### W4.2: Recovery Codes (S)

- Generate 8 recovery codes on 2FA enable
- Display once (with copy + download buttons)
- Each code single-use
- `POST /auth/2fa/use-recovery` — verify + consume

### W4.3: 2FA Login Flow (M)

- After password/OTP verification, check if 2FA enabled
- If yes, show TOTP code input form
- Option: "Use recovery code instead"
- Remember device option (cookie 30 days)

### W4.4: Suspicious Login Alert (S)

- On login: compare IP + UA with `login_history`
- If new IP or new UA: create notification "Đăng nhập mới từ [device] tại [IP]"
- Show in notification bell immediately (SSE)

### W4.5: Trusted Device Management (M)

**Migration:**
```sql
CREATE TABLE trusted_devices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    device_name TEXT,
    device_fingerprint TEXT,
    trusted_at TIMESTAMPTZ DEFAULT NOW(),
    last_used TIMESTAMPTZ DEFAULT NOW()
);
```

- Skip 2FA prompt for trusted devices
- List in security tab with "Xóa" button
- Auto-expire after 30 days inactive

---

## DB Migrations Summary

| Migration | Wave | Table |
|-----------|------|-------|
| 022_profile_views.sql | 2 | `profile_views` (viewer_id, viewed_id, created_at) |
| 023_achievements.sql | 3 | `achievements` + `user_achievements` + seed data |
| 024_login_streak.sql | 3 | `ALTER users ADD COLUMN login_streak INT DEFAULT 0, last_login_date DATE` |
| 025_user_2fa.sql | 4 | `user_2fa` (user_id, secret, recovery_codes, enabled) |
| 026_trusted_devices.sql | 4 | `trusted_devices` (user_id, device_name, fingerprint, trusted_at) |

Tất cả additive, không break existing data.

## Dependencies

- Wave 1: independent, no new dependencies
- Wave 2: W2.1 benefits from W3.1 (show achievements in timeline) but can ship without
- Wave 3: independent
- Wave 4: `pyotp` package (pure Python, ~10KB). `qrcode` package hoặc inline SVG

## Exclusions

- **Email notifications** — không có email service, chỉ in-app
- **Push notifications** — cần service worker + FCM, quá nặng
- **OAuth/social login** — phone auth đúng cho VN market
- **Direct messaging** — users dùng Zalo
- **Rich text editor** — thêm XSS surface, VN users prefer photo+plain text

## Verification

Mỗi wave:
1. `python -m pytest -q` — baseline xanh
2. Implement từng item → test → verify
3. `cd web-nuxt && npm run build` — build pass
4. Dev server smoke test
5. `python -m pytest -q` — vẫn xanh
