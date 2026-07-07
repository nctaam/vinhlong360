# B2G Partnership — Pitch Template

> **STATUS (2026-07-07): active — đã truth-sync.** Số liệu đối chiếu `web/data.json` 2026-07-07; mọi claim "đã xác minh" / "cập nhật tự động" đã gỡ theo chốt trust (CLAUDE.md §1.7) — kiểm chứng thực địa nay là hạng mục ĐỀ XUẤT HỢP TÁC (mục 2.1). KHÔNG thêm lại các claim này khi `verifiedAt` chưa phủ.

> Ngày soạn: 27/06/2026 | Cập nhật: 07/07/2026 | Phiên bản: 1.1
> Tài liệu nội bộ — template cho chủ dự án sử dụng khi tiếp cận đối tác cơ quan nhà nước
> Cần điều chỉnh theo từng cơ quan cụ thể trước khi gửi

---

## 1. Giới thiệu vinhlong360

### Về dự án

**vinhlong360.vn** là nền tảng thông tin du lịch, sản phẩm OCOP và cộng đồng phục vụ **tỉnh Vĩnh Long mới** — sáp nhập Vĩnh Long, Bến Tre, Trà Vinh theo Nghị quyết 1687/NQ-UBTVQH15, hiệu lực từ 1/7/2025 (mô hình chính quyền 2 cấp: tỉnh → xã/phường).

### Quy mô hiện tại

| Chỉ số | Giá trị |
|--------|---------|
| Tổng thực thể (entity) | 1.730 |
| Quan hệ dữ liệu | 12.200+ |
| Loại entity | 17 (quán ăn, điểm du lịch, sản phẩm OCOP, cơ sở hành chính, làng nghề, lưu trú...) |
| Phủ sóng địa lý | Toàn bộ 124 xã/phường của tỉnh Vĩnh Long mới (35 phường + 89 xã) |
| Nền tảng | Web (SSR, SEO-friendly, mobile-first) |
| Trợ lý AI | Chatbot trả lời 24/7, hiểu ngữ cảnh địa phương |

### Đặc điểm khác biệt

- **Dữ liệu có nguồn, không bịa đặt**: 1.730 thực thể được biên tập có ghi nguồn thu thập — phần lớn từ nguồn công khai (cổng tỉnh, báo địa phương, cổng du lịch...); trang hiển thị trích dẫn + link gốc khi có nguồn công khai (chưa phủ 100%, đang bổ sung dần); kênh "Báo sai dữ liệu" công khai trên từng trang để tiếp nhận đính chính. Kiểm chứng thực địa là hạng mục **đề xuất hợp tác** với cơ quan chủ quản — xem mục 2.1.
- **Đã cập nhật theo sáp nhập**: cấu trúc hành chính 2 cấp (1 tỉnh → 124 xã/phường = 35 phường + 89 xã, không cấp huyện) theo Nghị quyết 1687/NQ-UBTVQH15 đã vận hành đầy đủ trên hệ thống từ 18/6/2026, gồm cả đợt 16 xã lên phường 09/06/2026.
- **Trí tuệ nhân tạo**: Chatbot AI hiểu ngữ cảnh Vĩnh Long, trả lời câu hỏi du khách bằng tiếng Việt tự nhiên, 24/7.
- **Cộng đồng xác thực**: Hệ thống xác thực OTP, kiểm duyệt nội dung, đánh giá từ người dùng thật.

---

## 2. Giá trị cho cơ quan nhà nước

### 2.1 Chuẩn hóa danh bạ hành chính

- Khung danh bạ phủ toàn bộ 124 đơn vị hành chính cấp xã/phường (35 phường + 89 xã) — mỗi đơn vị có trang riêng, sẵn sàng nạp dữ liệu
- Trường thông tin chuẩn hóa: tên chính thức, địa chỉ, SĐT, giờ làm việc, dịch vụ. **Dữ liệu liên hệ thật của từng cơ quan chính là hạng mục đề xuất hợp tác** (nạp từ nguồn chính thống của tỉnh — tránh tự thu thập dễ sai, gây hại cho dân)
- Khi có dữ liệu, tìm kiếm được bằng AI: "UBND xã Tân Long Hội điện thoại bao nhiêu?" — chatbot trả lời ngay
- Quy trình cập nhật biên tập khi có thay đổi nhân sự, địa giới; kênh "Báo sai dữ liệu" công khai trên từng trang để tiếp nhận đính chính
- **Đề xuất hợp tác kiểm chứng**: cơ quan chủ quản xác nhận thông tin đơn vị mình → hệ thống đóng dấu ngày kiểm chứng công khai trên trang (trường `verifiedAt`) — nâng danh bạ từ "biên tập từ nguồn công khai" lên "đã kiểm chứng bởi cơ quan chủ quản"

### 2.2 Quảng bá du lịch và sản phẩm OCOP

- Mỗi sản phẩm OCOP có trang riêng với mô tả, hình ảnh, thông tin cơ sở sản xuất
- Du khách tìm kiếm theo mùa vụ: "Đặc sản tháng 6" — hệ thống trả về sản phẩm đúng mùa
- Lộ trình du lịch gợi ý bằng AI dựa trên sở thích, thời gian, vị trí
- Chuẩn SEO/SSR với cổng chất lượng nội dung per-trang — sẵn sàng xuất hiện trên Google với từ khóa "du lịch Vĩnh Long", "đặc sản Bến Tre" (site đang chủ động hoàn thiện nội dung trước khi mở index)

### 2.3 Chatbot AI trả lời du khách

- Hoạt động 24/7, không cần nhân sự trực
- Trả lời bằng tiếng Việt tự nhiên, hiểu ngữ cảnh địa phương Vĩnh Long
- Có thể gợi ý quán ăn, điểm tham quan, lộ trình theo mùa
- Tích hợp Zalo OA (nền tảng phổ biến nhất tại địa phương)
- An toàn: hệ thống chống prompt injection, không trả lời ngoài phạm vi du lịch/cộng đồng

### 2.4 Dashboard analytics (phát triển theo yêu cầu)

- Thống kê lượt tìm kiếm theo loại: du lịch, ẩm thực, hành chính, OCOP
- Xu hướng quan tâm theo mùa
- Bản đồ nhiệt: khu vực nào được tìm kiếm nhiều nhất
- Dữ liệu phục vụ quy hoạch du lịch và phát triển kinh tế

---

## 3. Đề xuất hợp tác

### Package A: Danh bạ hành chính + Widget nhúng

| Hạng mục | Chi tiết |
|----------|----------|
| Nội dung | Danh bạ 124 đơn vị HC chuẩn hóa, cập nhật liên tục |
| Tích hợp | Widget nhúng (embed) vào website Sở/UBND hiện có |
| Chatbot | Trả lời câu hỏi HC: SĐT, địa chỉ, giờ làm việc |
| Hỗ trợ | Cập nhật dữ liệu hàng tháng |
| **Chi phí** | **800.000 - 1.500.000 VND/tháng** |

### Package B: OCOP Showcase + Chiến dịch theo mùa

| Hạng mục | Chi tiết |
|----------|----------|
| Nội dung | Trang giới thiệu cho từng sản phẩm OCOP với hình ảnh, thông tin cơ sở |
| Tính năng | Tìm kiếm theo mùa, gợi ý sản phẩm liên quan |
| Chiến dịch | 4 chiến dịch/năm theo mùa vụ (nếp, bưởi, dừa, chôm chôm...) |
| SEO | Tối ưu từ khóa "OCOP [tên sản phẩm] Vĩnh Long" |
| **Chi phí** | **500.000 - 1.000.000 VND/tháng** |

### Package C: Toàn diện (A + B + Custom branding)

| Hạng mục | Chi tiết |
|----------|----------|
| Nội dung | Bao gồm cả Package A và B |
| Branding | Giao diện tùy chỉnh theo nhận diện thương hiệu cơ quan |
| Analytics | Dashboard thống kê riêng cho cơ quan |
| Ưu tiên | Hỗ trợ kỹ thuật ưu tiên, cập nhật trong 24h |
| Đào tạo | Hướng dẫn nhân sự cơ quan sử dụng admin CMS |
| **Chi phí** | **2.000.000 - 3.000.000 VND/tháng** |

> **Ghi chú về giá:** Mức giá trên phù hợp với ngân sách cấp Sở/ngành, thấp hơn nhiều so với xây dựng hệ thống riêng (thường 50-200 triệu/dự án + chi phí vận hành). Cơ quan không cần đầu tư hạ tầng, nhân sự IT.

---

## 4. Năng lực kỹ thuật

### Hạ tầng

| Thành phần | Công nghệ | Ghi chú |
|-----------|-----------|---------|
| Backend | Python FastAPI | API hiệu năng cao, bảo mật nhiều lớp |
| Frontend | Nuxt 4 (Vue.js SSR) | SEO tối ưu, tải nhanh, responsive |
| Cơ sở dữ liệu | PostgreSQL | Ổn định, mở rộng được |
| Cache | Redis | Phản hồi nhanh (<1 giây) |
| AI/LLM | GPT-5.4 (tool-calling) | Hiểu ngữ cảnh, trả lời tự nhiên |
| Hosting | VPS chuyên dụng | Uptime 99.5%+ |

### Bảo mật

- Mã hóa dữ liệu nhạy cảm (PII masking)
- Chống prompt injection (30+ mẫu Vietnamese)
- Xác thực OTP, chống brute force
- Quét bí mật trong mã nguồn (TruffleHog CI)
- Khóa thao tác phá dữ liệu (destructive ops lock)

### Dữ liệu

- 1.730 thực thể biên tập có ghi nguồn thu thập; trích dẫn + link nguồn hiển thị trên trang khi có nguồn công khai (kiểm chứng thực địa: hạng mục đề xuất hợp tác — mục 2.1)
- 12.208 mối quan hệ (nearby, belongs_to, serves...)
- Dữ liệu mùa vụ gắn với toàn bộ sản phẩm và điểm du lịch
- Knowledge graph cho gợi ý thông minh

---

## 5. Lộ trình hợp tác

### Giai đoạn 1: Pilot (3 tháng)

| Tuần | Hoạt động |
|------|-----------|
| 1-2 | Ký thỏa thuận pilot, xác định scope cụ thể |
| 2-4 | Chuẩn bị dữ liệu theo yêu cầu cơ quan |
| 4-8 | Triển khai, tích hợp widget (nếu có) |
| 8-12 | Vận hành, thu thập feedback, đo lường KPI |

### Giai đoạn 2: Đánh giá

- Báo cáo kết quả pilot: lượt truy cập, lượt tìm kiếm, feedback người dùng
- Đề xuất điều chỉnh (nếu cần)
- Quyết định tiếp tục hoặc dừng

### Giai đoạn 3: Hợp đồng chính thức (12 tháng)

- Ký hợp đồng dịch vụ 12 tháng
- SLA: uptime 99.5%, cập nhật dữ liệu hàng tháng
- Thanh toán: hàng tháng hoặc hàng quý
- Gia hạn tự động nếu hai bên đồng ý

---

## 6. Liên hệ

| Thông tin | Giá trị |
|-----------|---------|
| Dự án | vinhlong360.vn |
| Người liên hệ | [Tên chủ dự án] |
| Điện thoại | [SĐT] |
| Email | [Email] |
| Địa chỉ | [Địa chỉ] |

---

> *Tài liệu này là template nội bộ. Cần điều chỉnh nội dung, số liệu và thông tin liên hệ cụ thể cho từng cơ quan trước khi sử dụng. Giá có thể đàm phán tùy theo scope và ngân sách thực tế của đối tác. Trước khi gửi: đối chiếu lại số liệu với `web/data.json`; TUYỆT ĐỐI không thêm lại claim "đã xác minh/kiểm chứng" khi `attributes.verifiedAt` chưa phủ (CLAUDE.md §1.7). Việc gửi tài liệu đối ngoại phải qua chủ dự án duyệt.*
