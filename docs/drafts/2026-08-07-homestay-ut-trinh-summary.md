> STATUS: active — BẢN NHÁP chờ chủ dự án duyệt. KHÔNG ghi vào `web/data.json`, KHÔNG chạy ETL.
> Ngày: 2026-08-07 · Skill: viet-content-optimizer (S+) · Entity: 1/1

# Nháp mô tả S+ — Homestay Út Trinh

### Homestay Út Trinh (`homestay-ut-trinh`, accommodation, vinh-long)

**Cũ (103 ký tự):** Nhà vườn 4 phòng trên cù lao An Bình — ngủ giữa vườn trái cây, chèo xuồng, ăn cơm nhà vườn với chủ nhà.

**Mới (397 ký tự):**

Giai đoạn 2017–2019, Homestay Út Trinh trên cù lao An Bình, Vĩnh Long là nơi duy nhất ở miền Nam đạt chuẩn ASEAN. Nhà chính là căn nhà cổ hơn trăm tuổi ở ấp Hòa Quý. Hai căn kế bên, Út Bình và Út Quỳnh, dựng năm 1953; cả cụm 14 phòng, tối đa 34 khách. Chủ nhà là bà Phạm Thị Ngọc Trinh, mở Mekong Travel năm 2005. Ban ngày hái trái, chèo xuồng bắt cá, đổ bánh xèo; tối có đờn ca tài tử và hát bội.

---

## Đọc kỹ tên entity (bước bắt buộc)

**"Út Trinh" là TÊN NGƯỜI, không phải địa danh.** "Út" là từ xưng hô Nam Bộ chỉ người con thứ út;
"Trinh" là tên chủ nhà — bà **Phạm Thị Ngọc Trinh**, được gọi thân mật là Út Trinh. Đây đúng là loại
bẫy mà skill cảnh báo (tiền lệ "cá lăng hơ"): nếu không tra, dễ viết thành một đặc điểm cảnh quan
hoặc một địa danh trên cù lao.

Hệ quả cho cách viết: mô tả phải có **con người** trong đó, và hai căn nhà phụ **Út Bình / Út Quỳnh**
cũng theo cùng lối đặt tên. Cả cụm homestay lân cận trên cù lao cũng vậy (Út Thủy, Sáu Thành, Năm
Thành, Ba Lình) — tên theo thứ bậc trong nhà, một nét bản địa có thật, không phải trùng hợp.

---

## Nguồn từng fact

| Fact | Nguồn | Mức |
|---|---|---|
| **Chuẩn ASEAN Homestay giai đoạn 2017–2019**, trao tại ATF 2017 | vinhlongtourist.vn (nguyên văn: "Homestay Út Trinh đã được Ban Tổ chức Diễn đàn Du lịch ASEAN (ATF) 2017, tặng giải thưởng ASEAN Homestay standard 2017 - 2019") + portal.vinhlong.gov.vn | ★★★★ × 2 |
| **Nơi duy nhất ở miền Nam** đạt chuẩn đợt đó (cả nước 3 điểm: Bắc/Trung/Nam) | portal.vinhlong.gov.vn — "toàn khu vực chỉ có ba điểm được công nhận" | ★★★★ ⚠ 1 nguồn |
| Trao tại **Singapore** | portal.vinhlong.gov.vn ("công nhận ... tại Singapore") | ★★★★ |
| **Ấp Hòa Quý**, xã Hòa Ninh, huyện Long Hồ (cũ) — trên **cù lao An Bình** | vinhlongtourist.vn (trang hồ sơ cơ sở) + uttrinhhomestay.com | ★★★★ + ★★★ |
| Cù lao nay thuộc **xã An Bình** (Hòa Ninh + Bình Hòa Phước + Đồng Phú + An Bình, từ 1/7/2025) | `attributes.merged_from` của `xa-an-binh` + NQ 1687/NQ-UBTVQH15 | ★★★★★ |
| **Nhà chính là nhà cổ hơn 100 năm tuổi** | portal.vinhlong.gov.vn — "ngôi nhà cổ hơn 100 năm tuổi (Út Trinh)" | ★★★★ |
| **Út Bình và Út Quỳnh dựng năm 1953** | portal.vinhlong.gov.vn — "hai ngôi nhà xây dựng năm 1953 (Út Bình, Út Quỳnh)" | ★★★★ |
| **14 phòng, tối đa 34 khách** | uttrinhhomestay.com (trang chính chủ, dữ liệu vận hành của chính cơ sở) | ★★★ |
| Chủ nhà **Phạm Thị Ngọc Trinh** | portal.vinhlong.gov.vn + vinhlongtourist.vn | ★★★★ × 2 |
| **Mekong Travel thành lập 2005** | vinhlongtourist.vn ("Hành trình giữ hồn miệt vườn của Út Trinh Homestay") | ★★★★ |
| Hoạt động: **hái trái, chèo xuồng, bắt cá, làm bánh** | vinhlongtourist.vn (nguyên văn: "Đạp xe, chèo xuồng, bắt cá, làm bánh...") + uttrinhhomestay.com | ★★★★ + ★★★ |
| **Đờn ca tài tử và hát bội** | vinhlongtourist.vn — "các đêm văn nghệ truyền thống như đờn ca tài tử, hát bội" | ★★★★ |

**Đã loại bỏ vì không đủ nguồn / mâu thuẫn:**
- **Giá phòng** — mâu thuẫn 3 chiều (xem Cảnh báo 1). Cố ý KHÔNG đưa số nào vào mô tả.
- **"4 phòng"** trong attributes — mâu thuẫn trực tiếp với trang chính chủ (14 phòng). Xem Cảnh báo 2.
- **Giải thưởng ASEAN 2023** — KHÔNG thuộc Út Trinh (xem Cảnh báo 4). Không gán.
- **Quê Bến Tre (cũ) của chủ nhà** — có nguồn ★★★★ nhưng cắt vì trần ký tự; giữ lại ở phần attributes.
- **"Từng làm hướng dẫn viên quốc tế"** — có nguồn ★★★★, cắt vì trần ký tự.
- **Số điện thoại** — không đưa vào mô tả (thuộc attributes), và số trong data hiện bị che.
- **Khoảng cách tới các điểm khác trên cù lao** — `coords_approximate=true` ở các entity lân cận,
  không đủ cơ sở để ghi "cách X km" (§ Bẫy khoảng cách/hướng bịa).

---

## Tự kiểm (3 bài test bắt buộc)

**Substitution** — Thay "Út Trinh" bằng homestay khác cùng cù lao (Phương Thảo, Ngọc Phượng, Ba Lình):
**sai ngay ở cả 5 câu.** Phương Thảo đạt chuẩn ASEAN đợt **2019–2021** chứ không phải 2017–2019; nhà
1953 và nhà cổ trăm tuổi là của riêng cụm này; 14 phòng/34 khách, Phạm Thị Ngọc Trinh, Mekong Travel
2005 đều không chuyển được sang cơ sở khác. **Đạt mạnh.**

**Deletion** — Xoá C1: mất danh hiệu + định vị + toàn bộ lý do đáng chú ý. Xoá C2: mất tuổi nhà chính,
tức mất điểm khác biệt lớn nhất so với homestay xây mới. Xoá C3: mất quy mô thật (người đọc không biết
đặt được mấy phòng) + mất niên đại hai căn phụ. Xoá C4: mất "ai là chủ" — mà đây là homestay, danh
tính chủ nhà chính là sản phẩm. Xoá C5: mất toàn bộ phần "làm gì ở đó". **Không câu nào là filler.**

**Curiosity** — Hook ở câu mở là một danh hiệu kiểm chứng được, không phải lời khen chung chung
("nơi duy nhất ở miền Nam" > "homestay nổi tiếng"). Chi tiết **hát bội** là thứ hiếm: hầu hết homestay
miệt vườn chỉ có đờn ca tài tử, nên nó tạo câu hỏi "sao chỗ này có hát bội?". Nhà cổ trăm tuổi + hai
căn 1953 cho người đọc hình dung được sẽ ngủ trong cái gì. **Đạt.**

**Gate kỹ thuật:** 397 ký tự (trần 400) · câu đầu 113 ký tự (trần 155, dùng làm meta description) ·
NFC chuẩn · nhịp câu 23–13–20–13–20 từ (xen dài–ngắn đều đặn) · không mở bằng tên entity đứng đầu câu ·
không từ sáo rỗng ("nổi tiếng/hấp dẫn/độc đáo/tuyệt vời") · không ẩn dụ sáo · không "miền Tây" ·
không nhắc "huyện" hay tên tỉnh cũ · không tự gán nhãn kiểm-chứng-thực-địa cho bất kỳ fact nào,
mỗi fact chỉ dẫn nguồn kèm hạng ★ của nguồn đó (§1.7) ·
keyword SEO "Homestay Út Trinh" + "cù lao An Bình" + "Vĩnh Long" nằm trọn trong câu đầu.

**Ghi chú Gate 4 (cross-reference):** mô tả chỉ liên kết được 1 entity (`xa-an-binh` qua "cù lao An
Bình") vì đã chạm trần 400 ký tự. Nếu chủ dự án muốn nối **narrative thread An Bình** sang nhà cổ,
thay câu 2 bằng: *"Nhà chính là căn nhà cổ hơn trăm tuổi ở ấp Hòa Quý, cùng cù lao với nhà cổ Cai
Cường."* → tổng thành **431 ký tự** (vượt trần 31 ký tự), cần đánh đổi bằng việc bỏ "mở Mekong Travel
năm 2005".

---

## Attributes đề xuất bổ sung / sửa

| Field | Giá trị đề xuất | Nguồn | Ghi chú |
|---|---|---|---|
| `rooms` | **14 phòng (tối đa 34 khách)** | uttrinhhomestay.com ★★★ | **SỬA GẤP** — hiện ghi "4 phòng", gần như chắc là rớt chữ số |
| `room_breakdown` | 1 phòng giường đôi (2 khách) · 1 phòng 2 giường đơn (2 khách) · 12 phòng giường đôi + giường đơn (3 khách) | uttrinhhomestay.com ★★★ | Cộng lại đúng 14 phòng / 34 khách — số tự khớp, tăng độ tin |
| `price` | **XOÁ** hoặc để "liên hệ" | — | Ba nguồn ba giá khác nhau (Cảnh báo 1). §1.4 cấm chốt đơn on-site nên không cần giá cứng |
| `price_range` | **XOÁ** (hiện "250.000–400.000đ/đêm") | — | Mâu thuẫn với `price` ngay trong cùng entity, và lệch xa nguồn ngoài |
| `phone` | **0919 002 505** | vinhlongtourist.vn ★★★★ ("0919.002505") + uttrinhhomestay.com ★★★ ("091 900 2505") | Thay `phone_note` "0270 385 xxxx" đang bị che, không dùng được |
| `email` | vinhlongmekongtravel@yahoo.com | vinhlongtourist.vn ★★★★ | |
| `address` | Ấp Hòa Quý, **xã An Bình**, tỉnh Vĩnh Long | ★★★★ (ấp) + NQ 1687 ★★★★★ (xã) | Hiện chỉ ghi "Xã An Bình, Vĩnh Long" — thêm được cấp ấp |
| `former_address` | Ấp Hòa Quý, xã Hòa Ninh, huyện Long Hồ (trước 7/2025) | ★★★★ | Địa chỉ kép cho ĐVHC sáp nhập |
| `award` | ASEAN Homestay Standard 2017–2019 (ATF 2017, Singapore) | ★★★★ × 2 | Danh hiệu có thời hạn — xem Cảnh báo 3 |
| `operator` | Mekong Travel (thành lập 2005) | ★★★★ | |
| `owner` | Phạm Thị Ngọc Trinh ("Út Trinh") | ★★★★ × 2 | Người còn sống — chỉ nêu thông tin nghề nghiệp công khai |
| `built` | Nhà chính hơn 100 năm tuổi; Út Bình & Út Quỳnh dựng 1953 | portal.vinhlong.gov.vn ★★★★ | |
| `package` | Ăn tối + phòng máy lạnh + ăn sáng | uttrinhhomestay.com ★★★ | Giải thích được vì sao giá/khách cao hơn giá phòng trần |
| `facilities` | giữ nguyên, thêm: wifi miễn phí, võng | ★★★★ | |
| `related_houses` | Út Bình, Út Quỳnh (cùng chủ, cùng khuôn viên) | ★★★★ | Cân nhắc tạo entity riêng hoặc gộp làm attribute |
| `verifiedAt` | **cân nhắc xoá** | — | Xem Cảnh báo 6 |

---

## Cảnh báo

1. **Giá mâu thuẫn 3 chiều — đã cố ý bỏ giá khỏi mô tả.**
   - `web/data.json`: `price` = "từ 350.000đ/đêm" **và** `price_range` = "250.000–400.000đ/đêm (bao ăn
     sáng)" — hai field đá nhau **ngay trong cùng một entity**.
   - vinhlongtourist.vn (★★★★): **800.000đ/khách**.
   - foody.vn (★★): **500.000–800.000đ/khách**.
   Lệch tới ~2–3 lần, và nhiều khả năng là lệch **đơn vị** (đ/đêm vs đ/khách, có kèm ăn tối + ăn sáng
   hay không). Nguồn duy nhất của data hiện tại là `"Seed lưu trú"` (★) → theo confidence gating là
   **loại bỏ**. Cần gọi 0919 002 505 xác nhận trước khi hiển thị bất kỳ con số nào.

2. **`rooms` = "4 phòng" gần như chắc chắn SAI.** Trang chính chủ ghi 14 phòng / tối đa 34 khách, kèm
   bảng phân loại phòng cộng lại đúng khớp. "4" là chuỗi con của "14" → nghi lỗi rớt ký tự lúc seed,
   không phải hai nguồn bất đồng. Đây là lỗi làm hỏng cả mô tả cũ ("Nhà vườn 4 phòng") lẫn `description`.

3. **Danh hiệu ASEAN có thời hạn.** Chuẩn ASEAN Homestay cấp theo kỳ 2 năm; kỳ của Út Trinh là
   **2017–2019** và **chưa tìm thấy nguồn nào ghi tái công nhận sau 2019**. Mô tả đã viết đúng thì quá
   khứ ("Giai đoạn 2017–2019 ... là nơi duy nhất") — **không được sửa thành thì hiện tại** ("hiện đạt
   chuẩn ASEAN") vì sẽ thành claim không có nguồn.

4. **KHÔNG gán giải ASEAN 2023 cho Út Trinh.** Giải tại ATF 2023 (Indonesia) trao cho **cụm 6 hộ ở An
   Bình**: Út Thủy, Sáu Thành, Năm Thành, Ba Lình, Ngọc Phượng, Ngọc Sang — **không có Út Trinh**
   (nguồn: nhandan.vn + vtr.org.vn + tinhdoan.vinhlong.gov.vn, ★★★★). Phương Thảo là kỳ 2019–2021.
   Rất dễ nhầm vì cả ba đều là "homestay An Bình đạt giải ASEAN".

5. **Nghi trùng lặp entity — 3 bản ghi cho cùng 1–2 cơ sở thật.**
   - `khu-du-lich-nha-xua-va-homestay-ut-trinh` (`placeId=p-long-ho`, coords **10.1834 / 105.9985**)
     mô tả đúng cơ sở này ("homestay Út Trinh trên cù lao An Bình") nhưng toạ độ **không nằm trên cù
     lao An Bình**, và nguồn chỉ là `agent discovery (cx/gpt-5.4)`. Nhiều khả năng là **bản ghi ảo do
     LLM sinh**, cần rà.
   - `homestay-ut-trinh-con-tam-hiep` có `phone` = **"09190020505"** (11 số) — chính là **0919002505**
     bị thừa một số. Trang chính chủ xác nhận cơ sở thứ hai ở **Tổ 9, ấp 1, xã Tam Hiệp, huyện Bình
     Đại (cũ)** → đây là **cùng một chủ**, không phải hai doanh nghiệp khác nhau. (Data ghi
     "xã Phú Thuận"; trang chính chủ ghi "xã Tam Hiệp" — cần đối chiếu sáp nhập.)
   Đề xuất: gộp hoặc gắn quan hệ `same_operator`, và **không để 3 entity cùng xuất hiện** trong kết
   quả tìm kiếm như 3 chỗ ở khác nhau.

6. **`verifiedAt` KHÔNG phải bằng chứng kiểm chứng thực địa.** Entity này có
   `verifiedAt = 2026-06-28T02:24:21Z` **trùng khít từng giây với `updatedAt`**, và toàn bộ các entity
   lân cận cũng có `verifiedAt` trùng `updatedAt` trong cùng phút → dấu hiệu **auto-fill hàng loạt**,
   không phải người đi kiểm. Theo §1.7, **không được dùng field này để claim "đã xác minh"**. Đề xuất
   xoá `verifiedAt` khỏi các entity auto-fill để field này giữ được ý nghĩa thật.

7. **Fact "3 điểm cả nước" chỉ có 1 nguồn ★★★★** (portal.vinhlong.gov.vn). Đủ ngưỡng theo confidence
   gating (≥1 nguồn ★★★+), nhưng mô tả đã diễn đạt ở mức an toàn hơn — "nơi duy nhất ở **miền Nam**"
   — thay vì khẳng định con số 3 của cả nước.

8. **`images=[]`.** Theo §1.5 chỉ dùng ảnh AI-gen qua `scripts/gen_image.py`, giữ nhãn minh hoạ
   `dc-nophoto-note`. Đặc biệt lưu ý với cơ sở lưu trú: ảnh AI **không được** trông như ảnh phòng thật,
   vì khách sẽ đặt kỳ vọng theo ảnh.

9. **`description` cũ cần sửa đồng bộ** — đang ghi "Nhà vườn 4 phòng" + "Giá từ 250.000–400.000
   đồng/đêm, bao ăn sáng", tức mang cả hai lỗi ở Cảnh báo 1 và 2.

---

## Nguồn đã dùng

- [Loại hình Homestay, thế mạnh và đặc trưng của du lịch huyện Long Hồ / "Đệ nhất homestay" (portal.vinhlong.gov.vn — Văn nghệ Cửu Long)](https://portal.vinhlong.gov.vn/portal/wpvannghecuulong/vannghecuulong/page/xemtin.cpx?uuid=65ae385e6e97bb344adeed71) — ★★★★ (nhà cổ >100 năm, Út Bình/Út Quỳnh 1953, chuẩn ASEAN 2017–2019 tại Singapore, 3 điểm cả nước)
- [Homestay huyện Long Hồ — niềm tự hào cho du lịch Vĩnh Long (vinhlongtourist.vn)](https://vinhlongtourist.vn/vi/detailnews/?t=homestay-huyen-long-ho-niem-tu-hao-cho-du-lich-vinh-long&id=news_11236) — ★★★★ (nguyên văn giải ASEAN Homestay standard 2017–2019 tại ATF 2017; danh sách các kỳ)
- [Hành trình giữ hồn miệt vườn của Út Trinh Homestay (vinhlongtourist.vn)](https://vinhlongtourist.vn/iv/detailnews/?t=hanh-trinh-giu-hon-miet-vuon-cua-ut-trinh-homestay&id=news_12295) — ★★★★ (Phạm Thị Ngọc Trinh, Mekong Travel 2005, đờn ca tài tử + hát bội)
- [Hồ sơ Út Trinh Homestay (vinhlongtourist.vn/en)](https://vinhlongtourist.vn/en/uttrinhhomestay) — ★★★★ (địa chỉ ấp Hòa Quý, điện thoại, email, giá 800.000đ/khách)
- [Trang chính chủ — uttrinhhomestay.com](https://uttrinhhomestay.com/homestay-ut-trinh-1) — ★★★ (14 phòng / 34 khách, phân loại phòng, gói ăn tối + máy lạnh + ăn sáng, cơ sở thứ hai ở Bình Đại)
- [Hấp dẫn homestay Vĩnh Long (Báo Nhân Dân)](https://nhandan.vn/hap-dan-homestay-vinh-long-post761561.html) — ★★★★ (cụm An Bình đạt giải ATF 2023 — dùng để **loại trừ**, không gán cho Út Trinh)
- [Cụm homestay An Bình đạt giải thưởng Du lịch ASEAN 2023 (Tạp chí Du lịch)](https://www.vtr.org.vn/cum-homestay-an-binh-dat-giai-thuong-du-lich-asean-2023.html) — ★★★ (danh sách 6 hộ đạt giải 2023)
- [Homestay Út Trinh đạt Giải thưởng du lịch ASEAN (dulichphuocthanhiv.com)](https://dulichphuocthanhiv.com/tin-tuc/homestay-ut-trinh-vinh-long-dat-giai-thuong-du-lich-asean/) — ★★ (chỉ dùng đối chiếu, mọi fact đều đã có nguồn ★★★★ độc lập)
- [Út Trinh Homestay (foody.vn)](https://www.foody.vn/vinh-long/ut-trinh-homestay) — ★★ (chỉ dùng để ghi nhận mâu thuẫn giá, không dùng làm căn cứ)
