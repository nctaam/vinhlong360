# Session 5: Tài khoản & Cộng đồng
<!-- Phạm vi: Cài đặt tài khoản, cộng đồng (feed/bài viết), hồ sơ người dùng, thông báo + component riêng (PostCard, AuthModal, UserMenu, NotificationBell...) + composable auth/notification/draft -->

> Paste toàn bộ nội dung này làm message đầu tiên.

## Bối cảnh

Worktree `C:/Code/vinhlong360/vl360-usercp`, nhánh `dev/usercp`. Dự án vinhlong360. **Đọc `CLAUDE.md` + `docs/PARALLEL-BRANCHES.md`.**

## Phạm vi file SỞ HỮU

**Pages:**
- `web-nuxt/pages/cai-dat.vue` — Settings (tabbed)
- `web-nuxt/pages/cong-dong.vue` — Community feed
- `web-nuxt/pages/nguoi-dung/[id].vue` — User profile
- `web-nuxt/pages/bai-viet/[id].vue` — Post detail
- `web-nuxt/pages/thong-bao.vue` — Notifications

**Components:**
- `PostCard.vue`, `NotificationBell.vue`, `AuthModal.vue`
- `UserMenu.vue`, `UserCoverPlaceholder.vue`, `AvatarPlaceholder.vue`
- `ReportModal.vue`, `OnboardingSheet.vue`

**Composables:**
- `useNotifications.ts`, `useAuth.ts`, `useAuthModal.ts`
- `useDrafts.ts`, `useReport.ts`, `useRepost.ts`
- `useMentionAutocomplete.ts`

**Backend (additive only):**
- `agent/social.py`, `agent/auth.py`, `agent/notifications.py`

**KHÔNG SỬA:** base.css, layouts/, admin/**, public pages, server.py, database.py.

## Công việc

### Đã xong:
- A2d notification preferences (API + FE + migration 021 + tests)
- A2e tabbed settings, A5b notification grouping

### Audit 10 tầng:
- T1: Auth flow, compose/edit post, comment/reply, follow, block
- T2: Empty states (no posts, no notifications, new user)
- T3: Compose UX, feed interaction, settings completeness
- T4: Focus management (modal trap, compose focus), keyboard nav
- T7: Block enforcement, XSS prevention in user content
- T8: Loading/error states cho feed, profile, notifications
- T9: Mobile compose, touch-friendly interactions

**Lưu ý:**
- `social.py` ~1000 LOC — chỉ thêm, không refactor
- UGC = Postgres-only (§1.3) — cần `docker compose up postgres` cho dev
- Block enforcement đã implement

## Verify

```bash
python -m pytest -q
cd web-nuxt && npm run build
```

## Commit prefix: `[usercp]`
