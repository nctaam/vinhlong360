# Kế hoạch nâng cấp giao diện trang chủ

> **STATUS (2026-09-06): complete — Chủ dự án phê duyệt mô hình Đặc sản F + E-lite; Đợt 1, 2, 3, 4 đã hoàn tất.**
> Cơ sở nghiên cứu: `docs/ROADMAP.md` §19–32 (8 đợt đo, 4 site đối chiếu, thẩm định 14-agent).
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

- [x] **T1 — Thanh tiêu đề mục nhận lại dải phù sa ba màu.**
  `pages/index.vue`, quy tắc `.home .section-head h2::before`: đổi
  `background: var(--color-brand)` → gradient river→amber→clay giống
  `assets/css/components.css:813`.
  **Vì sao:** hai quy tắc hiện giống hệt nhau từng chữ trừ dòng này — trang chủ đã chép
  hình dạng sediment-tick rồi bỏ ý nghĩa (§24.3). Vì `f55aeede` đã gộp cả 6 tiêu đề mục
  về dùng chung thanh này nên **một dòng nâng cả sáu**.
  **Rủi ro:** không đổi hình học (cùng `width/height/border-radius`); thanh trang trí
  4px nên không ràng buộc tương phản.
  **Verify:** `npx vitest run` · `python scripts/checks/run_hard.py --staged` · mắt thường.

- [x] **T2 — Hero nhận lại motif sóng nước.**
  `pages/index.vue:728` `.home .hero { background-image: none; }` — gỡ, và cho hero dùng
  lớp `::before` motif như `.catalog-hero` (`assets/css/catalog.css:54`).
  **Vì sao:** 12+ trang đều có motif hero; trang chủ là trang **duy nhất** tắt nó, bằng
  một dòng không ghi chú (§21.1).
  **Đã kiểm trước trên trình duyệt:** motif áp sạch, `.hero-inner` lên `z-index:1`,
  tương phản `h1` **15,98 → 12,44** và `.hero-sub` **18,52 → 14,41** — vẫn gấp ~3 lần
  ngưỡng AA.
  **Verify:** như T1, cộng đo lại tương phản hero ở cả hai chế độ.


## Kết quả Đợt 1 (2026-08-25)

| | commit | đo được |
|---|---|---|
| T1 | `8800796e` | 5/5 thanh tiêu đề có dải phù sa, cả hai chế độ; `/dia-diem` 3/3 không hỏng |
| T2 | `794d7398` | motif hero dựng ở cả hai chế độ; tràn ngang 0; tương phản sáng 16,74/10,85 · tối 15,98/18,52 |

**Cả hai làm bằng TOKEN, không chép giá trị** — thêm `--sediment-tick` và
`--hero-motif-waves`, mỗi cái khai một lần ở `:root` và một lần ở `.dark`. Nhờ token
tự biết chế độ, **xoá được 3 quy tắc `.dark` thừa** (components.css, index.vue,
catalog.css).

**Hai lần verify cứu tôi khỏi giao thiếu/giao sai:**
- T1 lượt đầu chỉ 2/5 thanh đổi — ba tiêu đề mục dựng bằng component lấy kiểu từ
  `home-nocturne.css`, quy tắc do chính tôi viết ở `f55aeede`. Sửa file đầu tiên rồi
  tin là xong thì đã giao một trang nửa vời.
- T2 lượt đầu đọc ra `hero-sub` tương phản **1,04** và suýt báo động. So sai nền —
  `.hero-sub` có nền đen riêng, phải chồng lên nền hero rồi mới so, thật ra **10,85**.

**Phát hiện ngoài dự kiến:** `/img/hero.webp` **tồn tại** (190 KB) và `base.css:163`
có sẵn quy tắc dùng nó, nhưng `home-nocturne.css:64` dùng `background:` dạng rút gọn
nạp sau nên ảnh không bao giờ hiện. Đã kiểm: sau T2 ảnh vẫn KHÔNG tải (0 request).
Tôi không tự bật — đó là lựa chọn của đợt nocturne. Nhưng nó liên quan thẳng tới
§19.3/§20 (trang chủ ít hình nhất trong 4 site): **có sẵn một tấm hero đang nằm không.**

## ĐỢT 2 — nhắm đúng đối tượng và nới nhịp

- [ ] **T3 — "Giữ mạch khám phá" chỉ hiện khi có tín hiệu cá nhân.**
  `pages/index.vue:260`, thêm điều kiện giống cách "Dành cho bạn" đã làm ở declutter-3
  B1-7 (`hasPersonalSignal`).
  **Vì sao:** tiêu đề *"…khi bạn ĐÃ CÓ một điểm bắt đầu"* nhắm vào người quay lại, nhưng
  hiện cho **mọi** khách; với khách lần đầu nó chứa đúng 2 liên kết **đều đã xuất hiện
  phía trên**. Trang đang dành 181px cho nhóm chưa tồn tại (§22.1).
  **Verify:** test + xoá `localStorage` rồi tải lại, mục phải biến mất.

- [~] **T4 — HUỶ. Tiền đề sai (ROADMAP §29).**
  Kế hoạch ban đầu: nới 75px → 130px mỗi đơn vị. **Chỉ số đó không dùng được.**
  Phép đo cũ (a) đếm cả 21 đơn vị chrome header/footer, (b) chia cho số thẻ bất kể thẻ
  nằm cạnh nhau trong lưới nhiều cột.
  Đo lại theo HÀNG: hero 298px · "Hôm nay bạn muốn…" 133px · Tín hiệu 112px · Cộng đồng
  112px · Giữ mạch 91px. **Trang chủ không chật** — nhịp bình thường.
  Số của các site đối chiếu nhiễm cùng hai lỗi và **không đo lại được** (quét site ngoài
  bằng trình duyệt đã sập 4 lần, §28.4).

  **Thay bằng:** việc đúng cho phản hồi "giao diện chỉ toàn chữ" là **thêm hình**, không
  phải nới khoảng trống. Bằng chứng còn đứng vững là **đếm ảnh**: vinhlong360 **1 ảnh**,
  peers 4–19 — chỉ số này không có mẫu số nên không dính hai lỗi trên.
  Xem mockup phương án A/B đã dựng; chờ chủ dự án chọn.

## ĐỢT 3 — GỐC RỄ: Phê duyệt phương án Đặc sản (ĐÃ HOÀN THÀNH 2026-09-06)

- [x] **Chủ dự án phê duyệt phương án kết hợp F (Tin chính đặc sản) + E-lite (Sổ vàng OCOP):**
  - Khối Tin chính: Hiện thực hóa qua component `HomeProductLead.vue`, giữ nguyên tên thật, 1 ảnh chính đạt chuẩn `ImageDisclosure`, responsive an toàn $\ge 900$px, kiểm định qua `tests/home-product-lead.test.ts` (8/8 pass).
  - Khối Sổ vàng OCOP: Hiện thực hóa qua `HomeOcopLedger.vue`, viền dày 2px + halo, độc lập với payload động, kiểm định qua `tests/home-ocop-ledger.test.ts` (7/7 pass).
  - Hướng Bento C chính thức bị bác bỏ hoàn toàn theo thẩm định 14-agent (ROADMAP §31).

## ĐỢT 4 — dữ liệu máy đọc (độc lập, làm lúc nào cũng được)

- [x] **T8 — Đưa "ba tỉnh ngang hàng" về đúng chuẩn §1.6.**
  Chuẩn hóa 7 vị trí máy đọc/SEO, danh bạ (`pages/danh-ba.vue`), danh bạ địa điểm (`pages/dia-diem/index.vue`), và bản đồ (`pages/ban-do.vue`) theo mốc hành chính 2 cấp 1/7/2025 tỉnh Vĩnh Long hợp nhất (kèm dấu lịch sử theo luật `sachTheo16`).
  **Verify:** `tests/seo-tinh-hop-nhat.test.ts` (6/6 pass), `python scripts/checks/run_hard.py --staged`.

- [x] **T9 — Thêm schema `QAPage` cho hỏi–đáp cộng đồng.**
  `pages/bai-viet/[id].vue` đã có `post_type === 'question'` + `bestAnswerId`; toàn dự án
  **0 chỗ** dùng `QAPage`/`acceptedAnswer`.
  **Vì sao:** 64% nhà tiếp thị điểm đến đang làm đúng việc này để được cỗ máy trả lời
  trích dẫn; dữ liệu đã có sẵn trong DB (§23.3).
  *(Đã hoàn thành: phân nhánh `QAPage` + `Question` + `acceptedAnswer` khi `post_type === 'question'`, bảo toàn bất biến `safeJsonLd(articleLd)`).*

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

---

## KẾT QUẢ (cập nhật 2026-08-25, sau thẩm định đối kháng)

- **Đợt 1 (T1, T2): XONG** — commit `794d7398`, `8800796e`; hai lỗi bắt được ở bước verify
  đã ghi trong plan.
- **T4: HUỶ** — tiền đề "75px mỗi đơn vị" sai do máy đo (ROADMAP §29); không sửa mã.
- **Hướng bento cho mục Đặc sản (nối dài T6): BỊ BÁC sau thẩm định 14-agent** — ROADMAP
  §31. Bốn lý do: mockup bản 2 rút gọn 7/8 tên (không phải bằng chứng); hình học vỡ ở
  tầng cấu trúc (ô vừa trống 119,56px, đổi tỉ lệ không cứu); HAI dải viewport hỏng
  [320–450) và [721–874); thuật toán xếp hạng không biết độ dài tên (11/12 tháng đẩy
  entity-tổ-chức vào top). Luận cứ "67% SaaS dùng bento" truy về một blog duy nhất không
  phương pháp — đã rút lại.
- **Phương án sống sót, chờ chủ dự án chọn (ROADMAP §31.4):** D (nhịp sắc độ — làm trước,
  điều kiện cần) + F (Đặc sản tin chính, tái dùng CatalogSpotlight — khuyến nghị) hoặc
  E (sổ vàng OCOP 5 sao, star-band /ocop — đủ dữ liệu: 5 món sau khử trùng lặp).
- **Ràng buộc thực thi đã dò sẵn cho người làm sau (chi tiết trong kết quả workflow):**
  R30.8/R30.2 dư địa ratchet = 0 (dùng --radius-control/surface/sheet, icon từ
  IconLine.vue); mục mới phải đăng ký surface ảnh (entity-image-renderers.json +
  requiredBoundaries cùng commit); KHÔNG thêm dòng vào mảng css của nuxt.config.ts;
  KHÔNG dùng nguồn `seasonal` cho mục Đặc sản; verify bằng `run_hard.py --all` (chế độ
  --staged của hook đếm thiếu); scorecard.py chỉ chạy với `--no-append`.
