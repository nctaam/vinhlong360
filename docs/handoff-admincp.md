# Session 4: AdminCP — Admin CMS

> Paste toàn bộ nội dung này làm message đầu tiên.

## Bối cảnh

Worktree `C:/Code/vl360-admincp`, nhánh `dev/admincp`. Dự án vinhlong360. **Đọc `CLAUDE.md` + `docs/PARALLEL-BRANCHES.md`.**

## Phạm vi file SỞ HỮU

**Pages:**
- `web-nuxt/pages/admin/index.vue` — Dashboard
- `web-nuxt/pages/admin/entities.vue` — Entity CRUD
- `web-nuxt/pages/admin/kiem-duyet.vue` — Moderation
- `web-nuxt/pages/admin/duyet-anh.vue` — Image review
- `web-nuxt/pages/admin/data-quality.vue` — Data quality
- `web-nuxt/pages/admin/thong-ke.vue` — Analytics
- `web-nuxt/pages/admin/users.vue` — User management
- `web-nuxt/pages/admin/nhat-ky.vue` — Audit log
- `web-nuxt/pages/admin/media.vue` — Media library
- `web-nuxt/pages/admin/ai.vue` — AI tools
- `web-nuxt/pages/admin/bao-cao.vue`, `lich-trinh.vue`, `danh-ba.vue`, `chua-phan-loai.vue`, `duyet-tu-hoc.vue`
- `web-nuxt/pages/admin/cai-dat/**` — Admin settings (CMS)

**Components + Layout:**
- `web-nuxt/layouts/admin.vue`
- `web-nuxt/components/CommandPalette.vue`
- `web-nuxt/components/admin/**`

**Backend (additive only):**
- `agent/admin.py`

**KHÔNG SỬA:** base.css, default.vue layout, user pages, public pages, server.py.

## Công việc

### Deep upgrade (còn lại):
- [ ] **B7b** Bulk relationship add — `POST /admin/relationships/bulk` + textarea UI

### Audit 10 tầng admin pages:
- T1: CRUD hoạt động, form validate, error handling
- T3: Batch operations, keyboard shortcuts
- T4: Focus trap modals, ARIA labels, form a11y
- T8: Error states cho API calls, loading spinners
- T9: Responsive sidebar collapse, table scroll

**Đã xong:** B2e, B8c, B2a, B1d, B2c, B3d, B4a/B4b, B1f.

## Verify

```bash
python -m pytest -q
cd web-nuxt && npm run build
```

## Commit prefix: `[admincp]`
