# Data Verification Report — vinhlong360

> Forensic audit: xác minh sự thật, phát hiện hallucination, đảm bảo data integrity.  
> Cập nhật: 2026-06-29

---

## MỤC LỤC
1. Executive Summary — Verdict tổng
2. Hallucination Scan (V1)
3. Geographic Verification (V2)
4. Name Verification (V3)
5. Historical Fact-Check (V4)
6. Culinary & Product Verification (V5)
7. Contact Info Verification (V6)
8. Source Attribution Audit (V7)
9. Relationship Truth Check (V8)
10. Itinerary Verification (V9)
11. Attribute Verification (V10)
12. Enrichment Pipeline Risk Assessment
13. Trust Score Distribution
14. Completeness Audit (secondary)
15. Fix Priority — Factual Errors First
16. Appendixes

---

## 1. EXECUTIVE SUMMARY

### Verdict tổng
- Total entities audited: 1745
- VERIFIED: 29 (1.7%)
- PARTIAL: 858 (49.2%)
- SUSPECT: 766 (43.9%)
- UNTRUSTED: 86 (4.9%)
- FABRICATED/confirmed false entities: 6 (0.3%)
- EMPTY: 0 (0.0%)

### Top findings
- P0 confirmed false: `hu-tieu-my-tho` gán Hủ tiếu Mỹ Tho cho Vĩnh Long; source độc lập xác nhận món do người Mỹ Tho chế biến.
- P0 confirmed false: `banh-cong-soc-trang` gán origin Trà Vinh cho Bánh cống Sóc Trăng; VnExpress mô tả đây là đặc sản/nguyên gốc Sóc Trăng.
- P0 confirmed false: `chua-sa-lon-chua-chen-kieu` đặt Chùa Sà Lôn/Chén Kiểu vào Trà Vinh; nguồn ngoài cho thấy thực thể thuộc khu vực Sóc Trăng cũ/Cần Thơ mới.
- Round 3 full coverage: 1745/1745 entities web-searched; current automated `MISMATCH` rows manually reviewed 27/27.
- Current `MISMATCH` adjudication: 4 confirmed P0, 9 P1 suspect, 14 false-positive search mismatches.
- Cumulative manual mismatch reviews: 38 cases; totals CONFIRMED_P0=5, P1_SUSPECT=14, FALSE_POSITIVE=19.
- Search `ERROR` rows: 19 DDGS timeouts/connect errors; these are not treated as evidence that entities do not exist.
- New P0 from Round 2: `chien-thang-giong-dua-giong-trom` is Tiền Giang/out-of-scope and its DB description is copied from an unrelated Chợ Lách tomb entry.
- New P0 from Round 2: `chua-ong-met-botum-vong-sa-som-rong` conflates Chùa Ông Mẹt (Trà Vinh) with Som Rong/Bô Tum Vông Sa Som Rông (Sóc Trăng/Cần Thơ mới).
- New P0 from Round 3: `khu-bao-ton-lung-binh-hoa-tra-vinh` is a contaminated entity whose content describes Lung Ngọc Hoàng in Hậu Giang/Cần Thơ mới, not a verified Trà Vinh nature reserve.
- Source risk: 1350/1745 entities (77.4%) chưa có URL nguồn độc lập; 449 source trỏ về chính platform.
- Coordinate risk: 74 exact-coordinate clusters >3 entities, 1106 clustered entities; cụm lớn nhất có 255 entities.
- Image completeness: 0/1745 entities có image URL.

### LLM enrichment impact
- Explicit LLM/agent-discovery source: 171/1745 (9.8%)
- Estimated LLM-like or unreviewed prose: 183/1745 (10.5%)
- LLM/no-url/self-source entities with factual claims: 1146
- Confirmed false claims in this pass: 6

### Overall trust score: 63.7/100

Từ sau đợt sắp xếp hành chính 2025, nhiều nguồn mới gọi vùng Bến Tre/Trà Vinh cũ là tỉnh Vĩnh Long mới. Báo cáo này vẫn kiểm tra theo legacy area trong data (`vinh-long`, `ben-tre`, `tra-vinh`) và không coi từ khóa 'Vĩnh Long' trong nguồn 2026 là lỗi nếu entity thuộc Bến Tre/Trà Vinh cũ.

External audit artifacts:
- Full entity matrix: `docs\data-verification-matrix.csv`
- Full claim inventory: `docs\data-verification-claims.csv`
- Full web cross-reference log: `docs\data-verification-web-log.csv`
- Full source URL audit: `docs\data-verification-sources.csv`
- P0 quarantine SQL: `docs\data-verification-fixes.sql`

---

## 2. HALLUCINATION SCAN (V1)

### 2.1 Pattern frequency
| Pattern | Occurrences | Interpretation |
| --- | --- | --- |
| H1 year | 593 | Needs source-level verification |
| H2 measurement | 1308 | Needs source-level verification |
| H3 date/season | 348 | Needs source-level verification |
| H4 hours | 601 | Needs source-level verification |
| H5 phone | 288 | Needs source-level verification |
| H6 OCOP | 654 | Needs source-level verification |
| H7 named/superlative/certificate | 3881 | Needs source-level verification |
| H8 explicit LLM source | 171 | Needs source-level verification |
| H9 no-URL source object | 903 | Needs source-level verification |
| H10 LLM prose fingerprint | 183 | Needs source-level verification |

### 2.2 Confirmed false claims
| # | Entity ID | Claim | Truth | Source | Fix |
| --- | --- | --- | --- | --- | --- |
| 1 | hu-tieu-my-tho | DB gán origin='Vĩnh Long' và area='vinh-long' cho Hủ tiếu Mỹ Tho. | Hủ tiếu Mỹ Tho là món do người Mỹ Tho chế biến; Mỹ Tho thuộc Tiền Giang cũ, ngoài 3 legacy areas. | [source](https://vi.wikipedia.org/wiki/H%E1%BB%A7_ti%E1%BA%BFu_M%E1%BB%B9_Tho) | Quarantine/remove from Vĩnh Long-specific dish catalog, or relabel as out-of-scope regional reference with origin='Mỹ Tho, Tiền Giang'. |
| 2 | banh-cong-soc-trang | DB gán origin='Trà Vinh' và area='tra-vinh' cho Bánh cống Sóc Trăng. | Nguồn báo chí mô tả bánh cống là đặc sản/nguyên gốc Sóc Trăng cũ. | [source](https://vnexpress.net/banh-cong-dac-san-cua-nguoi-khmer-o-soc-trang-4523101.html) | Quarantine/remove from Trà Vinh-specific dish catalog unless there is a local Trà Vinh serving-place entity with separate evidence. |
| 3 | chua-sa-lon-chua-chen-kieu | DB đặt Chùa Sà Lôn/Chùa Chén Kiểu ở Phường Trà Vinh, Trà Vinh và architectural_style='Chùa Việt'. | Chùa Sà Lôn/Chùa Chén Kiểu là chùa Khmer Nam tông ở khu vực Sóc Trăng cũ, nay thuộc Cần Thơ sau sáp nhập; không thuộc legacy Trà Vinh. | [source](https://vi.wikipedia.org/wiki/Ch%C3%B9a_S%C3%A0_L%C3%B4n) | Quarantine/remove from Trà Vinh scope. Do not rewrite to another unsupported province without a scoped data model. |
| 4 | chien-thang-giong-dua-giong-trom | DB đặt Di tích lịch sử Chiến thắng Giồng Dứa ở Bến Tre và phần mô tả lại nói về mộ hợp chất Chợ Lách. | Nguồn báo chí địa phương mô tả Di tích lịch sử Chiến thắng Giồng Dứa là di tích cấp quốc gia của tỉnh Tiền Giang; nội dung mộ hợp chất Chợ Lách không khớp với tên entity. | [source](https://tintucmientay.baoangiang.com.vn/tien-giang-chien-thang-giong-dua-lam-chan-dong-du-luan-trong-va-ngoai-nuoc-a361124.html) | Quarantine/remove khỏi Bến Tre scope. Không tự viết lại mô tả cho Tiền Giang nếu catalog chỉ phục vụ 3 legacy areas. |
| 5 | chua-ong-met-botum-vong-sa-som-rong | DB gộp tên Chùa Ông Mẹt với 'Botum Vong Sa Som Rong' và đặt architectural_style='Chùa Hoa'. | Chùa Ông Mẹt ở Trà Vinh là chùa Khmer Nam tông, còn Bô Tum Vông Sa Som Rông/Som Rong là một chùa Khmer khác ở Sóc Trăng/Cần Thơ mới. | [source](https://vovworld.vn/vi-VN/viet-nam-dat-nuoc-con-nguoi/chua-ong-met-di-tich-cap-quoc-gia-o-tinh-tra-vinh-2004638.vov5) | Quarantine entity để tách lại thành Chùa Ông Mẹt; bỏ cụm Som Rong và sửa phong cách kiến trúc chỉ sau khi có nguồn claim-level. |
| 6 | khu-bao-ton-lung-binh-hoa-tra-vinh | DB tạo entity 'Khu bảo tồn thiên nhiên Lung Bình Hòa' ở Trà Vinh nhưng summary/description lại nói về Khu bảo tồn thiên nhiên Lung Ngọc Hoàng ở Hậu Giang. | Khu bảo tồn thiên nhiên Lung Ngọc Hoàng là một thực thể khác, nằm ở vùng Hậu Giang/Cần Thơ mới; nội dung hiện tại không chứng minh sự tồn tại của 'Lung Bình Hòa' tại Trà Vinh. | [source](https://vi.wikipedia.org/wiki/Khu_b%E1%BA%A3o_t%E1%BB%93n_thi%C3%AAn_nhi%C3%AAn_Lung_Ng%E1%BB%8Dc_Ho%C3%A0ng) | Quarantine/remove entity. Không sửa tên hoặc địa chỉ nếu chưa có nguồn độc lập xác nhận 'Lung Bình Hòa' ở Trà Vinh. |

### 2.2b Round 3 manual adjudication of automated MISMATCH rows
The search classifier is intentionally noisy: it catches outside-area terms in snippets, including historical province names and unrelated top results. This full-coverage round reviewed 27/27 current automated `MISMATCH` rows before promoting anything to P0.

Verdict counts: CONFIRMED_P0=4; P1_SUSPECT=9; FALSE_POSITIVE=14.

| Entity ID | Manual verdict | Confidence | Finding | Source | Action |
| --- | --- | --- | --- | --- | --- |
| banh-cong-soc-trang | CONFIRMED_P0 | 95% | Area/origin DB gán Trà Vinh nhưng chính tên và nguồn ngoài đều chỉ Sóc Trăng. | [source](https://vnexpress.net/banh-cong-dac-san-cua-nguoi-khmer-o-soc-trang-4523101.html) | Keep quarantined as P0. |
| cha-lua-thanh-cong | FALSE_POSITIVE | 85% | Nguồn Báo Vĩnh Long xác nhận cơ sở chả lụa Thành Công ở Hiếu Phụng, Vũng Liêm; top result Sóc Trăng là nhiễu. | [source](https://baovinhlong.com.vn/kinh-te/202501/don-xuan-cung-san-pham-ocop-0ef5d8d/) | Không nâng P0; cần bổ sung nguồn OCOP/source chính thức. |
| chien-thang-giong-dua-giong-trom | CONFIRMED_P0 | 95% | Nguồn ngoài đặt Chiến thắng Giồng Dứa ở Tiền Giang, còn DB vừa gán Bến Tre vừa mô tả nhầm mộ hợp chất Chợ Lách. | [source](https://tintucmientay.baoangiang.com.vn/tien-giang-chien-thang-giong-dua-lam-chan-dong-du-luan-trong-va-ngoai-nuoc-a361124.html) | Quarantine/remove khỏi catalog Bến Tre. |
| chua-sa-lon-chua-chen-kieu | CONFIRMED_P0 | 95% | Nguồn ngoài đặt Chùa Sà Lôn/Chén Kiểu ở Sóc Trăng/Cần Thơ mới, không phải legacy Trà Vinh. | [source](https://vi.wikipedia.org/wiki/Ch%C3%B9a_S%C3%A0_L%C3%B4n) | Keep quarantined as P0. |
| dua-hau-tan-hung-ocop | FALSE_POSITIVE | 90% | Nguồn Vĩnh Long xác nhận Tân Hưng/Bình Tân là vùng dưa hấu; automated mismatch do từ 'Bình Tân' trùng ngoài-area term TP.HCM. | [source](https://baovinhlong.com.vn/video/202402/nong-dan-binh-tan-thu-hoach-nuoc-rut-dua-hau-tet-3180243/) | Không nâng P0; classifier cần phân biệt huyện Bình Tân Vĩnh Long và quận Bình Tân TP.HCM. |
| khu-luu-niem-nu-anh-hung-nguyen-thi-ut-ut-tich | FALSE_POSITIVE | 95% | Nguồn tỉnh xác nhận Khu tưởng niệm Nguyễn Thị Út tại Tam Ngãi, Cầu Kè, Trà Vinh cũ; snippet 'Cần Thơ' là ngữ cảnh hành chính lịch sử. | [source](https://vinhlong.gov.vn/LinkClick.aspx?fileticket=IrTz6niTXLs%3D&mid=10814&portalid=0&tabid=63) | Không nâng P0; nên đổi địa chỉ từ huyện cũ nếu dùng tỉnh mới 2025. |
| khu-tuong-niem-nguyen-thi-ut-ut-tich | FALSE_POSITIVE | 95% | Nguồn tỉnh xác nhận cùng thực thể ở Tam Ngãi, Cầu Kè, Trà Vinh cũ; không phải area mismatch. | [source](https://vinhlong.gov.vn/LinkClick.aspx?fileticket=IrTz6niTXLs%3D&mid=10814&portalid=0&tabid=63) | Không nâng P0; kiểm tra trùng lặp với entity khu-lưu-niệm. |
| nguyen-van-ton-thach-duong | FALSE_POSITIVE | 90% | Cục Di sản xác nhận Nguyễn Văn Tồn/Thạch Duồng gắn với Trà Ôn, Cầu Kè và Lăng Ông Trà Ôn; snippet An Giang chỉ là một sự kiện khác. | [source](https://dsvh.gov.vn/le-hoi-lang-ong-tra-on-3264) | Không nâng P0; bổ sung source Tier 1/2. |
| tuong-quan-nguyen-van-ton | FALSE_POSITIVE | 90% | Nguồn Cục Di sản xác nhận nhân vật Nguyễn Văn Tồn, năm 1763-1820 và Lăng Ông Trà Ôn; automated mismatch do snippet nhắc An Giang. | [source](https://dsvh.gov.vn/le-hoi-lang-ong-tra-on-3264) | Không nâng P0; bổ sung source Tier 1/2. |
| backpacker-mien-tay-3ngay-500k | P1_SUSPECT | 85% | Itinerary chứa nhiều giá, tuyến xe và mốc giờ không có source; top result ngoài An Giang chỉ cho thấy search không xác minh được itinerary này. | [source](https://tourmientay.vn/blogs/tour-ve-mien-tay-4-ngay-3-dem-2-ngay-dau-tai-an-giang-44) | Giữ UNTRUSTED; cần review route/cost từng chặng trước khi publish. |
| banh-mi-sau-hoa-ben-tre | P1_SUSPECT | 75% | Không tìm được nguồn độc lập cho quán Bánh mì Sáu Hoà Bến Tre; top result là Bánh mì Huynh Hoa TP.HCM, không liên quan. | [source](https://banhmihuynhhoa.vn/) | Human/Maps check tồn tại thật; gỡ claim 20+ năm, giờ mở cửa và giá nếu không có nguồn. |
| banh-trang-nem-cu-lao-may | FALSE_POSITIVE | 90% | Nguồn Báo Sài Gòn Giải Phóng xác nhận làng bánh tráng Cù Lao Mây và sản phẩm bánh tráng nem tại Vĩnh Long; classifier chỉ không nhận area. | [source](https://dttc.sggp.org.vn/ron-rang-lang-banh-trang-cu-lao-may-tram-nam-tuoi-post131500.html) | Không nâng P0; thêm source độc lập vào entity. |
| ben-xe-mien-tay-hcm | FALSE_POSITIVE | 95% | Bến xe Miền Tây đúng là ở TP.HCM và area=None; đây là node giao thông ngoài-scope dùng cho itinerary, không phải entity bị gán sai Vĩnh Long/Bến Tre/Trà Vinh. | [source](https://benxemiendong.com.vn/ben-xe-mien-tay/) | Giữ như external transport node hoặc tách taxonomy `external_gateway` để tránh bị tính là area mismatch. |
| bun-nuoc-leo-cho-ba-tri-ben-tre | P1_SUSPECT | 75% | Không có nguồn độc lập rõ cho quán bún nước lèo chợ Ba Tri; top result bị kéo sang bún nước lèo Sóc Trăng. | [source](https://cl.pinterest.com/pin/bn-nc-lo-mt-c-sn-quen-thuc-ca-cc-tnh-min-ty-nhng-vn-b-nhiu-ngi-lm-tng-l-bn-mm--886294401661397928/) | Human/Maps check; không publish giờ, giá, công suất/ngày nếu chưa xác minh. |
| chua-giac-linh | FALSE_POSITIVE | 90% | Nguồn du lịch sau sáp nhập hiển thị Chùa Giác Linh trong mục Trà Vinh và nêu quyết định di tích; domain Cần Thơ không phải bằng chứng sai area legacy. | [source](https://dulichcantho.vn/kham-pha-diem-den/tra-vinh/di-tich-chua-giac-linh-2171007.html) | Không nâng P0; vẫn cần thay LLM prose bằng claim có nguồn. |
| chua-khai-tuong | P1_SUSPECT | 85% | Top Tier 1 cho 'Chùa Khải Tường' là cổ tự Gia Định/TP.HCM; chưa có nguồn đáng tin xác nhận một Chùa Khải Tường nổi tiếng/di tích ở Ba Tri, Bến Tre. | [source](https://vi.wikipedia.org/wiki/Ch%C3%B9a_Kh%E1%BA%A3i_T%C6%B0%E1%BB%9Dng) | Quarantine P1; human verify thực thể cùng tên ở Ba Tri trước khi publish. |
| di-tich-duong-ho-chi-minh-tren-bien-ben-thanh-phong | FALSE_POSITIVE | 90% | Classifier bắt chữ 'Hồ Chí Minh' trong tên tuyến hậu cần, không phải TP.HCM; Bến Thạnh Phong là địa danh Bến Tre cần source địa phương bổ sung. | [source](https://vi.wikipedia.org/wiki/%C4%90%C6%B0%E1%BB%9Dng_H%E1%BB%93_Ch%C3%AD_Minh_tr%C3%AAn_bi%E1%BB%83n) | Không nâng P0; bổ sung nguồn Bến Tre/di tích cho địa điểm Bến Thạnh Phong. |
| homestay-con-ba-tu | FALSE_POSITIVE | 95% | Nguồn du lịch Bến Tre xác nhận Homestay Cồn Bà Tư; snippet nhắc TP.HCM chỉ là mô tả khoảng cách di chuyển. | [source](https://bentretourism.vn/vi/homestayconbatu2) | Không nâng P0; thay self-source bằng nguồn Bến Tre. |
| homestay-lang-be | FALSE_POSITIVE | 85% | DB đã có source vinhlong.gov.vn cho danh sách khách sạn/nhà nghỉ; top result localhome.vn là nhiễu search. | [source](https://vinhlong.gov.vn/du-khach/khach-san-nha-nghi) | Không nâng P0; cần kiểm tra lại xã An Khánh/Vĩnh Long theo mô hình hành chính mới. |
| hu-tieu-sa-dec-chu-tu-gan-cho-phu-hung-ben-tre | P1_SUSPECT | 80% | Không tìm được nguồn độc lập cho quán; top result nói về quán hủ tiếu ở Sa Đéc/Đồng Tháp. Tên 'Sa Đéc' có thể chỉ phong cách món, chưa đủ kết luận sai. | [source](https://dulichbinhphuoc.vn/13-quan-hu-tieu-sa-dec-ngon-ma-ban-nen-ghe/) | Human/Maps check tồn tại thật; gỡ claim giá/giờ/năm hoạt động nếu không có nguồn. |
| itinerary-tuan-trang-mat-mien-tay-4n3d | P1_SUSPECT | 85% | Itinerary có nhiều giá, resort, chi phí và giờ hoạt động không có source; top result Đà Nẵng là search noise, không xác minh được route. | [source](https://dulichdaiviet.com/tour-noi-dia/tour-du-lich-trang-mat-da-nang-4-ngay-3-dem-tu-ha-noi-tp-hcm.html) | Giữ UNTRUSTED; cần verify từng stop/price hoặc chuyển thành nội dung gợi ý không factual. |
| khoai-lang-binh-tan | P1_SUSPECT | 85% | Nguồn ngoài nói khoai lang Bình Tân đạt OCOP 4 sao, trong DB lại có cả `ocop='3 sao'` và `ocop_star=4`. | [source](https://tapchicongthuong.vn/magazine/emagazine--khoai-lang-binh-tan-but-pha-nho-ocop-317499.htm) | Review numeric/OCOP fields; chưa nâng P0 vì cần xác định sản phẩm/năm chứng nhận cụ thể. |
| khu-bao-ton-lung-binh-hoa-tra-vinh | CONFIRMED_P0 | 95% | DB entity Trà Vinh nhưng summary/description là Lung Ngọc Hoàng ở Hậu Giang/Cần Thơ mới; đây là content contamination rõ. | [source](https://vi.wikipedia.org/wiki/Khu_b%E1%BA%A3o_t%E1%BB%93n_thi%C3%AAn_nhi%C3%AAn_Lung_Ng%E1%BB%8Dc_Ho%C3%A0ng) | Quarantine/remove entity đến khi có nguồn xác nhận Lung Bình Hòa ở Trà Vinh. |
| p-tan-quoi | FALSE_POSITIVE | 90% | Snippet An Giang là lịch sử hành chính thế kỷ XIX; entity Phường Tân Quới hiện thuộc Vĩnh Long. | [source](https://vi.wikipedia.org/wiki/T%C3%A2n_Qu%E1%BB%9Bi) | Không nâng P0; classifier cần bỏ qua historic province context. |
| quan-thuan-phuc-vinh-long | P1_SUSPECT | 75% | Không tìm được nguồn độc lập cho Quán Thuận Phúc tại 135 Phạm Thái Bường; top result TikTok Kiên Giang không liên quan. | [source](https://www.tiktok.com/@phuc_vinh_thuan/video/7631125885692792085) | Human/Maps check; không publish giờ/giá/món nổi bật nếu chưa xác minh. |
| somo-farm-cuu-long | FALSE_POSITIVE | 90% | Nguồn chính của Somo Farm Cửu Long xác nhận thực thể; automated mismatch chỉ vì snippet không chứa area legacy. | [source](https://somofarmcuulong.somogroup.vn/) | Không nâng P0; cần bổ sung nguồn độc lập cho claim OCOP/star nếu publish. |
| tom-kho-binh-dai | P1_SUSPECT | 80% | Top result nói tôm khô Cà Mau; chưa có nguồn Tier 1/2 xác nhận Tôm khô Bình Đại/Anfoods OCOP như DB claim. | [source](https://sanphamocop.com.vn/dac-san-tet-cac-vung-mien-ma-ban-nen-biet-2/) | Giữ suspect; cần nguồn OCOP/địa phương trước khi publish claim Anfoods/OCOP 2023. |

### 2.3 Unverifiable claims (need human check)
Detected factual claims: 5101. Extracted claims contradicted by this audit: 10; confirmed false entities: 6. One P0 finding is entity/address scope rather than a single extracted sentence. Entity-level existence found by web search is not the same as claim-level verification; most claims remain `UNVERIFIED` in `docs\data-verification-claims.csv`.

Lowest-trust unverified examples:
| Entity | Type | Area | Score | Verdict | Source | Why |
| --- | --- | --- | --- | --- | --- | --- |
| chua-sa-lon-chua-chen-kieu | history | tra-vinh | 0 | FABRICATED | NO_URL | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_74;approximate_coordinates;missing_imag |
| banh-cong-soc-trang | dish | tra-vinh | 20 | FABRICATED | NO_URL | source_without_url;approximate_coordinates;missing_images;unverified_claims_1;mentions_outside_area: |
| chien-thang-giong-dua-giong-trom | history | ben-tre | 20 | FABRICATED | NO_URL | source_without_url;missing_images;unverified_claims_2;web_area_mismatch;confirmed_factual_error |
| chua-ong-met-botum-vong-sa-som-rong | history | tra-vinh | 20 | FABRICATED | INDEPENDENT_LOW | source_not_tier1_2;large_coordinate_cluster_74;approximate_coordinates;missing_images;unverified_cla |
| hu-tieu-my-tho | dish | vinh-long | 20 | FABRICATED | NO_URL | source_without_url;large_coordinate_cluster_89;approximate_coordinates;missing_images;unverified_cla |
| khu-bao-ton-lung-binh-hoa-tra-vinh | nature | tra-vinh | 20 | FABRICATED | NO_URL | source_without_url;approximate_coordinates;missing_images;unverified_claims_2;mentions_outside_area: |
| hu-tieu-sa-dec-chu-tu-gan-cho-phu-hung-ben-tre | restaurant | ben-tre | 22 | UNTRUSTED | NO_URL | source_without_url;large_coordinate_cluster_80;approximate_coordinates;missing_images;unverified_cla |
| lang-nghe-tau-hu-ky-my-hoa | attraction | vinh-long | 22 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_255;approximate_coordinates;missing_ima |
| itinerary-tuan-trang-mat-mien-tay-4n3d | itinerary |  | 24 | UNTRUSTED | NO_URL | source_without_url;llm_fingerprint;missing_coordinates;missing_images;unverified_claims_5;manual_p1_ |
| chom-chom-con-tan-quy | product | tra-vinh | 25 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_53;approximate_coordinates;missing_imag |
| thanh-that-cao-dai-vinh-long | history | vinh-long | 25 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_89;approximate_coordinates;missing_imag |
| vung-khoai-lang-binh-tan | craft_village | vinh-long | 26 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_89;approximate_coordinates;missing_imag |
| backpacker-mien-tay-3ngay-500k | itinerary |  | 28 | UNTRUSTED | NO_URL | source_without_url;missing_coordinates;missing_images;unverified_claims_3;mentions_outside_area:dong |
| khu-du-lich-lan-vuong | attraction | ben-tre | 28 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;coordinate_cluster_25;approximate_coordinates;missing_images;unv |
| so-huyet-tra-vinh | product | tra-vinh | 28 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;coordinate_cluster_20;approximate_coordinates;missing_images;unv |
| banh-mi-sau-hoa-ben-tre | restaurant | ben-tre | 30 | UNTRUSTED | NO_URL | source_without_url;large_coordinate_cluster_80;approximate_coordinates;missing_images;unverified_cla |
| bao-tang-tong-hop-tinh-tra-vinh | history | tra-vinh | 30 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_53;approximate_coordinates;missing_imag |
| bun-mam-mien-tay-vinh-long | dish | vinh-long | 30 | UNTRUSTED | NO_URL | source_without_url;llm_fingerprint;large_coordinate_cluster_255;approximate_coordinates;missing_imag |
| ca-chay-tra-on | product | vinh-long | 30 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_255;approximate_coordinates;missing_ima |
| ca-dieu-hong-nuoi-be-long-ho | product | vinh-long | 30 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_255;approximate_coordinates;missing_ima |
| ca-tra-thuong-pham-vinh-long | product | vinh-long | 30 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_89;approximate_coordinates;missing_imag |
| chua-ang-angkorajaborey | history | tra-vinh | 30 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_53;approximate_coordinates;missing_imag |
| chua-lo-gach | history | tra-vinh | 30 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_53;approximate_coordinates;missing_imag |
| chua-phuoc-son | history | vinh-long | 30 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_255;approximate_coordinates;missing_ima |
| chua-samrong-ek | history | tra-vinh | 30 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_74;approximate_coordinates;missing_imag |

### 2.4 LLM fingerprint analysis
The main LLM fingerprints are explicit `agent discovery`/`gpt` source labels, long polished descriptions without independent URLs, generic travel adjectives, and facts embedded in prose without source-specific attribution. This scan does not say every such entity is false; it says those entities cannot be trusted as factual until a human or crawler binds each claim to an external source.

---

## 3. GEOGRAPHIC VERIFICATION (V2)

**Scope:** 1745 entities.  
**Method:** bbox check (9.2–10.65 lat, 105.6–106.95 lon), exact coordinate cluster scan, outside-province keyword scan, and web-search area comparison for 1745 high-risk entries.

Findings:
- Missing coordinates: 6
- Coordinates outside tight bbox: 0
- Exact coordinate clusters >3 entities: 74
- Entities in large coordinate clusters: 1106
- Entities mentioning outside-area terms: 101

Largest coordinate clusters:
| Coordinate | Entity count | Example IDs |
| --- | --- | --- |
| 10.2542,105.9628 | 255 | vinh-long-1-day-backpacker, itinerary-mien-tay-nhiet-anh-001, cho-noi-tra-on-trai-nghiem-thuyen-hoa-qua, vl-accessibility-itinerary-001, lang-banh-trang-tra-on, lang-banh-trang-giay-tuong-loc |
| 10.2539,105.9722 | 89 | nha-hang-thien-tan, cu-lao-may-tra-on, cho-noi-tra-on-dc, khu-du-lich-s-mo-farm-cuu-long, nha-gom-tu-buoi, chua-khmer-vinh-long |
| 10.2272,106.4072 | 80 | ben-tre-couple-2day-001, ben-tre-vam-ho-birdwatching-t9-t3, itinerary-cai-mon-tet-ben-tre, ben-tre-1-ngay-con-phuong-tphcm, co-diem---banh-canh-vit-bot-xat, banh-canh-bot-xat |
| 9.9516,106.3322 | 74 | quyt-duong-cau-ke, cua-hang-ocop-tra-vinh-trung-tam-xuc-tien-thuong-mai-tinh-tra-vinh, cua-hang-dac-san-mien-tay-tra-vinh-tra-vinh, cho-dem-tra-vinh-pho-di-bo-hung-vuong-tra-vinh, nha-tho-chanh-toa-tra-vinh-tra-vinh, khu-du-lich-sinh-thai-huynh-kha |
| 9.9513,106.3346 | 53 | nguyen-thi-ut, thach-sok-xane, thach-oai, song-long-binh, canh-dong-dieu-tra-vinh, canh-dong-dien-gio-ngoai-khoi-ba-dong |
| 10.0260,106.2930 | 47 | tra-vinh-2-ngay-van-hoa-khmer, itinerary-ok-om-bok-tra-vinh-2024, dua-sap-sinh-to, com-dep-tra-vinh, cha-hoa-nam-thuy, banh-u-da-loc |
| 10.2433,106.3753 | 25 | khu-bao-ton-thien-nhien-thanh-phu, banh-trang-my-long, cho-thanh-phu, nha-dua-cocohome, khu-du-lich-lan-vuong, lang-nghe-cay-giong-cho-lach |
| 9.6621,106.5179 | 20 | monkey-tea---tra-sua-coffee, hu-tieu-go-duyen-hai-tra-vinh, quan-hai-san-duyen-hai-cho-duyen-hai-tra-vinh, khu-du-lich-sinh-thai-vung-dao-duyen-hai, tom-duyen-hai, chu-u-ba-dong |
| 9.9334,106.3122 | 17 | lang-nghe-che-tac-mat-na-khmer-nguyet-hoa, le-hoi-ok-om-bok, khu-van-hoa-du-lich-ao-ba-om, bao-tang-van-hoa-dan-toc-khmer-tra-vinh, bao-tang-van-hoa-dan-toc-khmer, bun-rieu-cua-thao-my |
| 10.2415,106.3759 | 17 | tom-cang-xanh-lot-an-thanh, lang-nghe-dan-gio-cong-dua-hung-phong, kem-baskin-robbins---sense-city, nha-hang-noi-ben-tre, quan-banh-uot-hai-nen, lau-3-con-tep |

Area mismatch report is in Appendix M. Confirmed errors are intentionally limited to cases with outside source support.

---

## 4. NAME VERIFICATION (V3)

**Scope:** 1745 names.  
**Method:** normalized duplicate scan, outside-place keywords, and web-search existence checks.

Duplicate exact names: 0 by current structural validation. Near-name risk remains for similarly named hotels and places; these need manual merge review, especially where coordinates are identical or near-identical.

Outside-area keyword hits:
| Entity | Area | Outside signal |
| --- | --- | --- |
| bao-tang-ben-tre | ben-tre | hcm |
| vinh-long-1-day-backpacker | vinh-long | hcm,tien-giang |
| ben-tre-couple-2day-001 | ben-tre | hcm |
| tra-vinh-2-ngay-van-hoa-khmer | tra-vinh | hcm |
| itinerary-mien-tay-nhiet-anh-001 | vinh-long | tien-giang |
| ben-tre-vam-ho-birdwatching-t9-t3 | ben-tre | hcm |
| ben-tre-1-ngay-con-phuong-tphcm | ben-tre | hcm |
| nha-co-huynh-thuy-le | ben-tre | dong-thap |
| mam-song-khoai-lang | vinh-long | hcm |
| den-tho-bac-ho | vinh-long | hcm |
| ben-xe-ben-tre-trung-tam-ben-tre | ben-tre | bac-lieu,ca-mau,can-tho,hcm,soc-trang |
| ben-tre-tong-tai-romantic-2day-001 | ben-tre | hcm,tien-giang |
| ben-xe-mien-tay-hcm |  | can-tho,hcm |
| lang-banh-trang-my-long | ben-tre | hcm |
| lang-nghe-tau-hu-ky-my-hoa | vinh-long | can-tho |
| dinh-an-hoi | ben-tre | hcm |
| lang-hoa-kieng-cai-mon-cho-lach | ben-tre | dong-thap |
| itinerary-vl-bt-tv-3d3t-giadinh |  | hcm,tien-giang |
| backpacker-mien-tay-3ngay-500k |  | dong-thap,hcm |
| itinerary-lang-nghe-vong-quanh |  | dong-thap |
| ninh-kieu-5---quoc-lo-60 | ben-tre | can-tho |
| cau-can-tho | vinh-long | can-tho |
| khu-du-lich-lan-vuong | ben-tre | hcm |
| khoai-lang-mam-song-cuon-la-cach | vinh-long | hcm |
| bun-mam-mien-tay-vinh-long | vinh-long | soc-trang |
| cua-hang-ocop-vinh-long-trung-tam-xuc-tien-thuong-mai-vinh-long | vinh-long | hcm |
| nha-thuc-pham-sach-khoai-lang-tim-binh-tan-vinh-long | vinh-long | hcm |
| shop-luu-niem-ben-ninh-kieu-gian-hang-vinh-long-vinh-long | vinh-long | can-tho |
| cua-hang-qua-tang-dac-san-ben-tre-mekong-delta-ben-tre | ben-tre | can-tho |
| rach-gam-ben-tre | ben-tre | tien-giang |
| cua-ben-gia-my-thanh-tra-vinh | tra-vinh | soc-trang |
| hu-tieu-my-tho-anh-tuan-ben-tre | ben-tre | tien-giang |
| hu-tieu-sa-dec-chu-tu-gan-cho-phu-hung-ben-tre | ben-tre | dong-thap |
| quan-bun-nuoc-leo-cho-tra-vinh-tra-vinh | tra-vinh | soc-trang |
| ca-phe-song-tien-ben-ninh-kieu-vinh-long-vinh-long | vinh-long | can-tho |
| hu-tieu-ca-phe-cho-cai-be-quan-truoc-cong-cho-cai-be-vinh-long | vinh-long | tien-giang |
| cong-ty-tnhh-mtv-quoc-thao | vinh-long | hcm |
| khu-du-lich-sinh-thai-truong-huy-vinh-long | vinh-long | hcm |
| tour-song-nuoc-cai-be-vinh-long | vinh-long | tien-giang |
| khoai-lang-say-binh-tan | vinh-long | hcm |

---

## 5. HISTORICAL FACT-CHECK (V4)

**Scope:** 188 history entities + 35 person entities.  
**Method:** one web search per `history`/`person` entity in this pass, plus source-tier analysis and claim extraction.

Coverage:
- Person web searches: 35/35
- History web searches: 188/188
- Confirmed historical/geographic P0 errors: 3

Important nuance: `Chùa Vàm Ray` current Wikipedia text says tỉnh Vĩnh Long because Trà Vinh cũ is inside Vĩnh Long mới. The legacy area `tra-vinh` should not be auto-corrected just because a 2026 source says Vĩnh Long.

---

## 6. CULINARY & PRODUCT VERIFICATION (V5)

**Scope:** 339 dish/product/drink entities.  
**Method:** origin/OCOP claim extraction, web search sample, source-tier scan.

Confirmed culinary origin errors:
| Entity ID | Current claim | Correct sourced fact | Source |
| --- | --- | --- | --- |
| hu-tieu-my-tho | DB gán origin='Vĩnh Long' và area='vinh-long' cho Hủ tiếu Mỹ Tho. | Hủ tiếu Mỹ Tho là món do người Mỹ Tho chế biến; Mỹ Tho thuộc Tiền Giang cũ, ngoài 3 legacy areas. | [source](https://vi.wikipedia.org/wiki/H%E1%BB%A7_ti%E1%BA%BFu_M%E1%BB%B9_Tho) |
| banh-cong-soc-trang | DB gán origin='Trà Vinh' và area='tra-vinh' cho Bánh cống Sóc Trăng. | Nguồn báo chí mô tả bánh cống là đặc sản/nguyên gốc Sóc Trăng cũ. | [source](https://vnexpress.net/banh-cong-dac-san-cua-nguoi-khmer-o-soc-trang-4523101.html) |

OCOP/product risk:
- Product entities: 218
- Claims containing OCOP: 654
- Product/dish entities without independent source: 307

---

## 7. CONTACT INFO VERIFICATION (V6)

**Scope:** restaurants, cafes, accommodations, facilities, plus any entity with `attributes.phone`.  
**Method:** phone format validation and source-status check. Live phone calling/Google Maps verification was not performed.

Findings:
- Phone values found: 142
- Invalid phone formats: 0
- Contact-type entities with only format-level phone validation: 115

Because no live Maps/API verification was performed, all phone numbers remain “format-valid only.”

---

## 8. SOURCE ATTRIBUTION AUDIT (V7)

**Scope:** 1745 entities.  
**Method:** parse every `source` object, classify domain tier, detect self-references/no-URL/LLM labels.

| Source domain/status | Count |
| --- | --- |
| (no-url-source-object) | 903 |
| vinhlong360.vn | 449 |
| vinhlong.gov.vn | 144 |
| mytour.vn | 53 |
| vinhlongtourist.vn | 48 |
| baovinhlong.com.vn | 29 |
| blog.vexere.com | 10 |
| viettopreview.vn | 10 |
| langthangvinhlong.vn | 9 |
| nucuoimekong.com | 7 |
| dulichbinhminh.com | 6 |
| nongthon.vietnamtourism.gov.vn | 6 |
| nhandan.vn | 6 |
| maps.app.goo.gl | 5 |
| dantoc.vietnamtourism.gov.vn | 5 |
| baodongkhoi.vn | 5 |
| traveloka.com | 5 |
| mia.vn | 5 |
| bluepillow.co.uk | 4 |
| bentretourism.vn | 3 |

Summary:
- Entities with Tier 1/2 source URL: 221/1745 (12.7%)
- Entities with no independent URL: 1350/1745 (77.4%)
- Explicit LLM/agent source: 171/1745

---

## 9. RELATIONSHIP TRUTH CHECK (V8)

**Scope:** 12441 relationships.  
**Method:** relationship type counts, duplicate triple scan, fanout check, near-distance check.

| Relationship type | Count |
| --- | --- |
| near | 5065 |
| related_to | 4305 |
| located_in | 2214 |
| associated_with | 670 |
| produced_in | 187 |

Findings:
- `near` + `related_to`: 9370/12441 (75.3%) low-specificity relationships.
- Duplicate relationship triples: 0
- `near` relationships >50km: 0
- Fanout >120 direct relationships: 4 (p-long-chau:251, p-phu-khuong:147, lang-banh-trang-tra-on:128, p-tra-vinh:121)

---

## 10. ITINERARY VERIFICATION (V9)

**Scope:** 33 top-level itineraries in `web/data.json`.  
**Method:** stop reference existence, relationship coverage via structural validators, and area-mismatch review.

Structural validators report itinerary stop references are present, but factual route timing/transport claims still need source-level verification. This audit did not validate real travel times, road conditions, boat schedules, or seasonal closures.

---

## 11. ATTRIBUTE VERIFICATION (V10)

**Scope:** every `attributes` object.  
**Method:** scan high-risk attributes: address, origin, OCOP, price, hours, phone, coordinates approximation flags.

High-risk attribute issues:
- `origin` contradicted: `hu-tieu-my-tho`, `banh-cong-soc-trang`
- `address` contradicted/out-of-scope: `chua-sa-lon-chua-chen-kieu`
- Approximate coordinates: 1156
- Price/hour attributes: format scanned only, not live verified.

---

## 12. ENRICHMENT PIPELINE RISK ASSESSMENT

### 12.1 Current pipeline analysis
The current pipeline can produce public-facing prose from sparse metadata (`name + type + area`) and later import it into the database. Prompt-only guardrails say “do not invent facts,” but there is no enforced source binding, claim extraction, or mandatory human review before publish.

### 12.2 Guardrail gaps
- LLM output is not tagged per claim.
- `source` presence is treated too much like verification, even when URL is absent.
- No mandatory review queue for history/person/attraction.
- No source-to-claim alignment test.
- No external contradiction scanner before import.
- No provenance field distinguishing crawled/human/LLM/curated/seed.
- No confidence penalty for self-reference/no-url source.
- AI image generation has no real-appearance validation.
- Coordinates can be centroid/approximate while entity appears “verified.”
- Restaurant/contact fields are format-checked but not live-checked.

### 12.3 Recommendations
| # | Recommendation | Impact | Effort |
| --- | --- | --- | --- |
| R1 | Add `content_origin`: human/crawled/llm/seed/curated per field | Trust transparency | S |
| R2 | Require source URL for every non-generic factual claim | Prevents sourceless claims | M |
| R3 | Add claim extractor before import; block year/number/name claims without source | Stops hallucinated facts | M |
| R4 | Move LLM enrich output to `pending_review` by default | Prevents direct publish | M |
| R5 | Lower factual generation temperature to <=0.2 | Reduces fabrication | S |
| R6 | Restrict LLM to rewrite/summary expansion only; forbid new facts | Tighter scope | S |
| R7 | Persist source snippets/hash per claim | Audit reproducibility | M |
| R8 | Add external contradiction checks for area/origin before export | Catches out-of-province items | M |
| R9 | Separate legacy area from current merged province naming | Avoids false corrections | S |
| R10 | Add Maps/OSM live check queue for contact and coordinates | Operational accuracy | L |
| R11 | Apply trust score in UI/admin filters | Prevents low-trust content surfacing | M |
| R12 | Make backup mandatory in every mutating ETL script | Prevents data-loss regressions | S |

---

## 13. TRUST SCORE DISTRIBUTION

Overall average: 63.7/100.

| Bucket | Entities | % |
| --- | --- | --- |
| 0-19 | 1 | 0.1% |
| 20-39 | 91 | 5.2% |
| 40-59 | 642 | 36.8% |
| 60-79 | 787 | 45.1% |
| 80-100 | 224 | 12.8% |

High trust (>=90): 88 (5.0%)  
Untrusted (<50): 225 (12.9%)

### Per-type trust score
| Type | Avg trust | Min | Max | Lowest-trust entities |
| --- | --- | --- | --- | --- |
| accommodation | 70.9 | 30 | 93 | con-chim-homestay, malis-hotel-tra-vinh, muoi-quynh-homestay, vinh-sang-resort, khu-du-lich-bien-ba-dong |
| attraction | 67.3 | 22 | 96 | lang-nghe-tau-hu-ky-my-hoa, khu-du-lich-lan-vuong, khu-can-cu-tinh-uy-tra-vinh, nha-thuc-pham-sach-khoai-lang-tim-binh-tan-vinh-long, khu-du-lich-lang-be |
| cafe | 58.5 | 42 | 78 | ca-phe-song-tien-ben-ninh-kieu-vinh-long-vinh-long, sinh-to-ha-tien-duong-pham-thai-buong-vinh-long, 1983-coffee-pizza, 1985-cafe, ca-phe-bo-song-tra-vinh |
| craft_village | 57.5 | 26 | 96 | vung-khoai-lang-binh-tan, cong-ty-tnhh-tra-vinh-farm-sokfarm, hop-tac-xa-buoi-nam-roi-my-hoa, lang-mai-vang-phuoc-dinh, lang-nghe-bun-suong |
| dish | 60.2 | 20 | 88 | banh-cong-soc-trang, hu-tieu-my-tho, bun-mam-mien-tay-vinh-long, tom-rang-muoi-ot, banh-canh-bot-xat |
| drink | 44.0 | 44 | 44 | dua-sap-sinh-to |
| event | 62.7 | 42 | 96 | giai-ban-marathon-vinh-long-mo-rong-hanh-trinh-trai-tim-mekong-vinh-long, hoi-cho-xuc-tien-thuong-mai-san-pham-cong-nghiep-nong-thon-va-ocop-vinh-long-gan-voi-ok-om-bok-vinh-long, lien-hoan-don-ca-tai-tu-nam-bo-tinh-ben-tre-ben-tre, trien-lam-hoi-cho-nong-nghiep-cong-nghe-cao-ben-tre-ben-tre, cho-hoa-tet |
| experience | 64.5 | 42 | 96 | cho-noi-cai-be, hai-chom-chom-an-binh, mua-nuoc-noi-dbscl, vuot-song-co-chien, trai-nghiem-cau-ca-cau-tom-song-hau |
| facility | 58.0 | 42 | 76 | ben-pha-tran-phu-can-tho-vinh-long-vinh-long, ben-xe-tra-on-tich-thien-vinh-long, diem-giao-dich-vinaphone-vnpt-cach-mang-thang-8-ben-tre, diem-xe-buyt-phuong-trang-vinh-long-can-tho-tuyen-lien-tinh-vinh-long, ben-xe-duyen-hai-tx-duyen-hai-tra-vinh |
| history | 63.1 | 0 | 96 | chua-sa-lon-chua-chen-kieu, chien-thang-giong-dua-giong-trom, chua-ong-met-botum-vong-sa-som-rong, thanh-that-cao-dai-vinh-long, bao-tang-tong-hop-tinh-tra-vinh |
| itinerary | 44.1 | 24 | 66 | itinerary-tuan-trang-mat-mien-tay-4n3d, backpacker-mien-tay-3ngay-500k, itinerary-cai-mon-tet-ben-tre, ben-tre-1-ngay-con-phuong-tphcm, ben-tre-couple-2day-001 |
| nature | 65.1 | 20 | 100 | khu-bao-ton-lung-binh-hoa-tra-vinh, cu-lao-my-hoa, bien-an-thuy, khu-bao-ton-thien-nhien-dat-ngap-nuoc-vam-ho, bien-thua-duc |
| organization | 64.0 | 64 | 64 | cong-ty-tnhh-du-lich-sinh-thai-bao-duyen |
| person | 72.4 | 49 | 95 | nguyen-van-ton-thach-duong, chau-van-sanh-cong-tu-loi, vien-chau-huynh-tri-ba, nguyen-thi-ut, dong-van-cong |
| place | 76.1 | 45 | 100 | xa-hoa-minh, p-tra-vinh, xa-luc-si-thanh, p-ba-tri, xa-hau-loc |
| product | 59.5 | 25 | 100 | chom-chom-con-tan-quy, so-huyet-tra-vinh, ca-chay-tra-on, ca-dieu-hong-nuoi-be-long-ho, ca-tra-thuong-pham-vinh-long |
| restaurant | 58.7 | 22 | 92 | hu-tieu-sa-dec-chu-tu-gan-cho-phu-hung-ben-tre, banh-mi-sau-hoa-ben-tre, quan-thuan-phuc-vinh-long, hai-san-ngoc-hiep-binh-dai-ben-tre, mi-cay-vinh-long |

---

## 14. COMPLETENESS AUDIT (secondary)

### 14.1 Entity statistics
| Type | Count | % summary | % description | % coords | % images | % source object | % independent source |
| --- | --- | --- | --- | --- | --- | --- | --- |
| product | 218 | 100.0% | 100.0% | 100.0% | 0.0% | 100.0% | 8.3% |
| attraction | 202 | 100.0% | 100.0% | 100.0% | 0.0% | 100.0% | 41.1% |
| restaurant | 191 | 100.0% | 100.0% | 100.0% | 0.0% | 100.0% | 5.8% |
| history | 188 | 100.0% | 100.0% | 100.0% | 0.0% | 100.0% | 21.3% |
| accommodation | 164 | 100.0% | 100.0% | 100.0% | 0.0% | 100.0% | 56.1% |
| nature | 125 | 100.0% | 100.0% | 100.0% | 0.0% | 100.0% | 15.2% |
| place | 125 | 100.0% | 100.0% | 100.0% | 0.0% | 100.0% | 20.0% |
| dish | 120 | 100.0% | 100.0% | 100.0% | 0.0% | 100.0% | 11.7% |
| experience | 92 | 100.0% | 100.0% | 100.0% | 0.0% | 100.0% | 43.5% |
| craft_village | 86 | 100.0% | 100.0% | 100.0% | 0.0% | 100.0% | 18.6% |
| event | 67 | 100.0% | 100.0% | 100.0% | 0.0% | 100.0% | 22.4% |
| facility | 58 | 100.0% | 100.0% | 98.3% | 0.0% | 100.0% | 0.0% |
| cafe | 56 | 100.0% | 100.0% | 100.0% | 0.0% | 100.0% | 0.0% |
| person | 35 | 100.0% | 100.0% | 100.0% | 0.0% | 100.0% | 60.0% |
| itinerary | 16 | 100.0% | 100.0% | 68.8% | 0.0% | 100.0% | 0.0% |
| drink | 1 | 100.0% | 100.0% | 100.0% | 0.0% | 100.0% | 0.0% |
| organization | 1 | 100.0% | 100.0% | 100.0% | 0.0% | 100.0% | 100.0% |

### 14.2 Coverage map
| Area | Total | attraction | dish | restaurant | product | event | history | nature | person |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Vĩnh Long | 709 | 86 | 52 | 67 | 75 | 30 | 66 | 28 | 23 |
| Bến Tre | 549 | 61 | 41 | 60 | 82 | 15 | 63 | 59 | 6 |
| Trà Vinh | 481 | 55 | 27 | 64 | 61 | 22 | 59 | 38 | 6 |
| None | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

### 14.3 Missing entity candidates
This pass did not add missing entities because fabricating new POIs is explicitly disallowed. Candidate generation should be a separate source-first crawl from Tier 1/2 directories.

---

## 15. FIX PRIORITY — FACTUAL ERRORS FIRST

### P0 — Confirmed factual errors (fix IMMEDIATELY)
| # | Entity ID | Error | Correct value | Source | Fix method |
| --- | --- | --- | --- | --- | --- |
| 1 | hu-tieu-my-tho | DB gán origin='Vĩnh Long' và area='vinh-long' cho Hủ tiếu Mỹ Tho. | Hủ tiếu Mỹ Tho là món do người Mỹ Tho chế biến; Mỹ Tho thuộc Tiền Giang cũ, ngoài 3 legacy areas. | [source](https://vi.wikipedia.org/wiki/H%E1%BB%A7_ti%E1%BA%BFu_M%E1%BB%B9_Tho) | Quarantine/remove from Vĩnh Long-specific dish catalog, or relabel as out-of-scope regional reference with origin='Mỹ Tho, Tiền Giang'. |
| 2 | banh-cong-soc-trang | DB gán origin='Trà Vinh' và area='tra-vinh' cho Bánh cống Sóc Trăng. | Nguồn báo chí mô tả bánh cống là đặc sản/nguyên gốc Sóc Trăng cũ. | [source](https://vnexpress.net/banh-cong-dac-san-cua-nguoi-khmer-o-soc-trang-4523101.html) | Quarantine/remove from Trà Vinh-specific dish catalog unless there is a local Trà Vinh serving-place entity with separate evidence. |
| 3 | chua-sa-lon-chua-chen-kieu | DB đặt Chùa Sà Lôn/Chùa Chén Kiểu ở Phường Trà Vinh, Trà Vinh và architectural_style='Chùa Việt'. | Chùa Sà Lôn/Chùa Chén Kiểu là chùa Khmer Nam tông ở khu vực Sóc Trăng cũ, nay thuộc Cần Thơ sau sáp nhập; không thuộc legacy Trà Vinh. | [source](https://vi.wikipedia.org/wiki/Ch%C3%B9a_S%C3%A0_L%C3%B4n) | Quarantine/remove from Trà Vinh scope. Do not rewrite to another unsupported province without a scoped data model. |
| 4 | chien-thang-giong-dua-giong-trom | DB đặt Di tích lịch sử Chiến thắng Giồng Dứa ở Bến Tre và phần mô tả lại nói về mộ hợp chất Chợ Lách. | Nguồn báo chí địa phương mô tả Di tích lịch sử Chiến thắng Giồng Dứa là di tích cấp quốc gia của tỉnh Tiền Giang; nội dung mộ hợp chất Chợ Lách không khớp với tên entity. | [source](https://tintucmientay.baoangiang.com.vn/tien-giang-chien-thang-giong-dua-lam-chan-dong-du-luan-trong-va-ngoai-nuoc-a361124.html) | Quarantine/remove khỏi Bến Tre scope. Không tự viết lại mô tả cho Tiền Giang nếu catalog chỉ phục vụ 3 legacy areas. |
| 5 | chua-ong-met-botum-vong-sa-som-rong | DB gộp tên Chùa Ông Mẹt với 'Botum Vong Sa Som Rong' và đặt architectural_style='Chùa Hoa'. | Chùa Ông Mẹt ở Trà Vinh là chùa Khmer Nam tông, còn Bô Tum Vông Sa Som Rông/Som Rong là một chùa Khmer khác ở Sóc Trăng/Cần Thơ mới. | [source](https://vovworld.vn/vi-VN/viet-nam-dat-nuoc-con-nguoi/chua-ong-met-di-tich-cap-quoc-gia-o-tinh-tra-vinh-2004638.vov5) | Quarantine entity để tách lại thành Chùa Ông Mẹt; bỏ cụm Som Rong và sửa phong cách kiến trúc chỉ sau khi có nguồn claim-level. |
| 6 | khu-bao-ton-lung-binh-hoa-tra-vinh | DB tạo entity 'Khu bảo tồn thiên nhiên Lung Bình Hòa' ở Trà Vinh nhưng summary/description lại nói về Khu bảo tồn thiên nhiên Lung Ngọc Hoàng ở Hậu Giang. | Khu bảo tồn thiên nhiên Lung Ngọc Hoàng là một thực thể khác, nằm ở vùng Hậu Giang/Cần Thơ mới; nội dung hiện tại không chứng minh sự tồn tại của 'Lung Bình Hòa' tại Trà Vinh. | [source](https://vi.wikipedia.org/wiki/Khu_b%E1%BA%A3o_t%E1%BB%93n_thi%C3%AAn_nhi%C3%AAn_Lung_Ng%E1%BB%8Dc_Ho%C3%A0ng) | Quarantine/remove entity. Không sửa tên hoặc địa chỉ nếu chưa có nguồn độc lập xác nhận 'Lung Bình Hòa' ở Trà Vinh. |

### P1 — Suspected hallucinations (review within 1 week)
| Entity ID | Score | Reason | Action |
| --- | --- | --- | --- |
| hu-tieu-sa-dec-chu-tu-gan-cho-phu-hung-ben-tre | 22 | source_without_url;large_coordinate_cluster_80;approximate_coordinates;missing_images;unverified_claims_1;mentions_outside_area:dong-thap;ma | Human fact-check + source binding |
| lang-nghe-tau-hu-ky-my-hoa | 22 | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_255;approximate_coordinates;missing_images;unverified_claims_8;mentions_outside | Human fact-check + source binding |
| itinerary-tuan-trang-mat-mien-tay-4n3d | 24 | source_without_url;llm_fingerprint;missing_coordinates;missing_images;unverified_claims_5;manual_p1_suspect | Human fact-check + source binding |
| chom-chom-con-tan-quy | 25 | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_53;approximate_coordinates;missing_images;unverified_claims_3 | Human fact-check + source binding |
| thanh-that-cao-dai-vinh-long | 25 | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_89;approximate_coordinates;missing_images;unverified_claims_3 | Human fact-check + source binding |
| vung-khoai-lang-binh-tan | 26 | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_89;approximate_coordinates;missing_images;mentions_outside_area:hcm;web_match | Human fact-check + source binding |
| backpacker-mien-tay-3ngay-500k | 28 | source_without_url;missing_coordinates;missing_images;unverified_claims_3;mentions_outside_area:dong-thap,hcm;manual_p1_suspect | Human fact-check + source binding |
| khu-du-lich-lan-vuong | 28 | explicit_llm_source;llm_fingerprint;coordinate_cluster_25;approximate_coordinates;missing_images;unverified_claims_2;mentions_outside_area:h | Human fact-check + source binding |
| so-huyet-tra-vinh | 28 | explicit_llm_source;llm_fingerprint;coordinate_cluster_20;approximate_coordinates;missing_images;unverified_claims_1;mentions_outside_area:h | Human fact-check + source binding |
| banh-mi-sau-hoa-ben-tre | 30 | source_without_url;large_coordinate_cluster_80;approximate_coordinates;missing_images;unverified_claims_4;manual_p1_suspect | Human fact-check + source binding |
| bao-tang-tong-hop-tinh-tra-vinh | 30 | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_53;approximate_coordinates;missing_images;unverified_claims_2;web_match | Human fact-check + source binding |
| bun-mam-mien-tay-vinh-long | 30 | source_without_url;llm_fingerprint;large_coordinate_cluster_255;approximate_coordinates;missing_images;unverified_claims_5;mentions_outside_ | Human fact-check + source binding |
| ca-chay-tra-on | 30 | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_255;approximate_coordinates;missing_images;unverified_claims_3;web_match | Human fact-check + source binding |
| ca-dieu-hong-nuoi-be-long-ho | 30 | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_255;approximate_coordinates;missing_images;unverified_claims_3;web_match | Human fact-check + source binding |
| ca-tra-thuong-pham-vinh-long | 30 | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_89;approximate_coordinates;missing_images;unverified_claims_1;web_match | Human fact-check + source binding |
| chua-ang-angkorajaborey | 30 | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_53;approximate_coordinates;missing_images;unverified_claims_4;web_match | Human fact-check + source binding |
| chua-lo-gach | 30 | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_53;approximate_coordinates;missing_images;unverified_claims_7;web_match | Human fact-check + source binding |
| chua-phuoc-son | 30 | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_255;approximate_coordinates;missing_images;unverified_claims_3;web_match | Human fact-check + source binding |
| chua-samrong-ek | 30 | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_74;approximate_coordinates;missing_images;unverified_claims_3;web_match | Human fact-check + source binding |
| chua-soc-tro | 30 | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_53;approximate_coordinates;missing_images;unverified_claims_3;web_match | Human fact-check + source binding |
| con-chim-homestay | 30 | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_53;approximate_coordinates;missing_images;unverified_claims_4;web_match | Human fact-check + source binding |
| cong-ty-tnhh-tra-vinh-farm-sokfarm | 30 | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_53;approximate_coordinates;missing_images;unverified_claims_7;web_match | Human fact-check + source binding |
| cu-lao-my-hoa | 30 | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_89;approximate_coordinates;missing_images;unverified_claims_5;web_match | Human fact-check + source binding |
| hop-tac-xa-buoi-nam-roi-my-hoa | 30 | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_89;approximate_coordinates;missing_images;unverified_claims_8;web_match | Human fact-check + source binding |
| khu-can-cu-tinh-uy-tra-vinh | 30 | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_53;approximate_coordinates;missing_images;unverified_claims_2;web_match | Human fact-check + source binding |
| lang-mai-vang-phuoc-dinh | 30 | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_89;approximate_coordinates;missing_images;unverified_claims_8;web_match | Human fact-check + source binding |
| lang-nghe-bun-suong | 30 | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_53;approximate_coordinates;missing_images;unverified_claims_3;web_match | Human fact-check + source binding |
| lang-nghe-tac-tuong-go-long-duc | 30 | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_74;approximate_coordinates;missing_images;unverified_claims_2;web_match | Human fact-check + source binding |
| lang-nghe-tom-kho-vinh-kim | 30 | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_53;approximate_coordinates;missing_images;unverified_claims_5;web_match | Human fact-check + source binding |
| malis-hotel-tra-vinh | 30 | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_74;approximate_coordinates;missing_images;unverified_claims_1;web_match | Human fact-check + source binding |
| mang-cut-binh-hoa-phuoc | 30 | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_255;approximate_coordinates;missing_images;unverified_claims_1;web_match | Human fact-check + source binding |
| mieu-ba-chua-xu-tra-vinh | 30 | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_53;approximate_coordinates;missing_images;unverified_claims_2;web_match | Human fact-check + source binding |
| muoi-quynh-homestay | 30 | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_53;approximate_coordinates;missing_images;unverified_claims_2;web_match | Human fact-check + source binding |
| nha-thuc-pham-sach-khoai-lang-tim-binh-tan-vinh-long | 30 | source_without_url;llm_fingerprint;large_coordinate_cluster_255;approximate_coordinates;missing_images;unverified_claims_3;mentions_outside_ | Human fact-check + source binding |
| quan-thuan-phuc-vinh-long | 30 | source_without_url;large_coordinate_cluster_255;approximate_coordinates;missing_images;unverified_claims_3;manual_p1_suspect | Human fact-check + source binding |
| quyt-duong-cau-ke | 30 | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_74;approximate_coordinates;missing_images;unverified_claims_4;web_match | Human fact-check + source binding |
| quyt-duong-long-tri | 30 | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_53;approximate_coordinates;missing_images;unverified_claims_1;web_match | Human fact-check + source binding |
| tep-kho-my-long | 30 | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_53;approximate_coordinates;missing_images;unverified_claims_3;web_match | Human fact-check + source binding |
| that-phu-mieu-chua-ong | 30 | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_255;approximate_coordinates;missing_images;unverified_claims_4;web_match | Human fact-check + source binding |
| vinh-sang-resort | 30 | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_255;approximate_coordinates;missing_images;unverified_claims_3;web_match | Human fact-check + source binding |

Round 2 P1 suspects from manual `MISMATCH` review:

| Entity ID | Confidence | Why suspect | Evidence/source | Action |
| --- | --- | --- | --- | --- |
| cha-gio-chay | 65% | Search chỉ hỗ trợ món chả giò chay nói chung; chưa có nguồn đáng tin cho claim origin/where/price riêng tại Trà Vinh. | [source](https://www.huongnghiepaau.com/cha-gio-chay) | Giữ generic hoặc gỡ claim địa phương/giá cho đến khi có nguồn Trà Vinh. |
| dinh-cai-von | 70% | Nguồn chính thống thấy Đình Thần Mỹ Thuận tại Bình Minh; chưa xác nhận tên chính thức 'Đình Cái Vồn' và các claim thương cảng/kiến trúc Hoa kiều. | [source](https://svhttdl.vinhlong.gov.vn/xem-chi-tiet-tin-tuc/id/228793) | Human verify official name; gỡ claim không nguồn nếu không chứng minh được. |
| rau-thom-ocop-hop-tac-xa-phuoc-hau | 80% | Nguồn Vĩnh Long xác nhận HTX Phước Hậu nhưng số liệu nguồn là 35 xã viên, 15 ha, trên 780 tấn/năm; DB ghi 15,5 ha và 850 tấn/năm. | [source](https://portal.vinhlong.gov.vn/portal/wpxttm/xttm/page/xemtin.cpx?item=60b9ce759332504c4746c3b7) | Review/update numeric claims; không coi là P0 vì số liệu có thể theo năm. |
| shop-luu-niem-ben-ninh-kieu-gian-hang-vinh-long-vinh-long | 85% | Tên entity chứa Bến Ninh Kiều (biểu tượng Cần Thơ) nhưng summary/address lại nói Cù lao An Bình, Vĩnh Long; chưa tìm thấy nguồn cho shop này. | [source](https://canthotourism.vn/vi/benninhkieu) | Quarantine P1 name/address conflict; cần human/Maps check tồn tại thật. |
| so-diep-binh-dai | 70% | Không tìm được nguồn Tier 1/2 xác nhận 'Sò điệp Bình Đại' là đặc sản; kết quả chủ yếu là generic/imported scallop hoặc social posts. | [source](https://vi.wikipedia.org/wiki/S%C3%B2_%C4%91i%E1%BB%87p) | Giữ suspect; cần nguồn thủy sản/địa phương trước khi publish claim đặc sản. |
| backpacker-mien-tay-3ngay-500k | 85% | Itinerary chứa nhiều giá, tuyến xe và mốc giờ không có source; top result ngoài An Giang chỉ cho thấy search không xác minh được itinerary này. | [source](https://tourmientay.vn/blogs/tour-ve-mien-tay-4-ngay-3-dem-2-ngay-dau-tai-an-giang-44) | Giữ UNTRUSTED; cần review route/cost từng chặng trước khi publish. |
| banh-mi-sau-hoa-ben-tre | 75% | Không tìm được nguồn độc lập cho quán Bánh mì Sáu Hoà Bến Tre; top result là Bánh mì Huynh Hoa TP.HCM, không liên quan. | [source](https://banhmihuynhhoa.vn/) | Human/Maps check tồn tại thật; gỡ claim 20+ năm, giờ mở cửa và giá nếu không có nguồn. |
| bun-nuoc-leo-cho-ba-tri-ben-tre | 75% | Không có nguồn độc lập rõ cho quán bún nước lèo chợ Ba Tri; top result bị kéo sang bún nước lèo Sóc Trăng. | [source](https://cl.pinterest.com/pin/bn-nc-lo-mt-c-sn-quen-thuc-ca-cc-tnh-min-ty-nhng-vn-b-nhiu-ngi-lm-tng-l-bn-mm--886294401661397928/) | Human/Maps check; không publish giờ, giá, công suất/ngày nếu chưa xác minh. |
| chua-khai-tuong | 85% | Top Tier 1 cho 'Chùa Khải Tường' là cổ tự Gia Định/TP.HCM; chưa có nguồn đáng tin xác nhận một Chùa Khải Tường nổi tiếng/di tích ở Ba Tri, Bến Tre. | [source](https://vi.wikipedia.org/wiki/Ch%C3%B9a_Kh%E1%BA%A3i_T%C6%B0%E1%BB%9Dng) | Quarantine P1; human verify thực thể cùng tên ở Ba Tri trước khi publish. |
| hu-tieu-sa-dec-chu-tu-gan-cho-phu-hung-ben-tre | 80% | Không tìm được nguồn độc lập cho quán; top result nói về quán hủ tiếu ở Sa Đéc/Đồng Tháp. Tên 'Sa Đéc' có thể chỉ phong cách món, chưa đủ kết luận sai. | [source](https://dulichbinhphuoc.vn/13-quan-hu-tieu-sa-dec-ngon-ma-ban-nen-ghe/) | Human/Maps check tồn tại thật; gỡ claim giá/giờ/năm hoạt động nếu không có nguồn. |
| itinerary-tuan-trang-mat-mien-tay-4n3d | 85% | Itinerary có nhiều giá, resort, chi phí và giờ hoạt động không có source; top result Đà Nẵng là search noise, không xác minh được route. | [source](https://dulichdaiviet.com/tour-noi-dia/tour-du-lich-trang-mat-da-nang-4-ngay-3-dem-tu-ha-noi-tp-hcm.html) | Giữ UNTRUSTED; cần verify từng stop/price hoặc chuyển thành nội dung gợi ý không factual. |
| khoai-lang-binh-tan | 85% | Nguồn ngoài nói khoai lang Bình Tân đạt OCOP 4 sao, trong DB lại có cả `ocop='3 sao'` và `ocop_star=4`. | [source](https://tapchicongthuong.vn/magazine/emagazine--khoai-lang-binh-tan-but-pha-nho-ocop-317499.htm) | Review numeric/OCOP fields; chưa nâng P0 vì cần xác định sản phẩm/năm chứng nhận cụ thể. |
| quan-thuan-phuc-vinh-long | 75% | Không tìm được nguồn độc lập cho Quán Thuận Phúc tại 135 Phạm Thái Bường; top result TikTok Kiên Giang không liên quan. | [source](https://www.tiktok.com/@phuc_vinh_thuan/video/7631125885692792085) | Human/Maps check; không publish giờ/giá/món nổi bật nếu chưa xác minh. |
| tom-kho-binh-dai | 80% | Top result nói tôm khô Cà Mau; chưa có nguồn Tier 1/2 xác nhận Tôm khô Bình Đại/Anfoods OCOP như DB claim. | [source](https://sanphamocop.com.vn/dac-san-tet-cac-vung-mien-ma-ban-nen-biet-2/) | Giữ suspect; cần nguồn OCOP/địa phương trước khi publish claim Anfoods/OCOP 2023. |

### P2 — Missing sources (add within 1 month)
Entities missing independent sources: 1350. Prioritize history/person/attraction/product first.

### P3 — Completeness gaps
Images are missing for all entities. This is secondary to factual correction but should be addressed before public launch.

### P4 — Pipeline improvements
Implement Recommendations R1–R12 before another mass LLM enrichment/import run.

---

## 16. APPENDIXES

### A. Complete Entity Verification Matrix
Full matrix: `docs\data-verification-matrix.csv`. Lowest-trust 60 rows:

| entity_id | type | area | trust_score | verdict | source_status | flags |
| --- | --- | --- | --- | --- | --- | --- |
| chua-sa-lon-chua-chen-kieu | history | tra-vinh | 0 | FABRICATED | NO_URL | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_74;approximate_coordinates;missing_imag |
| banh-cong-soc-trang | dish | tra-vinh | 20 | FABRICATED | NO_URL | source_without_url;approximate_coordinates;missing_images;unverified_claims_1;mentions_outside_area: |
| chien-thang-giong-dua-giong-trom | history | ben-tre | 20 | FABRICATED | NO_URL | source_without_url;missing_images;unverified_claims_2;web_area_mismatch;confirmed_factual_error |
| chua-ong-met-botum-vong-sa-som-rong | history | tra-vinh | 20 | FABRICATED | INDEPENDENT_LOW | source_not_tier1_2;large_coordinate_cluster_74;approximate_coordinates;missing_images;unverified_cla |
| hu-tieu-my-tho | dish | vinh-long | 20 | FABRICATED | NO_URL | source_without_url;large_coordinate_cluster_89;approximate_coordinates;missing_images;unverified_cla |
| khu-bao-ton-lung-binh-hoa-tra-vinh | nature | tra-vinh | 20 | FABRICATED | NO_URL | source_without_url;approximate_coordinates;missing_images;unverified_claims_2;mentions_outside_area: |
| hu-tieu-sa-dec-chu-tu-gan-cho-phu-hung-ben-tre | restaurant | ben-tre | 22 | UNTRUSTED | NO_URL | source_without_url;large_coordinate_cluster_80;approximate_coordinates;missing_images;unverified_cla |
| lang-nghe-tau-hu-ky-my-hoa | attraction | vinh-long | 22 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_255;approximate_coordinates;missing_ima |
| itinerary-tuan-trang-mat-mien-tay-4n3d | itinerary |  | 24 | UNTRUSTED | NO_URL | source_without_url;llm_fingerprint;missing_coordinates;missing_images;unverified_claims_5;manual_p1_ |
| chom-chom-con-tan-quy | product | tra-vinh | 25 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_53;approximate_coordinates;missing_imag |
| thanh-that-cao-dai-vinh-long | history | vinh-long | 25 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_89;approximate_coordinates;missing_imag |
| vung-khoai-lang-binh-tan | craft_village | vinh-long | 26 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_89;approximate_coordinates;missing_imag |
| backpacker-mien-tay-3ngay-500k | itinerary |  | 28 | UNTRUSTED | NO_URL | source_without_url;missing_coordinates;missing_images;unverified_claims_3;mentions_outside_area:dong |
| khu-du-lich-lan-vuong | attraction | ben-tre | 28 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;coordinate_cluster_25;approximate_coordinates;missing_images;unv |
| so-huyet-tra-vinh | product | tra-vinh | 28 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;coordinate_cluster_20;approximate_coordinates;missing_images;unv |
| banh-mi-sau-hoa-ben-tre | restaurant | ben-tre | 30 | UNTRUSTED | NO_URL | source_without_url;large_coordinate_cluster_80;approximate_coordinates;missing_images;unverified_cla |
| bao-tang-tong-hop-tinh-tra-vinh | history | tra-vinh | 30 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_53;approximate_coordinates;missing_imag |
| bun-mam-mien-tay-vinh-long | dish | vinh-long | 30 | UNTRUSTED | NO_URL | source_without_url;llm_fingerprint;large_coordinate_cluster_255;approximate_coordinates;missing_imag |
| ca-chay-tra-on | product | vinh-long | 30 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_255;approximate_coordinates;missing_ima |
| ca-dieu-hong-nuoi-be-long-ho | product | vinh-long | 30 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_255;approximate_coordinates;missing_ima |
| ca-tra-thuong-pham-vinh-long | product | vinh-long | 30 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_89;approximate_coordinates;missing_imag |
| chua-ang-angkorajaborey | history | tra-vinh | 30 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_53;approximate_coordinates;missing_imag |
| chua-lo-gach | history | tra-vinh | 30 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_53;approximate_coordinates;missing_imag |
| chua-phuoc-son | history | vinh-long | 30 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_255;approximate_coordinates;missing_ima |
| chua-samrong-ek | history | tra-vinh | 30 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_74;approximate_coordinates;missing_imag |
| chua-soc-tro | history | tra-vinh | 30 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_53;approximate_coordinates;missing_imag |
| con-chim-homestay | accommodation | tra-vinh | 30 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_53;approximate_coordinates;missing_imag |
| cong-ty-tnhh-tra-vinh-farm-sokfarm | craft_village | tra-vinh | 30 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_53;approximate_coordinates;missing_imag |
| cu-lao-my-hoa | nature | vinh-long | 30 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_89;approximate_coordinates;missing_imag |
| hop-tac-xa-buoi-nam-roi-my-hoa | craft_village | vinh-long | 30 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_89;approximate_coordinates;missing_imag |
| khu-can-cu-tinh-uy-tra-vinh | attraction | tra-vinh | 30 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_53;approximate_coordinates;missing_imag |
| lang-mai-vang-phuoc-dinh | craft_village | vinh-long | 30 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_89;approximate_coordinates;missing_imag |
| lang-nghe-bun-suong | craft_village | tra-vinh | 30 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_53;approximate_coordinates;missing_imag |
| lang-nghe-tac-tuong-go-long-duc | craft_village | tra-vinh | 30 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_74;approximate_coordinates;missing_imag |
| lang-nghe-tom-kho-vinh-kim | craft_village | tra-vinh | 30 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_53;approximate_coordinates;missing_imag |
| malis-hotel-tra-vinh | accommodation | tra-vinh | 30 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_74;approximate_coordinates;missing_imag |
| mang-cut-binh-hoa-phuoc | product | vinh-long | 30 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_255;approximate_coordinates;missing_ima |
| mieu-ba-chua-xu-tra-vinh | history | tra-vinh | 30 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_53;approximate_coordinates;missing_imag |
| muoi-quynh-homestay | accommodation | tra-vinh | 30 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_53;approximate_coordinates;missing_imag |
| nha-thuc-pham-sach-khoai-lang-tim-binh-tan-vinh-long | attraction | vinh-long | 30 | UNTRUSTED | NO_URL | source_without_url;llm_fingerprint;large_coordinate_cluster_255;approximate_coordinates;missing_imag |
| quan-thuan-phuc-vinh-long | restaurant | vinh-long | 30 | UNTRUSTED | NO_URL | source_without_url;large_coordinate_cluster_255;approximate_coordinates;missing_images;unverified_cl |
| quyt-duong-cau-ke | craft_village | tra-vinh | 30 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_74;approximate_coordinates;missing_imag |
| quyt-duong-long-tri | product | tra-vinh | 30 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_53;approximate_coordinates;missing_imag |
| tep-kho-my-long | product | tra-vinh | 30 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_53;approximate_coordinates;missing_imag |
| that-phu-mieu-chua-ong | history | vinh-long | 30 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_255;approximate_coordinates;missing_ima |
| vinh-sang-resort | accommodation | vinh-long | 30 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_255;approximate_coordinates;missing_ima |
| vung-cam-sanh-tra-on | craft_village | vinh-long | 30 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_89;approximate_coordinates;missing_imag |
| xa-lach-xoong-thuan-an | product | vinh-long | 30 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;large_coordinate_cluster_255;approximate_coordinates;missing_ima |
| bien-an-thuy | nature | ben-tre | 31 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;coordinate_cluster_25;approximate_coordinates;missing_images;unv |
| ca-da-tron-nuoi-nuoc-ngot | product | ben-tre | 31 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;coordinate_cluster_11;approximate_coordinates;missing_images;unv |
| chua-xvayton | history | tra-vinh | 31 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;coordinate_cluster_12;approximate_coordinates;missing_images;unv |
| cong-ty-tnhh-che-bien-dua-luong-quoi | craft_village | ben-tre | 31 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;coordinate_cluster_12;approximate_coordinates;missing_images;unv |
| khu-bao-ton-thien-nhien-dat-ngap-nuoc-vam-ho | nature | ben-tre | 31 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;coordinate_cluster_12;approximate_coordinates;missing_images;unv |
| khu-du-lich-lang-be | attraction | ben-tre | 31 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;coordinate_cluster_12;approximate_coordinates;missing_images;unv |
| sa-po-che-cho-lach | product | ben-tre | 31 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;coordinate_cluster_25;approximate_coordinates;missing_images;unv |
| chua-giac-linh | history | tra-vinh | 33 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;coordinate_cluster_12;approximate_coordinates;missing_images;unv |
| khu-luu-niem-nu-anh-hung-nguyen-thi-ut-ut-tich | history | tra-vinh | 33 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;coordinate_cluster_13;approximate_coordinates;missing_images;unv |
| bien-thua-duc | nature | ben-tre | 36 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;coordinate_cluster_12;approximate_coordinates;missing_images;unv |
| bo-da-xanh-ba-tri | product | ben-tre | 36 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;coordinate_cluster_12;approximate_coordinates;missing_images;unv |
| ca-tra | product | ben-tre | 36 | UNTRUSTED | NO_URL | explicit_llm_source;llm_fingerprint;coordinate_cluster_11;approximate_coordinates;missing_images;unv |

### B. All Factual Claims Inventory
Full claim inventory: `docs\data-verification-claims.csv` (5101 extracted claims). Sample:

| entity_id | claim_type | verified | claim_text |
| --- | --- | --- | --- |
| quyt-duong-cau-ke | named_fact | ENTITY_FOUND_NOT_CLAIM_VERIFIED | Quýt đường Cầu Kè Vùng nước ngọt ven sông Hậu ở Cầu Kè cho ra giống quýt đường Long Trị vỏ mỏng, ngọt thanh, mọng nước — đặc sản trái cây của Trà Vinh. |
| quyt-duong-cau-ke | named_fact | ENTITY_FOUND_NOT_CLAIM_VERIFIED | Vùng nước ngọt ven sông Hậu ở Cầu Kè cho ra giống quýt đường Long Trị vỏ mỏng, ngọt thanh, mọng nước — đặc sản trái cây của Trà Vinh. |
| quyt-duong-cau-ke | measurement+named_fact | ENTITY_FOUND_NOT_CLAIM_VERIFIED | Hợp tác xã Thuận Phú ở xã Bình Phú đã khôi phục hơn 100 ha giống quýt này theo chuẩn VietGAP và canh tác hữu cơ. |
| quyt-duong-cau-ke | season/date | ENTITY_FOUND_NOT_CLAIM_VERIFIED | Cây cho trái hai vụ, xuân từ tháng 2 đến tháng 4 và thu từ tháng 8 đến tháng 10. |
| cua-hang-ocop-tra-vinh-trung-tam-xuc-tien-thuong-mai-tinh-tra-vinh | measurement+named_fact+ocop | ENTITY_FOUND_NOT_CLAIM_VERIFIED | Cửa hàng OCOP Trà Vinh (Trung tâm Xúc tiến Thương mại tỉnh) Điểm trưng bày và bán lẻ các sản phẩm OCOP đạt chuẩn 3–5 sao của tỉnh Trà Vinh, đặt tại Trung tâm Xúc tiến Thương mại tỉ |
| cua-hang-ocop-tra-vinh-trung-tam-xuc-tien-thuong-mai-tinh-tra-vinh | measurement+named_fact+ocop | ENTITY_FOUND_NOT_CLAIM_VERIFIED | Điểm trưng bày và bán lẻ các sản phẩm OCOP đạt chuẩn 3–5 sao của tỉnh Trà Vinh, đặt tại Trung tâm Xúc tiến Thương mại tỉnh trên đường Lê Lợi. |
| cua-hang-ocop-tra-vinh-trung-tam-xuc-tien-thuong-mai-tinh-tra-vinh | named_fact+ocop | ENTITY_FOUND_NOT_CLAIM_VERIFIED | {"shop_type": "cửa hàng OCOP", "address": "Số 10 Lê Lợi, Phường 1, TP. |
| cua-hang-ocop-tra-vinh-trung-tam-xuc-tien-thuong-mai-tinh-tra-vinh | measurement+hours+named_fact+ocop | ENTITY_FOUND_NOT_CLAIM_VERIFIED | Trà Vinh", "hours": "07:30–17:00 (thứ Hai - thứ Sáu)", "what_to_buy": "Sản phẩm OCOP 3-4 sao: trà mãng cầu, tôm khô, mắm cá linh, gạo Huyết Rồng, muối hạt Duyên Hải, bánh tráng phơ |
| cua-hang-dac-san-mien-tay-tra-vinh-tra-vinh | named_fact | ENTITY_FOUND_NOT_CLAIM_VERIFIED | {"shop_type": "cửa hàng đặc sản", "address": "Đường Nguyễn Đáng, Phường 3, TP. |
| cua-hang-dac-san-mien-tay-tra-vinh-tra-vinh | measurement+hours | ENTITY_FOUND_NOT_CLAIM_VERIFIED | Trà Vinh", "hours": "07:00–20:00 hàng ngày", "what_to_buy": "Mật ong rừng U Minh, rượu nếp than, muối tôm, bánh phồng sữa, dừa sáp Cầu Kè (khô và tươi đóng gói), kẹo dừa", "price_r |
| cho-dem-tra-vinh-pho-di-bo-hung-vuong-tra-vinh | named_fact | ENTITY_FOUND_NOT_CLAIM_VERIFIED | Khu vực quy tụ các gian hàng ẩm thực đường phố, quà lưu niệm văn hóa Khmer, bánh dân gian và đồ thủ công mỹ nghệ — không gian sôi động để khám phá đời sống về đêm của thành phố. |
| cho-dem-tra-vinh-pho-di-bo-hung-vuong-tra-vinh | measurement+hours+named_fact | ENTITY_FOUND_NOT_CLAIM_VERIFIED | Trà Vinh", "hours": "18:00–23:00 (thứ Sáu, thứ Bảy, Chủ nhật)", "what_to_buy": "Quà lưu niệm văn hóa Khmer, bánh dân gian, đồ thủ công mỹ nghệ, đặc sản ăn liền, tranh ảnh Trà Vinh, |
| bao-tang-ben-tre | measurement | ENTITY_FOUND_NOT_CLAIM_VERIFIED | Bảo tàng Bến Tre Tọa lạc trên khuôn viên 20.000m² từng là dinh Tỉnh trưởng thời Pháp thuộc, Bảo tàng Bến Tre lưu giữ hơn 15.000 hiện vật kể chuyện vùng đất dừa qua từng thời kỳ lịc |
| bao-tang-ben-tre | measurement | ENTITY_FOUND_NOT_CLAIM_VERIFIED | Tọa lạc trên khuôn viên 20.000m² từng là dinh Tỉnh trưởng thời Pháp thuộc, Bảo tàng Bến Tre lưu giữ hơn 15.000 hiện vật kể chuyện vùng đất dừa qua từng thời kỳ lịch sử. |
| bao-tang-ben-tre | named_fact | ENTITY_FOUND_NOT_CLAIM_VERIFIED | Bước vào đây là bước vào ký ức của xứ cù lao — từ những công cụ lao động thô mộc của người nông dân miệt vườn đến hiện vật kháng chiến hào hùng của 'Đội quân tóc dài' Bến Tre. |
| bao-tang-ben-tre | named_fact | ENTITY_FOUND_NOT_CLAIM_VERIFIED | Không gian cây xanh thoáng mát bao quanh giúp chuyến tham quan trở nên thư thái. |
| bao-tang-ben-tre | named_fact | ENTITY_FOUND_NOT_CLAIM_VERIFIED | Ghé buổi sáng để có trọn 2 tiếng khám phá yên tĩnh trước khi nắng lên. |
| bao-tang-ben-tre | measurement+hours | ENTITY_FOUND_NOT_CLAIM_VERIFIED | {"address": "Số 146 đường Hùng Vương, phường An Hội, Thành phố Bến Tre, tỉnh Bến Tre", "hours": "7:30–11:30 và 13:30–16:30, Thứ 2 - Thứ 6", "fee": "50.000đ người lớn, 20.000đ trẻ e |
| bao-tang-ben-tre | measurement | ENTITY_FOUND_NOT_CLAIM_VERIFIED | Trẻ em cao trên 1,2m: 20.000 VNĐ |
| bao-tang-ben-tre | measurement+hours | ENTITY_FOUND_NOT_CLAIM_VERIFIED | Trẻ em cao dưới 1,2m: miễn phí", "best_time": "Buổi sáng sớm (7:00 – 10:00) để tránh nắng |
| bao-tang-ben-tre | year+measurement+season/date+named_fact | ENTITY_FOUND_NOT_CLAIM_VERIFIED | tránh mùa mưa tháng 9-11 khi khu ngoài trời bị ảnh hưởng", "key_facts": ["Thành lập năm 1981, diện tích khuôn viên khoảng 20.000m², tọa lạc trên nền dinh Tỉnh trưởng cũ thời Pháp t |
| bao-tang-ben-tre | phone+named_fact | ENTITY_FOUND_NOT_CLAIM_VERIFIED | tổ chức giao lưu đờn ca tài tử tại Nhà Dừa"], "phone": "02753822735", "booking_note": "Không cần đặt trước |
| bao-tang-ben-tre | hours+named_fact | ENTITY_FOUND_NOT_CLAIM_VERIFIED | mở cửa tất cả các ngày trong tuần kể cả cuối tuần", "season_note": "Mùa khô, ít mưa, đi lại dễ, tham quan trong nhà thoải mái không lo ngập úng", "peak_event": "Các triển lãm chuyê |
| nha-tho-chanh-toa-tra-vinh-tra-vinh | named_fact | ENTITY_FOUND_NOT_CLAIM_VERIFIED | Nhà thờ Chánh tòa Trà Vinh (Nhà thờ Mẹ Vô Nhiễm) Tôn giáo: Công giáo (Giáo phận Vĩnh Long). |
| nha-tho-chanh-toa-tra-vinh-tra-vinh | year | ENTITY_FOUND_NOT_CLAIM_VERIFIED | Thành lập: 1885. |
| nha-tho-chanh-toa-tra-vinh-tra-vinh | measurement+named_fact | ENTITY_FOUND_NOT_CLAIM_VERIFIED | Kiến trúc Gothic thuộc địa Pháp, tháp chuông đôi cao 30m, cửa sổ kính màu nhập từ Pháp, vòm cuốn nhọn, mặt tiền đá granit xám. |
| nha-tho-chanh-toa-tra-vinh-tra-vinh | named_fact | ENTITY_FOUND_NOT_CLAIM_VERIFIED | Tôn giáo: Công giáo (Giáo phận Vĩnh Long). |
| nha-tho-chanh-toa-tra-vinh-tra-vinh | year | ENTITY_FOUND_NOT_CLAIM_VERIFIED | Thành lập: 1885. |
| nha-tho-chanh-toa-tra-vinh-tra-vinh | measurement+named_fact | ENTITY_FOUND_NOT_CLAIM_VERIFIED | Kiến trúc Gothic thuộc địa Pháp, tháp chuông đôi cao 30m, cửa sổ kính màu nhập từ Pháp, vòm cuốn nhọn, mặt tiền đá granit xám. |
| nha-tho-chanh-toa-tra-vinh-tra-vinh | year+measurement+hours+named_fact | ENTITY_FOUND_NOT_CLAIM_VERIFIED | {"stream": "religious", "category": "religious", "religion": "Công giáo (Giáo phận Vĩnh Long)", "founding_year": "1885", "architecture_style": "Kiến trúc Gothic thuộc địa Pháp, thá |
| nha-tho-chanh-toa-tra-vinh-tra-vinh | hours | ENTITY_FOUND_NOT_CLAIM_VERIFIED | lễ sáng 05:30 và 17:30", "annual_festival": "Lễ Giáng Sinh (24–25/12), Lễ Đức Mẹ Vô Nhiễm (8/12), Phục Sinh", "coords_approximate": true, "schema_type": "TouristAttraction", "addre |
| chua-vam-ray | named_fact | ENTITY_FOUND_NOT_CLAIM_VERIFIED | Chùa Vàm Ray (Wath Vam Ray) là ngôi chùa Khmer lớn nhất Trà Vinh và cả ĐBSCL, tọa lạc tại xã Hàm Tân, huyện Trà Cú. |
| chua-vam-ray | measurement | ENTITY_FOUND_NOT_CLAIM_VERIFIED | Kiến trúc Khmer nguy nga, chánh điện rộng 50m × 22m, trang trí nổi bật với rắn thần Naga, Kinnari và phù điêu kể chuyện đời Phật. |
| chua-vam-ray | year | ENTITY_FOUND_NOT_CLAIM_VERIFIED | Tốn 50 tỷ đồng xây dựng, khánh thành 2010. |
| chua-vam-ray | named_fact | ENTITY_FOUND_NOT_CLAIM_VERIFIED | Chùa Vàm Ray (Wath Vam Ray) là ngôi chùa Khmer lớn nhất Trà Vinh và cả ĐBSCL, tọa lạc tại xã Hàm Tân, huyện Trà Cú. |
| chua-vam-ray | measurement | ENTITY_FOUND_NOT_CLAIM_VERIFIED | Kiến trúc Khmer nguy nga, chánh điện rộng 50m × 22m, trang trí nổi bật với rắn thần Naga, Kinnari và phù điêu kể chuyện đời Phật. |
| chua-vam-ray | year | ENTITY_FOUND_NOT_CLAIM_VERIFIED | Tốn 50 tỷ đồng xây dựng, khánh thành 2010. |
| chua-vam-ray | hours+named_fact | ENTITY_FOUND_NOT_CLAIM_VERIFIED | {"hours": "6:00–18:00", "admission": "Miễn phí", "type": "chùa Khmer lớn nhất ĐBSCL", "schema_type": "TouristAttraction", "address": "Xã Trà Cú, Trà Vinh", "sub_category": "pagoda" |
| vinh-long-1-day-backpacker | hours | ENTITY_FOUND_NOT_CLAIM_VERIFIED | Vĩnh Long 1 ngày – Cù lao + Chợ nổi Hành trình 1 ngày backpacker từ TP.HCM đến Vĩnh Long: xuất phát 5h sáng, qua phà Đình Khao, khám phá cù lao Bình Hòa Phước, vườn trái cây, đò ch |
| vinh-long-1-day-backpacker | measurement+hours | ENTITY_FOUND_NOT_CLAIM_VERIFIED | Tổng chi phí khoảng 350.000–450.000 VNĐ/người, về lại TP.HCM trước 21h. |
| vinh-long-1-day-backpacker | named_fact | ENTITY_FOUND_NOT_CLAIM_VERIFIED | Phù hợp khách ưa trải nghiệm thực tế, không cần đặt tour. |
| vinh-long-1-day-backpacker | hours | ENTITY_FOUND_NOT_CLAIM_VERIFIED | Hành trình 1 ngày backpacker từ TP.HCM đến Vĩnh Long: xuất phát 5h sáng, qua phà Đình Khao, khám phá cù lao Bình Hòa Phước, vườn trái cây, đò chèo kênh rạch, gốm Mang Thít và chợ n |
| vinh-long-1-day-backpacker | measurement+hours | ENTITY_FOUND_NOT_CLAIM_VERIFIED | Tổng chi phí khoảng 350.000–450.000 VNĐ/người, về lại TP.HCM trước 21h. |
| vinh-long-1-day-backpacker | named_fact | ENTITY_FOUND_NOT_CLAIM_VERIFIED | Phù hợp khách ưa trải nghiệm thực tế, không cần đặt tour. |
| vinh-long-1-day-backpacker | measurement+hours+named_fact | ENTITY_FOUND_NOT_CLAIM_VERIFIED | {"traveler_type": "backpacker", "duration": "1 ngày", "provinces": ["Vĩnh Long", "Tiền Giang"], "best_time": "Thứ 3–Thứ 5, sáng sớm", "budget_range": "485.000–550.000 VNĐ/người", " |
| vinh-long-1-day-backpacker | measurement+hours | ENTITY_FOUND_NOT_CLAIM_VERIFIED | Đặt vé trước qua app, chọn chuyến 5h–5h30.\n> Chi phí: 90.000 VNĐ/chiều\n\n### 7:00 – Đến bến xe Vĩnh Long, bắt xe ôm/grab ra bến phà Đình Khao\nKhoảng 3 km từ bến xe. |
| vinh-long-1-day-backpacker | measurement+hours | ENTITY_FOUND_NOT_CLAIM_VERIFIED | Ghé ăn sáng bún nước lèo hoặc hủ tiếu Nam Vang ngay khu bến.\n> Chi phí: Ăn sáng 30.000–40.000 VNĐ \| Grab/xe ôm 15.000 VNĐ\n\n### 7:30 – Phà Đình Khao sang cù lao Bình Hòa Phước\nP |
| vinh-long-1-day-backpacker | measurement+hours | ENTITY_FOUND_NOT_CLAIM_VERIFIED | Sang đảo thuê xe đạp hoặc đi bộ khám phá.\n> Chi phí: Phà 5.000 VNĐ \| Xe đạp thuê 50.000 VNĐ/ngày\n\n### 8:00–10:00 – Vườn trái cây + đò chèo kênh rạch\nGhé vườn trái cây nhà dân ( |
| vinh-long-1-day-backpacker | measurement+hours | ENTITY_FOUND_NOT_CLAIM_VERIFIED | Thuê đò chèo luồn kênh rạch nhỏ, ngắm dừa nước, cầu khỉ.\n> Chi phí: Vào vườn + trái cây ~50.000 VNĐ \| Đò chèo 60.000–80.000 VNĐ/người (nhóm 2–4 giảm giá)\n> *Ghi chú: Mặc cả nhẹ v |
| vinh-long-1-day-backpacker | measurement+hours+named_fact | ENTITY_FOUND_NOT_CLAIM_VERIFIED | Chụp ảnh check-in, xem thợ làm gốm thủ công.\n> Chi phí: Miễn phí tham quan \| Mua gốm lưu niệm nhỏ 20.000–50.000 VNĐ\n> *Ghi chú: Vào trong lò gốm cũ cần hỏi chủ nhà, đa số họ vui  |
| vinh-long-1-day-backpacker | year+measurement+hours+named_fact | ENTITY_FOUND_NOT_CLAIM_VERIFIED | Buổi chiều ít người hơn sáng nhưng vẫn có ghe bán trái cây.\n> Chi phí: Thuê xuồng 100.000–120.000 VNĐ/người (nhóm 3–5 người)\n> *Ghi chú: Không mua hàng trên xuồng nếu không hỏi g |
| ben-tre-couple-2day-001 | named_fact | ENTITY_FOUND_NOT_CLAIM_VERIFIED | Nghỉ đêm tại homestay nhà vườn yên tĩnh, tận hưởng không khí miền Tây sông nước đúng nghĩa. |
| ben-tre-couple-2day-001 | named_fact | ENTITY_FOUND_NOT_CLAIM_VERIFIED | Nghỉ đêm tại homestay nhà vườn yên tĩnh, tận hưởng không khí miền Tây sông nước đúng nghĩa. |
| ben-tre-couple-2day-001 | measurement+hours+named_fact | ENTITY_FOUND_NOT_CLAIM_VERIFIED | {"content": "# Bến Tre 2 ngày – Cặp đôi lãng mạn\n\n## Di chuyển đến Bến Tre\n- **Từ TP.HCM:** Xe khách Phương Trang tại bến Miền Tây → Bến Tre (~2,5 giờ)\n- **Chi phí:** 80.000–12 |
| ben-tre-couple-2day-001 | measurement+hours+named_fact | ENTITY_FOUND_NOT_CLAIM_VERIFIED | buổi sáng ánh sáng đẹp nhất để chụp ảnh\n\n**11:00** – **Vườn dừa Bến Tre** *(khu vực Châu Thành)*\n- Dạo vườn, hái dừa uống tươi, chụp ảnh couple giữa hàng dừa thẳng tắp\n- **Chi  |
| ben-tre-couple-2day-001 | measurement+hours | ENTITY_FOUND_NOT_CLAIM_VERIFIED | xưởng Thanh Long và Duy Loan uy tín\n\n**17:00** – Nhận phòng **Homestay nhà vườn**\n- Gợi ý: Mekong Homestay hoặc Sân Vườn Bến Tre (khu Châu Thành)\n- **Chi phí:** 500.000–800.000 |
| ben-tre-couple-2day-001 | measurement+hours+named_fact | ENTITY_FOUND_NOT_CLAIM_VERIFIED | chọn phòng view sông\n\n**19:00** – Tối lãng mạn tại homestay\n- Chủ nhà nấu cơm miền Tây theo yêu cầu, ngồi võng ngắm đom đóm\n- **Chi phí:** 200.000–300.000đ/bữa\n\n---\n\n## Ngà |
| ben-tre-couple-2day-001 | measurement+season/date+hours | ENTITY_FOUND_NOT_CLAIM_VERIFIED | mang áo khoác vì sáng sớm lạnh\n\n**08:30** – Ăn sáng gần Vàm Hồ\n- Bánh canh Bến Tre, cháo vịt đặc sản Ba Tri\n- **Chi phí:** 50.000–70.000đ/2 người\n\n**10:00** – Mua sắm & về TP |
| tra-vinh-2-ngay-van-hoa-khmer | named_fact | ENTITY_FOUND_NOT_CLAIM_VERIFIED | Từ Chùa Âng linh thiêng, Ao Bà Om huyền thoại, Chùa Hang độc đáo, Bảo tàng Khmer phong phú đến chợ địa phương sầm uất và Biển Ba Động thơ mộng. |
| tra-vinh-2-ngay-van-hoa-khmer | named_fact | ENTITY_FOUND_NOT_CLAIM_VERIFIED | Từ Chùa Âng linh thiêng, Ao Bà Om huyền thoại, Chùa Hang độc đáo, Bảo tàng Khmer phong phú đến chợ địa phương sầm uất và Biển Ba Động thơ mộng. |
| tra-vinh-2-ngay-van-hoa-khmer | named_fact | ENTITY_FOUND_NOT_CLAIM_VERIFIED | {"content": "# Trà Vinh 2 Ngày – Văn Hóa Khmer\n\n## Thông tin chung\n- **Xuất phát:** TP. |
| tra-vinh-2-ngay-van-hoa-khmer | measurement+season/date+hours+named_fact | ENTITY_FOUND_NOT_CLAIM_VERIFIED | Hồ Chí Minh hoặc Vĩnh Long\n- **Phương tiện:** Xe máy hoặc xe thuê\n- **Đối tượng:** Cặp đôi, gia đình, nhóm bạn yêu văn hóa bản địa\n\n---\n\n## Ngày 1 – Khám Phá Trung Tâm Văn Hó |
| itinerary-mien-tay-nhiet-anh-001 | hours+named_fact | ENTITY_FOUND_NOT_CLAIM_VERIFIED | Miền Tây Nhiếp ảnh – Chợ nổi, làng gốm, hoàng hôn Hành trình 2 ngày dành cho nhiếp ảnh gia khám phá miền Tây sông nước: bình minh tại Chợ Nổi Trà Ôn (Vĩnh Long) lúc 5h sáng, "giờ v |
| itinerary-mien-tay-nhiet-anh-001 | measurement | ENTITY_FOUND_NOT_CLAIM_VERIFIED | Tổng chi phí ước tính 1.200.000–1.600.000 VNĐ/người, phù hợp nhiếp ảnh gia độc lập hoặc nhóm nhỏ. |
| itinerary-mien-tay-nhiet-anh-001 | hours+named_fact | ENTITY_FOUND_NOT_CLAIM_VERIFIED | Hành trình 2 ngày dành cho nhiếp ảnh gia khám phá miền Tây sông nước: bình minh tại Chợ Nổi Trà Ôn (Vĩnh Long) lúc 5h sáng, "giờ vàng" gốm đỏ Mang Thít rực lửa, và hoàng hôn cháy đ |
| itinerary-mien-tay-nhiet-anh-001 | measurement | ENTITY_FOUND_NOT_CLAIM_VERIFIED | Tổng chi phí ước tính 1.200.000–1.600.000 VNĐ/người, phù hợp nhiếp ảnh gia độc lập hoặc nhóm nhỏ. |
| itinerary-mien-tay-nhiet-anh-001 | measurement+hours+named_fact | ENTITY_FOUND_NOT_CLAIM_VERIFIED | {"content": "# Miền Tây Nhiếp ảnh – Chợ nổi, làng gốm, hoàng hôn\n\n**Tuyến:** Vĩnh Long → Trà Ôn → Mang Thít → sông Tiền Giang\n**Thời lượng:** 2 ngày 1 đêm\n\n---\n\n## Ngày 1\n\ |
| itinerary-mien-tay-nhiet-anh-001 | year+measurement+season/date+hours+named_fact | ENTITY_FOUND_NOT_CLAIM_VERIFIED | Mang ống kính tele 70–200mm.\n\n### 9:30 – Làng gốm Mang Thít\n- \"Giờ vàng\" chụp lò nung là 9:30–11:00\n- Chi phí: Vào tham quan miễn phí\n\n### 13:00 – Nghỉ trưa, nhận phòng hom |
| itinerary-ok-om-bok-tra-vinh-2024 | season/date | ENTITY_FOUND_NOT_CLAIM_VERIFIED | Lễ hội Ok Om Bok – Trà Vinh tháng 10 âm lịch Lịch trình 2 ngày 1 đêm khám phá Lễ hội Ok Om Bok tại Trà Vinh – nét văn hóa độc đáo của người Khmer Nam Bộ. |
| itinerary-ok-om-bok-tra-vinh-2024 | named_fact | ENTITY_FOUND_NOT_CLAIM_VERIFIED | Hành trình bao gồm lễ cúng trăng truyền thống, đua ghe ngo huyền thoại trên sông Long Bình, dạo phố đèn lồng lung linh và tham quan hội chợ đặc sản Khmer. |
| itinerary-ok-om-bok-tra-vinh-2024 | named_fact | ENTITY_FOUND_NOT_CLAIM_VERIFIED | Phù hợp cặp đôi, gia đình và nhóm bạn yêu văn hóa bản địa miền Tây sông nước. |
| itinerary-ok-om-bok-tra-vinh-2024 | named_fact | ENTITY_FOUND_NOT_CLAIM_VERIFIED | Hành trình bao gồm lễ cúng trăng truyền thống, đua ghe ngo huyền thoại trên sông Long Bình, dạo phố đèn lồng lung linh và tham quan hội chợ đặc sản Khmer. |
| itinerary-ok-om-bok-tra-vinh-2024 | named_fact | ENTITY_FOUND_NOT_CLAIM_VERIFIED | Phù hợp cặp đôi, gia đình và nhóm bạn yêu văn hóa bản địa miền Tây sông nước. |
| itinerary-ok-om-bok-tra-vinh-2024 | measurement+season/date+hours+named_fact | ENTITY_FOUND_NOT_CLAIM_VERIFIED | {"content": "# Lễ hội Ok Om Bok – Trà Vinh tháng 10 âm lịch\n\n## Ngày 1 – Khám phá lễ hội và đua ghe ngo\n\n**09:30** – Chùa Âng: Miễn phí, ngôi chùa Khmer cổ hơn 1.500 năm\n\n**1 |
| itinerary-ok-om-bok-tra-vinh-2024 | measurement+hours+named_fact | ENTITY_FOUND_NOT_CLAIM_VERIFIED | VIP 50.000–100.000đ\n- Hơn 30 đội ghe từ các chùa Khmer\n\n**19:30** – Lễ cúng trăng (Ok Om Bok) tại Ao Bà Om: Miễn phí\n\n**21:00** – Dạo phố đèn lồng trung tâm TP. |
| itinerary-ok-om-bok-tra-vinh-2024 | measurement+season/date+hours+named_fact | ENTITY_FOUND_NOT_CLAIM_VERIFIED | Trà Vinh\n\n---\n\n## Ngày 2 – Di tích và về\n\n**07:30** – Bánh canh Bến Có: 35.000–50.000đ\n\n**09:00** – Ao Bà Om & Bảo tàng văn hóa Khmer: 15.000đ/người\n\n---\n\n## Tổng chi p |
| ben-tre-vam-ho-birdwatching-t9-t3 | season/date+hours | ENTITY_FOUND_NOT_CLAIM_VERIFIED | Bến Tre – Ngắm chim Vàm Hồ tháng 9–3 Hành trình 2 ngày khám phá thiên nhiên Bến Tre dành cho người yêu birdwatching: thức dậy lúc 4h30 để đến sân chim Vàm Hồ ngắm hàng ngàn cò, vạc |
| ben-tre-vam-ho-birdwatching-t9-t3 | named_fact | ENTITY_FOUND_NOT_CLAIM_VERIFIED | tối thưởng thức kẹo dừa thủ công. |
| ben-tre-vam-ho-birdwatching-t9-t3 | season/date | ENTITY_FOUND_NOT_CLAIM_VERIFIED | Mùa cao điểm tháng 9 đến tháng 3, chi phí khoảng 600.000–900.000 đồng/người. |
| ben-tre-vam-ho-birdwatching-t9-t3 | hours | ENTITY_FOUND_NOT_CLAIM_VERIFIED | Hành trình 2 ngày khám phá thiên nhiên Bến Tre dành cho người yêu birdwatching: thức dậy lúc 4h30 để đến sân chim Vàm Hồ ngắm hàng ngàn cò, vạc, diệc bay về tổ lúc bình minh |

### C. Duplicate Candidates
No exact duplicate names were found by normalized-name scan. Near-duplicates remain a human merge-review task, especially for hotel names and entities sharing exact coordinates.

### D. Coordinates Anomalies
Full coordinate clusters are represented in the report above. Top clusters:

| Coordinate | Count | Example IDs |
| --- | --- | --- |
| 10.2542,105.9628 | 255 | vinh-long-1-day-backpacker, itinerary-mien-tay-nhiet-anh-001, cho-noi-tra-on-trai-nghiem-thuyen-hoa-qua, vl-accessibility-itinerary-001, lang-banh-trang-tra-on, lang-banh-trang-giay-tuong-loc, lang-det-chieu-cu-lao-dai, khu-sinh-thai-nha-xua-long-ho, cheo-xuong-rach-an-binh, lang-gach-gom-mang-thit |
| 10.2539,105.9722 | 89 | nha-hang-thien-tan, cu-lao-may-tra-on, cho-noi-tra-on-dc, khu-du-lich-s-mo-farm-cuu-long, nha-gom-tu-buoi, chua-khmer-vinh-long, vo-van-kiet, tong-huu-dinh, tran-quang-quon, truong-duy-toan |
| 10.2272,106.4072 | 80 | ben-tre-couple-2day-001, ben-tre-vam-ho-birdwatching-t9-t3, itinerary-cai-mon-tet-ben-tre, ben-tre-1-ngay-con-phuong-tphcm, co-diem---banh-canh-vit-bot-xat, banh-canh-bot-xat, goi-cu-hu-dua-tom-thit, com-dua-com-trai-dua, ca-bong-kho-nuoc-dua, chuot-dua-hap-com |
| 9.9516,106.3322 | 74 | quyt-duong-cau-ke, cua-hang-ocop-tra-vinh-trung-tam-xuc-tien-thuong-mai-tinh-tra-vinh, cua-hang-dac-san-mien-tay-tra-vinh-tra-vinh, cho-dem-tra-vinh-pho-di-bo-hung-vuong-tra-vinh, nha-tho-chanh-toa-tra-vinh-tra-vinh, khu-du-lich-sinh-thai-huynh-kha, tuan-le-van-hoa-du-lich-gan-voi-le-hoi-ok-om-bok, dua-sap, mua-chan, chua-samrong-ek |
| 9.9513,106.3346 | 53 | nguyen-thi-ut, thach-sok-xane, thach-oai, song-long-binh, canh-dong-dieu-tra-vinh, canh-dong-dien-gio-ngoai-khoi-ba-dong, tham-chua-khmer, banh-canh-ben-co-tra-vinh, thach-boi, chua-ba-thien-hau-tra-vinh |
| 10.0260,106.2930 | 47 | tra-vinh-2-ngay-van-hoa-khmer, itinerary-ok-om-bok-tra-vinh-2024, dua-sap-sinh-to, com-dep-tra-vinh, cha-hoa-nam-thuy, banh-u-da-loc, loi-choi-sa-ot, kenh-bong-bot-tra-vinh, rach-ba-sach-tra-vinh, cua-ben-gia-my-thanh-tra-vinh |
| 10.2433,106.3753 | 25 | khu-bao-ton-thien-nhien-thanh-phu, banh-trang-my-long, cho-thanh-phu, nha-dua-cocohome, khu-du-lich-lan-vuong, lang-nghe-cay-giong-cho-lach, hop-tac-xa-thuy-san-thanh-loi-ngheu-thanh-hai-ocop, bien-an-thuy, xoai-tu-quy, sa-po-che-cho-lach |
| 9.6621,106.5179 | 20 | monkey-tea---tra-sua-coffee, hu-tieu-go-duyen-hai-tra-vinh, quan-hai-san-duyen-hai-cho-duyen-hai-tra-vinh, khu-du-lich-sinh-thai-vung-dao-duyen-hai, tom-duyen-hai, chu-u-ba-dong, so-huyet-tra-vinh, khu-di-tich-can-cu-tinh-uy-tra-vinh, ben-xe-duyen-hai-tx-duyen-hai-tra-vinh, dinh-mieu-con-trung |
| 9.9334,106.3122 | 17 | lang-nghe-che-tac-mat-na-khmer-nguyet-hoa, le-hoi-ok-om-bok, khu-van-hoa-du-lich-ao-ba-om, bao-tang-van-hoa-dan-toc-khmer-tra-vinh, bao-tang-van-hoa-dan-toc-khmer, bun-rieu-cua-thao-my, ut-ngan-quan---dui-cuu-nuong, rang-bien-2---quan-nhau-binh-dan, cua-hang-ocop-ao-ba-om, banh-canh-ben-co |
| 10.2415,106.3759 | 17 | tom-cang-xanh-lot-an-thanh, lang-nghe-dan-gio-cong-dua-hung-phong, kem-baskin-robbins---sense-city, nha-hang-noi-ben-tre, quan-banh-uot-hai-nen, lau-3-con-tep, lucid-dream---tea-cake, banh-xeo-oc-gao-con-phu-da, ruou-phu-le-ba-tri, tom-su-nuong-than-binh-dai |
| 9.8716,106.0899 | 13 | dua-sap-cau-ke, bao-tang-dua-sap-tra-vinh, hu-tieu-ba-tam-cau-ke-tra-vinh, quan-chao-ca-ro-dong-cho-cau-ke-tra-vinh, mut-dua-sap-cau-ke, mia-tra-vinh, khu-luu-niem-nu-anh-hung-nguyen-thi-ut-ut-tich, ben-xe-cau-ke-tra-vinh, suonsia-homestay, cu-cai-muoi-chit-sa |
| 10.1673,106.6971 | 12 | khu-du-lich-sinh-thai-anh-ba-khia, tom-kho-binh-dai, mut-dua-huu-co-binh-dai, banh-xeo-bien-binh-dai, ca-doi-kho-mot-nang-binh-dai, le-hoi-nghinh-ong-binh-thang, bien-thua-duc, nhan-tieu-da-bo, ca-bong-lau-mot-nang-binh-dai, so-diep-binh-dai |
| 10.2361,106.3764 | 12 | nha-co-huynh-thuy-le, lang-keo-dua-phuong-7-ben-tre, am-thuc-chay-ta-on---duong-so-2, kem-xoi-dua---khu-sao-mai, vung-buoi-da-xanh-chau-thanh, khu-du-lich-lang-be, che-chuoi-nuong, khach-san-huynh-thao, buu-dien-trung-tam-tp-ben-tre-ben-tre, p-ben-tre |
| 9.9763,106.3446 | 12 | den-tho-bac-ho-tra-vinh, khu-du-lich-sinh-thai-deja-vu-huynh-kha, bun-bo-hue-19, ct-quan---mon-nuong-coffee, uyen-uong---nha-hang-tiec-cuoi, bun-nuoc-leo-hem-ly-thuong-kiet, quan-bun-rieu-cua-cho-cu-tra-vinh-tra-vinh, quan-di-bay-com-nieu-tra-vinh, ca-phe-cay-bang-phuong-4-tra-vinh, chua-ang |
| 10.0729,106.5977 | 12 | khu-di-tich-nguyen-dinh-chieu, lang-nghe-dan-dat-phuoc-tuy, lang-nghe-det-chieu-an-hiep, lang-nghe-keo-dua-ba-tri, lang-nghe-dan-lat-an-duc, khu-bao-ton-thien-nhien-dat-ngap-nuoc-vam-ho, bo-da-xanh-ba-tri, chua-khai-tuong, lang-nghe-tre-truc-ba-tri, bien-con-nhan |
| 9.7976,106.4548 | 12 | dac-san-mam-bo-hoc-tra-cuon, lang-nghe-banh-tet-tra-cuon, nha-trung-bay-va-ban-san-pham-ocop-cau-ngang-tra-vinh, tom-kho-vinh-kim, dau-phong-tra-vinh, ben-xe-cau-ngang-tra-vinh, chua-xvayton, lang-nghe-com-dep-ba-so, chua-giac-linh, san-pham-ocop-cau-ngang |
| 9.6427,106.5489 | 12 | ca-khoai-tra-vinh, nha-hang-bien-nho-ba-ong-tra-vinh, quan-nhau-hai-san-bien-ba-dong-tra-vinh, tom-kho-cham-mam-chua-ngot-duyen-hai, le-hoi-nghinh-ong-lang-con-tau, di-tich-lich-su-ben-tiep-nhan-vu-khi-con-tau, lau-ba-lau-ba-co-hy, lau-ba-co-hy-thuong-dong-nuong-nuong, khu-di-tich-lang-ong-con-tau, le-cung-lau-ba-ram-thang-gieng |
| 9.8837,106.7340 | 11 | cho-dem-ben-tre, keo-dua-ben-tre, mat-ong-hoa-dua-ben-tre, ngheu-ben-tre, festival-dua-ben-tre, ruou-dua-ben-tre, tinh-dau-dua, resort-ben-tre-riverside, mango-home-ben-tre, chua-van-phuoc |
| 10.0711,106.3585 | 11 | chua-tuyen-linh, lang-nghe-san-xuat-chi-xo-dua-an-thanh, lang-nghe-thu-cong-my-nghe-dua-mo-cay-nam, thu-hoach-dua-mo-cay, lang-keo-dua-mo-cay, ca-da-tron-nuoi-nuoc-ngot, nau-ruou-dua, lam-keo-dua-mo-cay, pho-tien, keo-dua-tuyet-phung |
| 10.2238,106.1914 | 11 | lang-van-hoa-du-lich-cho-lach, sau-rieng-cap-dong-chanh-thu, hoi-cho-thuong-mai-cay-giong-hoa-kieng-cho-lach, ca-tra, chom-chom-cho-lach, nhan-xuong-com-vang, di-ghe-tam-ban, ben-xe-cho-lach-ben-tre, lang-hoa-kieng-va-cay-giong-cho-lach, sau-rieng-cap-dong-cho-lach |
| 9.8506,106.6308 | 10 | bien-con-bung-thanh-phu-ben-tre, du-lich-sinh-thai-cong-dong-thanh-phong-ben-tre, ca-kho-dac-san-thanh-phong-ocop, xoai-tu-quy-va-cua-bien-thanh-phong-ocop, kho-ca-bong-lau-ca-du-do-ca-bong-cat-mot-nang-thanh-phong, ngheu-thanh-hai, lang-nghe-che-bien-hai-san-kho-thanh-phong, cua-bien-thanh-phu, khu-bao-ve-canh-quan-thanh-phu-ben-tre, duong-ho-chi-minh-tren-bien-ben-xuat-phat-thanh-phong |
| 9.8403,106.1729 | 9 | quan-hu-tieu-tieu-can-hu-tieu-muc-tra-vinh, quan-nhau-bo-song-ba-ke-tieu-can-tra-vinh, quan-lau-mam-mien-tay-cho-tieu-can-tra-vinh, lang-nghe-dan-chapay-phu-can, ben-xe-tieu-can-tra-vinh, thien-hau-cung-quang-dong, chua-kompongrang-wat-kompongro, vuon-buoi-xanh-vietgap-tu-o, p-tieu-can |
| 10.1834,105.9985 | 9 | lau-bo-bay-map, khu-du-lich-nha-xua-va-homestay-ut-trinh, lang-du-lich-cong-dong-cai-ngang, sieu-thi-thuy-tien, khu-tuong-niem-co-chu-tich-hdbt-pham-hung, dinh-ky-ha, khach-san-tan-xuan, riverside-park-eco-resort, nha-nghi-dl-sinh-thai-hoang-hao |
| 9.6578,106.2652 | 8 | chua-vam-ray-wat-samrong, lang-det-chieu-ca-hom-ham-tan, lang-nghe-det-chieu-ham-tan, lang-nghe-do-go-tre-ham-giang, lang-nghe-det-chieu-ca-hom, lang-nghe-tieu-thu-cong-nghiep-ham-giang-tre-truc, bo-salon-tre-ocop-tri-canh, xa-ham-giang |
| 9.8627,106.0262 | 8 | cu-lao-tan-quy-cau-ke, cu-lao-an-loc, du-lich-sinh-thai-nam-son, nha-tho-kinh-long-hoi, khu-du-lich-sinh-thai-nam-son, con-tan-quy-cu-lao-tan-quy, dua-sap-hoa-tan, mieu-ba-chua-xu-tan-quy |

### E. Phone Number Audit
Phone values found: 142. Invalid format count: 0.

### F. Source URL Audit
Full source audit: `docs\data-verification-sources.csv`.

### G. LLM-Generated Content Inventory
Explicit LLM/agent source entities: 171. Estimated LLM-like entities: 183. Treat all as `pending factual verification`.

### H. Mekong Delta Reference Data
Reference model used here: legacy areas `vinh-long`, `ben-tre`, `tra-vinh`; current post-2025 official naming may collapse Bến Tre/Trà Vinh old areas under tỉnh Vĩnh Long mới. Store both fields to avoid future confusion.

### I. Enrichment Prompt Templates
Prompt sources reviewed:
- `scripts/enrich_descriptions.py`: uses `cx/gpt-5.5`, temperature 0.65, 3–5 paragraphs from sparse metadata.
- `scripts/enrich_with_llm.py`: temperature 0.3, summary-to-description expansion.
- `scripts/generate_missing_descriptions.py`: temperature 0.7 fallback generation.

### J. Recommended Corrected Values
| entity_id | field | current_value | corrected_value | source |
| --- | --- | --- | --- | --- |
| hu-tieu-my-tho | attributes.origin / area | DB gán origin='Vĩnh Long' và area='vinh-long' cho Hủ tiếu Mỹ Tho. | Hủ tiếu Mỹ Tho là món do người Mỹ Tho chế biến; Mỹ Tho thuộc Tiền Giang cũ, ngoài 3 legacy areas. | [source](https://vi.wikipedia.org/wiki/H%E1%BB%A7_ti%E1%BA%BFu_M%E1%BB%B9_Tho) |
| banh-cong-soc-trang | attributes.origin / area | DB gán origin='Trà Vinh' và area='tra-vinh' cho Bánh cống Sóc Trăng. | Nguồn báo chí mô tả bánh cống là đặc sản/nguyên gốc Sóc Trăng cũ. | [source](https://vnexpress.net/banh-cong-dac-san-cua-nguoi-khmer-o-soc-trang-4523101.html) |
| chua-sa-lon-chua-chen-kieu | area / attributes.address / attributes.architectural_style | DB đặt Chùa Sà Lôn/Chùa Chén Kiểu ở Phường Trà Vinh, Trà Vinh và architectural_style='Chùa Việt'. | Chùa Sà Lôn/Chùa Chén Kiểu là chùa Khmer Nam tông ở khu vực Sóc Trăng cũ, nay thuộc Cần Thơ sau sáp nhập; không thuộc legacy Trà Vinh. | [source](https://vi.wikipedia.org/wiki/Ch%C3%B9a_S%C3%A0_L%C3%B4n) |
| chien-thang-giong-dua-giong-trom | area / summary / description | DB đặt Di tích lịch sử Chiến thắng Giồng Dứa ở Bến Tre và phần mô tả lại nói về mộ hợp chất Chợ Lách. | Nguồn báo chí địa phương mô tả Di tích lịch sử Chiến thắng Giồng Dứa là di tích cấp quốc gia của tỉnh Tiền Giang; nội dung mộ hợp chất Chợ Lách không khớp với tên entity. | [source](https://tintucmientay.baoangiang.com.vn/tien-giang-chien-thang-giong-dua-lam-chan-dong-du-luan-trong-va-ngoai-nuoc-a361124.html) |
| chua-ong-met-botum-vong-sa-som-rong | name / attributes.architectural_style | DB gộp tên Chùa Ông Mẹt với 'Botum Vong Sa Som Rong' và đặt architectural_style='Chùa Hoa'. | Chùa Ông Mẹt ở Trà Vinh là chùa Khmer Nam tông, còn Bô Tum Vông Sa Som Rông/Som Rong là một chùa Khmer khác ở Sóc Trăng/Cần Thơ mới. | [source](https://vovworld.vn/vi-VN/viet-nam-dat-nuoc-con-nguoi/chua-ong-met-di-tich-cap-quoc-gia-o-tinh-tra-vinh-2004638.vov5) |
| khu-bao-ton-lung-binh-hoa-tra-vinh | summary / description / area | DB tạo entity 'Khu bảo tồn thiên nhiên Lung Bình Hòa' ở Trà Vinh nhưng summary/description lại nói về Khu bảo tồn thiên nhiên Lung Ngọc Hoàng ở Hậu Giang. | Khu bảo tồn thiên nhiên Lung Ngọc Hoàng là một thực thể khác, nằm ở vùng Hậu Giang/Cần Thơ mới; nội dung hiện tại không chứng minh sự tồn tại của 'Lung Bình Hòa' tại Trà Vinh. | [source](https://vi.wikipedia.org/wiki/Khu_b%E1%BA%A3o_t%E1%BB%93n_thi%C3%AAn_nhi%C3%AAn_Lung_Ng%E1%BB%8Dc_Ho%C3%A0ng) |

### K. External Cross-Reference Log
Full log: `docs\data-verification-web-log.csv` (1745 searches). Sorted sample:

| # | entity_id | query | result | source | snippet |
| --- | --- | --- | --- | --- | --- |
| 1 | backpacker-mien-tay-3ngay-500k | Backpacker tiết kiệm 3 ngày dưới 500k ngày Miền Tây None | MISMATCH | [tourmientay.vn](https://tourmientay.vn/blogs/tour-ve-mien-tay-4-ngay-3-dem-2-ngay-dau-tai-an-giang-44) | Nếu bạn đang cảm thấy nhàm chán cuộc sống nơi thành thị phồn hoa hiện đại thì có lẽ bạn sẽ cần 1 tour về Miền Tây 4 ngày 3 đêm, cụ thể hơn là du lịch  |
| 2 | banh-cong-soc-trang | Bánh cống Sóc Trăng Trà Vinh đặc sản OCOP | MISMATCH | [tripi.vn](https://tripi.vn/blog/vi/du-lich/dac-san-soc-trang-nhung-mon-qua-am-thuc-doc-dao-kho-quen-tripi) | Bánh Cóng Sóc Trăng - Món ngon truyền thống đậm đà hương vị miền Tây.Hủ tíu cà ri, đặc sản của Vĩnh Châu - Sóc Trăng, được chế biến từ thịt vịt xiêm t |
| 3 | banh-mi-sau-hoa-ben-tre | Bánh mì Sáu Hoà Bến Tre địa chỉ | MISMATCH | [banhmihuynhhoa.vn](https://banhmihuynhhoa.vn/) | Không chỉ thu hút người dân Sài Gòn, người sành ăn, cộng đồng food blogger trên toàn thế giới, bánh mì Huynh Hoa còn được báo chí nước ngoài ca ngợi n |
| 4 | banh-trang-nem-cu-lao-may | Bánh tráng nem Cù Lao Mây Vĩnh Long đặc sản OCOP | MISMATCH | [dttc.sggp.org.vn](https://dttc.sggp.org.vn/ron-rang-lang-banh-trang-cu-lao-may-tram-nam-tuoi-post131500.html) | Lò bánh tráng Tuyết Mai là một trong những cơ sở có nhiều năm kinh nghiệm sản xuất bánh tráng nhúng và bánh nem ở làng nghề Cù lao Mây. |
| 5 | ben-xe-mien-tay-hcm | Bến xe Miền Tây None địa chỉ | MISMATCH | [paracelresort.com](https://paracelresort.com/ben-xe-mien-tay-o-dau-dia-chi-cach-di-so-dien-thoai-va-nhung-dieu-can-biet-truoc-khi-den/) | 1 day ago · Bến xe Miền Tây nằm tại 395 Kinh Dương Vương, phường An Lạc, quận Bình Tân, TP.HCM. Đây là bến xe khách lớn phục vụ các tuyến đi về khu vự |
| 6 | bun-nuoc-leo-cho-ba-tri-ben-tre | Bún nước lèo chợ Ba Tri Bến Tre địa chỉ | MISMATCH | [cl.pinterest.com](https://cl.pinterest.com/pin/bn-nc-lo-mt-c-sn-quen-thuc-ca-cc-tnh-min-ty-nhng-vn-b-nhiu-ngi-lm-tng-l-bn-mm--886294401661397928/) | Cách Làm Bún Nước Lèo Sóc Trăng đơn giản, mang đậm nét miền Tây. Bún nước lèo Sóc Trăng với vị ngọt ngon của cá đồng, mùi mắm thơm lừng đặc trưng, đặc |
| 7 | cha-lua-thanh-cong | Chả lụa Thành Công Vĩnh Long đặc sản OCOP | MISMATCH | [tintucmientay.baoangiang.com.vn](https://tintucmientay.baoangiang.com.vn/soc-trang-da-dang-san-pham-ocop-cung-ung-dip-tet-nguyen-dan-a386245.html) | Do sản phẩm chả lụa, pate sản xuất trong ngày là có nên tôi luôn chủ động được sản lượng để lúc nào hàng hóa cũng dồi dào, sẵn sàng đáp ứng nhu cầu củ |
| 8 | chien-thang-giong-dua-giong-trom | Di tích lịch sử Chiến thắng Giồng Dứa Bến Tre di tích lịch sử | MISMATCH | [tiengiangtoplist.vn](https://tiengiangtoplist.vn/top-20-di-tich-lich-su-o-tien-giang-nen-ghe-tham-mot-lan/) | Chien-thang-giong-dua-1-tiengiangtoplist. Chiến thắng Giồng Dứa.Chiến thắng Cổ Cò. Khi di tích lịch sử được xây dựng với tổng diện tích lên đến 5.000m |
| 9 | chua-giac-linh | Chùa Giác Linh Trà Vinh di tích lịch sử | MISMATCH | [dulichcantho.vn](https://dulichcantho.vn/kham-pha-diem-den/tra-vinh/di-tich-chua-giac-linh-2171007.html) | Chùa Giác linh được Bộ Văn hóa Thông tin công nhận là di tích lịch sử văn hóa cấp quốc gia theo Quyết định số 95-1998-QĐ/BVHTT ngày 24/01/1998. |
| 10 | chua-khai-tuong | Chùa Khải Tường Bến Tre di tích lịch sử | MISMATCH | [vi.wikipedia.org](https://vi.wikipedia.org/wiki/Chùa_Khải_Tường) | Chùa Khải Tường là một ngôi cổ tự, trước đây tọa lạc trên một gò cao tại ấp Tân Lộc, thuộc Gia Định xưa; nay ở khoảng khu vực Bảo tàng Chứng tích chiế |
| 11 | chua-sa-lon-chua-chen-kieu | Chùa Sà Lôn chùa Chén Kiểu Trà Vinh di tích lịch sử | MISMATCH | [mia.vn](https://mia.vn/cam-nang-du-lich/kham-pha-chua-sa-lon-voi-net-kien-truc-dac-sac-nhat-mien-song-nuoc-10615) | Nov 17, 2025 · Vào năm 1815, Chùa Sà Lôn (Chén Kiểu) được xây dựng bằng các nguyên vật liệu khai thác trong khu vực địa phương như gỗ, đất, lá cây...  |
| 12 | di-tich-duong-ho-chi-minh-tren-bien-ben-thanh-phong | Di tích Đường Hồ Chí Minh trên Biển Bến Thạnh Bến Tre di tích lịch sử | MISMATCH | [vi.wikipedia.org](https://vi.wikipedia.org/wiki/Đường_Hồ_Chí_Minh_trên_biển) | Đường Hồ Chí Minh trên biển là tên gọi của tuyến hậu cần chiến lược trên Biển Đông, đảm bảo nhiệm vụ vận tải quân sự đặc biệt, do Hải quân nhân dân Vi |
| 13 | dua-hau-tan-hung-ocop | Dưa hấu Tân Hưng OCOP Vĩnh Long đặc sản OCOP | MISMATCH | [khonggianthuonghieu.vinhlong.gov.vn](https://khonggianthuonghieu.vinhlong.gov.vn/en/product/dua-hau-binh-tan-p10490) | Dưa hấu Bình Tân là một trong những nông sản đặc trưng của vùng đất Tân Hưng, nơi người dân gắn bó lâu đời với nghề trồng dưa trên những chân đất phù  |
| 14 | homestay-con-ba-tu | Homestay Cồn Bà Tư Bến Tre địa chỉ | MISMATCH | [bentretourism.vn](https://bentretourism.vn/vi/homestayconbatu2) | Homestay Cồn Bà Tư. Giới thiệu. Một nơi bình yên và giản dị, tránh xa sự nhộn nhịp ồn ào của TP.Hcm cách 3h di chuyển. |
| 15 | homestay-lang-be | Homestay Làng Bè Vĩnh Long địa chỉ | MISMATCH | [localhome.vn](https://localhome.vn/) | Hotline 5 : 0787817569 Hotline 6 : 0392347181 Giám Đốc : 0901416888 local@gmail.com GPKD số: 093090000276 cấp ngày 13/11/2024 tại Phòng Kinh Tế, Hạ Tầ |
| 16 | hu-tieu-sa-dec-chu-tu-gan-cho-phu-hung-ben-tre | Hủ tiếu Sa Đéc Chú Tư gần chợ Phú Hưng Bến Tre địa chỉ | MISMATCH | [dulichbinhphuoc.vn](https://dulichbinhphuoc.vn/13-quan-hu-tieu-sa-dec-ngon-ma-ban-nen-ghe/) | Tô xương ống tại hủ tiếu Cô Liên. Ngoài hủ tiếu tại đây còn bán thêm bánh cánh, hoành thánh, nuôi và một số món khác. Địa chỉ: 111 đường Trần Phú, phư |
| 17 | itinerary-tuan-trang-mat-mien-tay-4n3d | Tuần trăng mật Miền Tây 4 ngày 3 đêm None | MISMATCH | [dulichdaiviet.com](https://dulichdaiviet.com/tour-noi-dia/tour-du-lich-trang-mat-da-nang-4-ngay-3-dem-tu-ha-noi-tp-hcm.html) | Du lịch tuần trăng mật.Mã tour: DN32. Thời gian: 4 ngày 3 đêm. |
| 18 | khoai-lang-binh-tan | Khoai lang tím Nhật Bình Tân Vĩnh Long đặc sản OCOP | MISMATCH | [tapchicongthuong.vn](https://tapchicongthuong.vn/magazine/emagazine--khoai-lang-binh-tan-but-pha-nho-ocop-317499.htm) | Dec 7, 2025 · Năm 2020, sản phẩm khoai lang tím sấy của Công ty chính thức đạt chứng nhận OCOP 4 sao, đánh dấu bước khởi đầu quan trọng trong lộ trình |
| 19 | khu-bao-ton-lung-binh-hoa-tra-vinh | Khu bảo tồn thiên nhiên Lung Bình Hòa Trà Vinh | MISMATCH | [vi.wikipedia.org](https://vi.wikipedia.org/wiki/Khu_bảo_tồn_thiên_nhiên_Lung_Ngọc_Hoàng) | Khu bảo tồn nằm tại xã Phương Bình, thành phố Cần Thơ cách trung tâm Thành phố Cần Thơ khoảng 40 km. Lung Ngọc Hoàng có nghĩa là "Vùng đất trũng ngập  |
| 20 | khu-luu-niem-nu-anh-hung-nguyen-thi-ut-ut-tich | Khu lưu niệm Nữ anh hùng Nguyễn Thị Út Út Trà Vinh di tích lịch sử | MISMATCH | [hauionline.edu.vn](https://hauionline.edu.vn/hinh-anh-ut-trang-a103055.html) | Nguyễn Thị Út (Út Tịch) sinh ngày 19/4/1931 tại xã Tam Ngãi, quận Cầu Kè, tỉnh Cần thơ. |
| 21 | khu-tuong-niem-nguyen-thi-ut-ut-tich | Khu Tưởng niệm Nguyễn Thị Út Út Tịch Trà Vinh di tích lịch sử | MISMATCH | [hauionline.edu.vn](https://hauionline.edu.vn/hinh-anh-ut-trang-a103055.html) | Nguyễn Thị Út (Út Tịch) sinh ngày 19/4/1931 tại xã Tam Ngãi, quận Cầu Kè, tỉnh Cần thơ. |
| 22 | nguyen-van-ton-thach-duong | Nguyễn Văn Tồn Thạch Duồng Vĩnh Long tiểu sử | MISMATCH | [vi.wikipedia.org](https://vi.wikipedia.org/wiki/Nguyễn_Văn_Tồn_(nhà_Nguyễn)) | Thống chế Điều bát Nguyễn Văn Tồn (Chữ Hán: 阮文存, 1763 – 1820) là một danh tướng và nhà khai hoang đầu thời nhà Nguyễn trong lịch sử Việt Nam. Ông là n |
| 23 | p-tan-quoi | Phường Tân Quới Vĩnh Long | MISMATCH | [vi.wikipedia.org](https://vi.wikipedia.org/wiki/Tân_Quới) | Tân Quới vốn là một thôn được thành lập từ thế kỷ XIX, được ghi trong địa bạ triều vua Minh Mạng từ năm 1836. Khi đó, Tân Quới thuộc tổng An Trường, h |
| 24 | quan-thuan-phuc-vinh-long | Quán Thuận Phúc Vĩnh Long địa chỉ | MISMATCH | [tiktok.com](https://www.tiktok.com/@phuc_vinh_thuan/video/7631125885692792085) | Phúc - vĩnh thuận kiên giang. Trả lời @Phạm Kiều trang Mai e Sam do dep e ban Cho Chế coi he#phucvinhthuan #xuhuongtiktok #lamtheoyeucau #monque. |
| 25 | somo-farm-cuu-long | Somo Farm Cửu Long lưu trú sinh thái Vĩnh Long địa chỉ | MISMATCH | [somofarmcuulong.somogroup.vn](https://somofarmcuulong.somogroup.vn/) | Trải nghiệm sinh thái.Góc chia sẻ. Ngày 03/11/2024. Lễ ký kết hợp tác giữa đại học kinh tế tp.hcm (ueh) và somo farm cửu long. |
| 26 | tom-kho-binh-dai | Tôm khô Bình Đại Bến Tre đặc sản OCOP | MISMATCH | [sanphamocop.com.vn](https://sanphamocop.com.vn/dac-san-tet-cac-vung-mien-ma-ban-nen-biet-2/) | Tôm khô Cà Mau là đặc sản được xem như “vàng đỏ” của miền Tây. Tôm tươi được luộc, bóc vỏ rồi phơi khô tự nhiên dưới nắng biển, giữ nguyên vị ngọt đậm |
| 27 | tuong-quan-nguyen-van-ton | Tướng quân Nguyễn Văn Tồn Vĩnh Long tiểu sử | MISMATCH | [vi.wikipedia.org](https://vi.wikipedia.org/wiki/Nguyễn_Văn_Tồn_(nhà_Nguyễn)) | Thống chế Điều bát Nguyễn Văn Tồn (Chữ Hán: 阮文存, 1763 – 1820) là một danh tướng và nhà khai hoang đầu thời nhà Nguyễn trong lịch sử Việt Nam. Ông là n |
| 28 | 1983-coffee-pizza | 1983 Coffee & Pizza Trà Vinh địa chỉ | MATCH | [diadiem247.com](https://diadiem247.com/tra-vinh/1983-coffee-pizza-l176128.html) | Thông tin về địa điểm 1983 Coffee & Pizza, 26 Nguyễn Thái Học, Phường 1, Thành phố Trà Vinh, Tỉnh Trà Vinh |
| 29 | 1985-cafe | 1985 Cafe Trà Vinh địa chỉ | MATCH | [danhgiathuonghieu.vn](https://danhgiathuonghieu.vn/bo-tui-ngay-top-5-quan-cafe-dep-o-tra-vinh-ban-co-the-check-in/) | Quán cafe Trà Vinh 1985 sẽ là một điểm nghỉ ngơi rất yên tĩnh cho các thực khách.Menu quán gồm các loại trà, cafe có hương vị rất riêng biệt. Ngoài vi |
| 30 | 3-mien-tra-vinh---bun-dau-mam-tom | 3 Miền Trà Vinh Bún Đậu Mắm Tôm Trà Vinh đặc sản OCOP | MATCH | [foody.vn](https://www.foody.vn/tra-vinh/3-hien-tra-vinh-bun-dau-mam-tom) | Trà Vinh, Trà Vinh. Đang mở cửa. Từ khoá đã tìm.Hơn 3 tháng chưa có tương tác mới tại địa điểm này, bạn hãy liên hệ để kiểm tra lại trước khi đến! 3 M |
| 31 | agribank-chi-nhanh-vinh-long-vinh-long | Agribank Chi nhánh Vĩnh Long Vĩnh Long địa chỉ | MATCH | [timbankvn.com](https://timbankvn.com/ngan-hang/agribank-vinh-long/) | Danh Sách Ngân Hàng Agribank Vĩnh Long. Thông tin chi nhánh & phòng giao dịch Agribank tại Vĩnh Long bao gồm : Hotline, địa chỉ và lịch làm việc... |
| 32 | am-thuc-chay-hoa-sen-vinh-long | Ẩm Thực Chay Hoa Sen Vĩnh Long địa chỉ | MATCH | [3321.info](https://3321.info/A830F0A1H2C7081) | Địa chỉ: 191/2 đường lò rèn, phường Phước hậu, tỉnh Vĩnh Long, Việt Nam. Chủ đề: Email: [email protected].không khí ở Chay Hoa Sen nhẹ nhàng để chào đ |
| 33 | am-thuc-chay-ta-on---duong-so-2 | Ẩm Thực Chay Tạ Ơn Đường Số 2 Bến Tre địa chỉ | MATCH | [foody.vn](https://www.foody.vn/ben-tre/am-thuc-chay-ta-on-duong-so-2) | Ẩm Thực Chay Tạ Ơn - Đường Số 2 - Quán ăn - Món Việt tại 27E Đường Số 2, KP. Mỹ Tân, P. 7, Thành Phố Bến Tre, Bến Tre. Giá bình quân đầu người 15.000đ |
| 34 | am-thuc-ngo-dong-ben-tre | Ẩm Thực Ngô Đồng Bến Tre địa chỉ | MATCH | [tintuc.obranding.vn](https://tintuc.obranding.vn/am-thuc-ngo-dong-diem-hen-am-thuc-mien-tay-dam-chat-dong-que-tai-ben-tre/) | Ẩm Thực Ngô Đồng không chỉ là nơi mang đến những món ăn ngon mà còn là cầu nối để thực khách trải nghiệm nét văn hóa ẩm thực đặc sắc của miền Tây. Địa |
| 35 | am-thuc-san-vuon-1985-vinh-long | Ẩm Thực Sân Vườn 1985 Vĩnh Long địa chỉ | AMBIGUOUS | [tiktok.com](https://www.tiktok.com/discover/ẩm-thực-sân-vườn-mái-lá-quận-7) | Món cơm ngon tại Hòa Ký, Cơm heo quay đặc sắc, Cơm vịt quay hấp dẫn, Cơm gà tươi ngon, Cơm xá xíu truyền thống, Cơm Ngũ Bảo thú vị, Địa chỉ Hòa Ký Quậ |
| 36 | an-vat-kimoochi-tra-vinh | Ăn Vặt Kimoochi Trà Vinh điểm tham quan | MATCH | [inhat.vn](https://inhat.vn/an-vat-tra-vinh/) | Tham khảo bảng giá các món ăn vặt tại Kimoochi. 5. Ti – Ăn Vặt Bánh Tráng Trà Vinh. |
| 37 | anns-coffee | Ann's Coffee Bến Tre địa chỉ | MATCH | [facebook.com](https://www.facebook.com/anncoffeetea/) | ANN’S CHÍNH THỨC MỞ BÁN MENU MỚI 😍 🥳 Tụi mình mời bạn chọn! ~~~~~~~~~~~~~~~~~~~~ 🌲Ann's Coffee & Tea 📍 142B2, Đại Lộ Đồng Khởi, P. Phú Khương, TP. Bến |
| 38 | ao-ba-om | Ao Bà Om Trà Vinh điểm tham quan | MATCH | [traveloka.com](https://www.traveloka.com/vi-vn/explore/destination/ao-ba-om/514387) | Khám phá Ao Bà Om ở Trà Vinh nổi tiếng với mặt nước trong xanh và hàng cây sao, cây dầu cổ thụ lâu đời, tạo nên vẻ đẹp thiên nhiên yên bình, huyền bí. |
| 39 | ao-ba-om-ao-vuong | Ao Bà Om Ao Vuông di tích văn hóa Khmer Trà Vinh di tích lịch sử | MATCH | [vietnam.vn](https://www.vietnam.vn/tra-vinh-di-tich-ao-ba-om) | Di tích danh thắng Ao Bà Om còn gọi là Ao Vuông vì ao có hình gần vuông. Việt Nam Việt Nam•02/01/2025. Theo dõi Vietnam.vn trên. |
| 40 | ao-ba-om-ao-vuong-tra-vinh | Ao Bà Om Ao Vuông thắng cảnh Trà Vinh Trà Vinh điểm tham quan | MATCH | [hitour.vn](https://hitour.vn/tin-tuc-du-lich-tra-vinh/diem-den-tra-vinh/ao-ba-om-tra-vinh) | tour du lịch Trà Vinh. Ao Bà Om Trà Vinh - Ảnh: ST.Chùa Âng Trà Vinh tọa lạc bên quốc lộ 53, thuộc khóm 4, phường 8, thành phố Trà Vinh, tỉnh Trà Vinh |
| 41 | atm-vietcombank-benh-vien-da-khoa-tinh-vinh-long | ATM Vietcombank Bệnh viện Đa khoa tỉnh Vĩnh Long địa chỉ | MATCH | [vietcombank.diadiembank.com](https://vietcombank.diadiembank.com/atm-vietcombank-thanh-pho-vinh-long/) | ATM Vietcombank BVĐK Vĩnh Long. Địa chỉ : 301 Trần Phú, Phường 4, Long Hồ, Vĩnh Long. Giờ Mở Cửa : 24/7. ATM Vietcombank Bệnh Viên Triều An - Loan Trâ |
| 42 | ba-ba---banh-flan | Bà Ba Bánh Flan Bến Tre đặc sản OCOP | MATCH | [vntraveller.com](https://vntraveller.com/quan-an-ben-tre/) | 6-Quán flan Bà Ba – quán ăn Bến Tre ngon.Đuông Dừa – đặc sản nổi tiếng “dị” có phần kinh hãi nhưng thú vị của ẩm thực Bến Tre. Bởi chúng là sâu dừa ch |
| 43 | ba-dong-beach-resort | Ba Động Beach Resort Trà Vinh địa chỉ | MATCH | [foody.vn](https://www.foody.vn/tra-vinh/khu-du-lich-bien-ba-dong-tra-vinh/binh-luan-364482) | Biển Ba động, 1 bãi biển nổi tiếng còn giữ nét hoang sơ nhất của Trà Vinh. Tôi bước tới đây vào một buổi sáng cùng bạn bè. Trên đường đi bạn được ngắm |
| 44 | ba-du | Ba Du Vĩnh Long tiểu sử | AMBIGUOUS | [vi.wikipedia.org](https://vi.wikipedia.org/wiki/Ba_Du) | Ba Du (1904 – 1980) là một nghệ sĩ cải lương người Việt Nam. Ông là một trong những nghệ sĩ tiên phong của sân khấu cải lương Nam Bộ, được xem là một  |
| 45 | ba-linh-homestay | Ba Linh Homestay Vĩnh Long địa chỉ | MATCH | [mytour.vn](https://mytour.vn/khach-san/22374-ba-linh-homestay.html) | Chào mừng bạn đến Ba Linh Homestay - Ngôi Nhà Ấm Cúng ở Vĩnh Long Địa chỉ: 112/8 An Thanh, An Binh, Long Ho, Vĩnh Long, Việt Nam Tại Ba Linh Homestay, |
| 46 | ba-nhi-bun-bo-hue-vinh-long | Ba Nhì Bún Bò Huế Vĩnh Long đặc sản OCOP | MATCH | [canthogo.vn](https://canthogo.vn/dac-san-tra-vinh-vinh-long/) | Trần Kim Nhờ Vĩnh Long, Đặc sản Không có bình luận. Trà Vinh (Vĩnh Long) – viên ngọc quý của Đồng bằng sông Cửu Long, không chỉ nổi tiếng với những vư |
| 47 | bai-bien-ba-dong | bãi biển Ba Động Trà Vinh | MATCH | [blog.vexere.com](https://blog.vexere.com/bien-ba-dong-tra-vinh/) | Nơi đây cách trung tâm thành phố Trà Vinh khoảng 55km và cách TP.HCM khoảng 200km. Với vẻ đẹp hoang sơ, bãi cát dài và không gian yên bình, biển Ba Độ |
| 48 | bai-bien-ba-tri | Bãi biển Ba Tri Bến Tre | MATCH | [dulichbinhminh.com](https://dulichbinhminh.com/bien-ba-tri-ben-tre) | Đó là biển Ba Tri, thuộc huyện Ba Tri, tỉnh Bến Tre — nơi có ít khách du lịch hơn các bãi biển nổi tiếng nên giữ được không khí yên bình. |
| 49 | bai-bien-con-bung-thanh-hai | Bãi biển Cồn Bửng Thạnh Hải Bến Tre | MATCH | [mia.vn](https://mia.vn/cam-nang-du-lich/bien-con-bung-ben-tre-noi-tieng-voi-net-dep-thuan-tu-nhien-11579) | Oct 11, 2023 · Biển Cồn Bửng là địa điểm du lịch Bến Tre rất được người dân bản địa và tín đồ xê dịch ưa chuộng. Nơi đây khiến bao người ngẩn ngơ bởi  |
| 50 | bai-bien-mo-o-truong-long-hoa-tra-vinh | Bãi biển Mỏ Ó Trường Long Hòa Trà Vinh | MATCH | [vi.wikipedia.org](https://vi.wikipedia.org/wiki/Biển_Ba_Động) | Biển Ba Động là một khu du lịch biển tọa lạc trên địa bàn khóm Cồn Trứng, phường Trường Long Hòa, tỉnh Vĩnh Long, Việt Nam (trước đây là xã Trường Lon |
| 51 | bai-bien-thanh-phu | Bãi biển Thạnh Phú Bến Tre | MATCH | [halotravel.vn](https://halotravel.vn/bien-thanh-phu-ben-tre/) | bien thanh phu ben tre. Ảnh: @1chuong1.Đa số mọi người đi du lịch biển Thạnh Phú Bến Tre đều chỉ đi trong ngày, nên các du khách thường thuê ghế trên  |
| 52 | bai-boi-rung-ngap-man-ba-tri-ben-tre | Bãi Bồi Và Rừng Ngập Mặn Ba Tri Bến Tre | MATCH | [mytour.vn](https://mytour.vn/vi/blog/bai-viet/du-lich-ba-tri-ben-tre-5-diem-thu-vi-dang-cho-ban-kham-pha.html) | Ba Tri là một trong những điểm du lịch phổ biến của tỉnh Bến Tre. Hãy cùng khám phá 5 điểm du lịch Ba Tri đầy hấp dẫn, đẹp mắt và nổi tiếng. Tổng quan |
| 53 | bai-tam-con-phu-binh | Bãi tắm cồn Phú Bình Bến Tre | MATCH | [vietwave.com.vn](https://vietwave.com.vn/mextravel/vi/tin-tuc/top-nhung-diem-tham-quan-noi-tieng-tai-ben-tre-90) | Tắm Biển Cồn Bửng Bến Tre ăn hải sản bao ngon bao rẻ. Biển Cồn Bửng còn được nhiều người biết tới với tên Thạnh Phú, một trong những bãi biển vẫn còn  |
| 54 | banh-bao-tai-co | Bánh Bao Tài Có Vĩnh Long đặc sản OCOP | MATCH | [vinhlongtourist.vn](https://vinhlongtourist.vn/vi/detailnews/?t=vinh-long-tham-gia-ngay-hoi-banh-dan-gian-nam-bo-ket-hop-hoi-cho-xuc-tien-thuong-mai-san-pham-ocop-va-dac-san-vung-mien-tinh-vinh-long-nam-2025&id=news_12133) | sản phẩm OCOP tiêu biểu đặc trưng của tỉnh như bánh phồng khoai lang, bánh quy khoai lang, khoai lang sấy,... để giới thiệu đến du khách trong và ngoà |
| 55 | banh-bo-nuong-tra-vinh | Bánh bò nướng Trà Vinh Trà Vinh đặc sản OCOP | MATCH | [thamhiemmekong.com](https://thamhiemmekong.com/thong-tin-du-lich-mien-tay/nhung-mon-ngon-dac-san-tra-vinh-nhat-dinh-phai-thu.html) | Món ăn này có sự kết hợp giữa các nguyên liệu như mắm bò hóc, thịt heo quay và các loại rau sống.Xuất phát từ món ăn dân dã trong đời sống hàng ngày,  |
| 56 | banh-canh-ben-co | Bánh canh Bến Có Trà Vinh đặc sản OCOP | MATCH | [vicosap.vn](https://vicosap.vn/top-3-dia-diem-mua-qua-tet-uy-tin-o-tra-vinh-d480263) | Bánh canh Bến Có nổi tiếng hơn 20 năm qua gắn liền với địa danh ấp Bến Có, thuộc xã Nguyệt Hóa, huyện Châu Thành, tỉnh Trà Vinh.Cửa hàng trưng bày sản |
| 57 | banh-canh-ben-co-tra-vinh | Bánh Canh Bến Có Trà Vinh Trà Vinh đặc sản OCOP | MATCH | [duasapvicosap.vn](http://duasapvicosap.vn/top-3-dia-diem-mua-qua-tet-uy-tin-o-tra-vinh-d480263) | Tỉnh Trà Vinh hiện có 184 sản phẩm OCOP của 118 chủ thể (72 hộ kinh doanh; 20 công ty, 5 doanh nghiệp, 19 hợp tác xã và 2 tổ hợp tác). Trung ương cũng |
| 58 | banh-canh-ben-tre | Bánh canh Bến Tre Bến Tre đặc sản OCOP | MATCH | [oneshop.vn](https://oneshop.vn/blog/dac-san-o-ben-tre-mon-gi-ngon-n10p) | Bến Tre nổi tiếng với nhiều món ăn mang hương vị đặc trưng miền Tây Nam Bộ.Bánh canh bột xắt là đáp án tiếp theo cho câu hỏi “Đặc sản ở Bến Tre món gì |
| 59 | banh-canh-bot-xat | Bánh Canh Bột Xắt Bến Tre đặc sản OCOP | MATCH | [vietfuntravel.com.vn](https://www.vietfuntravel.com.vn/blog/banh-canh-bot-xat-ben-tre.html) | Bánh canh bột xắt - đặc sản nức tiếng Bến Tre.Sở dĩ có tên là bánh canh bột xắt Bến Tre vì các sợi bánh canh đều được xắt hoàn toàn bằng tay. Các sợi  |
| 60 | banh-canh-bot-xat-ben-tre | Bánh Canh Bột Xắt Bến Tre Bến Tre đặc sản OCOP | MATCH | [vietfuntravel.com.vn](https://www.vietfuntravel.com.vn/blog/banh-canh-bot-xat-ben-tre.html) | Bánh canh bột xắt - đặc sản nức tiếng Bến Tre.Bánh canh bột xắt thịt vịt thường có vị thơm và đặc sắc hơn bánh canh giò heo. Thịt vịt tính hàn ăn cùng |
| 61 | banh-canh-cho-ben-tre-hang-goc-cho-ben-tre-ben-tre | Bánh canh chợ Bến Tre hàng góc chợ Bến Tre Bến Tre địa chỉ | MATCH | [buulong.com.vn](https://buulong.com.vn/banh-canh-bot-xat-cho-ben-tre.html) | Những địa chỉ nổi bật để thưởng thức bánh canh bột xắt ở Bến Tre. Quán “BA Chớ” – hương vị vịt đậm đà. Lý do “BA Chớ” được yêu thích. |
| 62 | banh-canh-chu-bay-giong-trom-ben-tre | Bánh canh Chú Bảy Giồng Trôm Bến Tre địa chỉ | MATCH | [tiktok.com](https://www.tiktok.com/@angiodauvlog/video/7477417905928277255) | 9945 Lượt thích,497 Bình luận.Video TikTok từ Ăn Gì Ở Đâu? (@angiodauvlog): "Tìm hiểu về món Bánh Canh Lùm nổi tiếng ở Giồng Trôm, Bến Tre. |
| 63 | banh-cuon-nong---tran-quoc-tuan | Bánh Cuốn Nóng Trần Quốc Tuấn Trà Vinh đặc sản OCOP | MATCH | [foody.vn](https://www.foody.vn/tra-vinh/banh-cuon-nong-tran-quoc-tuan/album-tong-hop) | Trà Vinh tra vinh. Bạc Liêu bac lieu. Phú Thọ phu tho. |
| 64 | banh-dua-giong-luong | Bánh dừa Giồng Luông Bến Tre đặc sản OCOP | AMBIGUOUS | [nhandan.vn](https://nhandan.vn/luu-giu-nghe-lam-banh-dua-truyen-thong-post778945.html) | Sản phẩm bánh dừa Giồng Luông được cấp nhãn hiệu và đạt chứng nhận OCOP hạng 3 sao.Từ đó, bánh dừa mang tên Giồng Luông trở thành đặc sản của địa phươ |
| 65 | banh-flan-14 | Bánh Flan 14 Bến Tre đặc sản OCOP | MATCH | [tasteofvietnam.vn](https://tasteofvietnam.vn/top-16-mon-ngon-ben-tre-dac-san-mien-tay-dang-thu-nhat.html) | Món ngon Bến Tre – Bến Tre nổi tiếng với du khách gần xa bởi những rặng dừa xanh bát ngát. Đây cũng là nơi thiên nhiên ưu ái ban tặng những vườn trái  |
| 66 | banh-kep-thuy-kieu | Bánh kẹp Thúy Kiều Bến Tre đặc sản OCOP | MATCH | [nongthon.vietnamtourism.gov.vn](https://nongthon.vietnamtourism.gov.vn/ben-tre-khai-thac-phat-trien-tuyen-du-lich-cho-noi-dua-song-thom/) | ...đặc biệt là giới thiệu, quảng bá sản phẩm OCOP đạt chất lượng 3 sao, 4 sao của huyện đến nhiều công ty lữ hành du lịch và khách du lịch như: Kẹo dừ |
| 67 | banh-la-dua-vinh-long | Bánh lá dứa Vĩnh Long Vĩnh Long đặc sản OCOP | MATCH | [baovinhlong.com.vn](https://baovinhlong.com.vn/tin-moi/202504/da-them-voi-hang-tram-loai-banh-dan-gian-nam-bo-76f08de/) | Vĩnh Long là địa phương có thế mạnh nông nghiệp với nhiều sản phẩm chủ lực như bưởi năm roi Bình Minh, cam sành Tam Bình, sầu riêng ri 6, chôm chôm Bì |
| 68 | banh-mi-co-lan-duong-hung-vuong-ben-tre | Bánh mì Cô Lan đường Hùng Vương Bến Tre địa chỉ | MATCH | [mytour.vn](https://mytour.vn/vi/blog/bai-viet/danh-sach-cac-nha-hang-ngon-nhat-o-ben-tre.html) | Địa chỉ: Bến Hùng Vương, Thành phố Bến Tre.Địa chỉ: Số 210B, đại lộ Đồng Khởi, Thành phố Bến Tre. Với phòng riêng thiết kế ấm cúng và tiện nghi, Nhà h |
| 69 | banh-mi-co-sau-gan-truong-ai-hoc-tra-vinh-tra-vinh | Bánh mì Cô Sáu gần Trường Đại học Trà Vinh Trà Vinh địa chỉ | MATCH | [tiktok.com](https://www.tiktok.com/@anvattravinh/video/7582960990199794965) | Ăn vặt Trà Vinh Quyên. Dâu hôm nay đẹp xuất sắc, dâu tây mùa này ngọt rồi nhe khách ơi, ở Trà Vinh có tìm dâu thì ghé em nhe. |
| 70 | banh-nhat-ngoc | Bánh Nhật Ngọc Vĩnh Long đặc sản OCOP | MATCH | [demeter.vn](https://demeter.vn/tin-tuc/hang-nghin-san-pham-ocop-do-bo-ve-phien-cho-tet-xanh) | Tiểu thương sẵn sàng đón khách. Anh Nguyễn Thanh Việt, đại diện Công ty TNHH Bánh Nhật Ngọc (Vĩnh Long), cho biết năm nay là năm thứ ba anh tham gia p |
| 71 | banh-phong-khoai-lang-nhat-ngoc | Bánh phồng khoai lang Nhật Ngọc Vĩnh Long đặc sản OCOP | MATCH | [vinhlong.gov.vn](https://vinhlong.gov.vn/svhttdl/xem-chi-tiet-tin-tuc/id/208085) | Mong rằng, trong thời gian tới, các sản phẩm được làm từ khoai lang, đặc biệt là sản phẩm được công nhận OCOP tiêu biểu 4 sao, sẽ trở thành một trong  |
| 72 | banh-phong-mi-giong-trom | Bánh Phồng Mì Giồng Trôm Bến Tre đặc sản OCOP | AMBIGUOUS | [vi.wikipedia.org](https://vi.wikipedia.org/wiki/Bánh_phồng_Sơn_Đốc) | Ngoài hai nguyên liệu chính, bánh phồng Sơn Đốc được làm bằng hai loại bột nếp và bột khoai mì, kèm theo đó là mè, đậu xanh, sầu riêng, trứng gà, sữa, |
| 73 | banh-phong-son-doc | Bánh phồng Sơn Đốc Bến Tre đặc sản OCOP | MATCH | [dulichvn.org.vn](https://dulichvn.org.vn/index.php/item/ben-tre-ve-tham-lang-nghe-banh-phong-son-doc-hon-tram-nam-tuoi-63465) | Bánh phồng Sơn Đốc vang danh hàng trăm năm qua.Hiện tại cơ sở của tôi có 2 sản phẩm OCOP hạng 3 sao là bánh phồng mì dán chuối và bánh phồng mì béo”. |
| 74 | banh-phu-the-vinh-long | Bánh phu thê Vĩnh Long Vĩnh Long đặc sản OCOP | MATCH | [baomoi.com](https://baomoi.com/banh-phong-son-doc-giu-hon-lang-nghe-nho-nhan-hieu-tap-the-c55500479.epi) | 3 hours ago · Làng nghề bánh phồng Sơn Đốc hơn trăm năm tuổi ở Vĩnh Long đang nâng cao giá trị nhờ phát triển sở hữu trí tuệ. Với vai trò quan trọng c |
| 75 | banh-tam-ben-tre-hang-xe-day-khu-vuc-truong-hoc-ben-tre | Bánh tằm Bến Tre hàng xe đẩy khu vực trường Bến Tre địa chỉ | MATCH | [vietfuntravel.com.vn](https://www.vietfuntravel.com.vn/blog/nhung-dia-diem-tham-quan-va-du-lich-o-ben-tre.html) | Cách trung tâm thành phố Bến Tre khoảng 5km, khu du lịch Lan Vương là thiên đường vui chơi nghỉ dưỡng được nhiều bạn trẻ Sài Thành tìm đến dạo thời gi |
| 76 | banh-tet-ba-nhan | Bánh tét ba nhân Vĩnh Long đặc sản OCOP | MATCH | [baotintuc.vn](https://baotintuc.vn/kinh-te/dac-san-banh-tet-vinh-long-khang-dinh-thuong-hieu-nho-ocop-20260206155542860.htm) | Feb 6, 2026 · Từ các hộ làm bánh ở làng nghề bánh tét Trà Cuôn (xã Vinh Kim) đến những hộ gói bánh truyền thống ngoài làng nghề, không khí sản xuất tấ |
| 77 | banh-tet-la-cam | Bánh tét lá cẩm Trà Vinh đặc sản OCOP | MATCH | [mytour.vn](https://mytour.vn/vi/blog/bai-viet/nhung-dac-san-noi-tieng-cua-am-thuc-tra-vinh.html) | Bánh tét cốm dẹp Trà Vinh, không chỉ dẻo quyện như bánh chưng hay bánh tét truyền thống mà còn đậm đà với hương thơm của cốm, dừa, và gạo mới. Mỗi miế |
| 78 | banh-tet-tra-cuon | Bánh tét Trà Cuôn Trà Vinh đặc sản OCOP | MATCH | [nhandan.vn](https://nhandan.vn/san-pham-ocop-phuc-vu-thi-truong-tet-post936928.html) | Đa dạng sản phẩm bánh tét Trà Cuôn.Theo Sở Công thương tỉnh Vĩnh Long, thực hiện Chương trình mỗi xã một sản phẩm, các sản phẩm đặc trưng, OCOP của tỉ |
| 79 | banh-tet-tra-cuon-co-huong | Bánh Tét Trà Cuôn Cô Hường Trà Vinh đặc sản OCOP | MATCH | [facebook.com](https://www.facebook.com/banhtetcohuongtv/) | Feb 12, 2026 · Alo aloooo, Tết Đoan Ngọ sắp tới rồiiii, bánh Bá Trạng lên bàn nhe bà con ơi! 50 năm, dấu mốc tự hào dân tộc! Hãy cùng Bánh tét Cô Hườn |
| 80 | banh-tet-tu-quy-hai-ly | Bánh tét Tứ Quý Hai Lý Trà Vinh đặc sản OCOP | AMBIGUOUS | [khonggianthuonghieu.vinhlong.gov.vn](https://khonggianthuonghieu.vinhlong.gov.vn/vi/san-pham/banh-tet-tu-quy-hai-ly-p10142) | Tham gia OCOP, Bánh tét Tứ Quý Hai Lý không chỉ là món ăn mà còn là biểu tượng văn hóa ẩm thực địa phương, được chọn làm quà biếu Tết, lễ hội và dịp g |

Manual adjudication of automated `MISMATCH` rows (cumulative across Round 2 and Round 3):

| Entity ID | Manual verdict | Confidence | Finding | Source | Action |
| --- | --- | --- | --- | --- | --- |
| banh-cong-soc-trang | CONFIRMED_P0 | 95% | Area/origin DB gán Trà Vinh nhưng chính tên và nguồn ngoài đều chỉ Sóc Trăng. | [source](https://vnexpress.net/banh-cong-dac-san-cua-nguoi-khmer-o-soc-trang-4523101.html) | Keep quarantined as P0. |
| banh-trang-ngot-le-hang-htx-banh-trang-cu-lao-may | FALSE_POSITIVE | 90% | Nguồn ngoài xác nhận bánh tráng Cù Lao Mây/Lệ Hằng/OCOP ở Vĩnh Long; automated mismatch chỉ do classifier không bắt được area. | [source](https://dttc.sggp.org.vn/ron-rang-lang-banh-trang-cu-lao-may-tram-nam-tuoi-post131500.html) | Không nâng P0; cần thêm source độc lập vào entity. |
| can-cu-khu-uy-sai-gon-gia-dinh-tai-tan-phu-tay | FALSE_POSITIVE | 95% | Nguồn du lịch Bến Tre xác nhận căn cứ ở xã Tân Phú Tây, huyện Mỏ Cày Bắc, Bến Tre. | [source](https://bentretourism.vn/vi/cancukhuuysaigongiadinh) | Không nâng P0; thay source tự tham chiếu bằng nguồn ngoài. |
| cha-gio-chay | P1_SUSPECT | 65% | Search chỉ hỗ trợ món chả giò chay nói chung; chưa có nguồn đáng tin cho claim origin/where/price riêng tại Trà Vinh. | [source](https://www.huongnghiepaau.com/cha-gio-chay) | Giữ generic hoặc gỡ claim địa phương/giá cho đến khi có nguồn Trà Vinh. |
| cha-lua-thanh-cong | FALSE_POSITIVE | 85% | Nguồn Báo Vĩnh Long xác nhận cơ sở chả lụa Thành Công ở Hiếu Phụng, Vũng Liêm; top result Sóc Trăng là nhiễu. | [source](https://baovinhlong.com.vn/kinh-te/202501/don-xuan-cung-san-pham-ocop-0ef5d8d/) | Không nâng P0; cần bổ sung nguồn OCOP/source chính thức. |
| chien-thang-giong-dua-giong-trom | CONFIRMED_P0 | 95% | Nguồn ngoài đặt Chiến thắng Giồng Dứa ở Tiền Giang, còn DB vừa gán Bến Tre vừa mô tả nhầm mộ hợp chất Chợ Lách. | [source](https://tintucmientay.baoangiang.com.vn/tien-giang-chien-thang-giong-dua-lam-chan-dong-du-luan-trong-va-ngoai-nuoc-a361124.html) | Quarantine/remove khỏi catalog Bến Tre. |
| cho-cai-von | FALSE_POSITIVE | 90% | Snippet nhắc An Giang thời Nguyễn chỉ là ngữ cảnh lịch sử; nguồn vẫn xác nhận Cái Vồn hiện thuộc Vĩnh Long. | [source](https://vi.wikipedia.org/wiki/C%C3%A1i_V%E1%BB%93n) | Không nâng P0; nên đổi classifier để xử lý lịch sử hành chính. |
| chua-ong-met-botum-vong-sa-som-rong | CONFIRMED_P0 | 90% | DB gộp hai chùa: Chùa Ông Mẹt ở Trà Vinh và Bô Tum Vông Sa Som Rông/Som Rong ở Sóc Trăng/Cần Thơ mới. | [source](https://vietnamtourism.gov.vn/post/60568) | Quarantine; tách lại tên và architecture theo nguồn. |
| chua-sa-lon-chua-chen-kieu | CONFIRMED_P0 | 95% | Nguồn ngoài đặt Chùa Sà Lôn/Chén Kiểu ở Sóc Trăng/Cần Thơ mới, không phải legacy Trà Vinh. | [source](https://vi.wikipedia.org/wiki/Ch%C3%B9a_S%C3%A0_L%C3%B4n) | Keep quarantined as P0. |
| cuu-long-my-tuu-ruou-ocop-mang-thit | FALSE_POSITIVE | 85% | Báo Vĩnh Long xác nhận nhóm rượu Cửu Long Mỹ Tửu/Truyền thống Cửu Long ở TT Cái Nhum, Mang Thít. | [source](https://baovinhlong.com.vn/kinh-te/202401/cong-nhan-36-san-pham-ocop-dat-4-sao-3179449/) | Không nâng P0; bổ sung nguồn OCOP 4 sao nếu cần claim số sao. |
| di-tich-can-cu-khu-uy-sai-gon-gia-dinh | FALSE_POSITIVE | 95% | Nguồn du lịch Bến Tre xác nhận căn cứ Khu ủy Sài Gòn - Gia Định tại Tân Phú Tây, Bến Tre. | [source](https://bentretourism.vn/vi/cancukhuuysaigongiadinh) | Không nâng P0; thay source tự tham chiếu bằng nguồn ngoài. |
| dinh-cai-von | P1_SUSPECT | 70% | Nguồn chính thống thấy Đình Thần Mỹ Thuận tại Bình Minh; chưa xác nhận tên chính thức 'Đình Cái Vồn' và các claim thương cảng/kiến trúc Hoa kiều. | [source](https://svhttdl.vinhlong.gov.vn/xem-chi-tiet-tin-tuc/id/228793) | Human verify official name; gỡ claim không nguồn nếu không chứng minh được. |
| dua-hau-tan-hung-ocop | FALSE_POSITIVE | 90% | Nguồn Vĩnh Long xác nhận Tân Hưng/Bình Tân là vùng dưa hấu; automated mismatch do từ 'Bình Tân' trùng ngoài-area term TP.HCM. | [source](https://baovinhlong.com.vn/video/202402/nong-dan-binh-tan-thu-hoach-nuoc-rut-dua-hau-tet-3180243/) | Không nâng P0; classifier cần phân biệt huyện Bình Tân Vĩnh Long và quận Bình Tân TP.HCM. |
| khu-luu-niem-nu-anh-hung-nguyen-thi-ut-ut-tich | FALSE_POSITIVE | 95% | Nguồn tỉnh xác nhận Khu tưởng niệm Nguyễn Thị Út tại Tam Ngãi, Cầu Kè, Trà Vinh cũ; snippet 'Cần Thơ' là ngữ cảnh hành chính lịch sử. | [source](https://vinhlong.gov.vn/LinkClick.aspx?fileticket=IrTz6niTXLs%3D&mid=10814&portalid=0&tabid=63) | Không nâng P0; nên đổi địa chỉ từ huyện cũ nếu dùng tỉnh mới 2025. |
| khu-tuong-niem-nguyen-thi-ut-ut-tich | FALSE_POSITIVE | 95% | Nguồn tỉnh xác nhận cùng thực thể ở Tam Ngãi, Cầu Kè, Trà Vinh cũ; không phải area mismatch. | [source](https://vinhlong.gov.vn/LinkClick.aspx?fileticket=IrTz6niTXLs%3D&mid=10814&portalid=0&tabid=63) | Không nâng P0; kiểm tra trùng lặp với entity khu-lưu-niệm. |
| nguyen-van-ton-thach-duong | FALSE_POSITIVE | 90% | Cục Di sản xác nhận Nguyễn Văn Tồn/Thạch Duồng gắn với Trà Ôn, Cầu Kè và Lăng Ông Trà Ôn; snippet An Giang chỉ là một sự kiện khác. | [source](https://dsvh.gov.vn/le-hoi-lang-ong-tra-on-3264) | Không nâng P0; bổ sung source Tier 1/2. |
| rau-thom-ocop-hop-tac-xa-phuoc-hau | P1_SUSPECT | 80% | Nguồn Vĩnh Long xác nhận HTX Phước Hậu nhưng số liệu nguồn là 35 xã viên, 15 ha, trên 780 tấn/năm; DB ghi 15,5 ha và 850 tấn/năm. | [source](https://portal.vinhlong.gov.vn/portal/wpxttm/xttm/page/xemtin.cpx?item=60b9ce759332504c4746c3b7) | Review/update numeric claims; không coi là P0 vì số liệu có thể theo năm. |
| shop-luu-niem-ben-ninh-kieu-gian-hang-vinh-long-vinh-long | P1_SUSPECT | 85% | Tên entity chứa Bến Ninh Kiều (biểu tượng Cần Thơ) nhưng summary/address lại nói Cù lao An Bình, Vĩnh Long; chưa tìm thấy nguồn cho shop này. | [source](https://canthotourism.vn/vi/benninhkieu) | Quarantine P1 name/address conflict; cần human/Maps check tồn tại thật. |
| so-diep-binh-dai | P1_SUSPECT | 70% | Không tìm được nguồn Tier 1/2 xác nhận 'Sò điệp Bình Đại' là đặc sản; kết quả chủ yếu là generic/imported scallop hoặc social posts. | [source](https://vi.wikipedia.org/wiki/S%C3%B2_%C4%91i%E1%BB%87p) | Giữ suspect; cần nguồn thủy sản/địa phương trước khi publish claim đặc sản. |
| tuong-quan-nguyen-van-ton | FALSE_POSITIVE | 90% | Nguồn Cục Di sản xác nhận nhân vật Nguyễn Văn Tồn, năm 1763-1820 và Lăng Ông Trà Ôn; automated mismatch do snippet nhắc An Giang. | [source](https://dsvh.gov.vn/le-hoi-lang-ong-tra-on-3264) | Không nâng P0; bổ sung source Tier 1/2. |
| backpacker-mien-tay-3ngay-500k | P1_SUSPECT | 85% | Itinerary chứa nhiều giá, tuyến xe và mốc giờ không có source; top result ngoài An Giang chỉ cho thấy search không xác minh được itinerary này. | [source](https://tourmientay.vn/blogs/tour-ve-mien-tay-4-ngay-3-dem-2-ngay-dau-tai-an-giang-44) | Giữ UNTRUSTED; cần review route/cost từng chặng trước khi publish. |
| banh-mi-sau-hoa-ben-tre | P1_SUSPECT | 75% | Không tìm được nguồn độc lập cho quán Bánh mì Sáu Hoà Bến Tre; top result là Bánh mì Huynh Hoa TP.HCM, không liên quan. | [source](https://banhmihuynhhoa.vn/) | Human/Maps check tồn tại thật; gỡ claim 20+ năm, giờ mở cửa và giá nếu không có nguồn. |
| banh-trang-nem-cu-lao-may | FALSE_POSITIVE | 90% | Nguồn Báo Sài Gòn Giải Phóng xác nhận làng bánh tráng Cù Lao Mây và sản phẩm bánh tráng nem tại Vĩnh Long; classifier chỉ không nhận area. | [source](https://dttc.sggp.org.vn/ron-rang-lang-banh-trang-cu-lao-may-tram-nam-tuoi-post131500.html) | Không nâng P0; thêm source độc lập vào entity. |
| ben-xe-mien-tay-hcm | FALSE_POSITIVE | 95% | Bến xe Miền Tây đúng là ở TP.HCM và area=None; đây là node giao thông ngoài-scope dùng cho itinerary, không phải entity bị gán sai Vĩnh Long/Bến Tre/Trà Vinh. | [source](https://benxemiendong.com.vn/ben-xe-mien-tay/) | Giữ như external transport node hoặc tách taxonomy `external_gateway` để tránh bị tính là area mismatch. |
| bun-nuoc-leo-cho-ba-tri-ben-tre | P1_SUSPECT | 75% | Không có nguồn độc lập rõ cho quán bún nước lèo chợ Ba Tri; top result bị kéo sang bún nước lèo Sóc Trăng. | [source](https://cl.pinterest.com/pin/bn-nc-lo-mt-c-sn-quen-thuc-ca-cc-tnh-min-ty-nhng-vn-b-nhiu-ngi-lm-tng-l-bn-mm--886294401661397928/) | Human/Maps check; không publish giờ, giá, công suất/ngày nếu chưa xác minh. |
| chua-giac-linh | FALSE_POSITIVE | 90% | Nguồn du lịch sau sáp nhập hiển thị Chùa Giác Linh trong mục Trà Vinh và nêu quyết định di tích; domain Cần Thơ không phải bằng chứng sai area legacy. | [source](https://dulichcantho.vn/kham-pha-diem-den/tra-vinh/di-tich-chua-giac-linh-2171007.html) | Không nâng P0; vẫn cần thay LLM prose bằng claim có nguồn. |
| chua-khai-tuong | P1_SUSPECT | 85% | Top Tier 1 cho 'Chùa Khải Tường' là cổ tự Gia Định/TP.HCM; chưa có nguồn đáng tin xác nhận một Chùa Khải Tường nổi tiếng/di tích ở Ba Tri, Bến Tre. | [source](https://vi.wikipedia.org/wiki/Ch%C3%B9a_Kh%E1%BA%A3i_T%C6%B0%E1%BB%9Dng) | Quarantine P1; human verify thực thể cùng tên ở Ba Tri trước khi publish. |
| di-tich-duong-ho-chi-minh-tren-bien-ben-thanh-phong | FALSE_POSITIVE | 90% | Classifier bắt chữ 'Hồ Chí Minh' trong tên tuyến hậu cần, không phải TP.HCM; Bến Thạnh Phong là địa danh Bến Tre cần source địa phương bổ sung. | [source](https://vi.wikipedia.org/wiki/%C4%90%C6%B0%E1%BB%9Dng_H%E1%BB%93_Ch%C3%AD_Minh_tr%C3%AAn_bi%E1%BB%83n) | Không nâng P0; bổ sung nguồn Bến Tre/di tích cho địa điểm Bến Thạnh Phong. |
| homestay-con-ba-tu | FALSE_POSITIVE | 95% | Nguồn du lịch Bến Tre xác nhận Homestay Cồn Bà Tư; snippet nhắc TP.HCM chỉ là mô tả khoảng cách di chuyển. | [source](https://bentretourism.vn/vi/homestayconbatu2) | Không nâng P0; thay self-source bằng nguồn Bến Tre. |
| homestay-lang-be | FALSE_POSITIVE | 85% | DB đã có source vinhlong.gov.vn cho danh sách khách sạn/nhà nghỉ; top result localhome.vn là nhiễu search. | [source](https://vinhlong.gov.vn/du-khach/khach-san-nha-nghi) | Không nâng P0; cần kiểm tra lại xã An Khánh/Vĩnh Long theo mô hình hành chính mới. |
| hu-tieu-sa-dec-chu-tu-gan-cho-phu-hung-ben-tre | P1_SUSPECT | 80% | Không tìm được nguồn độc lập cho quán; top result nói về quán hủ tiếu ở Sa Đéc/Đồng Tháp. Tên 'Sa Đéc' có thể chỉ phong cách món, chưa đủ kết luận sai. | [source](https://dulichbinhphuoc.vn/13-quan-hu-tieu-sa-dec-ngon-ma-ban-nen-ghe/) | Human/Maps check tồn tại thật; gỡ claim giá/giờ/năm hoạt động nếu không có nguồn. |
| itinerary-tuan-trang-mat-mien-tay-4n3d | P1_SUSPECT | 85% | Itinerary có nhiều giá, resort, chi phí và giờ hoạt động không có source; top result Đà Nẵng là search noise, không xác minh được route. | [source](https://dulichdaiviet.com/tour-noi-dia/tour-du-lich-trang-mat-da-nang-4-ngay-3-dem-tu-ha-noi-tp-hcm.html) | Giữ UNTRUSTED; cần verify từng stop/price hoặc chuyển thành nội dung gợi ý không factual. |
| khoai-lang-binh-tan | P1_SUSPECT | 85% | Nguồn ngoài nói khoai lang Bình Tân đạt OCOP 4 sao, trong DB lại có cả `ocop='3 sao'` và `ocop_star=4`. | [source](https://tapchicongthuong.vn/magazine/emagazine--khoai-lang-binh-tan-but-pha-nho-ocop-317499.htm) | Review numeric/OCOP fields; chưa nâng P0 vì cần xác định sản phẩm/năm chứng nhận cụ thể. |
| khu-bao-ton-lung-binh-hoa-tra-vinh | CONFIRMED_P0 | 95% | DB entity Trà Vinh nhưng summary/description là Lung Ngọc Hoàng ở Hậu Giang/Cần Thơ mới; đây là content contamination rõ. | [source](https://vi.wikipedia.org/wiki/Khu_b%E1%BA%A3o_t%E1%BB%93n_thi%C3%AAn_nhi%C3%AAn_Lung_Ng%E1%BB%8Dc_Ho%C3%A0ng) | Quarantine/remove entity đến khi có nguồn xác nhận Lung Bình Hòa ở Trà Vinh. |
| p-tan-quoi | FALSE_POSITIVE | 90% | Snippet An Giang là lịch sử hành chính thế kỷ XIX; entity Phường Tân Quới hiện thuộc Vĩnh Long. | [source](https://vi.wikipedia.org/wiki/T%C3%A2n_Qu%E1%BB%9Bi) | Không nâng P0; classifier cần bỏ qua historic province context. |
| quan-thuan-phuc-vinh-long | P1_SUSPECT | 75% | Không tìm được nguồn độc lập cho Quán Thuận Phúc tại 135 Phạm Thái Bường; top result TikTok Kiên Giang không liên quan. | [source](https://www.tiktok.com/@phuc_vinh_thuan/video/7631125885692792085) | Human/Maps check; không publish giờ/giá/món nổi bật nếu chưa xác minh. |
| somo-farm-cuu-long | FALSE_POSITIVE | 90% | Nguồn chính của Somo Farm Cửu Long xác nhận thực thể; automated mismatch chỉ vì snippet không chứa area legacy. | [source](https://somofarmcuulong.somogroup.vn/) | Không nâng P0; cần bổ sung nguồn độc lập cho claim OCOP/star nếu publish. |
| tom-kho-binh-dai | P1_SUSPECT | 80% | Top result nói tôm khô Cà Mau; chưa có nguồn Tier 1/2 xác nhận Tôm khô Bình Đại/Anfoods OCOP như DB claim. | [source](https://sanphamocop.com.vn/dac-san-tet-cac-vung-mien-ma-ban-nen-biet-2/) | Giữ suspect; cần nguồn OCOP/địa phương trước khi publish claim Anfoods/OCOP 2023. |

### L. Entity Existence Verification
Entities with at least one web MATCH/AMBIGUOUS result: 1699. Entities with NOT_FOUND/ERROR need manual follow-up; see full log.

### M. Area Mismatch Report
Confirmed area/origin mismatches:

| entity_id | DB area | Real area/source fact | Action |
| --- | --- | --- | --- |
| hu-tieu-my-tho | vinh-long | Hủ tiếu Mỹ Tho là món do người Mỹ Tho chế biến; Mỹ Tho thuộc Tiền Giang cũ, ngoài 3 legacy areas. | Quarantine/remove from Vĩnh Long-specific dish catalog, or relabel as out-of-scope regional reference with origin='Mỹ Tho, Tiền Giang'. |
| banh-cong-soc-trang | tra-vinh | Nguồn báo chí mô tả bánh cống là đặc sản/nguyên gốc Sóc Trăng cũ. | Quarantine/remove from Trà Vinh-specific dish catalog unless there is a local Trà Vinh serving-place entity with separate evidence. |
| chua-sa-lon-chua-chen-kieu | tra-vinh | Chùa Sà Lôn/Chùa Chén Kiểu là chùa Khmer Nam tông ở khu vực Sóc Trăng cũ, nay thuộc Cần Thơ sau sáp nhập; không thuộc legacy Trà Vinh. | Quarantine/remove from Trà Vinh scope. Do not rewrite to another unsupported province without a scoped data model. |
| chien-thang-giong-dua-giong-trom | ben-tre | Nguồn báo chí địa phương mô tả Di tích lịch sử Chiến thắng Giồng Dứa là di tích cấp quốc gia của tỉnh Tiền Giang; nội dung mộ hợp chất Chợ Lách không khớp với tên entity. | Quarantine/remove khỏi Bến Tre scope. Không tự viết lại mô tả cho Tiền Giang nếu catalog chỉ phục vụ 3 legacy areas. |
| chua-ong-met-botum-vong-sa-som-rong | tra-vinh | Chùa Ông Mẹt ở Trà Vinh là chùa Khmer Nam tông, còn Bô Tum Vông Sa Som Rông/Som Rong là một chùa Khmer khác ở Sóc Trăng/Cần Thơ mới. | Quarantine entity để tách lại thành Chùa Ông Mẹt; bỏ cụm Som Rong và sửa phong cách kiến trúc chỉ sau khi có nguồn claim-level. |
| khu-bao-ton-lung-binh-hoa-tra-vinh | tra-vinh | Khu bảo tồn thiên nhiên Lung Ngọc Hoàng là một thực thể khác, nằm ở vùng Hậu Giang/Cần Thơ mới; nội dung hiện tại không chứng minh sự tồn tại của 'Lung Bình Hòa' tại Trà Vinh. | Quarantine/remove entity. Không sửa tên hoặc địa chỉ nếu chưa có nguồn độc lập xác nhận 'Lung Bình Hòa' ở Trà Vinh. |

Automated outside-area keyword hits are not automatically false; they are triage candidates listed in section 4.

### N. Cross-Reference Statistics
- Total entities web-searched: 1745 / 1745
- MATCH: 1505 (86.2%)
- MISMATCH: 27 (1.5%)
- AMBIGUOUS: 194 (11.1%)
- NOT_FOUND: 0 (0.0%)
- ERROR: 19 (1.1%)

Coverage by type:
| Type | Searches |
| --- | --- |
| product | 218 |
| attraction | 202 |
| restaurant | 191 |
| history | 188 |
| accommodation | 164 |
| nature | 125 |
| place | 125 |
| dish | 120 |
| experience | 92 |
| craft_village | 86 |
| event | 67 |
| facility | 58 |
| cafe | 56 |
| person | 35 |
| itinerary | 16 |
| organization | 1 |
| drink | 1 |

Coverage by area:
| Area | Searches |
| --- | --- |
| vinh-long | 709 |
| ben-tre | 549 |
| tra-vinh | 481 |
| None | 6 |

### Quality Gate Self-Check
| Gate | Check | Status |
| --- | --- | --- |
| QG1 | Web search cho 100% person + history | PASS |
| QG2 | Attraction có claim lịch sử được web-check | PARTIAL |
| QG3 | OCOP/product claims được web-check | PARTIAL |
| QG4 | Restaurant/cafe spot-check | PASS |
| QG5 | Mọi factual claim có Tier 1/2 source | FAIL |
| QG6 | Appendix K >= 200 search entries | PASS |
| QG7 | Automated MISMATCH rows manually adjudicated | PASS |
| QG13 | Mọi coordinates bbox-check | PASS |
| QG14 | Phone format + area-code format audit | PASS |
| QG16 | Trust score cho mọi entity | PASS |
| QG22 | Fix script runnable | PASS |

Hard forensic note: this report is intentionally stricter than the existing structural quality report. Structural validity does not equal factual truth.
