---
name: viet-content-optimizer
description: >
  Tối ưu nội dung tiếng Việt cho vinhlong360.vn — tầng S+. Nghiên cứu thích ứng
  (adaptive research), viết giọng miền Nam chuyên nghiệp, anti-hallucination cứng,
  SEO chuyên sâu, batch intelligence. LUÔN dùng skill này khi user muốn: viết/sửa
  mô tả cho xã, phường, điểm đến, món ăn, sản phẩm, lịch trình, sự kiện; cải
  thiện chất lượng nội dung hàng loạt; chuẩn hoá giọng văn; tối ưu SEO. Kể cả
  khi user chỉ nói "viết lại mô tả", "cập nhật nội dung", "làm content", "tối ưu
  SEO" — đều kích hoạt skill này.
---

# Vietnamese Content Optimizer S+ — vinhlong360.vn

Skill viết và tối ưu nội dung tiếng Việt tầng cao nhất cho MXH du lịch/OCOP/cộng
đồng Vĩnh Long mới (Vĩnh Long + Bến Tre + Trà Vinh).

**Triết lý S+:** Mỗi summary phải vượt qua 3 bài test:
1. **Substitution test** — thay tên entity bằng entity khác, summary còn đúng không?
   Nếu còn → quá chung chung, viết lại.
2. **Deletion test** — xoá từng câu, mất thông tin gì không? Câu không mất gì = filler, xoá.
3. **Craving test** (món ăn) / **Curiosity test** (địa điểm) — đọc xong có muốn
   thử/đến không? Nếu không → chưa đủ sống động.

---

## 0. Nghiên cứu thích ứng (Adaptive Research)

Thay vì nghiên cứu cố định (A: 3 search, B: 1), S+ dùng **adaptive loop**: đọc
entity → xác định knowledge gaps → target search vào đúng lỗ hổng → dừng khi đủ.

### Bước 1 — Đọc entity, xác định gaps

Đọc `attributes`, `merge_note`, `relationships`, `summary` hiện tại. Phân loại
thông tin thành 3 nhóm:

| Nhóm | Ví dụ | Hành động |
|---|---|---|
| **Có & tin được** | area_km2, population, merge_phases, coordinates | Dùng trực tiếp |
| **Có nhưng ngờ** | founding_year không rõ nguồn, heritage_level mập mờ | Red flag → verify |
| **Thiếu & cần** | Lịch sử, đặc trưng kinh tế, di tích, đặc sản vùng | Gap → target search |

### Bước 2 — Red flag detection

Dấu hiệu cần verify (KHÔNG tin mù):
- `founding_year` hoặc `built` không kèm source → search xác minh
- `heritage_level` ghi "cấp tỉnh"/"cấp quốc gia" → search nghị định/quyết định
- Tên entity chứa từ ambiguous (§ Đọc kỹ tên entity) → search nghĩa
- `summary` hiện tại dài >300 chars nhưng không có source → nghi scrape, verify facts
- Số liệu attributes mâu thuẫn (ví dụ area_km2 = 0.5 nhưng population = 50000)

### Bước 3 — Targeted search

Mỗi gap/red flag → 1 search query **cụ thể**. Không search chung chung.

**Cấu trúc query hiệu quả cho nội dung Việt:**
```
"{tên entity}" "{tên huyện/tỉnh}"           → định vị chính xác
"{tên entity}" lịch sử OR di tích OR thành lập  → lịch sử
"{tên entity}" đặc sản OR làng nghề OR OCOP     → kinh tế/sản phẩm
site:vi.wikipedia.org "{tên entity}"            → Wikipedia
site:*.gov.vn "{tên entity}"                    → nguồn chính thống
```

**Ưu tiên query theo loại entity:**
- Phường/xã: lịch sử hành chính + đặc trưng kinh tế + di tích
- Món ăn: nguyên liệu gốc + cách chế biến vùng + mùa vụ
- Điểm tham quan: năm xây + kiến trúc + ý nghĩa lịch sử
- Sản phẩm OCOP: quy trình + nguyên liệu + cấp sao + nơi mua

### Bước 4 — Source reliability matrix

| Độ tin cậy | Nguồn | Dùng cho |
|---|---|---|
| **★★★★★** | Nghị quyết UBTVQH, Sắc lệnh, Công báo | Hành chính, sáp nhập |
| **★★★★☆** | Wikipedia có dẫn nguồn, cổng TTĐT UBND tỉnh/huyện | Lịch sử, địa lý |
| **★★★☆☆** | Báo chính thống (Tuổi Trẻ, VnExpress, Thanh Niên, Dân Trí) | Sự kiện, nhân vật |
| **★★☆☆☆** | Blog du lịch, travel review | Trải nghiệm, ẩm thực (cần đối chiếu) |
| **★☆☆☆☆** | SEO farm, nội dung AI, trang tổng hợp không rõ nguồn | KHÔNG dùng |

**Quy tắc nguồn:**
- Fact dùng trong summary cần ≥1 nguồn ★★★+ hoặc ≥2 nguồn ★★ trùng khớp
- Fact chỉ có 1 nguồn ★★ → ghi nhưng đặt confidence thấp
- Fact chỉ có nguồn ★ → loại bỏ, không dùng
- Mâu thuẫn giữa nguồn: UBND/Công báo > Wikipedia > báo chí > blog

### Bước 5 — Dừng khi đủ

Nghiên cứu dừng khi: (a) mọi gap đã lấp, (b) mọi red flag đã verify, (c) thêm
search không ra thông tin mới. Không nghiên cứu thêm chỉ vì "chưa đủ lượng search".

**Với entity ít thông tin** (xã nhỏ, sản phẩm ít tiếng): 1-2 search không ra gì
mới = dừng, viết summary tối thiểu từ attributes. Ghi rõ cho user entity cần bổ
sung sau. KHÔNG bịa thông tin lấp chỗ trống.

---

## 1. Craft viết S+

### Bản sắc 3 vùng — chọn đúng, không trộn

**Vĩnh Long cũ** — miệt vườn sông nước:
- Sông Tiền, sông Cổ Chiên, sông Mang Thít, cù lao, rạch, kinh
- Đờn ca tài tử, nhà vườn, vườn trái cây bốn mùa, phà
- Giọng: trù phú, chậm rãi, hiền hoà

**Bến Tre** — xứ dừa, Đồng Khởi:
- Dừa xuyên suốt (ẩm thực, thủ công, cảnh quan), cồn (không gọi "cù lao")
- Sông Hàm Luông, sông Ba Lai, kẹo dừa, cồn Phụng/Lân/Quy/Long
- Giọng: tự hào truyền thống cách mạng nhưng không giáo điều

**Trà Vinh** — văn hoá Khmer đặc trưng:
- Chùa Khmer (thuật ngữ đúng: vihear, gopura, sala, stupa — KHÔNG tam quan)
- Ok Om Bok, Chol Chnam Thmay, Sene Đolta, giồng cát, rừng ngập mặn
- Giọng: tôn trọng đa văn hoá Kinh-Khmer-Hoa

**Vi phạm cứng:** viết chùa Khmer Trà Vinh bằng giọng "miệt vườn xứ dừa" = sai.

### Ngôn ngữ miền Nam — tự nhiên, không diễn

**Dùng** (khi đúng ngữ cảnh, không ép):
- Miệt vườn, xứ dừa, cù lao, bến phà, rạch, kinh, ấp, bưng, lung, giồng, vàm
- "Qua phà là tới", "dọc theo con kinh", "nằm cặp mé sông", "bao đời nay"
- Chan, dầm, kho quẹt, nước cốt dừa, lá chuối, cơm nóng canh chua

**Cấm tuyệt đối:**
- Giọng brochure: "Đến với X, du khách sẽ được thưởng thức..."
- Giọng Wikipedia: "X là một Y thuộc Z, có diện tích..."
- Từ sáo rỗng: nổi tiếng, thu hút, hấp dẫn, tuyệt vời, độc đáo, ấn tượng
- Ẩn dụ sáo: "trái tim của...", "viên ngọc ẩn", "thiên đường ẩm thực",
  "bức tranh sống động"
- Giọng Bắc trong ngữ cảnh Nam: "thưởng ngoạn", "du ngoạn", "trẩy hội",
  "phong cảnh hữu tình"

### 8 pattern mở bài

Câu mở tốt = **1 sự thật cụ thể + bất ngờ nhẹ**. Chọn pattern phù hợp với
entity và thông tin thực sự có:

| # | Pattern | Khi nào dùng | Ví dụ cốt lõi |
|---|---|---|---|
| 1 | **Thời gian neo** | Có năm/sự kiện lịch sử rõ ràng | "Từ năm 1846, khi ông Huỳnh Văn Sắc dựng ngôi đình đầu tiên..." |
| 2 | **Địa lý cảm giác** | Vị trí đặc biệt (cù lao, ven sông, giồng cát) | "Nằm giữa sông Tiền và sông Cổ Chiên..." |
| 3 | **Tên gọi kể chuyện** | Tên cũ/tên dân gian thú vị | "Dân Bến Tre gọi hồ này là Bờ Hồ — nơi..." |
| 4 | **Giác quan** | Món ăn, chợ, làng nghề | "Mùi dừa nướng thơm lừng từ đầu con hẻm..." |
| 5 | **Tương phản** | Entity có 2 mặt rõ rệt | "Ban ngày là phường hành chính sầm uất, chiều xuống..." |
| 6 | **Con số bất ngờ** | Có số liệu ấn tượng | "Chỉ 1 trong 5 trái trên buồng là dừa sáp — từ..." |
| 7 | **Hành động** | Trải nghiệm, lễ hội, làng nghề | "Mỗi rằm tháng 10, mặt nước Ao Bà Om lấp lánh..." |
| 8 | **Sáp nhập kể** | Xã/phường sáp nhập đáng kể | "Ba đợt sáp nhập trong 5 năm biến..." |

**Quy tắc chọn:** ưu tiên 1→4 nếu có dữ liệu. Pattern 5-8 khi phù hợp. Không
dùng cùng pattern cho >2 entity liên tiếp trong batch. Không bao giờ mở bằng tên
entity đứng đầu câu hoặc "X là một..."

### Sentence rhythm — nhịp viết

Summary hay = **xen kẽ câu ngắn (≤15 từ) và câu dài (20-35 từ)**. Không viết
toàn câu cùng độ dài.

```
[DÀI] Nơi đặt tỉnh lỵ Trúc Giang của tỉnh Kiến Hòa, phường An Hội vẫn
      là trung tâm hành chính và thương mại TP Bến Tre.
[NGẮN] Ba đợt sáp nhập từ 2020 đến 2025 gộp tám đơn vị cũ.
[DÀI] Quanh Hồ Trúc Giang — đào từ thập niên 1930, dân gọi Bờ Hồ — là
      Đình An Hội gỗ mộng từ giữa thế kỷ 19 và chợ Bến Tre trăm tuổi.
[NGẮN] Phần mở rộng phía đông vẫn giữ nét miệt vườn xứ dừa.
```

### "Chỉ entity này" test

Đọc lại mỗi câu trong summary và hỏi: **"Câu này có thể đúng cho entity nào
khác không?"** Nếu đúng cho nhiều entity → câu đó quá chung, cần chi tiết hoá.

- "Vùng đất giàu truyền thống" → đúng cho 100+ xã → **filler, xoá**
- "Đào từ thập niên 1930, dân gọi Bờ Hồ" → chỉ đúng Hồ Trúc Giang → **giữ**
- "Hình thành từ sáp nhập nhiều xã" → đúng cho 80+ xã → **thêm tên cụ thể**

### Đọc kỹ tên entity

Tên thường mã hoá thông tin. KHÔNG giả định nghĩa — WebSearch xác minh:

- **Bẫy tên giống vs chế biến**: "cá lăng hơ" → "hơ" là tên giống cá, KHÔNG phải
  bước hơ lửa. Quy tắc: từ có thể là chế biến HOẶC tên giống → search trước.
- **Nguyên liệu**: "dừa sáp" → cùi đặc sánh; "nếp than" → nếp đen
- **Địa danh trong tên**: "bún nước lèo Trà Vinh" → phải nhắc Trà Vinh
- **Danh hiệu**: OCOP 5 sao cho "dừa sáp sợi" ≠ OCOP 5 sao cho "sinh tố dừa sáp"

### Ngữ pháp siết chặt

- Mỗi câu phải có chủ ngữ rõ (trừ liệt kê)
- Không lặp từ/cụm từ >2 lần cùng đoạn. Không lặp nghĩa.
- Cấu trúc câu đa dạng: xen ngắn-dài (§ Sentence rhythm)
- Số liệu xen tự nhiên: "rộng gần 32 km²" thay vì "Diện tích: 31,9 km²"
- Dấu tiếng Việt NFC chuẩn (hoà → hòa, khoá → khóa)
- Dấu gạch ngang em (—) cho thông tin phụ chêm vào

### Bẫy phổ biến

1. **Tên entity trùng tên huyện** (Cầu Ngang, Tam Bình...): bỏ "huyện X" ở câu
   đầu (breadcrumb đã cho thấy), hoặc viết "huyện cùng tên". Tên ≤2 lần/đoạn.

2. **Sai hướng sáp nhập**: P.1+2+3 gộp **tạo thành** An Hội (entity mới), không
   phải An Hội "gộp từ". Đọc `merge_phases` để biết entity tồn tại trước hay mới.

3. **Sai thời kỳ lịch sử**: Pháp thuộc (<1945), VNCH (1955-75: Kiến Hòa=BT,
   Vĩnh Bình=TV, Phước Long=một phần VL), sau 1975 (tên hiện tại). Ghi rõ năm,
   không ghi "từ xưa" mà không có năm.

4. **Thuật ngữ Khmer đúng cho chùa Khmer**: gopura (cổng), vihear (chánh điện),
   sala (nhà hội), stupa (tháp cốt). KHÔNG dùng "tam quan" (chùa Việt).

5. **Câu filler**: bỏ câu đi, summary không mất thông tin → xoá. Mỗi câu phải
   chứa ≥1 fact cụ thể (số liệu, tên riêng, đặc điểm chỉ đúng entity này).

6. **Khoảng cách/hướng bịa**: "cách trung tâm X km", "phía đông huyện Y" — chỉ
   dùng khi có coordinates/boundaries hoặc WebSearch xác nhận.

---

## 2. Anti-Hallucination Protocol

### Source audit (BẮT BUỘC sau khi viết)

Sau khi viết summary, **duyệt từng fact** và ghi nguồn:

```
Fact: "tỉnh lỵ Trúc Giang thời Kiến Hòa (1956–1975)"
→ Nguồn: Wikipedia TP Bến Tre + Sắc lệnh 143-NV (★★★★)

Fact: "Hồ Trúc Giang đào thập niên 1930"
→ Nguồn: top9.com.vn + bazantravel.com (★★☆ × 2 = đủ)

Fact: "Đình An Hội gỗ mộng từ giữa thế kỷ 19"
→ Nguồn: mia.vn (★★☆) — single source, cần lưu ý
```

Fact không truy xuất được nguồn → **xoá khỏi summary**. Không giữ.

### Confidence gating

| Mức | Điều kiện | Cho phép |
|---|---|---|
| **Dùng** | ≥1 nguồn ★★★+ hoặc ≥2 nguồn ★★ trùng khớp | Ghi vào summary |
| **Dùng cẩn thận** | 1 nguồn ★★ duy nhất | Ghi nhưng tránh ghi quá chính xác (làm tròn số, dùng "khoảng") |
| **Loại bỏ** | Chỉ có nguồn ★ hoặc không có nguồn | Không ghi, dù "biết" |

### 3 bài test bắt buộc

Chạy sau khi viết xong, trước khi trả output:

**Test 1 — Substitution:** Thay tên entity bằng entity cùng loại (xã khác, món khác).
Summary vẫn đúng? → Quá chung chung. Thêm chi tiết chỉ đúng entity này.

**Test 2 — Deletion:** Xoá từng câu. Câu nào xoá mà summary không mất thông tin
cụ thể → câu đó là filler, xoá thật.

**Test 3 — Craving/Curiosity:** Đọc như người dùng lần đầu.
- Món ăn: đọc xong có thèm không? Không → thiếu giác quan, thêm mùi/vị/hình.
- Địa điểm: đọc xong có tò mò muốn đến không? Không → thiếu hook, thêm chi tiết bất ngờ.
- Xã/phường: đọc xong có biết xã này khác xã kia chỗ nào không? Không → quá chung.

### Xử lý mâu thuẫn attributes vs nghiên cứu

Khi WebSearch trả thông tin khác attributes:
1. Xác định nguồn nào đáng tin hơn (★ matrix)
2. Ưu tiên nguồn cao hơn trong summary
3. **Báo user** sự khác biệt để sửa data: "Note: attributes ghi founding_year 1842
   nhưng Wikipedia dẫn nguồn Đại Nam nhất thống chí ghi 1677 — đề xuất sửa data."

---

## 3. SEO Mastery

### Câu đầu = meta description

Câu đầu tiên (≤155 ký tự) dùng trực tiếp làm `<meta description>` trên Google.
Phải: chứa keyword chính, đọc tự nhiên, gợi click.

### Keyword strategy theo loại entity

| Loại | Keyword chính | Ví dụ user search |
|---|---|---|
| Xã/phường BT | tên + "Bến Tre" | "phường An Hội Bến Tre" |
| Xã/phường TV | tên + "Trà Vinh" | "xã Cầu Ngang Trà Vinh" |
| Xã/phường VL | tên + "Vĩnh Long" | "cù lao An Bình Vĩnh Long" |
| Chùa Khmer | tên chùa + "Trà Vinh" | "chùa Âng Trà Vinh" |
| Món ăn | tên món + vùng gốc | "bún nước lèo Trà Vinh" |
| OCOP | tên SP + vùng | "dừa sáp Bến Tre" |
| Di tích | tên + tỉnh | "văn miếu Vĩnh Long" |

### Vietnamese search patterns

Người Việt search cả có dấu và không dấu. Câu đầu summary phải chứa keyword
**có dấu đúng** (Google match tốt hơn). Tránh viết tắt trong câu đầu (TP → thành
phố, TX → thị xã, H. → huyện) — Google snippet hiển thị đầy đủ hơn.

### Featured snippet targeting

Google trích câu trả lời trực tiếp cho query dạng "X là gì", "X ở đâu". Câu đầu
summary nên **trả lời ngầm** câu hỏi phổ biến nhất về entity:

- Phường/xã: "ở đâu + đặc điểm gì" → câu đầu có vị trí + điểm nổi bật
- Món ăn: "là gì + ở đâu" → câu đầu có mô tả ngắn + vùng
- Di tích: "ở đâu + có gì" → câu đầu có vị trí + ý nghĩa

### Internal linking hints

Khi nhắc entity liên quan trong summary, chọn entity có trang trên website. Frontend
sẽ auto-link tên entity. Ưu tiên nhắc 2-3 entity nổi bật nhất trong relationships.

---

## 4. Hướng dẫn theo loại entity

### Phường / Xã (type: place)

**Cấu trúc:** câu mở SEO (≤155 chars) → sáp nhập tự nhiên → diện tích/dân số →
đặc trưng (kinh tế, di tích, đặc sản) → 200-400 chars.

**Quy tắc riêng:**
- merge_note → diễn giải tự nhiên, không copy format "A+B+C→D"
- 16 phường mới (có `phuong_upgrade`) → nhắc việc lên phường
- Phường Vũng Liêm: ghi rõ tên cũ Trung Thành
- Địa chỉ kép: tên mới + (tên cũ) cho ĐVHC sáp nhập
- Dùng "tỉnh Vĩnh Long" (không tỉnh cũ) cho context hành chính hiện tại

**Entity ít thông tin (tầng C):** summary tối thiểu 100-150 chars từ attributes +
merge_note + vị trí. Dùng vị trí sông/huyện, kinh tế vùng (nếu chắc chắn).
Báo user cần bổ sung. Confidence ≤0.5.

### Món ăn / Đặc sản (type: dish)

**Cấu trúc:** câu mở giác quan → nguyên liệu + chế biến đặc trưng → nơi ăn/mùa
ngon → 150-300 chars.

**Giọng:** gợi hình, gợi vị — người đọc phải thèm. Dùng từ ẩm thực miền Nam:
chan, dầm, kho quẹt, nước cốt dừa, lá chuối. Phải pass Craving test.

**Cảnh báo:** Đọc kỹ tên → search nghĩa trước khi viết chế biến (§ Đọc kỹ tên).

### Điểm tham quan (type: attraction, nature, history)

**Cấu trúc:** câu mở gợi cảm xúc + vị trí → lịch sử/ý nghĩa → trải nghiệm →
giờ mở cửa/giá vé (nếu có) → 200-350 chars.

**Quy tắc:** Địa chỉ kép cho ĐVHC sáp nhập. Phải pass Curiosity test.

### Sản phẩm / Nghề truyền thống (type: product, craft_village)

**Cấu trúc:** sản phẩm + vùng + điểm đặc biệt → quy trình/nguyên liệu → nơi
mua + OCOP (nếu có) → 150-300 chars.

### Sự kiện / Lễ hội (type: event)

Gợi không khí, âm thanh, hình ảnh. Thời gian từ `best_time`. Ý nghĩa văn hoá.
Giọng sống động. Thuật ngữ Khmer đúng cho lễ hội Khmer.

### Lịch trình (type: itinerary)

Đối tượng + thời gian + highlight → điểm chính theo thứ tự → ngân sách ước tính.
200-400 chars.

---

## 5. Batch Intelligence

Khi xử lý ≥5 entity cùng lúc, kích hoạt hệ thống chống đơn điệu:

### Cross-entity coherence

- Trước khi viết, đọc summary của **siblings** (cùng huyện/cùng loại) đã có
- Không lặp cùng opening pattern, cùng cấu trúc, cùng fact vùng cho 2 siblings
- Entity cùng huyện dùng đặc trưng huyện khác nhau (xã ven sông vs xã nội đồng)

### Vocabulary budget

Theo dõi từ khoá xuyên batch:

| Từ/cụm | Ngưỡng cảnh báo | Cách xử lý |
|---|---|---|
| "sáp nhập" | >60% summary | Đổi: "gộp", "hợp nhất", "ra đời khi...nhập lại" |
| "hình thành từ" | >40% summary | Đổi: "ra đời", "gộp từ", "tách ra từ" |
| "nằm ở" | >50% summary | Đổi: "toạ lạc", "trải dọc", "cặp mé", bỏ qua vị trí ở câu mở |
| Tên huyện | >3 lần/summary (khi trùng tên xã) | Viết "huyện cùng tên" |

### Diversity scoring

Sau mỗi 10 summary, đọc lại 10 câu mở. Đánh giá:
- ≤2 câu cùng pattern → ✅
- 3 câu cùng pattern → ⚠️ viết lại 1
- ≥4 câu cùng pattern → ❌ viết lại tất cả câu trùng

### Narrative threads

Entity cùng vùng nên tạo "sợi dây" kết nối:
- Sông Hàm Luông nối nhiều phường Bến Tre
- Sông Mang Thít nối nhiều xã Tam Bình/Mang Thít
- "Giồng cát" nối nhiều xã Trà Vinh
- Dừa xuyên suốt Bến Tre

Nhắc sợi dây tự nhiên trong summary — tạo cảm giác khám phá chuỗi, không phải
đọc từng entry cô lập.

---

## 6. Quy trình xử lý

### Viết mới / Cải thiện — cùng quy trình

**Phase 1 — Research:**
1. Đọc entity data (attributes, merge_note, relationships, summary hiện tại)
2. Đọc kỹ tên entity → xác định ambiguous terms
3. Xác định vùng → chọn giọng + bản sắc
4. Xác định keyword SEO (§3)
5. Adaptive research loop (§0): gaps → search → verify → dừng khi đủ
6. Đọc relationships → chọn 2-3 entity cross-reference

**Phase 2 — Write:**
7. Chọn opening pattern (§1) phù hợp thông tin có
8. Viết summary: câu mở SEO → thân → kết
9. Kiểm tra sentence rhythm (ngắn-dài xen kẽ)

**Phase 3 — Verify (BẮT BUỘC, không bỏ):**
10. Source audit: mỗi fact → nguồn cụ thể. Fact không có nguồn → xoá.
11. Substitution test: thay tên → vẫn đúng → quá chung → chi tiết hoá
12. Deletion test: xoá từng câu → không mất gì → filler → xoá
13. Craving/Curiosity test: đọc như user → có muốn thử/đến/biết thêm?
14. Checklist (§7)
15. Nếu fail bất kỳ test → sửa → chạy lại từ bước 10

### Xử lý hàng loạt

1. Backup: `python scripts/backup_data.py`
2. Phân nhóm: chia theo huyện/vùng (để dùng narrative threads)
3. Adaptive research theo nhóm: entity ít thông tin dùng attributes, entity quan
   trọng search sâu
4. Viết + verify mỗi entity
5. Diversity scoring mỗi 10 entity → sửa nếu cần
6. Sync: `python scripts/normalize_data.py --no-backup`

---

## 7. Quality Gates — Checklist cuối

### Gate 1: Factual accuracy
- [ ] Mọi fact có nguồn ≥★★ (source audit passed)
- [ ] Confidence gating applied
- [ ] Tên entity đã đọc kỹ, nghĩa xác minh qua search
- [ ] Danh hiệu (OCOP, di tích...) gán đúng entity
- [ ] merge_note diễn giải đúng hướng (tạo thành vs mở rộng)
- [ ] Số liệu khớp attributes (hoặc ghi chú mâu thuẫn)
- [ ] Không có fact bịa đặt

### Gate 2: Linguistic quality
- [ ] Giọng miền Nam tự nhiên, đúng bản sắc vùng
- [ ] Không từ sáo rỗng, không ẩn dụ sáo, không giọng brochure/Wikipedia
- [ ] Sentence rhythm: xen ngắn-dài
- [ ] Chủ ngữ rõ, không lặp từ/ý, cấu trúc đa dạng
- [ ] Dấu tiếng Việt NFC chuẩn
- [ ] Không copy câu/cụm từ từ ví dụ skill

### Gate 3: SEO compliance
- [ ] Câu đầu ≤155 chars, chứa keyword chính (tên + vùng)
- [ ] Tổng 150-400 chars (tầng C: 100-150)
- [ ] Không mở bằng tên entity đứng đầu / "X là một..."
- [ ] Keyword tự nhiên, không nhồi
- [ ] Địa danh mức cụ thể nhất có thể

### Gate 4: Emotional resonance
- [ ] Substitution test passed (không quá chung)
- [ ] Deletion test passed (không filler)
- [ ] Craving/Curiosity test passed
- [ ] Cross-reference 2-3 entity liên quan (nếu có relationships)
- [ ] Đọc như user lần đầu: tự nhiên, muốn biết thêm

### Batch bonus gates (≥5 entity)
- [ ] Diversity scoring ≤2 câu cùng pattern / 10 entity
- [ ] Vocabulary budget trong ngưỡng
- [ ] Narrative threads tự nhiên (nếu cùng vùng)

---

## 8. Bản quyền nội dung (§B6 CLAUDE.md)

- KHÔNG copy nguyên văn từ bất kỳ nguồn nào. Tổng hợp rồi viết lại bằng giọng
  riêng website.
- Trích dẫn trực tiếp chỉ cho tên riêng, thuật ngữ, danh hiệu chính thức.
- Ảnh: không nhúng/hotlink từ nguồn khác. Chỉ dùng ảnh trong hệ thống hoặc
  nguồn cấp phép (Wikimedia/Pexels/Unsplash).
