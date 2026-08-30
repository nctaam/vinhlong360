# Hồ sơ chờ chủ dự án quyết — sau đợt "giải quyết tất cả nợ" (2026-08-30)

> STATUS: active — mỗi mục là MỘT quyết định. Máy đã làm hết phần tự quyết được
> theo hiến pháp; những mục dưới đây dừng lại vì cần quyền của chủ dự án
> (đổi tiêu chuẩn, đổi diện mạo, pháp lý, chi phí) chứ không vì thiếu năng lực
> hay thiếu thời gian.

## 0. Bảng điểm trước → sau đợt

| Chiều | Trước (2026-08-29) | Sau | Nợ còn |
|---|---:|---:|---|
| data | 100 | **100** | 0 |
| backend | 81 | **100** | R20.4 (chỉ thiếu artifact `coverage.json`) |
| frontend | 64 | **86** | 331 = R30.2 emoji 330 + R30.7 bundle 1 |
| ui-design | 100 | **100** | 0 |
| content | 51 | **99** | R50.2 = 8 (đều là tên riêng / thuật ngữ lịch sử) |
| docs | 100 | **100** | 0 |
| ops | 100 | **100** | 0 |

Nợ R20.8 (complexity backend): **47 → 0 toàn repo**.

---

## 0. ⚠ P0 — hứa "xoá vĩnh viễn" nhưng hệ thống chỉ ĐẾM (mở từ 2026-08-22)

**Nghiêm trọng nhất trong hồ sơ này.** Kiểm lại hôm nay: **vẫn còn đúng từng chi tiết**.

- `agent/identity/api.py:1294` trả lời người dùng: *«Tài khoản sẽ bị xoá vĩnh viễn
  sau N ngày»*.
- `.env.example:161-162` mặc định `ERASURE_AUDIT_ONLY=true` +
  `ERASURE_ACTIVATION_ENABLED=false` → `_effective_erasure_audit_only()`
  (`agent/scheduler.py:137`) trả True, tác vụ nền **đếm hồ sơ quá hạn rồi thoát
  trước vòng xoá**, 288 lần/ngày.
- Deploy đúng theo file mẫu là rơi vào trạng thái này mà không ai biết mình đã chọn.

Đây là hứa một đằng làm một nẻo, và nó chạm thẳng Luật 91/2025 (quyền xoá dữ liệu).

**Chủ dự án phải chọn MỘT — máy KHÔNG được tự làm cả hai:**
- (a) **Bật xoá thật**: đặt hai khoá và kiểm trên môi trường có backup. Đây là
  thao tác phá dữ liệu → §4/B7, bắt buộc có chỉ đạo trực tiếp cho đúng việc đó.
- (b) **Giữ chỉ-đếm nhưng sửa câu trả lời**, đừng hứa "vĩnh viễn". Đây là sửa
  copy pháp-lý về quyền dữ liệu → Track-H, nên đi cùng luật sư ở §5.

Phần khả kiến đã làm sẵn từ 2026-08-27 (khoá khai trong `.env.example`,
`overdue_count` + `state` chiếu ra `/health/ready`, `_erasure_readiness` tách ra
mức module để kiểm được). Chỉ còn đúng lựa chọn trên.

---

## 0b. ⚠ MÌN CHỜ PUSH — cổng coverage R20.4 sẽ làm đỏ CI ngay lần push đầu

**Đã đo, không phải suy đoán.** Nhánh này chưa từng push nên CI chưa thấy; nhưng
cấu hình hiện tại không thể xanh:

- Ngưỡng `docs/standards/coverage-thresholds.json` đặt `identity/api.py: 85` và
  `community/api.py: 90`, ghi rõ là "đo thật 91/97" — con số **chỉ đạt được khi
  CÓ PostgreSQL**.
- Nhưng cổng `run_hard.py --all` (bước *Enforce standards and coverage ratchet*)
  nằm ở job `test`, và job đó **chạy SQLite, không có service postgres**.
- Đo tại chỗ hai môi trường: **không PG → identity 46,2% · community 29,2%**;
  **có PG → identity 88,3% · community 95,8%**. Job `test-pg` có đủ biến PG và
  chạy đúng các suite đó, nhưng **không chạy bước ratchet** nào.

Nói gọn: cổng đang được thực thi ở nơi phép đo không đầy đủ.

**Ba lối, đều là sửa hạ tầng CI nên cần chủ chốt (máy KHÔNG vá mù — bài học §5b:
vá CI bằng suy luận sai 2/2 lần, đo trước trúng 4/4):**
- (a) Thêm `--cov ... --cov-report=json` vào job `test-pg` rồi chuyển bước cổng
  coverage sang đó — đúng tiền lệ `check_bundle.main()` (chạy R30.7 ở job có
  `.output`). Cần thêm một `main()` cho `check_coverage.py`.
- (b) Cấp service postgres + 4 biến `*_TEST_DATABASE_URL` cho job `test` — đổi lại
  job "nhanh, ổn định" theo thiết kế hiện tại sẽ chậm đi.
- (c) Hạ hai ngưỡng về mức SQLite đạt được — **trái luật ratchet "chỉ NÂNG"**, và
  vứt bỏ độ phủ thật đã có.

Đề nghị của máy: (a). Nhưng đây là đổi kết cấu CI, xin chủ chốt trước.

---

## 1. Gói JS 803/800 kB — nới trần, đợt giảm cân, hay ĐỔI ĐỊNH NGHĨA thước đo?

**Sự thật đo được.** Trần 800 đặt 2026-07-10 khi bundle đang 790 (biên 10 kB).
Nay 803: **tăng trưởng thật** của 18 task correction-case pilot, không phải rác.

Đã thử và ĐỀU KHÔNG ĂN (đo, không đoán):
- Gom chunk nhỏ `experimentalMinChunkSize` 6 KB → **811** (tệ hơn: chunk dùng
  chung bị nhân bản vào từng importer); hạ 2 KB → **810**. Đã hoàn nguyên.
- Soi mỡ thư viện: `ipx/yup/chart` trong chunk là **dương-tính-giả** (trùng chuỗi
  trong hash tên file). Không có provider chết để gỡ.
- 276/803 kB là `maplibre-gl` và nó **đã lazy đúng** (`await import`), chỉ bị cổng
  đếm vì cổng cộng mọi `*.js`.
- Phiên 2026-08-27 độc lập đã tới cùng kết luận (sổ `90-exceptions-log.md`), và
  việc này đã nằm ở **ROADMAP §37.3** như một task hiệu năng riêng.

**Ba đường, chọn một:**
- (a) **Nới trần lên 820** kèm giải trình trong `bundle-budget.json` — mở lại cổng
  frontend của CI ngay, đổi lại hạ một nấc tiêu chuẩn.
- (b) **Giữ trần, xếp đợt giảm cân** (thay maplibre bằng bản nhẹ hơn, hoặc tách
  route bản đồ khỏi build chính) — giữ tiêu chuẩn, đổi lại CI frontend còn đỏ.
- (c) **Đổi định nghĩa thước đo** (câu hỏi ROADMAP §39 đã nêu): trần "tổng" có nên
  đếm chunk vendor **tải-lười** không, hay chỉ đếm phần vào lần sơn đầu? Nếu chỉ
  đếm phần sơn-đầu thì maplibre (276 kB, lazy đúng) ra khỏi phép cộng và con số
  thật sự phản ánh cái người dùng phải tải. Đây là đổi ĐỊNH NGHĨA, không phải nới
  trần cho dễ thở — nên cũng phải chủ chốt.

Máy KHÔNG tự chọn: cả ba đều đổi/hạ một tiêu chuẩn của dự án.

---

## 2. Emoji chức năng 330 chỗ (R30.2) — đại tu bộ icon?

**Sự thật.** 330 emoji trong 38 file: 157 ở trường `icon:`, 88 trong
`<span aria-hidden>`, 85 chỗ khác (nhãn option, ví dụ JSON trong trang hướng dẫn).
Chuẩn nhà đòi emoji-chức-năng dùng component `IconLine` — nhưng `IconLine` hiện
**chỉ có 18 icon**, còn 110 emoji khác nhau đang dùng.

Quy đổi đủ = vẽ/nhập ~110 SVG mới và **đổi diện mạo 38 trang**. Đây là quyết định
thị giác, không phải phép thay chuỗi — và bài học đã ghi: chủ dự án đánh giá theo
bố cục/màu sắc, đề xuất phải trình **tổng phổ toàn trang**.

**Đề nghị:** cho phép mở một đợt riêng, máy sẽ dựng mockup tổng phổ (tên trang
thật, cả sáng lẫn tối) rồi mới thay. Chi phí ước tính: 1 đợt cỡ chiến dịch F1/F2.

**Lưu ý:** R30.2 là *soft-ratchet* — 330 này là **tồn kho hợp lệ**, cổng chỉ chặn
emoji-chức-năng MỚI. Không sửa cũng không ai vi phạm gì.

---

## 3. R50.2 còn 7 — giữ nguyên (đề nghị đóng, không phải nợ)

> **ĐÍNH CHÍNH 2026-08-30: trước đây mục này ghi 8 và nói cả 8 đều chính đáng —
> SAI ở hai điểm.** (a) Cách chia cũ ("3 chỗ trường + 3 ĐCTT + 1 lịch sử + 1 `name`
> của chính entity trường") **đếm trùng 1**: cái `name` đã nằm trong nhóm 3 chỗ của
> trường. (b) Vì đếm trùng nên nó **bỏ sót một hit thật sự là filler**:
> `vinh-long-1-day-backpacker.attributes.content` viết *"nắng miền Tây rất gắt từ
> 9h"* — đây là mẹo du lịch, "miền Tây" ở đúng nghĩa định-vị-generic mà §1.6 dẹp,
> không phải tên riêng cũng không phải lịch sử. Đã sửa thành *"từ 9h nắng đã gắt,
> mà đoạn qua phà và đường đạp xe trên cù lao gần như không có bóng cây"* — giữ
> nguyên nội dung khuyến cáo, thay nhãn vùng bằng chi tiết có thật của chính lộ
> trình đó. Ghi kép data.json + DB (B1 backup trước), R50.2 8→7, baseline siết
> cùng commit.

7 chỗ chứa chữ "miền Tây" còn lại KHÔNG phải filler:
- `Trường Xây dựng miền Tây` — **tên riêng** của trường: `name`, `summary`,
  `description` (3 chỗ).
- `nhóm đờn ca tài tử miền Tây` — **thuật ngữ âm nhạc học**: trường phái miền Tây
  (Trần Quang Quờn) đối với trường phái miền Đông; `summary`, `attributes.role`,
  `description` (3 chỗ).
- `ba tỉnh miền Tây` 1867 (Phan Thanh Giản) — **sự kiện lịch sử** (1 chỗ).

Cổng là bộ so chuỗi nên không phân biệt được. **Đề nghị chủ duyệt** coi 7 là mức
sàn đúng của R50.2 (giống whitelist của R10.7), hoặc cho phép thêm whitelist
per-occurrence để cổng về 0 mà không phải viết sai lịch sử.

*Ghi thêm cho người sửa sau:* checker R50.2 báo vi phạm nhưng **không nói ở entity
nào, trường nào** — cả 8 dòng đều là `web/data.json:0` với cùng một thông điệp. Muốn
định vị phải tự dựng lại vòng lặp của nó. Đó là lý do mục này bị chia sai suốt một
đợt mà không ai phát hiện.

---

## 4. 157 entity cần khảo sát thực địa — DANH SÁCH NAY ĐÃ NẰM TRONG KHO

Trong 245 entity mỏng vừa viết lại, **157 cái chỉ có địa chỉ (± số điện thoại)**:
phần lớn là quán ăn/cà phê/nhà nghỉ nhập từ danh bạ. Nội dung đã viết trung thực
từ dữ liệu thật và KHÔNG bịa thêm — nên chúng ngắn và khô.

Muốn dày hơn thì cần **dữ liệu mới** (giờ mở cửa, khoảng giá, món đặc trưng, ảnh) —
tức khảo sát/gọi điện, việc của người.

> **Cập nhật 2026-08-30 — hai đính chính về chính mục này:**
>
> 1. Danh sách từng chỉ nằm ở `C:\tmp\apply_log.json`, **ngoài kho, không được
>    version** — một lượt dọn ổ đĩa là mất trắng. Nay đã xuất vào kho:
>    **`docs/2026-08-30-entity-can-khao-sat.csv`** (mở được bằng Excel,
>    167 dòng = 157 `can_bo_sung` + 10 `ten_rieng` của mục §6; mỗi dòng ghi rõ
>    THIẾU GÌ nên cầm đi khảo sát được ngay).
> 2. Chữ "gắn cờ" trong ROADMAP là **nói quá**: cờ `can_bo_sung` CHƯA HỀ được ghi
>    vào dữ liệu (`web/data.json` không có khoá nào chứa `bo_sung`; DB 0 hàng).
>    Phân loại chỉ tồn tại trong nhật ký chạy. Ghi cờ thật vào dữ liệu là thao tác
>    cần B1 + chỉ đạo của chủ dự án — chưa làm.

Cũng phát hiện vài dữ liệu **nghi sai** cần chủ xác nhận:
- ~~`khach-san-khoi-hoa` có `ocop_star = 2`~~ → **rộng hơn nhiều so với báo cáo
  ban đầu, và đã chặn ở BÊN ĐỌC 2026-08-30 (`434bdeb6`).** Không phải một khách
  sạn: **13 cơ sở lưu trú** mang `ocop_star`, cả 13 đều bằng đúng `star_rating`
  của chính nó — vân tay chép nhầm cột. Trang chi tiết đang in «Sản phẩm OCOP 1
  sao» cho khách sạn, tức khai khống một chứng nhận nhà nước (§1.7). Đã gỡ 13 huy
  hiệu giả bằng hai luật (OCOP không có bậc 1–2 sao; số chỉ chép lại `star_rating`
  mà văn xuôi không xác nhận), giữ nguyên `somo-farm-cuu-long` vì nó có chứng nhận
  OCOP 4 sao THẬT. **Dữ liệu vẫn còn sai** — 13 ô `ocop_star` rác vẫn nằm đó; xoá
  chúng là thao tác dữ liệu, chờ chủ dự án.
- `lang-be---am-thuc-du-lich-sinh-thai` có `sub_category = lake`.
- `mandi-cafe` từng ghi "Đánh giá 7.3/5" (vượt thang) — đã bỏ khi viết lại.

---

## 4b. Meta SEO của 8 trang con còn tên tỉnh cũ (ROADMAP §41) — đánh đổi thật

99 lần nhắc tỉnh cũ / 30 file FE, đã phân thành 4 lớp (máy-đọc cần sửa · taxonomy ·
đúng-rồi-đừng-đụng · tên riêng). Lớp "cần sửa" nặng nhất là `utils/pageManifest.ts`
(20 chỗ: `seoTitle`/`seoDescription`/`ogDescription`/`heroSubtitle` của từng trang
danh mục) — và nó vướng đánh đổi:

- (a) **Bỏ hẳn tên tỉnh cũ khỏi meta trang con** — đúng §1.6 tuyệt đối, nhưng **mất**
  truy vấn «du lịch Bến Tre», «OCOP Trà Vinh» mà người dân còn tìm nhiều năm nữa.
- (b) **Giữ tên cũ kèm dấu lịch sử ngắn** («… Bến Tre, Trà Vinh cũ») — giữ truy vấn,
  tốn ~12 ký tự trong ngân sách 155 của mỗi mô tả.

Đây là đánh đổi SEO/nội dung, không phải sửa kỹ thuật. Site đang noindex nên **chưa
mất gì**, nhưng việc này phải xong TRƯỚC khi mở index.

---

## 5. Track-H — pháp lý (giữ nguyên, vẫn chờ luật sư)

Không đổi so với đánh giá 2026-08-21, nhắc lại vì vẫn là mục treo nghiêm trọng nhất:
- **Luật 91/2025/QH15** (Bảo vệ dữ liệu cá nhân, hiệu lực 01/01/2026) đã thay khung
  NĐ13 mà mọi ghi chú pháp lý trong repo đang dựa vào.
- **Ranh giới TMĐT** của mô hình premium/featured listing hẹp hơn giả định §1.4.

Hồ sơ câu hỏi đã soạn sẵn: `docs/2026-08-22-cau-hoi-cho-luat-su.md`.

---

## 6. Việc chờ nguồn dữ liệu chính thức (không phải nợ kỹ thuật)

- Bảng ánh xạ xã-cũ → xã-mới (124 đơn vị) — cần văn bản chính thức.
- 10 entity còn tên riêng chứa "tỉnh X" trong whitelist R10.7 — chờ chủ soát tên
  hiển thị (vd `Cửa hàng OCOP tỉnh Bến Tre` là tên đơn vị đặt trước 7-2025).
- Re-author `xa-hung-khanh-trung`; quyết `require_admin` cho `/search/enhanced`.

---

## 6b. BỐN KHOẢN MỚI — phát sinh từ đợt "hoàn thiện việc còn lại" (2026-08-30)

Cả bốn đều đã được CHẶN ở phần máy tự làm được; phần còn lại đúng là quyền của chủ.

**(a) 13 ô `ocop_star` rác vẫn nằm trong dữ liệu.** Huy hiệu giả đã tắt ở bên đọc
(`434bdeb6`) nên trang không còn khai khống. Nhưng `web/data.json` + DB vẫn mang 13
giá trị sai; xoá chúng là thao tác dữ liệu (B1 + §4). Riêng `homestay-sokfram` cần
mắt người: văn xuôi của nó nói nó BÀY BÁN sản phẩm OCOP 3–5 sao của địa phương, tức
`ocop_star=5` gần chắc là chép nhầm — nhưng "gần chắc" không đủ để máy xoá.

**(b) 255 file nhật ký kiểm toán rác + phần rác đã lẫn vào nhật ký thật.** Test đã
ngừng ghi vào đó (`296e1d04`), nhưng `agent/data/admin_audit.*.jsonl` còn 255 file và
`admin_audit.jsonl` 1,3 MB là trộn lẫn thao tác thật với rác test. Xoá nhật ký kiểm
toán thì càng không tự tiện — chờ chỉ đạo.

**(c) `POST /admin/relationships` KHÔNG kiểm hai đầu có tồn tại.** Route trả 201 và
ghi quan hệ treo đầu; `Database.add_relationship` chèn thẳng `INSERT OR IGNORE`.
Hiện DB dev có đúng 1 hàng như vậy (di tích, rò đã bịt từ 2026-08-28). Vô hình với
người dùng vì `get_relationships` JOIN hai đầu. **Câu hỏi:** có nên chặn ở tầng
admin không? Chặn sẽ cấm luôn cách dùng "tạo quan hệ trước, tạo entity sau". Máy
không tự đổi hành vi một API quản trị; đã viết lại test cho nó nói đúng lỗ hổng thay
vì che (`6bbe508b`). Xoá hàng rác kia cũng là §4.

**(d) Ba cổng nằm NGOÀI lệnh nghiệm thu §5, và cả ba đều từng đỏ mà không ai biết:**
`npx vitest run` (đỏ 3 ngày), `npm run typecheck` (đỏ sẵn), và `node
scripts/check-tri-region-contrast.mjs`. Cả ba nay xanh. **Đề nghị:** bổ sung chúng
vào §5 của CLAUDE.md để lần sau không phải phát hiện bằng may mắn. Đây là sửa hiến
pháp nên xin chủ chốt.

---

## 7. Dung lượng máy (ngoài dự án)

Đã dọn phần thuộc quyền trong đợt trước: Downloads 14 GB → 0,9 GB, vhdx Docker
32,7 → 24 GB, Temp/pytest/playwright/pnpm. Còn **chờ chủ**: `.codex/sessions`
8 GB, `Claude/vm_bundles` 9 GB, `Packages` 10,6 GB, `Documents` 37,9 GB (repo dự
án khác — muốn tỉa `node_modules` các repo ngủ thì ra lệnh). Máy hiện ~22 GB trống.
