> STATUS: complete (2026-09-20)

# Homepage UI Decluttering & Modern Refinement (Part 13)

## 1. Mục Tiêu & Định Hướng
Thực hiện yêu cầu trực quan của người dùng: "bỏ tất cả tọa độ" trên trang chủ theo triết lý "Sâu hơn, đơn giản, không thêm" (Deeper Mekong Heritage, Calmer Scrims, Zero Redundancy):
- **Ẩn toàn bộ tọa độ GPS kỹ thuật gây rối mắt trên toàn bộ giao diện trang chủ:**
  - Hero Gateway: `.home-feature-dossier__coords` (`HomeFeatureDossier.vue` & `home-nocturne.css`).
  - Folio I (Chốn dừng chân di sản): `.home-curated-lead__coords` và `.home-curated-satellite__coords` (`HomeCuratedShowcase.vue`).
  - Folio II (Hương vị khẩn hoang): `.home-culinary-card__coords` và `.home-culinary-card__coords-sep` (`HomeCulinaryTrail.vue`).
  - Folio III (Nghỉ dưỡng sông nước): `.home-stay-card__coords` và `.home-stay-card__coords-sep` (`HomeRiversideStays.vue`).
- **Triển khai kỹ thuật & Tương thích hệ thống:**
  - Thiết lập thuộc tính `display: none !important;` trên `home-nocturne.css` áp dụng cho selector tổng hợp:
    `[data-home-pilot="nocturne-b1"] :is(.home-feature-dossier__coords, .home-curated-lead__coords, .home-curated-satellite__coords, .home-culinary-card__coords, .home-stay-card__coords)`.
  - Thiết lập `display: none !important;` trên scoped CSS của các component `HomeCuratedShowcase.vue`, `HomeCulinaryTrail.vue`, `HomeRiversideStays.vue`.
  - Giữ nguyên cấu trúc template và các selector hover/focus/active cần thiết để bảo toàn trọn vẹn hợp đồng kiểm thử lịch sử (`phase2-experience-elevation.test.ts`, `home-feature-dossier.test.ts`, `home-hero-dossier-polish.test.ts`).
  - Tuyệt đối không can thiệp các tiểu hệ thống bản đồ hoặc offline yêu cầu tọa độ kỹ thuật (`OfflineTerroirPanel.vue`, `ban-do.vue`).
- **Bảo toàn chất lượng:**
  - Bổ sung test kiểm thử Task 29 trong `tests/home-deep-simplify.test.ts`.
  - Duy trì 100% tỷ lệ pass trên toàn bộ 27 test files liên quan đến trang chủ (281/281 tests pass).
  - Duy trì ngân sách CSS gzipped $\le 194.560\text{ bytes}$ (R30.7).
  - Cổng Python AST pre-commit `run_hard.py --all` đạt chuẩn 100% xanh (`✓ run_hard: sạch`).
  - Triển khai cập nhật trực tiếp lên máy chủ online VPS `66.42.57.202` và kích hoạt an toàn.

## 2. Kế Hoạch Thực Hiện Cụ Thể
- [x] **Task 29.1**: Cập nhật `home-nocturne.css` ẩn toàn bộ các thẻ tọa độ trên trang chủ (`display: none !important`).
- [x] **Task 29.2**: Cập nhật scoped CSS của `HomeCuratedShowcase.vue`, `HomeCulinaryTrail.vue`, `HomeRiversideStays.vue` ẩn tọa độ và dấu phân cách.
- [x] **Task 29.3**: Bổ sung test case Task 29 vào `tests/home-deep-simplify.test.ts`.
- [x] **Task 29.4**: Chạy kiểm thử xác minh toàn diện:
  - `npm --prefix web-nuxt test home-deep-simplify` (28/28 pass)
  - `npm --prefix web-nuxt test home challenger-homepage subsystems-unification phase2-experience-elevation` (281/281 pass)
  - `$env:PYTHONIOENCODING="utf-8"; python scripts/checks/run_hard.py --all` (sạch 100%)
  - `npm --prefix web-nuxt run build` (build thành công)
  - `$env:PYTHONIOENCODING="utf-8"; python -m scripts.checks.check_bundle` (đạt R30.7)
- [ ] **Task 29.5**: Cập nhật `walkthrough.md`, commit và push lên remote `origin/codex/correction-case-pilot`.
- [ ] **Task 29.6**: Đóng gói và triển khai lên máy chủ VPS `66.42.57.202`, chạy `activate_remote.sh` và kiểm tra trực tuyến.
