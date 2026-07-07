# SP6 Content — Design v2 (KHẮC KHE)

> **STATUS (2026-07-07): active — v2 theo yêu cầu chủ "nâng cấp, yêu cầu cao hơn, khắc khe hơn"; chờ duyệt toàn văn.**
> Thuộc chương trình chuẩn-hoá (spec mẹ: `2026-07-07-chuan-hoa-program-design.md`). Grounding: workflow 5-agent đo trên data thật 2026-07-07 (1.766 entity, 439 index-worthy). v1 → v2: mọi đích "giảm %" nâng thành "về 0 hoặc nợ-có-hồ-sơ"; gate content lên hard-ratchet; verify 2 tầng + re-audit mẫu; vá lỗ hổng R10.8 đang đo sai chất.

## Quyết định chủ dự án (2026-07-07)

1. **Xoá cả 7 entity HOLD** — audit 3 nguồn độc lập kết luận 4 bịa/sai-thực-thể + 3 trùng-kém-hơn; zero side-effect. Ưu tiên `thanh-loc` (thông tin bịa về người thật). Có nguồn thật sau này → tạo entity MỚI, không khôi phục bản nhiễm.
2. **Phạm vi viết-lại: Keystone + cụm 407 có tín hiệu** (~209 quán <80 từ có `specialty`). v2 siết thêm: accommodation và entity "bỏ qua" đều phải **được THỬ nguồn trước khi kết luận giữ** — không bỏ qua mù (xem W4bis).
3. **Mở rộng OFFICE_KINDS** thêm `giao_thong` / `ngan_hang` / `vien_thong` / `cua_hang` (schema change + test theo B4).

## Grounding — số đo chốt (2026-07-07)

| Mặt | Số đo | Ghi chú |
|---|---|---|
| Filler R50.2 | 370 lượt filler thật ("miền Tây") / 200 entity; 56 index-worthy; 106 lượt trong attributes | 7 pattern khác = 0 toàn kho; 37 lượt "Bến xe Miền Tây" = danh từ riêng cần whitelist; FE ~20 occ (một phần là câu địa-văn-hoá hợp lệ) |
| Formula R50.3 | Tọa lạc 9 · Nằm ở/tại/trong/bên 5 · câu-đầu-chứa-"là một" 34 · kết sáo 0; union 61 entity, 38 index-worthy | regex loose (câu đầu chứa " là một ") mới bắt đúng |
| Superlative trơ | "nổi tiếng" không số/năm/nguồn cùng câu 10 + "nhất vùng" 9 = 19 entity (13 iw) | tách thành gate riêng R50.5 (v2) |
| Thin R50.4 | 245 entity <200 ký tự (185 trong cụm 407, accommodation 83); median site 76 từ; 67 entity dải 120-129 từ | index-worthy: 439, toàn bộ ≥130 từ |
| R10.3b | 49 = facility.office_kind 34 + craft_village.specialty 15; suy-tự-động 21, cần-enum-mới 28 | person.role + accommodation.accommodation_type đã phủ 100% |
| desc==summary | 113 entity (đa số place/phường) | UI đã dedup nhưng data vẫn in đôi |
| Nguồn | 403/439 iw (92%) có chỗ bám; **89/439 iw không URL ngoài** (34 chỉ self-link); 36 iw trống hoàn toàn; 720 entity source là nhãn không-URL | **R10.8 hiện đo "source non-empty" mà 100% entity có nhãn → gate đang vô hiệu về chất** — v2 phải siết semantics |
| Đơn vị HC cũ | "huyện X" còn sót trong data (vd khu-du-lich-vinh-sang "huyện Long Hồ") — chưa đo đếm | v2 thêm sweep + gate R10.10, đo trong plan |
| HOLD | 7/7 không cứu được | verdict FABRICATED×2, trùng×3, nhầm người thật×1, nghi bịa×1 |

## Nguyên tắc bất di bất dịch

- **CHỈ viết từ nguồn có thật**: (a) attributes sẵn có, (b) trang nguồn ĐÃ FETCH toàn văn (cấm viết từ snippet), (c) hồ sơ corpus docs/research. Không nguồn → GIỮ NGUYÊN text, nhưng phải có **verdict ghi hồ sơ** (no-source-found), không bỏ qua im lặng.
- **Cấm bịa** fact thực địa (món/giá/giờ/năm/giải thưởng) — R10.5. Superlative trơ: bổ sung bằng chứng từ nguồn hoặc XOÁ từ.
- **Verify 2 tầng độc lập mỗi bài**: (1) fact-lens — đối chiếu TỪNG fact mới với nguồn đã fetch, fact không truy được → loại; (2) voice-lens — chấm rubric checklist §8 playbook (test thay-tên, ≥1 danh từ riêng/câu, không formula/filler/superlative, khiếm khuyết trung thực khi nguồn có), **bài dưới 8/10 → viết lại**, tối đa 2 vòng, vẫn trượt → giữ text cũ + ghi hồ sơ.
- **Re-audit mẫu cuối đợt**: agent thứ ba lấy ngẫu nhiên ≥10% bài đã áp, đối chiếu lại từ nguồn gốc. Phát hiện ≥1 fact bịa lọt lưới → DỪNG, rà lại 100% batch chứa nó.
- Đích cụm 407 là **hết thin trung thực** (fact thật: specialty/must_order/địa chỉ/loại món), KHÔNG độn lên 130 từ để index — cụm này vẫn noindex theo playbook P0-2.

## Workstreams

- **W1 · Dọn nền**: backup B1 → xoá 7 HOLD khỏi local SQLite → local = prod = data.json = 1.766 tuyệt đối (verify script SP2).
- **W2 · Enum + auto-fill R10.3b**: mở rộng OFFICE_KINDS (4 mục mới + test B4 + label "Loại cơ quan / tiện ích"); script fill 21 ca suy-được (lọc bẫy 'mộc mạc/trường hợp/quảng trường/ATM-tại-bệnh-viện') + 28 ca theo enum mới; --dry-run trước (R70.5); ghi cả 3 kho. Đích: **R10.3b = 0**.
- **W3 · Nối nguồn + vá R10.8**: script map corpus/catalog/evidence-matrix/THVL-urls → entity.source (thêm URL + trích dẫn, không ghi đè nguồn cũ); tách nhãn quy trình (curated/auto-learn/foody-không-URL) sang key `provenance` để `source` chỉ còn nguồn kiểm chứng. **Siết check R10.8: RICH phải có ≥1 URL ngoài** (loại self-link vinhlong360.vn) — TDD sửa DataRichSourceCheck, đo lại sau khi nối nguồn + W4bis, baseline = số đo thật (đích ≤10), hard-ratchet.
- **W4 · Campaign viết lại** (workflow: fetch-nguồn → viết → fact-lens → voice-lens → áp, batch ≤50 entity/commit):
  - A (~90 iw): union 56 filler + 38 formula + 13 superlative trong index-worthy — viết lại theo nguồn, rubric ≥8/10.
  - B (67): dải 120-129 từ — thêm fact từ nguồn để vượt ngưỡng 130. **Xử lý 67/67** (không nguồn → verdict ghi hồ sơ); đích ≥55 vượt ngưỡng.
  - C (113): desc==summary — có nguồn → viết description riêng; không nguồn → để description trống. Đích: **desc==summary = 0** (mọi ca đều một trong hai hướng).
  - D (~209): cụm 407 có specialty — dệt specialty/must_order/địa chỉ thành mô tả trung thực; specialty generic vẫn phải THỬ web-log/fetch trước khi chấp nhận ngắn.
  - E (~144 non-iw còn "miền Tây" + toàn bộ occurrence còn lại): sweep match-old thay đặc-thù — đích **filler thật = 0 toàn kho** (data + FE; giữ lại duy nhất whitelist danh-từ-riêng/địa-văn-hoá per-occurrence).
  - F (mới): sweep "huyện/thị xã" đơn-vị-cũ trong data (đo → phân loại ngữ-cảnh-lịch-sử → sửa/whitelist như chiến dịch tỉnh-cũ SP2).
- **W4bis · Không-bỏ-qua-mù (mới)**: (a) **36 iw trống nguồn**: từng cái qua web-research tìm nguồn — tìm được → nối + đưa vào nhóm A; không → **fact-audit cắt claim không truy được** về mô tả tối thiểu an toàn, hoặc hạ noindex trung thực (đề xuất per-entity trong plan-result). 0 trang "dài mà không nguồn" giữ nguyên trạng. (b) **83 accommodation trong R50.4**: thử fetch web-log MATCH; có fact thật → viết; không → verdict no-source ghi hồ sơ.
- **W5 · Gate có răng (v2)**: R50.2 thêm whitelist per-occurrence (`whitelist-mien-tay.txt` kiểu tinh-cu) + **nâng hard-ratchet baseline 0** sau campaign; **R50.3 gate mới** (mở-bài công-thức + kết-sáo, quét cả summary, đệ quy attributes) **hard-ratchet baseline 0** sau dọn; **R50.5 gate mới** superlative-trơ soft-ratchet baseline 0; **R10.10 gate mới** đơn-vị-HC-cũ soft-ratchet baseline 0. Tất cả TDD như SP1.
- **W6 · Kết đợt**: đồng bộ 3 kho (local → prod → export data.json, restart vl-agent, health port 8360) + baseline --write cùng commit giải trình + pytest/build + scorecard + plan-result (kèm campaign-log: verdict từng entity đã chạm) + merge + memory.

## DoD v2 (số cứng — không đạt là chưa xong)

| # | Tiêu chí | Đích |
|---|---|---|
| 1 | 3 kho đồng nhất | 1.766 entity, text khác = 0 |
| 2 | R10.3b | **0** |
| 3 | Filler R50.2 (sau whitelist danh-từ-riêng) | **0 toàn kho** (data + FE), gate lên hard-ratchet |
| 4 | R50.3 formula (gate mới) | **0 toàn kho** (61 entity dọn sạch), hard-ratchet |
| 5 | R50.5 superlative trơ (gate mới) | **0** (19 entity: bổ chứng cứ hoặc xoá từ), soft-ratchet |
| 6 | desc==summary | **0** (113 ca đều xử một trong hai hướng) |
| 7 | R50.4 thin | **≤90** VÀ 100% ca còn lại có verdict no-source trong campaign-log (nợ-có-hồ-sơ, không nợ mù) |
| 8 | R10.8 siết (URL ngoài) | bật sau W3+W4bis, **baseline ≤10**, hard-ratchet |
| 9 | R10.10 đơn-vị-HC-cũ (gate mới) | baseline **0** sau sweep (whitelist ngữ-cảnh lịch sử) |
| 10 | 36 iw trống nguồn | 100% có kết cục: nguồn-mới / cắt-claim / noindex — **0 giữ nguyên trạng** |
| 11 | Nhóm B | 67/67 xử lý, ≥55 vượt ngưỡng index |
| 12 | Chống bịa | 0 fact mới không nguồn; re-audit mẫu ≥10% sạch; ngưỡng dừng campaign: >5% bài có fact không truy được nguồn |
| 13 | Chất lượng bài | 100% bài nhóm A đạt rubric ≥8/10 (voice-lens) |
| 14 | Scorecard | content-dim **≥80/100**; KHÔNG dim nào tụt |
| 15 | Hệ thống | pytest + build xanh (fail-đã-biết không tăng); prod health 200 |

## Ngoài phạm vi SP6

Mở noindex toàn site (chủ quyết riêng) · viết mô tả dài cho accommodation không-nguồn · ảnh AI (GĐ8) · đổi id chom-chom-binh-hoa-phuoc-rambutan (backlog) · siết ngưỡng is_index_worthy lên 150 từ (backlog SP6.2 — cần làm dày 159 trang dải 130-149 trước).

## Điều kiện dừng

Nguồn mâu thuẫn nhau về 1 fact → giữ text cũ + ghi hồ sơ, không tự phân xử. Prod apply lỗi → restore pg_dump, báo chủ. Fact-lens bắt >5% bài có fact không nguồn → DỪNG campaign, sửa prompt, chạy lại từ batch lỗi. Re-audit mẫu phát hiện fact bịa → DỪNG + rà 100% batch chứa nó. Rubric trượt 2 vòng → giữ text cũ, ghi hồ sơ, KHÔNG hạ chuẩn rubric.
