# Báo cáo nghiệm thu Homepage B1 — Adaptive Nocturne

> STATUS: implemented-and-verified — 2026-07-31. Không bao gồm triển khai production.

## 1. Phạm vi và phiên bản

- Route nghiệm thu: `/`.
- Branch: `codex/homepage-b1-nocturne`.
- Revision ứng viên cuối: `d5dd453af02ccc0984574d21177525bc10cfa0b0`.
- Production preview: `http://127.0.0.1:3177/`.
- Mock backend phục vụ ma trận trạng thái: `http://127.0.0.1:8360/`.
- Browser QA: in-app Browser, Chromium surface.
- Không deploy, không thay API, shell, auth, RBAC, location, trust, booking, ordering hoặc payment.

## 2. Các commit B1

| Commit | Nội dung |
| --- | --- |
| `33abe261` | Presentation adapter thuần, quyết định ổn định và khử trùng lặp. |
| `f66f64bd` | Ba component trình bày hẹp của homepage. |
| `1cc09bb0` | Tích hợp hero, decision ledger, category index và image-policy guard. |
| `2de0e678` | Hoàn thiện composition giữa/cuối trang và CSS chỉ áp dụng cho B1. |
| `859755e7` | Assertion chống rank/trust giả trong DOM. |
| `ad8ee726` | Tách recovery của homepage API khỏi dữ liệu community. |
| `d5dd453a` | Render ảnh feature local bằng native `<img>`, chỉ dùng `NuxtImg` cho URL remote. |

## 3. Bằng chứng TDD cho remediation cuối

- Root cause: `HomeFeatureDossier` gửi cả URL nội bộ qua `NuxtImg`; weserv viết lại `/img/features/trai-nghiem.webp` thành provider URL không hợp lệ và ảnh có `naturalWidth = 0`.
- RED: `npm test -- tests/home-nocturne-components.test.ts` thoát `1`; 1 test fail, 4 test pass. Test local bắt đúng marker `data-nuxt-img-stub="true"` xuất hiện ngoài mong đợi.
- GREEN: cùng focused suite thoát `0`; 5/5 test pass.
- Regression liên quan: 5 suites, 35/35 test pass.
- Test remote xác nhận vẫn dùng `NuxtImg`, giữ `sizes`, disclosure, kích thước và loading priority.
- Test local xác nhận dùng native `<img>`, giữ alt, `aria-describedby`, width, height, `loading="eager"` và `fetchpriority="high"`.

## 4. Automated gate cuối

| Gate | Kết quả |
| --- | --- |
| 11 behavior/regression suites | PASS — 11 files, 151/151 tests. |
| `npm run typecheck` | PASS — exit `0`. |
| `npm run build` | PASS — exit `0`, 765 modules transformed, output 6.49 MB, manifest tại revision `d5dd453a`. |
| `python scripts/checks/run_hard.py --staged` cho remediation | PASS — `hard=0`, ratchet không tăng. |
| `git diff --cached --check` cho remediation | PASS. |
| Dependency audit | Không thay `package.json` hoặc lockfile. |

Build chỉ còn warning không phát sinh từ B1: sourcemap của module-preload polyfill, chunk lớn hơn 500 kB và deprecation trailing-slash export của package Vue.

Một lần chạy thăm dò `run_hard.py --all` không được dùng làm gate của Task 2 vì checkout này không có coverage artifact toàn backend và baseline toàn branch hiện báo R20.8 `28 > 14`, R20.4 `1 > 0`. Task-scoped staged gate của hai file remediation vẫn sạch.

## 5. Audit behavior tích hợp

No missing behavior assertion after integrated review.

- Lỗi `/api/homepage` vẫn giữ search, bảy category routes, retry và public shell.
- Community empty/failure không xóa editorial feature, spotlight, story hoặc homepage recovery.
- Không có favorites/recent-history thì không render `data-home-section="for-you"`.
- Nocturne và Daylight Parchment giữ cùng DOM, section order, actions và ý nghĩa.
- Không có numeric rank marker, nhãn trust/source không được hỗ trợ hoặc badge `Mới` từ rating bằng 0.
- Hero, decision entries và các danh sách event/seasonal/dish kế tiếp không lặp entity.
- Loading skeleton và empty state của homepage độc lập với việc community có bài viết.

## 6. Ma trận browser QA

| Viewport | Theme | Fixture/trạng thái | Keyboard | Overflow | Disclosure | Baseline |
| --- | --- | --- | --- | --- | --- | --- |
| 375 portrait | Nocturne | Success | PASS | Không | Hiển thị | not canonical |
| 375 portrait | Parchment | Success | PASS | Không | Hiển thị | not canonical |
| 390 × 844 | Nocturne | Success | PASS | Không | Hiển thị | `nocturne-mobile-390.webp` |
| 390 × 844 | Parchment | Success | PASS | Không | Hiển thị | `parchment-mobile-390.webp` |
| 768 portrait | Nocturne/Parchment | Success | PASS | Không | Hiển thị | not canonical |
| 1024 desktop | Nocturne/Parchment | Success | PASS | Không | Hiển thị | not canonical |
| 1440 × 1024 | Nocturne | Success | PASS | Không | Hiển thị | `nocturne-desktop-1440.webp` |
| 1440 × 1024 | Parchment | Success | PASS | Không | Hiển thị | `parchment-desktop-1440.webp` |
| Mobile landscape | Nocturne/Parchment | Success | PASS | Không | Hiển thị | not canonical |
| 390 portrait | Homepage partial/empty/failure | Recovery | PASS | Không | Khi có media | not canonical |
| 390 portrait | Community empty/failure | Isolated recovery | PASS | Không | Không ảnh hưởng hero | not canonical |
| 390 portrait | Image fallback | Placeholder geometry | PASS | Không | Hiển thị copy placeholder | not canonical |

Kết quả chung:

- Không có page overflow ở các viewport đã kiểm tra.
- Không có target hiển thị thấp hơn 44 px; phép đo cuối tại 390 px cho `minVisibleTarget = 44`.
- Không clipping label/action; bảy category destinations giữ đúng và chỉ xuất hiện một lần.
- Theme control giữ focus; outline sau khi click Nocturne là `solid`.
- Section order quan sát được ở Parchment: `hero → decisions → categories → events-seasonal → editorial-feature → spotlight-food → story-spread → community`; Nocturne tương đương, ngoài client-only regions khi có signal.
- Console cuối không có app warning/error và không có framework overlay.

## 7. Xác nhận ảnh production sau remediation

| Kiểm tra | Kết quả |
| --- | --- |
| DOM `src` | `/img/features/trai-nghiem.webp` — không còn weserv rewrite. |
| `currentSrc` | `http://127.0.0.1:3177/img/features/trai-nghiem.webp`. |
| HTTP asset | `200`, `Content-Type: image/webp`, 235440 bytes. |
| Mobile 390 | `complete=true`, `naturalWidth=1200`, `naturalHeight=675`. |
| Desktop 1440 | `complete=true`, `naturalWidth=1200`, `naturalHeight=675`. |
| Theme toggle | Ảnh giữ nguyên URL, kích thước tự nhiên và disclosure ở cả hai theme. |

## 8. Canonical baselines

| Tệp | SHA-256 |
| --- | --- |
| `nocturne-mobile-390.webp` | `2ac1075901dcbb6e562040c905174fa20be91361e4a2653b179e58b45a1f9243` |
| `parchment-mobile-390.webp` | `83852d31ab6f2836a744900440588a08a18b2af89b1470395de29a372866d796` |
| `nocturne-desktop-1440.webp` | `901f6aa76e60e0d7f65eec9e3ab691f11c3d6ced549fa0c707cfe778f27772eb` |
| `parchment-desktop-1440.webp` | `075f03ec622c1777ac3af9ea3acc8bd91495c4c809b633ecce87932b95e723fe` |

## 9. Anti-template và rollback audit

- Diff B1 từ `7ad42fd3` đến `d5dd453a` không thêm `hero-kenburns`, `dx-num`, glass/backdrop effect, negative translate hover, gradient mới, HOT, fake verification, popularity hoặc travel-time claim.
- Lệnh quét toàn `pages/index.vue` vẫn thấy gradient, backdrop và transform trong legacy CSS/descriptor tồn tại trước B1. `git diff -U0 7ad42fd3..HEAD` xác nhận không có prohibited addition mới; không mở rộng cleanup ra ngoài pilot.
- Pilot được giới hạn bởi `data-home-pilot="nocturne-b1"` và import `home-nocturne.css` ngay tại homepage.
- Rollback code: revert `d5dd453a` nếu chỉ cần hoàn tác renderer split; để bỏ toàn B1, revert các commit Task 2–4/remediation hoặc xóa ba component usages và page-only CSS import.
- Rollback không chạm API, shared shell, auth, location, trust hoặc Plan A shared tokens.

## 10. Review độc lập và giới hạn công cụ

- Fresh implementer remediation (`gpt-5.6-terra`) lỗi trước khi làm việc: `404 Not Found: No active credentials for provider: openai`.
- Fresh retry (`gpt-5.6-sol`) lỗi tương tự.
- Independent spec review và independent quality review đều lỗi trước khi đọc diff với cùng thông báo 404.
- Các self-review/fallback trong session không được mô tả là independent approval. Independent approval vẫn không khả dụng do provider outage; failure evidence được ghi trong SDD ledger và Task 2 report.
- Browser surface không cung cấp media emulation độc lập cho forced colors, reduced motion hoặc 200% text zoom. Các mục này dựa trên CSS contract, mounted behavior checks và kiểm tra layout/label đã thực hiện; báo cáo không tuyên bố đã có visual emulation độc lập.

## 11. Parallel-session guard

- Workspace chính `C:/Code/vinhlong360`: `design-system/vinhlong360/pages/home.md` giữ object hash `b694ac09ede89442c8af48e193534f0fd25ee3a4`.
- Isolated worktree giữ tracked object riêng `f9c8ea5ce71fc20a542e82a55415cddd21e5c10c` và không sửa/stage file này.
- Không stage `.superpowers/`, artifact session khác hoặc file bị cấm trong Global Constraints.
