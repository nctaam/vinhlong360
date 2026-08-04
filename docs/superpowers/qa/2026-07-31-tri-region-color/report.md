# Báo cáo đóng cổng chất lượng Tri-Region Color Excellence

> STATUS (2026-08-04): complete — closure evidence for exact code HEAD 074b4210.

## Kết luận và quan hệ revision

`PASS` — toàn bộ cổng tự động và ma trận thị giác `16/16` đã được chấp nhận.

- Ảnh và bằng chứng runtime được chụp trên code HEAD chính xác `074b42101b47903b142099589a8d80fb25253139` (`074b4210`) của nhánh `codex/tri-region-color`.
- Commit closure chứa báo cáo này là commit con trực tiếp của `074b4210`; commit đó chỉ lưu bằng chứng QA, ba artifact debt/ratchet và hai dòng trạng thái, không thay đổi logic production hoặc test đã được chụp.
- Vì SHA của một commit không thể tự nằm trong nội dung của chính commit đó, SHA closure cuối cùng được ghi trong git history và báo cáo SDD `task-7-closure-commit-074b421-report.md`.
- Nguồn runtime chung là bản Nuxt/Nitro build đúng revision, backend mới ở chế độ SQLite, cache trình duyệt tắt và profile Chrome mới cho từng trạng thái. Không cài dependency và không dùng mock UI.

## Fixture nguồn

| Mã fixture | Route | Nội dung định danh | Tương tác dữ liệu |
|---|---|---|---|
| `home-sqlite` | `/` | H1 `Vu Lan bên sông, chùa cổ và món chay` | Dữ liệu Homepage thật từ backend SQLite |
| `discovery-sqlite` | `/du-lich` | H1 `Ba tỉnh, một nhịp sông. Khám phá theo mùa nước, theo mùa trái, theo mùa lễ.` | Chuyển mode thật từ `Trải nghiệm` sang `Ẩm thực` |
| `search-sqlite` | `/tim-kiem` | H1 `Tìm kiếm` | Nhập `dừa`, submit thật tới `/tim-kiem?q=d%E1%BB%ABa` |
| `detail-an-hoi-sqlite` | `/dia-diem/cong-vien-an-hoi` | H1 `Công viên An Hội` | Dữ liệu Detail thật, gallery, ContactWidget và public bottom nav |

## Ma trận ảnh được chấp nhận

`Nocturne` bắt đầu từ mặc định profile mới (`dark`); `Parchment` được chọn bằng control công khai (`light`). Nguồn chụp `full-r2` cung cấp 15 ảnh. Riêng `search-nocturne-desktop-1440.webp` đến từ lần recovery profile mới, có điều kiện chờ ảnh hữu hạn `focus-search-r3`.

| Route | Theme | Viewport | Fixture nguồn | Nguồn chụp | File | Kích thước | Bytes | SHA-256 | Accent |
|---|---|---:|---|---|---|---:|---:|---|---:|
| `/` | Nocturne | `1440x1000` | `home-sqlite` | `full-r2` | `home-nocturne-desktop-1440.webp` | `1440x1000` | 66,710 | `58318d55f4b95d29827d0e0b56fc050d380ddc6533011b46fc372a8b89a8506e` | 9% |
| `/` | Nocturne | `390x844` | `home-sqlite` | `full-r2` | `home-nocturne-mobile-390.webp` | `390x844` | 28,366 | `bba9e15515ae97b2e62205981cc0a26da538dd7a2aed90ed879c661c5c1d6d6a` | 9% |
| `/` | Parchment | `1440x1000` | `home-sqlite` | `full-r2` | `home-parchment-desktop-1440.webp` | `1440x1000` | 66,846 | `d16ec27c400139cea1d90b0c7bad81629ad5a0056e5e59c569bc36abf0134734` | 9% |
| `/` | Parchment | `390x844` | `home-sqlite` | `full-r2` | `home-parchment-mobile-390.webp` | `390x844` | 26,278 | `2bc1412ae64640d217b98a7b7541dcc5d878ca8e49402a99c81b3ec94d8c8863` | 9% |
| `/du-lich` | Nocturne | `1440x1000` | `discovery-sqlite` | `full-r2` | `discovery-nocturne-desktop-1440.webp` | `1440x1000` | 71,576 | `cb964b0c348021cb246852160129e0b28620ee331b790cff47fb6249901cd5a7` | 5% |
| `/du-lich` | Nocturne | `390x844` | `discovery-sqlite` | `full-r2` | `discovery-nocturne-mobile-390.webp` | `390x844` | 30,776 | `fa1a580598432c0d5e53705b54368921b7f8e4946244fc19fcd7359abf2fdb91` | 5% |
| `/du-lich` | Parchment | `1440x1000` | `discovery-sqlite` | `full-r2` | `discovery-parchment-desktop-1440.webp` | `1440x1000` | 66,112 | `17a56c0e230c67e166944979e5134051ecf1ed6e430c73be7dd4e5d7d136121a` | 5% |
| `/du-lich` | Parchment | `390x844` | `discovery-sqlite` | `full-r2` | `discovery-parchment-mobile-390.webp` | `390x844` | 30,758 | `c9b6e2fb46902d1eac11d079d38ed29c1191d0eb4fc3c1ca3cb350af7ce335e3` | 5% |
| `/tim-kiem` | Nocturne | `1440x1000` | `search-sqlite` | `focus-search-r3` | `search-nocturne-desktop-1440.webp` | `1440x1000` | 76,058 | `0b3d97496dbfbf87beaa80f7db3951cd666e1d04d201d2a707f954621d1cb266` | 5% |
| `/tim-kiem` | Nocturne | `390x844` | `search-sqlite` | `full-r2` | `search-nocturne-mobile-390.webp` | `390x844` | 23,754 | `f6e0903c03a8381e392c3761fee6241fe403f79f093d18aa4dd0de42d8c8d28b` | 5% |
| `/tim-kiem` | Parchment | `1440x1000` | `search-sqlite` | `full-r2` | `search-parchment-desktop-1440.webp` | `1440x1000` | 81,684 | `52d01a6d8dd6bf9c235bf705e3abf35931e06805d20385c08c9935896b422a1a` | 5% |
| `/tim-kiem` | Parchment | `390x844` | `search-sqlite` | `full-r2` | `search-parchment-mobile-390.webp` | `390x844` | 25,482 | `a5909e75d2c17b1286aaf9e7df1f4793ec54fe4c83475825d7972276d30b2ee5` | 5% |
| `/dia-diem/cong-vien-an-hoi` | Nocturne | `1440x1000` | `detail-an-hoi-sqlite` | `full-r2` | `detail-nocturne-desktop-1440.webp` | `1440x1000` | 201,838 | `b36b69e6ecada18a2b4a803d008064429ed8b3b2e34ebce71e7b8c19a4227924` | 7% |
| `/dia-diem/cong-vien-an-hoi` | Nocturne | `390x844` | `detail-an-hoi-sqlite` | `full-r2` | `detail-nocturne-mobile-390.webp` | `390x844` | 59,390 | `b484efb9ea8cb6aaca74eaa689855ac318fd7d42f56c4f6148e536c421000dc1` | 7% |
| `/dia-diem/cong-vien-an-hoi` | Parchment | `1440x1000` | `detail-an-hoi-sqlite` | `full-r2` | `detail-parchment-desktop-1440.webp` | `1440x1000` | 223,124 | `3e766704f8ebee437109a5890af563272e37b38bc95e41844684a3abe9d8c870` | 7% |
| `/dia-diem/cong-vien-an-hoi` | Parchment | `390x844` | `detail-an-hoi-sqlite` | `full-r2` | `detail-parchment-mobile-390.webp` | `390x844` | 64,118 | `d540c887ac05632453c57e665b6ec6241728ea98da86481ef4349e6286c77862` | 7% |

Các ước lượng accent đều nằm trong biên bắt buộc: Homepage `9%` trong `8–10%`; Discovery và Search `5%` trong `4–6%`; Detail `7%` trong `6–8%`.

## Browser-first, tương tác và hình học

- Browser-first thành công trong lần thử cho phép: đúng URL/title Homepage, DOM có H1/main/theme/navigation/control chính, không framework overlay, không warning/error trong lượt Browser-first; screenshot thành công qua API `tab.screenshot`.
- Homepage, cả bốn trạng thái: mở `Chat AI` làm `aria-expanded=true`, thấy nút đóng duy nhất; đóng panel trả về `aria-expanded=false`. Control đăng nhập giữ kích thước tối thiểu `44x44`.
- Discovery, cả bốn trạng thái: click vật lý đổi `Trải nghiệm` sang `Ẩm thực`, đổi hero copy, `aria-pressed` và material accent từ `leaf` sang `amber`.
- Search, cả bốn trạng thái: nhập `dừa`, click vật lý submit, URL thành `/tim-kiem?q=d%E1%BB%ABa`; giao input/nút bằng `0`, tâm nút thuộc nút; target desktop cao `59px`, mobile cao `44px`.
- Detail, cả bốn trạng thái: lightbox ảnh mở và đóng bằng control thật; giao giữa trip/photo control bằng `0`, tâm thuộc đúng control và chiều cao tối thiểu `44px`. Hero hoàn tất ở `800x533`, có class loaded, opacity ổn định `0.92` Nocturne và `1` Parchment.
- Detail mobile, cả hai theme: `.detail-body` client/scroll `390/390`, `.detail-main` nằm gọn; ContactWidget và bottom nav cùng hiện, giao rectangle `0`; cả sáu tâm CTA/nav thuộc đúng target; main giữ bottom reservation `145px`.

## Focus, zoom, media và mô phỏng thị giác màu

- Mỗi trạng thái có đúng một public theme control và đúng một nút pressed khớp theme yêu cầu.
- Tab tạo focus ring nhìn thấy ở `16/16`: `2px` tại 15 trạng thái và `3px` tại Detail Nocturne desktop.
- Zoom trang `200%` giữ H1/main có nghĩa ở `16/16`, không có horizontal overflow.
- `prefers-contrast: more`, `forced-colors: active` và `prefers-reduced-motion: reduce` tạo `48/48` proof không trắng, giữ H1 và cấu trúc action được chọn.
- Achromatopsia, protanopia, deuteranopia và tritanopia tạo `64/64` proof không trắng, giữ H1, nhãn theme được chọn và cấu trúc action/status.

## Console, network và kiểm tra bằng mắt

- Blocker console/runtime liên quan: `0`; blocker network liên quan: `0`; framework overlay: `0`; ảnh hỏng cuối: `0`; trạng thái page overflow: `0`.
- Ba nhóm `503` SQLite nhẹ được ghi nhận và phân loại rõ, không che giấu: `/auth/me`, `/api/entities/cong-vien-an-hoi/feed?limit=5`, `/api/entities/cong-vien-an-hoi/feed?page=1&limit=10`. Cảnh báo deprecation `apple-mobile-web-app-capable` của Chrome được xếp non-blocking.
- Controller đã xem trực tiếp 16 candidate gốc và bốn contact sheet theo route: không blank page, overlay, clipping ngang, fixed-control overlap, ảnh nhìn thấy bị thiếu, primary action bị che, loading state cũ hoặc chữ trên ảnh không đọc được.
- Phần chip Search mobile lộ một phần là continuation cue ngang có chủ ý, không phải page/grid overflow hoặc scroll trap.

## Bằng chứng tự động trên code HEAD `074b4210`

- Contrast audit: `82/82 PASS`.
- Debt checker: `PASS`; ratchet artifact được bảo vệ và không làm tăng raw hex/legacy primary debt.
- Exact serial Task 7: `16` files, `203/203 PASS` với `--maxWorkers=1`.
- `npm run typecheck`: PASS; `node --check` cho `detail-grid-gate-core.mjs` và `check-detail-grid-containment.mjs`: PASS; `git diff --check`: PASS; hard-ratchet hook: `hard=0`, không tăng ratchet.
- Nuxt/Nitro build: PASS; `.output/server/index.mjs` tồn tại. Manifest `1,240` bytes, SHA-256 `BFA717920BA6B64664C967251631FE1808624B69B604F33A793255D488976E11`, có `build_revision=074b42101b47903b142099589a8d80fb25253139`, route revision `launch-indexing-policy-v1`, AI disclosure revision `ai-disclosure-v1` và cache purge đã xác minh.
- Detail normal gate: exit `0`, verdict `pass`, reasons `0/0/0`, `blocker_codes=[]`, `cleanup_errors=[]`, `owned_processes_remaining=[]`, `profile_removed=true`; mobile body `390/390`, main `350/350`, overflow `0`; ContactWidget/bottom-nav intersection `0`.
- Detail intentional mutation `mobile-main-auto-min-width`: gate exit `1` đúng fail-closed, verdict `fail`, reasons `26/12/14`; mutation `.detail-main { min-width:auto !important }` được chứng minh. Mobile body `390/1400`, overflow khác `0` là `1010px`, main `1380px`; desktop body overflow `872px`; cleanup vẫn sạch với `cleanup_errors=[]`, `owned_processes_remaining=[]`, `profile_removed=true`.

## Review độc lập

- Final spec review cho range `dff96ab1..074b4210`: `PASS`, không có finding Critical, Important hoặc Minor.
- Final quality review cho cùng range: `PASS`, không có finding Critical hoặc Important. Classifier SQLite, stacking/ownership ContactWidget-bottom-nav, cleanup process, asset/console catalog, compact lặp, JSON thuần có bound và proof mutation khác `0` đều được chấp nhận.

## Inventory commit Tasks 1–7 và remediation

- Task 1 — semantic foundation/action-focus: `8a152510`, `b2bcf7e7`, `59238319`, `2eb41577` (accepted HEAD `2eb41577`).
- Task 2 — regional accent/trust primitives: `9f0ee084`, `57b20952` (accepted HEAD `57b20952`).
- Task 3 — Homepage recipe và cascade audit: `d9c45f7b`, `cf0504b3`, `c03f0304`, `04d756ca`, `da119399`, `3b48afbd`, `7578bd29`, `96bfba4c`, `82f02cad` (accepted HEAD `82f02cad`).
- Task 4 — Discovery recipe: `df295a7e`, `fe7a90c5`, `226f7d7d` (accepted HEAD `226f7d7d`).
- Task 5 — Search recipe: `5c74eea7`, `cbf8686d` (accepted HEAD `cbf8686d`).
- Task 6 — Detail trust/media/action recipe: `d58bb823`, `32ffcf1e`, `44f272e9` (accepted HEAD `44f272e9`).
- Task 7 Homepage runtime remediation: `3d3bd6da`, `fe3ea4bd`.
- Task 7 global action remediation: `8f9c74e0`, `306c1b26`, `7b137a41`.
- Task 7 Detail hero hydration remediation: `de68107b`, `da6405ce`, `67012596`, `9665b6b6`, `29b52dfe`, `e1653f32`, `d1dd0b0b`.
- Task 7 Detail mobile action remediation: `2ec601d9`, `242a19db`, `b583674f`, `c3cefe42`.
- Task 7 Search mobile action/package remediation: `4798d401`, `cae69acd`, `185247f2`, `008611f7`.
- Task 7 Detail clipping/gate remediation: `7f8ef150`, `a82bfb0a`, `9e3d3c0f`, `24e9dec6`, `f189fbd5`, `bef2e02e`, `b9ac10a0`, `a9ab2c66`, `85896c8f`, `ee16eecd`, `dff96ab1`.
- Task 7 ContactWidget/feed/evidence remediation: `3cad85e2`, `faed0123`, `a94d85e2`, `df0c8986`, `074b4210` (accepted code HEAD `074b4210`).
- Task 7 closure artifact commit: commit con trực tiếp của `074b4210`, gồm đúng 22 path closure được liệt kê trong plan/brief.

## Cleanup và rủi ro Minor còn lại

- Browser session được đóng, không giữ QA tab. Backend/preview thuộc lượt chụp đã được revalidate ownership rồi dừng; listener cuối ở `3189` và `8360` bằng `0`; không còn helper Chrome/Node/Python thuộc task và không còn `chrome-profile-*` trong staging.
- Hai Minor coverage gap được final quality review ghi nhận: chưa có browser gate đúng breakpoint `767px` với safe-area inset khác `0`; chưa có negative orchestration test trực tiếp cho redirect sai origin/endpoint, JSON không hợp lệ và readiness unavailable của `probeReadinessBackend()`.
- Minor cũ còn lại: exported `runControlHelper` chưa có guard non-Windows rõ ràng, dù caller production hiện chỉ dùng Windows.
- Mismatch API Browser `qaTab.playwright.screenshot` không blocking; API runtime đúng `qaTab.screenshot({ fullPage: false })` đã thành công ngay. Những rủi ro này không làm thay đổi verdict closure.
