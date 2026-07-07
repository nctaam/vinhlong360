# SP6 Content — Design

> **STATUS (2026-07-07): active — chủ đã duyệt 3 quyết định phạm vi, chờ duyệt spec toàn văn.**
> Thuộc chương trình chuẩn-hoá (spec mẹ: `2026-07-07-chuan-hoa-program-design.md`). Grounding: workflow 5-agent đo trên data thật 2026-07-07 (1.766 entity, 439 index-worthy).

## Quyết định chủ dự án (2026-07-07)

1. **Xoá cả 7 entity HOLD** — audit 3 nguồn độc lập kết luận 4 bịa/sai-thực-thể + 3 trùng-kém-hơn; zero side-effect (0 tham chiếu). Ưu tiên `thanh-loc` (thông tin bịa về người thật). Nếu sau này có nguồn thật → tạo entity MỚI, không khôi phục bản nhiễm.
2. **Phạm vi viết-lại: Keystone + cụm 407 có tín hiệu** — nhóm index-worthy đầy đủ + ~209 quán ăn/cà phê <80 từ ĐÃ có `specialty` thật. Accommodation (0/164 có specialty — nghèo tín hiệu) KHÔNG viết đợt này.
3. **Mở rộng OFFICE_KINDS** thêm `giao_thong` / `ngan_hang` / `vien_thong` / `cua_hang` (schema change + test theo B4).

## Grounding — số đo chốt (2026-07-07)

| Mặt | Số đo | Ghi chú |
|---|---|---|
| Filler R50.2 | 370 lượt filler thật ("miền Tây") / 200 entity; 56 index-worthy; 106 lượt trong attributes | 7 pattern khác = 0 toàn kho; 37 lượt "Bến xe Miền Tây" = danh từ riêng cần whitelist |
| Formula R50.3 | Tọa lạc 9 · Nằm ở 5 · câu-đầu-chứa-"là một" 34 · superlative trơ 19 · kết sáo 0; union 38 index-worthy | regex loose (câu đầu chứa " là một ") mới bắt đúng |
| Thin R50.4 | 245 entity <200 ký tự (185 trong cụm 407); median site 76 từ; 67 entity dải 120-129 từ | index-worthy: 439, toàn bộ ≥130 từ |
| R10.3b | 49 = facility.office_kind 34 + craft_village.specialty 15; suy-tự-động 21, cần-enum-mới 28 | person.role + accommodation.accommodation_type đã phủ 100% |
| desc==summary | 113 entity (đa số place/phường) | UI đã dedup nhưng data vẫn in đôi |
| Nguồn | 403/439 iw (92%) có chỗ bám (316 URL ngoài · corpus · web-log MATCH 356); 36 iw trống hoàn toàn; 720 entity source không URL | corpus 21 hồ sơ + catalog 62 + 194 bài BáoVL + 117 URL THVL CHƯA nối vào source |
| HOLD | 7/7 không cứu được | verdict FABRICATED×2, trùng×3, nhầm người thật×1, nghi bịa×1 |

## Nguyên tắc bất di bất dịch của SP6

- **CHỈ viết từ nguồn có thật**: (a) attributes sẵn có của entity, (b) trang nguồn ĐÃ FETCH (không viết từ snippet 1-2 câu), (c) hồ sơ corpus trong docs/research. Entity không nguồn → **GIỮ NGUYÊN** (36 iw trống nguồn không đụng).
- **Cấm bịa** fact thực địa (món/giá/giờ/năm/giải thưởng) — R10.5. Superlative trơ: bổ sung bằng chứng từ nguồn hoặc XOÁ từ, không thay bằng superlative khác.
- Mỗi bài viết lại qua **adversarial verify**: agent thứ hai đối chiếu TỪNG fact mới với nguồn đã fetch; fact không truy được nguồn → loại trước khi áp.
- Giọng theo playbook §4: mở bằng chi tiết cụ thể, ≥1 danh từ riêng/câu, khiếm khuyết trung thực khi nguồn có, không rule-of-three, không CTA sáo.
- Đích của cụm 407 là **hết thin trung thực** (≥200 ký tự fact thật: specialty/must_order/địa chỉ/loại món), KHÔNG phải độn lên 130 từ để index — cụm này vẫn noindex theo playbook P0-2.

## Workstreams

- **W1 · Dọn nền**: backup B1 → xoá 7 HOLD khỏi local SQLite → local = prod = data.json = 1.766 tuyệt đối.
- **W2 · Enum + auto-fill R10.3b**: mở rộng OFFICE_KINDS (4 mục mới, +test B4, sửa cả label "Loại cơ quan" → "Loại cơ quan / tiện ích"); script fill 21 ca suy-được (15 craft specialty từ name/desc — lọc bẫy 'mộc mạc/trường hợp'; 6 y_te) + 28 ca theo enum mới; --dry-run trước (R70.5); ghi cả 3 kho. Đích: R10.3b 49 → 0.
- **W3 · Nối nguồn**: script map tên corpus/catalog/evidence-matrix/THVL-urls → entity.source (thêm URL + trích dẫn, KHÔNG ghi đè nguồn cũ); tách nhãn quy trình (curated/auto-learn/foody-không-URL) sang key riêng để R10.8 tương lai đo đúng "URL thật". Đo lại phủ nguồn sau nối.
- **W4 · Campaign viết lại** (workflow đa agent, mỗi entity: fetch-nguồn → viết → verify → áp):
  - A (~85 iw): union 56 filler + 38 formula + 13 superlative trong index-worthy — viết lại theo nguồn.
  - B (67): dải 120-129 từ — thêm 1-3 câu fact từ nguồn → vượt ngưỡng 130 (tăng trang index).
  - C (113): desc==summary — có nguồn thì viết description riêng; không nguồn → để description trống (hết in đôi).
  - D (~209): cụm 407 có specialty — dệt specialty/must_order/địa chỉ thành mô tả trung thực ≥200 ký tự; specialty generic ('Cà phê') viết được bao nhiêu viết bấy nhiêu, không độn.
  - E (~144 entity non-iw còn "miền Tây"): sweep thay đặc-thù theo match-old (pattern SP2), không cần viết lại cả bài.
- **W5 · Gate**: R50.2 thêm whitelist danh từ riêng ("Bến xe Miền Tây"…); R50.3 bật check mở-bài-công-thức (^Tọa lạc | ^Nằm (ở|tại|trong|bên) | câu đầu chứa " là một ") soft-ratchet, baseline đo sau campaign (kỳ vọng iw = 0); quét đệ quy attributes.
- **W6 · Kết đợt**: đồng bộ 3 kho (local → prod → export data.json, restart vl-agent, health đúng port 8360) + baseline --write cùng commit giải trình + pytest/build + scorecard (content-dim TĂNG, không dim tụt) + plan-result + merge + memory.

## DoD (số cứng)

- 3 kho = 1.766 entity, text đồng nhất (verify script SP2 tái dùng) · R10.3b = 0 · R50.2 index-worthy = 0 và tổng ≤170 (từ 429, sau whitelist danh-từ-riêng + campaign — số chốt lại trong plan khi đo với whitelist) · R50.3 bật, iw-nợ = 0 · R50.4 ≤ 120 (từ 245; phần giữ lại = accommodation không tín hiệu + không nguồn) · desc==summary ≤ 20 · 0 fact mới không nguồn (verify log kèm plan-result) · 67 entity dải 120-129: ≥50 vượt ngưỡng index · pytest/build xanh · scorecard content-dim tăng.

## Ngoài phạm vi SP6

Mở noindex toàn site (chủ quyết riêng) · viết cụm accommodation 164 · 36 iw trống nguồn · ảnh AI (GĐ8) · đổi id chom-chom-binh-hoa-phuoc-rambutan (backlog) · siết ngưỡng is_index_worthy lên 150 từ (cần làm dày 159 trang dải 130-149 trước — backlog SP6.2).

## Điều kiện dừng

Nguồn mâu thuẫn nhau về 1 fact → giữ nguyên text cũ + ghi chú vào plan-result, không tự phân xử. Prod apply lỗi → restore pg_dump, báo chủ. Verify bắt >10% bài có fact không nguồn → DỪNG campaign, xem lại prompt trước khi chạy tiếp.
