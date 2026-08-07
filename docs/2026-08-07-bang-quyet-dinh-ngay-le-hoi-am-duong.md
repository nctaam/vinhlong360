> STATUS: active
> Ngày lập: 2026-08-07 · Phạm vi: 67 entity `type=event` · **Tài liệu PHÂN TÍCH — chưa sửa một dòng dữ liệu nào.**
> Người quyết: chủ dự án. Cách dùng: đọc §3 → điền cột **CHỐT** ở §6 → lúc đó mới mở task sửa.

# Bảng quyết định — dữ liệu sự kiện lệch âm/dương

## 0. Vì sao có tài liệu này

Một đợt sửa trước đã **ghi vào DB rồi phải hoàn nguyên**, vì sửa xong lại hỏng hơn lúc đầu.
Nguyên nhân gốc không phải lỗi tính lịch, mà là **ngày của một lễ hội nằm ở sáu ô khác nhau**,
và **cả sáu cùng hiển thị trên một trang**. Sửa một ô → năm ô kia thành lời nói ngược →
mâu thuẫn *công khai*, tệ hơn trạng thái lệch ban đầu.

Sáu ô đó:

| # | Ô chứa ngày | Kiểu | Hiện ra ở đâu |
|---|---|---|---|
| 1 | `attributes.lunar_date` | chuỗi tự do tiếng Việt | badge 🌙 trên `/le-hoi` (3 chỗ) |
| 2 | `attributes.date_start` | ISO hoặc **văn xuôi** | JSON-LD `Event.startDate`, nút tải **.ics**, sort "sắp diễn ra" |
| 3 | `attributes.date_end` | ISO hoặc rỗng | JSON-LD `Event.endDate`, `.ics` DTEND |
| 4 | `entities.summary` | văn xuôi | tiêu đề phụ trang chi tiết + card |
| 5 | `entities.description` | văn xuôi | thân trang chi tiết |
| 6 | `entities.season` (`.text` `.months` `.peak`) | JSON | lưới 12 tháng "Mùa vụ" + dòng fact "Mùa" trên trang chi tiết |

**Hệ quả nặng nhất:** ô #2/#3 không chỉ là chữ trên trang — chúng chảy vào
`schema.org/Event` (Google rich result) và vào **file .ics người dùng tải về lịch cá nhân**.
Một ngày sai ở đây đi thẳng vào điện thoại người đọc.

> Đối chiếu: **`web/data.json` khớp DB 100%** trên cả 3 trường ngày của cả 67 event
> (0 khác biệt). Không có trục phân kỳ thứ hai — bớt được một biến.

## 1. Con số tổng

| Chỉ số | Số lượng |
|---|---|
| Tổng entity `type=event` | **67** |
| Có `lunar_date` | 36 |
| `date_start` dạng ISO (`YYYY-MM-DD`) | 57 |
| `date_start` là **văn xuôi** ("Tháng 2 âm lịch"…) → không lên JSON-LD/.ics | 10 |
| **Đang công bố ngày cứng ra JSON-LD + .ics** | **36** |
| Bị backend chặn bởi heuristic `month` (xem §5) | 21 |
| `season.text` = "Chưa xác định mùa vụ" | 22 |
| `season.text` rỗng | 13 |

## 2. Oracle và cách kiểm chứng

Dùng `agent/lunar_calendar.py`, múi giờ mặc định **UTC+7** (đúng cho lịch VN từ 1968).

> ⚠️ **Thứ tự tham số**: `solar_to_lunar(dd, mm, yy)` và `lunar_to_solar(dd, mm, yy)` —
> **ngày trước, tháng sau**. Gọi nhầm cho ra kết quả trông-như-thật nhưng vô nghĩa.

Kiểm chứng oracle trước khi tin: `solar_to_lunar(29,1,2025)` → `01/01/2025` (Tết Ất Tỵ) ✔

### Bảng tra âm → dương năm 2026 (để chủ dự án đối chiếu tay)

Tết Bính Ngọ = **17/02/2026**.

| Âm lịch | Dương lịch 2026 | | Âm lịch | Dương lịch 2026 |
|---|---|---|---|---|
| Mùng 1 tháng Giêng | 17/02 | | Mùng 2 tháng 6 | 15/07 |
| Mùng 3–4 tháng Giêng | 19–20/02 | | Mùng 3 tháng 6 | 16/07 |
| **Rằm tháng Giêng** | **03/03** | | 15 tháng 6 | 28/07 |
| 16–18 tháng Giêng | 04–06/03 | | 16 tháng 6 | 29/07 |
| **Rằm tháng 2** | **02/04** | | Mùng 3 tháng 7 | 15/08 |
| 16–17 tháng 2 | 03–04/04 | | Mùng 4–5 tháng 7 | 16–17/08 |
| 10–12 tháng 3 | 26–28/04 | | Rằm tháng 7 (Vu Lan) | 27/08 |
| 16–17 tháng 3 | 02–03/05 | | Rằm tháng 8 (Trung Thu) | 25/09 |
| 18–19 tháng 3 | 04–05/05 | | 29 tháng 8 | 09/10 |
| 23–27 tháng 3 | 09–13/05 | | Mùng 1 tháng 9 | 10/10 |
| 16 tháng 4 | 01/06 | | 12–13 tháng 10 | 20–21/11 |
| Mùng 5 tháng 5 (Đoan Ngọ) | 19/06 | | **Rằm tháng 10 (Ok Om Bok)** | **23/11** |
| 11–12 tháng 5 | 25–26/06 | | 16–17 tháng 10 | 24–25/11 |

**Hai ngày âm KHÔNG tồn tại trong 2026** (tháng thiếu): `30 tháng 8` và `30 tháng Chạp`.
Bất kỳ chỗ nào trong dữ liệu ghi "29-30 tháng 8 âm lịch" đều không quy đổi được cho năm nay.

**Ngày theo can-chi** (không phải số ngày cố định — xem ca C-3):
Xuân Đinh 2026 = ngày Đinh đầu tháng 2 ÂL = **24/03/2026** (Đinh Dậu).
Thu Đinh 2026 = ngày Đinh cuối tháng 8 ÂL = **30/09/2026** (Đinh Mùi).

---

## 3. Phân loại

### A. KHỚP — mọi trường nói cùng một thứ. **KHÔNG ĐỤNG.** (12)

| id | lunar_date | Oracle 2026 | date_start..end trong DB |
|---|---|---|---|
| `lang-ong-tien-quan-thong-che-dieu-bat-tuong-quan-nguyen-van-` | Mùng 3–4 tháng Giêng | 19–20/02 | 2026-02-19 .. 02-20 ✔ |
| `le-cung-lau-ba-ram-thang-gieng` | Rằm tháng Giêng | 03/03 | 2026-03-03 ✔ |
| `le-hoi-ky-yen-ha-dien-dinh-tan-giai` | 16–17 tháng 3 | 02–03/05 | 2026-05-02 .. 05-03 ✔ |
| `le-hoi-ky-yen-dinh-phu-le` | 18–19 tháng 3 | 04–05/05 | 2026-05-04 .. 05-05 ✔ |
| `le-cung-bien-dong-cao` | 11–12 tháng 5 | 25–26/06 | 2026-06-25 .. 06-27 (dư 1 ngày đuôi) |
| `le-hoi-cung-bien-my-long` | 11–12 tháng 5 | 25–26/06 | 2026-06-25 .. 06-27 (dư 1 ngày đuôi) |
| `le-via-quoc-cong-tong-phuoc-hiep` | Mùng 2–3 tháng 6 | 15–16/07 | 2026-07-15 .. 07-16 ✔ |
| `le-hoi-nghinh-ong-binh-thang` | 16 tháng 6 | 29/07 | 2026-07-29 .. 07-30 ✔ |
| `sen-dolta` | 29 tháng 8 – 1 tháng 9 | 09–10/10 | 2026-10-09 .. 10-11 (dư 1 ngày đuôi) |
| `le-hoi-ok-om-bok` | Rằm tháng 10 | 23/11 | 2026-11-22 .. 11-24 — **cửa sổ ôm đúng ngày rằm**, hợp lý |
| `hoi-thi-ghe-ngo-mo-rong-tinh-tra-vinh-…` | Rằm tháng 10 | 23/11 | 2026-11-22 .. 11-24 — như trên |
| `giai-dua-ghe-ngo-truyen-thong-tinh-ben-tre-ben-tre` | Rằm tháng 10 | 23/11 | 2026-11-22 .. 11-24 — như trên |

*Ghi chú:* `le-hoi-nguyen-tieu` và `le-hoi-nguyen-tieu-o-tra-cu` (2026-03-02 .. 03-03, rằm = 03/03)
cũng thuộc dạng "cửa sổ ôm ngày rằm" — đêm 14 + ngày rằm. Đúng tập tục, **không phải lỗi**.

### B. LỆCH KỸ THUẬT — các trường đồng ý với nhau, chỉ `date_start/date_end` tính sai. Sửa được tự động. (3)

| id | Mọi trường đồng ý | Oracle 2026 | DB đang ghi | Lệch | Đề xuất |
|---|---|---|---|---|---|
| `le-cung-mieu` | 16–18 tháng Giêng ÂL | 04–06/03 | 2026-03-05 .. 03-07 | **+1 ngày** | → `2026-03-04` .. `2026-03-06` |
| `le-thuong-dien-dinh-tan-ngai` | 16–17 tháng 10 ÂL (lunar_date + summary + season.text **đều nói vậy**, và **nguồn ngoài xác nhận**) | 24–25/11 | 2026-11-15 .. 11-16 | **−9 ngày** | → `2026-11-24` .. `2026-11-25` |
| `le-hoi-dom-long-neak-ta` | lunar_date "cuối tháng 3 – đầu tháng 4 ÂL" + season "tháng 4–5, cao điểm tháng 5" | ~16–17/05 | 2026-10-08 .. 10-10 | **~5 tháng** | thấy §3.C-11 — có bẫy, đọc trước |

**Nguồn ngoài cho đình Tân Ngãi:** Wikipedia tiếng Việt mục *Đình Tân Ngãi* ghi đình có hai lễ lớn —
Hạ điền 16–17 tháng 3 ÂL và **Thượng điền 16–17 tháng 10 ÂL**. Trùng khớp `lunar_date` hiện có
⇒ đây là ca an toàn nhất để sửa.

### C. TỰ MÂU THUẪN — các trường nói khác nhau. **KHÔNG giải được từ dữ liệu. Phải có người chốt.** (14)

Đọc kỹ: **12/14 ca dưới đây đang công bố ngày cứng ra JSON-LD + .ics ngay lúc này.**

---

**C-1 · `le-gio-nguyen-dinh-chieu` — Lễ giỗ Nguyễn Đình Chiểu** 🔴 *đang live*

| Đáp án | Dựa vào trường | Ra ngày 2026 |
|---|---|---|
| **(a) 3 tháng 7 DƯƠNG lịch** | `date_start` = 2026-07-03 | **03/07/2026** |
| (b) Mùng 3 tháng 7 ÂM lịch | `lunar_date`, `summary`, `description`, `season.text` ("tháng 7-8 DL, cao điểm tháng 8"), `season.months`=[7,8] | 15/08/2026 |

**Nguồn ngoài ủng hộ (a):** Nguyễn Đình Chiểu sinh **1/7/1822** và mất **3/7/1888** — cả hai đều là
ngày **dương lịch**. Bến Tre lấy **1/7 dương lịch** làm *"Ngày hội truyền thống văn hóa tỉnh"*;
lễ hội Nguyễn Đình Chiểu tổ chức quanh 30/6–2/7 hằng năm tại Khu lăng mộ, xã An Đức, Ba Tri.

> ⚠️ **Bẫy ngược đời:** đây là ca duy nhất mà **`date_start` đúng còn 4 trường kia sai**.
> Ai "sửa `date_start` theo `lunar_date`" bằng script sẽ đẩy ngày đúng thành ngày sai.
> Nhiều khả năng chuỗi "3 tháng 7" (dương) đã bị một vòng enrichment gắn nhầm chữ "âm lịch".

**Cần chốt:** xoá `lunar_date` + sửa `summary`/`description`/`season` về **3/7 dương lịch**, giữ nguyên `date_start`? → ☐

---

**C-2 · `le-gio-phan-thanh-gian-tai-van-thanh-mieu` — Lễ giỗ Phan Thanh Giản** 🔴 *đang live*

| Đáp án | Dựa vào trường | Ra ngày 2026 |
|---|---|---|
| (a) 15 tháng 6 ÂL | `lunar_date` | 28/07/2026 |
| **(b) Mùng 4–5 tháng 7 ÂL** | `summary`, `description` | **16–17/08/2026** |
| (c) — | `date_start` = 2026-08-04 (= **22/6 ÂL**, không ứng với đáp án nào) | 04/08/2026 |

**Nguồn ngoài ủng hộ (b):** Báo Vĩnh Long (bài công nhận Lễ hội Văn Thánh Miếu là DSVH phi vật thể
quốc gia) viết nguyên văn: *"tại Tụy Văn Lâu có lễ vía cụ Phan Thanh Giản vào các ngày mùng 4 và
mùng 5 tháng bảy âm lịch"*. Bảo tàng Vĩnh Long cũng liệt kê 4 lễ chính của Văn Thánh Miếu trong đó
lễ giỗ Phan Thanh Giản = 4–5 tháng 7 ÂL.

**Cần chốt:** lấy (b) → `lunar_date`="Mùng 4–5 tháng 7 âm lịch", `date_start`=2026-08-16, `date_end`=2026-08-17? → ☐

---

**C-3 · `le-hoi-van-thanh-mieu` — Lễ hội Văn Thánh Miếu** 🔴 *đang live* — **ca đặc biệt**

| Đáp án | Dựa vào trường | Ra ngày 2026 |
|---|---|---|
| (a) Rằm tháng 2 ÂL | `lunar_date` | 02/04/2026 |
| **(b) Lễ Xuân Đinh = ngày ĐINH đầu tiên của tháng 2 ÂL** | `season.text` ("Lễ Xuân Đinh") | **24/03/2026** (Đinh Dậu) |
| (c) — | `date_start` = 2026-03-10 (= **22/1 ÂL**, không ứng với đáp án nào) | 10/03/2026 |

**Nguồn ngoài ủng hộ (b):** Văn Thánh Miếu Vĩnh Long có 4 lễ/năm — **Xuân Đinh (ngày Đinh đầu
tháng 2 ÂL)**, Thu Đinh (ngày Đinh cuối tháng 8 ÂL), giỗ Phan Thanh Giản (4–5/7 ÂL), giỗ các trung
thần liệt tử (12–13/10 ÂL). Lễ hội được công nhận DSVH phi vật thể quốc gia 21/02/2024.

> ⚠️ **Bẫy kiểu ngày:** "ngày Đinh" là **can-chi**, KHÔNG phải số ngày âm cố định — mỗi năm rơi
> vào một ngày âm khác nhau. Trường `lunar_date` kiểu "rằm tháng X" **không biểu diễn được** loại
> ngày này. Muốn làm đúng phải tính bằng `can_chi_day()` mỗi năm, hoặc chấp nhận ghi mô tả
> ("ngày Đinh đầu tháng 2 âm lịch") và **bỏ hẳn ngày cứng**.
> 2026: Xuân Đinh = 24/03, Thu Đinh = 30/09.

**Cần chốt:** đổi sang mô hình can-chi (và bỏ `date_start` cứng), hay giữ ngày cứng tính sẵn từng năm? → ☐

---

**C-4 · `le-via-ba-co-hy` — Lễ Vía Bà Cố Hỷ** 🔴 *đang live*

| Đáp án | Dựa vào trường | Ra ngày 2026 |
|---|---|---|
| (a) Rằm tháng 2 ÂL | `lunar_date` | 02/04/2026 |
| **(b) Rằm tháng Giêng ÂL** | `summary`, `description`, `season.text`, `season.months`=[2], `season.peak`=[2] | **03/03/2026** |
| (c) — | `date_start` = 2026-04-03 | 03/04/2026 |

**Nguồn ngoài ủng hộ (b):** các mô tả Lầu Bà Cố Hỷ (Thượng Động Nương Nương), ấp Ba Động,
xã Trường Long Hòa, TX Duyên Hải ghi lễ vía chính **rằm tháng Giêng** (15–16/1 ÂL), và một kỳ phụ
15–16 tháng 7 ÂL.

> Đây đúng là ví dụ mà đề bài nêu: `lunar_date` và `season.text` **cách nhau 30 ngày**.
> Ở ca này thế đa số rất rõ — 4 trường nói rằm tháng Giêng, chỉ `lunar_date` nói tháng 2.

**Cần chốt:** lấy (b) → `lunar_date`="Rằm tháng Giêng âm lịch", `date_start`=2026-03-03? → ☐
**Kèm câu hỏi:** có bổ sung kỳ phụ 15–16/7 ÂL (= 27–28/08/2026) không? → ☐

---

**C-5 · `le-hoi-ngu-dan-thanh-hai-le-hoi-cau-ngu` — Lễ hội Ngư dân Thạnh Hải** 🔴 *đang live* — **bốn trường, bốn đáp án**

| Đáp án | Dựa vào trường | Ra ngày 2026 |
|---|---|---|
| (a) 15–16 tháng 2 ÂL | `lunar_date` | 02–03/04/2026 |
| (b) "15–16 tháng âm lịch" — **thiếu hẳn số tháng** | `summary`, `description` | không quy đổi được |
| (c) Rằm tháng Giêng ÂL | `season.text` | 03/03/2026 |
| (d) — | `date_start` = 2026-03-10 (= 22/1 ÂL) | 10/03/2026 |

Không tìm được nguồn chính thống đủ rõ cho lễ cầu ngư Cồn Bửng – Thạnh Hải (Thạnh Phú).
**Không tự chọn được.** Lưu ý (b) là **lỗi văn bản** — câu văn khuyết số tháng, phải sửa dù chốt đáp án nào.

**Cần chốt:** tháng mấy? ☐ Giêng ☐ tháng 2 ☐ khác: ______

---

**C-6 · `le-hoi-nghinh-ong-lang-con-tau` — Lễ hội Nghinh Ông Lăng Cồn Tàu** 🔴 *đang live*

| Đáp án | Dựa vào trường | Ra ngày 2026 |
|---|---|---|
| (a) 10–11 tháng 3 ÂL | `lunar_date`, `date_start`=2026-04-26..27 | 26–27/04/2026 |
| **(b) 15 tháng 2 ÂL (và 15 tháng 7 ÂL)** | `summary`, `description`, `season.text` | 02/04/2026 (và 27/08/2026) |

`season.months`=[2,3] / `peak`=[3] — nằm giữa hai đáp án, không phân xử được.
Mẫu "hai kỳ 15/2 và 15/7 ÂL" trùng với mẫu của Bà Cố Hỷ (C-4) ⇒ (b) có vẻ là mô tả thực địa.

**Cần chốt:** ☐ (a) một kỳ tháng 3 ☐ (b) hai kỳ 15/2 + 15/7 ÂL

---

**C-7 · `le-hoi-nghinh-ong-duyen-hai` — Lễ hội Nghinh Ông Duyên Hải** 🔴 *đang live*

| Đáp án | Dựa vào trường | Ra ngày 2026 |
|---|---|---|
| (a) 10–12 tháng 3 ÂL | `lunar_date`, `date_start`=2026-04-26..28 | 26–28/04/2026 |
| (b) 20–21 tháng 2 ÂL | `description` | 07–08/04/2026 |

`season.text`="Chưa xác định mùa vụ", `season.months`=[4] → không giúp gì.
Tra nguồn ngoài **không kết luận được**: kết quả trả về chủ yếu là *Lễ hội cúng biển Mỹ Long*
(Cầu Ngang, 11–13 tháng 5 ÂL) — một lễ **khác**, đã có entity riêng. Cần người biết địa bàn Duyên Hải.

**Cần chốt:** ☐ (a) ☐ (b) ☐ gộp vào Mỹ Long ☐ bỏ ngày cứng

---

**C-8 · `le-ha-dien-dinh-tan-hoa` — Lễ Hạ điền Đình Tân Hoa** 🔴 *đang live*

| Đáp án | Dựa vào trường | Ra ngày 2026 |
|---|---|---|
| (a) 16 tháng 4 ÂL | `lunar_date`, `date_start`=2026-06-01 | 01/06/2026 |
| (b) 14–15 tháng 3 ÂL | `summary`, `description` | 30/04–01/05/2026 |
| (c) "tháng 3 ÂL ≈ tháng 3–4 DL, cao điểm tháng 4" | `season.text`, `season.months`=[3,4], `peak`=[4] | tháng 3–4/2026 |

**Mâu thuẫn hiển thị rõ nhất trong cả bộ:** `date_start` = **tháng 6** trong khi lưới "Mùa vụ" ngay
bên dưới tô sáng **tháng 3 và 4**. Hai thứ này nằm cùng một màn hình.

Nguồn ngoài mô tả đình Tân Hoa có **Thượng điền 11–12 tháng 9 ÂL** và **lễ Thần Hoàng 12–13 tháng 3 ÂL**
— **không khớp đáp án nào ở trên**, làm ca này càng cần người xác nhận thực địa.

**Cần chốt:** ☐ (a) ☐ (b) ☐ theo nguồn ngoài (12–13/3 ÂL) ☐ bỏ ngày cứng

---

**C-9 · `le-hoi-ky-yen` — Lễ hội Kỳ Yên (entity chung, không gắn đình cụ thể)** 🔴 *đang live*

| Đáp án | Dựa vào trường | Ra ngày 2026 |
|---|---|---|
| (a) 16–17 tháng 2 ÂL | `lunar_date` | 03–04/04/2026 |
| (b) — | `date_start` = 2026-03-15..17 (= 27–29/1 ÂL) | 15–17/03/2026 |

`season.text`="Chưa xác định mùa vụ". Kỳ Yên là **lễ tế Thần Thành Hoàng của mọi đình Nam Bộ**,
mỗi đình một ngày khác nhau (đã có 2 entity Kỳ Yên gắn đình cụ thể: Tân Giai 16–17/3 ÂL,
Phú Lễ 18–19/3 ÂL — cả hai đều KHỚP).

**Khuyến nghị mạnh:** entity chung như thế này **không nên có ngày cứng** — nó sẽ bơm một ngày bịa
vào .ics và JSON-LD. Nên chuyển thành bài giải thích phong tục, `date_start` để trống.

**Cần chốt:** ☐ bỏ ngày cứng (khuyến nghị) ☐ giữ (a) ☐ giữ (b)

---

**C-10 · `le-hoi-ba-chua-xu` — Lễ hội Bà Chúa Xứ** ⚪ *không live (date_start là văn xuôi)*

| Đáp án | Dựa vào trường | Ra ngày 2026 |
|---|---|---|
| (a) 23–27 tháng 3 ÂL | `lunar_date` | 09–13/05/2026 |
| (b) 23–27 tháng 4 ÂL | `date_start` (văn xuôi: "23-27 tháng 4 âm lịch (khoảng tháng 5-6 dương lịch)") | 08–12/06/2026 |

`season.months`=[4,5], `peak`=[4] → nghiêng (a). `season.text` rỗng.
Hai trường **lệch nhau đúng một tháng âm** — dấu hiệu kinh điển của một lần chép tay sai.
(Vía Bà Chúa Xứ Núi Sam ở An Giang là 23–27 tháng 4 ÂL; entity này nói về "các miếu Bà trong vùng
Vĩnh Long, Trà Vinh" nên **không suy ra được** từ mốc An Giang.)

**Cần chốt:** ☐ (a) tháng 3 ☐ (b) tháng 4 ☐ bỏ ngày cứng

---

**C-11 · `le-hoi-dom-long-neak-ta` — Lễ hội Đom Lơng Néak Tà** 🔴 *đang live* — cũng nằm ở §3.B

| Đáp án | Dựa vào trường | Ra ngày 2026 |
|---|---|---|
| (a) cuối tháng 3 – đầu tháng 4 ÂL | `lunar_date` | ~16–17/05/2026 |
| (b) tháng 4–5 dương, cao điểm tháng 5 | `season.text`, `peak`=[5] | tháng 4–5/2026 |
| (c) — | `date_start` = 2026-10-08..10 (= 28/8 ÂL) | 08–10/10/2026 |

(a) và (b) **đồng ý với nhau**; chỉ `date_start` lạc ~5 tháng ⇒ về mặt kỹ thuật là "lệch một ô".

**Nguồn ngoài:** Bộ VHTTDL công bố Đom Lơng Néak Tà là DSVH phi vật thể quốc gia (QĐ 22/02/2024) và
ghi rõ lễ **do từng phum sóc tự chọn ngày, phần lớn rơi vào tháng 3, 4, 5 âm lịch** (ví dụ ấp Truôn,
xã Hòa Lợi chọn 12–13/5 ÂL). ⇒ **Không tồn tại một ngày đúng duy nhất toàn tỉnh.**

**Khuyến nghị:** bỏ ngày cứng, giữ mô tả "tháng 3–5 âm lịch, mỗi phum sóc một ngày".

**Cần chốt:** ☐ bỏ ngày cứng (khuyến nghị) ☐ đặt một ngày đại diện: ______

---

**C-12 · `le-hoi-cau-ngu` — Lễ hội Cầu Ngư** ⚪ *không live*

`lunar_date`="Rằm tháng 2 âm lịch" (→ 02/04/2026) vs `date_start`="Tháng 2 âm lịch" (mơ hồ).
`season.text` rỗng, `months`=[2,3], `peak`=[2] → **season nói tháng 2–3 dương**, tức lệch một nhịp
so với "rằm tháng 2 âm" (= tháng 4 dương).
Ngoài ra `summary` mô tả **lễ cúng biển Ba Động, Duyên Hải, tế tại miếu Bà Chúa Xứ** — trùng địa bàn
và trùng mô-típ với `le-cung-lau-ba-ram-thang-gieng` và `le-via-ba-co-hy` (C-4).

**Cần chốt:** ☐ đây là entity riêng, ngày = ______ ☐ trùng lặp, gộp vào Bà Cố Hỷ

---

**C-13 · `le-hoi-chol-chnam-thmay-va-sen-dolta`** 🔴 *đang live* — **một entity, hai lễ cách nhau nửa năm**

`lunar_date` = `"Chol Chnam Thmay: 13–16/4 DL; Sen Dolta: 29/8–1/9 ÂL"` — **hai lễ nhét chung một ô**.
`date_start`/`date_end` = 2026-04-13..16 → **chỉ mô tả được lễ thứ nhất**.
`season.months`=[4,9,10], `peak`=[4,10] → season biết có hai mùa, nhưng .ics và JSON-LD thì không:
người tải lịch về **chỉ nhận được Chol Chnam Thmay**, mất hoàn toàn Sen Dolta.

Đã tồn tại sẵn entity riêng cho từng lễ: `le-chol-chhnam-thmay`, `le-hoi-chol-chnam-thmay-tai-chua-ky-son`, `sen-dolta`.

**Cần chốt:** ☐ tách làm 2 entity ☐ bỏ ngày cứng, để làm bài tổng quan về Trà Cú ☐ xoá (trùng lặp)

---

**C-14 · `le-hoi-chol-chnam-thmay-tai-chua-ky-son`** 🔴 *đang live* — lệch nhỏ nhưng có bẫy

`lunar_date`="13–15 tháng 4 **dương lịch** (cố định)" nhưng `date_end`=2026-04-16 (tức 13–**16**).
Entity anh em `le-chol-chhnam-thmay` ghi "13–**16**". Lệch 1 ngày ở đuôi, tự mâu thuẫn nội bộ nhẹ.

> ⚠️ **BẪY QUAN TRỌNG CHO MỌI SCRIPT SỬA TỰ ĐỘNG:**
> Chol Chnam Thmay là lễ **ấn định theo dương lịch 13–16/4**, KHÔNG theo âm lịch Việt.
> Trường tên là `lunar_date` nhưng nội dung ghi rõ *"dương lịch"*. Script nào đọc `lunar_date`
> rồi ném vào `lunar_to_solar()` sẽ biến 13/4 thành **29/05** — sai 46 ngày.
> Phải kiểm chuỗi `"dương lịch"` trước khi quy đổi.

**Cần chốt:** thống nhất 13–15 hay 13–16/4? → ☐

---

### D. LỄ KHMER — nhóm riêng (vấn đề *tên gọi*, không chỉ ngày)

**D-1 · Ba lễ lớn đang có nhiều cách viết trong DB** (khảo sát toàn bộ 1746 entity, không riêng event):

| Lễ | Các cách viết đang tồn tại | Số entity |
|---|---|---|
| Sen Dolta | `Sen Dolta` (5) · `Sen Đôn Ta` (1) | 6 |
| Chol Chnam Thmay | `Chol Chnam Thmay` (8) · `Chôl Chnăm Thmây` (3) | 11 |
| Ok Om Bok | `Ok Om Bok` (25) · `Oóc-Om-Bóc` (2) · `Ok-om-bok` (1) | 28 |

Cùng một lễ hiện ra dưới 2–3 mặt chữ khác nhau trên cùng site ⇒ search nội bộ tách nhóm,
người đọc tưởng là các lễ khác nhau. (Dạng `Sene Dolta` không có trong DB nhưng đang được dùng
trong tài liệu nội bộ — cần chốt luôn để tài liệu và dữ liệu nói cùng một tên.)

**Cần chốt — chọn một chính tả chuẩn cho mỗi lễ, các dạng khác thành bí danh:**
Sen Dolta: ☐ `Sen Dolta` ☐ `Sene Dolta` ☐ `Sen Đôn Ta`
Chol Chnam Thmay: ☐ `Chol Chnam Thmay` ☐ `Chôl Chnăm Thmây`
Ok Om Bok: ☐ `Ok Om Bok` ☐ `Oóc Om Bóc`

**D-2 · Entity gộp hai lễ cách nhau nửa năm** → xem **C-13**.

**D-3 · Chol Chnam Thmay theo DƯƠNG lịch** → xem **C-14** (bẫy quy đổi).

**D-4 · Cụm Ok Om Bok — 5 entity cùng một ngày rằm tháng 10:**
`le-hoi-ok-om-bok`, `tuan-le-van-hoa-du-lich-gan-voi-le-hoi-ok-om-bok`,
`hoi-thi-ghe-ngo-mo-rong-tinh-tra-vinh-…`, `giai-dua-ghe-ngo-truyen-thong-tinh-ben-tre-ben-tre`,
`hoi-cho-xuc-tien-thuong-mai-san-pham-…-gan-voi-ok-om-bok-vinh-long`.

Ngày đều hợp lý (23/11/2026 = rằm tháng 10). Nhưng **hai giải đua ghe ngo có `lunar_date` và
`date_start` giống hệt nhau từng ký tự** — một cái ghi "tỉnh Bến Tre", một cái "tỉnh Trà Vinh",
trong khi từ 07/2025 **chỉ còn một tỉnh Vĩnh Long**. Nghi trùng lặp, cần chủ dự án xác nhận đây là
hai giải thật sự khác nhau hay một giải bị nhân đôi.

**Cần chốt:** ☐ hai giải khác nhau, giữ cả hai ☐ trùng lặp, gộp

**D-5 · `sen-dolta` và tháng thiếu:** `description` của `le-hoi-chol-chnam-thmay-tai-chua-ky-son`
ghi *"Sen Dolta (29-30 tháng 8 âm lịch)"* — nhưng **30 tháng 8 âm KHÔNG tồn tại năm 2026**
(tháng thiếu). Bản thân entity `sen-dolta` ghi "29 tháng 8 – 1 tháng 9" là cách viết đúng và
an toàn qua mọi năm. Nên thống nhất theo cách viết của `sen-dolta`.

---

## 4. Tổng hợp để chốt nhanh

Cộng phải ra đúng **67**. Kiểm lại phép cộng trước khi tin bảng:

| Nhóm | Số ca | Hành động |
|---|---|---|
| A. KHỚP | 12 | không đụng |
| B. LỆCH KỸ THUẬT | 3 | sửa được tự động (C-11 đọc kỹ trước) |
| C. TỰ MÂU THUẪN | 14 | **chờ chủ dự án** — 12 ca đang live |
| E. Có `lunar_date` nhưng `date_start` là **văn xuôi** | 7 | đã xét, KHÔNG đụng — xem dưới |
| Không có `lunar_date`, không kiểm chứng được bằng oracle | 31 | xem §5 |
| **Tổng** | **67** | |

*(D — lễ Khmer — không phải một nhóm đếm riêng: 3 quyết định chính tả + 2 ca trùng
lặp nằm rải trong A/C ở trên, nên không cộng vào tổng.)*

### E. Bảy ca có `lunar_date` mà `date_start` là văn xuôi

Bản đầu của tài liệu này bỏ sót chúng: cộng ra 60 chứ không phải 67. Chúng không
vào được A/B/C vì A/B/C so `lunar_date` với một ngày ISO, mà bảy ca này không có
ngày ISO nào để so.

| id | `date_start` |
|---|---|
| `tet-doan-ngo` | 5 tháng 5 âm lịch (khoảng tháng 6 dương lịch) |
| `tet-nguyen-dan-mien-tay` | Tháng 1 âm lịch (khoảng tháng 1-2 dương lịch) |
| `le-vu-lan` | Rằm tháng 7 âm lịch (khoảng tháng 8 dương lịch) |
| `le-gio-to-hung-vuong` | 10 tháng 3 âm lịch (khoảng tháng 4 dương lịch) |
| `le-hoi-cau-ngu` | Tháng 2 âm lịch |
| `le-hoi-long-den` | Rằm tháng 8 âm lịch (khoảng tháng 9-10 dương lịch) |
| `le-hoi-ba-chua-xu` | 23-27 tháng 4 âm lịch (khoảng tháng 5-6 dương lịch) |

**Rủi ro thấp, nhưng không phải bằng không.** Vì `date_start` không phải ngày máy
đọc được, site không công bố một ngày cứng nào cho chúng — tức không thể sai ngày.
Đổi lại, chúng cũng không lên được lịch, không sắp xếp được, không lọc theo tháng.
Muốn đưa vào lịch thì phải quy ra ISO, và lúc đó chúng rơi thẳng vào bài toán
sáu-ô của §0 — làm thì làm cả sáu ô một lần.

> **Ngoài phạm vi, gặp lúc kiểm:** id `tet-nguyen-dan-mien-tay` mang filler
> "mien-tay" — trái §1.6 CLAUDE.md (định vị là Vĩnh Long đặc thù, không phải
> "miền Tây" chung chung). Đổi id kéo theo URL nên là task riêng, không gộp vào đây.

---

## 5. 🚨 MÌN — `attributes.month` là cầu dao an toàn, KHÔNG PHẢI dữ liệu hỏng

`agent/public_api.py:2429-2432` và `2827-2830`:

```python
# Skip if month field set but conflicts with date_start (fabricated date)
attr_month = attrs.get("month")
if attr_month and isinstance(attr_month, (int, float)) and int(attr_month) != d.month:
    continue
```

**21 event đang bị chặn khỏi "sắp diễn ra"/homepage** đúng nhờ cơ chế này, vì `month` lệch tháng
của `date_start`. Đây là **hàng rào chống ngày bịa**, không phải bug.

> ⚠️ Ai nhìn thấy "21 chỗ lệch" rồi chạy script cho `month` khớp `date_start` sẽ **mở cống cho
> đúng 21 ngày bịa tràn ra JSON-LD + .ics**. Đây gần như chắc chắn là cách đợt sửa trước
> "làm hỏng thêm". **Đừng chạm vào `month`.**

Ghi chú kèm: `attributes.month` và `duration_days` **không được render ở bất kỳ đâu trong frontend** —
chúng thuần tuý là cờ nội bộ. Lệch ở đó **không phải mâu thuẫn công khai**, nên không cần sửa.

**Bất đối xứng đáng lưu ý:** `giai-dua-ghe-ngo-…-ben-tre` bị chặn (`month`=10 ≠ tháng 11) trong khi
bản sao `hoi-thi-ghe-ngo-…-tra-vinh` được phát (`month`=11) — **cùng một lễ, cùng một ngày, một cái
hiện một cái ẩn**. Cần chốt cùng D-4.

---

## 6. Bảng CHỐT — chủ dự án điền vào đây

| Mã | Entity | Câu hỏi | Chốt |
|---|---|---|---|
| C-1 | Lễ giỗ Nguyễn Đình Chiểu | 3/7 **dương** (giữ date_start, sửa 4 trường kia)? | |
| C-2 | Lễ giỗ Phan Thanh Giản | 4–5/7 ÂL → 16–17/08/2026? | |
| C-3 | Lễ hội Văn Thánh Miếu | chuyển sang mô hình "ngày Đinh" (can-chi)? | |
| C-4 | Lễ Vía Bà Cố Hỷ | rằm tháng Giêng → 03/03/2026? kỳ phụ 15/7 ÂL? | |
| C-5 | Lễ hội Ngư dân Thạnh Hải | tháng mấy? (summary khuyết số tháng) | |
| C-6 | Nghinh Ông Lăng Cồn Tàu | một kỳ tháng 3, hay hai kỳ 15/2 + 15/7 ÂL? | |
| C-7 | Nghinh Ông Duyên Hải | 10–12/3 ÂL hay 20–21/2 ÂL? | |
| C-8 | Lễ Hạ điền Đình Tân Hoa | 16/4, 14–15/3, hay 12–13/3 ÂL? | |
| C-9 | Lễ hội Kỳ Yên (chung) | bỏ ngày cứng? | |
| C-10 | Lễ hội Bà Chúa Xứ | 23–27 tháng 3 hay tháng 4 ÂL? | |
| C-11 | Đom Lơng Néak Tà | bỏ ngày cứng (mỗi phum sóc một ngày)? | |
| C-12 | Lễ hội Cầu Ngư | entity riêng hay trùng Bà Cố Hỷ? | |
| C-13 | Chol Chnam Thmay + Sen Dolta | tách 2 entity? | |
| C-14 | Chol Chnam Thmay chùa Kỳ Son | 13–15 hay 13–16/4? | |
| D-1 | Chính tả 3 lễ Khmer | chốt 1 dạng chuẩn mỗi lễ | |
| D-4 | Hai giải đua ghe ngo | hai giải khác nhau hay trùng lặp? | |
| B | 3 ca lệch kỹ thuật | cho phép sửa tự động? | |

---

## 7. Việc KHÔNG được làm (rút từ đợt hỏng trước)

1. **Không sửa một ô mà không sửa cả sáu.** Sáu ô cùng render trên một trang.
2. **Không suy `date_start` từ `lunar_date` bằng script.** C-1 chứng minh có ca `date_start`
   đúng còn `lunar_date` sai — script sẽ phá ngày đúng.
3. **Không đụng `attributes.month`** — nó là cầu dao, không phải dữ liệu (§5).
4. **Không quy đổi `lunar_date` chứa chữ "dương lịch"** — Chol Chnam Thmay lệch 46 ngày (C-14).
5. **Không tự chọn đáp án cho nhóm C.** Không giải được từ dữ liệu; ép chọn = tái diễn đợt trước.
6. **Không đặt ngày cứng cho lễ dạng-phong-tục** (Kỳ Yên chung, Đom Lơng Néak Tà) — mỗi
   đình/phum sóc một ngày; ngày cứng ở đây luôn là ngày bịa với phần lớn người đọc.
7. **Backup trước mọi thao tác ghi** (§B1) và nhớ `web/data.json` hiện **khớp DB 100%** —
   sửa một bên phải đồng bộ bên kia, đừng để phân kỳ.

## 8. Phụ lục — tái lập kết quả

Chỉ đọc, không ghi:

```powershell
# Oracle: kiem chung truoc khi tin (phai ra 01/01/2025)
python -c "import sys; sys.path.insert(0,'.'); from agent.lunar_calendar import solar_to_lunar; print(solar_to_lunar(29,1,2025))"

# Tra 1 ngay am -> duong 2026  (THU TU: dd, mm, yy)
python -c "import sys; sys.path.insert(0,'.'); from agent.lunar_calendar import lunar_to_solar; print(lunar_to_solar(15,10,2026))"

# Ngay Dinh dau tien cua thang 2 am lich 2026 (le Xuan Dinh)
python -c "import sys; sys.path.insert(0,'.'); from agent.lunar_calendar import lunar_to_solar,can_chi_day; [print(d,lunar_to_solar(d,2,2026)) for d in range(1,31) if can_chi_day(*[lunar_to_solar(d,2,2026).day,lunar_to_solar(d,2,2026).month,2026]).startswith('Đinh')]"
```

Đọc DB (chế độ read-only, KHÔNG ghi):

> **Chạy từ đâu là chuyện sống còn.** Mọi con số trong tài liệu này đo trên DB của
> worktree `.worktrees/tri-region-color`. DB ở worktree main là một bản KHÁC — nó chỉ
> có **49/67** dòng `entity_event_details`, nên chạy cùng đoạn lệnh ở đó sẽ ra
> 27/45/28/17 và 39 chỗ lệch với `data.json`, mâu thuẫn thẳng với bảng bên dưới.
> Dùng đường dẫn TUYỆT ĐỐI, đừng dùng đường dẫn tương đối.

```python
sqlite3.connect(
    "file:C:/Code/vinhlong360/.worktrees/tri-region-color/agent/data/vinhlong360.db?mode=ro",
    uri=True,
)
# SELECT e.id,e.name,e.summary,e.description,e.season,e.attributes,
#        d.date_start,d.date_end,d.lunar_date,d.month
# FROM entities e LEFT JOIN entity_event_details d ON d.entity_id=e.id
# WHERE e.type='event'
```

### Nguồn ngoài đã dùng

- [Lăng Nguyễn Đình Chiểu — Wikipedia tiếng Việt](https://vi.wikipedia.org/wiki/L%C4%83ng_Nguy%E1%BB%85n_%C4%90%C3%ACnh_Chi%E1%BB%83u) (C-1)
- [Di tích lịch sử Mộ và Khu tưởng niệm Nguyễn Đình Chiểu — Cục Di sản văn hoá](https://dsvh.gov.vn/di-tich-lich-su-mo-va-khu-tuong-niem-nguyen-dinh-chieu-2999) (C-1)
- [Lễ hội Văn Thánh Miếu được công nhận DSVH phi vật thể quốc gia — Vĩnh Long Online](https://baovinhlong.com.vn/van-hoa-giai-tri/202402/le-hoi-truyen-thong-le-hoi-van-thanh-mieu-duoc-cong-nhan-di-san-van-hoa-phi-vat-the-quoc-gia-3180733/) (C-2, C-3)
- [DSVH phi vật thể "Lễ hội Văn Thánh Miếu tỉnh Vĩnh Long" — Bảo tàng Vĩnh Long](https://www.baotangvinhlong.vn/di-san-van-hoa-phi-vat-the/di-san-van-hoa-phi-vat-the-le-hoi-van-thanh-mieu-tinh-vinh-long-587079) (C-3)
- [Lầu Bà Cố Hỷ — Di tích lịch sử cấp tỉnh](https://tinhdoantravinh.vn/2025/04/26/lau-ba-co-hy-di-tich-lich-su-cap-tinh/) (C-4)
- [Lầu thờ Bà Cố Hỷ Thượng Động nương nương — Du lịch Trà Vinh](https://dulichtravinh.com.vn/lau-tho-ba-co-hy-thuong-dong-nuong-nuong-tiem-nang-du-lich-tam-linh/) (C-4)
- [Đình Tân Ngãi — Wikipedia tiếng Việt](https://vi.wikipedia.org/wiki/%C4%90%C3%ACnh_T%C3%A2n_Ng%C3%A3i) (B, C-8)
- [Trà Vinh: Phát huy Lễ hội Đom Lơng Néak Tà gắn với phát triển du lịch — Bộ VHTTDL](https://bvhttdl.gov.vn/tra-vinh-phat-huy-le-hoi-dom-long-neak-ta-gan-voi-phat-trien-du-lich-20240417151437044.htm) (C-11)
- [Công bố DSVH phi vật thể quốc gia Lễ hội Đom Lơng Néak Tà — Bộ VHTTDL](https://bvhttdl.gov.vn/tra-vinh-cong-bo-disan-vanhoa-phi-vat-the-quocgia-le-hoi-dom-long-neak-ta-20240412151301904.htm) (C-11)
- [Lễ hội Cúng biển Mỹ Long — Du lịch Trà Vinh](https://dulichtravinh.com.vn/le-hoi-nghinh-ong/) (A, C-7)

> Nguồn ngoài dùng để **gợi ý cho người quyết**, không phải để tự động ghi vào DB.
> Theo §1.7, chưa entity nào có `attributes.verifiedAt` — **không được ghi "đã xác minh"**
> ở bất kỳ đâu trong sản phẩm dựa trên tài liệu này.
