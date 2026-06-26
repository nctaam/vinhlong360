# Handoff: Session UserCP (`dev/usercp`)

> Paste toàn bộ nội dung này làm message đầu tiên trong session Claude Code mới.

---

## Bối cảnh

Bạn đang làm trên nhánh `dev/usercp` của dự án vinhlong360 — MXH du lịch/OCOP cho Vĩnh Long (3 tỉnh sáp nhập). Solo dev, Nuxt 4 SSR + FastAPI. **Đọc `CLAUDE.md` và `docs/PARALLEL-BRANCHES.md` trước khi bắt đầu.**

## Nhánh hiện tại

```bash
git checkout dev/usercp
```

## Phạm vi file bạn SỞ HỮU (chỉ sửa các file này)

- `web-nuxt/pages/cai-dat.vue`
- `web-nuxt/pages/cong-dong.vue`
- `web-nuxt/pages/nguoi-dung/[id].vue`
- `web-nuxt/pages/bai-viet/[id].vue`
- `web-nuxt/pages/thong-bao.vue`
- `web-nuxt/components/PostCard.vue`
- `web-nuxt/components/NotificationBell.vue`
- `web-nuxt/components/AuthModal.vue`
- `web-nuxt/composables/useNotifications.ts`
- `agent/social.py`, `agent/auth.py`, `agent/notifications.py` (additive — chỉ thêm, không sửa logic hiện tại)

**KHÔNG SỬA:** `base.css`, `nuxt.config.ts`, `database.py` (trừ migration mới), `server.py`, file admin/, file public pages.

## Công việc

### Từ deep upgrade plan (ưu tiên cao):

1. **A2d — Notification preferences**:
   - **Migration mới** (`agent/migrations/XXX_notification_preferences.sql`): tạo bảng `notification_preferences` (user_id FK, pref_like BOOL DEFAULT true, pref_comment BOOL DEFAULT true, pref_mention BOOL DEFAULT true, pref_follow BOOL DEFAULT true, pref_system BOOL DEFAULT true)
   - **Backend** (`agent/notifications.py`): `GET/PUT /api/notification-preferences` + gate trong `create_notification()` — check pref trước khi tạo notification
   - **Frontend** (`cai-dat.vue`): tab "Thông báo" — toggle switches cho từng loại (thích, bình luận, nhắc đến, theo dõi, hệ thống)
   - **Lưu ý:** UGC = Postgres-only (§1.3). Migration phải là PostgreSQL DDL.

### Tự audit thêm:
- Profile page: kiểm tra empty states, loading states, error states
- Community page: compose UX, filter UX, infinite scroll performance
- Settings page: kiểm tra tất cả tab hoạt động đúng
- Notification page: grouping hiển thị đúng, mark-as-read hoạt động
- PostCard: interaction feedback (like animation, bookmark confirmation)
- Comment/reply flow: focus management, error handling
- Auth flow: modal UX, redirect after login

## Lưu ý kỹ thuật

- `social.py` rất lớn (~1000 LOC) — chỉ thêm code mới, không refactor code hiện tại
- `cai-dat.vue` đã có tab layout (Hồ sơ / Bảo mật / Giao diện / Nguy hiểm) — thêm tab "Thông báo"
- Notification system đã có SSE + polling 30s — không cần thay đổi transport
- Block enforcement đã implement — không cần sửa

## Verify

```bash
python -m pytest -q                    # backend xanh
cd web-nuxt && npm run build           # FE build OK
```

## Commit convention

```
[usercp] mô tả ngắn

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```
