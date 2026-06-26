# Parallel Worktree Strategy — vinhlong360

> Tạo 2026-06-26. 10 session song song qua **git worktree** (mỗi session = thư mục riêng).
> **Merge flow:** branch → main (build+test xanh). KHÔNG merge chéo giữa dev branches.

---

## Quy tắc chung

1. **Đọc `CLAUDE.md` trước** — mọi bất biến §2 vẫn áp dụng.
2. **Chỉ sửa file trong phạm vi SỞ HỮU** — file ngoài scope là READ-ONLY.
3. **Build + test trước merge:** `python -m pytest -q` + `cd web-nuxt && npm run build`
4. **Commit message prefix:** `[tên-session]`
5. **Additive-first (§B2):** thêm mới → verify → xoá cũ.
6. **nuxt.config.ts / server.py** — KHÔNG sửa.
7. **base.css** — chỉ session `shared-fe` được sửa.

---

## 10 Session

| # | Tên | Nhánh | Thư mục | Phạm vi tác động |
|---|------|-------|---------|-----------------|
| 1 | **Trang chủ & Danh mục** | `dev/public-front` | `vl360-public-front` | Homepage, catalog (du lịch/SP/OCOP/lễ hội/sự kiện/theo mùa), trang tĩnh, EntityCard |
| 2 | **Chi tiết & Thư mục** | `dev/public-detail` | `vl360-public-detail` | Chi tiết địa điểm, xã/phường, khu vực, danh bạ HC, tuyến đường, lưu trú |
| 3 | **Bản đồ & Lịch trình** | `dev/interactive` | `vl360-interactive` | Bản đồ, tìm kiếm, tạo lịch trình, chat AI, khám phá, bảng xếp hạng |
| 4 | **Quản trị** | `dev/admincp` | `vl360-admincp` | Toàn bộ admin/**: dashboard, entity CRUD, kiểm duyệt, thống kê, media, CMS |
| 5 | **Tài khoản & Cộng đồng** | `dev/usercp` | `vl360-usercp` | Cài đặt, cộng đồng, hồ sơ, bài viết, thông báo, auth composable |
| 6 | **Bảo mật API** | `dev/backend-security` | `vl360-backend-sec` | Middleware xác thực, rate limit, kiểm duyệt nội dung, test bảo mật |
| 7 | **Chịu lỗi AI** | `dev/backend-resilience` | `vl360-backend-res` | Toàn bộ pipeline chat AI: orchestrator, knowledge, guardrails, memory, proactive, recommender, prompt cache/compiler, semantic cache, reflexion, agentic RAG, dynamic agents, smart rank, autocorrect |
| 8 | **Dữ liệu & SEO** | `dev/data-seo` | `vl360-data-seo` | Scripts kiểm tra dữ liệu, SEO (JSON-LD/sitemap/og), data.json |
| 9 | **Khung giao diện** | `dev/shared-fe` | `vl360-shared-fe` | Layout, CSS tokens, shared component (Toast/Confirm/Skeleton...), composable chung |
| 10 | **Hạ tầng Backend** | `dev/backend-infra` | `vl360-backend-infra` | Database core, cache, storage, config, scheduler, self-evolve/eval chain, KB versioning, feature modules (itinerary_gen/saved/visits/plans/analytics/site_settings/cost_tracker/ab_testing), geocode, dead code cleanup |

---

## Thứ tự merge

1. **Dữ liệu & SEO** (`dev/data-seo`) → main
2. **Hạ tầng Backend** (`dev/backend-infra`) → main
3. **Bảo mật API** (`dev/backend-security`) → main
4. **Chịu lỗi AI** (`dev/backend-resilience`) → main
5. **Khung giao diện** (`dev/shared-fe`) → main
6. **Trang chủ & Danh mục** (`dev/public-front`) → main
7. **Chi tiết & Thư mục** (`dev/public-detail`) → main
8. **Bản đồ & Lịch trình** (`dev/interactive`) → main
9. **Tài khoản & Cộng đồng** (`dev/usercp`) → main
10. **Quản trị** (`dev/admincp`) → main

---

## Cách mở session (Claude Desktop)

1. Mở Claude Desktop → New conversation
2. **Add folder** → chọn thư mục worktree (VD: `C:\Code\vinhlong360\vl360-public-front`)
3. Paste nội dung file handoff tương ứng (`docs/handoff-*.md`) làm message đầu tiên
