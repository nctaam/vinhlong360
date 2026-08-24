# Kế hoạch nâng cấp giao diện trang chủ

> **STATUS (2026-08-25): active — chờ chủ dự án duyệt Đợt 3.**
> Cơ sở nghiên cứu: `docs/ROADMAP.md` §19–27 (8 đợt đo, 4 site đối chiếu).
> **1 việc = 1 commit.** Bất biến §2 CLAUDE.md áp dụng nguyên vẹn.

## Goal

Trang chủ nói **cùng ngôn ngữ thị giác** với 12 trang còn lại của site, mà **không
thêm ảnh, không thêm dịch vụ, không thêm chi phí**.

## Chẩn đoán một câu (§27)

> Dự án đã xây một hệ thiết kế giàu — 12/14 motif giác quan, thang chữ 10 bậc, ẩn dụ
> phù sa ba màu, `EntityCard` với hệ ảnh-bìa-sinh-tự-động chạy trên 12 trang — **và
> trang chủ dùng gần như không cái nào.**

Năm "vấn đề" tìm được ở §19–26 là **một vấn đề nhìn từ năm phía**: trang chủ được dựng
bằng **từ vựng thẻ riêng** thay vì từ vựng của site.

## Điều nghiên cứu đã BÁC BỎ — đừng làm

| giả định | số đo bác bỏ |
|---|---|
| "Trang chủ rối vì nhiều màu" | 3 họ màu có sắc. Atlas Obscura chỉ **2**, Emilia Romagna **4** (§20, §26) |
| "Cần cắt bớt nội dung" | Trang chủ **ngắn nhất** trong 4 site (4,9 màn hình so với 7–8) (§20) |
| "Khối danh mục trùng header nên bỏ" | **Cả 3 site đối chiếu đều có** khối này; ở 360px header chỉ hiện 1 link (§22.3) |
| "Chữ thân bài quá nhỏ" | Thân bài **16px**, kế thừa mặc định. Đo trên trang: `16px ×280` (§25.3) |
| "Vi phạm ngân sách chuyển động" | Stagger 40ms có chặn trần; ambient thật nằm trong mã chết (§21.4) |

## Bất biến áp dụng

- **B5** — mỗi task để lại hệ thống chạy được, commit nhỏ. KHÔNG big-bang.
- **B2** — additive-first: thêm đường mới, verify, rồi mới gỡ đường cũ.
- **§3.2** — mỗi task chạy lệnh verify trước khi commit.
- **§3.3** — test đang xanh bỗng đỏ mà chưa rõ nguyên nhân → DỪNG, báo người.

---

## ĐỢT 1 — hai dòng, đã kiểm trước, thấy được ngay

Rủi ro gần bằng không: hình học không đổi, tương phản đã đo.

- [ ] **T1 — Thanh tiêu đề mục nhận lại dải phù sa ba màu.**
  `pages/index.vue`, quy tắc `.home .section-head h2::before`: đổi
  `background: var(--color-brand)` → gradient river→amber→clay giống
  `assets/css/components.css:813`.
  **Vì sao:** hai quy tắc hiện giống hệt nhau từng chữ trừ dòng này — trang chủ đã chép
  hình dạng sediment-tick rồi bỏ ý nghĩa (§24.3). Vì `f55aeede` đã gộp cả 6 tiêu đề mục
  về dùng chung thanh này nên **một dòng nâng cả sáu**.
  **Rủi ro:** không đổi hình học (cùng `width/height/border-radius`); thanh trang trí
  4px nên không ràng buộc tương phản.
  **Verify:** `npx vitest run` · `python scripts/checks/run_hard.py --staged` · mắt thường.

- [ ] **T2 — Hero nhận lại motif sóng nước.**
  `pages/index.vue:728` `.home .hero { background-image: none; }` — gỡ, và cho hero dùng
  lớp `::before` motif như `.catalog-hero` (`assets/css/catalog.css:54`).
  **Vì sao:** 12+ trang đều có motif hero; trang chủ là trang **duy nhất** tắt nó, bằng
  một dòng không ghi chú (§21.1).
  **Đã kiểm trước trên trình duyệt:** motif áp sạch, `.hero-inner` lên `z-index:1`,
  tương phản `h1` **15,98 → 12,44** và `.hero-sub` **18,52 → 14,41** — vẫn gấp ~3 lần
  ngưỡng AA.
  **Verify:** như T1, cộng đo lại tương phản hero ở cả hai chế độ.

## ĐỢT 2 — nhắm đúng đối tượng và nới nhịp

- [ ] **T3 — "Giữ mạch khám phá" chỉ hiện khi có tín hiệu cá nhân.**
  `pages/index.vue:260`, thêm điều kiện giống cách "Dành cho bạn" đã làm ở declutter-3
  B1-7 (`hasPersonalSignal`).
  **Vì sao:** tiêu đề *"…khi bạn ĐÃ CÓ một điểm bắt đầu"* nhắm vào người quay lại, nhưng
  hiện cho **mọi** khách; với khách lần đầu nó chứa đúng 2 liên kết **đều đã xuất hiện
  phía trên**. Trang đang dành 181px cho nhóm chưa tồn tại (§22.1).
  **Verify:** test + xoá `localStorage` rồi tải lại, mục phải biến mất.

- [ ] **T4 — Nới khoảng trống mỗi đơn vị nội dung.**
  Hiện **75px** mỗi đơn vị bấm được; Emilia Romagna 133, Visit Jeju 140, Atlas Obscura
  **323** (§26.1). Nới nhịp dọc trong mục và đệm thẻ, đích **~120–140px**.
  **Vì sao:** 4 phép đo độc lập đều nói mật độ là vấn đề, không phải số lượng mục.
  **Rủi ro:** trang dài ra. Chấp nhận được — Atlas Obscura để mobile dài **15,2 màn
  hình** mà vẫn giữ 300px/đơn vị (§27.1).
  **Verify:** đo lại px/đơn vị ở 1280 và 360; tràn ngang phải = 0.

## ĐỢT 3 — GỐC RỄ, cần chủ dự án duyệt trước khi làm

Không tự làm. Đây là thay đổi lớn, đụng dữ liệu, và phải nhìn bằng mắt mới duyệt được.

- [ ] **T5 — (đo, không sửa) Xác nhận `type` có mặt trên dữ liệu trang chủ.**
  `HomePresentationEntity` khai `id/name/title/days_until/attributes` cộng index
  signature `[key: string]: unknown`. `EntityCard` cần `id`, `type`, `name`.
  **Phải đo runtime, không suy từ kiểu.** Nếu thiếu `type` thì Đợt 3 dừng tại đây.

- [ ] **T6 — Thử `EntityCard` trên ĐÚNG MỘT mục: "Dành cho bạn".**
  Chọn mục này vì `forYou` đã khai sẵn `{ id, name, type, imageDescriptor, to }` —
  đúng ba trường `EntityCard` cần, và đã có sẵn image descriptor.
  **Vì sao:** `EntityCard` mang theo hệ ảnh bìa sinh tự động (`placeholderBg` gieo theo
  `entity.id`, `cover-grain`, glyph danh mục lệch tâm) — tức **lời giải cho bài toán
  ~97% entity không có ảnh** (§27.2). Thẻ Atlas Obscura có **83% chiều cao là ảnh**
  (§27.1); đây là cách đạt điều đó mà không cần một tấm ảnh mới nào.
  **B2:** thêm đường mới sau cờ, so sánh, rồi mới gỡ `fy-chip`.
  **Verify:** test + chủ dự án nhìn và duyệt.

- [ ] **T7 — Sau T6: quyết định cho các mục còn lại.**
  `event-mini` / `dish-item` (là entity, dùng được) so với `cm-card` (là **post**, KHÔNG
  phải entity — có thể không dùng được). Quyết sau khi thấy kết quả T6.

## ĐỢT 4 — dữ liệu máy đọc (độc lập, làm lúc nào cũng được)

- [ ] **T8 — Đưa "ba tỉnh ngang hàng" về đúng chuẩn §1.6.**
  7 chỗ: `pages/index.vue` JSON-LD `areaServed`, `ban-do.vue:7,228`,
  `cong-dong.vue:1473`, `danh-ba.vue:280`, `dia-diem/index.vue:13,299`.
  **Vì sao:** `utils/adminUnit.ts` đã đặt chuẩn rất chỉn chu (dẫn §1.6, đúng mốc
  1/7/2025, 124 xã/phường, `area` là vùng cũ chỉ để tra cứu). Tầng SEO/JSON-LD chưa
  theo kịp — **hai tầng lệch nhau**, không phải site sai (§24.5).
  **Cấp thiết vì:** nên vá **trước khi mở index**; mở rồi mới sửa thì dữ kiện đã kịp
  vào chỉ mục và vào mô hình (§23.7).

- [ ] **T9 — Thêm schema `QAPage` cho hỏi–đáp cộng đồng.**
  `pages/bai-viet/[id].vue` đã có `post_type === 'question'` + `bestAnswerId`; toàn dự án
  **0 chỗ** dùng `QAPage`/`acceptedAnswer`.
  **Vì sao:** 64% nhà tiếp thị điểm đến đang làm đúng việc này để được cỗ máy trả lời
  trích dẫn; dữ liệu đã có sẵn trong DB (§23.3).

---

## Ngoài phạm vi — cần chủ dự án quyết riêng

| việc | ROADMAP | vì sao không tự làm |
|---|---|---|
| 5 nhãn "Chưa rõ nguồn" trên cửa trước | §19.5, §23.5 | quyết định về tín nhiệm, không phải kỹ thuật |
| Đặc sản là mục con thay vì lối vào riêng | §22.2 | quyết định biên tập |
| Di trú thang bo góc (370 chỗ) | §18.1 | đã chọn hướng (a), ratchet R30.8 đang giữ |
| Khu admin dùng chung bảng màu hay giữ kiểu iOS | §17.6 | quyết định sản phẩm |
| Thêm khối tầng A dùng `HeroIllustration` | §21.2 | cần sinh ảnh AI + duyệt bằng mắt |

## Kết

Chạy `python -m pytest -q`, `npx vitest run`, `python scripts/checks/run_hard.py --all`,
`python scripts/scorecard.py` (không được tụt điểm). Ghi plan-result. Cập nhật ROADMAP.
