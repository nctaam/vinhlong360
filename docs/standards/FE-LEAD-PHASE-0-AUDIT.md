# BÁO CÁO KIỂM TOÁN VÀ CHUẨN HÓA FRONTEND TOÀN DIỆN — GIAI ĐOẠN 0 (PHASE 0)
> **STATUS**: active

**Dự án:** VinhLong360 (Cổng thông tin Văn hóa & Du lịch Tỉnh Vĩnh Long)  
**Đơn vị thực hiện:** Frontend Lead & Core Engineering Team  
**Mốc cơ sở (Base Ref):** `0c060e566c14480a8ea8c31f9d90c55b89bf3a3e` (`codex/correction-case-pilot`)  
**Mốc commit hiện tại (Branch: `frontend/lead/foundation`):** `6ee33c35`  
**Ngày hoàn thành:** 04/09/2026  
**Nguyên tắc cốt lõi:** `visual-change: none` (Đóng băng giao diện tuyệt đối; không redesign trái phép, không đổi palette màu, không thêm thư viện UI/Tailwind)

---

## 1. TỔNG QUAN HIỆN TRẠNG & KẾT QUẢ XÁC MINH CƠ SỞ (BASELINE ATTESTATION)

### 1.1. Môi trường độc lập & Hệ thống kiểm thử
- **Isolated Worktree:** Toàn bộ công tác phát triển được cách ly hoàn toàn tại `C:\Users\NCTaam\Documents\vl360-frontend-lead` trên nhánh `frontend/lead/foundation`. Không đụng chạm cây làm việc chính `vinhlong360-correction-case-pilot` của backend.
- **TypeScript Typecheck:** Chạy `npm run typecheck` (`vue-tsc --noEmit`) đạt **EXIT CODE 0 (0 errors)** trên toàn bộ 20 trang và 40+ components.
- **Vitest Unit & Integration Suite:** 
  - Đã cập nhật mốc ghim phiên bản TypeScript `5.9.3` trong `web-nuxt/tests/tri-region-color-contract.test.ts` khớp chính xác với commit base `0c060e56`.
  - Kết quả chạy toàn bộ test suite `npm test`: **134/134 test files PASSED, 2,204/2,204 tests PASSED (100% GREEN)** trong thời gian 70.90s.
- **Hợp đồng API & Drift Check:**
  - `python scripts/check_contract_drift.py`: **0 drift**, hợp đồng OpenAPI tại `contracts/openapi/backend-openapi.json` hoàn toàn đồng bộ với FastAPI backend.
  - `python -m pytest tests/contracts/test_frontend_endpoint_inventory.py`: **6/6 tests PASSED**, xác thực toàn vẹn 227 endpoints trong danh mục `contracts/frontend-endpoints.json`.
- **Nuxt 4 Production Build:**
  - `npm run build`: Hoàn tất biên dịch sạch (`Σ Total size: 7.01 MB / 1.75 MB gzip`), xuất thành công `.output/server/index.mjs` và sinh tệp tin `launch-readiness-manifest.json`.
- **E2E Smoke & Visual Baseline Capture:**
  - `scripts/smoke_e2e_chrome.mjs` chạy qua Headless Chrome:
    - 20/20 routes công khai và nội bộ phản hồi trạng thái `[OK]`, `legacyRuntimeIssueCount: 0`, `journeyRuntimeIssues: 0`.
    - Chụp thành công toàn bộ **60 kịch bản giao diện chuẩn** (6 routes trọng yếu × 2 theme Nocturne/Parchment × 5 viewports từ 375px đến 1440px) và ghi nhận vào `artifacts/visual-baseline/visual-manifest.json` có kèm hàm băm SHA-256 xác thực chống hồi quy thị giác.

---

## 2. PHÂN TÍCH KIẾN TRÚC & NUXT 4 COMPLIANCE

### 2.1. Cấu trúc thư mục & Tuân thủ Nuxt 4
- Mã nguồn đặt trong `web-nuxt/` tuân thủ mô hình thư mục Nuxt 4:
  - `pages/`: 20 tệp route chính thức sử dụng hệ thống định tuyến tệp tin tự động của Vue Router.
  - `components/`: 45+ SFC components được tổ chức theo module chức năng (Community, Itinerary, Search, A11y, v.v.).
  - `composables/`: 32 composables tự động import (`useAuth`, `useCorrectionCases`, `useAI`, `usePublicApi`, v.v.).
  - `assets/css/`: Hệ thống CSS thuần `variables.css` (Nocturne mặc định, Parchment tùy chọn) và `main.css`.
  - `server/`: Các Nitro route bổ trợ (`routes/_internal/launch-readiness.get.ts`, `routes/robots.txt.ts`, `routes/sitemap*.xml.ts`).
- **Phân định SSR vs ClientOnly:**
  - Tiêu chuẩn R30.4 yêu cầu các phần tử dễ biến động hoặc phụ thuộc môi trường trình duyệt (`window`, `localStorage`, `navigator`, `Notification`) phải được bọc trong `<ClientOnly>`.
  - Đa số các khối volatile đã được bao bọc tốt, tuy nhiên vẫn còn một số điểm gọi `localStorage` sớm trong setup script trước khi mounted hoặc cần củng cố hydration guard.

---

## 3. BIÊN GIỚI CONTRACT API & DATA FETCHING LAYER

### 3.1. Phân mảnh tầng giao vận (Transport Layer Fragmentation)
- Toàn dự án hiện có **263 lần gọi `$fetch` trực tiếp** rải rác trong `pages/` và `composables/`.
- Thực trạng:
  - `composables/useAuth.ts` có cung cấp hàm `authFetch`, nhưng nhiều trang vẫn tự lấy token qua `useCookie('vl360_token')` rồi tự lắp thủ công `headers: { Authorization: ... }`.
  - Một số trang gọi trực tiếp `$fetch('/api/...')` tương đối trong ngữ cảnh SSR mà không thông qua base URL chuẩn, vi phạm nguyên tắc SSR-fetch an toàn và có thể gây lỗi hydration nếu server không phân giải được host nội bộ.
- **Quy tắc chuẩn hóa bắt buộc:** Mọi truy vấn từ Frontend sang Backend phải đi qua một API client thống nhất (`apiFetch` / `authFetch` chuẩn) tự động xử lý base URL, credentials, CSRF, timeout, retry theo mã lỗi, và parse kiểu dữ liệu có kiểm soát.

### 3.2. Lỗ hổng Type Safety & Thiếu hụt Codegen
- Toàn bộ thư mục `web-nuxt/types/` hiện được viết tay, không có quy trình tự động sinh type (Codegen) từ `contracts/openapi/backend-openapi.json`.
- Hệ quả:
  - Xuất hiện tràn lan kiểu `any`, `Record<string, any>`, ép kiểu `as any` (điển hình: `types/entity.ts` định nghĩa `EntityAttributes extends Record<string, any>`, `useAI.ts:92` `$fetch<any>`, `pages/cai-dat.vue` 24 lời gọi `$fetch` với kiểu `any[]`).
  - Khi backend thay đổi hoặc bổ sung trường dữ liệu trong schema OpenAPI, frontend không thể phát hiện lỗi gãy schema lúc biên dịch.

---

## 4. CÁC PHÁT HIỆN NGHIÊM TRỌNG (CRITICAL FINDINGS)

### 4.1. [MỨC ĐỘ P0] Che giấu lỗi hệ thống 503 (Error Masking Violation)
- **Vị trí 1:** `web-nuxt/pages/cong-dong.vue` (dòng 329–333 và 1039–1042):
  ```ts
  // HIỆN TRẠNG SAI PHẠM:
  // Khi Backend PostgreSQL hoặc Feed API trả về 503 Service Unavailable,
  // trang bắt lỗi và hiển thị Empty State "Cộng đồng sắp mở" thay vì thông báo lỗi máy chủ.
  <EmptyState icon-name="sparkles" title="Cộng đồng sắp mở" />
  ```
  *Hậu quả:* Người dùng và đội vận hành hiểu nhầm tính năng chưa ra mắt thay vì phát hiện sự cố hạ tầng cơ sở dữ liệu. Vi phạm trực tiếp Tiêu chuẩn §12.4 về tính trung thực của giao diện trạng thái.
- **Vị trí 2:** `web-nuxt/pages/bai-viet/[id].vue` (dòng 173):
  Bắt chung mọi mã lỗi HTTP 500, 503, 429 thành một thông báo mập mờ: `"Lỗi kết nối. Vui lòng thử lại."`, không phân biệt lỗi quá tải (429), lỗi bảo trì (503), hay lỗi không tìm thấy (404).

### 4.2. [MỨC ĐỘ P1] Vi phạm vòng đời Vue 3 Lifecycle Hook (Memory Leak & Warning)
- **Vị trí:**
  - `web-nuxt/pages/bai-viet/[id].vue` (dòng 130–155)
  - `web-nuxt/pages/dia-diem/[id].vue` (dòng 145–180)
  - `web-nuxt/pages/nguoi-dung/[id].vue` (dòng 120–140)
- **Bản chất lỗi:**
  Trong cú pháp `<script setup>`, các hook vòng đời `onMounted`, `onBeforeUnmount` được khai báo **sau câu lệnh `await useAsyncData(...)`** ở cấp cao nhất (top-level await).
- **Hậu quả:**
  Vue 3 gắn hook vòng đời dựa trên instance hiện hành của component (`getCurrentInstance()`). Khi luồng thực thi gặp `await`, ngữ cảnh instance của component bị mất sau khi promise trả về, dẫn tới cảnh báo từ Vue engine:
  `[Vue warn]: onMounted is called when there is no active component instance to be associated with.`
  Các listener sự kiện bàn phím hoặc scroll không được dọn dẹp lúc component unmount, gây rò rỉ bộ nhớ (memory leaks).
- **Vị trí phụ:** `composables/useCorrectionCases.ts` (dòng 419–424) gọi `onScopeDispose` mà chưa kiểm tra `getCurrentScope()`.

### 4.3. [MỨC ĐỘ P1] Luồng AI Chat & Streaming thiếu an toàn
- **Vị trí:** `web-nuxt/composables/useAI.ts`
- **Khuyết tật:**
  - Bắt nuốt lỗi âm thầm (`catch { return '' }`), khiến người dùng không biết hệ thống bị giới hạn tốc độ (429 Rate Limit) hay lỗi dịch vụ AI (503).
  - Hàm stream `aiStream()` chưa hỗ trợ `AbortSignal`, khiến client không thể hủy truy vấn khi người dùng chuyển trang hoặc nhấn nút dừng.

### 4.4. [MỨC ĐỘ P2] Nợ kỹ thuật các Component khổng lồ ("God Objects")
Các tệp SFC quá dài, gộp chung hàng chục trách nhiệm xử lý nghiệp vụ, giao diện, và thao tác dữ liệu:
1. `web-nuxt/pages/tao-lich-trinh.vue`: **2,083 dòng**
2. `web-nuxt/pages/cong-dong.vue`: **1,981 dòng**
3. `web-nuxt/pages/cai-dat.vue`: **1,792 dòng**
4. `web-nuxt/pages/dia-diem/[id].vue`: **1,326 dòng**
*Giải pháp:* Lên kế hoạch bóc tách có kiểm soát thành các sub-components thuần túy trình bày, giữ nguyên 100% hợp đồng prop và CSS scoped.

---

## 5. ĐÁNH GIÁ THIẾT KẾ TRI-REGION & ĐỘ TƯƠNG PHẢN (A11Y & DESIGN TOKENS)

### 5.1. Hệ thống Token & CSS Variables
- Toàn bộ màu sắc và quy tắc trình bày tuân theo `web-nuxt/assets/css/variables.css`.
- Đã được bảo vệ nghiêm ngặt bởi 78 bài kiểm tra tự động trong `tri-region-color-contract.test.ts`:
  - Khóa chặt mọi ghi đè CSS trái phép ở cấp root hoặc selector phức tạp.
  - Đảm bảo độ tương phản semantic đạt chuẩn WCAG 2.1 AA (tối thiểu 4.5:1 cho văn bản thông thường, 3:1 cho tiêu đề lớn và điều khiển giao diện).
  - Nghiêm cấm đặt màu hex/rgb trực tiếp trong thẻ `<style>` của các tệp `.vue` (Tiêu chuẩn R30.3).

### 5.2. Kết quả kiểm toán Accessibility (A11y)
- Chạy kịch bản `npm run check:public-accessibility` qua Headless Chrome:
  - `forcedColorsActive: true`, `forcedControlBorderVisible: true` (Tương thích hoàn hảo chế độ tương phản cao của Windows).
  - `controlsBelow44: 0` (100% điều khiển đáp ứng kích thước chạm tối thiểu 44×44px theo R30.5).
  - `contrastViolations: 0` (Không có bất kỳ vi phạm tương phản màu sắc nào).
  - `lcpMs: 508ms` (Thời gian tải nội dung lớn nhất cực nhanh, đạt chuẩn Core Web Vitals < 2.5s).
  - `cls: 0.0109` (Độ lệch bố cục gần như bằng 0, đạt chuẩn < 0.1).
  - `inpMs: 0ms` (Độ phản hồi tương tác mượt mà, đạt chuẩn < 200ms).

---

## 6. NỢ BUNDLE & CORE PERFORMANCE (R30.7)

- `bundleTotalGzKb: 880 kB gzip`
- `bundleCssGzKb: 221 kB gzip`
- Cảnh báo: `bundle-budget-exceeded` (vượt ngưỡng mục tiêu 200 kB gzip entry).
- **Hiện trạng pháp lý kỹ thuật:** Khoản nợ này đã được ghi nhận chính thức tại `docs/standards/90-exceptions-log.md` (chủ yếu do tích hợp thư viện bản đồ MapLibre GL và các bộ icon SVG nội tuyến). Việc tối ưu phân mảnh bundle (code-splitting và lazy loading các component nặng như bản đồ) được xếp vào Giai đoạn 2 để không làm gián đoạn độ ổn định nền tảng.

---

## 7. BẢNG ĐỐI CHIẾU VISUAL BASELINE (60 KỊCH BẢN THỊ GIÁC ĐÃ CHỤP)

Toàn bộ hình ảnh kiểm chuẩn đã được tạo và lưu trữ tại `artifacts/visual-baseline/`:
| Tuyến đường (Route) | Khóa (Key) | Viewport | Theme | Trạng thái (State) | Tệp tin minh chứng |
|---|---|---|---|---|---|
| `/` | `home` | 375px, 390px, 768px, 1024px, 1440px | Nocturne / Parchment | ready | `home__*__ready.png` (10 tệp) |
| `/du-lich` | `tourism` | 375px, 390px, 768px, 1024px, 1440px | Nocturne / Parchment | ready | `tourism__*__ready.png` (10 tệp) |
| `/tim-kiem` | `search` | 375px, 390px, 768px, 1024px, 1440px | Nocturne / Parchment | ready | `search__*__ready.png` (10 tệp) |
| `/ban-do` | `map` | 375px, 390px, 768px, 1024px, 1440px | Nocturne / Parchment | ready | `map__*__ready.png` (10 tệp) |
| `/dia-diem/gom-do-mang-thit` | `detail` | 375px, 390px, 768px, 1024px, 1440px | Nocturne / Parchment | ready | `detail__*__ready.png` (10 tệp) |
| `/tao-lich-trinh` | `planner` | 375px, 390px, 768px, 1024px, 1440px | Nocturne / Parchment | ready | `planner__*__ready.png` (10 tệp) |

*Ghi chú:* Mỗi ảnh được sinh kèm hàm băm SHA-256 đối chiếu tự động trong `visual-manifest.json`. Mọi thay đổi mã nguồn trong các giai đoạn tiếp theo nếu làm thay đổi pixel của các giao diện trên sẽ bị chặn lập tức trong quy trình CI.

---

## 8. LỘ TRÌNH THỰC THI CHUẨN HÓA

### Giai đoạn 1: Chuẩn hóa Nền tảng & Vá lỗi Nghiêm trọng (Foundation & Critical Fixes)
1. **Khắc phục lỗi P0 Error Masking:**
   - Cập nhật `pages/cong-dong.vue`: Khi gặp mã 503, hiển thị thông báo gián đoạn dịch vụ kèm nút thử lại trung thực, không hiển thị empty state "sắp mở".
   - Cập nhật `pages/bai-viet/[id].vue`: Bắt chi tiết mã lỗi 404/429/503/500 và phản hồi thông điệp chính xác.
2. **Sửa lỗi P1 Vue 3 Lifecycle Order:**
   - Di chuyển toàn bộ khai báo `onMounted`, `onBeforeUnmount` lên trước `await useAsyncData` trong `bai-viet/[id].vue`, `dia-diem/[id].vue`, `nguoi-dung/[id].vue`.
   - Bọc guard `if (getCurrentScope())` cho `onScopeDispose` trong `composables/useCorrectionCases.ts`.
3. **Cải tiến luồng AI Chat Stream:**
   - Bổ sung `AbortSignal` cho `useAI.ts:aiStream()` và truyền đạt minh bạch lỗi 429/503.
4. **Xây dựng Boundary API Type-Safe:**
   - Thiết lập cơ chế sinh/dẫn xuất TypeScript types tự động từ `contracts/openapi/backend-openapi.json`.
   - Bọc API client chuẩn hóa thay thế dần các lời gọi `$fetch` trần thiếu kiểm soát.

### Giai đoạn 2: Tối ưu Hóa & Bóc tách Component (Decomposition & Performance)
1. Bóc tách các tệp God Object (`tao-lich-trinh.vue`, `cong-dong.vue`, `cai-dat.vue`).
2. Tối ưu code-splitting cho MapLibre GL và các module kích thước lớn nhằm đưa bundle về gần ngưỡng ngân sách R30.7.

### Giai đoạn 3: Kiểm thử Chuyên sâu & Chuyển giao
1. Bổ sung các bài test hồi quy giao diện tự động.
2. Hoàn thiện tài liệu kiến trúc bàn giao và chuẩn bị hồ sơ nghiệm thu.
