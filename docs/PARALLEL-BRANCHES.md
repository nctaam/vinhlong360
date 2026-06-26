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

| # | Branch | Worktree | Scope |
|---|--------|----------|-------|
| 1 | `dev/public-front` | `C:/Code/vinhlong360/vl360-public-front` | Homepage + catalog + static pages |
| 2 | `dev/public-detail` | `C:/Code/vinhlong360/vl360-public-detail` | Entity detail + ward/area + directory |
| 3 | `dev/interactive` | `C:/Code/vinhlong360/vl360-interactive` | Map + search + itinerary + chat |
| 4 | `dev/admincp` | `C:/Code/vinhlong360/vl360-admincp` | Admin CMS |
| 5 | `dev/usercp` | `C:/Code/vinhlong360/vl360-usercp` | User profile + community + notifications |
| 6 | `dev/backend-security` | `C:/Code/vinhlong360/vl360-backend-sec` | Auth/moderation hardening |
| 7 | `dev/backend-resilience` | `C:/Code/vinhlong360/vl360-backend-res` | LLM pipeline resilience |
| 8 | `dev/data-seo` | `C:/Code/vinhlong360/vl360-data-seo` | SEO + data validation scripts |
| 9 | `dev/shared-fe` | `C:/Code/vinhlong360/vl360-shared-fe` | Shared FE: layouts, composables, CSS, components |
| 10 | `dev/backend-infra` | `C:/Code/vinhlong360/vl360-backend-infra` | Backend core + scripts + legacy cleanup |

---

## Merge order

1. `dev/data-seo` → main
2. `dev/backend-infra` → main
3. `dev/backend-security` → main
4. `dev/backend-resilience` → main
5. `dev/shared-fe` → main
6. `dev/public-front` → main
7. `dev/public-detail` → main
8. `dev/interactive` → main
9. `dev/usercp` → main
10. `dev/admincp` → main

---

## Cách mở session

Trong Claude Desktop: mở terminal tại thư mục worktree rồi chạy `claude`.

Paste handoff prompt tương ứng (`docs/handoff-*.md`) làm message đầu tiên.
