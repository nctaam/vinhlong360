# Hồ Sơ Vi Phẫu Thuật Mỹ Học UI/UX & Triệt Tiêu Toàn Diện AI-Slop

> STATUS: active
> **Mã hồ sơ:** `AUDIT-2026-09-14-DEEP-POLISH-V1`  
> **Cửa sổ mục tiêu duy nhất:** Screen `113af35ecf1846e8b4dd7425c432f425` (Dự án Stitch `14916181929760067680`)  
> **Trường phái thiết kế:** `editorial-grid-magazine` (UI Pro Max) · Tạp chí điền dã chuyên khảo Sơn Nam

---

## 1. Rà Soát Chi Tiết 4 Phân Đoạn Trên Cửa Sổ Hiện Tại

### 1.1. Phân đoạn 1 — The River Horizon & Masthead
* **Hiện trạng:** Đã có măng-sét Lora trang nhã, ảnh đứng lò gạch Măng Thít bờ kênh Thầy Cai và khung tìm kiếm phẳng.
* **Điểm hoàn thiện sâu:**
  1. Thêm viền nhấn màu vàng phù sa (`#C99446`) rất mảnh dưới chữ ký thương hiệu `VINHLONG360`.
  2. Bổ sung nhãn xuất xứ lưu trữ: `LƯU TRỮ ĐIỀN DÃ ĐỒNG BẰNG SÔNG CỬU LONG · TẬP I`.
  3. Tinh chỉnh khung tìm kiếm: Khoảng đệm êm ái hơn, nút bấm Terracotta với hiệu ứng hover co giãn nhẹ (`transform: scale(0.99)`).

### 1.2. Phân đoạn 2 — Bộ Tứ Không Gian Văn Hóa Điền Dã (4 Terroir Pillars)
* **Hiện trạng:** 4 khối chữ nhật $2 \times 2$ thoáng đãng, ảnh chất lượng cao.
* **Điểm hoàn thiện sâu:**
  1. Thêm chỉ số trắc địa thu nhỏ góc trên mỗi thẻ: `[KINH ĐỘ: 105.972° E]` để củng cố cảm giác khảo cứu thực địa.
  2. Đổi liên kết chữ cuối thẻ thành: `Đọc hồ sơ điền dã →` với nét gạch chân mỏng cách đáy 3px.

### 1.3. Phân đoạn 3 — Ký Sự Phù Sa Thực Địa (Sediment Field Dispatches)
* **Hiện trạng:** 3 bài ký sự ngang với trích dẫn văn học.
* **Điểm hoàn thiện sâu (Cực kỳ quan trọng để diệt AI-slop):**
  1. **Drop Cap (Chữ khởi đầu cổ điển):** Chữ cái đầu tiên của bài 1 ("C") và bài 2 ("N") được thiết kế cỡ lớn (3 dòng cao, font Lora Serif màu Terracotta `#B95F38`) tạo phong thái ấn phẩm hàn lâm.
  2. **Pull Quote có hồn:** Viền trái vệt son đất nung (`border-l-2 border-[#B95F38]`), nền phớt ấm nhẹ (`#F5EFEB`), trích dẫn rõ tên sách: *Trích: Sơn Nam — "Hương Rừng Cà Mau"*.

### 1.4. Phân đoạn 4 — Cẩm Nang Hành Trình Bỏ Túi & Chân Trang
* **Hiện trạng:** Dải thông báo con nước 1 dòng và chân trang 4 cột.
* **Điểm hoàn thiện sâu:**
  1. Nẹp dải ruy-băng con nước bằng viền đôi thanh nhã.
  2. Thêm nhãn xác minh nguồn: `SourceMark: Xác thực bởi Ban Biên tập Địa phương VinhLong360 · Giấy phép lưu chiểu số 2026/VL-360`.

---

## 2. Lời Lệnh (Prompt) Chuyên Biệt Dành Riêng Cho Stitch `edit_screens`

Lệnh này sẽ được truyền trực tiếp vào tham số `prompt` của `edit_screens` trên chính ID `113af35ecf1846e8b4dd7425c432f425`:

```markdown
Refine and deeply polish the CURRENT screen "VinhLong360 - Kỳ Đài Sông Nước Nam Bộ" in place. DO NOT create a new screen. Retain the exact 4-act broadside structure while elevating micro-craftsmanship:

1. SECTION 1 (MASTHEAD & HERO):
   - Add a subtle archival registration line above the masthead: "LƯU TRỮ ĐIỀN DÃ ĐỒNG BẰNG SÔNG CỬU LONG · TẬP I · KHẢO CỨU NÔNG VỤ & THỦY TRÌNH".
   - Refine the search bar with comfortable micro-padding and a terracotta button with a crisp 1px border.

2. SECTION 2 (BỘ TỨ KHÔNG GIAN ĐIỀN DÃ):
   - Ensure the 4 quadrant plates have crisp hairline borders (1px solid #E5DDD0) and subtle accession tags (e.g. "[KINH ĐỘ: 105.972° E]").
   - Action links styled with delicate bottom border: "Đọc hồ sơ điền dã →".

3. SECTION 3 (KÝ SỰ PHÙ SA THỰC ĐỊA):
   - Add a magnificent serif drop cap (font Lora, terracotta color #B95F38) to the opening paragraph of the first field dispatch ("C").
   - Style pull quotes with an authentic terracotta left accent border (border-l-2 #B95F38), pale warm substrate (#F5EFEB), and explicit scholarly citation: "— Trích lục: Sơn Nam, 'Hương Rừng Cà Mau'".

4. SECTION 4 (TIDAL ADVISORY & FOOTER):
   - Keep the clean 1-line tidal briefing inside a refined warm ribbon with a subtle alluvial border.
   - Include the authoritative verification mark: "SourceMark: Ban Biên Tập VinhLong360 · Nghiên cứu văn hóa phi thương mại".
```
