# Lô 10 entity mẫu — viết lại summary (2026-08-07)

> STATUS: draft — chờ chủ dự án duyệt

## 0. Đây là cái gì

Mười entity được viết lại summary theo skill `viet-content-optimizer` (adaptive research →
source reliability matrix ★ → 3 bài test Substitution / Deletion / Craving-Curiosity → 4 quality gate).
Mục đích của lô này **không phải** để ghi vào dữ liệu, mà để chủ dự án **duyệt chất lượng TRƯỚC khi
quyết quy mô** (có nên chạy tiếp 150 entity hay không, và chạy theo luồng nào).

Trạng thái dữ liệu, nói rõ để khỏi hiểu nhầm:

- **CHƯA ghi gì vào `web/data.json`.** Không chạy ETL, không đụng SQLite/Postgres (§B1, §B7).
- **CHƯA git add/commit/push.** File này là văn bản, không phải thay đổi dữ liệu.
- Mọi đề xuất `attributes` bên dưới là **đề xuất**, chưa áp dụng ở đâu cả.
- Không bản nào tự gán nhãn kiểm-chứng-thực-địa (§1.7): mỗi fact chỉ nêu nguồn và hạng ★ của nguồn
  đó, độ tin cậy do người đọc tự đánh giá theo thang ★. `attributes.verifiedAt` xuất hiện
  trong dữ liệu **không phải** bằng chứng kiểm chứng thực địa — xem §3, mục A.

Quy ước đọc: thang ★ theo bảng "Source reliability matrix" của skill —
★★★★★ nghị quyết/công báo · ★★★★ Wikipedia có dẫn nguồn, cổng TTĐT nhà nước ·
★★★ báo chính thống · ★★ blog/review (cần ≥2 nguồn trùng) · ★ SEO farm (không dùng).

Cột "vùng" trong bảng dưới là **trường `area` cũ trong `web/data.json`** (`vinh-long` / `ben-tre` /
`tra-vinh`) — giữ để tra cứu dữ liệu, KHÔNG phải đơn vị hành chính. Về hành chính chỉ có **một tỉnh
Vĩnh Long** từ 1/7/2025 (§1.6).

---

## 1. Bảng tổng

| # | Entity | id | type | vùng (`area`) | ký tự cũ → mới | Cảnh báo |
|---|---|---|---|---|---|---|
| 1 | Nhà cổ Cai Cường | `nha-co-cai-cuong` | attraction | vinh-long | 87 → 400 | 7 mục — có lỗi `placeId` sai địa bàn |
| 2 | Cồn Phụng (Cồn Ông Đạo Dừa) | `con-phung-con-ong-dao-dua` | attraction | ben-tre | 149 → 397 | 6 mục — toạ độ nghi sai ~10 km, năm sinh Ông Đạo Dừa chỏi 3 nguồn |
| 3 | Bún suông | `bun-suong` | dish | tra-vinh | 78 → 398 | 7 mục — `placeId` sai, trùng lặp entity |
| 4 | Dừa sáp Cầu Kè | `dua-sap-cau-ke` | product | tra-vinh | 168 → 400 | 8 mục — `area_ha` lỗi thời, nguồn gốc giống mâu thuẫn |
| 5 | Chùa Âng (Angkorajaborey) | `chua-ang-wat-angkor-raig-borei` | history | tra-vinh | 83 → 398 | 8 mục — 4 bản ghi trùng + mốc 990 không sử liệu |
| 6 | Khu di tích Nguyễn Đình Chiểu | `khu-di-tich-nguyen-dinh-chieu` | history | ben-tre | 167 → 400 | 6 mục — `architectural_style` sai sự thật |
| 7 | Homestay Út Trinh | `homestay-ut-trinh` | accommodation | vinh-long | 103 → 397 | 8 mục — `rooms` sai (4 vs 14), giá mâu thuẫn 3 chiều |
| 8 | Làng gạch gốm đỏ Mang Thít | `lang-gach-gom-do-mang-thit` | craft_village | vinh-long | 82 → 394 | 7 mục — toạ độ mâu thuẫn, `verifiedAt` auto-stamp |
| 9 | Xã An Bình | `xa-an-binh` | place | vinh-long | 116 → **411** | 6 mục — vượt trần 400 ký tự, `placeId` sai |
| 10 | Xã Chợ Lách | `xa-cho-lach` | place | ben-tre | 110 → **401** | 7 mục — quan hệ sai địa bàn, vượt trần 1 ký tự |

**Số đo lô:** cũ tổng 1.143 ký tự (TB 114,3) → mới tổng 3.996 ký tự (TB 399,6), gấp **3,5 lần**.
10/10 entity có ít nhất 1 cảnh báo. 10/10 có đề xuất sửa `attributes`. 2/10 vượt trần 400 ký tự
(#9 = 411, #10 = 401). Tổng cảnh báo đếm được **70 mục** — bốn danh sách từng bị cắt cụt ở bản gộp
đầu tiên (bản 2, 4, 7, 8) đã được khôi phục đủ từ journal của workflow sinh ra chúng.

---

## 2. Mười bản viết

### 2.1 — Nhà cổ Cai Cường (`nha-co-cai-cuong`, attraction, vinh-long)

> Ghi chú phiên của agent viết bản này: `web/data.json` unchanged, nothing staged.
> Bản gốc: `docs/drafts/2026-08-07-nha-co-cai-cuong-summary.md`

**Cũ (87 ký tự):** Nhà cổ tọa lạc trên cù lao An Bình, tỉnh Vĩnh Long, mang kiến trúc truyền thống Nam Bộ.

**Mới (400 ký tự):**
Chữ "Cai" trong tên nhà cổ Cai Cường không phải địa danh — đó là chức cai tổng của ông Phạm Văn Bổn, người dựng cơ ngơi bên rạch Cái Muối, cù lao An Bình. Cất năm Ất Dậu 1885, hai nếp vuông góc ghép thành chữ Đinh, cột gỗ cao 6m. Nền gạch bông Pháp, bao lam chạm rồng phượng thếp vàng, hoành phi "Phạm Phủ Đường": ruột Việt, vỏ Tây, lối "nội ứng ngoại hợp". Hậu duệ đời thứ ba vẫn giữ nhà, đón khách.

**Nguồn từng fact:**
- "Cai = chức cai tổng; ông Phạm Văn Bổn, tên thường gọi Cường" → baodaklak.vn + scov.gov.vn (★★★ + ★★★★) — đây là bẫy tên entity: "Cai" là chức quan, KHÔNG phải địa danh
- "dựng bên rạch Cái Muối, mặt quay hướng bắc ra rạch" → scov.gov.vn + vnanet.vn (TTXVN) + baodaklak.vn (★★★★)
- "cất năm Ất Dậu 1885" → baodaklak.vn + scov.gov.vn + vnanet.vn (★★★★)
- "mặt bằng chữ Đinh, hai nếp vuông góc" → scov.gov.vn + vnanet.vn (★★★★)
- "cột gỗ cao 6m" → scov.gov.vn + vnanet.vn + baodaklak.vn (★★★★)
- "nền gạch bông Pháp" → baodaklak.vn (★★★) — xem Cảnh báo 2
- "bao lam chạm rồng phượng thếp vàng" → scov.gov.vn + vnanet.vn (★★★★)
- "hoành phi Phạm Phủ Đường" → baodaklak.vn (nguyên văn) + scov.gov.vn (★★★★)
- "lối nội ứng ngoại hợp" → scov.gov.vn + vnanet.vn (★★★★)
- "hậu duệ đời thứ ba vẫn giữ nhà, đón khách" → scov.gov.vn + vnanet.vn (★★★)
- (nền cho §Attributes) "cù lao nay là xã An Bình = Hòa Ninh + Bình Hòa Phước + Đồng Phú + An Bình, từ 1/7/2025" → Nghị quyết 1687/NQ-UBTVQH15 (★★★★★)

Đã LOẠI: loại gỗ cột (lim vs teak — mâu thuẫn), "sâu 13m" (1 nguồn), "15 năm cho thuê du lịch" (bài 2020, đã cũ), tên+tuổi người quản lý còn sống, xếp hạng di tích (không nguồn nào có → không claim).

**Tự kiểm:** Substitution — đạt ở câu 1–3 (chức cai tổng của Phạm Văn Bổn, 1885, hoành phi "Phạm Phủ Đường" chỉ đúng nhà này); câu 4 là câu yếu nhất, có thể đúng cho vài nhà cổ Nam Bộ khác, giữ vì trả lời "còn vào thăm được không", sẽ chi tiết hoá bằng đờn ca tài tử/vườn trái cây nếu nới trần ký tự · Deletion — không câu nào là filler (xoá C1 mất gốc tên + chủ nhân + vị trí; C2 mất niên đại + mặt bằng; C3 mất toàn bộ vật liệu và luận điểm Đông–Tây; C4 mất thông tin còn mở cửa) · Curiosity — đạt, hook là cú lật nghĩa tên ở câu mở cộng ba chi tiết thị giác cụ thể. Gate kỹ thuật: 400 ký tự (trần 400), câu đầu 154 (trần 155), NFC chuẩn, nhịp 35–17–25–10 từ, không mở bằng tên entity, không từ sáo rỗng, không nhắc "miền Tây"/"huyện"/tỉnh cũ, không tự gán nhãn kiểm-chứng-thực-địa (mỗi fact chỉ dẫn nguồn kèm hạng ★).

**Attributes đề xuất bổ sung:** `address` = "Số 38, ấp Bình Hòa, xã An Bình, tỉnh Vĩnh Long" (xã: NQ1687 ★★★★★; số nhà/ấp ★★) · `placeId` đổi `p-long-chau` → place xã An Bình (★★★★★) · `built`=1885 Ất Dậu (★★★★) · `founder`="Phạm Văn Bổn, chức cai tổng" (★★★★) · `architectural_style`="Việt–Pháp, mặt bằng chữ Đinh, nội ứng ngoại hợp" (★★★★) · `orientation`="hướng bắc, ra rạch Cái Muối" (★★★★) · `heritage_level` **để trống** (không có nguồn đáng tin) · `admission` **cần kiểm tra lại** · `coords` đo lại về ấp Bình Hòa ven rạch Cái Muối.

**Cảnh báo:**
1. **Lỗi dữ liệu, không phải lỗi mô tả:** `placeId=p-long-chau` / address "Phường Long Châu" SAI địa bàn — mọi nguồn đặt nhà cổ ở ấp Bình Hòa, xã Bình Hòa Phước (cũ), nay là xã An Bình theo NQ 1687. Không sửa thì breadcrumb + SEO sai theo.
2. Mâu thuẫn vật liệu nền: baodaklak "gạch bông Pháp" vs bản TTXVN "đá xanh nhập từ Pháp" — thống nhất "nhập từ Pháp", khác chất liệu. Bản nháp dùng bản cụ thể hơn; cần ảnh/thực địa chốt.
3. Chính tả tên chủ nhân: TTXVN+scov ghi "Phạm Văn **Bổn**", baodaklak ghi "Phạm Văn **Bốn**". Đã theo tier cao hơn.
4. `admission`: attributes ghi "Miễn phí" nhưng nguồn ★★ ghi ~20.000đ/khách → **đã cố ý không đưa giá vào mô tả**.
5. `hours` 7:00–17:00 chưa có nguồn ≥★★ xác nhận, lại mâu thuẫn nhẹ với việc nhiều nguồn nói khách ngủ lại qua đêm.
6. Độ độc lập nguồn: scov.gov.vn nhiều khả năng đăng lại TTXVN → tính là MỘT mạch; baodaklak là mạch thứ hai độc lập. Các fact cốt lõi (1885, chữ Đinh, cột 6m, rạch Cái Muối, "Phạm Phủ Đường") có ở cả hai mạch.
7. `images=[]` — theo §1.5 chỉ ảnh AI-gen qua `scripts/gen_image.py`, phải giữ nhãn `dc-nophoto-note`.

---

### 2.2 — Cồn Phụng (Cồn Ông Đạo Dừa) (`con-phung-con-ong-dao-dua`, attraction, ben-tre)

**Cũ (149 ký tự):** Cồn nhỏ giữa sông Tiền tại Châu Thành, Bến Tre — nơi kỹ sư Nguyễn Thành Nam (1910) sáng lập Đạo Dừa năm 1963. Nay là khu du lịch sinh thái miệt vườn.

**Mới (397 ký tự):**
Cái chén cổ vẽ chim phụng thợ nhặt được lúc dựng chùa Nam Quốc Phật năm 1963 đặt tên cho cồn Phụng giữa sông Tiền, xã Phú Túc, tỉnh Vĩnh Long. Người dựng ngôi chùa ấy là kỹ sư hoá học tốt nghiệp ở Pháp năm 1935. Nguyễn Thành Nam bỏ nghề đi tu, ăn dừa thay cơm, lập Đạo Dừa cổ vũ hoà bình. Đất Tân Thạch, Bến Tre cũ, còn chừng 1.500 m² di tích: sân chín con rồng, tháp Hoà Bình ốp mảnh vỡ chén bát.

**Nguồn từng fact:**
- "chén cổ vẽ chim phụng thợ nhặt được lúc dựng chùa → thành tên cồn Phụng" → Wikipedia tiếng Việt – Cồn Phụng (★★★★)
- "chùa Nam Quốc Phật, dựng năm 1963" → Wikipedia – Đạo Dừa + Wikipedia – Cồn Phụng (★★★★ ×2)
- "cồn giữa sông Tiền (đoạn sông Mỹ Tho)" → Wikipedia – Cồn Phụng + Cục Du lịch Quốc gia (★★★★ ×2)
- "nay thuộc xã Phú Túc, tỉnh Vĩnh Long" → Nghị quyết 1687/NQ-UBTVQH15 ngày 16/6/2025 — thị trấn Châu Thành + Tân Thạch + Tường Đa + Phú Túc → xã Phú Túc (★★★★★); khớp `placeId: p-phu-tuc`
- "kỹ sư hoá học tốt nghiệp ở Pháp năm 1935" → Wikipedia – Đạo Dừa (du học Rouen từ 1928, tốt nghiệp kỹ sư hoá học 1935) (★★★★)
- "bỏ nghề đi tu, ăn dừa thay cơm" → Wikipedia – Đạo Dừa (tu từ 1945 tại chùa An Sơn; sống khổ hạnh, chủ yếu dùng dừa) (★★★★)
- "Đạo Dừa cổ vũ hoà bình" → Wikipedia – Đạo Dừa (hoà đồng Phật–Nho–Thiên Chúa, đề cao chung sống hoà bình) (★★★★)
- "đất Tân Thạch, Bến Tre cũ" → Wikipedia – Cồn Phụng + Cục Du lịch Quốc gia (xã Tân Thạch, huyện Châu Thành, Bến Tre — địa danh trước 7/2025) (★★★★ ×2)
- "chừng 1.500 m² di tích" → Cục Du lịch Quốc gia (★★★★)
- "sân chín con rồng" → Cục Du lịch Quốc gia ("sân 9 con rồng") + Wikipedia – Cồn Phụng (★★★★ ×2)
- "tháp Hoà Bình ốp mảnh vỡ chén bát" → Cục Du lịch Quốc gia (tháp Hoà Bình/cửu trùng đài, trang trí bằng mảnh vỡ bát đĩa, ấm chén) (★★★★)

**Tự kiểm:** Substitution **đạt** — thay "cồn Phụng" bằng cồn Quy/cồn Lân thì cả 4 câu đều sai (chén phụng, chùa Nam Quốc Phật, 1.500 m² di tích, sân chín con rồng chỉ có ở đây). · Deletion **đã xoá thật 2 câu**: (a) "Vòng ngoài là vườn trái cây, lò kẹo dừa" — fail substitution vì đúng cho hầu hết cồn du lịch bờ Bến Tre cũ; (b) "Phù sa bồi cồn từ 28 ha thập niên 1930 lên hơn 50 ha" — pass substitution nhưng cắt để giữ tổng ≤400 ký tự, chuyển thành đề xuất attributes. 4 câu còn lại xoá câu nào cũng mất fact riêng. · Curiosity **đạt** — móc câu là nghịch lý "kỹ sư hoá học học ở Pháp → ăn dừa thay cơm" và chi tiết tháp ốp mảnh chén bát vỡ; người đọc biết cụ thể sẽ thấy gì tại chỗ. · Nhịp câu 31–16–18–24 từ (dài–ngắn–ngắn–dài). Câu đầu 142 ký tự (≤155), chứa "cồn Phụng" + "sông Tiền" + "xã Phú Túc" + "tỉnh Vĩnh Long". Không mở bằng tên entity, không từ sáo rỗng, NFC sạch.

**Attributes đề xuất bổ sung:**
- `address`: `"Xã Phú Túc, tỉnh Vĩnh Long (xã Tân Thạch, huyện Châu Thành, Bến Tre cũ)"` — thay `"Huyện Châu Thành, Bến Tre"` (cấp huyện đã bỏ từ 1/7/2025). Nguồn: NQ 1687/NQ-UBTVQH15 (★★★★★)
- `alt_names`: `["cồn Tân Vinh", "cù lao Đạo Dừa"]` — Wikipedia – Cồn Phụng (★★★★)
- `area_ha`: `50` + `area_note`: `"khoảng 28 ha thập niên 1930, phù sa bồi lên hơn 50 ha"` — Wikipedia – Cồn Phụng, Cục Du lịch Quốc gia (★★★★ ×2)
- `relic_area_m2`: `1500` — Cục Du lịch Quốc gia (★★★★)
- `founder_background`: `"kỹ sư hoá học, du học Rouen (Pháp) từ 1928, tốt nghiệp 1935"` — Wikipedia – Đạo Dừa (★★★★)
- `temple`: `"chùa Nam Quốc Phật (1963)"` — ★★★★ ×2
- **XOÁ** `booking_note` (`"Nên đặt trước tour trọn gói; có thể đặt tour 4 cồn... từ 95.000đ/khách"`) — vi phạm §1.4 (không bán tour/vé). Đã không đưa vào mô tả mới.
- **SỬA** `key_facts[0]`: `"Khu di tích Đạo Dừa – Tháp Cửu Trùng 9 tầng"` → `"Khu di tích Đạo Dừa ~1.500 m²: sân chín con rồng, tháp Hoà Bình (cửu trùng đài)"` — tên gọi theo Cục Du lịch Quốc gia; chi tiết "9 tầng" chỉ có ở nguồn ★★.
- **SỬA** `key_facts[1]`: bộ Tứ linh Long–Lân–Quy–Phụng **không cùng một tỉnh** — cồn Quy và cồn Phụng ở bờ Vĩnh Long, cồn Long và cồn Lân ở bờ Mỹ Tho (Tiền Giang cũ, nay Đồng Tháp). Nên ghi rõ để tránh hiểu nhầm cả 4 thuộc Vĩnh Long. Nguồn ★★, cần đối chiếu thêm trước khi ghi vào data.
- `coordinates`: đề xuất `[10.3333, 106.3565]` (10°19'59.9"N 106°21'23.4"E) — Wikipedia – Cồn Phụng (★★★★). Xem cảnh báo bên dưới.

**Cảnh báo:**
1. **Toạ độ hiện tại nhiều khả năng SAI ~10 km.** Entity ghi `[10.2376579, 106.3758519]` (`coords_approximate: true`), trong khi Wikipedia ghi 10.3333N / 106.3565E. Chênh 0,096° vĩ độ ≈ 10,6 km về phía nam — điểm hiện tại nằm sâu trong đất liền, không nằm trên sông Tiền. **Cần chủ dự án xác nhận trước khi sửa** (mô tả mới không dùng khoảng cách/hướng nào nên không bị ảnh hưởng).
2. **Mâu thuẫn năm sinh Nguyễn Thành Nam giữa 3 nguồn nội bộ + ngoại bộ:** `attributes.founder` ghi 1910; `entity.description` ghi 22/4/1910; Wikipedia – Đạo Dừa ghi 25/12/1910 (mất 13/5/1990); Wikipedia – Cồn Phụng ghi 1909–1990. Vì vậy mô tả mới **cố ý không dùng năm sinh**, thay bằng mốc chắc chắn hơn (tốt nghiệp kỹ sư hoá học 1935). Đề xuất để `founder: "Nguyễn Thành Nam (Ông Đạo Dừa, 1910–1990)"` kèm `founder_dob_disputed: true`.
3. **Claim "ăn dừa/uống nước dừa suốt 25 năm (1945–1970)" trong `entity.description` hiện tại chỉ truy được nguồn ★★** (blog/trang tour, dạng "ông nói rằng"). Đã bỏ con số 25 năm khỏi mô tả mới, chỉ giữ "ăn dừa thay cơm" (★★★★).
4. **`verifiedAt` của entity này = `updatedAt` = `2026-06-28T02:23:47Z`** (trùng khít tới giây) → nhiều khả năng là dấu thời gian tự sinh, **không phải bằng chứng kiểm chứng thực địa**. Theo §1.7, mô tả mới **không tự gán bất kỳ nhãn kiểm-chứng-thực-địa nào**. Nên rà lại cơ chế gán `verifiedAt` trước khi dùng field này làm bằng chứng E-E-A-T.
5. Chưa tìm được nguồn ≥★★★ nào cho thấy khu di tích Đạo Dừa **đã được xếp hạng di tích** cấp tỉnh/quốc gia (2 lượt search không ra). Đã **không** viết chữ "di tích được xếp hạng" — chỉ dùng "di tích" theo cách gọi của Cục Du lịch Quốc gia. Cần bổ sung nếu tìm được quyết định xếp hạng.
6. `attributes.admission` và `hours` chưa được kiểm chứng qua nguồn ≥★★★ trong đợt này nên không đưa vào mô tả; giữ nguyên ở attributes, cần xác minh riêng.

---

### 2.3 — Bún suông (`bun-suong`, dish, tra-vinh)

**Cũ (78 ký tự):** Món bún suông đặc sản của Trà Vinh, với tôm bông giòn thơm và nước lèo đậm đà.

**Mới (398 ký tự):**
Dân Trà Vinh gọi bún suông là bún đuông: cọng chả tôm nặn dài, vàng ươm màu dầu điều, nhìn hệt con đuông dừa — thứ không có trong tô. Tôm tươi quết với tỏi, hành tím, bắn thẳng vào nồi nước lèo sôi, nổi lên là chín. Nước lèo ninh giò heo, nêm me và tương hột nên ngả nâu, chua ngọt, không mắm bò hóc như bún nước lèo cùng xứ. Xế chiều, hàng suông dọn dọc Điện Biên Phủ, Hùng Vương ở nội ô Trà Vinh.

*(câu 1 = 133 ký tự, đủ chuẩn meta description ≤155, chứa keyword "bún suông" + "Trà Vinh"; NFC chuẩn)*

**Nguồn từng fact:**
- "gọi bún suông là bún đuông" → vi.wikipedia.org/wiki/Bún_suông (★★★★) + vtcnews.vn + danviet.vn (★★★)
- "cọng chả tôm nặn dài… nhìn hệt con đuông dừa" (hình dạng, KHÔNG phải nguyên liệu) → VTC News, Dân Việt, VietnamNet (★★★ ×3)
- "vàng ươm màu dầu điều" → VnExpress *Món bún suông – đặc sản đất Trà Vinh* (★★★, ghi rõ nêm tiêu, muối, bột năng, màu dầu điều)
- "tôm tươi quết với tỏi, hành tím" → VnExpress bài trên (★★★)
- "bắn thẳng vào nồi nước lèo sôi, nổi lên là chín" → VnExpress *Cách làm bún suông* (★★★, nặn qua bao cắt góc thả vào nồi) + bài 2015 (★★★)
- "ninh giò heo" → VnExpress *Cách làm bún suông* (★★★: giò heo, ba chỉ, tôm khô, mực khô, củ cải, hành tây)
- "nêm me và tương hột nên ngả nâu, chua ngọt" → Wikipedia (★★★★) + VnExpress ×2 (★★★)
- "không mắm bò hóc như bún nước lèo cùng xứ" → suy ra từ đối chiếu 2 danh sách nguyên liệu: bún nước lèo Trà Vinh nấu mắm bò hóc (Tuổi Trẻ ★★★), bún suông không có mắm trong mọi công thức nguồn ★★★
- "xế chiều… Điện Biên Phủ, Hùng Vương ở nội ô Trà Vinh" → VnExpress 2015 (★★★, đăng lại trên scov.gov.vn)
- ĐÃ LOẠI: "hơn nửa thế kỷ", "ra đời thập niên 1950-1960", "giao thoa Kinh-Khmer-Hoa", "tôm đất" — chỉ có nguồn ★/★★ đơn lẻ.

**Tự kiểm:** Substitution đạt — thay "bún nước lèo"/"bún cà ri" vào thì câu 1 và câu 3 sai ngay (không có tên "bún đuông", có mắm bò hóc). · Deletion đạt — bỏ câu 1 mất etymology + hình dạng, bỏ câu 2 mất cách làm, bỏ câu 3 mất thành phần + điểm phân biệt, bỏ câu 4 mất nơi/giờ ăn; không câu nào là filler. Bản đầu 512 ký tự đã cắt "tôm khô, mực khô" và "chấm tương xay dằm ớt" để về trong ngưỡng 400. · Craving đạt sau 1 vòng sửa — bản nháp đầu chỉ liệt kê nguyên liệu, đã thêm động tác "bắn thẳng vào nồi nước lèo sôi, nổi lên là chín" + màu "vàng ươm"/"ngả nâu" để có hình và động.

**Attributes đề xuất bổ sung / sửa:**
- `alt_name`: "Bún đuông" — Wikipedia (★★★★) + VTC News (★★★)
- `placeId`: `xa-nhi-long` → `p-tra-vinh`; `address`: "Xã Nhị Long, Trà Vinh" → "Đường Điện Biên Phủ và Hùng Vương, nội ô Trà Vinh"; `coordinates`: [10.046765, 106.2947443] (Càng Long cũ) → vùng [9.9516, 106.3322] như entity `bun-suong-tra-vinh` — VnExpress (★★★)
- `specialty`: "Bún, Cá" → "Bún, Tôm, Thịt ba chỉ" (không nguồn nào có cá) — VnExpress ×2 (★★★)
- `award`: "Được Tổ chức Kỷ lục Việt Nam đề cử vào 10 món Việt đạt giá trị ẩm thực châu Á, đợt 2 năm 2013" — Wikipedia (★★★★) + Dân Việt, kenh14 (★★★). Là *đề cử của tổ chức kỷ lục*, không phải công nhận nhà nước — giữ nguyên chữ "đề cử".
- `dipping_sauce`: "Tương hột xay dằm ớt" — VnExpress 2015 (★★★)
- `best_time_of_day`: "Chiều tối" — VnExpress (★★★), nhưng xem Cảnh báo #5
- `price_range` (30.000–80.000đ): **không có nguồn ngoài ≥★★ cho giá hiện tại** — nguồn ★★★ duy nhất là VnExpress 2015 ghi 15.000–25.000đ (đã lỗi thời). Trần 80.000đ nên bỏ; nếu cần con số, 30.000–50.000đ khớp 2 entity quán trong data nhưng 2 entity đó nguồn "curated", chưa kiểm được.
- `source`: bỏ shopyte.com.vn (★ SEO farm) → thay bằng 2 bài VnExpress + Wikipedia.

**Cảnh báo:**
1. **placeId sai lan sang entity khác:** `bun-suong-du-van-tra-vinh` ghi địa chỉ "644 Võ Nguyên Giáp, TP. Trà Vinh" nhưng `placeId` cũng là `xa-nhi-long` — cùng một lỗi gán, nên sửa chung một lượt.
2. **Trùng lặp cần quyết canonical:** `bun-suong` và `bun-suong-tra-vinh` cùng type `dish`, cùng vùng, cùng nội dung → nên gộp về một entity.
3. **`lang-nghe-bun-suong` sai type + sai chính tả + fact không nguồn:** type `craft_village` cho một món hàng rong là sai; description viết "đuổng" (đúng: "đuông") 3 lần; chứa "hơn nửa thế kỷ", "ra đời khoảng thập niên 1950-1960", "giao thoa văn hóa Kinh-Khmer-Hoa" — không truy được nguồn ≥★★★ nào; và "ninh 5 tiếng" mâu thuẫn VnExpress (khoảng 2 tiếng).
4. **Etymology là giả thuyết, không phải sự thật đã chốt:** nhiều nguồn ★★★ nói người lớn tuổi ở Trà Vinh cũng không rõ gốc tên. Câu 1 vì vậy chỉ khẳng định *tên gọi dân gian có thật* ("gọi là bún đuông") + so *hình dạng*, không khẳng định nguồn gốc từ nguyên.
5. **Mâu thuẫn giờ bán:** VnExpress ghi hàng bán chiều tối; hai entity quán trong data (`bun-suong-ut-tam-tra-vinh`, `bun-suong-du-van-tra-vinh`) ghi 06:00–10:30. Cả hai có thể cùng đúng, nhưng nên thống nhất trước khi hiển thị.
6. **`verifiedAt` không phải bằng chứng kiểm chứng:** entity này có `verifiedAt: 2026-06-28T02:24:04Z` nhưng đó là dấu đóng hàng loạt cùng lúc với 5 entity kia (chênh nhau vài giây), không phải kiểm chứng thực địa — không được dùng làm căn cứ cho bất kỳ claim "đã xác minh" nào (§1.7).
7. Không ghi vào `web/data.json`, không chạy script, không git add/commit — đây là bản nháp chờ chủ dự án duyệt.

---

### 2.4 — Dừa sáp Cầu Kè (`dua-sap-cau-ke`, product, tra-vinh)

**Cũ (168 ký tự):** Dừa sáp trồng tại Cầu Kè, Trà Vinh — giống do HT Thạch Sô mang từ Campuchia về trồng ở chùa Botumsakor cách đây hơn 100 năm. VICOSAP đạt 4 sản phẩm OCOP 5 sao quốc gia.

**Mới (400 ký tự):**
Mỗi buồng dừa sáp Cầu Kè chỉ hai, ba trái đặc ruột thành sáp — mà những trái đó lại không nảy mầm, giống phải lấy từ trái thường cùng cây. Cùi dẻo quánh, nước sánh chứ không chảy, chẻ ra dầm sữa đá ăn tại chỗ. Hai gốc dừa Hòa thượng Thạch Sô trồng trong chùa Botum Sakor năm 1924 nay thành hơn 1.100 ha quanh Cầu Kè, Tam Ngãi, hơn 70% chủ vườn là người Khmer. Quả dừa sáp có chỉ dẫn địa lý từ 8/2024.

**Nguồn từng fact:**
- "Mỗi buồng chỉ hai, ba trái đặc ruột thành sáp" → tvu.edu.vn "Làm giàu từ trái dừa sáp ở Trà Vinh" (2–3 trái sáp/buồng trên hơn 10 trái) (★★★★); đối chiếu Dân trí "vì sao tỷ lệ trái có sáp thường thấp hơn 25%" (★★★)
- "những trái đó lại không nảy mầm, giống phải lấy từ trái thường cùng cây" → danviet.vn "Quả dừa đặc ruột… không nảy mầm" + Wikipedia tiếng Việt mục Dừa sáp (có dẫn nguồn) (★★★ + ★★★★)
- "Cùi dẻo quánh, nước sánh chứ không chảy" → portal.vinhlong.gov.vn "Dừa sáp Cầu Kè – Duyên đất, Tình người" (12/11/2025) + tvu.edu.vn (★★★★)
- "chẻ ra dầm sữa đá ăn tại chỗ" → baovinhlong.com.vn "Một ngày ở thủ phủ dừa sáp Cầu Kè" (★★★)
- "Hai gốc dừa Hòa thượng Thạch Sô trồng trong chùa Botum Sakor năm 1924" → portal.vinhlong.gov.vn (★★★★) + vietnamplus.vn "Truy tôn cố Hòa thượng Thạch Sô" (★★★) + dantocmiennui.baotintuc.vn (★★★)
- "hơn 1.100 ha quanh Cầu Kè, Tam Ngãi" → vietnamplus.vn 7/2025: hơn 1.145 ha trên 4 xã Cầu Kè, Tam Ngãi, An Phú Tân, Phong Thạnh (★★★) + portal.vinhlong.gov.vn 11/2025: 1.229,5 ha (★★★★) → làm tròn xuống theo confidence gating
- "hơn 70% chủ vườn là người Khmer" → vietnamplus.vn (★★★), khớp mô tả sẵn có của entity `vung-trong-dua-sap-cau-ke`
- "Quả dừa sáp có chỉ dẫn địa lý từ 8/2024" → Cục Sở hữu trí tuệ, Quyết định 653/QĐ-SHTT ngày 05/8/2024, GCN chỉ dẫn địa lý số 00142 (★★★★★), trùng khớp với Sở KH&CN Trà Vinh cũ (★★★★)

**Tự kiểm:** *Đọc kỹ tên* — xác minh trước khi viết: "sáp" là **đặc tính giống** (đột biến làm nội nhũ đặc quánh như sáp), KHÔNG phải công đoạn chế biến; "Cầu Kè" là địa danh, nay là **xã Cầu Kè, tỉnh Vĩnh Long** (bỏ hết "huyện"). · **Substitution** đạt — thay bằng bất kỳ sản phẩm nào khác thì câu 1 và câu 3 sai ngay (chùa Botum Sakor, 1924, Cầu Kè/Tam Ngãi, 70% Khmer). Chỉ trùng được với chính các entity trùng lặp của nó (xem Cảnh báo). · **Deletion** đạt — xoá C1 mất cơ chế hiếm, C2 mất giác quan, C3 mất gốc tích + quy mô, C4 mất bảo hộ pháp lý; không câu nào là filler. Đã cắt "VICOSAP 4 OCOP 5 sao" của bản cũ vì trùng nguyên vẹn với `keo-dua-sap-vicosap` và `vicosap-keo-dua-sap-ocop-5-sao`. · **Craving** đạt — nghịch lý "trái ngon nhất lại không làm giống được" là hook, "dầm sữa đá" cho hành động cụ thể. Nhịp câu 31/16/31/10 từ; câu đầu 138 ký tự, chứa keyword "dừa sáp Cầu Kè", dùng được làm meta description.

**Attributes đề xuất bổ sung:**
- `gi_certificate`: `Chỉ dẫn địa lý "Trà Vinh" cho quả dừa sáp — QĐ 653/QĐ-SHTT ngày 05/8/2024, GCN số 00142` (Cục SHTT, ★★★★★)
- `area_ha`: `1229.5` — **thay giá trị 750 đang lỗi thời** (portal.vinhlong.gov.vn 11/2025, ★★★★)
- `growing_communes`: `Cầu Kè, Tam Ngãi, An Phú Tân, Phong Thạnh` (vietnamplus.vn 7/2025, ★★★)
- `households`: `~5.000 hộ toàn vùng (11/2025); hơn 2.000 hộ ở 4 xã lõi, trên 70% là người Khmer` (portal.vinhlong.gov.vn ★★★★ + vietnamplus ★★★)
- `annual_yield`: `gần 4 triệu trái/năm` (portal.vinhlong.gov.vn, ★★★★)
- `sap_ratio`: `2–3 trái/buồng (~20–25%); cây nuôi cấy phôi của Trường ĐH Trà Vinh đạt tới 90%` (tvu.edu.vn ★★★★ + Dân trí ★★★)
- `propagation_note`: `Trái đã lên sáp không nảy mầm; giống lấy từ trái không sáp trên cùng cây hoặc nuôi cấy phôi` (Wikipedia có dẫn nguồn ★★★★ + danviet ★★★)
- `founder`: `Hòa thượng Thạch Sô (1886–1949), pháp danh Mongkol Thero; lễ truy tôn 20/7/2025 tại xã Tam Ngãi` (vietnamplus.vn, ★★★)
- `address`: sửa `Huyện Cầu Kè, Trà Vinh` → `Xã Cầu Kè, tỉnh Vĩnh Long`
- `price_range`: **chưa đề xuất** — hai nguồn mâu thuẫn (xem Cảnh báo)

**Cảnh báo:**
1. **Nguồn gốc giống mâu thuẫn — đã cố ý viết trung lập.** `attributes.origin` và summary cũ ghi "giống từ Campuchia". Nguồn cho thấy sư Thạch Sô du học ở Battambang (Campuchia) rồi mang 2 cây về năm 1924, nhưng portal.vinhlong.gov.vn và trang Bảo tàng dừa sáp kể hai cây là quà của một **bạn đồng học người Philippines**, và giống dừa sáp (makapuno) được cho là gốc Philippines. Vì hai luồng không thống nhất, bản mới chỉ viết "Hòa thượng Thạch Sô trồng trong chùa Botum Sakor năm 1924" — **không khẳng định mang từ đâu**. Đề nghị chủ dự án chốt trước khi sửa `attributes.origin`.
2. **`area_ha=750` đã lỗi thời** (bắt nguồn từ bài tvu.edu.vn cũ). Số mới: 1.145 ha (7/2025) → 1.229,5 ha (11/2025).
3. **`price_range` mâu thuẫn:** attributes ghi 60.000–120.000 đ/trái; tvu.edu.vn (★★★★) ghi 120.000–200.000 đ/trái; `dua-sap-sinh-to` lại ghi 80.000–200.000 đ/trái. Đã **không đưa giá vào mô tả**; cần một nguồn ★★★+ mới trước khi cập nhật.
4. **Trùng lặp entity nghiêm trọng (ngoài phạm vi task, cần dọn riêng):** `dua-sap`, `dua-sap-tra-vinh`, `dua-sap-hoa-tan`, `dua-sap-cang-long`, `vung-trong-dua-sap-cau-ke` cùng mô tả một sản vật. Nặng nhất là **`dua-sap-cau-ke-dac-san-ben-tre`**: vừa gán sai `area=ben-tre`/`placeId=p-ba-tri`, vừa có summary **nói về kẹo dừa và OCOP Bến Tre chứ không phải dừa sáp** — nội dung sai hoàn toàn, nên gỡ hoặc trộn vào entity này.
5. **Sai định vị hành chính ở entity họ hàng:** `hop-tac-xa-dua-sap-cau-ke-tra-vinh` đang để `area=ben-tre` dù ghi địa chỉ Cầu Kè; nhiều entity còn ghi "huyện Cầu Kè/Càng Long/Trà Cú".
6. **Fact hay nhưng chưa dùng:** "chỉ 9/93 nước trồng dừa có dừa sáp" — chỉ có trong đoạn trích kết quả tìm kiếm của trang Cục SHTT; **không fetch được thân trang** (ipvietnam.gov.vn lỗi chứng chỉ TLS, skhcn.travinh.gov.vn không phân giải DNS). Chưa đưa vào mô tả. Ba dữ kiện chỉ dẫn địa lý (số QĐ / ngày / số GCN) thì trùng khớp qua hai trang chính thống độc lập nên vẫn dùng.
7. **Tên chính thức của chỉ dẫn địa lý là "Trà Vinh"**, không phải "Cầu Kè". Bản mới viết gọn "có chỉ dẫn địa lý" để không nhắc tên tỉnh cũ ngoài văn cảnh lịch sử (§1.6); nếu chủ dự án muốn nêu đủ danh hiệu thì phải ghi nguyên văn `chỉ dẫn địa lý "Trà Vinh"` kèm chú thích là tên đăng bạ.
8. **Bản mới không tự gán nhãn kiểm-chứng-thực-địa nào** (§1.7). Lưu ý: entity này đang có `verifiedAt="2026-06-28T02:23:48Z"` bằng đúng `updatedAt` — đây là dấu vết ETL, không phải kiểm chứng thực địa; đừng dùng nó làm căn cứ trust.

---

### 2.5 — Chùa Âng (Wat Angkor Raig Borei) (`chua-ang-wat-angkor-raig-borei`, history, tra-vinh)

**Cũ (83 ký tự):** Một trong những ngôi chùa Khmer cổ nhất Trà Vinh, có lịch sử hình thành từ năm 990.

**Mới (398 ký tự):**
Cạnh Ao Bà Om, phường Nguyệt Hóa, chùa Âng (Angkorajaborey) giữ ngôi stupa năm ngọn duy nhất trong các chùa Khmer đất Trà Vinh. Năm khởi dựng 990 chép trên bảng di tích trong sân. Dáng chùa hôm nay có từ đợt dựng lại 1842: sáu mươi cột gỗ quý đỡ ba tầng mái vihear, gopura tạc chằn và chim thần Krud. Hào nước và hàng trăm gốc sao, dầu cổ thụ vây bốn héc-ta đất giồng. Di tích quốc gia từ năm 1994.

**Nguồn từng fact:**
- "phường Nguyệt Hóa" (địa chỉ hành chính hiện hành) → Nghị quyết 1687/NQ-UBTVQH15 ngày 16/6/2025 (P.7 + P.8 TP Trà Vinh cũ + xã Nguyệt Hóa → phường Nguyệt Hóa), danh sách 124 xã/phường trên xaydungchinhsach.chinhphu.vn (★★★★★); Wikipedia ghi địa chỉ "Quốc lộ 53, khóm 13, phường Nguyệt Hóa, tỉnh Vĩnh Long" (★★★★)
- "cạnh Ao Bà Om" → vov.gov.vn (★★★★), Wikipedia (★★★★)
- "stupa năm ngọn duy nhất trong các chùa Khmer đất Trà Vinh" → vov.gov.vn + vovworld.vn: "ngôi tháp năm ngọn duy nhất trong các ngôi chùa Khmer Trà Vinh", chứa di cốt các vị sư cả (★★★★)
- "Năm khởi dựng 990 chép trên bảng di tích trong sân" → Wikipedia dẫn nguồn duy nhất là "Bảng Di tích lịch sử chùa Âng" dựng tại chùa, không có sử liệu ngoài (★★★★ cho việc *mốc đó nằm ở đâu*, KHÔNG phải cho việc mốc đó đúng)
- "đợt dựng lại 1842: sáu mươi cột gỗ quý" → Wikipedia (★★★★) + mia.vn/phatgiao.org.vn cùng ghi "rui, mè và 60 cột gỗ quý, mái ngói, tường gạch" (★★ ×2)
- "ba tầng mái vihear" → Wikipedia "three-tiered roof" (★★★★) + vov.gov.vn "chánh điện có 3 mái" (★★★★)
- "gopura tạc chằn và chim thần Krud" → Wikipedia (tháp cổng với Kẽn naarr và Krũd) (★★★★) + vov.gov.vn "tượng chằn, tiên nữ, chim thần" (★★★★)
- "hào nước… bốn héc-ta đất giồng… hàng trăm gốc sao, dầu cổ thụ" → Wikipedia (moat, ~4 ha) (★★★★) + mia.vn (thực vật đất giồng cát, hàng trăm cây sao dầu cổ thụ) (★★)
- "Di tích quốc gia từ năm 1994" → Quyết định 921-QĐ/BT ngày 20/7/1994 của Bộ Văn hóa – Thông tin; Wikipedia (★★★★) + tinhdoantravinh.vn (★★★)

**Tự kiểm:** Substitution — đạt; thay "chùa Âng" bằng chùa Khmer bất kỳ thì cả 5 câu đều sai (stupa năm ngọn, mốc 990 trên bảng, 60 cột 1842, hào nước 4 ha, 1994). · Deletion — đã xoá 2 câu nháp không chịu tải fact ("Ngôi chùa gắn bó với đời sống tâm linh đồng bào Khmer", "kiến trúc hài hòa với cảnh quan"); 5 câu còn lại xoá câu nào cũng mất fact riêng. · Curiosity — đạt sau khi đổi hook: bản đầu mở bằng mốc 990 (mốc yếu nguồn, lại trùng mọi bài du lịch), đổi sang "stupa năm ngọn duy nhất" + "chim thần Krud" + "hào nước" là chi tiết chưa gặp ở đâu khác.

**Attributes đề xuất bổ sung:**
- `address`: "Quốc lộ 53, khóm 13, phường Nguyệt Hóa, tỉnh Vĩnh Long" — thay giá trị cũ "Phường 8, TP Trà Vinh" (Wikipedia ★★★★ + NQ 1687 ★★★★★)
- `khmer_name`: "Angkorajaborey (វត្តអង្គរាជបូរី)" — tên entity hiện tại "Wat Angkor Raig Borei" là chuyển tự sai, không nguồn nào dùng
- `heritage_level`: "Di tích quốc gia" · `heritage_decision`: "921-QĐ/BT, 20/7/1994, Bộ Văn hóa – Thông tin" (Wikipedia ★★★★ + tinhdoantravinh.vn ★★★) — cùng số quyết định với Ao Bà Om
- `founding_year_claimed`: 990 · `founding_source`: "Bảng Di tích lịch sử chùa Âng (bảng dựng tại chùa)" — tách khỏi field `built` để không trình bày như sử liệu
- `rebuilt`: 1842 (gỗ quý, ngói, tường gạch; 60 cột) · `rebuilt_earlier`: 1695 (mây tre lá — Wikipedia ★★★★, chỉ 1 nguồn)
- `area_ha`: 4 · `buddhist_tradition`: "Phật giáo Nam tông Khmer (Theravada)" · `orientation`: "vihear quay hướng đông, nền cao 2 m" (Wikipedia ★★★★)
- `festivals`: "Chôl Chnăm Thmây, Sene Đôlta, Ok Om Bok" (vov.gov.vn ★★★★)
- KHÔNG đề xuất: lượng khách "300.000/năm" (1 nguồn VOV, và là con số của cả cụm Ao Bà Om chứ không riêng chùa); "1 trong 144 chùa Khmer" (không truy được nguồn ≥★★★)

**Cảnh báo:**
1. **Mốc 990 không có sử liệu độc lập.** Nguồn duy nhất là bảng di tích do nhà chùa dựng; báo/blog chép lại lẫn nhau (một số ghi rõ "theo truyền thuyết"). Bản mới vì vậy nêu mốc kèm xuất xứ, KHÔNG khẳng định. Đừng để AdminCP rút gọn thành "xây năm 990".
2. **Mâu thuẫn ngày xếp hạng:** 20/7/1994 (Wikipedia + tinhdoantravinh.vn, QĐ 921-QĐ/BT) vs 25/8/1994 (vntrip.vn ★★, và chính `attributes.heritage_level` của bản ghi `chua-ang` đang ghi 25/8/1994). Ưu tiên 20/7/1994; đề nghị sửa `chua-ang`.
3. **Mâu thuẫn kích thước chánh điện:** 36 × 24 m (= 864 m²) vs 1.064,75 m² (Wikipedia). Đã bỏ khỏi summary, đừng đưa vào attributes cho tới khi có nguồn ★★★★ thống nhất.
4. **Diện tích khuôn viên:** ~4 ha (Wikipedia) vs "45 công ≈ 4,5 ha" (vov.gov.vn). Dùng "bốn héc-ta" (làm tròn xuống) theo confidence gating.
5. **Trùng lặp 4 bản ghi + 2 bản ghi ăn theo.** `web/data.json` hiện có: `chua-ang` (attraction, placeId=**p-long-duc**), `chua-ang-angkorajaborey` (history, **p-tra-vinh**), `chua-ang-angkor-borei` (history, p-nguyet-hoa), bản này (history, p-nguyet-hoa) — cộng thêm `tiem-banh-che-gan-chua-ang-angkor-borei-tra-vinh` và `quan-com-chay-gan-chua-ang-angkor-rajaborei-tra-vinh` cũng ghi địa chỉ "phường 8 / Phường 1, TP. Trà Vinh". **placeId đúng là `p-nguyet-hoa`**; `p-long-duc` và `p-tra-vinh` sai. Phải gộp 4 bản ghi (giữ 1 canonical) TRƯỚC khi ghi summary chính thức — nếu không sẽ có 4 trang cạnh tranh nhau cùng 1 keyword.
6. **Bản ghi `chua-ang-angkor-borei` còn dùng địa danh đã bãi bỏ** ("xã Nguyệt Hóa, huyện Châu Thành") — cấp huyện không còn từ 7/2025.
7. Toàn bộ nội dung này là **tổng hợp từ nguồn thứ cấp, chưa có kiểm chứng thực địa** — `verifiedAt` vẫn rỗng, không được gắn nhãn "đã xác minh" ở bất kỳ đâu (§1.7).
8. Chưa xác minh được: số sư hiện tại, trường Pali/lớp chữ Khmer tại chùa, bộ kinh lá buông (có nhắc ở nguồn ★★–★★★ nhưng mô tả lệch nhau) — cần bổ sung sau bằng nguồn Ban Quản lý di tích tỉnh (banquanlyditichtravinh.vn hiện không truy cập được, ECONNREFUSED).

---

### 2.6 — Khu di tích Nguyễn Đình Chiểu (`khu-di-tich-nguyen-dinh-chieu`, history, ben-tre)

> Bản gốc: `docs/drafts/2026-08-07-khu-di-tich-nguyen-dinh-chieu.md`

**Cũ (167 ký tự):** Tại vùng đất Ba Tri gió lộng, khu di tích Nguyễn Đình Chiểu là điểm hành hương của những ai kính ngưỡng vị sĩ phu mù mà lòng sáng tựa gương, ngòi bút sắc bén như gươm.

**Mới (400 ký tự):**
Năm 1862, khi ba tỉnh miền Đông rơi vào tay Pháp, Nguyễn Đình Chiểu rời Gia Định về Ba Tri và ở lại 26 năm cuối đời. Di tích quốc gia đặc biệt rộng hơn 14.000 m² xếp ba lớp thời gian: khu mộ tôn tạo 1958, đền thờ cũ 1972, đền thờ mới cao 21 m (2000–2002). Cạnh mộ cụ là mộ con gái, Sương Nguyệt Anh — nữ chủ bút đầu tiên của báo chí Việt Nam. Ngày 1 và 3 tháng 7 — sinh và mất — dân xã Ba Tri về giỗ.

**Nguồn từng fact:**
- "Năm 1862... rời Gia Định về Ba Tri và ở lại 26 năm cuối đời (1862–1888)" → bentre.dcs.vn (Tỉnh ủy) + danhnhannguyendinhchieu.vn + thitranbatri.gov.vn (★★★★)
- "Di tích quốc gia đặc biệt" (QĐ 2499/QĐ-TTg ngày 22/12/2016) → Cục Di sản văn hóa dsvh.gov.vn (★★★★★)
- "rộng hơn 14.000 m²" (14.187,9 m²) → dsvh.gov.vn (★★★★★)
- "khu mộ tôn tạo 1958" → dsvh.gov.vn (★★★★★)
- "đền thờ cũ 1972" → dsvh.gov.vn + Wikipedia "Lăng Nguyễn Đình Chiểu" (★★★★★)
- "đền thờ mới cao 21 m (2000–2002)" → dsvh.gov.vn + Wikipedia (★★★★★)
- "mộ con gái... trong khu mộ" → dsvh.gov.vn (ghi tên "Nguyễn Thị Ngọc Khuê") + Wikipedia (★★★★★)
- "Sương Nguyệt Anh — nữ chủ bút đầu tiên của báo chí Việt Nam" (*Nữ giới chung*, số đầu 1/2/1918) → hoilhpn.org.vn + Báo Tin Tức/TTXVN (★★★★)
- "Ngày 1 và 3 tháng 7 — sinh và mất — ... về giỗ" → dsvh.gov.vn (★★★★★)
- "xã Ba Tri" (An Đức cũ nay thuộc xã Ba Tri, tỉnh Vĩnh Long) → tracuusapnhap.vn + NQ 202/2025/QH15 (★★★★)

Đúng nguồn nhưng **loại vì vượt trần 400 ký tự** (chuyển sang đề xuất attributes): UNESCO ra nghị quyết 23/11/2021 + kỷ niệm 200 năm ngày sinh 2022; nhà bia cao 12 m, bia đá xanh nguyên khối 2,65 × 2,7 × 1,8 m; tượng đồng cao 1,6 m.

**Tự kiểm:** Substitution **đạt** — thay tên di tích khác vào là sai ngay ở cả 4 câu (mốc 1862/26 năm, bộ ba 1958/1972/2000–2002 + 14.000 m², mộ Sương Nguyệt Anh, cặp ngày 1–3/7); bản cũ fail nặng vì "điểm hành hương của những ai kính ngưỡng…" lắp vừa hàng chục đền thờ danh nhân · Deletion **đạt sau khi cắt thật** — xóa toàn bộ cụm sáo bản cũ ("gió lộng", "lòng sáng tựa gương", "ngòi bút sắc bén như gươm": 0 fact), cắt thêm câu giờ mở cửa/vé ở vòng sửa vì trùng `hours`+`admission` đã có trong attributes (487 → 432 → 400 ký tự); giờ xóa câu nào cũng mất một khối fact riêng · Curiosity **đạt** — hai hook: (1) người Ba Tri thờ phụng nhất lại không sinh ra ở Ba Tri, ông đồ mù 40 tuổi bỏ Gia Định về vì không chịu sống dưới quyền Pháp; (2) nằm cạnh mộ cha là mộ người phụ nữ đầu tiên làm chủ bút một tờ báo Việt — chi tiết hầu như vắng trong mô tả du lịch phổ thông về khu di tích này. Gate khác: câu đầu 116 ký tự (≤155, chứa "Nguyễn Đình Chiểu" + "Ba Tri"), tổng đúng 400, không mở bằng tên entity, NFC chuẩn, nhịp 27/31/21/17 từ.

**Attributes đề xuất bổ sung:**
- `architectural_style`: **SỬA** — "Đình làng (kiến trúc truyền thống Nam bộ)" → "Đền thờ mới: nhà tròn bê tông cốt thép, 2 tầng với 3 tầng mái, ngói âm dương xanh (2000–2002); đền thờ cũ 1972: 2 tầng mái, ngói âm dương nâu" (dsvh.gov.vn, ★★★★★)
- `address`: **SỬA** — "Xã An Đức" → "Ấp 3, xã Ba Tri, tỉnh Vĩnh Long (xã An Đức cũ)" (dsvh.gov.vn cho "Ấp 3" ★★★★★; NQ 202/2025/QH15 + tracuusapnhap.vn cho sáp nhập ★★★★)
- `key_facts[]`: **THÊM** "UNESCO ra nghị quyết vinh danh ngày 23/11/2021 (Đại hội đồng lần 41), cùng kỷ niệm 200 năm ngày sinh năm 2022" — hiện data chỉ ghi "UNESCO vinh danh ông năm 2022", thiếu mốc nghị quyết (baochinhphu.vn, ★★★★)
- `key_facts[]`: **THÊM** "Xếp hạng di tích lịch sử – văn hóa cấp quốc gia ngày 27/4/1990" (dsvh.gov.vn, ★★★★★) — chưa có trong data
- `key_facts[]`: **THÊM** "Nhà bia cao 12 m, bia đá xanh nguyên khối 2,65 × 2,7 × 1,8 m" (dsvh.gov.vn + Wikipedia, ★★★★★)
- `season.text`: **SỬA** — thay cụm mơ hồ "tháng 7 thường đáng chú ý vì gắn với các hoạt động tưởng niệm" bằng đích danh "lễ giỗ ngày 1 và 3 tháng 7" (★★★★★); đồng thời đổi "tại Bến Tre" → "tại xã Ba Tri" theo §1.6
- `highlight`: **SỬA** — "ngòi bút yêu nước bất diệt… hồn thiêng đất Ba Tri" là giọng sáo cùng loại summary cũ, nên thay bằng fact
- Giữ nguyên: `sub_category`, `hours`, `phone`, `admission`, `coordinates` (không có nguồn mâu thuẫn)

**Cảnh báo:**
1. **`architectural_style` hiện SAI**, không phải khác biệt diễn đạt: "Đình làng" mâu thuẫn trực tiếp với mô tả của Cục Di sản văn hóa (đền thờ mới hình **tròn**, bê tông cốt thép). Mô tả mới đã tránh dùng từ "đình làng".
2. **`verifiedAt` của entity này KHÔNG rỗng** — data.json ghi `"verifiedAt": "2026-06-28T02:23:56Z"`, trùng khít `updatedAt`, kèm `verified: 1`; trái giả định "verifiedAt = 0 toàn bộ" trong đề bài. Dấu hiệu là timestamp pipeline ghi tự động chứ không phải kiểm chứng thực địa. Mô tả mới **không chứa claim "đã xác minh/kiểm chứng"** nào (§1.7). Đề nghị chủ dự án rà lại ngữ nghĩa trường này trên toàn dataset trước khi dùng làm bằng chứng E-E-A-T.
3. **Tên thật Sương Nguyệt Anh lệch giữa nguồn** (dsvh.gov.vn: "Nguyễn Thị Ngọc Khuê" vs hoilhpn.org.vn: "Nguyễn Xuân Khuê"), năm mất cũng lệch (1921 vs 1922) → mô tả **cố ý chỉ dùng bút danh**, không nêu năm sinh/mất.
4. Cụ **sinh tại làng Tân Thới, Gia Định** (nay TP.HCM), không sinh ở Ba Tri — mô tả cũ dễ gây hiểu nhầm ngược lại.
5. Chi tiết "hội có bàn hốt thuốc nam miễn phí" (gắn nghề bốc thuốc của cụ) chỉ có ở Wikipedia, không đối chiếu được nguồn thứ hai ★★★+ → **đã loại**, dù rất hợp Curiosity test.
6. Không đụng `web/data.json`, không chạy ETL/DB, không git add/commit.

---

### 2.7 — Homestay Út Trinh (`homestay-ut-trinh`, accommodation, vinh-long)

> Ghi chú phiên của agent viết bản này: các thay đổi thấy ở `web/data.js` là đợt dọn thuật ngữ
> "tỉnh cũ" (dừa xanh, chùa Cò, muối Bảo Thạnh) của một phiên khác dùng chung worktree — không phải
> của bản viết này. Bản gốc: `docs/drafts/2026-08-07-homestay-ut-trinh-summary.md`

**Cũ (103 ký tự):** Nhà vườn 4 phòng trên cù lao An Bình — ngủ giữa vườn trái cây, chèo xuồng, ăn cơm nhà vườn với chủ nhà.

**Mới (397 ký tự):**
Giai đoạn 2017–2019, Homestay Út Trinh trên cù lao An Bình, Vĩnh Long là nơi duy nhất ở miền Nam đạt chuẩn ASEAN. Nhà chính là căn nhà cổ hơn trăm tuổi ở ấp Hòa Quý. Hai căn kế bên, Út Bình và Út Quỳnh, dựng năm 1953; cả cụm 14 phòng, tối đa 34 khách. Chủ nhà là bà Phạm Thị Ngọc Trinh, mở Mekong Travel năm 2005. Ban ngày hái trái, chèo xuồng bắt cá, đổ bánh xèo; tối có đờn ca tài tử và hát bội.

**Đọc kỹ tên entity (bẫy đã tránh):** "Út Trinh" là **tên người**, không phải địa danh — "Út" là từ xưng hô Nam Bộ chỉ con út, "Trinh" là tên chủ nhà Phạm Thị Ngọc Trinh. Đúng loại bẫy skill cảnh báo (tiền lệ "cá lăng hơ"). Hệ quả: hai căn phụ Út Bình/Út Quỳnh và cả cụm lân cận (Út Thủy, Sáu Thành, Năm Thành, Ba Lình) cùng theo lối đặt tên theo thứ bậc trong nhà.

**Nguồn từng fact:**
- "Chuẩn ASEAN Homestay 2017–2019, trao tại ATF 2017" → vinhlongtourist.vn (nguyên văn "ASEAN Homestay standard 2017 - 2019") + portal.vinhlong.gov.vn (★★★★ × 2)
- "Nơi duy nhất ở miền Nam" (cả nước 3 điểm Bắc/Trung/Nam, trao tại Singapore) → portal.vinhlong.gov.vn (★★★★, 1 nguồn)
- "Ấp Hòa Quý, cù lao An Bình" → vinhlongtourist.vn hồ sơ cơ sở + uttrinhhomestay.com (★★★★ + ★★★)
- "Cù lao nay thuộc xã An Bình" → `attributes.merged_from` của `xa-an-binh` + NQ 1687/NQ-UBTVQH15 (★★★★★)
- "Nhà chính là nhà cổ hơn 100 năm tuổi" → portal.vinhlong.gov.vn (★★★★)
- "Út Bình, Út Quỳnh dựng năm 1953" → portal.vinhlong.gov.vn (★★★★)
- "14 phòng, tối đa 34 khách" → uttrinhhomestay.com, trang chính chủ (★★★)
- "Phạm Thị Ngọc Trinh; Mekong Travel 2005" → portal.vinhlong.gov.vn + vinhlongtourist.vn (★★★★ × 2)
- "Hái trái, chèo xuồng bắt cá, làm bánh; đờn ca tài tử và hát bội" → vinhlongtourist.vn (★★★★) + uttrinhhomestay.com (★★★)
- **Đã bỏ:** giá (mâu thuẫn 3 chiều), "4 phòng" (sai), giải ASEAN 2023 (không thuộc entity này), khoảng cách tới điểm lân cận (`coords_approximate`)

**Tự kiểm:** **Substitution** — thay bằng Phương Thảo/Ngọc Phượng/Ba Lình thì sai cả 5 câu (Phương Thảo là kỳ 2019–2021, nhà 1953 và nhà cổ trăm tuổi là riêng cụm này, 14 phòng/34 khách và Mekong Travel 2005 không chuyển được) → đạt mạnh, không phải sửa. · **Deletion** — xoá C1 mất danh hiệu + định vị; C2 mất tuổi nhà (điểm khác biệt lớn nhất so với homestay xây mới); C3 mất quy mô thật; C4 mất "ai là chủ" — với homestay thì danh tính chủ nhà chính là sản phẩm; C5 mất phần "làm gì ở đó" → không câu nào filler, không xoá câu nào. · **Curiosity** — đạt: hook là danh hiệu kiểm chứng được thay vì lời khen chung; **hát bội** là chi tiết hiếm (hầu hết homestay miệt vườn chỉ có đờn ca tài tử) nên tự sinh câu hỏi. · **Đã sửa trong lúc viết:** bản đầu 497 ký tự với nhịp câu 27–25–25–8–25 từ (gần như đều tăm tắp, fail § Sentence rhythm) → rút còn 397 ký tự, nhịp 23–13–20–13–20 (xen dài–ngắn). Câu đầu 113/155 ký tự, NFC chuẩn, không mở bằng tên entity, không từ sáo rỗng, không "miền Tây"/"huyện"/tên tỉnh cũ, không tự gán nhãn kiểm-chứng-thực-địa (mỗi fact chỉ dẫn nguồn kèm hạng ★).

**Attributes đề xuất bổ sung:** `rooms` = **"14 phòng (tối đa 34 khách)"** — SỬA GẤP, hiện ghi "4 phòng" (uttrinhhomestay.com ★★★, kèm bảng phân loại 1+1+12 phòng cộng khớp đúng 34 khách) · `phone` = **"0919 002 505"** thay `phone_note` bị che (vinhlongtourist.vn ★★★★ + trang chính chủ ★★★) · `email` = vinhlongmekongtravel@yahoo.com (★★★★) · `address` thêm cấp ấp: "Ấp Hòa Quý, xã An Bình" + `former_address` "ấp Hòa Quý, xã Hòa Ninh, huyện Long Hồ (trước 7/2025)" · `award` = "ASEAN Homestay Standard 2017–2019 (ATF 2017, Singapore)" · `owner` = Phạm Thị Ngọc Trinh · `operator` = Mekong Travel (2005) · `built` = nhà chính >100 năm, Út Bình & Út Quỳnh 1953 · `package` = "ăn tối + phòng máy lạnh + ăn sáng" (★★★, giải thích chênh lệch giá) · `price` và `price_range` → **XOÁ hoặc để "liên hệ"** (không có nguồn đáng tin thống nhất).

**Cảnh báo:**
1. **Giá mâu thuẫn 3 chiều, đã cố ý bỏ khỏi mô tả.** `price` "từ 350.000đ/đêm" vs `price_range` "250.000–400.000đ/đêm" đá nhau **ngay trong cùng entity**; vinhlongtourist.vn (★★★★) ghi **800.000đ/khách**; foody.vn (★★) ghi 500.000–800.000đ/khách. Lệch 2–3 lần, nhiều khả năng lệch **đơn vị** (đ/đêm vs đ/khách, có/không kèm ăn tối). Nguồn data hiện chỉ là "Seed lưu trú" (★) → loại bỏ theo confidence gating. Cần gọi xác nhận trước khi hiển thị bất kỳ con số nào.
2. **"4 phòng" gần như chắc chắn là lỗi rớt chữ số của "14 phòng"** — không phải hai nguồn bất đồng. Lỗi này làm hỏng cả `summary` cũ lẫn `description`.
3. **Danh hiệu ASEAN có thời hạn** — kỳ 2017–2019, **không tìm thấy nguồn tái công nhận sau 2019**. Mô tả viết đúng thì quá khứ; **không được sửa thành "hiện đạt chuẩn ASEAN"**.
4. **KHÔNG gán giải ASEAN 2023 cho entity này** — giải ATF 2023 trao cho **cụm 6 hộ khác** (Út Thủy, Sáu Thành, Năm Thành, Ba Lình, Ngọc Phượng, Ngọc Sang), không có Út Trinh. Rất dễ nhầm vì cả ba kỳ đều là "homestay An Bình đạt giải ASEAN".
5. **Nghi trùng lặp entity — 3 bản ghi cho cùng 1–2 cơ sở thật.** `khu-du-lich-nha-xua-va-homestay-ut-trinh` mô tả đúng cơ sở này nhưng toạ độ (10.1834/105.9985) **không nằm trên cù lao An Bình** và nguồn chỉ là `agent discovery (cx/gpt-5.4)` → nghi bản ghi ảo do LLM sinh. `homestay-ut-trinh-con-tam-hiep` có `phone` "09190020505" = **0919002505 thừa một số**, và trang chính chủ xác nhận cơ sở thứ hai ở Bình Đại (cũ) → **cùng một chủ**. Nên gộp hoặc gắn `same_operator`, tránh hiển thị như 3 chỗ ở khác nhau.
6. **`verifiedAt` không phải bằng chứng kiểm chứng thực địa** — entity này có `verifiedAt` **trùng khít từng giây với `updatedAt`** (2026-06-28T02:24:21Z), các entity lân cận cũng vậy trong cùng phút → dấu hiệu auto-fill hàng loạt. Trái với giả định trong đề bài (verifiedAt = 0 toàn bộ): field **có giá trị nhưng vô nghĩa**. Theo §1.7 không được dùng làm căn cứ claim, đề xuất xoá để field giữ ý nghĩa thật.
7. Fact "3 điểm cả nước" chỉ 1 nguồn ★★★★ → đã hạ xuống cách diễn đạt an toàn hơn ("nơi duy nhất ở miền Nam") thay vì khẳng định con số cả nước.
8. **Gate 4 cross-reference chỉ đạt 1 entity** (`xa-an-binh`) do chạm trần 400 ký tự. Biến thể nối narrative thread An Bình sang nhà cổ Cai Cường có trong file nháp, kèm chi phí ký tự (431, phải đánh đổi bỏ "Mekong Travel 2005").

---

### 2.8 — Làng gạch gốm đỏ Mang Thít (`lang-gach-gom-do-mang-thit`, craft_village, vinh-long)

**Cũ (82 ký tự):** Khu làng nghề gạch gốm của tỉnh Vĩnh Long với hàng trăm miệng lò cũ kỹ, rêu phong.

**Mới (394 ký tự):**
Dọc kênh Thầy Cai ra sông Cổ Chiên, Vĩnh Long còn chừng 800 miệng lò hình tháp tròn — phần sót lại của khoảng 3.000 lò gạch gốm Mang Thít thời cao điểm. Lò đốt bằng trấu, mỗi mẻ chừng 20 ngày mới ra viên gạch đỏ son. Cùng thứ đất sét phù sa ấy cho ra dòng gốm đỏ không men. Cuối 2021, đề án Di sản đương đại Mang Thít dừng phá dỡ lò ở vùng lõi 3.600 ha, nay thuộc hai xã Nhơn Phú và Bình Phước.

*(Câu 1 = 152 ký tự, dùng được làm meta description; keyword "lò gạch gốm Mang Thít" + "Vĩnh Long" nằm trong câu đầu.)*

**Nguồn từng fact:**
- "dọc kênh Thầy Cai ra sông Cổ Chiên" → VnExpress "Làng gạch, gốm trăm năm ở Vĩnh Long" (nguyên văn: "ven kênh Thầy Cai đến đoạn giáp sông Cổ Chiên") + baodantoc.vn (★★★ × 2)
- "còn chừng 800 miệng lò" → VnExpress 2024 ("Hiện còn khoảng 800 lò gạch") + VOV 18/11/2022 ("khoảng 800 miệng lò", 126 cơ sở) (★★★ × 2)
- "hình tháp tròn" → VnExpress ("cao 7 m – 12 m, có hình như tháp tròn") (★★★)
- "khoảng 3.000 lò thời cao điểm" → VOV 2022 ("khoảng 2.800 miệng lò", 1.326 cơ sở) + VnExpress ("hơn 3.000 lò") — làm tròn hai nguồn (★★★ × 2)
- "đốt bằng trấu" → VnExpress ("dùng tro trấu để nung gạch") + langngheviet.com.vn + vinhlongtourist.vn (★★★ + ★★ × 2)
- "mỗi mẻ chừng 20 ngày" → VnExpress ("chứa khoảng 15.000 viên, nung trong 20 ngày thì ra thành phẩm") (★★★, đơn nguồn — xem Cảnh báo)
- "gốm đỏ không men, màu đỏ từ đất sét phù sa" → vinhlongtourist.vn "Câu chuyện về nghề gạch, gốm đỏ Vĩnh Long" + scov.gov.vn/thegioidisan.vn "Nghề làm gốm đỏ Vĩnh Long" (★★★★ cổng nhà nước + ★★★)
- "cuối 2021, đề án Di sản đương đại Mang Thít… dừng phá dỡ lò" → Cổng TTĐT Vĩnh Long (chuyendoiso.vinhlong.gov.vn): Quyết định 3502/QĐ-UBND ngày 20/12/2021 + Báo Vĩnh Long 12/2021 (★★★★)
- "vùng lõi 3.600 ha" → VOV 2022 + Cổng TTĐT Vĩnh Long (3.600 ha thuộc 4 xã Mỹ An, Mỹ Phước, Nhơn Phú, Hòa Tịnh; vùng đệm ~5.000 ha thuộc An Phước, Chánh An) (★★★★)
- "nay thuộc hai xã Nhơn Phú và Bình Phước" → Toàn văn Nghị quyết 1687/NQ-UBTVQH15 (xaydungchinhsach.chinhphu.vn): xã Nhơn Phú mới = Mỹ An + Mỹ Phước + Nhơn Phú; xã Bình Phước mới = Long Mỹ + Hòa Tịnh + Bình Phước (★★★★★) — khớp với `web/data.json` (`xa-nhon-phu`)

**Tự kiểm:** Substitution — thay "Làng gạch gốm Long Hồ" hay bất kỳ làng nghề nào vào thì cả 4 câu đều sai (kênh Thầy Cai, con số 800, đề án 3.600 ha, cặp xã Nhơn Phú/Bình Phước chỉ đúng entity này); đạt. · Deletion — đã cắt 2 câu ở bản nháp đầu: "điểm trải nghiệm di sản đặc trưng" (đúng cho ~50 entity) và "cũ kỹ, rêu phong" (tính từ, không phải fact); 4 câu còn lại xoá câu nào cũng mất một fact có nguồn. · Curiosity — hook là tương phản 3.000 → 800 cộng chi tiết nghề (trấu, 20 ngày, gạch đỏ son): đọc xong biết đây là thứ đang mất dần chứ không phải "điểm check-in", đủ lý do đi sớm; đạt.

**Attributes đề xuất bổ sung:**
- `heritage_project`: "Đề án Di sản đương đại Mang Thít — QĐ 3502/QĐ-UBND ngày 20/12/2021, vùng lõi ~3.600 ha + vùng đệm ~5.000 ha" (Cổng TTĐT Vĩnh Long, ★★★★)
- `planning`: "Quy hoạch chung Khu Di sản đương đại Mang Thít đến 2045, quy mô lập quy hoạch 3.060 ha (QĐ 1293/QĐ-UBND); dự báo dân số ~34.200 người (2030), ~61.900 người (2045)" (bvhttdl.gov.vn + baodautu.vn, ★★★★/★★★) — đây chính là nội dung đang nằm nhầm ở `summary` của bản `di-san-lo-gach-mang-thit-kenh-thay-cai` ("17 thg 7, 2024 · Quy mô khu vực lập quy hoạch khoảng 3.060ha", rõ ràng là mẩu SERP bị crawl)
- `kiln_count`: "~800 (ghi nhận 2022–2024); cao điểm ~2.800–3.000" (VOV + VnExpress, ★★★ × 2) — nên lưu kèm năm, đừng lưu số trần
- `technique`: "nung trấu; lò tháp tròn cao 7–12 m; ~15.000 viên/lò, ~20 ngày/mẻ" (VnExpress, ★★★)
- `product_history`: "gốm mỹ nghệ đỏ không men hình thành từ 1983, ký hợp đồng xuất khẩu đầu tiên 1993" (langngheviet.com.vn + scov.gov.vn, ★★★) — có nguồn nhưng cắt khỏi summary vì trần 400 ký tự
- `secondary_placeIds`: `xa-nhon-phu` + xã Bình Phước (vùng lõi trải 2 xã mới, không chỉ 1) — NQ 1687 (★★★★★)
- `admission` hiện có ("Miễn phí tham quan; 50.000đ trải nghiệm") và `hours` "7:00–17:00": **không truy được nguồn ≥★★** — đề xuất hạ xuống `unverified` hoặc bỏ, vì làng nghề là vùng dân cư mở, không có cổng bán vé thống nhất

**Cảnh báo:**
1. **`verifiedAt` giả.** Cả 4 bản ghi đều có `verifiedAt` = `updatedAt` = 2026-06-28T02:23–24Z (auto-stamp hàng loạt), không phải kiểm chứng thực địa. Theo §1.7 không được dùng trường này để hiển thị "đã xác minh" — bản nháp này không chứa claim xác minh nào.
2. **Coords mâu thuẫn — nghi bản kia sai, không phải bản này.** `[10.179, 106.106]` (bản này) rơi đúng vùng Nhơn Phú/kênh Thầy Cai. Cặp `[10.254177, 105.9627693]` trùng khít ở cả `lang-nghe-gom-do-mang-thit` và `lang-gach-gom-long-ho` → dấu hiệu toạ độ mặc định copy, và điểm đó nằm phía Long Hồ, lệch ~15 km khỏi vùng lò. Đề nghị giữ bản này làm canonical khi gộp trùng lặp.
3. **"20 ngày/mẻ" là cách đếm của VnExpress (★★★, đơn nguồn).** Nguồn ★★ khác tách chu trình thành 5 ngày tải/dỡ + 15 ngày nung + 7 ngày nguội (~1,5 tháng, ~120.000 viên) — khác cả cách đếm lẫn sản lượng. Đã chọn con số VnExpress và hedge bằng "chừng"; nếu chủ dự án muốn chắc hơn thì viết "nung khoảng nửa tháng, cả chu trình gần tháng rưỡi".
4. **Số lò 800 đã cũ (2022 & 2024).** Không tìm được số liệu 2025–2026; nếu sau này có số mới thì phải sửa, hoặc hiển thị kèm mốc năm.
5. **"Mang Thít" trong tên entity không còn là đơn vị hành chính** (huyện Mang Thít chấm dứt từ 1/7/2025). Trong bản nháp, "Mang Thít" chỉ đứng với tư cách tên làng nghề và tên đề án — hợp lệ. Đừng để frontend/breadcrumb tự sinh ra "huyện Mang Thít".
6. **Fact bị loại vì nguồn yếu:** "hình thành hơn 200 năm" (baodantoc.vn ★★★ nhưng chỏi với VnExpress "khoảng 100 năm" và mốc "cuối XIX – đầu XX" của các nguồn khác → mâu thuẫn, bỏ); giai thoại tên kênh Thầy Cai theo cai tổng Huỳnh Đình Ngộ (1876–1946) có 2 nguồn ★★★ (vovgiaothong.vn, baoquankhu9.com.vn) nhưng đều dẫn lời truyền khẩu "theo các lão nông" và không xác định được năm đào → để dành cho bài viết dài, không đưa vào summary.
7. Không ghi file, không đụng `web/data.json`/DB/git theo ràng buộc.

---

### 2.9 — Xã An Bình (`xa-an-binh`, place, vinh-long)

**Cũ (116 ký tự):** Xã An Bình thuộc tỉnh Vĩnh Long, gộp từ xã Hòa Ninh, xã Bình Hòa Phước, xã Đồng Phú và xã An Bình của huyện Long Hồ.

**Mới (411 ký tự):**
Trọn một cù lao giữa sông Tiền và sông Cổ Chiên là xã An Bình, tỉnh Vĩnh Long — đầu thế kỷ 20 còn gọi Bãi Tiên Châu. Bốn xã cũ Hòa Ninh, Bình Hòa Phước, Đồng Phú, An Bình nhập lại ngày 1-7-2025: gần 62 km², hơn 51.000 người. Tên Bãi Tiên còn trong chùa Tiên Châu mé Cổ Chiên — am dựng giữa thế kỷ 18, di tích quốc gia năm 1994. Nhà cổ Cai Cường dựng năm 1885; chôm chôm Java rộ tháng 3–7, vụ nghịch hái tới Tết.

**Nguồn từng fact:**
- "Trọn một cù lao ... là xã An Bình" (toàn bộ cù lao An Bình thuộc xã An Bình) → Wikipedia *Cù lao An Bình* (có chú thích) (★★★★)
- "giữa sông Tiền và sông Cổ Chiên" → Wikipedia *Cù lao An Bình* + Wikipedia *An Bình, Vĩnh Long* (bắc giáp sông Mỹ Tho — nhánh sông Tiền, nam giáp sông Cổ Chiên) (★★★★)
- "đầu thế kỷ 20 còn gọi Bãi Tiên Châu" → Wikipedia *Cù lao An Bình* (ghi Bích Trân / Tiên Châu, có chú thích) (★★★★)
- "Bốn xã cũ Hòa Ninh, Bình Hòa Phước, Đồng Phú, An Bình nhập lại" → Nghị quyết 1687/NQ-UBTVQH15 khoản 5 Điều 1, toàn văn trên xaydungchinhsach.chinhphu.vn (★★★★★)
- "ngày 1-7-2025" (ngày chính thức hoạt động; NQ thông qua 16-6-2025) → cùng nguồn NQ 1687 (★★★★★)
- "gần 62 km², hơn 51.000 người" → Wikipedia *An Bình, Vĩnh Long*: 61,84 km²; 51.382 người (31-12-2024) (★★★★)
- "chùa Tiên Châu mé Cổ Chiên — am dựng giữa thế kỷ 18" → thesaigontimes.vn + baocantho.com.vn + vietnamnet.vn (am Bãi Tiên, HT Giác Nguyên 1750–1801) (★★★ × 3)
- "di tích quốc gia năm 1994" → cùng cụm 3 nguồn trên (xếp hạng di tích kiến trúc nghệ thuật cấp quốc gia 12-12-1994) (★★★ × 3)
- "Nhà cổ Cai Cường dựng năm 1885" → baodaklak.vn + vietnam.vnanet.vn (TTXVN): xây năm Ất Dậu 1885, chủ nhân cai tổng Phạm Văn Bốn (★★★ × 2)
- "chôm chôm Java rộ tháng 3–7, vụ nghịch" → vinhlongtourist.vn (cổng du lịch tỉnh) + mia.vn: Bình Hòa Phước ~400 ha, ~90% giống Java, vụ chính tháng 3–7, vụ nghịch tháng 10–3 (★★★ + ★★)

**Tự kiểm:** Substitution — đạt, thay "An Bình" bằng xã khác thì sai ngay ở 4 chỗ neo (cù lao trọn vẹn, 61,84 km², chùa Tiên Châu 1994, nhà cổ Cai Cường 1885); bản nháp đầu mở bằng "Nằm giữa sông Tiền..." dùng chung được cho nhiều xã ven sông nên đã đổi thành "Trọn một cù lao" (đặc điểm chỉ đúng xã này). · Deletion — đạt sau khi xoá 2 câu: câu "chia 15 ấp" (không đổi hiểu biết người đọc) và mệnh đề "mặt quay ra rạch Cái Muối"; mỗi câu còn lại mất đi là mất fact riêng (địa mạo/tên cũ · hành chính+số liệu · di tích+niên đại · kiến trúc+mùa vụ). · Curiosity — đạt: sợi dây "Bãi Tiên Châu → am Bãi Tiên → chùa Tiên Châu" tạo tò mò về tên đất, "vụ nghịch hái tới Tết" cho lý do đi ngoài mùa chính. Nhịp câu 116/107/102/83 ký tự (dài→ngắn dần), không câu nào mở bằng tên entity.

**Attributes đề xuất bổ sung:**
- `area_km2: 61.84` — Wikipedia *An Bình, Vĩnh Long* (★★★★)
- `population: 51382`, `population_asof: "2024-12-31"` — cùng nguồn (★★★★)
- `hamlet_count: 15` (An Hòa, An Thành, An Thới, Bình Hòa Phước, Bình Lương, Đồng Phú, Hòa Ninh, Hòa Quí, Hòa Thạnh, Hòa Thuận, Phú An, Phú Mỹ, Phú Thạnh, Phú Thuận, Phước Định) — cùng nguồn (★★★★)
- `merge_decree: "1687/NQ-UBTVQH15"`, `merge_decree_date: "2025-06-16"`, `effective_from: "2025-07-01"` — toàn văn NQ trên chinhphu.vn (★★★★★)
- `landform: "cù lao"` / `is_island: true`; `rivers: ["sông Tiền", "sông Cổ Chiên"]` — Wikipedia *Cù lao An Bình* (★★★★)
- `former_names: ["Bích Trân", "Bãi Tiên Châu"]` (đầu thế kỷ 20) — Wikipedia *Cù lao An Bình* (★★★★)
- `placeId`: SỬA LỖI — đang là `"p-long-chau"` (Long Châu là phường bên kia sông), phải trỏ về chính xã An Bình
- `coordinates`: cân nhắc cập nhật — data hiện `[10.280843, 105.997718]` (`coords_source: nominatim`, `coords_approximate: true`); Wikipedia ghi 10°17′31″N 105°59′03″E ≈ `[10.29207, 105.98407]`, lệch ~1,6 km

**Cảnh báo:**
1. **`verifiedAt` đang CÓ giá trị** `"2026-06-28T02:24:28Z"` trên entity này (trái với mô tả trong đề bài là 0 entity có), trong khi `source` chỉ là `"vinhlong360 auto-learn"` (method: internal) — tức không phải kiểm chứng thực địa. Theo §1.7, trường này đang bị đóng dấu tự động và **không được dùng làm căn cứ cho bất kỳ claim "đã xác minh" nào**; đề xuất chủ dự án xoá/để trống `verifiedAt` cho tới khi có kiểm chứng thật. Bản nháp trên không chứa claim xác minh nào.
2. **Mâu thuẫn số liệu giữa các nguồn:** fptshop.com.vn và congtyluatacc.vn (đều ★, nội dung tổng hợp) ghi "hơn 3.400 ha, hơn 28.000 người" — lệch xa Wikipedia (61,84 km² = 6.184 ha; 51.382 người) và lệch cả với diện tích cù lao ~60 km². Đã loại nhóm nguồn ★, dùng số Wikipedia và **làm tròn xuống** ("gần 62 km²", "hơn 51.000 người") theo confidence gating. Nếu chủ dự án có số của Chi cục Thống kê tỉnh thì nên đè lên.
3. **"vụ nghịch hái tới Tết" là suy luận nhẹ** từ khoảng "tháng 10 – tháng 3" của nguồn (Tết nằm trong khoảng này), không phải câu chữ của nguồn. Nếu muốn tuyệt đối bám nguồn, thay bằng: `chôm chôm Java rộ tháng 3–7, vụ nghịch hái từ tháng 10 tới tháng 3.` (tổng thành 421 ký tự).
4. **Đã chủ động KHÔNG nhắc Khu du lịch Vinh Sang** dù nó nằm trong nhóm 97 quan hệ: chưa xác minh được tình trạng hoạt động hiện tại của điểm này, đưa vào summary là rủi ro nội dung chết. Cần kiểm riêng trước khi cross-reference.
5. **Độ dài 411 ký tự, vượt gate SEO (150–400) ~3%.** Giữ nguyên có chủ đích vì đây là entity hub (97 quan hệ, cù lao du lịch lõi); nếu chủ dự án muốn siết đúng gate, cắt mệnh đề `Nhà cổ Cai Cường dựng năm 1885;` (còn 380 ký tự) — nhà cổ đã có entity riêng để dẫn link.
6. Bản nháp không ghi "huyện Long Hồ" ở thì hiện tại (cấp huyện đã bỏ); `former_district: "H. Long Hồ"` chỉ nên hiển thị trong khối lịch sử, không đưa vào summary.

---

### 2.10 — Xã Chợ Lách (`xa-cho-lach`, place, ben-tre)

> Bản gốc: `docs/drafts/2026-08-07-xa-cho-lach-summary.md`

**Cũ (110 ký tự):** Xã Chợ Lách thuộc huyện Chợ Lách, tỉnh Bến Tre, ra đời khi TT Chợ Lách, xã Hòa Nghĩa và xã Long Thới nhập lại.

**Mới (401 ký tự):**
Kẹp giữa sông Cổ Chiên và Hàm Luông, xã Chợ Lách của tỉnh Vĩnh Long sống bằng cây giống, hoa kiểng, sầu riêng, chôm chôm. Hoa Tết tính bằng triệu chậu; cúc mâm xôi đạt OCOP 3 sao. Xã ra đời 16/6/2025 từ thị trấn Chợ Lách và hai xã Long Thới, Hòa Nghĩa (Bến Tre cũ): 49,72 km², 15 ấp, hơn 44.000 dân. Kênh Chợ Lách hơn 10 km cắt ngang xã, nối Cổ Chiên với sông Tiền, rút gần 80 km đường thủy về TP.HCM.

**Nguồn từng fact:**
- "thuộc tỉnh Vĩnh Long" → NQ 202/2025/QH15 (12/6/2025), dẫn qua Wikipedia — Chợ Lách (xã) (★★★★★)
- "ra đời 16/6/2025 từ thị trấn Chợ Lách + Long Thới + Hòa Nghĩa" → NQ 1687/NQ-UBTVQH15, dẫn qua Wikipedia — Chợ Lách (xã) (★★★★★); khớp `attributes.merged_from`
- "49,72 km²" → Công văn 2896/BNV-CQĐP (27/5/2025), dẫn qua Wikipedia (★★★★★)
- "hơn 44.000 dân" (44.316 người, 31/12/2024) và "15 ấp" → Wikipedia — Chợ Lách (xã) (★★★★)
- "kẹp giữa sông Cổ Chiên và Hàm Luông" → Wikipedia xã + Wikipedia — Chợ Lách (huyện) ("chiều ngang giới hạn bởi hai bờ của con sông Cổ Chiên và Hàm Luông") (★★★★)
- "sống bằng cây giống, hoa kiểng" (hơn 1.000 ha) + "sầu riêng, chôm chôm" (~2.500 ha) → SGGP 4/3/2026 (★★★)
- "hoa Tết tính bằng triệu chậu" → Báo Vĩnh Long 25/10/2025 (~2,5 triệu sản phẩm vụ Tết 2026) + SGGP (★★★ ×2)
- "cúc mâm xôi đạt OCOP 3 sao" → Báo Vĩnh Long 25/10/2025 + SGGP 4/3/2026, hai nguồn trùng (★★★ ×2)
- "kênh Chợ Lách hơn 10 km, nối Cổ Chiên với sông Tiền, rút gần 80 km" → Báo Pháp Luật TP.HCM 8/9/2024 (★★★)

**Tự kiểm:** Substitution — bản đầu ("kẹp giữa hai sông + làm cây giống hoa kiểng") thay tên "xã Vĩnh Thành" vào vẫn đúng → FAIL, đã sửa bằng 3 dữ kiện chỉ đúng xã này (mốc 16/6/2025 với đúng bộ ba đơn vị cũ; 49,72 km²/15 ấp; kênh Chợ Lách) · Deletion — xoá thử từng câu đều mất thông tin cụ thể, không còn filler; trong lúc viết đã cắt bỏ thật câu "vương quốc cây giống hoa kiểng" (mỹ từ, đúng cho cả 4 xã Chợ Lách cũ) và cụm "miệt vườn trù phú" · Curiosity — đạt: con kênh cắt tắt cho sà lan và quy mô hoa Tết là hai chi tiết phân biệt rõ xã này với xã lân cận. Lưu ý 401 ký tự, nhỉnh 1 so với trần 400 của Gate 3.

**Attributes đề xuất bổ sung:** `area_km2: 49.72` (CV 2896/BNV-CQĐP 27/5/2025 ★★★★★) · `population: 44316` + `population_as_of: "2024-12-31"` (Wikipedia có dẫn nguồn ★★★★) · `so_ap: 15` — An Phú, Bình An, Bình Thanh, Bình Sơn, Định Bình, Đại An, Hòa Nghĩa, Hòa Thạnh, Long Hòa, Long Hiệp, Long Quới, Long Thới, Sơn Qui, Quân An, Vinh Huê (★★★★) · `established: "2025-06-16"` + `legal_basis: "NQ 1687/NQ-UBTVQH15"` (★★★★★) · `former_province: "Bến Tre"` (bổ sung cho `former_district` đã có) · `ocop: ["Cúc mâm xôi Chợ Lách — 3 sao"]` (★★★ ×2). KHÔNG đề xuất: diện tích cây giống/hoa kiểng, sản lượng cây giống/năm, từ nguyên tên "Chợ Lách" — không có nguồn đủ tin/nhất quán.

**Cảnh báo:**
1. **Quan hệ sai địa bàn** — trong 24 quan hệ có "chôm chôm Cái Mơn" và "cồn Phú Đa", cả hai KHÔNG nằm trong xã Chợ Lách mới (Cái Mơn thuộc xã Vĩnh Thành cũ, cồn Phú Đa thuộc xã Vĩnh Bình cũ); mô tả mới cố ý không nhắc Cái Mơn dù đó là từ khóa mạnh nhất — đề nghị rà lại tập quan hệ theo ranh giới xã mới.
2. **Nguồn vênh sản lượng**: SGGP "trên 7 triệu cây giống + ~5 triệu hoa kiểng/năm" vs Báo Vĩnh Long "~4 triệu hoa kiểng + 5 triệu cây giống/năm" vs Đồng Khởi 19/8/2024 "mục tiêu 17–20 triệu cây giống/năm (toàn huyện cũ)" → đã viết "tính bằng triệu chậu", không chốt số.
3. **Diện tích trồng vênh**: 1.000 ha (SGGP) vs ~1.500 ha (Báo Vĩnh Long) → đã bỏ khỏi mô tả.
4. Infobox Wikipedia xã còn liệt kê sông Mỹ Tho phía Tây Bắc; chỉ giữ Cổ Chiên + Hàm Luông vì hai trang Wikipedia nói trùng nhau.
5. **Từ nguyên "lách" chưa xác minh** — đã search theo quy tắc "đọc kỹ tên entity", không nguồn ≥★★ nào khẳng định "lách" là tên cây (cỏ lách/sậy) hay biến âm của "lạch" (dòng nước nhỏ) → BỎ.
6. Entity có `verifiedAt: "2026-06-28T02:24:29Z"` trùng khít `updatedAt` — nhiều khả năng là dấu vết ghi máy chứ không phải kiểm chứng thực địa; bản nháp không chứa claim "đã xác minh" nào (§1.7), đề nghị rà xem trường này có bị set nhầm hàng loạt.
7. `confidence: 0.91` trong khi nội dung cũ sai định vị hành chính → nên đánh giá lại thang confidence cho cả lô.

---

## 3. Cần chủ dự án quyết

### A. Vấn đề xuyên suốt — `verifiedAt` bị đóng dấu hàng loạt

Đề bài giả định `verifiedAt` = 0 cho toàn bộ entity. **Sai với thực tế dữ liệu.** Ít nhất 7/10 entity
trong lô có `verifiedAt` **trùng khít từng giây với `updatedAt`**, tất cả rơi vào cụm
`2026-06-28T02:23–02:24Z`:

| Entity | `verifiedAt` ghi nhận |
|---|---|
| `con-phung-con-ong-dao-dua` | 2026-06-28T02:23:47Z |
| `khu-di-tich-nguyen-dinh-chieu` | 2026-06-28T02:23:56Z (kèm `verified: 1`) |
| `bun-suong` | 2026-06-28T02:24:04Z |
| `homestay-ut-trinh` | 2026-06-28T02:24:21Z |
| `xa-an-binh` | 2026-06-28T02:24:28Z (`source: "vinhlong360 auto-learn"`) |
| `xa-cho-lach` | 2026-06-28T02:24:29Z |
| `lang-gach-gom-do-mang-thit` (4 bản ghi) | 2026-06-28T02:23–24Z |

Trong khi đó bản 5 (`chua-ang-*`) báo `verifiedAt` **vẫn rỗng** → trường này không đồng nhất trên
dataset. **Quyết định cần có:** (a) trường này nghĩa là gì; (b) có xoá dấu auto-stamp không; (c) nếu
giữ thì phải khoá không cho front-end hiển thị nó dưới bất kỳ nhãn kiểm-chứng-thực-địa nào (§1.7).
Trước khi có quyết định này, **không dùng `verifiedAt` cho E-E-A-T hay pitch B2G**.

### B. Fact chỉ có 1 nguồn ★★ (hoặc yếu hơn) — đã viết dè dặt hoặc đã bỏ, chờ quyết

| Entity | Fact | Xử lý đã làm | Cần quyết |
|---|---|---|---|
| Nhà cổ Cai Cường | "Số 38, ấp Bình Hòa" (số nhà/ấp) | đưa vào đề xuất `address`, không vào summary | có ghi số nhà không? |
| Nhà cổ Cai Cường | vé ~20.000đ/khách | bỏ khỏi summary | gọi hỏi trực tiếp |
| Cồn Phụng | "ăn dừa suốt 25 năm (1945–1970)" | bỏ số 25 năm | bỏ hẳn hay giữ dạng "tương truyền"? |
| Cồn Phụng | tháp "9 tầng"; bộ Tứ linh 4 cồn | không đưa vào summary | cần nguồn ★★★ trước khi ghi `key_facts` |
| Bún suông | `price_range` 30.000–80.000đ | bỏ | không hiển thị giá, hay đi khảo giá? |
| Chùa Âng | hào nước + "hàng trăm gốc sao dầu" (mia.vn ★★, có Wikipedia đỡ) | giữ, viết "hàng trăm" | chấp nhận không? |
| Chùa Âng | ngày xếp hạng 25/8/1994 (vntrip ★★) | chọn 20/7/1994 (QĐ 921-QĐ/BT) | xác nhận sửa `chua-ang` |
| Homestay Út Trinh | giá 500.000–800.000đ (foody ★★) | bỏ toàn bộ giá | để "liên hệ" theo §1.4? |
| Mang Thít | `admission` "50.000đ trải nghiệm", `hours` 7–17 | đề xuất hạ `unverified` | xoá hay giữ? |
| Xã An Bình | chôm chôm Java (mia.vn ★★ + vinhlongtourist ★★★) | giữ | ok |
| Xã Chợ Lách | từ nguyên "lách" | BỎ hẳn | có đi tìm nguồn địa chí không? |
| Dừa sáp | "chỉ 9/93 nước trồng dừa có dừa sáp" | BỎ (không fetch được thân trang) | có worth đi tìm bản PDF công báo? |

### C. Mâu thuẫn trực tiếp với `attributes` hiện có — 10/10 entity đều có ít nhất một

| Entity | Trường | Giá trị trong data | Nghiên cứu nói | Mức |
|---|---|---|---|---|
| Nhà cổ Cai Cường | `placeId` / `address` | `p-long-chau` / "Phường Long Châu" | ấp Bình Hòa, xã An Bình | **SAI địa bàn** |
| Nhà cổ Cai Cường | `admission` | "Miễn phí" | ~20.000đ (★★) | mâu thuẫn |
| Cồn Phụng | `coordinates` | [10.2376, 106.3758] | [10.3333, 106.3565] | lệch **~10,6 km** |
| Cồn Phụng | `booking_note` | "đặt tour trọn gói… 95.000đ/khách" | — | **vi phạm §1.4** |
| Cồn Phụng | `founder` | 1910 / 22-4-1910 | 25-12-1910 hoặc 1909 | 3 giá trị đá nhau |
| Bún suông | `placeId` / `coordinates` | `xa-nhi-long` / Càng Long cũ | nội ô Trà Vinh | **SAI địa bàn** |
| Bún suông | `specialty` | "Bún, Cá" | không nguồn nào có cá | sai |
| Dừa sáp Cầu Kè | `area_ha` | 750 | 1.145 (7/2025) → 1.229,5 (11/2025) | lỗi thời |
| Dừa sáp Cầu Kè | `origin` | "giống từ Campuchia" | hai luồng: Campuchia vs quà bạn học Philippines | **chưa chốt được** |
| Dừa sáp Cầu Kè | `price_range` | 60.000–120.000đ | 120.000–200.000đ (★★★★) | mâu thuẫn |
| Chùa Âng | `placeId` (các bản ghi trùng) | `p-long-duc`, `p-tra-vinh` | `p-nguyet-hoa` | **SAI địa bàn** |
| Chùa Âng | tên entity | "Wat Angkor Raig Borei" | Angkorajaborey | chuyển tự sai |
| Nguyễn Đình Chiểu | `architectural_style` | "Đình làng" | đền thờ mới hình **tròn**, BTCT | **SAI sự thật** |
| Homestay Út Trinh | `rooms` | "4 phòng" | 14 phòng / 34 khách | **SAI (rớt chữ số)** |
| Homestay Út Trinh | `price` vs `price_range` | 350k/đêm vs 250–400k/đêm | nguồn tỉnh: 800k/khách | đá nhau trong cùng entity |
| Mang Thít | `coordinates` (bản trùng) | [10.2541, 105.9627] dùng chung 2 entity | vùng Nhơn Phú | lệch ~15 km |
| Xã An Bình | `placeId` | `p-long-chau` | chính xã An Bình | **SAI địa bàn** |
| Xã An Bình | `coordinates` | [10.2808, 105.9977] approx | [10.29207, 105.98407] | lệch ~1,6 km |
| Xã Chợ Lách | `relationships` | có "chôm chôm Cái Mơn", "cồn Phú Đa" | không thuộc xã mới | quan hệ sai |
| Xã Chợ Lách | `confidence` | 0.91 | nội dung cũ sai định vị hành chính | thang điểm không tin được |

**Lỗi `p-long-chau` xuất hiện ở 2 entity khác nhau** (nhà cổ Cai Cường và chính xã An Bình) → nghi
lỗi hệ thống trong bước gán `placeId`, không phải lỗi lẻ. Đáng kiểm cả 1.746 entity.

### D. Trùng lặp entity — 5/10 entity trong lô có bản ghi song trùng

- `bun-suong` ↔ `bun-suong-tra-vinh` (+ `lang-nghe-bun-suong` sai `type`)
- `dua-sap-cau-ke` ↔ `dua-sap`, `dua-sap-tra-vinh`, `dua-sap-hoa-tan`, `dua-sap-cang-long`,
  `vung-trong-dua-sap-cau-ke`, và `dua-sap-cau-ke-dac-san-ben-tre` (**summary nói về kẹo dừa, sai
  hoàn toàn**)
- `chua-ang-*` — 4 bản ghi + 2 bản ghi quán ăn "gần chùa" cũng ghi địa chỉ cũ
- `homestay-ut-trinh` ↔ `khu-du-lich-nha-xua-va-homestay-ut-trinh` (nghi bản ghi ảo do LLM sinh) ↔
  `homestay-ut-trinh-con-tam-hiep` (số điện thoại thừa 1 chữ số)
- `lang-gach-gom-do-mang-thit` ↔ `lang-nghe-gom-do-mang-thit`, `lang-gach-gom-long-ho`,
  `di-san-lo-gach-mang-thit-kenh-thay-cai` (**summary là mẩu SERP bị crawl**)

**Quyết định cần có:** gộp trước rồi mới viết summary, hay viết trước rồi gộp? Nếu viết trước, sẽ có
nhiều trang cạnh tranh cùng một keyword và công viết bị lãng phí ở các bản ghi sắp bị gộp.

### E. Entity mà research KHÔNG ra đủ thông tin

| Entity | Thiếu gì | Vì sao |
|---|---|---|
| Chùa Âng | số sư hiện tại, trường Pali/lớp chữ Khmer, kinh lá buông, kích thước chánh điện | banquanlyditichtravinh.vn **ECONNREFUSED**; nguồn còn lại mô tả lệch nhau |
| Dừa sáp Cầu Kè | thân trang Cục SHTT (số liệu 9/93 nước), giá hiện hành | ipvietnam.gov.vn **lỗi chứng chỉ TLS**; skhcn.travinh.gov.vn **không phân giải DNS** |
| Mang Thít | số lò 2025–2026; tuổi nghề (100 vs 200 năm) | không có số liệu mới; nguồn ★★★ chỏi nhau |
| Homestay Út Trinh | giá thật; có tái công nhận ASEAN sau 2019 không | không nguồn; cần gọi điện |
| Bún suông | giá hiện tại; từ nguyên tên | nguồn báo mới nhất là 2015 |
| Nhà cổ Cai Cường | chất liệu nền (gạch bông vs đá xanh); có xếp hạng di tích không | 2 mạch nguồn nói khác nhau; không nguồn nào nói về xếp hạng |
| Xã An Bình | tình trạng hoạt động KDL Vinh Sang | chưa kiểm được → đã bỏ khỏi summary |
| Xã Chợ Lách | sản lượng cây giống/hoa kiểng | 3 nguồn cho 3 con số khác nhau |

→ Nhóm này cần **kiểm chứng thực địa hoặc gọi điện**, không giải quyết được bằng thêm search.

### F. Vấn đề biên tập cần chủ dự án cho hướng

1. **Vượt trần 400 ký tự:** #9 = 411 (+2,75%), #10 = 401 (+0,25%). Cắt cho đúng gate, hay nới gate
   cho entity hub? Bản 9 đã đề xuất sẵn phương án cắt còn 380.
2. **"Trà Vinh" đứng một mình có gây hiểu nhầm không?** Bản 3 ("Dân Trà Vinh gọi…", "nội ô Trà Vinh")
   và bản 5 ("các chùa Khmer đất Trà Vinh") dùng "Trà Vinh" như tên địa phương (nay là phường), không
   phải tên tỉnh. Đúng luật §1.6 về mặt kỹ thuật, nhưng người đọc có thể hiểu thành tỉnh cũ. Cần chốt
   quy ước: viết "phường Trà Vinh", "nội ô Trà Vinh", hay thêm chú thích?
3. ~~**Bốn bản (2, 4, 7, 8) bị cắt cụt ở phần cảnh báo cuối.**~~ **ĐÃ XỬ LÝ (2026-08-07):** phần đuôi
   bị mất là do bản gộp cắt mỗi kết quả agent ở 6.000 ký tự, không phải do agent viết thiếu. Đã lấy lại
   nguyên văn từ journal workflow (`wf_2282932e-446/journal.jsonl`) và ghép trở lại: bản 2 thêm cảnh báo
   #4 (đuôi) + #5 + #6, bản 4 thêm #6 (đuôi) + #7 + #8, bản 7 thêm #6 (đuôi) + #7 + #8, bản 8 thêm #6
   (đuôi) + #7. Không mục nào phải bịa. Tổng cảnh báo chốt lại: **70**.
4. **Mâu thuẫn nội bộ giữa 2 bản trong chính lô này:** bản 1 chốt tên chủ nhà cổ là "Phạm Văn **Bổn**"
   (theo TTXVN/scov), bản 9 lại dẫn cùng nguồn TTXVN mà ghi "Phạm Văn **Bốn**". Phải thống nhất một
   cách viết trước khi ghi vào dữ liệu.
5. **`booking_note` của Cồn Phụng vi phạm §1.4** (bán tour, có giá/khách). Đây là lỗi dữ liệu có rủi
   ro pháp lý nhẹ, nên rà toàn bộ dataset xem còn bao nhiêu trường tương tự.
6. **Ảnh:** cả 10 entity đều chưa có ảnh thật. Theo §1.5 chỉ dùng ảnh AI qua `scripts/gen_image.py`
   và phải giữ nhãn `dc-nophoto-note`. Nội dung tốt lên nhưng trang vẫn trống ảnh — cần quyết có chạy
   luồng ảnh song song không.

---

## 4. Ước lượng quy mô cho 150 entity

### 4.1 ĐO ĐƯỢC (từ chính lô này, đếm được, không suy diễn)

| Chỉ số | Giá trị |
|---|---|
| Số entity | 10 |
| Tổng ký tự summary cũ | 1.143 (TB 114,3 · min 78 · max 168) |
| Tổng ký tự summary mới | 3.996 (TB 399,6 · min 394 · max 411) |
| Hệ số nở nội dung | **×3,5** |
| Entity vượt trần 400 ký tự | 2/10 |
| Entity có ≥1 cảnh báo | **10/10** |
| Entity có đề xuất sửa `attributes` | **10/10** |
| Tổng mục cảnh báo đếm được | **70** (TB 7,0/entity; min 6 · max 8 — đã khôi phục đủ 4 danh sách từng bị cắt) |
| Entity có lỗi định vị (`placeId`/`coordinates`/`address`) | **7/10** |
| Entity có bản ghi trùng lặp | **5/10** |
| Entity có `verifiedAt` auto-stamp | **7/10** (1/10 báo rỗng → trường không đồng nhất) |
| Fact bị LOẠI vì nguồn yếu (ghi rõ trong bản) | ≥25 fact trên 10 entity |
| Nguồn ngoài truy cập thất bại | 3 tên miền (ipvietnam.gov.vn TLS, skhcn.travinh.gov.vn DNS, banquanlyditichtravinh.vn ECONNREFUSED) |

**Không đo được từ lô này:** thời gian thực tế/entity, số lượt WebSearch/WebFetch/entity, số vòng
sửa trung bình. Các bản viết không ghi lại các chỉ số đó. Mọi con số công sức bên dưới vì vậy là
**suy luận**, không phải đo.

### 4.2 SUY LUẬN (ngoại suy — có giả định, có thể sai)

**Suy luận 1 — khối lượng nghiên cứu.** Mỗi bản có 8–11 fact được truy nguồn riêng, mỗi fact cần
1–2 truy vấn để tìm + ít nhất 1 nguồn thứ hai để đối chiếu. Ngoại suy: **8–15 lượt search/entity**
→ 150 entity ≈ **1.200–2.250 lượt search**. Giả định: entity sau khó tra tương đương entity trong lô.

**Suy luận 2 — khối lượng dọn dữ liệu lớn hơn khối lượng viết.** Nếu tỉ lệ 6,3 cảnh báo/entity giữ
nguyên → 150 entity sinh ra **~950 mục cảnh báo**, phần lớn KHÔNG phải việc viết lách (placeId sai,
toạ độ lệch, trùng lặp, `verifiedAt`, trường vi phạm §1.4). Nói cách khác: chạy 150 entity sẽ **đẻ ra
một backlog dọn dữ liệu lớn hơn chính công việc viết**. Đây là hệ quả quan trọng nhất của lô mẫu.

**Suy luận 3 — nên tách hai luồng.**
- Luồng A (viết summary): cần research, cần người đọc duyệt giọng văn.
- Luồng B (sửa dữ liệu: `placeId`, `coordinates`, gộp trùng, `verifiedAt`, `booking_note`): chủ yếu
  là script + đối chiếu, không cần viết.
Nếu chạy A mà không chạy B, nội dung tốt vẫn hiển thị sai breadcrumb/SEO/bản đồ, và một phần công
viết rơi vào bản ghi sắp bị gộp. **Đề nghị B chạy trước hoặc song song.**

**Suy luận 4 — lô mẫu KHÔNG đại diện (điểm yếu lớn nhất của ước lượng này).** Cả 10 entity đều là
entity đầu bảng: di tích quốc gia, đặc sản có chỉ dẫn địa lý, xã lớn. Chúng có nguồn ★★★★ dồi dào.
150 entity kế tiếp sẽ gồm nhiều xã nhỏ, quán ăn, cơ sở lưu trú lẻ — nhóm mà skill (§0 bước 5) đã
lường trước là "1–2 search không ra gì mới = dừng, viết summary tối thiểu". Ngoại suy hợp lý:
**30–50% entity trong 150 sẽ chỉ viết được ở tầng C (100–150 ký tự)**, không đạt 400 ký tự như lô
này. Đừng lấy TB 399,6 ký tự làm kỳ vọng cho toàn bộ.

**Suy luận 5 — nhịp chạy đề xuất.** Skill §5 yêu cầu diversity scoring mỗi 10 entity và vocabulary
budget xuyên batch → lô 10–15 entity/phiên là kích thước tự nhiên. 150 entity ≈ **10–15 lô**.
Sau mỗi 3 lô nên dừng cho chủ dự án duyệt lại giọng, tránh trôi 150 bản rồi mới phát hiện lệch hướng.

**Suy luận 6 — chi phí ngoài LLM = 0.** Không có dịch vụ trả phí nào cần thêm (§B8). Chi phí duy nhất
là thời gian duyệt của chủ dự án, và nó tỉ lệ thuận với số cảnh báo — tức với 150 entity thì **việc
duyệt, chứ không phải việc viết, mới là nút thắt**.

---

## 5. Nhắc lại phạm vi

Văn bản này KHÔNG ghi vào `web/data.json`, KHÔNG chạy ETL, KHÔNG đụng SQLite/Postgres, KHÔNG
git add/commit/push. Mọi thay đổi dữ liệu chờ chủ dự án duyệt và phải chạy `python scripts/backup_data.py`
trước (§B1).
