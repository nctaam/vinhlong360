> STATUS: draft — bản nháp chờ chủ dự án duyệt. KHÔNG ghi vào `web/data.json`/DB.

### Xã Chợ Lách (`xa-cho-lach`, place, ben-tre)

**Cũ (110 ký tự):** Xã Chợ Lách thuộc huyện Chợ Lách, tỉnh Bến Tre, ra đời khi TT Chợ Lách, xã Hòa Nghĩa và xã Long Thới nhập lại.

**Mới (401 ký tự):**

Kẹp giữa sông Cổ Chiên và Hàm Luông, xã Chợ Lách của tỉnh Vĩnh Long sống bằng cây giống, hoa kiểng, sầu riêng, chôm chôm. Hoa Tết tính bằng triệu chậu; cúc mâm xôi đạt OCOP 3 sao. Xã ra đời 16/6/2025 từ thị trấn Chợ Lách và hai xã Long Thới, Hòa Nghĩa (Bến Tre cũ): 49,72 km², 15 ấp, hơn 44.000 dân. Kênh Chợ Lách hơn 10 km cắt ngang xã, nối Cổ Chiên với sông Tiền, rút gần 80 km đường thủy về TP.HCM.

**Nguồn từng fact:**

- "thuộc tỉnh Vĩnh Long" → NQ 202/2025/QH15 ngày 12/6/2025, dẫn qua Wikipedia "Chợ Lách (xã)" (★★★★★)
- "ra đời 16/6/2025 từ thị trấn Chợ Lách + Long Thới + Hòa Nghĩa" → NQ 1687/NQ-UBTVQH15, dẫn qua Wikipedia "Chợ Lách (xã)" (★★★★★); khớp `attributes.merged_from`
- "49,72 km²" → Công văn 2896/BNV-CQĐP ngày 27/5/2025, dẫn qua Wikipedia (★★★★★)
- "hơn 44.000 dân" (44.316 người, 31/12/2024) → Wikipedia "Chợ Lách (xã)" có dẫn nguồn (★★★★)
- "15 ấp" → Wikipedia "Chợ Lách (xã)" (★★★★)
- "kẹp giữa sông Cổ Chiên và Hàm Luông" → Wikipedia "Chợ Lách (xã)" + "Chợ Lách (huyện)" ("chiều ngang giới hạn bởi hai bờ của con sông Cổ Chiên và Hàm Luông") (★★★★)
- "sống bằng cây giống, hoa kiểng" (hơn 1.000 ha) → sggp.org.vn/vinh-long-xa-cho-lach-phan-dau-moi-nam-cung-ung-toi-thieu-4-trieu-cay-giong-post841067.html, 4/3/2026 (★★★)
- "sầu riêng, chôm chôm" (~2.500 ha cây ăn trái) → SGGP bài trên (★★★)
- "hoa Tết tính bằng triệu chậu" → baovinhlong.com.vn 25/10/2025: dự kiến ~2,5 triệu sản phẩm hoa kiểng vụ Tết 2026, ~4 triệu sản phẩm hoa kiểng + 5 triệu cây giống/năm (★★★) — trùng khớp SGGP (★★★)
- "cúc mâm xôi đạt OCOP 3 sao" → Báo Vĩnh Long 25/10/2025 + SGGP 4/3/2026, hai nguồn trùng (★★★ ×2)
- "kênh Chợ Lách hơn 10 km, nối Cổ Chiên với sông Tiền, rút gần 80 km" → plo.vn/kenh-cho-lach-se-duoc-nao-vet... 8/9/2024 (★★★)

**Tự kiểm:**

- **Substitution** — bản đầu chỉ có "kẹp giữa hai sông + làm cây giống hoa kiểng", thay tên "xã Vĩnh Thành" vào vẫn đúng → FAIL. Đã sửa bằng cách thêm 3 dữ kiện chỉ đúng xã này: mốc 16/6/2025 với đúng bộ ba đơn vị cũ, 49,72 km²/15 ấp, và kênh Chợ Lách. Thay tên xã khác vào là sai ngay 3 chỗ → đạt.
- **Deletion** — xoá thử từng câu: câu 1 mất định vị sông + ngành nghề; câu 2 mất OCOP + quy mô hoa Tết; câu 3 mất toàn bộ dữ liệu hành chính (chính là lỗi cần sửa); câu 4 mất chi tiết bất ngờ nhất. Không câu nào xoá được → không còn filler. Đã cắt bỏ trong lúc viết: một câu về "vương quốc cây giống hoa kiểng" (mỹ từ, đúng cho cả 4 xã Chợ Lách cũ) và cụm "miệt vườn trù phú".
- **Curiosity** (xã/phường: đọc xong có phân biệt được xã này với xã kia không?) — đạt: con kênh cắt tắt cho sà lan và con số hoa Tết là hai chi tiết người đọc chưa từng gắn với một cái tên xã. Ghi chú: 401 ký tự, nhỉnh 1 ký tự so với trần 400 của Gate 3.

**Attributes đề xuất bổ sung:**

- `area_km2: 49.72` — Công văn 2896/BNV-CQĐP 27/5/2025 (★★★★★)
- `population: 44316` + `population_as_of: "2024-12-31"` — Wikipedia "Chợ Lách (xã)" có dẫn nguồn (★★★★)
- `so_ap: 15` (An Phú, Bình An, Bình Thanh, Bình Sơn, Định Bình, Đại An, Hòa Nghĩa, Hòa Thạnh, Long Hòa, Long Hiệp, Long Quới, Long Thới, Sơn Qui, Quân An, Vinh Huê) — Wikipedia (★★★★)
- `established: "2025-06-16"` + `legal_basis: "NQ 1687/NQ-UBTVQH15"` (★★★★★)
- `former_province: "Bến Tre"` — để phân biệt với `former_district` đã có
- `ocop: ["Cúc mâm xôi Chợ Lách — 3 sao"]` (★★★ ×2)
- KHÔNG đề xuất: diện tích cây giống/hoa kiểng (nguồn vênh nhau 1.000 ha vs 1.500 ha), sản lượng cây giống/năm (vênh "trên 7 triệu" vs "tối thiểu 4 triệu"), và từ nguyên tên "Chợ Lách" (không truy được nguồn ≥★★).

**Cảnh báo:**

1. **Quan hệ sai địa bàn (quan trọng nhất).** Trong 24 quan hệ của entity có "chôm chôm Cái Mơn" và "cồn Phú Đa" — **cả hai đều KHÔNG nằm trong xã Chợ Lách mới**. Cái Mơn thuộc xã Vĩnh Thành cũ, cồn Phú Đa thuộc xã Vĩnh Bình cũ; xã mới chỉ gồm thị trấn Chợ Lách + Long Thới + Hòa Nghĩa. Vì vậy mô tả mới cố ý KHÔNG nhắc Cái Mơn dù đó là từ khóa mạnh nhất. Đề nghị rà lại tập quan hệ theo ranh giới xã mới, tránh gán nhầm đặc sản của xã láng giềng.
2. **Nguồn vênh số liệu hoa kiểng.** SGGP 4/3/2026 ghi "trên 7 triệu cây giống và khoảng 5 triệu sản phẩm hoa kiểng/năm"; Báo Vĩnh Long 25/10/2025 ghi "khoảng 4 triệu sản phẩm hoa kiểng, 5 triệu cây giống/năm"; Báo Đồng Khởi 19/8/2024 ghi mục tiêu 17–20 triệu cây giống/năm cho toàn huyện cũ. Đã cố ý viết "tính bằng triệu chậu" thay vì chốt một con số.
3. **Diện tích trồng trọt vênh:** SGGP "hơn 1.000 ha cây giống, hoa kiểng"; Báo Vĩnh Long "khoảng 1.500 ha/3.500 ha đất nông nghiệp". Đã bỏ khỏi mô tả.
4. **Ranh giới sông:** infobox Wikipedia xã liệt kê cả sông Mỹ Tho ở phía Tây Bắc. Mô tả mới chỉ giữ Cổ Chiên + Hàm Luông vì đó là cặp sông được hai trang Wikipedia (xã + huyện) nói trùng nhau; nếu cần chính xác hơn phải tra bản đồ ranh giới chính thức.
5. **Từ nguyên "lách" chưa xác minh.** Đã search theo quy tắc "đọc kỹ tên entity" (bẫy tên giống vs. cách gọi): không có nguồn ≥★★ khẳng định "lách" là tên cây (cỏ lách/sậy) hay biến âm của "lạch" (dòng nước nhỏ). Đã BỎ, không đưa vào mô tả.
6. **Dữ liệu entity có `verifiedAt: "2026-06-28T02:24:29Z"` trùng khít `updatedAt`** — nhiều khả năng là dấu vết ghi máy chứ không phải kiểm chứng thực địa. Theo §1.7, bản nháp này không chứa bất kỳ claim "đã xác minh/kiểm chứng" nào; đề nghị rà soát xem trường này có bị set nhầm hàng loạt không.
7. Mô tả cũ ghi `confidence: 0.91` trong khi nội dung sai định vị hành chính — nên hạ/đánh giá lại thang confidence cho các entity cùng lô.
