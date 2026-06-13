# Runbook sự cố dữ liệu cá nhân (GĐ5.7)

> Theo Luật BVDLCN 91/2025/QH15 + NĐ356/2025: thông báo cơ quan có thẩm quyền (Bộ Công an/A05)
> trong **72 giờ** kể từ khi phát hiện rò rỉ dữ liệu cá nhân; thông báo người dùng bị ảnh hưởng
> với dữ liệu nhạy cảm/sinh trắc/vị trí.

## Khi nghi ngờ rò rỉ — làm ngay
1. **Khoanh vùng (giờ 0):** chặn truy cập trái phép — rotate `ADMIN_API_KEY`, `LLM_API_KEY`,
   `TELEGRAM_BOT_TOKEN`, mật khẩu Postgres; vô hiệu phiên nghi vấn (`DELETE FROM user_sessions`).
2. **Bảo toàn bằng chứng:** snapshot DB (`pg_dump`) + log (`agent/data/server.log.jsonl`), không xoá.
3. **Đánh giá phạm vi:** dữ liệu gì (SĐT/tên/vị trí/bài đăng), bao nhiêu người, đường rò.
4. **Đồng hồ 72h:** chuẩn bị hồ sơ thông báo (mô tả sự cố, dữ liệu ảnh hưởng, biện pháp khắc phục)
   gửi cơ quan có thẩm quyền trong **72 giờ**.
5. **Thông báo người dùng** bị ảnh hưởng (nếu dữ liệu nhạy cảm/vị trí) qua SMS/email.
6. **Khắc phục & hậu kiểm:** vá lỗ hổng, ghi lại nguyên nhân gốc, cập nhật runbook.

## Liên hệ
- Kênh tiếp nhận của người dùng: trang `/lien-he` (`lienhe@vinhlong360.vn`).
- Người chịu trách nhiệm: chủ dự án (solo). Khi >100k chủ thể dữ liệu hoặc xử lý dữ liệu
  nhạy cảm → cân nhắc bổ nhiệm DPO + nộp hồ sơ DPIA (hiện được miễn cho SME <100k, tới ~2031).

## Liên quan
- `docs/ugc-postgres.md` · `CLAUDE.md` §4 (điều kiện dừng) · pháp lý: NĐ147/2024, Luật 91/2025, NĐ356/2025.
- Track-H (cần con người): pháp nhân + đăng ký NĐ147 + luật sư ICT trước khi ra mắt công khai.
