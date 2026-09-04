> STATUS: active
Authority: config/release-authority.json

# QD-05 — Lập chỉ mục công khai (`public_indexing`)

> **Hồ sơ này CHƯA KÝ.** Máy **không được** điền §7. Gỡ noindex là cổng cuối cùng trước
> khi site có mặt trước công chúng; một agent điền §7 ở đây là tự cấp cho mình quyền
> công bố.

`decision_key`: `public_indexing` · Cổng liên quan: `docs/QUYET-DINH-DANG-CHO.md` mục B7

---

## 1. BỐI CẢNH

**Noindex toàn site đang BẬT, và bật theo kiểu mặc định-an-toàn.**
`web-nuxt/nuxt.config.ts:6`:
`const siteNoindex = process.env.NUXT_PUBLIC_SITE_NOINDEX !== 'false'` — phải **chủ động**
đặt chuỗi `'false'` mới tắt được. Quên biến, gõ sai chính tả, hay biến rỗng đều rơi về
"bật". `CLAUDE.md` §1.7 ghi đây là lựa chọn chủ động của chủ dự án, chỉ mở khi chủ dự án
quyết.

**Đã có một chính sách chỉ mục viết sẵn, nhưng chưa ai ký để dùng nó.**
`config/launch-indexing-policy.json`:

- `:2` `"schema_version": 1`, `:3` `"revision": "launch-indexing-policy-v1"`.
- `:4` `"canonical_origin": "https://vinhlong360.vn"`.
- `:5` `"unknown_policy": "noindex-follow-public"` — đường nào không khai thì mặc định
  không cho lập chỉ mục. Đây là mặc định đúng chiều.
- Khối `exact_routes` (`:14` trở đi) khai 26 đường `indexable-public` và 6 đường
  `noindex-follow-public`, trong đó `/cong-dong` là noindex (`:45`).
- Khối `sensitive_prefixes` (`:48`) chặn crawl 22 tiền tố (`/admin`, `/api`, `/auth`,
  `/health`, `/tai-khoan`…).
- Khối `dynamic_templates` (`:73`) giao quyền cho backend với `/dia-diem/{entity_id}` và
  `/xa-phuong/{ward_id}`, và ghim `fixed-noindex` cho `/bai-viet/{id}`,
  `/nguoi-dung/{id}`, `/lich-trinh/{id}`, `/lich-trinh-chia-se/{id}`.

**Sản phẩm tự khai đây là khoản phải quyết riêng.**
`web-nuxt/utils/legalContent.ts:67` — khoản `public_indexing` trong khối
`decisionRequired`: phạm vi lập chỉ mục công khai cần quyết định riêng; **không mặc định
coi nội dung là public-indexed**. Cùng khối này là `residency` (`:65`) và
`processors_subprocessors` (`:66`), tức chỉ mục được xếp cùng hạng với các khoản pháp lý,
không phải một thiết lập SEO.

**Một mâu thuẫn phải nêu ra trước khi ký, không phải sau.**
`config/launch-indexing-policy.json:38-40` xếp `/khu-vuc/vinh-long`,
`/khu-vuc/ben-tre`, `/khu-vuc/tra-vinh` là `indexable-public`. `CLAUDE.md` §1.6 chốt rằng
"tỉnh Bến Tre/Trà Vinh" chỉ được xuất hiện trong văn cảnh lịch sử có chữ "cũ/trước
7-2025". Khoản này đã có sổ riêng: `docs/QUYET-DINH-DANG-CHO.md` mục A5 (taxonomy 3 vùng
mang tên tỉnh cũ). **Mở chỉ mục cho ba đường đó là công bố ba trang hub mang tên đơn vị
hành chính không còn tồn tại** — và trang đã lập chỉ mục thì đắt hơn nhiều để rút lại.
*(Ghi chú: đây là nhận xét đối chiếu hai file trong repo, không phải kết luận SEO.)*

**Đợt rà soát xếp public launch ở NO_GO.** Mục "Public launch — No-Go hiện tại" của
`docs/audit-toan-du-an-2026-08.md` liệt các điều kiện còn đồng thời chưa đóng, trong đó
có: trust coverage thực địa gần như bằng 0; căn cứ pháp lý, nơi lưu trữ, SLA gỡ nội dung
và ranh giới thương mại chưa được chủ/luật sư chốt; deploy chưa có rollout/rollback thật;
monitoring chưa chứng minh alerting; backup chưa qua restore.

**Chưa kiểm được:** hồ sơ này **không** đo lại số trang đủ chất lượng để lập chỉ mục.
Con số 405 trang index / ~1.200 noindex ghi ở `docs/QUYET-DINH-DANG-CHO.md` mục B7 là số
đo của một phiên khác; tôi không tự đo lại trong phiên này nên không dùng nó làm căn cứ
quyết định.

## 2. LỰA CHỌN

1. **Giữ noindex toàn site suốt closed pilot.** Không đụng `NUXT_PUBLIC_SITE_NOINDEX`.
   Pilot chỉ mở cho nhóm được mời, đúng như mô tả closed pilot trong
   `docs/audit-toan-du-an-2026-08.md` §7.
2. **Mở đúng tập `exact_routes` đã khai `indexable-public`** trong
   `config/launch-indexing-policy.json`, giữ toàn bộ `dynamic_templates` ở noindex. Tập
   này là các trang tổng quan và trang chính sách — nội dung ít phụ thuộc dữ liệu entity
   nhất.
3. **Mở như (2) nhưng trừ ba đường `/khu-vuc/*`** (`:38-40`) cho tới khi mục A5 của
   `docs/QUYET-DINH-DANG-CHO.md` được chốt.
4. **Mở hết, kể cả `dynamic_templates`.**

## 3. ĐÁNH ĐỔI

- **(1)** không mất gì có thể mất, và giữ đúng `CLAUDE.md` §1.7. Đổi lại site vô hình:
  không có người dùng thật thì không có phản hồi thật, nên mọi công việc nội dung và
  hiệu năng vẫn là giả thuyết. Đây cũng chính là cái giá đã ghi ở mục B7 của sổ quyết
  định.
- **(2)** bắt đầu tích luỹ tín hiệu trên phần ít rủi ro nhất, và tôn trọng
  `unknown_policy` (`:5`) — đường không khai thì không lập chỉ mục. Đổi lại vẫn công bố
  ba trang `/khu-vuc/*` đang mâu thuẫn với `CLAUDE.md` §1.6, và mở chỉ mục trong khi
  các khoản pháp lý (`QD-02`) và nơi lưu trữ (`QD-04`) chưa ký thì trang chính sách bảo
  mật được lập chỉ mục lại chính là trang chưa được duyệt câu chữ.
- **(3)** đóng đúng mâu thuẫn đã nêu, chi phí gần bằng (2). Đổi lại: ba trang hub vùng là
  cấu trúc điều hướng chính của site, nên bỏ chúng khỏi chỉ mục làm gãy quan hệ
  hub–spoke tới các trang xã/phường. Và nó buộc mục A5 phải được quyết trước — tức
  chuyển một khoản đang treo thành một khoản chặn.
- **(4)** đơn giản nhất để làm, đắt nhất để sai. Uy tín miền trước máy tìm kiếm là thứ
  khó phục hồi nhất, và `dynamic_templates` bao gồm cả `/nguoi-dung/{id}` —
  `config/launch-indexing-policy.json` đang cố ý ghim nó `fixed-noindex`, tức chính sách
  hiện tại coi trang hồ sơ người dùng là **không nên** lập chỉ mục.

## 4. AI CHỊU ẢNH HƯỞNG

- **Uy tín miền trước máy tìm kiếm** — thứ đắt nhất để phục hồi nếu mở sớm với nội dung
  mỏng.
- **Người dùng có hồ sơ công khai**: nếu chọn (4), `/nguoi-dung/{id}` rời khỏi trạng thái
  `fixed-noindex` mà chính sách đang đặt cho nó.
- **Chủ dự án**: mọi câu chữ pháp lý được lập chỉ mục là câu chữ công bố ra công chúng,
  trong khi `web-nuxt/utils/legalContent.ts:64` vẫn ghi mốc 24/48 giờ là mục tiêu chờ
  duyệt.
- **Mục A5 và B7** của `docs/QUYET-DINH-DANG-CHO.md` — hai khoản đã treo sẵn, ràng trực
  tiếp vào hồ sơ này.

## 5. NẾU KHÔNG QUYẾT

Site ở lại vô hình — an toàn, và là trạng thái đúng cho tới khi các cổng khác đóng. Rủi
ro thật nằm ở chiều ngược lại: `web-nuxt/nuxt.config.ts:6` chỉ cần **một biến môi trường
đặt sai** là toàn bộ site chuyển sang cho phép lập chỉ mục, không qua hồ sơ nào, không có
ai xác nhận. Hồ sơ này tồn tại để lần đó không xảy ra một cách tình cờ.

## 6. BẰNG CHỨNG PHẢI KÈM KHI KÝ

1. Trạng thái các cổng khác tại thời điểm ký: `QD-02` (pháp lý) và `QD-04` (nơi lưu trữ)
   đã ký hay chưa. Mở chỉ mục trước hai khoản đó là công bố câu chữ chưa được duyệt.
2. Quyết định cho mục A5 (`docs/QUYET-DINH-DANG-CHO.md`) nếu `chosen_option` bao gồm ba
   đường `/khu-vuc/*` (`config/launch-indexing-policy.json:38-40`).
3. Một lượt đo lại số trang đủ chất lượng để lập chỉ mục, chạy trong cùng cửa sổ với chữ
   ký — không dùng lại con số của phiên trước.
4. Kiểm chứng rằng thẻ robots thật của từng nhóm đường khớp với
   `config/launch-indexing-policy.json` **trước** khi đổi
   `NUXT_PUBLIC_SITE_NOINDEX`, vì hiện noindex toàn site đang che cho mọi lệch ở tầng
   per-page.
5. Mục `public_indexing` trong `config/decision-records.json` được cập nhật cùng lúc, kèm
   `record_sha256` băm từ chính file này tại thời điểm ký.

## 7. CHỐT CỦA CHỦ DỰ ÁN

Trạng thái: CHƯA KÝ

| Trường | Giá trị (chỉ chủ dự án điền) |
|---|---|
| decision_key | |
| chosen_option | |
| signed_by | |
| signed_at | |
| signature | |
