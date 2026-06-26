# Handoff: Session AdminCP (`dev/admincp`)

> Paste toàn bộ nội dung này làm message đầu tiên trong session Claude Code mới.

---

## Bối cảnh

Bạn đang làm trên nhánh `dev/admincp` của dự án vinhlong360 — MXH du lịch/OCOP cho Vĩnh Long (3 tỉnh sáp nhập). Solo dev, Nuxt 4 SSR + FastAPI. **Đọc `CLAUDE.md` và `docs/PARALLEL-BRANCHES.md` trước khi bắt đầu.**

## Nhánh hiện tại

```bash
git checkout dev/admincp
```

## Phạm vi file bạn SỞ HỮU (chỉ sửa các file này)

- `web-nuxt/pages/admin/**` (trừ `admin/index.vue` — shared)
- `web-nuxt/layouts/admin.vue`
- `web-nuxt/components/CommandPalette.vue`
- `agent/admin.py` (chỉ thêm endpoint mới, không sửa hiện tại)

**KHÔNG SỬA:** `base.css`, `nuxt.config.ts`, `database.py`, `server.py`, bất kỳ file nào ngoài phạm vi trên.

## Công việc

### Từ deep upgrade plan (ưu tiên cao):

1. **B2e — Rich summary editor** trong entity editor (`admin/entities.vue`):
   - Character counter cho textarea summary (hiển thị `{count}/500`)
   - Toggle button markdown preview (render summary thành HTML xem trước)
   - Giữ textarea hiện tại, chỉ thêm counter + preview toggle

2. **B7b — Bulk relationship add** (`admin/entities.vue` hoặc panel mới):
   - Backend: `POST /admin-api/relationships/bulk` nhận `{source_id, targets: [{target_id, rel_type}]}`
   - Frontend: textarea cho admin paste nhiều entity ID + chọn loại quan hệ → tạo hàng loạt
   - Validate: entity tồn tại, không duplicate, không self-loop

3. **B8c — Contextual help tooltips**:
   - CSS-only `?` icon (`.help-tip`) cạnh các thuật ngữ admin khó hiểu
   - Áp dụng cho: data quality buckets, moderation status, entity completeness score
   - Tooltip hiện bằng `:hover` / `:focus`, không cần JS

### Tự audit thêm:
- Mở từng trang admin, tìm UX pain point
- Cải thiện entity editor workflow
- Media library: thêm sort/filter nếu thiếu
- Moderation: keyboard shortcuts nếu chưa có
- Dashboard: cải thiện visual hierarchy

## Verify

```bash
python -m pytest -q                    # backend xanh
cd web-nuxt && npm run build           # FE build OK
```

## Commit convention

```
[admincp] mô tả ngắn

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```
