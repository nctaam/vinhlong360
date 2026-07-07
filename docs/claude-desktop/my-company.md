# my-company.md — Claude hiểu mục tiêu và định hướng dự án

> STATUS (2026-07-07): active — file dán vào Claude Desktop (Project knowledge của Project "vinhlong360").
> SINH TỪ nguồn chuẩn: CLAUDE.md §0-§1 + docs/standards/. Khi nguồn đổi → sinh lại file này.

## Dự án là gì

**vinhlong360.vn** — mạng xã hội du lịch / OCOP / cộng đồng cho **tỉnh Vĩnh Long MỚI**: đơn vị hành chính hình thành 07/2025 khi sáp nhập Vĩnh Long + Bến Tre + Trà Vinh thành 1 tỉnh, hành chính 2 cấp (1 tỉnh → 124 xã/phường = 35 phường + 89 xã, KHÔNG còn cấp huyện). Trong nội dung: gọi vùng đất theo tỉnh MỚI; chữ "Bến Tre"/"Trà Vinh" đi kèm "tỉnh" chỉ dùng trong văn cảnh lịch sử có ghi rõ "cũ / trước 7-2025".

## Định vị (quan trọng nhất)

- Site **VỀ VĨNH LONG đặc thù** — KHÔNG phải "miền Tây / ĐBSCL" chung chung. Vốn liếng riêng: gạch gốm đỏ Mang Thít, bưởi Năm Roi Bình Minh, dừa sáp Cầu Kè, chùa Khmer Trà Vinh, cù lao An Bình trên sông Cổ Chiên, chợ nổi Trà Ôn, kẹo dừa Bến Tre, chiếu Cà Hom.
- Chống bị-đọc-như-AI và chống Google-spam bằng **chất lượng thật + E-E-A-T**, tuyệt đối không né detector.

## Mô hình — các chốt KHÔNG đổi

1. **CHỈ GIỚI THIỆU**: không đặt hàng/booking/thanh toán on-site, không sàn TMĐT bên thứ ba. CTA chỉ là liên hệ Zalo/điện thoại/hỏi giá. Giữ ở "tầng nhẹ" pháp lý.
2. **Doanh thu**: premium/featured listing + hợp đồng B2G + quảng cáo. KHÔNG hoa hồng booking, KHÔNG bán tour/vé.
3. **Ảnh: CHỈ AI-generated** (pipeline riêng của dự án), luôn kèm nhãn minh hoạ trung thực. CẤM ảnh stock (Pexels/Unsplash), CẤM Wikimedia, CẤM ảnh UGC, CẤM cào ảnh báo/gov.
4. **Trust không khai khống**: byline cấp tổ chức "Ban biên tập vinhlong360" (không tên cá nhân); không tự nhận "đã xác minh/kiểm chứng thực địa" khi chưa đi thực tế; nhãn "chưa có ảnh thật" là tín hiệu trung thực, giữ nguyên.
5. **Không re-host nội dung báo chí** — chỉ tiêu đề + trích đoạn + link gốc.

## Trạng thái & kỹ thuật (tóm tắt cho ngữ cảnh)

- Kiến trúc: backend FastAPI + frontend Nuxt 4 SSR; database là nguồn sự thật duy nhất; ~1.766 điểm đến/đặc sản/nhân vật + hệ cộng đồng (bài viết, hỏi đáp, sự kiện).
- Toàn site đang **chủ động noindex** cho tới khi nội dung đạt chuẩn — mở index là quyết định của chủ dự án.
- Có bộ tiêu chuẩn nội bộ "có răng" (docs/standards/): nợ chất lượng chỉ được giảm, cấm claim khống, cấm filler.
- Đối thủ tham chiếu: vinhlongtourist.vn — mọi trang của mình phải có ≥1 sự thật bản địa mà họ không có.

## Khi giúp tôi làm việc trong Claude Desktop

- Soạn nội dung/chiến lược thì bám các chốt trên; nếu một yêu cầu của tôi mâu thuẫn với chốt (vd "thêm nút đặt phòng") — nhắc tôi về chốt trước, đừng lặng lẽ làm.
- Tài liệu đối ngoại (pitch B2G, bài PR) là bản NHÁP cho tôi duyệt — không tự thêm số liệu/claim chưa kiểm chứng.
