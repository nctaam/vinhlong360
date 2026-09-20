> STATUS: complete (2026-09-20)

# Homepage UI Decluttering & Modern Refinement (Part 12)

## 1. Mục Tiêu & Định Hướng
Tiếp tục chuỗi hoàn thiện giao diện trang chủ Vĩnh Long 360 theo triết lý "Sâu hơn, đơn giản, không thêm" (Deeper Mekong Heritage, Calmer Scrims, Zero Redundancy):
- **Đồng bộ hóa nhãn liên kết đề mục (Folio See-All Links):**
  - Folio II (`HomeCulinaryTrail.vue`): Rút gọn từ `Xem trọn 120 món ngon di sản` thành `120 món ngon di sản`.
  - Folio III (`HomeRiversideStays.vue`): Rút gọn từ `Xem toàn bộ 164 nơi lưu trú` thành `164 nơi lưu trú`.
  - Folio III (`HomeTravelPlanner.vue`): Rút gọn từ `Xem trọn 16 lịch trình` thành `16 lịch trình thong dong` (đồng bộ hoàn hảo với Folio V `HomeContinuation.vue`).
- **Tinh giản nhãn & loại bỏ dấu thừa trong `HomeTravelPlanner.vue`:**
  - Tiêu đề chặng dừng: Bỏ dấu hai chấm thừa `Các chặng dừng chân nổi bật:` -> `Các chặng dừng chân nổi bật`.
  - Nhãn nút hành động: Rút gọn `Xem chi tiết lộ trình` -> `Chi tiết lộ trình`; `Tùy chỉnh lịch trình riêng` -> `Tùy chỉnh lịch trình`.
  - Dọn dẹp imports chết: Xóa bỏ `import SourceMark from '~/components/SourceMark.vue'` và `import FreshnessLine from '~/components/FreshnessLine.vue'` không hề được dùng.
- **Bảo toàn chất lượng:**
  - Bổ sung test kiểm thử Task 28 trong `tests/home-deep-simplify.test.ts`.
  - Duy trì 100% tỷ lệ pass trên toàn bộ 26 test suites trang chủ (267/267 tests pass).
  - Duy trì ngân sách CSS gzipped $\le 194.560\text{ bytes}$ (R30.7) với headroom an toàn $\ge +1.400\text{ bytes}$.
  - Cổng Python AST pre-commit `run_hard.py --all` đạt chuẩn 100% xanh.

## 2. Kế Hoạch Thực Hiện Cụ Thể
- [ ] **Task 28.1**: Cập nhật `HomeCulinaryTrail.vue` (rút gọn see-all link).
- [ ] **Task 28.2**: Cập nhật `HomeRiversideStays.vue` (rút gọn see-all link).
- [ ] **Task 28.3**: Cập nhật `HomeTravelPlanner.vue` (rút gọn see-all link, tiêu đề chặng dừng, nút hành động, xóa unused imports).
- [ ] **Task 28.4**: Cập nhật `tests/home-deep-simplify.test.ts` với test case Task 28.
- [ ] **Task 28.5**: Chạy toàn bộ kiểm thử xác minh:
  - `npm --prefix web-nuxt test home-deep-simplify`
  - `npm --prefix web-nuxt test home challenger-homepage subsystems-unification`
  - `npm --prefix web-nuxt run build`
  - `python -m scripts.checks.check_bundle`
  - `$env:PYTHONIOENCODING="utf-8"; python scripts/checks/run_hard.py --all`
- [ ] **Task 28.6**: Cập nhật `walkthrough.md`, commit và push lên remote.
